"""
_series_forecast.py — núcleo de previsão de séries mensais e sua avaliação
==========================================================================

Módulo compartilhado por `forecast_demanda_hospitalar.py` (que publica) e
`validate_forecast.py` (que mede). Existir separado é o que impede o erro
clássico: o script de publicação usar um método e o relatório de validação
medir outro.

O QUE ESTAVA ERRADO ANTES
-------------------------
O forecast publicado ajustava `y = a + b·t` com `t = np.arange(n)` — a POSIÇÃO
da linha na tabela, não o mês do calendário. Em 833 dos 4.848 hospitais a série
tem buraco (mês sem AIH), e para eles o eixo temporal estava distorcido: dois
pontos separados por seis meses contavam como vizinhos. Aqui `t` é sempre o
índice de calendário (ano*12 + mês), e buraco é buraco.

O intervalo era `previsão ± 1,96·desvio-padrão dos resíduos do ajuste`, constante
em todo horizonte e estimado dentro da amostra. Não é intervalo de predição: não
cresce com a distância da extrapolação nem incorpora a incerteza dos parâmetros.
Aqui cada modelo devolve `sigma_h`, o desvio-padrão do erro de previsão h passos
à frente, estimado SÓ com dados de treino — o que torna a cobertura empírica uma
medida honesta de calibração.

Não havia sazonalidade. Na série nacional (2022–2024) fevereiro fica 5,9% abaixo
da tendência e agosto 4,3% acima: ignorar isso enviesa sistematicamente previsões
de janeiro a março, que é exatamente o horizonte publicado.

CONVENÇÕES
----------
- Série = vetor `y` indexado por `t` (índice de calendário), com NaN onde falta.
- Todo modelo recebe apenas o passado (`y[:origem]`) e devolve h passos à frente.
  Vazamento é impossível por construção da assinatura, não por disciplina.
- Contagens: previsões são truncadas em zero. Internação negativa não existe.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

# Sazonalidade mensal. Séries do SIH são mensais; 12 é o único período plausível.
PERIODO = 12

# Mínimo de pontos observados para um ajuste de tendência não ser ruído.
MIN_PONTOS_TENDENCIA = 6

# Mínimo para tentar componente sazonal: é preciso ao menos dois ciclos para
# separar sazonalidade de tendência sem confundir uma com a outra.
MIN_PONTOS_SAZONAL = 24


# ---------------------------------------------------------------------------
# Calendário
# ---------------------------------------------------------------------------

def indice_mes(ano_mes: str) -> int:
    """'2024-03' → índice absoluto de meses. Base arbitrária, só a diferença importa."""
    ano, mes = ano_mes.split("-")
    return int(ano) * 12 + (int(mes) - 1)


def mes_de_indice(i: int) -> str:
    """Inverso de `indice_mes`."""
    return f"{i // 12}-{i % 12 + 1:02d}"


def serie_regular(meses: list[str], valores: list[float]) -> tuple[int, np.ndarray]:
    """Reamostra a série no calendário, com NaN nos meses ausentes.

    Devolve (índice do primeiro mês, vetor). O vetor tem um elemento por mês do
    calendário entre o primeiro e o último observado — buracos incluídos, porque
    é justamente o que o modelo antigo apagava.
    """
    if not meses:
        return 0, np.array([], dtype=float)
    idx = [indice_mes(m) for m in meses]
    ordem = np.argsort(idx)
    idx = [idx[i] for i in ordem]
    val = [float(valores[i]) for i in ordem]
    inicio, fim = idx[0], idx[-1]
    y = np.full(fim - inicio + 1, np.nan)
    for i, v in zip(idx, val, strict=True):
        y[i - inicio] = v
    return inicio, y


# ---------------------------------------------------------------------------
# Resultado de uma previsão
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Previsao:
    """Previsão pontual e incerteza para horizontes 1..H.

    `sigma` é o desvio-padrão do ERRO DE PREVISÃO em cada horizonte, estimado
    apenas com o treino. O intervalo é montado por quem consome, com o z que
    quiser, e a cobertura empírica no backtest diz se `sigma` está calibrado.
    """

    ponto: np.ndarray
    sigma: np.ndarray
    modelo: str

    def intervalo(self, z: float = 1.96) -> tuple[np.ndarray, np.ndarray]:
        return np.maximum(self.ponto - z * self.sigma, 0.0), self.ponto + z * self.sigma


def _vazio(h: int, modelo: str) -> Previsao:
    return Previsao(np.full(h, np.nan), np.full(h, np.nan), modelo)


# ---------------------------------------------------------------------------
# Baselines e modelos
# ---------------------------------------------------------------------------
# Assinatura comum: (y_treino, h) -> Previsao. `y_treino` é o vetor regular do
# calendário, podendo conter NaN; o último elemento é o mês imediatamente
# anterior ao primeiro horizonte previsto.

def _fator_sazonal(h: int) -> np.ndarray:
    """Crescimento do erro de previsão de um método sazonal ingênuo.

    Para o ingênuo sazonal, a variância do erro h passos à frente é
    σ²·(1 + ⌊(h−1)/m⌋): ela só cresce quando o horizonte ultrapassa um ciclo
    inteiro, porque até lá cada previsão usa um mês homólogo diferente e
    igualmente distante. Com m = 12 e horizontes de 1 a 12 o fator é 1 — o
    intervalo NÃO deve alargar, e alargá-lo por analogia com o passeio aleatório
    superestimaria a incerteza.
    """
    hs = np.arange(1, h + 1)
    return np.sqrt(1.0 + (hs - 1) // PERIODO)


def naive(y: np.ndarray, h: int) -> Previsao:
    """Último valor observado, repetido. O piso de qualquer comparação."""
    obs = y[~np.isnan(y)]
    if obs.size < 2:
        return _vazio(h, "naive")
    d = np.diff(obs)
    s1 = float(np.std(d, ddof=1)) if d.size > 1 else 0.0
    # Erro de um passeio aleatório acumula com sqrt(h).
    return Previsao(np.full(h, max(obs[-1], 0.0)),
                    s1 * np.sqrt(np.arange(1, h + 1)), "naive")


def seasonal_naive(y: np.ndarray, h: int) -> Previsao:
    """Valor do mesmo mês do ano anterior.

    Baseline obrigatório em série sazonal: um modelo que não o supere não está
    capturando nada além do calendário.
    """
    if y.size < PERIODO:
        return _vazio(h, "seasonal_naive")
    ponto = np.empty(h)
    for k in range(1, h + 1):
        pos = y.size - PERIODO + k - 1
        # Se o mês homólogo faltou, recua um ciclo por vez.
        while pos >= 0 and np.isnan(y[pos]):
            pos -= PERIODO
        ponto[k - 1] = y[pos] if pos >= 0 and not np.isnan(y[pos]) else np.nan
    if np.isnan(ponto).all():
        return _vazio(h, "seasonal_naive")
    dif = y[PERIODO:] - y[:-PERIODO]
    dif = dif[~np.isnan(dif)]
    s = float(np.std(dif, ddof=1)) if dif.size > 1 else 0.0
    return Previsao(np.maximum(np.nan_to_num(ponto, nan=np.nanmean(ponto)), 0.0),
                    s * _fator_sazonal(h), "seasonal_naive")


def media_movel(y: np.ndarray, h: int, janela: int = 3) -> Previsao:
    """Média dos últimos `janela` meses observados, repetida."""
    obs = y[~np.isnan(y)]
    if obs.size < janela:
        return _vazio(h, f"media_movel_{janela}")
    m = float(np.mean(obs[-janela:]))
    resid = obs[janela:] - np.array(
        [np.mean(obs[i - janela:i]) for i in range(janela, obs.size)]
    ) if obs.size > janela else np.array([])
    s = float(np.std(resid, ddof=1)) if resid.size > 1 else 0.0
    return Previsao(np.full(h, max(m, 0.0)),
                    s * np.sqrt(np.arange(1, h + 1)), f"media_movel_{janela}")


def tendencia_linear(y: np.ndarray, h: int) -> Previsao:
    """OLS sobre o tempo de CALENDÁRIO — o método hoje publicado, corrigido.

    Duas diferenças em relação ao que está no ar:

    1. `t` é o índice de calendário, não a posição na tabela. Com buraco na
       série, a versão antiga comprimia o eixo e inclinava a reta errado.
    2. O intervalo é o intervalo de predição da regressão, que cresce com a
       distância da extrapolação e inclui a incerteza dos coeficientes — não
       um desvio-padrão de resíduo constante.
    """
    obs = ~np.isnan(y)
    n = int(obs.sum())
    if n < MIN_PONTOS_TENDENCIA:
        return _vazio(h, "tendencia_linear")
    t = np.arange(y.size, dtype=float)[obs]
    v = y[obs]
    b, a = np.polyfit(t, v, 1)
    resid = v - (a + b * t)
    gl = n - 2
    s2 = float(resid @ resid / gl) if gl > 0 else 0.0
    t_bar = t.mean()
    sxx = float(((t - t_bar) ** 2).sum()) or 1.0

    t_fut = np.arange(y.size, y.size + h, dtype=float)
    ponto = np.maximum(a + b * t_fut, 0.0)
    # se² de predição: variância do erro + variância do valor ajustado no ponto.
    se = np.sqrt(s2 * (1.0 + 1.0 / n + (t_fut - t_bar) ** 2 / sxx))
    return Previsao(ponto, se, "tendencia_linear")


def tendencia_linear_publicada(y: np.ndarray, h: int) -> Previsao:
    """Réplica exata do método hoje no ar, para medir o custo dos seus defeitos.

    Reproduz `forecast_demanda_hospitalar.py` como estava antes desta revisão:

    - `t = np.arange(n)` sobre as linhas OBSERVADAS, ignorando o calendário: uma
      série com buraco tem o eixo temporal comprimido, e a inclinação sai errada;
    - banda = ±1,96 · desvio-padrão dos resíduos do ajuste (ddof=2), CONSTANTE em
      todo horizonte, estimada dentro da amostra. Não é intervalo de predição:
      não cresce com a distância da extrapolação nem carrega a incerteza dos
      coeficientes.

    Mantido no registro exclusivamente como termo de comparação. Não use para
    publicar — `tendencia_linear` é a mesma ideia sem os dois defeitos.
    """
    obs = y[~np.isnan(y)]
    n = obs.size
    if n < MIN_PONTOS_TENDENCIA:
        return _vazio(h, "tendencia_linear_publicada")
    t = np.arange(n, dtype=float)
    b, a = np.polyfit(t, obs, 1)
    resid_std = float(np.std(obs - (a + b * t), ddof=2)) if n > 2 else 0.0
    t_fut = np.arange(n, n + h, dtype=float)
    return Previsao(np.maximum(a + b * t_fut, 0.0),
                    np.full(h, resid_std), "tendencia_linear_publicada")


def snaive_drift(y: np.ndarray, h: int) -> Previsao:
    """Sazonal ingênuo corrigido pela tendência anual.

    Combina o que cada baseline puro acerta: o `seasonal_naive` conhece o
    formato do ano mas ignora o crescimento; a tendência linear conhece o
    crescimento mas apaga o formato. A série de internações do SIH tem os dois
    (≈ +0,5%/mês de tendência e ±6% de amplitude sazonal).

    Previsão = valor do mês homólogo + 12·b, com b a inclinação mensal estimada
    por OLS no treino.
    """
    obs = ~np.isnan(y)
    n = int(obs.sum())
    if y.size < PERIODO or n < MIN_PONTOS_SAZONAL:
        return _vazio(h, "snaive_drift")
    t = np.arange(y.size, dtype=float)[obs]
    v = y[obs]
    b, _a = np.polyfit(t, v, 1)

    base = seasonal_naive(y, h)
    if np.isnan(base.ponto).all():
        return _vazio(h, "snaive_drift")
    # O mês homólogo está 12 meses atrás; a tendência acumulada nesse intervalo
    # é 12·b. É a correção mínima que devolve o nível sem destruir o formato.
    ponto = np.maximum(base.ponto + b * PERIODO, 0.0)

    # sigma dos resíduos do PRÓPRIO método dentro do treino, não do sazonal puro:
    # medir o erro do sazonal cru superestimaria a incerteza deste, que já
    # corrigiu o viés de nível.
    resid = y[PERIODO:] - (y[:-PERIODO] + b * PERIODO)
    resid = resid[~np.isnan(resid)]
    s = float(np.std(resid, ddof=1)) if resid.size > 1 else 0.0
    return Previsao(ponto, s * _fator_sazonal(h), "snaive_drift")


def tendencia_sazonal(y: np.ndarray, h: int) -> Previsao:
    """Regressão com tendência + dummies de mês (decomposição aditiva).

    O modelo mais completo que ainda cabe em 24–36 pontos. Estima tendência e os
    doze efeitos mensais numa só regressão, então o intervalo sai com os graus de
    liberdade corretos — ao contrário de somar duas etapas ajustadas em separado.

    Com 36 pontos e 13 parâmetros, os graus de liberdade ficam apertados: por
    isso `MIN_PONTOS_SAZONAL` é a porta de entrada e o backtest decide se ele
    vale a pena por estrato, em vez de assumir que mais parâmetros é melhor.
    """
    obs = ~np.isnan(y)
    n = int(obs.sum())
    if n < MIN_PONTOS_SAZONAL:
        return _vazio(h, "tendencia_sazonal")
    pos = np.arange(y.size)[obs].astype(float)
    v = y[obs]
    meses = (np.arange(y.size)[obs] % PERIODO).astype(int)
    # Matriz: intercepto, tendência, 11 dummies (dezembro é a referência).
    X = np.zeros((n, 2 + PERIODO - 1))
    X[:, 0] = 1.0
    X[:, 1] = pos
    for j in range(PERIODO - 1):
        X[:, 2 + j] = (meses == j).astype(float)
    p = X.shape[1]
    gl = n - p
    if gl < 4:  # sem folga para estimar variância, o intervalo seria fantasia
        return _vazio(h, "tendencia_sazonal")
    beta, *_ = np.linalg.lstsq(X, v, rcond=None)
    resid = v - X @ beta
    s2 = float(resid @ resid / gl)
    try:
        xtx_inv = np.linalg.inv(X.T @ X)
    except np.linalg.LinAlgError:
        return _vazio(h, "tendencia_sazonal")

    pos_fut = np.arange(y.size, y.size + h, dtype=float)
    Xf = np.zeros((h, p))
    Xf[:, 0] = 1.0
    Xf[:, 1] = pos_fut
    for k in range(h):
        m = int(pos_fut[k]) % PERIODO
        if m < PERIODO - 1:
            Xf[k, 2 + m] = 1.0
    ponto = np.maximum(Xf @ beta, 0.0)
    se = np.sqrt(s2 * (1.0 + np.einsum("ij,jk,ik->i", Xf, xtx_inv, Xf)))
    return Previsao(ponto, se, "tendencia_sazonal")


#: Registro dos métodos avaliados. A ordem é a de apresentação no relatório.
MODELOS = {
    "naive": naive,
    "seasonal_naive": seasonal_naive,
    "media_movel_3": lambda y, h: media_movel(y, h, 3),
    "tendencia_linear_publicada": tendencia_linear_publicada,
    "tendencia_linear": tendencia_linear,
    "snaive_drift": snaive_drift,
    "tendencia_sazonal": tendencia_sazonal,
}

#: O que está publicado hoje — presente no registro para que o relatório meça o
#: método real, não uma idealização dele.
MODELO_ATUAL = "tendencia_linear_publicada"

#: Candidato a substituí-lo: mesma ideia, eixo de calendário e intervalo de
#: predição de verdade. A troca só se justifica se o backtest mostrar ganho.
MODELO_CANDIDATO = "tendencia_linear"

#: Baseline contra o qual um modelo precisa provar valor (MASE < 1 equivale a
#: superar o ingênuo sazonal do treino).
BASELINE_MASE = "seasonal_naive"


# ---------------------------------------------------------------------------
# Métricas
# ---------------------------------------------------------------------------

def mae(real: np.ndarray, prev: np.ndarray) -> float:
    return float(np.mean(np.abs(prev - real)))


def rmse(real: np.ndarray, prev: np.ndarray) -> float:
    return float(np.sqrt(np.mean((prev - real) ** 2)))


def smape(real: np.ndarray, prev: np.ndarray) -> float:
    """sMAPE em %, com denominador protegido.

    Preferido ao MAPE porque grande parte dos hospitais tem volume baixo — 290
    deles medianamente ≤5 internações/mês — e o MAPE explode quando o real se
    aproxima de zero, produzindo um número que diz mais sobre o denominador do
    que sobre o modelo.
    """
    den = np.abs(real) + np.abs(prev)
    ok = den > 0
    if not ok.any():
        return float("nan")
    return float(100.0 * np.mean(2.0 * np.abs(prev[ok] - real[ok]) / den[ok]))


def wape(real: np.ndarray, prev: np.ndarray) -> float:
    """Erro absoluto ponderado pelo volume, em %.

    Robusto a zeros e o que um gestor de rede realmente quer saber: de todas as
    internações do período, que fração o modelo errou.
    """
    s = float(np.sum(np.abs(real)))
    return float("nan") if s == 0 else float(100.0 * np.sum(np.abs(prev - real)) / s)


def escala_mase(y_treino: np.ndarray, periodo: int = PERIODO) -> float:
    """Denominador do MASE: erro médio do ingênuo sazonal DENTRO do treino.

    Sazonal quando há ao menos um ciclo completo de diferenças; caso contrário
    cai para a diferença de primeira ordem, e isso fica registrado no relatório
    porque muda a interpretação do número.
    """
    obs = y_treino.copy()
    if obs.size > periodo:
        d = obs[periodo:] - obs[:-periodo]
        d = d[~np.isnan(d)]
        if d.size >= 2:
            return float(np.mean(np.abs(d)))
    v = obs[~np.isnan(obs)]
    if v.size < 2:
        return float("nan")
    return float(np.mean(np.abs(np.diff(v))))


def mase(real: np.ndarray, prev: np.ndarray, escala: float) -> float:
    """MASE < 1 ⇒ melhor que o ingênuo sazonal do treino. É a régua de valor."""
    if not np.isfinite(escala) or escala <= 0:
        return float("nan")
    return float(np.mean(np.abs(prev - real)) / escala)


def cobertura(real: np.ndarray, lo: np.ndarray, hi: np.ndarray) -> float:
    """% de observações dentro do intervalo. Deve tender ao nominal (95%)."""
    ok = np.isfinite(lo) & np.isfinite(hi)
    if not ok.any():
        return float("nan")
    return float(100.0 * np.mean((real[ok] >= lo[ok]) & (real[ok] <= hi[ok])))


def largura_relativa(ponto: np.ndarray, lo: np.ndarray, hi: np.ndarray) -> float:
    """Largura média do intervalo como % da previsão.

    Anda junto com a cobertura: um intervalo cobre 100% por estar calibrado ou
    por ser largo demais para dizer alguma coisa, e só os dois números juntos
    distinguem os dois casos.
    """
    ok = np.isfinite(lo) & np.isfinite(hi) & (ponto > 0)
    if not ok.any():
        return float("nan")
    return float(100.0 * np.mean((hi[ok] - lo[ok]) / ponto[ok]))
