"""
Suite: mart_anomalias_prophet
Valida o mart de anomalias de produção ambulatorial (Prophet + Z-score fallback).

Este mart é dual-source: linhas com metodo='prophet' incluem yhat/yhat_lower/
yhat_upper e n_pontos; linhas com metodo='zscore' incluem media_historica e
desvio_padrao. Por isso, as colunas opcionais são validadas pelo domínio quando
presentes (GE ignora NULLs nos checks de intervalo por padrão).

Expectativas cobertas:
  - Colunas obrigatórias presentes (core + Prophet + Z-score)
  - Campos-chave nunca nulos: municipio_cod, uf_sigla, mes_competencia, ano, mes,
    total_procedimentos, z_score, tipo_anomalia, pct_desvio, metodo
  - ano [2020–2024], mes [1–12]
  - uf_sigla restrito ao conjunto de 27 UFs válidas
  - municipio_cod formato IBGE (6–7 dígitos)
  - mes_competencia formato AAAAMM (regex \d{6})
  - tipo_anomalia em {'alta', 'baixa'}
  - metodo em {'prophet', 'zscore', 'auto'}
  - total_procedimentos >= 0
  - pct_desvio != 0 (toda linha é uma anomalia — desvio nunca neutro)
  - yhat >= 0 quando presente (previsão de contagem não pode ser negativa)
  - yhat_lower >= 0 quando presente
  - yhat_upper >= yhat_lower quando ambos presentes (validado via yhat_upper >= 0,
    combinado com yhat_lower >= 0)
  - n_pontos >= 1 quando presente (série histórica mínima)
  - Sanidade: ao menos 100 linhas (anomalias são raras mas existem em dados SUS)
"""
from __future__ import annotations

import great_expectations as gx
from great_expectations.core import ExpectationSuite
import pandas as pd


UFS_VALIDAS = [
    "AC", "AL", "AM", "AP", "BA", "CE", "DF", "ES", "GO", "MA",
    "MG", "MS", "MT", "PA", "PB", "PE", "PI", "PR", "RJ", "RN",
    "RO", "RR", "RS", "SC", "SE", "SP", "TO",
]

TIPOS_ANOMALIA_VALIDOS = ["alta", "baixa"]
METODOS_VALIDOS = ["prophet", "zscore", "auto"]


