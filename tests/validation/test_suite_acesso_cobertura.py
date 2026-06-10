"""
Testes para validation/suites/mart_acesso_cobertura.py

Cobre:
  - Suite válida passa
  - Falha em colunas ausentes
  - Falha em nulos em campos obrigatórios
  - Falha em ano fora do intervalo
  - Falha em quartil_acesso com valor inválido
  - Falha em indice_acesso fora de [0, 1]
  - Falha em taxa_cobertura negativa
  - Falha em populacao <= 0
  - Falha em flag_baixa_cobertura com valor inválido (ex: 2)
  - Falha em contagem de linhas insuficiente
"""
from __future__ import annotations

import pandas as pd
import pytest

from validation.suites.mart_acesso_cobertura import build_suite


pytestmark = [pytest.mark.validation, pytest.mark.unit]


def _run(df: pd.DataFrame):
    suite, batch_def = build_suite(df)
    batch = batch_def.get_batch(batch_parameters={"dataframe": df})
    return batch.validate(suite)


class TestAcessoCoberturaValid:
    def test_full_valid_passes(self, df_acesso_cobertura_valid):
        result = _run(df_acesso_cobertura_valid)
        assert result.success

    def test_no_failed_expectations(self, df_acesso_cobertura_valid):
        result = _run(df_acesso_cobertura_valid)
        failed = [r.expectation_config.type for r in result.results if not r.success]
        assert failed == []


class TestAcessoCoberturaMissingColumns:
    @pytest.mark.parametrize("col", [
        "municipio_cod", "uf_sigla", "ano",
        "populacao", "taxa_cobertura",
        "indice_acesso", "quartil_acesso", "flag_baixa_cobertura",
    ])
    def test_missing_column_fails(self, df_acesso_cobertura_valid, col):
        df = df_acesso_cobertura_valid.drop(columns=[col])
        result = _run(df)
        assert not result.success


class TestAcessoCoberturaNull:
    @pytest.mark.parametrize("col", [
        "municipio_cod", "uf_sigla", "ano",
        "quartil_acesso", "flag_baixa_cobertura",
    ])
    def test_null_in_required_col_fails(self, df_acesso_cobertura_valid, col):
        df = df_acesso_cobertura_valid.copy()
        df.loc[0, col] = None
        result = _run(df)
        assert not result.success


class TestAcessoCoberturaDomains:
    def test_ano_out_of_range_fails(self, df_acesso_cobertura_valid):
        df = df_acesso_cobertura_valid.copy()
        df.loc[0, "ano"] = 2019
        result = _run(df)
        assert not result.success

    def test_invalid_quartil_fails(self, df_acesso_cobertura_valid):
        df = df_acesso_cobertura_valid.copy()
        df.loc[0, "quartil_acesso"] = "Q5"
        result = _run(df)
        assert not result.success

    def test_indice_acesso_above_one_fails(self, df_acesso_cobertura_valid):
        df = df_acesso_cobertura_valid.copy()
        df.loc[0, "indice_acesso"] = 1.001
        result = _run(df)
        assert not result.success

    def test_indice_acesso_negative_fails(self, df_acesso_cobertura_valid):
        df = df_acesso_cobertura_valid.copy()
        df.loc[0, "indice_acesso"] = -0.001
        result = _run(df)
        assert not result.success

    def test_taxa_cobertura_negative_fails(self, df_acesso_cobertura_valid):
        df = df_acesso_cobertura_valid.copy()
        df.loc[0, "taxa_cobertura"] = -1.0
        result = _run(df)
        assert not result.success

    def test_populacao_zero_fails(self, df_acesso_cobertura_valid):
        df = df_acesso_cobertura_valid.copy()
        df.loc[0, "populacao"] = 0
        result = _run(df)
        assert not result.success

    def test_flag_invalid_value_fails(self, df_acesso_cobertura_valid):
        df = df_acesso_cobertura_valid.copy()
        df.loc[0, "flag_baixa_cobertura"] = 2
        result = _run(df)
        assert not result.success

    def test_flag_accepts_true_false(self, df_acesso_cobertura_valid):
        """flag_baixa_cobertura aceita True/False além de 0/1."""
        df = df_acesso_cobertura_valid.copy()
        df["flag_baixa_cobertura"] = df["flag_baixa_cobertura"].map({0: False, 1: True})
        result = _run(df)
        assert result.success


class TestAcessoCoberturaRowCount:
    def test_too_few_rows_fails(self, df_acesso_cobertura_valid):
        df = df_acesso_cobertura_valid.head(300)
        result = _run(df)
        assert not result.success
