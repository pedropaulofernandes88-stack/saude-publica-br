"""
Testes unitários para validation/suites/mart_mortalidade.py

Abordagem: cria DataFrames sintéticos cobrindo casos válidos e inválidos,
executa a suite Great Expectations em modo efêmero e verifica os resultados.

Estrutura:
  - TestBuildSuiteStructure  — suite retorna tipos corretos, lista todas as colunas
  - TestValidRows            — DataFrame válido passa em todas as expectations
  - TestNullViolations       — campos obrigatórios nulos fazem falhar
  - TestDomainViolations     — valores fora do domínio fazem falhar
  - TestCardinalityViolation — tabela com menos de 10 001 linhas faz falhar
"""
from __future__ import annotations

import pandas as pd
import pytest

from validation.suites.mart_mortalidade import build_suite, UFS_VALIDAS, SEXOS_VALIDOS


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _make_row(**overrides) -> dict:
    """Retorna um registro sintético válido; sobrescreve campos via kwargs."""
    base = {
        "municipio_cod": "355030",
        "municipio_nome": "São Paulo",
        "uf_sigla": "SP",
        "mes_competencia": "202401",
        "ano_obito": 2024,
        "mes_obito": 1,
        "causabas_cap": "IX",
        "sexo": "M",
        "faixa_etaria": "30-39",
        "tipobito": "2",
        "lococor_grupo": "hospital",
        "total_obitos": 10,
        "obitos_hospital": 8,
        "obitos_domicilio": 2,
        "taxa_mortalidade_bruta": 4.5,
        "pct_obitos_hospital": 80.0,
        "dbt_updated_at": "2024-01-15T00:00:00",
    }
    base.update(overrides)
    return base


@pytest.fixture
def valid_df() -> pd.DataFrame:
    """DataFrame mínimo (10 001 linhas) que passa em todas as expectations."""
    rows = [_make_row() for _ in range(10_001)]
    return pd.DataFrame(rows)


@pytest.fixture
def small_valid_df() -> pd.DataFrame:
    """DataFrame com 5 linhas para testes de estrutura/domínio (sem cardinalidade)."""
    rows = [_make_row() for _ in range(5)]
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _run(df: pd.DataFrame):
    """Executa a suite e retorna o objeto de resultados GX."""
    suite, batch_def = build_suite(df)
    batch = batch_def.get_batch(batch_parameters={"dataframe": df})
    return batch.validate(suite)


def _failed_types(results) -> set[str]:
    """Retorna o conjunto de expectation_type que falharam."""
    return {
        r.expectation_config.type
        for r in results.results
        if not r.success
    }


def _failed_columns(results) -> set[str]:
    """Retorna o conjunto de colunas que tiveram alguma expectation falhando."""
    return {
        r.expectation_config.kwargs.get("column", "")
        for r in results.results
        if not r.success
    }


# ---------------------------------------------------------------------------
# Testes de estrutura
# ---------------------------------------------------------------------------

class TestBuildSuiteStructure:
    def test_returns_tuple(self, small_valid_df):
        result = build_suite(small_valid_df)
        assert isinstance(result, tuple) and len(result) == 2

    def test_suite_name(self, small_valid_df):
        suite, _ = build_suite(small_valid_df)
        assert suite.name == "mart_mortalidade"

    def test_has_column_existence_expectations(self, small_valid_df):
        suite, _ = build_suite(small_valid_df)
        types = [e.expectation_type for e in suite.expectations]
        assert "expect_column_to_exist" in types

    def test_expectation_count_reasonable(self, small_valid_df):
        suite, _ = build_suite(small_valid_df)
        # Pelo menos 20 expectations (colunas + nulidade + domínio + cardinalidade)
        assert len(suite.expectations) >= 20


# ---------------------------------------------------------------------------
# Testes com DataFrame válido
# ---------------------------------------------------------------------------

class TestValidRows:
    def test_all_pass_on_valid_df(self, valid_df):
        results = _run(valid_df)
        assert results.success, (
            f"Expectations falhando inesperadamente: {_failed_types(results)}"
        )

    def test_no_failed_expectations(self, valid_df):
        results = _run(valid_df)
        failed = [r for r in results.results if not r.success]
        assert failed == []


# ---------------------------------------------------------------------------
# Testes de nulidade
# ---------------------------------------------------------------------------

