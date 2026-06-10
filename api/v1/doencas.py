"""
Endpoints /v1/doencas — Doenças e Agravos Notificáveis (SINAN/DataSUS)

Dados do Sistema de Informação de Agravos de Notificação (SINAN), com
granularidade semanal (semana epidemiológica) por estado e agravo CID-10.
Inclui alertas de anomalia detectados pelo modelo Prophet (ML).

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
    DoencaItem,
    DoencaResponse,
    SurtoItem,
    SurtosResponse,
    MetaPaginacao,
    RateLimitInfo,
)

router = APIRouter(prefix="/doencas", tags=["Doenças e Agravos"])


# Agravos disponíveis no SINAN com seus códigos CID-10
AGRAVOS_SINAN = {
    "A90": "Dengue",
    "A92.0": "Chikungunya",
    "A928": "Zika",
    "A15": "Tuberculose",
    "B50": "Malária",
    "A27": "Leptospirose",
    "A37": "Coqueluche",
    "A95": "Febre amarela",
    "B05": "Sarampo",
    "A33": "Tétano neonatal",
    "B26": "Caxumba",
    "A00": "Cólera",
    "A01": "Febre tifoide",
    "A22": "Carbúnculo (Antraz)",
    "A98.0": "Febre hemorrágica da Crimeia-Congo",
}


@router.get(
    "",
    response_model=DoencaResponse,
    summary="Listar notificações de doenças e agravos",
    description="""
## Doenças e Agravos — SINAN/DataSUS

Dados semanais de doenças de notificação compulsória do SINAN,
com alertas epidemiológicos gerados pelo modelo Prophet (ML).

### Filtros
- **uf**: Sigla(s) do estado.
- **agravo**: Código CID-10 do agravo. Use `/v1/doencas/agravos` para listar os disponíveis.
- **ano**: Ano epidemiológico.
- **semana_inicio / semana_fim**: Semanas epidemiológicas (1–53).
- **apenas_alertas**: Se `true`, retorna apenas registros com alertas Prophet.

### Semana Epidemiológica
A semana epidemiológica brasileira começa no domingo e segue o padrão
da Organização Pan-Americana da Saúde (OPAS). A semana 1 do ano é a
primeira semana com pelo menos 4 dias em janeiro.

### Alertas Prophet
O campo `alertas` pode conter:
- `ANOMALIA_PROPHET`: casos observados > limite superior do intervalo de confiança 95%.
- `LIMIAR_EPIDEMICO`: casos > limiar epidêmico calculado pela média histórica + 2 desvios.

### Notas
- Dados com atraso de ~2 semanas (tempo de digitação nos municípios).
- Casos em investigação são incluídos mas marcados como `status = 'INVESTIGAÇÃO'`.
- Chaves `free`: últimos 2 anos. `pro`/`enterprise`: histórico completo.
""",
)
async def listar_doencas(
    uf: Optional[str] = Query(None, example="AM"),
    agravo: Optional[str] = Query(
        None,
        description="Código CID-10 do agravo (ex: `A90` = Dengue).",
        example="A90",
    ),
    ano: Optional[int] = Query(None, ge=2000, le=2030, example=2024),
    semana_inicio: Optional[int] = Query(None, ge=1, le=53, example=1),
    semana_fim: Optional[int] = Query(None, ge=1, le=53, example=52),
    apenas_alertas: bool = Query(
        False,
        description="Se true, retorna apenas registros com alertas Prophet.",
    ),
    pagina: int = Query(1, ge=1, example=1),
    por_pagina: int = Query(100, ge=1, le=1000, example=100),
    conn: Connection = Depends(get_conn),
    api_key: ApiKeyInfo = Depends(get_api_key),
) -> DoencaResponse:
    """Endpoint principal de notificações."""
    offset = (pagina - 1) * por_pagina

    limite_historico = ""
    if api_key.tier == "free":
        limite_historico = "AND ano >= EXTRACT(YEAR FROM now())::int - 2"

    filtros: list[str] = [limite_historico]
    params: list[object] = []
    idx = 1

    if uf:
        ufs = [u.strip().upper() for u in uf.split(",")]
        filtros.append(f"uf = ANY(${idx}::text[])")
        params.append(ufs)
        idx += 1

    if agravo:
        filtros.append(f"agravo_cid10 = ${idx}")
        params.append(agravo.upper())
        idx += 1

    if ano:
        filtros.append(f"ano = ${idx}")
        params.append(ano)
        idx += 1

    if semana_inicio:
        filtros.append(f"semana_epidemiologica >= ${idx}")
        params.append(semana_inicio)
        idx += 1

    if semana_fim:
        filtros.append(f"semana_epidemiologica <= ${idx}")
        params.append(semana_fim)
        idx += 1

    if apenas_alertas:
        filtros.append("cardinality(alertas) > 0")

    where = "WHERE " + " AND ".join(f for f in filtros if f) if any(filtros) else ""

    total = await conn.fetchval(
        f"SELECT COUNT(*) FROM marts.doencas_semana_epidemiologica {where}", *params
    )
    rows = await conn.fetch(
        f"""
        SELECT
            ano, semana_epidemiologica, uf, municipio_codigo,
            agravo_cid10, agravo_nome,
            casos, casos_graves, obitos,
            incidencia_100k, alertas
        FROM marts.doencas_semana_epidemiologica
        {where}
        ORDER BY ano DESC, semana_epidemiologica DESC, casos DESC
        LIMIT ${idx} OFFSET ${idx + 1}
        """,
        *params,
        por_pagina,
        offset,
    )

    return DoencaResponse(
        dados=[DoencaItem(**dict(r)) for r in rows],
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
    "/agravos",
    summary="Listar agravos disponíveis",
    description="Retorna a lista de doenças/agravos disponíveis no SINAN com seus códigos CID-10.",
)
async def listar_agravos(
    api_key: ApiKeyInfo = Depends(get_api_key),
):
    """Lista agravos disponíveis."""
    return {
        "dados": [
            {"cid10": cid, "nome": nome}
            for cid, nome in AGRAVOS_SINAN.items()
        ],
        "total": len(AGRAVOS_SINAN),
        "rate_limit": {
            "limite_hora": api_key.limite_hora,
            "usadas_hora": api_key.uso_hora,
            "tier": api_key.tier,
        },
    }


@router.get(
    "/surtos",
    response_model=SurtosResponse,
    summary="Surtos e alertas epidemiológicos ativos",
    description="""
