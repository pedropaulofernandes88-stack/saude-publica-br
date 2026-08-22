"""
ingest_sih.py
Pipeline de ingestão SIH/AIH (Internações Hospitalares) do DataSUS.

Estratégia:
  PySUS.download() → DataFrame → normalizar_dataframe() → PyArrow → Parquet → Supabase COPY

Suporta:
  - Todos os 27 estados brasileiros
  - Granularidade mensal (arquivo RD por UF/ano/mês no FTP DataSUS)
  - Controle incremental via ingestion_log (skipa competências já carregadas)
  - Retry automático com exponential backoff (tenacity)
  - Logging estruturado (loguru)

Uso:
  python -m ingestion.ingest_sih --estados SP RJ MG --anos 2023 2024
  python -m ingestion.ingest_sih --all          (todos 27 estados, todos os anos)
  python -m ingestion.ingest_sih --all --dry-run
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

from ingestion.utils.bulk_load import df_to_parquet, parquet_to_supabase, SIH_AIH_SCHEMA
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
    "n_aih", "ident",
    "dt_inter", "dt_saida",
    "ano_cmpt", "mes_cmpt", "dias_perm",
    "diag_princ", "diag_secun", "diag_cap",
    "proc_rea", "proc_sol",
    "cnes", "municipio_ocor", "uf_ocor",
    "municipio_res", "uf_res",
    "sexo", "idade", "nasc", "raca_cor",
    "morte", "cobranca",
    "val_tot", "val_sh", "val_sp", "val_sadt", "val_uci",
    "gestor_cod", "instru", "car_int",
    "uf_arquivo",
]

# Mapeamento PySUS → nosso schema padronizado
# Nomes conforme documentação SIH/RD do DataSUS (layout AIH Reduzida)
MAPA_COLUNAS_PYSUS = {
    "N_AIH":      "n_aih",
    "IDENT":      "ident",
    "DT_INTER":   "dt_inter",
    "DT_SAIDA":   "dt_saida",
    "ANO_CMPT":   "ano_cmpt",
    "MES_CMPT":   "mes_cmpt",
    "DIAS_PERM":  "dias_perm",
    "DIAG_PRINC": "diag_princ",
    "DIAG_SECUN": "diag_secun",
    "PROC_REA":   "proc_rea",
    "PROC_SOL":   "proc_sol",
    "CNES":       "cnes",
    "MUNIC_MOV":  "municipio_ocor",   # município do estabelecimento
    "MUNIC_RES":  "municipio_res",    # município de residência
    "SEXO":       "sexo",
    "IDADE":      "idade",
    "NASC":       "nasc",
    "RACA_COR":   "raca_cor",
    "MORTE":      "morte",
    "COBRANCA":   "cobranca",
    "VAL_TOT":    "val_tot",
    "VAL_SH":     "val_sh",
    "VAL_SP":     "val_sp",
    "VAL_SADT":   "val_sadt",
    "VAL_UCI":    "val_uci",
    "GESTOR_COD": "gestor_cod",
    "INSTRU":     "instru",
    "CAR_INT":    "car_int",
}

# Prefixo IBGE (2 dígitos) → sigla UF
_UF_IBGE: dict[str, str] = {
    "11": "RO", "12": "AC", "13": "AM", "14": "RR", "15": "PA",
    "16": "AP", "17": "TO", "21": "MA", "22": "PI", "23": "CE",
    "24": "RN", "25": "PB", "26": "PE", "27": "AL", "28": "SE",
    "29": "BA", "31": "MG", "32": "ES", "33": "RJ", "35": "SP",
    "41": "PR", "42": "SC", "43": "RS", "50": "MS", "51": "MT",
    "52": "GO", "53": "DF",
}

# Capítulos CID-10 (primeira letra da causa)
CID10_CAPITULOS: dict[str, str] = {
    "A": "I",    "B": "I",    # Infecciosas e parasitárias
    "C": "II",   "D": "II",   # Neoplasias
    "E": "IV",               # Endócrinas e metabólicas
    "F": "V",                # Transtornos mentais
    "G": "VI",               # Sistema nervoso
    "H": "VII",              # Olhos/ouvidos
    "I": "IX",               # Doenças cardiovasculares
    "J": "X",                # Respiratórias
    "K": "XI",               # Digestivas
    "L": "XII",              # Pele
    "M": "XIII",             # Músculo-esqueléticas
    "N": "XIV",              # Gênito-urinárias
    "O": "XV",               # Gravidez/parto
    "P": "XVI",              # Perinatal
    "Q": "XVII",             # Malformações congênitas
    "R": "XVIII",            # Sintomas e sinais não classificados
    "S": "XIX",  "T": "XIX", # Lesões e causas externas
    "U": "XXII",             # COVID-19 (U07–U09)
    "V": "XX",   "W": "XX",  # Causas externas de mortalidade
    "X": "XX",   "Y": "XX",
    "Z": "XXI",              # Fatores que influenciam a saúde
}


# ---------------------------------------------------------------------------
# Helpers de transformação
# ---------------------------------------------------------------------------

def _derivar_uf(municipio_series: pd.Series) -> pd.Series:
    """
    Deriva a sigla UF a partir dos 2 primeiros dígitos do código IBGE do município.
    Retorna 'ZZ' para códigos não reconhecidos.
    """
    prefixo = municipio_series.astype(str).str[:2]
    return prefixo.map(_UF_IBGE).fillna("ZZ")


def normalizar_dataframe(df: pd.DataFrame, uf: str, ano: int, mes: int) -> pd.DataFrame:
    """
    Normaliza o DataFrame SIH/AIH bruto (PySUS) para o schema padronizado:

    1. Renomeia colunas PySUS → schema padronizado
    2. Deriva/corrige: ano_cmpt, mes_cmpt, uf_ocor, uf_res, diag_cap
    3. Tipagem segura (int, float, str)
    4. Remove registros inválidos (sem município de residência)
    5. Retorna apenas as colunas do schema Supabase
    """
    # ── 1. Rename ──────────────────────────────────────────────────────────
    rename_map = {k: v for k, v in MAPA_COLUNAS_PYSUS.items() if k in df.columns}
    df = df.rename(columns=rename_map)

    # ── 2. Campos temporais ─────────────────────────────────────────────────
    # PySUS pode entregar ANO_CMPT/MES_CMPT como string ou int; normaliza para int16
    if "ano_cmpt" in df.columns:
        df["ano_cmpt"] = pd.to_numeric(df["ano_cmpt"], errors="coerce").astype("Int16")
    else:
        df["ano_cmpt"] = ano

    if "mes_cmpt" in df.columns:
        df["mes_cmpt"] = pd.to_numeric(df["mes_cmpt"], errors="coerce").astype("Int16")
    else:
        df["mes_cmpt"] = mes

    # ── 3. Município → normaliza para 6 dígitos (código IBGE com DV) ───────
    for col in ("municipio_res", "municipio_ocor"):
        if col in df.columns:
            df[col] = df[col].astype(str).str.strip().str.zfill(6)

    # ── 4. Deriva UF a partir do município ──────────────────────────────────
    if "municipio_res" in df.columns:
        df["uf_res"] = _derivar_uf(df["municipio_res"])
    else:
        df["uf_res"] = uf.upper()

    if "municipio_ocor" in df.columns:
        df["uf_ocor"] = _derivar_uf(df["municipio_ocor"])
    else:
        df["uf_ocor"] = uf.upper()

    # ── 5. Capítulo CID-10 do diagnóstico principal ──────────────────────────
    if "diag_princ" in df.columns:
        df["diag_princ"] = df["diag_princ"].astype(str).str.strip().str.upper()
        df["diag_cap"] = df["diag_princ"].str[:1].map(CID10_CAPITULOS)
    else:
        df["diag_cap"] = None

    # ── 6. Diagnóstico secundário e procedimentos ───────────────────────────
    for col in ("diag_secun", "proc_rea", "proc_sol"):
        if col in df.columns:
            df[col] = df[col].astype(str).str.strip().str.upper()

    # ── 7. Valores financeiros → float ───────────────────────────────────────
    for col in ("val_tot", "val_sh", "val_sp", "val_sadt", "val_uci"):
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    # ── 8. Dias de permanência e idade → int ────────────────────────────────
    for col in ("dias_perm", "idade"):
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").astype("Int16")

    # ── 9. Morte → 0/1 ────────────────────────────────────────────────────
    if "morte" in df.columns:
        df["morte"] = pd.to_numeric(df["morte"], errors="coerce").fillna(0).astype("Int16")

    # ── 10. uf_arquivo ────────────────────────────────────────────────────
    df["uf_arquivo"] = uf.upper()

    # ── 11. Filtra registros sem município de residência ──────────────────
    if "municipio_res" in df.columns:
        df = df[df["municipio_res"].str.len() == 6]
        df = df[df["municipio_res"] != "000000"]

    # ── 12. Seleciona apenas colunas do schema ──────────────────────────────
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
def baixar_sih_aih(estado: str, ano: int, mes: int) -> pd.DataFrame:
    """
    Baixa dados SIH/AIH (arquivo RD) via PySUS com retry automático.

    PySUS conecta ao FTP do DataSUS, baixa o .dbc e converte para DataFrame.
    Arquivo: RD<UF><AA><MM>.dbc (ex: RDSP2401.dbc para SP, jan/2024)

    Retry: até 3 tentativas com backoff exponencial (10s, 20s, 40s).
    """
    try:
        from pysus.online_data.SIH import download
        logger.debug(f"  PySUS: baixando SIH/RD {estado} {ano}/{mes:02d}...")
        df = download(estado, ano, mes, group="RD")
        if df is None or len(df) == 0:
            logger.warning(f"  Sem dados: SIH/RD {estado} {ano}/{mes:02d}")
            return pd.DataFrame()
        logger.debug(f"  Download OK: {len(df):,} registros brutos")
        return df
    except ImportError:
        # Fallback para nova API do PySUS (v4+)
        try:
            from pysus.data.public.sih import RD
            parquet = RD().download(states=estado, years=ano, months=mes)
            return parquet.to_dataframe() if parquet else pd.DataFrame()
        except Exception as e2:
            logger.error(f"  Fallback também falhou: {e2}")
            raise


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
    Processa uma competência SIH/AIH (estado/ano/mês):

    1. Verifica se já foi carregada (ingestion_log)
    2. Download via PySUS (SIH/RD)
    3. Normaliza o DataFrame
    4. Salva como Parquet particionado (uf/ano/mes)
    5. COPY para Supabase (sih_aih_raw)
    6. Atualiza ingestion_log

    Returns:
        dict com status, qtd_registros, elapsed_sec
    """
    chave = f"SIH {estado} {ano}/{mes:02d}"
    t0 = time.perf_counter()

    # ── Verifica se já foi carregada ─────────────────────────────────────
    if not force and is_already_loaded(estado, ano, mes, "SIH_AIH", database_url):
        logger.info(f"  ⏭️  Pulando {chave} (já carregada)")
        return {"status": "skipped", "qtd": 0, "elapsed": 0.0}

    # ── Marca como RUNNING ────────────────────────────────────────────────
    entry = IngestionEntry(
        estado=estado, ano=ano, mes=mes, sistema="SIH_AIH",
        status=IngestionStatus.RUNNING,
    )
    if not dry_run:
        upsert_log(entry, database_url)

    try:
        # 1. Download
        logger.info(f"  ⬇️  Baixando {chave}...")
        df_raw = baixar_sih_aih(estado, ano, mes)

        if df_raw.empty:
            entry.status = IngestionStatus.SKIPPED
            entry.qtd_registros = 0
            entry.loaded_at = datetime.utcnow()
            entry.elapsed_sec = round(time.perf_counter() - t0, 2)
            if not dry_run:
                upsert_log(entry, database_url)
            return {"status": "skipped", "qtd": 0, "elapsed": entry.elapsed_sec}

        # 2. Normaliza
        df = normalizar_dataframe(df_raw, estado, ano, mes)
        logger.info(f"  🔄 Normalizado: {len(df):,} registros válidos")

        if dry_run:
            logger.info(f"  [DRY RUN] Pularia Parquet + Supabase COPY ({len(df):,} registros)")
            return {"status": "dry_run", "qtd": len(df), "elapsed": 0.0}

        # 3. Salva Parquet particionado
        parquet_path = df_to_parquet(
            df, estado, ano, mes,
            schema=SIH_AIH_SCHEMA,
            table_name="sih_aih",
        )

        # 4. COPY → Supabase
        if database_url:
            qtd = parquet_to_supabase(
                parquet_path,
                "public.sih_aih_raw",
                COLUNAS_SUPABASE,
                database_url,
            )
        else:
            qtd = len(df)
            logger.warning("  DATABASE_URL não configurado — apenas Parquet salvo")

        # 5. Atualiza ingestion_log como SUCCESS
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
        entry.status      = IngestionStatus.ERROR
        entry.error_msg   = str(exc)[:500]
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
    help="Processa todos os 27 estados + período completo configurado no .env.",
)
@click.option(
    "--force", is_flag=True,
    help="Reprocessa mesmo que já esteja no ingestion_log como success.",
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
    Ingere dados SIH/AIH (Autorizações de Internação Hospitalar) do DataSUS.

    \b
    Exemplos:

      # Todos os estados, 2020-2024 (conforme .env)
      python -m ingestion.ingest_sih --all

      # Apenas SP e RJ, anos 2023 e 2024
      python -m ingestion.ingest_sih -e SP -e RJ -a 2023 -a 2024

      # Janeiro 2024 de SP
      python -m ingestion.ingest_sih -e SP -a 2024 -m 1

      # Simula sem salvar
      python -m ingestion.ingest_sih --all --dry-run
    """
    logger.remove()
    logger.add(
        sys.stderr,
        level=log_level,
        colorize=True,
        format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | {message}",
    )
    logger.add(
        "data/logs/ingestao_{time:YYYY-MM-DD}.log",
        rotation="1 day",
        retention="30 days",
        level="DEBUG",
    )

    # ── Resolve parâmetros ─────────────────────────────────────────────────
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
    logger.info("saude-publica-br | Ingestão SIH/AIH")
    logger.info(f"Estados : {', '.join(estados_list)} ({len(estados_list)})")
    logger.info(f"Anos    : {anos_list}")
    logger.info(f"Meses   : {meses_list}")
    logger.info(f"Total   : {total_combos:,} competências")
    logger.info(f"Mode    : {'DRY RUN' if dry_run else 'LIVE'}")
    logger.info("=" * 60)

    # ── Setup ingestion_log ────────────────────────────────────────────────
    if not dry_run and database_url:
        ensure_table(database_url)

    # ── Descobre competências pendentes ────────────────────────────────────
    if not force and database_url:
        pendentes = get_pending_combinations(
            estados_list, anos_list, meses_list, "SIH_AIH", database_url
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

    logger.info(f"Competências pendentes: {len(pendentes):,}")

    # ── Loop principal ─────────────────────────────────────────────────────
    resultados: dict[str, int] = {
        "success": 0, "skipped": 0, "error": 0, "dry_run": 0, "total_registros": 0,
    }

    for i, (estado, ano, mes) in enumerate(pendentes, 1):
        logger.info(f"\n[{i}/{len(pendentes)}] {estado} {ano}/{mes:02d}")
        result = processar_competencia(
            estado, ano, mes,
            force=force,
            dry_run=dry_run,
            database_url=database_url,
        )
        status_key = result.get("status", "error")
        resultados[status_key] = resultados.get(status_key, 0) + 1
        resultados["total_registros"] += result.get("qtd", 0)

    # ── Resumo final ──────────────────────────────────────────────────────
    logger.info("\n" + "=" * 60)
    logger.info("RESUMO FINAL — SIH/AIH")
    logger.info(f"  ✅ Sucesso   : {resultados['success']:,}")
    logger.info(f"  ⏭️  Pulados   : {resultados['skipped']:,}")
    logger.info(f"  ❌ Erros     : {resultados['error']:,}")
    logger.info(f"  📊 Registros : {resultados['total_registros']:,}")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
