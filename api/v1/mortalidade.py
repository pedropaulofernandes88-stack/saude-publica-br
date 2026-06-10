"""
Endpoints /v1/mortalidade — Mortalidade (SIM/DataSUS)

Dados do Sistema de Informações sobre Mortalidade (SIM), com granularidade
anual por estado, município e causa básica de morte (CID-10).

Autenticação: X-API-Key header ou ?api_key= query param.
Scope necessário: 'read'
"""
from __future__ import annotations

from typing import Optional
from fastapi import APIRouter, Depends, Query
from asyncpg import Connection

from api.deps import get_conn
from api.middleware.api_key import get_api_key, ApiKeyInfo
from api.v1.schema import (
    MortalidadeItem,
    MortalidadeResponse,
    MetaPaginacao,
    RateLimitInfo,
)

router = APIRouter(prefix="/mortalidade", tags=["Mortalidade"])


@router.get(
    "",
    response_model=MortalidadeResponse,
    summary="Listar mortalidade por causa",
    description="""
## Mortalidade — SIM/DataSUS

Dados anuais de mortalidade do Sistema de Informações sobre Mortalidade (SIM),
estruturados por estado, município e causa básica de morte (CID-10).

### Filtros
- **uf**: Sigla(s) do estado. Múltiplos separados por vírgula.
- **municipio**: Código IBGE (6 dígitos) do município de ocorrência.
- **cid10**: Código CID-10 exato (ex: `J18`) ou prefixo de capítulo (ex: `J` = aparelho respiratório).
- **ano_inicio / ano_fim**: Intervalo de anos (ex: `2019` a `2023`).
- **com_taxa**: Se `true`, inclui a taxa por 100k (requer denominador populacional; pode ser `null` para municípios muito pequenos).

### Hierarquia CID-10
| Prefixo | Capítulo |
|---------|---------|
| A–B | Doenças infecciosas e parasitárias |
| C–D | Neoplasias |
| I | Doenças do aparelho circulatório |
| J | Doenças do aparelho respiratório |
| V–Y | Causas externas |

### Notas técnicas
- Anos disponíveis: 2010–2023 (a partir de 2024 com atraso de ~12 meses).
- Óbitos com causa ignorada (código `R99`) são incluídos mas não têm `taxa_100k`.
- Chaves `free`: últimos 5 anos. `pro`/`enterprise`: histórico completo.
""",
)
async def listar_mortalidade(
    uf: Optional[str] = Query(None, description="Sigla(s) de UF.", example="SP"),
    municipio: Optional[str] = Query(
        None, description="Código IBGE (6 dígitos).", example="355030"
    ),
    cid10: Optional[str] = Query(
        None,
        description="Código CID-10 ou prefixo de capítulo (ex: `J`, `I2`).",
        example="J18",
    ),
    ano_inicio: Optional[int] = Query(
        None, ge=2000, le=2030, description="Ano inicial.", example=2020
    ),
    ano_fim: Optional[int] = Query(
        None, ge=2000, le=2030, description="Ano final.", example=2023
    ),
    com_taxa: bool = Query(
        False, description="Incluir taxa por 100k habitantes.", example=False
    ),
    pagina: int = Query(1, ge=1, example=1),
    por_pagina: int = Query(100, ge=1, le=1000, example=100),
    conn: Connection = Depends(get_conn),
    api_key: ApiKeyInfo = Depends(get_api_key),
) -> MortalidadeResponse:
    """Endpoint principal de mortalidade."""
    offset = (pagina - 1) * por_pagina

    limite_historico = ""
    if api_key.tier == "free":
        limite_historico = "AND ano >= EXTRACT(YEAR FROM now())::int - 5"

    filtros: list[str] = [limite_historico]
    params: list[object] = []
    idx = 1

    if uf:
        ufs = [u.strip().upper() for u in uf.split(",")]
        filtros.append(f"uf = ANY(${idx}::text[])")
        params.append(ufs)
        idx += 1

    if municipio:
        filtros.append(f"municipio_codigo = ${idx}")
        params.append(municipio)
        idx += 1

    if cid10:
        if len(cid10) <= 3:
            filtros.append(f"causa_cid10 LIKE ${idx}")
            params.append(cid10.upper() + "%")
        else:
            filtros.append(f"causa_cid10 = ${idx}")
            params.append(cid10.upper())
        idx += 1

    if ano_inicio:
        filtros.append(f"ano >= ${idx}")
        params.append(ano_inicio)
        idx += 1

    if ano_fim:
        filtros.append(f"ano <= ${idx}")
        params.append(ano_fim)
        idx += 1

    where = "WHERE " + " AND ".join(f for f in filtros if f) if any(filtros) else ""

    taxa_col = ", taxa_100k, idade_media, prop_feminino" if com_taxa else ", NULL::float AS taxa_100k, NULL::float AS idade_media, NULL::float AS prop_feminino"

    sql_count = f"SELECT COUNT(*) FROM marts.mortalidade_anual {where}"
    sql_data = f"""
        SELECT
            ano, uf, municipio_codigo,
            causa_cid10, causa_descricao, capitulo_cid,
            obitos
            {taxa_col}
        FROM marts.mortalidade_anual
        {where}
        ORDER BY ano DESC, obitos DESC
        LIMIT ${idx} OFFSET ${idx + 1}
    """

    total = await conn.fetchval(sql_count, *params)
    rows = await conn.fetch(sql_data, *params, por_pagina, offset)

    return MortalidadeResponse(
        dados=[MortalidadeItem(**dict(r)) for r in rows],
        meta=MetaPaginacao(
            total=total or 0,
            pagina=pagina,
            por_pagina=por_pagina,
            paginas=max(1, -(-( total or 0) // por_pagina)),
        ),
        rate_limit=RateLimitInfo(
            limite_hora=api_key.limite_hora,
            usadas_hora=api_key.uso_hora,
            tier=api_key.tier,
        ),
        ultima_atualizacao=await _ultima_atualizacao(conn),
    )


@router.get(
    "/causas-principais",
    summary="Top causas de morte por UF e ano",
    description="""
Retorna as N principais causas de morte (por número de óbitos) para um estado
e ano especificados. Útil para ranking rápido sem paginação.

Máximo de 50 causas por chamada.
""",
)
async def causas_principais(
    uf: str = Query(..., description="Sigla do estado.", example="SP"),
    ano: int = Query(..., ge=2000, le=2030, description="Ano de referência.", example=2023),
    top_n: int = Query(10, ge=1, le=50, description="Quantidade de causas.", example=10),
    conn: Connection = Depends(get_conn),
    api_key: ApiKeyInfo = Depends(get_api_key),
):
    """Top-N causas de morte."""
    rows = await conn.fetch(
        """
        SELECT
            causa_cid10,
            causa_descricao,
            capitulo_cid,
            SUM(obitos)         AS obitos,
            SUM(obitos) * 100.0
              / NULLIF(SUM(SUM(obitos)) OVER (), 0) AS pct_total
        FROM marts.mortalidade_anual
        WHERE uf = $1 AND ano = $2
        GROUP BY causa_cid10, causa_descricao, capitulo_cid
        ORDER BY obitos DESC
        LIMIT $3
        """,
        uf.upper(),
        ano,
        top_n,
    )
    return {
        "uf": uf.upper(),
        "ano": ano,
        "dados": [dict(r) for r in rows],
        "rate_limit": {
            "limite_hora": api_key.limite_hora,
            "usadas_hora": api_key.uso_hora,
            "tier": api_key.tier,
        },
        "fonte": "SIM/DataSUS",
    }


@router.get(
    "/tendencia",
    summary="Série histórica de óbitos por causa",
    description="""
Retorna a evolução anual de óbitos para uma causa específica em um estado.
Ideal para construir gráficos de linha com tendência temporal.
""",
)
async def tendencia_mortalidade(
    uf: str = Query(..., example="SP"),
    cid10: str = Query(..., description="Código CID-10.", example="I21"),
    conn: Connection = Depends(get_conn),
    api_key: ApiKeyInfo = Depends(get_api_key),
):
    """Série histórica anual para uma causa."""
    rows = await conn.fetch(
        """
        SELECT ano, SUM(obitos) AS obitos, AVG(taxa_100k) AS taxa_100k
        FROM marts.mortalidade_anual
        WHERE uf = $1 AND causa_cid10 = $2
        GROUP BY ano
        ORDER BY ano
        """,
        uf.upper(),
        cid10.upper(),
    )
    return {
        "uf": uf.upper(),
        "causa_cid10": cid10.upper(),
        "serie": [dict(r) for r in rows],
        "rate_limit": {
            "limite_hora": api_key.limite_hora,
            "usadas_hora": api_key.uso_hora,
            "tier": api_key.tier,
        },
        "fonte": "SIM/DataSUS",
    }


async def _ultima_atualizacao(conn: Connection) -> str:
    row = await conn.fetchrow(
        """
        SELECT to_char(max(concluido_em), 'YYYY-MM-DD"T"HH24:MI:SS"Z"') AS dt
        FROM pipeline_runs WHERE sistema = 'sim' AND status = 'success'
        """
    )
    return (row["dt"] if row else None) or "2024-01-01T00:00:00Z"
