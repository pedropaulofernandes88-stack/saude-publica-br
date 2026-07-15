"""
forecast_demanda_hospitalar.py — Forecast de demanda mensal por hospital
=========================================================================

Lê mart_demanda_mensal_hospital (gerada por pipeline_sih_hospitalar.py) e
projeta as internações dos próximos meses por hospital, via regressão linear
simples (internações ~ índice do mês), o mesmo método já usado no excesso de
mortalidade (tendência sobre a série observada).

Metodologia:
  - Ajusta y = a + b*t (t = índice sequencial do mês) por hospital, com
    mínimo de MIN_MESES pontos históricos.
  - Projeta HORIZONTE meses à frente; IC aproximado = previsão ± 1.96 * desvio
    padrão dos resíduos do ajuste (não é IC de predição formal — é uma faixa
    de incerteza indicativa, declarada como tal).
  - `confianca`: "baixa" quando o hospital tem menos de MESES_CONFIANCA meses
    de histórico (uma tendência calculada sobre poucos pontos é instável —
    mesmo princípio já usado no excesso de mortalidade, que exige uma janela
    mínima de anos antes de projetar). Não ocultamos a previsão: sinalizamos.

Uso:
  .venv311/Scripts/python scripts/forecast_demanda_hospitalar.py --horizonte 3
"""
from __future__ import annotations

import argparse
import json
import os
import time
from pathlib import Path

import numpy as np
import pandas as pd
import requests

ROOT = Path(__file__).resolve().parents[1]
MARTS = ROOT / "data" / "marts"

MIN_MESES = 6           # mínimo de meses para sequer tentar uma tendência
MESES_CONFIANCA = 24    # abaixo disso, confianca="baixa" (~2 anos)


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


def _forecast_hospital(g: pd.DataFrame, horizonte: int) -> pd.DataFrame | None:
    g = g.sort_values("ano_mes").reset_index(drop=True)
    n = len(g)
    if n < MIN_MESES:
        return None
    t = np.arange(n)
    y = g["internacoes"].to_numpy(dtype=float)
    b, a = np.polyfit(t, y, 1)  # slope, intercept
    pred_hist = a + b * t
    resid_std = float(np.std(y - pred_hist, ddof=2)) if n > 2 else 0.0

    ultimo_ano_mes = g["ano_mes"].iloc[-1]
    ano0, mes0 = (int(x) for x in ultimo_ano_mes.split("-"))
    linhas = []
    for h in range(1, horizonte + 1):
        t_fut = n - 1 + h
        pred = max(a + b * t_fut, 0.0)
        mes_fut = mes0 + h
        ano_fut = ano0 + (mes_fut - 1) // 12
        mes_fut = (mes_fut - 1) % 12 + 1
        linhas.append({
            "ano_mes_previsto": f"{ano_fut}-{mes_fut:02d}",
            "internacoes_previstas": round(pred, 1),
            "ic_inferior": round(max(pred - 1.96 * resid_std, 0.0), 1),
            "ic_superior": round(pred + 1.96 * resid_std, 1),
        })
    out = pd.DataFrame(linhas)
    out["cnes"] = g["cnes"].iloc[0]
    out["n_meses_historico"] = n
    out["confianca"] = np.where(n >= MESES_CONFIANCA, "adequada", "baixa")
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--horizonte", type=int, default=3)
    ap.add_argument("--no-upload", action="store_true")
    args = ap.parse_args()

    src = MARTS / "mart_demanda_mensal_hospital.parquet"
    if not src.exists():
        raise SystemExit(f"faltando {src} — rode pipeline_sih_hospitalar.py primeiro")
    demanda = pd.read_parquet(src)

    parts = []
    for cnes, g in demanda.groupby("cnes"):
        r = _forecast_hospital(g, args.horizonte)
        if r is not None:
            parts.append(r)
    if not parts:
        raise SystemExit("nenhum hospital com histórico suficiente para forecast")

    forecast = pd.concat(parts, ignore_index=True)
    ref = demanda[["cnes", "municipio_cod", "municipio_nome", "uf_sigla"]].drop_duplicates("cnes")
    forecast = forecast.merge(ref, on="cnes", how="left")
    forecast = forecast[["cnes", "municipio_cod", "municipio_nome", "uf_sigla",
                         "ano_mes_previsto", "internacoes_previstas", "ic_inferior",
                         "ic_superior", "n_meses_historico", "confianca"]]

    MARTS.mkdir(exist_ok=True)
    forecast.to_parquet(MARTS / "mart_forecast_demanda_hospital.parquet", compression="zstd", index=False)
    n_baixa = (forecast.confianca == "baixa").sum()
    print(f"[forecast] {len(forecast):,} previsões | {forecast.cnes.nunique():,} hospitais | "
          f"{n_baixa:,} linhas com confiança baixa (<{MESES_CONFIANCA} meses de histórico)", flush=True)

    if args.no_upload:
        return
    env = load_env()
    url, key = env["SUPABASE_URL"], env["SUPABASE_ANON_KEY"]
    h = {"apikey": key, "Authorization": f"Bearer {key}", "Content-Type": "application/json",
         "Prefer": "return=minimal,resolution=merge-duplicates"}
    recs = forecast.astype(object).where(pd.notna(forecast), None).to_dict("records")
    for i in range(0, len(recs), 8000):
        body = json.dumps(recs[i:i+8000], default=lambda o: o.item() if hasattr(o, "item") else o, allow_nan=False)
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
