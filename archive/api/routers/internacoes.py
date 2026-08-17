"""
Router: Internações Hospitalares (SIH/AIH)

Endpoints:
  GET /internacoes                            — lista paginada com filtros
  GET /internacoes/municipio/{municipio_cod}  — série temporal por município
  GET /internacoes/uf/{uf_sigla}             — resumo por UF
  GET /internacoes/ranking                   — ranking por taxa de internação

Fonte: SIH/RD — Sistema de Informações Hospitalares (Autorização de Internação
Hospitalar) — DataSUS. Período: 2020–2024, 27 UFs, ~5 570 municípios.
"""
from __future__ import annotations

import math
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status

from api.database import fetch_paginated, get_db
from api.schemas import (
    InternacoesItem,
    InternacoesResponse,
    InternacoesSerieItem,
    InternacoesSerieResponse,
    PaginacaoMeta,
)

router = APIRouter(
    prefix="/internacoes",
    tags=["Internações Hospitalares (SIH/AIH)"],
)

# ---------------------------------------------------------------------------
# Constantes de domínio
# ---------------------------------------------------------------------------

_UFS_VALIDAS = {
    "AC", "AL", "AM", "AP", "BA", "CE", "DF", "ES", "GO", "MA",
    "MG", "MS", "MT", "PA", "PB", "PE", "PI", "PR", "RJ", "RN",
    "RO", "RR", "RS", "SC", "SE", "SP", "TO",
}

_CAR_INT_GRUPOS_VALIDOS = {"ELETIVO", "URGENCIA", "PARTO", "OUTROS", "TOTAL"}

_METRICAS_RANKING = {"taxa_internacao", "taxa_mortalidade_intra"}

# Colunas comuns para SELECTs em mart_internacoes (alinhadas com InternacoesItem)
_INTERNACOES_COLS = """
    municipio_cod, municipio_nome, uf_sigla, regiao,
    mes_competencia, ano_cmpt, mes_cmpt,
    diag_cap, diag_grupo,
    sexo, faixa_etaria, car_int_grupo,
    total_internacoes, total_obitos_internados,
    dias_perm_total, dias_perm_medio,
    val_tot_total, val_tot_medio,
    populacao, taxa_internacao, taxa_mortalidade_intra
"""


# ---------------------------------------------------------------------------
# GET /internacoes — lista paginada
# ---------------------------------------------------------------------------

@router.get(
    "",
    response_model=InternacoesResponse,
    summary="Lista de internações hospitalares com filtros",
    description=(
        "Retorna registros do mart de internações hospitalares (SIH/AIH) "
        "com filtros por UF, município, período, capítulo CID-10, sexo, "
        "faixa etária e grupo de caráter de internação (ELETIVO, URGENCIA, "
        "PARTO, OUTROS). Use `apenas_totais=true` para retornar somente as "
        "linhas de subtotais (sexo='TOTAL' **e** faixa_etaria='TOTAL')."
    ),
)
async def listar_internacoes(
    db=Depends(get_db),
    uf_sigla: Optional[str] = Query(None, description="Sigla da UF (ex: SP)"),
    municipio_cod: Optional[str] = Query(
        None, description="Código IBGE do município (6–7 dígitos)"
    ),
    ano_inicio: Optional[int] = Query(None, ge=2020, le=2024, description="Ano inicial"),
    ano_fim: Optional[int] = Query(None, ge=2020, le=2024, description="Ano final"),
    diag_cap: Optional[str] = Query(
        None,
        max_length=2,
        description="Capítulo CID-10 do diagnóstico principal (ex: 'IX')",
    ),
    sexo: Optional[str] = Query(None, description="Sexo (M, F ou TOTAL)"),
    faixa_etaria: Optional[str] = Query(None, description="Faixa etária (ex: '30-39')"),
    car_int_grupo: Optional[str] = Query(
        None, description="Grupo de caráter de internação: ELETIVO, URGENCIA, PARTO, OUTROS, TOTAL"
    ),
    apenas_totais: bool = Query(
        False, description="Se true, retorna somente linhas com sexo='TOTAL' e faixa_etaria='TOTAL'"
    ),
    pagina: int = Query(1, ge=1, description="Página (começa em 1)"),
    por_pagina: int = Query(100, ge=1, le=1000, description="Registros por página"),
) -> InternacoesResponse:

    # Validações de domínio
    if uf_sigla and uf_sigla.upper() not in _UFS_VALIDAS:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"uf_sigla '{uf_sigla}' inválida.",
        )
    if car_int_grupo and car_int_grupo.upper() not in _CAR_INT_GRUPOS_VALIDOS:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"car_int_grupo '{car_int_grupo}' inválido. Use: {sorted(_CAR_INT_GRUPOS_VALIDOS)}",
        )
    if ano_inicio and ano_fim and ano_inicio > ano_fim:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="ano_inicio não pode ser maior que ano_fim.",
        )

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
    if ano_inicio:
        conditions.append(f"ano_cmpt >= ${idx}")
        params.append(ano_inicio)
        idx += 1
    if ano_fim:
        conditions.append(f"ano_cmpt <= ${idx}")
        params.append(ano_fim)
        idx += 1
    if diag_cap:
        conditions.append(f"diag_cap = ${idx}")
        params.append(diag_cap.upper())
        idx += 1
    if sexo:
        conditions.append(f"sexo = ${idx}")
        params.append(sexo.upper())
        idx += 1
    if faixa_etaria:
        conditions.append(f"faixa_etaria = ${idx}")
        params.append(faixa_etaria)
        idx += 1
    if car_int_grupo:
        conditions.append(f"car_int_grupo = ${idx}")
        params.append(car_int_grupo.upper())
        idx += 1
    if apenas_totais:
        conditions.append("sexo = 'TOTAL'")
        conditions.append("faixa_etaria = 'TOTAL'")

    where_clause = ("WHERE " + " AND ".join(conditions)) if conditions else ""

    base_q = f"""
        SELECT {_INTERNACOES_COLS}
        FROM marts.mart_internacoes
        {where_clause}
        ORDER BY uf_sigla, municipio_cod, ano_cmpt DESC, mes_cmpt DESC
    """
    count_q = f"SELECT COUNT(*) FROM marts.mart_internacoes {where_clause}"

    rows, total = await fetch_paginated(db, base_q, count_q, params, pagina, por_pagina)

    return InternacoesResponse(
        data=[InternacoesItem(**dict(r)) for r in rows],
        paginacao=PaginacaoMeta(
            total=total,
            pagina=pagina,
            por_pagina=por_pagina,
            paginas=max(1, math.ceil(total / por_pagina)),
        ),
    )


