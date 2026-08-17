# Publicar o Saúde em Dado

O projeto roda **sem servidor para administrar**. Não há Docker, nginx, VPS nem
API própria: o site é estático e os dados vêm do PostgREST do Supabase.

> Versões anteriores deste guia descreviam um provisionamento com Hetzner,
> Docker Compose, Redis, Prometheus e Grafana. Essa arquitetura foi aposentada e
> está em [`archive/`](archive/README.md) — seguir aquele roteiro hoje monta uma
> infraestrutura que não serve o site.

## O que compõe a publicação

| camada | onde vive | como publica |
|---|---|---|
| site | `site/` (Next.js, export estático) | `deploy-site.yml` → GitHub Pages |
| dados | Supabase (PostgREST) | `scripts/` escrevem os marts |
| servidor MCP | `mcp_server/` | `publish-mcp.yml` → PyPI + registry |

Custo de infraestrutura: zero, dentro dos planos gratuitos.

---

## 1. Supabase

1. Criar projeto em [app.supabase.com](https://app.supabase.com) — região **South America (São Paulo)**.
2. Em **Settings → API**, copiar:
   - `Project URL` → `SUPABASE_URL`
   - `anon public` → `SUPABASE_ANON_KEY` (**pública por design**, vai para o browser)
   - `service_role` → `SUPABASE_SERVICE_ROLE_KEY` (**nunca commitar, nunca expor**)
3. Aplicar as migrations de `migrations/` pelo SQL Editor.

A `anon` só lê. A escrita nos marts é feita com a `service_role`, usada apenas
pelos pipelines — ver `scripts/_supabase_key.py`.

## 2. Domínio no GitHub Pages

Em **Settings → Pages**, definir a origem como **GitHub Actions**.

No registrador do domínio:

```
A     @     185.199.108.153
A     @     185.199.109.153
A     @     185.199.110.153
A     @     185.199.111.153
CNAME www   pedropaulofernandes88-stack.github.io
```

O arquivo `CNAME` é gerado no build (`deploy-site.yml`), não versionado.

> O registro `www` precisa apontar para o host `github.io` — não para o apex.
> Sem isso o certificado não cobre `www.saudeemdado.com`.

## 3. Carregar os dados

Localmente, com Python 3.11+:

```bash
pip install -r requirements.txt
cp .env.example .env      # preencher SUPABASE_SERVICE_ROLE_KEY
python scripts/pipeline_v2.py
```

O pipeline baixa os microdados do DataSUS, agrega em DuckDB e publica os marts
no Supabase. Detalhes de método em [`/metodologia/`](https://saudeemdado.com/metodologia/).

## 4. Publicar o site

Qualquer push em `main` que toque `site/**` dispara `deploy-site.yml`. Não há
passo manual.

Para conferir localmente antes:

```bash
cd site
npm ci
npm run build      # gera site/out
npm test           # 23 testes, runner nativo do Node
```

## 5. Publicar o servidor MCP

Uma tag `mcp-v*` dispara `publish-mcp.yml`, que publica no PyPI (trusted
publishing via OIDC, sem segredo) e no registry oficial de MCP.

```bash
git tag -a mcp-v0.4.0 -m "..." && git push origin mcp-v0.4.0
```

> Versão publicada no PyPI **não pode ser reenviada**. Antes de taguear:
> `mcp_server/pyproject.toml` e `mcp_server/server.json` precisam ter a mesma
> versão, e o marcador `mcp-name:` deve estar no README do pacote.

---

## Segredos do repositório

Configurados em **Settings → Secrets and variables → Actions**:

| segredo | usado por |
|---|---|
| `SUPABASE_HOST`, `SUPABASE_PASSWORD` | `dbt-docs.yml` |
| `ALERTAS_ENVIO_SECRET` | `boletim-semanal.yml` |

O PyPI não precisa de segredo: usa OIDC.

## Automações agendadas

| workflow | quando |
|---|---|
| `boletim-semanal.yml` | segundas, 12h UTC |
| `validate-data.yml` | agendado |
| `supabase-keepalive.yml` | agendado (evita pausa do projeto free) |
