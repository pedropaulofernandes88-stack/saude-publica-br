"""
Router: Capacidade Hospitalar / CNES (/capacidade-hospitalar)

Endpoints:
  GET /capacidade-hospitalar              — lista paginada de capacidade instalada
  GET /capacidade-hospitalar/{uf}         — detalhe consolidado de uma UF

Fonte: mart_capacidade_hospitalar (dbt, via CNES — Cadastro Nacional de
  Estabelecimentos de Saúde + CNES leitos/estabelecimentos).

Notas de modelagem:
  - unique_key: [ano_cmpt, mes_cmpt, uf, municipio_cod]
  - Contagens de leitos provêm da tabela LT (cnes_leitos), com fallback para
    a tabela ST (cnes_estabelecimentos) via COALESCE no mart.
  - municipio_cod NULL indica linha de agregação por UF (sem quebra municipal).
"""
from __future__ import annotations

import math
from typing import Annotated

import asyncpg
from fastapi import APIRouter, Depends, Query

from api.cache import TTL_INDICADORES
from api.database import fetch_paginated, get_db
from api.schemas import (
    CapacidadeHospitalarItem,
    CapacidadeHospitalarResponse,
    PaginacaoMeta,
)

router = APIRouter(prefix="/capacidade-hospitalar", tags=["Capacidade Hospitalar (CNES)"])


# ---------------------------------------------------------------------------
# GET /capacidade-hospitalar
# ---------------------------------------------------------------------------


@router.get(
    "",
    response_model=CapacidadeHospitalarResponse,
    summary="Capacidade instalada de estabelecimentos de saúde (CNES)",
)
async def listar_capacidade_hospitalar(
    uf: Annotated[str | None, Query(min_length=2, max_length=2, description="Sigla da UF")] = None,
    municipio_cod: Annotated[
        str | None,
        Query(min_length=6, max_length=7, description="Código IBGE do município (6 ou 7 dígitos)"),
    ] = None,
    ano_cmpt: Annotated[int | None, Query(ge=2000, le=2030)] = None,
    mes_cmpt: Annotated[int | None, Query(ge=1, le=12)] = None,
    ano_inicio: Annotated[int | None, Query(ge=2000, le=2030, description="Ano inicial (filtro de intervalo)")] = None,
    ano_fim: Annotated[int | None, Query(ge=2000, le=2030, description="Ano final (filtro de intervalo)")] = None,
    apenas_sus: Annotated[
        bool,
        Query(description="Se true, retorna apenas estabelecimentos com vínculo ao SUS"),
    ] = False,
    pagina: Annotated[int, Query(ge=1)] = 1,
    por_pagina: Annotated[int, Query(ge=1, le=500)] = 50,
    db: asyncpg.Connection = Depends(get_db),
) -> CapacidadeHospitalarResponse:
    """
    Capacidade instalada do sistema de saúde por município e competência.

    Inclui estabelecimentos totais e vinculados ao SUS, leitos (total, SUS, por tipo),
    ambulatório e serviços especializados (UTI, emergência, cirurgia, obstetrícia).

    Use `municipio_cod` para granularidade municipal ou apenas `uf` para visão estadual.
    Omitir ambos retorna o Brasil completo (recomenda-se paginar).
    """
    conditions: list[str] = []
    filter_params: list = []
    idx = 1

    if uf:
        conditions.append(f"uf = ${idx}")
        filter_params.append(uf.upper())
        idx += 1
    if municipio_cod:
        conditions.append(f"municipio_cod = ${idx}")
        filter_params.append(municipio_cod)
        idx += 1

    # Filtros temporais
    if ano_cmpt:
        conditions.append(f"ano_cmpt = ${idx}")
        filter_params.append(ano_cmpt)
        idx += 1
    else:
        if ano_inicio:
            conditions.append(f"ano_cmpt >= ${idx}")
            filter_params.append(ano_inicio)
            idx += 1
        if ano_fim:
            conditions.append(f"ano_cmpt <= ${idx}")
            filter_params.append(ano_fim)
            idx += 1

    if mes_cmpt:
        conditions.append(f"mes_cmpt = ${idx}")
        filter_params.append(mes_cmpt)
        idx += 1

    # Filtro SUS: pct_estab_sus > 0 é proxy para "tem vínculo SUS"
    if apenas_sus:
        conditions.append("estab_vinculados_sus > 0")

    where = f"WHERE {' AND '.join(conditions)}" if conditions else ""

    base_q = f"""
        SELECT
            ano_cmpt, mes_cmpt,
            uf, municipio_cod,
            total_estabelecimentos,
            estab_vinculados_sus, pct_estab_sus,
            qt_amb_sus, qt_amb_nao_sus, qt_amb_total, qt_cons_sus,
            estab_com_uti, estab_com_emergencia, estab_com_cirurgia,
            estab_com_obstetricia, estab_com_hemoterapia, estab_com_diagnostico,
            leitos_total, leitos_sus, leitos_nao_sus,
            leitos_contratualizados, pct_leitos_sus,
            leitos_cirurgico, leitos_clinico, leitos_complementar,
            leitos_obstetrico, leitos_pediatrico,
            leitos_reabilitacao, leitos_outro,
            leitos_sus_cirurgico, leitos_sus_clinico,
            leitos_sus_complementar, leitos_sus_obstetrico,
            leitos_sus_pediatrico, leitos_sus_reabilitacao
        FROM mart_capacidade_hospitalar
        {where}
        ORDER BY uf ASC, municipio_cod ASC NULLS FIRST, ano_cmpt DESC, mes_cmpt DESC
    """
    count_q = f"SELECT COUNT(*) FROM mart_capacidade_hospitalar {where}"

    rows, total = await fetch_paginated(
        db, base_q, count_q, filter_params, pagina, por_pagina,
        count_params=filter_params,
    )

    return CapacidadeHospitalarResponse(
        data=[CapacidadeHospitalarItem(**dict(r)) for r in rows],
        paginacao=PaginacaoMeta(
            total=total,
            pagina=pagina,
            por_pagina=por_pagina,
            paginas=max(1, math.ceil(total / por_pagina)),
        ),
    )


