"""
analise_cobertura_icsap.py — Cobertura da APS x ICSAP: a hipotese e o confundimento
===================================================================================

Pergunta: municipios com maior cobertura de Atencao Primaria internam menos por
condicoes sensiveis a atencao primaria (ICSAP)?

A hipotese de politica publica diz que sim. Este script testa isso e, mais
importante, testa se a associacao bruta sobrevive ao controle do principal
confundidor suspeito: o TAMANHO do municipio.

Por que o tamanho confunde: a cobertura potencial e capacidade instalada
(n equipes x capacidade padrao por equipe) dividida pela populacao. Em
municipios pequenos, poucas equipes ja saturam o indicador (>100%, ate 800%).
Esses mesmos municipios pequenos tendem a ter ICSAP alto por outras razoes
(menos alternativas assistenciais, menos especialistas, hospital local que
interna o que um centro maior resolveria em ambulatorio). Logo, uma correlacao
positiva bruta entre cobertura e ICSAP pode ser inteiramente artefato de
tamanho, e nao evidencia de que APS "causa" internacao.

Saidas: estatisticas impressas + data/marts/mart_cobertura_icsap_municipio.parquet
(o painel cruzado, para o site).

Uso:
  .venv311/Scripts/python scripts/analise_cobertura_icsap.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

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
ANO = 2024


def spearman(x: pd.Series, y: pd.Series) -> tuple[float, int]:
    """Correlacao de postos (robusta a nao-linearidade e outliers)."""
    d = pd.DataFrame({"x": x, "y": y}).dropna()
    if len(d) < 10:
        return float("nan"), len(d)
    return float(d["x"].corr(d["y"], method="spearman")), len(d)


def partial_spearman(y: pd.Series, x: pd.Series, controls: pd.DataFrame) -> tuple[float, int]:
    """
    Correlacao parcial de postos: correlaciona os RESIDUOS de y~controles com os
    residuos de x~controles. Se a associacao bruta era artefato dos controles,
    a parcial colapsa para perto de zero.
    """
    d = pd.concat([y.rename("y"), x.rename("x"), controls], axis=1).dropna()
    if len(d) < 20:
        return float("nan"), len(d)
    r = d.rank()  # postos -> regressao linear sobre postos = Spearman parcial
    C = np.column_stack([np.ones(len(r))] + [r[c].to_numpy() for c in controls.columns])

    def resid(v: np.ndarray) -> np.ndarray:
        beta, *_ = np.linalg.lstsq(C, v, rcond=None)
        return v - C @ beta

    ry, rx = resid(r["y"].to_numpy()), resid(r["x"].to_numpy())
    return float(np.corrcoef(ry, rx)[0, 1]), len(d)


def main() -> None:
    cob = pd.read_parquet(MARTS / "mart_cobertura_aps_municipio.parquet")
    icsap = pd.read_parquet(MARTS / "mart_icsap_municipio.parquet")
    ivs = pd.read_parquet(MARTS / "dim_ivs.parquet")[["municipio_cod", "ivs_score"]]

    # cobertura media do ano (12 competencias) por municipio
    cob_ano = (cob[cob.ano == ANO]
               .groupby("municipio_cod", as_index=False)
               .agg(cobertura_pct=("cobertura_pct", "mean"),
                    qt_esf=("qt_esf", "mean"),
                    populacao_aps=("populacao", "mean")))
    cob_ano["cobertura_pct"] = cob_ano["cobertura_pct"].round(2)

    df = (icsap[icsap.ano == ANO]
          .merge(cob_ano, on="municipio_cod", how="inner")
          .merge(ivs, on="municipio_cod", how="left"))

    # Cobertura "efetiva": o indicador oficial nao e limitado, mas para fins de
    # comparacao entre municipios, capacidade acima de 100% da populacao nao
    # representa mais acesso — representa saturacao. Publicamos as duas.
    df["cobertura_efetiva"] = df["cobertura_pct"].clip(upper=100)

    print(f"=== Amostra: {len(df):,} municipios, {ANO} ===")
    print(f"cobertura bruta   — mediana {df.cobertura_pct.median():.1f}% | "
          f"acima de 100%: {(df.cobertura_pct > 100).mean()*100:.1f}%")
    print(f"cobertura efetiva — mediana {df.cobertura_efetiva.median():.1f}% | "
          f"saturados em 100%: {(df.cobertura_efetiva >= 100).mean()*100:.1f}%")

    print("\n=== 1. Associacao BRUTA (Spearman) ===")
    for nome, col in [("cobertura bruta", "cobertura_pct"), ("cobertura efetiva", "cobertura_efetiva")]:
        r, n = spearman(df[col], df["icsap_100k"])
        print(f"  {nome:18s} x ICSAP/100k : rho = {r:+.3f}  (n={n:,})")
        r2, _ = spearman(df[col], df["pct_icsap"])
        print(f"  {nome:18s} x %ICSAP     : rho = {r2:+.3f}")

    print("\n=== 2. O confundidor: TAMANHO do municipio ===")
    r_pop_cob, _ = spearman(df["populacao"], df["cobertura_pct"])
    r_pop_ics, _ = spearman(df["populacao"], df["icsap_100k"])
    print(f"  populacao x cobertura bruta : rho = {r_pop_cob:+.3f}")
    print(f"  populacao x ICSAP/100k      : rho = {r_pop_ics:+.3f}")
    print("  (se ambos forem fortes e de sinais opostos, a associacao bruta e suspeita)")

    print("\n=== 3. Associacao PARCIAL (controlando populacao e vulnerabilidade) ===")
    for nome, col in [("cobertura bruta", "cobertura_pct"), ("cobertura efetiva", "cobertura_efetiva")]:
        ctrl = df[["populacao"]].assign(ivs_score=df["ivs_score"])
        r, n = partial_spearman(df["icsap_100k"], df[col], ctrl)
        print(f"  {nome:18s} x ICSAP/100k | pop, IVS : rho_parcial = {r:+.3f}  (n={n:,})")

    print("\n=== 4. Estratificado por porte populacional ===")
    faixas = [(0, 10_000), (10_000, 50_000), (50_000, 200_000), (200_000, 10**9)]
    rotulos = ["< 10 mil", "10-50 mil", "50-200 mil", "> 200 mil"]
    linhas = []
    for (lo, hi), rot in zip(faixas, rotulos):
        sub = df[(df.populacao >= lo) & (df.populacao < hi)]
        r_bruta, n = spearman(sub["cobertura_pct"], sub["icsap_100k"])
        r_efet, _ = spearman(sub["cobertura_efetiva"], sub["icsap_100k"])
        med_cob = sub.cobertura_pct.median()
        med_ics = sub.icsap_100k.median()
        print(f"  {rot:12s} n={n:5,}  rho_bruta={r_bruta:+.3f}  rho_efetiva={r_efet:+.3f}  "
              f"| mediana cobertura {med_cob:6.1f}%  ICSAP/100k {med_ics:7.1f}")
        linhas.append((rot, n, r_bruta, r_efet, med_cob, med_ics))

    print("\n=== 5. Leitura ===")
    r_bruta_geral, _ = spearman(df["cobertura_pct"], df["icsap_100k"])
    ctrl = df[["populacao"]].assign(ivs_score=df["ivs_score"])
    r_parcial_geral, _ = partial_spearman(df["icsap_100k"], df["cobertura_pct"], ctrl)
    reducao = abs(r_bruta_geral) - abs(r_parcial_geral)
    print(f"  |rho| bruta {abs(r_bruta_geral):.3f} -> parcial {abs(r_parcial_geral):.3f} "
          f"(reducao de {reducao:+.3f})")
    if abs(r_parcial_geral) < 0.10:
        print("  => a associacao NAO sobrevive ao controle: era majoritariamente confundimento.")
    elif abs(r_parcial_geral) < abs(r_bruta_geral) * 0.6:
        print("  => a associacao encolhe muito: parte relevante era confundimento.")
    else:
        print("  => a associacao sobrevive ao controle.")

    # mart cruzado para o site
    out = df[["municipio_cod", "municipio_nome", "uf_sigla", "regiao", "populacao",
              "cobertura_pct", "cobertura_efetiva", "qt_esf",
              "internacoes_total", "internacoes_icsap", "pct_icsap", "icsap_100k",
              "ivs_score"]].copy()
    out["ano"] = ANO
    out["qt_esf"] = out["qt_esf"].round(1)
    escrever_parquet(
        out, MARTS / "mart_cobertura_icsap_municipio.parquet",
        origem="pipeline", produtor="scripts/analise_cobertura_icsap.py")
    print(f"\n[mart] mart_cobertura_icsap_municipio: {len(out):,} municipios")


if __name__ == "__main__":
    main()
