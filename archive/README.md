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

### `ingestion/` — microdados brutos via PySUS

Baixava microdados do DataSUS e fazia `COPY` para tabelas `*_raw`, que o dbt
transformava em marts. Substituído pelos pipelines de `scripts/`, que calculam
os marts em DuckDB local e publicam o resultado agregado no Supabase.

Evidência de que não roda: `ingest_all_states.py` levanta `NameError` no import
(`_sia_pa_schema` não existe) desde junho de 2026; nenhum módulo vivo importa o
pacote; e as tabelas que ele escreve (`sim_do_raw`, `mart_mortalidade`) têm
nomes disjuntos das que o site e o servidor MCP consomem
(`mart_mortalidade_municipio`, …).

`ingestion/utils/` **não** veio junto — ver "O que NÃO está aqui".
Detalhes em [`ingestion/README.md`](ingestion/README.md).

### `flows/` — orquestração Prefect

Sete flows que disparavam a ingestão semanal e o `dbt build`. Nenhum agendador
os inicia — não há deployment do Prefect em lugar nenhum do repositório, e o
`requirements-test.txt` exclui o Prefect de propósito. Orquestravam
`ingestion/`, que está aqui ao lado.

Detalhes em [`flows/README.md`](flows/README.md).

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

**`ingestion/utils/` continua na raiz** — `bulk_load.py` e `ingestion_log.py`,
cobertos por 64 testes em `tests/ingestion/test_utils.py` que o CI executa. Não
têm consumidor em produção hoje (os pipelines de `scripts/` usam o próprio
`SupabaseLoader`); ficaram porque arquivá-los custaria 64 testes que passam em
troca de nada. Ver [`ingestion/README.md`](ingestion/README.md).

> Uma versão anterior desta seção dizia que **`flows/` continua na raiz** porque
> orquestrava `ingestion/`, "que é código vivo", e que arquivá-lo seria decisão
> de produto e não conclusão de evidência. A premissa era falsa: nada importava
> `ingestion/`, as tabelas que ele escrevia não são as publicadas, e seu módulo
> de entrada levantava `NameError` no import desde junho de 2026. Os dois
> diretórios desceram para cá em 2026-08-22.

## Decisões registradas

Os ADRs em `docs/architecture/` descrevem as escolhas originais desta stack.
Continuam válidos como **registro histórico** — não como instrução vigente.

## Se você precisar reviver algo

O histórico do Git está intacto: `git log --follow archive/api/main.py` mostra
tudo desde antes da mudança de nome. Nada foi apagado.
