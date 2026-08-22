"""
validate_forecast.py — backtesting temporal do forecast de demanda hospitalar
==============================================================================

Responde, com número, à pergunta que a plataforma publicava sem responder:
a previsão de demanda por hospital é melhor que um baseline trivial, e o
intervalo declarado cobre o que promete?

MÉTODO
------
Validação por **origem móvel** (rolling origin / walk-forward). Para cada
hospital e cada origem `o` a partir de um mínimo de meses de treino:

    treino = série[:o]          teste = série[o], série[o+1], série[o+2]

O modelo enxerga exclusivamente `série[:o]`. A separação é estrutural — as
funções de `_series_forecast` recebem só o passado —, não uma disciplina que
alguém precise lembrar de manter. `train_test_split` aleatório seria
cientificamente inválido aqui e não existe neste arquivo.

Cada modelo é medido por horizonte separadamente. Uma métrica agregada única
esconderia a deterioração do horizonte longo, que é justamente o que interessa
a quem planeja.

MÉTRICAS
--------
MAE, RMSE, sMAPE, WAPE, MASE, cobertura do IC95% e largura relativa do IC.
MASE usa como denominador o erro do ingênuo sazonal DENTRO do treino de cada
origem: MASE < 1 significa que o modelo supera esse baseline. É a régua de
valor, e um modelo que não a passa não deveria ser publicado.

sMAPE e WAPE em vez de MAPE porque 290 hospitais têm mediana ≤ 5 internações
por mês: com real perto de zero, o MAPE mede o denominador, não o modelo.

PANDEMIA E COMPLETUDE
---------------------
A série do SIH hospitalar começa em 2022-01 — depois do choque agudo de 2020–21,
mas dentro do período de recuperação. Nenhum ponto é removido: remover ano
"atípico" sem critério é a forma mais fácil de fabricar um resultado bom. O
efeito aparece nas métricas por origem, que o relatório publica separadamente.

Meses ausentes no meio da série entram como NaN e não são preenchidos. Prever um
mês sem AIH como se fosse zero de demanda confundiria falha de registro com
queda real de internação — o erro que este projeto declara evitar em todo o
resto da metodologia.

USO
---
    .venv311/Scripts/python scripts/validate_forecast.py
    .venv311/Scripts/python scripts/validate_forecast.py --amostra 400
    .venv311/Scripts/python scripts/validate_forecast.py --horizontes 1 3 6

Saídas em `data/validacao/`: CSV (uma linha por modelo × horizonte × estrato),
JSON (mesmos números, para consumo programático) e Markdown (o relatório lido
por humanos). Reprodutível: sem aleatoriedade, sem rede.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _series_forecast import (  # noqa: E402
    BASELINE_MASE,
    MODELO_ATUAL,
    MODELOS,
    escala_mase,
    serie_regular,
)

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parents[1]
MARTS = ROOT / "data" / "marts"
SAIDA = ROOT / "data" / "validacao"
FONTE = MARTS / "mart_demanda_mensal_hospital.parquet"

Z95 = 1.959963984540054

# Treino mínimo antes da primeira origem. 24 = dois ciclos anuais, o mínimo para
# que um modelo sazonal seja sequer identificável; usar menos compararia modelos
# em condições onde metade deles não pode existir.
MIN_TREINO = 24

HORIZONTES_PADRAO = (1, 2, 3)

# Faixas de volume mensal mediano. O corte não é estético: 20% dos hospitais têm
# ≤ 20 internações/mês, e agregar tudo numa métrica só deixaria o desempenho nos
# pequenos invisível atrás do peso dos grandes.
FAIXAS = [
    ("≤5/mês", 0, 5),
    ("6–20/mês", 5, 20),
    ("21–100/mês", 20, 100),
    ("101–500/mês", 100, 500),
    (">500/mês", 500, float("inf")),
]


def faixa_de(mediana: float) -> str:
    for nome, lo, hi in FAIXAS:
        if lo < mediana <= hi:
            return nome
    return FAIXAS[0][0]


# ---------------------------------------------------------------------------
# Acumulador de estatísticas suficientes
# ---------------------------------------------------------------------------

@dataclass
class Acumulador:
    """Estatísticas suficientes para todas as métricas, sem guardar as previsões.

    São ~915 mil previsões (5.083 hospitais × origens × horizontes × modelos).
    Guardá-las para agregar depois custaria memória sem acrescentar nada: toda
    métrica do relatório é função destes somatórios.
    """

    n: int = 0
    soma_abs: float = 0.0
    soma_sq: float = 0.0
    soma_real: float = 0.0
    soma_smape: float = 0.0
    n_smape: int = 0
    soma_escalado: float = 0.0
    n_escalado: int = 0
    n_dentro: int = 0
    n_intervalo: int = 0
    soma_largura: float = 0.0
    n_largura: int = 0
    hospitais: set = field(default_factory=set)
    #: |erro| / sigma de cada previsão. Guardado porque calibração é quantil, e
    #: quantil não sai de somatório. É a única lista que este acumulador mantém.
    razoes: list = field(default_factory=list)

    def somar(self, cnes: str, real: np.ndarray, ponto: np.ndarray,
              lo: np.ndarray, hi: np.ndarray, sigma: np.ndarray, escala: float) -> None:
        ok = np.isfinite(ponto) & np.isfinite(real)
        if not ok.any():
            return
        real, ponto = real[ok], ponto[ok]
        lo, hi = lo[ok], hi[ok]
        sigma = sigma[ok]
        err = np.abs(ponto - real)

        self.n += real.size
        self.soma_abs += float(err.sum())
        self.soma_sq += float(((ponto - real) ** 2).sum())
        self.soma_real += float(np.abs(real).sum())
        self.hospitais.add(cnes)

        den = np.abs(real) + np.abs(ponto)
        m = den > 0
        if m.any():
            self.soma_smape += float((200.0 * err[m] / den[m]).sum())
            self.n_smape += int(m.sum())

        if np.isfinite(escala) and escala > 0:
            self.soma_escalado += float((err / escala).sum())
            self.n_escalado += real.size

        vi = np.isfinite(lo) & np.isfinite(hi)
        if vi.any():
            self.n_dentro += int(((real[vi] >= lo[vi]) & (real[vi] <= hi[vi])).sum())
            self.n_intervalo += int(vi.sum())
            pos = vi & (ponto > 0)
            if pos.any():
                self.soma_largura += float((100.0 * (hi[pos] - lo[pos]) / ponto[pos]).sum())
                self.n_largura += int(pos.sum())
            # sigma vem do modelo, não da meia-largura: o limite inferior é
            # truncado em zero (internação negativa não existe), e reconstruir
            # sigma a partir de (hi−lo)/2z o subestimaria justamente nos
            # hospitais de baixo volume, que são um quinto da base.
            usa = vi & np.isfinite(sigma) & (sigma > 0)
            if usa.any():
                self.razoes.extend(
                    (np.abs(ponto[usa] - real[usa]) / sigma[usa]).tolist())

    def fator_calibracao(self, nominal: float = 0.95) -> float:
        """Multiplicador de `sigma` que faria o IC cobrir o nominal de verdade.

        É o quantil empírico de |erro|/sigma. Se o modelo estivesse calibrado sob
        normalidade, daria ≈ 1,96 e a razão fator/1,96 seria 1. Acima disso, o
        intervalo declarado é estreito demais — e o número diz exatamente quanto.

        Calibração assim é legítima porque usa apenas o passado: o conjunto de
        calibração é o histórico de backtest, e a aplicação é para o futuro.
        """
        if len(self.razoes) < 100:
            return float("nan")
        return float(np.quantile(np.asarray(self.razoes), nominal))

    def resumo(self) -> dict:
        def div(a: float, b: int) -> float:
            return float(a / b) if b else float("nan")
        fator = self.fator_calibracao()
        return {
            "n_previsoes": self.n,
            "n_hospitais": len(self.hospitais),
            "mae": div(self.soma_abs, self.n),
            "rmse": float(np.sqrt(self.soma_sq / self.n)) if self.n else float("nan"),
            "smape_pct": div(self.soma_smape, self.n_smape),
            "wape_pct": float(100.0 * self.soma_abs / self.soma_real) if self.soma_real else float("nan"),
            "mase": div(self.soma_escalado, self.n_escalado),
            "cobertura_ic95_pct": float(100.0 * self.n_dentro / self.n_intervalo) if self.n_intervalo else float("nan"),
            "largura_ic_pct_da_previsao": div(self.soma_largura, self.n_largura),
            # z empírico que entregaria 95% de cobertura, e quanto ele excede o
            # z=1,96 assumido. >1 significa intervalo publicado estreito demais.
            "z_empirico_p95": fator,
            "fator_alargamento_necessario": float(fator / Z95) if np.isfinite(fator) else float("nan"),
        }


# ---------------------------------------------------------------------------
# Backtest
# ---------------------------------------------------------------------------

def backtest_serie(
    y: np.ndarray, horizontes: tuple[int, ...], min_treino: int,
) -> dict[tuple[str, int], list[tuple[float, float, float, float, float]]]:
    """Roda todos os modelos em todas as origens válidas de UMA série.

    Devolve, por (modelo, horizonte), a lista de
    (real, ponto, lo, hi, escala_mase). Nenhum modelo recebe `y[origem:]`.
    """
    h_max = max(horizontes)
    fora: dict[tuple[str, int], list] = defaultdict(list)

    for origem in range(min_treino, y.size):
        treino = y[:origem]
        # Origem sobre um mês não observado não gera previsão avaliável: o
        # "último mês conhecido" seria NaN e o naive herdaria o buraco.
        if np.isnan(treino[-1]):
            continue
        n_obs = int((~np.isnan(treino)).sum())
        if n_obs < min_treino:
            continue

        escala = escala_mase(treino)
        alvos = np.array([y[origem + k - 1] if origem + k - 1 < y.size else np.nan
                          for k in range(1, h_max + 1)])
        if np.isnan(alvos).all():
            continue

        for nome, fn in MODELOS.items():
            prev = fn(treino, h_max)
            lo, hi = prev.intervalo(Z95)
            for h in horizontes:
                if h > h_max or origem + h - 1 >= y.size:
                    continue
                real = alvos[h - 1]
                if not np.isfinite(real):
                    continue
                fora[(nome, h)].append(
                    (float(real), float(prev.ponto[h - 1]),
                     float(lo[h - 1]), float(hi[h - 1]),
                     float(prev.sigma[h - 1]), escala)
                )
    return fora


def rodar(
    demanda: pd.DataFrame, horizontes: tuple[int, ...], min_treino: int,
    amostra: int | None, quieto: bool = False,
) -> tuple[dict, dict]:
    """Backtest sobre todos os hospitais. Devolve (geral, por_faixa)."""
    grupos = list(demanda.groupby("cnes"))
    if amostra:
        # Amostra determinística: os `amostra` primeiros CNES em ordem. Sem RNG,
        # para que duas execuções do relatório produzam exatamente o mesmo número.
        grupos = sorted(grupos, key=lambda kv: str(kv[0]))[:amostra]

    geral: dict[tuple[str, int], Acumulador] = defaultdict(Acumulador)
    por_faixa: dict[tuple[str, str, int], Acumulador] = defaultdict(Acumulador)

    total = len(grupos)
    for i, (cnes, g) in enumerate(grupos, 1):
        if not quieto and (i % 500 == 0 or i == total):
            print(f"  ... {i:,}/{total:,} hospitais", flush=True)
        g = g.sort_values("ano_mes")
        _inicio, y = serie_regular(g["ano_mes"].tolist(), g["internacoes"].tolist())
        if y.size <= min_treino:
            continue
        faixa = faixa_de(float(np.nanmedian(y)))

        for (modelo, h), linhas in backtest_serie(y, horizontes, min_treino).items():
            if not linhas:
                continue
            arr = np.array(linhas, dtype=float)
            real, ponto, lo, hi = arr[:, 0], arr[:, 1], arr[:, 2], arr[:, 3]
            sigma, esc = arr[:, 4], arr[:, 5]
            # A escala do MASE varia por origem; como o acumulador soma o erro
            # escalado, a média das escalas da série é o denominador correto.
            boa = np.isfinite(esc) & (esc > 0)
            escala = float(np.mean(esc[boa])) if boa.any() else float("nan")
            geral[(modelo, h)].somar(str(cnes), real, ponto, lo, hi, sigma, escala)
            por_faixa[(faixa, modelo, h)].somar(
                str(cnes), real, ponto, lo, hi, sigma, escala)

    return geral, por_faixa


# ---------------------------------------------------------------------------
# Relatório
# ---------------------------------------------------------------------------

def _commit() -> str:
    try:
        return subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT,
                              capture_output=True, text=True, timeout=10).stdout.strip() or "desconhecido"
    except Exception:
        return "desconhecido"


def _linhas(acum: dict, chave_extra: tuple = ()) -> list[dict]:
    saida = []
    for chave, a in sorted(acum.items(), key=lambda kv: (kv[0][-1], kv[0][-2])):
        reg = dict(zip(chave_extra + ("modelo", "horizonte_meses"), chave, strict=True))
        reg.update(a.resumo())
        saida.append(reg)
    return saida


def _tabela_md(linhas: list[dict], horizonte: int) -> str:
    sel = [x for x in linhas if x["horizonte_meses"] == horizonte]
    sel.sort(key=lambda x: (np.inf if not np.isfinite(x["mase"]) else x["mase"]))
    cab = ("| Modelo | MAE | RMSE | sMAPE % | WAPE % | MASE | Cobertura IC95 % | "
           "Largura IC % | z empírico | Veredito |\n"
           "|---|---:|---:|---:|---:|---:|---:|---:|---:|---|\n")
    linhas_md = []
    for x in sel:
        if x["modelo"] == BASELINE_MASE:
            veredito = "baseline (MASE ≡ 1)"
        elif not np.isfinite(x["mase"]):
            veredito = "sem MASE calculável"
        elif x["mase"] < 1:
            veredito = "supera o baseline"
        else:
            veredito = "**não supera o baseline**"
        if x["modelo"] == MODELO_ATUAL:
            veredito += " · *publicado hoje*"
        z = x.get("z_empirico_p95", float("nan"))
        z_txt = f"{z:.2f}" if np.isfinite(z) else "—"
        linhas_md.append(
            f"| `{x['modelo']}` | {x['mae']:,.1f} | {x['rmse']:,.1f} | {x['smape_pct']:.2f} | "
            f"{x['wape_pct']:.2f} | {x['mase']:.3f} | {x['cobertura_ic95_pct']:.1f} | "
            f"{x['largura_ic_pct_da_previsao']:.1f} | {z_txt} | {veredito} |"
        )
    return cab + "\n".join(linhas_md) + "\n"


def escrever_relatorio(
    geral: list[dict], por_faixa: list[dict], meta: dict, destino: Path,
) -> None:
    horizontes = sorted({x["horizonte_meses"] for x in geral})
    p = [
        "# Validação do forecast de demanda hospitalar",
        "",
        "> Gerado por `scripts/validate_forecast.py`. Não editar à mão: qualquer",
        "> alteração é sobrescrita na próxima execução.",
        "",
        "| | |",
        "|---|---|",
        f"| Gerado em | {meta['gerado_em']} |",
        f"| Commit | `{meta['commit']}` |",
        f"| Fonte | `{meta['fonte']}` |",
        f"| Período | {meta['periodo']} |",
        f"| Hospitais na fonte | {meta['n_hospitais']:,} |",
        f"| Hospitais avaliados | {meta['n_avaliados']:,} |",
        f"| Treino mínimo | {meta['min_treino']} meses |",
        f"| Origens por hospital | mediana {meta['origens_medianas']} |",
        "| Validação | origem móvel (walk-forward), sem embaralhamento |",
        "",
        "## Como ler",
        "",
        "**MASE** é a régua: erro do modelo dividido pelo erro do ingênuo sazonal",
        "dentro do treino. Abaixo de 1, o modelo acrescenta algo; acima, não.",
        "",
        "**Cobertura** e **largura** andam juntas. Um intervalo pode cobrir 95%",
        "por estar calibrado ou por ser largo demais para informar — só o par",
        "distingue os dois casos.",
        "",
        "**Horizontes são reportados separados** de propósito: uma média única",
        "esconderia a deterioração do horizonte longo.",
        "",
    ]
    for h in horizontes:
        p += [f"## Horizonte de {h} {'mês' if h == 1 else 'meses'}", "",
              _tabela_md(geral, h), ""]

    p += ["## Por faixa de volume", "",
          "Vinte por cento dos hospitais têm até 20 internações por mês. Agregar",
          "tudo numa métrica só deixaria o desempenho nesses invisível atrás do",
          "peso dos grandes.", ""]
    faixas_presentes = [f for f, _, _ in FAIXAS if any(x["faixa"] == f for x in por_faixa)]
    for faixa in faixas_presentes:
        sel = [x for x in por_faixa if x["faixa"] == faixa]
        h0 = min(horizontes)
        p += [f"### {faixa} — horizonte de {h0} {'mês' if h0 == 1 else 'meses'}", "",
              _tabela_md(sel, h0), ""]

    destino.write_text("\n".join(p), encoding="utf-8")


# ---------------------------------------------------------------------------

def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[1])
    ap.add_argument("--horizontes", type=int, nargs="+", default=list(HORIZONTES_PADRAO))
    ap.add_argument("--min-treino", type=int, default=MIN_TREINO)
    ap.add_argument("--amostra", type=int, default=None,
                    help="avalia só os N primeiros CNES (execução rápida; determinístico)")
    ap.add_argument("--quieto", action="store_true")
    args = ap.parse_args()

    if not FONTE.exists():
        raise SystemExit(
            f"faltando {FONTE}\n"
            "reconstrua com: python scripts/_baixar_mart_completo.py mart_demanda_mensal_hospital"
        )
    demanda = pd.read_parquet(FONTE)
    horizontes = tuple(sorted(set(args.horizontes)))

    print(f"[validação] {len(demanda):,} linhas · {demanda.cnes.nunique():,} hospitais · "
          f"{demanda.ano_mes.min()} a {demanda.ano_mes.max()}", flush=True)
    print(f"[validação] modelos: {', '.join(MODELOS)}", flush=True)
    print(f"[validação] horizontes: {horizontes} · treino mínimo: {args.min_treino} meses", flush=True)

    geral, por_faixa = rodar(demanda, horizontes, args.min_treino, args.amostra, args.quieto)
    if not geral:
        raise SystemExit("nenhuma série com histórico suficiente para backtest")

    linhas_geral = _linhas(geral)
    linhas_faixa = _linhas(por_faixa, ("faixa",))

    n_avaliados = max((x["n_hospitais"] for x in linhas_geral), default=0)
    origens = [x["n_previsoes"] / max(x["n_hospitais"], 1)
               for x in linhas_geral if x["horizonte_meses"] == min(horizontes)]
    meta = {
        "gerado_em": datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC"),
        "commit": _commit(),
        "fonte": "mart_demanda_mensal_hospital",
        "periodo": f"{demanda.ano_mes.min()} a {demanda.ano_mes.max()}",
        "n_hospitais": int(demanda.cnes.nunique()),
        "n_avaliados": int(n_avaliados),
        "min_treino": args.min_treino,
        "horizontes": list(horizontes),
        "origens_medianas": round(float(np.median(origens)), 1) if origens else 0,
        "modelo_publicado": MODELO_ATUAL,
        "baseline_mase": BASELINE_MASE,
    }

    SAIDA.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(linhas_geral).to_csv(SAIDA / "forecast_backtest_geral.csv",
                                      index=False, encoding="utf-8")
    pd.DataFrame(linhas_faixa).to_csv(SAIDA / "forecast_backtest_por_faixa.csv",
                                      index=False, encoding="utf-8")
    (SAIDA / "forecast_backtest.json").write_text(
        json.dumps({"meta": meta, "geral": linhas_geral, "por_faixa": linhas_faixa},
                   ensure_ascii=False, indent=2, default=float),
        encoding="utf-8")
    escrever_relatorio(linhas_geral, linhas_faixa, meta, SAIDA / "forecast_backtest.md")

    print(f"\n[ok] {n_avaliados:,} hospitais avaliados", flush=True)
    for h in horizontes:
        print(f"\n--- horizonte {h}m ---")
        for x in sorted((y for y in linhas_geral if y["horizonte_meses"] == h),
                        key=lambda z: z["mase"] if np.isfinite(z["mase"]) else np.inf):
            marca = "  <-- publicado hoje" if x["modelo"] == MODELO_ATUAL else ""
            print(f"  {x['modelo']:20s} MAE={x['mae']:9,.1f}  sMAPE={x['smape_pct']:6.2f}%  "
                  f"MASE={x['mase']:.3f}  cobertura={x['cobertura_ic95_pct']:5.1f}%{marca}")
    print(f"\n[ok] relatório em {(SAIDA / 'forecast_backtest.md').relative_to(ROOT)}")


if __name__ == "__main__":
    main()
