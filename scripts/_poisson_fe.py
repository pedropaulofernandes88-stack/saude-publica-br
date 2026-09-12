"""
_poisson_fe.py — Poisson condicional de efeitos fixos, e a prova de que funciona
=================================================================================

Estimador de Hausman, Hall e Griliches (1984) para painel de contagem. Usado por
`analise_agua_mortalidade.py`.

POR QUE ESTE ESTIMADOR, E NÃO UMA REGRESSÃO COMUM
--------------------------------------------------
O desenho compara municípios que vigiam a água com municípios que não vigiam, e
municípios diferem em tudo: renda, urbanização, estrutura etária, acesso a
serviço, qualidade de registro. Um efeito fixo de município absorve **todo**
confundidor que não varia no tempo, medido ou não — é a única forma de controle
que não depende de eu ter pensado na variável certa.

O preço é que a exposição precisa **variar dentro do município**. Uma exposição
constante por município é apagada inteira pelo efeito fixo, e é por isso que a
exposição aqui é a vigilância do ano ANTERIOR, que muda ao longo do painel.

COMO OS EFEITOS FIXOS DESAPARECEM
----------------------------------
Condicionando na soma de contagens do município, as contagens dos seus anos
seguem uma multinomial cujas probabilidades não contêm o intercepto do
município. A log-verossimilhança condicional é

    ℓ(β) = Σ_i Σ_t  y_it · [ η_it − log Σ_s exp(η_is) ],   η = xβ + log(offset)

e ela não tem um parâmetro por município — o que importa num painel de 5.570
unidades, em que estimar um intercepto para cada uma seria mal condicionado.

POR QUE HÁ UM TESTE DE RECUPERAÇÃO NESTE ARQUIVO
-------------------------------------------------
Implementar estimador à mão só se justifica se ele for demonstrado. `autoteste()`
simula painel com efeito **conhecido** e intercepto de município variando duas
ordens de grandeza, e exige que o estimador recupere o valor verdadeiro dentro
de tolerância. Ele roda em `tests/test_poisson_fe.py`, e falha se a conta estiver
errada — que é a diferença entre usar um estimador e acreditar num.

O intervalo de confiança NÃO sai daqui. Ele vem de bootstrap de município, feito
por quem chama, pela mesma razão do resto do projeto: a unidade de reamostragem
tem de ser a unidade de análise.
"""
from __future__ import annotations

import numpy as np
from scipy.optimize import minimize


def _preparar(y, X, offset, grupos):
    """Ordena por grupo uma vez e devolve os limites de cada bloco.

    Ordenar aqui, e nao dentro da verossimilhanca, e' o que permite usar
    `reduceat` do numpy em vez de um laco Python sobre 5.570 municipios. Com o
    laco, cada avaliacao custava segundos e o bootstrap ficava inviavel.
    """
    ordem = np.argsort(grupos, kind="stable")
    g = np.asarray(grupos)[ordem]
    inicio = np.concatenate(([0], np.flatnonzero(g[1:] != g[:-1]) + 1))
    return (np.asarray(y, float)[ordem], np.asarray(X, float)[ordem],
            np.log(np.maximum(np.asarray(offset, float)[ordem], 1e-9)), inicio)


def _objetivo(beta, y, X, log_offset, inicio):
    """Log-verossimilhanca condicional NEGATIVA e o seu gradiente.

    O gradiente e' fechado: a derivada da multinomial condicional e'

        d/dbeta = - sum_it ( y_it - Y_i * p_it ) x_it

    com p_it a probabilidade do ano t dentro do municipio i. Dar o gradiente
    analitico, em vez de deixar o BFGS estima-lo por diferencas finitas,
    dispensa 11 avaliacoes extra por iteracao — e e' a diferenca entre um ajuste
    de minutos e um de centesimos de segundo.
    """
    eta = X @ beta + log_offset
    # max por grupo, para estabilizar a exponencial
    mx = np.maximum.reduceat(eta, inicio)
    e = np.exp(eta - np.repeat(mx, np.diff(np.append(inicio, len(eta)))))
    soma_e = np.add.reduceat(e, inicio)
    tam = np.diff(np.append(inicio, len(eta)))
    p = e / np.repeat(soma_e, tam)                  # prob. dentro do grupo
    Y = np.add.reduceat(y, inicio)                  # total do grupo

    log_p = np.log(np.maximum(p, 1e-300))
    fx = -float(np.dot(y, log_p))
    grad = -(X * (y - np.repeat(Y, tam) * p)[:, None]).sum(axis=0)
    return fx, grad


