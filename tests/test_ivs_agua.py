"""
A classificação da água no Censo é HIERÁRQUICA, e somar o nível errado mente.

A tabela 6803 do SIDRA classifica domicílios por ligação à rede geral numa
árvore: três categorias de primeiro nível que fecham o total, cada uma com
filhos por forma de abastecimento. `pipeline_ivs.fetch_sem_agua` somava
72144+72145+72146+72147 como "com água" — e 72146 e 72147 são FILHOS de 72145,
não irmãos. O pai entrava duas vezes, e cinco irmãos ficavam de fora.

Em Cruzaltense/RS isso dava 967 domicílios com água num total de 616, e
`pct_sem_agua` saía **−56,98%**. Medido em 2026-09-12, o valor estava errado em
5.477 dos 5.570 municípios (98,3%); 418 ficaram negativos, e foram esses que
denunciaram o resto — os outros 5.059 estavam errados dentro da faixa plausível,
onde nada acusa.

Estes testes fixam as duas coisas que teriam pego o defeito no dia em que ele
foi escrito: a soma do primeiro nível tem de fechar com o total, e proporção
tem de ficar entre 0 e 100.

Executar: .venv311/Scripts/python -m pytest tests/test_ivs_agua.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import pytest

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "scripts"))

import pipeline_ivs  # noqa: E402


def _resposta(linhas: list[tuple[str, str, str]]) -> list[dict]:
    """Imita o formato do SIDRA: primeira linha é cabeçalho, não dado."""
    cab = {"D1C": "Município", "D4C": "Categoria", "V": "Valor"}
    return [cab] + [{"D1C": c, "D4C": k, "V": v} for c, k, v in linhas]


#: Cruzaltense/RS, os números reais que produziram o −56,98%.
CRUZALTENSE = [
    ("4306130", "72129", "616"),   # total
    ("4306130", "72144", "163"),   # possui ligação e usa como principal
    ("4306130", "72145", "448"),   # possui ligação, usa outra forma (PAI)
    ("4306130", "72153", "5"),     # NÃO possui ligação
]


def _com_sidra(monkeypatch, linhas):
    monkeypatch.setattr(pipeline_ivs, "_sidra",
                        lambda url: pd.DataFrame(_resposta(linhas)[1:]))


def test_conta_certa_em_cruzaltense(monkeypatch):
    """A metade aprovando: 5 de 616 sem ligação = 0,81%, não −56,98%."""
    _com_sidra(monkeypatch, CRUZALTENSE)
    d = pipeline_ivs.fetch_sem_agua()
    assert len(d) == 1
    assert d.iloc[0]["pct_sem_agua"] == pytest.approx(0.81, abs=0.01)


def test_primeiro_nivel_tem_de_fechar_com_o_total(monkeypatch):
    """A metade reprovando — e é a guarda que teria pego o defeito original.

    Aqui o total é menor que a soma das categorias de primeiro nível, que é o
    que acontece quando alguém soma filho junto com pai.
    """
    quebrado = [
        ("4306130", "72129", "616"),
        ("4306130", "72144", "163"),
        ("4306130", "72145", "448"),
        ("4306130", "72153", "300"),   # 163+448+300 = 911 > 616
    ]
    _com_sidra(monkeypatch, quebrado)
    with pytest.raises(SystemExit, match="não somam o total"):
        pipeline_ivs.fetch_sem_agua()


def test_categoria_ausente_aborta(monkeypatch):
    """Se o IBGE remexer a c1821, a conta para — em vez de calar e errar."""
    sem_a_categoria = [x for x in CRUZALTENSE if x[1] != "72153"]
    _com_sidra(monkeypatch, sem_a_categoria)
    with pytest.raises(SystemExit, match="não devolveu as categorias"):
        pipeline_ivs.fetch_sem_agua()


def test_proporcao_impossivel_aborta(monkeypatch):
    """Nenhuma proporção pode sair de 0–100, qualquer que seja o caminho.

    É a rede de segurança final: mesmo que a hierarquia passe a fechar por
    coincidência, um percentual fora da faixa continua sendo impossível.
    """
    impossivel = [
        ("4306130", "72129", "616"),
        ("4306130", "72144", "163"),
        ("4306130", "72145", "-247"),   # negativo absurdo que FECHA a soma
        ("4306130", "72153", "700"),    # 163-247+700 = 616, mas 700/616 = 114%
    ]
    _com_sidra(monkeypatch, impossivel)
    with pytest.raises(SystemExit, match="fora de 0–100"):
        pipeline_ivs.fetch_sem_agua()


def test_mart_publicado_nao_tem_percentual_impossivel():
    """O dado EM DISCO, não só o código que o gera.

    Enquanto `dim_ivs.parquet` não for regerado, este teste falha — e é para
    falhar: ele é o que impede a correção de ficar só no código enquanto a
    tabela publicada e servida continua com 418 valores negativos.
    """
    caminho = RAIZ / "data" / "marts" / "dim_ivs.parquet"
    if not caminho.exists():
        pytest.skip("dim_ivs.parquet não está em disco")
    d = pd.read_parquet(caminho, columns=["municipio_cod", "pct_sem_agua"])
    fora = d[~d.pct_sem_agua.between(0, 100)]
    assert fora.empty, (
        f"{len(fora)} municípios com pct_sem_agua fora de 0–100 "
        f"(mínimo {d.pct_sem_agua.min():.2f}). O código já está correto; "
        "falta regerar o mart e republicá-lo."
    )
