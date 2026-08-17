"""
api/main.py — saude-publica-br  v0.7.0
FastAPI application: registro de routers e middleware global.

Fase 12: API pública estável v1.0
  - Router /v1 com autenticação por API key e rate limiting por tier
  - Endpoint /auth/api-keys para gestão de chaves programáticas
  - Documentação OpenAPI enriquecida com exemplos e esquemas de erro
  - Versão semântica 0.7.0 (feature release: public API)
"""

from __future__ import annotations

import os
import time

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

# ─── Routers legados (Fases 1–11) ────────────────────────────────────────────
from api.routers.producao    import router as r_producao
from api.routers.mortalidade import router as r_mortalidade
from api.routers.sinan       import router as r_doencas
from api.routers.nacional    import router as r_nacional

# Fase 11 — autenticação JWT, dashboards, exportação
from api.routers.auth        import router as r_auth
from api.routers.dashboards  import router as r_dashboards
from api.routers.exports     import router as r_exports

# Fase 12 — API pública v1 com API-key + rate limiting
from api.v1.router           import router as r_v1

# Routers complementares (fases 3–10, nunca registrados)
from api.routers.epidemiologia import router as r_epidemiologia
from api.routers.indicadores   import router as r_indicadores
from api.routers.ranking       import router as r_ranking
from api.routers.internacoes   import router as r_internacoes
from api.routers.cnes          import router as r_cnes

# ─── Metadados OpenAPI ────────────────────────────────────────────────────────

DESCRIPTION = """
## Saúde Pública BR — API v0.7.0

**O Our World in Data do SUS.** Dados abertos do DataSUS transformados em
inteligência epidemiológica acessível, consumível por pesquisadores, jornalistas,
desenvolvedores e gestores de saúde.

### Cobertura

| Dimensão | Detalhe |
|----------|---------|
| **Estados** | 27 UFs (todos os estados + DF) |
| **Sistemas** | SIA, SIM, SIH, SINAN, CNES |
| **Período** | 2019–2024 |
| **Registros** | ~480 milhões |

### Autenticação

A API pública (`/v1/*`) utiliza **API Keys** passadas no header `X-API-Key`.
Endpoints internos (`/auth/*`, `/dashboards/*`, `/exports/*`) utilizam **JWT Bearer tokens**.

### Rate Limiting por Tier

| Tier | Req/min | Histórico | Granularidade |
|------|---------|-----------|---------------|
| `free` | 60 | 12 meses | UF |
| `pro` | 600 | Completo | UF + Municipal |
| `enterprise` | 6000 | Completo | UF + Municipal |
"""

CONTACT = {
    "name": "Equipe Saúde Pública BR",
    "url": "https://saude-publica-br.gov.br",
    "email": "api@saude-publica-br.gov.br",
}

LICENSE_INFO = {
    "name": "MIT",
    "url": "https://opensource.org/licenses/MIT",
}

TAGS_METADATA = [
    {"name": "Root", "description": "Health check e informações gerais da API."},
    {"name": "API v1 — Produção Ambulatorial", "description": "Dados do SIA — procedimentos ambulatoriais por UF e período."},
    {"name": "API v1 — Mortalidade", "description": "Dados do SIM — óbitos por CID-10, causa básica, faixa etária e UF."},
    {"name": "API v1 — Capacidade Hospitalar", "description": "Dados do CNES — estabelecimentos, leitos e recursos humanos."},
    {"name": "API v1 — Doenças Notificáveis", "description": "Dados do SINAN — notificações de doenças e surtos epidemiológicos."},
    {"name": "API v1 — Utilitários", "description": "Status da API, informações da chave atual e sistemas disponíveis."},
    {"name": "Autenticação", "description": "Registro, login, refresh de JWT e gestão de API keys."},
    {"name": "Dashboards", "description": "CRUD de dashboards customizáveis para usuários autenticados."},
    {"name": "Exportação", "description": "Exportação de datasets em CSV, Excel (XLSX) e JSON."},
]

# ─── App ──────────────────────────────────────────────────────────────────────

app = FastAPI(
    title="Saúde Pública BR — API",
    description=DESCRIPTION,
    version="0.7.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    contact=CONTACT,
    license_info=LICENSE_INFO,
    openapi_tags=TAGS_METADATA,
    swagger_ui_parameters={
        "defaultModelsExpandDepth": 2,
        "defaultTagsExpandDepth": 1,
        "tryItOutEnabled": True,
        "filter": True,
        "syntaxHighlight.theme": "monokai",
    },
)

