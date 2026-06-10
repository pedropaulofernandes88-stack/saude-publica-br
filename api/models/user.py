"""
Modelos Pydantic para autenticação e usuários.
Fase 11 — Portal Público com Autenticação
"""
from __future__ import annotations

import re
from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field, field_validator


# ────────────────────────────────────────────────────────────
# ENUMS
# ────────────────────────────────────────────────────────────

class UserRole(str, Enum):
    viewer = "viewer"
    analyst = "analyst"
    admin = "admin"


class UserStatus(str, Enum):
    pending = "pending"
    active = "active"
    suspended = "suspended"


class WidgetType(str, Enum):
    bar_chart = "bar_chart"
    line_chart = "line_chart"
    area_chart = "area_chart"
    pie_chart = "pie_chart"
    map_choropleth = "map_choropleth"
    kpi_card = "kpi_card"
    data_table = "data_table"
    ranking_table = "ranking_table"


class ExportFormat(str, Enum):
    csv = "csv"
    excel = "excel"
    json = "json"


# ────────────────────────────────────────────────────────────
# VALIDADORES REUTILIZÁVEIS
# ────────────────────────────────────────────────────────────

_SENHA_RE = re.compile(r'^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*#?&]).{8,}$')


def _validar_senha(v: str) -> str:
    if not _SENHA_RE.match(v):
        raise ValueError(
            "Senha deve ter mínimo 8 caracteres, "
            "com maiúscula, minúscula, número e caractere especial."
        )
    return v


# ────────────────────────────────────────────────────────────
# REQUESTS — Auth
# ────────────────────────────────────────────────────────────

class RegisterRequest(BaseModel):
    email: EmailStr
    nome: str = Field(..., min_length=3, max_length=100)
    senha: str = Field(..., min_length=8, max_length=128)
    confirmar_senha: str

    @field_validator("nome")
    @classmethod
    def nome_strip(cls, v: str) -> str:
        return v.strip()

    @field_validator("senha")
    @classmethod
    def senha_forte(cls, v: str) -> str:
        return _validar_senha(v)

    def model_post_init(self, __context) -> None:
        if self.senha != self.confirmar_senha:
            raise ValueError("Senhas não conferem.")


class LoginRequest(BaseModel):
    email: EmailStr
    senha: str


class RefreshRequest(BaseModel):
    refresh_token: str


class AlterarSenhaRequest(BaseModel):
    senha_atual: str
    nova_senha: str = Field(..., min_length=8, max_length=128)
    confirmar_nova_senha: str

    @field_validator("nova_senha")
    @classmethod
    def nova_senha_forte(cls, v: str) -> str:
        return _validar_senha(v)

    def model_post_init(self, __context) -> None:
        if self.nova_senha != self.confirmar_nova_senha:
            raise ValueError("Senhas não conferem.")


# ────────────────────────────────────────────────────────────
# RESPONSES — Auth & Usuário
# ────────────────────────────────────────────────────────────

class UserPublic(BaseModel):
    """Representação pública do usuário (sem dados sensíveis)."""
    id: UUID
    email: str
    nome: str
    role: UserRole
    status: UserStatus
    email_verificado: bool
    ultimo_login: Optional[datetime]
    criado_em: datetime

    model_config = {"from_attributes": True}


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "Bearer"
    expires_in: int           # segundos até expirar o access_token
    usuario: UserPublic


class RegisterResponse(BaseModel):
    mensagem: str
    usuario_id: UUID
    email_verificacao_enviado: bool


# ────────────────────────────────────────────────────────────
# REQUESTS/RESPONSES — Dashboards
# ────────────────────────────────────────────────────────────

class WidgetPositionConfig(BaseModel):
    x: int = Field(0, ge=0, le=11)
    y: int = Field(0, ge=0)
    w: int = Field(6, ge=1, le=12)
    h: int = Field(4, ge=2)


class WidgetCreate(BaseModel):
    tipo: WidgetType
    titulo: str = Field(..., min_length=1, max_length=120)
    posicao: WidgetPositionConfig = WidgetPositionConfig()
    fonte: str = Field(
        ...,
        pattern=r'^(producao|mortalidade|capacidade|doencas|ranking)$'
    )
    filtros: dict = Field(default_factory=dict)
    config: dict = Field(default_factory=dict)
    ordem: int = Field(0, ge=0)


class WidgetResponse(BaseModel):
    id: UUID
    dashboard_id: UUID
    tipo: WidgetType
    titulo: str
    posicao: dict
    fonte: str
    filtros: dict
    config: dict
    ordem: int
    criado_em: datetime

    model_config = {"from_attributes": True}


class DashboardCreate(BaseModel):
    titulo: str = Field(..., min_length=1, max_length=200)
    descricao: Optional[str] = Field(None, max_length=500)
    publico: bool = False
    slug: Optional[str] = Field(
        None,
        pattern=r'^[a-z0-9-]{3,80}$',
        description="Slug único para URL pública (apenas letras, números e hífens)"
    )
    config: dict = Field(
        default_factory=dict,
        description="Filtros globais padrão: {ufs, anos, meses, regioes}"
    )
    widgets: list[WidgetCreate] = Field(default_factory=list)


class DashboardUpdate(BaseModel):
    titulo: Optional[str] = Field(None, min_length=1, max_length=200)
    descricao: Optional[str] = None
    publico: Optional[bool] = None
    slug: Optional[str] = Field(None, pattern=r'^[a-z0-9-]{3,80}$')
    config: Optional[dict] = None


class DashboardResponse(BaseModel):
    id: UUID
    user_id: UUID
    titulo: str
    descricao: Optional[str]
    publico: bool
    slug: Optional[str]
    config: dict
    thumbnail_url: Optional[str]
    criado_em: datetime
    atualizado_em: datetime
    widgets: list[WidgetResponse] = []
    total_widgets: int = 0
    favoritado: bool = False

    model_config = {"from_attributes": True}


class DashboardListItem(BaseModel):
    """Item resumido para listagem de dashboards."""
    id: UUID
    titulo: str
    descricao: Optional[str]
    publico: bool
    slug: Optional[str]
    total_widgets: int
    criado_em: datetime
    atualizado_em: datetime
    favoritado: bool = False

    model_config = {"from_attributes": True}


# ────────────────────────────────────────────────────────────
# REQUESTS/RESPONSES — Exportações
# ────────────────────────────────────────────────────────────

class ExportRequest(BaseModel):
    endpoint: str = Field(
        ...,
        pattern=r'^nacional/(producao|mortalidade|capacidade|doencas|ranking)$'
    )
    formato: ExportFormat
    filtros: dict = Field(default_factory=dict)


class ExportResponse(BaseModel):
    export_id: UUID
    status: str
    mensagem: str
    download_url: Optional[str] = None
    total_linhas: Optional[int] = None
    tamanho_bytes: Optional[int] = None
