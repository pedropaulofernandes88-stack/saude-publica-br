"""
saude-publica-br — Dashboard Streamlit MVP
==========================================
Página inicial: visão nacional com KPIs de alto nível.

Execução:
    cd dashboard
    streamlit run app.py

Requisito: API rodando em API_BASE_URL (padrão: http://localhost:8000)
"""
from __future__ import annotations

import os

import streamlit as st

from dashboard.api_client import APIClient, APIError

# ---------------------------------------------------------------------------
# Configuração da página
# ---------------------------------------------------------------------------

st.set_page_config(
    page_title="saude-publica-br",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={
        "Get Help": "https://github.com/saude-publica-br",
        "Report a bug": "https://github.com/saude-publica-br/issues",
        "About": "O Our World in Data do SUS 🇧🇷",
    },
)

# ---------------------------------------------------------------------------
# Estilo customizado
# ---------------------------------------------------------------------------

st.markdown(
    """
    <style>
    .metric-card {
        background: #F0F2F6;
        border-radius: 12px;
        padding: 20px 24px;
        text-align: center;
    }
    .metric-title { font-size: 13px; color: #555; margin-bottom: 4px; }
    .metric-value { font-size: 32px; font-weight: 700; color: #0068C9; }
    .metric-sub   { font-size: 12px; color: #888; margin-top: 4px; }
    .stAlert { border-radius: 8px; }
    </style>
    """,
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------

with st.sidebar:
    st.image(
        "https://upload.wikimedia.org/wikipedia/commons/thumb/0/05/Flag_of_Brazil.svg/320px-Flag_of_Brazil.svg.png",
        width=80,
    )
    st.title("saude-publica-br")
    st.caption("O Our World in Data do SUS 🏥")
    st.divider()

    api_url = st.text_input(
        "API URL",
        value=os.environ.get("API_BASE_URL", "http://localhost:8000"),
        help="URL base da FastAPI local ou em produção",
    )
    st.session_state["api_url"] = api_url

    st.divider()
    st.caption("📊 **Páginas**")
    st.page_link("app.py", label="🏠 Visão Nacional", icon="🏠")
    st.page_link("pages/1_Mapa.py", label="🗺️ Mapa por UF")
    st.page_link("pages/2_Serie_Temporal.py", label="📈 Série Temporal")
    st.page_link("pages/3_Anomalias.py", label="⚠️ Anomalias")
    st.page_link("pages/4_Ranking.py", label="🏆 Ranking")
    st.page_link("pages/5_Epidemiologia.py", label="🦠 Epidemiologia CID-10")
    st.divider()
    st.caption("Dados: SIA/PA · DataSUS · IBGE")
    st.caption("Pipeline: dbt · Supabase · Prefect")

# ---------------------------------------------------------------------------
# Cabeçalho
# ---------------------------------------------------------------------------

st.title("🏥 saude-publica-br")
st.subheader("Inteligência Epidemiológica do SUS — Atenção Ambulatorial")
st.markdown(
    "Produção ambulatorial, acesso, cobertura e perfil epidemiológico "
    "de **5.570 municípios** e **27 estados** brasileiros · 2020–2024"
)

# ---------------------------------------------------------------------------
# Verificação de saúde da API
# ---------------------------------------------------------------------------

client = APIClient(base_url=st.session_state.get("api_url", "http://localhost:8000"))

with st.spinner("Conectando à API..."):
    health = client.health()

if health.get("status") != "ok":
    st.error(
        f"⚠️ API indisponível em `{client.base_url}`. "
        "Verifique se a FastAPI está rodando (`python -m api.main`) "
        "e ajuste a URL na barra lateral.",
        icon="🚨",
    )
    st.stop()

col_h1, col_h2, col_h3 = st.columns(3)
col_h1.success(f"✅ API v{health.get('versao', '?')} — {health.get('ambiente', '')}")
col_h2.info(f"🗄️ DB: {'✅ OK' if health.get('db_conectado') else '❌ Offline'}")
col_h3.info(f"⚡ Cache: {'✅ Redis' if health.get('cache_conectado') else '⚠️ Sem cache'}")

st.divider()

# ---------------------------------------------------------------------------
# KPIs Nacionais
# ---------------------------------------------------------------------------

st.markdown("### 📊 Visão Geral Nacional · 2024")

@st.cache_data(ttl=3600, show_spinner=False)
def _kpis_nacionais(api_url: str):
    c = APIClient(api_url)
    # Produção agregada
    prod = c.get("/producao", params={"ano_inicio": 2024, "ano_fim": 2024, "por_pagina": 1})
    total_proc = prod.get("meta", {}).get("total", 0)

    # Anomalias recentes
    anom = c.get("/indicadores/anomalias", params={"sigma": 2.0, "por_pagina": 1})
    total_anomalias = anom.get("meta", {}).get("total", 0)

    # Municípios com dados
    rank = c.get("/ranking/nacional", params={"ano": 2024, "top": 1})
    municipios = rank.get("meta", {}).get("total", 0)

    return {
        "total_proc": total_proc,
        "total_anomalias": total_anomalias,
        "municipios": municipios,
    }

try:
    kpis = _kpis_nacionais(st.session_state.get("api_url", "http://localhost:8000"))

    k1, k2, k3, k4 = st.columns(4)

    with k1:
        st.markdown(
            f"""<div class="metric-card">
            <div class="metric-title">Competências com dados</div>
            <div class="metric-value">{kpis['total_proc']:,}</div>
            <div class="metric-sub">registros municipio/mês · 2024</div>
            </div>""",
            unsafe_allow_html=True,
        )
    with k2:
        st.markdown(
            f"""<div class="metric-card">
            <div class="metric-title">Municípios ranqueados</div>
            <div class="metric-value">{kpis['municipios']:,}</div>
            <div class="metric-sub">com dados em 2024</div>
            </div>""",
            unsafe_allow_html=True,
        )
    with k3:
        st.markdown(
            f"""<div class="metric-card">
            <div class="metric-title">Alertas de anomalia</div>
            <div class="metric-value" style="color:#E53E3E">{kpis['total_anomalias']:,}</div>
            <div class="metric-sub">Z-score ≥ 2σ · todos os períodos</div>
            </div>""",
            unsafe_allow_html=True,
        )
    with k4:
        st.markdown(
            f"""<div class="metric-card">
            <div class="metric-title">Estados cobertos</div>
            <div class="metric-value">27</div>
            <div class="metric-sub">cobertura nacional · 2020–2024</div>
            </div>""",
            unsafe_allow_html=True,
        )

except APIError as e:
    st.warning(f"Não foi possível carregar KPIs nacionais: {e}")

# ---------------------------------------------------------------------------
# Tabela de info da API
# ---------------------------------------------------------------------------

st.divider()

info_col, guide_col = st.columns([1, 1])

with info_col:
    st.markdown("#### ℹ️ Sobre os dados")
    st.markdown(
        """
        | Atributo | Valor |
        |---|---|
        | **Fonte** | SIA/PA — DataSUS |
        | **Período** | 2020 – 2024 |
        | **Granularidade** | Município × mês |
        | **Procedimentos** | ~150M registros brutos |
        | **Atualização** | Semanal (seg. 04h BRT) |
        | **Pipeline** | PySUS → dbt → Supabase |
        """
    )

with guide_col:
    st.markdown("#### 🧭 Como explorar")
    st.markdown(
        """
        1. **🗺️ Mapa** — compare municípios de uma UF num coroplético  
        2. **📈 Série Temporal** — veja a evolução mensal de um município  
        3. **⚠️ Anomalias** — detecte picos e quedas fora do padrão histórico  
        4. **🏆 Ranking** — ranqueie municípios por score de acesso  
        5. **🦠 Epidemiologia** — perfil de diagnósticos por capítulo CID-10  
        """
    )

st.caption("saude-publica-br · MIT License · github.com/saude-publica-br")
