"""
ingest_sia_pa.py
Pipeline de ingestão SIA/PA (Produção Ambulatorial) do DataSUS.

Estratégia:
  PySUS.fetch() → DataFrame → PyArrow → Parquet local → Supabase COPY

Suporta:
  - Todos os 27 estados brasileiros
  - Período 2020–2024 (configurável via .env)
  - Controle incremental via ingestion_log (skipa combinações já carregadas)
  - Retry automático com exponential backoff (tenacity)
  - Logging estruturado (loguru)

Uso:
  python -m ingestion.ingest_sia_pa --estados SP RJ MG --anos 2023 2024
  python -m ingestion.ingest_sia_pa --all   (todos 27 estados, todos os anos)
"""

from __future__ import annotations

import os
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

import click
import pandas as pd
from loguru import logger
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)

# Garante que o root do projeto está no PATH
sys.path.insert(0, str(Path(__file__).parent.parent))

from ingestion.utils.bulk_load import df_to_parquet, parquet_to_supabase, SIA_PA_SCHEMA
from ingestion.utils.ingestion_log import (
    IngestionEntry,
    IngestionStatus,
    ensure_table,
    get_pending_combinations,
    is_already_loaded,
    upsert_log,
)

# ---------------------------------------------------------------------------
# Constantes
# ---------------------------------------------------------------------------

TODOS_ESTADOS = [
    "AC", "AL", "AP", "AM", "BA", "CE", "DF", "ES", "GO",
    "MA", "MT", "MS", "MG", "PA", "PB", "PR", "PE", "PI",
    "RJ", "RN", "RS", "RO", "RR", "SC", "SP", "SE", "TO",
]

COLUNAS_SUPABASE = [
    "mes_competencia", "ano_competencia", "mes_num",
    "municipio_cod", "proc_id", "cid_primario",
    "qtd_aprovada", "valor_aprovado", "tipo_financiamento",
    "categoria_atendimento", "sexo", "faixa_etaria", "uf_sigla",
]

MAPA_COLUNAS_PYSUS = {
    # PySUS → nosso schema padronizado
    "PA_CMP":     "mes_competencia",
    "PA_MUNPCN":  "municipio_cod",
    "PA_PROC_ID": "proc_id",
    "PA_CIDPRI":  "cid_primario",
    "PA_QTDAPR":  "qtd_aprovada",
    "PA_VALAPR":  "valor_aprovado",
    "PA_TPFIN":   "tipo_financiamento",
    "PA_CATEND":  "categoria_atendimento",
    "PA_SEXO":    "sexo",
    "PA_IDADE":   "faixa_etaria",
}


# ---------------------------------------------------------------------------
# Helpers de transformação
# ---------------------------------------------------------------------------

def normalizar_dataframe(df: pd.DataFrame, uf: str) -> pd.DataFrame:
    """
    Renomeia colunas PySUS → schema padronizado.
    Adiciona colunas derivadas: ano_competencia, mes_num, uf_sigla.
    Filtra registros inválidos.
    """
    # Renomeia apenas as colunas que existem no DataFrame
    rename_map = {k: v for k, v in MAPA_COLUNAS_PYSUS.items() if k in df.columns}
    df = df.rename(columns=rename_map)

    # --- Derivações ---
    if "mes_competencia" in df.columns:
        # PA_CMP formato: AAAAMM ou MMAAAA — PySUS normaliza para AAAAMM
        df["mes_competencia"] = df["mes_competencia"].astype(str).str.zfill(6)
        df["ano_competencia"] = df["mes_competencia"].str[:4].astype("int16")
        df["mes_num"]         = df["mes_competencia"].str[4:6].astype("int8")

    df["uf_sigla"] = uf.upper()

    # --- Limpeza ---
    if "municipio_cod" in df.columns:
        df["municipio_cod"] = df["municipio_cod"].astype(str).str.strip().str.zfill(6)
        df = df[df["municipio_cod"].str.len() == 6]

    if "qtd_aprovada" in df.columns:
        df["qtd_aprovada"] = pd.to_numeric(df["qtd_aprovada"], errors="coerce").fillna(0)
        df = df[df["qtd_aprovada"] > 0]

    if "valor_aprovado" in df.columns:
        df["valor_aprovado"] = pd.to_numeric(df["valor_aprovado"], errors="coerce")

    # --- Garante apenas as colunas do schema ---
    colunas_existentes = [c for c in COLUNAS_SUPABASE if c in df.columns]
    return df[colunas_existentes].copy()


