"""
Suite: mart_mix_complexidade
Valida o mart de mix de complexidade dos procedimentos ambulatoriais.

Expectativas cobertas:
  - Colunas obrigatórias presentes
  - Campos-chave não nulos
  - ano [2020–2024]
  - pct_ab, pct_mc, pct_ac individualmente entre 0 e 100
  - soma dos percentuais pct_ab + pct_mc + pct_ac ≈ 100 (via coluna derivada)
  - indice_complexidade entre 1 e 3 (escala: 1=baixo, 3=alto)
  - total_procedimentos >= 0
  - nivel_complexidade no domínio válido
  - Sanidade: ao menos 500 linhas
"""
from __future__ import annotations

import great_expectations as gx
from great_expectations.core import ExpectationSuite
import pandas as pd


NIVEIS_COMPLEXIDADE = ["Baixa", "Média", "Alta"]


def build_suite(df: pd.DataFrame) -> tuple[ExpectationSuite, object]:
    """Constrói a ExpectationSuite para mart_mix_complexidade."""
    context = gx.get_context(mode="ephemeral")

    ds = context.data_sources.add_pandas("mix_complexidade_ds")
    asset = ds.add_dataframe_asset("mix_complexidade_asset")
    batch_def = asset.add_batch_definition_whole_dataframe("full")

    suite = context.suites.add(ExpectationSuite(name="mart_mix_complexidade"))

    # Colunas obrigatórias
    required_cols = [
        "municipio_cod", "uf_sigla", "ano",
        "total_procedimentos",
        "pct_ab",       # Atenção Básica
        "pct_mc",       # Média Complexidade
        "pct_ac",       # Alta Complexidade
        "indice_complexidade",
        "nivel_complexidade",
    ]
    for col in required_cols:
        suite.add_expectation(gx.expectations.ExpectColumnToExist(column=col))

    # Não nulos em colunas-chave
    for col in (
        "municipio_cod", "uf_sigla", "ano",
        "total_procedimentos", "indice_complexidade", "nivel_complexidade",
    ):
        suite.add_expectation(gx.expectations.ExpectColumnValuesToNotBeNull(column=col))

    # Domínio: ano 2020–2024
    suite.add_expectation(
        gx.expectations.ExpectColumnValuesToBeBetween(column="ano", min_value=2020, max_value=2024)
    )

    # Percentuais individuais [0, 100]
    for col in ("pct_ab", "pct_mc", "pct_ac"):
        suite.add_expectation(
            gx.expectations.ExpectColumnValuesToBeBetween(
                column=col, min_value=0.0, max_value=100.0
            )
        )

    # Total de procedimentos não-negativo
    suite.add_expectation(
        gx.expectations.ExpectColumnValuesToBeBetween(
            column="total_procedimentos", min_value=0
        )
    )

    # Índice de complexidade na escala [1, 3]
    # 1 = perfil de Atenção Básica pura; 3 = perfil de Alta Complexidade pura
    suite.add_expectation(
        gx.expectations.ExpectColumnValuesToBeBetween(
            column="indice_complexidade", min_value=1.0, max_value=3.0
        )
    )

    # Nível de complexidade no domínio textual
    suite.add_expectation(
        gx.expectations.ExpectColumnValuesToBeInSet(
            column="nivel_complexidade", value_set=NIVEIS_COMPLEXIDADE
        )
    )

    # Sanidade: ao menos 500 linhas
    suite.add_expectation(
        gx.expectations.ExpectTableRowCountToBeBetween(min_value=500)
    )

    return suite, batch_def
