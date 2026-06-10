"""
Router: Ranking de municípios (/ranking)

Endpoints:
  GET /ranking/nacional           — top N municípios a nível nacional
  GET /ranking/{uf_sigla}         — ranking de municípios de uma UF

IMPORTANTE: /nacional deve vir antes de /{uf_sigla} para evitar que
FastAPI capture "nacional" como valor do path param uf_sigla.
"""
from __future__ import annotations

import math
from typing import Annotated

import asyncpg
from fastapi import APIRouter, Depends, Query

from api.cache import TTL_RANKING
from api.database import fetch_paginated, get_db
from api.schemas import PaginacaoMeta, RankingMunicipioItem, RankingResponse

router = APIRouter(prefix="/ranking", tags=["Ranking de Municípios"])


# ---------------------------------------------------------------------------
# GET /ranking/nacional  (deve vir ANTES de /{uf_sigla})
# ---------------------------------------------------------------------------


@router.get(
    "/nacional",
    response_model=RankingResponse,
    summary="Top N municípios com melhor/pior acesso no Brasil",
)
async def ranking_nacional(
    ano: Annotated[int, Query(ge=2000, le=2030)] = 2024,
    top: Annotated[int, Query(ge=1, le=200, description="Número de municípios")] = 100,
    ordem: Annotated[str, Query(description="melhor | pior")] = "melhor",
    db: asyncpg.Connection = Depends(get_db),
) -> RankingResponse:
    """
    Retorna os `top` municípios com melhor ou pior score de acesso no Brasil.
    """
    order_dir = "ASC" if ordem == "melhor" else "DESC"

    query = f"""
        SELECT
            municipio_cod, municipio_nome, uf_sigla, ano,
            score_acesso, ranking_estadual, ranking_nacional,
            percentil_estadual, percentil_nacional, categoria
        FROM mart_ranking_municipios
        WHERE ano = $1
        ORDER BY ranking_nacional {order_dir} NULLS LAST
        LIMIT $2
    """
    rows = await db.fetch(query, ano, top)
    total = len(rows)

    return RankingResponse(
        uf_sigla="BR",
        ano=ano,
        data=[RankingMunicipioItem(**dict(r)) for r in rows],
        paginacao=PaginacaoMeta(
            total=total, pagina=1, por_pagina=top,
            paginas=1,
        ),
    )


# ---------------------------------------------------------------------------
# GET /ranking/{uf_sigla}
# ---------------------------------------------------------------------------


@router.get(
    "/{uf_sigla}",
    response_model=RankingResponse,
    summary="Ranking de municípios de uma UF por acesso ambulatorial",
)
async def ranking_uf(
    uf_sigla: str,
    ano: Annotated[int, Query(ge=2000, le=2030)] = 2024,
    pagina: Annotated[int, Query(ge=1)] = 1,
    por_pagina: Annotated[int, Query(ge=1, le=500)] = 100,
    db: asyncpg.Connection = Depends(get_db),
) -> RankingResponse:
    """
    Retorna o ranking de todos os municípios de uma UF
    ordenado por score de acesso (melhor → pior).
    """
    base_q = """
        SELECT
            municipio_cod, municipio_nome, uf_sigla, ano,
            score_acesso, ranking_estadual, ranking_nacional,
            percentil_estadual, percentil_nacional, categoria
        FROM mart_ranking_municipios
        WHERE uf_sigla = $1 AND ano = $2
        ORDER BY ranking_estadual ASC
    """
    count_q = """
        SELECT COUNT(*) FROM mart_ranking_municipios
        WHERE uf_sigla = $1 AND ano = $2
    """
    rows, total = await fetch_paginated(
        db, base_q, count_q, [uf_sigla.upper(), ano], pagina, por_pagina
    )

    return RankingResponse(
        uf_sigla=uf_sigla.upper(),
        ano=ano,
        data=[RankingMunicipioItem(**dict(r)) for r in rows],
        paginacao=PaginacaoMeta(
            total=total, pagina=pagina, por_pagina=por_pagina,
            paginas=max(1, math.ceil(total / por_pagina)),
        ),
    )