## Alertas Epidemiológicos Ativos

Retorna surtos e clusters em andamento detectados pelo modelo Prophet
nas últimas 4 semanas epidemiológicas.

### Níveis de Alerta
| Nível | Razão Obs/Esp | Cor |
|-------|--------------|-----|
| VERDE | < 1.5 | ✅ Normal |
| AMARELO | 1.5 – 2.9 | ⚠️ Atenção |
| LARANJA | 3.0 – 4.9 | 🟠 Alerta |
| VERMELHO | ≥ 5.0 | 🔴 Emergência |

Endpoint especialmente útil para integração com sistemas de vigilância
epidemiológica municipal e estadual.
""",
)
async def listar_surtos(
    uf: Optional[str] = Query(None, description="Filtrar por UF.", example="AM"),
    agravo: Optional[str] = Query(None, example="A90"),
    nivel_minimo: str = Query(
        "AMARELO",
        description="Nível mínimo de alerta: 'AMARELO', 'LARANJA' ou 'VERMELHO'.",
        example="LARANJA",
    ),
    conn: Connection = Depends(get_conn),
    api_key: ApiKeyInfo = Depends(get_api_key),
) -> SurtosResponse:
    """Surtos ativos nas últimas 4 semanas."""
    niveis = {"VERDE": 0, "AMARELO": 1, "LARANJA": 2, "VERMELHO": 3}
    nivel_idx = niveis.get(nivel_minimo.upper(), 1)
    niveis_filtro = [n for n, i in niveis.items() if i >= nivel_idx]

    filtros = ["nivel_alerta = ANY($1::text[])"]
    params: list[object] = [niveis_filtro]
    idx = 2

    if uf:
        filtros.append(f"uf = ${idx}")
        params.append(uf.upper())
        idx += 1

    if agravo:
        filtros.append(f"agravo_nome ILIKE ${idx}")
        params.append(f"%{agravo}%")
        idx += 1

    where = "WHERE " + " AND ".join(filtros)

    rows = await conn.fetch(
        f"""
        SELECT
            agravo_nome, uf,
            semana_inicio, semana_fim,
            casos_observados, casos_esperados,
            razao_observado_esperado, nivel_alerta
        FROM marts.alertas_epidemiologicos
        {where}
        ORDER BY razao_observado_esperado DESC
        LIMIT 200
        """,
        *params,
    )

    gerado_em = await conn.fetchval(
        "SELECT to_char(now(), 'YYYY-MM-DD\"T\"HH24:MI:SS\"Z\"')"
    )

    return SurtosResponse(
        dados=[SurtoItem(**dict(r)) for r in rows],
        rate_limit=RateLimitInfo(
            limite_hora=api_key.limite_hora,
            usadas_hora=api_key.uso_hora,
            tier=api_key.tier,
        ),
        gerado_em=gerado_em or "2024-01-01T00:00:00Z",
    )


@router.get(
    "/serie",
    summary="Série temporal de um agravo por UF",
    description="""
Retorna a série histórica semanal de casos de um agravo específico em um estado.
Inclui o intervalo de confiança do Prophet (yhat_lower, yhat_upper) quando disponível.

Ideal para construir gráficos de linha com banda de confiança do modelo preditivo.
""",
)
async def serie_temporal(
    uf: str = Query(..., example="AM"),
    agravo: str = Query(..., description="Código CID-10.", example="A90"),
    ano: int = Query(..., ge=2000, le=2030, example=2024),
    conn: Connection = Depends(get_conn),
    api_key: ApiKeyInfo = Depends(get_api_key),
):
    """Série semanal com bandas Prophet."""
    rows = await conn.fetch(
        """
        SELECT
            semana_epidemiologica,
            casos,
            incidencia_100k,
            prophet_yhat,
            prophet_yhat_lower,
            prophet_yhat_upper,
            alertas
        FROM marts.doencas_semana_epidemiologica
        WHERE uf = $1 AND agravo_cid10 = $2 AND ano = $3
        ORDER BY semana_epidemiologica
        """,
        uf.upper(),
        agravo.upper(),
        ano,
    )
    return {
        "uf": uf.upper(),
        "agravo_cid10": agravo.upper(),
        "agravo_nome": AGRAVOS_SINAN.get(agravo.upper(), agravo),
        "ano": ano,
        "serie": [dict(r) for r in rows],
        "rate_limit": {
            "limite_hora": api_key.limite_hora,
            "usadas_hora": api_key.uso_hora,
            "tier": api_key.tier,
        },
        "fonte": "SINAN/DataSUS + Prophet ML",
    }


async def _ultima_atualizacao(conn: Connection) -> str:
    row = await conn.fetchrow(
        """
        SELECT to_char(max(concluido_em), 'YYYY-MM-DD"T"HH24:MI:SS"Z"') AS dt
        FROM pipeline_runs WHERE sistema = 'sinan' AND status = 'success'
        """
    )
    return (row["dt"] if row else None) or "2024-01-01T00:00:00Z"
