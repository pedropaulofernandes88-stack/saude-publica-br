"""
Suite: mart_sazonalidade
Valida o mart de padrões de sazonalidade dos procedimentos ambulatoriais.

Expectativas cobertas:
  - Colunas obrigatórias presentes
  - Campos-chave não nulos
  - mes_num entre 1 e 12
  - media_historica, desvio_padrao, limite_inferior >= 0
  - limite_superior >= limite_inferior (via ExpectColumnPairValuesAToBeGreaterThanB)
  - indice_sazonalidade > 0 (razão observado/esperado; 1.0 = sem sazonalidade)
  - anos_historico >= 3 (mínimo para séries temporais confiáveis)
  - classificacao_sazo no domínio válido
  - Sanidade: ao menos 300 linhas (12 meses × ≥25 UFs)
"""
from __future__ import annotations

import great_expectations as gx
from great_expectations.core import ExpectationSuite
import pandas as pd


CLASSIFICACOES_SAZO = ["Baixa", "Normal", "Alta", "Muito Alta"]


def build_suite(df: pd.DataFrame) -> tuple[ExpectationSuite, object]:
    """Constrói a ExpectationSuite para mart_sazonalidade."""
    context = gx.get_context(mode="ephemeral")

    ds = context.data_sources.add_pandas("sazonalidade_ds")
    asset = ds.add_dataframe_asset("sazonalidade_asset")
    batch_def = asset.add_batch_definition_whole_dataframe("full")

    suite = context.suites.add(ExpectationSuite(name="mart_sazonalidade"))

    # Colunas obrigatórias
    required_cols = [
        "uf_sigla", "mes_num", "mes_nome",
        "media_historica", "desvio_padrao",
        "limite_inferior", "limite_superior",
        "indice_sazonalidade",
        "anos_historico",
        "classificacao_sazo",
    ]
    for col in required_cols:
        suite.add_expectation(gx.expectations.ExpectColumnToExist(column=col))

    # Não nulos em colunas-chave
    for col in (
        "uf_sigla", "mes_num", "mes_nome",
        "media_historica", "indice_sazonalidade",
        "anos_historico", "classificacao_sazo",
    ):
        suite.add_expectation(gx.expectations.ExpectColumnValuesToNotBeNull(column=col))

    # Mês: 1–12
    suite.add_expectation(
        gx.expectations.ExpectColumnValuesToBeBetween(
            column="mes_num", min_value=1, max_value=12
        )
    )

    # Valores de referência histórica não-negativos
    for col in ("media_historica", "desvio_padrao", "limite_inferior"):
        suite.add_expectation(
            gx.expectations.ExpectColumnValuesToBeBetween(column=col, min_value=0.0)
        )

    # Limite superior também não-negativo
    suite.add_expectation(
        gx.expectations.ExpectColumnValuesToBeBetween(
            column="limite_superior", min_value=0.0
        )
    )

    # Limite superior >= limite inferior
    suite.add_expectation(
        gx.expectations.ExpectColumnPairValuesAToBeGreaterThanB(
            column_A="limite_superior",
            column_B="limite_inferior",
            or_equal=True,
        )
    )

    # Índice de sazonalidade > 0 (razão observado/esperado, jamais negativo)
    suite.add_expectation(
        gx.expectations.ExpectColumnValuesToBeBetween(
            column="indice_sazonalidade", min_value=0.0
        )
    )

    # Série histórica mínima de 3 anos para robustez estatística
    suite.add_expectation(
        gx.expectations.ExpectColumnValuesToBeBetween(
            column="anos_historico", min_value=3
        )
    )

    # Classificação sazonal no domínio textual
    suite.add_expectation(
        gx.expectations.ExpectColumnValuesToBeInSet(
            column="classificacao_sazo", value_set=CLASSIFICACOES_SAZO
        )
    )

    # Sanidade: 12 meses × 27 UFs = 324 linhas mínimas; exigimos >= 300
    suite.add_expectation(
        gx.expectations.ExpectTableRowCountToBeBetween(min_value=300)
    )

    return suite, batch_def
