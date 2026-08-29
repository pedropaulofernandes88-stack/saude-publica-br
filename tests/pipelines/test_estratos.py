"""Testes do estrato de saúde municipal (scripts/pipeline_estratos.py).

O ponto da substituição do k-means foi a DETERMINAÇÃO: o estrato tem de ser
função apenas dos valores do próprio município. Estes testes existem para que
isso não volte a se perder em silêncio — inclusive testando que a guarda de
deriva realmente reprova quando os cortes deixam de descrever a base.
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pandas as pd
import pytest

RAIZ = Path(__file__).resolve().parents[2]


def _carregar():
    """Importa o pipeline sem executar o main nem exigir credencial.

    O módulo importa `_supabase_key`, que vive em scripts/; por isso scripts/
    entra no path antes.
    """
    sys.path.insert(0, str(RAIZ / "scripts"))
    spec = importlib.util.spec_from_file_location(
        "pipeline_estratos", RAIZ / "scripts" / "pipeline_estratos.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


pe = _carregar()


# --------------------------------------------------------------------------
# 1. o estrato depende só do município
# --------------------------------------------------------------------------
def test_tercil_e_funcao_apenas_do_valor():
    corte = (10.0, 20.0)
    assert pe.tercil(9.99, corte) == 1
    assert pe.tercil(10.0, corte) == 2      # limite inferior pertence ao tercil de cima
    assert pe.tercil(19.99, corte) == 2
    assert pe.tercil(20.0, corte) == 3


def test_estrato_id_e_bijetivo_com_a_tripla():
    vistos = {}
    for tm in (1, 2, 3):
        for tv in (1, 2, 3):
            for ti in (1, 2, 3):
                i = pe.estrato_id(tm, tv, ti)
                assert 1 <= i <= 27
                assert i not in vistos, "dois estratos com o mesmo id"
                vistos[i] = (tm, tv, ti)
    assert len(vistos) == 27


def test_mesma_entrada_devolve_sempre_o_mesmo_estrato():
    """Sem semente, sem vizinhança: 200 execuções, uma resposta."""
    valores = (712.5, 31.0, 6200.0)
    esperado = pe.estrato_id(
        *[pe.tercil(v, pe.CORTES[f]) for v, f in zip(valores, pe.FEATS, strict=True)])
    for _ in range(200):
        obtido = pe.estrato_id(
            *[pe.tercil(v, pe.CORTES[f]) for v, f in zip(valores, pe.FEATS, strict=True)])
        assert obtido == esperado


def test_municipio_nao_muda_de_estrato_quando_a_companhia_muda():
    """O defeito que derrubou o k-means, escrito como teste.

    Um município mantém os próprios valores; TODOS os outros mudam. Sob
    k-means isso movia centróides e reclassificava. Sob corte congelado, não
    pode mexer em nada.
    """
    alvo = (712.5, 31.0, 6200.0)
    antes = pe.estrato_id(
        *[pe.tercil(v, pe.CORTES[f]) for v, f in zip(alvo, pe.FEATS, strict=True)])
    # a "base" mudou radicalmente — irrelevante, porque o corte não vem dela
    depois = pe.estrato_id(
        *[pe.tercil(v, pe.CORTES[f]) for v, f in zip(alvo, pe.FEATS, strict=True)])
    assert antes == depois


# --------------------------------------------------------------------------
# 2. rótulo e estrato são 1-para-1
# --------------------------------------------------------------------------
def test_rotulo_identifica_o_estrato():
    rotulos = {
        ", ".join(pe.ROTULOS[f][t - 1] for f, t in zip(pe.FEATS, (tm, tv, ti), strict=True))
        for tm in (1, 2, 3) for tv in (1, 2, 3) for ti in (1, 2, 3)
    }
    assert len(rotulos) == 27, "dois estratos compartilhariam o mesmo rótulo"


# --------------------------------------------------------------------------
# 3. a guarda de deriva reprova quando deve
# --------------------------------------------------------------------------
def _base_sintetica(escala: float = 1.0) -> pd.DataFrame:
    """Base cujos tercis caem EXATAMENTE sobre os cortes congelados.

    Com quatro pontos, a interpolação linear do quantil 1/3 cai no índice 1 e a
    do 2/3 no índice 2 — ou seja, no segundo e no terceiro valores. Pôr os
    cortes nessas posições dá deriva zero, que é o ponto de partida honesto
    para testar a guarda.
    """
    colunas = {}
    for f in pe.FEATS:
        c0, c1 = pe.CORTES[f]
        colunas[f] = [v * escala for v in (c0 * 0.5, c0, c1, c1 * 1.5)]
    return pd.DataFrame(colunas)


def test_deriva_dentro_da_tolerancia_passa():
    pe.conferir_deriva(_base_sintetica())


def test_deriva_grande_aborta():
    """Base multiplicada por 3: os cortes congelados não a descrevem mais."""
    with pytest.raises(SystemExit) as exc:
        pe.conferir_deriva(_base_sintetica(escala=3.0))
    assert "ABORTA" in str(exc.value)
    assert "re-congelar" in str(exc.value) or "recalcule" in str(exc.value)


def test_tolerancia_e_explicita_e_pequena():
    """Tolerância frouxa esvaziaria a guarda sem ninguém notar."""
    assert 0 < pe.TOLERANCIA <= 0.15


# --------------------------------------------------------------------------
# 4. os cortes estão versionados, e não recalculados
# --------------------------------------------------------------------------
def test_cortes_sao_constantes_no_repositorio():
    assert set(pe.CORTES) == set(pe.FEATS)
    for f in pe.FEATS:
        inferior, superior = pe.CORTES[f]
        assert inferior < superior, f"cortes fora de ordem em {f}"
    assert pe.CORTES_CONGELADOS_EM, "a data do congelamento faz parte do método"
