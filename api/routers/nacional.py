"""
Router Nacional — /nacional/*
Endpoints agregados para todos os 27 estados do Brasil (2019–2024).

Cada endpoint suporta filtros opcionais por UF, região, ano e mês.
Respostas são cacheadas no Redis com TTL configurável para reduzir
carga no banco em consultas repetidas (dados históricos não mudam).
"""

from __future__ import annotations

import hashlib
import json
import logging
from enum import Enum
from typing import Any, Optional

import asyncpg
import redis.asyncio as aioredis
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuração
# ---------------------------------------------------------------------------

router = APIRouter(prefix="/nacional", tags=["Nacional – 27 estados"])

# TTL de cache por tipo de endpoint (segundos)
CACHE_TTL = {
    "producao":    3600 * 6,   # 6 horas  — atualização semanal
    "mortalidade": 3600 * 12,  # 12 horas — atualização mensal
    "capacidade":  3600 * 24,  # 24 horas — atualização mensal
    "doencas":     3600 * 4,   # 4 horas  — atualização semanal (SINAN)
    "ranking":     3600 * 6,   # 6 horas
}

# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class RegiaoEnum(str, Enum):
    norte        = "Norte"
    nordeste     = "Nordeste"
    centro_oeste = "Centro-Oeste"
    sudeste      = "Sudeste"
    sul          = "Sul"

class SistemaEnum(str, Enum):
    sia   = "SIA"
    sim   = "SIM"
    sih   = "SIH"
    sinan = "SINAN"
    cnes  = "CNES"

class MetricaRankingEnum(str, Enum):
    procedimentos          = "procedimentos"
    valor_brl              = "valor_brl"
    taxa_proc_por_1k_hab   = "taxa_proc_por_1k_hab"
    obitos                 = "obitos"
    taxa_mortalidade_100k  = "taxa_mortalidade_100k"
    leitos_sus             = "leitos_sus"
    taxa_leitos_sus_1k     = "taxa_leitos_sus_1k"
    medicos                = "medicos"
    taxa_medicos_1k        = "taxa_medicos_1k"
    notificacoes           = "notificacoes"
    taxa_incidencia_100k   = "taxa_incidencia_100k"

# ---------------------------------------------------------------------------
# Schemas de resposta
# ---------------------------------------------------------------------------

class ProducaoNacionalItem(BaseModel):
    uf_sigla:               str
    nome_uf:                str
    regiao:                 str
    ano:                    int
    mes:                    int
    complexidade:           str
    procedimentos:          int
    valor_brl:              float
    pacientes_unicos:       Optional[int]
    taxa_proc_por_1k_hab:   Optional[float]
    variacao_yoy_pct:       Optional[float]

class MortalidadeNacionalItem(BaseModel):
    uf_sigla:                   str
    nome_uf:                    str
    regiao:                     str
    ano:                        int
    mes:                        int
    cid10_capitulo:             str
    sexo:                       str
    faixa_etaria:               str
    obitos:                     int
    taxa_mortalidade_100k:      Optional[float]
    pct_causas_cronicas:        Optional[float]
    variacao_obitos_yoy_pct:    Optional[float]

class CapacidadeNacionalItem(BaseModel):
    uf_sigla:                   str
    nome_uf:                    str
    regiao:                     str
    ano:                        int
    tipo_unidade_cod:           str
    tipo_unidade_descricao:     str
    estabelecimentos:           int
    leitos_sus:                 int
    leitos_totais:              int
    uti_total_sus:              int
    medicos:                    int
    enfermeiros:                int
    taxa_leitos_sus_1k:         Optional[float]
    taxa_medicos_1k:            Optional[float]
    variacao_leitos_sus_yoy_pct: Optional[float]

