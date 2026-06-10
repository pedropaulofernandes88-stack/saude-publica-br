"""
Testes para validation/suites/mart_epi_cid10.py

Cobre:
  - Suite válida passa
  - Falha em colunas ausentes
  - Falha em nulos em campos obrigatórios (variacao_anual_pct é NULLABLE — não deve falhar)
  - Falha em ano fora do intervalo
  - Falha em pct_atend_uf fora de [0, 100]
  - Falha em rank_capitulo_uf < 1
  - Falha em total_procedimentos negativo
  - Falha em capitulo_cid10 com formato inválido (não romano)
  - variacao_anual_pct NULL não causa falha (primeiro ano válido)
  - Falha em contagem de linhas insuficiente
"""
from __future__ import annotations

import pandas as pd
import pytest

from validation.suites.mart_epi_cid10 import build_suite


pytestmark = [pytest.mark.validation, pytest.mark.unit]


def _run(df: pd.DataFrame):
    suite, batch_def = build_suite(df)
    batch = batch_def.get_batch(batch_parameters={"dataframe": df})
    return batch.validate(suite)


class TestEpiCid10Valid:
    def test_full_valid_passes(self, df_epi_cid10_valid):
        result = _run(df_epi_cid10_valid)
        assert result.success

    def test_variacao_anual_all_null_does_not_fail(self, df_epi_cid10_valid):
        """variacao_anual_pct pode ser inteiramente NULL (ex: série só do 1º ano)."""
        df = df_epi_cid10_valid.copy()
        df["variacao_anual_pct"] = None
        result = _run(df)
        assert result.success


class TestEpiCid10MissingColumns:
    @pytest.mark.parametrize("col", [
        "uf_sigla", "ano", "capitulo_cid10", "descricao_capitulo",
        "total_procedimentos", "pct_atend_uf",
        "rank_capitulo_uf", "variacao_anual_pct",
    ])
    def test_missing_column_fails(self, df_epi_cid10_valid, col):
        df = df_epi_cid10_valid.drop(columns=[col])
        result = _run(df)
        assert not result.success


class TestEpiCid10Null:
    @pytest.mark.parametrize("col", [
        "uf_sigla", "ano", "capitulo_cid10", "descricao_capitulo",
        "total_procedimentos", "pct_atend_uf", "rank_capitulo_uf",
    ])
    def test_null_in_required_col_fails(self, df_epi_cid10_valid, col):
        df = df_epi_cid10_valid.copy()
        df.loc[0, col] = None
        result = _run(df)
        assert not result.success


class TestEpiCid10Domains:
    def test_ano_below_range_fails(self, df_epi_cid10_valid):
        df = df_epi_cid10_valid.copy()
        df.loc[0, "ano"] = 2019
        result = _run(df)
        assert not result.success

    def test_pct_above_100_fails(self, df_epi_cid10_valid):
        df = df_epi_cid10_valid.copy()
        df.loc[0, "pct_atend_uf"] = 100.5
        result = _run(df)
        assert not result.success

    def test_pct_negative_fails(self, df_epi_cid10_valid):
        df = df_epi_cid10_valid.copy()
        df.loc[0, "pct_atend_uf"] = -1.0
        result = _run(df)
        assert not result.success

    def test_rank_zero_fails(self, df_epi_cid10_valid):
        df = df_epi_cid10_valid.copy()
        df.loc[0, "rank_capitulo_uf"] = 0
        result = _run(df)
        assert not result.success

    def test_total_procedimentos_negative_fails(self, df_epi_cid10_valid):
        df = df_epi_cid10_valid.copy()
        df.loc[0, "total_procedimentos"] = -1
        result = _run(df)
        assert not result.success

    @pytest.mark.parametrize("cap_invalido", [
        "A",       # letra latina
        "XXXXXXX", # muito longo (> 6 chars)
        "12",      # número
        "i",       # minúscula
        "",        # vazio
    ])
    def test_invalid_capitulo_format_fails(self, df_epi_cid10_valid, cap_invalido):
        df = df_epi_cid10_valid.copy()
        df.loc[0, "capitulo_cid10"] = cap_invalido
        result = _run(df)
        assert not result.success

    @pytest.mark.parametrize("cap_valido", [
        "I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X",
        "XI", "XII", "XIII", "XIV", "XV", "XVI", "XVII", "XVIII", "XIX", "XX", "XXI",
    ])
    def test_all_cid10_chapters_accepted(self, df_epi_cid10_valid, cap_valido):
        df = df_epi_cid10_valid.copy()
        # Substitui todos para o capítulo testado — apenas verifica o regex
        df["capitulo_cid10"] = cap_valido
        result = _run(df)
        # Pode falhar por outro motivo (ex: row count), foca apenas na expectativa do regex
        regex_fails = [
            r for r in result.results
            if not r.success
            and "regex" in r.expectation_config.type.lower()
        ]
        assert regex_fails == [], f"Capítulo {cap_valido!r} rejeitado pelo regex"


class TestEpiCid10RowCount:
    def test_too_few_rows_fails(self, df_epi_cid10_valid):
        df = df_epi_cid10_valid.head(50)
        result = _run(df)
        assert not result.success
