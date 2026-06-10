"""
Página 1 — Mapa de Produção Ambulatorial por Município
Exibe mapa coroplético com Plotly usando a API /producao/mapa/{uf_sigla}
"""
import plotly.express as px
import pandas as pd
import streamlit as st

from dashboard.api_client import APIError, get_producao_mapa

# ── Config da página ──────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Mapa | saude-publica-br",
    page_icon="🗺️",
    layout="wide",
)

# ── Estado global: URL da API (definida na Home) ──────────────────────────────
api_url = st.session_state.get("api_url", "http://localhost:8000")

# ── Constantes ────────────────────────────────────────────────────────────────
UFS = [
    "AC","AL","AM","AP","BA","CE","DF","ES","GO","MA","MG","MS","MT","PA",
    "PB","PE","PI","PR","RJ","RN","RO","RR","RS","SC","SE","SP","TO",
]
ANOS = list(range(2020, 2025))
MESES = {
    1:"Janeiro",2:"Fevereiro",3:"Março",4:"Abril",5:"Maio",6:"Junho",
    7:"Julho",8:"Agosto",9:"Setembro",10:"Outubro",11:"Novembro",12:"Dezembro",
}

METRIC_OPTIONS = {
    "Total de Procedimentos": "total_procedimentos",
    "Taxa por 10 mil hab.": "taxa_proc_10k",
    "% Aprovação": "pct_aprovacao",
    "Ranking (posição)": "ranking",
    "Percentil": "percentil",
}

# ── Sidebar — filtros ─────────────────────────────────────────────────────────
with st.sidebar:
    st.header("🗺️ Mapa")
    uf_sel = st.selectbox("Estado (UF)", UFS, index=UFS.index("SP"))
    ano_sel = st.selectbox("Ano", ANOS, index=len(ANOS) - 1)
    mes_sel = st.selectbox("Mês (opcional)", ["Todos"] + list(MESES.values()))
    metrica_label = st.selectbox("Métrica", list(METRIC_OPTIONS.keys()))
    st.divider()
    st.caption(f"API: {api_url}")

mes_num = None
if mes_sel != "Todos":
    mes_num = {v: k for k, v in MESES.items()}[mes_sel]

metrica_col = METRIC_OPTIONS[metrica_label]

# ── Título ────────────────────────────────────────────────────────────────────
periodo = f"{mes_sel} / {ano_sel}" if mes_num else str(ano_sel)
st.title(f"🗺️ Mapa — {uf_sel}")
st.caption(f"Produção Ambulatorial (SIA/PA) · {periodo} · {metrica_label}")

# ── Carga de dados ────────────────────────────────────────────────────────────
with st.spinner("Carregando dados..."):
    try:
        resp = get_producao_mapa(
            api_url, uf_sigla=uf_sel, ano=ano_sel, mes=mes_num,
            indicador=metrica_col,
        )
    except APIError as e:
        st.error(f"❌ Erro ao buscar dados: {e}")
        st.stop()

data = resp.get("data", [])
if not data:
    st.warning("Nenhum dado encontrado para os filtros selecionados.")
    st.stop()

df = pd.DataFrame(data)

# A API agrega o indicador solicitado na coluna genérica "valor".
# Se a coluna esperada não existe mas "valor" está presente, renomeia.
if metrica_col not in df.columns and "valor" in df.columns:
    df = df.rename(columns={"valor": metrica_col})

# Verificar se a métrica existe no DataFrame após o rename
if metrica_col not in df.columns:
    st.warning(f"Coluna '{metrica_col}' não disponível nos dados retornados.")
    st.dataframe(df.head())
    st.stop()

# ── Mapa ──────────────────────────────────────────────────────────────────────
# GeoJSON IBGe para municípios brasileiros — carregado via CDN
GEOJSON_URL = (
    "https://raw.githubusercontent.com/tbrugz/geodata-br/"
    "master/geojson/geojs-{uf_code}-mun.json"
)