# ---------------------------------------------------------------------------
# Download via PySUS (com retry)
# ---------------------------------------------------------------------------

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=2, min=10, max=120),
    retry=retry_if_exception_type((ConnectionError, TimeoutError, OSError)),
    reraise=True,
)
def baixar_sia_pa(estado: str, ano: int, mes: int) -> pd.DataFrame:
    """
    Baixa dados SIA/PA via PySUS com retry automático.
    
    PySUS conecta ao FTP do DataSUS, baixa o .dbc e converte para DataFrame.
    Retry: até 3 tentativas com backoff exponencial (10s, 20s, 40s).
    """
    try:
        from pysus.online_data.SIA import download
        logger.debug(f"  PySUS: baixando SIA/PA {estado} {ano}/{mes:02d}...")
        df = download(estado, ano, mes, group="PA")
        if df is None or len(df) == 0:
            logger.warning(f"  Sem dados: SIA/PA {estado} {ano}/{mes:02d}")
            return pd.DataFrame()
        logger.debug(f"  Download OK: {len(df):,} registros brutos")
        return df
    except ImportError:
        # Fallback para API alternativa do PySUS se a sintaxe mudar
        from pysus.data.public.sia import PA
        parquet = PA().download(states=estado, years=ano, months=mes)
        return parquet.to_dataframe() if parquet else pd.DataFrame()


# ---------------------------------------------------------------------------
# Pipeline principal por (estado, ano, mês)
# ---------------------------------------------------------------------------

def processar_competencia(
    estado: str,
    ano: int,
    mes: int,
    force: bool = False,
    dry_run: bool = False,
    database_url: Optional[str] = None,
) -> dict:
    """
    Processa uma competência (estado/ano/mês) completa:
    1. Verifica se já foi carregada (ingestion_log)
    2. Download via PySUS
    3. Normaliza o DataFrame
    4. Salva como Parquet
    5. COPY para Supabase
    6. Atualiza ingestion_log
    
    Returns:
        dict com status, qtd_registros, elapsed_sec
    """
    chave = f"{estado} {ano}/{mes:02d}"
    t0 = time.perf_counter()

    # --- Verifica se já foi carregada ---
    if not force and is_already_loaded(estado, ano, mes, "SIA_PA", database_url):
        logger.info(f"  ⏭️  Pulando {chave} (já carregada)")
        return {"status": "skipped", "qtd": 0, "elapsed": 0.0}

    # --- Marca como RUNNING ---
    entry = IngestionEntry(
        estado=estado, ano=ano, mes=mes, sistema="SIA_PA",
        status=IngestionStatus.RUNNING,
    )
    if not dry_run:
        upsert_log(entry, database_url)

    try:
        # 1. Download
        logger.info(f"  ⬇️  Baixando {chave}...")
        df_raw = baixar_sia_pa(estado, ano, mes)

        if df_raw.empty:
            entry.status = IngestionStatus.SKIPPED
            entry.qtd_registros = 0
            entry.loaded_at = datetime.utcnow()
            entry.elapsed_sec = round(time.perf_counter() - t0, 2)
            if not dry_run:
                upsert_log(entry, database_url)
            return {"status": "skipped", "qtd": 0, "elapsed": entry.elapsed_sec}

        # 2. Normaliza
        df = normalizar_dataframe(df_raw, estado)
        logger.info(f"  🔄 Normalizado: {len(df):,} registros válidos")

        if dry_run:
            logger.info(f"  [DRY RUN] Pularia Parquet + Supabase COPY")
            return {"status": "dry_run", "qtd": len(df), "elapsed": 0.0}

        # 3. Salva Parquet
        parquet_path = df_to_parquet(df, estado, ano, mes, SIA_PA_SCHEMA)

        # 4. COPY → Supabase
        if database_url:
            qtd = parquet_to_supabase(
                parquet_path, "public.sia_pa_raw", COLUNAS_SUPABASE, database_url
            )
        else:
            qtd = len(df)
            logger.warning("  DATABASE_URL não configurado — apenas Parquet salvo")

        # 5. Atualiza log como SUCCESS
        elapsed = round(time.perf_counter() - t0, 2)
        entry.status        = IngestionStatus.SUCCESS
        entry.qtd_registros = qtd
        entry.loaded_at     = datetime.utcnow()
        entry.elapsed_sec   = elapsed
        upsert_log(entry, database_url)

        logger.success(f"  ✅ {chave}: {qtd:,} registros em {elapsed:.1f}s")
        return {"status": "success", "qtd": qtd, "elapsed": elapsed}

    except Exception as exc:
        elapsed = round(time.perf_counter() - t0, 2)
        entry.status    = IngestionStatus.ERROR
        entry.error_msg = str(exc)[:500]
        entry.elapsed_sec = elapsed
        if not dry_run:
            upsert_log(entry, database_url)
        logger.error(f"  ❌ {chave}: {exc}")
        return {"status": "error", "qtd": 0, "elapsed": elapsed, "error": str(exc)}


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

