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
    FAIXA_IGNORADA,
    PRAZO_LEGAL_DIAS,
    SENTINELA_TEMPO,
    Estadiamento,
    _faixa,
    _tempo,
    agregar,
    guarda_nao_encolher,
    guardas,
    guardas_estadiamento,
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


# ── estadiamento: a ausência é maioria, e não pode virar filtro ─────────────
#
# O campo ESTADIAM é 51,0% '9', 19,0% '5' e 5,0% vazio em POBR2023 — só 24,9%
# dos casos trazem estádio 0–4. Um mart que já chegasse com "avançado sim/não"
# publicaria a completude do preenchimento como se fosse estágio da doença.

def caso_est(**kw):
    base = {"MUN_RESID": "431630", "ANO_DIAGN": "2024", "TRATAMENTO": "1",
            "TEMPO_TRAT": "+0030", "DIAG_DETH": "C50", "IDADE": "070",
            "ESTADIAM": "2"}
    base.update(kw)
    return base


@pytest.mark.parametrize(("valor", "esperado"), [
    ("000", "0-4"), ("004", "0-4"), ("005", "5-14"), ("014", "5-14"),
    ("015", "15-29"), ("029", "15-29"), ("030", "30-44"), ("044", "30-44"),
    ("045", "45-59"), ("059", "45-59"), ("060", "60-74"), ("074", "60-74"),
    ("075", "75+"), ("070", "60-74"), ("130", "75+"),
])
def test_faixa_etaria_respeita_os_limites_do_projeto(valor, esperado):
    assert _faixa(valor) == esperado


@pytest.mark.parametrize("valor", ["", "   ", None, "abc", "999", "131"])
def test_idade_ilegivel_vira_categoria_e_nao_descarte(valor):
    """Idade impossível não some: vira faixa própria, como `sem_tratamento`."""
    assert _faixa(valor) == FAIXA_IGNORADA


def test_estadiamento_guarda_o_valor_bruto_sem_traduzir():
    """'9' e '' são preservados. Traduzir aqui esconderia a completude."""
    est = Estadiamento()
    for v in ("0", "4", "5", "9", ""):
        est(caso_est(ESTADIAM=v))
    df = est.df(2024)
    assert sorted(df["estadiam"]) == ["", "0", "4", "5", "9"]
    assert df["casos"].sum() == 5


def test_estadiamento_agrega_pela_chave_completa():
    est = Estadiamento()
    est(caso_est())
    est(caso_est())
    est(caso_est(DIAG_DETH="C53"))
    est(caso_est(IDADE="030"))
    df = est.df(2024)
    assert len(df) == 3
    assert int(df[df["sitio"] == "C50"]["casos"].max()) == 2


def test_sitio_vem_do_cid_truncado_em_tres():
    est = Estadiamento()
    est(caso_est(DIAG_DETH="C50.9"))
    assert est.df(2024)["sitio"].tolist() == ["C50"]


def test_registro_sem_sitio_e_descartado_e_contado():
    """Descarte que ninguém conta é o modo silencioso de encolher um mart."""
    est = Estadiamento()
    est(caso_est())
    est(caso_est(DIAG_DETH=""))
    df = est.df(2024)
    assert int(df["casos"].sum()) == 1
    assert est.descartados == 1
    assert est.lidos == 2


def test_guarda_pega_registro_que_sumiu_sem_ser_descartado():
    est = Estadiamento()
    est(caso_est())
    est.lidos += 3          # simula três registros perdidos por um `continue`
    with pytest.raises(SystemExit, match="mas leu"):
        est.df(2024)


def test_ano_divergente_aborta_tambem_no_estadiamento():
    est = Estadiamento()
    est(caso_est(ANO_DIAGN="2023"))
    with pytest.raises(SystemExit, match="ANO_DIAGN diferente"):
        est.df(2024)


def test_agregar_entrega_ao_coletor_ate_o_que_ele_proprio_descarta():
    """O gancho existe para ler o arquivo UMA vez; ele não pode filtrar antes.

    `agregar` descarta município inválido. Se o descarte acontecesse antes do
    gancho, o mart de estadiamento herdaria silenciosamente o critério do outro
    — e os dois deixariam de ser auditáveis separadamente.
    """
    vistos = []
    agregar([caso_est(), caso_est(MUN_RESID="XXX")], 2024, tambem=vistos.append)
    assert len(vistos) == 2


def test_guarda_reprova_estadiamento_com_mais_casos_que_o_prazo():
    prazo = agregar([caso_est()], 2024)
    est = Estadiamento()
    est(caso_est())
    est(caso_est())
    with pytest.raises(SystemExit, match="não pode ter mais"):
        guardas_estadiamento(est.df(2024), prazo)


def test_guarda_reprova_faixa_etaria_desconhecida():
    prazo = agregar([caso_est()], 2024)
    est = Estadiamento()
    est(caso_est())
    ruim = est.df(2024)
    ruim.loc[0, "faixa_etaria"] = "18-65"
    with pytest.raises(SystemExit, match="faixas etárias desconhecidas"):
        guardas_estadiamento(ruim, prazo)


def test_guarda_reprova_estadiamento_vazio():
    with pytest.raises(SystemExit, match="estadiamento vazia"):
        guardas_estadiamento(pd.DataFrame(), pd.DataFrame({"casos": [1]}))


# ── a gravação é sobrescrita, e sobrescrita encolhe ─────────────────────────

def test_guarda_recusa_encolher_o_mart(tmp_path):
    """`--anos 2023` reduzia um mart de 14 anos a um, com exit 0."""
    destino = tmp_path / "m.parquet"
    pd.DataFrame({"ano": [2022, 2023, 2024], "casos": [1, 1, 1]}).to_parquet(destino)
    with pytest.raises(SystemExit, match=r"perderia \[2022, 2024\]"):
        guarda_nao_encolher(pd.DataFrame({"ano": [2023], "casos": [1]}), destino, False)


def test_guarda_deixa_passar_o_recorte_declarado(tmp_path):
    destino = tmp_path / "m.parquet"
    pd.DataFrame({"ano": [2022, 2023], "casos": [1, 1]}).to_parquet(destino)
    guarda_nao_encolher(pd.DataFrame({"ano": [2023], "casos": [1]}), destino, True)


def test_guarda_deixa_passar_quando_nao_perde_ano(tmp_path):
    destino = tmp_path / "m.parquet"
    pd.DataFrame({"ano": [2022], "casos": [1]}).to_parquet(destino)
    guarda_nao_encolher(pd.DataFrame({"ano": [2022, 2023], "casos": [1, 1]}), destino, False)


def test_guarda_nao_reprova_primeira_gravacao(tmp_path):
    guarda_nao_encolher(pd.DataFrame({"ano": [2023], "casos": [1]}),
                        tmp_path / "nao_existe.parquet", False)
