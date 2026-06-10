"""
Router: Epidemiologia / CID-10 (/epidemiologia)

Endpoints:
  GET /epidemiologia/cid10               — distribuição por capítulo CID-10
  GET /epidemiologia/cid10/{uf_sigla}    — detalhe por UF com série anual
"""
from __future__ import annotations

import math
from typing import Annotated

import asyncpg
from fastapi import APIRouter, Depends, Query

from api.cache import TTL_EPI
from api.database import fetch_paginated, get_db
from api.schemas import EpiCid10Item, EpiCid10Response, PaginacaoMeta

router = APIRouter(prefix="/epidemiologia", tags=["Epidemiologia CID-10"])


# ---------------------------------------------------------------------------
# GET /epi/cid10
# ---------------------------------------------------------------------------


@router.get(
    "/cid10",
    response_model=EpiCid10Response,
    summary="Distribuição de procedimentos por capítulo CID-10",
)
async def listar_epi_cid10(
    uf_sigla: Annotated[str | None, Query(min_length=2, max_length=2)] = None,
    ano: Annotated[int | None, Query(ge=2000, le=2030)] = None,
    capitulo: Annotated[str | None, Query(description="Código do capítulo CID-10 (ex: I, II, X)")] = None,
    top_n: Annotated[int | None, Query(ge=1, le=50, description="Retorna apenas os N capítulos mais frequentes")] = None,
    pagina: Annotated[int, Query(ge=1)] = 1,
    por_pagina: Annotated[int, Query(ge=1, le=500)] = 50,
    db: asyncpg.Connection = Depends(get_db),
) -> EpiCid10Response:
    """
    Perfil epidemiológico por capítulo CID-10 (grupos de procedimentos/diagnósticos).

    Use `top_n` para obter apenas os N capítulos mais frequentes por UF/ano.
    """
    conditions: list[str] = []
    filter_params: list = []   # params usados APENAS nos filtros WHERE (uf/ano/capitulo)
    idx = 1

    if uf_sigla:
        conditions.append(f"uf_sigla = ${idx}")
        filter_params.append(uf_sigla.upper())
        idx += 1
    if ano:
        conditions.append(f"ano = ${idx}")
        filter_params.append(ano)
        idx += 1
    if capitulo:
        conditions.append(f"capitulo_cid10 = ${idx}")
        filter_params.append(capitulo.upper())
        idx += 1

    where = f"WHERE {' AND '.join(conditions)}" if conditions else ""

    # top_n: aplica SOMENTE em base_q; count_q usa apenas filter_params
    # para reportar o total real de capítulos, não apenas os top_n.
    top_filter = ""
    data_params = list(filter_params)   # cópia; receberá top_n se presente
    if top_n:
        top_filter = f"AND rank_capitulo_uf <= ${idx}"
        data_params.append(top_n)
        # idx não precisa avançar além daqui

    base_q = f"""
        SELECT
            uf_sigla, ano, capitulo_cid10, descricao_capitulo,
            total_procedimentos, pct_atend_uf,
            rank_capitulo_uf, variacao_anual_pct
        FROM mart_epi_cid10
        {where}
        {"AND" if where else "WHERE"} 1=1 {top_filter}
        ORDER BY uf_sigla ASC, ano DESC, rank_capitulo_uf ASC
    """

    # count_q usa somente filter_params (sem top_n) para total real de capítulos
    count_q = f"SELECT COUNT(*) FROM mart_epi_cid10 {where}"
    rows, total = await fetch_paginated(
        db, base_q, count_q, data_params, pagina, por_pagina,
        count_params=filter_params,
    )

    return EpiCid10Response(
        data=[EpiCid10Item(**dict(r)) for r in rows],
        paginacao=PaginacaoMeta(
            total=total, pagina=pagina, por_pagina=por_pagina,
            paginas=max(1, math.ceil(total / por_pagina)),
        ),
    )


# ---------------------------------------------------------------------------
# GET /epi/cid10/{uf_sigla}
# ---------------------------------------------------------------------------


@router.get(
    "/cid10/{uf_sigla}",
    response_model=EpiCid10Response,
    summary="Perfil CID-10 de uma UF com comparação anual",
)
async def epi_cid10_uf(
    uf_sigla: str,
    top: Annotated[int, Query(ge=1, le=20, description="Top N capítulos")] = 10,
    db: asyncpg.Connection = Depends(get_db),
) -> EpiCid10Response:
    """
    Retorna os N capítulos CID-10 mais frequentes de uma UF,
    com variação anual para identificar tendências.
    """
    query = """
        SELECT
            uf_sigla, ano, capitulo_cid10, descricao_capitulo,
            total_procedimentos, pct_atend_uf,
            rank_capitulo_uf, variacao_anual_pct
        FROM mart_epi_cid10
        WHERE uf_sigla = $1
          AND rank_capitulo_uf <= $2
        ORDER BY ano DESC, rank_capitulo_uf ASC
    """
    rows = await db.fetch(query, uf_sigla.upper(), top)
    total = len(rows)

    return EpiCid10Response(
        data=[EpiCid10Item(**dict(r)) for r in rows],
        paginacao=PaginacaoMeta(
            total=total, pagina=1, por_pagina=total or 1,
            paginas=1,
        ),
    )
