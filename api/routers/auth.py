"""
api/routers/auth.py
Endpoints de autenticação: registro, login, refresh, logout, perfil.
"""

from __future__ import annotations

import hashlib
import os
from datetime import datetime, timedelta, timezone
from typing import Optional
from uuid import UUID, uuid4

from asyncpg import Connection
from fastapi import APIRouter, Depends, HTTPException, Request, status

from api.database import get_db
from api.middleware.auth import (
    criar_access_token,
    criar_refresh_token_raw,
    get_current_user,
    set_pg_user_id,
)
from api.models.user import (
    AlterarSenhaRequest,
    LoginRequest,
    RefreshRequest,
    RegisterRequest,
    RegisterResponse,
    TokenResponse,
    UserPublic,
    UserRole,
    UserStatus,
)

router = APIRouter(prefix="/auth", tags=["Autenticação"])

REFRESH_TOKEN_EXP_DAYS = int(os.getenv("REFRESH_TOKEN_EXP_DAYS", "30"))
MAX_LOGIN_ATTEMPTS     = int(os.getenv("MAX_LOGIN_ATTEMPTS", "5"))


# ─── Helpers ─────────────────────────────────────────────────────────────────

def _get_ip(request: Request) -> str:
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


async def _verificar_rate_limit(conn: Connection, ip: str) -> None:
    """Bloqueia IP com ≥ MAX_LOGIN_ATTEMPTS falhas no último minuto."""
    count = await conn.fetchval(
        """
        SELECT COUNT(*) FROM auth.rate_limit_log
         WHERE ip = $1::inet
           AND tentativa_em > NOW() - INTERVAL '1 minute'
        """,
        ip,
    )
    if count and count >= MAX_LOGIN_ATTEMPTS:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Muitas tentativas de login. Aguarde 1 minuto.",
        )


async def _registrar_falha(conn: Connection, ip: str, email: str) -> None:
    await conn.execute(
        "INSERT INTO auth.rate_limit_log (ip, email) VALUES ($1::inet, $2)",
        ip,
        email,
    )


async def _emitir_tokens(
    conn: Connection,
    user_id: UUID,
    role: UserRole,
    email: str,
    request: Request,
) -> TokenResponse:
    """Gera access + refresh tokens e persiste o refresh no banco."""
    access_token = criar_access_token(user_id, role, email)
    raw_refresh, hashed_refresh = criar_refresh_token_raw()
    exp = datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_EXP_DAYS)

    await conn.execute(
        """
        INSERT INTO auth.refresh_tokens
               (user_id, token_hash, expirado_em, ip_origem, user_agent)
        VALUES ($1, $2, $3, $4::inet, $5)
        """,
        user_id,
        hashed_refresh,
        exp,
        _get_ip(request),
        request.headers.get("User-Agent", ""),
    )

    # Busca dados completos do usuário para incluir na resposta
    row = await conn.fetchrow(
        """
        SELECT id, email, nome, role, status, email_verificado,
               ultimo_login, criado_em
          FROM auth.users WHERE id = $1
        """,
        user_id,
    )

    usuario = UserPublic(
        id=row["id"],
        email=row["email"],
        nome=row["nome"],
        role=UserRole(row["role"]),
        status=UserStatus(row["status"]),
        email_verificado=row["email_verificado"],
        ultimo_login=row["ultimo_login"],
        criado_em=row["criado_em"],
    )

    from api.middleware.auth import ACCESS_TOKEN_EXP
    return TokenResponse(
        access_token=access_token,
        refresh_token=raw_refresh,
        token_type="Bearer",
        expires_in=ACCESS_TOKEN_EXP * 60,
        usuario=usuario,
    )


# ─── Registro ────────────────────────────────────────────────────────────────

@router.post("/registro", response_model=RegisterResponse, status_code=201)
async def registro(
    body: RegisterRequest,
    conn: Connection = Depends(get_db),
):
    """
    Registra novo usuário.
    Retorna 201 com o ID e aviso de verificação de e-mail pendente.
    A função SQL auth.criar_usuario() faz o bcrypt e gera o token de verificação.
    """
    try:
        result = await conn.fetchrow(
            "SELECT * FROM auth.criar_usuario($1, $2, $3, $4::auth.user_role)",
            body.email.lower(),
            body.nome,
            body.senha,
            UserRole.viewer.value,
        )
    except Exception as exc:
        if "Email já cadastrado" in str(exc):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="E-mail já cadastrado",
            )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao criar usuário: {exc}",
        )

    # Em produção: disparar e-mail com result["token_verificacao"]
    # Por ora apenas registra no log
    print(f"[AUTH] Novo usuário: {body.email} | token: {result['token_verificacao']}")

    return RegisterResponse(
        mensagem=(
            "Usuário criado com sucesso. "
            "Verifique seu e-mail para ativar a conta."
        ),
        usuario_id=result["usuario_id"],
        email_verificacao_enviado=True,
    )


# ─── Login ───────────────────────────────────────────────────────────────────

