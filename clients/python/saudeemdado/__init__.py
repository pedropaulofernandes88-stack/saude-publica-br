"""
saudeemdado — cliente Python da API pública do Saúde em Dado
=============================================================

Mortalidade no Brasil (SIM/DataSUS, 2015–2024): 14,4 milhões de óbitos em
indicadores agregados, com taxas padronizadas por idade, IC95% e excesso de
mortalidade. Sem cadastro; a chave embutida é pública e somente leitura.

Uso básico::

    import saudeemdado as sd

    # Série mensal de óbitos no Brasil
    serie = sd.serie_mensal()                      # lista de dicts
    df = sd.serie_mensal(as_df=True)               # pandas (pip install saudeemdado[pandas])

    # Municípios de MG em 2023, ordenados pela taxa padronizada
    mg = sd.municipios(uf="MG", ano=2023, pop_min=50_000, as_df=True)

    # Principais causas (CID-10) em SP, 2024
    causas = sd.causas(uf="SP", ano=2024, top=20)

    # Excesso de mortalidade no Brasil
    exc = sd.excesso(as_df=True)

Fontes: SIM/DataSUS (MS) e IBGE — cite-as em trabalhos acadêmicos.
Metodologia completa: https://saudeemdado.com/metodologia/
"""
from __future__ import annotations

from typing import Any, Optional

import requests

__version__ = "2.0.0"

BASE_URL = "https://zekjhmxjamatlxpkykde.supabase.co/rest/v1"
ANON_KEY = (
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9."
    "eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Inpla2pobXhqYW1hdGx4cGt5a2RlIiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODEwNzY4MzIsImV4cCI6MjA5NjY1MjgzMn0."
    "px8FcU0QK8w9v95kwGlGzASKpY3drsxAvFe0e6wUoCU"
)
_PAGE = 1000

Rows = list[dict[str, Any]]


def _get(table: str, params: dict[str, str], max_rows: int = 200_000) -> Rows:
    """GET paginado no PostgREST (ordem determinística obrigatória)."""
    headers = {"apikey": ANON_KEY, "Authorization": f"Bearer {ANON_KEY}"}
    rows: Rows = []
    offset = 0
    while len(rows) < max_rows:
        h = {**headers, "Range-Unit": "items", "Range": f"{offset}-{offset + _PAGE - 1}"}
        r = requests.get(f"{BASE_URL}/{table}", params=params, headers=h, timeout=120)
        r.raise_for_status()
        chunk = r.json()
        rows.extend(chunk)
        if len(chunk) < _PAGE:
            break
        offset += _PAGE
    return rows


def _maybe_df(rows: Rows, as_df: bool):
    if not as_df:
        return rows
    try:
        import pandas as pd
    except ImportError as exc:  # pragma: no cover
        raise ImportError("instale com: pip install saudeemdado[pandas]") from exc
    return pd.DataFrame(rows)


def serie_mensal(
    uf: Optional[str] = None,
    capitulo: str = "TOTAL",
    sexo: str = "TOTAL",
    faixa_etaria: str = "TOTAL",
    as_df: bool = False,
):
    """Série mensal de óbitos (2015–2024) por UF (None = todas as UFs)."""
    params = {
        "select": "uf_sigla,ano,mes,mes_competencia,obitos",
        "capitulo_cid": f"eq.{capitulo}",
        "sexo": f"eq.{sexo}",
        "faixa_etaria": f"eq.{faixa_etaria}",
        "order": "mes_competencia,uf_sigla",
    }
    if uf:
        params["uf_sigla"] = f"eq.{uf.upper()}"
    return _maybe_df(_get("mart_mortalidade_uf_mes", params), as_df)


