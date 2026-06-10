"""
Pydantic v2 response models para a API saude-publica-br.

Cada modelo corresponde a um dbt mart ou view agregada no Supabase.
Todos os campos opcionais refletem possíveis NULLs no banco (dados SUS
nem sempre são completos para todos os municípios/períodos).
"""
from __future__ import annotations

from datetime import datetime
from typing import Annotated, Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

# ---------------------------------------------------------------------------
# Base
# ---------------------------------------------------------------------------


class APIBase(BaseModel):
    """Configuração compartilhada: orm_mode + alias_generator snake_case."""

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
        str_strip_whitespace=True,
    )


class PaginacaoMeta(APIBase):
    """Metadados de paginação incluídos em respostas de lista."""

    total: int = Field(..., description="Total de registros na consulta")
    pagina: int = Field(..., ge=1, description="Página atual (1-indexed)")
    por_pagina: int = Field(..., ge=1, le=1000)
    paginas: int = Field(..., ge=1, description="Total de páginas")


class ErroResponse(APIBase):
    """Resposta de erro padronizada (RFC 7807-like)."""

    status: int
    erro: str
    detalhe: str | None = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


# ---------------------------------------------------------------------------
# Filtros comuns (query params)
# ---------------------------------------------------------------------------


class FiltroBase(APIBase):
    """Filtros comuns a múltiplos endpoints."""

    uf_sigla: str | None = Field(None, min_length=2, max_length=2, description="Sigla da UF (ex: SP)")
    municipio_cod: str | None = Field(None, min_length=6, max_length=7, description="Código IBGE município")
    ano_inicio: int | None = Field(None, ge=2000, le=2030)
    ano_fim: int | None = Field(None, ge=2000, le=2030)
    mes_competencia: str | None = Field(None, pattern=r"^\d{6}$", description="AAAAMM (ex: 202401)")

    @field_validator("uf_sigla")
    @classmethod
    def uf_maiuscula(cls, v: str | None) -> str | None:
        return v.upper() if v else v


# ---------------------------------------------------------------------------
# mart_producao_amb
# ---------------------------------------------------------------------------


class ProducaoAmbItem(APIBase):
    """Um registro de produção ambulatorial por município/competência."""

    municipio_cod: str
    municipio_nome: str | None = None
    uf_sigla: str
    mes_competencia: str
    ano: int
    mes: int
    total_procedimentos: int
    total_aprovados: int
    populacao: int | None = None
    taxa_proc_10k: float | None = Field(None, description="Procedimentos por 10 mil habitantes")
    pct_aprovacao: float | None = Field(None, description="% procedimentos aprovados")


class ProducaoAmbResponse(APIBase):
    data: list[ProducaoAmbItem]
    paginacao: PaginacaoMeta


class ProducaoSerieItem(APIBase):
    """Série temporal de produção para um município."""

    mes_competencia: str
    ano: int
    mes: int
    total_procedimentos: int
    taxa_proc_10k: float | None = None
    variacao_pct: float | None = Field(None, description="Variação % em relação ao mês anterior")


class ProducaoSerieResponse(APIBase):
    municipio_cod: str
    municipio_nome: str | None = None
    uf_sigla: str
    serie: list[ProducaoSerieItem]


# ---------------------------------------------------------------------------
# mart_acesso_cobertura
# ---------------------------------------------------------------------------


class AcessoCoberturaItem(APIBase):
    """Indicadores de acesso e cobertura por município."""

    municipio_cod: str
    municipio_nome: str | None = None
    uf_sigla: str
    ano: int
    populacao: int | None = None
    atendimentos_ab: int | None = Field(None, description="Atendimentos Atenção Básica")
    atendimentos_mc: int | None = Field(None, description="Atendimentos Média Complexidade")
    atendimentos_ac: int | None = Field(None, description="Atendimentos Alta Complexidade")
    taxa_cobertura_ab: float | None = None
    pct_cobertura: float | None = Field(None, ge=0, le=100)
    quartil_acesso: str | None = Field(None, description="Q1 (melhor) a Q4 (pior)")
    indice_acesso: float | None = None


