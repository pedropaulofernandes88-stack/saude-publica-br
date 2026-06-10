"""
Modelos Pydantic v2 para a API pública v1.

Todos os campos têm Field(description=..., example=...) para gerar
documentação Swagger/OpenAPI rica e legível.
"""
from __future__ import annotations

from typing import Any, Optional
from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Utilitários / base
# ---------------------------------------------------------------------------

class MetaPaginacao(BaseModel):
    """Informações de paginação retornadas em toda listagem."""

    total: int = Field(
        ...,
        description="Total de registros disponíveis (antes da paginação).",
        examples=[12_847],
    )
    pagina: int = Field(
        ...,
        description="Página atual (1-based).",
        examples=[1],
    )
    por_pagina: int = Field(
        ...,
        description="Registros por página (máx 1000).",
        examples=[100],
    )
    paginas: int = Field(
        ...,
        description="Total de páginas disponíveis.",
        examples=[129],
    )


class RateLimitInfo(BaseModel):
    """Headers de rate limit incluídos em toda resposta."""

    limite_hora: Optional[int] = Field(
        None,
        description="Requisições permitidas por hora (null = ilimitado).",
        examples=[100],
    )
    usadas_hora: int = Field(
        ...,
        description="Requisições realizadas na última hora.",
        examples=[7],
    )
    tier: str = Field(
        ...,
        description="Tier da API key: 'free', 'pro' ou 'enterprise'.",
        examples=["free"],
    )


# ---------------------------------------------------------------------------
# Produção Ambulatorial (SIA)
# ---------------------------------------------------------------------------

class ProducaoItem(BaseModel):
    """Um registro de produção ambulatorial agregado por mês/estado/procedimento."""

    competencia: str = Field(
        ...,
        description="Mês de referência no formato AAAA-MM.",
        examples=["2024-03"],
    )
    uf: str = Field(
        ...,
        description="Sigla do estado (UF).",
        examples=["SP"],
    )
    municipio_codigo: Optional[str] = Field(
        None,
        description="Código IBGE do município (6 dígitos), se filtrado.",
        examples=["355030"],
    )
    procedimento_codigo: str = Field(
        ...,
        description="Código do procedimento SIGTAP (10 dígitos).",
        examples=["0301010064"],
    )
    procedimento_nome: str = Field(
        ...,
        description="Descrição do procedimento.",
        examples=["CONSULTA MÉDICA EM ATENÇÃO BÁSICA"],
    )
    quantidade_aprovada: int = Field(
        ...,
        description="Quantidade de procedimentos aprovados no mês.",
        examples=[1_284_730],
    )
    valor_aprovado: float = Field(
        ...,
        description="Valor total aprovado em reais (R$).",
        examples=[987_432.50],
    )
    estabelecimentos: int = Field(
        ...,
        description="Número de estabelecimentos que realizaram o procedimento.",
        examples=[342],
    )


class ProducaoResponse(BaseModel):
    """Resposta paginada de produção ambulatorial."""

    dados: list[ProducaoItem]
    meta: MetaPaginacao
    rate_limit: RateLimitInfo
    fonte: str = Field(
        default="SIA/DataSUS",
        description="Sistema de origem dos dados.",
        examples=["SIA/DataSUS"],
    )
    ultima_atualizacao: str = Field(
        ...,
        description="Data da última carga de dados (ISO 8601).",
        examples=["2024-04-15T03:00:00Z"],
    )


# ---------------------------------------------------------------------------
# Mortalidade (SIM)
# ---------------------------------------------------------------------------

class MortalidadeItem(BaseModel):
    """Um registro de mortalidade agregado por ano/estado/causa."""

    ano: int = Field(
        ...,
        description="Ano de referência.",
        examples=[2023],
    )
    uf: str = Field(
        ...,
        description="Sigla do estado (UF) de ocorrência.",
        examples=["RJ"],
    )
    municipio_codigo: Optional[str] = Field(
        None,
        description="Código IBGE do município de ocorrência (6 dígitos).",
        examples=["330455"],
    )
    causa_cid10: str = Field(
        ...,
        description="Código CID-10 da causa básica de morte.",
        examples=["J18"],
    )
    causa_descricao: str = Field(
        ...,
        description="Descrição da causa básica (CID-10).",
        examples=["Pneumonia não especificada"],
    )
    capitulo_cid: str = Field(
        ...,
        description="Capítulo CID-10 (ex: X — Doenças do aparelho respiratório).",
        examples=["X"],
    )
    obitos: int = Field(
        ...,
        description="Número de óbitos no período.",
        examples=[4_231],
    )
    taxa_100k: Optional[float] = Field(
        None,
        description="Taxa de mortalidade por 100.000 habitantes (requer denominador populacional).",
        examples=[18.7],
    )
    idade_media: Optional[float] = Field(
        None,
        description="Idade média dos óbitos.",
        examples=[71.4],
    )
    prop_feminino: Optional[float] = Field(
        None,
        description="Proporção de óbitos femininos (0–1).",
        examples=[0.48],
    )


