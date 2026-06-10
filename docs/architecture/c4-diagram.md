# Diagrama de Arquitetura C4 — saude-publica-br

> **C4 Model**: Context → Container → Component → Code
> Este documento cobre os níveis **Context** e **Container**.

---

## Nível 1 — Contexto do Sistema

```mermaid
C4Context
    title Diagrama de Contexto — saude-publica-br

    Person(pesquisador, "Pesquisador / Gestor", "Analista de saúde pública, epidemiologista, gestor municipal")
    Person(contribuidor, "Contribuidor Open Source", "Desenvolvedor que contribui com novos estados, indicadores ou features")
    Person(prefect_scheduler, "Prefect Scheduler", "Orquestrador automático que dispara o pipeline toda segunda-feira")

    System(saude_publica_br, "saude-publica-br", "Plataforma de inteligência epidemiológica: coleta, processa e expõe dados do SUS")

    System_Ext(datasus, "DataSUS / FTP DATASUS", "Servidor FTP público do Ministério da Saúde com arquivos DBF brutos (SIA, SIM, SIH, SINAN, CNES)")
    System_Ext(ibge, "IBGE", "Populações municipais e shapefiles geográficos")
    System_Ext(supabase_cloud, "Supabase Cloud", "PostgreSQL 15 gerenciado + Autenticação + Storage")
    System_Ext(github_actions, "GitHub Actions", "CI/CD: lint, testes, build de imagens Docker, deploy automático")

    Rel(pesquisador, saude_publica_br, "Consulta indicadores via dashboard e API REST")
    Rel(contribuidor, saude_publica_br, "Contribui código via Pull Request")
    Rel(prefect_scheduler, saude_publica_br, "Dispara pipeline de ingestão semanal")
    Rel(saude_publica_br, datasus, "Baixa arquivos DBF via PySUS (FTP/HTTP)")
    Rel(saude_publica_br, ibge, "Importa populações e geometrias municipais")
    Rel(saude_publica_br, supabase_cloud, "Persiste marts dbt e serve dados via PostgREST")
    Rel(github_actions, saude_publica_br, "Valida, testa e faz deploy a cada PR/merge")
```

---

## Nível 2 — Containers

```mermaid
C4Container
    title Diagrama de Containers — saude-publica-br

    Person(usuario, "Usuário Final", "Pesquisador, gestor de saúde")

    Container_Boundary(prod, "Produção (Docker Compose / VPS)") {
        Container(nginx, "nginx", "nginx:alpine", "Reverse proxy, TLS termination, rate limiting (10r/s API, 30r/s global)")
        Container(frontend, "Frontend Next.js", "Next.js 14 / Node.js", "5 páginas: Visão Geral, Produção, Mortalidade, Internações, SINAN. Deck.gl + Recharts.")
        Container(api, "FastAPI API", "Python 3.11 / uvicorn", "REST API com 8 routers, cache Redis, instrumentação Prometheus. v0.4.0.")
        Container(redis, "Redis", "Redis 7.2-alpine", "Cache de respostas da API (TTL 6h prod, 24h histórico)")
        Container(prometheus, "Prometheus", "prom/prometheus:v2.54", "Coleta métricas da API e nginx a cada 15s. Retenção: 15 dias.")
        Container(grafana, "Grafana", "grafana/grafana:11.2", "12 painéis: throughput, latência P50/P95/P99, cache hit rate, nginx")
        Container(nginx_exporter, "nginx Exporter", "nginx/nginx-prometheus-exporter:1.1", "Converte stub_status do nginx para métricas Prometheus")
    }

    Container_Boundary(pipeline_layer, "Pipeline de Dados (local ou servidor dedicado)") {
        Container(pysus, "Ingestão PySUS", "Python / PySUS", "Baixa arquivos DBF do DataSUS, converte para Parquet via PyArrow")
        Container(duckdb, "DuckDB", "DuckDB in-process", "Transformações in-memory antes de carregar no Supabase")
        Container(dbt, "dbt-core", "dbt-postgres 1.8", "Staging → Intermediate → Marts. 6 conjuntos de indicadores.")
        Container(great_exp, "Great Expectations", "GE 0.18", "6 suites de validação de qualidade de dados")
        Container(prefect, "Prefect 2.x", "Prefect / Python", "Orquestra: ingestão → validação → dbt run → notify")
    }

    Container_Boundary(data_layer, "Armazenamento") {
        ContainerDb(parquet, "Parquet Files", "Apache Parquet / S3-compatible", "Dados brutos normalizados por estado/ano (~50GB para SP+RJ+MG)")
        ContainerDb(postgres, "Supabase/PostgreSQL 15", "PostgreSQL 15", "Marts dbt, migrações V001–V010, Row Level Security habilitado")
    }

    Rel(usuario, nginx, "HTTPS :443", "TLS 1.3")
    Rel(nginx, frontend, "HTTP interno :3000")
    Rel(nginx, api, "HTTP interno :8000 (/api/*)")
    Rel(nginx, nginx_exporter, "stub_status :8080")
    Rel(api, redis, "cache get/set", "Redis protocol")
    Rel(api, postgres, "SELECT queries", "asyncpg / PostgreSQL wire")
    Rel(nginx_exporter, prometheus, "scrape /metrics", "HTTP :9113")
    Rel(api, prometheus, "scrape /metrics", "HTTP :8000/metrics")
    Rel(prometheus, grafana, "datasource", "HTTP :9090")
    Rel(pysus, parquet, "escreve Parquet")
    Rel(duckdb, parquet, "lê Parquet")
    Rel(dbt, postgres, "CREATE/INSERT marts", "PostgreSQL wire")
    Rel(duckdb, dbt, "pré-processa antes do dbt load")
    Rel(great_exp, parquet, "valida schemas e qualidade")
    Rel(prefect, pysus, "dispara ingestão")
    Rel(prefect, dbt, "dispara dbt run")
    Rel(prefect, great_exp, "dispara validação")
```

