"""
Endpoints /v1/capacidade — Capacidade Instalada (CNES/DataSUS)

Dados do Cadastro Nacional de Estabelecimentos de Saúde (CNES): leitos,
equipamentos, profissionais e cobertura da Estratégia Saúde da Família.

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
    EstabelecimentoItem,
    CapacidadeResponse,
    ResumoCapacidade,
    ResumoCapacidadeResponse,
    MetaPaginacao,
    RateLimitInfo,
)

router = APIRouter(prefix="/capacidade", tags=["Capacidade Instalada"])


@router.get(
    "/estabelecimentos",
    response_model=CapacidadeResponse,
    summary="Listar estabelecimentos de saúde",
    description="""
## Estabelecimentos de Saúde — CNES/DataSUS

Lista estabelecimentos do Sistema Único de Saúde cadastrados no CNES,
com informações de leitos, profissionais e localização geográfica.

### Filtros
- **uf**: Sigla(s) do estado.
- **municipio**: Código IBGE (6 dígitos).
- **tipo**: Tipo de unidade CNES. Exemplos: `HOSPITAL GERAL`, `UPA`, `UBS`, `AME`.
- **gestao**: Esfera de gestão: `MUNICIPAL`, `ESTADUAL`, `FEDERAL`.
- **apenas_sus**: Se `true` (padrão), retorna apenas estabelecimentos com leitos SUS.
- **competencia**: Mês de referência AAAA-MM (padrão: mês mais recente disponível).
- **com_coords**: Se `true`, inclui latitude/longitude (nem todos têm geocodificação).

### Notas
- Dados atualizados mensalmente a partir do arquivo de disseminação do CNES.
- Leitos hospitalares incluem leitos clínicos, cirúrgicos, obstétricos e de UTI.
- Equipes de Saúde da Família (ESF) são cadastradas apenas para UBS/UBSF.
""",
)
async def listar_estabelecimentos(
    uf: Optional[str] = Query(None, example="SP"),
    municipio: Optional[str] = Query(None, example="355030"),
    tipo: Optional[str] = Query(
        None,
        description="Tipo de unidade CNES (correspondência parcial, case-insensitive).",
        example="HOSPITAL GERAL",
    ),
    gestao: Optional[str] = Query(
        None,
        description="'MUNICIPAL', 'ESTADUAL' ou 'FEDERAL'.",
        example="ESTADUAL",
    ),
    apenas_sus: bool = Query(True, description="Filtrar apenas estabelecimentos com leitos SUS."),
    competencia: Optional[str] = Query(
        None,
        description="Mês de referência AAAA-MM. Padrão: mais recente disponível.",
        example="2024-03",
    ),
    com_coords: bool = Query(False, description="Incluir latitude/longitude."),
    pagina: int = Query(1, ge=1, example=1),
    por_pagina: int = Query(100, ge=1, le=1000, example=100),
    conn: Connection = Depends(get_conn),
    api_key: ApiKeyInfo = Depends(get_api_key),
) -> CapacidadeResponse:
    """Lista estabelecimentos com filtros."""
    offset = (pagina - 1) * por_pagina

    # Competência padrão = mais recente disponível
    if not competencia:
        competencia = await conn.fetchval(
            "SELECT max(competencia) FROM marts.capacidade_estabelecimentos"
        ) or "2024-03"

    filtros = [f"competencia = $1"]
    params: list[object] = [competencia]
    idx = 2

    if uf:
        ufs = [u.strip().upper() for u in uf.split(",")]
        filtros.append(f"uf = ANY(${idx}::text[])")
        params.append(ufs)
        idx += 1

    if municipio:
        filtros.append(f"municipio_codigo = ${idx}")
        params.append(municipio)
        idx += 1

    if tipo:
        filtros.append(f"tipo_unidade ILIKE ${idx}")
        params.append(f"%{tipo}%")
        idx += 1

    if gestao:
        filtros.append(f"gestao = ${idx}")
        params.append(gestao.upper())
        idx += 1

    if apenas_sus:
        filtros.append("leitos_sus > 0")

    lat_col = ", latitude, longitude" if com_coords else ", NULL::float AS latitude, NULL::float AS longitude"
    where = "WHERE " + " AND ".join(filtros)

    total = await conn.fetchval(
        f"SELECT COUNT(*) FROM marts.capacidade_estabelecimentos {where}", *params
    )
    rows = await conn.fetch(
        f"""
        SELECT
            cnes, nome, uf, municipio_codigo, municipio_nome,
            tipo_unidade, gestao,
            leitos_sus, leitos_uti,
            equipes_saude_familia, profissionais,
            competencia
            {lat_col}
        FROM marts.capacidade_estabelecimentos
        {where}
        ORDER BY leitos_sus DESC, nome
        LIMIT ${idx} OFFSET ${idx + 1}
        """,
        *params,
        por_pagina,
        offset,
    )

    return CapacidadeResponse(
        dados=[EstabelecimentoItem(**dict(r)) for r in rows],
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
    "/resumo",
    response_model=ResumoCapacidadeResponse,
    summary="Resumo de capacidade por UF",
    description="""
