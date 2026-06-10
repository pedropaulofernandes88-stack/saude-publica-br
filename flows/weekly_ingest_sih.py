"""
flows/weekly_ingest_sih.py
==========================
Prefect flow para ingestão mensal incremental do SIH/AIH
(Sistema de Informações Hospitalares / Autorização de Internação Hospitalar).

SIH tem granularidade mensal (estado × ano × mês).

Uso:
    # Executar diretamente (teste local):
    python flows/weekly_ingest_sih.py

    # Forçar re-ingestão de um estado:
    python flows/weekly_ingest_sih.py --estados SP --force

    # Dry-run (ver pendências sem gravar):
    python flows/weekly_ingest_sih.py --dry-run

    # Deploy no Prefect Cloud:
    prefect deploy flows/weekly_ingest_sih.py:ingestao_semanal_sih_aih \
        --name "ingestao-semanal-sih-aih"

    # Serve local com agendamento (todo domingo às 06:00 BRT):
    prefect flow serve flows/weekly_ingest_sih.py:ingestao_semanal_sih_aih \
        --cron "0 9 * * 0" \
        --name "ingestao-semanal-sih-aih"
"""

from __future__ import annotations

import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
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
from ingestion.ingest_sih import (
    TODOS_ESTADOS,
    COLUNAS_SUPABASE,
    baixar_sih_aih,
    normalizar_dataframe,
)
from ingestion.utils.bulk_load import df_to_parquet, parquet_to_supabase, SIH_AIH_SCHEMA


# ────────────────────────────────────────────────
# Config
# ────────────────────────────────────────────────
load_dotenv()

DATABASE_URL = os.environ["DATABASE_URL"]
DATA_DIR = Path(os.getenv("DATA_DIR", "data"))

SISTEMA = "SIH_AIH"

ESTADOS_DEFAULT = os.getenv("ESTADOS_INGESTAO", ",".join(TODOS_ESTADOS)).split(",")
ANO_INICIO  = int(os.getenv("ANO_INICIO", "2020"))
ANO_FIM     = int(os.getenv("ANO_FIM", "2024"))
MESES_DEFAULT = list(range(1, 13))  # 1–12


# ────────────────────────────────────────────────
# Tasks
# ────────────────────────────────────────────────

@task(
    name="verificar-pendencias-sih",
    description="Lista todos os (estado, ano, mes) SIH/AIH ainda não carregados",
    retries=2,
    retry_delay_seconds=30,
)
def verificar_pendencias_sih(
    estados: list[str],
    anos: list[int],
    meses: list[int],
) -> list[tuple[str, int, int]]:
    """
    Retorna lista de (estado, ano, mes) pendentes para ingestão SIH/AIH.
    """
    log = get_run_logger()
    ensure_table(DATABASE_URL)

    pendentes = get_pending_combinations(
        estados, anos, meses, SISTEMA, DATABASE_URL
    )

    log.info(
        f"SIH/AIH pendente: {len(pendentes)} combinações "
        f"de {len(estados)} estados × {len(anos)} anos × {len(meses)} meses"
    )
    return sorted(pendentes)


