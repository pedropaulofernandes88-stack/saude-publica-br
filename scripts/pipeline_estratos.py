"""
pipeline_estratos.py — Arquétipos de saúde municipal (estratificação determinística)
====================================================================================

Substitui o k-means que ocupava este lugar até 2026-08-29. A troca não foi de
gosto: a estabilidade do agrupamento anterior foi medida e reprovada.

  k-means (k=5, z-score, semente 42)
    silhueta caindo monotonicamente a partir de K=2 — ou seja, os dados não
    têm cinco grumos, têm um contínuo que o algoritmo era obrigado a cortar;
    ARI de 0,571 entre reamostragens; 280 municípios (16%) trocavam de grupo
    SEM QUE O DADO DELES MUDASSE. Um município que consultasse o site duas
    vezes podia ler dois arquétipos diferentes.

  estratificação por tercis com CORTES CONGELADOS (este arquivo)
    ARI 1,000 por construção: o estrato de um município é função apenas dos
    três valores dele contra três constantes versionadas aqui embaixo.
    Nenhuma semente, nenhuma vizinhança, nenhuma reamostragem.

O corte é uma DECISÃO, não um cálculo. Por isso ele mora no repositório e não
é recalculado a cada execução: se o corte se movesse junto com os dados, um
município mudaria de estrato porque outros municípios mudaram — que é
exatamente o defeito que estamos removendo. O pipeline recalcula os tercis só
para CONFERIR a distância até os cortes congelados e falhar alto se a base
tiver andado demais (ver TOLERANCIA).

Honestidade sobre o que continua valendo: reamostrando a base e recalculando
os cortes, o ARI fica em 0,899 (p10 0,846) e 10 municípios (0,6%) trocariam
em mais da metade das reamostragens. Ou seja, ainda há municípios em cima da
fronteira — só que agora eles são poucos, identificáveis, e não se movem
sozinhos entre duas visitas ao site.

Três dimensões, as mesmas de antes:
  - mortalidade padronizada por idade (SIM, 2023)
  - vulnerabilidade social (proxy Censo 2022)
  - internações por 100 mil hab. (SIH, 2023)

Uso: .venv311/Scripts/python scripts/pipeline_estratos.py
"""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd
import requests
from _supabase_key import chave_escrita

# A linhagem viaja com os BYTES: `escrever_parquet` grava no proprio
# Parquet quem o produziu. Sem isso, um arquivo que veio do Postgres e um
# que veio do pipeline sao indistinguiveis, e o manifesto afirma o que
# ninguem verificou.
sys.path.insert(0, str(Path(__file__).resolve().parent))
from _publicacao import escrever_parquet  # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parents[1]
MARTS = ROOT / "data" / "marts"
ANO = 2023
POP_MINIMA = 20000

FEATS = ["taxa_padronizada_100k", "ivs_score", "internacoes_100k"]

# Cortes congelados em 2026-08-29, calculados como os tercis (percentis 33,3 e
# 66,7) da base de 1.728 municipios com populacao >= 20 mil no ano de 2023.
# NAO recalcular automaticamente: ver o cabecalho deste arquivo.
CORTES: dict[str, tuple[float, float]] = {
    "taxa_padronizada_100k": (680.26, 751.09),   # obitos/100k, padronizada
    "ivs_score": (28.60, 43.53),                 # 0-100, alto = mais vulneravel
    "internacoes_100k": (6000.37, 7534.23),      # internacoes/100k
}
CORTES_CONGELADOS_EM = "2026-08-29"

# Se a base andar mais do que isso em relacao ao corte congelado, o pipeline
# para. Nao e erro de dado: e sinal de que a decisao precisa ser revisitada por
# gente, e re-congelada de proposito.
TOLERANCIA = 0.10

ROTULOS = {
    "taxa_padronizada_100k": ("mortalidade baixa", "mortalidade média", "mortalidade alta"),
    "ivs_score": ("vulnerabilidade baixa", "vulnerabilidade média", "vulnerabilidade alta"),
    "internacoes_100k": ("pouca internação", "internação média", "muita internação"),
}
SIGLAS = {"taxa_padronizada_100k": "M", "ivs_score": "V", "internacoes_100k": "I"}


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


def tercil(valor: float, corte: tuple[float, float]) -> int:
    """1, 2 ou 3 — funcao APENAS do valor do proprio municipio."""
    if valor < corte[0]:
        return 1
    if valor < corte[1]:
        return 2
    return 3


def estrato_id(tm: int, tv: int, ti: int) -> int:
    """1..27, na ordem mortalidade -> vulnerabilidade -> internacao."""
    return (tm - 1) * 9 + (tv - 1) * 3 + (ti - 1) + 1


