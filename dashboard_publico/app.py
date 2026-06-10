"""
Painel público — Mortalidade no Brasil (SIM/DataSUS)
====================================================

Dashboard de custo zero: consulta a API pública (Supabase/PostgREST) que serve
os marts agregados gerados por scripts/pipeline_custo_zero.py.

Deploy gratuito: Streamlit Community Cloud (share.streamlit.io)
  - Main file: dashboard_publico/app.py
  - Secrets (opcional): SUPABASE_URL, SUPABASE_ANON_KEY

A chave anon é pública por design (acesso somente leitura via RLS).
"""
from __future__ import annotations

import os

import pandas as pd
import requests
import streamlit as st

# ──────────────────────────────────────────────────────────────────────────────
# Configuração
# ──────────────────────────────────────────────────────────────────────────────

DEFAULT_URL = "https://zekjhmxjamatlxpkykde.supabase.co"
DEFAULT_KEY = (
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9."
    "eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Inpla2pobXhqYW1hdGx4cGt5a2RlIiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODEwNzY4MzIsImV4cCI6MjA5NjY1MjgzMn0."
    "px8FcU0QK8w9v95kwGlGzASKpY3drsxAvFe0e6wUoCU"
)


def _secret(name: str, default: str) -> str:
    try:
        return st.secrets.get(name, os.environ.get(name, default))
    except Exception:
        return os.environ.get(name, default)


SUPABASE_URL = _secret("SUPABASE_URL", DEFAULT_URL).rstrip("/")
SUPABASE_KEY = _secret("SUPABASE_ANON_KEY", DEFAULT_KEY)

HEADERS = {"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}"}

UFS = [
    "Brasil", "AC", "AL", "AM", "AP", "BA", "CE", "DF", "ES", "GO", "MA", "MG",
    "MS", "MT", "PA", "PB", "PE", "PI", "PR", "RJ", "RN", "RO", "RR", "RS",
    "SC", "SE", "SP", "TO",
]


@st.cache_data(ttl=21_600, show_spinner=False)
def rest(table: str, params: dict) -> pd.DataFrame:
    """GET no PostgREST com paginação automática (Range)."""
    rows: list[dict] = []
    offset, page = 0, 10_000
    while True:
        headers = {**HEADERS, "Range-Unit": "items", "Range": f"{offset}-{offset + page - 1}"}
        r = requests.get(f"{SUPABASE_URL}/rest/v1/{table}", params=params, headers=headers, timeout=60)
        r.raise_for_status()
        chunk = r.json()
        rows.extend(chunk)
        if len(chunk) < page:
            break
        offset += page
    return pd.DataFrame(rows)


# ──────────────────────────────────────────────────────────────────────────────
# UI
# ──────────────────────────────────────────────────────────────────────────────

st.set_page_config(page_title="Mortalidade no Brasil — SIM/DataSUS", page_icon="🏥", layout="wide")
st.title("🏥 Mortalidade no Brasil — dados abertos do SUS")
st.caption(
    "Fonte: SIM/DataSUS (Ministério da Saúde) e IBGE. Óbitos não fetais. "
    "Dados do ano mais recente podem ser preliminares."
)

with st.sidebar:
    st.header("Filtros")
    caps = rest("dim_cid10_capitulo", {"select": "capitulo,descricao", "order": "capitulo_num"})
    cap_opts = ["TOTAL (todas as causas)"] + [
        f"{r.capitulo} — {r.descricao}" for r in caps.itertuples()
    ]
    uf = st.selectbox("UF", UFS, index=0)
    cap_sel = st.selectbox("Capítulo CID-10 (causa)", cap_opts, index=0)
    capitulo = "TOTAL" if cap_sel.startswith("TOTAL") else cap_sel.split(" — ")[0]
    anos_df = rest("meta_dataset", {"select": "valor", "chave": "eq.anos_cobertura"})
    anos = [int(a) for a in anos_df.iloc[0]["valor"].split(",")] if not anos_df.empty else [2022, 2023, 2024]
    ano = st.selectbox("Ano (ranking e causas)", sorted(anos, reverse=True), index=0)
    st.markdown("---")
    st.markdown(
        f"**API pública (REST):**\n\n`{SUPABASE_URL}/rest/v1/`\n\n"
        "Documentação no README do projeto."
    )

# ── Série mensal ──────────────────────────────────────────────────────────────
st.subheader(f"Série mensal de óbitos — {uf}" + ("" if capitulo == "TOTAL" else f" · capítulo {capitulo}"))

params = {
    "select": "mes_competencia,uf_sigla,obitos",
    "capitulo_cid": f"eq.{capitulo}",
    "sexo": "eq.TOTAL",
    "faixa_etaria": "eq.TOTAL",
    "order": "mes_competencia",
}
if uf != "Brasil":
    params["uf_sigla"] = f"eq.{uf}"
serie = rest("mart_mortalidade_uf_mes", params)

if serie.empty:
    st.info("Sem dados para a seleção.")
