"""
Suite: mart_mortalidade
Valida o mart de mortalidade derivado do SIM/DO (Declarações de Óbito).

O mart usa o padrão UNION ALL de 4 blocos:
  1. Detalhe: sexo × faixa_etaria
  2. Subtotal sexo: faixa_etaria='TOTAL'
  3. Subtotal faixa_etaria: sexo='TOTAL'
  4. Grand total: sexo='TOTAL' e faixa_etaria='TOTAL'

Expectativas cobertas:
  Estrutura
  - Todas as colunas obrigatórias presentes

  Nulidade (campos-chave)
  - municipio_cod, uf_sigla, mes_competencia, ano_obito, mes_obito,
    sexo, faixa_etaria, total_obitos, dbt_updated_at nunca nulos

  Domínios temporais
  - ano_obito  ∈ [2020, 2024]
  - mes_obito  ∈ [1, 12]
  - mes_competencia ~ r'^\d{6}$'

  Domínios geográficos
  - uf_sigla ∈ conjunto de 27 UFs válidas
  - municipio_cod ~ r'^\d{6,7}$'

  Domínios de categoria
  - sexo ∈ {M, F, I, TOTAL}

  Valores não-negativos
  - total_obitos >= 0
  - taxa_mortalidade_bruta >= 0 (quando não nulo)

  Cardinalidade
  - Ao menos 10 000 linhas (dados nacionais 2020-2024 geram volume alto)
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

SEXOS_VALIDOS = ["M", "F", "I", "TOTAL"]


def build_suite(df: pd.DataFrame) -> tuple[ExpectationSuite, object]:
    """
    Constrói a ExpectationSuite para mart_mortalidade.

    Parameters
    ----------
    df : pd.DataFrame
        DataFrame carregado do mart_mortalidade.

    Returns
    -------
    (suite, batch_definition)  — ambos registados no contexto efêmero GX.
    """
    context = gx.get_context(mode="ephemeral")

    ds = context.data_sources.add_pandas("mortalidade_ds")
    asset = ds.add_dataframe_asset("mortalidade_asset")
    batch_def = asset.add_batch_definition_whole_dataframe("full")

    suite = context.suites.add(ExpectationSuite(name="mart_mortalidade"))

    # -----------------------------------------------------------------------
    # 1. Colunas obrigatórias presentes
    # -----------------------------------------------------------------------
    required_columns = [
        "municipio_cod",
        "municipio_nome",
        "uf_sigla",
        "mes_competencia",
        "ano_obito",
        "mes_obito",
        "causabas_cap",
        "sexo",
        "faixa_etaria",
        "tipobito",
        "lococor_grupo",
        "total_obitos",
        "obitos_hospital",
        "obitos_domicilio",
        "taxa_mortalidade_bruta",
        "pct_obitos_hospital",
        "dbt_updated_at",
    ]
    for col in required_columns:
        suite.add_expectation(gx.expectations.ExpectColumnToExist(column=col))

    # -----------------------------------------------------------------------
    # 2. Campos-chave: não nulos
    # -----------------------------------------------------------------------
    not_null_cols = [
        "municipio_cod",
        "uf_sigla",
        "mes_competencia",
        "ano_obito",
        "mes_obito",
        "sexo",
        "faixa_etaria",
        "total_obitos",
        "dbt_updated_at",
    ]
    for col in not_null_cols:
        suite.add_expectation(
            gx.expectations.ExpectColumnValuesToNotBeNull(column=col)
        )

    # -----------------------------------------------------------------------
    # 3. Domínios temporais
    # -----------------------------------------------------------------------
    suite.add_expectation(
        gx.expectations.ExpectColumnValuesToBeBetween(
            column="ano_obito", min_value=2020, max_value=2024
        )
    )
    suite.add_expectation(
        gx.expectations.ExpectColumnValuesToBeBetween(
            column="mes_obito", min_value=1, max_value=12
        )
    )
    # mes_competencia: AAAAMM (6 dígitos)
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
    # 5. Domínios de categoria
    # -----------------------------------------------------------------------
    suite.add_expectation(
        gx.expectations.ExpectColumnValuesToBeInSet(
            column="sexo", value_set=SEXOS_VALIDOS
        )
    )

    # -----------------------------------------------------------------------
    # 6. Valores não-negativos
    # -----------------------------------------------------------------------
    suite.add_expectation(
        gx.expectations.ExpectColumnValuesToBeBetween(
            column="total_obitos", min_value=0
        )
    )
    suite.add_expectation(
        gx.expectations.ExpectColumnValuesToBeBetween(
            column="obitos_hospital", min_value=0
        )
    )
    suite.add_expectation(
        gx.expectations.ExpectColumnValuesToBeBetween(
            column="obitos_domicilio", min_value=0
        )
    )
    # taxa_mortalidade_bruta pode ser NULL para municípios sem pop IBGE
    suite.add_expectation(
        gx.expectations.ExpectColumnValuesToBeBetween(
            column="taxa_mortalidade_bruta", min_value=0.0
        )
    )
    # pct_obitos_hospital: 0–100 quando não nulo
    suite.add_expectation(
        gx.expectations.ExpectColumnValuesToBeBetween(
            column="pct_obitos_hospital", min_value=0.0, max_value=100.0
        )
    )

    # -----------------------------------------------------------------------
    # 7. Cardinalidade mínima
    # -----------------------------------------------------------------------
    # Dados nacionais 2020-2024 (5 570 municípios × 60 meses × subtotais)
    # geram centenas de milhares de linhas; 10 000 é um piso conservador.
    suite.add_expectation(
        gx.expectations.ExpectTableRowCountToBeBetween(min_value=10_000)
    )

    return suite, batch_def
