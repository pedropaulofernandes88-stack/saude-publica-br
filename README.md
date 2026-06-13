<div align="center">

# 🏥 saude-publica-br

**Dados abertos do SUS transformados em inteligência epidemiológica acessível**

Mortalidade no Brasil (SIM/DataSUS) — 27 estados, 5.570+ municípios,
**13+ milhões de óbitos (2015–2024)** — com taxas padronizadas por idade,
IC95%, excesso de mortalidade, mapa municipal e API pública gratuita.

🌐 **[saudeemdado.com](https://saudeemdado.com)**

[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](https://opensource.org/licenses/MIT)
[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://www.python.org/)
[![Custo](https://img.shields.io/badge/Custo-R%24%200%2Fm%C3%AAs-success.svg)](PUBLICACAO_CUSTO_ZERO.md)

</div>

---

## O que é isso?

Os dados do SUS são públicos, mas **inacessíveis na prática**: arquivos
fragmentados, formatos proprietários, sem padronização. Pesquisadores perdem
semanas para obter um indicador simples.

**saude-publica-br** automatiza o processo — coleta → normalização →
indicadores → API → visualização — e publica o resultado **a custo zero**,
para todo o público de pesquisa.

## 🚀 Acesso imediato (sem instalar nada)

**API REST pública** (PostgREST/Supabase):

```bash
URL="https://zekjhmxjamatlxpkykde.supabase.co"
KEY="<chave pública de leitura — veja .env.example>"

# Série mensal de óbitos no Brasil (todas as causas)
curl "$URL/rest/v1/mart_mortalidade_uf_mes?select=mes_competencia,uf_sigla,obitos&capitulo_cid=eq.TOTAL&sexo=eq.TOTAL&faixa_etaria=eq.TOTAL" \
  -H "apikey: $KEY"

# Municípios de MG com maior taxa de mortalidade em 2023 (pop ≥ 50 mil)
curl "$URL/rest/v1/mart_mortalidade_municipio?uf_sigla=eq.MG&ano=eq.2023&capitulo_cid=eq.TOTAL&sexo=eq.TOTAL&populacao=gte.50000&order=taxa_obitos_100k.desc&limit=20" \
  -H "apikey: $KEY"
```

Guia completo, tabelas e exemplos: **[PUBLICACAO_CUSTO_ZERO.md](PUBLICACAO_CUSTO_ZERO.md)**

**Site oficial (Next.js)**: em [`site/`](site/) — home, painel navegável com
filtros (UF, ano, causa CID-10, sexo), ranking de municípios com exportação
CSV, página de dados/API e metodologia completa. Export 100% estático:

```bash
cd site && npm install && npm run build   # gera site/out/ (deploy automático no GitHub Pages)
```

Páginas: painel com filtros, **mapa coroplético municipal**, **tendências e
excesso de mortalidade**, **boletim municipal imprimível** (`/boletim/?m=<cod>`),
dados & API, metodologia e sobre. Dados de navegação comum servidos como JSON
estático gerado no build (egress zero no banco).

**Para pesquisadores**:
- 🐍 Pacote Python [`clients/python`](clients/python/) — `sd.municipios(uf="MG", ano=2023, as_df=True)`
- 🤖 Servidor MCP [`mcp_server/server.py`](mcp_server/server.py) — consulte o
  dataset por assistentes de IA (Claude Desktop/Code) em linguagem natural

**Dashboard alternativo (Streamlit)**: `streamlit run dashboard_publico/app.py`
(ou publique grátis no [Streamlit Community Cloud](https://share.streamlit.io)).

**Keep-alive**: o free tier do Supabase pausa após 7 dias sem requisições.
O workflow [.github/workflows/supabase-keepalive.yml](.github/workflows/supabase-keepalive.yml)
faz uma consulta a cada ≤6 dias (e há um script equivalente para o Agendador
de Tarefas do Windows em [scripts/supabase_keepalive.ps1](scripts/supabase_keepalive.ps1)).

## 📊 Dados publicados

| Conjunto | Fonte | Cobertura |
|----------|-------|-----------|
| **Mortalidade** por município, ano, CID-10 e sexo + **IC95%** e **taxa padronizada por idade** | SIM/DataSUS | 2015–2024, nacional |
| **Excesso de mortalidade** (observado × esperado, baseline 2015–2019) | derivado | 2020+, UF e Brasil |
| **Dengue**: casos prováveis, graves, óbitos e incidência por município × semana epidemiológica | SINAN/DataSUS | 2015–2024, nacional |
| **Internações SUS**: volume, permanência média, mortalidade hospitalar e custo por município × CID-10 | SIH/DataSUS | 2022–2024, nacional |
| Municípios, população total e por faixa etária | IBGE | Censo 2022 + Estimativas |
| Descrições CID-10 (capítulos e categorias) | DATASUS | — |

Metodologia completa (padronização direta com padrão Brasil/Censo 2022, IC
gamma/Poisson exato, redistribuição de idade ignorada, grão histórico,
limitações declaradas): [saudeemdado.com/metodologia](https://saudeemdado.com/metodologia/).
Validação automática contínua: [.github/workflows/validate-data.yml](.github/workflows/validate-data.yml).

> Detalhe demográfico completo (capítulo × sexo × faixa) a partir de 2022;
> 2015–2021 publica totais e marginais. 2024 é preliminar.

## 🔁 Reprodutibilidade

Todo o dataset é gerado por um único script auditável, a partir de fontes
100% abertas:

```bash
pip install duckdb pandas pyarrow requests
python scripts/pipeline_custo_zero.py --anos 2022 2023 2024
```

O script baixa os microdados nacionais do
[OpenDataSUS](https://opendatasus.saude.gov.br/dataset/sim) (~1,5 GB), agrega
4,4M+ registros com DuckDB em segundos e publica apenas os marts compactos
(~150 MB) no Postgres.

## Arquitetura de publicação (R$ 0/mês)

```
OpenDataSUS (SIM, CSV)   IBGE (localidades + SIDRA)
        └──────────┬──────────┘
                   ▼
     pipeline_custo_zero.py  (local: DuckDB)
                   │
                   ▼
     Supabase free tier (Postgres + PostgREST)
        ├── API REST pública (leitura, RLS)
        └── Dashboard Streamlit (Community Cloud)
```

## 🏗️ Modo completo (self-hosted)

O repositório também contém a plataforma completa para quem quiser hospedar
com mais sistemas (SIA, SIH, SINAN, CNES), API FastAPI própria, dbt,
orquestração Prefect e observabilidade:

- `api/` — FastAPI REST (producao, internacoes, mortalidade, epidemiologia…)
- `dbt/` — staging → intermediate → marts
- `ingestion/` — ingestão PySUS por estado/sistema/ano
- `dashboard/` — Streamlit multi-página
- `frontend/` — Next.js 14 (esqueleto)
- `docker-compose.yml`, `nginx/`, `monitoring/` — stack de produção

Veja [SETUP.md](SETUP.md) e [LAUNCH.md](LAUNCH.md) (requer servidor pago,
~€4–30/mês). O caminho recomendado e mantido é o de custo zero.

## Roadmap

- [x] Mortalidade nacional 2015–2024 (SIM) com taxa padronizada, IC95% e excesso
- [x] **Dengue** (SINAN) 2015–2024 — incidência, gravidade e sazonalidade
- [x] **Internações** (SIH) 2022–2024 — permanência, custo e mortalidade hospitalar
- [x] Pacote Python, servidor MCP e boletim municipal
- [ ] SIH anos anteriores (2015–2021) via GitHub Actions
- [ ] SINAN outros agravos (chikungunya, zika, leishmaniose)
- [ ] CNES (estabelecimentos e leitos) e SINASC (nascidos vivos)
- [ ] Mortalidade infantil e materna (indicadores derivados)

## Contribuindo

Contribuições são bem-vindas — leia [CONTRIBUTING.md](CONTRIBUTING.md).
Áreas prioritárias: novos indicadores, validação epidemiológica, documentação
e tutoriais de uso da API para pesquisadores.

## Licença

Código: MIT. Dados originais: DATASUS/Ministério da Saúde e IBGE — públicos;
cite as fontes em trabalhos acadêmicos.