class AcessoCoberturaResponse(APIBase):
    data: list[AcessoCoberturaItem]
    paginacao: PaginacaoMeta


class IndicadoresMunicipioResponse(APIBase):
    """Visão consolidada de indicadores para um único município."""

    municipio_cod: str
    municipio_nome: str | None = None
    uf_sigla: str
    ano: int | None = None
    # Produção
    total_procedimentos: int | None = None
    taxa_proc_10k: float | None = None
    # Acesso
    pct_cobertura: float | None = None
    quartil_acesso: str | None = None
    # Mix de complexidade
    pct_ab: float | None = None
    pct_mc: float | None = None
    pct_ac: float | None = None
    indice_complexidade: float | None = None
    # Ranking
    ranking_estadual: int | None = None
    percentil_estadual: float | None = None
    ranking_nacional: int | None = None
    # Sazonalidade
    mes_pico: int | None = None
    amplitude_sazonal: float | None = None


# ---------------------------------------------------------------------------
# mart_epi_cid10
# ---------------------------------------------------------------------------


class EpiCid10Item(APIBase):
    """Distribuição de procedimentos por capítulo CID-10."""

    uf_sigla: str
    ano: int
    capitulo_cid10: str
    descricao_capitulo: str | None = None
    total_procedimentos: int
    pct_atend_uf: float | None = Field(None, ge=0, le=100)
    rank_capitulo_uf: int | None = Field(None, ge=1)
    variacao_anual_pct: float | None = None


class EpiCid10Response(APIBase):
    data: list[EpiCid10Item]
    paginacao: PaginacaoMeta


# ---------------------------------------------------------------------------
# mart_mix_complexidade
# ---------------------------------------------------------------------------


class MixComplexidadeItem(APIBase):
    """Mix de complexidade de procedimentos por município."""

    municipio_cod: str
    municipio_nome: str | None = None
    uf_sigla: str
    ano: int
    total_procedimentos: int | None = None
    qtd_ab: int | None = None
    qtd_mc: int | None = None
    qtd_ac: int | None = None
    pct_ab: float | None = Field(None, ge=0, le=100, description="% Atenção Básica")
    pct_mc: float | None = Field(None, ge=0, le=100, description="% Média Complexidade")
    pct_ac: float | None = Field(None, ge=0, le=100, description="% Alta Complexidade")
    indice_complexidade: float | None = Field(None, ge=1, le=3, description="Índice ponderado 1-3")


class MixComplexidadeResponse(APIBase):
    data: list[MixComplexidadeItem]
    paginacao: PaginacaoMeta


# ---------------------------------------------------------------------------
# mart_sazonalidade
# ---------------------------------------------------------------------------


class SazonalidadeItem(APIBase):
    """Padrões sazonais de procedimentos."""

    municipio_cod: str
    municipio_nome: str | None = None
    uf_sigla: str
    mes: int = Field(..., ge=1, le=12)
    media_historica: float
    desvio_padrao: float | None = None
    limite_inferior: float | None = Field(None, ge=0)
    limite_superior: float | None = None
    mes_pico: int | None = Field(None, ge=1, le=12)
    amplitude_sazonal: float | None = None
    anos_historico: int | None = None


class SazonalidadeResponse(APIBase):
    data: list[SazonalidadeItem]
    paginacao: PaginacaoMeta


# ---------------------------------------------------------------------------
# mart_ranking_municipios
# ---------------------------------------------------------------------------


class RankingMunicipioItem(APIBase):
    """Posição de município no ranking de acesso ambulatorial."""

    municipio_cod: str
    municipio_nome: str | None = None
    uf_sigla: str
    ano: int
    score_acesso: float | None = None
    ranking_estadual: int = Field(..., ge=1)
    ranking_nacional: int | None = Field(None, ge=1)
    percentil_estadual: float | None = Field(None, ge=0, le=100)
    percentil_nacional: float | None = Field(None, ge=0, le=100)
    categoria: str | None = Field(None, description="Excelente/Bom/Regular/Crítico")


class RankingResponse(APIBase):
    uf_sigla: str
    ano: int
    data: list[RankingMunicipioItem]
    paginacao: PaginacaoMeta


