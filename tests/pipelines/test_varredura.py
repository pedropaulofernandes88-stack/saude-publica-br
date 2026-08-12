"""
Testes da varredura de linhas orfas (scripts/_varredura.py).

Os pipelines publicam com upsert, que nunca remove o que deixou de existir. Em
12/08/2026 havia 1.830 linhas orfas publicadas -- descobertas por acidente. A
varredura fecha isso, mas ela APAGA dado publicado, entao a logica que decide o
que e orfa precisa de rede de seguranca:

  - chave errada faz toda a tabela parecer orfa (por isso LIMITE_ORFAS);
  - comparacao de tipos frouxa faz linha valida parecer orfa (municipio_cod
    '350000' vindo como int do parquet e como str da API).
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))

from _varredura import LIMITE_ORFAS, calcular_orfas  # noqa: E402

pytestmark = pytest.mark.unit

CHAVES = ["cnes", "ano", "cid3"]


def _df(tuplas):
    return pd.DataFrame(tuplas, columns=CHAVES)


def test_nada_a_remover_quando_o_conjunto_e_o_mesmo():
    pub = _df([("111", 2024, "I10"), ("222", 2024, "J44")])
    assert calcular_orfas(pub, pub, CHAVES).empty


def test_detecta_o_que_saiu_do_calculo():
    pub = _df([("111", 2024, "I10"), ("222", 2024, "J44"), ("333", 2024, "E10")])
    novas = _df([("111", 2024, "I10"), ("222", 2024, "J44")])
    orfas = calcular_orfas(pub, novas, CHAVES)
    assert len(orfas) == 1
    assert orfas.iloc[0].tolist() == ["333", "2024", "E10"]


def test_linha_nova_nao_conta_como_orfa():
    """Chave que existe no calculo e nao na API e insercao, nao remocao."""
    pub = _df([("111", 2024, "I10")])
    novas = _df([("111", 2024, "I10"), ("999", 2024, "Z00")])
    assert calcular_orfas(pub, novas, CHAVES).empty


def test_comparacao_tolera_tipos_diferentes():
    """O parquet devolve ano como int64; a API devolve como str. Nao pode divergir."""
    pub = pd.DataFrame([{"cnes": "111", "ano": "2024", "cid3": "I10"}])
    novas = pd.DataFrame([{"cnes": 111, "ano": 2024, "cid3": "I10"}])
    # cnes 111 vs "111": a coercao para str resolve o ano, mas nao um zero a esquerda
    orfas = calcular_orfas(pub, novas, CHAVES)
    assert orfas.empty, "int 2024 e str '2024' tem de casar"


def test_zero_a_esquerda_no_cnes_e_divergencia_real():
    """Guarda documentando um risco: '0027014' != 27014 mesmo apos str().

    Se algum dia um pipeline passar o CNES como int, a varredura veria tudo como
    orfa -- e e por isso que LIMITE_ORFAS existe.
    """
    pub = pd.DataFrame([{"cnes": "0027014", "ano": 2024, "cid3": "I10"}])
    novas = pd.DataFrame([{"cnes": 27014, "ano": 2024, "cid3": "I10"}])
    assert len(calcular_orfas(pub, novas, CHAVES)) == 1


def test_duplicatas_no_calculo_nao_inflam_o_resultado():
    pub = _df([("111", 2024, "I10")])
    novas = _df([("111", 2024, "I10"), ("111", 2024, "I10")])
    assert calcular_orfas(pub, novas, CHAVES).empty


def test_publicadas_vazio_devolve_vazio():
    assert calcular_orfas(_df([]), _df([("111", 2024, "I10")]), CHAVES).empty


def test_calculo_vazio_marca_tudo_como_orfa():
    """Caso extremo: e justamente o que a trava de fracao deve barrar la em cima."""
    pub = _df([("111", 2024, "I10"), ("222", 2024, "J44")])
    orfas = calcular_orfas(pub, _df([]), CHAVES)
    assert len(orfas) == 2
    assert len(orfas) / len(pub) > LIMITE_ORFAS


def test_limite_de_seguranca_e_conservador():
    """Orfas reais sao punhado: as 1.829 do mart_los_hospital eram 0,7%."""
    assert 0 < LIMITE_ORFAS <= 0.25
    assert 1829 / 248138 < LIMITE_ORFAS
