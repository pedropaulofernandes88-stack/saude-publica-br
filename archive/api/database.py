"""
Camada de acesso ao banco de dados (PostgreSQL/Supabase) via asyncpg.

Usa um pool de conexões async para queries nos dbt marts.
O pool é criado no lifespan da FastAPI e compartilhado via dependency injection.

Arquitetura:
  FastAPI endpoint → get_db() dependency → AsyncPool → Supabase PostgreSQL
                                         ↕
                              dbt marts (schema public)
"""
from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager
from typing import Any, AsyncGenerator

import asyncpg

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Pool global
# ---------------------------------------------------------------------------

_pool: asyncpg.Pool | None = None


async def init_db(dsn: str | None = None) -> None:
    """
    Inicializa o pool de conexões PostgreSQL.
    Chamar no startup do lifespan FastAPI.
    """
    global _pool
    database_url = dsn or os.environ["DATABASE_URL"]
    # asyncpg não aceita o prefixo "postgresql+asyncpg://"
    database_url = database_url.replace("postgresql+asyncpg://", "postgresql://")

    try:
        _pool = await asyncpg.create_pool(
            dsn=database_url,
            min_size=2,
            max_size=10,
            command_timeout=30,
            # Supabase requer SSL
            ssl="require" if "supabase" in database_url else None,
        )
        # Smoke test
        async with _pool.acquire() as conn:
            version = await conn.fetchval("SELECT version()")
            logger.info("DB conectado: %.60s", version)
    except Exception as exc:
        logger.error("Falha ao conectar DB: %s", exc)
        raise


async def close_db() -> None:
    """Fecha o pool. Chamar no shutdown do lifespan."""
    global _pool
    if _pool:
        await _pool.close()
        _pool = None
        logger.info("Pool DB fechado.")


# ---------------------------------------------------------------------------
# Dependency injection
# ---------------------------------------------------------------------------


async def get_db() -> AsyncGenerator[asyncpg.Connection, None]:
    """
    FastAPI dependency que fornece uma conexão do pool.

    Uso:
        @router.get("/endpoint")
        async def endpoint(db: asyncpg.Connection = Depends(get_db)):
            rows = await db.fetch("SELECT ...")
    """
    if _pool is None:
        raise RuntimeError("Pool DB não inicializado. Verifique o lifespan da aplicação.")
    async with _pool.acquire() as conn:
        yield conn


@asynccontextmanager
async def db_context() -> AsyncGenerator[asyncpg.Connection, None]:
    """Context manager para uso fora do escopo de endpoints FastAPI."""
    if _pool is None:
        raise RuntimeError("Pool DB não inicializado.")
    async with _pool.acquire() as conn:
        yield conn


# ---------------------------------------------------------------------------
# Query helpers
# ---------------------------------------------------------------------------


def build_where_clauses(
    filters: dict[str, Any],
    param_start: int = 1,
) -> tuple[list[str], list[Any]]:
    """
    Converte um dict de filtros em cláusulas WHERE parametrizadas para asyncpg.

    Args:
        filters: {coluna: valor} — valores None são ignorados.
        param_start: índice inicial do placeholder ($1, $2, ...).

    Returns:
        (clauses, params) onde clauses = ["coluna = $1", ...] e params = [valor, ...]

    Exemplo:
        clauses, params = build_where_clauses({"uf_sigla": "SP", "ano": 2024})
        # → (["uf_sigla = $1", "ano = $2"], ["SP", 2024])
    """
    clauses: list[str] = []
    params: list[Any] = []
    idx = param_start

    for col, val in filters.items():
        if val is None:
            continue
        if isinstance(val, (list, tuple)):
            placeholders = ", ".join(f"${idx + i}" for i in range(len(val)))
            clauses.append(f"{col} = ANY(ARRAY[{placeholders}])")
            params.extend(val)
            idx += len(val)
        else:
            clauses.append(f"{col} = ${idx}")
            params.append(val)
            idx += 1

    return clauses, params


def build_pagination(
    pagina: int,
    por_pagina: int,
    param_idx: int,
) -> tuple[str, list[Any]]:
    """
    Gera cláusula LIMIT/OFFSET e seus parâmetros.

    Returns:
        ("LIMIT $N OFFSET $M", [limit_val, offset_val])
    """
    offset = (pagina - 1) * por_pagina
    return f"LIMIT ${param_idx} OFFSET ${param_idx + 1}", [por_pagina, offset]


async def fetch_paginated(
    conn: asyncpg.Connection,
    base_query: str,
    count_query: str,
    params: list[Any],
    pagina: int,
    por_pagina: int,
    count_params: list[Any] | None = None,
) -> tuple[list[asyncpg.Record], int]:
    """
    Executa query paginada e retorna (registros, total).

    Args:
        base_query: SELECT ... FROM ... WHERE ... (sem LIMIT/OFFSET)
        count_query: SELECT COUNT(*) FROM ... WHERE ... (mesmos filtros)
        params: lista de parâmetros para base_query (pode incluir filtros extras)
        pagina: página atual (1-indexed)
        por_pagina: número de registros por página
        count_params: parâmetros para count_query quando diferem de params.
            Use quando base_query tem filtros adicionais não presentes em
            count_query (ex: top_n em epidemiologia). Se None, usa params.

    Returns:
        (rows, total_count)
    """
    # Total sem paginação — usa count_params quando fornecido (evita
    # "unexpected parameter" quando base_query tem placeholders extras)
    _count_params = count_params if count_params is not None else params
    total: int = await conn.fetchval(count_query, *_count_params) or 0

    # Resultados paginados
    page_sql, page_params = build_pagination(pagina, por_pagina, len(params) + 1)
    rows = await conn.fetch(f"{base_query} {page_sql}", *params, *page_params)

    return rows, total


# ---------------------------------------------------------------------------
# Helpers de serialização asyncpg → dict
# ---------------------------------------------------------------------------


def record_to_dict(record: asyncpg.Record) -> dict[str, Any]:
    """Converte asyncpg.Record para dict serializável."""
    return dict(record)


def records_to_list(records: list[asyncpg.Record]) -> list[dict[str, Any]]:
    """Converte lista de asyncpg.Record para lista de dicts."""
    return [record_to_dict(r) for r in records]


# ---------------------------------------------------------------------------
# Health-check
# ---------------------------------------------------------------------------


async def db_health() -> dict[str, Any]:
    """Verifica saúde do banco para o endpoint /health."""
    if _pool is None:
        return {"conectado": False, "erro": "Pool não inicializado"}
    try:
        async with _pool.acquire() as conn:
            await conn.fetchval("SELECT 1")
            stats = _pool.get_size()
        return {
            "conectado": True,
            "pool_size": stats,
            "pool_min": _pool.get_min_size(),
            "pool_max": _pool.get_max_size(),
        }
    except Exception as exc:  # noqa: BLE001
        return {"conectado": False, "erro": str(exc)}
