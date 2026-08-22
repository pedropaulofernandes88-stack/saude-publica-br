"""
ingest_sim.py
Pipeline de ingestão SIM/DO (Declarações de Óbito) do DataSUS.

Estratégia:
  PySUS.fetch() → DataFrame → PyArrow → Parquet local → Supabase COPY

Suporta:
  - Todos os 27 estados brasileiros
  - Período 2020–2024 (configurável via .env)
  - Controle incremental via ingestion_log (skipa combinações já carregadas)
  - Retry automático com exponential backoff (tenacity)
  - Logging estruturado (loguru)

Uso:
  python -m ingestion.ingest_sim --estados SP RJ MG --anos 2023 2024
  python -m ingestion.ingest_sim --all   (todos 27 estados, todos os anos)

Nota sobre granularidade temporal do SIM:
  O SIM/DO é disponibilizado com granularidade anual (não mensal) no FTP
  do DataSUS. Portanto o loop externo é por estado × ano (sem mês).
  O campo mes_obito é extraído do DTOBITO para granularidade mensal no dbt.
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

sys.path.insert(0, str(Path(__file__).parent.parent))

from ingestion.utils.bulk_load import df_to_parquet, parquet_to_supabase, SIM_DO_SCHEMA
from ingestion.utils.ingestion_log import (
    IngestionEntry,
    IngestionStatus,
    ensure_table,
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

# Colunas que serão gravadas no Supabase (ordem deve coincidir com schema)
COLUNAS_SUPABASE = [
    "numerodo", "tipobito",
    "dtobito", "ano_obito", "mes_obito",
    "causabas", "causabas_cap",
    "municipio_ocor", "uf_ocor",
    "municipio_res", "uf_res",
    "sexo", "idade_valor", "idade_unidade",
    "racacor", "escolaridade", "estadociv",
    "lococor", "assistmed",
    "uf_arquivo",
]

# Mapeamento PySUS → nosso schema
# Fonte: dicionário de variáveis SIM/DO do DataSUS
MAPA_COLUNAS_PYSUS = {
    "NUMERODO":   "numerodo",
    "TIPOBITO":   "tipobito",
    "DTOBITO":    "dtobito",
    "CAUSABAS":   "causabas",
    "CODMUNOCOR": "municipio_ocor",
    "CODMUNRES":  "municipio_res",
    "SEXO":       "sexo",
    "IDADE":      "idade_raw",      # campo complexo — processado em normalizar_dataframe
    "RACACOR":    "racacor",
    "ESC":        "escolaridade",
    "ESTCIV":     "estadociv",
    "LOCOCOR":    "lococor",
    "ASSISTMED":  "assistmed",
}

# Capítulos do CID-10 (letra inicial do código)
CID10_CAPITULOS = {
    "A": "I", "B": "I",      # I — Infecciosas e parasitárias
    "C": "II", "D": "II",    # II — Neoplasias
    "E": "IV",               # IV — Endócrinas/nutricionais/metabólicas
    "F": "V",                # V — Transtornos mentais
    "G": "VI",               # VI — Nervoso
    "H": "VII",              # VII — Olho/ouvido
    "I": "IX",               # IX — Cardiovasculares
    "J": "X",                # X — Respiratórias
    "K": "XI",               # XI — Digestivo
    "L": "XII",              # XII — Pele
    "M": "XIII",             # XIII — Musculoesquelético
    "N": "XIV",              # XIV — Geniturinário
    "O": "XV",               # XV — Gravidez/parto
    "P": "XVI",              # XVI — Perinatal
    "Q": "XVII",             # XVII — Malformações congênitas
    "R": "XVIII",            # XVIII — Sintomas não classificados
    "S": "XIX", "T": "XIX",  # XIX — Lesões/envenenamentos
    "V": "XX", "W": "XX", "X": "XX", "Y": "XX",  # XX — Causas externas
    "Z": "XXI",              # XXI — Contato com serviços de saúde
}


# ---------------------------------------------------------------------------
# Helpers de transformação
# ---------------------------------------------------------------------------

def _parse_idade(idade_raw: pd.Series) -> tuple[pd.Series, pd.Series]:
    """
    Decodifica o campo IDADE do SIM/DO.

    Formato: UAAA  onde U=unidade, AAA=valor
      U=1 → horas   (AAA = horas de vida,  0-23)
      U=2 → dias    (AAA = dias de vida,   1-29)
      U=3 → meses   (AAA = meses de vida,  1-11)
      U=4 → anos <1 (AAA = meses, usado para < 1 ano — sinônimo de U=3)
      U=5 → anos    (AAA = anos de vida,   1-130)
      000 → sem informação

    Returns:
        tuple[pd.Series, pd.Series]: (idade_valor, idade_unidade)
    """
    idade_str = idade_raw.astype(str).str.zfill(4)
    unidade_cod = idade_str.str[0]
    valor_str = idade_str.str[1:]

    valor = pd.to_numeric(valor_str, errors="coerce").astype("Int16")

    mapa_unidade = {"1": "H", "2": "D", "3": "M", "4": "M", "5": "A"}
    unidade = unidade_cod.map(mapa_unidade).fillna(pd.NA).astype("string")

    # Zera registros sem informação
    sem_info = idade_str == "0000"
    valor[sem_info] = pd.NA
    unidade[sem_info] = pd.NA

    return valor, unidade


def normalizar_dataframe(df: pd.DataFrame, uf: str, ano: int) -> pd.DataFrame:
    """
    Renomeia colunas PySUS → schema padronizado.
    Extrai ano/mes do DTOBITO, decodifica IDADE, infere capítulo CID-10.
    Filtra registros inválidos.
    """
    # Normaliza nomes de coluna para maiúsculas (PySUS pode variar)
    df.columns = [c.upper().strip() for c in df.columns]

    # Renomeia apenas as colunas existentes
    rename_map = {k: v for k, v in MAPA_COLUNAS_PYSUS.items() if k in df.columns}
    df = df.rename(columns=rename_map)

    # --- Derivações temporais ---
    if "dtobito" in df.columns:
        dtobito = df["dtobito"].astype(str).str.zfill(8)
        # DDMMAAAA → extrai ano e mês
        df["ano_obito"] = pd.to_numeric(dtobito.str[4:8], errors="coerce").astype("Int16")
        df["mes_obito"] = pd.to_numeric(dtobito.str[2:4], errors="coerce").astype("Int16")
    else:
        df["ano_obito"] = ano
        df["mes_obito"] = pd.NA

    # Fallback: ano do arquivo quando dtobito é inválido
    df["ano_obito"] = df["ano_obito"].fillna(ano).astype("int16")

    # --- Decodifica IDADE ---
    if "idade_raw" in df.columns:
        df["idade_valor"], df["idade_unidade"] = _parse_idade(df["idade_raw"])
        df.drop(columns=["idade_raw"], inplace=True)
    else:
        df["idade_valor"] = pd.NA
        df["idade_unidade"] = pd.NA

    # --- UF de ocorrência e residência (derivadas do código IBGE) ---
    # O código IBGE tem 6 dígitos: primeiros 2 = código da UF
    _UF_IBGE = {
        "11": "RO", "12": "AC", "13": "AM", "14": "RR", "15": "PA",
        "16": "AP", "17": "TO", "21": "MA", "22": "PI", "23": "CE",
        "24": "RN", "25": "PB", "26": "PE", "27": "AL", "28": "SE",
        "29": "BA", "31": "MG", "32": "ES", "33": "RJ", "35": "SP",
        "41": "PR", "42": "SC", "43": "RS", "50": "MS", "51": "MT",
        "52": "GO", "53": "DF",
    }
    if "municipio_res" in df.columns:
        df["municipio_res"] = df["municipio_res"].astype(str).str.strip().str.zfill(6)
        df["uf_res"] = df["municipio_res"].str[:2].map(_UF_IBGE)
        df = df[df["municipio_res"].str.len() == 6]
    else:
        df["uf_res"] = pd.NA

    if "municipio_ocor" in df.columns:
        df["municipio_ocor"] = df["municipio_ocor"].astype(str).str.strip().str.zfill(6)
        df["uf_ocor"] = df["municipio_ocor"].str[:2].map(_UF_IBGE)
    else:
        df["uf_ocor"] = pd.NA

    # --- Capítulo CID-10 da causa básica ---
    if "causabas" in df.columns:
        df["causabas"] = df["causabas"].astype(str).str.strip().str.upper()
        df["causabas_cap"] = df["causabas"].str[0].map(CID10_CAPITULOS)
    else:
        df["causabas_cap"] = pd.NA

    # --- Metadados ---
    df["uf_arquivo"] = uf.upper()

    # --- Filtra registros com ano_obito inválido ---
    df = df[df["ano_obito"].between(2000, 2030)]

    # --- Filtra mes_obito (alguns óbitos têm data faltante — ficam com mes=NA) ---
    df["mes_obito"] = df["mes_obito"].where(
        df["mes_obito"].between(1, 12), other=pd.NA
    )

    # --- Garante apenas colunas do schema ---
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
def baixar_sim_do(estado: str, ano: int) -> pd.DataFrame:
    """
    Baixa dados SIM/DO via PySUS com retry automático.

    PySUS conecta ao FTP do DataSUS, baixa o .dbc e converte para DataFrame.
    O SIM é disponibilizado com granularidade anual (não mensal).
    Retry: até 3 tentativas com backoff exponencial (10s, 20s, 40s).
    """
    try:
        from pysus.online_data.SIM import download
        logger.debug(f"  PySUS: baixando SIM/DO {estado} {ano}...")
        df = download(estado, ano, group="DO")
        if df is None or len(df) == 0:
            logger.warning(f"  Sem dados: SIM/DO {estado} {ano}")
            return pd.DataFrame()
        logger.debug(f"  Download OK: {len(df):,} registros brutos")
        return df
    except ImportError:
        # Fallback para API v2 do PySUS
        from pysus.data.public.sim import DO
        parquet = DO().download(states=estado, years=ano)
        return parquet.to_dataframe() if parquet else pd.DataFrame()


# ---------------------------------------------------------------------------
# Pipeline principal por (estado, ano)
# ---------------------------------------------------------------------------

def processar_ano(
    estado: str,
    ano: int,
    force: bool = False,
    dry_run: bool = False,
    database_url: Optional[str] = None,
) -> dict:
    """
    Processa um ano completo de SIM/DO para um estado.

    1. Verifica se já foi carregado (ingestion_log)
    2. Download via PySUS
    3. Normaliza o DataFrame
    4. Salva como Parquet (particionado por UF/ano)
    5. COPY para Supabase
    6. Atualiza ingestion_log

    O SIM não tem granularidade mensal no FTP — usamos mes=0 como sentinel
    para indicar "arquivo anual completo" no ingestion_log.
    """
    chave = f"{estado} {ano}"
    t0 = time.perf_counter()
    MES_ANUAL = 0  # sentinel para arquivo anual no ingestion_log

    # --- Verifica se já foi carregada ---
    if not force and is_already_loaded(estado, ano, MES_ANUAL, "SIM_DO", database_url):
        logger.info(f"  ⏭️  Pulando {chave} (já carregada)")
        return {"status": "skipped", "qtd": 0, "elapsed": 0.0}

    entry = IngestionEntry(
        estado=estado, ano=ano, mes=MES_ANUAL, sistema="SIM_DO",
        status=IngestionStatus.RUNNING,
    )
    if not dry_run:
        upsert_log(entry, database_url)

    try:
        # 1. Download
        logger.info(f"  ⬇️  Baixando SIM/DO {chave}...")
        df_raw = baixar_sim_do(estado, ano)

        if df_raw.empty:
            entry.status = IngestionStatus.SKIPPED
            entry.qtd_registros = 0
            entry.loaded_at = datetime.utcnow()
            entry.elapsed_sec = round(time.perf_counter() - t0, 2)
            if not dry_run:
                upsert_log(entry, database_url)
            return {"status": "skipped", "qtd": 0, "elapsed": entry.elapsed_sec}

        # 2. Normaliza
        df = normalizar_dataframe(df_raw, estado, ano)
        logger.info(f"  🔄 Normalizado: {len(df):,} registros válidos")

        if dry_run:
            logger.info(f"  [DRY RUN] Pularia Parquet + Supabase COPY")
            return {"status": "dry_run", "qtd": len(df), "elapsed": 0.0}

        # 3. Salva Parquet (mes=1 como placeholder — dado é anual)
        parquet_path = df_to_parquet(
            df, estado, ano, mes=1,
            schema=SIM_DO_SCHEMA,
            table_name="sim_do",
        )

        # 4. COPY → Supabase
        if database_url:
            qtd = parquet_to_supabase(
                parquet_path, "public.sim_do_raw", COLUNAS_SUPABASE, database_url
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
    process_all: bool,
    force: bool,
    dry_run: bool,
    log_level: str,
) -> None:
    """
    Ingere dados SIM/DO (óbitos) do DataSUS para o Supabase.

    Exemplos:

      # Todos os estados, 2020-2024 (configurado no .env)
      python -m ingestion.ingest_sim --all

      # Apenas SP e RJ, anos 2022 e 2023
      python -m ingestion.ingest_sim -e SP -e RJ -a 2022 -a 2023

      # Simula sem salvar
      python -m ingestion.ingest_sim --all --dry-run
    """
    logger.remove()
    logger.add(sys.stderr, level=log_level, colorize=True,
               format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | {message}")
    logger.add(
        "data/logs/ingestao_sim_{time:YYYY-MM-DD}.log",
        rotation="1 day", retention="30 days", level="DEBUG",
    )

    estados_list = list(estados) if estados else TODOS_ESTADOS
    if process_all:
        estados_list = TODOS_ESTADOS

    ano_inicio = int(os.getenv("ANO_INICIO", "2020"))
    ano_fim    = int(os.getenv("ANO_FIM",    "2024"))
    anos_list  = list(anos) if anos else list(range(ano_inicio, ano_fim + 1))

    database_url = os.getenv("DATABASE_URL") or None

    total_combos = len(estados_list) * len(anos_list)
    logger.info("=" * 60)
    logger.info("saude-publica-br | Ingestão SIM/DO (Óbitos)")
    logger.info(f"Estados: {', '.join(estados_list)} ({len(estados_list)})")
    logger.info(f"Anos:    {anos_list}")
    logger.info(f"Total:   {total_combos:,} combinações estado×ano")
    logger.info(f"Mode:    {'DRY RUN' if dry_run else 'LIVE'}")
    logger.info("=" * 60)

    if not dry_run and database_url:
        ensure_table(database_url)

    resultados: dict[str, int] = {"success": 0, "skipped": 0, "error": 0, "total_registros": 0}
    pendentes = [
        (e, a)
        for e in estados_list
        for a in anos_list
    ]

    for i, (estado, ano) in enumerate(pendentes, 1):
        logger.info(f"\n[{i}/{len(pendentes)}] {estado} {ano}")
        result = processar_ano(
            estado, ano, force=force, dry_run=dry_run,
            database_url=database_url,
        )
        resultados[result["status"]] = resultados.get(result["status"], 0) + 1
        resultados["total_registros"] += result.get("qtd", 0)

    logger.info("\n" + "=" * 60)
    logger.info("RESUMO FINAL — SIM/DO")
    logger.info(f"  ✅ Sucesso:    {resultados['success']:,}")
    logger.info(f"  ⏭️  Pulados:    {resultados['skipped']:,}")
    logger.info(f"  ❌ Erros:      {resultados['error']:,}")
    logger.info(f"  📊 Registros:  {resultados['total_registros']:,}")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
