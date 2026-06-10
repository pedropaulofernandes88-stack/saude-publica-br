"""
Página 5 — Epidemiologia por CID-10
Usa /epidemiologia/cid10 e /epidemiologia/cid10/{uf_sigla}
"""
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import streamlit as st

from dashboard.api_client import APIError, get_epi_cid10

# ── Config ────────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Epidemiologia | saude-publica-br",
    page_icon="🦠",
    layout="wide",
)

api_url = st.session_state.get("api_url", "http://localhost:8000")

UFS_ALL = ["Nacional"] + [
    "AC","AL","AM","AP","BA","CE","DF","ES","GO","MA","MG","MS","MT","PA",
    "PB","PE","PI","PR","RJ","RN","RO","RR","RS","SC","SE","SP","TO",
]
ANOS = [None] + list(range(2020, 2025))

# CID-10 capítulos para referência rápida
CID10_CAPITULOS = {
    "I":   "Inf. Intestinais e outras",
    "II":  "Neoplasias",
    "III": "Sangue e órgãos hematopoéticos",
    "IV":  "Endócrinas e nutricionais",
    "V":   "Transtornos mentais",
    "VI":  "Sistema nervoso",
    "VII": "Olho e anexos",
    "VIII":"Ouvido e apófise mastoide",
    "IX":  "Aparelho circulatório",
    "X":   "Aparelho respiratório",
    "XI":  "Aparelho digestivo",
    "XII": "Pele e tecido subcutâneo",
    "XIII":"Sistema osteomuscular",
    "XIV": "Aparelho geniturinário",
    "XV":  "Gravidez, parto e puerpério",
    "XVI": "Perinatal",
    "XVII":"Malformações congênitas",
    "XVIII":"Sintomas e sinais mal definidos",
    "XIX": "Lesões e envenenamentos",
    "XX":  "Causas externas",
    "XXI": "Fatores que influenciam saúde",
}

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.header("🦠 Epidemiologia")
    uf_sel = st.selectbox("Estado (UF)", UFS_ALL)
    ano_sel = st.selectbox("Ano", [str(a) if a else "Todos" for a in ANOS])
    top_n = st.slider("Top N diagnósticos", min_value=5, max_value=30, value=15)

    st.divider()
    st.caption(
        "Dados do SIA/PA — diagnóstico principal (CID-10).\n\n"
        "Representa o 1º diagnóstico registrado na produção ambulatorial."
    )
    st.caption(f"API: {api_url}")

uf_param = None if uf_sel == "Nacional" else uf_sel
ano_param = None if ano_sel == "Todos" else int(ano_sel)

# ── Título ────────────────────────────────────────────────────────────────────
st.title("🦠 Epidemiologia por CID-10")
escopo = "Brasil" if not uf_param else uf_param
periodo = "Todos os anos" if not ano_param else ano_param
st.caption(f"{escopo} · {periodo} · Top {top_n} diagnósticos")

# ── Carga ─────────────────────────────────────────────────────────────────────
with st.spinner("Carregando dados epidemiológicos..."):
    try:
        resp = get_epi_cid10(api_url, uf_sigla=uf_param, ano=ano_param, top_n=top_n)
    except APIError as e:
        st.error(f"❌ {e}")
        st.stop()

data = resp.get("data", [])
if not data:
    st.warning("Nenhum dado epidemiológico encontrado.")
    st.stop()

df = pd.DataFrame(data)

# ── KPIs ──────────────────────────────────────────────────────────────────────
k1, k2, k3 = st.columns(3)
k1.metric("Diagnósticos distintos", f"{resp.get('paginacao', {}).get('total', len(df)):,}")

if "total_procedimentos" in df.columns:
    k2.metric("Total Atendimentos (Top)", f"{df['total_procedimentos'].sum():,.0f}")
if "pct_total" in df.columns:
    k3.metric("Cobertura Top N", f"{df['pct_total'].sum():.1f}%")

