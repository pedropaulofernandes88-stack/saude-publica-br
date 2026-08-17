"""
Endpoints /v1/producao — Produção Ambulatorial (SIA/DataSUS)

Dados agregados de produção do Sistema de Informações Ambulatoriais (SIA),
com granularidade mensal por estado, município e procedimento SIGTAP.

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
    ProducaoItem,
    ProducaoResponse,
    MetaPaginacao,
    RateLimitInfo,
)

router = APIRouter(prefix="/producao", tags=["Produção Ambulatorial"])


@router.get(
    "",
    response_model=ProducaoResponse,
    summary="Listar produção ambulatorial",
    description="""
## Produção Ambulatorial — SIA/DataSUS

Retorna dados agregados de produção ambulatorial do SUS, extraídos mensalmente
do Sistema de Informações Ambulatoriais (SIA).

### Filtros disponíveis
- **uf**: Sigla do estado (ex: `SP`, `RJ`). Múltiplos separados por vírgula: `SP,RJ,MG`.
- **municipio**: Código IBGE de 6 dígitos (ex: `355030`).
- **procedimento**: Código SIGTAP de 10 dígitos. Aceita prefixo: `03` retorna todos os procedimentos que começam com 03.
- **competencia_inicio / competencia_fim**: Intervalo de meses no formato `AAAA-MM`.
- **pagina / por_pagina**: Paginação (máx 1.000 registros por página).

### Ordenação
O resultado é ordenado por `competencia DESC, uf, quantidade_aprovada DESC` por padrão.

### Notas
- Os dados são carregados semanalmente via pipeline PySUS → Parquet → DuckDB → Supabase.
- Valores monetários refletem os aprovados pela auditoria do DATASUS, não necessariamente pagos.
- Chaves `free` têm acesso retroativo de 12 meses; chaves `pro`/`enterprise` têm acesso ao histórico completo.
""",
    response_description="Lista paginada de registros de produção ambulatorial.",
    openapi_extra={
        "x-code-samples": [
            {
                "lang": "Python",
                "label": "Python SDK",
                "source": (
                    "from saude_publica_br import Client\n"
                    "client = Client(api_key='spbr_...')\n"
                    "dados = client.producao.listar(uf='SP', competencia_inicio='2024-01')\n"
                    "print(dados.meta.total)"
                ),
            },
            {
                "lang": "Shell",
                "label": "cURL",
                "source": (
                    "curl -H 'X-API-Key: spbr_...' \\\n"
                    "  'https://api.saudepublica.br/v1/producao?uf=SP&competencia_inicio=2024-01'"
                ),
            },
        ]
    },
)
async def listar_producao(
    uf: Optional[str] = Query(
        None,
        description="Sigla(s) do estado. Múltiplos separados por vírgula: `SP,RJ`.",
        example="SP",
    ),
    municipio: Optional[str] = Query(
        None,
        description="Código IBGE do município (6 dígitos).",
        example="355030",
    ),
    procedimento: Optional[str] = Query(
        None,
        description="Código SIGTAP (10 dígitos) ou prefixo (ex: `03` = todas as consultas).",
        example="0301010064",
    ),
    competencia_inicio: Optional[str] = Query(
        None,
        description="Mês de início no formato AAAA-MM.",
        example="2024-01",
    ),
    competencia_fim: Optional[str] = Query(
        None,
        description="Mês de fim no formato AAAA-MM.",
        example="2024-03",
    ),
    pagina: int = Query(1, ge=1, description="Número da página (1-based).", example=1),
    por_pagina: int = Query(
        100, ge=1, le=1000, description="Registros por página (máx 1.000).", example=100
    ),
    conn: Connection = Depends(get_conn),
    api_key: ApiKeyInfo = Depends(get_api_key),
) -> ProducaoResponse:
    """Endpoint principal de produção ambulatorial."""
    offset = (pagina - 1) * por_pagina

    # Restrição de histórico para tier free (12 meses)
    limite_historico = ""
    if api_key.tier == "free":
        limite_historico = "AND competencia >= to_char(now() - interval '12 months', 'YYYY-MM')"

    # Construção dinâmica de filtros
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

    if procedimento:
        if len(procedimento) < 10:
            filtros.append(f"procedimento_codigo LIKE ${idx}")
            params.append(procedimento + "%")
        else:
            filtros.append(f"procedimento_codigo = ${idx}")
            params.append(procedimento)
        idx += 1

    if competencia_inicio:
        filtros.append(f"competencia >= ${idx}")
        params.append(competencia_inicio)
        idx += 1

    if competencia_fim:
        filtros.append(f"competencia <= ${idx}")
        params.append(competencia_fim)
        idx += 1

    where = "WHERE " + " AND ".join(f for f in filtros if f) if any(filtros) else ""

    sql_count = f"""
        SELECT COUNT(*)
        FROM marts.producao_ambulatorial_mensal
        {where}
    """
    sql_data = f"""
        SELECT
            competencia,
            uf,
            municipio_codigo,
            procedimento_codigo,
            procedimento_nome,
            quantidade_aprovada,
            valor_aprovado,
            estabelecimentos
        FROM marts.producao_ambulatorial_mensal
        {where}
        ORDER BY competencia DESC, uf, quantidade_aprovada DESC
        LIMIT ${idx} OFFSET ${idx + 1}
    """

    total = await conn.fetchval(sql_count, *params)
    rows = await conn.fetch(sql_data, *params, por_pagina, offset)

    dados = [ProducaoItem(**dict(r)) for r in rows]

    return ProducaoResponse(
        dados=dados,
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
        ultima_atualizacao=await _ultima_atualizacao(conn, "sia"),
    )


@router.get(
    "/resumo",
    summary="Resumo de produção por UF",
    description="""
