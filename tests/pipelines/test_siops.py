"""
Testes do parser do SIOPS (scripts/pipeline_siops.py).

O SIOPS entra por raspagem de TABNET — um CGI dos anos 2000 que devolve texto
pré-formatado em ISO-8859-1. Parser de texto de terceiro é exatamente o tipo de
código que quebra em silêncio quando a fonte muda de formato, então a régua aqui
vale mais do que na leitura de um DBF com schema.

Casos derivados de respostas reais da fonte.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))

from pipeline_siops import INDICADORES, _numero, parse_prn  # noqa: E402

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# _numero — o TABNET usa formato brasileiro
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("txt,esperado", [
    ("1012,63", 1012.63),
    ("1.882,07", 1882.07),
    ("1.234.567,89", 1234567.89),
    ("0,00", 0.0),
    ("15", 15.0),
    ("-1.500,50", -1500.50),
])
def test_numero_no_formato_brasileiro(txt, esperado):
    assert _numero(txt) == pytest.approx(esperado)


@pytest.mark.parametrize("txt", ["", "   ", "-", "...", None, "abc"])
def test_ausente_vira_none_e_nao_zero(txt):
    """'-' no TABNET significa NÃO DECLARADO. Virar 0,0 afirmaria gasto zero."""
    assert _numero(txt) is None


# ---------------------------------------------------------------------------
# parse_prn
# ---------------------------------------------------------------------------

CORPO_REAL = '''TabNet Win32 3.0: Indicadores Municipais S&atilde;o Paulo
Per&iacute;odo: 2024
"Munic&iacute;pios";"D.R.Pr&oacute;prios em Sa&uacute;de/Hab"
"350010 Adamantina";1012,63
"350020 Adolfo";1882,07
"350030 Agua&iacute;";932,83
"350040 &Aacute;guas da Prata";1366,80
"350045 Municipio Sem Dado";-
"Total";1234,56
'''


def test_extrai_codigo_e_valor():
    d = parse_prn(CORPO_REAL)
    assert d["350010"] == pytest.approx(1012.63)
    assert d["350020"] == pytest.approx(1882.07)
    assert d["350040"] == pytest.approx(1366.80)


def test_acentos_em_entidade_html_nao_atrapalham():
    d = parse_prn(CORPO_REAL)
    assert "350030" in d and d["350030"] == pytest.approx(932.83)


def test_linha_total_nao_vira_municipio():
    """'Total' fecha a tabela do TABNET; contá-lo criaria um município fantasma."""
    d = parse_prn(CORPO_REAL)
    assert len(d) == 5
    assert all(c.isdigit() and len(c) == 6 for c in d)


def test_municipio_sem_declaracao_fica_none():
    d = parse_prn(CORPO_REAL)
    assert "350045" in d and d["350045"] is None


def test_cabecalho_e_ruido_sao_ignorados():
    assert parse_prn("TabNet Win32 3.0\nPer&iacute;odo: 2024\n<b>nada</b>\n") == {}


def test_corpo_vazio_nao_estoura():
    assert parse_prn("") == {}


def test_codigo_de_municipio_tem_seis_digitos():
    """O projeto inteiro usa IBGE de 6 dígitos; 7 aqui quebraria todo join."""
    for cod in parse_prn(CORPO_REAL):
        assert len(cod) == 6


# ---------------------------------------------------------------------------
# Configuração dos indicadores
# ---------------------------------------------------------------------------

def test_indicadores_mapeiam_para_colunas_distintas():
    assert len(set(INDICADORES.values())) == len(INDICADORES)


def test_indicador_do_minimo_constitucional_esta_presente():
    """Sem a EC 29 o mart perde a única leitura normativa que o SIOPS oferece."""
    assert "3.2_%R.Próprios_em_Saúde-EC_29" in INDICADORES
    assert INDICADORES["3.2_%R.Próprios_em_Saúde-EC_29"] == "pct_receita_propria_saude"


def test_subfuncoes_ficaram_de_fora():
    """2.20/2.21 existem no .def mas vêm vazios de 2016 em diante.

    Conferido em AC: 22 de 23 municípios preenchidos em 2015, ZERO em 2020 e em
    2024. Mantê-los custaria 104 requisições por rodada num CGI antigo para
    devolver coluna nula. Se um dia voltarem a ser populados, este teste é o
    lembrete de que a ausência foi medida, não esquecida.
    """
    assert not [k for k in INDICADORES if "Aten" in k or "SUBFUN" in k.upper()]
