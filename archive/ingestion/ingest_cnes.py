"""
ingest_cnes.py
Ingestão do CNES (Cadastro Nacional de Estabelecimentos de Saúde).

Grupos suportados:
  ST — estabelecimentos (identificação, classificação, capacidade)
  LT — leitos por estabelecimento e tipo

Fonte: DataSUS via PySUS (pysus.online_data.CNES).

Uso:
    python ingest_cnes.py --grupo ST --estados SP RJ --anos 2023 --meses 1 2 3
    python ingest_cnes.py --grupo ST LT --all --anos 2022 2023
    python ingest_cnes.py --grupo LT --all --anos 2023 --dry-run
"""

from __future__ import annotations

import sys
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

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from ingestion.utils.bulk_load import (
    df_to_supabase_bulk,
    CNES_ESTAB_SCHEMA,
    CNES_LEITOS_SCHEMA,
)

# ---------------------------------------------------------------------------
# Constantes
# ---------------------------------------------------------------------------

TODOS_ESTADOS: list[str] = [
    "AC", "AL", "AP", "AM", "BA", "CE", "DF", "ES", "GO",
    "MA", "MT", "MS", "MG", "PA", "PB", "PR", "PE", "PI",
    "RJ", "RN", "RS", "RO", "RR", "SC", "SP", "SE", "TO",
]

GRUPOS_VALIDOS: dict[str, str] = {
    "ST": "estabelecimentos",
    "LT": "leitos",
}

# ---------------------------------------------------------------------------
# Mapeamento de colunas — grupo ST (estabelecimentos)
# ---------------------------------------------------------------------------

MAPA_ST: dict[str, Optional[str]] = {
    "CNES":         "cnes",
    "ANO_CMPT":     "ano_cmpt",
    "MES_CMPT":     "mes_cmpt",
    "CODUFMUN":     "municipio_cod",
    "MUNNAME":      "municipio_nome",
    "CEP":          "cep",
    "TP_UNID":      "tp_unid",
    "TPUNIDADE":    "tp_unid_desc",
    "CNPJ_MAN":     "cnpj_mantenedora",
    "PF_PJ":        "pf_pj",
    "TP_PREST":     "tp_prest",
    "ESFERA_A":     "esfera_adm",
    "RETENCAO":     "ret_obrig",
    "NAT_JUR":      "nat_jur",
    "NIVEL_DEP":    "nivel_dep",
    "TP_GESTAO":    "tp_gestao",
    "QT_LEITO_SUS": "qt_leitos_sus",
    "LEITO_NSUS":   "qt_leitos_nao_sus",
    "QT_CONSULT":   "qt_cons_sus",
    "QTAMBSUS":     "qt_amb_sus",
    "QTAMBNOT":     "qt_amb_nao_sus",
    "UTI_ADULT":    "serv_uti",
    "EMERG":        "serv_emer",
    "CIRURGIA":     "serv_cirg",
    "OBSTRECN":     "serv_obstet",
    "HEMOTERAP":    "serv_hemot",
    "ATEND_PR":     "serv_diag",
    "VINC_SUS":     "vinc_sus",
    # Colunas ignoradas
    "COMPETEN":     None,
    "REGSAUDE":     None,
    "MICR_REG":     None,
    "DISTR_SAN":    None,
    "DISTR_AD":     None,
    "TPGESTAO":     None,
    "DIRETOR_":     None,
}

COLUNAS_ST: list[str] = [
    "cnes", "ano_cmpt", "mes_cmpt", "uf",
    "municipio_cod", "municipio_nome", "cep",
    "tp_unid", "tp_unid_desc",
    "cnpj_mantenedora", "pf_pj", "tp_prest",
    "esfera_adm", "ret_obrig", "nat_jur",
    "nivel_dep", "tp_gestao",
    "qt_leitos_sus", "qt_leitos_nao_sus", "qt_amb_sus", "qt_amb_nao_sus", "qt_cons_sus",
    "serv_uti", "serv_emer", "serv_cirg", "serv_obstet", "serv_hemot", "serv_diag",
    "vinc_sus",
    "uf_arquivo",
]

# ---------------------------------------------------------------------------
# Mapeamento de colunas — grupo LT (leitos)
# ---------------------------------------------------------------------------

