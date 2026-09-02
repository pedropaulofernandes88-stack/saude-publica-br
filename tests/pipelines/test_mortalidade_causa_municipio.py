"""Testes de `scripts/pipeline_mortalidade_causa_municipio.py`.

A tabela existe para sustentar uma análise não supervisionada — clusterizar
municípios pela composição de causas de morte. Isso muda o que precisa ser
testado: não basta o dado bater, o MÉTODO precisa distinguir estrutura de ruído.
Uma matriz de contagens pequenas se parece com estrutura por acidente de
amostragem, e um PCA rodado em cima dela devolve componentes bonitos que não
significam nada.

Por isso os testes se dividem em dois grupos:

  * as guardas de INTEGRIDADE (reconciliação, COVID, vocabulário), que impedem
    publicar um dado errado;
  * a guarda de MÉTODO (modelo nulo), testada nos dois sentidos — que ela
    aprova uma matriz com estrutura plantada E reprova ruído multinomial puro.
    Guarda que só foi vista aprovando não é guarda; é decoração.
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


def _carregar():
    sys.path.insert(0, str(RAIZ / "scripts"))
    spec = importlib.util.spec_from_file_location(
        "pipeline_mortalidade_causa_municipio",
        RAIZ / "scripts" / "pipeline_mortalidade_causa_municipio.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


pm = _carregar()


def _anual(linhas: list[tuple]) -> pd.DataFrame:
    return pd.DataFrame(linhas, columns=["municipio_cod", "ano", "causabas_3", "obitos"])


# --------------------------------------------------------------------------
# 1. a guarda do COVID, nas duas direções
# --------------------------------------------------------------------------
def test_u07_aborta_porque_invalidaria_a_marca_is_covid():
    """Se o DataSUS passar a usar U07, `is_covid = B34` fica errado.

    A marca não é convenção do projeto: é leitura de como o SIM codificou. No
    dia em que a codificação mudar, publicar em silêncio produziria uma coluna
    que afirma o contrário do dado.
    """
    df = _anual([("350280", 2021, "B34", 500), ("350280", 2021, "U07", 12)])
    with pytest.raises(SystemExit, match="U07"):
        pm.conferir_covid(df)


def test_b34_esvaziado_na_pandemia_aborta():
    """B34 sem os óbitos de 2020–2021 significa derivação quebrada."""
    df = _anual([("350280", 2020, "B34", 91), ("350280", 2021, "I21", 400)])
    with pytest.raises(SystemExit, match="B34"):
        pm.conferir_covid(df)


def test_b34_com_a_pandemia_passa():
    df = _anual([("350280", 2020, "B34", 213_233), ("350280", 2021, "B34", 425_218)])
    pm.conferir_covid(df)


def test_recorte_sem_2020_nao_exige_covid():
    """`--anos 2023 2024` não deve reprovar por não conter a pandemia."""
    pm.conferir_covid(_anual([("350280", 2023, "I21", 50)]))


# --------------------------------------------------------------------------
# 2. o vocabulário: tolera o ruído real, reprova o sistemático
# --------------------------------------------------------------------------
def _dim(linhas: list[tuple]) -> pd.DataFrame:
    return pd.DataFrame(linhas, columns=["causabas_3", "capitulo_cid", "obitos_total"])


def test_dois_cids_invalidos_sao_tolerados():
    """D96 e K99 existem de verdade no SIM, com um óbito cada.

    Removê-los quebraria a reconciliação com `mart_mortalidade_municipio`, que
    os conta. Tolerar o ruído real é o que permite a guarda ser rígida no resto.
    """
    pm.conferir_vocabulario(_dim([("D96", "N/D", 1), ("K99", "N/D", 1),
                                  ("I21", "IX", 931_049)]))


def test_muitos_orfaos_abortam_porque_a_tabela_de_capitulos_e_que_esta_errada():
    with pytest.raises(SystemExit, match="fora da CID-10"):
        pm.conferir_vocabulario(_dim([("A00", "N/D", 50_000)]))


# --------------------------------------------------------------------------
# 3. a reconciliação com o mart já publicado
# --------------------------------------------------------------------------
def test_reconciliacao_aborta_quando_o_total_do_municipio_diverge(tmp_path, monkeypatch):
    publicado = pd.DataFrame(
        [("350280", 2024, "TOTAL", "TOTAL", 1000)],
        columns=["municipio_cod", "ano", "capitulo_cid", "sexo", "obitos"])
    publicado.to_parquet(tmp_path / "mart_mortalidade_municipio.parquet")
    monkeypatch.setattr(pm, "MARTS", tmp_path)

    # 999 != 1000: um óbito a menos é divergência, não arredondamento.
    with pytest.raises(SystemExit, match="reconciliação"):
        pm.conferir_reconciliacao(_anual([("350280", 2024, "I21", 999)]))


def test_reconciliacao_passa_quando_a_soma_fecha(tmp_path, monkeypatch):
    publicado = pd.DataFrame(
        [("350280", 2024, "TOTAL", "TOTAL", 1000)],
        columns=["municipio_cod", "ano", "capitulo_cid", "sexo", "obitos"])
    publicado.to_parquet(tmp_path / "mart_mortalidade_municipio.parquet")
    monkeypatch.setattr(pm, "MARTS", tmp_path)
    pm.conferir_reconciliacao(_anual([("350280", 2024, "I21", 600),
                                      ("350280", 2024, "J18", 400)]))


# --------------------------------------------------------------------------
# 4. a guarda de método: o modelo nulo precisa DISCRIMINAR
# --------------------------------------------------------------------------
def _matriz_para_frames(contagens: np.ndarray, cids: list[str]):
    """Converte uma matriz município × CID nos dois frames que a guarda espera."""
    linhas = [(f"{i:06d}", 2024, cid, int(contagens[i, j]))
              for i in range(contagens.shape[0])
              for j, cid in enumerate(cids) if contagens[i, j] > 0]
    dim = pd.DataFrame({"causabas_3": cids, "informativo": True})
    return _anual(linhas), dim


def test_nulo_reprova_ruido_multinomial_puro():
    """O caso que a guarda existe para pegar.

    Todo município sorteia da MESMA composição nacional: não há epidemiologia
    nenhuma, só amostragem. Se a razão passasse de 2x aqui, a guarda estaria
    aprovando ruído — e o PCA da análise acharia componentes inventados.
    """
    rng = np.random.default_rng(11)
    cids = [f"X{i:02d}" for i in range(40)]
    p = rng.dirichlet(np.ones(len(cids)) * 3)
    contagens = np.vstack([rng.multinomial(800, p) for _ in range(300)])
    anual, dim = _matriz_para_frames(contagens, cids)
    with pytest.raises(SystemExit, match="modelo nulo"):
        pm.guarda_modelo_nulo(anual, dim)


def test_nulo_aprova_estrutura_plantada():
    """Dois grupos com composições diferentes têm de superar o nulo com folga."""
    rng = np.random.default_rng(11)
    cids = [f"X{i:02d}" for i in range(40)]
    pa = rng.dirichlet(np.ones(len(cids)) * 3)
    pb = rng.dirichlet(np.ones(len(cids)) * 3)
    contagens = np.vstack([rng.multinomial(800, pa) for _ in range(150)]
                          + [rng.multinomial(800, pb) for _ in range(150)])
    anual, dim = _matriz_para_frames(contagens, cids)
    assert pm.guarda_modelo_nulo(anual, dim) > pm.NULO_LIMIAR


def test_variancia_dos_componentes_e_uma_fracao_decrescente():
    rng = np.random.default_rng(3)
    proporcoes = rng.dirichlet(np.ones(12), size=200)
    v = pm._variancia_pcs(proporcoes)
    assert len(v) == 5
    assert 0 < v.sum() <= 1 + 1e-9
    assert all(v[i] >= v[i + 1] - 1e-12 for i in range(len(v) - 1))


# --------------------------------------------------------------------------
# 5. o vocabulário publicado: as duas marcas que mudam a análise
# --------------------------------------------------------------------------
@pytest.mark.skipif(not (MARTS / "dim_cid10_informativo.parquet").exists(),
                    reason="dim_cid10_informativo ainda não foi gerada")
def test_b34_e_informativo_e_marcado_como_covid():
    """A armadilha em uma linha.

    A descrição oficial de B34 é "Doenc p/virus de localiz NE" — o texto exato
    que um filtro de causas inespecíficas descartaria. No SIM brasileiro B34 é
    COVID-19, e descartá-lo apaga a pandemia da matriz.
    """
    d = pd.read_parquet(MARTS / "dim_cid10_informativo.parquet").set_index("causabas_3")
    assert bool(d.loc["B34", "is_covid"])
    assert bool(d.loc["B34", "informativo"])
    assert not bool(d.loc["B34", "is_mal_definida"])


@pytest.mark.skipif(not (MARTS / "dim_cid10_informativo.parquet").exists(),
                    reason="dim_cid10_informativo ainda não foi gerada")
def test_causa_mal_definida_nunca_e_informativa():
    """R99 está em 98% dos municípios e ainda assim não é informativa.

    Prevalência alta não redime: ela mede qualidade do registro, não doença.
    """
    d = pd.read_parquet(MARTS / "dim_cid10_informativo.parquet")
    assert not d[d.is_mal_definida].informativo.any()
    r99 = d[d.causabas_3 == "R99"].iloc[0]
    assert r99.prevalencia_municipal > 0.9 and not r99.informativo


@pytest.mark.skipif(not (MARTS / "dim_cid10_informativo.parquet").exists(),
                    reason="dim_cid10_informativo ainda não foi gerada")
def test_u07_ausente_do_vocabulario_publicado():
    d = pd.read_parquet(MARTS / "dim_cid10_informativo.parquet")
    assert not d.causabas_3.str.startswith("U0").any()


# --------------------------------------------------------------------------
# 6. integração: o que foi publicado fecha com o que já estava publicado
# --------------------------------------------------------------------------
@pytest.mark.skipif(
    not ((MARTS / "mart_mortalidade_causa_municipio.parquet").exists()
         and (MARTS / "mart_mortalidade_municipio.parquet").exists()),
    reason="marts de mortalidade ainda não foram gerados")
def test_o_parquet_publicado_reconcilia_com_o_mart_de_capitulo():
    causa = pd.read_parquet(MARTS / "mart_mortalidade_causa_municipio.parquet",
                            columns=["municipio_cod", "ano", "obitos"])
    cap = pd.read_parquet(MARTS / "mart_mortalidade_municipio.parquet",
                          columns=["municipio_cod", "ano", "capitulo_cid", "sexo", "obitos"])
    cap = cap[(cap.capitulo_cid == "TOTAL") & (cap.sexo == "TOTAL")]
    assert int(causa.obitos.sum()) == int(cap.obitos.sum())


@pytest.mark.skipif(
    not ((MARTS / "mart_mortalidade_causa_municipio.parquet").exists()
         and (MARTS / "mart_mortalidade_causa_municipio_mes.parquet").exists()),
    reason="marts de mortalidade ainda não foram gerados")
def test_o_grao_mensal_soma_o_grao_anual():
    """Duas tabelas do mesmo pipeline que não somam igual são uma delas errada."""
    anual = pd.read_parquet(MARTS / "mart_mortalidade_causa_municipio.parquet",
                            columns=["obitos"])
    mensal = pd.read_parquet(MARTS / "mart_mortalidade_causa_municipio_mes.parquet",
                             columns=["obitos"])
    assert int(anual.obitos.sum()) == int(mensal.obitos.sum())
