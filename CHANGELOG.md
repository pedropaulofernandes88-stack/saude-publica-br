# Changelog — Saúde Pública BR

Todas as mudanças notáveis deste projeto são documentadas aqui.

Formato baseado em [Keep a Changelog](https://keepachangelog.com/pt-BR/1.0.0/).
Versionamento semântico conforme [SemVer](https://semver.org/lang/pt-BR/).

---

## [0.7.0] — 2024-01-15 — API Pública Estável v1.0 (Fase 12)

### ✨ Adicionado

#### API Pública `/v1`
- **Router `/v1`** com prefixo versionado e documentação OpenAPI enriquecida
- **`/v1/status`** — endpoint público sem autenticação (health check da API pública)
- **`/v1/me`** — informações da API key atual (tier, uso, limites)
- **`/v1/sistemas`** — lista dos sistemas DataSUS disponíveis com descrições
- **`/v1/producao`** — dados do SIA (Sistema de Informações Ambulatoriais)
  - `GET /v1/producao` — lista procedimentos com filtros (uf, ano, mes, tipo, procedimento)
  - `GET /v1/producao/resumo` — resumo agregado por UF e período
- **`/v1/mortalidade`** — dados do SIM (Sistema de Informações sobre Mortalidade)
  - `GET /v1/mortalidade` — lista óbitos com filtros (uf, ano, cid_capitulo, faixa_etaria)
  - `GET /v1/mortalidade/causas-principais` — top causas de mortalidade por UF/período
  - `GET /v1/mortalidade/tendencia` — série temporal anual de óbitos
- **`/v1/capacidade`** — dados do CNES (Cadastro Nacional de Estabelecimentos)
  - `GET /v1/capacidade/estabelecimentos` — lista estabelecimentos (403 para municipal + free)
  - `GET /v1/capacidade/resumo` — resumo de capacidade por UF
  - `GET /v1/capacidade/leitos-uti` — disponibilidade de leitos de UTI
- **`/v1/doencas`** — dados do SINAN (Sistema de Agravos de Notificação)
  - `GET /v1/doencas` — lista notificações com filtros (uf, ano, agravo, alerta)
  - `GET /v1/doencas/surtos` — surtos epidemiológicos detectados
  - `GET /v1/doencas/agravos` — lista de agravos notificáveis disponíveis
  - `GET /v1/doencas/serie` — série temporal de um agravo específico

#### Autenticação e Rate Limiting
- **Migration V015** — tabela `api_keys` com campo `tier` (free/pro/enterprise), `api_usage_log` particionada por mês, funções SECURITY DEFINER `criar_api_key()` e `verificar_api_key()`
- **`api/middleware/api_key.py`** — middleware `get_api_key()` como dependência FastAPI; logging de uso fire-and-forget (não bloqueia resposta)
- **Rate limiting por tier**:
  - `free`: 60 req/min, histórico 12 meses, granularidade UF
  - `pro`: 600 req/min, histórico completo, granularidade UF + Municipal
  - `enterprise`: 6000 req/min, histórico completo, granularidade UF + Municipal
- **Controle de acesso por tier**: endpoints de granularidade municipal retornam `403 Forbidden` para tier `free`

#### SDKs Cliente
- **SDK Python** (`sdk/python/saude_publica_br/`) — cliente httpx com suporte sync e async, retry com exponential backoff, dataclass models tipados, 4 sub-clientes (Producao, Mortalidade, Capacidade, Doencas)
- **SDK TypeScript** (`sdk/javascript/src/index.ts`) — cliente nativo `fetch` (sem dependências externas), tipagem TypeScript completa, retry automático, AbortController para timeout, classes de erro (`SaudePublicaError`, `RateLimitError`, `AuthError`, `ForbiddenError`)

#### Schemas Pydantic v2
- **`api/v1/schema.py`** — todos os modelos de resposta com `model_config`, exemplos embutidos e validação estrita: `ProducaoItem`, `MortalidadeItem`, `EstabelecimentoItem`, `DoencaItem`, `SurtoItem`, `PaginatedResponse[T]`, `ApiKeyMeResponse`, `StatusResponse`, `SistemasResponse`

#### Documentação OpenAPI
- Descrição rica em Markdown com tabelas de cobertura e rate limiting
- Exemplos de response por endpoint
- Esquemas de erro padronizados (401, 403, 422, 429, 500) em todos os endpoints
- Tags de agrupamento com descrições detalhadas
- Parâmetros `swagger_ui_parameters` para melhor UX no Swagger UI

### 🔄 Alterado
- **`api/main.py`** atualizado para v0.7.0 com:
  - Inclusão do router `/v1`
  - Header `X-API-Version` em todas as respostas
  - Metadados OpenAPI enriquecidos (contact, license, tags)
  - Endpoint `/` inclui links para SDKs, portal dev e status page
  - Endpoint `/health` retorna versão do PostgreSQL
  - `fases_completas` atualizado para incluir Fase 12 (1–12)

### 📦 Infraestrutura
- Headers de resposta padronizados: `X-Process-Time`, `X-API-Version`, `X-RateLimit-Limit`, `X-RateLimit-Remaining`, `Retry-After`

---

## [0.6.0] — 2024-01-08 — Portal Público e Autenticação (Fase 11)

### ✨ Adicionado
- **Migration V014** — tabelas `users`, `dashboards`, `exports_log`
- **JWT authentication** — registro, login, refresh token
- **`api/routers/auth.py`** — endpoints `/auth/register`, `/auth/login`, `/auth/refresh`, `/auth/me`
- **`api/routers/dashboards.py`** — CRUD de dashboards customizáveis
- **`api/routers/exports.py`** — exportação em CSV, Excel (XLSX) e JSON
- **Frontend Next.js** — páginas de login, registro e portal público
- **Dashboard builder** — interface de criação de visualizações interativas

---

## [0.5.0] — 2024-01-01 — Cobertura Nacional (Fase 10)

### ✨ Adicionado
- **Migration V013** — particionamento PostgreSQL por `uf_sigla` (27 estados)
- **`ingestion/ingest_all_states.py`** — ingestão paralela dos 27 estados com ThreadPoolExecutor
- **`flows/weekly_ingest_nacional.py`** — Prefect flow para ingestão semanal nacional
- **4 dbt marts nacionais** — producao_nacional, mortalidade_nacional, capacidade_nacional, doencas_nacional
- **`api/routers/nacional.py`** — endpoints de visão nacional agregada

---

## [0.4.0] — 2023-12-20 — Infraestrutura de Produção (Fase 8)

### ✨ Adicionado
- **nginx** com SSL (Let's Encrypt), rate limiting e reverse proxy
- **Prometheus** + **Grafana** — métricas e dashboards de observabilidade
- **`prometheus-fastapi-instrumentator`** — métricas automáticas de latência e throughput
- **docker-compose.yml** completo com todos os serviços (API, frontend, nginx, Prometheus, Grafana)

---

## [0.3.0] — 2023-12-15 — SINAN + CNES (Fases 7A e 7B)

### ✨ Adicionado
- **Migration V011** — tabela `sinan_notificacoes` (doenças notificáveis)
- **Migration V012** — tabelas CNES (`cnes_estabelecimentos`, `cnes_leitos`)
- **`ingestion/ingest_sinan.py`** e **`ingestion/ingest_cnes.py`** — ingestores PySUS
- **dbt models** — staging + mart para doenças notificáveis e capacidade hospitalar
- **`api/routers/sinan.py`** e **`api/routers/cnes.py`** — endpoints epidemiológicos

---

## [0.2.0] — 2023-12-10 — CI/CD e Frontend (Fases 6D e 6E)

### ✨ Adicionado
- **Next.js 14 frontend** — scaffold, layout e API client
- **GitHub Actions** — pipelines de CI para API (Python) e frontend (TypeScript)
- **dbt-docs workflow** — geração automática de documentação dbt
- **docker-compose.yml** com serviços api e frontend

---

## [0.1.0] — 2023-12-01 — MVP (Fases 1–6C)

### ✨ Adicionado
- Pipeline de ingestão DataSUS via PySUS (SIA, SIM, SIH)
- PostgreSQL com migrations Flyway (V001–V010)
- FastAPI com routers de produção, mortalidade e capacidade
- dbt models — staging, intermediate, marts
- Prefect flows — ingestão e transformação semanais
- Análise exploratória em Jupyter Notebook
- README orientado ao público externo

---

[0.7.0]: https://github.com/saude-publica-br/api/compare/v0.6.0...v0.7.0
[0.6.0]: https://github.com/saude-publica-br/api/compare/v0.5.0...v0.6.0
[0.5.0]: https://github.com/saude-publica-br/api/compare/v0.4.0...v0.5.0
[0.4.0]: https://github.com/saude-publica-br/api/compare/v0.3.0...v0.4.0
[0.3.0]: https://github.com/saude-publica-br/api/compare/v0.2.0...v0.3.0
[0.2.0]: https://github.com/saude-publica-br/api/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/saude-publica-br/api/releases/tag/v0.1.0