# ---------------------------------------------------------------------------
# Anomalias (Z-score histórico e/ou Prophet pré-computado)
# ---------------------------------------------------------------------------


class AnomaliaItem(APIBase):
    """Município/competência com produção fora dos limites sazonais esperados.

    Os campos `yhat*`, `metodo` e `n_pontos` são preenchidos quando os resultados
    provêm do modelo Prophet pré-computado (`mart_anomalias_prophet`).
    Quando a fonte é o Z-score puro (via CTE SQL), `media_historica` e
    `desvio_padrao` estão presentes; `yhat*` ficam como None.
    """

    municipio_cod: str
    municipio_nome: str | None = None
    uf_sigla: str
    mes_competencia: str
    ano: int
    mes: int
    total_procedimentos: int

    # Z-score fields (presentes no modo zscore e auto-fallback)
    media_historica: float | None = Field(
        None, description="Média histórica sazonal (disponível no modo zscore)"
    )
    desvio_padrao: float | None = Field(
        None, description="Desvio padrão histórico (disponível no modo zscore)"
    )

    z_score: float
    tipo_anomalia: str = Field(..., description="'alta' ou 'baixa'")
    pct_desvio: float = Field(..., description="% acima/abaixo da média histórica")

    # Prophet fields (presentes quando metodo='prophet')
    yhat: float | None = Field(None, description="Valor previsto pelo modelo Prophet")
    yhat_lower: float | None = Field(
        None, description="Limite inferior do intervalo de confiança 95%"
    )
    yhat_upper: float | None = Field(
        None, description="Limite superior do intervalo de confiança 95%"
    )
    metodo: str = Field(
        default="zscore",
        description="Método de detecção utilizado: 'prophet' | 'zscore'",
    )
    n_pontos: int | None = Field(
        None, description="Número de pontos históricos utilizados no modelo"
    )


class AnomaliaResponse(APIBase):
    data: list[AnomaliaItem]
    paginacao: PaginacaoMeta
    threshold_sigma: float = Field(default=2.0, description="Limiar Z-score utilizado")
    method_used: str = Field(
        default="auto",
        description=(
            "Método dominante empregado nesta resposta: "
            "'prophet' (pré-computado), 'zscore' (SQL puro) ou 'auto' (misto)"
        ),
    )


# ---------------------------------------------------------------------------
# mart_mortalidade
# ---------------------------------------------------------------------------


class MortalidadeItem(APIBase):
    """Um registro de mortalidade agregado por município/competência/causa/demográfico."""

    municipio_cod: str
    municipio_nome: str | None = None
    uf_sigla: str
    regiao: str | None = None
    ano_obito: int
    mes_obito: int | None = None
    mes_competencia: str
    causabas_cap: str | None = Field(None, description="Capítulo CID-10 da causa básica (letra)")
    causabas_grupo: str | None = Field(None, description="Grupo descritivo da causa básica")
    sexo: str | None = None
    faixa_etaria: str | None = None
    total_obitos: int
    obitos_fetais: int = 0
    obitos_naofetais: int = 0
    obitos_hospital: int = 0
    obitos_domicilio: int = 0
    obitos_outros_local: int = 0
    populacao: int | None = None
    taxa_mortalidade_bruta: float | None = Field(
        None, description="Óbitos por 1.000 habitantes"
    )
    pct_obitos_hospital: float | None = Field(
        None, ge=0, le=100, description="% de óbitos ocorridos em hospital"
    )


class MortalidadeResponse(APIBase):
    data: list[MortalidadeItem]
    paginacao: PaginacaoMeta


class MortalidadeSerieItem(APIBase):
    """Ponto de série temporal de mortalidade."""

    mes_competencia: str
    ano_obito: int
    mes_obito: int | None = None
    total_obitos: int
    taxa_mortalidade_bruta: float | None = None


class MortalidadeSerieResponse(APIBase):
    municipio_cod: str
    municipio_nome: str | None = None
    uf_sigla: str
    causabas_cap: str | None = None
    causabas_grupo: str | None = None
    serie: list[MortalidadeSerieItem]


# ---------------------------------------------------------------------------
# mart_internacoes
# ---------------------------------------------------------------------------


