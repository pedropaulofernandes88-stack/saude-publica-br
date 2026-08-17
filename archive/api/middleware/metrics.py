"""
api/middleware/metrics.py
saude-publica-br — Configuração do Prometheus Instrumentator

Expõe métricas HTTP padrão via prometheus-fastapi-instrumentator:
  • http_requests_total           (counter)   — total de requisições por método/rota/status
  • http_request_duration_seconds (histogram) — latência P50/P95/P99
  • http_request_size_bytes       (histogram) — tamanho do request body
  • http_response_size_bytes      (histogram) — tamanho do response body
  • http_requests_in_progress     (gauge)     — requisições simultâneas em andamento

Métricas de negócio adicionais (custom):
  • api_cache_hits_total    — acertos de cache Redis por endpoint
  • api_cache_misses_total  — misses de cache Redis por endpoint

Uso em main.py:
    from api.middleware.metrics import init_metrics
    init_metrics(app)

O endpoint /metrics fica restrito por IP no nginx (redes Docker internas).
"""
from __future__ import annotations

from prometheus_client import Counter
from prometheus_fastapi_instrumentator import Instrumentator, metrics

# ---------------------------------------------------------------------------
# Métricas de negócio (custom counters)
# ---------------------------------------------------------------------------

CACHE_HITS = Counter(
    "api_cache_hits_total",
    "Total de acertos de cache Redis",
    labelnames=["endpoint"],
)

CACHE_MISSES = Counter(
    "api_cache_misses_total",
    "Total de misses de cache Redis (miss ou indisponível)",
    labelnames=["endpoint"],
)

# ---------------------------------------------------------------------------
# Instrumentator configurado
# ---------------------------------------------------------------------------

_instrumentator = Instrumentator(
    # Não instrumentar endpoints de infra para não poluir métricas de SLA
    should_ignore_handler=lambda req: req.url.path in {
        "/metrics", "/health", "/nginx-health", "/",
    },
    # Agrupa path params: /municipio/3304557 → /municipio/{codigo_ibge}
    should_group_handler_names=True,
    inprogress_name="http_requests_in_progress",
    inprogress_labels=True,
)

# Adiciona métricas padrão (latência + tamanho de request/response)
_instrumentator.add(metrics.default())
_instrumentator.add(metrics.combined_size())


def init_metrics(app) -> None:
    """
    Instrumenta a app FastAPI e expõe o endpoint /metrics.

    Chamar no final de main.py, depois de registrar todos os routers,
    para que todas as rotas sejam detectadas corretamente.

    Args:
        app: instância FastAPI
    """
    _instrumentator.instrument(app).expose(
        app,
        endpoint="/metrics",
        include_in_schema=False,  # não aparece no Swagger
    )
