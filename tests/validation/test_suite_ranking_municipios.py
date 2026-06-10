"""
Testes para validation/suites/mart_ranking_municipios.py

Cobre:
  - Suite válida passa
  - Falha em colunas ausentes
  - Falha em nulos em campos obrigatórios
  - Falha em ano fora do intervalo
  - Falha em ranking_estadual/nacional < 1
  - Falha em percentil_* fora de [0, 100]
  - Falha em taxa_proc_10k negativa
  - Falha em pct_aprovacao fora de [0, 100]
  - Falha em scores fora de [0, 1]
  - Falha em categoria com valor inválido
  - Falha em contagem de linhas insuficiente
"""
from __future__ import annotations

import pandas as pd
import pytest

from validation.suites.mart_ranking_municipios import build_suite


pytestmark = [pytest.mark.validation, pytest.mark.unit]


def _run(df: pd.DataFrame):
    suite, batch_def = build_suite(df)
    batch = batch_def.get_batch(batch_parameters={"dataframe": df})
    return batch.validate(suite)


class TestRankingMunicipiosValid:
    def test_full_valid_passes(self, df_ranking_municipios_valid):
        result = _run(df_ranking_municipios_valid)
        assert result.success

    def test_no_failed_expectations(self, df_ranking_municipios_valid):
        failed = [r.expectation_config.type
                  for r in _run(df_ranking_municipios_valid).results
                  if not r.success]
        assert failed == []


class TestRankingMunicipiosMissingColumns:
    @pytest.mark.parametrize("col", [
        "municipio_cod", "municipio_nome", "uf_sigla", "ano",
        "total_procedimentos", "total_aprovados",
        "taxa_proc_10k", "pct_aprovacao",
        "ranking_estadual", "ranking_nacional",
        "percentil_estadual", "percentil_nacional",
        "score_acesso", "score_producao", "score_geral",
        "categoria",
    ])
    def test_missing_column_fails(self, df_ranking_municipios_valid, col):
        df = df_ranking_municipios_valid.drop(columns=[col])
        result = _run(df)
        assert not result.success


class TestRankingMunicipiosNull:
    @pytest.mark.parametrize("col", [
        "municipio_cod", "uf_sigla", "ano",
        "total_procedimentos", "ranking_estadual",
        "ranking_nacional", "categoria",
    ])
    def test_null_in_required_col_fails(self, df_ranking_municipios_valid, col):
        df = df_ranking_municipios_valid.copy()
        df.loc[0, col] = None
        result = _run(df)
        assert not result.success


class TestRankingMunicipiosDomains:
    def test_ano_out_of_range_fails(self, df_ranking_municipios_valid):
        df = df_ranking_municipios_valid.copy()
        df.loc[0, "ano"] = 2019
        result = _run(df)
        assert not result.success

    @pytest.mark.parametrize("col", ["ranking_estadual", "ranking_nacional"])
    def test_ranking_zero_fails(self, df_ranking_municipios_valid, col):
        df = df_ranking_municipios_valid.copy()
        df.loc[0, col] = 0
        result = _run(df)
        assert not result.success

    @pytest.mark.parametrize("col", ["ranking_estadual", "ranking_nacional"])
    def test_ranking_negative_fails(self, df_ranking_municipios_valid, col):
        df = df_ranking_municipios_valid.copy()
        df.loc[0, col] = -1
        result = _run(df)
        assert not result.success

    @pytest.mark.parametrize("col", ["percentil_estadual", "percentil_nacional"])
    def test_percentil_above_100_fails(self, df_ranking_municipios_valid, col):
        df = df_ranking_municipios_valid.copy()
        df.loc[0, col] = 100.01
        result = _run(df)
        assert not result.success

    @pytest.mark.parametrize("col", ["percentil_estadual", "percentil_nacional"])
    def test_percentil_negative_fails(self, df_ranking_municipios_valid, col):
        df = df_ranking_municipios_valid.copy()
        df.loc[0, col] = -0.01
        result = _run(df)
        assert not result.success

    def test_taxa_proc_negative_fails(self, df_ranking_municipios_valid):
        df = df_ranking_municipios_valid.copy()
        df.loc[0, "taxa_proc_10k"] = -1.0
        result = _run(df)
        assert not result.success

    def test_pct_aprovacao_above_100_fails(self, df_ranking_municipios_valid):
        df = df_ranking_municipios_valid.copy()
        df.loc[0, "pct_aprovacao"] = 101.0
        result = _run(df)
        assert not result.success

    @pytest.mark.parametrize("score_col", ["score_acesso", "score_producao", "score_geral"])
    def test_score_above_one_fails(self, df_ranking_municipios_valid, score_col):
        df = df_ranking_municipios_valid.copy()
        df.loc[0, score_col] = 1.001
        result = _run(df)
        assert not result.success

    @pytest.mark.parametrize("score_col", ["score_acesso", "score_producao", "score_geral"])
    def test_score_negative_fails(self, df_ranking_municipios_valid, score_col):
        df = df_ranking_municipios_valid.copy()
        df.loc[0, score_col] = -0.001
        result = _run(df)
        assert not result.success

    def test_invalid_categoria_fails(self, df_ranking_municipios_valid):
        df = df_ranking_municipios_valid.copy()
        df.loc[0, "categoria"] = "Ótimo"
        result = _run(df)
        assert not result.success

    @pytest.mark.parametrize("cat", ["Excelente", "Bom", "Regular", "Crítico"])
    def test_all_categorias_accepted(self, df_ranking_municipios_valid, cat):
        df = df_ranking_municipios_valid.copy()
        df["categoria"] = cat
        result = _run(df)
        cat_fails = [
            r for r in result.results
            if not r.success and "categoria" in str(r.expectation_config.kwargs)
        ]
        assert cat_fails == []


class TestRankingMunicipiosRowCount:
    def test_too_few_rows_fails(self, df_ranking_municipios_valid):
        df = df_ranking_municipios_valid.head(200)
        result = _run(df)
        assert not result.success