def ajustar(y: np.ndarray, X: np.ndarray, offset: np.ndarray,
            grupos: np.ndarray) -> np.ndarray:
    """Devolve beta. `grupos` e' o indice de municipio; `offset`, pessoas-ano.

    Municipio com contagem total zero nao contribui — a multinomial condicional
    dele e' degenerada — e sai aqui, em vez de gerar NaN silencioso adiante.
    """
    y = np.asarray(y, dtype=float)
    X = np.asarray(X, dtype=float)
    offset = np.asarray(offset, dtype=float)
    grupos = np.asarray(grupos)

    total = {}
    for gi, yi in zip(grupos, y):
        total[gi] = total.get(gi, 0.0) + yi
    fica = np.array([total[gi] > 0 for gi in grupos])
    if not fica.any():
        return np.full(X.shape[1], np.nan)
    y, X, offset, grupos = y[fica], X[fica], offset[fica], grupos[fica]

    ys, Xs, log_offset, inicio = _preparar(y, X, offset, grupos)
    r = minimize(_objetivo, np.zeros(X.shape[1]), jac=True,
                 args=(ys, Xs, log_offset, inicio), method="BFGS",
                 options={"maxiter": 200, "gtol": 1e-7})
    return r.x if r.x is not None else np.full(X.shape[1], np.nan)


def ajustar_matriz(Y: np.ndarray, X: np.ndarray, OFF: np.ndarray) -> np.ndarray:
    """Versão MATRICIAL, para painel balanceado. Sem laço e sem `reduceat`.

    `Y` e `OFF` têm forma (M, T) — municípios por anos — e `X` tem (M, T, K).
    O painel deste projeto é balanceado (5.570 municípios × 9 anos, conferido),
    e isso muda a conta de ordem prática: cada município é uma LINHA, de modo
    que somar dentro do município é somar ao longo de um eixo do numpy.

    POR QUE ISTO EXISTE AO LADO DE `ajustar`
    -----------------------------------------
    `ajustar` aceita painel desbalanceado e ordena por grupo. Funciona, e é
    lenta o suficiente para inviabilizar o bootstrap: uma réplica exigia
    remontar 5.570 pedaços, e a primeira das cinco causas não terminou em vinte
    minutos. Na forma matricial a réplica é `Y[amostra]` — indexação de linhas,
    sem cópia pedaço a pedaço —, e o município sorteado duas vezes entra duas
    vezes sem precisar de identificador novo.
    """
    M, T = Y.shape
    K = X.shape[2]
    Xf = X.reshape(M * T, K)
    log_off = np.log(np.maximum(OFF, 1e-9))
    total = Y.sum(axis=1)
    fica = total > 0
    if not fica.any():
        return np.full(K, np.nan)

    Yv, Xv = Y[fica], X[fica]
    offv, totv = log_off[fica], total[fica]
    Mv = Yv.shape[0]
    Xv2 = Xv.reshape(Mv * T, K)

    def objetivo(beta):
        eta = (Xv2 @ beta).reshape(Mv, T) + offv
        eta = eta - eta.max(axis=1, keepdims=True)
        e = np.exp(eta)
        p = e / e.sum(axis=1, keepdims=True)
        fx = -float((Yv * np.log(np.maximum(p, 1e-300))).sum())
        resid = (Yv - totv[:, None] * p).reshape(Mv * T)
        return fx, -(Xv2 * resid[:, None]).sum(axis=0)

    r = minimize(objetivo, np.zeros(K), jac=True, method="BFGS",
                 options={"maxiter": 200, "gtol": 1e-7})
    del Xf
    return r.x if r.x is not None else np.full(K, np.nan)


def autoteste(semente: int = 7, n_mun: int = 400, n_ano: int = 9,
              beta_verdadeiro: tuple[float, ...] = (-0.4, 0.25)) -> dict:
    """Simula painel com efeito CONHECIDO e mede se o estimador o recupera.

    O intercepto de município varia duas ordens de grandeza de propósito: é
    exatamente o confundidor que o efeito fixo precisa absorver, e um estimador
    que ignorasse os efeitos fixos devolveria viés grande aqui.
    """
    rng = np.random.default_rng(semente)
    beta = np.array(beta_verdadeiro, dtype=float)

    mun = np.repeat(np.arange(n_mun), n_ano)
    # intercepto por municipio: de exp(-3) a exp(+2), ~150x entre extremos
    alfa = rng.uniform(-3.0, 2.0, size=n_mun)[mun]
    pop = np.exp(rng.uniform(7.0, 13.0, size=n_mun))[mun]     # 1 mil a 440 mil

    x1 = rng.binomial(1, 0.3, size=mun.size).astype(float)     # exposicao binaria
    x2 = rng.normal(0, 1, size=mun.size)                       # covariavel continua
    X = np.column_stack([x1, x2])

    lam = pop * np.exp(alfa + X @ beta)
    y = rng.poisson(lam).astype(float)

    est = ajustar(y, X, pop, mun)
    return {"verdadeiro": beta.tolist(), "estimado": est.tolist(),
            "erro_absoluto": np.abs(est - beta).tolist(),
            "municipios": n_mun, "anos": n_ano, "obitos": int(y.sum())}


if __name__ == "__main__":
    import json
    print(json.dumps(autoteste(), indent=2))
