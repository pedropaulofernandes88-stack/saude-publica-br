"""
flows/weekly_ingest.py
======================
Prefect flow para ingestão semanal incremental do SIA/PA.

Executa toda segunda-feira às 04:00 BRT.
Baixa apenas as competências ainda não carregadas (controle via ingestion_log).

Uso:
    # Rodar manualmente (teste):
    python flows/weekly_ingest.py

    # Deploy no Prefect Cloud:
    prefect deploy flows/weekly_ingest.py:ingestao_semanal_sia_pa

    # Agendar via serve (auto-hospedado):
    prefect flow serve flows/weekly_ingest.py:ingestao_semanal_sia_pa \
        --cron "0 7 * * 1" \
        --name "ingestao-semanal-sia-pa"
"""

import os
import sys
from datetime import datetime, date
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from loguru import logger
from prefect import flow, task, get_run_logger
from prefect.task_runners import ConcurrentTaskRunner

# Garante imports do projeto
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from ingestion.utils.ingestion_log import (
    IngestionStatus,
    IngestionEntry,
    ensure_table,
    get_pending_combinations,
    is_already_loaded,
    upsert_log,
)
from ingestion.ingest_sia_pa import (
    TODOS_ESTADOS,
    normalizar_dataframe,
    baixar_sia_pa,
)
from ingestion.utils.bulk_load import df_to_supabase_bulk, SIA_PA_SCHEMA


# ────────────────────────────────────────────────
# Config
# ────────────────────────────────────────────────
load_dotenv()

DATABASE_URL = os.environ["DATABASE_URL"]
DATA_DIR = Path(os.getenv("DATA_DIR", "data"))
SISTEMA = "SIA_PA"

# Estados e período padrão (podem ser sobrescritos via parâmetros do flow)
ESTADOS_DEFAULT = os.getenv("ESTADOS_INGESTAO", ",".join(TODOS_ESTADOS)).split(",")
ANO_INICIO = int(os.getenv("ANO_INICIO", "2020"))
ANO_FIM = int(os.getenv("ANO_FIM", "2024"))


# ────────────────────────────────────────────────
# Tasks
# ────────────────────────────────────────────────

@task(
    name="verificar-pendencias",
    description="Lista todas as combinações (estado, ano, mês) ainda não carregadas",
    retries=2,
    retry_delay_seconds=30,
)
def verificar_pendencias(
    estados: list[str],
    anos: list[int],
    meses: list[int],
) -> list[tuple[str, int, int]]:
    """Retorna lista de (estado, ano, mes) pendentes para ingestão."""
    log = get_run_logger()
    ensure_table(DATABASE_URL)
    pendentes = get_pending_combinations(estados, anos, meses, SISTEMA, DATABASE_URL)
    log.info(f"Total pendente: {len(pendentes)} competências de {len(estados)} estados")
    return sorted(pendentes)


@task(
    name="ingerir-competencia",
    description="Baixa, normaliza e carrega uma competência SIA/PA",
    retries=3,
    retry_delay_seconds=60,
    tags=["ingestao", "sia-pa"],
)
def ingerir_competencia(
    estado: str,
    ano: int,
    mes: int,
    force: bool = False,
) -> dict:
    """
    Pipeline completo para uma competência (estado, ano, mês):
    1. Verifica ingestion_log (pula se já carregado)
    2. Baixa via PySUS (com retry)
    3. Normaliza DataFrame
    4. Salva Parquet local
    5. Carrega no Supabase via COPY
    6. Atualiza ingestion_log
    """
    log = get_run_logger()
    inicio = datetime.now()

    # Guard: já carregado?
    if not force and is_already_loaded(estado, ano, mes, SISTEMA, DATABASE_URL):
        log.info(f"[SKIP] {estado}/{ano}/{mes:02d} — já carregado")
        return {"estado": estado, "ano": ano, "mes": mes, "status": "skipped", "qtd": 0}

    # Marcar como running
    entry = IngestionEntry(
        estado=estado, ano=ano, mes=mes, sistema=SISTEMA,
        status=IngestionStatus.RUNNING,
    )
    upsert_log(entry, DATABASE_URL)

    try:
        # Download
        log.info(f"[DOWN] {estado}/{ano}/{mes:02d} — baixando SIA/PA...")
        df_raw = baixar_sia_pa(estado, ano, mes)

        if df_raw is None or df_raw.empty:
            log.warning(f"[EMPTY] {estado}/{ano}/{mes:02d} — sem dados")
            upsert_log(
                IngestionEntry(estado=estado, ano=ano, mes=mes, sistema=SISTEMA,
                               status=IngestionStatus.SKIPPED, qtd_registros=0),
                DATABASE_URL,
            )
            return {"estado": estado, "ano": ano, "mes": mes, "status": "empty", "qtd": 0}

        # Normalizar
        df = normalizar_dataframe(df_raw, estado)
        qtd = len(df)
        log.info(f"[NORM] {estado}/{ano}/{mes:02d} — {qtd:,} registros normalizados")

        # Parquet + Supabase COPY
        df_to_supabase_bulk(
            df=df,
            uf=estado,
            ano=ano,
            mes=mes,
            table_name="sia_pa_raw",
            columns=list(SIA_PA_SCHEMA.names),
            database_url=DATABASE_URL,
            base_dir=DATA_DIR,
            schema=SIA_PA_SCHEMA,
        )

        elapsed = (datetime.now() - inicio).total_seconds()

        # Sucesso
        upsert_log(
            IngestionEntry(
                estado=estado, ano=ano, mes=mes, sistema=SISTEMA,
                status=IngestionStatus.SUCCESS,
                qtd_registros=qtd,
                elapsed_sec=elapsed,
            ),
            DATABASE_URL,
        )

        log.info(f"[OK] {estado}/{ano}/{mes:02d} — {qtd:,} reg em {elapsed:.1f}s")
        return {"estado": estado, "ano": ano, "mes": mes, "status": "success", "qtd": qtd}

    except Exception as exc:
        elapsed = (datetime.now() - inicio).total_seconds()
        err_msg = str(exc)[:500]
        log.error(f"[ERR] {estado}/{ano}/{mes:02d} — {err_msg}")
        upsert_log(
            IngestionEntry(
                estado=estado, ano=ano, mes=mes, sistema=SISTEMA,
                status=IngestionStatus.ERROR,
                error_msg=err_msg,
                elapsed_sec=elapsed,
            ),
            DATABASE_URL,
        )
        raise