@task(
    name="ingerir-competencia-sih",
    description="Baixa, normaliza e carrega dados de internações SIH/AIH de um estado/ano/mês",
    retries=3,
    retry_delay_seconds=60,
    tags=["ingestao", "sih-aih"],
)
def ingerir_competencia_sih(
    estado: str,
    ano: int,
    mes: int,
    force: bool = False,
) -> dict:
    """
    Pipeline completo para uma combinação (estado, ano, mes) SIH/AIH:
      1. Verifica ingestion_log (pula se já carregado)
      2. Marca RUNNING no ingestion_log
      3. Baixa via PySUS (baixar_sih_aih)
      4. Normaliza DataFrame (normalizar_dataframe)
      5. Salva Parquet local
      6. Carrega no Supabase (public.sih_aih_raw) via COPY
      7. Atualiza ingestion_log (SUCCESS / ERROR)

    Returns
    -------
    dict com chaves: estado, ano, mes, status, qtd
    """
    log = get_run_logger()
    inicio = datetime.now()

    # ── Guard: já carregado? ──────────────────────────────────────────────
    if not force and is_already_loaded(estado, ano, mes, SISTEMA, DATABASE_URL):
        log.info(f"[SKIP] {estado}/{ano}/{mes:02d} SIH/AIH — já carregado")
        return {"estado": estado, "ano": ano, "mes": mes, "status": "skipped", "qtd": 0}

    # ── Marcar RUNNING ───────────────────────────────────────────────────
    upsert_log(
        IngestionEntry(
            estado=estado, ano=ano, mes=mes, sistema=SISTEMA,
            status=IngestionStatus.RUNNING,
        ),
        DATABASE_URL,
    )

    try:
        # ── Download ──────────────────────────────────────────────────────
        log.info(f"[DOWN] {estado}/{ano}/{mes:02d} SIH/AIH — baixando via PySUS...")
        df_raw = baixar_sih_aih(estado, ano, mes)

        if df_raw is None or df_raw.empty:
            log.warning(f"[EMPTY] {estado}/{ano}/{mes:02d} SIH/AIH — sem dados retornados")
            upsert_log(
                IngestionEntry(
                    estado=estado, ano=ano, mes=mes, sistema=SISTEMA,
                    status=IngestionStatus.SKIPPED, qtd_registros=0,
                ),
                DATABASE_URL,
            )
            return {"estado": estado, "ano": ano, "mes": mes, "status": "empty", "qtd": 0}

        # ── Normalizar ────────────────────────────────────────────────────
        df = normalizar_dataframe(df_raw, estado, ano, mes)
        qtd = len(df)
        log.info(f"[NORM] {estado}/{ano}/{mes:02d} SIH/AIH — {qtd:,} registros normalizados")

        # ── Parquet local ─────────────────────────────────────────────────
        parquet_path = df_to_parquet(
            df=df,
            uf=estado,
            ano=ano,
            mes=mes,
            table_name="sih_aih_raw",
            base_dir=DATA_DIR,
            schema=SIH_AIH_SCHEMA,
        )

        # ── Supabase COPY ─────────────────────────────────────────────────
        parquet_to_supabase(
            parquet_path=parquet_path,
            table_name="public.sih_aih_raw",
            columns=list(SIH_AIH_SCHEMA.names),
            database_url=DATABASE_URL,
        )

        elapsed = (datetime.now() - inicio).total_seconds()

        # ── SUCCESS ───────────────────────────────────────────────────────
        upsert_log(
            IngestionEntry(
                estado=estado, ano=ano, mes=mes, sistema=SISTEMA,
                status=IngestionStatus.SUCCESS,
                qtd_registros=qtd,
                elapsed_sec=elapsed,
            ),
            DATABASE_URL,
        )

        log.info(f"[OK] {estado}/{ano}/{mes:02d} SIH/AIH — {qtd:,} registros em {elapsed:.1f}s")
        return {"estado": estado, "ano": ano, "mes": mes, "status": "success", "qtd": qtd}

    except Exception as exc:
        elapsed = (datetime.now() - inicio).total_seconds()
        err_msg = str(exc)[:500]
        log.error(f"[ERR] {estado}/{ano}/{mes:02d} SIH/AIH — {err_msg}")
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
    name="gerar-resumo-sih",
    description="Consolida resultados da ingestão SIH/AIH",
)
def gerar_resumo_sih(resultados: list[dict]) -> dict:
    """Gera relatório com totais de sucesso, erro e skip."""
    log = get_run_logger()

    sucesso = [r for r in resultados if r.get("status") == "success"]
    erros   = [r for r in resultados if r.get("status") == "error"]
    skips   = [r for r in resultados if r.get("status") in ("skipped", "empty")]

    total_registros = sum(r.get("qtd", 0) for r in sucesso)

    resumo = {
        "data_execucao": datetime.now().isoformat(),
        "total_combinacoes": len(resultados),
        "sucesso": len(sucesso),
        "erros": len(erros),
        "skips": len(skips),
        "total_registros_carregados": total_registros,
        "estados_com_erro": list({r["estado"] for r in erros}),
    }

    log.info("=" * 60)
    log.info("RESUMO DA INGESTÃO SIH/AIH (INTERNAÇÕES)")
    log.info(f"  Combinações processadas  : {len(resultados)}")
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
    name="ingestao-semanal-sih-aih",
    description=(
        "Ingestão incremental mensal do SIH/AIH (internações hospitalares) — "
        "todos os 27 estados, 2020-2024"
    ),
    task_runner=ConcurrentTaskRunner(max_workers=4),
    log_prints=True,
)
def ingestao_semanal_sih_aih(
    estados: Optional[list[str]] = None,
    anos: Optional[list[int]] = None,
    meses: Optional[list[int]] = None,
    force: bool = False,
    dry_run: bool = False,
) -> dict:
    """
    Flow de ingestão incremental do SIH/AIH.

    Args:
        estados : Lista de siglas de UF. Padrão: todos os 27.
        anos    : Anos a processar. Padrão: ANO_INICIO..ANO_FIM do .env.
        meses   : Meses a processar. Padrão: 1–12.
        force   : Re-processar mesmo que já carregado.
        dry_run : Simular sem gravar dados.

    Returns
    -------
    dict com resumo: sucesso, erros, skips, total_registros_carregados.
    """
    log = get_run_logger()

    _estados = estados or ESTADOS_DEFAULT
    _anos    = anos or list(range(ANO_INICIO, ANO_FIM + 1))
    _meses   = meses or MESES_DEFAULT

    log.info(
        f"🚀 Ingestão SIH/AIH: {len(_estados)} estados × "
        f"{len(_anos)} anos × {len(_meses)} meses"
    )
    log.info(f"   Estados : {_estados}")
    log.info(f"   Período : {_anos[0]}–{_anos[-1]}")

    if dry_run:
        log.info("⚠️  DRY RUN — nenhum dado será gravado")
        pendentes = verificar_pendencias_sih(_estados, _anos, _meses)
        log.info(
            f"   Seriam processadas: {len(pendentes)} combinações "
            "(estado × ano × mês)"
        )
        return {"dry_run": True, "pendentes": len(pendentes)}

    # Verificar pendências
    pendentes = verificar_pendencias_sih(_estados, _anos, _meses)

    if not pendentes:
        log.info("✅ Nenhuma combinação pendente — SIH/AIH atualizado!")
        return {"status": "up_to_date", "pendentes": 0, "total_registros_carregados": 0}

    log.info(f"📋 {len(pendentes)} combinações (estado × ano × mês) para processar")

    # Processar em paralelo (até 4 simultâneos)
    futures = [
        ingerir_competencia_sih.submit(estado, ano, mes, force)
        for estado, ano, mes in pendentes
    ]

    resultados = [f.result(raise_on_failure=False) for f in futures]
    resumo = gerar_resumo_sih(resultados)

    return resumo


# ────────────────────────────────────────────────
# Ponto de entrada (execução direta para teste)
# ────────────────────────────────────────────────

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Ingestão incremental SIH/AIH (internações)")
    parser.add_argument("--estados", nargs="+", default=None, help="Siglas de UF (ex: SP RJ MG)")
    parser.add_argument("--anos", nargs="+", type=int, default=None, help="Anos (ex: 2022 2023)")
    parser.add_argument("--meses", nargs="+", type=int, default=None, help="Meses (ex: 1 2 3)")
    parser.add_argument("--force", action="store_true", help="Re-processar mesmo que já carregado")
    parser.add_argument("--dry-run", action="store_true", help="Simular sem gravar")
    args = parser.parse_args()

    ingestao_semanal_sih_aih(
        estados=args.estados,
        anos=args.anos,
        meses=args.meses,
        force=args.force,
        dry_run=args.dry_run,
    )