class InternacoesItem(APIBase):
    """Um registro de internações hospitalares por município/competência/diagnóstico."""

    municipio_cod: str
    municipio_nome: str | None = None
    uf_sigla: str
    regiao: str | None = None
    ano_cmpt: int
    mes_cmpt: int | None = None
    mes_competencia: str
    diag_cap: str | None = Field(None, description="Capítulo CID-10 do diagnóstico principal")
    diag_grupo: str | None = Field(None, description="Grupo descritivo do diagnóstico")
    sexo: str | None = None
    faixa_etaria: str | None = None
    car_int_grupo: str | None = Field(
        None, description="Caráter de internação: ELETIVO | URGENCIA | PARTO | OUTROS | TOTAL"
    )
    total_internacoes: int
    total_obitos_internados: int = 0
    dias_perm_total: int | None = None
    dias_perm_medio: float | None = Field(None, description="Média de dias de permanência")
    val_tot_total: float | None = Field(None, description="Valor total aprovado (R$)")
    val_tot_medio: float | None = Field(None, description="Valor médio por internação (R$)")
    populacao: int | None = None
    taxa_internacao: float | None = Field(
        None, description="Internações por 1.000 habitantes"
    )
    taxa_mortalidade_intra: float | None = Field(
        None, ge=0, le=100, description="% óbitos sobre internações"
    )


class InternacoesResponse(APIBase):
    data: list[InternacoesItem]
    paginacao: PaginacaoMeta


class InternacoesSerieItem(APIBase):
    """Ponto de série temporal de internações."""

    mes_competencia: str
    ano_cmpt: int
    mes_cmpt: int | None = None
    total_internacoes: int
    taxa_internacao: float | None = None
    taxa_mortalidade_intra: float | None = None
    dias_perm_medio: float | None = None


class InternacoesSerieResponse(APIBase):
    municipio_cod: str
    municipio_nome: str | None = None
    uf_sigla: str
    diag_cap: str | None = None
    diag_grupo: str | None = None
    serie: list[InternacoesSerieItem]


# ---------------------------------------------------------------------------
# Mapa (GeoJSON simplificado para visualização)
# ---------------------------------------------------------------------------


class MapaMunicipioFeature(APIBase):
    """Feature simplificada para choropleth map (sem geometria, apenas dados)."""

    municipio_cod: str
    municipio_nome: str | None = None
    valor: float | None = None
    categoria: str | None = None
    ranking: int | None = None
    percentil: float | None = None


class MapaResponse(APIBase):
    uf_sigla: str
    indicador: str = Field(..., description="Nome do indicador representado")
    ano: int
    data: list[MapaMunicipioFeature]
    escala_min: float | None = None
    escala_max: float | None = None


# ---------------------------------------------------------------------------
# mart_doencas_notificaveis (SINAN)
# ---------------------------------------------------------------------------


class DoencasNotificaveisItem(APIBase):
    """Um registro de doenças notificáveis agregado por agravo/período/município."""

    agravo: str = Field(..., description="Código do agravo (ex: DENG, CHIK, ZIKA, LEIV)")
    agravo_label: str | None = Field(None, description="Nome completo do agravo")
    ano_notif: int
    mes_notif: int | None = None
    uf_notif: str
    municipio_notif: str | None = None
    faixa_etaria: str | None = Field(None, description="Faixa etária ou 'Total' para linha agregada")
    cs_sexo: str | None = Field(None, description="Sexo: M / F / I / T (T = Total)")
    total_notificacoes: int
    total_obitos: int = 0
    casos_confirmados: int | None = None
    casos_alarme: int | None = Field(None, description="Dengue: casos com sinais de alarme")
    casos_graves: int | None = Field(None, description="Dengue: casos graves")
    # Sintomas
    c_febre: int | None = None
    c_mialgia: int | None = None
    c_cefaleia: int | None = None
    c_exantema: int | None = None
    c_vomito: int | None = None
    c_artralgia: int | None = None
    c_artrite: int | None = None
    # Laboratório
    lab_ns1_pos: int | None = Field(None, description="NS1 positivo (dengue)")
    lab_soro_pos: int | None = Field(None, description="Sorologia positiva")
    lab_pcr_pos: int | None = Field(None, description="PCR positivo")
    sorotipo_predominante: str | None = Field(None, description="Sorotipo DENV predominante no período")
    # Taxas
    taxa_letalidade_pct: float | None = Field(None, ge=0, le=100, description="Taxa de letalidade (%)")
    pct_confirmados: float | None = Field(None, ge=0, le=100, description="% de casos confirmados sobre notificados")