class TestNullViolations:
    @pytest.mark.parametrize("col", [
        "municipio_cod", "uf_sigla", "mes_competencia",
        "ano_obito", "mes_obito", "sexo", "faixa_etaria",
        "total_obitos",
    ])
    def test_null_key_column_fails(self, col):
        rows = [_make_row(**{col: None}) for _ in range(5)]
        df = pd.DataFrame(rows)
        results = _run(df)
        assert col in _failed_columns(results), (
            f"Esperava falha na coluna '{col}' com valores nulos"
        )


# ---------------------------------------------------------------------------
# Testes de domínio
# ---------------------------------------------------------------------------

class TestDomainViolations:
    def test_ano_obito_below_range(self):
        rows = [_make_row(ano_obito=2019) for _ in range(5)]
        results = _run(pd.DataFrame(rows))
        assert "ano_obito" in _failed_columns(results)

    def test_ano_obito_above_range(self):
        rows = [_make_row(ano_obito=2025) for _ in range(5)]
        results = _run(pd.DataFrame(rows))
        assert "ano_obito" in _failed_columns(results)

    def test_mes_obito_zero(self):
        rows = [_make_row(mes_obito=0) for _ in range(5)]
        results = _run(pd.DataFrame(rows))
        assert "mes_obito" in _failed_columns(results)

    def test_mes_obito_thirteen(self):
        rows = [_make_row(mes_obito=13) for _ in range(5)]
        results = _run(pd.DataFrame(rows))
        assert "mes_obito" in _failed_columns(results)

    def test_mes_competencia_wrong_format(self):
        rows = [_make_row(mes_competencia="2024-01") for _ in range(5)]
        results = _run(pd.DataFrame(rows))
        assert "mes_competencia" in _failed_columns(results)

    def test_invalid_uf_sigla(self):
        rows = [_make_row(uf_sigla="XX") for _ in range(5)]
        results = _run(pd.DataFrame(rows))
        assert "uf_sigla" in _failed_columns(results)

    def test_invalid_municipio_cod_too_short(self):
        rows = [_make_row(municipio_cod="12345") for _ in range(5)]
        results = _run(pd.DataFrame(rows))
        assert "municipio_cod" in _failed_columns(results)

    def test_invalid_sexo(self):
        rows = [_make_row(sexo="X") for _ in range(5)]
        results = _run(pd.DataFrame(rows))
        assert "sexo" in _failed_columns(results)

    def test_negative_total_obitos(self):
        rows = [_make_row(total_obitos=-1) for _ in range(5)]
        results = _run(pd.DataFrame(rows))
        assert "total_obitos" in _failed_columns(results)

    def test_negative_taxa_mortalidade(self):
        rows = [_make_row(taxa_mortalidade_bruta=-0.1) for _ in range(5)]
        results = _run(pd.DataFrame(rows))
        assert "taxa_mortalidade_bruta" in _failed_columns(results)

    def test_pct_obitos_above_100(self):
        rows = [_make_row(pct_obitos_hospital=101.0) for _ in range(5)]
        results = _run(pd.DataFrame(rows))
        assert "pct_obitos_hospital" in _failed_columns(results)

    def test_all_ufs_valid(self):
        """Garante que todos os 27 valores de UF passam na suite."""
        rows = [_make_row(uf_sigla=uf) for uf in UFS_VALIDAS]
        # precisa atingir cardinalidade mínima
        rows = rows * (10_001 // len(rows) + 1)
        results = _run(pd.DataFrame(rows))
        # somente cardinalidade deve passar; UF não deve estar em falhas
        assert "uf_sigla" not in _failed_columns(results)

    def test_all_sexos_valid(self):
        """Garante que todos os valores de sexo passam na suite."""
        rows = [_make_row(sexo=s) for s in SEXOS_VALIDOS]
        rows = rows * (10_001 // len(rows) + 1)
        results = _run(pd.DataFrame(rows))
        assert "sexo" not in _failed_columns(results)


# ---------------------------------------------------------------------------
# Testes de cardinalidade
# ---------------------------------------------------------------------------

class TestCardinalityViolation:
    def test_too_few_rows_fails(self):
        rows = [_make_row() for _ in range(100)]
        results = _run(pd.DataFrame(rows))
        failed_types = _failed_types(results)
        assert "expect_table_row_count_to_be_between" in failed_types

    def test_exactly_10001_rows_passes_cardinality(self):
        rows = [_make_row() for _ in range(10_001)]
        results = _run(pd.DataFrame(rows))
        failed_types = _failed_types(results)
        assert "expect_table_row_count_to_be_between" not in failed_types
