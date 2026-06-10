"""
Router: Mortalidade (/mortalidade)

Endpoints:
  GET /mortalidade                         — lista de registros paginados
  GET /mortalidade/uf/{uf_sigla}           — resumo anual por UF
  GET /mortalidade/municipio/{cod}         — série temporal de um município
  GET /mortalidade/ranking                 — municípios por taxa de mortalidade
"""
from __future__ import annotations

import math
from typing import Annotated

import asyncpg
from fastapi import APIRouter, Depends, HTTPException, Query

from api.cache import TTL_EPI
from api.database import fetch_paginated, get_db, records_to_list
from api.schemas import (
    MortalidadeItem,
    MortalidadeResponse,
    MortalidadeSerieItem,
    MortalidadeSerieResponse,
    PaginacaoMeta,
)

router = APIRouter(prefix="/mortalidade", tags=["Mortalidade (SIM/DO)"])


# ---------------------------------------------------------------------------
# GET /mortalidade
# ---------------------------------------------------------------------------


@router.get(
    "",
    response_model=MortalidadeResponse,
    summary="Lista de mortalidade por município / causa / demográfico",
)
async def listar_mortalidade(
    uf_sigla: Annotated[str | None, Query(min_length=2, max_length=2)] = None,
    municipio_cod: Annotated[str | None, Query(min_length=6, max_length=7)] = None,
    ano_inicio: Annotated[int | None, Query(ge=2000, le=2030)] = None,
    ano_fim: Annotated[int | None, Query(ge=2000, le=2030)] = None,
    causabas_cap: Annotated[
        str | None,
        Query(min_length=1, max_length=1, description="Capítulo CID-10 (ex: I, J, C)"),
    ] = None,
    sexo: Annotated[str | None, Query(min_length=1, max_length=1)] = None,
    faixa_etaria: Annotated[str | None, Query(description="Ex: 0-4 | 5-14 | 15-29 | 30-59 | 60+ | TOTAL")] = None,
    apenas_totais: Annotated[
        bool,
        Query(description="Se True, retorna apenas linhas com sexo='TOTAL' e faixa_etaria='TOTAL'"),
    ] = False,
    pagina: Annotated[int, Query(ge=1)] = 1,
    por_pagina: Annotated[int, Query(ge=1, le=1000)] = 100,
    db: asyncpg.Connection = Depends(get_db),
) -> MortalidadeResponse:
    """
    Mortalidade agregada por município, causa básica (capítulo CID-10),
    sexo e faixa etária.

    Use `apenas_totais=true` para obter somente os subtotais (sem abertura
    por sexo/faixa_etaria), equivalente ao total geral por município/causa.
    """
    conditions: list[str] = []
    params: list = []
    idx = 1

    if uf_sigla:
        conditions.append(f"uf_sigla = ${idx}")
        params.append(uf_sigla.upper())
        idx += 1
    if municipio_cod:
        conditions.append(f"municipio_cod = ${idx}")
        params.append(municipio_cod.strip())
        idx += 1
    if ano_inicio:
        conditions.append(f"ano_obito >= ${idx}")
        params.append(ano_inicio)
        idx += 1
    if ano_fim:
        conditions.append(f"ano_obito <= ${idx}")
        params.append(ano_fim)
        idx += 1
    if causabas_cap:
        conditions.append(f"causabas_cap = ${idx}")
        params.append(causabas_cap.upper())
        idx += 1
    if sexo:
        conditions.append(f"sexo = ${idx}")
        params.append(sexo.upper())
        idx += 1
    if faixa_etaria:
        conditions.append(f"faixa_etaria = ${idx}")
        params.append(faixa_etaria)
        idx += 1
    if apenas_totais:
        conditions.append("sexo = 'TOTAL'")
        conditions.append("faixa_etaria = 'TOTAL'")

    where = f"WHERE {' AND '.join(conditions)}" if conditions else ""

    base_q = f"""
        SELECT
            municipio_cod, municipio_nome, uf_sigla, regiao,
            ano_obito, mes_obito, mes_competencia,
            causabas_cap, causabas_grupo,
            sexo, faixa_etaria,
            total_obitos, obitos_fetais, obitos_naofetais,
            obitos_hospital, obitos_domicilio, obitos_outros_local,
            populacao, taxa_mortalidade_bruta, pct_obitos_hospital
        FROM marts.mart_mortalidade
        {where}
        ORDER BY municipio_cod ASC, ano_obito DESC, mes_obito DESC NULLS LAST,
                 causabas_cap ASC NULLS LAST
    """
    count_q = f"SELECT COUNT(*) FROM marts.mart_mortalidade {where}"

    rows, total = await fetch_paginated(db, base_q, count_q, params, pagina, por_pagina)

    return MortalidadeResponse(
        data=[MortalidadeItem(**dict(r)) for r in rows],
        paginacao=PaginacaoMeta(
            total=total,
            pagina=pagina,
            por_pagina=por_pagina,
            paginas=max(1, math.ceil(total / por_pagina)),
        ),
    )


