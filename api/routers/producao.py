"""
Router: Produção Ambulatorial (/producao)

Endpoints:
  GET /producao                         — lista paginada com filtros
  GET /producao/series/{municipio_cod}  — série temporal de um município
  GET /producao/mapa/{uf_sigla}         — dados para choropleth por UF
"""
from __future__ import annotations

import math
from typing import Annotated, Literal

import asyncpg
from fastapi import APIRouter, Depends, Query

from api.cache import TTL_MAPA, TTL_PRODUCAO, cached
from api.database import fetch_paginated, get_db, records_to_list
from api.schemas import (
    MapaMunicipioFeature,
    MapaResponse,
    PaginacaoMeta,
    ProducaoAmbItem,
    ProducaoAmbResponse,
    ProducaoSerieItem,
    ProducaoSerieResponse,
)

router = APIRouter(prefix="/producao", tags=["Produção Ambulatorial"])

# ---------------------------------------------------------------------------
# GET /producao
# ---------------------------------------------------------------------------


@router.get("", response_model=ProducaoAmbResponse, summary="Lista produção ambulatorial")
async def listar_producao(
    uf_sigla: Annotated[str | None, Query(min_length=2, max_length=2, description="Sigla da UF")] = None,
    municipio_cod: Annotated[str | None, Query(min_length=6, max_length=7)] = None,
    ano_inicio: Annotated[int | None, Query(ge=2000, le=2030)] = None,
    ano_fim: Annotated[int | None, Query(ge=2000, le=2030)] = None,
    mes_competencia: Annotated[str | None, Query(pattern=r"^\d{6}$")] = None,
    pagina: Annotated[int, Query(ge=1)] = 1,
    por_pagina: Annotated[int, Query(ge=1, le=500)] = 100,
    db: asyncpg.Connection = Depends(get_db),
) -> ProducaoAmbResponse:
    """
    Retorna produção ambulatorial (mart_producao_amb) com filtros opcionais.

    Filtra por UF, município, período e competência mensal.
    Ordenação padrão: uf_sigla ASC, mes_competencia DESC.
    """
    conditions = []
    params: list = []
    idx = 1

    if uf_sigla:
        conditions.append(f"uf_sigla = ${idx}")
        params.append(uf_sigla.upper())
        idx += 1
    if municipio_cod:
        conditions.append(f"municipio_cod = ${idx}")
        params.append(municipio_cod)
        idx += 1
    if mes_competencia:
        conditions.append(f"mes_competencia = ${idx}")
        params.append(mes_competencia)
        idx += 1
    if ano_inicio:
        conditions.append(f"ano >= ${idx}")
        params.append(ano_inicio)
        idx += 1
    if ano_fim:
        conditions.append(f"ano <= ${idx}")
        params.append(ano_fim)
        idx += 1

    where = f"WHERE {' AND '.join(conditions)}" if conditions else ""

    base_q = f"""
        SELECT municipio_cod, municipio_nome, uf_sigla,
               mes_competencia, ano, mes,
               total_procedimentos, total_aprovados,
               populacao, taxa_proc_10k, pct_aprovacao
        FROM mart_producao_amb
        {where}
        ORDER BY uf_sigla ASC, mes_competencia DESC, municipio_cod ASC
    """
    count_q = f"SELECT COUNT(*) FROM mart_producao_amb {where}"

    rows, total = await fetch_paginated(db, base_q, count_q, params, pagina, por_pagina)

    return ProducaoAmbResponse(
        data=[
            ProducaoAmbItem(
                municipio_cod=r["municipio_cod"],
                municipio_nome=r.get("municipio_nome"),
                uf_sigla=r["uf_sigla"],
                mes_competencia=str(r["mes_competencia"]),
                ano=r["ano"],
                mes=r["mes"],
                total_procedimentos=r["total_procedimentos"],
                total_aprovados=r["total_aprovados"],
                populacao=r.get("populacao"),
                taxa_proc_10k=r.get("taxa_proc_10k"),
                pct_aprovacao=r.get("pct_aprovacao"),
            )
            for r in rows
        ],
        paginacao=PaginacaoMeta(
            total=total,
            pagina=pagina,
            por_pagina=por_pagina,
            paginas=max(1, math.ceil(total / por_pagina)),
        ),
    )


# ---------------------------------------------------------------------------
# GET /producao/series/{municipio_cod}
# ---------------------------------------------------------------------------


