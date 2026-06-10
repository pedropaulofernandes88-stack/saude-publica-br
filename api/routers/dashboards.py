"""
api/routers/dashboards.py
CRUD de dashboards e widgets personalizados do usuário.
"""

from __future__ import annotations

import json
from typing import List, Optional
from uuid import UUID

from asyncpg import Connection
from fastapi import APIRouter, Depends, HTTPException, Query, status

from api.database import get_db
from api.middleware.auth import get_current_user, get_optional_user
from api.models.user import (
    DashboardCreate,
    DashboardListItem,
    DashboardResponse,
    UserPublic,
    WidgetCreate,
    WidgetType,
)

router = APIRouter(prefix="/dashboards", tags=["Dashboards"])


# ─── Helpers ─────────────────────────────────────────────────────────────────

async def _get_dashboard_or_404(
    conn: Connection,
    dashboard_id: UUID,
    user_id: Optional[UUID] = None,
) -> dict:
    """Busca dashboard; lança 404 se não existir ou sem acesso."""
    row = await conn.fetchrow(
        """
        SELECT d.id, d.user_id, d.titulo, d.descricao, d.publico,
               d.slug, d.config, d.thumbnail_url,
               d.criado_em, d.atualizado_em,
               u.nome AS autor_nome
          FROM public.dashboards d
          JOIN auth.users u ON u.id = d.user_id
         WHERE d.id = $1
           AND (d.publico = TRUE OR d.user_id = $2)
        """,
        dashboard_id,
        user_id,
    )
    if not row:
        raise HTTPException(status_code=404, detail="Dashboard não encontrado")
    return dict(row)


async def _get_widgets(conn: Connection, dashboard_id: UUID) -> List[dict]:
    rows = await conn.fetch(
        """
        SELECT id, tipo, titulo, posicao, fonte, filtros,
               config, ordem, criado_em
          FROM public.dashboard_widgets
         WHERE dashboard_id = $1
         ORDER BY ordem ASC, criado_em ASC
        """,
        dashboard_id,
    )
    return [dict(r) for r in rows]


def _dashboard_to_response(dash: dict, widgets: List[dict]) -> DashboardResponse:
    return DashboardResponse(
        id=dash["id"],
        user_id=dash["user_id"],
        autor_nome=dash.get("autor_nome", ""),
        titulo=dash["titulo"],
        descricao=dash.get("descricao"),
        publico=dash["publico"],
        slug=dash["slug"],
        config=dash["config"] or {},
        thumbnail_url=dash.get("thumbnail_url"),
        criado_em=dash["criado_em"],
        atualizado_em=dash["atualizado_em"],
        widgets=widgets,
    )


# ─── Listar Dashboards ────────────────────────────────────────────────────────

@router.get("", response_model=List[DashboardListItem])
async def listar_dashboards(
    publico: Optional[bool] = Query(None, description="Filtrar por visibilidade"),
    busca: Optional[str]   = Query(None, description="Busca por título"),
    limite: int            = Query(20, ge=1, le=100),
    offset: int            = Query(0, ge=0),
    conn: Connection       = Depends(get_db),
    current_user: Optional[UserPublic] = Depends(get_optional_user),
):
    """
    Lista dashboards disponíveis.
    - Sem autenticação: apenas dashboards públicos.
    - Autenticado: dashboards públicos + os próprios.
    """
    user_id = current_user.id if current_user else None

    conditions = ["(d.publico = TRUE OR d.user_id = $1)"]
    params: list = [user_id]
    idx = 2

    if publico is not None:
        conditions.append(f"d.publico = ${idx}")
        params.append(publico)
        idx += 1
        if publico is False and user_id:
            # dashboards privados apenas do próprio usuário
            conditions.append(f"d.user_id = ${idx}")
            params.append(user_id)
            idx += 1

    if busca:
        conditions.append(f"d.titulo ILIKE ${idx}")
        params.append(f"%{busca}%")
        idx += 1

    where = " AND ".join(conditions)
    rows = await conn.fetch(
        f"""
        SELECT d.id, d.user_id, d.titulo, d.descricao, d.publico,
               d.slug, d.thumbnail_url, d.criado_em, d.atualizado_em,
               u.nome AS autor_nome,
               (SELECT COUNT(*) FROM public.dashboard_widgets w WHERE w.dashboard_id = d.id) AS total_widgets,
               (SELECT COUNT(*) FROM public.dashboard_favoritos f WHERE f.dashboard_id = d.id) AS total_favoritos
          FROM public.dashboards d
          JOIN auth.users u ON u.id = d.user_id
         WHERE {where}
         ORDER BY d.atualizado_em DESC
         LIMIT ${idx} OFFSET ${idx+1}
        """,
        *params, limite, offset,
    )

    return [
        DashboardListItem(
            id=r["id"],
            user_id=r["user_id"],
            autor_nome=r["autor_nome"],
            titulo=r["titulo"],
            descricao=r.get("descricao"),
            publico=r["publico"],
            slug=r["slug"],
            thumbnail_url=r.get("thumbnail_url"),
            total_widgets=r["total_widgets"],
            total_favoritos=r["total_favoritos"],
            criado_em=r["criado_em"],
            atualizado_em=r["atualizado_em"],
        )
        for r in rows
    ]