def conferir_deriva(df: pd.DataFrame) -> None:
    """Recalcula os tercis da base atual e compara com o corte congelado.

    Nao aplica o resultado — so decide se o corte ainda descreve esta base.
    """
    print(f"[estrato] cortes congelados em {CORTES_CONGELADOS_EM}; conferindo deriva")
    estourou = []
    for f in FEATS:
        q1, q2 = np.quantile(df[f].to_numpy(dtype=float), [1 / 3, 2 / 3])
        for atual, congelado, qual in ((q1, CORTES[f][0], "inferior"), (q2, CORTES[f][1], "superior")):
            deriva = abs(atual - congelado) / congelado
            marca = "  <-- ESTOUROU" if deriva > TOLERANCIA else ""
            print(f"   {f:24s} {qual}: congelado {congelado:9.2f} | base atual "
                  f"{atual:9.2f} | deriva {100 * deriva:5.2f}%{marca}")
            if deriva > TOLERANCIA:
                estourou.append(f"{f} ({qual}): {100 * deriva:.1f}%")
    if estourou:
        raise SystemExit(
            "\n[estrato] ABORTA: a base andou mais que a tolerancia de "
            f"{100 * TOLERANCIA:.0f}% nos cortes: {'; '.join(estourou)}.\n"
            "  Isso NAO e falha de coleta — e sinal de que os cortes de "
            f"{CORTES_CONGELADOS_EM} nao descrevem mais esta base.\n"
            "  A decisao de re-congelar e humana: recalcule os tercis, revise o "
            "efeito sobre mart_icsap_pares\n"
            "  e atualize CORTES e CORTES_CONGELADOS_EM neste arquivo, no mesmo "
            "commit que explica por que.")


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
    # Municipios pequenos ficam de fora: com poucos eventos, a taxa oscila por
    # acaso e o estrato descreveria ruido.
    df = df[(df.populacao >= POP_MINIMA) & df.taxa_padronizada_100k.notna()
            & df.ivs_score.notna() & df.internacoes_100k.notna()].copy()
    print(f"[estrato] {len(df)} municípios (pop>={POP_MINIMA:,}, {ANO})")

    conferir_deriva(df)

    for f in FEATS:
        df["t_" + f] = df[f].map(lambda v, c=CORTES[f]: tercil(float(v), c))

    df["cluster"] = [
        estrato_id(a, b, c) for a, b, c in zip(
            df["t_" + FEATS[0]], df["t_" + FEATS[1]], df["t_" + FEATS[2]], strict=True)
    ]
    df["estrato_cod"] = [
        "".join(f"{SIGLAS[f]}{t}" for f, t in zip(FEATS, ts, strict=True))
        for ts in zip(*(df["t_" + f] for f in FEATS), strict=True)
    ]
    df["perfil"] = [
        ", ".join(ROTULOS[f][t - 1] for f, t in zip(FEATS, ts, strict=True))
        for ts in zip(*(df["t_" + f] for f in FEATS), strict=True)
    ]

    out = df[["municipio_cod", "municipio_nome", "uf_sigla", "regiao", "cluster",
              "estrato_cod", "perfil", "taxa_padronizada_100k", "ivs_score",
              "internacoes_100k"]].copy()
    out["ivs_score"] = out["ivs_score"].round(1)

    # Guarda: rotulo e estrato tem que ser bijetivos. Se dois estratos dividirem
    # o mesmo rotulo, o texto do boletim deixa de identificar o grupo.
    pares = out.groupby("cluster").perfil.nunique()
    if (pares > 1).any() or out.groupby("perfil").cluster.nunique().gt(1).any():
        raise SystemExit("[estrato] ABORTA: rótulo e estrato deixaram de ser 1-para-1")

    MARTS.mkdir(exist_ok=True)
    escrever_parquet(
        out, MARTS / "dim_cluster_municipio.parquet",
        origem="pipeline", produtor="scripts/pipeline_estratos.py")

    tam = out.cluster.value_counts()
    print(f"[estrato] {len(tam)} estratos ocupados de 27; menor={tam.min()}, "
          f"mediana={int(tam.median())}, maior={tam.max()}")
    for c in sorted(out.cluster.unique()):
        sub = out[out.cluster == c]
        print(f"  estrato {c:2d} {sub.estrato_cod.iloc[0]} (n={len(sub):3d}): {sub.perfil.iloc[0]}")

    if "--offline" in sys.argv:
        print("[estrato] --offline: parquet gravado, upload pulado.")
        return

    url, key = env["SUPABASE_URL"], chave_escrita(env)
    h = {"apikey": key, "Authorization": f"Bearer {key}", "Content-Type": "application/json",
         "Prefer": "return=minimal,resolution=merge-duplicates"}
    recs = out.astype(object).where(pd.notna(out), None).to_dict("records")
    for i in range(0, len(recs), 5000):
        body = json.dumps(recs[i:i + 5000],
                          default=lambda o: o.item() if hasattr(o, "item") else o,
                          allow_nan=False)
        r = requests.post(f"{url.rstrip('/')}/rest/v1/dim_cluster_municipio",
                          headers=h, data=body, timeout=300)
        if r.status_code not in (200, 201):
            raise RuntimeError(f"upload: HTTP {r.status_code} {r.text[:200]}")
    print(f"[supabase] dim_cluster_municipio: {len(recs)} OK")

    cortes_txt = "; ".join(
        f"{f}: {CORTES[f][0]}/{CORTES[f][1]}" for f in FEATS)
    meta = [{"chave": "fonte_clusters",
             "valor": ("Estratificação determinística por tercis com cortes congelados em "
                       f"{CORTES_CONGELADOS_EM} ({cortes_txt}) sobre mortalidade padronizada "
                       f"(SIM {ANO}), vulnerabilidade-proxy (Censo 2022) e internações/100k "
                       f"(SIH {ANO}). Municípios com pop>={POP_MINIMA // 1000} mil. "
                       "Substitui o k-means, reprovado em teste de estabilidade "
                       "(ARI 0,571; 16% dos municípios reclassificados sem mudança de dado).")},
            {"chave": "gerado_em", "valor": datetime.now().isoformat(timespec="seconds")}]
    requests.post(f"{url.rstrip('/')}/rest/v1/meta_dataset", headers=h,
                  data=json.dumps(meta), timeout=60)
    print("[done] estratos concluído.")


if __name__ == "__main__":
    main()
