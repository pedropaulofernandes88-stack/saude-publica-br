"""
Painel Oncologia: 99999 não é um tempo, e "sem tratamento" não é um filtro.

A fonte codifica ausência de tratamento como `TEMPO_TRAT = 99999`. Tratar esse
número como duração publica duas mentiras de uma vez — uma mediana de 273 anos,
e um percentual dentro do prazo legal calculado sobre um denominador que inclui
quem nunca iniciou tratamento. Foi o que a primeira leitura do arquivo real
produziu (24,2% contra 54,4%), e o erro empurra o indicador para baixo, onde
parece notícia ruim plausível.

Executar: .venv311/Scripts/python -m pytest tests/test_painel_oncologia.py
"""
from __future__ import annotations

import pandas as pd
import pytest

from scripts.pipeline_painel_oncologia import (
    PRAZO_LEGAL_DIAS,
    SENTINELA_TEMPO,
    _tempo,
    agregar,
    guardas,
)


def caso(**kw):
    base = {"MUN_RESID": "431630", "ANO_DIAGN": "2024",
            "TRATAMENTO": "1", "TEMPO_TRAT": "+0030"}
    base.update(kw)
    return base


SEM_TRAT = {"TRATAMENTO": "5", "TEMPO_TRAT": "99999"}


# ── a sentinela ────────────────────────────────────────────────────────────

def test_sentinela_nao_e_duracao():
    """O teste que impede a mediana de 273 anos."""
    assert _tempo("99999") is None
    assert _tempo("+99999") is None
    assert _tempo(SENTINELA_TEMPO) is None


def test_vazio_e_nao_numerico_nao_viram_zero():
    for v in ("", "   ", None, "abc", "+"):
        assert _tempo(v) is None, f"{v!r} deveria ser ausência, não zero"


def test_duracao_normal_e_lida_com_o_sinal():
    assert _tempo("+0030") == 30
    assert _tempo("0000") == 0
    assert _tempo("-0090") == -90


# ── o denominador ──────────────────────────────────────────────────────────

def test_sem_tratamento_sai_do_denominador_do_prazo_e_vira_coluna():
    """A regra central: ausência vira número próprio, não exclusão silenciosa."""
    d = agregar([caso(TEMPO_TRAT="+0030"), caso(**SEM_TRAT), caso(**SEM_TRAT)], 2024).iloc[0]
    assert d["casos"] == 3
    assert d["sem_tratamento"] == 2
    assert d["com_tratamento"] == 1
    assert d["pct_ate_60_dias"] == 100.0, "o prazo é medido só sobre quem tratou"
    assert d["pct_sem_tratamento"] == pytest.approx(66.7, abs=0.1)


def test_o_denominador_errado_seria_metade_do_certo():
    """Reproduz o erro real: 1 no prazo entre 2 tratados é 50%, não 25%."""
    d = agregar([caso(TEMPO_TRAT="+0030"), caso(TEMPO_TRAT="+0090"),
                 caso(**SEM_TRAT), caso(**SEM_TRAT)], 2024).iloc[0]
    assert d["pct_ate_60_dias"] == 50.0
    assert d["casos"] == 4 and d["com_tratamento"] == 2


def test_tratamento_5_conta_como_sem_tratamento_mesmo_com_tempo_valido():
    """Se os dois campos discordarem, o código de tratamento manda."""
    d = agregar([caso(TRATAMENTO="5", TEMPO_TRAT="+0010")], 2024).iloc[0]
    assert d["sem_tratamento"] == 1 and d["com_tratamento"] == 0


# ── o prazo legal ──────────────────────────────────────────────────────────

def test_o_limiar_e_exatamente_o_da_lei():
    """60 dias entra; 61 não. O corte é a Lei 12.732/2012, não arredondamento."""
    d = agregar([caso(TEMPO_TRAT=f"+{PRAZO_LEGAL_DIAS:04d}"),
                 caso(TEMPO_TRAT=f"+{PRAZO_LEGAL_DIAS + 1:04d}")], 2024).iloc[0]
    assert d["ate_60_dias"] == 1 and d["acima_60_dias"] == 1