# ─── CORS ─────────────────────────────────────────────────────────────────────

_ALLOWED_ORIGINS = os.getenv(
    "CORS_ORIGINS",
    "http://localhost:3000,https://saude-publica-br.gov.br",
).split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=_ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── Routers ──────────────────────────────────────────────────────────────────

# v1 público (API Key auth) — prefix="/v1" já definido no próprio router
app.include_router(r_v1)

# Fases 1-10 (legado / interno)
app.include_router(r_producao,    tags=["Produção Ambulatorial (legado)"])
app.include_router(r_mortalidade, tags=["Mortalidade (legado)"])
app.include_router(r_doencas,     tags=["Doenças Notificáveis (legado)"])
app.include_router(r_nacional,    tags=["Dados Nacionais (legado)"])

# Routers complementares (registrados agora — sem double-prefix)
app.include_router(r_epidemiologia)
app.include_router(r_indicadores)
app.include_router(r_ranking)
app.include_router(r_internacoes)
app.include_router(r_cnes)

# Fase 11 — JWT auth
app.include_router(r_auth,        tags=["Autenticação"])
app.include_router(r_dashboards,  tags=["Dashboards"])
app.include_router(r_exports,     tags=["Exportação"])



@app.get("/info", tags=["Root"], summary="Metadados detalhados da API")
async def info():
    """Retorna informações detalhadas sobre cobertura, sistemas e autenticação."""
    return {
        "api": "Saúde Pública BR",
        "versao": "0.7.0",
        "descricao": "O Our World in Data do SUS — dados abertos do DataSUS como inteligência epidemiológica.",
        "cobertura": {
            "estados": 27,
            "sistemas": ["SIA", "SIM", "SIH", "SINAN", "CNES"],
            "periodo": "2019-2024",
            "registros_aproximados": 480_000_000,
        },
        "autenticacao": {
            "publica_v1": "API Key via header X-API-Key",
            "interna": "JWT Bearer token via /auth/login",
        },
        "tiers": {
            "free":       {"req_min": 60,   "historico": "12 meses", "granularidade": "UF"},
            "pro":        {"req_min": 600,  "historico": "Completo", "granularidade": "UF + Municipal"},
            "enterprise": {"req_min": 6000, "historico": "Completo", "granularidade": "UF + Municipal"},
        },
        "links": {
            "docs":    "/docs",
            "redoc":   "/redoc",
            "openapi": "/openapi.json",
            "status":  "https://status.saude-publica-br.gov.br",
        },
    }

# ─── Middleware de telemetria ─────────────────────────────────────────────────


@app.middleware("http")
async def telemetry_middleware(request: Request, call_next):
    start = time.perf_counter()
    response = await call_next(request)
    elapsed_ms = (time.perf_counter() - start) * 1000
    response.headers["X-Response-Time-Ms"] = f"{elapsed_ms:.1f}"
    response.headers["X-API-Version"] = "0.7.0"
    return response


# ─── Endpoints raiz ───────────────────────────────────────────────────────────


@app.get("/", tags=["Root"], summary="Informações gerais da API")
async def root():
    """Retorna metadados da API: versão, fases completas e links úteis."""
    return {
        "api": "Saúde Pública BR",
        "versao": "0.7.0",
        "fases_completas": list(range(1, 13)),
        "cobertura": {
            "estados": 27,
            "sistemas": ["SIA", "SIM", "SIH", "SINAN", "CNES"],
            "periodo": "2019-2024",
            "registros_aproximados": 480_000_000,
        },
        "links": {
            "docs":           "/docs",
            "redoc":          "/redoc",
            "openapi":        "/openapi.json",
            "sdk_python":     "pip install saude-publica-br",
            "sdk_typescript": "npm install saude-publica-br",
            "portal":         "https://saude-publica-br.gov.br/dev",
            "status":         "https://status.saude-publica-br.gov.br",
        },
    }


@app.get("/health", tags=["Root"], summary="Health check com versão do banco")
async def health():
    """Verifica conectividade com o banco e retorna estado do serviço."""
    from api.database import get_db
    try:
        async for db in get_db():
            result = await db.execute("SELECT version()")
            db_version = result.scalar()
        return {
            "status": "ok",
            "db": "connected",
            "db_version": db_version,
            "api_version": "0.7.0",
        }
    except Exception as exc:
        return JSONResponse(
            status_code=503,
            content={"status": "degraded", "db": "unreachable", "error": str(exc)},
        )
