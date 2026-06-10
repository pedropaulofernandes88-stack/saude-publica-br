"""
Router: Indicadores por município (/indicadores)

Endpoints:
  GET /indicadores/{municipio_cod}    — visão consolidada de todos indicadores
  GET /indicadores/acesso             — lista paginada de acesso e cobertura
  GET /indicadores/complexidade       — mix de complexidade paginado
  GET /indicadores/sazonalidade       — padrões sazonais
  GET /indicadores/anomalias          — alertas de desvio (Prophet / Z-score / auto)
"""
from __future__ import annotations

import math
from typing import Annotated, Literal

import asyncpg
from fastapi import APIRouter, Depends, HTTPException, Query, status

from api.cache import TTL_ANOMALIAS, TTL_COMPLEXIDADE, TTL_INDICADORES
from api.database import fetch_paginated, get_db
from api.schemas import (
    AcessoCoberturaItem,
    AcessoCoberturaResponse,
    AnomaliaItem,
    AnomaliaResponse,
    IndicadoresMunicipioResponse,
    MixComplexidadeItem,
    MixComplexidadeResponse,
    PaginacaoMeta,
    SazonalidadeItem,
    SazonalidadeResponse,
)

router = APIRouter(prefix="/indicadores", tags=["Indicadores"])


# ---------------------------------------------------------------------------
# GET /indicadores/acesso
# ---------------------------------------------------------------------------


@router.get(
    "/acesso",
    response_model=AcessoCoberturaResponse,
    summary="Indicadores de acesso e cobertura",
)
async def listar_acesso(
    uf_sigla: Annotated[str | None, Query(min_length=2, max_length=2)] = None,
    ano: Annotated[int, Query(ge=2000, le=2030)] = 2024,
    quartil: Annotated[str | None, Query(description="Q1 | Q2-Q3 | Q4")] = None,
    pagina: Annotated[int, Query(ge=1)] = 1,
    por_pagina: Annotated[int, Query(ge=1, le=500)] = 100,
    db: asyncpg.Connection = Depends(get_db),
) -> AcessoCoberturaResponse:
    """Lista acesso e cobertura ambulatorial por município."""
    conditions = ["ano = $1"]
    params: list = [ano]
    idx = 2

    if uf_sigla:
        conditions.append(f"uf_sigla = ${idx}")
        params.append(uf_sigla.upper())
        idx += 1
    if quartil:
        conditions.append(f"quartil_acesso = ${idx}")
        params.append(quartil)
        idx += 1

    where = f"WHERE {' AND '.join(conditions)}"
    base_q = f"""
        SELECT municipio_cod, municipio_nome, uf_sigla, ano,
               populacao, atendimentos_ab, atendimentos_mc, atendimentos_ac,
               taxa_cobertura_ab, pct_cobertura, quartil_acesso, indice_acesso
        FROM mart_acesso_cobertura
        {where}
        ORDER BY uf_sigla, pct_cobertura DESC NULLS LAST
    """
    count_q = f"SELECT COUNT(*) FROM mart_acesso_cobertura {where}"
    rows, total = await fetch_paginated(db, base_q, count_q, params, pagina, por_pagina)

    return AcessoCoberturaResponse(
        data=[AcessoCoberturaItem(**dict(r)) for r in rows],
        paginacao=PaginacaoMeta(
            total=total, pagina=pagina, por_pagina=por_pagina,
            paginas=max(1, math.ceil(total / por_pagina)),
        ),
    )


# ---------------------------------------------------------------------------
# GET /indicadores/complexidade
# ---------------------------------------------------------------------------