# ---------------------------------------------------------------------------
# GET /mortalidade/municipio/{municipio_cod}
# ---------------------------------------------------------------------------


@router.get(
    "/municipio/{municipio_cod}",
    response_model=MortalidadeSerieResponse,
    summary="Série temporal de mortalidade de um município",
)
async def serie_mortalidade_municipio(
    municipio_cod: str,
    causabas_cap: Annotated[
        str | None,
        Query(min_length=1, max_length=1, description="Filtrar por capítulo CID-10"),
    ] = None,
    db: asyncpg.Connection = Depends(get_db),
) -> MortalidadeSerieResponse:
    """
    Retorna a série temporal mensal de mortalidade (totais agregados)
    para um município.  Útil para construir gráficos de tendência.

    Por padrão retorna todos os capítulos somados (sexo=TOTAL, faixa_etaria=TOTAL).
    Use `causabas_cap` para filtrar um capítulo CID-10 específico.
    """
    params: list = [municipio_cod.strip()]
    extra = ""
    if causabas_cap:
        extra = "AND causabas_cap = $2"
        params.append(causabas_cap.upper())

    info_q = """
        SELECT municipio_nome, uf_sigla
        FROM marts.mart_mortalidade
        WHERE municipio_cod = $1
        LIMIT 1
    """
    info_row = await db.fetchrow(info_q, municipio_cod.strip())
    if info_row is None:
        raise HTTPException(status_code=404, detail=f"Município '{municipio_cod}' não encontrado.")

    serie_q = f"""
        SELECT
            mes_competencia, ano_obito, mes_obito,
            SUM(total_obitos)             AS total_obitos,
            MAX(taxa_mortalidade_bruta)   AS taxa_mortalidade_bruta
        FROM marts.mart_mortalidade
        WHERE municipio_cod = $1
          AND sexo = 'TOTAL'
          AND faixa_etaria = 'TOTAL'
          {extra}
        GROUP BY mes_competencia, ano_obito, mes_obito
        ORDER BY mes_competencia ASC
    """
    rows = await db.fetch(*([serie_q] + params))

    grupo_q = """
        SELECT DISTINCT causabas_cap, causabas_grupo
        FROM marts.mart_mortalidade
        WHERE municipio_cod = $1
          AND causabas_cap = $2
        LIMIT 1
    """
    grupo_info: dict = {}
    if causabas_cap:
        g = await db.fetchrow(grupo_q, municipio_cod.strip(), causabas_cap.upper())
        if g:
            grupo_info = dict(g)

    return MortalidadeSerieResponse(
        municipio_cod=municipio_cod.strip(),
        municipio_nome=info_row["municipio_nome"],
        uf_sigla=info_row["uf_sigla"],
        causabas_cap=causabas_cap,
        causabas_grupo=grupo_info.get("causabas_grupo"),
        serie=[MortalidadeSerieItem(**dict(r)) for r in rows],
    )


# ---------------------------------------------------------------------------
# GET /mortalidade/uf/{uf_sigla}
# ---------------------------------------------------------------------------


