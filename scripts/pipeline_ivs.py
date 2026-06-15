"""
pipeline_ivs.py — Índice de Vulnerabilidade Social (proxy, Censo 2022)
=====================================================================

Compõe um índice municipal de vulnerabilidade social a partir de dois
indicadores oficiais do Censo 2022 (IBGE/SIDRA), pela média de z-scores
(normalização Z-Score — método formalizado pelo LabSUS):

  - taxa de analfabetismo (15+)        = 100 − alfabetização (t/9543)
  - % domicílios sem água encanada     = 100 − % com rede geral (t/6803)

ivs_score = média(z_analfabetismo, z_sem_agua); reescalado 0–100 (percentil-like
via min-max) → maior = mais vulnerável. Quartis (Q1 menos vulnerável … Q4 mais).

IMPORTANTE — honestidade metodológica: este é um PROXY transparente e
reproduzível, NÃO o IVS oficial do IPEA (que usa 16 indicadores, base 2010).
A ideia de cruzar saúde × vulnerabilidade e o uso de z-score seguem o LabSUS
(Lucas Amaral Dourado, UFT). Crédito em saudeemdado.com/sobre.

Uso: .venv311/Scripts/python scripts/pipeline_ivs.py
"""
from __future__ import annotations

import json
import math
import os
import sys
import time
from datetime import datetime
from pathlib import Path

import pandas as pd
import requests

ROOT = Path(__file__).resolve().parents[1]
REFS = ROOT / "data" / "refs"
MARTS_DIR = ROOT / "data" / "marts"
SIDRA = "https://apisidra.ibge.gov.br/values"


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


def _sidra(url: str) -> pd.DataFrame:
    r = requests.get(url, timeout=300)
    r.raise_for_status()
    return pd.DataFrame(r.json()[1:])


def fetch_alfabetizacao() -> pd.DataFrame:
    print("[ivs] alfabetização 15+ (Censo 2022, t/9543)...")
    df = _sidra(f"{SIDRA}/t/9543/n6/all/v/2513/p/2022")
    df = df[["D1C", "V"]].rename(columns={"D1C": "cod7", "V": "alfab"})
    df["alfab"] = pd.to_numeric(df["alfab"], errors="coerce")
    df["municipio_cod"] = df["cod7"].astype(str).str[:6]
    df["taxa_analfabetismo"] = (100 - df["alfab"]).round(2)
    return df[["municipio_cod", "taxa_analfabetismo"]].dropna()


def fetch_sem_agua() -> pd.DataFrame:
    print("[ivs] água encanada (Censo 2022, t/6803)...")
    # total (72129) e categorias 'possui ligação à rede geral' (72144..72147)
    cats = "72129,72144,72145,72146,72147"
    df = _sidra(f"{SIDRA}/t/6803/n6/all/v/381/p/2022/c1821/{cats}")
    df = df[["D1C", "D4C", "V"]].rename(columns={"D1C": "cod7", "D4C": "cat", "V": "dom"})
    df["dom"] = pd.to_numeric(df["dom"], errors="coerce").fillna(0)
    df["municipio_cod"] = df["cod7"].astype(str).str[:6]
    tot = df[df["cat"] == "72129"].set_index("municipio_cod")["dom"]
    comraj = (df[df["cat"] != "72129"].groupby("municipio_cod")["dom"].sum())
    out = pd.DataFrame({"total": tot, "com_agua": comraj}).reset_index()
    out["pct_sem_agua"] = ((1 - out["com_agua"] / out["total"]) * 100).round(2)
    return out[["municipio_cod", "pct_sem_agua"]].replace([float("inf")], pd.NA).dropna()


def main() -> None:
    env = load_env()
    alf = fetch_alfabetizacao()
    agua = fetch_sem_agua()
    municipios = pd.read_parquet(REFS / "municipios.parquet")

    df = (municipios[["municipio_cod", "municipio_nome", "uf_sigla", "regiao"]]
          .merge(alf, on="municipio_cod", how="inner")
          .merge(agua, on="municipio_cod", how="inner"))

    # z-score (método LabSUS) e composição
    for col in ("taxa_analfabetismo", "pct_sem_agua"):
        mu, sd = df[col].mean(), df[col].std(ddof=0)
        df[f"z_{col}"] = (df[col] - mu) / sd
    df["z_ivs"] = (df["z_taxa_analfabetismo"] + df["z_pct_sem_agua"]) / 2
    # reescala 0–100 (min-max) — maior = mais vulnerável
    lo, hi = df["z_ivs"].min(), df["z_ivs"].max()
    df["ivs_score"] = ((df["z_ivs"] - lo) / (hi - lo) * 100).round(1)
    df["ivs_quartil"] = pd.qcut(df["ivs_score"], 4, labels=["Q1", "Q2", "Q3", "Q4"]).astype(str)

    out = df[["municipio_cod", "municipio_nome", "uf_sigla", "regiao",
              "taxa_analfabetismo", "pct_sem_agua", "ivs_score", "ivs_quartil"]].copy()
    print(f"[ivs] {len(out):,} municípios | ivs médio {out['ivs_score'].mean():.1f} | "
          f"Q4 (mais vulnerável) ex.: {out.nlargest(3,'ivs_score')['municipio_nome'].tolist()}")

    MARTS_DIR.mkdir(parents=True, exist_ok=True)
    out.to_parquet(MARTS_DIR / "dim_ivs.parquet", compression="zstd", index=False)

    url, key = env["SUPABASE_URL"], env["SUPABASE_ANON_KEY"]
    h = {"apikey": key, "Authorization": f"Bearer {key}",
         "Content-Type": "application/json",
         "Prefer": "return=minimal,resolution=merge-duplicates"}
    recs = out.astype(object).where(pd.notna(out), None).to_dict("records")
    for i in range(0, len(recs), 5000):
        body = json.dumps(recs[i:i+5000], default=lambda o: o.item() if hasattr(o, "item") else o, allow_nan=False)
        for a in range(4):
            r = requests.post(f"{url.rstrip('/')}/rest/v1/dim_ivs", headers=h, data=body, timeout=300)
            if r.status_code in (200, 201):
                break
            if a == 3 or r.status_code in (400, 401, 403, 404, 409):
                raise RuntimeError(f"dim_ivs: HTTP {r.status_code} {r.text[:200]}")
            time.sleep(3 * (a + 1))
    print(f"[supabase]   dim_ivs: {len(recs):,} OK")

    meta = pd.DataFrame([
        ("fonte_ivs", "IBGE Censo 2022 (SIDRA t/9543 alfabetização, t/6803 água); proxy de vulnerabilidade por z-score"),
        ("ivs_nota", "Proxy reproduzível (2 indicadores), NÃO é o IVS oficial do IPEA (16 indicadores, base 2010); método z-score inspirado no LabSUS"),
        ("gerado_em", datetime.now().isoformat(timespec="seconds")),
    ], columns=["chave", "valor"])
    mrecs = meta.to_dict("records")
    requests.post(f"{url.rstrip('/')}/rest/v1/meta_dataset", headers=h, data=json.dumps(mrecs), timeout=60)
    print("[done] pipeline IVS concluído.")


if __name__ == "__main__":
    main()
