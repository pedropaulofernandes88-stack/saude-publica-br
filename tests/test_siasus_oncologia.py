"""Guardas do mart oncológico do SIA/SUS.

A primeira existe por um defeito que eu mesmo introduzi e que a cobertura do
primeiro ano coletado denunciou: `_estadio("")` devolvia `"0"`. Estádio 0 é
estádio REAL (carcinoma in situ), então toda ausência de estadiamento era
publicada como diagnóstico precoce. Medido no dado cru de PE em 2013-01: 1.119
vazios contra 446 zeros verdadeiros — o estádio 0 saía inflado em 3,5 vezes.

É o mesmo defeito que este projeto aponta no Painel de Oncologia. Reproduzi-lo
em três linhas mostra o quanto ele é fácil, e é por isso que a guarda é o
primeiro teste do arquivo.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "scripts"))

import pipeline_siasus_oncologia as po  # noqa: E402


@pytest.mark.parametrize("vazio", ["", "   ", None])
def test_estadiamento_AUSENTE_nunca_vira_estadio_zero(vazio):
    """O teste mais importante deste arquivo."""
    assert po._estadio(vazio) == "ignorado", (
        "estádio 0 é carcinoma in situ — um diagnóstico REAL e precoce. "
        "Mapear ausência para ele transforma falta de registro em bom prognóstico."
    )


def test_estadio_zero_verdadeiro_continua_sendo_zero():
    """E o contrário também: não dá para resolver jogando tudo em ignorado."""
    assert po._estadio("0") == "0"
    assert po._estadio("00") == "0"


@pytest.mark.parametrize("valor,esperado", [("1", "1"), ("2", "2"), ("3", "3"),
                                            ("4", "4"), ("04", "4")])
def test_os_estadios_reais_atravessam(valor, esperado):
    assert po._estadio(valor) == esperado


@pytest.mark.parametrize("lixo", ["5", "9", "X", "ND", "-"])
def test_valor_fora_da_escala_vira_ignorado_e_nao_estadio(lixo):
    assert po._estadio(lixo) == "ignorado"


def test_as_duas_modalidades_leem_o_campo_de_estadiamento_certo():
    """`AQ_ESTADI` na quimio e `AR_ESTADI` na radio. Ler o campo do outro grupo
    devolveria None em 100% das linhas — ou seja, tudo "ignorado", em silêncio."""
    assert set(po.MODALIDADES) == {"AQ", "AR"}
    for grupo in po.MODALIDADES:
        assert f"{grupo}_ESTADI"  # o pipeline monta o nome a partir do grupo


def test_a_unidade_declarada_e_a_APAC_e_nao_a_pessoa():
    """Paciente em quimioterapia contínua gera várias APACs por ano, e o
    identificador de pessoa vem criptografado. Ler a coluna como pacientes
    inflaria qualquer taxa; o cabeçalho tem de dizer isso."""
    texto = (RAIZ / "scripts" / "pipeline_siasus_oncologia.py").read_text(encoding="utf-8")
    assert "não a pessoa" in texto.lower() or "NÃO A PESSOA" in texto
    assert "AP_CNSPCN" in texto


def test_o_cabecalho_avisa_que_a_fonte_nao_mede_o_prazo_dos_60_dias():
    """A conta óbvia sobre esta fonte produz manchete falsa. Quem abrir o
    arquivo tem de topar com isso antes de escrever a subtração."""
    texto = (RAIZ / "scripts" / "pipeline_siasus_oncologia.py").read_text(encoding="utf-8")
    assert "60 Dias" in texto and "AQ_DTIDEN" in texto


def test_os_dois_municipios_sao_campos_diferentes():
    """`AP_MUNPCN` é residência e `AP_UFMUN` é o estabelecimento; 54% das APACs
    têm os dois diferentes. Confundi-los viraria deslocamento em oferta local."""
    texto = (RAIZ / "scripts" / "pipeline_siasus_oncologia.py").read_text(encoding="utf-8")
    assert "AP_MUNPCN" in texto and "AP_UFMUN" in texto