@router.get(
    "/complexidade",
    response_model=MixComplexidadeResponse,
    summary="Mix de complexidade por município",
)
async def listar_complexidade(
    uf_sigla: Annotated[str | None, Query(min_length=2, max_length=2)] = None,
    ano: Annotated[int, Query(ge=2000, le=2030)] = 2024,
    pagina: Annotated[int, Query(ge=1)] = 1,
    por_pagina: Annotated[int, Query(ge=1, le=500)] = 100,
    db: asyncpg.Connection = Depends(get_db),
) -> MixComplexidadeResponse:
    """Distribuição de procedimentos por nível de complexidade (AB/MC/AC)."""
    conditions = ["ano = $1"]
    params: list = [ano]
    idx = 2

    if uf_sigla:
        conditions.append(f"uf_sigla = ${idx}")
        params.append(uf_sigla.upper())
        idx += 1

    where = f"WHERE {' AND '.join(conditions)}"
    base_q = f"""
        SELECT municipio_cod, municipio_nome, uf_sigla, ano,
               total_procedimentos, qtd_ab, qtd_mc, qtd_ac,
               pct_ab, pct_mc, pct_ac, indice_complexidade
        FROM mart_mix_complexidade
        {where}
        ORDER BY uf_sigla, indice_complexidade DESC NULLS LAST
    """
    count_q = f"SELECT COUNT(*) FROM mart_mix_complexidade {where}"
    rows, total = await fetch_paginated(db, base_q, count_q, params, pagina, por_pagina)

    return MixComplexidadeResponse(
        data=[MixComplexidadeItem(**dict(r)) for r in rows],
        paginacao=PaginacaoMeta(
            total=total, pagina=pagina, por_pagina=por_pagina,
            paginas=max(1, math.ceil(total / por_pagina)),
        ),
    )


# ---------------------------------------------------------------------------
# GET /indicadores/sazonalidade
# ---------------------------------------------------------------------------


@router.get(
    "/sazonalidade",
    response_model=SazonalidadeResponse,
    summary="Padrões sazonais de produção",
)
async def listar_sazonalidade(
    uf_sigla: Annotated[str | None, Query(min_length=2, max_length=2)] = None,
    municipio_cod: Annotated[str | None, Query(min_length=6, max_length=7)] = None,
    pagina: Annotated[int, Query(ge=1)] = 1,
    por_pagina: Annotated[int, Query(ge=1, le=500)] = 100,
    db: asyncpg.Connection = Depends(get_db),
) -> SazonalidadeResponse:
    """Médias históricas e limites de controle sazonais por município."""
    conditions: list[str] = []
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

    where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
    base_q = f"""
        SELECT municipio_cod, municipio_nome, uf_sigla, mes,
               media_historica, desvio_padrao, limite_inferior, limite_superior,
               mes_pico, amplitude_sazonal, anos_historico
        FROM mart_sazonalidade
        {where}
        ORDER BY uf_sigla, municipio_cod, mes
    """
    count_q = f"SELECT COUNT(*) FROM mart_sazonalidade {where}"
    rows, total = await fetch_paginated(db, base_q, count_q, params, pagina, por_pagina)

    return SazonalidadeResponse(
        data=[SazonalidadeItem(**dict(r)) for r in rows],
        paginacao=PaginacaoMeta(
            total=total, pagina=pagina, por_pagina=por_pagina,
            paginas=max(1, math.ceil(total / por_pagina)),
        ),
    )


# ---------------------------------------------------------------------------
# GET /indicadores/anomalias
# ---------------------------------------------------------------------------

# Colunas extras nulas para uniformizar o SELECT das duas fontes
_PROPHET_NULL_COLS = """
    NULL::float   AS media_historica,
    NULL::float   AS desvio_padrao,
    NULL::float   AS yhat,
    NULL::float   AS yhat_lower,
    NULL::float   AS yhat_upper,
    'zscore'      AS metodo,
    NULL::integer AS n_pontos
"""
_ZSCORE_NULL_COLS = """
    NULL::float   AS yhat,
    NULL::float   AS yhat_lower,
    NULL::float   AS yhat_upper,
    'zscore'      AS metodo,
    NULL::integer AS n_pontos
"""


