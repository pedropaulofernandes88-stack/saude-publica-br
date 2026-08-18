# Changelog — Saúde Pública BR

Todas as mudanças notáveis deste projeto são documentadas aqui.

Formato baseado em [Keep a Changelog](https://keepachangelog.com/pt-BR/1.0.0/).
Versionamento semântico conforme [SemVer](https://semver.org/lang/pt-BR/).

---

## [3.3.0] — 2026-08-18 — Legibilidade, acessibilidade e uma stack a menos

> Nenhum número publicado mudou de valor: os marts, as colunas e os endpoints
> continuam idênticos. O que mudou foi quem consegue ler, e quanta coisa morta
> havia em volta. O gatilho foi uma auditoria externa cujo achado mais grave —
> credenciais vazadas em `deploy/.env.production` — era falso positivo: o
> arquivo só tinha placeholders. Os achados restantes eram reais e viraram
> esta versão.

### Adicionado

- **Sistemas de código documentados em `/dados/`.** Cada coluna de código passa a
  declarar o sistema que segue, com o URI canônico da RNDS: IBGE
  (`BRDivisaoGeograficaBrasil`), CID-10 (`BRCID10`), CNES e o
  `administrative-gender` do HL7. Registra também que `municipio_cod` já está nos
  mesmos 6 dígitos que a RNDS adota — junta sem conversão — enquanto `uf_sigla` é
  sigla e não código.
- **Valores sentinela em tabela própria.** `TOTAL`, `IGN`/`I`, `ND` e os
  agregados `<UF>0000` deixam de estar espalhados em prosa.
- **Equivalente textual em todos os gráficos.** Os cinco tipos ganham
  `role="img"` com nome acessível gerado e uma tabela de dados em `<details>`,
  com `caption` e `th[scope]`.
- **Metodologia navegável.** As 22 seções ganham âncora, sumário e link
  permanente derivado do título — renumerar não quebra link de terceiro.
- **`SECURITY.md`**, escrito sobre o falso positivo que abriu o ciclo: diz o que
  *não* é vazamento aqui antes de listar o que é.
- **Templates de issue e de PR**, incluindo um para "um número não bate" com as
  três causas que respondem pela maioria das divergências.
- **`.mailmap`**, unificando as duas identidades de autor.

### Alterado

- **Identidade visual "papel científico"** — neutro quente, verde-petroleo e
  cinco cores de região validadas para daltonismo. As cores de dado passam a ter
  um módulo só (`site/lib/tokens.ts`), porque o Recharts recebe cor por prop.
- **Contraste AA e escala tipográfica** como tokens, com `line-height` por passo.
- **Navegação mobile de verdade** — botão de 44px com `aria-expanded`, painel
  agrupado, fechamento por Escape, clique fora e navegação.
- **Densidade cortada em todas as rotas**: rankings longos passam a exibir um
  recorte com botão de expansão, mantendo a tabela inteira no DOM para busca e
  leitor de tela.
- **`metadata` própria em doze rotas**, cada uma com seu `canonical`.
- **Servidor MCP migrado para o SDK 2.x** (`FastMCP` → `MCPServer`), publicado
  no PyPI como `saudeemdado-mcp` 0.4.0.
- **CI passa a rodar em Node 24** e a executar os testes da raiz, que antes não
  rodavam em lugar nenhum.

### Corrigido

- **Códigos `<UF>0000` eram contados como município** no KPI do painel, inflando
  o total. A regra de classificação passa a ter um módulo testado
  (`site/lib/municipios.ts`) com teste de invariante contra os 5.571 do IBGE.
- **Meses de registro parcial pareciam queda real** nas séries. A linha agora se
  divide em trecho consolidado e trecho parcial, compartilhando o mês de junção.
- **A regra de completude vivia em dois lugares** — boletim e gráficos — que
  concordavam até deixarem de concordar. Passou a ter um lugar só
  (`site/lib/completude.ts`).
- **O pino do `mcp` vivia em três arquivos** e a migração atualizou um; o CI
  quebrou por `ImportError`.
- **`canonical` apontando para `/`** em três páginas, que se declaravam
  duplicatas da home para os buscadores.
- **Rolagem horizontal no celular** e versão, licença, marca e contagens
  divergentes entre JSON-LD, prosa e metadados.

### Removido

- **A primeira arquitetura inteira foi para `archive/`**: API FastAPI + Redis,
  front na Vercel, Docker Compose, nginx, Prometheus/Grafana e os painéis
  Streamlit. Nada disso estava implantado — o site é estático no GitHub Pages e a
  API é o PostgREST do Supabase. `supabase/` e `flows/` ficaram na raiz por
  estarem vivos.
- **Quatro arquivos saíram da raiz**: `railway.toml` e `vercel.json` (apontavam
  para dentro de `archive/`), `base.md` (1.660 linhas de documento histórico) e
  `PUBLICACAO_CUSTO_ZERO.md` (duplicava README, `/dados/` e `LAUNCH.md`).

### Segurança

- `.gitignore` passa a cobrir `.env.*`, reabrindo só o sufixo `.example` — um
  arquivo de ambiente preenchido no futuro fica invisível ao `git add`.
- `deploy/setup-server.sh` reusava `API_SECRET_KEY` como `JWT_SECRET_KEY`: o
  `sed` com `/g` substituía as duas ocorrências pelo mesmo valor. Corrigido com
  âncora no nome da variável.

---

## [3.2.0] — 2026-08-12 — Tipo de AIH, unidade da ANS e escrita fechada

> Três correções que mudam número publicado, e a régua que faltava para pegá-las
> antes da produção. Motivadas pela leitura de *Sistemas de Informação em Saúde no
> Brasil* (R. F. Saldanha, rfsaldanha.github.io/sis).

### Corrigido

- **SIH — AIH de continuação (IDENT=5) era contada como internação separada.** Uma
  internação que se prolonga emite várias AIHs; o mart tratava cada uma como um
  episódio. Efeito concentrado: capítulo V (transtornos mentais) 25,2% de continuação,
  permanência 14,71 → 11,92 dias; capítulo VI (sistema nervoso) 10,2%, 8,78 → 6,40
  dias; nos outros 17 capítulos, ≤ 1,8%. Novas colunas `aih_continuacao`,
  `aih_normal`, `dias_permanencia_normal`, `valor_normal`; `permanencia_media` e
  `custo_medio` passam a ser por episódio. HSMR e LOS passam a ser calculados só
  sobre AIH normal — o HSMR quase não se move (0,6479 → 0,6499 em 2024, 19 hospitais
  em 4.739 mudando de classificação). %ICSAP sobe 0,15pp.
- **ANS — `pct_saude_suplementar` afirmava proporção de pessoas.** O SIB conta
  vínculos e localiza pelo endereço do contrato, não da residência; a razão pode
  passar de 100, e passa (Belém/AL, 115,9 em 2021). Renomeada para
  `vinculos_plano_por_100_hab`, com flag `razao_implausivel`. Não muda nenhuma
  conclusão: os testes são de posto e o gradiente por porte fica igual.
- **Linhas órfãs.** Upsert nunca removia o que saía do cálculo; 1.830 linhas
  publicadas não correspondiam a nenhum cálculo vigente. Removidas, e os pipelines
  ganharam varredura com trava de segurança.
- **Windows.** Os pipelines morriam ao ter a saída redirecionada para arquivo (cp1252
  vs. UTF-8 nos logs).

### Segurança

- **`anon` podia escrever e apagar.** A chave pública tinha INSERT/UPDATE/DELETE em 18
  tabelas e TRUNCATE em outras 17 — qualquer pessoa com o repositório aberto podia
  sobrescrever ou zerar os dados publicados. Os pipelines passam a escrever com
  `service_role` (`SUPABASE_SERVICE_ROLE_KEY` no `.env`) e as migrations V022/V023
  revogam escrita de `anon` e `authenticated` em todo o schema, views inclusive.
  Leitura pública não muda.

### Adicionado

- Primeiros testes dos pipelines: 90 casos cobrindo a matemática de agregação, as
  faixas de LOS, a faixa etária, a lista ICSAP, a seleção de chave e a varredura de
  órfãs. Antes, nenhum teste tocava o código que produz os números publicados.
- `scripts/_metricas_aih.py` (regras compartilhadas, antes triplicadas),
  `scripts/_supabase_key.py`, `scripts/_varredura.py`, `scripts/_subir_mart.py`.
- MCP e client Python expõem as colunas por tipo de AIH; nova regra anti-alucinação
  proibindo chamar AIH de paciente.

### Mudado

- `data/marts/` deixa de ser versionado — é saída regenerável, e versioná-la fazia
  um commit de mudança de definição carregar dados da definição anterior.

---

## [3.1.0] — 2026-06-29 — Internações, agravos, fluxo e excesso corrigido

> Linha atual da plataforma (site estático + Supabase). As entradas de versão
> `0.x` abaixo são da arquitetura legada (backend FastAPI, descontinuada).

### ✨ Adicionado
- **Internações hospitalares (SIH/AIH 2022–2024)** por município e capítulo CID-10: permanência média, mortalidade intra-hospitalar e custo.
- **ICSAP — internações por condições sensíveis à atenção primária** (aproximação da Lista Brasileira, CID-3): proporção, **gasto potencialmente evitável** (estimativa) e **sinalização de outlier** (IC95% de Wilson).
- **Fluxo intermunicipal de pacientes** (residência → atendimento, SIH 2024) — inspirado no LabSUS.
- **Internações por agravo traçador** (CID-3): diabetes, AVC, IAM, insuficiência cardíaca, asma, DPOC, pneumonia, depressão, esquizofrenia, álcool/drogas, TCE.
- **Visão hospitalar (CNES)**: agregados por estabelecimento (volume, permanência, mortalidade, custo, capítulo predominante).
- **Arquétipos de saúde municipal** (k-means) no boletim.
- Página Dados: **vigência por base**, **qualidade do registro** (% causas mal-definidas), licença **CC BY 4.0** para os agregados e bloco "Como citar".

### 🔧 Alterado
- **Excesso de mortalidade — método corrigido.** Baseline mudou de "média 2015–2019 × razão populacional" para **tendência linear por mês civil**, captando o envelhecimento. Brasil 2020–2021: 702.871 → **643.482**; "excesso persistente" de 2022–2023 encolhe; 2024 ~zero. **(altera números publicados)**
- Caveats epidemiológicos no ponto de uso: confundimento por cobertura SUS-only, mortalidade hospitalar bruta (case-mix), falácia ecológica.
- Malhas municipais auto-hospedadas (remove dependência instável do IBGE em runtime).

### 🔬 Robustez
- **Análise de sensibilidade do excesso** (variante padronizada por idade com a projeção IBGE 2018): documenta que ela subestima por problemas de denominador (overcount pré-Censo + descontinuidade de 2022); o método de tendência foi retido por ser imune ao denominador. Script e base reproduzíveis em `scripts/sensibilidade_excesso_idade.py`.

### Fontes e cobertura
- SIM 2015–2024 · SIH 2022–2024 · SINAN 2015–2024 · SINASC 2021–2023 · IBGE Censo 2022 e projeções.

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