def test_mesmo_dia_conta_como_dentro_do_prazo():
    d = agregar([caso(TEMPO_TRAT="0000")], 2024).iloc[0]
    assert d["ate_60_dias"] == 1


def test_tempo_negativo_e_contado_e_nao_entra_nas_faixas():
    """Tratar antes de diagnosticar é impossível: vai para coluna própria."""
    d = agregar([caso(TEMPO_TRAT="-0090"), caso(TEMPO_TRAT="+0030")], 2024).iloc[0]
    assert d["tempo_negativo"] == 1
    assert d["com_tratamento"] == 2
    assert d["ate_60_dias"] == 1 and d["acima_60_dias"] == 0
    assert d["pct_ate_60_dias"] == 100.0, "o impossível não conta como fora do prazo"


# ── grão e chaves ──────────────────────────────────────────────────────────

def test_agrega_por_municipio_de_residencia():
    df = agregar([caso(MUN_RESID="431630"), caso(MUN_RESID="431750")], 2024)
    assert set(df["municipio_cod"]) == {"431630", "431750"}


def test_codigo_de_municipio_invalido_e_descartado_sem_derrubar():
    df = agregar([caso(MUN_RESID="43163"), caso(MUN_RESID="abcdef"),
                  caso(MUN_RESID=""), caso(MUN_RESID="431630")], 2024)
    assert len(df) == 1 and df.iloc[0]["casos"] == 1


def test_ano_divergente_do_arquivo_aborta():
    """Arquivo anual com registro de outro ano estaria misturando séries."""
    with pytest.raises(SystemExit, match="ANO_DIAGN"):
        agregar([caso(ANO_DIAGN="2019")], 2024)


# ── guardas ────────────────────────────────────────────────────────────────

def test_guardas_passam_num_recorte_sao():
    """A metade que nenhuma guarda deste projeto pode ficar sem: dizer SIM."""
    guardas(agregar([caso(TEMPO_TRAT="+0030"), caso(**SEM_TRAT)], 2024))


def test_guarda_pega_sentinela_que_virou_duracao():
    """Se 99999 escapar para o cálculo, a mediana denuncia."""
    df = agregar([caso(TEMPO_TRAT="+0030")], 2024)
    df.loc[0, "mediana_dias"] = float(SENTINELA_TEMPO)
    with pytest.raises(SystemExit, match="sentinela"):
        guardas(df)


def test_espera_longa_de_verdade_nao_e_reprovada():
    """Falso positivo custa o mesmo que falso negativo.

    A primeira versão da guarda reprovava mediana acima de 10 anos e barrava
    12 município-anos REAIS: diagnóstico em 2013, tratamento em 2023, com as
    duas datas conferindo. Dez anos de espera é achado, não corrupção.
    """
    df = agregar([caso(TEMPO_TRAT="+3713")], 2024)
    assert df.iloc[0]["mediana_dias"] == 3713
    guardas(df)


def test_guarda_pega_contas_que_nao_fecham():
    df = agregar([caso(TEMPO_TRAT="+0030")], 2024)
    df.loc[0, "casos"] = 99
    with pytest.raises(SystemExit, match="≠ casos"):
        guardas(df)


def test_guarda_pega_percentual_fora_de_0_100():
    df = agregar([caso(TEMPO_TRAT="+0030")], 2024)
    df.loc[0, "pct_ate_60_dias"] = 130.0
    with pytest.raises(SystemExit, match="fora de 0"):
        guardas(df)


def test_guarda_pega_faixas_que_nao_somam_com_tratamento():
    df = agregar([caso(TEMPO_TRAT="+0030")], 2024)
    df.loc[0, "acima_60_dias"] = 7
    with pytest.raises(SystemExit, match="faixas de prazo"):
        guardas(df)


def test_guarda_reprova_agregacao_vazia():
    with pytest.raises(SystemExit, match="vazia"):
        guardas(pd.DataFrame())
