"""
Middleware de autenticação por API key para a API pública v1.
Suporta três tiers: free (100 req/h), pro (5000 req/h), enterprise (sem limite).

A chave deve ser enviada como:
  - Header: X-API-Key: spbr_xxxx_...
  - Query param: ?api_key=spbr_xxxx_...  (compatibilidade)

A validação usa a função SQL SECURITY DEFINER `verificar_api_key()`,
que compara o SHA-256 da chave recebida contra o hash armazenado.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Optional
from uuid import UUID

from fastapi import Depends, HTTPException, Request, Security
from fastapi.security import APIKeyHeader, APIKeyQuery

from api.database import get_db

log = logging.getLogger(__name__)

# ── esquemas de extração da chave ─────────────────────────────────────────────
_header_scheme = APIKeyHeader(name="X-API-Key", auto_error=False)
_query_scheme  = APIKeyQuery(name="api_key",   auto_error=False)


# ── modelo de retorno da validação ────────────────────────────────────────────
class ApiKeyInfo:
    """Dados da API key validada, injetados como dependência nos handlers."""

    def __init__(self, row: dict):
        self.api_key_id: UUID  = row["api_key_id"]
        self.user_id: Optional[UUID] = row["user_id"]
        self.tier: str         = row["tier"]
        self.scopes: list[str] = row["scopes"] or ["read"]
        self.uso_hora: int     = int(row["uso_hora"])
        self.limite_hora: Optional[int] = row["limite_hora"]

    def has_scope(self, scope: str) -> bool:
        return scope in self.scopes or "admin" in self.scopes

    @property
    def requests_remaining_hour(self) -> Optional[int]:
        if self.limite_hora is None:
            return None  # enterprise: ilimitado
        return max(0, self.limite_hora - self.uso_hora)


# ── extração da chave bruta da requisição ─────────────────────────────────────
def _extract_raw_key(
    header_key: Optional[str] = Security(_header_scheme),
    query_key:  Optional[str] = Security(_query_scheme),
) -> Optional[str]:
    return header_key or query_key


# ── dependência principal ─────────────────────────────────────────────────────
async def get_api_key(
    request: Request,
    raw_key: Optional[str] = Depends(_extract_raw_key),
    conn = Depends(get_db),
) -> ApiKeyInfo:
    """
    Valida a API key e aplica rate limiting.

    Raises:
        401 — chave ausente ou inválida
        403 — chave sem o scope necessário (verificado no handler)
        429 — rate limit atingido (retorna Retry-After)
    """
    if not raw_key:
        raise HTTPException(
            status_code=401,
            detail="API key obrigatória. Envie X-API-Key no header ou ?api_key= na query.",
            headers={"WWW-Authenticate": "ApiKey"},
        )

    if not raw_key.startswith("spbr_"):
        raise HTTPException(status_code=401, detail="Formato de API key inválido.")

    # valida + contabiliza uso (função SQL atômica)
    row = await conn.fetchrow(
        "SELECT * FROM public.verificar_api_key($1)", raw_key
    )

    if not row or not row["valida"]:
        raise HTTPException(status_code=401, detail="API key inválida ou expirada.")

    if not row["rate_limit_ok"]:
        limite = row["limite_hora"]
        raise HTTPException(
            status_code=429,
            detail=f"Rate limit atingido: {limite} requisições/hora para o tier {row['tier']}. "
                   f"Aguarde ou faça upgrade em saude-publica-br.org/planos.",
            headers={"Retry-After": "3600"},
        )

    key_info = ApiKeyInfo(row)

    # registra uso assincronamente (fire-and-forget, não bloqueia resposta)
    endpoint = request.url.path
    asyncio.create_task(
        _registrar_uso(conn, key_info.api_key_id, endpoint, request.method)
    )

    return key_info


async def _registrar_uso(conn, api_key_id: UUID, endpoint: str, metodo: str) -> None:
    """Registra uso na tabela particionada api_usage_log."""
    try:
        await conn.execute(
            """
            INSERT INTO public.api_usage_log (api_key_id, endpoint, metodo, status_code)
            VALUES ($1, $2, $3, 200)
            """,
            api_key_id, endpoint, metodo,
        )
    except Exception as exc:  # pragma: no cover
        log.warning("Erro ao registrar uso da API key: %s", exc)


# ── dependência opcional (para endpoints que aceitam auth OU chave) ───────────
async def get_optional_api_key(
    raw_key: Optional[str] = Depends(_extract_raw_key),
    conn = Depends(get_db),
) -> Optional[ApiKeyInfo]:
    """Retorna None se nenhuma chave for fornecida (não levanta 401)."""
    if not raw_key:
        return None
    try:
        return await get_api_key.__wrapped__(raw_key=raw_key, conn=conn)  # type: ignore
    except HTTPException:
        return None


# ── verificação de scope ──────────────────────────────────────────────────────
def require_scope(scope: str):
    """Factory: verifica se a API key tem o scope necessário."""
    async def _checker(key: ApiKeyInfo = Depends(get_api_key)) -> ApiKeyInfo:
        if not key.has_scope(scope):
            raise HTTPException(
                status_code=403,
                detail=f"Scope '{scope}' necessário. Seu plano atual: {key.tier}.",
            )
        return key
    return _checker