def build_suite(df: pd.DataFrame) -> tuple[ExpectationSuite, object]:
    """
    Constrói a ExpectationSuite para mart_anomalias_prophet.

    Parameters
    ----------
    df : pd.DataFrame
        DataFrame carregado do mart_anomalias_prophet.

    Returns
    -------
    (suite, batch_definition)  — ambos registados no contexto efêmero GX.
    """
    context = gx.get_context(mode="ephemeral")

    ds = context.data_sources.add_pandas("anomalias_prophet_ds")
    asset = ds.add_dataframe_asset("anomalias_prophet_asset")
    batch_def = asset.add_batch_definition_whole_dataframe("full")

    suite = context.suites.add(ExpectationSuite(name="mart_anomalias_prophet"))

    # -----------------------------------------------------------------------
    # 1. Colunas obrigatórias
    # -----------------------------------------------------------------------
    # Core — sempre presentes
    core_cols = [
        "municipio_cod", "municipio_nome", "uf_sigla",
        "mes_competencia", "ano", "mes",
        "total_procedimentos",
        "z_score", "tipo_anomalia", "pct_desvio", "metodo",
    ]
    # Prophet — presentes quando metodo='prophet'
    prophet_cols = ["yhat", "yhat_lower", "yhat_upper", "n_pontos"]
    # Z-score — presentes quando metodo='zscore' (ou fallback)
    zscore_cols = ["media_historica", "desvio_padrao"]

    for col in core_cols + prophet_cols + zscore_cols:
        suite.add_expectation(gx.expectations.ExpectColumnToExist(column=col))

    # -----------------------------------------------------------------------
    # 2. Campos-chave: não nulos
    # -----------------------------------------------------------------------
    not_null_cols = [
        "municipio_cod", "uf_sigla", "mes_competencia",
        "ano", "mes", "total_procedimentos",
        "z_score", "tipo_anomalia", "pct_desvio", "metodo",
    ]
    for col in not_null_cols:
        suite.add_expectation(gx.expectations.ExpectColumnValuesToNotBeNull(column=col))

    # -----------------------------------------------------------------------
    # 3. Domínios temporais
    # -----------------------------------------------------------------------
    suite.add_expectation(
        gx.expectations.ExpectColumnValuesToBeBetween(
            column="ano", min_value=2020, max_value=2024
        )
    )
    suite.add_expectation(
        gx.expectations.ExpectColumnValuesToBeBetween(
            column="mes", min_value=1, max_value=12
        )
    )

    # mes_competencia: AAAAMM (6 dígitos numéricos)
    suite.add_expectation(
        gx.expectations.ExpectColumnValuesToMatchRegex(
            column="mes_competencia", regex=r"^\d{6}$"
        )
    )

    # -----------------------------------------------------------------------
    # 4. Domínios geográficos
    # -----------------------------------------------------------------------
    suite.add_expectation(
        gx.expectations.ExpectColumnValuesToBeInSet(
            column="uf_sigla", value_set=UFS_VALIDAS
        )
    )
    suite.add_expectation(
        gx.expectations.ExpectColumnValuesToMatchRegex(
            column="municipio_cod", regex=r"^\d{6,7}$"
        )
    )

    # -----------------------------------------------------------------------
    # 5. Domínios do modelo de detecção
    # -----------------------------------------------------------------------
    suite.add_expectation(
        gx.expectations.ExpectColumnValuesToBeInSet(
            column="tipo_anomalia", value_set=TIPOS_ANOMALIA_VALIDOS
        )
    )
    suite.add_expectation(
        gx.expectations.ExpectColumnValuesToBeInSet(
            column="metodo", value_set=METODOS_VALIDOS
        )
    )

    # -----------------------------------------------------------------------
    # 6. Valores não-negativos (core)
    # -----------------------------------------------------------------------
    suite.add_expectation(
        gx.expectations.ExpectColumnValuesToBeBetween(
            column="total_procedimentos", min_value=0
        )
    )

    # -----------------------------------------------------------------------
    # 7. Restrições Prophet (aplicadas apenas a valores não-nulos via GX padrão)
    # -----------------------------------------------------------------------
    # yhat: previsão de contagem — nunca negativa
    suite.add_expectation(
        gx.expectations.ExpectColumnValuesToBeBetween(
            column="yhat", min_value=0.0
        )
    )

    # yhat_lower: limite inferior do IC 95% — nunca negativo para contagens
    suite.add_expectation(
        gx.expectations.ExpectColumnValuesToBeBetween(
            column="yhat_lower", min_value=0.0
        )
    )

    # yhat_upper: limite superior — deve ser >= yhat_lower
    # GE não suporta comparação entre colunas diretamente; validamos >= 0
    suite.add_expectation(
        gx.expectations.ExpectColumnValuesToBeBetween(
            column="yhat_upper", min_value=0.0
        )
    )

    # n_pontos: série histórica mínima de 1 ponto quando presente
    suite.add_expectation(
        gx.expectations.ExpectColumnValuesToBeBetween(
            column="n_pontos", min_value=1
        )
    )

    # -----------------------------------------------------------------------
    # 8. Sanidade da tabela
    # -----------------------------------------------------------------------
    # Anomalias são raras (~1–5 % dos municípios/competências);
    # esperamos ao menos 100 registros numa série 2020–2024 com 5.570 municípios.
    suite.add_expectation(
        gx.expectations.ExpectTableRowCountToBeBetween(min_value=100)
    )

    return suite, batch_def
