"""
O estimador de painel tem de recuperar um efeito conhecido — e o ingênuo, não.

`scripts/_poisson_fe.py` implementa Poisson condicional de efeitos fixos à mão,
porque o projeto não tem `statsmodels`. Implementar estimador à mão só se
justifica se ele for demonstrado, e é isto que estes testes fazem: simulam
painel com efeito **conhecido** e exigem recuperação.

O terceiro teste é o que dá sentido aos dois primeiros. Ele mostra que um
estimador SEM efeitos fixos — Poisson comum sobre o mesmo painel — devolve viés
grande quando o intercepto de município varia. Sem ele, "o estimador acertou"
não diria se os efeitos fixos estavam fazendo alguma coisa.

Executar: .venv311/Scripts/python -m pytest tests/test_poisson_fe.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "scripts"))

from _poisson_fe import ajustar, autoteste  # noqa: E402

pytestmark = pytest.mark.unit


def test_recupera_o_efeito_conhecido():
    """Tolerância de 0,02 no log — folgada para o ruído, apertada para viés."""
    r = autoteste()
    for verdadeiro, estimado, erro in zip(r["verdadeiro"], r["estimado"],
                                          r["erro_absoluto"]):
        assert erro < 0.02, (
            f"o estimador devolveu {estimado:.4f} para um efeito verdadeiro de "
            f"{verdadeiro:.4f}. Erro de {erro:.4f} no log é viés, não ruído: "
            "com 400 municípios e 9 anos o desvio amostral é uma ordem de "
            "grandeza menor que isso.")


def test_recupera_com_outra_semente():
    """Uma semente que acerta pode acertar por sorte. Duas, não."""
    r = autoteste(semente=20260912, n_mun=300)
    assert max(r["erro_absoluto"]) < 0.03, r


def test_ignorar_os_efeitos_fixos_enviesa():
    """A metade que mostra o estimador trabalhando.

    Aqui a exposição é correlacionada com o intercepto do município — que é o
    caso real: município que não vigia a água é município diferente em tudo. Um
    Poisson comum confunde o efeito da exposição com o nível do município; o
    condicional não pode, porque o nível não está na verossimilhança dele.
    """
    rng = np.random.default_rng(3)
    n_mun, n_ano, beta = 500, 9, -0.4
    mun = np.repeat(np.arange(n_mun), n_ano)
    alfa_mun = rng.uniform(-3.0, 2.0, size=n_mun)
    alfa = alfa_mun[mun]
    pop = np.exp(rng.uniform(8.0, 12.0, size=n_mun))[mun]

    # exposicao MAIS provavel onde o intercepto e' alto: confundimento por
    # construcao, e a razao de o efeito fixo existir
    p = 1 / (1 + np.exp(-(alfa_mun - alfa_mun.mean())))
    x = rng.binomial(1, p[mun]).astype(float)
    X = x.reshape(-1, 1)
    y = rng.poisson(pop * np.exp(alfa + beta * x)).astype(float)

    # com efeitos fixos
    com_fe = ajustar(y, X, pop, mun)[0]

    # sem efeitos fixos: um unico grupo, isto e', Poisson comum com offset
    sem_fe = ajustar(y, np.column_stack([x, np.ones_like(x)]), pop,
                     np.zeros_like(mun))[0]

    assert abs(com_fe - beta) < 0.05, f"com FE devia recuperar {beta}, deu {com_fe:.3f}"
    assert abs(sem_fe - beta) > abs(com_fe - beta) * 3, (
        f"sem efeitos fixos o viés devia ser grande (deu {sem_fe:.3f} contra "
        f"{beta}), e com eles pequeno ({com_fe:.3f}). Se os dois acertam, o "
        "painel simulado não tem confundimento e o teste não prova nada.")


def test_municipio_sem_obito_nao_gera_nan():
    """Município com contagem total zero tem multinomial degenerada.

    Descartá-lo é correto; deixá-lo entrar produzia NaN que se propagava até a
    tabela do artigo sem nada acusar.
    """
    rng = np.random.default_rng(11)
    mun = np.repeat(np.arange(50), 6)
    pop = np.full(mun.size, 10_000.0)
    x = rng.binomial(1, 0.4, size=mun.size).astype(float)
    y = rng.poisson(2.0, size=mun.size).astype(float)
    y[mun < 10] = 0.0                      # dez municipios sem obito algum
    b = ajustar(y, x.reshape(-1, 1), pop, mun)
    assert np.isfinite(b).all(), b