# Mapear UF → código IBGE do estado
UF_CODES = {
    "AC":"12","AL":"27","AM":"13","AP":"16","BA":"29","CE":"23","DF":"53",
    "ES":"32","GO":"52","MA":"21","MG":"31","MS":"50","MT":"51","PA":"15",
    "PB":"25","PE":"26","PI":"22","PR":"41","RJ":"33","RN":"24","RO":"11",
    "RR":"14","RS":"43","SC":"42","SE":"28","SP":"35","TO":"17",
}
uf_code = UF_CODES.get(uf_sel, "35")

# Usar visualização por escala de cor com px.choropleth_mapbox
# Se não tiver geojson disponível, fallback para scatter_geo

escala_min = resp.get("escala_min", df[metrica_col].min())
escala_max = resp.get("escala_max", df[metrica_col].max())

# Hover com informações completas
hover_cols = ["municipio_nome", "municipio_cod", metrica_col]
hover_cols = [c for c in hover_cols if c in df.columns]

fig = px.choropleth_mapbox(
    df,
    geojson=f"https://raw.githubusercontent.com/tbrugz/geodata-br/master/geojson/geojs-{uf_code}-mun.json",
    locations="municipio_cod",
    featureidkey="properties.id",
    color=metrica_col,
    color_continuous_scale="Blues",
    range_color=(escala_min, escala_max),
    hover_name="municipio_nome" if "municipio_nome" in df.columns else "municipio_cod",
    hover_data={c: True for c in hover_cols},
    mapbox_style="carto-positron",
    zoom=5,
    center={"lat": -15.0, "lon": -53.0},
    opacity=0.75,
    labels={metrica_col: metrica_label},
    title=f"{metrica_label} — {uf_sel} · {periodo}",
)
fig.update_layout(
    margin={"r": 0, "t": 40, "l": 0, "b": 0},
    height=600,
    coloraxis_colorbar=dict(title=metrica_label, thickness=15),
)

st.plotly_chart(fig, use_container_width=True)

# ── Tabela de municípios ──────────────────────────────────────────────────────
with st.expander("📋 Ver tabela de municípios", expanded=False):
    cols_show = [c for c in [
        "municipio_nome", "municipio_cod", "uf_sigla",
        "total_procedimentos", "total_aprovados",
        "taxa_proc_10k", "pct_aprovacao", "ranking", "percentil",
    ] if c in df.columns]

    rename_map = {
        "municipio_nome": "Município",
        "municipio_cod": "Código",
        "uf_sigla": "UF",
        "total_procedimentos": "Procedimentos",
        "total_aprovados": "Aprovados",
        "taxa_proc_10k": "Taxa/10k hab.",
        "pct_aprovacao": "% Aprovação",
        "ranking": "Ranking",
        "percentil": "Percentil",
    }
    df_show = df[cols_show].rename(columns=rename_map)
    _sort_col = "Procedimentos" if "Procedimentos" in df_show.columns else df_show.columns[-1]
    st.dataframe(
        df_show.sort_values(_sort_col, ascending=False)
               .reset_index(drop=True),
        use_container_width=True,
        height=400,
    )
    st.caption(f"Total: {len(df)} municípios")

# ── Métricas rápidas ──────────────────────────────────────────────────────────
st.divider()
m1, m2, m3, m4 = st.columns(4)
if "total_procedimentos" in df.columns:
    m1.metric("Total Procedimentos", f"{df['total_procedimentos'].sum():,.0f}")
if "taxa_proc_10k" in df.columns:
    m2.metric("Média Taxa/10k", f"{df['taxa_proc_10k'].mean():.1f}")
if "pct_aprovacao" in df.columns:
    m3.metric("Média Aprovação", f"{df['pct_aprovacao'].mean():.1f}%")
m4.metric("Municípios", f"{len(df):,}")
