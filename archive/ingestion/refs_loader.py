"""
refs_loader.py
Carrega tabelas de referência: CID-10, SIGTAP, IBGE Municípios, IBGE Populações.

Estas tabelas são relativamente estáticas e só precisam ser carregadas uma vez
(ou atualizadas anualmente). São a base para os JOINs nos modelos dbt.
"""

from __future__ import annotations

import io
import os
import sys
import zipfile
from pathlib import Path
from typing import Optional

import click
import pandas as pd
import psycopg
import requests
from loguru import logger

sys.path.insert(0, str(Path(__file__).parent.parent))

DATABASE_URL = os.getenv("DATABASE_URL", "")
DATA_DIR = Path(os.getenv("DATA_DIR", "./data"))


# ---------------------------------------------------------------------------
# DDL — Tabelas de referência
# ---------------------------------------------------------------------------

CREATE_REFS_SQL = """
-- CID-10
CREATE TABLE IF NOT EXISTS public.ref_cid10 (
    codigo_cid       VARCHAR(4)   PRIMARY KEY,
    descricao_cid    TEXT,
    grupo_cid        VARCHAR(10),
    nome_grupo_cid   TEXT,
    capitulo_cid     VARCHAR(5),
    nome_capitulo_cid TEXT
);

-- SIGTAP
CREATE TABLE IF NOT EXISTS public.ref_sigtap (
    proc_id          VARCHAR(10)  PRIMARY KEY,
    nome_procedimento TEXT,
    complexidade     VARCHAR(2),   -- '01'=AB, '02'=MC, '03'=AC
    grupo_proc       VARCHAR(2),
    nome_grupo       TEXT,
    subgrupo_proc    VARCHAR(4),
    valor_sp         NUMERIC(10,4),
    valor_sh         NUMERIC(10,4),
    competencia_ref  VARCHAR(6)   -- competência do SIGTAP (AAAAMM)
);

-- IBGE Municípios
CREATE TABLE IF NOT EXISTS public.ref_ibge_municipios (
    municipio_cod    VARCHAR(7)   PRIMARY KEY,  -- 7 dígitos (com dígito verificador)
    municipio_cod6   VARCHAR(6),               -- 6 dígitos (usado no SIA)
    nome_municipio   TEXT,
    uf_sigla         VARCHAR(2),
    uf_nome          TEXT,
    regiao           VARCHAR(20),
    capital          BOOLEAN DEFAULT FALSE,
    latitude         NUMERIC(9,6),
    longitude        NUMERIC(9,6)
);

CREATE INDEX IF NOT EXISTS idx_mun_cod6 ON public.ref_ibge_municipios (municipio_cod6);
CREATE INDEX IF NOT EXISTS idx_mun_uf   ON public.ref_ibge_municipios (uf_sigla);

-- IBGE Populações estimadas
CREATE TABLE IF NOT EXISTS public.ref_ibge_populacao (
    municipio_cod6      VARCHAR(6),
    uf_sigla            VARCHAR(2),
    ano_referencia      SMALLINT,
    populacao_estimada  INTEGER,
    fonte               VARCHAR(20) DEFAULT 'IBGE_ESTIMATIVA',
    PRIMARY KEY (municipio_cod6, ano_referencia)
);
"""


def criar_tabelas_ref(database_url: Optional[str] = None) -> None:
    db_url = database_url or DATABASE_URL
    with psycopg.connect(db_url) as conn:
        conn.execute(CREATE_REFS_SQL)
        conn.commit()
    logger.info("Tabelas de referência criadas/verificadas")


# ---------------------------------------------------------------------------
# CID-10
# ---------------------------------------------------------------------------

