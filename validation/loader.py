"""
loader.py — Carrega DataFrames dos dbt marts diretamente do Supabase/PostgreSQL.

Usa psycopg (v3) síncrono para manter compatibilidade simples com o CLI
de validação. Lê a DATABASE_URL do ambiente (mesma variável usada pela API).

Cada função carrega uma amostra ou a tabela completa, conforme o parâmetro
`limit`. Para validações de produção, use limit=None (tabela inteira).
"""
from __future__ import annotations

import logging
import os
from typing import Optional

import pandas as pd

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Conexão
# ---------------------------------------------------------------------------

def _get_conn_str() -> str:
    url = os.environ.get("DATABASE_URL")
    if not url:
        raise EnvironmentError(
            "DATABASE_URL não configurado. "
            "Defina a variável de ambiente antes de rodar as validações."
        )
    # psycopg v3 aceita tanto postgres:// quanto postgresql://
    return url.replace("postgres://", "postgresql://", 1)


def load_mart(
    table: str,
    limit: Optional[int] = None,
    where: Optional[str] = None,
) -> pd.DataFrame:
    """
    Carrega um mart do Supabase em um DataFrame pandas.

    Parameters
    ----------
    table   : nome da tabela (ex: 'mart_producao_amb')
    limit   : máximo de linhas (None = sem limite)
    where   : cláusula WHERE sem a palavra-chave (ex: "ano = 2024")
    """
    try:
        import psycopg  # psycopg v3
    except ImportError:
        try:
            import psycopg2 as psycopg  # fallback para psycopg v2
        except ImportError as exc:
            raise ImportError(
                "psycopg (v3) ou psycopg2 (v2) é necessário para o loader. "
                "Instale com: pip install psycopg[binary] ou pip install psycopg2-binary"
            ) from exc

    parts = [f"SELECT * FROM {table}"]
    if where:
        parts.append(f"WHERE {where}")
    if limit:
        parts.append(f"LIMIT {limit}")
    query = " ".join(parts)

    conn_str = _get_conn_str()
    logger.debug("Carregando %s — query: %s", table, query)

    with psycopg.connect(conn_str) as conn:
        df = pd.read_sql(query, conn)

    logger.info("✓ %s: %d linhas carregadas", table, len(df))
    return df


# ---------------------------------------------------------------------------
# Loaders específicos (convenientes para o CLI)
# ---------------------------------------------------------------------------

def load_producao_amb(limit: Optional[int] = None) -> pd.DataFrame:
    return load_mart("mart_producao_amb", limit=limit)


def load_epi_cid10(limit: Optional[int] = None) -> pd.DataFrame:
    return load_mart("mart_epi_cid10", limit=limit)


def load_ranking_municipios(limit: Optional[int] = None) -> pd.DataFrame:
    return load_mart("mart_ranking_municipios", limit=limit)


def load_acesso_cobertura(limit: Optional[int] = None) -> pd.DataFrame:
    return load_mart("mart_acesso_cobertura", limit=limit)


def load_mix_complexidade(limit: Optional[int] = None) -> pd.DataFrame:
    return load_mart("mart_mix_complexidade", limit=limit)


def load_sazonalidade(limit: Optional[int] = None) -> pd.DataFrame:
    return load_mart("mart_sazonalidade", limit=limit)


def load_anomalias_prophet(limit: Optional[int] = None) -> pd.DataFrame:
    return load_mart("mart_anomalias_prophet", limit=limit)


def load_mortalidade(limit: Optional[int] = None) -> pd.DataFrame:
    return load_mart("marts.mart_mortalidade", limit=limit)


def load_internacoes(limit: Optional[int] = None) -> pd.DataFrame:
    return load_mart("marts.mart_internacoes", limit=limit)


# Mapa nome→loader para uso genérico no CLI
MART_LOADERS: dict[str, callable] = {
    "producao_amb": load_producao_amb,
    "epi_cid10": load_epi_cid10,
    "ranking_municipios": load_ranking_municipios,
    "acesso_cobertura": load_acesso_cobertura,
    "mix_complexidade": load_mix_complexidade,
    "sazonalidade": load_sazonalidade,
    "anomalias_prophet": load_anomalias_prophet,
    "mortalidade": load_mortalidade,
    "internacoes": load_internacoes,
}
