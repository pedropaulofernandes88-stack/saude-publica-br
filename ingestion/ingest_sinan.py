"""
ingest_sinan.py
Ingestão de notificações SINAN (Sistema de Informação de Agravos de Notificação).

Agravos suportados:
  DENG — dengue
  CHIK — chikungunya
  ZIKA — zika vírus

Fonte: DataSUS via PySUS (pysus.online_data.SINAN).

Uso:
    python ingest_sinan.py --agravo DENG --anos 2022 2023 --estados SP RJ MG
    python ingest_sinan.py --agravo DENG CHIK ZIKA --all --anos 2023
    python ingest_sinan.py --agravo DENG --all --anos 2022 2023 2024 --dry-run
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

# Adiciona raiz do projeto ao path para imports relativos
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from ingestion.utils.bulk_load import (
    df_to_supabase_bulk,
    SINAN_SCHEMA,
)

# ---------------------------------------------------------------------------
# Constantes
# ---------------------------------------------------------------------------

TODOS_ESTADOS: list[str] = [
    "AC", "AL", "AP", "AM", "BA", "CE", "DF", "ES", "GO",
    "MA", "MT", "MS", "MG", "PA", "PB", "PR", "PE", "PI",
    "RJ", "RN", "RS", "RO", "RR", "SC", "SP", "SE", "TO",
]

AGRAVOS_VALIDOS: dict[str, str] = {
    "DENG": "dengue",
    "CHIK": "chikungunya",
    "ZIKA": "zika",
}

# Colunas que a tabela Supabase espera (mesma ordem do schema)
COLUNAS_SUPABASE: list[str] = [
    "nu_notific", "agravo", "dt_notific", "ano_notif", "mes_notif",
    "uf_notif", "municipio_notif", "cnes_unidade",
    "uf_res", "municipio_res",
    "dt_sin_pri", "dt_nasc", "nu_idade_n", "idade_anos",
    "cs_sexo", "cs_raca", "cs_gestant",
    "classi_fin", "criterio", "evolucao", "dt_obito", "dt_encerra",
    "febre", "mialgia", "cefaleia", "exantema", "vomito", "artralgia", "artrite",
    "sorotipo", "resul_ns1", "resul_prnt", "resul_soro", "resul_pcr",
    "dt_soro", "dt_pcr",
    "uf_arquivo",
]

# Mapeamento: coluna PySUS → coluna Supabase
# PySUS retorna nomes em maiúsculas; mapeamos para snake_case da nossa tabela.
MAPA_COLUNAS_PYSUS: dict[str, str] = {
    "NU_NOTIFIC":       "nu_notific",
    "DT_NOTIFIC":       "dt_notific",
    "SEM_NOT":          None,           # ignorar — semana epidemiológica
    "NU_ANO":           None,           # derivado de dt_notific
    "SG_UF_NOT":        "uf_notif",
    "ID_MUNICIP":       "municipio_notif",
    "ID_UNIDADE":       "cnes_unidade",
    "SG_UF":            "uf_res",
    "ID_MN_RESI":       "municipio_res",
    "DT_SIN_PRI":       "dt_sin_pri",
    "DT_NASC":          "dt_nasc",
    "NU_IDADE_N":       "nu_idade_n",
    "CS_SEXO":          "cs_sexo",
    "CS_GESTANT":       "cs_gestant",
    "CS_RACA":          "cs_raca",
    "CLASSI_FIN":       "classi_fin",
    "CRITERIO":         "criterio",
    "EVOLUCAO":         "evolucao",
    "DT_OBITO":         "dt_obito",
    "DT_ENCERRA":       "dt_encerra",
    "FEBRE":            "febre",
    "MIALGIA":          "mialgia",
    "CEFALEIA":         "cefaleia",
    "EXANTEMA":         "exantema",
    "VOMITO":           "vomito",
    "ARTRALGIA":        "artralgia",
    "ARTRITE":          "artrite",
    # Dengue específicos
    "SOROTIPO":         "sorotipo",
    "RESUL_NS1":        "resul_ns1",
    "RESUL_PRNT":       "resul_prnt",
    "RESUL_SORO":       "resul_soro",
    "RESUL_PCR":        "resul_pcr",
    "DT_SORO":          "dt_soro",
    "DT_PCR":           "dt_pcr",
}


# ---------------------------------------------------------------------------
# Funções auxiliares
# ---------------------------------------------------------------------------

def _decode_idade(nu_idade_n: pd.Series) -> pd.Series:
    """
    Converte a codificação DataSUS de idade para anos.

    Formato: centena indica unidade → 1=dias, 2=meses, 3=anos.
    Ex: 320 → 20 anos | 215 → 15 meses → 1 ano | 105 → 5 dias → 0 anos.
    """
    s = pd.to_numeric(nu_idade_n, errors="coerce").fillna(0).astype(int)
    unidade = (s // 100).astype(int)
    valor = (s % 100).astype(int)
    idade_anos = pd.Series(0, index=s.index, dtype="Int16")
    # unidade == 3 → anos direto
    mask_anos = unidade == 3
    idade_anos[mask_anos] = valor[mask_anos]
    # unidade == 2 → meses → divide por 12
    mask_meses = unidade == 2
    idade_anos[mask_meses] = (valor[mask_meses] // 12).astype("Int16")
    # unidade == 1 → dias → 0 anos
    return idade_anos


def _normaliza_df(df_raw: pd.DataFrame, agravo: str, uf: str) -> pd.DataFrame:
    """
    Aplica mapeamento de colunas, adiciona colunas derivadas e garante
    que todas as colunas esperadas existam (preenchendo com None se ausentes).
    """
    # Renomeia colunas mapeadas; descarta as marcadas None
    rename_map = {k: v for k, v in MAPA_COLUNAS_PYSUS.items() if v is not None}
    df = df_raw.rename(columns=rename_map)

    # Remove colunas não mapeadas (PySUS às vezes retorna extras)
    colunas_extra = [c for c in df.columns if c not in COLUNAS_SUPABASE
                     and c not in {"agravo", "ano_notif", "mes_notif", "idade_anos", "uf_arquivo"}]
    df = df.drop(columns=colunas_extra, errors="ignore")

    # Colunas derivadas
    df["agravo"] = agravo

    if "dt_notific" in df.columns:
        dt = pd.to_datetime(df["dt_notific"], format="%Y%m%d", errors="coerce")
        df["ano_notif"] = dt.dt.year.astype("Int16")
        df["mes_notif"] = dt.dt.month.astype("Int16")
    else:
        df["ano_notif"] = pd.NA
        df["mes_notif"] = pd.NA

    if "nu_idade_n" in df.columns:
        df["idade_anos"] = _decode_idade(df["nu_idade_n"])
    else:
        df["idade_anos"] = pd.NA

    df["uf_arquivo"] = uf

    # Garante que todas as colunas existam (evita KeyError no COPY)
    for col in COLUNAS_SUPABASE:
        if col not in df.columns:
            df[col] = pd.NA

    return df[COLUNAS_SUPABASE]


@retry(
    retry=retry_if_exception_type(Exception),
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=2, min=4, max=30),
    reraise=True,
)
def _download_sinan(agravo: str, ano: int) -> Optional[pd.DataFrame]:
    """
    Baixa dados SINAN via PySUS com retentativas automáticas.

    Returns None se o arquivo não existir no FTP (ex: ano futuro).
    """
    try:
        from pysus.online_data.SINAN import download as sinan_download
    except ImportError as exc:
        raise ImportError("PySUS não instalado: pip install pysus") from exc

    try:
        df = sinan_download(disease=agravo, year=ano)
        if df is None or len(df) == 0:
            return None
        return df
    except Exception as exc:
        msg = str(exc).lower()
        if "not found" in msg or "no such file" in msg or "550" in msg:
            logger.warning(f"    Arquivo não encontrado no FTP: {agravo}/{ano}")
            return None
        raise


# ---------------------------------------------------------------------------
# Ingestão por agravo / ano
# ---------------------------------------------------------------------------

def ingerir_agravo_ano(
    agravo: str,
    ano: int,
    dry_run: bool = False,
) -> int:
    """
    Baixa e ingere um agravo para um ano completo (todos os estados agregados
    pelo PySUS — SINAN distribui por ano, não por UF).

    Returns:
        int: total de registros carregados (0 em dry-run ou se vazio)
    """
    logger.info(f"⬇  {AGRAVOS_VALIDOS[agravo].upper()} {ano} — baixando do DataSUS...")

    df_raw = _download_sinan(agravo, ano)

    if df_raw is None:
        logger.warning(f"  Sem dados para {agravo}/{ano} — pulando.")
        return 0

    logger.info(f"  Recebido: {len(df_raw):,} notificações brutas")

    # Normaliza por UF de notificação (para particionar corretamente)
    col_uf = None
    for candidato in ("SG_UF_NOT", "uf_notif"):
        if candidato in df_raw.columns:
            col_uf = candidato
            break

    if col_uf is None:
        logger.error(f"  Coluna UF não encontrada em {agravo}/{ano} — abortando.")
        return 0

    total_carregado = 0

    # Itera por UF para usar o particionamento LIST da tabela
    for uf in sorted(df_raw[col_uf].dropna().unique()):
        uf_str = str(uf).strip().upper()
        if uf_str not in TODOS_ESTADOS:
            continue

        df_uf = df_raw[df_raw[col_uf] == uf].copy()
        if df_uf.empty:
            continue

        df_norm = _normaliza_df(df_uf, agravo=agravo, uf=uf_str)
        n_linhas = len(df_norm)
        logger.info(f"  UF={uf_str}: {n_linhas:,} notificações")

        if dry_run:
            logger.info(f"  [DRY-RUN] Pulando carga de {n_linhas:,} registros")
            total_carregado += n_linhas
            continue

        # mes=1 como placeholder — SINAN por ano não tem partição mensal
        _, loaded = df_to_supabase_bulk(
            df=df_norm,
            uf=uf_str,
            ano=ano,
            mes=1,
            table_name="sinan_notificacoes",
            columns=COLUNAS_SUPABASE,
            schema=SINAN_SCHEMA,
        )
        total_carregado += loaded

    return total_carregado


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

@click.command()
@click.option(
    "--agravo",
    multiple=True,
    type=click.Choice(list(AGRAVOS_VALIDOS.keys()), case_sensitive=False),
    default=["DENG"],
    show_default=True,
    help="Código(s) do agravo: DENG, CHIK, ZIKA (aceita múltiplos).",
)
@click.option(
    "--anos",
    multiple=True,
    type=int,
    required=True,
    help="Ano(s) de competência (ex: 2022 2023 2024).",
)
@click.option(
    "--estados",
    multiple=True,
    type=str,
    help="Siglas de UF para filtrar (ex: SP RJ MG). "
         "Ignorado pois SINAN agrega por ano; mantido para consistência de CLI.",
)
@click.option(
    "--all",
    "todos_estados",
    is_flag=True,
    default=False,
    help="Ingerir todos os estados (padrão para SINAN, que agrega por ano).",
)
@click.option(
    "--dry-run",
    is_flag=True,
    default=False,
    help="Processa e normaliza os dados mas não carrega no Supabase.",
)
@click.option(
    "--verbose",
    is_flag=True,
    default=False,
    help="Ativa logs de DEBUG.",
)
def main(
    agravo: tuple[str, ...],
    anos: tuple[int, ...],
    estados: tuple[str, ...],
    todos_estados: bool,
    dry_run: bool,
    verbose: bool,
) -> None:
    """Ingestão SINAN — dengue, chikungunya, zika."""
    # Configura logger
    log_level = "DEBUG" if verbose else "INFO"
    logger.remove()
    logger.add(sys.stderr, level=log_level,
               format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | {message}")

    agravos = [a.upper() for a in agravo]
    anos_list = sorted(set(anos))

    logger.info(f"Agravos  : {agravos}")
    logger.info(f"Anos     : {anos_list}")
    logger.info(f"Dry-run  : {dry_run}")

    grand_total = 0
    erros: list[str] = []

    for agr in agravos:
        for ano in anos_list:
            try:
                n = ingerir_agravo_ano(agr, ano, dry_run=dry_run)
                grand_total += n
            except Exception as exc:
                logger.error(f"✗ {agr}/{ano}: {exc}")
                erros.append(f"{agr}/{ano}: {exc}")

    # Resumo final
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
