"""
Suite: mart_ranking_municipios
Valida o mart de ranking de municípios por acesso/produção ambulatorial.

Expectativas cobertas:
  - Colunas obrigatórias presentes
  - Campos-chave não nulos
  - ano [2020–2024]
  - ranking_estadual e ranking_nacional >= 1
  - percentil_estadual e percentil_nacional entre 0 e 100
  - taxa_proc_10k >= 0
  - pct_aprovacao entre 0 e 100
  - categoria nos valores válidos do domínio
  - score_acesso e score_producao entre 0 e 1 (scores normalizados)
  - Sanidade: ao menos 500 linhas
"""
from __future__ import annotations

import great_expectations as gx
from great_expectations.core import ExpectationSuite
import pandas as pd


CATEGORIAS_VALIDAS = ["Excelente", "Bom", "Regular", "Crítico"]


def build_suite(df: pd.DataFrame) -> tuple[ExpectationSuite, object]:
    """Constrói a ExpectationSuite para mart_ranking_municipios."""
    context = gx.get_context(mode="ephemeral")

    ds = context.data_sources.add_pandas("ranking_municipios_ds")
    asset = ds.add_dataframe_asset("ranking_municipios_asset")
    batch_def = asset.add_batch_definition_whole_dataframe("full")

    suite = context.suites.add(ExpectationSuite(name="mart_ranking_municipios"))

    # Colunas obrigatórias
    required_cols = [
        "municipio_cod", "municipio_nome", "uf_sigla", "ano",
        "total_procedimentos", "total_aprovados",
        "taxa_proc_10k", "pct_aprovacao",
        "ranking_estadual", "ranking_nacional",
        "percentil_estadual", "percentil_nacional",
        "score_acesso", "score_producao", "score_geral",
        "categoria",
    ]
    for col in required_cols:
        suite.add_expectation(gx.expectations.ExpectColumnToExist(column=col))

    # Não nulos em colunas-chave
    for col in (
        "municipio_cod", "uf_sigla", "ano",
        "total_procedimentos", "ranking_estadual",
        "ranking_nacional", "categoria",
    ):
        suite.add_expectation(gx.expectations.ExpectColumnValuesToNotBeNull(column=col))

    # Domínio: ano
    suite.add_expectation(
        gx.expectations.ExpectColumnValuesToBeBetween(column="ano", min_value=2020, max_value=2024)
    )

    # Rankings >= 1
    for col in ("ranking_estadual", "ranking_nacional"):
        suite.add_expectation(
            gx.expectations.ExpectColumnValuesToBeBetween(column=col, min_value=1)
        )

    # Percentis [0, 100]
    for col in ("percentil_estadual", "percentil_nacional"):
        suite.add_expectation(
            gx.expectations.ExpectColumnValuesToBeBetween(
                column=col, min_value=0.0, max_value=100.0
            )
        )

    # Taxa não-negativa
    suite.add_expectation(
        gx.expectations.ExpectColumnValuesToBeBetween(column="taxa_proc_10k", min_value=0)
    )

    # % aprovação [0, 100]
    suite.add_expectation(
        gx.expectations.ExpectColumnValuesToBeBetween(
            column="pct_aprovacao", min_value=0.0, max_value=100.0
        )
    )

    # Scores normalizados [0, 1]
    for col in ("score_acesso", "score_producao", "score_geral"):
        suite.add_expectation(
            gx.expectations.ExpectColumnValuesToBeBetween(
                column=col, min_value=0.0, max_value=1.0
            )
        )

    # Categoria no domínio
    suite.add_expectation(
        gx.expectations.ExpectColumnValuesToBeInSet(
            column="categoria", value_set=CATEGORIAS_VALIDAS
        )
    )

    # Sanidade: ao menos 500 linhas (cobre pelo menos 1 UF × 1 ano)
    suite.add_expectation(
        gx.expectations.ExpectTableRowCountToBeBetween(min_value=500)
    )

    return suite, batch_def