class MortalidadeResponse(BaseModel):
    """Resposta paginada de mortalidade."""

    dados: list[MortalidadeItem]
    meta: MetaPaginacao
    rate_limit: RateLimitInfo
    fonte: str = Field(default="SIM/DataSUS")
    ultima_atualizacao: str = Field(..., examples=["2024-03-01T03:00:00Z"])


# ---------------------------------------------------------------------------
# Capacidade Instalada (CNES)
# ---------------------------------------------------------------------------

class EstabelecimentoItem(BaseModel):
    """Um estabelecimento de saúde com indicadores de capacidade."""

    cnes: str = Field(
        ...,
        description="Código CNES do estabelecimento (7 dígitos).",
        examples=["2077396"],
    )
    nome: str = Field(
        ...,
        description="Nome fantasia do estabelecimento.",
        examples=["HOSPITAL DAS CLÍNICAS DA FMUSP"],
    )
    uf: str = Field(..., examples=["SP"])
    municipio_codigo: str = Field(..., examples=["355030"])
    municipio_nome: str = Field(..., examples=["São Paulo"])
    tipo_unidade: str = Field(
        ...,
        description="Tipo de unidade conforme tabela CNES.",
        examples=["HOSPITAL GERAL"],
    )
    gestao: str = Field(
        ...,
        description="Esfera de gestão: 'MUNICIPAL', 'ESTADUAL' ou 'FEDERAL'.",
        examples=["ESTADUAL"],
    )
    leitos_sus: int = Field(
        ...,
        description="Total de leitos SUS cadastrados.",
        examples=[2_200],
    )
    leitos_uti: int = Field(
        ...,
        description="Leitos de UTI (adulto + pediátrico + neonatal).",
        examples=[320],
    )
    equipes_saude_familia: int = Field(
        ...,
        description="Equipes de Saúde da Família cadastradas.",
        examples=[0],
    )
    profissionais: int = Field(
        ...,
        description="Total de profissionais de saúde vinculados.",
        examples=[8_740],
    )
    latitude: Optional[float] = Field(None, examples=[-23.5558])
    longitude: Optional[float] = Field(None, examples=[-46.6396])
    competencia: str = Field(
        ...,
        description="Mês de referência do cadastro CNES (AAAA-MM).",
        examples=["2024-03"],
    )


class CapacidadeResponse(BaseModel):
    """Resposta paginada de capacidade instalada."""

    dados: list[EstabelecimentoItem]
    meta: MetaPaginacao
    rate_limit: RateLimitInfo
    fonte: str = Field(default="CNES/DataSUS")
    ultima_atualizacao: str = Field(..., examples=["2024-04-01T03:00:00Z"])


class ResumoCapacidade(BaseModel):
    """Agregado de capacidade por UF ou município."""

    uf: str = Field(..., examples=["SP"])
    municipio_codigo: Optional[str] = Field(None, examples=["355030"])
    municipio_nome: Optional[str] = Field(None, examples=["São Paulo"])
    total_estabelecimentos: int = Field(..., examples=[12_847])
    total_leitos_sus: int = Field(..., examples=[78_432])
    total_leitos_uti: int = Field(..., examples=[9_120])
    leitos_uti_por_100k: float = Field(
        ...,
        description="Leitos de UTI por 100.000 habitantes (WHO recomenda ≥1).",
        examples=[19.8],
    )
    equipes_esf: int = Field(..., examples=[5_432])
    cobertura_esf_pct: float = Field(
        ...,
        description="Cobertura estimada da Estratégia Saúde da Família (%).",
        examples=[72.4],
    )
    competencia: str = Field(..., examples=["2024-03"])