class DoencasNacionalItem(BaseModel):
    uf_sigla:                   str
    nome_uf:                    str
    regiao:                     str
    ano:                        int
    semana_epidemiologica:      Optional[int]
    agravo:                     str
    cid10_grupo:                str
    notificacoes:               int
    casos_confirmados:          int
    obitos_agravo:              int
    taxa_incidencia_100k:       Optional[float]
    taxa_letalidade_pct:        Optional[float]
    alerta_epidemiologico:      bool
    variacao_casos_yoy_pct:     Optional[float]

class RankingItem(BaseModel):
    posicao:    int
    uf_sigla:   str
    nome_uf:    str
    regiao:     str
    metrica:    str
    valor:      float
    ano:        int

class ResumoNacionalResponse(BaseModel):
    total_registros:    int
    pagina:             int
    pagina_tamanho:     int
    total_paginas:      int
    filtros_aplicados:  dict[str, Any]
    dados:              list[Any]

# ---------------------------------------------------------------------------
# Dependências
# ---------------------------------------------------------------------------

async def get_db() -> asyncpg.Pool:
    """
    Retorna o pool de conexões PostgreSQL.
    Em produção, o pool é criado no startup da aplicação (app.state.db_pool).
    Aqui importamos para manter compatibilidade com o padrão do projeto.
    """
    from api.main import app  # import circular leve — somente em runtime
    return app.state.db_pool

async def get_redis() -> Optional[aioredis.Redis]:
    """Retorna cliente Redis ou None se não configurado."""
    try:
        from api.main import app
        return getattr(app.state, "redis", None)
    except Exception:
        return None

# ---------------------------------------------------------------------------
# Helpers de cache
# ---------------------------------------------------------------------------

def _cache_key(endpoint: str, params: dict) -> str:
    """Gera chave de cache determinística a partir do endpoint + parâmetros."""
    params_str = json.dumps(params, sort_keys=True, default=str)
    digest     = hashlib.md5(params_str.encode()).hexdigest()[:12]
    return f"saude:nacional:{endpoint}:{digest}"

async def _get_cached(redis: Optional[aioredis.Redis], key: str) -> Optional[list]:
    """Lê do cache Redis. Retorna None se ausente ou Redis indisponível."""
    if redis is None:
        return None
    try:
        raw = await redis.get(key)
        return json.loads(raw) if raw else None
    except Exception as exc:
        logger.warning("Redis GET falhou: %s", exc)
        return None

async def _set_cached(
    redis: Optional[aioredis.Redis],
    key: str,
    value: list,
    ttl: int,
) -> None:
    """Salva no cache Redis. Falha silenciosa."""
    if redis is None:
        return
    try:
        await redis.setex(key, ttl, json.dumps(value, default=str))
    except Exception as exc:
        logger.warning("Redis SET falhou: %s", exc)

# ---------------------------------------------------------------------------
# Helper de paginação
# ---------------------------------------------------------------------------

