"""
Página 3 — Anomalias de Produção (Z-score)
Usa /indicadores/anomalias com sigma configurável pelo usuário
"""
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import streamlit as st

from dashboard.api_client import APIError, get_anomalias

# ── Config ────────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Anomalias | saude-publica-br",
    page_icon="⚠️",
    layout="wide",
)

api_url = st.session_state.get("api_url", "http://localhost:8000")

UFS_ALL = ["Todos"] + [
    "AC","AL","AM","AP","BA","CE","DF","ES","GO","MA","MG","MS","MT","PA",
    "PB","PE","PI","PR","RJ","RN","RO","RR","RS","SC","SE","SP","TO",
]
ANOS = [None] + list(range(2020, 2025))

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.header("⚠️ Anomalias")

    sigma = st.slider(
        "Sensibilidade (σ — sigma)",
        min_value=1.0,
        max_value=4.0,
        value=2.0,
        step=0.5,
        help=(
            "Desvios-padrão acima/abaixo da média histórica. "
            "σ=2 detecta ~5% dos meses; σ=3 detecta ~0.3%."
        ),
    )
    uf_sel = st.selectbox("Estado (UF)", UFS_ALL)
    ano_sel = st.selectbox("Ano", [str(a) if a else "Todos" for a in ANOS])
    tipo_sel = st.radio("Tipo", ["Todos", "Alta", "Baixa"], horizontal=True)

    st.divider()
    st.caption(
        "**Como funciona:**\n\n"
        "O Z-score mede quantos desvios-padrão um mês está da média histórica "
        "do município. Valores extremos indicam eventos incomuns."
    )
    st.caption(f"API: {api_url}")

# Traduzir filtros
uf_param = None if uf_sel == "Todos" else uf_sel
ano_param = None if ano_sel == "Todos" else int(ano_sel)
tipo_param = None if tipo_sel == "Todos" else tipo_sel.lower()

# ── Título ────────────────────────────────────────────────────────────────────
st.title("⚠️ Anomalias de Produção Ambulatorial")
st.caption(
    f"Municípios com Z-score ≥ |{sigma}σ| · "
    f"{'Todos os estados' if not uf_param else uf_param} · "
    f"{'Todos os anos' if not ano_param else ano_param}"
)

# ── Carga ─────────────────────────────────────────────────────────────────────
with st.spinner("Detectando anomalias..."):
    try:
        resp = get_anomalias(
            api_url,
            sigma=sigma,
            uf_sigla=uf_param,
            ano=ano_param,
            tipo=tipo_param,
            por_pagina=500,
        )
    except APIError as e:
        st.error(f"❌ {e}")
        st.stop()

data = resp.get("data", [])
total = resp.get("paginacao", {}).get("total", len(data))

if not data:
    st.success(f"✅ Nenhuma anomalia detectada com σ ≥ {sigma}.")
    st.stop()

df = pd.DataFrame(data)
df["mes_competencia"] = pd.to_datetime(df["mes_competencia"])

# ── KPIs ──────────────────────────────────────────────────────────────────────
k1, k2, k3, k4 = st.columns(4)
k1.metric("Total Anomalias", f"{total:,}")

if "tipo_anomalia" in df.columns:
    n_alta = (df["tipo_anomalia"] == "alta").sum()
    n_baixa = (df["tipo_anomalia"] == "baixa").sum()
    k2.metric("📈 Pico (alta)", n_alta)
    k3.metric("📉 Queda (baixa)", n_baixa)

if "z_score" in df.columns:
    max_z = df["z_score"].abs().max()
    k4.metric("Z-score Máx.", f"{max_z:.2f}σ")

st.divider()

# ── Tabs ──────────────────────────────────────────────────────────────────────
tab1, tab2, tab3 = st.tabs(["📋 Tabela", "📊 Distribuição por Estado", "🗓️ Linha do Tempo"])

