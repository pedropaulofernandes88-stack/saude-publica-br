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

### `dashboard_publico/` e `dashboard/` — Streamlit

Painéis exploratórios anteriores ao site atual. O `dashboard/` consumia
`http://localhost:8000` — a API que está aqui ao lado, o que o torna inoperante
por definição.

### `nginx/` — reverse proxy

Fazia proxy para `api:8000` e `frontend:3000`, ambos containers do
`docker-compose.yml` que está neste diretório.

### `monitoring/` — Prometheus + Grafana

Raspava `api:8000/metrics` e `nginx:80`. O painel Grafana visualiza métricas que
nenhum serviço emite mais.

### `docker-compose.yml`

Orquestra os serviços de `api/`, `frontend/`, `nginx/` e `monitoring/`.

### `railway.toml` e `vercel.json` — hospedagem da stack antiga

Ficavam na raiz do repositório e apontavam para dentro deste diretório:
`railway.toml` constrói `api/Dockerfile` e `vercel.json` declara
`rootDirectory: "frontend"`. Nenhum dos dois serviços é usado — o site vai para
o GitHub Pages por `deploy-site.yml`. Estavam quebrados desde que `api/` e
`frontend/` saíram da raiz.

### `base.md` — documento de concepção

1.660 linhas descrevendo a arquitetura planejada em 2023 (FastAPI, Redis, nginx,
Prometheus/Grafana, Streamlit, Prefect). O próprio arquivo já se declarava
histórico no cabeçalho. Vale como registro de intenção; não como instrução.

### `PUBLICACAO_CUSTO_ZERO.md` — guia de publicação duplicado

Repetia a arquitetura do README, a lista de tabelas de `/dados/` e os passos de
`LAUNCH.md`, e ainda ensinava a subir o dashboard Streamlit que está aqui ao
lado. A única parte que não existia em outro lugar — a tabela de limites do
plano gratuito — foi movida para `LAUNCH.md`.

## O que NÃO está aqui, e por quê

**`supabase/` continua na raiz** — são Edge Functions **implantadas e em uso**:
`alertas-assinatura` atende o formulário de inscrição do site e `alertas-envio`
recebe o POST do boletim semanal. Verificado por HTTP (200 e 405,
respectivamente).

**`flows/` continua na raiz** — flows do Prefect que orquestram `ingestion/`,
que é código vivo. Nenhum agendador os inicia hoje, mas eles apontam para o
Supabase atual, não para a stack morta. Arquivá-los é decisão de produto (o
Prefect foi abandonado ou é caminho a retomar?), não conclusão de evidência.

## Decisões registradas

Os ADRs em `docs/architecture/` descrevem as escolhas originais desta stack.
Continuam válidos como **registro histórico** — não como instrução vigente.

## Se você precisar reviver algo

O histórico do Git está intacto: `git log --follow archive/api/main.py` mostra
tudo desde antes da mudança de nome. Nada foi apagado.