# ---------------------------------------------------------------------------
# GET /internacoes/municipio/{municipio_cod} — série temporal
# ---------------------------------------------------------------------------

@router.get(
    "/municipio/{municipio_cod}",
    response_model=InternacoesSerieResponse,
    summary="Série temporal de internações de um município",
    description=(
        "Retorna a série temporal mensal de internações hospitalares para um "
        "município específico. Agrega todas as faixas etárias, sexos e grupos "
        "de caráter de internação (somente linhas TOTAL×TOTAL×TOTAL). "
        "Ordena do mais antigo ao mais recente."
    ),
)
async def serie_municipio_internacoes(
    municipio_cod: str,
    db=Depends(get_db),
    ano_inicio: Optional[int] = Query(None, ge=2020, le=2024),
    ano_fim: Optional[int] = Query(None, ge=2020, le=2024),
) -> InternacoesSerieResponse:

    if ano_inicio and ano_fim and ano_inicio > ano_fim:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="ano_inicio não pode ser maior que ano_fim.",
        )

    # Busca metadados do município (nome + UF)
    info_q = """
        SELECT municipio_nome, uf_sigla
        FROM marts.mart_internacoes
        WHERE municipio_cod = $1
        LIMIT 1
    """
    info_row = await db.fetchrow(info_q, municipio_cod)
    if info_row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Município '{municipio_cod}' não encontrado ou sem dados.",
        )

    conditions = [
        "municipio_cod = $1",
        "sexo = 'TOTAL'",
        "faixa_etaria = 'TOTAL'",
        "car_int_grupo = 'TOTAL'",
    ]
    params: list = [municipio_cod]
    idx = 2

    if ano_inicio:
        conditions.append(f"ano_cmpt >= ${idx}")
        params.append(ano_inicio)
        idx += 1
    if ano_fim:
        conditions.append(f"ano_cmpt <= ${idx}")
        params.append(ano_fim)
        idx += 1

    where_clause = "WHERE " + " AND ".join(conditions)

    serie_q = f"""
        SELECT
            mes_competencia,
            ano_cmpt,
            mes_cmpt,
            SUM(total_internacoes)       AS total_internacoes,
            MAX(taxa_internacao)         AS taxa_internacao,
            MAX(taxa_mortalidade_intra)  AS taxa_mortalidade_intra,
            AVG(dias_perm_medio)         AS dias_perm_medio
        FROM marts.mart_internacoes
        {where_clause}
        GROUP BY mes_competencia, ano_cmpt, mes_cmpt
        ORDER BY ano_cmpt ASC, mes_cmpt ASC
    """

    rows = await db.fetch(serie_q, *params)

    return InternacoesSerieResponse(
        municipio_cod=municipio_cod,
        municipio_nome=info_row["municipio_nome"],
        uf_sigla=info_row["uf_sigla"],
        serie=[InternacoesSerieItem(**dict(r)) for r in rows],
    )


# ---------------------------------------------------------------------------
# GET /internacoes/uf/{uf_sigla} — resumo por UF
# ---------------------------------------------------------------------------

