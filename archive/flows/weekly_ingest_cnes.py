"""
flows/weekly_ingest_cnes.py
===========================
Prefect flow para ingestão incremental semanal do CNES.

Grupos suportados: ST (estabelecimentos) e LT (leitos).

Diferença do SIA/PA:
  O CNES é particionado por GRUPO + UF + ANO + MÊS.
  Cada combinação (grupo, uf, ano, mes) é uma unidade de trabalho independente.
  O flow processa ST e LT separadamente, com sistemas distintos no ingestion_log.

Convenções de ingestion_log:
  estado  = sigla da UF   (ex: "SP", "RJ")
  mes     = mês competência (1–12)
  sistema = "CNES_ST"  ou  "CNES_LT"

Uso:
    # Rodar manualmente:
    python flows/weekly_ingest_cnes.py

    # Deploy no Prefect Cloud:
    prefect deploy flows/weekly_ingest_cnes.py:ingestao_semanal_cnes

    # Agendar via serve:
    prefect flow serve flows/weekly_ingest_cnes.py:ingestao_semanal_cnes \\
        --cron "0 8 * * 1" \\
        --name "ingestao-semanal-cnes"
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
from ingestion.ingest_cnes import (
    TODOS_ESTADOS,
    GRUPOS_VALIDOS,
    ingerir_cnes_uf_mes,
)


# ────────────────────────────────────────────────
# Config
# ────────────────────────────────────────────────

load_dotenv()

DATABASE_URL = os.environ["DATABASE_URL"]

GRUPOS_DEFAULT = os.getenv(
    "CNES_GRUPOS",
    ",".join(GRUPOS_VALIDOS.keys()),
).split(",")

ESTADOS_DEFAULT = os.getenv(
    "ESTADOS_INGESTAO",
    ",".join(TODOS_ESTADOS),
).split(",")

ANO_INICIO = int(os.getenv("ANO_INICIO", "2020"))
ANO_FIM = int(os.getenv("ANO_FIM", "2024"))
MESES_DEFAULT = list(range(1, 13))


def _sistema(grupo: str) -> str:
    """Chave de sistema no ingestion_log: 'CNES_ST' ou 'CNES_LT'."""
    return f"CNES_{grupo.upper()}"


# ────────────────────────────────────────────────
# Tasks
# ────────────────────────────────────────────────


@task(
    name="verificar-pendencias-cnes",
    description="Lista combinações (grupo, uf, ano, mes) ainda não carregadas",
    retries=2,
    retry_delay_seconds=30,
)
def verificar_pendencias_cnes(
    grupos: list[str],
    estados: list[str],
    anos: list[int],
    meses: list[int],
) -> list[tuple[str, str, int, int]]:
    """
    Retorna lista de (grupo, uf, ano, mes) pendentes para ingestão.

    Consulta o ingestion_log separadamente para cada grupo (sistema distinto).
    """
    log = get_run_logger()
    ensure_table(DATABASE_URL)

    pendentes: list[tuple[str, str, int, int]] = []
    for grupo in grupos:
        sistema = _sistema(grupo)
        pend = get_pending_combinations(estados, anos, meses, sistema, DATABASE_URL)
        for uf, ano, mes in pend:
            pendentes.append((grupo, uf, ano, mes))

    pendentes = sorted(pendentes)
    log.info(f"Total pendente CNES: {len(pendentes)} combinações (grupo × uf × ano × mes)")
    for grupo in grupos:
        n = sum(1 for g, *_ in pendentes if g == grupo)
        if n:
            log.info(f"  {grupo} ({GRUPOS_VALIDOS.get(grupo, grupo)}): {n} combinação(ões) pendente(s)")
    return pendentes


@task(
    name="ingerir-cnes-uf-mes",
    description="Baixa, normaliza e carrega um grupo/UF/mês do CNES",
    retries=3,
    retry_delay_seconds=90,
    tags=["ingestao", "cnes"],
)
def ingerir_cnes_uf_mes_task(
    grupo: str,
    uf: str,
    ano: int,
    mes: int,
    force: bool = False,
) -> dict:
    """
    Pipeline completo para um (grupo, uf, ano, mes):
    1. Verifica ingestion_log (pula se já carregado)
    2. Baixa via PySUS (CNES)
    3. Carrega no Supabase via COPY
    4. Atualiza ingestion_log
    """
    log = get_run_logger()
    inicio = datetime.now()
    sistema = _sistema(grupo)

    # Guard: já carregado?
    if not force and is_already_loaded(uf, ano, mes, sistema, DATABASE_URL):
        log.info(f"[SKIP] CNES/{grupo}/{uf}/{ano}/{mes:02d} — já carregado")
        return {"grupo": grupo, "uf": uf, "ano": ano, "mes": mes, "status": "skipped", "qtd": 0}

    # Marcar como running
    entry = IngestionEntry(
        estado=uf, ano=ano, mes=mes, sistema=sistema,
        status=IngestionStatus.RUNNING,
    )
    upsert_log(entry, DATABASE_URL)

    try:
        log.info(f"[DOWN] CNES/{grupo}/{uf}/{ano}/{mes:02d} — baixando do DataSUS...")
        qtd = ingerir_cnes_uf_mes(grupo=grupo, uf=uf, ano=ano, mes=mes, dry_run=False)

        elapsed = (datetime.now() - inicio).total_seconds()

        if qtd == 0:
            log.warning(f"[EMPTY] CNES/{grupo}/{uf}/{ano}/{mes:02d} — sem dados disponíveis")
            upsert_log(
                IngestionEntry(
                    estado=uf, ano=ano, mes=mes, sistema=sistema,
                    status=IngestionStatus.SKIPPED, qtd_registros=0,
                ),
                DATABASE_URL,
            )
            return {"grupo": grupo, "uf": uf, "ano": ano, "mes": mes, "status": "empty", "qtd": 0}

        log.info(f"[OK] CNES/{grupo}/{uf}/{ano}/{mes:02d} — {qtd:,} registros em {elapsed:.1f}s")
        upsert_log(
            IngestionEntry(
                estado=uf, ano=ano, mes=mes, sistema=sistema,
                status=IngestionStatus.SUCCESS,
                qtd_registros=qtd,
                elapsed_sec=elapsed,
            ),
            DATABASE_URL,
        )
        return {"grupo": grupo, "uf": uf, "ano": ano, "mes": mes, "status": "success", "qtd": qtd}

    except Exception as exc:
        elapsed = (datetime.now() - inicio).total_seconds()
        err_msg = str(exc)[:500]
        log.error(f"[ERR] CNES/{grupo}/{uf}/{ano}/{mes:02d} — {err_msg}")
        upsert_log(
            IngestionEntry(
                estado=uf, ano=ano, mes=mes, sistema=sistema,
                status=IngestionStatus.ERROR,
                error_msg=err_msg,
                elapsed_sec=elapsed,
            ),
            DATABASE_URL,
        )
        raise


@task(
    name="gerar-resumo-cnes",
    description="Consolida resultados da ingestão CNES",
)
def gerar_resumo_cnes(resultados: list[dict]) -> dict:
    """Gera relatório com totais de sucesso, erro e skip por grupo."""
    log = get_run_logger()

    sucesso = [r for r in resultados if r.get("status") == "success"]
    erros = [r for r in resultados if r.get("status") == "error"]
    skips = [r for r in resultados if r.get("status") in ("skipped", "empty")]

    total_registros = sum(r.get("qtd", 0) for r in sucesso)

    resumo = {
        "data_execucao": datetime.now().isoformat(),
        "total_combinacoes": len(resultados),
        "sucesso": len(sucesso),
        "erros": len(erros),
        "skips": len(skips),
        "total_registros_carregados": total_registros,
        "grupos_com_erro": list({r["grupo"] for r in erros}),
        "ufs_com_erro": list({r["uf"] for r in erros}),
    }

    log.info("=" * 60)
    log.info("RESUMO DA INGESTÃO CNES")
    log.info(f"  Combinações processadas  : {len(resultados)}")
    log.info(f"  ✅ Sucesso               : {len(sucesso)}")
    log.info(f"  ❌ Erros                 : {len(erros)}")
    log.info(f"  ⏭️  Skips/Vazios          : {len(skips)}")
    log.info(f"  📊 Registros carregados  : {total_registros:,}")
    if erros:
        log.warning(f"  Grupos com erro: {resumo['grupos_com_erro']}")
        log.warning(f"  UFs com erro   : {resumo['ufs_com_erro']}")
    log.info("=" * 60)

    return resumo


# ────────────────────────────────────────────────
# Flow principal
# ────────────────────────────────────────────────


@flow(
    name="ingestao-semanal-cnes",
    description="Ingestão incremental semanal do CNES — estabelecimentos (ST) e leitos (LT), 2020-2024",
    task_runner=ConcurrentTaskRunner(max_workers=4),
    log_prints=True,
)
def ingestao_semanal_cnes(
    grupos: Optional[list[str]] = None,
    estados: Optional[list[str]] = None,
    anos: Optional[list[int]] = None,
    meses: Optional[list[int]] = None,
    force: bool = False,
    dry_run: bool = False,
) -> dict:
    """
    Flow de ingestão incremental do CNES.

    Args:
        grupos: Códigos de grupo. Padrão: ["ST", "LT"].
        estados: Siglas das UFs. Padrão: todos os 27 estados.
        anos: Anos a processar. Padrão: ANO_INICIO..ANO_FIM do .env.
        meses: Meses a processar. Padrão: 1–12.
        force: Re-processar mesmo que já carregado.
        dry_run: Simular sem gravar dados.
    """
    log = get_run_logger()

    _grupos = [g.upper() for g in (grupos or GRUPOS_DEFAULT)]
    _estados = [e.upper() for e in (estados or ESTADOS_DEFAULT)]
    _anos = anos or list(range(ANO_INICIO, ANO_FIM + 1))
    _meses = meses or MESES_DEFAULT

    log.info(f"🚀 Iniciando ingestão CNES")
    log.info(f"   Grupos  : {_grupos}")
    log.info(f"   Estados : {len(_estados)} UFs")
    log.info(f"   Período : {_anos[0]}–{_anos[-1]}, meses {_meses[0]}–{_meses[-1]}")

    if dry_run:
        log.info("⚠️  DRY RUN — nenhum dado será gravado")
        pendentes = verificar_pendencias_cnes(_grupos, _estados, _anos, _meses)
        log.info(f"   Seriam processadas: {len(pendentes)} combinações (grupo × uf × ano × mes)")
        return {"dry_run": True, "pendentes": len(pendentes)}

    # Verificar pendências
    pendentes = verificar_pendencias_cnes(_grupos, _estados, _anos, _meses)

    if not pendentes:
        log.info("✅ Nenhuma combinação pendente — CNES atualizado!")
        return {"status": "up_to_date", "pendentes": 0}

    log.info(f"📋 {len(pendentes)} combinações para processar")

    # Processar em paralelo (até 4 simultâneos)
    futures = [
        ingerir_cnes_uf_mes_task.submit(grupo, uf, ano, mes, force)
        for grupo, uf, ano, mes in pendentes
    ]

    resultados = [f.result(raise_on_failure=False) for f in futures]

    # Resumo final
    resumo = gerar_resumo_cnes(resultados)

    return resumo


# ────────────────────────────────────────────────
# Ponto de entrada (execução direta para teste)
# ────────────────────────────────────────────────

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Ingestão incremental CNES")
    parser.add_argument(
        "--grupos", nargs="+", default=None,
        help="Grupos: ST LT",
    )
    parser.add_argument(
        "--estados", nargs="+", default=None,
        help="Siglas das UFs (ex: SP RJ MG)",
    )
    parser.add_argument("--anos", nargs="+", type=int, default=None)
    parser.add_argument(
        "--meses", nargs="+", type=int, default=None,
        help="Meses (1-12)",
    )
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    ingestao_semanal_cnes(
        grupos=args.grupos,
        estados=args.estados,
        anos=args.anos,
        meses=args.meses,
        force=args.force,
        dry_run=args.dry_run,
    )