Agrega a produção ambulatorial total por estado, retornando quantidade total,
valor total e procedimentos distintos para o período especificado.
Útil para dashboards de visão geral sem necessidade de paginação.
""",
)
async def resumo_producao(
    competencia_inicio: str = Query(
        ...,
        description="Mês de início (AAAA-MM).",
        example="2024-01",
    ),
    competencia_fim: str = Query(
        ...,
        description="Mês de fim (AAAA-MM).",
        example="2024-03",
    ),
    conn: Connection = Depends(get_conn),
    api_key: ApiKeyInfo = Depends(get_api_key),
):
    """Agrega produção por UF no período."""
    rows = await conn.fetch(
        """
        SELECT
            uf,
            SUM(quantidade_aprovada)                AS total_quantidade,
            SUM(valor_aprovado)                     AS total_valor,
            COUNT(DISTINCT procedimento_codigo)     AS procedimentos_distintos,
            COUNT(DISTINCT municipio_codigo)        AS municipios_ativos
        FROM marts.producao_ambulatorial_mensal
        WHERE competencia BETWEEN $1 AND $2
        GROUP BY uf
        ORDER BY total_quantidade DESC
        """,
        competencia_inicio,
        competencia_fim,
    )
    return {
        "dados": [dict(r) for r in rows],
        "periodo": {"inicio": competencia_inicio, "fim": competencia_fim},
        "rate_limit": {
            "limite_hora": api_key.limite_hora,
            "usadas_hora": api_key.uso_hora,
            "tier": api_key.tier,
        },
        "fonte": "SIA/DataSUS",
    }


async def _ultima_atualizacao(conn: Connection, sistema: str) -> str:
    """Retorna a data da última carga bem-sucedida do sistema."""
    row = await conn.fetchrow(
        """
        SELECT to_char(max(concluido_em), 'YYYY-MM-DD"T"HH24:MI:SS"Z"') AS dt
        FROM pipeline_runs
        WHERE sistema = $1 AND status = 'success'
        """,
        sistema,
    )
    return (row["dt"] if row else None) or "2024-01-01T00:00:00Z"
