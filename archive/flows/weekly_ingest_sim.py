"""
flows/weekly_ingest_sim.py
==========================
Prefect flow para ingestão anual incremental do SIM/DO
(Sistema de Informações sobre Mortalidade / Declaração de Óbito).

SIM tem granularidade anual (estado × ano — sem mês).
O ingestion_log usa mes=0 como sentinel para registros anuais.

Uso:
    # Executar diretamente (teste local):
    python flows/weekly_ingest_sim.py

    # Forçar re-ingestão de um estado:
    python flows/weekly_ingest_sim.py --estados SP --force

    # Dry-run (ver pendências sem gravar):
    python flows/weekly_ingest_sim.py --dry-run

    # Deploy no Prefect Cloud:
    prefect deploy flows/weekly_ingest_sim.py:ingestao_anual_sim_do \
        --name "ingestao-anual-sim-do"

    # Serve local com agendamento (todo domingo às 05:00 BRT):
    prefect flow serve flows/weekly_ingest_sim.py:ingestao_anual_sim_do \
        --cron "0 8 * * 0" \
        --name "ingestao-anual-sim-do"
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
from ingestion.ingest_sim import (
    TODOS_ESTADOS,
    COLUNAS_SUPABASE,
    baixar_sim_do,
    normalizar_dataframe,
)
from ingestion.utils.bulk_load import df_to_parquet, parquet_to_supabase, SIM_DO_SCHEMA


# ────────────────────────────────────────────────
# Config
# ────────────────────────────────────────────────
load_dotenv()

DATABASE_URL = os.environ["DATABASE_URL"]
DATA_DIR = Path(os.getenv("DATA_DIR", "data"))

SISTEMA = "SIM_DO"
# SIM é anual: usamos mes=0 como sentinel no ingestion_log
# (consistente com ingest_sim.py que também define MES_ANUAL=0)
MES_ANUAL = 0

ESTADOS_DEFAULT = os.getenv("ESTADOS_INGESTAO", ",".join(TODOS_ESTADOS)).split(",")
ANO_INICIO = int(os.getenv("ANO_INICIO", "2020"))
ANO_FIM = int(os.getenv("ANO_FIM", "2024"))


# ────────────────────────────────────────────────
# Tasks
# ────────────────────────────────────────────────

@task(
    name="verificar-pendencias-sim",
    description="Lista todos os (estado, ano) SIM/DO ainda não carregados",
    retries=2,
    retry_delay_seconds=30,
)
def verificar_pendencias_sim(
    estados: list[str],
    anos: list[int],
) -> list[tuple[str, int]]:
    """
    Retorna lista de (estado, ano) pendentes para ingestão SIM/DO.

    Internamente passa meses=[MES_ANUAL] ao get_pending_combinations para que
    a busca no ingestion_log use o sentinel correto (mes=0).
    """
    log = get_run_logger()
    ensure_table(DATABASE_URL)

    # get_pending_combinations devolve (estado, ano, mes) — descartamos mes (sempre 0 para SIM)
    pendentes_raw = get_pending_combinations(
        estados, anos, [MES_ANUAL], SISTEMA, DATABASE_URL
    )
    pendentes = [(estado, ano) for estado, ano, _ in pendentes_raw]

    log.info(
        f"SIM/DO pendente: {len(pendentes)} combinações "
        f"de {len(estados)} estados × {len(anos)} anos"
    )
    return sorted(pendentes)


@task(
    name="ingerir-ano-sim",
    description="Baixa, normaliza e carrega dados de óbitos SIM/DO de um estado/ano",
    retries=3,
    retry_delay_seconds=60,
    tags=["ingestao", "sim-do"],
)
def ingerir_ano_sim(
    estado: str,
    ano: int,
    force: bool = False,
) -> dict:
    """
    Pipeline completo para uma combinação (estado, ano) SIM/DO:
      1. Verifica ingestion_log (pula se já carregado)
      2. Marca RUNNING no ingestion_log
      3. Baixa via PySUS (baixar_sim_do)
      4. Normaliza DataFrame (normalizar_dataframe — sem parâmetro mes)
      5. Salva Parquet local
      6. Carrega no Supabase (public.sim_do_raw) via COPY
      7. Atualiza ingestion_log (SUCCESS / ERROR)

    Returns
    -------
    dict com chaves: estado, ano, status, qtd
    """
    log = get_run_logger()
    inicio = datetime.now()

    # ── Guard: já carregado? ──────────────────────────────────────────────
    if not force and is_already_loaded(estado, ano, MES_ANUAL, SISTEMA, DATABASE_URL):
        log.info(f"[SKIP] {estado}/{ano} SIM/DO — já carregado")
        return {"estado": estado, "ano": ano, "status": "skipped", "qtd": 0}

    # ── Marcar RUNNING ───────────────────────────────────────────────────
    upsert_log(
        IngestionEntry(
            estado=estado, ano=ano, mes=MES_ANUAL, sistema=SISTEMA,
            status=IngestionStatus.RUNNING,
        ),
        DATABASE_URL,
    )

    try:
        # ── Download ──────────────────────────────────────────────────────
        log.info(f"[DOWN] {estado}/{ano} SIM/DO — baixando via PySUS...")
        df_raw = baixar_sim_do(estado, ano)

        if df_raw is None or df_raw.empty:
            log.warning(f"[EMPTY] {estado}/{ano} SIM/DO — sem dados retornados")
            upsert_log(
                IngestionEntry(
                    estado=estado, ano=ano, mes=MES_ANUAL, sistema=SISTEMA,
                    status=IngestionStatus.SKIPPED, qtd_registros=0,
                ),
                DATABASE_URL,
            )
            return {"estado": estado, "ano": ano, "status": "empty", "qtd": 0}

        # ── Normalizar (SIM não tem mes) ──────────────────────────────────
        df = normalizar_dataframe(df_raw, estado, ano)
        qtd = len(df)
        log.info(f"[NORM] {estado}/{ano} SIM/DO — {qtd:,} registros normalizados")

        # ── Parquet local ─────────────────────────────────────────────────
        parquet_path = df_to_parquet(
            df=df,
            uf=estado,
            ano=ano,
            mes=MES_ANUAL,
            table_name="sim_do_raw",
            base_dir=DATA_DIR,
            schema=SIM_DO_SCHEMA,
        )

        # ── Supabase COPY ─────────────────────────────────────────────────
        parquet_to_supabase(
            parquet_path=parquet_path,
            table_name="public.sim_do_raw",
            columns=list(SIM_DO_SCHEMA.names),
            database_url=DATABASE_URL,
        )

        elapsed = (datetime.now() - inicio).total_seconds()

        # ── SUCCESS ───────────────────────────────────────────────────────
        upsert_log(
            IngestionEntry(
                estado=estado, ano=ano, mes=MES_ANUAL, sistema=SISTEMA,
                status=IngestionStatus.SUCCESS,
                qtd_registros=qtd,
                elapsed_sec=elapsed,
            ),
            DATABASE_URL,
        )

        log.info(f"[OK] {estado}/{ano} SIM/DO — {qtd:,} registros em {elapsed:.1f}s")
        return {"estado": estado, "ano": ano, "status": "success", "qtd": qtd}

    except Exception as exc:
        elapsed = (datetime.now() - inicio).total_seconds()
        err_msg = str(exc)[:500]
        log.error(f"[ERR] {estado}/{ano} SIM/DO — {err_msg}")
        upsert_log(
            IngestionEntry(
                estado=estado, ano=ano, mes=MES_ANUAL, sistema=SISTEMA,
                status=IngestionStatus.ERROR,
                error_msg=err_msg,
                elapsed_sec=elapsed,
            ),
            DATABASE_URL,
        )
        raise


@task(
    name="gerar-resumo-sim",
    description="Consolida resultados da ingestão SIM/DO",
)
def gerar_resumo_sim(resultados: list[dict]) -> dict:
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
    log.info("RESUMO DA INGESTÃO SIM/DO (ÓBITOS)")
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
    name="ingestao-anual-sim-do",
    description=(
        "Ingestão incremental anual do SIM/DO (óbitos) — "
        "todos os 27 estados, 2020-2024"
    ),
    task_runner=ConcurrentTaskRunner(max_workers=4),
    log_prints=True,
)
def ingestao_anual_sim_do(
    estados: Optional[list[str]] = None,
    anos: Optional[list[int]] = None,
    force: bool = False,
    dry_run: bool = False,
) -> dict:
    """
    Flow de ingestão incremental do SIM/DO.

    Args:
        estados : Lista de siglas de UF. Padrão: todos os 27.
        anos    : Anos a processar. Padrão: ANO_INICIO..ANO_FIM do .env.
        force   : Re-processar mesmo que já carregado.
        dry_run : Simular sem gravar dados.

    Returns
    -------
    dict com resumo: sucesso, erros, skips, total_registros_carregados.
    """
    log = get_run_logger()

    _estados = estados or ESTADOS_DEFAULT
    _anos    = anos or list(range(ANO_INICIO, ANO_FIM + 1))

    log.info(f"🚀 Ingestão SIM/DO: {len(_estados)} estados × {len(_anos)} anos")
    log.info(f"   Estados : {_estados}")
    log.info(f"   Período : {_anos[0]}–{_anos[-1]}")

    if dry_run:
        log.info("⚠️  DRY RUN — nenhum dado será gravado")
        pendentes = verificar_pendencias_sim(_estados, _anos)
        log.info(f"   Seriam processadas: {len(pendentes)} combinações (estado × ano)")
        return {"dry_run": True, "pendentes": len(pendentes)}

    # Verificar pendências
    pendentes = verificar_pendencias_sim(_estados, _anos)

    if not pendentes:
        log.info("✅ Nenhuma combinação pendente — SIM/DO atualizado!")
        return {"status": "up_to_date", "pendentes": 0, "total_registros_carregados": 0}

    log.info(f"📋 {len(pendentes)} combinações (estado × ano) para processar")

    # Processar em paralelo (até 4 simultâneos)
    futures = [
        ingerir_ano_sim.submit(estado, ano, force)
        for estado, ano in pendentes
    ]

    resultados = [f.result(raise_on_failure=False) for f in futures]
    resumo = gerar_resumo_sim(resultados)

    return resumo


# ────────────────────────────────────────────────
# Ponto de entrada (execução direta para teste)
# ────────────────────────────────────────────────

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Ingestão incremental SIM/DO (óbitos)")
    parser.add_argument("--estados", nargs="+", default=None, help="Siglas de UF (ex: SP RJ MG)")
    parser.add_argument("--anos", nargs="+", type=int, default=None, help="Anos (ex: 2022 2023)")
    parser.add_argument("--force", action="store_true", help="Re-processar mesmo que já carregado")
    parser.add_argument("--dry-run", action="store_true", help="Simular sem gravar")
    args = parser.parse_args()

    ingestao_anual_sim_do(
        estados=args.estados,
        anos=args.anos,
        force=args.force,
        dry_run=args.dry_run,
    )