else:
    serie_m = serie.groupby("mes_competencia", as_index=False)["obitos"].sum()
    serie_m["mes_competencia"] = pd.to_datetime(serie_m["mes_competencia"])
    c1, c2, c3 = st.columns(3)
    total_periodo = int(serie_m["obitos"].sum())
    c1.metric("Óbitos no período", f"{total_periodo:,}".replace(",", "."))
    c2.metric("Média mensal", f"{int(serie_m['obitos'].mean()):,}".replace(",", "."))
    ultimo = serie_m.iloc[-1]
    c3.metric(f"Último mês ({ultimo['mes_competencia']:%m/%Y})", f"{int(ultimo['obitos']):,}".replace(",", "."))
    st.line_chart(serie_m.set_index("mes_competencia")["obitos"], height=320)

# ── Composição por sexo e faixa etária ───────────────────────────────────────
col_a, col_b = st.columns(2)

with col_a:
    st.subheader("Por faixa etária")
    p = {
        "select": "faixa_etaria,obitos",
        "capitulo_cid": f"eq.{capitulo}",
        "sexo": "eq.TOTAL",
        "faixa_etaria": "neq.TOTAL",
        "ano": f"eq.{ano}",
    }
    if uf != "Brasil":
        p["uf_sigla"] = f"eq.{uf}"
    fx = rest("mart_mortalidade_uf_mes", p)
    if not fx.empty:
        ordem = ["<1", "1-4", "5-14", "15-29", "30-44", "45-59", "60-74", "75+", "IGN"]
        fx = fx.groupby("faixa_etaria", as_index=False)["obitos"].sum()
        fx["faixa_etaria"] = pd.Categorical(fx["faixa_etaria"], categories=ordem, ordered=True)
        st.bar_chart(fx.sort_values("faixa_etaria").set_index("faixa_etaria")["obitos"], height=300)

with col_b:
    st.subheader("Por sexo")
    p = {
        "select": "sexo,obitos",
        "capitulo_cid": f"eq.{capitulo}",
        "sexo": "neq.TOTAL",
        "faixa_etaria": "eq.TOTAL",
        "ano": f"eq.{ano}",
    }
    if uf != "Brasil":
        p["uf_sigla"] = f"eq.{uf}"
    sx = rest("mart_mortalidade_uf_mes", p)
    if not sx.empty:
        sx = sx.groupby("sexo", as_index=False)["obitos"].sum()
        sx["sexo"] = sx["sexo"].map({"M": "Masculino", "F": "Feminino", "I": "Ignorado"})
        st.bar_chart(sx.set_index("sexo")["obitos"], height=300)

# ── Ranking de municípios ─────────────────────────────────────────────────────
st.subheader(f"Municípios — taxa de óbitos por 100 mil hab. ({ano})")
pop_min = st.slider("População mínima do município", 0, 500_000, 50_000, step=10_000)

p = {
    "select": "municipio_nome,uf_sigla,obitos,populacao,taxa_obitos_100k",
    "capitulo_cid": f"eq.{capitulo}",
    "sexo": "eq.TOTAL",
    "ano": f"eq.{ano}",
    "populacao": f"gte.{max(pop_min, 1)}",
    "order": "taxa_obitos_100k.desc.nullslast",
    "limit": "300",
}
if uf != "Brasil":
    p["uf_sigla"] = f"eq.{uf}"
rank = rest("mart_mortalidade_municipio", p)
if not rank.empty:
    rank.columns = ["Município", "UF", "Óbitos", "População", "Taxa /100k hab"]
    st.dataframe(rank, use_container_width=True, height=380)

# ── Top causas ────────────────────────────────────────────────────────────────
st.subheader(f"Principais causas básicas (CID-10) — {uf}, {ano}")
p = {"select": "causabas_3,obitos", "ano": f"eq.{ano}", "order": "obitos.desc"}
if uf != "Brasil":
    p["uf_sigla"] = f"eq.{uf}"
causas = rest("mart_mortalidade_causa", p)
if not causas.empty:
    top = causas.groupby("causabas_3", as_index=False)["obitos"].sum().nlargest(15, "obitos")
    st.bar_chart(top.set_index("causabas_3")["obitos"], height=320)
    st.caption("Códigos CID-10 de 3 caracteres (ex.: I21 = infarto agudo do miocárdio, C34 = neoplasia de brônquios/pulmões).")

# ── Rodapé ────────────────────────────────────────────────────────────────────
st.markdown("---")
meta = rest("meta_dataset", {"select": "chave,valor"})
with st.expander("ℹ️ Sobre os dados (fontes, metodologia e licença)"):
    for r in meta.itertuples():
        st.markdown(f"- **{r.chave}**: {r.valor}")
    st.markdown(
        "- **Reprodutibilidade**: pipeline aberto em `scripts/pipeline_custo_zero.py` "
        "(microdados OpenDataSUS → DuckDB → marts agregados)."
    )
