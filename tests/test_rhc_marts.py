"""As guardas do RHC, vistas reprovando e aprovando.

O pipeline publica a primeira fonte oncológica do projeto cuja unidade é a
PESSOA, e as quatro armadilhas da sondagem são todas do tipo que produz número
plausível e errado. Estes testes constroem a entrada defeituosa e exigem o
aborto, porque guarda que só foi vista aprovando é indistinguível de guarda
quebrada — este projeto inventariou 14 assim, e três não funcionavam.

A mais cara é a última: 2023 traz 71.019 casos contra 230.583 em 2022, o que
lido como série é um colapso de 69% na detecção de câncer no Brasil. São 15 UFs
contra 26, e o carimbo `ano_incompleto` é o que separa as duas leituras.

Nada aqui toca a rede.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import pytest

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "scripts"))

import pipeline_rhc as pr  # noqa: E402


def cobertura(hospitais_por_ano: dict[int, int]) -> pd.DataFrame:
    """Cobertura sintética com uma linha por ano, para exercitar o carimbo."""
    return pd.DataFrame([
        {"ano_primeira_consulta": ano, "uf_sigla": "XX", "casos": h * 2000,
         "analiticos": h * 1500, "nao_analiticos": h * 500,
         "sem_estadiamento": h * 1000, "sem_prazo": h * 600,
         "ano_diagnostico_difere": h * 400, "hospitais": h, "municipios": 100}
        for ano, h in sorted(hospitais_por_ano.items())
    ])


def caso(anos: list[int], estadiamentos: list[str] | None = None) -> pd.DataFrame:
    est = estadiamentos or ["1", "ignorado"]
    linhas = []
    for ano in anos:
        for e in est:
            linhas.append({"municipio_cod": "355030",
                           "ano_primeira_consulta": ano, "cid3": "C50",
                           "estadiamento": e, "tipo_caso": "analitico",
                           "casos": 100, "casos_com_prazo": 60,
                           "casos_ate_60d": 25, "casos_acima_60d": 35})
    return pd.DataFrame(linhas)


# ---------------------------------------------------------------------------
# 1. O carimbo de ano incompleto
# ---------------------------------------------------------------------------

def test_ano_com_poucos_hospitais_e_marcado():
    """O caso real: 2022 cai para 189 e 2023 para 69, de um platô de ~224."""
    cob = cobertura({2013: 213, 2014: 219, 2015: 229, 2016: 229, 2017: 235,
                     2018: 233, 2019: 224, 2020: 223, 2021: 216, 2022: 189,
                     2023: 69})
    assert pr.anos_incompletos(cob) == {2022, 2023}


def test_serie_estavel_nao_marca_ninguem():
    """Marcar ano completo é tão errado quanto não marcar o incompleto."""
    cob = cobertura({a: 220 + (a % 3) for a in range(2013, 2024)})
    assert pr.anos_incompletos(cob) == set()


def test_serie_curta_nao_arrisca_palpite():
    """Com três anos não há platô, e inventar um seria pior que não marcar."""
    assert pr.anos_incompletos(cobertura({2021: 200, 2022: 190, 2023: 60})) == set()


def test_o_limiar_nao_marca_queda_pequena():
    """±5% é a variação medida entre anos assentados; 0,90 fica acima dela."""
    cob = cobertura({a: 224 for a in range(2013, 2023)} | {2023: 210})
    assert pr.anos_incompletos(cob) == set()
    cob = cobertura({a: 224 for a in range(2013, 2023)} | {2023: 190})
    assert pr.anos_incompletos(cob) == {2023}


# ---------------------------------------------------------------------------
# 2. As guardas de publicação, cada uma vista reprovando
# ---------------------------------------------------------------------------

def _valido() -> tuple[pd.DataFrame, pd.DataFrame]:
    cob = cobertura({2013: 224, 2014: 224, 2015: 224, 2016: 224, 2017: 224,
                     2018: 224, 2019: 224, 2020: 224, 2021: 224, 2022: 189,
                     2023: 69})
    c = caso(sorted(cob.ano_primeira_consulta))
    incompletos = pr.anos_incompletos(cob)
    for df in (c, cob):
        df["ano_incompleto"] = df.ano_primeira_consulta.isin(incompletos)
    return c, cob


def test_o_conjunto_valido_passa():
    """Sem isto, todos os testes abaixo passariam por motivo errado."""
    c, cob = _valido()
    pr._guardas(c, cob)


def test_reprova_quando_ninguem_fica_sem_estadiamento():
    """~53% é o medido. Zero é a assinatura de 88/99 virando estádio."""
    c, cob = _valido()
    cob["sem_estadiamento"] = 0
    with pytest.raises(SystemExit, match="NENHUM caso sem estadiamento"):
        pr._guardas(c, cob)


def test_reprova_quando_quase_tudo_fica_sem_estadiamento():
    c, cob = _valido()
    cob["sem_estadiamento"] = cob.casos
    with pytest.raises(SystemExit, match="mudou de código"):
        pr._guardas(c, cob)


def test_reprova_quando_some_o_caso_nao_analitico():
    """Somar os dois universos vira outro estudo, e em silêncio."""
    c, cob = _valido()
    cob["nao_analiticos"] = 0
    with pytest.raises(SystemExit, match="não analítico"):
        pr._guardas(c, cob)


def test_reprova_quando_a_classificacao_do_prazo_nao_fecha():
    c, cob = _valido()
    c.loc[0, "casos_ate_60d"] = 1
    with pytest.raises(SystemExit, match="não fecha"):
        pr._guardas(c, cob)


def test_reprova_mais_casos_com_prazo_do_que_casos():
    c, cob = _valido()
    c.loc[0, "casos"] = 10
    with pytest.raises(SystemExit):
        pr._guardas(c, cob)


def test_reprova_estadio_zero_sem_rotulo_de_ausencia():
    """O erro que a APAC já pagou: ausência publicada como diagnóstico precoce."""
    c, cob = _valido()
    c = c[c.estadiamento != "ignorado"].copy()
    c["estadiamento"] = "0"
    with pytest.raises(SystemExit, match="diagnóstico"):
        pr._guardas(c, cob)


def test_reprova_carimbo_no_ano_errado():
    c, cob = _valido()
    cob["ano_incompleto"] = cob.ano_primeira_consulta == 2013
    with pytest.raises(SystemExit, match="fora do lugar"):
        pr._guardas(c, cob)


def test_reprova_carimbo_divergente_dentro_do_ano():
    """Uma linha marcada e outra não, no mesmo ano, é pior que nenhuma."""
    c, cob = _valido()
    c.loc[c.index[-1], "ano_incompleto"] = not c.ano_incompleto.iloc[-1]
    with pytest.raises(SystemExit, match="divergente"):
        pr._guardas(c, cob)


def test_reprova_mart_vazio():
    with pytest.raises(SystemExit, match="vazio"):
        pr._guardas(pd.DataFrame(), pd.DataFrame())


# ---------------------------------------------------------------------------
# 3. O prazo: ausência e intervalo impossível não viram zero dia
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("di,dt,esperado", [
    ("01/03/2019", "01/03/2019", (True, 0)),
    ("01/03/2019", "30/04/2019", (True, 60)),
    ("01/03/2019", "01/05/2019", (True, 61)),
    ("01/03/2018", "01/03/2019", (True, 365)),   # 2018 nao e bissexto
])
def test_prazo_dentro_da_janela(di, dt, esperado):
    assert pr._prazo({"DTDIAGNO": di, "DATAINITRT": dt}) == esperado


@pytest.mark.parametrize("di,dt", [
    ("", "01/03/2019"),          # sem diagnóstico
    ("01/03/2019", ""),          # sem tratamento
    ("01/03/2019", "28/02/2019"),  # tratamento ANTES do diagnóstico
    ("20190301", "20190401"),    # o formato do resto do projeto
])
def test_prazo_fora_da_janela_nao_vira_zero(di, dt):
    ok, _ = pr._prazo({"DTDIAGNO": di, "DATAINITRT": dt})
    assert ok is False


def test_prazo_acima_de_365_sai_como_jomar_faz():
    ok, dias = pr._prazo({"DTDIAGNO": "01/03/2018", "DATAINITRT": "01/03/2020"})
    assert ok is False and dias > pr.TETO_PRAZO


def test_o_teto_e_o_do_artigo_e_o_prazo_e_o_da_lei():
    assert pr.TETO_PRAZO == 365
    assert pr.PRAZO_LEGAL == 60


# ---------------------------------------------------------------------------
# 4. O mart publicado obedece ao que o cabeçalho promete
# ---------------------------------------------------------------------------

MART = RAIZ / "data" / "marts" / "mart_rhc_caso.parquet"
COB = RAIZ / "data" / "marts" / "mart_rhc_cobertura.parquet"


@pytest.mark.skipif(not MART.exists(), reason="mart não gerado neste ambiente")
def test_o_mart_real_passa_nas_proprias_guardas():
    pr._guardas(pd.read_parquet(MART), pd.read_parquet(COB))


@pytest.mark.skipif(not MART.exists(), reason="mart não gerado neste ambiente")
def test_o_mart_real_carimba_os_anos_incompletos():
    cob = pd.read_parquet(COB)
    marcados = set(cob.loc[cob.ano_incompleto, "ano_primeira_consulta"])
    assert marcados, "nenhum ano marcado — o RHC sempre tem cauda de reporte"
    assert int(cob.ano_primeira_consulta.max()) in marcados


@pytest.mark.skipif(not MART.exists(), reason="mart não gerado neste ambiente")
def test_o_mart_real_nao_publica_identificador():
    """A doutrina vale para fonte nova também, e esta traz pessoa."""
    from _identificador import conferir_sem_identificador

    conferir_sem_identificador(pd.read_parquet(MART), "mart_rhc_caso")
    conferir_sem_identificador(pd.read_parquet(COB), "mart_rhc_cobertura")


# ---------------------------------------------------------------------------
# 5. A validação EXTERNA: o mart reproduz uma coorte publicada
# ---------------------------------------------------------------------------

PERFIL = RAIZ / "data" / "marts" / "mart_rhc_perfil.parquet"

#: Jomar RT et al., Cien Saude Colet 2023;28(7):2155-2164 (PMID 37436327):
#: Rio de Janeiro, mama (C50), mulheres com 20 anos ou mais, casos analíticos,
#: 2013-2019. Publicam 18.098 casos e 82,1% acima de 60 dias.
JOMAR_N = 18_098
JOMAR_PCT = 82.1

MENORES_E_IGNORADA = {"00-04", "05-09", "10-14", "15-19", "ignorada"}


@pytest.mark.skipif(not PERFIL.exists(), reason="mart não gerado neste ambiente")
def test_o_mart_reproduz_a_coorte_publicada_de_jomar():
    """A única checagem deste projeto contra uma coorte publicada de fora.

    Importa mais que qualquer guarda interna: foi ela que confirmou que a
    desduplicação de página está certa. Sem a correção o recorte daria 35.748,
    quase o dobro do n publicado — e nenhuma guarda de forma reprovaria.
    """
    p = pd.read_parquet(PERFIL)
    c = p[(p.uf_sigla == "RJ") & (p.cid3 == "C50")
          & (p.sexo == "feminino")
          & (~p.faixa_etaria.isin(MENORES_E_IGNORADA))
          & (p.tipo_caso == "analitico")
          & (p.ano_primeira_consulta.between(2013, 2019))]
    n = int(c.casos.sum())
    # 5% de folga: eles excluem tratamento prévio (DIAGANT/ANTRI) e este
    # recorte não, então bater exato seria suspeito, não tranquilizador.
    assert 0.95 * JOMAR_N <= n <= 1.05 * JOMAR_N, (
        f"o recorte de Jomar et al. dá {n:,} e o publicado é {JOMAR_N:,}. "
        f"Se ficou perto do DOBRO, a desduplicação de página parou de valer — "
        f"ver pipeline_rhc._posicao.")

    pct = 100 * c.casos_acima_60d.sum() / c.casos_com_prazo.sum()
    assert abs(pct - JOMAR_PCT) < 5, (
        f"desfecho em {pct:.1f}% contra {JOMAR_PCT}% publicados")


@pytest.mark.skipif(not PERFIL.exists(), reason="mart não gerado neste ambiente")
def test_o_perfil_e_o_caso_contam_o_mesmo_universo():
    """`caso` é municipal e descarta município inválido, logo é menor ou igual."""
    perfil = pd.read_parquet(PERFIL)
    caso = pd.read_parquet(MART)
    assert int(caso.casos.sum()) <= int(perfil.casos.sum())


@pytest.mark.skipif(not PERFIL.exists(), reason="mart não gerado neste ambiente")
def test_nenhuma_contagem_do_perfil_e_toda_par():
    """A assinatura que denunciou a duplicação, virada guarda permanente.

    Com o arquivo duplicado, TODA contagem em TODA categoria era par. Se isso
    voltar, a correção foi desfeita.
    """
    perfil = pd.read_parquet(PERFIL)
    por_cid = perfil.groupby("cid3").casos.sum()
    assert (por_cid % 2 != 0).any(), (
        "toda contagem por CID-3 está par — é a assinatura da duplicação de "
        "página do exportador do INCA")