def municipios(
    uf: Optional[str] = None,
    ano: int = 2023,
    capitulo: str = "TOTAL",
    sexo: str = "TOTAL",
    pop_min: int = 0,
    as_df: bool = False,
):
    """Óbitos, taxa bruta (IC95%) e taxa padronizada por município."""
    params = {
        "select": (
            "municipio_cod,municipio_nome,uf_sigla,regiao,ano,obitos,"
            "obitos_hospital,obitos_domicilio,populacao,taxa_obitos_100k,"
            "ic95_inf,ic95_sup,taxa_padronizada_100k"
        ),
        "ano": f"eq.{ano}",
        "capitulo_cid": f"eq.{capitulo}",
        "sexo": f"eq.{sexo}",
        "order": "municipio_cod",
    }
    if uf:
        params["uf_sigla"] = f"eq.{uf.upper()}"
    if pop_min:
        params["populacao"] = f"gte.{pop_min}"
    return _maybe_df(_get("mart_mortalidade_municipio", params), as_df)


def causas(
    uf: Optional[str] = None,
    ano: int = 2023,
    top: Optional[int] = None,
    as_df: bool = False,
):
    """Óbitos por causa básica (CID-10, 3 caracteres), agregados no servidor."""
    params = {
        "select": "causabas_3,obitos:obitos.sum()",
        "ano": f"eq.{ano}",
        "order": "causabas_3",
    }
    if uf:
        params["uf_sigla"] = f"eq.{uf.upper()}"
    rows = _get("mart_mortalidade_causa", params)
    rows.sort(key=lambda r: -r["obitos"])
    if top:
        rows = rows[:top]
    return _maybe_df(rows, as_df)


def excesso(uf: str = "BR", as_df: bool = False):
    """Excesso de mortalidade (2020+): observado × esperado (baseline 2015–2019)."""
    params = {
        "select": "uf_sigla,ano,mes,mes_competencia,obitos,esperado,excesso,pct_excesso",
        "uf_sigla": f"eq.{uf.upper()}",
        "order": "mes_competencia",
    }
    return _maybe_df(_get("mart_excesso_uf_mes", params), as_df)


def dengue(
    uf: Optional[str] = None,
    ano: int = 2024,
    nivel: str = "ano",
    as_df: bool = False,
):
    """Dengue (SINAN). nivel='ano' → resumo municipal anual com incidência e
    letalidade; nivel='semana' → série por semana epidemiológica."""
    if nivel == "semana":
        params = {
            "select": "municipio_cod,uf_sigla,ano_epi,semana_epi,casos_provaveis,casos_graves,obitos",
            "ano_epi": f"eq.{ano}",
            "order": "municipio_cod,semana_epi",
        }
        table = "mart_dengue_semana"
    else:
        params = {
            "select": "municipio_cod,municipio_nome,uf_sigla,regiao,ano_epi,"
                      "casos_provaveis,casos_graves,obitos,populacao,incidencia_100k,letalidade_pct",
            "ano_epi": f"eq.{ano}",
            "order": "municipio_cod",
        }
        table = "mart_dengue_municipio_ano"
    if uf:
        params["uf_sigla"] = f"eq.{uf.upper()}"
    return _maybe_df(_get(table, params), as_df)


def internacoes(
    uf: Optional[str] = None,
    ano: int = 2024,
    capitulo: str = "TOTAL",
    as_df: bool = False,
):
    """Internações SUS (SIH/AIH) por município: volume, permanência média,
    mortalidade intra-hospitalar e custo médio. capitulo: I–XXII ou TOTAL."""
    params = {
        "select": "municipio_cod,municipio_nome,uf_sigla,regiao,ano,capitulo_cid,"
                  "internacoes,obitos,dias_permanencia,valor_total,permanencia_media,"
                  "mortalidade_pct,custo_medio,internacoes_100k,populacao",
        "ano": f"eq.{ano}",
        "capitulo_cid": f"eq.{capitulo}",
        "order": "municipio_cod",
    }
    if uf:
        params["uf_sigla"] = f"eq.{uf.upper()}"
    return _maybe_df(_get("mart_internacoes_municipio", params), as_df)


def cid10(as_df: bool = False):
    """Descrições das categorias CID-10 (3 caracteres) e capítulos."""
    cats = _get("dim_cid10_categoria", {"select": "causabas_3,descricao", "order": "causabas_3"})
    return _maybe_df(cats, as_df)


def metadados() -> dict[str, str]:
    """Fontes, métodos, exclusões, licença e versão do dataset."""
    return {r["chave"]: r["valor"] for r in _get("meta_dataset", {"select": "chave,valor"})}