@router.post("/login", response_model=TokenResponse)
async def login(
    body: LoginRequest,
    request: Request,
    conn: Connection = Depends(get_db),
):
    """
    Autentica usuário com e-mail + senha.
    Retorna par de tokens (access + refresh).
    """
    ip = _get_ip(request)
    await _verificar_rate_limit(conn, ip)

    result = await conn.fetchrow(
        "SELECT * FROM auth.verificar_senha($1, $2)",
        body.email.lower(),
        body.senha,
    )

    if not result or not result["autenticado"]:
        await _registrar_falha(conn, ip, body.email.lower())
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="E-mail ou senha incorretos",
        )

    user_id = result["usuario_id"]
    role    = UserRole(result["role"])

    return await _emitir_tokens(conn, user_id, role, body.email.lower(), request)


# ─── Verificação de E-mail ────────────────────────────────────────────────────

@router.get("/verificar-email/{token}")
async def verificar_email(
    token: str,
    conn: Connection = Depends(get_db),
):
    """Ativa conta após clique no link de verificação enviado por e-mail."""
    result = await conn.fetchrow(
        "SELECT * FROM auth.verificar_email($1)", token
    )
    if not result or not result["verificado"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Token inválido ou expirado",
        )
    return {"mensagem": "E-mail verificado com sucesso. Sua conta está ativa."}


# ─── Refresh de Token ────────────────────────────────────────────────────────

@router.post("/refresh", response_model=TokenResponse)
async def refresh(
    body: RefreshRequest,
    request: Request,
    conn: Connection = Depends(get_db),
):
    """
    Troca refresh token por novo par de tokens (rotação automática).
    O token antigo é revogado imediatamente após uso.
    """
    token_hash = hashlib.sha256(body.refresh_token.encode()).hexdigest()

    row = await conn.fetchrow(
        """
        SELECT rt.id, rt.user_id, rt.expirado_em, rt.revogado,
               u.role, u.email, u.status
          FROM auth.refresh_tokens rt
          JOIN auth.users u ON u.id = rt.user_id
         WHERE rt.token_hash = $1
        """,
        token_hash,
    )

    if not row:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token inválido",
        )
    if row["revogado"]:
        # Possível token replay — revogar todos os tokens do usuário (segurança)
        await conn.execute(
            "UPDATE auth.refresh_tokens SET revogado = TRUE WHERE user_id = $1",
            row["user_id"],
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token já utilizado. Todos os tokens foram invalidados por segurança.",
        )
    if row["expirado_em"] < datetime.now(timezone.utc):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token expirado. Faça login novamente.",
        )
    if row["status"] != "active":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Conta suspensa ou inativa",
        )

    # Revogar token atual (rotação)
    await conn.execute(
        "UPDATE auth.refresh_tokens SET revogado = TRUE WHERE id = $1",
        row["id"],
    )

    return await _emitir_tokens(
        conn,
        row["user_id"],
        UserRole(row["role"]),
        row["email"],
        request,
    )


# ─── Logout ──────────────────────────────────────────────────────────────────

@router.post("/logout")
async def logout(
    body: RefreshRequest,
    conn: Connection = Depends(get_db),
    current_user: UserPublic = Depends(get_current_user),
):
    """Revoga o refresh token fornecido (logout de um dispositivo)."""
    token_hash = hashlib.sha256(body.refresh_token.encode()).hexdigest()
    await conn.execute(
        """
        UPDATE auth.refresh_tokens
           SET revogado = TRUE
         WHERE token_hash = $1 AND user_id = $2
        """,
        token_hash,
        current_user.id,
    )
    return {"mensagem": "Logout realizado com sucesso"}


@router.post("/logout-all")
async def logout_all(
    conn: Connection = Depends(get_db),
    current_user: UserPublic = Depends(get_current_user),
):
    """Revoga TODOS os refresh tokens do usuário (logout de todos os dispositivos)."""
    await conn.execute(
        "UPDATE auth.refresh_tokens SET revogado = TRUE WHERE user_id = $1",
        current_user.id,
    )
    return {"mensagem": "Logout realizado em todos os dispositivos"}


# ─── Perfil ───────────────────────────────────────────────────────────────────

@router.get("/me", response_model=UserPublic)
async def me(current_user: UserPublic = Depends(get_current_user)):
    """Retorna dados do usuário autenticado."""
    return current_user


@router.put("/me/senha")
async def alterar_senha(
    body: AlterarSenhaRequest,
    conn: Connection = Depends(get_db),
    current_user: UserPublic = Depends(get_current_user),
):
    """Altera a senha do usuário autenticado."""
    # Verifica senha atual
    result = await conn.fetchrow(
        "SELECT autenticado FROM auth.verificar_senha($1, $2)",
        current_user.email,
        body.senha_atual,
    )
    if not result or not result["autenticado"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Senha atual incorreta",
        )

    # Atualiza com bcrypt
    await conn.execute(
        """
        UPDATE auth.users
           SET senha_hash = crypt($1, gen_salt('bf', 12)),
               atualizado_em = NOW()
         WHERE id = $2
        """,
        body.nova_senha,
        current_user.id,
    )

    # Revogar todos os refresh tokens (forçar re-login nos outros dispositivos)
    await conn.execute(
        "UPDATE auth.refresh_tokens SET revogado = TRUE WHERE user_id = $1",
        current_user.id,
    )

    return {"mensagem": "Senha alterada com sucesso. Faça login novamente nos outros dispositivos."}
