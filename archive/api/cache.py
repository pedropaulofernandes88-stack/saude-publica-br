"""
Camada de cache Redis para a API saude-publica-br.

Estratégia de TTL por tipo de dado:
  - /mapa, /ranking      → 6 horas   (dados geográficos, mudam pouco)
  - /producao, /series   → 12 horas  (produção mensal, estável durante o dia)
  - /epi, /complexidade  → 24 horas  (indicadores epidemiológicos, estáveis)
  - /anomalias           → 6 horas   (alertas devem ser relativamente frescos)
  - /indicadores         → 12 horas

Degradação graciosa: se Redis não estiver disponível, a API funciona
normalmente sem cache (log de aviso, sem exceção).
"""
from __future__ import annotations

import functools
import hashlib
import json
import logging
from collections.abc import Callable
from datetime import timedelta
from typing import Any

import asyncpg
import redis.asyncio as aioredis

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# TTL constants (em segundos)
# ---------------------------------------------------------------------------

TTL_MAPA = int(timedelta(hours=6).total_seconds())          # 21_600
TTL_RANKING = int(timedelta(hours=6).total_seconds())        # 21_600
TTL_PRODUCAO = int(timedelta(hours=12).total_seconds())      # 43_200
TTL_INDICADORES = int(timedelta(hours=12).total_seconds())   # 43_200
TTL_EPI = int(timedelta(hours=24).total_seconds())           # 86_400
TTL_COMPLEXIDADE = int(timedelta(hours=24).total_seconds())  # 86_400
TTL_ANOMALIAS = int(timedelta(hours=6).total_seconds())      # 21_600

# Prefixo de chaves no Redis
CACHE_PREFIX = "spbr"


# ---------------------------------------------------------------------------
# Pool global (inicializado no lifespan da FastAPI)
# ---------------------------------------------------------------------------

_redis_pool: aioredis.Redis | None = None


async def init_redis(redis_url: str) -> None:
    """Cria o pool Redis. Chamar no lifespan startup."""
    global _redis_pool
    try:
        _redis_pool = await aioredis.from_url(
            redis_url,
            encoding="utf-8",
            decode_responses=True,
            max_connections=20,
        )
        await _redis_pool.ping()
        logger.info("Redis conectado: %s", redis_url)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Redis indisponível (%s). Cache desabilitado.", exc)
        _redis_pool = None


async def close_redis() -> None:
    """Fecha o pool Redis. Chamar no lifespan shutdown."""
    global _redis_pool
    if _redis_pool:
        await _redis_pool.aclose()
        _redis_pool = None
        logger.info("Redis fechado.")


def get_redis() -> aioredis.Redis | None:
    """Dependency injection — retorna None se Redis não estiver disponível."""
    return _redis_pool


# ---------------------------------------------------------------------------
# Cache key builder
# ---------------------------------------------------------------------------


def build_cache_key(prefix: str, **kwargs: Any) -> str:
    """
    Constrói chave de cache determinística.

    Exemplo:
        build_cache_key("producao", uf_sigla="SP", ano=2024)
        → "spbr:producao:4a2c8f..."
    """
    # Ordena params para garantir a mesma chave independente da ordem
    params_str = json.dumps(kwargs, sort_keys=True, default=str)
    digest = hashlib.sha256(params_str.encode()).hexdigest()[:16]
    return f"{CACHE_PREFIX}:{prefix}:{digest}"


# ---------------------------------------------------------------------------
# Get / Set / Invalidate
# ---------------------------------------------------------------------------


async def cache_get(key: str) -> Any | None:
    """Lê valor do cache. Retorna None se miss ou Redis indisponível."""
    if _redis_pool is None:
        return None
    try:
        raw = await _redis_pool.get(key)
        if raw is None:
            return None
        return json.loads(raw)
    except Exception as exc:  # noqa: BLE001
        logger.debug("Cache GET error (%s): %s", key, exc)
        return None


async def cache_set(key: str, value: Any, ttl: int) -> None:
    """Grava valor no cache com TTL em segundos."""
    if _redis_pool is None:
        return
    try:
        serialized = json.dumps(value, default=str)
        await _redis_pool.setex(key, ttl, serialized)
    except Exception as exc:  # noqa: BLE001
        logger.debug("Cache SET error (%s): %s", key, exc)


async def cache_invalidate_pattern(pattern: str) -> int:
    """
    Invalida chaves que casam com o padrão glob.
    Retorna número de chaves deletadas.

    Exemplo:
        await cache_invalidate_pattern("spbr:producao:*")
    """
    if _redis_pool is None:
        return 0
    try:
        keys = await _redis_pool.keys(f"{CACHE_PREFIX}:{pattern}")
        if keys:
            return await _redis_pool.delete(*keys)
        return 0
    except Exception as exc:  # noqa: BLE001
        logger.debug("Cache INVALIDATE error (%s): %s", pattern, exc)
        return 0


async def cache_invalidate_all() -> int:
    """Invalida TODAS as chaves deste projeto. Usar com cautela."""
    return await cache_invalidate_pattern("*")


# ---------------------------------------------------------------------------
# Decorator de cache para endpoints FastAPI
# ---------------------------------------------------------------------------


def cached(ttl: int, key_prefix: str):
    """
    Decorator para endpoints FastAPI que cacheia a resposta JSON.

    Uso:
        @router.get("/producao")
        @cached(ttl=TTL_PRODUCAO, key_prefix="producao")
        async def get_producao(uf_sigla: str | None = None, ...):
            ...

    O decorator inspeciona os kwargs do endpoint (excluindo a conexão DB)
    para construir a chave de cache. Compatível com FastAPI Depends.
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            # Exclui objetos de conexão DB — não são serializáveis nem
            # fazem parte da chave de cache (asyncpg.Connection / PoolProxy)
            cache_params = {
                k: v for k, v in kwargs.items()
                if not isinstance(
                    v,
                    (asyncpg.Connection, asyncpg.pool.PoolConnectionProxy),
                )
            }
            key = build_cache_key(key_prefix, **cache_params)

            # Cache HIT
            cached_value = await cache_get(key)
            if cached_value is not None:
                logger.debug("Cache HIT: %s", key)
                return cached_value

            # Cache MISS — executa a função original
            result = await func(*args, **kwargs)

            # Serializa e guarda (Pydantic models → dict)
            try:
                if hasattr(result, "model_dump"):
                    serializable = result.model_dump(mode="json")
                else:
                    serializable = result
                await cache_set(key, serializable, ttl)
                logger.debug("Cache SET: %s (ttl=%ds)", key, ttl)
            except Exception as exc:  # noqa: BLE001
                logger.debug("Cache serialize error: %s", exc)

            return result

        return wrapper

    return decorator


# ---------------------------------------------------------------------------
# Utilitários de diagnóstico
# ---------------------------------------------------------------------------


async def cache_stats() -> dict[str, Any]:
    """Retorna estatísticas do Redis para o health-check."""
    if _redis_pool is None:
        return {"disponivel": False}
    try:
        info = await _redis_pool.info("stats")
        keys_count = await _redis_pool.dbsize()
        return {
            "disponivel": True,
            "total_chaves": keys_count,
            "hits": info.get("keyspace_hits", 0),
            "misses": info.get("keyspace_misses", 0),
            "hit_rate": (
                round(
                    info.get("keyspace_hits", 0)
                    / max(info.get("keyspace_hits", 0) + info.get("keyspace_misses", 0), 1)
                    * 100,
                    1,
                )
            ),
        }
    except Exception as exc:  # noqa: BLE001
        return {"disponivel": False, "erro": str(exc)}