class DoencasNotificaveisResponse(APIBase):
    data: list[DoencasNotificaveisItem]
    paginacao: PaginacaoMeta


class DoencasNotificaveisSerieItem(APIBase):
    """Ponto de série temporal de notificações de um agravo."""

    ano_notif: int
    mes_notif: int | None = None
    total_notificacoes: int
    total_obitos: int = 0
    casos_confirmados: int | None = None
    taxa_letalidade_pct: float | None = None


class DoencasNotificaveisSerieResponse(APIBase):
    agravo: str
    agravo_label: str | None = None
    uf_notif: str | None = None
    municipio_notif: str | None = None
    serie: list[DoencasNotificaveisSerieItem]


# ---------------------------------------------------------------------------
# mart_capacidade_hospitalar (CNES)
# ---------------------------------------------------------------------------


class CapacidadeHospitalarItem(APIBase):
    """Capacidade instalada de estabelecimentos de saúde por município/competência."""

    ano_cmpt: int
    mes_cmpt: int | None = None
    uf: str = Field(..., description="Sigla da UF")
    municipio_cod: str | None = Field(None, description="Código IBGE do município")
    # Estabelecimentos
    total_estabelecimentos: int | None = None
    estab_vinculados_sus: int | None = Field(None, description="Estabelecimentos com vínculo ao SUS")
    pct_estab_sus: float | None = Field(None, ge=0, le=100, description="% estabelecimentos vinculados ao SUS")
    # Ambulatório
    qt_amb_sus: int | None = Field(None, description="Quantidade de atendimentos SUS/mês (capacidade instalada)")
    qt_amb_nao_sus: int | None = Field(None, description="Quantidade de atendimentos não-SUS/mês")
    qt_amb_total: int | None = None
    qt_cons_sus: int | None = Field(None, description="Quantidade de consultas SUS/mês")
    # Serviços especializados
    estab_com_uti: int | None = Field(None, description="Estabelecimentos com UTI")
    estab_com_emergencia: int | None = None
    estab_com_cirurgia: int | None = None
    estab_com_obstetricia: int | None = None
    estab_com_hemoterapia: int | None = None
    estab_com_diagnostico: int | None = None
    # Leitos totais
    leitos_total: int | None = None
    leitos_sus: int | None = None
    leitos_nao_sus: int | None = None
    leitos_contratualizados: int | None = Field(None, description="Leitos contratualizados com o SUS")
    pct_leitos_sus: float | None = Field(None, ge=0, le=100, description="% de leitos SUS sobre total")
    # Leitos por tipo
    leitos_cirurgico: int | None = None
    leitos_clinico: int | None = None
    leitos_complementar: int | None = Field(None, description="Leitos complementares (UTI, semi-intensivos)")
    leitos_obstetrico: int | None = None
    leitos_pediatrico: int | None = None
    leitos_reabilitacao: int | None = None
    leitos_outro: int | None = None
    # Leitos SUS por tipo
    leitos_sus_cirurgico: int | None = None
    leitos_sus_clinico: int | None = None
    leitos_sus_complementar: int | None = None
    leitos_sus_obstetrico: int | None = None
    leitos_sus_pediatrico: int | None = None
    leitos_sus_reabilitacao: int | None = None


class CapacidadeHospitalarResponse(APIBase):
    data: list[CapacidadeHospitalarItem]
    paginacao: PaginacaoMeta


# ---------------------------------------------------------------------------
# Health-check
# ---------------------------------------------------------------------------


class HealthResponse(APIBase):
    status: str = "ok"
    versao: str
    ambiente: str
    db_conectado: bool
    cache_conectado: bool
    timestamp: datetime = Field(default_factory=datetime.utcnow)
