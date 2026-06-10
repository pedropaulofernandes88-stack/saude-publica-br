"""
Suite: mart_epi_cid10
Valida o mart de perfil epidemiológico por capítulo CID-10.

Expectativas cobertas:
  - Colunas obrigatórias presentes
  - Campos-chave não nulos
  - ano [2020–2024]
  - pct_atend_uf entre 0 e 100
  - rank_capitulo_uf >= 1 (ranking começa em 1)
  - total_procedimentos >= 0
  - variacao_anual_pct pode ser NULL (primeiro ano sem comparação)
  - capitulo_cid10 não vazio
  - Sanidade: ao menos 100 linhas
"""
from __future__ import annotations

import great_expectations as gx
from great_expectations.core import ExpectationSuite
import pandas as pd


def build_suite(df: pd.DataFrame) -> tuple[ExpectationSuite, object]:
    """Constrói a ExpectationSuite para mart_epi_cid10."""
    context = gx.get_context(mode="ephemeral")

    ds = context.data_sources.add_pandas("epi_cid10_ds")
    asset = ds.add_dataframe_asset("epi_cid10_asset")
    batch_def = asset.add_batch_definition_whole_dataframe("full")

    suite = context.suites.add(ExpectationSuite(name="mart_epi_cid10"))

    # Colunas obrigatórias
    required_cols = [
        "uf_sigla", "ano", "capitulo_cid10", "descricao_capitulo",
        "total_procedimentos", "pct_atend_uf",
        "rank_capitulo_uf", "variacao_anual_pct",
    ]
    for col in required_cols:
        suite.add_expectation(gx.expectations.ExpectColumnToExist(column=col))

    # Não nulos (variacao_anual_pct é excluída — NULL válido no 1º ano)
    for col in (
        "uf_sigla", "ano", "capitulo_cid10", "descricao_capitulo",
        "total_procedimentos", "pct_atend_uf", "rank_capitulo_uf",
    ):
        suite.add_expectation(gx.expectations.ExpectColumnValuesToNotBeNull(column=col))

    # Domínio: ano 2020–2024
    suite.add_expectation(
        gx.expectations.ExpectColumnValuesToBeBetween(column="ano", min_value=2020, max_value=2024)
    )

    # % atendimento UF: [0, 100]
    suite.add_expectation(
        gx.expectations.ExpectColumnValuesToBeBetween(
            column="pct_atend_uf", min_value=0.0, max_value=100.0
        )
    )

    # Ranking: >= 1
    suite.add_expectation(
        gx.expectations.ExpectColumnValuesToBeBetween(column="rank_capitulo_uf", min_value=1)
    )

    # Procedimentos não-negativos
    suite.add_expectation(
        gx.expectations.ExpectColumnValuesToBeBetween(column="total_procedimentos", min_value=0)
    )

    # Capítulo não vazio
    suite.add_expectation(
        gx.expectations.ExpectColumnValueLengthsToBeBetween(
            column="capitulo_cid10", min_value=1, max_value=8
        )
    )

    # Capítulo segue padrão romano (I, II, III, ... XXI)
    suite.add_expectation(
        gx.expectations.ExpectColumnValuesToMatchRegex(
            column="capitulo_cid10",
            regex=r"^[IVX]{1,6}$",
        )
    )

    # Sanidade: ao menos 100 linhas
    suite.add_expectation(
        gx.expectations.ExpectTableRowCountToBeBetween(min_value=100)
    )

    return suite, batch_def
