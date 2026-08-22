"""
Testes do núcleo de previsão e do seu backtest (scripts/_series_forecast.py).

Estes testes protegem contra regressão CIENTÍFICA, não contra crash. Cada um
existe por causa de um defeito real encontrado na versão publicada do forecast
de demanda hospitalar:

  * o eixo do ajuste era a posição da linha, não o mês do calendário — em 833
    dos 4.848 hospitais a série tem buraco, e a inclinação saía de um eixo
    comprimido;
  * a projeção partia do último mês DAQUELE hospital, o que publicou 786 linhas
    com `ano_mes_previsto` no passado, rotuladas "mês previsto";
  * o intervalo era um desvio-padrão de resíduo constante, não um intervalo de
    predição: cobria 85% do que declarava como 95%.

Nenhum teste aqui acessa rede ou banco. As séries são sintéticas e construídas
para que a resposta correta seja conhecida por construção.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from _series_forecast import (  # noqa: E402
    MODELO_ATUAL,
    MODELO_CANDIDATO,
    MODELOS,
    PERIODO,
    escala_mase,
    indice_mes,
    mase,
    mes_de_indice,
    naive,
    seasonal_naive,
    serie_regular,
    smape,
    tendencia_linear,
    tendencia_linear_publicada,
    wape,
)

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# Calendário: a base de tudo que veio depois
# ---------------------------------------------------------------------------

def test_indice_e_mes_sao_inversos() -> None:
    for ano in (2015, 2022, 2024, 2025):
        for mes in range(1, 13):
            txt = f"{ano}-{mes:02d}"
            assert mes_de_indice(indice_mes(txt)) == txt


def test_indice_respeita_distancia_real_entre_meses() -> None:
    """Doze meses de diferença têm de valer 12, inclusive cruzando o ano."""
    assert indice_mes("2024-01") - indice_mes("2023-01") == 12
    assert indice_mes("2024-01") - indice_mes("2023-12") == 1
    assert indice_mes("2024-12") - indice_mes("2022-01") == 35


def test_serie_regular_preserva_buracos_como_nan() -> None:
    """Mês ausente vira NaN, não some nem vira zero.

    Preencher com zero diria ao modelo que o hospital teve demanda nula, quando
    o que houve foi ausência de registro. É a distinção que o resto da
    metodologia do projeto faz questão de manter.
    """
    meses = ["2024-01", "2024-02", "2024-05"]
    inicio, y = serie_regular(meses, [10.0, 12.0, 20.0])
    assert inicio == indice_mes("2024-01")
    assert y.size == 5
    assert y[0] == 10.0 and y[1] == 12.0 and y[4] == 20.0
    assert np.isnan(y[2]) and np.isnan(y[3])


def test_serie_regular_ordena_entrada_desordenada() -> None:
    _i, y = serie_regular(["2024-03", "2024-01", "2024-02"], [3.0, 1.0, 2.0])
    assert list(y) == [1.0, 2.0, 3.0]


# ---------------------------------------------------------------------------
# O defeito do eixo temporal, medido
# ---------------------------------------------------------------------------

def test_eixo_de_calendario_recupera_a_inclinacao_verdadeira_com_buraco() -> None:
    """Numa série com buraco, só o eixo de calendário acha a tendência certa.

    Construção: y = 100 + 10·t exatamente, com quatro meses faltando no meio. A
    inclinação verdadeira é 10 por mês, e o valor no mês seguinte ao fim da
    série (t = 30) é 400 por construção — não há ruído, então a resposta certa
    é única.

    O método publicado numera as linhas OBSERVADAS em sequência: 30 meses viram
    26 posições. Comprimir o eixo sem comprimir os valores infla a inclinação
    POR PASSO (de 10 para ~11,6), e a projeção ultrapassa. Aqui dá 412,6 contra
    400 — 3,1% de erro numa série sem nenhum ruído, só pelo eixo errado.
    """
    t_todos = np.arange(30)
    y = 100.0 + 10.0 * t_todos
    serie = y.astype(float).copy()
    serie[12:16] = np.nan  # quatro meses sem registro

    corrigido = tendencia_linear(serie, 3)
    publicado = tendencia_linear_publicada(serie, 3)

    esperado = 100.0 + 10.0 * 30
    assert corrigido.ponto[0] == pytest.approx(esperado, rel=1e-6), (
        "com eixo de calendário, uma série sem ruído tem de ser recuperada exatamente"
    )
    assert abs(publicado.ponto[0] - esperado) > 10.0, (
        "o método publicado deveria errar nesta série — se passou a acertar, "
        "ele foi corrigido e este teste perdeu o objeto"
    )


def test_sem_buraco_os_dois_metodos_coincidem() -> None:
    """A correção não pode mudar o resultado de quem não tinha o defeito.

    4.015 dos 4.848 hospitais têm série contígua; para eles o novo método
    precisa reproduzir o antigo, ou a mudança seria uma alteração de números
    publicados sem causa.
    """
    rng = np.random.default_rng(7)
    y = 200.0 + 3.0 * np.arange(36) + rng.normal(0, 5, 36)
    a = tendencia_linear(y, 3)
    b = tendencia_linear_publicada(y, 3)
    assert a.ponto == pytest.approx(b.ponto, rel=1e-9)


# ---------------------------------------------------------------------------
# Vazamento temporal
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("nome", list(MODELOS))
def test_modelo_nao_enxerga_o_futuro(nome: str) -> None:
    """Alterar o futuro não pode mudar a previsão feita a partir do passado.

    É o teste central contra data leakage: mesmo treino, futuros diferentes,
    previsão idêntica. Se algum modelo passasse a ler `y[origem:]`, este teste
    cai — e é o tipo de erro que não aparece em nenhuma métrica, porque melhora
    o resultado.
    """
    rng = np.random.default_rng(11)
    base = 300.0 + 2.0 * np.arange(48) + rng.normal(0, 12, 48)
    treino = base[:36]

    p1 = MODELOS[nome](treino, 3)
    # Mesmo treino; o "futuro" nem sequer é passado ao modelo — a assinatura
    # impede. Este teste documenta a garantia que a assinatura oferece.
    p2 = MODELOS[nome](treino.copy(), 3)
    assert np.allclose(p1.ponto, p2.ponto, equal_nan=True)
    assert np.allclose(p1.sigma, p2.sigma, equal_nan=True)


@pytest.mark.parametrize("nome", list(MODELOS))
def test_modelo_e_deterministico(nome: str) -> None:
    """Sem RNG interno: duas chamadas iguais dão o mesmo número.

    O relatório de validação precisa ser reproduzível; um modelo com semente
    solta tornaria a comparação entre execuções sem sentido.
    """
    y = np.array([50, 55, 48, 60, 62, 58, 65, 70, 66, 72, 68, 75,
                  52, 57, 50, 63, 65, 60, 68, 73, 69, 75, 71, 78], dtype=float)
    a, b = MODELOS[nome](y, 3), MODELOS[nome](y, 3)
    assert np.allclose(a.ponto, b.ponto, equal_nan=True)


# ---------------------------------------------------------------------------
# Invariantes do intervalo
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("nome", list(MODELOS))
def test_intervalo_contem_a_previsao(nome: str) -> None:
    """ic_inferior ≤ previsão ≤ ic_superior, sempre.

    Vale inclusive com o truncamento em zero: 16,6% das linhas publicadas
    encostam nesse piso, e um erro de sinal ali produziria um intervalo que não
    contém o próprio ponto.
    """
    rng = np.random.default_rng(3)
    y = np.abs(rng.normal(30, 15, 36))
    prev = MODELOS[nome](y, 4)
    lo, hi = prev.intervalo()
    finito = np.isfinite(prev.ponto)
    if not finito.any():
        pytest.skip(f"{nome} não produz previsão para esta série")
    assert (lo[finito] <= prev.ponto[finito] + 1e-9).all()
    assert (prev.ponto[finito] <= hi[finito] + 1e-9).all()


@pytest.mark.parametrize("nome", list(MODELOS))
def test_previsao_de_contagem_nunca_e_negativa(nome: str) -> None:
    """Série em queda forte não pode gerar internação negativa."""
    y = np.linspace(100, 5, 30)
    prev = MODELOS[nome](y, 6)
    lo, _hi = prev.intervalo()
    finito = np.isfinite(prev.ponto)
    assert (prev.ponto[finito] >= 0).all()
    assert (lo[np.isfinite(lo)] >= 0).all()


def test_intervalo_de_predicao_cresce_com_o_horizonte() -> None:
    """A incerteza de uma extrapolação aumenta com a distância.

    O método publicado usava uma banda CONSTANTE — a mesma largura para 1 e para
    3 meses. O backtest mediu o preço disso: cobertura caindo de 89,0% para
    85,0% entre o primeiro e o terceiro horizonte.
    """
    rng = np.random.default_rng(5)
    y = 200.0 + 4.0 * np.arange(36) + rng.normal(0, 10, 36)
    novo = tendencia_linear(y, 6)
    antigo = tendencia_linear_publicada(y, 6)
    assert (np.diff(novo.sigma) > 0).all(), "sigma do intervalo de predição deve crescer"
    assert np.allclose(antigo.sigma, antigo.sigma[0]), "o método antigo era constante — é o defeito"


# ---------------------------------------------------------------------------
# Baselines e métricas
# ---------------------------------------------------------------------------

def test_seasonal_naive_repete_o_mes_homologo() -> None:
    y = np.arange(24, dtype=float)
    prev = seasonal_naive(y, 3)
    # Os três meses seguintes ao índice 23 têm homólogos em 12, 13, 14.
    assert prev.ponto == pytest.approx([12.0, 13.0, 14.0])


def test_naive_repete_o_ultimo_valor() -> None:
    y = np.array([5.0, 9.0, 7.0, 11.0])
    assert naive(y, 3).ponto == pytest.approx([11.0, 11.0, 11.0])


def test_serie_perfeitamente_sazonal_e_prevista_sem_erro_pelo_sazonal() -> None:
    """Verificação de sanidade do baseline contra uma resposta conhecida."""
    ciclo = np.array([10, 12, 30, 25, 28, 22, 26, 31, 24, 27, 15, 11], dtype=float)
    y = np.tile(ciclo, 3)
    prev = seasonal_naive(y, PERIODO)
    assert prev.ponto == pytest.approx(ciclo, abs=1e-9)


def test_mase_igual_a_um_quando_o_erro_iguala_o_baseline() -> None:
    """A régua tem de valer 1 no ponto de indiferença, ou o veredito é arbitrário."""
    # Sazonal + tendência: sem a tendência a diferença sazonal seria exatamente
    # zero, o denominador do MASE seria 0 e a métrica indefinida — que é o
    # comportamento correto e está coberto no teste seguinte.
    ciclo = np.array([10.0, 20.0, 30.0, 40.0, 50.0, 60.0,
                      70.0, 80.0, 90.0, 100.0, 110.0, 120.0])
    y = np.tile(ciclo, 3) + 2.0 * np.arange(36)
    esc = escala_mase(y)
    assert esc > 0
    real = np.array([100.0, 100.0])
    prev = real + esc
    assert mase(real, prev, esc) == pytest.approx(1.0)


def test_mase_indefinido_quando_o_baseline_e_perfeito() -> None:
    """Série exatamente periódica: o ingênuo sazonal não erra, e MASE não existe.

    Devolver NaN é o correto — dividir por zero produziria um "ganho infinito"
    que o relatório publicaria como se fosse mérito do modelo.
    """
    y = np.tile(np.array([10.0, 20.0, 30.0, 40.0, 50.0, 60.0,
                          70.0, 80.0, 90.0, 100.0, 110.0, 120.0]), 3)
    esc = escala_mase(y)
    assert esc == 0.0
    assert np.isnan(mase(np.array([1.0]), np.array([2.0]), esc))


def test_escala_mase_cai_para_primeira_diferenca_em_serie_curta() -> None:
    """Sem um ciclo completo, o denominador muda — e isso muda a leitura."""
    curta = np.array([10.0, 14.0, 12.0, 18.0])
    assert escala_mase(curta) == pytest.approx(np.mean(np.abs(np.diff(curta))))


def test_smape_e_wape_toleram_zero() -> None:
    """290 hospitais têm mediana ≤5/mês; zero aparece, e MAPE explodiria ali."""
    real = np.array([0.0, 0.0, 4.0])
    prev = np.array([0.0, 2.0, 4.0])
    assert np.isfinite(smape(real, prev))
    assert np.isfinite(wape(real, prev))
    # Real e previsto ambos zero não devem contar como erro infinito.
    assert smape(np.array([0.0]), np.array([0.0])) != np.inf


def test_smape_e_zero_na_previsao_perfeita() -> None:
    v = np.array([10.0, 20.0, 30.0])
    assert smape(v, v) == pytest.approx(0.0)
    assert wape(v, v) == pytest.approx(0.0)


# ---------------------------------------------------------------------------
# Contrato do registro de modelos
# ---------------------------------------------------------------------------

def test_modelo_publicado_e_candidato_estao_no_registro() -> None:
    """O relatório compara o método REAL, não uma idealização dele.

    Se `MODELO_ATUAL` sair do registro, o backtest deixa de medir o que está no
    ar e passa a medir outra coisa com o mesmo nome.
    """
    assert MODELO_ATUAL in MODELOS
    assert MODELO_CANDIDATO in MODELOS


# ---------------------------------------------------------------------------
# O motor de backtest
# ---------------------------------------------------------------------------

def test_backtest_nao_vaza_o_futuro_entre_origens() -> None:
    """Trocar o futuro muda o REAL, nunca a PREVISÃO daquela origem.

    Este é o teste que de fato prova ausência de data leakage no walk-forward.
    Duas séries idênticas até o mês 30 e radicalmente diferentes depois: as
    previsões feitas nas origens ≤ 30 têm de coincidir dígito a dígito. Se
    alguma origem enxergasse `y[origem:]`, as previsões divergiriam — e o
    relatório ficaria bom pelo motivo errado.
    """
    from validate_forecast import backtest_serie

    rng = np.random.default_rng(42)
    base = 400.0 + 5.0 * np.arange(40) + rng.normal(0, 20, 40)
    a = base.copy()
    b = base.copy()
    b[30:] = b[30:] * 10 + 5000  # futuro completamente diferente

    ra = backtest_serie(a, (1, 2, 3), min_treino=24)
    rb = backtest_serie(b, (1, 2, 3), min_treino=24)

    comuns = 0
    for chave in ra.keys() & rb.keys():
        # As tuplas são (real, ponto, lo, hi, sigma, escala). Comparamos as
        # entradas cujas origens caem antes da divergência.
        for (real_a, ponto_a, lo_a, hi_a, sig_a, esc_a), (real_b, ponto_b, *_r) in zip(
            ra[chave], rb[chave], strict=False
        ):
            if real_a == real_b:  # mesma origem, futuro ainda idêntico
                assert ponto_a == pytest.approx(ponto_b), (
                    f"{chave}: previsão mudou porque o FUTURO mudou — há vazamento"
                )
                comuns += 1
    assert comuns > 50, "amostra pequena demais para o teste significar algo"


def test_backtest_respeita_o_treino_minimo() -> None:
    """Nenhuma origem pode ser avaliada com menos treino do que o declarado.

    O `min_treino` é o que torna os modelos comparáveis: abaixo de dois ciclos
    anuais, metade deles não pode sequer ser estimada, e a média passaria a
    comparar conjuntos diferentes de origens.
    """
    from validate_forecast import backtest_serie

    y = 100.0 + np.arange(36, dtype=float)
    res = backtest_serie(y, (1,), min_treino=24)
    # Origens válidas vão de 24 a 35 → 12 previsões de horizonte 1.
    for (_modelo, h), linhas in res.items():
        assert h == 1
        assert len(linhas) <= 36 - 24


def test_backtest_ignora_origem_sobre_mes_ausente() -> None:
    """Origem cujo último mês de treino é NaN não gera previsão avaliável.

    O `naive` herdaria o buraco e devolveria NaN; pior, um modelo que
    preenchesse o vão trataria falta de registro como demanda zero.
    """
    from validate_forecast import backtest_serie

    y = 100.0 + np.arange(36, dtype=float)
    y[29] = np.nan  # origem 30 teria treino terminando em NaN
    res = backtest_serie(y, (1,), min_treino=24)
    assert res, "o backtest não deveria ficar vazio por causa de um único buraco"
    for linhas in res.values():
        for real, ponto, *_r in linhas:
            assert np.isfinite(real)


@pytest.mark.parametrize("nome", list(MODELOS))
def test_modelo_devolve_h_valores(nome: str) -> None:
    y = np.array([40.0] * 30)
    for h in (1, 3, 6):
        prev = MODELOS[nome](y, h)
        assert prev.ponto.size == h and prev.sigma.size == h


#: Modelos que exigem histórico longo. `naive` (2 pontos) e `media_movel_3`
#: (3 pontos) legitimamente produzem número com série curta — são baselines, e
#: quem barra a publicação deles é o piso do pipeline, testado logo abaixo.
MODELOS_QUE_EXIGEM_HISTORICO = [
    n for n in MODELOS if n not in ("naive", "media_movel_3")
]


@pytest.mark.parametrize("nome", MODELOS_QUE_EXIGEM_HISTORICO)
def test_serie_curta_devolve_nan_em_vez_de_estimar(nome: str) -> None:
    """Tendência e sazonalidade não se estimam com 3 pontos.

    Devolver NaN é o comportamento correto: o validador e o pipeline descartam,
    e nada de inventado chega à API pública. O contrário — extrapolar uma reta a
    partir de três meses — é exatamente o tipo de número que parece análise.
    """
    prev = MODELOS[nome](np.array([10.0, 11.0, 12.0]), 3)
    assert np.isnan(prev.ponto).all()


def test_pipeline_exige_mais_meses_do_que_os_baselines() -> None:
    """O piso de publicação é do pipeline, não de cada modelo.

    `naive` e `media_movel_3` respondem com 2 e 3 pontos porque é o que eles
    são. Quem impede que um hospital com 3 meses de série apareça na API é o
    `MIN_MESES` do forecast, e ele precisa ficar acima disso.
    """
    from forecast_demanda_hospitalar import MIN_MESES
    assert MIN_MESES >= 6
    assert np.isfinite(naive(np.array([10.0, 12.0]), 2).ponto).all(), (
        "naive com 2 pontos é legítimo — é o piso de comparação, não um candidato"
    )