def _build_zscore_cte(where_extra: str) -> str:
    """Retorna o CTE SQL de Z-score histórico (sem paginação)."""
    return f"""
    zscore_raw AS (
        SELECT
            p.municipio_cod,
            p.municipio_nome,
            p.uf_sigla,
            p.mes_competencia,
            p.ano,
            p.mes,
            p.total_procedimentos,
            s.media_historica,
            s.desvio_padrao,
            ROUND(
                (p.total_procedimentos - s.media_historica)
                / NULLIF(s.desvio_padrao, 0),
                3
            )                                                                    AS z_score,
            CASE
                WHEN p.total_procedimentos > s.media_historica THEN 'alta'
                ELSE 'baixa'
            END                                                                  AS tipo_anomalia,
            ROUND(
                100.0 * (p.total_procedimentos - s.media_historica)
                / NULLIF(s.media_historica, 0),
                2
            )                                                                    AS pct_desvio,
            NULL::float   AS yhat,
            NULL::float   AS yhat_lower,
            NULL::float   AS yhat_upper,
            'zscore'      AS metodo,
            NULL::integer AS n_pontos
        FROM mart_producao_amb p
        JOIN mart_sazonalidade s
            ON s.municipio_cod = p.municipio_cod
           AND s.mes = p.mes
        WHERE s.desvio_padrao > 0
          {where_extra}
    )"""


def _build_prophet_select(where_clause: str) -> str:
    """SELECT direto de mart_anomalias_prophet com colunas uniformizadas."""
    return f"""
        SELECT
            municipio_cod,
            municipio_nome,
            uf_sigla,
            mes_competencia,
            ano,
            mes,
            total_procedimentos,
            NULL::float   AS media_historica,
            NULL::float   AS desvio_padrao,
            ROUND(z_score::numeric, 3) AS z_score,
            tipo_anomalia,
            ROUND(pct_desvio::numeric, 2) AS pct_desvio,
            yhat,
            yhat_lower,
            yhat_upper,
            metodo,
            n_pontos
        FROM mart_anomalias_prophet
        WHERE is_anomaly = TRUE
          {where_clause}"""


