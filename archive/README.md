# Arquivo — o que já rodou e não roda mais

Este diretório guarda a primeira arquitetura do projeto. **Nada aqui está
implantado**, nada aqui é executado por CI, e o site publicado não depende de
nenhuma linha deste conteúdo.

Está preservado porque documenta decisões reais e o porquê de terem sido
revertidas — não porque ainda sirva.

## O que roda hoje

| camada | onde |
|---|---|
| site | `site/` — Next.js exportado estático, GitHub Pages |
| API pública | PostgREST sobre Supabase (sem código próprio) |
| pipelines | `scripts/` — DuckDB local, publicando marts no Supabase |
| servidor MCP | `mcp_server/` — publicado no PyPI como `saudeemdado-mcp` |

## O que está aqui, e por que saiu

### `api/` — FastAPI + Redis

API própria com autenticação JWT, cache Redis e paginação. Substituída pelo
PostgREST do Supabase, que entrega o mesmo contrato REST sobre as mesmas tabelas
sem código para manter.

Evidência de que não está no ar: `https://saudeemdado.com/api/health` responde
404 (cai no 404 do site estático).

Os testes correspondentes estão em `tests-api/`.

### `frontend/` — Next.js na Vercel

Front separado, consumindo a API acima. Substituído por `site/`, que é estático
e não precisa de servidor.

### `deploy/` — Docker Compose, nginx, Hetzner

Provisionamento de servidor com PostgreSQL local, Redis, nginx, Prometheus e
Grafana. Substituído por GitHub Pages (site) + Supabase (dados), ambos sem
servidor para administrar.

`deploy/.env.production.example` é um **template com placeholders**, não
credenciais. Em agosto de 2026 uma auditoria automática o leu como vazamento de
segredos e custou uma investigação inteira para provar o contrário — parte da
razão de este material sair do caminho.

### `dashboard_publico/` — Streamlit

Painel exploratório anterior ao site atual.

### `docker-compose.yml`

Orquestra os serviços de `api/`, `frontend/` e `deploy/`.

## Decisões registradas

Os ADRs em `docs/architecture/` descrevem as escolhas originais desta stack.
Continuam válidos como **registro histórico** — não como instrução vigente.

## Se você precisar reviver algo

O histórico do Git está intacto: `git log --follow archive/api/main.py` mostra
tudo desde antes da mudança de nome. Nada foi apagado.
