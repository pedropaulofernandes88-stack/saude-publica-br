"""
Testes para validation/suites/mart_mix_complexidade.py

Cobre:
  - Suite válida passa
  - Falha em colunas ausentes
  - Falha em nulos em campos obrigatórios
  - Falha em ano fora do intervalo
  - Falha em pct_ab/pct_mc/pct_ac fora de [0, 100]
  - Falha em total_procedimentos negativo
  - Falha em indice_complexidade fora de [1, 3]
  - Falha em nivel_complexidade com valor inválido
  - Falha em contagem de linhas insuficiente
"""
from __future__ import annotations

import pandas as pd
import pytest

from validation.suites.mart_mix_complexidade import build_suite


pytestmark = [pytest.mark.validation, pytest.mark.unit]


def _run(df: pd.DataFrame):
    suite, batch_def = build_suite(df)
    batch = batch_def.get_batch(batch_parameters={"dataframe": df})
    return batch.validate(suite)


class TestMixComplexidadeValid:
    def test_full_valid_passes(self, df_mix_complexidade_valid):
        result = _run(df_mix_complexidade_valid)
        assert result.success

    def test_no_failed_expectations(self, df_mix_complexidade_valid):
        result = _run(df_mix_complexidade_valid)
        failed = [r.expectation_config.type for r in result.results if not r.success]
        assert failed == []


class TestMixComplexidadeMissingColumns:
    @pytest.mark.parametrize("col", [
        "municipio_cod", "uf_sigla", "ano",
        "total_procedimentos",
        "pct_ab", "pct_mc", "pct_ac",
        "indice_complexidade", "nivel_complexidade",
    ])
    def test_missing_column_fails(self, df_mix_complexidade_valid, col):
        df = df_mix_complexidade_valid.drop(columns=[col])
        result = _run(df)
        assert not result.success


class TestMixComplexidadeNull:
    @pytest.mark.parametrize("col", [
        "municipio_cod", "uf_sigla", "ano",
        "total_procedimentos", "indice_complexidade", "nivel_complexidade",
    ])
    def test_null_in_required_col_fails(self, df_mix_complexidade_valid, col):
        df = df_mix_complexidade_valid.copy()
        df.loc[0, col] = None
        result = _run(df)
        assert not result.success


class TestMixComplexidadeDomains:
    def test_ano_out_of_range_fails(self, df_mix_complexidade_valid):
        df = df_mix_complexidade_valid.copy()
        df.loc[0, "ano"] = 2025
        result = _run(df)
        assert not result.success

    @pytest.mark.parametrize("col", ["pct_ab", "pct_mc", "pct_ac"])
    def test_pct_above_100_fails(self, df_mix_complexidade_valid, col):
        df = df_mix_complexidade_valid.copy()
        df.loc[0, col] = 100.1
        result = _run(df)
        assert not result.success

    @pytest.mark.parametrize("col", ["pct_ab", "pct_mc", "pct_ac"])
    def test_pct_negative_fails(self, df_mix_complexidade_valid, col):
        df = df_mix_complexidade_valid.copy()
        df.loc[0, col] = -0.01
        result = _run(df)
        assert not result.success

    def test_total_procedimentos_negative_fails(self, df_mix_complexidade_valid):
        df = df_mix_complexidade_valid.copy()
        df.loc[0, "total_procedimentos"] = -1
        result = _run(df)
        assert not result.success

    def test_indice_complexidade_below_one_fails(self, df_mix_complexidade_valid):
        df = df_mix_complexidade_valid.copy()
        df.loc[0, "indice_complexidade"] = 0.99
        result = _run(df)
        assert not result.success

    def test_indice_complexidade_above_three_fails(self, df_mix_complexidade_valid):
        df = df_mix_complexidade_valid.copy()
        df.loc[0, "indice_complexidade"] = 3.01
        result = _run(df)
        assert not result.success

    def test_indice_complexidade_boundary_one_passes(self, df_mix_complexidade_valid):
        df = df_mix_complexidade_valid.copy()
        df.loc[0, "indice_complexidade"] = 1.0
        result = _run(df)
        indice_fails = [
            r for r in result.results
            if not r.success
            and "indice_complexidade" in str(r.expectation_config.kwargs)
        ]
        assert indice_fails == []

    def test_invalid_nivel_complexidade_fails(self, df_mix_complexidade_valid):
        df = df_mix_complexidade_valid.copy()
        df.loc[0, "nivel_complexidade"] = "Muito Alta"
        result = _run(df)
        assert not result.success

    @pytest.mark.parametrize("nivel", ["Baixa", "Média", "Alta"])
    def test_valid_niveis_accepted(self, df_mix_complexidade_valid, nivel):
        df = df_mix_complexidade_valid.copy()
        df["nivel_complexidade"] = nivel
        result = _run(df)
        nivel_fails = [
            r for r in result.results
            if not r.success
            and "nivel_complexidade" in str(r.expectation_config.kwargs)
        ]
        assert nivel_fails == []


class TestMixComplexidadeRowCount:
    def test_too_few_rows_fails(self, df_mix_complexidade_valid):
        df = df_mix_complexidade_valid.head(200)
        result = _run(df)
        assert not result.success