@router.get(
    "/anomalias",
    response_model=AnomaliaResponse,
    summary="Municípios com produção fora dos padrões históricos",
)
async def listar_anomalias(
    uf_sigla: Annotated[str | None, Query(min_length=2, max_length=2)] = None,
    mes_competencia: Annotated[str | None, Query(pattern=r"^\d{6}$")] = None,
    ano: Annotated[int | None, Query(ge=2000, le=2030)] = None,
    tipo: Annotated[str | None, Query(description="alta | baixa")] = None,
    sigma: Annotated[float, Query(ge=1.0, le=4.0, description="Limiar Z-score")] = 2.0,
    method: Annotated[
        Literal["prophet", "zscore", "auto"],
        Query(
            description=(
                "Método de detecção: "
                "'prophet' usa resultados pré-computados do modelo Prophet, "
                "'zscore' usa média histórica sazonal (SQL puro), "
                "'auto' combina Prophet onde disponível e Z-score para os demais."
            )
        ),
    ] = "auto",
    pagina: Annotated[int, Query(ge=1)] = 1,
    por_pagina: Annotated[int, Query(ge=1, le=500)] = 100,
    db: asyncpg.Connection = Depends(get_db),
) -> AnomaliaResponse:
    """
    Detecta anomalias de produção ambulatorial comparando produção real vs. esperada.

    **Modos de detecção:**
    - `auto` (padrão): usa resultados do modelo Prophet pré-computado para municípios
      já processados; aplica Z-score histórico (SQL) para os demais.
    - `prophet`: utiliza exclusivamente a tabela `mart_anomalias_prophet`.
      Requer que o `batch_scorer` tenha sido executado previamente.
    - `zscore`: detecção online via SQL puro (sem ML). Sempre disponível.

    Um registro é considerado anomalia quando |Z-score| ≥ `sigma` (padrão 2.0).
    """
    uf = uf_sigla.upper() if uf_sigla else None

    # ------------------------------------------------------------------
    # Construção dinâmica dos filtros comuns
    # ------------------------------------------------------------------
    params: list = []
    idx = 1

    # Filtros de data/localização — usados nos dois modos
    date_loc_parts_p: list[str] = []   # para mart_anomalias_prophet (sem prefixo)
    date_loc_parts_z: list[str] = []   # para mart_producao_amb (prefixo p.)

    if uf:
        date_loc_parts_p.append(f"uf_sigla = ${idx}")
        date_loc_parts_z.append(f"p.uf_sigla = ${idx}")
        params.append(uf)
        idx += 1
    if mes_competencia:
        date_loc_parts_p.append(f"mes_competencia = ${idx}")
        date_loc_parts_z.append(f"p.mes_competencia = ${idx}")
        params.append(mes_competencia)
        idx += 1
    if ano:
        date_loc_parts_p.append(f"ano = ${idx}")
        date_loc_parts_z.append(f"p.ano = ${idx}")
        params.append(ano)
        idx += 1

    where_prophet = ("AND " + " AND ".join(date_loc_parts_p)) if date_loc_parts_p else ""
    where_z_extra = ("AND " + " AND ".join(date_loc_parts_z)) if date_loc_parts_z else ""

    # Filtro de tipo (alta/baixa) — aplicado depois do cálculo de Z-score
    tipo_filter_p = ""   # prophet table column
    tipo_filter_z = ""   # zscore CTE alias
    if tipo in ("alta", "baixa"):
        tipo_filter_p = f"AND tipo_anomalia = ${idx}"
        tipo_filter_z = f"AND tipo_anomalia = ${idx}"
        params.append(tipo)
        idx += 1

    # sigma — índice dinâmico
    sigma_idx = idx
    params.append(sigma)

    # ------------------------------------------------------------------
    # Modo PROPHET — lê exclusivamente mart_anomalias_prophet
    # ------------------------------------------------------------------
    if method == "prophet":
        base_q = f"""
            {_build_prophet_select(where_prophet)}
              AND ABS(z_score) >= ${sigma_idx}
              {tipo_filter_p}
            ORDER BY ABS(z_score) DESC
        """
        count_q = f"""
            SELECT COUNT(*) FROM mart_anomalias_prophet
            WHERE is_anomaly = TRUE
              AND ABS(z_score) >= ${sigma_idx}
              {where_prophet}
              {tipo_filter_p}
        """
        rows, total = await fetch_paginated(db, base_q, count_q, params, pagina, por_pagina)
        return AnomaliaResponse(
            data=[AnomaliaItem(**dict(r)) for r in rows],
            paginacao=PaginacaoMeta(
                total=total, pagina=pagina, por_pagina=por_pagina,
                paginas=max(1, math.ceil(total / por_pagina)),
            ),
            threshold_sigma=sigma,
            method_used="prophet",
        )

    # ------------------------------------------------------------------
    # Modo ZSCORE — Z-score puro via SQL CTE
    # ------------------------------------------------------------------
    if method == "zscore":
        base_q = f"""
            WITH {_build_zscore_cte(where_z_extra)}
            SELECT *
            FROM zscore_raw
            WHERE ABS(z_score) >= ${sigma_idx}
              {tipo_filter_z}
            ORDER BY ABS(z_score) DESC
        """
        count_q = f"""
            WITH {_build_zscore_cte(where_z_extra)}
            SELECT COUNT(*) FROM zscore_raw
            WHERE ABS(z_score) >= ${sigma_idx}
              {tipo_filter_z}
        """
        rows, total = await fetch_paginated(db, base_q, count_q, params, pagina, por_pagina)
        return AnomaliaResponse(
            data=[AnomaliaItem(**dict(r)) for r in rows],
            paginacao=PaginacaoMeta(
                total=total, pagina=pagina, por_pagina=por_pagina,
                paginas=max(1, math.ceil(total / por_pagina)),
            ),
            threshold_sigma=sigma,
            method_used="zscore",
        )

    # ------------------------------------------------------------------
    # Modo AUTO — Prophet onde disponível, Z-score para os demais
    # ------------------------------------------------------------------
    # A condição NOT EXISTS exclui do Z-score os municípios já cobertos
    # pelo modelo Prophet para a mesma (municipio_cod, mes_competencia).
    not_in_prophet = """
        AND NOT EXISTS (
            SELECT 1 FROM mart_anomalias_prophet ap
            WHERE ap.municipio_cod = p.municipio_cod
              AND ap.mes_competencia = p.mes_competencia
        )"""

    zscore_where_auto = where_z_extra + not_in_prophet

    base_q = f"""
        WITH
        prophet_rows AS (
            {_build_prophet_select(where_prophet)}
              AND ABS(z_score) >= ${sigma_idx}
              {tipo_filter_p}
        ),
        {_build_zscore_cte(zscore_where_auto)},
        zscore_rows AS (
            SELECT * FROM zscore_raw
            WHERE ABS(z_score) >= ${sigma_idx}
              {tipo_filter_z}
        ),
        combined AS (
            SELECT * FROM prophet_rows
            UNION ALL
            SELECT * FROM zscore_rows
        )
        SELECT * FROM combined
        ORDER BY ABS(z_score) DESC
    """
    count_q = f"""
        WITH
        prophet_rows AS (
            SELECT municipio_cod FROM mart_anomalias_prophet
            WHERE is_anomaly = TRUE
              AND ABS(z_score) >= ${sigma_idx}
              {where_prophet}
              {tipo_filter_p}
        ),
        {_build_zscore_cte(zscore_where_auto)},
        zscore_rows AS (
            SELECT municipio_cod FROM zscore_raw
            WHERE ABS(z_score) >= ${sigma_idx}
              {tipo_filter_z}
        )
        SELECT (SELECT COUNT(*) FROM prophet_rows)
             + (SELECT COUNT(*) FROM zscore_rows) AS total
    """
    rows, total = await fetch_paginated(db, base_q, count_q, params, pagina, por_pagina)
    return AnomaliaResponse(
        data=[AnomaliaItem(**dict(r)) for r in rows],
        paginacao=PaginacaoMeta(
            total=total, pagina=pagina, por_pagina=por_pagina,
            paginas=max(1, math.ceil(total / por_pagina)),
        ),
        threshold_sigma=sigma,
        method_used="auto",
    )


