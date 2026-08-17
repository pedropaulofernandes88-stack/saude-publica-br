"""
Router principal da API pública v1.

Agrega todos os sub-routers e expõe endpoints utilitários:
  GET /v1/status  — health check público (sem autenticação)
  GET /v1/me      — informações da API key autenticada
  GET /v1/sistemas — sistemas de informação disponíveis e cobertura temporal

Prefixo: /v1
Tags: ["API v1"]
"""
from __future__ import annotations

from fastapi import APIRouter, Depends
from asyncpg import Connection

from api.deps import get_conn
from api.middleware.api_key import get_api_key, ApiKeyInfo
from api.v1 import producao, mortalidade, capacidade, doencas
from api.v1.schema import ApiKeyMeResponse, RateLimitInfo

# Router raiz /v1
v1_router = APIRouter(
    prefix="/v1",
    responses={
        401: {
            "description": "API key ausente ou inválida.",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "API key obrigatória. Forneça via header X-API-Key ou ?api_key= na query string."
                    }
                }
            },
        },
        429: {
            "description": "Rate limit atingido.",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Rate limit atingido (100 req/hora para tier free). Tente novamente em 3600s."
                    }
                }
            },
        },
        403: {
            "description": "Scope insuficiente para o recurso solicitado.",
            "content": {
                "application/json": {
                    "example": {"detail": "Scope 'write' necessário. Sua chave tem: ['read']"}
                }
            },
        },
    },
)

# Sub-routers de domínio
v1_router.include_router(producao.router)
v1_router.include_router(mortalidade.router)
v1_router.include_router(capacidade.router)
v1_router.include_router(doencas.router)


# ---------------------------------------------------------------------------
# /v1/status — health check público (sem autenticação)
# ---------------------------------------------------------------------------
@v1_router.get(
    "/status",
    tags=["Utilitários"],
    summary="Status da API",
    description="""
Verifica se a API está operacional e retorna o status dos sistemas de dados.

**Este endpoint não requer autenticação.**

Retorna:
- `status`: 'ok' | 'degradado' | 'indisponível'
- `sistemas`: estado de cada sistema de informação (SIA, SIM, SINAN, CNES)
- `ultima_carga`: data da última ingestão bem-sucedida por sistema
- `versao`: versão atual da API
""",
    response_description="Status operacional da API e dos sistemas de dados.",
)
async def status(conn: Connection = Depends(get_conn)):
    """Health check público sem autenticação."""
    sistemas_rows = await conn.fetch(
        """
        SELECT
            sistema,
            max(concluido_em)               AS ultima_carga,
            bool_and(status = 'success')    AS ok
        FROM pipeline_runs
        WHERE concluido_em > now() - interval '7 days'
        GROUP BY sistema
        ORDER BY sistema
        """
    )

    sistemas = {}
    todos_ok = True
    for r in sistemas_rows:
        ok = r["ok"]
        if not ok:
            todos_ok = False
        sistemas[r["sistema"]] = {
            "status": "ok" if ok else "degradado",
            "ultima_carga": (
                r["ultima_carga"].isoformat() + "Z" if r["ultima_carga"] else None
            ),
        }

    return {
        "status": "ok" if todos_ok else "degradado",
        "versao": "1.0.0",
        "sistemas": sistemas,
        "documentacao": "https://api.saudepublica.br/docs",
        "repositorio": "https://github.com/seu-usuario/saude-publica-br",
    }


