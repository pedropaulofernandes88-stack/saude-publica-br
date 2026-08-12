"""
analise_siops_icsap.py — gastar mais em saúde está associado a internar menos
por condição evitável?
==============================================================================

O projeto media desfecho (ICSAP, HSMR, mortalidade) e oferta física (leitos),
nunca o insumo financeiro. Com o SIOPS (scripts/pipeline_siops.py) a pergunta
fica testável: municípios que gastam mais por habitante têm menor proporção de
internações sensíveis à atenção primária?

DESENHO — o mesmo já estabelecido no projeto para APS × ICSAP e saúde
suplementar × ICSAP, porque o confundidor é o mesmo:

  1. correlação bruta;
  2. o confundidor de sempre: PORTE. Município pequeno tem gasto per capita mais
     alto (custo fixo diluído em menos gente) E %ICSAP mais alto (menos oferta
     de alta complexidade). Isso sozinho fabrica associação;
  3. correlação parcial controlando população e vulnerabilidade;
  4. o teste decisivo: dentro de cada QUARTIL DE PORTE, comparando cada
     município só com pares de tamanho semelhante;
  5. co-ocorrência (alto gasto + baixo %ICSAP) contra o esperado ao acaso;
  6. sensibilidade ao piso constitucional: quem declara abaixo de 15% difere?

POR QUE %ICSAP E NÃO ICSAP/100k — a taxa por habitante é confundida pelo ACESSO:
onde ninguém consegue internar, a taxa cai sem que a atenção primária seja boa.
A proporção pergunta outra coisa ("das internações que ocorreram, quantas eram
evitáveis?") e resiste melhor. Ambas são reportadas.

O QUE ISTO NÃO É — associação ecológica municipal, não efeito individual e não
causa. Gasto empenhado não é gasto executado, não é acesso e não é qualidade.
Um município pode gastar muito e mal.

Uso:
  .venv311/Scripts/python scripts/analise_siops_icsap.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parents[1]
MARTS = ROOT / "data" / "marts"
ANO = 2024


def spearman(x: pd.Series, y: pd.Series) -> tuple[float, int]:
    d = pd.DataFrame({"x": x, "y": y}).dropna()
    if len(d) < 10:
        return float("nan"), len(d)
    return float(d["x"].corr(d["y"], method="spearman")), len(d)


def spearman_parcial(y: pd.Series, x: pd.Series, controles: pd.DataFrame) -> tuple[float, int]:
    d = pd.concat([y.rename("y"), x.rename("x"), controles], axis=1).dropna()
    if len(d) < 20:
        return float("nan"), len(d)
    r = d.rank()
    C = np.column_stack([np.ones(len(r))] + [r[c].to_numpy() for c in controles.columns])

    def resid(v):
        beta, *_ = np.linalg.lstsq(C, v, rcond=None)
        return v - C @ beta

    return float(np.corrcoef(resid(r["y"].to_numpy()), resid(r["x"].to_numpy()))[0, 1]), len(d)


def main() -> None:
    siops = pd.read_parquet(MARTS / "mart_siops_municipio.parquet")
    siops = siops[siops.ano == ANO][["municipio_cod", "gasto_proprio_saude_hab",
                                      "transf_sus_hab", "pct_receita_propria_saude",
                                      "abaixo_do_minimo_ec29"]]
    icsap = pd.read_parquet(MARTS / "mart_icsap_municipio.parquet")
    icsap = icsap[icsap.ano == ANO][["municipio_cod", "municipio_nome", "uf_sigla",
                                      "internacoes_total", "internacoes_icsap",
                                      "pct_icsap", "icsap_100k", "populacao"]]
    ivs = pd.read_parquet(MARTS / "dim_ivs.parquet")[["municipio_cod", "ivs_score"]]

    df = icsap.merge(siops, on="municipio_cod", how="left").merge(ivs, on="municipio_cod", how="left")
    df["gasto_total_hab"] = df["gasto_proprio_saude_hab"].fillna(0) + df["transf_sus_hab"].fillna(0)
    df.loc[df["gasto_proprio_saude_hab"].isna(), "gasto_total_hab"] = np.nan

    print(f"=== Amostra: {len(df):,} municípios, {ANO} ===")
    print(f"gasto próprio/hab: mediana R$ {df.gasto_proprio_saude_hab.median():,.0f}, "
          f"P10 R$ {df.gasto_proprio_saude_hab.quantile(.1):,.0f}, "
          f"P90 R$ {df.gasto_proprio_saude_hab.quantile(.9):,.0f}, "
          f"sem declaração: {int(df.gasto_proprio_saude_hab.isna().sum())}")
    print(f"%ICSAP: mediana {df.pct_icsap.median():.1f}%")

    print("\n=== 1. Associação BRUTA (Spearman) ===")
    for rot, col in [("%ICSAP", "pct_icsap"), ("ICSAP/100k", "icsap_100k")]:
        r, n = spearman(df["gasto_proprio_saude_hab"], df[col])
        print(f"  gasto próprio/hab × {rot:<11}: rho = {r:+.3f}  (n={n:,})")

    print("\n=== 2. O confundidor de sempre: PORTE ===")
    r1, _ = spearman(df["populacao"], df["gasto_proprio_saude_hab"])
    r2, _ = spearman(df["populacao"], df["pct_icsap"])
    print(f"  população × gasto próprio/hab : rho = {r1:+.3f}")
    print(f"  população × %ICSAP            : rho = {r2:+.3f}")
    print("  (se ambos forem não-nulos e de sinais opostos, a bruta acima é em boa")
    print("   parte porte, não gasto)")

    print("\n=== 3. Parcial, controlando população e vulnerabilidade ===")
    ctrl = df[["populacao"]].assign(ivs_score=df["ivs_score"])
    for rot, col in [("%ICSAP", "pct_icsap"), ("ICSAP/100k", "icsap_100k")]:
        r, n = spearman_parcial(df[col], df["gasto_proprio_saude_hab"], ctrl)
        print(f"  gasto × {rot:<11} | pop, IVS : rho_parcial = {r:+.3f}  (n={n:,})")

    print("\n=== 4. Dentro do quartil de porte (n igual por grupo) ===")
    df["porte_quartil"] = pd.qcut(df["populacao"], 4,
                                   labels=["Q1 (menores)", "Q2", "Q3", "Q4 (maiores)"])
    rhos = []
    for _, g in df.groupby("porte_quartil", observed=True):
        r, n = spearman(g["gasto_proprio_saude_hab"], g["pct_icsap"])
        rhos.append(r)
        print(f"  {g['porte_quartil'].iloc[0]:16s} n={n:5,}  rho={r:+.3f}  "
              f"mediana gasto=R$ {g.gasto_proprio_saude_hab.median():>6,.0f}  "
              f"mediana %ICSAP={g.pct_icsap.median():5.1f}%")

    print("\n=== 5. Co-ocorrência: alto gasto + baixo %ICSAP, dentro do porte ===")
    df["pct_gasto_no_porte"] = df.groupby("porte_quartil", observed=True)[
        "gasto_proprio_saude_hab"].rank(pct=True)
    df["pct_icsap_no_porte"] = df.groupby("porte_quartil", observed=True)["pct_icsap"].rank(pct=True)
    alto_gasto = df["pct_gasto_no_porte"] >= 2 / 3
    baixo_icsap = df["pct_icsap_no_porte"] <= 1 / 3
    obs = (alto_gasto & baixo_icsap).mean()
    esp = alto_gasto.mean() * baixo_icsap.mean()
    print(f"  observado={obs*100:.2f}%  esperado sob independência={esp*100:.2f}%  "
          f"razão={obs/esp:.2f}×")

    print("\n=== 6. Quem declara abaixo do piso de 15% (EC 29) ===")
    ab = df[df["abaixo_do_minimo_ec29"] == True]  # noqa: E712
    ok = df[df["abaixo_do_minimo_ec29"] == False]  # noqa: E712
    print(f"  abaixo do piso: {len(ab):,} municípios | %ICSAP mediano {ab.pct_icsap.median():.1f}%")
    print(f"  no piso ou acima: {len(ok):,} | %ICSAP mediano {ok.pct_icsap.median():.1f}%")
    print("  (n pequeno demais para conclusão; serve para saber que o grupo existe)")

    print("\n=== Leitura ===")
    maior = max(abs(r) for r in rhos if not np.isnan(r))
    sinais = {np.sign(r) for r in rhos if not np.isnan(r) and abs(r) > 0.02}
    if maior < 0.10 and abs(obs / esp - 1) < 0.15:
        print("  => o gasto próprio por habitante NÃO explica a variação do %ICSAP entre")
        print("     municípios comparáveis. Some-se aos achados nulos de cobertura da APS e")
        print("     de saúde suplementar: o %ICSAP resiste a explicações de insumo, e o que")
        print("     move o indicador continua sendo porte e oferta hospitalar local.")
    elif len(sinais) > 1:
        print(f"  => sinal INCONSISTENTE entre quartis ({['%+.2f' % r for r in rhos]}) — resíduo")
        print("     de porte mal controlado, não efeito estável de gasto.")
    else:
        print(f"  => associação consistente dentro do porte (maior |rho| = {maior:.3f}).")
        print("     Ecológica e sem causa estabelecida, mas vale investigar.")

    out = df[["municipio_cod", "municipio_nome", "uf_sigla", "populacao",
              "gasto_proprio_saude_hab", "transf_sus_hab", "pct_receita_propria_saude",
              "abaixo_do_minimo_ec29", "internacoes_total", "internacoes_icsap",
              "pct_icsap", "icsap_100k", "ivs_score"]].copy()
    out["ano"] = ANO
    out.to_parquet(MARTS / "mart_siops_icsap_municipio.parquet", compression="zstd", index=False)
    print(f"\n[mart] mart_siops_icsap_municipio: {len(out):,} municípios")


if __name__ == "__main__":
    main()