# ---------------------------------------------------------------------------
# GET /indicadores/{municipio_cod}
# IMPORTANT: must be registered LAST so literal paths (/acesso, /complexidade,
# /sazonalidade, /anomalias) are matched before this catch-all parameter route.
# ---------------------------------------------------------------------------


@router.get(
    "/{municipio_cod}",
    response_model=IndicadoresMunicipioResponse,
    summary="Visão consolidada de todos indicadores de um município",
)
async def indicadores_municipio(
    municipio_cod: str,
    ano: Annotated[int, Query(ge=2000, le=2030)] = 2024,
    db: asyncpg.Connection = Depends(get_db),
) -> IndicadoresMunicipioResponse:
    """
    Consolida produção, acesso, mix de complexidade e ranking
    de um município em uma única resposta.
    Útil para ficha resumo / dashboard de município.
    """
    query = """
        SELECT
            p.municipio_cod,
            p.municipio_nome,
            p.uf_sigla,
            $2::int                         AS ano,
            -- Produção
            SUM(p.total_procedimentos)::int AS total_procedimentos,
            ROUND(AVG(p.taxa_proc_10k)::numeric, 2) AS taxa_proc_10k,
            -- Acesso
            a.pct_cobertura,
            a.quartil_acesso,
            -- Mix
            m.pct_ab, m.pct_mc, m.pct_ac,
            m.indice_complexidade,
            -- Ranking
            r.ranking_estadual,
            r.percentil_estadual,
            r.ranking_nacional
        FROM mart_producao_amb p
        LEFT JOIN mart_acesso_cobertura a
            ON a.municipio_cod = p.municipio_cod AND a.ano = $2
        LEFT JOIN mart_mix_complexidade m
            ON m.municipio_cod = p.municipio_cod AND m.ano = $2
        LEFT JOIN mart_ranking_municipios r
            ON r.municipio_cod = p.municipio_cod AND r.ano = $2
        WHERE p.municipio_cod = $1
          AND p.ano = $2
        GROUP BY
            p.municipio_cod, p.municipio_nome, p.uf_sigla,
            a.pct_cobertura, a.quartil_acesso,
            m.pct_ab, m.pct_mc, m.pct_ac, m.indice_complexidade,
            r.ranking_estadual, r.percentil_estadual, r.ranking_nacional
    """
    row = await db.fetchrow(query, municipio_cod, ano)
    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Município {municipio_cod} sem dados para o ano {ano}.",
        )
    return IndicadoresMunicipioResponse(**dict(row))
