"""
Página 4 — Ranking de Municípios
Usa /ranking/{uf_sigla} e /ranking/nacional
"""
import plotly.express as px
import pandas as pd
import streamlit as st

from dashboard.api_client import APIError, get_ranking_uf, get_ranking_nacional

# ── Config ────────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Ranking | saude-publica-br",
    page_icon="🏆",
    layout="wide",
)

api_url = st.session_state.get("api_url", "http://localhost:8000")

UFS = [
    "AC","AL","AM","AP","BA","CE","DF","ES","GO","MA","MG","MS","MT","PA",
    "PB","PE","PI","PR","RJ","RN","RO","RR","RS","SC","SE","SP","TO",
]
ANOS = list(range(2020, 2025))

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.header("🏆 Ranking")
    modo = st.radio("Escopo", ["Por Estado", "Nacional"], horizontal=True)

    if modo == "Por Estado":
        uf_sel = st.selectbox("Estado (UF)", UFS, index=UFS.index("SP"))
    else:
        uf_sel = None
        top_n = st.slider("Top N municípios", min_value=10, max_value=500, value=100, step=10)
        ordem = st.radio("Ordem", ["Melhores", "Piores"], horizontal=True)

    ano_sel = st.selectbox("Ano", ANOS, index=len(ANOS) - 1)
    st.divider()
    st.caption(f"API: {api_url}")

# ── Título ────────────────────────────────────────────────────────────────────
st.title("🏆 Ranking de Municípios")

# ── Carga ─────────────────────────────────────────────────────────────────────
with st.spinner("Carregando ranking..."):
    try:
        if modo == "Por Estado":
            resp = get_ranking_uf(api_url, uf_sigla=uf_sel, ano=ano_sel)
            st.caption(f"Municípios de {uf_sel} · {ano_sel}")
        else:
            ordem_param = "melhor" if ordem == "Melhores" else "pior"
            resp = get_ranking_nacional(
                api_url, ano=ano_sel, top=top_n, ordem=ordem_param
            )
            st.caption(f"Top {top_n} municípios — {ordem} · {ano_sel}")
    except APIError as e:
        st.error(f"❌ {e}")
        st.stop()

data = resp.get("data", [])
if not data:
    st.warning("Nenhum dado de ranking encontrado.")
    st.stop()

df = pd.DataFrame(data)

# ── Detecção de colunas disponíveis ──────────────────────────────────────────
ranking_col = next((c for c in ["ranking_estadual", "ranking_nacional"] if c in df.columns), None)
score_col = next((c for c in ["score_acesso", "score_producao", "score_geral"] if c in df.columns), None)
taxa_col = "taxa_proc_10k" if "taxa_proc_10k" in df.columns else None

# ── KPIs ──────────────────────────────────────────────────────────────────────
k1, k2, k3 = st.columns(3)
k1.metric("Municípios", f"{len(df):,}")
if taxa_col:
    k2.metric("Média Taxa/10k", f"{df[taxa_col].mean():.1f}")
if "pct_aprovacao" in df.columns:
    k3.metric("Média Aprovação", f"{df['pct_aprovacao'].mean():.1f}%")

st.divider()

# ── Tabs ──────────────────────────────────────────────────────────────────────
tab1, tab2 = st.tabs(["📊 Gráfico de Barras", "📋 Tabela"])

with tab1:
    if taxa_col and "municipio_nome" in df.columns:
        top_show = df.nlargest(30, taxa_col) if len(df) > 30 else df
        top_show = top_show.sort_values(taxa_col, ascending=True)

        fig = px.bar(
            top_show,
            x=taxa_col,
            y="municipio_nome",
            orientation="h",
            color=taxa_col,
            color_continuous_scale="Blues",
            text=taxa_col,
            labels={
                taxa_col: "Taxa por 10k hab.",
                "municipio_nome": "Município",
            },
            title=f"Top 30 — Taxa de Procedimentos por 10 mil hab. · {ano_sel}",
        )
        fig.update_traces(texttemplate="%{text:.0f}", textposition="outside")
        fig.update_layout(
            height=600,
            showlegend=False,
            margin=dict(l=200, r=60, t=50, b=30),
            coloraxis_showscale=False,
        )
        st.plotly_chart(fig, use_container_width=True)
    elif score_col and "municipio_nome" in df.columns:
        top_show = df.nlargest(30, score_col) if len(df) > 30 else df
        top_show = top_show.sort_values(score_col, ascending=True)
        fig = px.bar(
            top_show,
            x=score_col,
            y="municipio_nome",
            orientation="h",
            color=score_col,
            color_continuous_scale="Greens",
            labels={score_col: "Score", "municipio_nome": "Município"},
            title=f"Top 30 por Score · {ano_sel}",
        )
        fig.update_layout(height=600, showlegend=False, margin=dict(l=200))
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Gráfico não disponível — colunas de métrica não encontradas.")

with tab2:
    col_rename = {
        "ranking_estadual": "Rank UF",
        "ranking_nacional": "Rank Nacional",
        "municipio_cod": "Código",
        "municipio_nome": "Município",
        "uf_sigla": "UF",
        "populacao": "População",
        "total_procedimentos": "Procedimentos",
        "total_aprovados": "Aprovados",
        "taxa_proc_10k": "Taxa/10k",
        "pct_aprovacao": "% Aprov.",
        "score_acesso": "Score Acesso",
        "score_producao": "Score Produção",
        "score_geral": "Score Geral",
    }
    cols_show = [c for c in col_rename if c in df.columns]
    df_show = df[cols_show].rename(columns=col_rename)

    # Ordenar por ranking se existir, senão taxa
    sort_col = "Rank UF" if "Rank UF" in df_show.columns else (
        "Rank Nacional" if "Rank Nacional" in df_show.columns else
        "Taxa/10k" if "Taxa/10k" in df_show.columns else df_show.columns[0]
    )
    ascending = sort_col.startswith("Rank")
    df_show = df_show.sort_values(sort_col, ascending=ascending).reset_index(drop=True)

    st.dataframe(df_show, use_container_width=True, height=500)
    st.caption(f"Total: {resp.get('paginacao', {}).get('total', len(df))} municípios")

# ── Dispersão ─────────────────────────────────────────────────────────────────
if taxa_col and "pct_aprovacao" in df.columns:
    with st.expander("🔍 Gráfico de Dispersão — Taxa vs Aprovação"):
        fig_scatter = px.scatter(
            df,
            x=taxa_col,
            y="pct_aprovacao",
            hover_name="municipio_nome" if "municipio_nome" in df.columns else None,
            color="uf_sigla" if "uf_sigla" in df.columns else None,
            size="populacao" if "populacao" in df.columns else None,
            size_max=25,
            labels={
                taxa_col: "Taxa/10k hab.",
                "pct_aprovacao": "% Aprovação",
                "uf_sigla": "UF",
            },
            title=f"Taxa de Procedimentos vs % Aprovação · {ano_sel}",
        )
        fig_scatter.update_layout(height=450)
        st.plotly_chart(fig_scatter, use_container_width=True)
