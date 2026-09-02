"""Testes de `analise_perfil_mortalidade.py` e `analise_anomalia_causas.py`.

Análise não supervisionada tem um problema que pipeline de dado não tem: ela
sempre devolve alguma coisa. PCA sempre acha componentes, k-means sempre acha
grupos, e uma busca por defasagem sempre acha um lag de pico. Nada disso falha
com erro — falha produzindo resultado bonito e vazio.

Por isso estes testes atacam o método, não o dado:

  * o nulo multinomial precisa REPROVAR ruído e APROVAR estrutura plantada;
  * a residualização precisa apagar de fato o confundidor plantado;
  * a desazonalização precisa derrubar correlação induzida por sazonalidade
    comum, que é o jeito mais fácil de publicar correlação inexistente;
  * o teste de contagem precisa concordar com Poisson quando não há
    superdispersão, e ficar mais conservador quando há;
  * o Benjamini-Hochberg precisa controlar FDR sob a hipótese nula.

Os controles positivos do dado real (dengue em 2024, COVID em 2020–2021) estão
no fim, e pulam quando os marts ainda não foram gerados.
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

RAIZ = Path(__file__).resolve().parents[2]
MARTS = RAIZ / "data" / "marts"


def _carregar(nome: str):
    sys.path.insert(0, str(RAIZ / "scripts"))
    spec = importlib.util.spec_from_file_location(nome, RAIZ / "scripts" / f"{nome}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


perfil = _carregar("analise_perfil_mortalidade")
anomalia = _carregar("analise_anomalia_causas")


# --------------------------------------------------------------------------
# 1. residualização: o confundidor plantado tem de sumir
# --------------------------------------------------------------------------
def test_residualizar_apaga_o_confundidor_plantado():
    rng = np.random.default_rng(0)
    n = 400
    conf = pd.DataFrame({"x": rng.normal(size=n)})
    # duas colunas que SÓ dependem do confundidor, com sinais opostos
    y = np.column_stack([3 * conf.x.values + 0.01 * rng.normal(size=n),
                         -2 * conf.x.values + 0.01 * rng.normal(size=n)])
    antes = abs(np.corrcoef(y[:, 0], conf.x)[0, 1])
    depois = abs(np.corrcoef(perfil.residualizar(y, conf)[:, 0], conf.x)[0, 1])
    assert antes > 0.99
    assert depois < 0.01


def test_residualizar_preserva_o_que_nao_depende_do_confundidor():
    rng = np.random.default_rng(1)
    n = 300
    conf = pd.DataFrame({"x": rng.normal(size=n)})
    sinal = rng.normal(size=n)
    y = np.column_stack([sinal, sinal])
    r = perfil.residualizar(y, conf)
    assert np.corrcoef(r[:, 0], sinal)[0, 1] > 0.95


# --------------------------------------------------------------------------
# 2. componentes: variância decrescente e somando um
# --------------------------------------------------------------------------
def test_componentes_devolvem_fracao_decrescente():
    rng = np.random.default_rng(2)
    _, var, cargas = perfil.componentes(rng.normal(size=(200, 15)))
    assert abs(var.sum() - 1) < 1e-9
    assert all(var[i] >= var[i + 1] - 1e-12 for i in range(len(var) - 1))
    assert cargas.shape[1] == 15


# --------------------------------------------------------------------------
# 3. desazonalização: a armadilha mais fácil de cair
# --------------------------------------------------------------------------
def test_remover_mes_derruba_correlacao_puramente_sazonal():
    """Duas causas sem relação nenhuma, ambas com pico no inverno.

    Na série bruta elas correlacionam forte — e seria publicado como "causas
    associadas". Depois de tirar o efeito de mês civil, a correlação some.
    """
    rng = np.random.default_rng(3)
    idx = pd.MultiIndex.from_tuples([(a, m) for a in range(2015, 2025)
                                     for m in range(1, 13)], names=["ano", "mes"])
    mes = np.array([m for (_, m) in idx])
    sazonal = 40 * np.cos((mes - 7) * np.pi / 6)
    serie = pd.DataFrame({"A": 200 + sazonal + rng.normal(0, 3, len(idx)),
                          "B": 150 + sazonal + rng.normal(0, 3, len(idx))}, index=idx)
    bruto = abs(np.corrcoef(serie.A, serie.B)[0, 1])
    r = perfil._sem_tendencia_nem_mes(serie)
    limpo = abs(np.corrcoef(r[:, 0], r[:, 1])[0, 1])
    assert bruto > 0.9, "o teste precisa de correlação sazonal forte para valer"
    assert limpo < 0.3


def test_remover_mes_preserva_correlacao_real():
    """Choque comum NÃO sazonal tem de sobreviver — senão o filtro apaga o sinal."""
    rng = np.random.default_rng(4)
    idx = pd.MultiIndex.from_tuples([(a, m) for a in range(2015, 2025)
                                     for m in range(1, 13)], names=["ano", "mes"])
    choque = rng.normal(0, 20, len(idx))
    serie = pd.DataFrame({"A": 200 + choque + rng.normal(0, 2, len(idx)),
                          "B": 150 + choque + rng.normal(0, 2, len(idx))}, index=idx)
    r = perfil._sem_tendencia_nem_mes(serie)
    assert abs(np.corrcoef(r[:, 0], r[:, 1])[0, 1]) > 0.9


# --------------------------------------------------------------------------
# 4. Benjamini-Hochberg
# --------------------------------------------------------------------------
def test_bh_nao_descobre_quase_nada_sob_a_nula():
    """p uniformes = nenhuma hipótese verdadeira. Descobrir muito seria defeito."""
    rng = np.random.default_rng(5)
    p = rng.uniform(size=20_000)
    assert len(perfil._bh(p, q=0.01)) <= 20


def test_bh_encontra_o_que_esta_plantado():
    rng = np.random.default_rng(6)
    p = np.concatenate([rng.uniform(size=9_900), np.full(100, 1e-12)])
    achados = perfil._bh(p, q=0.01)
    assert len(achados) >= 100
    assert set(range(9_900, 10_000)).issubset(set(achados.tolist()))


# --------------------------------------------------------------------------
# 5. o teste de contagem
# --------------------------------------------------------------------------
def test_sem_superdispersao_concorda_com_poisson():
    from scipy.stats import poisson
    obs = np.array([10, 20, 3])
    esp = np.array([5.0, 12.0, 1.0])
    p_nb = anomalia._p_binomial_negativa(obs, esp, np.ones(3))
    p_pois = poisson.sf(obs - 1, esp)
    assert np.allclose(p_nb, p_pois, rtol=1e-3)


def test_superdispersao_torna_o_teste_mais_conservador():
    """Com φ maior, o mesmo excesso precisa ser maior para significar algo."""
    obs = np.array([20])
    esp = np.array([5.0])
    p1 = anomalia._p_binomial_negativa(obs, esp, np.array([1.0]))
    p3 = anomalia._p_binomial_negativa(obs, esp, np.array([3.0]))
    assert p3 > p1


def test_phi_igual_a_um_nao_divide_por_zero():
    """`np.where` avalia os dois ramos; φ=1 exato já produziu aviso de divisão."""
    with np.errstate(divide="raise", invalid="raise"):
        p = anomalia._p_binomial_negativa(np.array([3]), np.array([1.0]), np.array([1.0]))
    assert 0 <= p[0] <= 1


# --------------------------------------------------------------------------
# 6. o controle positivo aborta quando deveria
# --------------------------------------------------------------------------
def _alvo(linhas):
    return pd.DataFrame(linhas, columns=["causabas_3", "ano", "excesso_proprio"])


def test_sem_dengue_o_controle_positivo_aborta():
    with pytest.raises(SystemExit, match="dengue"):
        anomalia.conferir_controles(_alvo([("B34", 2020, True), ("I21", 2022, True)]))


def test_sem_covid_o_controle_positivo_aborta():
    with pytest.raises(SystemExit, match="COVID"):
        anomalia.conferir_controles(_alvo([("A90", 2024, True), ("I21", 2022, True)]))


def test_com_os_dois_controles_passa():
    anomalia.conferir_controles(_alvo([("A90", 2024, True), ("B34", 2021, True)]))


# --------------------------------------------------------------------------
# 7. o que foi publicado
# --------------------------------------------------------------------------
@pytest.mark.skipif(not (MARTS / "mart_anomalia_causa_municipio.parquet").exists(),
                    reason="mart de anomalia ainda não gerado")
def test_dengue_so_aparece_em_2024():
    """2024 teve 6,6 milhões de casos prováveis contra 1,6 milhão em 2023.

    Dengue sinalizada em outro ano indicaria linha de base contaminada.
    """
    d = pd.read_parquet(MARTS / "mart_anomalia_causa_municipio.parquet")
    dengue = d[d.causabas_3.isin(["A90", "A91"]) & d.excesso_proprio]
    assert len(dengue) > 0
    assert sorted(dengue.ano.unique()) == [2024]


@pytest.mark.skipif(not (MARTS / "mart_perfil_mortalidade_municipio.parquet").exists(),
                    reason="mart de perfil ainda não gerado")
def test_o_perfil_publica_coordenadas_e_nao_so_rotulo():
    """Se um dia sobrar só `grupo`, a leitura de contínuo terá se perdido."""
    d = pd.read_parquet(MARTS / "mart_perfil_mortalidade_municipio.parquet")
    assert {"pc1", "pc2", "pc3", "grupo", "indice_inespecificidade"} <= set(d.columns)
    assert d.pc1.std() > 0


@pytest.mark.skipif(not (MARTS / "achados.json").exists(),
                    reason="achados ainda não registrados")
def test_a_leitura_de_continuo_esta_registrada():
    """ARI alto com silhueta baixa é a conclusão central da análise 1.

    Registrada em `achados.json` para que, se o dado mudar e a conclusão virar,
    a mudança apareça em vez de a prosa do site continuar afirmando o antigo.
    """
    import json
    a = json.loads((MARTS / "achados.json").read_text(encoding="utf-8"))
    if "perfil_ari_k3" not in a:
        pytest.skip("analise_perfil_mortalidade.py ainda não rodou")
    assert a["perfil_ari_k3"]["valor"] >= 0.90
    assert a["perfil_silhueta_k3"]["valor"] < 0.25