@click.command()
@click.option(
    "--estados", "-e", multiple=True,
    help="Siglas dos estados (ex: SP RJ MG). Padrão: todos 27.",
)
@click.option(
    "--anos", "-a", multiple=True, type=int,
    help="Anos a processar (ex: 2023 2024). Padrão: ANO_INICIO–ANO_FIM do .env.",
)
@click.option(
    "--meses", "-m", multiple=True, type=int, default=list(range(1, 13)),
    help="Meses (1-12). Padrão: todos.",
    show_default=True,
)
@click.option(
    "--all", "process_all", is_flag=True,
    help="Processa todos os 27 estados + período completo do .env.",
)
@click.option(
    "--force", is_flag=True,
    help="Reprocessa mesmo que já esteja no log como success.",
)
@click.option(
    "--dry-run", is_flag=True,
    help="Simula sem salvar nada (download + normalização, sem Parquet/Supabase).",
)
@click.option(
    "--log-level", default="INFO",
    type=click.Choice(["DEBUG", "INFO", "WARNING", "ERROR"]),
    show_default=True,
)
def main(
    estados: tuple,
    anos: tuple,
    meses: tuple,
    process_all: bool,
    force: bool,
    dry_run: bool,
    log_level: str,
) -> None:
    """
    Ingere dados SIA/PA do DataSUS para o Supabase.
    
    Exemplos:
    
      # Todos os estados, 2020-2024 (configurado no .env)
      python -m ingestion.ingest_sia_pa --all
      
      # Apenas SP e RJ, anos 2023 e 2024
      python -m ingestion.ingest_sia_pa -e SP -e RJ -a 2023 -a 2024
      
      # Simula sem salvar
      python -m ingestion.ingest_sia_pa --all --dry-run
    """
    logger.remove()
    logger.add(sys.stderr, level=log_level, colorize=True,
               format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | {message}")
    logger.add(
        "data/logs/ingestao_{time:YYYY-MM-DD}.log",
        rotation="1 day", retention="30 days", level="DEBUG",
    )

    # --- Resolve parâmetros ---
    estados_list = list(estados) if estados else TODOS_ESTADOS
    if process_all:
        estados_list = TODOS_ESTADOS

    ano_inicio = int(os.getenv("ANO_INICIO", "2020"))
    ano_fim    = int(os.getenv("ANO_FIM", "2024"))
    anos_list  = list(anos) if anos else list(range(ano_inicio, ano_fim + 1))
    meses_list = list(meses)

    database_url = os.getenv("DATABASE_URL") or None

    total_combos = len(estados_list) * len(anos_list) * len(meses_list)
    logger.info("=" * 60)
    logger.info(f"saude-publica-br | Ingestão SIA/PA")
    logger.info(f"Estados: {', '.join(estados_list)} ({len(estados_list)})")
    logger.info(f"Anos:    {anos_list}")
    logger.info(f"Meses:   {meses_list}")
    logger.info(f"Total:   {total_combos:,} competências")
    logger.info(f"Mode:    {'DRY RUN' if dry_run else 'LIVE'}")
    logger.info("=" * 60)

    # --- Setup Supabase ---
    if not dry_run and database_url:
        ensure_table(database_url)

    # --- Descobre pendentes ---
    if not force and database_url:
        pendentes = get_pending_combinations(
            estados_list, anos_list, meses_list, "SIA_PA", database_url
        )
    else:
        pendentes = [
            (e, a, m)
            for e in estados_list
            for a in anos_list
            for m in meses_list
        ]

    if not pendentes:
        logger.success("Nada a processar — todas as competências já carregadas!")
        return

    # --- Loop principal ---
    resultados = {"success": 0, "skipped": 0, "error": 0, "total_registros": 0}

    for i, (estado, ano, mes) in enumerate(pendentes, 1):
        logger.info(f"\n[{i}/{len(pendentes)}] {estado} {ano}/{mes:02d}")
        result = processar_competencia(
            estado, ano, mes, force=force, dry_run=dry_run,
            database_url=database_url,
        )
        resultados[result["status"]] = resultados.get(result["status"], 0) + 1
        resultados["total_registros"] += result.get("qtd", 0)

    # --- Resumo ---
    logger.info("\n" + "=" * 60)
    logger.info("RESUMO FINAL")
    logger.info(f"  ✅ Sucesso:    {resultados['success']:,}")
    logger.info(f"  ⏭️  Pulados:    {resultados['skipped']:,}")
    logger.info(f"  ❌ Erros:      {resultados['error']:,}")
    logger.info(f"  📊 Registros:  {resultados['total_registros']:,}")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
