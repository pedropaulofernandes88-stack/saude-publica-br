"""
Os intervalos do artigo de neoplasias, conferidos contra referência independente.

`taxa_padronizada_ic` (Fay & Feuer) e `razao_taxas_ic` (binomial exata
condicional) sustentam afirmações do manuscrito — inclusive a de que dois
intervalos NÃO se sobrepõem, que é o que carrega o argumento onde ele é mais
forte. Até 2026-09-07 nenhum teste tocava neste arquivo: as duas funções eram
conferidas só por parecerem plausíveis na tabela.

Cada teste aqui compara contra algo que não é a própria implementação — a
função de distribuição do scipy, o intervalo exato de Poisson, ou uma identidade
algébrica —, nunca contra um número que saiu de uma execução anterior.

Executar: .venv311/Scripts/python -m pytest tests/test_analise_neoplasias.py
"""
from __future__ import annotations

import math

import pytest

pytest.importorskip("scipy")
pytest.importorskip("duckdb")

from scripts.analise_neoplasias import (  # noqa: E402
    PADRAO_OMS,
    razao_taxas_ic,
    taxa_padronizada_ic,
)


# ── razão de duas taxas: binomial exata condicional ────────────────────────

def test_razao_bate_com_clopper_pearson_do_scipy():
    """A razão é p/(1−p)·n2/n1, com p pelo intervalo exato da binomial.

    A referência é `binomtest(...).proportion_ci(method='exact')`, que é o
    Clopper–Pearson do scipy — implementação independente desta.
    """
    from scipy.stats import binomtest

    d1, d2 = 137, 421
    _, inf, sup = razao_taxas_ic(d1, 1.0, d2, 1.0)
    ic = binomtest(d1, d1 + d2).proportion_ci(method="exact")
    assert inf == pytest.approx(ic.low / (1 - ic.low), rel=1e-9)
    assert sup == pytest.approx(ic.high / (1 - ic.high), rel=1e-9)


def test_razao_pontual_e_a_divisao_das_duas_taxas():
    razao, _, _ = razao_taxas_ic(300, 2.0, 100, 5.0)
    assert razao == pytest.approx((300 / 2.0) / (100 / 5.0))


def test_intervalo_contem_a_razao_pontual():
    for d1, d2 in [(1, 1), (5, 500), (500, 5), (12_345, 6_789)]:
        razao, inf, sup = razao_taxas_ic(d1, 1.0, d2, 1.0)
        assert inf <= razao <= sup, (d1, d2)


def test_a_escala_entra_na_razao_e_no_intervalo():
    """Dobrar o tempo-pessoa do denominador dobra razão e extremos."""
    r1, i1, s1 = razao_taxas_ic(200, 1.0, 100, 1.0)
    r2, i2, s2 = razao_taxas_ic(200, 1.0, 100, 2.0)
    assert r2 == pytest.approx(2 * r1)
    assert i2 == pytest.approx(2 * i1)
    assert s2 == pytest.approx(2 * s1)


def test_intervalo_encolhe_quando_a_contagem_cresce():
    """Mesma razão, dez vezes mais eventos: o intervalo tem de estreitar."""
    _, i1, s1 = razao_taxas_ic(50, 1.0, 50, 1.0)
    _, i2, s2 = razao_taxas_ic(500, 1.0, 500, 1.0)
    assert (s2 - i2) < (s1 - i1)


def test_contagem_zero_no_numerador_da_limite_inferior_zero():
    razao, inf, sup = razao_taxas_ic(0, 1.0, 40, 1.0)
    assert razao == 0.0
    assert inf == 0.0
    assert sup > 0.0


def test_sem_evento_nenhum_devolve_nan_em_vez_de_dividir_por_zero():
    for v in razao_taxas_ic(0, 1.0, 0, 1.0):
        assert math.isnan(v)


# ── taxa padronizada: Fay & Feuer ──────────────────────────────────────────

def test_um_estrato_so_reduz_ao_intervalo_exato_de_poisson():
    """Com um estrato, a padronizada é a bruta e o IC é o de Poisson.

    Referência: os limites exatos de Poisson por qui-quadrado, que é a
    construção clássica e independente do gama de Fay–Feuer.
    """
    from scipy.stats import chi2

    d, py = 42, 100_000.0
    taxa, inf, sup = taxa_padronizada_ic([d], [py], [1.0])
    assert taxa == pytest.approx(1e5 * d / py)
    assert inf == pytest.approx(1e5 * chi2.ppf(0.025, 2 * d) / 2 / py, rel=1e-6)
    assert sup == pytest.approx(1e5 * chi2.ppf(0.975, 2 * (d + 1)) / 2 / py, rel=1e-6)


def test_peso_igual_em_todo_estrato_reproduz_a_taxa_bruta():
    obitos = [10.0, 40.0, 250.0]
    py = [50_000.0, 80_000.0, 120_000.0]
    taxa, _, _ = taxa_padronizada_ic(obitos, py, py)  # peso = a própria população
    assert taxa == pytest.approx(1e5 * sum(obitos) / sum(py))


def test_padronizacao_desfaz_a_diferenca_de_estrutura_etaria():
    """Duas populações com as MESMAS taxas por faixa e pirâmides opostas.

    A bruta as separa; a padronizada tem de devolver o mesmo número. É o achado
    central do artigo reduzido a um caso de teste.
    """
    taxas = [0.0001, 0.005]                 # jovens, idosos
    jovem = [900_000.0, 100_000.0]
    velha = [100_000.0, 900_000.0]
    peso = [1.0, 1.0]
    a, _, _ = taxa_padronizada_ic([t * p for t, p in zip(taxas, jovem, strict=True)],
                                  jovem, peso)
    b, _, _ = taxa_padronizada_ic([t * p for t, p in zip(taxas, velha, strict=True)],
                                  velha, peso)
    assert a == pytest.approx(b)
    bruta_jovem = 1e5 * sum(t * p for t, p in zip(taxas, jovem, strict=True)) / sum(jovem)
    bruta_velha = 1e5 * sum(t * p for t, p in zip(taxas, velha, strict=True)) / sum(velha)
    assert bruta_velha > 4 * bruta_jovem


def test_intervalo_da_padronizada_contem_a_estimativa():
    obitos = [3.0, 25.0, 180.0, 900.0]
    py = [40_000.0, 90_000.0, 70_000.0, 30_000.0]
    peso = [0.4, 0.3, 0.2, 0.1]
    taxa, inf, sup = taxa_padronizada_ic(obitos, py, peso)
    assert inf < taxa < sup


def test_zero_obito_nao_derruba_a_padronizada():
    """Estrato sem óbito conta como zero — é o esqueleto completo do artigo."""
    taxa, inf, sup = taxa_padronizada_ic([0.0, 30.0], [10_000.0, 10_000.0], [1.0, 1.0])
    assert taxa == pytest.approx(1e5 * (0 / 10_000 + 30 / 10_000) / 2)
    assert inf >= 0.0
    assert sup > taxa


# ── a constante que não pode derivar ───────────────────────────────────────

def test_padrao_da_oms_soma_um_milhao():
    """O padrão mundial é norma publicada; somar diferente é tê-lo digitado errado."""
    assert sum(PADRAO_OMS.values()) == 1_000_000


def test_padrao_da_oms_e_monotonicamente_decrescente_a_partir_dos_10_anos():
    idades = sorted(PADRAO_OMS)
    pesos = [PADRAO_OMS[i] for i in idades if i >= 10]
    assert pesos == sorted(pesos, reverse=True)