@router.get(
    "/series/{municipio_cod}",
    response_model=ProducaoSerieResponse,
    summary="Série temporal de produção por município",
)
async def serie_producao(
    municipio_cod: str,
    ano_inicio: Annotated[int | None, Query(ge=2000, le=2030)] = None,
    ano_fim: Annotated[int | None, Query(ge=2000, le=2030)] = None,
    db: asyncpg.Connection = Depends(get_db),
) -> ProducaoSerieResponse:
    """
    Retorna a série temporal mensal de procedimentos de um município.
    Inclui variação percentual em relação ao mês anterior.
    """
    conditions = ["municipio_cod = $1"]
    params: list = [municipio_cod]
    idx = 2

    if ano_inicio:
        conditions.append(f"ano >= ${idx}")
        params.append(ano_inicio)
        idx += 1
    if ano_fim:
        conditions.append(f"ano <= ${idx}")
        params.append(ano_fim)
        idx += 1

    where = " AND ".join(conditions)

    # Usa LAG para calcular variação mês a mês
    query = f"""
        SELECT
            mes_competencia,
            ano,
            mes,
            total_procedimentos,
            taxa_proc_10k,
            ROUND(
                100.0 * (total_procedimentos - LAG(total_procedimentos)
                    OVER (ORDER BY mes_competencia)) /
                NULLIF(LAG(total_procedimentos) OVER (ORDER BY mes_competencia), 0),
                2
            ) AS variacao_pct
        FROM mart_producao_amb
        WHERE {where}
        ORDER BY mes_competencia ASC
    """

    rows = await db.fetch(query, *params)

    # Dados do município (nome, UF) — lemos da primeira linha ou buscamos separado
    municipio_info = await db.fetchrow(
        """SELECT municipio_nome, uf_sigla
           FROM mart_producao_amb
           WHERE municipio_cod = $1
           LIMIT 1""",
        municipio_cod,
    )

    return ProducaoSerieResponse(
        municipio_cod=municipio_cod,
        municipio_nome=municipio_info["municipio_nome"] if municipio_info else None,
        uf_sigla=municipio_info["uf_sigla"] if municipio_info else "??",
        serie=[ProducaoSerieItem(**dict(r)) for r in rows],
    )


# ---------------------------------------------------------------------------
# GET /producao/mapa/{uf_sigla}
# ---------------------------------------------------------------------------


@router.get(
    "/mapa/{uf_sigla}",
    response_model=MapaResponse,
    summary="Dados de produção para mapa coroplético por UF",
)
async def mapa_producao(
    uf_sigla: str,
    ano: Annotated[int, Query(ge=2000, le=2030)] = 2024,
    indicador: Annotated[
        Literal["taxa_proc_10k", "total_procedimentos", "pct_aprovacao"],
        Query(description="taxa_proc_10k | total_procedimentos | pct_aprovacao"),
    ] = "taxa_proc_10k",
    db: asyncpg.Connection = Depends(get_db),
) -> MapaResponse:
    """
    Retorna valores por município de uma UF para renderização de mapa.
    O campo `valor` pode ser taxa_proc_10k, total_procedimentos ou pct_aprovacao.
    Valores inválidos para `indicador` retornam HTTP 422 (validação automática via Literal).
    """

    query = f"""
        WITH stats AS (
            SELECT
                municipio_cod,
                municipio_nome,
                SUM(total_procedimentos)::int          AS total_procedimentos,
                ROUND(AVG(taxa_proc_10k)::numeric, 2)  AS taxa_proc_10k,
                ROUND(AVG(pct_aprovacao)::numeric, 2)  AS pct_aprovacao
            FROM mart_producao_amb
            WHERE uf_sigla = $1 AND ano = $2
            GROUP BY municipio_cod, municipio_nome
        ),
        ranked AS (
            SELECT *,
                RANK() OVER (ORDER BY {indicador} DESC NULLS LAST) AS ranking,
                ROUND(
                    100.0 * PERCENT_RANK() OVER (ORDER BY {indicador} ASC NULLS FIRST),
                    1
                ) AS percentil
            FROM stats
        )
        SELECT
            municipio_cod, municipio_nome,
            {indicador}::float   AS valor,
            ranking::int,
            percentil::float
        FROM ranked
        ORDER BY valor DESC NULLS LAST
    """

    rows = await db.fetch(query, uf_sigla.upper(), ano)
    municipios = [
        MapaMunicipioFeature(
            municipio_cod=r["municipio_cod"],
            municipio_nome=r["municipio_nome"],
            valor=r["valor"],
            ranking=r["ranking"],
            percentil=r["percentil"],
        )
        for r in rows
    ]

    valores = [m.valor for m in municipios if m.valor is not None]

    return MapaResponse(
        uf_sigla=uf_sigla.upper(),
        indicador=indicador,
        ano=ano,
        data=municipios,
        escala_min=min(valores) if valores else None,
        escala_max=max(valores) if valores else None,
    )
