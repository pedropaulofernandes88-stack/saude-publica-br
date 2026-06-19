"""
pipeline_clusters.py — Arquétipos de saúde municipal (k-means)
==============================================================

Agrupa municípios em perfis de saúde por k-means sobre três dimensões
padronizadas por z-score (método inspirado no LabSUS, UFT):
  - mortalidade padronizada por idade (SIM, 2023)
  - vulnerabilidade social (proxy Censo 2022)
  - internações por 100 mil hab. (SIH, 2023)

Usa apenas marts já existentes (data/marts/*.parquet) — sem novo download.
k-means via scipy.cluster.vq (sem dependência de scikit-learn).

Uso: .venv311/Scripts/python scripts/pipeline_clusters.py
"""
from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd
import requests
from scipy.cluster.vq import kmeans2, whiten  # noqa: F401

ROOT = Path(__file__).resolve().parents[1]
MARTS = ROOT / "data" / "marts"
ANO = 2023
K = 5
SEED = 42


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


def main() -> None:
    env = load_env()

    mort = pd.read_parquet(MARTS / "mart_mortalidade_municipio.parquet")
    mort = mort[(mort.ano == ANO) & (mort.capitulo_cid == "TOTAL") & (mort.sexo == "TOTAL")][
        ["municipio_cod", "municipio_nome", "uf_sigla", "regiao", "taxa_padronizada_100k", "populacao"]
    ]
    ivs = pd.read_parquet(MARTS / "dim_ivs.parquet")[["municipio_cod", "ivs_score"]]
    intern = pd.read_parquet(MARTS / "mart_internacoes_municipio.parquet")
    intern = intern[(intern.ano == ANO) & (intern.capitulo_cid == "TOTAL")][
        ["municipio_cod", "internacoes_100k"]
    ]

    df = (mort.merge(ivs, on="municipio_cod", how="inner")
              .merge(intern, on="municipio_cod", how="inner"))
    # foco em municípios com taxas estáveis
    df = df[(df.populacao >= 20000) & df.taxa_padronizada_100k.notna()
            & df.ivs_score.notna() & df.internacoes_100k.notna()].copy()
    print(f"[cluster] {len(df)} municípios (pop>=20k, 2023)")

    feats = ["taxa_padronizada_100k", "ivs_score", "internacoes_100k"]
    X = df[feats].to_numpy(dtype=float)
    # z-score
    Z = (X - X.mean(axis=0)) / X.std(axis=0)
    np.random.seed(SEED)
    centroides, rot = kmeans2(Z, K, seed=SEED, minit="++", missing="warn")
    df["cluster"] = rot.astype(int)

    # rótulos interpretáveis por posição do centróide (em z): alto/baixo
    cent = pd.DataFrame(centroides, columns=feats)
    def rotulo(c: int) -> str:
        mortz, ivsz, intz = cent.loc[c, "taxa_padronizada_100k"], cent.loc[c, "ivs_score"], cent.loc[c, "internacoes_100k"]
        mort_t = "mortalidade alta" if mortz > 0.4 else "mortalidade baixa" if mortz < -0.4 else "mortalidade média"
        vul_t = "vulnerabilidade alta" if ivsz > 0.4 else "vulnerabilidade baixa" if ivsz < -0.4 else "vulnerabilidade média"
        int_t = "muita internação" if intz > 0.4 else "pouca internação" if intz < -0.4 else "internação média"
        return f"{mort_t}, {vul_t}, {int_t}"
    df["perfil"] = df["cluster"].map(rotulo)

    out = df[["municipio_cod", "municipio_nome", "uf_sigla", "regiao", "cluster", "perfil",
              "taxa_padronizada_100k", "ivs_score", "internacoes_100k"]].copy()
    out["ivs_score"] = out["ivs_score"].round(1)
    MARTS.mkdir(exist_ok=True)
    out.to_parquet(MARTS / "dim_cluster_municipio.parquet", compression="zstd", index=False)

    print("[cluster] distribuição:")
    for c in sorted(out.cluster.unique()):
        sub = out[out.cluster == c]
        print(f"  cluster {c} (n={len(sub)}): {sub.perfil.iloc[0]}")

    # upload
    url, key = env["SUPABASE_URL"], env["SUPABASE_ANON_KEY"]
    h = {"apikey": key, "Authorization": f"Bearer {key}", "Content-Type": "application/json",
         "Prefer": "return=minimal,resolution=merge-duplicates"}
    recs = out.astype(object).where(pd.notna(out), None).to_dict("records")
    for i in range(0, len(recs), 5000):
        body = json.dumps(recs[i:i+5000], default=lambda o: o.item() if hasattr(o, "item") else o, allow_nan=False)
        r = requests.post(f"{url.rstrip('/')}/rest/v1/dim_cluster_municipio", headers=h, data=body, timeout=300)
        if r.status_code not in (200, 201):
            raise RuntimeError(f"upload: HTTP {r.status_code} {r.text[:200]}")
    print(f"[supabase] dim_cluster_municipio: {len(recs)} OK")

    meta = [{"chave": "fonte_clusters", "valor": "K-means (k=5) sobre z-score de mortalidade padronizada (SIM 2023), vulnerabilidade-proxy (Censo 2022) e internações/100k (SIH 2023); método inspirado no LabSUS (UFT). Municípios com pop>=20 mil."},
            {"chave": "gerado_em", "valor": datetime.now().isoformat(timespec="seconds")}]
    requests.post(f"{url.rstrip('/')}/rest/v1/meta_dataset", headers=h, data=json.dumps(meta), timeout=60)
    print("[done] clusters concluído.")


if __name__ == "__main__":
    main()