def _paginate(data: list, pagina: int, tamanho: int) -> tuple[list, int]:
    """Pagina uma lista em memória. Retorna (página, total_páginas)."""
    total  = len(data)
    inicio = (pagina - 1) * tamanho
    fim    = inicio + tamanho
    n_pag  = max(1, (total + tamanho - 1) // tamanho)
    return data[inicio:fim], n_pag

# ---------------------------------------------------------------------------
# Helper de query com filtros dinâmicos
# ---------------------------------------------------------------------------

def _build_filters(
    ufs:     Optional[list[str]],
    regioes: Optional[list[RegiaoEnum]],
    anos:    Optional[list[int]],
    meses:   Optional[list[int]],
) -> tuple[str, list]:
    """
    Constrói cláusula WHERE dinâmica e lista de parâmetros posicionais ($1, $2, …).
    Retorna (where_clause, params).
    """
    clauses: list[str] = []
    params:  list[Any] = []
    idx = 1

    if ufs:
        ufs_upper = [u.upper() for u in ufs]
        clauses.append(f"uf_sigla = ANY(${idx})")
        params.append(ufs_upper)
        idx += 1

    if regioes:
        clauses.append(f"regiao = ANY(${idx})")
        params.append([r.value for r in regioes])
        idx += 1

    if anos:
        clauses.append(f"ano = ANY(${idx})")
        params.append(anos)
        idx += 1

    if meses:
        clauses.append(f"mes = ANY(${idx})")
        params.append(meses)
        idx += 1

    where = ("WHERE " + " AND ".join(clauses)) if clauses else ""
    return where, params

# ---------------------------------------------------------------------------
# Endpoint: Produção Ambulatorial Nacional
# ---------------------------------------------------------------------------

@router.get(
    "/producao",
    response_model=ResumoNacionalResponse,
    summary="Produção ambulatorial nacional – todos os 27 estados",
    description="""
Retorna dados agregados do SIA/PA (Produção Ambulatorial) para todos os estados.

**Métricas disponíveis:**
- Procedimentos realizados por UF, mês, ano e complexidade
- Valor total em R$
- Taxa de procedimentos por 1.000 habitantes
- Variação percentual ano a ano (YoY)

**Paginação:** Use `pagina` e `pagina_tamanho` para controlar o volume retornado.
    """,
)
async def get_producao_nacional(
    ufs:           Optional[list[str]]       = Query(None, description="Filtrar por siglas de UF (ex: SP, RJ)"),
    regioes:       Optional[list[RegiaoEnum]] = Query(None, description="Filtrar por região geográfica"),
    anos:          Optional[list[int]]        = Query(None, ge=2019, le=2024, description="Filtrar por ano(s)"),
    meses:         Optional[list[int]]        = Query(None, ge=1, le=12, description="Filtrar por mês(es)"),
    complexidades: Optional[list[str]]        = Query(None, description="Filtrar por complexidade (AB, MC, AC)"),
    pagina:        int                        = Query(1, ge=1, description="Página (começa em 1)"),
    tamanho:       int                        = Query(100, ge=1, le=1000, description="Registros por página"),
    db:            asyncpg.Pool               = Depends(get_db),
    redis:         Optional[aioredis.Redis]   = Depends(get_redis),
) -> ResumoNacionalResponse:

    filtros = dict(ufs=ufs, regioes=[r.value if r else r for r in (regioes or [])],
                   anos=anos, meses=meses, complexidades=complexidades)
    cache_key = _cache_key("producao", filtros)

    # Tentar cache
    cached = await _get_cached(redis, cache_key)
    if cached is not None:
        pagina_dados, n_pag = _paginate(cached, pagina, tamanho)
        return ResumoNacionalResponse(
            total_registros=len(cached),
            pagina=pagina,
            pagina_tamanho=tamanho,
            total_paginas=n_pag,
            filtros_aplicados=filtros,
            dados=pagina_dados,
        )

    # Construir query
    where, params = _build_filters(ufs, regioes, anos, meses)
    extra_clauses: list[str] = []
    if complexidades:
        idx = len(params) + 1
        extra_clauses.append(f"complexidade = ANY(${idx})")
        params.append(complexidades)

    if extra_clauses:
        where = (where + " AND " + " AND ".join(extra_clauses)).lstrip("AND ").strip()
        if not where.startswith("WHERE"):
            where = "WHERE " + where

    sql = f"""
        SELECT
            uf_sigla, nome_uf, regiao, ano, mes, complexidade,
            procedimentos, valor_brl, pacientes_unicos,
            taxa_proc_por_1k_hab, variacao_yoy_pct
        FROM marts.nacional_producao
        {where}
        ORDER BY uf_sigla, ano, mes, complexidade
    """

    try:
        rows = await db.fetch(sql, *params)
    except Exception as exc:
        logger.error("Erro ao buscar producao nacional: %s", exc)
        raise HTTPException(status_code=500, detail="Erro interno ao buscar dados de produção")

    dados = [dict(r) for r in rows]
    await _set_cached(redis, cache_key, dados, CACHE_TTL["producao"])

    pagina_dados, n_pag = _paginate(dados, pagina, tamanho)
    return ResumoNacionalResponse(
        total_registros=len(dados),
        pagina=pagina,
        pagina_tamanho=tamanho,
        total_paginas=n_pag,
        filtros_aplicados=filtros,
        dados=pagina_dados,
    )

# ---------------------------------------------------------------------------
# Endpoint: Mortalidade Nacional
# ---------------------------------------------------------------------------

@router.get(
    "/mortalidade",
    response_model=ResumoNacionalResponse,
    summary="Mortalidade nacional – todos os 27 estados",
    description="""
Retorna dados agregados do SIM/DO (mortalidade) para todos os estados.

**Métricas disponíveis:**
- Óbitos por UF, CID-10 capítulo, sexo e faixa etária
- Taxa bruta de mortalidade por 100.000 hab
- % de causas crônicas
- Variação YoY de óbitos
    """,
)
async def get_mortalidade_nacional(
    ufs:              Optional[list[str]]       = Query(None),
    regioes:          Optional[list[RegiaoEnum]] = Query(None),
    anos:             Optional[list[int]]        = Query(None, ge=2019, le=2024),
    meses:            Optional[list[int]]        = Query(None, ge=1, le=12),
    cid10_capitulos:  Optional[list[str]]        = Query(None, description="Filtrar por capítulo CID-10 (A–Z)"),
    sexos:            Optional[list[str]]        = Query(None, description="Masculino, Feminino, Ignorado"),
    pagina:           int                        = Query(1, ge=1),
    tamanho:          int                        = Query(100, ge=1, le=1000),
    db:               asyncpg.Pool               = Depends(get_db),
    redis:            Optional[aioredis.Redis]   = Depends(get_redis),
) -> ResumoNacionalResponse:

    filtros = dict(ufs=ufs, regioes=[r.value if r else r for r in (regioes or [])],
                   anos=anos, meses=meses, cid10_capitulos=cid10_capitulos, sexos=sexos)
    cache_key = _cache_key("mortalidade", filtros)

    cached = await _get_cached(redis, cache_key)
    if cached is not None:
        pagina_dados, n_pag = _paginate(cached, pagina, tamanho)
        return ResumoNacionalResponse(
            total_registros=len(cached), pagina=pagina,
            pagina_tamanho=tamanho, total_paginas=n_pag,
            filtros_aplicados=filtros, dados=pagina_dados,
        )

    where, params = _build_filters(ufs, regioes, anos, meses)
    extra: list[str] = []
    if cid10_capitulos:
        idx = len(params) + 1
        extra.append(f"cid10_capitulo = ANY(${idx})")
        params.append([c.upper() for c in cid10_capitulos])
    if sexos:
        idx = len(params) + 1
        extra.append(f"sexo = ANY(${idx})")
        params.append(sexos)
    if extra:
        connector = " AND " if where else "WHERE "
        where = where + connector + " AND ".join(extra)

    sql = f"""
        SELECT
            uf_sigla, nome_uf, regiao, ano, mes,
            cid10_capitulo, cid10_grupo, sexo, faixa_etaria,
            local_obito_descricao,
            obitos, taxa_mortalidade_100k,
            pct_causas_cronicas, variacao_obitos_yoy_pct
        FROM marts.nacional_mortalidade
        {where}
        ORDER BY uf_sigla, ano, mes, cid10_capitulo
    """

    try:
        rows = await db.fetch(sql, *params)
    except Exception as exc:
        logger.error("Erro ao buscar mortalidade nacional: %s", exc)
        raise HTTPException(status_code=500, detail="Erro interno ao buscar dados de mortalidade")

    dados = [dict(r) for r in rows]
    await _set_cached(redis, cache_key, dados, CACHE_TTL["mortalidade"])

    pagina_dados, n_pag = _paginate(dados, pagina, tamanho)
    return ResumoNacionalResponse(
        total_registros=len(dados), pagina=pagina,
        pagina_tamanho=tamanho, total_paginas=n_pag,
        filtros_aplicados=filtros, dados=pagina_dados,
    )

# ---------------------------------------------------------------------------
# Endpoint: Capacidade Instalada Nacional
# ---------------------------------------------------------------------------

@router.get(
    "/capacidade",
    response_model=ResumoNacionalResponse,
    summary="Capacidade instalada nacional – todos os 27 estados",
    description="""
Retorna dados agregados do CNES (capacidade instalada) para todos os estados.

**Métricas disponíveis:**
- Estabelecimentos, leitos SUS, UTI, médicos, enfermeiros
- Taxas por 1.000 / 10.000 habitantes
- Variação YoY de leitos e médicos
    """,
)
async def get_capacidade_nacional(
    ufs:         Optional[list[str]]       = Query(None),
    regioes:     Optional[list[RegiaoEnum]] = Query(None),
    anos:        Optional[list[int]]        = Query(None, ge=2019, le=2024),
    tipos:       Optional[list[str]]        = Query(None, description="Filtrar por código de tipo de unidade CNES"),
    pagina:      int                        = Query(1, ge=1),
    tamanho:     int                        = Query(100, ge=1, le=1000),
    db:          asyncpg.Pool               = Depends(get_db),
    redis:       Optional[aioredis.Redis]   = Depends(get_redis),
) -> ResumoNacionalResponse:

    filtros = dict(ufs=ufs, regioes=[r.value if r else r for r in (regioes or [])],
                   anos=anos, tipos=tipos)
    cache_key = _cache_key("capacidade", filtros)

    cached = await _get_cached(redis, cache_key)
    if cached is not None:
        pagina_dados, n_pag = _paginate(cached, pagina, tamanho)
        return ResumoNacionalResponse(
            total_registros=len(cached), pagina=pagina,
            pagina_tamanho=tamanho, total_paginas=n_pag,
            filtros_aplicados=filtros, dados=pagina_dados,
        )

    where, params = _build_filters(ufs, regioes, anos, meses=None)
    if tipos:
        idx = len(params) + 1
        connector = " AND " if where else "WHERE "
        where = where + connector + f"tipo_unidade_cod = ANY(${idx})"
        params.append(tipos)

    sql = f"""
        SELECT
            uf_sigla, nome_uf, regiao, ano, mes_referencia,
            tipo_unidade_cod, tipo_unidade_descricao,
            estabelecimentos, estabelecimentos_ativos, pct_estabelecimentos_ativos,
            leitos_sus, leitos_totais, uti_total_sus,
            medicos, enfermeiros, tecnicos_enfermagem,
            taxa_leitos_sus_1k, taxa_leitos_totais_1k,
            taxa_medicos_1k, taxa_uti_sus_1k,
            variacao_leitos_sus_yoy_pct, variacao_medicos_yoy_pct
        FROM marts.nacional_capacidade
        {where}
        ORDER BY uf_sigla, ano, tipo_unidade_cod
    """

    try:
        rows = await db.fetch(sql, *params)
    except Exception as exc:
        logger.error("Erro ao buscar capacidade nacional: %s", exc)
        raise HTTPException(status_code=500, detail="Erro interno ao buscar dados de capacidade")

    dados = [dict(r) for r in rows]
    await _set_cached(redis, cache_key, dados, CACHE_TTL["capacidade"])

    pagina_dados, n_pag = _paginate(dados, pagina, tamanho)
    return ResumoNacionalResponse(
        total_registros=len(dados), pagina=pagina,
        pagina_tamanho=tamanho, total_paginas=n_pag,
        filtros_aplicados=filtros, dados=pagina_dados,
    )

# ---------------------------------------------------------------------------
# Endpoint: Doenças e Agravos Nacional
# ---------------------------------------------------------------------------

@router.get(
    "/doencas",
    response_model=ResumoNacionalResponse,
    summary="Doenças e agravos nacional – todos os 27 estados",
    description="""
Retorna dados agregados do SINAN + SIH/AIH para todos os estados.

**Métricas disponíveis:**
- Notificações, casos confirmados, óbitos por agravo
- Taxa de incidência por 100.000 hab
- Taxa de letalidade
- Alerta epidemiológico (crescimento > 20% YoY)
- Cruzamento com internações hospitalares (SIH)
    """,
)
async def get_doencas_nacional(
    ufs:       Optional[list[str]]       = Query(None),
    regioes:   Optional[list[RegiaoEnum]] = Query(None),
    anos:      Optional[list[int]]        = Query(None, ge=2019, le=2024),
    meses:     Optional[list[int]]        = Query(None, ge=1, le=12),
    agravos:   Optional[list[str]]        = Query(None, description="Filtrar por nome do agravo"),
    alertas:   Optional[bool]             = Query(None, description="Se True, retorna apenas agravos com alerta epidemiológico"),
    pagina:    int                        = Query(1, ge=1),
    tamanho:   int                        = Query(100, ge=1, le=1000),
    db:        asyncpg.Pool               = Depends(get_db),
    redis:     Optional[aioredis.Redis]   = Depends(get_redis),
) -> ResumoNacionalResponse:

    filtros = dict(ufs=ufs, regioes=[r.value if r else r for r in (regioes or [])],
                   anos=anos, meses=meses, agravos=agravos, alertas=alertas)
    cache_key = _cache_key("doencas", filtros)

    cached = await _get_cached(redis, cache_key)
    if cached is not None:
        pagina_dados, n_pag = _paginate(cached, pagina, tamanho)
        return ResumoNacionalResponse(
            total_registros=len(cached), pagina=pagina,
            pagina_tamanho=tamanho, total_paginas=n_pag,
            filtros_aplicados=filtros, dados=pagina_dados,
        )

    where, params = _build_filters(ufs, regioes, anos, meses)
    extra: list[str] = []
    if agravos:
        idx = len(params) + 1
        extra.append(f"agravo = ANY(${idx})")
        params.append([a.upper() for a in agravos])
    if alertas is not None:
        extra.append(f"alerta_epidemiologico = {str(alertas).lower()}")
    if extra:
        connector = " AND " if where else "WHERE "
        where = where + connector + " AND ".join(extra)

    sql = f"""
        SELECT
            uf_sigla, nome_uf, regiao, ano, semana_epidemiologica, mes,
            agravo, cid10_grupo, evolucao,
            notificacoes, casos_confirmados, hospitalizados, obitos_agravo,
            internacoes_sih, obitos_internacao_sih, total_obitos_estimado,
            taxa_incidencia_100k, taxa_notificacao_100k,
            taxa_hospitalizacao_pct, taxa_letalidade_pct,
            alerta_epidemiologico,
            variacao_casos_yoy_pct, variacao_notificacoes_yoy_pct
        FROM marts.nacional_doencas
        {where}
        ORDER BY uf_sigla, ano, agravo, semana_epidemiologica
    """

    try:
        rows = await db.fetch(sql, *params)
    except Exception as exc:
        logger.error("Erro ao buscar doencas nacional: %s", exc)
        raise HTTPException(status_code=500, detail="Erro interno ao buscar dados de doenças")

    dados = [dict(r) for r in rows]
    await _set_cached(redis, cache_key, dados, CACHE_TTL["doencas"])

    pagina_dados, n_pag = _paginate(dados, pagina, tamanho)
    return ResumoNacionalResponse(
        total_registros=len(dados), pagina=pagina,
        pagina_tamanho=tamanho, total_paginas=n_pag,
        filtros_aplicados=filtros, dados=pagina_dados,
    )

# ---------------------------------------------------------------------------
# Endpoint: Ranking de estados por métrica
# ---------------------------------------------------------------------------

@router.get(
    "/ranking",
    response_model=list[RankingItem],
    summary="Ranking de estados por métrica de saúde",
    description="""
Retorna os 27 estados ordenados por uma métrica específica para um determinado ano.

**Métricas disponíveis:**
- Produção: `procedimentos`, `valor_brl`, `taxa_proc_por_1k_hab`
- Mortalidade: `obitos`, `taxa_mortalidade_100k`
- Capacidade: `leitos_sus`, `taxa_leitos_sus_1k`, `medicos`, `taxa_medicos_1k`
- Doenças: `notificacoes`, `taxa_incidencia_100k`

O ranking é calculado sobre a soma anual de cada UF.
    """,
)
async def get_ranking_nacional(
    metrica:   MetricaRankingEnum = Query(..., description="Métrica para o ranking"),
    ano:       int                = Query(..., ge=2019, le=2024, description="Ano de referência"),
    ordem:     str                = Query("desc", regex="^(asc|desc)$", description="Ordenação: asc ou desc"),
    regiao:    Optional[RegiaoEnum] = Query(None, description="Filtrar por região"),
    db:        asyncpg.Pool       = Depends(get_db),
    redis:     Optional[aioredis.Redis] = Depends(get_redis),
) -> list[RankingItem]:

    filtros = dict(metrica=metrica.value, ano=ano, ordem=ordem, regiao=regiao.value if regiao else None)
    cache_key = _cache_key("ranking", filtros)

    cached = await _get_cached(redis, cache_key)
    if cached is not None:
        return [RankingItem(**r) for r in cached]

    # Mapear métrica → tabela e coluna
    metrica_map = {
        "procedimentos":        ("marts.nacional_producao",   "sum(procedimentos)"),
        "valor_brl":            ("marts.nacional_producao",   "sum(valor_brl)"),
        "taxa_proc_por_1k_hab": ("marts.nacional_producao",   "avg(taxa_proc_por_1k_hab)"),
        "obitos":               ("marts.nacional_mortalidade","sum(obitos)"),
        "taxa_mortalidade_100k":("marts.nacional_mortalidade","avg(taxa_mortalidade_100k)"),
        "leitos_sus":           ("marts.nacional_capacidade", "sum(leitos_sus)"),
        "taxa_leitos_sus_1k":   ("marts.nacional_capacidade", "avg(taxa_leitos_sus_1k)"),
        "medicos":              ("marts.nacional_capacidade", "sum(medicos)"),
        "taxa_medicos_1k":      ("marts.nacional_capacidade", "avg(taxa_medicos_1k)"),
        "notificacoes":         ("marts.nacional_doencas",    "sum(notificacoes)"),
        "taxa_incidencia_100k": ("marts.nacional_doencas",    "avg(taxa_incidencia_100k)"),
    }

    tabela, agg_expr = metrica_map[metrica.value]
    order_dir = "DESC" if ordem == "desc" else "ASC"

    params: list[Any] = [ano]
    regiao_filter = ""
    if regiao:
        regiao_filter = "AND regiao = $2"
        params.append(regiao.value)

    sql = f"""
        SELECT
            ROW_NUMBER() OVER (ORDER BY {agg_expr} {order_dir} NULLS LAST) AS posicao,
            uf_sigla,
            nome_uf,
            regiao,
            {agg_expr} AS valor,
            $1::int AS ano
        FROM {tabela}
        WHERE ano = $1
          {regiao_filter}
        GROUP BY uf_sigla, nome_uf, regiao
        ORDER BY {agg_expr} {order_dir} NULLS LAST
    """

    try:
        rows = await db.fetch(sql, *params)
    except Exception as exc:
        logger.error("Erro ao buscar ranking nacional: %s", exc)
        raise HTTPException(status_code=500, detail="Erro interno ao calcular ranking")

    dados = [
        RankingItem(
            posicao=r["posicao"],
            uf_sigla=r["uf_sigla"],
            nome_uf=r["nome_uf"],
            regiao=r["regiao"],
            metrica=metrica.value,
            valor=float(r["valor"] or 0),
            ano=r["ano"],
        )
        for r in rows
    ]

    await _set_cached(redis, cache_key, [d.dict() for d in dados], CACHE_TTL["ranking"])
    return dados

# ---------------------------------------------------------------------------
# Endpoint: Resumo executivo nacional
# ---------------------------------------------------------------------------

@router.get(
    "/resumo",
    summary="Resumo executivo nacional – indicadores consolidados",
    description="""
Retorna um resumo rápido com os principais indicadores nacionais agregados por ano.
Ideal para dashboards e telas de overview sem precisar filtrar tabelas grandes.
    """,
)
async def get_resumo_nacional(
    ano:   int               = Query(..., ge=2019, le=2024),
    db:    asyncpg.Pool      = Depends(get_db),
    redis: Optional[aioredis.Redis] = Depends(get_redis),
) -> dict[str, Any]:

    cache_key = _cache_key("resumo", {"ano": ano})
    cached = await _get_cached(redis, cache_key)
    if cached is not None:
        return cached

    sql_producao = """
        SELECT
            sum(procedimentos)         AS total_procedimentos,
            sum(valor_brl)             AS total_valor_brl,
            count(distinct uf_sigla)   AS estados_com_dados
        FROM marts.nacional_producao
        WHERE ano = $1
    """
    sql_mortalidade = """
        SELECT
            sum(obitos)                AS total_obitos,
            avg(taxa_mortalidade_100k) AS media_taxa_mortalidade_100k
        FROM marts.nacional_mortalidade
        WHERE ano = $1
    """
    sql_capacidade = """
        SELECT
            sum(leitos_sus)            AS total_leitos_sus,
            sum(medicos)               AS total_medicos,
            sum(estabelecimentos)      AS total_estabelecimentos
        FROM marts.nacional_capacidade
        WHERE ano = $1
    """
    sql_doencas = """
        SELECT
            sum(notificacoes)                       AS total_notificacoes,
            sum(casos_confirmados)                  AS total_casos_confirmados,
            count(*) filter (where alerta_epidemiologico) AS alertas_ativos
        FROM marts.nacional_doencas
        WHERE ano = $1
    """

    try:
        r_p, r_m, r_c, r_d = await asyncio_gather(
            db.fetchrow(sql_producao,   ano),
            db.fetchrow(sql_mortalidade, ano),
            db.fetchrow(sql_capacidade, ano),
            db.fetchrow(sql_doencas,    ano),
        )
    except Exception as exc:
        logger.error("Erro ao buscar resumo nacional: %s", exc)
        raise HTTPException(status_code=500, detail="Erro interno ao buscar resumo")

    resumo = {
        "ano": ano,
        "producao": {
            "total_procedimentos":  int(r_p["total_procedimentos"] or 0),
            "total_valor_brl":      float(r_p["total_valor_brl"] or 0),
            "estados_com_dados":    int(r_p["estados_com_dados"] or 0),
        },
        "mortalidade": {
            "total_obitos":                 int(r_m["total_obitos"] or 0),
            "media_taxa_mortalidade_100k":  round(float(r_m["media_taxa_mortalidade_100k"] or 0), 2),
        },
        "capacidade": {
            "total_leitos_sus":       int(r_c["total_leitos_sus"] or 0),
            "total_medicos":          int(r_c["total_medicos"] or 0),
            "total_estabelecimentos": int(r_c["total_estabelecimentos"] or 0),
        },
        "doencas": {
            "total_notificacoes":     int(r_d["total_notificacoes"] or 0),
            "total_casos_confirmados":int(r_d["total_casos_confirmados"] or 0),
            "alertas_ativos":         int(r_d["alertas_ativos"] or 0),
        },
    }

    await _set_cached(redis, cache_key, resumo, CACHE_TTL["producao"])
    return resumo


# Alias necessário para o endpoint /resumo usar asyncio.gather sem importar asyncio no topo
async def asyncio_gather(*coros):
    import asyncio
    return await asyncio.gather(*coros)
