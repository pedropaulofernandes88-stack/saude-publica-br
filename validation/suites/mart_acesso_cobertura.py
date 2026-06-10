"""
Suite: mart_acesso_cobertura
Valida o mart de índices de acesso e cobertura ambulatorial.

Expectativas cobertas:
  - Colunas obrigatórias presentes
  - Campos-chave não nulos (incluindo flag_baixa_cobertura)
  - ano [2020–2024]
  - quartil_acesso nos valores ['Q1', 'Q2-Q3', 'Q4']
  - indice_acesso entre 0 e 1 (normalizado)
  - taxa_cobertura >= 0
  - populacao > 0
  - flag_baixa_cobertura é booleano (0/1 ou True/False)
  - Sanidade: ao menos 500 linhas
"""
from __future__ import annotations

import great_expectations as gx
from great_expectations.core import ExpectationSuite
import pandas as pd


QUARTIS_VALIDOS = ["Q1", "Q2-Q3", "Q4"]


def build_suite(df: pd.DataFrame) -> tuple[ExpectationSuite, object]:
    """Constrói a ExpectationSuite para mart_acesso_cobertura."""
    context = gx.get_context(mode="ephemeral")

    ds = context.data_sources.add_pandas("acesso_cobertura_ds")
    asset = ds.add_dataframe_asset("acesso_cobertura_asset")
    batch_def = asset.add_batch_definition_whole_dataframe("full")

    suite = context.suites.add(ExpectationSuite(name="mart_acesso_cobertura"))

    # Colunas obrigatórias
    required_cols = [
        "municipio_cod", "uf_sigla", "ano",
        "populacao", "taxa_cobertura",
        "indice_acesso", "quartil_acesso", "flag_baixa_cobertura",
    ]
    for col in required_cols:
        suite.add_expectation(gx.expectations.ExpectColumnToExist(column=col))

    # Não nulos
    for col in (
        "municipio_cod", "uf_sigla", "ano",
        "quartil_acesso", "flag_baixa_cobertura",
    ):
        suite.add_expectation(gx.expectations.ExpectColumnValuesToNotBeNull(column=col))

    # Domínio: ano
    suite.add_expectation(
        gx.expectations.ExpectColumnValuesToBeBetween(column="ano", min_value=2020, max_value=2024)
    )

    # Quartil de acesso no domínio
    suite.add_expectation(
        gx.expectations.ExpectColumnValuesToBeInSet(
            column="quartil_acesso", value_set=QUARTIS_VALIDOS
        )
    )

    # Índice de acesso normalizado [0, 1]
    suite.add_expectation(
        gx.expectations.ExpectColumnValuesToBeBetween(
            column="indice_acesso", min_value=0.0, max_value=1.0
        )
    )

    # Taxa de cobertura >= 0
    suite.add_expectation(
        gx.expectations.ExpectColumnValuesToBeBetween(column="taxa_cobertura", min_value=0.0)
    )

    # População > 0
    suite.add_expectation(
        gx.expectations.ExpectColumnValuesToBeBetween(column="populacao", min_value=1)
    )

    # flag_baixa_cobertura: somente 0 ou 1 (booleano inteiro) — ou True/False
    suite.add_expectation(
        gx.expectations.ExpectColumnValuesToBeInSet(
            column="flag_baixa_cobertura", value_set=[0, 1, True, False]
        )
    )

    # Sanidade
    suite.add_expectation(
        gx.expectations.ExpectTableRowCountToBeBetween(min_value=500)
    )

    return suite, batch_def
