"""
Página 2 — Série Temporal de Produção por Município
Usa /producao/series/{municipio_cod} com variação mês-a-mês via LAG SQL
"""
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import streamlit as st

from dashboard.api_client import APIError, get_producao_serie, get_producao

# ── Config ────────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Série Temporal | saude-publica-br",
    page_icon="📈",
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
    st.header("📈 Série Temporal")
    uf_sel = st.selectbox("Estado (UF)", UFS, index=UFS.index("SP"))
    ano_inicio = st.selectbox("Ano início", ANOS, index=0)
    ano_fim = st.selectbox("Ano fim", ANOS, index=len(ANOS) - 1)

    # Buscar municípios da UF selecionada
    st.divider()
    st.caption("Selecione o município:")

    with st.spinner("Carregando municípios..."):
        try:
            mun_resp = get_producao(api_url, uf_sigla=uf_sel, por_pagina=600)
            mun_list = mun_resp.get("data", [])
            # deduplica por código
            seen = set()
            municipios = []
            for m in mun_list:
                cod = m.get("municipio_cod")
                if cod and cod not in seen:
                    seen.add(cod)
                    nome = m.get("municipio_nome") or cod
                    municipios.append({"cod": cod, "label": f"{nome} ({cod})"})
            municipios.sort(key=lambda x: x["label"])
        except APIError:
            municipios = []

    if not municipios:
        st.warning("Não foi possível carregar municípios.")
        mun_options = {}
        mun_label = st.selectbox("Município", ["(sem dados)"])
        mun_cod = None
    else:
        mun_options = {m["label"]: m["cod"] for m in municipios}
        mun_label = st.selectbox("Município", list(mun_options.keys()))
        mun_cod = mun_options[mun_label]

    st.divider()
    mostrar_variacao = st.checkbox("Mostrar variação % mensal", value=True)
    st.caption(f"API: {api_url}")

# ── Título ────────────────────────────────────────────────────────────────────
st.title("📈 Série Temporal")
if mun_cod:
    st.caption(f"{mun_label} · {ano_inicio}–{ano_fim}")
else:
    st.info("Selecione um município na barra lateral.")
    st.stop()

# ── Carga ─────────────────────────────────────────────────────────────────────
with st.spinner("Carregando série..."):
    try:
        resp = get_producao_serie(
            api_url,
            municipio_cod=mun_cod,
            ano_inicio=ano_inicio,
            ano_fim=ano_fim,
        )
    except APIError as e:
        st.error(f"❌ {e}")
        st.stop()

serie = resp.get("serie", [])
if not serie:
    st.warning("Nenhum dado de série temporal encontrado.")
    st.stop()

df = pd.DataFrame(serie)
df["mes_competencia"] = pd.to_datetime(df["mes_competencia"])
df = df.sort_values("mes_competencia")

# ── Gráfico principal ─────────────────────────────────────────────────────────
tab1, tab2 = st.tabs(["📊 Procedimentos", "📉 Variação Mensal"])

with tab1:
    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=df["mes_competencia"],
        y=df["total_procedimentos"],
        mode="lines+markers",
        name="Procedimentos",
        line=dict(color="#0068C9", width=2),
        marker=dict(size=5),
        hovertemplate="<b>%{x|%b/%Y}</b><br>Procedimentos: %{y:,.0f}<extra></extra>",
    ))

    if "total_aprovados" in df.columns:
        fig.add_trace(go.Scatter(
            x=df["mes_competencia"],
            y=df["total_aprovados"],
            mode="lines",
            name="Aprovados",
            line=dict(color="#29B09D", width=1.5, dash="dot"),
            hovertemplate="<b>%{x|%b/%Y}</b><br>Aprovados: %{y:,.0f}<extra></extra>",
        ))

    fig.update_layout(
        title=f"Produção Ambulatorial — {mun_label}",
        xaxis_title="Mês/Ano",
        yaxis_title="Qtd. Procedimentos",
        hovermode="x unified",
        legend=dict(orientation="h", yanchor="bottom", y=1.02),
        height=420,
        margin=dict(t=60, b=40),
    )
    st.plotly_chart(fig, use_container_width=True)

with tab2:
    if "variacao_pct" not in df.columns:
        st.info("Dados de variação % não disponíveis para este município.")
    else:
        df_var = df.dropna(subset=["variacao_pct"])
        cores = ["#E74C3C" if v < 0 else "#27AE60" for v in df_var["variacao_pct"]]

        fig2 = go.Figure()
        fig2.add_trace(go.Bar(
            x=df_var["mes_competencia"],
            y=df_var["variacao_pct"],
            marker_color=cores,
            name="Var. % m/m",
            hovertemplate="<b>%{x|%b/%Y}</b><br>Variação: %{y:.1f}%<extra></extra>",
        ))
        fig2.add_hline(y=0, line_color="black", line_width=1)
        fig2.update_layout(
            title="Variação % Mensal (mês anterior)",
            xaxis_title="Mês/Ano",
            yaxis_title="Variação %",
            height=380,
            margin=dict(t=60, b=40),
        )
        st.plotly_chart(fig2, use_container_width=True)

# ── Métricas ──────────────────────────────────────────────────────────────────
st.divider()
c1, c2, c3, c4 = st.columns(4)

total_geral = df["total_procedimentos"].sum()
media_mensal = df["total_procedimentos"].mean()
max_mes = df.loc[df["total_procedimentos"].idxmax()]
min_mes = df.loc[df["total_procedimentos"].idxmin()]

c1.metric("Total no Período", f"{total_geral:,.0f}")
c2.metric("Média Mensal", f"{media_mensal:,.0f}")
c3.metric(
    "Pico",
    f"{max_mes['total_procedimentos']:,.0f}",
    delta=max_mes["mes_competencia"].strftime("%b/%Y"),
)
c4.metric(
    "Mínimo",
    f"{min_mes['total_procedimentos']:,.0f}",
    delta=min_mes["mes_competencia"].strftime("%b/%Y"),
)

# ── Tabela ────────────────────────────────────────────────────────────────────
with st.expander("📋 Ver tabela completa", expanded=False):
    cols_show = [c for c in [
        "mes_competencia", "total_procedimentos", "total_aprovados",
        "taxa_proc_10k", "pct_aprovacao", "variacao_pct",
    ] if c in df.columns]
    df_show = df[cols_show].copy()
    df_show["mes_competencia"] = df_show["mes_competencia"].dt.strftime("%b/%Y")
    df_show = df_show.rename(columns={
        "mes_competencia": "Mês",
        "total_procedimentos": "Procedimentos",
        "total_aprovados": "Aprovados",
        "taxa_proc_10k": "Taxa/10k",
        "pct_aprovacao": "% Aprov.",
        "variacao_pct": "Var. %",
    })
    st.dataframe(df_show, use_container_width=True, height=350)
