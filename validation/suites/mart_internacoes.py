"""
Suite: mart_internacoes
Valida o mart de internações hospitalares derivado do SIH/AIH
(Autorização de Internação Hospitalar).

O mart usa o padrão UNION ALL de 4 blocos:
  1. Detalhe: sexo × faixa_etaria × car_int_grupo
  2. Subtotal sexo: faixa_etaria='TOTAL', car_int_grupo mantido
  3. Subtotal faixa_etaria: sexo='TOTAL', car_int_grupo mantido
  4. Subtotal car_int: sexo='TOTAL', faixa_etaria='TOTAL'
  5. Grand total: sexo='TOTAL', faixa_etaria='TOTAL', car_int_grupo='TOTAL'

Expectativas cobertas:
  Estrutura
  - Todas as colunas obrigatórias presentes

  Nulidade (campos-chave)
  - municipio_cod, uf_sigla, mes_competencia, ano_cmpt, mes_cmpt,
    sexo, faixa_etaria, car_int_grupo, total_internacoes, dbt_updated_at

  Domínios temporais
  - ano_cmpt  ∈ [2020, 2024]
  - mes_cmpt  ∈ [1, 12]
  - mes_competencia ~ r'^\d{6}$'

  Domínios geográficos
  - uf_sigla ∈ conjunto de 27 UFs válidas
  - municipio_cod ~ r'^\d{6,7}$'

  Domínios de categoria
  - sexo ∈ {M, F, I, TOTAL}
  - car_int_grupo ∈ {ELETIVO, URGENCIA, PARTO, OUTROS, TOTAL}

  Valores não-negativos
  - total_internacoes >= 0
  - total_obitos_internados >= 0
  - dias_perm_total >= 0
  - dias_perm_medio >= 0 (quando não nulo)
  - taxa_internacao >= 0 (quando não nulo)
  - taxa_mortalidade_intra ∈ [0, 100] (quando não nulo)

  Cardinalidade
  - Ao menos 10 000 linhas
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
CAR_INT_GRUPOS_VALIDOS = ["ELETIVO", "URGENCIA", "PARTO", "OUTROS", "TOTAL"]


def build_suite(df: pd.DataFrame) -> tuple[ExpectationSuite, object]:
    """
    Constrói a ExpectationSuite para mart_internacoes.

    Parameters
    ----------
    df : pd.DataFrame
        DataFrame carregado do mart_internacoes.

    Returns
    -------
    (suite, batch_definition)  — ambos registados no contexto efêmero GX.
    """
    context = gx.get_context(mode="ephemeral")

    ds = context.data_sources.add_pandas("internacoes_ds")
    asset = ds.add_dataframe_asset("internacoes_asset")
    batch_def = asset.add_batch_definition_whole_dataframe("full")

    suite = context.suites.add(ExpectationSuite(name="mart_internacoes"))

    # -----------------------------------------------------------------------
    # 1. Colunas obrigatórias presentes
    # -----------------------------------------------------------------------
    required_columns = [
        "municipio_cod",
        "municipio_nome",
        "uf_sigla",
        "mes_competencia",
        "ano_cmpt",
        "mes_cmpt",
        "diag_cap",
        "sexo",
        "faixa_etaria",
        "car_int_grupo",
        "total_internacoes",
        "total_obitos_internados",
        "dias_perm_total",
        "dias_perm_medio",
        "taxa_internacao",
        "taxa_mortalidade_intra",
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
        "ano_cmpt",
        "mes_cmpt",
        "sexo",
        "faixa_etaria",
        "car_int_grupo",
        "total_internacoes",
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
            column="ano_cmpt", min_value=2020, max_value=2024
        )
    )
    suite.add_expectation(
        gx.expectations.ExpectColumnValuesToBeBetween(
            column="mes_cmpt", min_value=1, max_value=12
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
    suite.add_expectation(
        gx.expectations.ExpectColumnValuesToBeInSet(
            column="car_int_grupo", value_set=CAR_INT_GRUPOS_VALIDOS
        )
    )

    # -----------------------------------------------------------------------
    # 6. Valores não-negativos
    # -----------------------------------------------------------------------
    suite.add_expectation(
        gx.expectations.ExpectColumnValuesToBeBetween(
            column="total_internacoes", min_value=0
        )
    )
    suite.add_expectation(
        gx.expectations.ExpectColumnValuesToBeBetween(
            column="total_obitos_internados", min_value=0
        )
    )
    suite.add_expectation(
        gx.expectations.ExpectColumnValuesToBeBetween(
            column="dias_perm_total", min_value=0
        )
    )
    # dias_perm_medio: pode ser NULL quando total_internacoes=0
    suite.add_expectation(
        gx.expectations.ExpectColumnValuesToBeBetween(
            column="dias_perm_medio", min_value=0.0
        )
    )
    # taxa_internacao: pode ser NULL quando pop IBGE indisponível
    suite.add_expectation(
        gx.expectations.ExpectColumnValuesToBeBetween(
            column="taxa_internacao", min_value=0.0
        )
    )
    # taxa_mortalidade_intra: percentual 0–100
    suite.add_expectation(
        gx.expectations.ExpectColumnValuesToBeBetween(
            column="taxa_mortalidade_intra", min_value=0.0, max_value=100.0
        )
    )

    # -----------------------------------------------------------------------
    # 7. Cardinalidade mínima
    # -----------------------------------------------------------------------
    # SIH mensal × 5 570 municípios × subtotais → volume alto;
    # 10 000 é um piso muito conservador para dados 2020-2024.
    suite.add_expectation(
        gx.expectations.ExpectTableRowCountToBeBetween(min_value=10_000)
    )

    return suite, batch_def
