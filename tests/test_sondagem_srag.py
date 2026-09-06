"""
O portão de prontidão do SRAG sabe dizer sim, e não só não.

Uma guarda que nunca foi vista APROVANDO é indistinguível de uma guarda
quebrada que reprova sempre — e este projeto já encontrou 14 delas assim. O
portão real reprova hoje (portal em 500, `dt_notific` corrompido), o que prova
metade. Estes testes provam a outra metade em cima de `veredito()`, que é puro
de propósito: recebe as medidas e devolve as reprovações, sem tocar a rede.

Executar: .venv311/Scripts/python -m pytest tests/test_sondagem_srag.py
"""
from __future__ import annotations

import pytest

from scripts.sondar_srag import (
    MAX_PCT_INVERTIDOS,
    MIN_MESES_DISTINTOS,
    avaliar,
    veredito,
)

PORTAL_OK = {"https://opendatasus.saude.gov.br/": 200}
PORTAL_FORA = {"https://opendatasus.saude.gov.br/": 500}


def medidas(meses_notif: int, pct_invertidos: float) -> dict:
    return {
        "registros_amostrados": 8000,
        "meses_distintos_dt_notific": meses_notif,
        "meses_distintos_dt_sin_pri": 65,
        "pct_notificacao_antes_do_sintoma": pct_invertidos,
        "meses_dt_notific": [f"2020-{i:02d}" for i in range(1, min(meses_notif, 12) + 1)],
    }


def test_fonte_sa_passa_no_portao():
    """O caso que importa: nada reprova quando a fonte está boa."""
    assert veredito(PORTAL_OK, 4_000_000, medidas(72, 0.3)) == []


def test_portal_fora_do_ar_reprova():
    falhas = veredito(PORTAL_FORA, 4_000_000, medidas(72, 0.3))
    assert len(falhas) == 1
    assert "rota CSV" in falhas[0]


def test_data_de_notificacao_curta_demais_reprova():
    """Foi o que a fonte real mostrou: 8 meses distintos em 8.000 registros."""
    falhas = veredito(PORTAL_OK, 4_000_000, medidas(8, 0.3))
    assert len(falhas) == 1
    assert "dt_notific" in falhas[0]
    assert "anomes_notific" in falhas[0], "a reprovação tem de dizer POR QUE isso importa"


def test_notificacao_antes_do_sintoma_reprova():
    falhas = veredito(PORTAL_OK, 4_000_000, medidas(72, 98.2))
    assert len(falhas) == 1
    assert "impossível" in falhas[0]


def test_as_tres_reprovacoes_sao_independentes():
    """Uma falha não pode mascarar as outras: o relatório precisa listar todas."""
    falhas = veredito(PORTAL_FORA, 4_000_000, medidas(8, 98.2))
    assert len(falhas) == 3


@pytest.mark.parametrize("meses", [MIN_MESES_DISTINTOS - 1, MIN_MESES_DISTINTOS])
def test_o_limiar_de_meses_e_o_declarado(meses):
    """O corte está onde a constante diz — não uma unidade ao lado."""
    reprovou = any("dt_notific" in f for f in veredito(PORTAL_OK, 1, medidas(meses, 0.0)))
    assert reprovou == (meses < MIN_MESES_DISTINTOS)


@pytest.mark.parametrize("pct", [MAX_PCT_INVERTIDOS, MAX_PCT_INVERTIDOS + 0.1])
def test_o_limiar_de_inversao_e_o_declarado(pct):
    reprovou = any("impossível" in f for f in veredito(PORTAL_OK, 1, medidas(72, pct)))
    assert reprovou == (pct > MAX_PCT_INVERTIDOS)


def test_avaliar_conta_inversao_de_data_como_a_fonte_real():
    """`avaliar` é o que transforma registros crus nas medidas do veredito."""
    regs = [
        # notificado antes de adoecer — impossível, e é o padrão da fonte real
        {"dt_notific": "2018-12-30", "dt_sin_pri": "2019-01-06"},
        {"dt_notific": "2020-12-31", "dt_sin_pri": "2021-01-02"},
        # são
        {"dt_notific": "2021-03-10", "dt_sin_pri": "2021-03-05"},
        {"dt_notific": "2021-04-10", "dt_sin_pri": "2021-04-01"},
    ]
    m = avaliar(regs)
    assert m["pct_notificacao_antes_do_sintoma"] == 50.0
    assert m["meses_distintos_dt_notific"] == 4
    assert m["meses_distintos_dt_sin_pri"] == 4


def test_registro_sem_data_nao_vira_zero_nem_derruba():
    """Campo ausente é ausente: sai da comparação, não entra como se fosse 0."""
    m = avaliar([
        {"dt_notific": None, "dt_sin_pri": "2021-03-05"},
        {"dt_notific": "2021-03-10", "dt_sin_pri": None},
        {"dt_notific": "2021-03-10", "dt_sin_pri": "2021-03-05"},
    ])
    # só UM registro tem as duas datas, e nele a ordem está certa
    assert m["pct_notificacao_antes_do_sintoma"] == 0.0
    assert m["meses_distintos_dt_notific"] == 1
