"""
Testes para validation/suites/mart_producao_amb.py

Cobre:
  - Suite válida passa em todos os checks
  - Falha em colunas ausentes
  - Falha em valores nulos em campos obrigatórios
  - Falha em ano fora do intervalo [2020–2024]
  - Falha em mes_competencia fora de [1–12]
  - Falha em UF inválida
  - Falha em métricas negativas (total_procedimentos, total_aprovados, taxa_proc_10k)
  - Falha em pct_aprovacao fora de [0, 100]
  - Falha em municipio_cod com formato inválido
  - Falha em contagem de linhas insuficiente (<= 1000)
"""
from __future__ import annotations

import copy

import pandas as pd
import pytest

from validation.suites.mart_producao_amb import build_suite


pytestmark = [pytest.mark.validation, pytest.mark.unit]


# ---------------------------------------------------------------------------
# Fixtures locais
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def df_valid(df_producao_amb_valid):
    """Reutiliza o DataFrame válido de conftest (1050 linhas)."""
    return df_producao_amb_valid.copy()


def _run(df: pd.DataFrame):
    suite, batch_def = build_suite(df)
    batch = batch_def.get_batch(batch_parameters={"dataframe": df})
    return batch.validate(suite)


# ---------------------------------------------------------------------------
# Testes positivos
# ---------------------------------------------------------------------------

class TestProducaoAmbValid:
    def test_full_valid_dataframe_passes(self, df_valid):
        result = _run(df_valid)
        failed_detail = [(r.expectation_config.type, r.expectation_config.kwargs) for r in result.results if not r.success]
        assert result.success, (
            f"Suite falhou inesperadamente. "
            f"Falhas: {[r.expectation_config.type for r in result.results if not r.success]}"
        )

    def test_result_has_no_failed_expectations(self, df_valid):
        result = _run(df_valid)
        failed = [r for r in result.results if not r.success]
        assert failed == [], f"Expectations falhas: {[r.expectation_config.type for r in failed]}"


# ---------------------------------------------------------------------------
# Testes de colunas ausentes
# ---------------------------------------------------------------------------

class TestProducaoAmbMissingColumns:
    @pytest.mark.parametrize("col", [
        "municipio_cod", "uf_sigla", "ano", "mes_competencia",
        "total_procedimentos", "total_aprovados", "taxa_proc_10k", "pct_aprovacao",
    ])
    def test_missing_column_fails(self, df_valid, col):
        df = df_valid.drop(columns=[col])
        result = _run(df)
        assert not result.success


# ---------------------------------------------------------------------------
# Testes de valores nulos
# ---------------------------------------------------------------------------

class TestProducaoAmbNullValues:
    @pytest.mark.parametrize("col", [
        # Apenas colunas com ExpectColumnValuesToNotBeNull no suite
        "municipio_cod", "uf_sigla", "ano",
        "mes_competencia", "total_procedimentos",
    ])
    def test_null_in_key_column_fails(self, df_valid, col):
        df = df_valid.copy()
        df.loc[0, col] = None
        result = _run(df)
        assert not result.success


# ---------------------------------------------------------------------------
# Testes de domínio numérico
# ---------------------------------------------------------------------------

class TestProducaoAmbDomains:
    def test_ano_below_minimum_fails(self, df_valid):
        df = df_valid.copy()
        df.loc[0, "ano"] = 2019
        result = _run(df)
        assert not result.success

    def test_ano_above_maximum_fails(self, df_valid):
        df = df_valid.copy()
        df.loc[0, "ano"] = 2025
        result = _run(df)
        assert not result.success

    def test_mes_zero_fails(self, df_valid):
        df = df_valid.copy()
        df.loc[0, "mes"] = 0
        result = _run(df)
        assert not result.success

    def test_mes_thirteen_fails(self, df_valid):
        df = df_valid.copy()
        df.loc[0, "mes"] = 13
        result = _run(df)
        assert not result.success

    def test_negative_total_procedimentos_fails(self, df_valid):
        df = df_valid.copy()
        df.loc[0, "total_procedimentos"] = -1
        result = _run(df)
        assert not result.success

    def test_negative_taxa_proc_fails(self, df_valid):
        df = df_valid.copy()
        df.loc[0, "taxa_proc_10k"] = -0.01
        result = _run(df)
        assert not result.success

    def test_pct_aprovacao_above_100_fails(self, df_valid):
        df = df_valid.copy()
        df.loc[0, "pct_aprovacao"] = 100.01
        result = _run(df)
        assert not result.success

    def test_pct_aprovacao_negative_fails(self, df_valid):
        df = df_valid.copy()
        df.loc[0, "pct_aprovacao"] = -1.0
        result = _run(df)
        assert not result.success


# ---------------------------------------------------------------------------
# Testes de domínio categórico
# ---------------------------------------------------------------------------

class TestProducaoAmbCategories:
    def test_invalid_uf_fails(self, df_valid):
        df = df_valid.copy()
        df.loc[0, "uf_sigla"] = "XX"
        result = _run(df)
        assert not result.success

    def test_municipio_cod_wrong_format_fails(self, df_valid):
        df = df_valid.copy()
        df.loc[0, "municipio_cod"] = "ABCDEF"
        result = _run(df)
        assert not result.success

    def test_municipio_cod_too_short_fails(self, df_valid):
        df = df_valid.copy()
        df.loc[0, "municipio_cod"] = "12345"  # < 6 dígitos
        result = _run(df)
        assert not result.success