@task(
    name="gerar-resumo-ingestao",
    description="Consolida resultados da ingestão e gera relatório",
)
def gerar_resumo(resultados: list[dict]) -> dict:
    """Gera relatório com totais de sucesso, erro e skip."""
    log = get_run_logger()

    sucesso = [r for r in resultados if r.get("status") == "success"]
    erros = [r for r in resultados if r.get("status") == "error"]
    skips = [r for r in resultados if r.get("status") in ("skipped", "empty")]

    total_registros = sum(r.get("qtd", 0) for r in sucesso)

    resumo = {
        "data_execucao": datetime.now().isoformat(),
        "total_competencias": len(resultados),
        "sucesso": len(sucesso),
        "erros": len(erros),
        "skips": len(skips),
        "total_registros_carregados": total_registros,
        "estados_com_erro": list({r["estado"] for r in erros}),
    }

    log.info("=" * 60)
    log.info("RESUMO DA INGESTÃO SEMANAL")
    log.info(f"  Competências processadas : {len(resultados)}")
    log.info(f"  ✅ Sucesso               : {len(sucesso)}")
    log.info(f"  ❌ Erros                 : {len(erros)}")
    log.info(f"  ⏭️  Skips/Vazios          : {len(skips)}")
    log.info(f"  📊 Registros carregados  : {total_registros:,}")
    if erros:
        log.warning(f"  Estados com erro: {resumo['estados_com_erro']}")
    log.info("=" * 60)

    return resumo


# ────────────────────────────────────────────────
# Flow principal
# ────────────────────────────────────────────────

@flow(
    name="ingestao-semanal-sia-pa",
    description="Ingestão incremental semanal do SIA/PA — todos os 27 estados, 2020-2024",
    task_runner=ConcurrentTaskRunner(max_workers=4),  # 4 estados em paralelo
    log_prints=True,
)
def ingestao_semanal_sia_pa(
    estados: Optional[list[str]] = None,
    anos: Optional[list[int]] = None,
    meses: Optional[list[int]] = None,
    force: bool = False,
    dry_run: bool = False,
) -> dict:
    """
    Flow de ingestão incremental do SIA/PA.

    Args:
        estados: Lista de siglas de UF. Padrão: todos os 27.
        anos: Anos a processar. Padrão: ANO_INICIO..ANO_FIM do .env.
        meses: Meses a processar. Padrão: 1-12 (ano completo).
        force: Re-processar mesmo que já carregado.
        dry_run: Simular sem gravar dados.
    """
    log = get_run_logger()

    # Defaults
    _estados = estados or ESTADOS_DEFAULT
    _anos = anos or list(range(ANO_INICIO, ANO_FIM + 1))
    _meses = meses or list(range(1, 13))

    log.info(f"🚀 Iniciando ingestão: {len(_estados)} estados × {len(_anos)} anos × {len(_meses)} meses")
    log.info(f"   Estados: {_estados}")
    log.info(f"   Período: {_anos[0]}–{_anos[-1]}")

    if dry_run:
        log.info("⚠️  DRY RUN — nenhum dado será gravado")
        pendentes = verificar_pendencias(_estados, _anos, _meses)
        log.info(f"   Seriam processadas: {len(pendentes)} competências")
        return {"dry_run": True, "pendentes": len(pendentes)}

    # Verificar pendências
    pendentes = verificar_pendencias(_estados, _anos, _meses)

    if not pendentes:
        log.info("✅ Nenhuma competência pendente — pipeline atualizado!")
        return {"status": "up_to_date", "pendentes": 0}

    log.info(f"📋 {len(pendentes)} competências para processar")

    # Processar em paralelo (até 4 simultâneos via ConcurrentTaskRunner)
    futures = [
        ingerir_competencia.submit(estado, ano, mes, force)
        for estado, ano, mes in pendentes
    ]

    resultados = [f.result(raise_on_failure=False) for f in futures]

    # Resumo final
    resumo = gerar_resumo(resultados)

    return resumo


# ────────────────────────────────────────────────
# Ponto de entrada (execução direta para teste)
# ────────────────────────────────────────────────

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Ingestão incremental SIA/PA")
    parser.add_argument("--estados", nargs="+", default=None, help="Siglas de UF")
    parser.add_argument("--anos", nargs="+", type=int, default=None)
    parser.add_argument("--meses", nargs="+", type=int, default=None)
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    ingestao_semanal_sia_pa(
        estados=args.estados,
        anos=args.anos,
        meses=args.meses,
        force=args.force,
        dry_run=args.dry_run,
    )