# ---------------------------------------------------------------------------
# GET /capacidade-hospitalar/{uf}
# ---------------------------------------------------------------------------


@router.get(
    "/{uf}",
    response_model=CapacidadeHospitalarResponse,
    summary="Capacidade hospitalar de uma UF com série histórica",
)
async def capacidade_por_uf(
    uf: str,
    municipio_cod: Annotated[
        str | None,
        Query(min_length=6, max_length=7, description="Filtra por município dentro da UF"),
    ] = None,
    ano_inicio: Annotated[int | None, Query(ge=2000, le=2030)] = None,
    ano_fim: Annotated[int | None, Query(ge=2000, le=2030)] = None,
    pagina: Annotated[int, Query(ge=1)] = 1,
    por_pagina: Annotated[int, Query(ge=1, le=500)] = 100,
    db: asyncpg.Connection = Depends(get_db),
) -> CapacidadeHospitalarResponse:
    """
    Capacidade instalada de uma UF com série histórica mensal.

    Retorna todos os municípios (ou um único se `municipio_cod` for informado),
    ordenados por mês descendente para facilitar análise de tendência.
    """
    conditions: list[str] = ["uf = $1"]
    params: list = [uf.upper()]
    idx = 2

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

    where = f"WHERE {' AND '.join(conditions)}"

    base_q = f"""
        SELECT
            ano_cmpt, mes_cmpt,
            uf, municipio_cod,
            total_estabelecimentos,
            estab_vinculados_sus, pct_estab_sus,
            qt_amb_sus, qt_amb_nao_sus, qt_amb_total, qt_cons_sus,
            estab_com_uti, estab_com_emergencia, estab_com_cirurgia,
            estab_com_obstetricia, estab_com_hemoterapia, estab_com_diagnostico,
            leitos_total, leitos_sus, leitos_nao_sus,
            leitos_contratualizados, pct_leitos_sus,
            leitos_cirurgico, leitos_clinico, leitos_complementar,
            leitos_obstetrico, leitos_pediatrico,
            leitos_reabilitacao, leitos_outro,
            leitos_sus_cirurgico, leitos_sus_clinico,
            leitos_sus_complementar, leitos_sus_obstetrico,
            leitos_sus_pediatrico, leitos_sus_reabilitacao
        FROM mart_capacidade_hospitalar
        {where}
        ORDER BY ano_cmpt DESC, mes_cmpt DESC, municipio_cod ASC NULLS FIRST
    """
    count_q = f"SELECT COUNT(*) FROM mart_capacidade_hospitalar {where}"

    rows, total = await fetch_paginated(
        db, base_q, count_q, params, pagina, por_pagina,
        count_params=params,
    )

    return CapacidadeHospitalarResponse(
        data=[CapacidadeHospitalarItem(**dict(r)) for r in rows],
        paginacao=PaginacaoMeta(
            total=total,
            pagina=pagina,
            por_pagina=por_pagina,
            paginas=max(1, math.ceil(total / por_pagina)),
        ),
    )