# ─── Criar Dashboard ──────────────────────────────────────────────────────────

@router.post("", response_model=DashboardResponse, status_code=201)
async def criar_dashboard(
    body: DashboardCreate,
    conn: Connection       = Depends(get_db),
    current_user: UserPublic = Depends(get_current_user),
):
    """Cria novo dashboard para o usuário autenticado."""
    # Verificar slug único
    if body.slug:
        existing = await conn.fetchval(
            "SELECT id FROM public.dashboards WHERE slug = $1", body.slug
        )
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Slug '{body.slug}' já está em uso",
            )

    slug = body.slug or str(uuid4())[:8]

    dash_id = await conn.fetchval(
        """
        INSERT INTO public.dashboards
               (user_id, titulo, descricao, publico, slug, config)
        VALUES ($1, $2, $3, $4, $5, $6::jsonb)
        RETURNING id
        """,
        current_user.id,
        body.titulo,
        body.descricao,
        body.publico,
        slug,
        json.dumps(body.config),
    )

    # Inserir widgets, se fornecidos
    if body.widgets:
        for i, w in enumerate(body.widgets):
            await conn.execute(
                """
                INSERT INTO public.dashboard_widgets
                       (dashboard_id, tipo, titulo, posicao, fonte, filtros, config, ordem)
                VALUES ($1, $2::widget_type, $3, $4::jsonb, $5, $6::jsonb, $7::jsonb, $8)
                """,
                dash_id,
                w.tipo.value,
                w.titulo,
                json.dumps(w.posicao.model_dump()),
                w.fonte,
                json.dumps(w.filtros),
                json.dumps(w.config),
                w.ordem if w.ordem is not None else i,
            )

    dash = await _get_dashboard_or_404(conn, dash_id, current_user.id)
    widgets = await _get_widgets(conn, dash_id)
    return _dashboard_to_response(dash, widgets)


# ─── Buscar por Slug ──────────────────────────────────────────────────────────

@router.get("/slug/{slug}", response_model=DashboardResponse)
async def get_dashboard_por_slug(
    slug: str,
    conn: Connection = Depends(get_db),
    current_user: Optional[UserPublic] = Depends(get_optional_user),
):
    """Busca dashboard pelo slug amigável."""
    user_id = current_user.id if current_user else None
    row = await conn.fetchrow(
        """
        SELECT d.id, d.user_id, d.titulo, d.descricao, d.publico,
               d.slug, d.config, d.thumbnail_url,
               d.criado_em, d.atualizado_em,
               u.nome AS autor_nome
          FROM public.dashboards d
          JOIN auth.users u ON u.id = d.user_id
         WHERE d.slug = $1
           AND (d.publico = TRUE OR d.user_id = $2)
        """,
        slug,
        user_id,
    )
    if not row:
        raise HTTPException(status_code=404, detail="Dashboard não encontrado")

    dash = dict(row)
    widgets = await _get_widgets(conn, dash["id"])
    return _dashboard_to_response(dash, widgets)


# ─── Buscar por ID ────────────────────────────────────────────────────────────

@router.get("/{dashboard_id}", response_model=DashboardResponse)
async def get_dashboard(
    dashboard_id: UUID,
    conn: Connection = Depends(get_db),
    current_user: Optional[UserPublic] = Depends(get_optional_user),
):
    user_id = current_user.id if current_user else None
    dash = await _get_dashboard_or_404(conn, dashboard_id, user_id)
    widgets = await _get_widgets(conn, dashboard_id)
    return _dashboard_to_response(dash, widgets)


# ─── Atualizar Dashboard ──────────────────────────────────────────────────────

