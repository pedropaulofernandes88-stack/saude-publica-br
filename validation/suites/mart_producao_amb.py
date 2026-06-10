"""
Suite: mart_producao_amb
Valida a tabela de produção ambulatorial mensal por município.

Expectativas cobertas:
  - Colunas obrigatórias presentes
  - Campos-chave não nulos
  - Tipos e domínios: ano [2020–2024], mes [1–12]
  - Métricas não-negativas: total_procedimentos, total_aprovados, taxa_proc_10k
  - % aprovação entre 0 e 100
  - uf_sigla restrito ao conjunto de 27 UFs válidas
  - municipio_cod com formato numérico IBGE (6-7 dígitos)
  - Sanidade: tabela com ao menos 1.000 linhas
"""
from __future__ import annotations

import great_expectations as gx
from great_expectations.core import ExpectationSuite
import pandas as pd


UFS_VALIDAS = [
    "AC","AL","AM","AP","BA","CE","DF","ES","GO","MA",
    "MG","MS","MT","PA","PB","PE","PI","PR","RJ","RN",
    "RO","RR","RS","SC","SE","SP","TO",
]


def build_suite(df: pd.DataFrame) -> tuple[ExpectationSuite, object]:
    """
    Constrói a ExpectationSuite para mart_producao_amb.

    Returns
    -------
    (suite, batch_definition)  — ambos registados no contexto efêmero.
    """
    context = gx.get_context(mode="ephemeral")

    ds = context.data_sources.add_pandas("producao_amb_ds")
    asset = ds.add_dataframe_asset("producao_amb_asset")
    batch_def = asset.add_batch_definition_whole_dataframe("full")

    suite = context.suites.add(ExpectationSuite(name="mart_producao_amb"))

    # Colunas obrigatórias
    required_cols = [
        "mes_competencia", "ano", "mes", "uf_sigla",
        "municipio_cod", "municipio_nome",
        "total_procedimentos", "total_aprovados",
        "taxa_proc_10k", "pct_aprovacao",
    ]
    for col in required_cols:
        suite.add_expectation(gx.expectations.ExpectColumnToExist(column=col))

    # Não nulos em colunas-chave
    for col in ("mes_competencia", "ano", "mes", "uf_sigla", "municipio_cod", "total_procedimentos"):
        suite.add_expectation(gx.expectations.ExpectColumnValuesToNotBeNull(column=col))

    # Domínio: ano 2020–2024
    suite.add_expectation(
        gx.expectations.ExpectColumnValuesToBeBetween(column="ano", min_value=2020, max_value=2024)
    )

    # Domínio: mês 1–12
    suite.add_expectation(
        gx.expectations.ExpectColumnValuesToBeBetween(column="mes", min_value=1, max_value=12)
    )

    # UF válida
    suite.add_expectation(
        gx.expectations.ExpectColumnValuesToBeInSet(column="uf_sigla", value_set=UFS_VALIDAS)
    )

    # Métricas não-negativas
    for col in ("total_procedimentos", "total_aprovados", "taxa_proc_10k"):
        suite.add_expectation(
            gx.expectations.ExpectColumnValuesToBeBetween(column=col, min_value=0)
        )

    # % aprovação [0, 100]
    suite.add_expectation(
        gx.expectations.ExpectColumnValuesToBeBetween(
            column="pct_aprovacao", min_value=0.0, max_value=100.0
        )
    )

    # Código IBGE: 6 ou 7 dígitos numéricos
    suite.add_expectation(
        gx.expectations.ExpectColumnValuesToMatchRegex(
            column="municipio_cod", regex=r"^\d{6,7}$"
        )
    )

    # Sanidade: ao menos 1.000 linhas
    suite.add_expectation(
        gx.expectations.ExpectTableRowCountToBeBetween(min_value=1000)
    )

    return suite, batch_def