class ResumoCapacidadeResponse(BaseModel):
    """Resposta de agregado de capacidade."""

    dados: list[ResumoCapacidade]
    rate_limit: RateLimitInfo
    fonte: str = Field(default="CNES/DataSUS")
    ultima_atualizacao: str = Field(..., examples=["2024-04-01T03:00:00Z"])


# ---------------------------------------------------------------------------
# Doenças e Agravos (SINAN)
# ---------------------------------------------------------------------------

class DoencaItem(BaseModel):
    """Um registro de agravo/doença notificada agregado por semana epidemiológica."""

    ano: int = Field(..., examples=[2024])
    semana_epidemiologica: int = Field(
        ...,
        description="Semana epidemiológica (1–53).",
        examples=[12],
    )
    uf: str = Field(..., examples=["AM"])
    municipio_codigo: Optional[str] = Field(None, examples=["130260"])
    agravo_cid10: str = Field(
        ...,
        description="Código CID-10 do agravo notificado.",
        examples=["A90"],
    )
    agravo_nome: str = Field(
        ...,
        description="Nome do agravo/doença.",
        examples=["Dengue"],
    )
    casos: int = Field(
        ...,
        description="Número de casos notificados no período.",
        examples=[3_847],
    )
    casos_graves: Optional[int] = Field(
        None,
        description="Casos graves / hospitalizados (quando disponível).",
        examples=[142],
    )
    obitos: Optional[int] = Field(
        None,
        description="Óbitos confirmados pelo agravo (quando disponível).",
        examples=[8],
    )
    incidencia_100k: Optional[float] = Field(
        None,
        description="Incidência por 100.000 habitantes.",
        examples=[183.4],
    )
    alertas: Optional[list[str]] = Field(
        None,
        description="Alertas epidemiológicos: 'ANOMALIA_PROPHET', 'LIMIAR_EPIDEMICO'.",
        examples=[["ANOMALIA_PROPHET"]],
    )


class DoencaResponse(BaseModel):
    """Resposta paginada de doenças e agravos notificados."""

    dados: list[DoencaItem]
    meta: MetaPaginacao
    rate_limit: RateLimitInfo
    fonte: str = Field(default="SINAN/DataSUS")
    ultima_atualizacao: str = Field(..., examples=["2024-04-10T03:00:00Z"])


class SurtoItem(BaseModel):
    """Um surto/cluster detectado pelo modelo Prophet."""

    agravo_nome: str = Field(..., examples=["Dengue"])
    uf: str = Field(..., examples=["AM"])
    semana_inicio: int = Field(..., examples=[10])
    semana_fim: Optional[int] = Field(None, examples=[14])
    casos_observados: int = Field(..., examples=[12_847])
    casos_esperados: float = Field(..., examples=[2_310.5])
    razao_observado_esperado: float = Field(
        ...,
        description="Razão casos observados / esperados (>1.5 = alerta).",
        examples=[5.56],
    )
    nivel_alerta: str = Field(
        ...,
        description="'VERDE', 'AMARELO', 'LARANJA' ou 'VERMELHO'.",
        examples=["VERMELHO"],
    )


class SurtosResponse(BaseModel):
    """Resposta de surtos e alertas epidemiológicos detectados."""

    dados: list[SurtoItem]
    rate_limit: RateLimitInfo
    fonte: str = Field(default="SINAN/DataSUS + Prophet ML")
    gerado_em: str = Field(..., examples=["2024-04-10T06:00:00Z"])


# ---------------------------------------------------------------------------
# Informações da API key (para /v1/me)
# ---------------------------------------------------------------------------

class ApiKeyMeResponse(BaseModel):
    """Informações da API key autenticada."""

    key_prefix: str = Field(
        ...,
        description="Prefixo visível da API key (ex: spbr_a1b2c3d4).",
        examples=["spbr_a1b2c3d4"],
    )
    nome: str = Field(..., examples=["Minha chave de pesquisa"])
    tier: str = Field(..., examples=["free"])
    scopes: list[str] = Field(..., examples=[["read"]])
    rate_limit_hora: Optional[int] = Field(None, examples=[100])
    rate_limit_dia: Optional[int] = Field(None, examples=[1000])
    total_requests: int = Field(..., examples=[4_271])
    criado_em: str = Field(..., examples=["2024-01-15T14:30:00Z"])
    ultimo_uso: Optional[str] = Field(None, examples=["2024-04-10T11:22:33Z"])
    rate_limit: RateLimitInfo
