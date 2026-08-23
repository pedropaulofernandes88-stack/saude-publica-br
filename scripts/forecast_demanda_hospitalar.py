"""
forecast_demanda_hospitalar.py — projeção de demanda mensal por hospital
=========================================================================

Lê `mart_demanda_mensal_hospital` (produzida por pipeline_sih_hospitalar.py) e
projeta as internações dos próximos meses por estabelecimento.

O QUE MUDOU NESTA REVISÃO, E POR QUÊ
------------------------------------
A versão anterior publicava uma extrapolação de tendência sem nunca ter sido
avaliada fora da amostra. O backtest agora existe (`scripts/validate_forecast.py`)
e mudou quatro coisas — três eram defeito, uma era ausência de evidência.

1. **Previsão retrospectiva.** O script projetava 1..h meses após o último mês
   DAQUELE hospital. Como 340 estabelecimentos pararam de reportar antes do fim
   da série (defasagem mediana de 6 meses, máxima de 30), a tabela publicada
   trazia linhas rotuladas "mês previsto" com meses de 2022 — previsões do
   passado, exibidas como previsões. Agora existe uma âncora única: a última
   competência da base. Hospital que não chega até ela não é projetado, e o
   motivo fica registrado.

2. **Eixo temporal errado.** O ajuste usava `t = np.arange(n)` — a posição da
   linha, não o mês. Em 833 dos 4.848 hospitais a série tem buraco, e para eles
   dois pontos separados por meio ano contavam como vizinhos. Agora o eixo é o
   calendário. O backtest mostra que o efeito no erro MÉDIO é nulo (MASE 0,810
   nos dois): o ganho é de correção, não de acurácia — mas a inclinação daqueles
   833 estava sendo estimada sobre um eixo comprimido, e isso não se defende.

3. **O intervalo não era intervalo.** Era `± 1,96 · desvio-padrão dos resíduos`,
   constante em todo horizonte e medido dentro da amostra. O backtest mediu a
   cobertura real: **85,0% num intervalo declarado de 95%** no horizonte de 3
   meses, piorando com o horizonte (89,0% → 86,8% → 85,0%). Agora são duas
   correções: o intervalo de predição da regressão, que cresce com a distância
   da extrapolação, e um fator de calibração empírico vindo do backtest.

4. **"Confiança" não media confiança.** `confianca = "adequada"` significava
   apenas "≥ 24 meses de histórico" — uma propriedade do tamanho da série, não
   do acerto do modelo. Agora o campo é `status_validacao` (A/B/C), derivado do
   erro MEDIDO no estrato de volume do hospital, e vem acompanhado do sMAPE que
   o backtest observou naquele estrato.

O QUE **NÃO** MUDOU, E POR QUÊ
------------------------------
O método continua sendo tendência linear. Foram avaliados seis: naive, ingênuo
sazonal, média móvel de 3 meses, tendência linear, sazonal+drift e tendência com
sazonalidade. A tendência linear supera o baseline sazonal em todos os
horizontes e em todos os estratos (MASE 0,810 / 0,867 / 0,922), o que a
qualifica para publicação.

A média móvel de 3 meses é marginalmente melhor (MASE 0,762 / 0,846 / 0,917),
mas no horizonte publicado de 3 meses a diferença é de 0,5% — dentro do ruído, e
não justifica trocar um método já documentado publicamente.

Os modelos SAZONAIS ficaram PIORES por hospital (ingênuo sazonal 1,081;
sazonal+drift 1,105 em 3 meses), apesar de a sazonalidade ser nítida no agregado
nacional (fevereiro 5,9% abaixo da tendência). O motivo é que a amplitude
sazonal de ~6% é menor que o ruído da série de um hospital isolado, e estimar
doze efeitos mensais com 24–36 pontos sobreajusta. É um resultado que vale
registrar: o que é verdade no agregado não transfere para o estabelecimento.

Uso:
  .venv311/Scripts/python scripts/forecast_demanda_hospitalar.py --horizonte 3
  .venv311/Scripts/python scripts/forecast_demanda_hospitalar.py --no-upload
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
import pandas as pd
import requests

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _series_forecast import (  # noqa: E402
    MODELO_CANDIDATO,
    mes_de_indice,
    serie_regular,
    tendencia_linear,
)
from _publicacao import escrever_parquet  # noqa: E402
from _supabase_key import chave_escrita  # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parents[1]
MARTS = ROOT / "data" / "marts"
VALIDACAO = ROOT / "data" / "validacao" / "forecast_backtest.json"

# Mínimo de meses OBSERVADOS para tentar um ajuste. Abaixo disso a inclinação é
# ruído, e o backtest sequer avalia esses hospitais.
MIN_MESES = 6

# ---------------------------------------------------------------------------
# Critérios de publicação
# ---------------------------------------------------------------------------
# Os limiares saem da distribuição MEDIDA de sMAPE por estrato no backtest de 3
# meses, não de convenção. Os valores observados foram:
#
#     >500/mês      13,6%        101–500/mês   18,3%
#     21–100/mês    28,4%        6–20/mês      45,4%        ≤5/mês  58,7%
#
# O erro aproximadamente DOBRA ao cruzar de 21–100 para 6–20. O corte de 30%
# fica logo acima do pior estrato do grupo estável; o de 50%, entre os dois
# estratos ruins. Nenhum modelo é bloqueado por não superar o baseline, porque
# todos superam em todos os estratos — o que separa um caso publicável de um
# não publicável aqui é a MAGNITUDE do erro, não a comparação relativa.
SMAPE_VALIDADO = 30.0
SMAPE_EXPERIMENTAL = 50.0

# Meses de histórico abaixo dos quais a previsão nunca passa de experimental,
# mesmo em estrato de erro baixo: dois ciclos anuais é o que separa tendência de
# oscilação, e o backtest só avalia origens com esse mínimo.
MESES_VALIDADO = 24


def load_env() -> dict[str, str]:
    env: dict[str, str] = {}
    f = ROOT / ".env"
    if f.exists():
        for line in f.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, _, v = line.partition("=")
                env[k.strip()] = v.strip()
    env.update({k: v for k, v in os.environ.items() if k.startswith("SUPABASE")})
    return env


def _commit() -> str:
    try:
        return subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT,
                              capture_output=True, text=True, timeout=10).stdout.strip() or "desconhecido"
    except Exception:
        return "desconhecido"


def carregar_validacao() -> dict:
    """Lê o backtest. Sem ele, não se publica.

    Falhar aqui é deliberado: o intervalo depende de um fator de calibração
    medido, e o status de publicação depende do erro por estrato. Publicar sem
    esses números seria voltar exatamente ao estado que esta revisão corrigiu —
    uma previsão no ar sem nenhuma avaliação fora da amostra por trás.
    """
    if not VALIDACAO.exists():
        raise SystemExit(
            f"faltando {VALIDACAO.relative_to(ROOT)}\n"
            "rode antes: python scripts/validate_forecast.py\n"
            "(o intervalo e o status de publicação vêm do backtest; sem ele não há o que publicar)"
        )
    d = json.loads(VALIDACAO.read_text(encoding="utf-8"))
    modelo = MODELO_CANDIDATO
    z: dict[int, float] = {}
    for x in d["geral"]:
        if x["modelo"] == modelo and np.isfinite(x.get("z_empirico_p95", float("nan"))):
            z[int(x["horizonte_meses"])] = float(x["z_empirico_p95"])
    smape: dict[tuple[str, int], float] = {}
    for x in d["por_faixa"]:
        if x["modelo"] == modelo:
            smape[(x["faixa"], int(x["horizonte_meses"]))] = float(x["smape_pct"])
    if not z:
        raise SystemExit(f"backtest não traz z empírico para o modelo {modelo}")
    return {"meta": d["meta"], "z": z, "smape": smape, "modelo": modelo}


def faixa_de(mediana: float) -> str:
    """Mesmos cortes do validador — importados de lá para não divergirem."""
    from validate_forecast import faixa_de as _f
    return _f(mediana)


def status_de(faixa: str, n_meses: int, smape: dict, horizonte: int) -> tuple[str, str, float]:
    """Classifica a previsão em A (validado), B (experimental) ou C (não publicar).

    Devolve (status, motivo legível, sMAPE medido no estrato).
    """
    s = smape.get((faixa, horizonte), float("nan"))
    if not np.isfinite(s):
        return ("C", f"sem métrica de backtest para o estrato {faixa}", s)
    if s > SMAPE_EXPERIMENTAL:
        return ("C", f"erro medido no estrato {faixa} é de {s:.0f}% (sMAPE) — alto demais "
                     "para apoiar decisão", s)
    if s > SMAPE_VALIDADO:
        return ("B", f"erro medido no estrato {faixa} é de {s:.0f}% (sMAPE) — resultado "
                     "exploratório, não use para dimensionar oferta", s)
    if n_meses < MESES_VALIDADO:
        return ("B", f"apenas {n_meses} meses de histórico (mínimo de {MESES_VALIDADO} "
                     "para dois ciclos anuais)", s)
    return ("A", f"erro medido no estrato {faixa} é de {s:.0f}% (sMAPE), com "
                 f"{n_meses} meses de histórico", s)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--horizonte", type=int, default=3)
    ap.add_argument("--no-upload", action="store_true")
    ap.add_argument("--incluir-nao-publicaveis", action="store_true",
                    help="mantém as linhas de status C na saída (padrão: descarta)")
    ap.add_argument("--sem-substituir", action="store_true",
                    help="não limpa a tabela antes de carregar; deixa resíduo de âncoras "
                         "anteriores. Só para depuração — foi este comportamento que "
                         "publicou 786 previsões de meses já passados.")
    args = ap.parse_args()

    src = MARTS / "mart_demanda_mensal_hospital.parquet"
    if not src.exists():
        raise SystemExit(f"faltando {src} — rode pipeline_sih_hospitalar.py primeiro")
    demanda = pd.read_parquet(src)

    val = carregar_validacao()
    z_por_h = val["z"]
    faltando_z = [h for h in range(1, args.horizonte + 1) if h not in z_por_h]
    if faltando_z:
        raise SystemExit(
            f"backtest não cobre o(s) horizonte(s) {faltando_z}. "
            f"rode: python scripts/validate_forecast.py --horizontes {' '.join(str(h) for h in range(1, args.horizonte + 1))}"
        )

    # Âncora única da base. Toda previsão é para DEPOIS dela — nunca depois do
    # último mês de cada hospital, que é o que produzia previsão retrospectiva.
    ancora_txt = str(demanda["ano_mes"].max())
    from _series_forecast import indice_mes
    ancora = indice_mes(ancora_txt)
    print(f"[forecast] âncora da base: {ancora_txt} — todas as previsões são posteriores a ela",
          flush=True)

    linhas: list[dict] = []
    descartes = {"serie_curta": 0, "nao_alcanca_ancora": 0, "ajuste_impossivel": 0, "status_C": 0}
    treinado_em = datetime.now(UTC).strftime("%Y-%m-%d")
    commit = _commit()

    for cnes, g in demanda.groupby("cnes"):
        g = g.sort_values("ano_mes")
        inicio, y = serie_regular(g["ano_mes"].tolist(), g["internacoes"].tolist())
        n_obs = int((~np.isnan(y)).sum())
        if n_obs < MIN_MESES:
            descartes["serie_curta"] += 1
            continue
        # A série precisa alcançar a âncora. Hospital que parou de reportar não
        # recebe previsão: não sabemos se fechou, se descredenciou ou se é atraso.
        if inicio + y.size - 1 < ancora:
            descartes["nao_alcanca_ancora"] += 1
            continue

        prev = tendencia_linear(y, args.horizonte)
        if not np.isfinite(prev.ponto).any():
            descartes["ajuste_impossivel"] += 1
            continue

        faixa = faixa_de(float(np.nanmedian(y)))
        status, motivo, smape_estrato = status_de(faixa, n_obs, val["smape"], args.horizonte)
        if status == "C" and not args.incluir_nao_publicaveis:
            descartes["status_C"] += 1
            continue

        for h in range(1, args.horizonte + 1):
            z = z_por_h[h]
            ponto = float(prev.ponto[h - 1])
            sigma = float(prev.sigma[h - 1])
            linhas.append({
                "cnes": cnes,
                "ano_mes_previsto": mes_de_indice(ancora + h),
                "internacoes_previstas": round(ponto, 1),
                "ic_inferior": round(max(ponto - z * sigma, 0.0), 1),
                "ic_superior": round(ponto + z * sigma, 1),
                "n_meses_historico": n_obs,
                "horizonte_meses": h,
                # Coluna obsoleta, mantida por um ciclo: a API é pública e sem
                # cadastro, então não há como avisar quem consome antes de
                # remover. Derivada do status para nunca divergir dele.
                "confianca": "adequada" if status == "A" else "baixa",
                "status_validacao": status,
                "motivo_status": motivo,
                "faixa_volume": faixa,
                "smape_backtest_pct": round(smape_estrato, 1) if np.isfinite(smape_estrato) else None,
                "modelo": val["modelo"],
                "ultima_competencia": ancora_txt,
                "treinado_em": treinado_em,
                "commit_codigo": commit,
            })

    if not linhas:
        raise SystemExit("nenhum hospital elegível — verifique a âncora e os critérios de status")

    forecast = pd.DataFrame(linhas)
    ref = demanda[["cnes", "municipio_cod", "municipio_nome", "uf_sigla"]].drop_duplicates("cnes")
    forecast = forecast.merge(ref, on="cnes", how="left")
    forecast = forecast[[
        "cnes", "municipio_cod", "municipio_nome", "uf_sigla", "ano_mes_previsto",
        "horizonte_meses", "internacoes_previstas", "ic_inferior", "ic_superior",
        "n_meses_historico", "faixa_volume", "status_validacao", "motivo_status",
        "smape_backtest_pct", "modelo", "ultima_competencia", "treinado_em",
        "commit_codigo", "confianca",
    ]]

    MARTS.mkdir(exist_ok=True)
    escrever_parquet(forecast, MARTS / "mart_forecast_demanda_hospital.parquet",
                     origem="pipeline", produtor="scripts/forecast_demanda_hospitalar.py")

    por_status = forecast.groupby("status_validacao").cnes.nunique().to_dict()
    print(f"[forecast] {len(forecast):,} previsões · {forecast.cnes.nunique():,} hospitais", flush=True)
    print(f"[forecast] por status: {por_status}", flush=True)
    print(f"[forecast] descartados: {descartes}", flush=True)
    print(f"[forecast] z empírico por horizonte: "
          f"{ {h: round(z_por_h[h], 2) for h in sorted(z_por_h) if h <= args.horizonte} } "
          f"(z normal seria 1,96 — a diferença é o quanto o intervalo antigo era estreito)",
          flush=True)

    if args.no_upload:
        return
    env = load_env()
    url, key = env["SUPABASE_URL"], chave_escrita(env)
    h = {"apikey": key, "Authorization": f"Bearer {key}", "Content-Type": "application/json",
         "Prefer": "return=minimal,resolution=merge-duplicates"}

    # A tabela é SUBSTITUÍDA, não mesclada — e esta é a correção que impede a
    # previsão retrospectiva de voltar.
    #
    # A chave é (cnes, ano_mes_previsto). Com upsert por merge, a previsão da
    # âncora anterior nunca saía: rodar em 2022 deixava linhas de 2022, rodar em
    # 2023 acrescentava as de 2023, e assim por diante. Foi assim que 786 linhas
    # com `ano_mes_previsto` no passado chegaram à API pública, rotuladas "mês
    # previsto". Previsão é um retrato de uma âncora; quando a âncora anda, o
    # retrato anterior não é histórico a preservar — é lixo com aparência de dado.
    #
    # O histórico auditável de previsões passadas, se um dia for desejado, é uma
    # tabela separada com a âncora na chave, não o resíduo acidental desta.
    if not args.sem_substituir:
        r = requests.delete(f"{url.rstrip('/')}/rest/v1/mart_forecast_demanda_hospital",
                            headers={**h, "Prefer": "return=minimal"},
                            params={"cnes": "not.is.null"}, timeout=300)
        if r.status_code not in (200, 204):
            raise RuntimeError(f"limpeza da tabela falhou: HTTP {r.status_code} {r.text[:200]}")
        print("[forecast] tabela limpa antes da carga (evita previsão retrospectiva residual)",
              flush=True)
    recs = forecast.astype(object).where(pd.notna(forecast), None).to_dict("records")
    for i in range(0, len(recs), 8000):
        body = json.dumps(recs[i:i + 8000],
                          default=lambda o: o.item() if hasattr(o, "item") else o, allow_nan=False)
        for a in range(4):
            r = requests.post(f"{url.rstrip('/')}/rest/v1/mart_forecast_demanda_hospital",
                              headers=h, data=body, timeout=300)
            if r.status_code in (200, 201):
                break
            if a == 3 or r.status_code in (400, 401, 403, 404, 409):
                raise RuntimeError(f"mart_forecast_demanda_hospital: HTTP {r.status_code} {r.text[:200]}")
            time.sleep(3 * (a + 1))
    print("[done] forecast de demanda concluído.", flush=True)


if __name__ == "__main__":
    main()
