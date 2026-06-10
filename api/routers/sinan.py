"""
Router: Doenças Notificáveis / SINAN (/doencas-notificaveis)

Endpoints:
  GET /doencas-notificaveis                    — lista paginada de notificações
  GET /doencas-notificaveis/{agravo}/serie     — série temporal de um agravo

Fonte: mart_doencas_notificaveis (dbt, via SINAN)
Agravos suportados: DENG (dengue), CHIK (chikungunya), ZIKA, LEIV (leishmaniose
  visceral), LTAN (leish. tegumentar), LEPT (leptospirose), entre outros.

Estratégia de totais:
  O mart contém linhas UNION ALL com subtotais pré-computados:
    - faixa_etaria = 'Total' + cs_sexo = 'T'  → total geral por agravo/mês/município
  Por padrão os endpoints retornam apenas essas linhas de total (mais rápido e
  suficiente para dashboards). Passe faixa_etaria e/ou cs_sexo para detalhamento.
"""
from __future__ import annotations

import math
from typing import Annotated

import asyncpg
from fastapi import APIRouter, Depends, Query

from api.cache import TTL_EPI
from api.database import fetch_paginated, get_db
from api.schemas import (
    DoencasNotificaveisItem,
    DoencasNotificaveisResponse,
    DoencasNotificaveisSerieItem,
    DoencasNotificaveisSerieResponse,
    PaginacaoMeta,
)

router = APIRouter(prefix="/doencas-notificaveis", tags=["Doenças Notificáveis (SINAN)"])

# ---------------------------------------------------------------------------
# GET /doencas-notificaveis
# ---------------------------------------------------------------------------


@router.get(
    "",
    response_model=DoencasNotificaveisResponse,
    summary="Lista de notificações de doenças (SINAN)",
)
async def listar_doencas_notificaveis(
    agravo: Annotated[
        str | None,
        Query(description="Código do agravo (ex: DENG, CHIK, ZIKA, LEIV, LTAN, LEPT)"),
    ] = None,
    uf_notif: Annotated[str | None, Query(min_length=2, max_length=2, description="Sigla da UF")] = None,
    municipio_notif: Annotated[
        str | None,
        Query(min_length=6, max_length=7, description="Código IBGE do município"),
    ] = None,
    ano_notif: Annotated[int | None, Query(ge=2000, le=2030)] = None,
    ano_inicio: Annotated[int | None, Query(ge=2000, le=2030, description="Ano inicial (filtro de intervalo)")] = None,
    ano_fim: Annotated[int | None, Query(ge=2000, le=2030, description="Ano final (filtro de intervalo)")] = None,
    faixa_etaria: Annotated[
        str | None,
        Query(
            description=(
                "Faixa etária. Omita para retornar apenas o total agregado. "
                "Use 'Total' explicitamente para a linha de subtotal. "
                "Outros valores: '<1', '1-4', '5-9', '10-14', '15-19', '20-39', '40-59', '60+'"
            )
        ),
    ] = None,
    cs_sexo: Annotated[
        str | None,
        Query(
            description=(
                "Sexo: M (masculino), F (feminino), I (ignorado), T (total). "
                "Omita para retornar apenas o total agregado (T)."
            )
        ),
    ] = None,
    pagina: Annotated[int, Query(ge=1)] = 1,
    por_pagina: Annotated[int, Query(ge=1, le=500)] = 50,
    db: asyncpg.Connection = Depends(get_db),
) -> DoencasNotificaveisResponse:
    """
    Notificações de doenças compulsórias do SINAN por período e localidade.

    Por padrão retorna apenas as linhas de **total agregado** (`faixa_etaria='Total'`
    e `cs_sexo='T'`), que são pre-computadas no mart e representam o universo
    completo de cada agravo por município/mês. Passe `faixa_etaria` e/ou `cs_sexo`
    para desagregar por perfil demográfico.
    """
    conditions: list[str] = []
    filter_params: list = []
    idx = 1

    # Filtros de localidade e agravo
    if agravo:
        conditions.append(f"agravo = ${idx}")
        filter_params.append(agravo.upper())
        idx += 1
    if uf_notif:
        conditions.append(f"uf_notif = ${idx}")
        filter_params.append(uf_notif.upper())
        idx += 1
    if municipio_notif:
        conditions.append(f"municipio_notif = ${idx}")
        filter_params.append(municipio_notif)
        idx += 1

    # Filtros temporais
    if ano_notif:
        conditions.append(f"ano_notif = ${idx}")
        filter_params.append(ano_notif)
        idx += 1
    else:
        if ano_inicio:
            conditions.append(f"ano_notif >= ${idx}")
            filter_params.append(ano_inicio)
            idx += 1
        if ano_fim:
            conditions.append(f"ano_notif <= ${idx}")
            filter_params.append(ano_fim)
            idx += 1

    # Filtros demográficos — padrão: linha de totais pré-computada
    if faixa_etaria:
        conditions.append(f"faixa_etaria = ${idx}")
        filter_params.append(faixa_etaria)
        idx += 1
    else:
        conditions.append(f"faixa_etaria = ${idx}")
        filter_params.append("Total")
        idx += 1

    if cs_sexo:
        conditions.append(f"cs_sexo = ${idx}")
        filter_params.append(cs_sexo.upper())
        idx += 1
    else:
        conditions.append(f"cs_sexo = ${idx}")
        filter_params.append("T")
        idx += 1

    where = f"WHERE {' AND '.join(conditions)}"

    base_q = f"""
        SELECT
            agravo, agravo_label,
            ano_notif, mes_notif,
            uf_notif, municipio_notif,
            faixa_etaria, cs_sexo,
            total_notificacoes, total_obitos,
            casos_confirmados, casos_alarme, casos_graves,
            c_febre, c_mialgia, c_cefaleia, c_exantema,
            c_vomito, c_artralgia, c_artrite,
            lab_ns1_pos, lab_soro_pos, lab_pcr_pos,
            sorotipo_predominante,
            taxa_letalidade_pct, pct_confirmados
        FROM mart_doencas_notificaveis
        {where}
        ORDER BY ano_notif DESC, mes_notif DESC, uf_notif ASC, agravo ASC
    """
    count_q = f"SELECT COUNT(*) FROM mart_doencas_notificaveis {where}"

    rows, total = await fetch_paginated(
        db, base_q, count_q, filter_params, pagina, por_pagina,
        count_params=filter_params,
    )

    return DoencasNotificaveisResponse(
        data=[DoencasNotificaveisItem(**dict(r)) for r in rows],
        paginacao=PaginacaoMeta(
            total=total,
            pagina=pagina,
            por_pagina=por_pagina,
            paginas=max(1, math.ceil(total / por_pagina)),
        ),
    )


