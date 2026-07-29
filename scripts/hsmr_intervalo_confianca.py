"""
hsmr_intervalo_confianca.py — IC95% exato (Poisson) para o HSMR
================================================================

O HSMR publicado ate aqui trazia uma flag binaria `estavel` (obitos esperados
>= 5). Isso responde "o numero e confiavel?", mas nao responde a pergunta que
o gestor realmente faz: "a mortalidade deste hospital difere do esperado?".

Um intervalo de confianca responde as duas de uma vez. Como o numero de obitos
observados segue distribuicao de Poisson e o esperado e tratado como constante
conhecida (padronizacao indireta), o IC exato do HSMR e:

    HSMR_inf = qgamma(0,025 ; O)     / E
    HSMR_sup = qgamma(0,975 ; O + 1) / E

E o mesmo metodo gamma/Poisson exato ja usado nas taxas brutas de mortalidade
municipal do projeto (scripts/pipeline_v2.py) — consistencia metodologica
interna, nao uma segunda convencao.

Leitura: se o IC95% NAO contem 1, a diferenca em relacao ao esperado e
estatisticamente significativa (a 5%). Se contem 1, o hospital nao se
distingue do padrao nacional dado seu case-mix — mesmo que o ponto estimado
pareca alto. Isso substitui com vantagem a flag binaria: um hospital com
HSMR 2,4 e IC [0,7 - 6,1] deixa de parecer um alarme.

Nao reprocessa o SIH: trabalha sobre mart_hsmr_hospital ja publicado.

Uso:
  .venv311/Scripts/python scripts/hsmr_intervalo_confianca.py [--no-upload]
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
from scipy.stats import gamma as gamma_dist

ROOT = Path(__file__).resolve().parents[1]
MARTS = ROOT / "data" / "marts"


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


def add_ic95(df: pd.DataFrame) -> pd.DataFrame:
    """IC95% gamma (Poisson exato) do HSMR, a partir de observado e esperado."""
    obs = df["obitos_observados"].to_numpy(dtype=float)
    esp = df["obitos_esperados"].to_numpy(dtype=float)

    valido = esp > 0
    inf = np.full(len(df), np.nan)
    sup = np.full(len(df), np.nan)

    # limite inferior: 0 quando nao houve obito observado (nao ha evidencia de excesso)
    inf[valido] = np.where(
        obs[valido] > 0,
        gamma_dist.ppf(0.025, np.maximum(obs[valido], 1e-9)) / esp[valido],
        0.0,
    )
    sup[valido] = gamma_dist.ppf(0.975, obs[valido] + 1) / esp[valido]

    df["hsmr_ic95_inf"] = np.round(inf, 3)
    df["hsmr_ic95_sup"] = np.round(sup, 3)

    # classificacao: acima / abaixo / dentro do esperado (IC nao contem 1).
    # Hospitais com esperado = 0 nao admitem IC — sao "indeterminado", nao
    # "esperado": nao ha base para afirmar que estao dentro do padrao.
    acima = df["hsmr_ic95_inf"] > 1
    abaixo = df["hsmr_ic95_sup"] < 1
    indet = df["hsmr_ic95_inf"].isna() | df["hsmr_ic95_sup"].isna()
    df["significancia"] = np.where(
        indet, "indeterminado",
        np.where(acima, "acima", np.where(abaixo, "abaixo", "esperado")),
    )
    return df


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-upload", action="store_true")
    args = ap.parse_args()

    src = MARTS / "mart_hsmr_hospital.parquet"
    if not src.exists():
        raise SystemExit(f"faltando {src}")
    df = pd.read_parquet(src)
    df = add_ic95(df)

    print(f"[hsmr-ic] {len(df):,} registros hospital-ano")
    for ano, g in df.groupby("ano"):
        dist = g["significancia"].value_counts()
        n = len(g)
        print(f"  {ano}: acima={dist.get('acima',0):5,} ({dist.get('acima',0)/n*100:4.1f}%)  "
              f"abaixo={dist.get('abaixo',0):5,} ({dist.get('abaixo',0)/n*100:4.1f}%)  "
              f"dentro do esperado={dist.get('esperado',0):5,} ({dist.get('esperado',0)/n*100:4.1f}%)")

    # quantos "alarmes" da flag antiga se dissolvem com o IC
    antigos_altos = df[(df.hsmr > 1.5)]
    dissolvidos = antigos_altos[antigos_altos.significancia == "esperado"]
    print(f"\n  HSMR > 1,5 no ponto estimado: {len(antigos_altos):,}")
    print(f"    destes, NAO significativos (IC contem 1): {len(dissolvidos):,} "
          f"({len(dissolvidos)/max(len(antigos_altos),1)*100:.1f}%)")
    print("    -> o IC evita tratar ruido de hospital pequeno como sinal")

    df.to_parquet(src, compression="zstd", index=False)
    print(f"\n[hsmr-ic] mart atualizado: {src.name}")

    if args.no_upload:
        return
    env = load_env()
    url, key = env["SUPABASE_URL"], env["SUPABASE_ANON_KEY"]
    h = {"apikey": key, "Authorization": f"Bearer {key}", "Content-Type": "application/json",
         "Prefer": "return=minimal,resolution=merge-duplicates"}
    recs = df.astype(object).where(pd.notna(df), None).to_dict("records")
    for i in range(0, len(recs), 8000):
        body = json.dumps(recs[i:i+8000], default=lambda o: o.item() if hasattr(o, "item") else o, allow_nan=False)
        for a in range(4):
            r = requests.post(f"{url.rstrip('/')}/rest/v1/mart_hsmr_hospital", headers=h, data=body, timeout=300)
            if r.status_code in (200, 201):
                break
            if a == 3 or r.status_code in (400, 401, 403, 404, 409):
                raise RuntimeError(f"mart_hsmr_hospital: HTTP {r.status_code} {r.text[:200]}")
            time.sleep(3 * (a + 1))
    print(f"[supabase]   mart_hsmr_hospital: {len(recs):,} OK")
    print("[done] IC95% do HSMR publicado.")


if __name__ == "__main__":
    main()