def carregar_cid10(database_url: Optional[str] = None) -> int:
    """
    Carrega CID-10 via PySUS ou arquivo local.
    Retorna qtd de registros carregados.
    """
    logger.info("Carregando CID-10...")
    db_url = database_url or DATABASE_URL
    
    try:
        # Tenta via PySUS primeiro
        from pysus.data.local import SIGTAP
        df_cid = SIGTAP().load_cid10()
    except Exception:
        # Fallback: download direto do DataSUS
        url = "ftp://ftp.datasus.gov.br/dissemin/publicos/CID10/CID-10-CATEGORIAS.CSV"
        logger.info(f"  Fallback: download de {url}")
        df_cid = pd.read_csv(url, encoding="latin-1", sep=";")

    # Padroniza colunas (adaptar conforme a fonte)
    df_cid = df_cid.rename(columns=str.upper)
    
    # Schema mínimo esperado
    cols_map = {
        "CAT": "codigo_cid",
        "DESCRICAO": "descricao_cid",
    }
    df_out = df_cid.rename(columns={k: v for k, v in cols_map.items() if k in df_cid.columns})
    
    if "codigo_cid" not in df_out.columns:
        logger.error("Coluna codigo_cid não encontrada no CID-10")
        return 0

    logger.info(f"  CID-10: {len(df_out):,} códigos")

    with psycopg.connect(db_url) as conn:
        conn.execute("TRUNCATE public.ref_cid10")
        buf = io.StringIO()
        df_out.to_csv(buf, index=False, header=False, sep="\t", na_rep="\\N")
        buf.seek(0)
        cols = ", ".join(df_out.columns.tolist()[:6])  # máx 6 colunas do schema
        with conn.cursor().copy(
            f"COPY public.ref_cid10 FROM STDIN WITH (FORMAT CSV, DELIMITER '\t', NULL '\\N')"
        ) as copy:
            copy.write(buf.read())
        conn.commit()

    logger.success(f"  ✅ CID-10 carregado: {len(df_out):,} registros")
    return len(df_out)


# ---------------------------------------------------------------------------
# IBGE Municípios
# ---------------------------------------------------------------------------

def carregar_municipios(database_url: Optional[str] = None) -> int:
    """
    Carrega tabela de municípios do IBGE via API JSON.
    """
    logger.info("Carregando municípios IBGE...")
    db_url = database_url or DATABASE_URL

    url = "https://servicodados.ibge.gov.br/api/v1/localidades/municipios?orderBy=nome"
    logger.info(f"  API IBGE: {url}")
    
    resp = requests.get(url, timeout=60)
    resp.raise_for_status()
    data = resp.json()

    regioes = {
        "Norte": "Norte", "Nordeste": "Nordeste",
        "Sudeste": "Sudeste", "Sul": "Sul", "Centro-Oeste": "Centro-Oeste",
    }

    rows = []
    for m in data:
        uf = m["microrregiao"]["mesorregiao"]["UF"]
        rows.append({
            "municipio_cod":  str(m["id"]),
            "municipio_cod6": str(m["id"])[:6],
            "nome_municipio": m["nome"],
            "uf_sigla":       uf["sigla"],
            "uf_nome":        uf["nome"],
            "regiao":         uf["regiao"]["nome"],
        })

    df = pd.DataFrame(rows)
    logger.info(f"  {len(df):,} municípios")

    with psycopg.connect(db_url) as conn:
        conn.execute("TRUNCATE public.ref_ibge_municipios")
        buf = io.StringIO()
        df[["municipio_cod", "municipio_cod6", "nome_municipio",
            "uf_sigla", "uf_nome", "regiao"]].to_csv(
            buf, index=False, header=False, sep="\t", na_rep="\\N"
        )
        buf.seek(0)
        with conn.cursor().copy(
            "COPY public.ref_ibge_municipios (municipio_cod, municipio_cod6, "
            "nome_municipio, uf_sigla, uf_nome, regiao) "
            "FROM STDIN WITH (FORMAT CSV, DELIMITER '\t', NULL '\\N')"
        ) as copy:
            copy.write(buf.read())
        conn.commit()

    logger.success(f"  ✅ Municípios carregados: {len(df):,}")
    return len(df)


# ---------------------------------------------------------------------------
# IBGE Populações
# ---------------------------------------------------------------------------