# ---------------------------------------------------------------------------
# /v1/me — informações da API key autenticada
# ---------------------------------------------------------------------------
@v1_router.get(
    "/me",
    response_model=ApiKeyMeResponse,
    tags=["Utilitários"],
    summary="Informações da minha API key",
    description="""
Retorna informações detalhadas sobre a API key autenticada:
tier, scopes, limites de uso, total de requisições e última utilização.

Útil para que aplicações monitorem seu próprio consumo.
""",
)
async def me(
    conn: Connection = Depends(get_conn),
    api_key: ApiKeyInfo = Depends(get_api_key),
) -> ApiKeyMeResponse:
    """Dados da API key autenticada."""
    row = await conn.fetchrow(
        """
        SELECT
            key_prefix,
            nome,
            tier::text,
            scopes,
            rate_limit_hora,
            rate_limit_dia,
            total_requests,
            to_char(criado_em,  'YYYY-MM-DD"T"HH24:MI:SS"Z"') AS criado_em,
            to_char(ultimo_uso, 'YYYY-MM-DD"T"HH24:MI:SS"Z"') AS ultimo_uso
        FROM public.api_keys
        WHERE id = $1
        """,
        api_key.api_key_id,
    )
    if not row:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="API key não encontrada.")

    return ApiKeyMeResponse(
        key_prefix=row["key_prefix"],
        nome=row["nome"],
        tier=row["tier"],
        scopes=row["scopes"] or ["read"],
        rate_limit_hora=row["rate_limit_hora"],
        rate_limit_dia=row["rate_limit_dia"],
        total_requests=row["total_requests"],
        criado_em=row["criado_em"],
        ultimo_uso=row["ultimo_uso"],
        rate_limit=RateLimitInfo(
            limite_hora=api_key.limite_hora,
            usadas_hora=api_key.uso_hora,
            tier=api_key.tier,
        ),
    )


# ---------------------------------------------------------------------------
# /v1/sistemas — catálogo dos sistemas de informação disponíveis
# ---------------------------------------------------------------------------
@v1_router.get(
    "/sistemas",
    tags=["Utilitários"],
    summary="Sistemas de informação disponíveis",
    description="""
Retorna o catálogo completo dos sistemas de informação do DataSUS disponíveis
na API, com cobertura temporal e estados incluídos por sistema.
""",
)
async def sistemas(
    conn: Connection = Depends(get_conn),
    api_key: ApiKeyInfo = Depends(get_api_key),
):
    """Catálogo de sistemas disponíveis."""
    catalogo = [
        {
            "sigla": "SIA",
            "nome": "Sistema de Informações Ambulatoriais",
            "descricao": "Produção ambulatorial mensal: procedimentos, quantidades e valores aprovados.",
            "granularidade": "mensal",
            "endpoints": ["/v1/producao", "/v1/producao/resumo"],
            "anos_disponiveis": {"inicio": 2010, "fim": 2024},
            "ufs": 27,
        },
        {
            "sigla": "SIM",
            "nome": "Sistema de Informações sobre Mortalidade",
            "descricao": "Óbitos anuais por causa básica (CID-10), sexo, idade e localização.",
            "granularidade": "anual",
            "endpoints": ["/v1/mortalidade", "/v1/mortalidade/causas-principais", "/v1/mortalidade/tendencia"],
            "anos_disponiveis": {"inicio": 2010, "fim": 2023},
            "ufs": 27,
        },
        {
            "sigla": "SINAN",
            "nome": "Sistema de Informação de Agravos de Notificação",
            "descricao": "Doenças de notificação compulsória por semana epidemiológica, com alertas Prophet.",
            "granularidade": "semanal",
            "endpoints": ["/v1/doencas", "/v1/doencas/surtos", "/v1/doencas/serie", "/v1/doencas/agravos"],
            "anos_disponiveis": {"inicio": 2015, "fim": 2024},
            "ufs": 27,
            "agravos_disponiveis": 15,
        },
        {
            "sigla": "CNES",
            "nome": "Cadastro Nacional de Estabelecimentos de Saúde",
            "descricao": "Estabelecimentos, leitos, profissionais e cobertura ESF por mês e localização.",
            "granularidade": "mensal",
            "endpoints": ["/v1/capacidade/estabelecimentos", "/v1/capacidade/resumo", "/v1/capacidade/leitos-uti"],
            "anos_disponiveis": {"inicio": 2019, "fim": 2024},
            "ufs": 27,
        },
        {
            "sigla": "SIH",
            "nome": "Sistema de Informações Hospitalares",
            "descricao": "Internações hospitalares: diagnóstico, procedimento, tempo de permanência e custo.",
            "granularidade": "mensal",
            "endpoints": ["em breve — previsto para v1.1"],
            "status": "em_desenvolvimento",
        },
    ]

    return {
        "sistemas": catalogo,
        "total": len(catalogo),
        "rate_limit": {
            "limite_hora": api_key.limite_hora,
            "usadas_hora": api_key.uso_hora,
            "tier": api_key.tier,
        },
    }

# Alias para compatibilidade com api/main.py
router = v1_router