st.divider()

# ── Tabs ──────────────────────────────────────────────────────────────────────
tab1, tab2, tab3 = st.tabs(["📊 Barras", "🥧 Composição", "📋 Tabela"])

with tab1:
    val_col = next((c for c in ["total_procedimentos","total_atendimentos","count"] if c in df.columns), None)
    label_col = next((c for c in ["descricao_capitulo","cid10_descricao","descricao"] if c in df.columns), None)

    if not val_col or not label_col:
        st.warning("Colunas esperadas não encontradas nos dados.")
        st.dataframe(df.head())
    else:
        df_plot = df.nlargest(top_n, val_col).sort_values(val_col, ascending=True)

        fig = px.bar(
            df_plot,
            x=val_col,
            y=label_col,
            orientation="h",
            color=val_col,
            color_continuous_scale="Reds",
            text=val_col,
            labels={val_col: "Atendimentos", label_col: "CID-10"},
            title=f"Top {top_n} Diagnósticos CID-10 — {escopo} · {periodo}",
        )
        fig.update_traces(texttemplate="%{text:,.0f}", textposition="outside")
        fig.update_layout(
            height=max(400, top_n * 28),
            showlegend=False,
            coloraxis_showscale=False,
            margin=dict(l=260, r=80, t=50, b=30),
            yaxis=dict(automargin=True),
        )
        st.plotly_chart(fig, use_container_width=True)

with tab2:
    if val_col and label_col:
        df_pie = df.nlargest(10, val_col).copy()
        outros_val = df[val_col].sum() - df_pie[val_col].sum()
        if outros_val > 0:
            row_outros = {label_col: "Outros", val_col: outros_val}
            df_pie = pd.concat([df_pie, pd.DataFrame([row_outros])], ignore_index=True)

        fig_pie = px.pie(
            df_pie,
            values=val_col,
            names=label_col,
            title=f"Composição dos Diagnósticos — {escopo} · {periodo}",
            color_discrete_sequence=px.colors.qualitative.Set3,
        )
        fig_pie.update_traces(textposition="inside", textinfo="percent+label")
        fig_pie.update_layout(height=500, showlegend=True)
        st.plotly_chart(fig_pie, use_container_width=True)
    else:
        st.info("Dados insuficientes para este gráfico.")

with tab3:
    col_rename = {
        "capitulo_cid10": "Capítulo",
        "descricao_capitulo": "Descrição",
        "cid10_descricao": "Descrição",
        "cid10_cod": "CID-10",
        "codigo": "CID-10",
        "descricao": "Descrição",
        "uf_sigla": "UF",
        "ano": "Ano",
        "total_procedimentos": "Procedimentos",
        "total_atendimentos": "Atendimentos",
        "count": "Qtd.",
        "pct_atend_uf": "% UF",
        "rank_capitulo_uf": "Ranking",
        "variacao_anual_pct": "Var. Anual %",
        "pct_total": "% do Total",
        "ranking_cid": "Ranking",
    }
    cols_show = [c for c in col_rename if c in df.columns]
    df_show = df[cols_show].rename(columns=col_rename)

    val_show = next((c for c in ["Atendimentos","Procedimentos","Qtd."] if c in df_show.columns), None)
    if val_show:
        df_show = df_show.sort_values(val_show, ascending=False)

    st.dataframe(df_show.reset_index(drop=True), use_container_width=True, height=450)
    st.caption(f"Total registros: {resp.get('paginacao', {}).get('total', len(df))}")

# ── Referência CID-10 ─────────────────────────────────────────────────────────
with st.expander("📚 Referência — Capítulos CID-10"):
    df_ref = pd.DataFrame([
        {"Capítulo": k, "Descrição": v} for k, v in CID10_CAPITULOS.items()
    ])
    st.dataframe(df_ref, use_container_width=True, height=300, hide_index=True)