MAPA_LT: dict[str, Optional[str]] = {
    "CNES":         "cnes",
    "ANO_CMPT":     "ano_cmpt",
    "MES_CMPT":     "mes_cmpt",
    "CODUFMUN":     "municipio_cod",
    "TP_LEITO":     "tp_leito",
    "NMTPLEITO":    "tp_leito_desc",
    "COD_ESPEC":    "cod_espec",
    "NMESPEC":      "cod_espec_desc",
    "QT_EXIST":     "qt_exist",
    "QT_SUS":       "qt_sus",
    "QT_NSUS":      "qt_nao_sus",
    "QT_CONTR":     "qt_contr",
    # Ignoradas
    "COMPETEN":     None,
    "REGSAUDE":     None,
}

COLUNAS_LT: list[str] = [
    "cnes", "ano_cmpt", "mes_cmpt", "uf",
    "municipio_cod",
    "tp_leito", "tp_leito_desc",
    "cod_espec", "cod_espec_desc",
    "qt_exist", "qt_sus", "qt_nao_sus", "qt_contr",
    "uf_arquivo",
]


# ---------------------------------------------------------------------------
# Normalização
# ---------------------------------------------------------------------------

def _normaliza_df(
    df_raw: pd.DataFrame,
    mapa: dict[str, Optional[str]],
    colunas: list[str],
    uf: str,
    ano: int,
    mes: int,
) -> pd.DataFrame:
    """Aplica mapeamento de colunas e garante schema consistente."""
    rename_map = {k: v for k, v in mapa.items() if v is not None}
    df = df_raw.rename(columns=rename_map)

    # Remove colunas que não fazem parte do schema final
    esperadas = set(colunas)
    extras = [c for c in df.columns if c not in esperadas]
    df = df.drop(columns=extras, errors="ignore")

    # Preenche colunas obrigatórias derivadas
    df["uf"] = uf
    df["uf_arquivo"] = uf

    # Garante ano_cmpt / mes_cmpt (às vezes o PySUS os omite)
    if "ano_cmpt" not in df.columns or df["ano_cmpt"].isna().all():
        df["ano_cmpt"] = ano
    if "mes_cmpt" not in df.columns or df["mes_cmpt"].isna().all():
        df["mes_cmpt"] = mes

    # Garante que todas as colunas existam
    for col in colunas:
        if col not in df.columns:
            df[col] = pd.NA

    return df[colunas]


# ---------------------------------------------------------------------------
# Download com retry
# ---------------------------------------------------------------------------

@retry(
    retry=retry_if_exception_type(Exception),
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=2, min=4, max=30),
    reraise=True,
)
def _download_cnes(grupo: str, uf: str, ano: int, mes: int) -> Optional[pd.DataFrame]:
    """
    Baixa arquivo CNES via PySUS.

    Returns None se o arquivo não existir no FTP.
    """
    try:
        from pysus.online_data.CNES import download as cnes_download
    except ImportError as exc:
        raise ImportError("PySUS não instalado: pip install pysus") from exc

    try:
        df = cnes_download(group=grupo, uf=uf, year=ano, month=mes)
        if df is None or len(df) == 0:
            return None
        return df
    except Exception as exc:
        msg = str(exc).lower()
        if "not found" in msg or "no such file" in msg or "550" in msg:
            logger.warning(f"    Arquivo não encontrado: CNES/{grupo}/{uf}/{ano:04d}-{mes:02d}")
            return None
        raise


# ---------------------------------------------------------------------------
# Ingestão de uma combinação grupo / UF / ano / mês
# ---------------------------------------------------------------------------

def ingerir_cnes_uf_mes(
    grupo: str,
    uf: str,
    ano: int,
    mes: int,
    dry_run: bool = False,
) -> int:
    """
    Baixa e ingere um arquivo CNES para um grupo, UF e mês específicos.

    Returns:
        int: registros carregados (0 se vazio ou dry-run sem dados)
    """
    mapa = MAPA_ST if grupo == "ST" else MAPA_LT
    colunas = COLUNAS_ST if grupo == "ST" else COLUNAS_LT
    schema = CNES_ESTAB_SCHEMA if grupo == "ST" else CNES_LEITOS_SCHEMA
    table_name = "cnes_estabelecimentos" if grupo == "ST" else "cnes_leitos"

    df_raw = _download_cnes(grupo, uf, ano, mes)
    if df_raw is None:
        return 0

    df_norm = _normaliza_df(df_raw, mapa, colunas, uf=uf, ano=ano, mes=mes)
    n = len(df_norm)

    if n == 0:
        return 0

    logger.info(f"  CNES/{grupo}/{uf}/{ano:04d}-{mes:02d}: {n:,} registros")

    if dry_run:
        logger.info(f"  [DRY-RUN] Não carregando {n:,} registros")
        return n

    _, loaded = df_to_supabase_bulk(
        df=df_norm,
        uf=uf,
        ano=ano,
        mes=mes,
        table_name=table_name,
        columns=colunas,
        schema=schema,
    )
    return loaded


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

