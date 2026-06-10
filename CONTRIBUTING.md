# Guia de Contribuição — saude-publica-br

Obrigado por querer contribuir! Este documento descreve como configurar o ambiente, as convenções do projeto e o fluxo de trabalho para enviar contribuições.

---

## Índice

1. [Código de Conduta](#código-de-conduta)
2. [Como posso contribuir?](#como-posso-contribuir)
3. [Pré-requisitos](#pré-requisitos)
4. [Configuração do ambiente local](#configuração-do-ambiente-local)
5. [Estrutura do projeto](#estrutura-do-projeto)
6. [Fluxo de trabalho](#fluxo-de-trabalho)
7. [Convenções de código](#convenções-de-código)
8. [Adicionando novos estados ou anos](#adicionando-novos-estados-ou-anos)
9. [Rodando os testes](#rodando-os-testes)
10. [Enviando um Pull Request](#enviando-um-pull-request)

---

## Código de Conduta

Este projeto adota o [Contributor Covenant v2.1](https://www.contributor-covenant.org/version/2/1/code_of_conduct/).
Em resumo: seja respeitoso, construtivo e inclusivo. Reporte comportamentos inadequados para `contato@saude-publica-br.dev`.

---

## Como posso contribuir?

- 🐛 **Reportar bugs** — abra uma [Issue](https://github.com/saude-publica-br/saude-publica-br/issues) com o label `bug`
- 💡 **Sugerir melhorias** — abra uma Issue com o label `enhancement`
- 📊 **Adicionar estados/anos** — veja a seção [Adicionando novos estados ou anos](#adicionando-novos-estados-ou-anos)
- 📖 **Melhorar documentação** — PRs de docs são sempre bem-vindos
- 🧪 **Escrever testes** — cobertura de testes é uma área prioritária
- 🌐 **Tradução** — ajude a traduzir a UI e a API para EN/ES

---

## Pré-requisitos

| Ferramenta | Versão mínima | Instalação |
|-----------|--------------|------------|
| Python | 3.11+ | [python.org](https://www.python.org/) |
| Docker | 24+ | [docs.docker.com](https://docs.docker.com/get-docker/) |
| Docker Compose | v2.20+ | incluído no Docker Desktop |
| Git | 2.40+ | [git-scm.com](https://git-scm.com/) |
| Node.js | 20+ | [nodejs.org](https://nodejs.org/) (apenas para frontend) |

---

## Configuração do ambiente local

### 1. Fork e clone

```bash
# Fork via GitHub UI, depois:
git clone https://github.com/SEU_USUARIO/saude-publica-br.git
cd saude-publica-br

# Adicione o remote upstream
git remote add upstream https://github.com/saude-publica-br/saude-publica-br.git
```

### 2. Configure as variáveis de ambiente

```bash
cp .env.example .env
```

Edite `.env` com suas configurações:

```bash
# Banco de dados (Supabase local via Docker ou Supabase Cloud)
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/saude_publica

# Redis
REDIS_URL=redis://localhost:6379/0

# Supabase (se usar cloud)
SUPABASE_URL=https://seu-projeto.supabase.co
SUPABASE_KEY=seu-anon-key

# Ambiente
ENV=development
DEBUG=1
LOG_LEVEL=DEBUG

# CORS (para desenvolvimento local)
CORS_ORIGINS=http://localhost:3000,http://localhost:8501
```

### 3. Instale as dependências Python

```bash
# Crie um virtualenv
python -m venv .venv
source .venv/bin/activate  # Linux/macOS
# ou .venv\Scripts\activate  # Windows

# Instale dependências
pip install -r requirements.txt
pip install -r requirements-dev.txt
```

> **`requirements-dev.txt`** inclui: `pytest`, `pytest-asyncio`, `httpx`, `ruff`, `mypy`, `pre-commit`

### 4. Configure os hooks de pré-commit

```bash
pre-commit install
```

Isso garante que lint e formatação rodem antes de cada commit.

### 5. Carregue os dados de demo

```bash
# Gera ~10k registros sintéticos (não requer acesso ao DataSUS)
python scripts/generate_demo_data.py

# Carrega no banco local (via Docker)
bash scripts/load_demo_data.sh
```

### 6. Suba a stack completa

```bash
docker compose up -d
```

Verifique que tudo está OK:

```bash
docker compose ps
curl http://localhost/api/health
```

Resposta esperada:
```json
{"versao": "0.4.0", "ambiente": "development", "db_conectado": true, "cache_conectado": true}
```

---

## Estrutura do projeto

```
saude-publica-br/
├── api/                    # FastAPI REST API
│   ├── routers/            # Um arquivo por domínio (producao, mortalidade, etc.)
│   ├── middleware/         # Prometheus metrics
│   ├── cache.py            # Integração Redis
│   ├── database.py         # Pool asyncpg
│   ├── schemas.py          # Modelos Pydantic
│   └── main.py             # App principal
├── dbt/                    # Transformações dbt-core
│   ├── models/
│   │   ├── staging/        # Normalização bruta → typed
│   │   ├── intermediate/   # Enriquecimento (join com IBGE, SIGTAP)
│   │   └── marts/          # Indicadores finais (produção, mortalidade, etc.)
│   ├── tests/              # Testes de dados dbt
│   └── profiles.yml
├── frontend/               # Next.js 14 App Router
│   ├── app/                # Rotas (page.tsx por página)
│   ├── components/         # Componentes reutilizáveis
│   └── lib/                # Clientes de API e utils
├── pipeline/               # Ingestão PySUS → Parquet
│   ├── ingest.py           # Ponto de entrada
│   └── loaders/            # Um módulo por sistema (sia, sim, sih, sinan, cnes)
├── prefect/                # Fluxos de orquestração
│   ├── weekly_pipeline.py
│   └── validation_flow.py
├── streamlit/              # Dashboard MVP
├── nginx/                  # Reverse proxy
├── monitoring/             # Prometheus + Grafana
├── scripts/                # Utilitários
├── docs/                   # Documentação e ADRs
│   └── architecture/
└── .github/workflows/      # CI/CD
```

---

## Fluxo de trabalho

### Convenções de branch

| Tipo | Formato | Exemplo |
|------|---------|---------|
| Feature | `feat/descricao-curta` | `feat/adicionar-estado-ba` |
| Bug fix | `fix/descricao-do-bug` | `fix/cache-miss-on-empty-result` |
| Docs | `docs/descricao` | `docs/adr-006-mlflow` |
| Refactor | `refactor/descricao` | `refactor/extract-query-builder` |
| Chore | `chore/descricao` | `chore/bump-fastapi-0116` |

### Convenções de commit (Conventional Commits)

```
<tipo>(<escopo>): <descrição curta em português ou inglês>

[corpo opcional]

[footer opcional: Closes #123]
```

**Tipos válidos:**

| Tipo | Quando usar |
|------|------------|
| `feat` | Nova funcionalidade |
| `fix` | Correção de bug |
| `docs` | Documentação |
| `refactor` | Refatoração sem mudança de comportamento |
| `test` | Adição ou correção de testes |
| `chore` | Manutenção, dependências |
| `perf` | Melhoria de performance |
| `ci` | Mudanças em CI/CD |

**Exemplos:**

```bash
git commit -m "feat(api): adicionar endpoint /doencas-notificaveis/tendencia"
git commit -m "fix(cache): corrigir TTL incorreto para dados de mortalidade"
git commit -m "docs: adicionar ADR-006 sobre uso do MLflow"
git commit -m "test(api): cobrir routers de internacoes com pytest-asyncio"
```

---

## Convenções de código

### Python (API e pipeline)

- Formatação: **ruff format** (substitui black)
- Lint: **ruff check** (substitui flake8 + isort)
- Type hints: obrigatório em funções públicas
- Docstrings: Google style para funções complexas

```bash
# Formatar
ruff format .

# Lint
ruff check .

# Type check
mypy api/ --ignore-missing-imports
```

### SQL / dbt

- Nomes de modelos: `snake_case`, prefixados por camada (`stg_`, `int_`, `mart_`)
- CTEs: uma por transformação, nomeadas descritivamente
- Sempre adicionar testes de `not_null` e `unique` nas chaves primárias dos marts
- Comentários em português (dados são contexto brasileiro)

```sql
-- Bom
with
producao_filtrada as (
    select ...
    from {{ ref('stg_sia_pa') }}
    where competencia_ano >= 2020
),

-- Use ref() sempre, nunca hardcode de schema
```

### TypeScript / Next.js

- Formatação: Prettier (config em `.prettierrc`)
- Lint: ESLint com config Next.js
- Componentes: functional components com TypeScript strict
- Sem `any` — use tipos precisos ou `unknown`

---

## Adicionando novos estados ou anos

O pipeline foi desenhado para ser extensível. Para adicionar, por exemplo, o estado da **Bahia (BA)** para o ano **2019**:

### 1. Ingestão

```bash
# Baixa e processa os dados do DataSUS
python -m pipeline.ingest --estados BA --anos 2019

# Verifica os arquivos Parquet gerados
ls data/parquet/BA/2019/
```

### 2. dbt

```bash
cd dbt

# Roda apenas os modelos afetados
dbt run --select tag:sia_pa+ --vars '{"estados": ["BA"], "anos": [2019]}'

# Executa os testes de qualidade
dbt test --select tag:sia_pa+
```

### 3. Validação com Great Expectations

```bash
python pipeline/validate.py --estado BA --ano 2019
```

### 4. Atualize a documentação

Se a cobertura geográfica do README mudou, atualize a tabela de fontes e o endpoint `/info` da API (`api/main.py`, campo `"abrangencia"`).

---

## Rodando os testes

### Testes de API (pytest + httpx)

```bash
# Todos os testes
pytest api/tests/ -v

# Com cobertura
pytest api/tests/ --cov=api --cov-report=html

# Apenas testes de um router
pytest api/tests/test_producao.py -v
```

### Testes dbt

```bash
cd dbt
dbt test                          # todos
dbt test --select mart_producao   # modelo específico
```

### Testes de integração (requer Docker)

```bash
docker compose -f docker-compose.test.yml up --abort-on-container-exit
```

### Pre-commit (roda automaticamente no commit)

```bash
pre-commit run --all-files
```

---

## Enviando um Pull Request

1. **Sincronize** com o upstream antes de começar:
   ```bash
   git fetch upstream
   git rebase upstream/main
   ```

2. **Crie a branch** seguindo as convenções acima

3. **Implemente** a mudança com testes adequados

4. **Verifique** que todos os checks passam localmente:
   ```bash
   pre-commit run --all-files
   pytest api/tests/ -v
   cd dbt && dbt test
   ```

5. **Abra o PR** para a branch `main` com:
   - Título seguindo Conventional Commits
   - Descrição clara do que foi feito e **por quê**
   - Screenshots/logs se aplicável
   - Referência a Issues relacionadas (`Closes #123`)

6. **Responda ao feedback** do code review com pontualidade

### Critérios para merge

- ✅ Todos os CI checks passando (lint, testes, build)
- ✅ Pelo menos 1 review de aprovação
- ✅ Sem conflitos com `main`
- ✅ Testes adicionados para novas funcionalidades
- ✅ Documentação atualizada se necessário

---

## Dúvidas?

Abra uma [Issue com label `question`](https://github.com/saude-publica-br/saude-publica-br/issues/new?labels=question) ou entre em contato: `contato@saude-publica-br.dev`
