"""
hsmr_intervalo_confianca.py — IC95%, p-valor exato e correcao FDR para o HSMR
==============================================================================

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

PROBLEMA DE MULTIPLAS COMPARACOES — por que o IC bruto nao basta.
Publicamos ~4.600 hospitais por ano, cada um com seu proprio teste implicito
(o IC nao contem 1?). Testar milhares de hipoteses simultaneamente ao nivel de
5% garante, por construcao, uma quantidade grande de falsos positivos: ao
acaso, ~5% dos hospitais teriam HSMR "significativamente" diferente de 1 mesmo
que a mortalidade real de TODOS fosse identica ao esperado. Em 2024 (4.633
hospitais testaveis), isso e ~232 falsos positivos esperados so por acaso —
~15% do grupo hoje classificado "acima do esperado" (778 hospitais).

Corrigimos com Benjamini-Hochberg (controle da taxa de falsas descobertas,
FDR), aplicado por ano civil (cada ano e uma familia de testes independente).
O p-valor exato de Poisson (bilateral) e calculado e depois ajustado; a
classificacao `significancia` passa a usar o q-valor (p ajustado), nao mais o
IC bruto. Em 2024, isso reduz o grupo "acima" de 778 para ~690 hospitais —
os que sobrevivem ao controle de multiplas comparacoes.

Leitura: `significancia` = acima/abaixo quando q < 0,05 (a diferenca resiste
ao controle de multiplas comparacoes); "esperado" quando q >= 0,05, mesmo que
o IC95% bruto exclua 1. O IC (`hsmr_ic95_inf/sup`) continua publicado como
faixa descritiva do ponto estimado, mas a classificacao categorica agora
reflete o q-valor, nao o IC bruto isoladamente.

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

from _supabase_key import chave_escrita
from scipy.stats import gamma as gamma_dist
from scipy.stats import poisson as poisson_dist

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


def add_ic95(df: pd.DataFrame, col_esperado: str = "obitos_esperados") -> pd.DataFrame:
    """
    IC95% gamma (Poisson exato) do HSMR, a partir de observado e esperado.

    `col_esperado` permite calcular o intervalo sobre o esperado recalibrado
    por estrato — necessario para que a faixa publicada corresponda a mesma
    regua da classificacao (do contrario o IC diria uma coisa e a flag outra).
    """
    obs = df["obitos_observados"].to_numpy(dtype=float)
    esp = df[col_esperado].to_numpy(dtype=float)

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
    return df


def _p_valor_poisson(obs: np.ndarray, esp: np.ndarray) -> np.ndarray:
    """P-valor bilateral exato: P(observar um desvio >= |O-E| sob H0: taxa=E)."""
    maior_ou_igual = obs >= esp
    p = np.where(
        maior_ou_igual,
        2 * poisson_dist.sf(obs - 1, esp),
        2 * poisson_dist.cdf(obs, esp),
    )
    return np.minimum(p, 1.0)


def _bh_fdr(p: np.ndarray, alpha: float = 0.05) -> np.ndarray:
    """
    Benjamini-Hochberg: retorna o q-valor (p-valor ajustado) para cada teste.
    Implementacao direta (sem statsmodels): ordena por p, aplica o fator
    m/rank, garante monotonicidade (q nao pode cair ao percorrer do maior
    p-valor para o menor).
    """
    n = len(p)
    ordem = np.argsort(p)
    p_ord = p[ordem]
    q_ord = p_ord * n / (np.arange(n) + 1)
    q_ord = np.minimum.accumulate(q_ord[::-1])[::-1]  # monotonicidade
    q_ord = np.minimum(q_ord, 1.0)
    q = np.empty(n)
    q[ordem] = q_ord
    return q


def add_estrato_uti(df: pd.DataFrame) -> pd.DataFrame:
    """
    Anexa o estrato de complexidade (com/sem UTI) por hospital-ano, a partir de
    data/refs/hsmr_estratos_uti.parquet (ver scripts/hsmr_estratos_uti.py).

    Hospitais sem correspondencia no cadastro de leitos daquela competencia
    ficam com estrato "indefinido" e sao tratados como uma familia propria: nao
    da para recalibra-los sem saber a que grupo pertencem.
    """
    ref = ROOT / "data" / "refs" / "hsmr_estratos_uti.parquet"
    if not ref.exists():
        raise SystemExit(
            f"faltando {ref}. Rode antes: scripts/hsmr_estratos_uti.py --anos 2022 2023 2024"
        )
    # O script roda sobre o proprio mart, entao precisa ser idempotente: colunas
    # derivadas de uma execucao anterior sao descartadas antes de recalcular
    # (do contrario o merge geraria tem_uti_x / tem_uti_y).
    derivadas = ["tem_uti", "leitos_total", "leitos_uti", "estrato",
                 "fator_estrato", "obitos_esperados_estrato", "hsmr_estrato"]
    df = df.drop(columns=[c for c in derivadas if c in df.columns])

    est = pd.read_parquet(ref)[["cnes", "ano", "tem_uti", "leitos_total", "leitos_uti"]]
    est["ano"] = est["ano"].astype(df["ano"].dtype)
    df = df.merge(est, on=["cnes", "ano"], how="left")
    df["estrato"] = np.where(df["tem_uti"].isna(), "indefinido",
                             np.where(df["tem_uti"].fillna(False), "com_uti", "sem_uti"))
    # o merge com how="left" promove as contagens a float (NaN nos sem
    # correspondencia); o destino no Postgres e integer.
    for c in ["leitos_total", "leitos_uti"]:
        df[c] = df[c].round().astype("Int64")
    return df


def recalibrar_por_estrato(df: pd.DataFrame) -> pd.DataFrame:
    """
    Recalibra o esperado DENTRO de cada estrato (ano x com/sem UTI).

    Por que: a padronizacao indireta usa taxas nacionais por faixa etaria x
    capitulo CID-10, um ajuste que enxerga diagnostico e nao gravidade. Como
    hospital com UTI recebe sistematicamente o caso critico do mesmo capitulo,
    o O/E agregado dos dois grupos nao e 1 — medimos 1,163 (com UTI) e 0,542
    (sem UTI) em 2024, contra 1,000 nacional por construcao. Comparar os dois
    grupos na mesma regua faz o indicador sinalizar "tem UTI", nao "assiste
    pior".

    A recalibracao multiplica o esperado pelo O/E agregado do proprio estrato,
    de modo que cada grupo passe a somar exatamente 1. O HSMR resultante
    responde "este hospital difere dos hospitais COMO ELE?" — mesma logica do
    desenho pareado ja usado em ICSAP e cobertura da APS.
    """
    fatores = (df[df["obitos_esperados"] > 0]
               .groupby(["ano", "estrato"])
               .apply(lambda g: g["obitos_observados"].sum() / g["obitos_esperados"].sum(),
                      include_groups=False)
               .rename("fator_estrato").reset_index())
    df = df.merge(fatores, on=["ano", "estrato"], how="left")
    df["fator_estrato"] = df["fator_estrato"].fillna(1.0)
    df["obitos_esperados_estrato"] = df["obitos_esperados"] * df["fator_estrato"]
    df["hsmr_estrato"] = np.where(
        df["obitos_esperados_estrato"] > 0,
        (df["obitos_observados"] / df["obitos_esperados_estrato"]).round(3),
        np.nan,
    )
    return df


def add_significancia_fdr(df: pd.DataFrame) -> pd.DataFrame:
    """
    P-valor exato de Poisson + correcao de multiplas comparacoes (Benjamini-
    Hochberg), calculados sobre o esperado RECALIBRADO POR ESTRATO e com a
    familia de testes definida por (ano, estrato) — cada grupo de hospitais
    comparaveis e uma familia independente.

    Classificacao final: acima/abaixo do esperado exigem q-valor < 0,05.
    Hospitais com esperado = 0 nao admitem teste -> "indeterminado".
    """
    obs = df["obitos_observados"].to_numpy(dtype=float)
    esp = df["obitos_esperados_estrato"].to_numpy(dtype=float)
    valido = esp > 0

    p = np.full(len(df), np.nan)
    p[valido] = _p_valor_poisson(obs[valido], esp[valido])
    df["hsmr_pvalor"] = np.round(p, 5)

    q_col = pd.Series(np.nan, index=df.index)
    for _, g in df.groupby(["ano", "estrato"]):
        sub = g[g["hsmr_pvalor"].notna()]
        if len(sub) == 0:
            continue
        q_col.loc[sub.index] = _bh_fdr(sub["hsmr_pvalor"].to_numpy())
    df["hsmr_q_valor"] = np.round(q_col.to_numpy(), 5)

    acima = (df["hsmr_estrato"] > 1) & (df["hsmr_q_valor"] < 0.05)
    abaixo = (df["hsmr_estrato"] < 1) & (df["hsmr_q_valor"] < 0.05)
    indet = df["hsmr_q_valor"].isna()
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
    df = add_estrato_uti(df)
    df = recalibrar_por_estrato(df)
    df = add_ic95(df, col_esperado="obitos_esperados_estrato")
    df = add_significancia_fdr(df)

    print("[hsmr-ic] calibracao por estrato (O/E agregado ANTES da recalibracao):")
    for (ano, estrato), g in df[df.obitos_esperados > 0].groupby(["ano", "estrato"]):
        oe = g.obitos_observados.sum() / g.obitos_esperados.sum()
        print(f"  {ano} {estrato:11s} n={len(g):5,}  O/E = {oe:.3f}"
              f"{'   <- referencia nacional e 1,000 por construcao' if estrato == 'com_uti' else ''}")
    print("  (nenhum grupo estava em 1: o ajuste por capitulo CID nao captura gravidade)")

    print(f"\n[hsmr-ic] {len(df):,} registros hospital-ano")
    for ano, g in df.groupby("ano"):
        dist = g["significancia"].value_counts()
        n = len(g)
        bruto = (g["hsmr_pvalor"] < 0.05).sum()
        print(f"  {ano}: acima={dist.get('acima',0):5,} ({dist.get('acima',0)/n*100:4.1f}%)  "
              f"abaixo={dist.get('abaixo',0):5,} ({dist.get('abaixo',0)/n*100:4.1f}%)  "
              f"dentro do esperado={dist.get('esperado',0):5,} ({dist.get('esperado',0)/n*100:4.1f}%)  "
              f"| sem correcao FDR seriam {bruto:,} significativos")

    # efeito da correcao FDR: quantos hospitais perdem o rotulo de significancia
    total_testado = df["hsmr_pvalor"].notna().sum()
    sig_bruto = (df["hsmr_pvalor"] < 0.05).sum()
    sig_fdr = (df["significancia"] != "esperado") & (df["significancia"] != "indeterminado")
    print(f"\n  hospitais testaveis: {total_testado:,}")
    print(f"  significativos SEM correcao (p<0,05)   : {sig_bruto:,} ({sig_bruto/total_testado*100:.1f}%)")
    print(f"  significativos APOS FDR (q<0,05)        : {sig_fdr.sum():,} ({sig_fdr.sum()/total_testado*100:.1f}%)")
    print(f"  perdem o rotulo de significancia         : {sig_bruto - sig_fdr.sum():,}")
    print("  -> sem essa correcao, parte do grupo 'acima do esperado' seria ruido estatistico")

    df.to_parquet(src, compression="zstd", index=False)
    print(f"\n[hsmr-ic] mart atualizado: {src.name}")

    if args.no_upload:
        return
    env = load_env()
    url, key = env["SUPABASE_URL"], chave_escrita(env)
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