# ---------------------------------------------------------------------------
# GET /doencas-notificaveis/{agravo}/serie
# ---------------------------------------------------------------------------


@router.get(
    "/{agravo}/serie",
    response_model=DoencasNotificaveisSerieResponse,
    summary="Série temporal de um agravo notificável",
)
async def serie_agravo(
    agravo: str,
    uf_notif: Annotated[str | None, Query(min_length=2, max_length=2)] = None,
    municipio_notif: Annotated[str | None, Query(min_length=6, max_length=7)] = None,
    ano_inicio: Annotated[int | None, Query(ge=2000, le=2030)] = None,
    ano_fim: Annotated[int | None, Query(ge=2000, le=2030)] = None,
    db: asyncpg.Connection = Depends(get_db),
) -> DoencasNotificaveisSerieResponse:
    """
    Série temporal mensal de notificações para um agravo específico.

    Usa sempre a linha de total agregado (`faixa_etaria='Total'`, `cs_sexo='T'`).
    Filtre por `uf_notif` e/ou `municipio_notif` para recorte geográfico.
    """
    conditions: list[str] = ["agravo = $1", "faixa_etaria = 'Total'", "cs_sexo = 'T'"]
    params: list = [agravo.upper()]
    idx = 2

    if uf_notif:
        conditions.append(f"uf_notif = ${idx}")
        params.append(uf_notif.upper())
        idx += 1
    if municipio_notif:
        conditions.append(f"municipio_notif = ${idx}")
        params.append(municipio_notif)
        idx += 1
    if ano_inicio:
        conditions.append(f"ano_notif >= ${idx}")
        params.append(ano_inicio)
        idx += 1
    if ano_fim:
        conditions.append(f"ano_notif <= ${idx}")
        params.append(ano_fim)
        idx += 1

    where = f"WHERE {' AND '.join(conditions)}"

    # Agrega por mês caso haja múltiplos municípios no escopo da UF
    query = f"""
        SELECT
            ano_notif,
            mes_notif,
            SUM(total_notificacoes)  AS total_notificacoes,
            SUM(total_obitos)        AS total_obitos,
            SUM(casos_confirmados)   AS casos_confirmados,
            CASE
                WHEN SUM(casos_confirmados) > 0
                THEN ROUND(
                    SUM(total_obitos)::numeric / SUM(casos_confirmados) * 100, 2
                )
                ELSE NULL
            END AS taxa_letalidade_pct
        FROM mart_doencas_notificaveis
        {where}
        GROUP BY ano_notif, mes_notif
        ORDER BY ano_notif ASC, mes_notif ASC
    """
    rows = await db.fetch(query, *params)

    # Metadados do agravo (pega label do primeiro registro disponível)
    meta_q = """
        SELECT agravo_label, uf_notif, municipio_notif
        FROM mart_doencas_notificaveis
        WHERE agravo = $1 AND faixa_etaria = 'Total' AND cs_sexo = 'T'
        LIMIT 1
    """
    meta = await db.fetchrow(meta_q, agravo.upper())

    return DoencasNotificaveisSerieResponse(
        agravo=agravo.upper(),
        agravo_label=meta["agravo_label"] if meta else None,
        uf_notif=uf_notif.upper() if uf_notif else None,
        municipio_notif=municipio_notif,
        serie=[
            DoencasNotificaveisSerieItem(
                ano_notif=r["ano_notif"],
                mes_notif=r["mes_notif"],
                total_notificacoes=r["total_notificacoes"],
                total_obitos=r["total_obitos"],
                casos_confirmados=r["casos_confirmados"],
                taxa_letalidade_pct=r["taxa_letalidade_pct"],
            )
            for r in rows
        ],
    )