def carregar_populacoes(
    anos: list[int],
    database_url: Optional[str] = None,
) -> int:
    """
    Carrega estimativas populacionais do IBGE para os anos informados.
    Usa API SIDRA do IBGE (tabela 6579 — estimativas populacionais).
    """
    logger.info(f"Carregando populações IBGE para: {anos}")
    db_url = database_url or DATABASE_URL
    total = 0

    for ano in anos:
        url = (
            f"https://servicodados.ibge.gov.br/api/v3/agregados/6579/"
            f"periodos/{ano}/variaveis/9324?localidades=N6[all]"
        )
        logger.info(f"  SIDRA {ano}...")
        try:
            resp = requests.get(url, timeout=60)
            resp.raise_for_status()
            data = resp.json()

            rows = []
            for item in data[0]["resultados"][0]["series"]:
                cod = item["localidade"]["id"]
                pop = item["serie"].get(str(ano))
                if pop and cod:
                    uf = cod[:2]
                    rows.append({
                        "municipio_cod6":     str(cod)[:6],
                        "uf_sigla":           _cod_uf_to_sigla(uf),
                        "ano_referencia":     ano,
                        "populacao_estimada": int(str(pop).replace(".", "").replace(",", "")),
                    })

            df = pd.DataFrame(rows)
            if df.empty:
                logger.warning(f"  Sem dados para {ano}")
                continue

            with psycopg.connect(db_url) as conn:
                conn.execute(
                    "DELETE FROM public.ref_ibge_populacao WHERE ano_referencia = %s", (ano,)
                )
                buf = io.StringIO()
                df.to_csv(buf, index=False, header=False, sep="\t", na_rep="\\N")
                buf.seek(0)
                with conn.cursor().copy(
                    "COPY public.ref_ibge_populacao "
                    "(municipio_cod6, uf_sigla, ano_referencia, populacao_estimada) "
                    "FROM STDIN WITH (FORMAT CSV, DELIMITER '\t', NULL '\\N')"
                ) as copy:
                    copy.write(buf.read())
                conn.commit()

            total += len(df)
            logger.success(f"  ✅ {ano}: {len(df):,} municípios")
        except Exception as exc:
            logger.error(f"  ❌ Erro {ano}: {exc}")

    return total


def _cod_uf_to_sigla(cod: str) -> str:
    """Converte código IBGE de UF para sigla."""
    mapa = {
        "11": "RO", "12": "AC", "13": "AM", "14": "RR", "15": "PA",
        "16": "AP", "17": "TO", "21": "MA", "22": "PI", "23": "CE",
        "24": "RN", "25": "PB", "26": "PE", "27": "AL", "28": "SE",
        "29": "BA", "31": "MG", "32": "ES", "33": "RJ", "35": "SP",
        "41": "PR", "42": "SC", "43": "RS", "50": "MS", "51": "MT",
        "52": "GO", "53": "DF",
    }
    return mapa.get(str(cod)[:2], "??")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

@click.command()
@click.option("--cid10",       is_flag=True, help="Carrega CID-10")
@click.option("--municipios",  is_flag=True, help="Carrega municípios IBGE")
@click.option("--populacoes",  is_flag=True, help="Carrega populações IBGE")
@click.option("--all-refs",    is_flag=True, help="Carrega todas as referências")
@click.option(
    "--anos", multiple=True, type=int,
    default=[2020, 2021, 2022, 2023, 2024],
    help="Anos para populações. Padrão: 2020-2024",
    show_default=True,
)
def main(cid10, municipios, populacoes, all_refs, anos):
    """Carrega tabelas de referência no Supabase."""
    logger.remove()
    logger.add(sys.stderr, level="INFO", colorize=True,
               format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | {message}")

    db_url = os.getenv("DATABASE_URL") or None
    if not db_url:
        logger.error("DATABASE_URL não configurado no .env")
        sys.exit(1)

    criar_tabelas_ref(db_url)

    if all_refs or cid10:
        carregar_cid10(db_url)

    if all_refs or municipios:
        carregar_municipios(db_url)

    if all_refs or populacoes:
        carregar_populacoes(list(anos), db_url)

    logger.success("Referências carregadas com sucesso!")


if __name__ == "__main__":
    main()
