"""
Home.py — Página inicial do saude-publica-br
O Our World in Data do SUS 🇧🇷
"""
import streamlit as st
from datetime import datetime
from dashboard.api_client import APIClient, APIError, get_health

# ── Configuração da página ──────────────────────────────────────────────────
st.set_page_config(
    page_title="Saúde Pública BR",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={
        "Get Help": "https://github.com/seu-usuario/saude-publica-br",
        "Report a bug": "https://github.com/seu-usuario/saude-publica-br/issues",
        "About": "O Our World in Data do SUS — dados públicos de saúde do Brasil",
    },
)

# ── Sidebar ─────────────────────────────────────────────────────────────────
with st.sidebar:
    st.image("https://upload.wikimedia.org/wikipedia/commons/thumb/0/05/Flag_of_Brazil.svg/320px-Flag_of_Brazil.svg.png", width=80)
    st.markdown("## saude-publica-br")
    st.markdown("O Our World in Data do SUS 🇧🇷")
    st.divider()

    api_url = st.text_input(
        "URL da API",
        value="http://localhost:8000",
        help="Endereço da API FastAPI",
    )
    st.session_state["api_url"] = api_url

    st.divider()
    st.markdown("**Navegação**")
    st.page_link("pages/1_Mapa.py",          label="🗺️  Mapa de Produção")
    st.page_link("pages/2_Serie_Temporal.py", label="📈  Série Temporal")
    st.page_link("pages/3_Anomalias.py",      label="⚡  Anomalias")
    st.page_link("pages/4_Ranking.py",        label="🏆  Ranking")
    st.page_link("pages/5_Epidemiologia.py",  label="🦠  Epidemiologia")

# ── Header ──────────────────────────────────────────────────────────────────
st.title("🏥 Saúde Pública BR")
st.markdown(
    "**O Our World in Data do SUS** — transparência e análise de dados públicos de saúde do Brasil."
)
st.divider()

# ── Status da API ───────────────────────────────────────────────────────────
col_status, col_ts = st.columns([3, 1])
with col_status:
    st.subheader("Status do sistema")

with col_ts:
    st.caption(f"Atualizado: {datetime.now().strftime('%H:%M:%S')}")
    if st.button("🔄 Refresh"):
        st.cache_data.clear()
        st.rerun()

health_data = get_health(api_url)

if health_data:
    status = health_data.get("status", "unknown")
    if status == "ok":
        st.success(f"✅ API operacional — {api_url}")
    else:
        st.warning(f"⚠️ API respondeu com status: {status}")

    # Métricas de saúde
    c1, c2, c3, c4 = st.columns(4)
    db_ok    = health_data.get("db_conectado", False)
    redis_ok = health_data.get("cache_conectado", False)
    versao   = health_data.get("versao", "—")
    ambiente = health_data.get("ambiente", "—")

    with c1:
        st.metric("Banco de Dados", "✅ OK" if db_ok    else "❌ OFF", delta=None)
    with c2:
        st.metric("Cache Redis",    "✅ OK" if redis_ok else "⚠️ OFF", delta=None)
    with c3:
        st.metric("Versão",         versao,   delta=None)
    with c4:
        st.metric("Ambiente",       ambiente, delta=None)
else:
    st.error("❌ API não acessível. Verifique se está rodando: `make api`")
    with st.expander("Como iniciar a API?"):
        st.code("""# Opção 1 — Makefile
make api

# Opção 2 — Direto
uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload

# Opção 3 — Setup completo pela primeira vez
python bootstrap.py""", language="bash")

st.divider()

# ── Páginas disponíveis ─────────────────────────────────────────────────────
st.subheader("📊 Análises disponíveis")

pages = [
    ("🗺️", "Mapa de Produção",  "pages/1_Mapa.py",          "Visualização geoespacial da produção ambulatorial por município. Choropleth interativo com filtros por UF, ano e mês."),
    ("📈", "Série Temporal",    "pages/2_Serie_Temporal.py", "Evolução mensal de procedimentos e aprovações. Identifique tendências e variação mês a mês."),
    ("⚡", "Anomalias",         "pages/3_Anomalias.py",      "Detecção automática via Z-score. Configure o limiar de sensibilidade e veja quais municípios estão fora do padrão."),
    ("🏆", "Ranking",           "pages/4_Ranking.py",        "Ranking de municípios por taxa de procedimentos e aprovação — por estado ou nacional."),
    ("🦠", "Epidemiologia CID", "pages/5_Epidemiologia.py",  "Top causas de atendimento por capítulo CID-10. Perfil epidemiológico por UF e ano."),
]

cols = st.columns(len(pages))
for col, (icon, title, link, desc) in zip(cols, pages):
    with col:
        st.markdown(f"### {icon} {title}")
        st.markdown(f"<small>{desc}</small>", unsafe_allow_html=True)
        st.page_link(link, label=f"Abrir {title} →")

st.divider()

# ── Cobertura de dados ──────────────────────────────────────────────────────
st.subheader("📦 Cobertura dos dados")

col_l, col_r = st.columns(2)

with col_l:
    st.markdown("""
**Fontes**
- 🏥 SIA/PA — Produção Ambulatorial (DataSUS)
- 🗺️ IBGE — Municípios e populações
- 📋 SIGTAP — Tabela de procedimentos
- 🔬 CID-10 — Classificação de doenças
""")

with col_r:
    st.markdown("""
**Período & Escopo**
- 📅 2020 – 2024
- 🇧🇷 27 estados + DF (cobertura nacional)
- 🏙️ ~5.570 municípios
- 🔄 Atualização mensal automática
""")

st.divider()

# ── Rodapé ──────────────────────────────────────────────────────────────────
st.markdown(
    "<center><small>Dados públicos do DataSUS/DATASUS | "
    "Fonte: Ministério da Saúde | "
    "Não substitui análise epidemiológica profissional</small></center>",
    unsafe_allow_html=True,
)
