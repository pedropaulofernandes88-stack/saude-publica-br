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

import sys
import json
import os
import time
from datetime import datetime
from pathlib import Path

import pandas as pd
import requests

from _supabase_key import chave_escrita

# A linhagem viaja com os BYTES: `escrever_parquet` grava no proprio
# Parquet quem o produziu. Sem isso, um arquivo que veio do Postgres e um
# que veio do pipeline sao indistinguiveis, e o manifesto afirma o que
# ninguem verificou.
sys.path.insert(0, str(Path(__file__).resolve().parent))
from _saida import Resultado

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

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


#: Categorias da classificação c1821 da tabela 6803 do SIDRA. Ela é
#: HIERÁRQUICA, e essa é a armadilha: 72146 e 72147 não são irmãos de 72145,
#: são FILHOS dele.
#:
#:     72129  Total
#:     72144    Possui ligação à rede geral e a utiliza como forma principal
#:     72145    Possui ligação à rede geral, mas utiliza principalmente outra
#:     72146      ... Poço profundo ou artesiano        <- filho de 72145
#:     72147      ... Poço raso, freático ou cacimba    <- filho de 72145
#:     72148      ... Fonte, nascente ou mina           <- filho de 72145
#:     72149..72152  ... (demais formas)                <- filhos de 72145
#:     72153    Não possui ligação com a rede geral
#:     72154..72160  ... (por forma de abastecimento)   <- filhos de 72153
#:
#: Somar 72144+72145+72146+72147 como "com água" — o que este arquivo fazia até
#: 2026-09-12 — conta os dois primeiros filhos DE NOVO dentro do pai, e ainda
#: ignora os outros cinco. Em Cruzaltense/RS dava 967 domicílios com água num
#: total de 616, e `pct_sem_agua` saía −56,98%.
#:
#: Medido em 2026-09-12: o valor estava errado em 5.477 dos 5.570 municípios
#: (98,3%) — os 93 restantes coincidiam por acaso —, com 418 negativos.
#:
#: A conta certa não precisa somar nada: `72153` JÁ É "não possui ligação",
#: e 72144+72145+72153 fecha com o total em 100,00% dos municípios (conferido
#: na guarda abaixo, que aborta se deixar de fechar).
TOTAL, SEM_LIGACAO = "72129", "72153"
COM_LIGACAO = ("72144", "72145")


def fetch_sem_agua() -> pd.DataFrame:
    print("[ivs] água encanada (Censo 2022, t/6803)...")
    cats = ",".join((TOTAL, *COM_LIGACAO, SEM_LIGACAO))
    df = _sidra(f"{SIDRA}/t/6803/n6/all/v/381/p/2022/c1821/{cats}")
    df = df[["D1C", "D4C", "V"]].rename(columns={"D1C": "cod7", "D4C": "cat", "V": "dom"})
    df["dom"] = pd.to_numeric(df["dom"], errors="coerce").fillna(0)
    df["municipio_cod"] = df["cod7"].astype(str).str[:6]
    p = df.pivot_table(index="municipio_cod", columns="cat", values="dom",
                       aggfunc="sum").fillna(0)

    # GUARDA: as três categorias de primeiro nível têm de somar o total. É ela
    # que teria pego o defeito original — e é ela que pega se o IBGE remexer a
    # classificação, porque aí a hierarquia deixa de fechar.
    faltando = [c for c in (TOTAL, *COM_LIGACAO, SEM_LIGACAO) if c not in p.columns]
    if faltando:
        raise SystemExit(f"[ivs] SIDRA não devolveu as categorias {faltando} — "
                         "a classificação c1821 mudou; a conta precisa ser refeita.")
    soma = p[list(COM_LIGACAO)].sum(axis=1) + p[SEM_LIGACAO]
    fora = (soma - p[TOTAL]).abs() > 1
    if fora.any():
        ex = p[fora].head(3).index.tolist()
        raise SystemExit(
            f"[ivs] em {int(fora.sum()):,} municípios as categorias de primeiro nível "
            f"não somam o total (ex.: {ex}). A hierarquia da c1821 mudou, e somar "
            "categoria de nível errado é exatamente o defeito de 2026-09-12.")

    out = p.reset_index()
    out["pct_sem_agua"] = (100 * out[SEM_LIGACAO] / out[TOTAL]).round(2)
    out = out.replace([float("inf")], pd.NA).dropna(subset=["pct_sem_agua"])
    if not out.pct_sem_agua.between(0, 100).all():
        raise SystemExit("[ivs] pct_sem_agua fora de 0–100 — proporção impossível.")
    return out[["municipio_cod", "pct_sem_agua"]]


def main() -> int:
    res = Resultado("scripts/pipeline_ivs.py")
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
    res.gravar(out, MARTS_DIR / "dim_ivs.parquet")

    url, key = env["SUPABASE_URL"], chave_escrita(env)
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
    return res.relatar()


if __name__ == "__main__":
    sys.exit(main())