Agrega os indicadores de capacidade instalada por estado: total de leitos SUS,
leitos UTI por 100k habitantes, cobertura da ESF e total de estabelecimentos.

Retorna todos os 27 estados em uma única chamada — ideal para mapas de calor
e comparações nacionais.
""",
)
async def resumo_por_uf(
    competencia: Optional[str] = Query(
        None,
        description="Mês de referência AAAA-MM. Padrão: mais recente.",
        example="2024-03",
    ),
    conn: Connection = Depends(get_conn),
    api_key: ApiKeyInfo = Depends(get_api_key),
) -> ResumoCapacidadeResponse:
    """Resumo de capacidade por UF."""
    if not competencia:
        competencia = await conn.fetchval(
            "SELECT max(competencia) FROM marts.capacidade_resumo_uf"
        ) or "2024-03"

    rows = await conn.fetch(
        """
        SELECT
            uf,
            NULL::text  AS municipio_codigo,
            NULL::text  AS municipio_nome,
            total_estabelecimentos,
            total_leitos_sus,
            total_leitos_uti,
            leitos_uti_por_100k,
            equipes_esf,
            cobertura_esf_pct,
            competencia
        FROM marts.capacidade_resumo_uf
        WHERE competencia = $1
        ORDER BY total_leitos_sus DESC
        """,
        competencia,
    )

    return ResumoCapacidadeResponse(
        dados=[ResumoCapacidade(**dict(r)) for r in rows],
        rate_limit=RateLimitInfo(
            limite_hora=api_key.limite_hora,
            usadas_hora=api_key.uso_hora,
            tier=api_key.tier,
        ),
        ultima_atualizacao=await _ultima_atualizacao(conn),
    )


@router.get(
    "/leitos-uti",
    summary="Ranking de leitos UTI por 100k habitantes",
    description="""
Retorna o ranking dos estados (ou municípios) por densidade de leitos de UTI
por 100.000 habitantes.

A OMS recomenda no mínimo **1 leito de UTI por 100k habitantes**; a média
brasileira varia entre 8–12 para estados mais desenvolvidos.
""",
)
async def ranking_leitos_uti(
    granularidade: str = Query(
        "uf",
        description="'uf' para ranking estadual, 'municipio' para municipal (requer tier pro+).",
        example="uf",
    ),
    competencia: Optional[str] = Query(None, example="2024-03"),
    top_n: int = Query(27, ge=5, le=100, description="Quantidade de registros."),
    conn: Connection = Depends(get_conn),
    api_key: ApiKeyInfo = Depends(get_api_key),
):
    """Ranking de leitos UTI por 100k."""
    if granularidade == "municipio" and api_key.tier == "free":
        from fastapi import HTTPException
        raise HTTPException(
            status_code=403,
            detail="Granularidade municipal requer tier 'pro' ou 'enterprise'. "
                   "Upgrade em https://saudepublica.br/api/upgrade",
        )

    if not competencia:
        competencia = await conn.fetchval(
            "SELECT max(competencia) FROM marts.capacidade_resumo_uf"
        ) or "2024-03"

    tabela = "marts.capacidade_resumo_uf" if granularidade == "uf" else "marts.capacidade_resumo_municipio"
    rows = await conn.fetch(
        f"""
        SELECT uf, total_leitos_uti, leitos_uti_por_100k, total_estabelecimentos
        FROM {tabela}
        WHERE competencia = $1
        ORDER BY leitos_uti_por_100k DESC
        LIMIT $2
        """,
        competencia,
        top_n,
    )
    return {
        "competencia": competencia,
        "granularidade": granularidade,
        "referencia_oms": 1.0,
        "dados": [dict(r) for r in rows],
        "rate_limit": {
            "limite_hora": api_key.limite_hora,
            "usadas_hora": api_key.uso_hora,
            "tier": api_key.tier,
        },
        "fonte": "CNES/DataSUS",
    }


async def _ultima_atualizacao(conn: Connection) -> str:
    row = await conn.fetchrow(
        """
        SELECT to_char(max(concluido_em), 'YYYY-MM-DD"T"HH24:MI:SS"Z"') AS dt
        FROM pipeline_runs WHERE sistema = 'cnes' AND status = 'success'
        """
    )
    return (row["dt"] if row else None) or "2024-01-01T00:00:00Z"