@router.patch("/{dashboard_id}", response_model=DashboardResponse)
async def atualizar_dashboard(
    dashboard_id: UUID,
    body: DashboardCreate,
    conn: Connection       = Depends(get_db),
    current_user: UserPublic = Depends(get_current_user),
):
    """Atualiza metadados do dashboard (apenas o dono)."""
    existing = await conn.fetchrow(
        "SELECT id, user_id FROM public.dashboards WHERE id = $1", dashboard_id
    )
    if not existing:
        raise HTTPException(status_code=404, detail="Dashboard não encontrado")
    if existing["user_id"] != current_user.id:
        raise HTTPException(status_code=403, detail="Sem permissão para editar este dashboard")

    await conn.execute(
        """
        UPDATE public.dashboards
           SET titulo = $1, descricao = $2, publico = $3,
               config = $4::jsonb, atualizado_em = NOW()
         WHERE id = $5
        """,
        body.titulo,
        body.descricao,
        body.publico,
        json.dumps(body.config),
        dashboard_id,
    )

    dash = await _get_dashboard_or_404(conn, dashboard_id, current_user.id)
    widgets = await _get_widgets(conn, dashboard_id)
    return _dashboard_to_response(dash, widgets)


# ─── Excluir Dashboard ────────────────────────────────────────────────────────

@router.delete("/{dashboard_id}", status_code=204)
async def excluir_dashboard(
    dashboard_id: UUID,
    conn: Connection       = Depends(get_db),
    current_user: UserPublic = Depends(get_current_user),
):
    existing = await conn.fetchrow(
        "SELECT user_id FROM public.dashboards WHERE id = $1", dashboard_id
    )
    if not existing:
        raise HTTPException(status_code=404, detail="Dashboard não encontrado")
    if existing["user_id"] != current_user.id:
        raise HTTPException(status_code=403, detail="Sem permissão")

    await conn.execute("DELETE FROM public.dashboards WHERE id = $1", dashboard_id)


# ─── Widgets ──────────────────────────────────────────────────────────────────

@router.post("/{dashboard_id}/widgets", status_code=201)
async def adicionar_widget(
    dashboard_id: UUID,
    body: WidgetCreate,
    conn: Connection       = Depends(get_db),
    current_user: UserPublic = Depends(get_current_user),
):
    """Adiciona widget ao dashboard do usuário."""
    existing = await conn.fetchrow(
        "SELECT user_id FROM public.dashboards WHERE id = $1", dashboard_id
    )
    if not existing or existing["user_id"] != current_user.id:
        raise HTTPException(status_code=403, detail="Sem permissão")

    widget_id = await conn.fetchval(
        """
        INSERT INTO public.dashboard_widgets
               (dashboard_id, tipo, titulo, posicao, fonte, filtros, config, ordem)
        VALUES ($1, $2::widget_type, $3, $4::jsonb, $5, $6::jsonb, $7::jsonb, $8)
        RETURNING id
        """,
        dashboard_id,
        body.tipo.value,
        body.titulo,
        json.dumps(body.posicao.model_dump()),
        body.fonte,
        json.dumps(body.filtros),
        json.dumps(body.config),
        body.ordem or 0,
    )
    return {"widget_id": widget_id, "mensagem": "Widget adicionado"}


@router.delete("/{dashboard_id}/widgets/{widget_id}", status_code=204)
async def remover_widget(
    dashboard_id: UUID,
    widget_id: UUID,
    conn: Connection       = Depends(get_db),
    current_user: UserPublic = Depends(get_current_user),
):
    existing = await conn.fetchrow(
        "SELECT d.user_id FROM public.dashboard_widgets w JOIN public.dashboards d ON d.id = w.dashboard_id WHERE w.id = $1 AND w.dashboard_id = $2",
        widget_id, dashboard_id,
    )
    if not existing or existing["user_id"] != current_user.id:
        raise HTTPException(status_code=403, detail="Sem permissão")
    await conn.execute(
        "DELETE FROM public.dashboard_widgets WHERE id = $1", widget_id
    )


# ─── Favoritos ────────────────────────────────────────────────────────────────

@router.post("/{dashboard_id}/favoritar", status_code=201)
async def favoritar(
    dashboard_id: UUID,
    conn: Connection       = Depends(get_db),
    current_user: UserPublic = Depends(get_current_user),
):
    await conn.execute(
        """
        INSERT INTO public.dashboard_favoritos (user_id, dashboard_id)
        VALUES ($1, $2) ON CONFLICT DO NOTHING
        """,
        current_user.id, dashboard_id,
    )
    return {"mensagem": "Dashboard favoritado"}


@router.delete("/{dashboard_id}/favoritar", status_code=204)
async def desfavoritar(
    dashboard_id: UUID,
    conn: Connection       = Depends(get_db),
    current_user: UserPublic = Depends(get_current_user),
):
    await conn.execute(
        "DELETE FROM public.dashboard_favoritos WHERE user_id = $1 AND dashboard_id = $2",
        current_user.id, dashboard_id,
    )
