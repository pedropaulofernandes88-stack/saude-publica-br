"""
Testes da matemática de agregação do SIH (scripts/_metricas_aih.py).

Por que estes testes existem: em 11/08/2026 o reprocessamento do SIH caiu duas
vezes EM PRODUÇÃO, depois de horas de download, por defeitos que qualquer um
destes casos teria pego em milissegundos:

  - `.replace(0, pd.NA)` no denominador devolvia dtype object com NAType, e o
    `.round()` seguinte estourava com "float() argument must be a string or a
    real number, not 'NAType'". Acontece só quando algum recorte tem
    aih_normal == 0, que é raro mas existe (57 linhas no mart publicado);
  - a chave de escrita caía para `anon` em silêncio e o upload levava 401.

Nenhum dos dois é sofisticado. Faltava régua.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))

from _metricas_aih import (  # noqa: E402
    CID10_CAPITULOS,
    MEDIDAS,
    aplica_metricas_por_episodio,
    capitulo,
)

pytestmark = pytest.mark.unit


def _linha(internacoes, obitos, dias, valor, cont, dias_norm, valor_norm) -> dict:
    return dict(zip(MEDIDAS, [internacoes, obitos, dias, valor, cont, dias_norm, valor_norm]))


# ---------------------------------------------------------------------------
# capitulo()
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("cid3,esperado", [
    ("A00", "I"), ("B99", "I"),          # limites do capítulo I
    ("C00", "II"), ("D48", "II"),
    ("D50", "III"),                       # D49 não existe; D50 abre o III
    ("F00", "V"), ("F32", "V"), ("F99", "V"),
    ("G00", "VI"), ("G40", "VI"), ("G99", "VI"),
    ("I10", "IX"), ("I69", "IX"),
    ("J44", "X"), ("O99", "XV"),
    ("S06", "XIX"), ("T98", "XIX"),       # XIX cruza a letra: S00-T98
    ("V01", "XX"), ("Y98", "XX"),
    ("U00", "XXII"),
])
def test_capitulo_mapeia_limites(cid3, esperado):
    assert capitulo(cid3) == esperado


def test_capitulo_desconhecido_vira_nd():
    assert capitulo("") == "N/D"
    assert capitulo("999") == "N/D"


def test_capitulos_nao_se_sobrepoem():
    """Nenhum CID pode cair em dois capítulos — a busca é linear e devolveria o primeiro."""
    for i, (cap_a, ini_a, fim_a) in enumerate(CID10_CAPITULOS):
        for cap_b, ini_b, fim_b in CID10_CAPITULOS[i + 1:]:
            sobrepoe = ini_a <= fim_b and ini_b <= fim_a
            assert not sobrepoe, f"{cap_a} ({ini_a}-{fim_a}) invade {cap_b} ({ini_b}-{fim_b})"


# ---------------------------------------------------------------------------
# aplica_metricas_por_episodio() — o caso que quebrou a produção
# ---------------------------------------------------------------------------

def test_aih_normal_zero_nao_estoura_e_vira_nan():
    """Recorte cujo volume inteiro é AIH de continuação: média por episódio não existe.

    Este é o caso exato que derrubou o pipeline. Tem de virar NaN, não exceção
    e não zero — zero afirmaria "permanência média de 0 dias", que é falso.
    """
    df = pd.DataFrame([
        _linha(10, 1, 40, 800.0, 2, 32, 640.0),   # normal
        _linha(3, 0, 30, 600.0, 3, 0, 0.0),       # tudo continuação
        _linha(0, 0, 0, 0.0, 0, 0, 0.0),          # recorte vazio
    ])
    out = aplica_metricas_por_episodio(df)

    assert out["permanencia_media"].dtype == np.float64
    assert out["custo_medio"].dtype == np.float64
    assert out.loc[0, "permanencia_media"] == pytest.approx(4.0)   # 32 / 8
    assert out.loc[0, "custo_medio"] == pytest.approx(80.0)        # 640 / 8
    assert pd.isna(out.loc[1, "permanencia_media"])
    assert pd.isna(out.loc[2, "permanencia_media"])


def test_metricas_nao_usam_a_continuacao_no_denominador():
    """Duas AIHs de continuação inflariam a média se entrassem na conta."""
    df = pd.DataFrame([_linha(12, 0, 100, 1200.0, 4, 60, 800.0)])
    out = aplica_metricas_por_episodio(df)
    assert out.loc[0, "aih_normal"] == 8
    assert out.loc[0, "permanencia_media"] == pytest.approx(7.5)    # 60/8, não 100/12
    assert out.loc[0, "custo_medio"] == pytest.approx(100.0)        # 800/8, não 1200/12


def test_mortalidade_usa_o_total_e_nao_a_base_normal():
    """O óbito cai na última AIH da sequência; dividir por aih_normal superestimaria."""
    df = pd.DataFrame([_linha(100, 5, 500, 1000.0, 20, 400, 800.0)])
    out = aplica_metricas_por_episodio(df)
    assert out.loc[0, "mortalidade_pct"] == pytest.approx(5.0)      # 5/100, não 5/80


def test_internacoes_zero_nao_estoura_na_mortalidade():
    df = pd.DataFrame([_linha(0, 0, 0, 0.0, 0, 0, 0.0)])
    out = aplica_metricas_por_episodio(df)
    assert pd.isna(out.loc[0, "mortalidade_pct"])


def test_casas_decimais_configuraveis():
    """pipeline_sih usa 2 casas na permanência; pipeline_sih_agravo usa 1."""
    df = pd.DataFrame([_linha(3, 0, 0, 0.0, 0, 10, 0.0)])
    assert aplica_metricas_por_episodio(df.copy(), 2).loc[0, "permanencia_media"] == pytest.approx(3.33)
    assert aplica_metricas_por_episodio(df.copy(), 1).loc[0, "permanencia_media"] == pytest.approx(3.3)


def test_sem_continuacao_a_media_bate_com_a_definicao_antiga():
    """Onde não há IDENT=5 — 17 dos 22 capítulos — o número não pode ter mudado."""
    df = pd.DataFrame([_linha(200, 10, 1000, 40000.0, 0, 1000, 40000.0)])
    out = aplica_metricas_por_episodio(df)
    assert out.loc[0, "permanencia_media"] == pytest.approx(1000 / 200)
    assert out.loc[0, "custo_medio"] == pytest.approx(40000.0 / 200)


# ---------------------------------------------------------------------------
# Invariantes dos contadores vindos do RD
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("linha,motivo", [
    (_linha(10, 0, 50, 100.0, 11, 40, 90.0), "continuação maior que o total"),
    (_linha(10, 0, 50, 100.0, 2, 60, 90.0), "dias normais maiores que os totais"),
    (_linha(10, 0, 50, 100.0, 2, 40, 110.0), "valor normal maior que o total"),
])
def test_invariantes_detectam_contagem_incoerente(linha, motivo):
    """Guarda contra regressão na acumulação: `_norm` é subconjunto do total."""
    df = pd.DataFrame([linha])
    coerente = (
        (df["aih_continuacao"] <= df["internacoes"]).all()
        and (df["dias_permanencia_normal"] <= df["dias_permanencia"]).all()
        and (df["valor_normal"] <= df["valor_total"] + 1e-6).all()
    )
    assert not coerente, f"o caso deveria ser flagrado como incoerente: {motivo}"


def test_acumulacao_real_respeita_os_invariantes():
    rng = np.random.default_rng(20260812)
    n = 500
    internacoes = rng.integers(1, 5000, n)
    cont = (internacoes * rng.uniform(0, 0.3, n)).astype(int)
    dias = rng.integers(0, 20, n) * internacoes
    dias_norm = (dias * (1 - cont / internacoes)).astype(int)
    valor = rng.uniform(100, 5000, n) * internacoes
    valor_norm = valor * (1 - cont / internacoes)
    df = pd.DataFrame({
        "internacoes": internacoes, "obitos": rng.integers(0, 100, n),
        "dias_permanencia": dias, "valor_total": valor, "aih_continuacao": cont,
        "dias_permanencia_normal": dias_norm, "valor_normal": valor_norm,
    })
    out = aplica_metricas_por_episodio(df)

    assert (out["aih_continuacao"] <= out["internacoes"]).all()
    assert (out["dias_permanencia_normal"] <= out["dias_permanencia"]).all()
    assert (out["valor_normal"] <= out["valor_total"] + 1e-6).all()
    assert (out["aih_normal"] >= 0).all()
    validas = out["permanencia_media"].notna()
    assert (out.loc[validas, "permanencia_media"] >= 0).all()
