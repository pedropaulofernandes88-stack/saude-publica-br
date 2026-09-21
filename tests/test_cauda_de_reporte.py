"""A formalização da cauda de reporte, exercitada nos dois sentidos.

As funções aqui são pequenas e a tentação de não testá-las é grande. O motivo
de existirem testes é que TODAS as três já erraram durante a construção:

  * `_completude` media sazonalidade como incompletude, e dava "cauda infinita"
    para o InfoDengue porque as semanas 23–34 são a baixa estação da dengue;
  * `defasagem` pegava o primeiro cruzamento isolado de τ, devolvendo defasagem
    otimista por acidente de ruído;
  * o piso de ruído não existia, e o script reportava A(0,99) como se 99% fosse
    mensurável numa fonte cujo τ assentado oscila 1,4%.

Nada aqui toca rede nem lê mart.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import pytest

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "scripts"))

import analise_cauda_de_reporte as ac  # noqa: E402


def _tau(valores: list[float]) -> pd.DataFrame:
    """τ por idade, com idade 0 na primeira posição da lista."""
    return pd.DataFrame({"idade": range(len(valores)), "tau": valores})


# ---------------------------------------------------------------------------
# U(θ, H): a conta que decide se a previsão serve para alguma coisa
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("a,h,esperado", [
    (0, 3, 1.0),        # sem defasagem, todo o horizonte é futuro
    (1, 3, 2 / 3),
    (2, 3, 1 / 3),
    (3, 3, 0.0),        # H == A: a previsão inteira já aconteceu
    (4, 3, 0.0),        # H < A: idem, e não pode dar negativo
    (1, 1, 0.0),
    (0, 1, 1.0),
])
def test_fracao_util(a, h, esperado):
    assert ac.fracao_util(a, h) == pytest.approx(esperado)


def test_fracao_util_nunca_e_negativa():
    """Sem o `max(0, ...)` a tabela sairia com horizonte útil negativo."""
    assert ac.fracao_util(99, 3) == 0.0


def test_criterio_inatingivel_zera_o_horizonte():
    """A(θ) = None é 'nunca completa' — e nunca completa é horizonte nenhum."""
    assert ac.fracao_util(None, 12) == 0.0


def test_u_e_nao_crescente_em_a():
    """O coração da tensão: mais defasagem nunca devolve mais horizonte."""
    for h in (1, 3, 6, 12):
        us = [ac.fracao_util(a, h) for a in range(0, h + 3)]
        assert us == sorted(us, reverse=True), (h, us)


# ---------------------------------------------------------------------------
# A(θ): tem que exigir que τ FIQUE acima, não que encoste uma vez
# ---------------------------------------------------------------------------

def test_defasagem_encontra_a_idade_de_assentamento():
    t = _tau([0.84, 0.93, 0.96, 0.97, 0.99, 1.00, 1.00, 1.00])
    assert ac.defasagem(t, 0.90) == 1
    assert ac.defasagem(t, 0.95) == 2
    assert ac.defasagem(t, 0.99) == 4


def test_defasagem_ignora_cruzamento_isolado():
    """τ encosta em 0,95 na idade 1 e cai de novo. A resposta é 3, não 1."""
    t = _tau([0.80, 0.96, 0.90, 0.99, 1.00, 1.00])
    assert ac.defasagem(t, 0.95) == 3, (
        "pegar o primeiro cruzamento devolve defasagem otimista, e defasagem "
        "otimista vira horizonte útil que não existe"
    )


def test_defasagem_devolve_none_quando_nunca_assenta():
    t = _tau([0.5, 0.6, 0.7, 0.8])
    assert ac.defasagem(t, 0.99) is None


def test_defasagem_e_nao_decrescente_em_theta():
    """Monotonicidade de A(θ) — a propriedade de que a tensão depende."""
    t = _tau([0.84, 0.93, 0.96, 0.97, 0.99, 1.00, 1.00, 1.00])
    anteriores = [ac.defasagem(t, c) for c in (0.80, 0.90, 0.95, 0.99)]
    finitos = [a for a in anteriores if a is not None]
    assert finitos == sorted(finitos), anteriores


def test_defasagem_zero_quando_ja_esta_completa():
    t = _tau([1.00, 1.00, 1.00, 1.00])
    assert ac.defasagem(t, 0.99) == 0


# ---------------------------------------------------------------------------
# τ: sazonalidade não pode ser lida como incompletude
# ---------------------------------------------------------------------------

def _serie_sazonal(anos: int, base: float, amplitude: float,
                   cauda: dict[int, float] | None = None) -> pd.Series:
    """Série mensal perfeitamente sazonal, opcionalmente com cauda no fim."""
    import math
    v, i = [], 0
    for _ in range(anos):
        for m in range(12):
            v.append(base + amplitude * math.sin(2 * math.pi * m / 12))
            i += 1
    s = pd.Series(v, index=[f"{2000 + k // 12}-{k % 12 + 1:02d}"
                            for k in range(len(v))])
    if cauda:
        for idade, fator in cauda.items():
            s.iloc[len(s) - 1 - idade] *= fator
    return s


def test_serie_sazonal_sem_cauda_nao_produz_incompletude():
    """O defeito original: sazonalidade lida como cauda de reporte."""
    s = _serie_sazonal(anos=5, base=1000, amplitude=600)
    tau, _ = ac._completude(s, 12)
    assert (tau.tau > 0.999).all(), (
        "série perfeitamente sazonal e completa não pode ter τ < 1 — foi assim "
        "que a baixa estação da dengue virou 'cauda infinita'\n"
        + tau.to_string()
    )


def test_cauda_real_aparece_mesmo_sob_sazonalidade_forte():
    s = _serie_sazonal(anos=5, base=1000, amplitude=600,
                       cauda={0: 0.80, 1: 0.93})
    tau, _ = ac._completude(s, 12)
    assert tau.loc[tau.idade == 0, "tau"].iloc[0] == pytest.approx(0.80, abs=0.01)
    assert tau.loc[tau.idade == 1, "tau"].iloc[0] == pytest.approx(0.93, abs=0.01)
    assert ac.defasagem(tau, 0.95) == 2


def test_piso_de_ruido_de_serie_limpa_e_praticamente_um():
    s = _serie_sazonal(anos=5, base=1000, amplitude=600, cauda={0: 0.80})
    tau, _ = ac._completude(s, 12)
    assert tau.attrs["piso_de_ruido"] > 0.99


def test_piso_de_ruido_cai_quando_a_serie_oscila_entre_anos():
    """Série cuja amplitude muda de ano para ano — o caso do InfoDengue."""
    import math
    v = []
    for ano, fator in enumerate([1.0, 1.8, 0.6, 1.4, 0.9]):
        for m in range(12):
            v.append(fator * (1000 + 600 * math.sin(2 * math.pi * m / 12)))
    s = pd.Series(v, index=[f"{2000 + k // 12}-{k % 12 + 1:02d}"
                            for k in range(len(v))])
    tau, _ = ac._completude(s, 12)
    assert tau.attrs["piso_de_ruido"] < 0.9, (
        "com base ano a ano instável, o piso tem que denunciar que nenhum "
        "critério usual é mensurável — senão o script reporta A(0,99) inventado"
    )


def test_serie_curta_demais_recusa_em_vez_de_inventar():
    s = pd.Series(range(20), index=[str(i) for i in range(20)])
    with pytest.raises(ValueError, match="curta demais"):
        ac._completude(s, 12)