@router.get(
    "/uf/{uf_sigla}",
    response_model=InternacoesResponse,
    summary="Internações hospitalares por UF",
    description=(
        "Retorna todos os registros de internações para uma UF específica, "
        "filtrados pelas linhas de subtotal (sexo='TOTAL' e faixa_etaria='TOTAL'). "
        "Útil para obter o perfil estadual por município, período e grupo de "
        "caráter de internação."
    ),
)
async def internacoes_por_uf(
    uf_sigla: str,
    db=Depends(get_db),
    ano_inicio: Optional[int] = Query(None, ge=2020, le=2024),
    ano_fim: Optional[int] = Query(None, ge=2020, le=2024),
    car_int_grupo: Optional[str] = Query(
        None, description="Filtrar por grupo de caráter: ELETIVO, URGENCIA, PARTO, OUTROS, TOTAL"
    ),
    pagina: int = Query(1, ge=1),
    por_pagina: int = Query(200, ge=1, le=1000),
) -> InternacoesResponse:

    if uf_sigla.upper() not in _UFS_VALIDAS:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"uf_sigla '{uf_sigla}' inválida.",
        )
    if car_int_grupo and car_int_grupo.upper() not in _CAR_INT_GRUPOS_VALIDOS:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"car_int_grupo '{car_int_grupo}' inválido.",
        )
    if ano_inicio and ano_fim and ano_inicio > ano_fim:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="ano_inicio não pode ser maior que ano_fim.",
        )

    conditions = [
        "uf_sigla = $1",
        "sexo = 'TOTAL'",
        "faixa_etaria = 'TOTAL'",
    ]
    params: list = [uf_sigla.upper()]
    idx = 2

    if ano_inicio:
        conditions.append(f"ano_cmpt >= ${idx}")
        params.append(ano_inicio)
        idx += 1
    if ano_fim:
        conditions.append(f"ano_cmpt <= ${idx}")
        params.append(ano_fim)
        idx += 1
    if car_int_grupo:
        conditions.append(f"car_int_grupo = ${idx}")
        params.append(car_int_grupo.upper())
        idx += 1

    where_clause = "WHERE " + " AND ".join(conditions)

    base_q = f"""
        SELECT {_INTERNACOES_COLS}
        FROM marts.mart_internacoes
        {where_clause}
        ORDER BY municipio_cod, ano_cmpt DESC, mes_cmpt DESC, car_int_grupo
    """
    count_q = f"SELECT COUNT(*) FROM marts.mart_internacoes {where_clause}"

    rows, total = await fetch_paginated(db, base_q, count_q, params, pagina, por_pagina)

    return InternacoesResponse(
        data=[InternacoesItem(**dict(r)) for r in rows],
        paginacao=PaginacaoMeta(
            total=total,
            pagina=pagina,
            por_pagina=por_pagina,
            paginas=max(1, math.ceil(total / por_pagina)),
        ),
    )


# ---------------------------------------------------------------------------
# GET /internacoes/ranking — top N municípios
# ---------------------------------------------------------------------------

@router.get(
    "/ranking",
    response_model=InternacoesResponse,
    summary="Ranking de municípios por taxa de internação",
    description=(
        "Retorna os N municípios com maior (ou menor) taxa de internação ou "
        "taxa de mortalidade intra-hospitalar. Considera somente as linhas de "
        "subtotal (sexo='TOTAL', faixa_etaria='TOTAL', car_int_grupo='TOTAL') "
        "do período especificado."
    ),
)
async def ranking_internacoes(
    db=Depends(get_db),
    uf_sigla: Optional[str] = Query(None, description="Filtrar por UF"),
    ano: Optional[int] = Query(None, ge=2020, le=2024, description="Ano de referência"),
    metrica: str = Query(
        "taxa_internacao",
        description="Métrica de ordenação: taxa_internacao | taxa_mortalidade_intra",
    ),
    ordem: str = Query("desc", description="Ordenação: asc | desc"),
    top: int = Query(50, ge=1, le=500, description="Número de registros"),
) -> InternacoesResponse:

    if metrica not in _METRICAS_RANKING:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"metrica '{metrica}' inválida. Use: {sorted(_METRICAS_RANKING)}",
        )
    if ordem not in ("asc", "desc"):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="ordem deve ser 'asc' ou 'desc'.",
        )
    if uf_sigla and uf_sigla.upper() not in _UFS_VALIDAS:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"uf_sigla '{uf_sigla}' inválida.",
        )

    # Coluna validada acima — sem risco de injeção SQL
    order_col = metrica

    conditions = [
        "sexo = 'TOTAL'",
        "faixa_etaria = 'TOTAL'",
        "car_int_grupo = 'TOTAL'",
        f"{metrica} IS NOT NULL",
    ]
    params: list = []
    idx = 1

    if uf_sigla:
        conditions.append(f"uf_sigla = ${idx}")
        params.append(uf_sigla.upper())
        idx += 1
    if ano:
        conditions.append(f"ano_cmpt = ${idx}")
        params.append(ano)
        idx += 1

    where_clause = "WHERE " + " AND ".join(conditions)

    query = f"""
        SELECT {_INTERNACOES_COLS}
        FROM marts.mart_internacoes
        {where_clause}
        ORDER BY {order_col} {ordem.upper()} NULLS LAST
        LIMIT {top}
    """

    rows = await db.fetch(query, *params)
    total = len(rows)

    return InternacoesResponse(
        data=[InternacoesItem(**dict(r)) for r in rows],
        paginacao=PaginacaoMeta(
            total=total, pagina=1, por_pagina=total or 1, paginas=1,
        ),
    )