@click.command()
@click.option(
    "--grupo",
    multiple=True,
    type=click.Choice(list(GRUPOS_VALIDOS.keys()), case_sensitive=False),
    default=["ST"],
    show_default=True,
    help="Grupo(s) CNES: ST (estabelecimentos), LT (leitos). Aceita múltiplos.",
)
@click.option(
    "--anos",
    multiple=True,
    type=int,
    required=True,
    help="Ano(s) de competência (ex: 2022 2023).",
)
@click.option(
    "--meses",
    multiple=True,
    type=click.IntRange(1, 12),
    default=list(range(1, 13)),
    show_default=True,
    help="Mês(es) de competência (1-12). Padrão: todos os meses.",
)
@click.option(
    "--estados",
    multiple=True,
    type=str,
    help="Siglas de UF (ex: SP RJ MG). Se omitido, usa --all.",
)
@click.option(
    "--all",
    "todos_estados",
    is_flag=True,
    default=False,
    help="Ingerir todos os 27 estados.",
)
@click.option(
    "--dry-run",
    is_flag=True,
    default=False,
    help="Baixa e normaliza dados sem carregar no Supabase.",
)
@click.option(
    "--verbose",
    is_flag=True,
    default=False,
    help="Ativa logs de DEBUG.",
)
def main(
    grupo: tuple[str, ...],
    anos: tuple[int, ...],
    meses: tuple[int, ...],
    estados: tuple[str, ...],
    todos_estados: bool,
    dry_run: bool,
    verbose: bool,
) -> None:
    """Ingestão CNES — estabelecimentos (ST) e leitos (LT)."""
    log_level = "DEBUG" if verbose else "INFO"
    logger.remove()
    logger.add(sys.stderr, level=log_level,
               format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | {message}")

    grupos = [g.upper() for g in grupo]
    anos_list = sorted(set(anos))
    meses_list = sorted(set(meses))

    if todos_estados:
        ufs = TODOS_ESTADOS
    elif estados:
        ufs = [e.upper() for e in estados if e.upper() in TODOS_ESTADOS]
    else:
        logger.error("Informe --estados ou use --all.")
        sys.exit(1)

    logger.info(f"Grupos   : {grupos}")
    logger.info(f"Anos     : {anos_list}")
    logger.info(f"Meses    : {meses_list}")
    logger.info(f"UFs      : {len(ufs)} estado(s)")
    logger.info(f"Dry-run  : {dry_run}")

    grand_total = 0
    erros: list[str] = []
    total_combinacoes = len(grupos) * len(ufs) * len(anos_list) * len(meses_list)
    processadas = 0

    for grp in grupos:
        for ano in anos_list:
            for mes in meses_list:
                for uf in ufs:
                    processadas += 1
                    pct = 100 * processadas / total_combinacoes
                    logger.debug(f"[{pct:5.1f}%] CNES/{grp}/{uf}/{ano:04d}-{mes:02d}")
                    try:
                        n = ingerir_cnes_uf_mes(grp, uf, ano, mes, dry_run=dry_run)
                        grand_total += n
                    except Exception as exc:
                        chave = f"CNES/{grp}/{uf}/{ano:04d}-{mes:02d}"
                        logger.error(f"✗ {chave}: {exc}")
                        erros.append(f"{chave}: {exc}")

    logger.info("=" * 60)
    if dry_run:
        logger.info(f"[DRY-RUN] Total processado: {grand_total:,} registros")
    else:
        logger.info(f"✓ Total carregado: {grand_total:,} registros")

    if erros:
        logger.warning(f"Erros ({len(erros)}):")
        for e in erros:
            logger.warning(f"  • {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
