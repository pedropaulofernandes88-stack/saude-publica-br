"""
api/deps.py — FastAPI dependency helpers.

Expõe get_conn para injeção de dependência nos endpoints v1.
Usa o pool asyncpg gerenciado por api.database.
"""
from __future__ import annotations

from typing import AsyncGenerator

import asyncpg

from api.database import _pool


async def get_conn() -> AsyncGenerator[asyncpg.Connection, None]:
    """
    FastAPI dependency: adquire uma conexão asyncpg do pool global.

    Uso:
        @router.get("/exemplo")
        async def handler(conn: asyncpg.Connection = Depends(get_conn)):
            rows = await conn.fetch("SELECT 1")
    """
    if _pool is None:
        raise RuntimeError(
            "Pool de banco de dados não inicializado. "
            "Certifique-se de que init_db() foi chamado no lifespan."
        )
    async with _pool.acquire() as conn:  # type: ignore[union-attr]
        yield conn
