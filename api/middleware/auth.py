"""
api/middleware/auth.py
JWT validation + FastAPI dependencies + PostgreSQL RLS integration.
"""

from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from asyncpg import Connection

from api.database import get_db
from api.models.user import UserPublic, UserRole, UserStatus

# ─── Configuração ────────────────────────────────────────────────────────────

JWT_SECRET       = os.getenv("JWT_SECRET", "CHANGE_ME_IN_PRODUCTION_USE_256BIT_RANDOM")
JWT_ALGORITHM    = "HS256"
ACCESS_TOKEN_EXP = int(os.getenv("ACCESS_TOKEN_EXP_MINUTES", "60"))   # minutos
REFRESH_TOKEN_EXP = int(os.getenv("REFRESH_TOKEN_EXP_DAYS", "30"))    # dias

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login", auto_error=False)

# ─── Helpers ─────────────────────────────────────────────────────────────────

def criar_access_token(user_id: UUID, role: UserRole, email: str) -> str:
    """Gera JWT de acesso com exp = agora + ACCESS_TOKEN_EXP minutos."""
    from datetime import timedelta
    import time

    now = int(time.time())
    payload = {
        "sub": str(user_id),
        "email": email,
        "role": role.value,
        "iat": now,
        "exp": now + ACCESS_TOKEN_EXP * 60,
        "type": "access",
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def criar_refresh_token_raw() -> tuple[str, str]:
    """
    Gera refresh token seguro.
    Retorna (raw_token, sha256_hash).
    raw_token → enviado ao cliente (nunca persiste no DB).
    sha256_hash → salvo em auth.refresh_tokens.token_hash.
    """
    import secrets
    import hashlib

    raw = secrets.token_hex(64)                        # 128 chars hex
    hashed = hashlib.sha256(raw.encode()).hexdigest()
    return raw, hashed


def _decodificar_token(token: str) -> dict:
    """Decodifica e valida JWT; lança HTTPException em caso de falha."""
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token expirado",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except jwt.InvalidTokenError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Token inválido: {exc}",
            headers={"WWW-Authenticate": "Bearer"},
        )


# ─── Configurar RLS no PostgreSQL ────────────────────────────────────────────

async def set_pg_user_id(conn: Connection, user_id: Optional[UUID]) -> None:
    """
    Define `app.current_user_id` como variável de sessão PostgreSQL.
    As políticas RLS de auth.users / public.dashboards leem esta variável.
    Deve ser chamado logo após obter a conexão, antes de qualquer SELECT/INSERT.
    """
    uid = str(user_id) if user_id else ""
    await conn.execute(f"SET LOCAL app.current_user_id = '{uid}'")


# ─── Dependências FastAPI ─────────────────────────────────────────────────────

async def get_current_user(
    token: Optional[str] = Depends(oauth2_scheme),
    conn: Connection = Depends(get_db),
) -> UserPublic:
    """
    Dependência principal: extrai e valida JWT, retorna UserPublic.
    Configura o RLS do PostgreSQL na mesma conexão.
    """
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciais não fornecidas",
            headers={"WWW-Authenticate": "Bearer"},
        )

    payload = _decodificar_token(token)

    if payload.get("type") != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token deve ser do tipo access",
        )

    user_id_str: Optional[str] = payload.get("sub")
    if not user_id_str:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token sem subject",
        )

    try:
        user_id = UUID(user_id_str)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Subject inválido no token",
        )

    # Busca o usuário no banco para garantir que ainda está ativo
    row = await conn.fetchrow(
        """
        SELECT id, email, nome, role, status, email_verificado,
               ultimo_login, criado_em
          FROM auth.users
         WHERE id = $1
        """,
        user_id,
    )

    if not row:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuário não encontrado",
        )

    if row["status"] != "active":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Conta com status '{row['status']}' não possui acesso",
        )

    # Configura RLS para esta transação
    await set_pg_user_id(conn, user_id)

    return UserPublic(
        id=row["id"],
        email=row["email"],
        nome=row["nome"],
        role=UserRole(row["role"]),
        status=UserStatus(row["status"]),
        email_verificado=row["email_verificado"],
        ultimo_login=row["ultimo_login"],
        criado_em=row["criado_em"],
    )


async def get_optional_user(
    token: Optional[str] = Depends(oauth2_scheme),
    conn: Connection = Depends(get_db),
) -> Optional[UserPublic]:
    """
    Igual a get_current_user, mas retorna None se não houver token.
    Útil para endpoints públicos que têm comportamento diferente para autenticados.
    """
    if not token:
        return None
    try:
        return await get_current_user(token, conn)
    except HTTPException:
        return None


async def require_active(
    current_user: UserPublic = Depends(get_current_user),
) -> UserPublic:
    """Shortcut: garante usuário ativo (redundante, get_current_user já checa)."""
    return current_user


def require_role(*roles: UserRole):
    """
    Fábrica de dependências para controle de acesso por papel.

    Uso:
        @router.get("/admin/...", dependencies=[Depends(require_role(UserRole.admin))])
        async def admin_endpoint():
            ...

    Ou como parâmetro:
        async def endpoint(user = Depends(require_role(UserRole.admin, UserRole.analyst))):
            ...
    """
    async def _checker(
        current_user: UserPublic = Depends(get_current_user),
    ) -> UserPublic:
        if current_user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=(
                    f"Acesso restrito. Papel necessário: "
                    f"{[r.value for r in roles]}. "
                    f"Seu papel: {current_user.role.value}"
                ),
            )
        return current_user

    return _checker
