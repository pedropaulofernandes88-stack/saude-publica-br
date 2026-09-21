"""O manifesto declara o PERÍODO de cada tabela, e a lista de nomes envelhece.

`_publicacao._competencias` procura o eixo de tempo por uma tupla de nomes de
coluna. Isso funciona e é barato, mas falha do jeito mais silencioso possível:
tabela nova cujo eixo se chama outra coisa declara `competencia_min = null`,
passa em toda guarda de forma, e some da completude histórica sem aviso.

Aconteceu duas vezes antes de existir este arquivo:

* `mart_cnes_municipio` tem `ano_referencia` e declarava período nenhum;
* `mart_rhc_caso` e `mart_rhc_cobertura` têm `ano_primeira_consulta`, cobrem
  2013–2023, e foram publicados em 2026-09-21 declarando período nenhum — no
  MESMO dia em que a coluna `ano_incompleto` foi criada para carimbar cauda de
  reporte. A ressalva estava na linha e o período não estava no manifesto.

O teste que importa é o último: ele não exercita função com dado sintético, ele
lê o MANIFESTO PUBLICADO e reprova tabela que tem eixo de tempo e não o declara.
É a única forma de pegar a terceira ocorrência, que virá com um nome que
ninguém previu aqui.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd
import pytest

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "scripts"))

from _publicacao import _competencias  # noqa: E402

# Nomes que, se aparecerem como coluna, SÃO eixo de tempo da tabela. Não é a
# mesma lista de `_competencias`: esta é a do teste, e a divergência entre as
# duas é justamente o defeito que se quer pegar.
COLUNAS_DE_TEMPO = frozenset({
    "ano", "ano_mes", "ano_epi", "competencia", "ano_mes_previsto",
    "ano_referencia", "ano_primeira_consulta", "ano_diagnostico",
    "ano_competencia", "ano_notificacao", "ano_ocorrencia",
})

# `coletado` é a data em que NÓS fomos buscar, não a competência do dado. As
# tabelas de cobertura a carregam de propósito, e declarar isso como período
# coberto seria pior que declarar nada: diria que a fonte cobre o dia de hoje.
NAO_E_COMPETENCIA = frozenset({"coletado", "gerado_em", "publicada_em"})


# ---------------------------------------------------------------------------
# 1. A função, vista achando e vista não achando
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("coluna", sorted({
    "ano_mes", "competencia", "ano_mes_previsto", "ano", "ano_epi",
    "ano_referencia", "ano_primeira_consulta",
}))
def test_cada_nome_conhecido_e_reconhecido(coluna):
    df = pd.DataFrame({coluna: [2013, 2019, 2023], "casos": [1, 2, 3]})
    assert _competencias(df) == ("2013", "2023")


def test_tabela_sem_eixo_de_tempo_declara_nada():
    """Dimensão não tem período, e inventar um seria pior que omitir."""
    df = pd.DataFrame({"municipio_cod": ["355030"], "nome": ["São Paulo"]})
    assert _competencias(df) == (None, None)


def test_coluna_vazia_nao_vira_periodo():
    df = pd.DataFrame({"ano": pd.Series([None, None], dtype="object")})
    assert _competencias(df) == (None, None)


def test_data_de_coleta_nao_e_competencia():
    """`coletado` diz quando fomos buscar, não o que o dado cobre."""
    df = pd.DataFrame({"coletado": ["2026-09-21"], "convenios": [10]})
    assert _competencias(df) == (None, None)


# ---------------------------------------------------------------------------
# 2. O manifesto real — a guarda que pega a próxima ocorrência
# ---------------------------------------------------------------------------

def _manifesto() -> dict:
    atual = RAIZ / "data" / "publicacoes" / "atual.json"
    ponteiro = json.loads(atual.read_text(encoding="utf-8"))
    alvo = RAIZ / "data" / "publicacoes" / f"{ponteiro['id']}.json"
    return json.loads(alvo.read_text(encoding="utf-8"))


ATUAL = RAIZ / "data" / "publicacoes" / "atual.json"


@pytest.mark.skipif(not ATUAL.exists(), reason="sem manifesto neste ambiente")
def test_toda_tabela_com_eixo_de_tempo_declara_o_periodo():
    mudas = []
    for nome, t in _manifesto()["tabelas"].items():
        tempo = COLUNAS_DE_TEMPO.intersection(t["colunas"])
        if tempo and not t.get("competencia_min"):
            mudas.append(f"{nome} (tem {sorted(tempo)} e não declara período)")
    assert not mudas, (
        "tabela publicada com eixo de tempo e sem período declarado: some da "
        "completude histórica sem avisar. Acrescentar o nome da coluna à tupla "
        "de `_publicacao._competencias`.\n  " + "\n  ".join(mudas)
    )


@pytest.mark.skipif(not ATUAL.exists(), reason="sem manifesto neste ambiente")
def test_a_guarda_reprova_tabela_muda():
    """Vista reprovando: sem isto ela seria indistinguível de guarda quebrada."""
    mudas = [
        nome for nome, t in {"mart_x": {"colunas": ["ano_referencia", "n"],
                                        "competencia_min": None}}.items()
        if COLUNAS_DE_TEMPO.intersection(t["colunas"]) and not t["competencia_min"]
    ]
    assert mudas == ["mart_x"]


@pytest.mark.skipif(not ATUAL.exists(), reason="sem manifesto neste ambiente")
def test_data_de_coleta_nao_entra_na_lista_de_tempo():
    """Se `coletado` virasse eixo, as tabelas de cobertura mentiriam o período."""
    assert not COLUNAS_DE_TEMPO & NAO_E_COMPETENCIA


@pytest.mark.skipif(not ATUAL.exists(), reason="sem manifesto neste ambiente")
def test_o_rhc_declara_a_janela_que_ele_cobre():
    """O caso que originou o arquivo, preso pelo número e não pela forma."""
    t = _manifesto()["tabelas"].get("mart_rhc_cobertura")
    if t is None:
        pytest.skip("RHC não está neste manifesto")
    assert t["competencia_min"] == "2013"
    assert t["competencia_max"] == "2023"
