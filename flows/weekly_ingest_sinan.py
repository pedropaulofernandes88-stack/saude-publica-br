"""
flows/weekly_ingest_sinan.py
============================
Prefect flow para ingestão incremental semanal do SINAN.

Agravos suportados: DENG (dengue), CHIK (chikungunya), ZIKA (zika vírus).

Diferença do SIA/PA/SIH:
  O SINAN distribui dados por AGRAVO + ANO (não por estado/mês).
  O download via PySUS retorna o Brasil completo para cada (agravo, ano);
  a normalização split por UF é feita internamente em ingest_sinan.py.

Convenções de ingestion_log:
  estado  = "BR"  (nível nacional — VARCHAR(2) suportado)
  mes     = 0     (sentinela anual, como SIM/DO)
  sistema = "SINAN_{AGRAVO}"   ex: "SINAN_DENG", "SINAN_CHIK", "SINAN_ZIKA"

Uso:
    # Rodar manualmente:
    python flows/weekly_ingest_sinan.py

    # Deploy no Prefect Cloud:
    prefect deploy flows/weekly_ingest_sinan.py:ingestao_semanal_sinan

    # Agendar via serve:
    prefect flow serve flows/weekly_ingest_sinan.py:ingestao_semanal_sinan \\
        --cron "0 9 * * 1" \\
        --name "ingestao-semanal-sinan"
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
from ingestion.ingest_sinan import (
    AGRAVOS_VALIDOS,
    ingerir_agravo_ano,
)


# ────────────────────────────────────────────────
# Config
# ────────────────────────────────────────────────

load_dotenv()

DATABASE_URL = os.environ["DATABASE_URL"]

# SINAN não particiona por UF — usa "BR" como estado sentinela no log
ESTADO_SINAN = "BR"
# Sentinela: dado anual (sem granularidade mensal)
MES_SINAN = 0

AGRAVOS_DEFAULT = os.getenv(
    "SINAN_AGRAVOS",
    ",".join(AGRAVOS_VALIDOS.keys()),
).split(",")

ANO_INICIO = int(os.getenv("ANO_INICIO", "2020"))
ANO_FIM = int(os.getenv("ANO_FIM", "2024"))


def _sistema(agravo: str) -> str:
    """Chave de sistema no ingestion_log: 'SINAN_DENG', 'SINAN_CHIK', etc."""
    return f"SINAN_{agravo.upper()}"


# ────────────────────────────────────────────────
# Tasks
# ────────────────────────────────────────────────


@task(
    name="verificar-pendencias-sinan",
    description="Lista combinações (agravo, ano) ainda não carregadas",
    retries=2,
    retry_delay_seconds=30,
)
def verificar_pendencias_sinan(
    agravos: list[str],
    anos: list[int],
) -> list[tuple[str, int]]:
    """
    Retorna lista de (agravo, ano) pendentes para ingestão.

    Usa ingestion_log com estado='BR', mes=0 e sistema='SINAN_{agravo}'.
    """
    log = get_run_logger()
    ensure_table(DATABASE_URL)

    pendentes: list[tuple[str, int]] = []
    for agravo in agravos:
        sistema = _sistema(agravo)
        pend = get_pending_combinations(
            [ESTADO_SINAN], anos, [MES_SINAN], sistema, DATABASE_URL
        )
        # get_pending_combinations retorna (estado, ano, mes); extraímos só o ano
        for _, ano, _ in pend:
            pendentes.append((agravo, ano))

    pendentes = sorted(pendentes)
    log.info(f"Total pendente SINAN: {len(pendentes)} combinações (agravo × ano)")
    for agravo in agravos:
        n = sum(1 for a, _ in pendentes if a == agravo)
        if n:
            log.info(f"  {agravo}: {n} ano(s) pendentes")
    return pendentes


@task(
    name="ingerir-agravo-ano",
    description="Baixa, normaliza e carrega um agravo/ano completo do SINAN",
    retries=3,
    retry_delay_seconds=90,
    tags=["ingestao", "sinan"],
)
def ingerir_agravo_ano_task(
    agravo: str,
    ano: int,
    force: bool = False,
) -> dict:
    """
    Pipeline completo para um (agravo, ano):
    1. Verifica ingestion_log (pula se já carregado)
    2. Baixa via PySUS (dado nacional, split por UF internamente)
    3. Carrega no Supabase via COPY
    4. Atualiza ingestion_log
    """
    log = get_run_logger()
    inicio = datetime.now()
    sistema = _sistema(agravo)

    # Guard: já carregado?
    if not force and is_already_loaded(ESTADO_SINAN, ano, MES_SINAN, sistema, DATABASE_URL):
        log.info(f"[SKIP] SINAN/{agravo}/{ano} — já carregado")
        return {"agravo": agravo, "ano": ano, "status": "skipped", "qtd": 0}

    # Marcar como running
    entry = IngestionEntry(
        estado=ESTADO_SINAN, ano=ano, mes=MES_SINAN, sistema=sistema,
        status=IngestionStatus.RUNNING,
    )
    upsert_log(entry, DATABASE_URL)

    try:
        log.info(f"[DOWN] SINAN/{agravo}/{ano} — baixando do DataSUS...")
        qtd = ingerir_agravo_ano(agravo=agravo, ano=ano, dry_run=False)

        elapsed = (datetime.now() - inicio).total_seconds()

        if qtd == 0:
            log.warning(f"[EMPTY] SINAN/{agravo}/{ano} — sem dados disponíveis")
            upsert_log(
                IngestionEntry(
                    estado=ESTADO_SINAN, ano=ano, mes=MES_SINAN, sistema=sistema,
                    status=IngestionStatus.SKIPPED, qtd_registros=0,
                ),
                DATABASE_URL,
            )
            return {"agravo": agravo, "ano": ano, "status": "empty", "qtd": 0}

        log.info(f"[OK] SINAN/{agravo}/{ano} — {qtd:,} registros em {elapsed:.1f}s")
        upsert_log(
            IngestionEntry(
                estado=ESTADO_SINAN, ano=ano, mes=MES_SINAN, sistema=sistema,
                status=IngestionStatus.SUCCESS,
                qtd_registros=qtd,
                elapsed_sec=elapsed,
            ),
            DATABASE_URL,
        )
        return {"agravo": agravo, "ano": ano, "status": "success", "qtd": qtd}

    except Exception as exc:
        elapsed = (datetime.now() - inicio).total_seconds()
        err_msg = str(exc)[:500]
        log.error(f"[ERR] SINAN/{agravo}/{ano} — {err_msg}")
        upsert_log(
            IngestionEntry(
                estado=ESTADO_SINAN, ano=ano, mes=MES_SINAN, sistema=sistema,
                status=IngestionStatus.ERROR,
                error_msg=err_msg,
                elapsed_sec=elapsed,
            ),
            DATABASE_URL,
        )
        raise


@task(
    name="gerar-resumo-sinan",
    description="Consolida resultados da ingestão SINAN",
)
def gerar_resumo_sinan(resultados: list[dict]) -> dict:
    """Gera relatório com totais de sucesso, erro e skip."""
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
        "agravos_com_erro": list({r["agravo"] for r in erros}),
    }

    log.info("=" * 60)
    log.info("RESUMO DA INGESTÃO SINAN")
    log.info(f"  Combinações processadas  : {len(resultados)}")
    log.info(f"  ✅ Sucesso               : {len(sucesso)}")
    log.info(f"  ❌ Erros                 : {len(erros)}")
    log.info(f"  ⏭️  Skips/Vazios          : {len(skips)}")
    log.info(f"  📊 Registros carregados  : {total_registros:,}")
    if erros:
        log.warning(f"  Agravos com erro: {resumo['agravos_com_erro']}")
    log.info("=" * 60)

    return resumo


# ────────────────────────────────────────────────
# Flow principal
# ────────────────────────────────────────────────


@flow(
    name="ingestao-semanal-sinan",
    description="Ingestão incremental semanal do SINAN — dengue, chikungunya e zika, 2020-2024",
    task_runner=ConcurrentTaskRunner(max_workers=3),  # 3 agravos em paralelo
    log_prints=True,
)
def ingestao_semanal_sinan(
    agravos: Optional[list[str]] = None,
    anos: Optional[list[int]] = None,
    force: bool = False,
    dry_run: bool = False,
) -> dict:
    """
    Flow de ingestão incremental do SINAN.

    Args:
        agravos: Códigos de agravo. Padrão: ["DENG", "CHIK", "ZIKA"].
        anos: Anos a processar. Padrão: ANO_INICIO..ANO_FIM do .env.
        force: Re-processar mesmo que já carregado.
        dry_run: Simular sem gravar dados.
    """
    log = get_run_logger()

    _agravos = [a.upper() for a in (agravos or AGRAVOS_DEFAULT)]
    _anos = anos or list(range(ANO_INICIO, ANO_FIM + 1))

    log.info(f"🚀 Iniciando ingestão SINAN")
    log.info(f"   Agravos : {_agravos}")
    log.info(f"   Período : {_anos[0]}–{_anos[-1]}")

    if dry_run:
        log.info("⚠️  DRY RUN — nenhum dado será gravado")
        pendentes = verificar_pendencias_sinan(_agravos, _anos)
        log.info(f"   Seriam processadas: {len(pendentes)} combinações (agravo × ano)")
        return {"dry_run": True, "pendentes": len(pendentes)}

    # Verificar pendências
    pendentes = verificar_pendencias_sinan(_agravos, _anos)

    if not pendentes:
        log.info("✅ Nenhuma combinação pendente — SINAN atualizado!")
        return {"status": "up_to_date", "pendentes": 0}

    log.info(f"📋 {len(pendentes)} combinações para processar")

    # Processar em paralelo (até 3 simultâneos — 1 por agravo)
    futures = [
        ingerir_agravo_ano_task.submit(agravo, ano, force)
        for agravo, ano in pendentes
    ]

    resultados = [f.result(raise_on_failure=False) for f in futures]

    # Resumo final
    resumo = gerar_resumo_sinan(resultados)

    return resumo


# ────────────────────────────────────────────────
# Ponto de entrada (execução direta para teste)
# ────────────────────────────────────────────────

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Ingestão incremental SINAN")
    parser.add_argument(
        "--agravos", nargs="+", default=None,
        help="Códigos de agravo: DENG CHIK ZIKA",
    )
    parser.add_argument("--anos", nargs="+", type=int, default=None)
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    ingestao_semanal_sinan(
        agravos=args.agravos,
        anos=args.anos,
        force=args.force,
        dry_run=args.dry_run,
    )