---

## Fluxo de dados — Pipeline semanal

```
Segunda-feira 07:00 UTC
        │
        ▼ Prefect: weekly_pipeline.py
┌───────────────────┐
│ 1. Ingestão       │  PySUS → DBF → Parquet
│    (por estado)   │  ~30 min para SP/RJ/MG
└───────────────────┘
        │
        ▼
┌───────────────────┐
│ 2. Validação      │  Great Expectations
│    (6 suites)     │  Schema, ranges, completude
└───────────────────┘
        │ se OK
        ▼
┌───────────────────┐
│ 3. DuckDB         │  Transformações in-memory
│    pre-processing │  Deduplicação, tipos, joins
└───────────────────┘
        │
        ▼
┌───────────────────┐
│ 4. dbt run        │  staging → intermediate → marts
│    (PostgreSQL)   │  Migrations aplicadas
└───────────────────┘
        │
        ▼
┌───────────────────┐
│ 5. Cache bust     │  Redis FLUSHDB seletivo
│    + notify       │  Slack/email se erros
└───────────────────┘
```

---

## Camadas de banco de dados (PostgreSQL)

```
public schema
├── raw_*           ← staging dbt (dados normalizados)
├── int_*           ← intermediate dbt (enriquecidos)
└── mart_*          ← marts finais (lidos pela API)
    ├── mart_producao_ambulatorial
    ├── mart_mortalidade
    ├── mart_internacoes
    ├── mart_indicadores_acesso
    ├── mart_epidemiologia_cid10
    ├── mart_sazonalidade
    ├── mart_ranking_municipios
    ├── mart_anomalias
    ├── mart_doencas_notificaveis
    └── mart_capacidade_hospitalar
```

---

## Veja também

- [ADR-001](adr-001-pysus-parquet.md) — Escolha do PySUS + Parquet
- [ADR-002](adr-002-dbt-supabase.md) — Escolha do dbt + Supabase
- [ADR-003](adr-003-fastapi-redis.md) — Escolha do FastAPI + Redis
- [ADR-004](adr-004-prophet-anomaly.md) — Detecção de anomalias com Prophet
- [ADR-005](adr-005-nginx-prometheus.md) — Produção com nginx + Prometheus