with tab1:
    col_rename = {
        "municipio_cod": "Código",
        "municipio_nome": "Município",
        "uf_sigla": "UF",
        "mes_competencia": "Competência",
        "ano": "Ano",
        "mes": "Mês",
        "total_procedimentos": "Procedimentos",
        "media_historica": "Média Hist.",
        "z_score": "Z-score",
        "tipo_anomalia": "Tipo",
        "pct_desvio": "Desvio %",
    }
    cols_show = [c for c in col_rename if c in df.columns]
    df_show = df[cols_show].copy()
    df_show["mes_competencia"] = df_show["mes_competencia"].dt.strftime("%b/%Y")
    df_show = df_show.rename(columns=col_rename)

    # Colorir linha por tipo
    def highlight_tipo(row):
        if row.get("Tipo") == "alta":
            return ["background-color: #fdecea"] * len(row)
        elif row.get("Tipo") == "baixa":
            return ["background-color: #e8f4fd"] * len(row)
        return [""] * len(row)

    df_sorted = (
        df_show.sort_values("Z-score", key=abs, ascending=False)
               .reset_index(drop=True)
    )
    st.dataframe(
        df_sorted.style.apply(highlight_tipo, axis=1),
        use_container_width=True,
        height=450,
    )
    st.caption(f"Exibindo {len(df_show)} de {total} anomalias")

with tab2:
    if "uf_sigla" in df.columns and "tipo_anomalia" in df.columns:
        df_uf = (
            df.groupby(["uf_sigla", "tipo_anomalia"])
            .size()
            .reset_index(name="count")
        )
        fig_bar = px.bar(
            df_uf,
            x="uf_sigla",
            y="count",
            color="tipo_anomalia",
            barmode="group",
            color_discrete_map={"alta": "#E74C3C", "baixa": "#3498DB"},
            labels={"uf_sigla": "Estado", "count": "Anomalias", "tipo_anomalia": "Tipo"},
            title=f"Anomalias por Estado — σ ≥ {sigma}",
        )
        fig_bar.update_layout(height=400, margin=dict(t=50, b=30))
        st.plotly_chart(fig_bar, use_container_width=True)
    else:
        st.info("Dados insuficientes para este gráfico.")

with tab3:
    if "mes_competencia" in df.columns:
        df_linha = (
            df.groupby(["mes_competencia", "tipo_anomalia"])
            .size()
            .reset_index(name="count")
        )
        fig_line = px.line(
            df_linha,
            x="mes_competencia",
            y="count",
            color="tipo_anomalia",
            markers=True,
            color_discrete_map={"alta": "#E74C3C", "baixa": "#3498DB"},
            labels={
                "mes_competencia": "Mês/Ano",
                "count": "Nº Anomalias",
                "tipo_anomalia": "Tipo",
            },
            title="Evolução Temporal das Anomalias",
        )
        fig_line.update_layout(height=380, margin=dict(t=50, b=30))
        st.plotly_chart(fig_line, use_container_width=True)
    else:
        st.info("Dados insuficientes para este gráfico.")

# ── Explicação ────────────────────────────────────────────────────────────────
with st.expander("ℹ️ Metodologia de detecção"):
    st.markdown("""
**Z-score por município**

Para cada município e mês, calculamos:

```
Z = (produção_mês - média_histórica) / desvio_padrão_histórico
```

- A média e desvio-padrão são calculados sobre todo o histórico disponível (2020–2024)
- Anomalia de **alta** (pico): Z ≥ +σ  — produção muito acima do normal
- Anomalia de **baixa** (queda): Z ≤ −σ — produção muito abaixo do normal
- Municípios com menos de 3 meses de histórico são excluídos

**Interpretação do sigma:**
- σ = 1.0 → 32% dos meses (muito sensível, muito ruído)
- σ = 2.0 → 5% dos meses (padrão)
- σ = 3.0 → 0.3% dos meses (apenas eventos extremos)
    """)