@router.get(
    "/uf/{uf_sigla}",
    response_model=MortalidadeResponse,
    summary="Mortalidade agregada por UF",
)
async def mortalidade_uf(
    uf_sigla: str,
    ano: Annotated[int | None, Query(ge=2000, le=2030)] = None,
    causabas_cap: Annotated[str | None, Query(min_length=1, max_length=1)] = None,
    pagina: Annotated[int, Query(ge=1)] = 1,
    por_pagina: Annotated[int, Query(ge=1, le=1000)] = 100,
    db: asyncpg.Connection = Depends(get_db),
) -> MortalidadeResponse:
    """
    Retorna dados de mortalidade de todos os municípios de uma UF,
    opcionalmente filtrados por ano e capítulo CID-10.
    """
    params: list = [uf_sigla.upper()]
    conditions = ["uf_sigla = $1", "sexo = 'TOTAL'", "faixa_etaria = 'TOTAL'"]
    idx = 2

    if ano:
        conditions.append(f"ano_obito = ${idx}")
        params.append(ano)
        idx += 1
    if causabas_cap:
        conditions.append(f"causabas_cap = ${idx}")
        params.append(causabas_cap.upper())
        idx += 1

    where = f"WHERE {' AND '.join(conditions)}"

    base_q = f"""
        SELECT
            municipio_cod, municipio_nome, uf_sigla, regiao,
            ano_obito, mes_obito, mes_competencia,
            causabas_cap, causabas_grupo,
            sexo, faixa_etaria,
            total_obitos, obitos_fetais, obitos_naofetais,
            obitos_hospital, obitos_domicilio, obitos_outros_local,
            populacao, taxa_mortalidade_bruta, pct_obitos_hospital
        FROM marts.mart_mortalidade
        {where}
        ORDER BY municipio_cod ASC, ano_obito DESC, causabas_cap ASC NULLS LAST
    """
    count_q = f"SELECT COUNT(*) FROM marts.mart_mortalidade {where}"

    rows, total = await fetch_paginated(db, base_q, count_q, params, pagina, por_pagina)

    return MortalidadeResponse(
        data=[MortalidadeItem(**dict(r)) for r in rows],
        paginacao=PaginacaoMeta(
            total=total,
            pagina=pagina,
            por_pagina=por_pagina,
            paginas=max(1, math.ceil(total / por_pagina)),
        ),
    )


# ---------------------------------------------------------------------------
# GET /mortalidade/ranking
# ---------------------------------------------------------------------------


@router.get(
    "/ranking",
    response_model=MortalidadeResponse,
    summary="Ranking de municípios por taxa de mortalidade",
)
async def ranking_mortalidade(
    uf_sigla: Annotated[str | None, Query(min_length=2, max_length=2)] = None,
    ano: Annotated[int | None, Query(ge=2000, le=2030)] = None,
    causabas_cap: Annotated[str | None, Query(min_length=1, max_length=1)] = None,
    top: Annotated[int, Query(ge=1, le=200, description="Número de municípios")] = 20,
    ordem: Annotated[str, Query(description="'desc' = maior taxa primeiro (padrão); 'asc' = menor taxa")] = "desc",
    db: asyncpg.Connection = Depends(get_db),
) -> MortalidadeResponse:
    """
    Municípios ordenados por taxa de mortalidade bruta (por 1.000 hab).

    Use `uf_sigla` para rankings estaduais; sem ela, o ranking é nacional.
    """
    if ordem not in ("asc", "desc"):
        raise HTTPException(status_code=422, detail="'ordem' deve ser 'asc' ou 'desc'.")

    params: list = []
    conditions = ["sexo = 'TOTAL'", "faixa_etaria = 'TOTAL'", "taxa_mortalidade_bruta IS NOT NULL"]
    idx = 1

    if uf_sigla:
        conditions.append(f"uf_sigla = ${idx}")
        params.append(uf_sigla.upper())
        idx += 1
    if ano:
        conditions.append(f"ano_obito = ${idx}")
        params.append(ano)
        idx += 1
    if causabas_cap:
        conditions.append(f"causabas_cap = ${idx}")
        params.append(causabas_cap.upper())
        idx += 1

    params.append(top)
    order_dir = "DESC" if ordem == "desc" else "ASC"
    where = f"WHERE {' AND '.join(conditions)}"

    query = f"""
        SELECT
            municipio_cod, municipio_nome, uf_sigla, regiao,
            ano_obito, mes_obito, mes_competencia,
            causabas_cap, causabas_grupo,
            sexo, faixa_etaria,
            total_obitos, obitos_fetais, obitos_naofetais,
            obitos_hospital, obitos_domicilio, obitos_outros_local,
            populacao, taxa_mortalidade_bruta, pct_obitos_hospital
        FROM marts.mart_mortalidade
        {where}
        ORDER BY taxa_mortalidade_bruta {order_dir}
        LIMIT ${idx}
    """
    rows = await db.fetch(query, *params)
    total = len(rows)

    return MortalidadeResponse(
        data=[MortalidadeItem(**dict(r)) for r in rows],
        paginacao=PaginacaoMeta(
            total=total, pagina=1, por_pagina=total or 1, paginas=1,
        ),
    )
