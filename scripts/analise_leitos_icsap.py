"""
analise_leitos_icsap.py — a falta de leito infla o %ICSAP?

O preprint da cobertura da APS declara, sem testar, que:

  "Proporcao alta de ICSAP pode ser efeito de acesso restrito. Onde faltam
   leitos, a internacao eletiva desaparece e a fatia de ICSAP sobe
   mecanicamente."

Ate agora isso era hipotese: nao havia dado de leitos. Agora ha
(scripts/pipeline_cnes_leitos.py). Este script testa.

MECANISMO PROPOSTO, em duas partes testaveis separadamente:
  (a) onde faltam leitos, o TOTAL de internacoes por habitante cai;
  (b) o que sobra e desproporcionalmente urgente/sensivel, entao %ICSAP sobe.
Se (a) e (b) valem juntos, %ICSAP alto em municipio sem leito e artefato de
denominador, nao sinal de atencao primaria fraca.

ARMADILHA SEMANTICA CENTRAL -- residencia x estabelecimento:
  ICSAP  vem do SIH por municipio de RESIDENCIA do paciente (CODMUNRES).
  Leitos vem do CNES por municipio do ESTABELECIMENTO (CODUFMUN).
Sao coisas diferentes: um morador de municipio sem leito nenhum se interna em
outro municipio, e essa internacao conta para a residencia dele. Ou seja,
"zero leitos no municipio" NAO significa "zero acesso a leito" -- significa
que o acesso depende de deslocamento. Por isso a leitura correta da variavel
nao e "oferta disponivel ao morador", e sim "oferta LOCAL", e o efeito
esperado passa por barreira de deslocamento, nao por ausencia absoluta.
Essa distincao esta declarada em toda a saida.

Uso:
  .venv311/Scripts/python scripts/analise_leitos_icsap.py
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


def partial_spearman(y: pd.Series, x: pd.Series, controls: pd.DataFrame) -> tuple[float, int]:
    d = pd.concat([y.rename("y"), x.rename("x"), controls], axis=1).dropna()
    if len(d) < 20:
        return float("nan"), len(d)
    r = d.rank()
    C = np.column_stack([np.ones(len(r))] + [r[c].to_numpy() for c in controls.columns])

    def resid(v: np.ndarray) -> np.ndarray:
        beta, *_ = np.linalg.lstsq(C, v, rcond=None)
        return v - C @ beta

    return float(np.corrcoef(resid(r["y"].to_numpy()), resid(r["x"].to_numpy()))[0, 1]), len(d)


def main() -> None:
    ic = pd.read_parquet(MARTS / "mart_icsap_municipio.parquet")
    ic = ic[ic.ano == ANO][["municipio_cod", "municipio_nome", "uf_sigla", "regiao",
                             "internacoes_total", "internacoes_icsap", "pct_icsap",
                             "icsap_100k", "populacao"]]
    lt = pd.read_parquet(MARTS / "mart_leitos_municipio.parquet")
    lt = lt[lt.ano == ANO][["municipio_cod", "leitos_total", "leitos_sus", "leitos_uti",
                             "leitos_sus_por_mil"]]
    ivs = pd.read_parquet(MARTS / "dim_ivs.parquet")[["municipio_cod", "ivs_score"]]

    df = ic.merge(lt, on="municipio_cod", how="inner").merge(ivs, on="municipio_cod", how="left")
    df["internacoes_por_mil"] = df.internacoes_total / df.populacao * 1_000
    df["sem_leito"] = df.leitos_total == 0

    print(f"=== Amostra: {len(df):,} municipios, {ANO} ===")
    print(f"municipios SEM nenhum leito: {df.sem_leito.sum():,} ({df.sem_leito.mean()*100:.1f}%)")
    print("(atencao: 'sem leito' = sem oferta LOCAL. O morador se interna em outro")
    print(" municipio e a internacao conta para a residencia dele -- ver docstring.)")

    print("\n=== 1. O mecanismo, parte (a): falta de leito reduz internacao total? ===")
    r_a, n_a = spearman(df["leitos_sus_por_mil"], df["internacoes_por_mil"])
    print(f"  leitos SUS/mil x internacoes/mil (residencia): rho = {r_a:+.3f}  (n={n_a:,})")
    com = df[~df.sem_leito].internacoes_por_mil.median()
    sem = df[df.sem_leito].internacoes_por_mil.median()
    print(f"  internacoes/mil mediana -- COM leito local: {com:.1f} | SEM leito local: {sem:.1f} "
          f"({(sem/com-1)*100:+.1f}%)")

    print("\n=== 2. O mecanismo, parte (b): falta de leito eleva a FATIA de ICSAP? ===")
    r_b, n_b = spearman(df["leitos_sus_por_mil"], df["pct_icsap"])
    print(f"  leitos SUS/mil x %ICSAP: rho = {r_b:+.3f}  (n={n_b:,})")
    com_p = df[~df.sem_leito].pct_icsap.median()
    sem_p = df[df.sem_leito].pct_icsap.median()
    print(f"  %ICSAP mediana -- COM leito local: {com_p:.1f}% | SEM leito local: {sem_p:.1f}% "
          f"({sem_p-com_p:+.1f} p.p.)")

    print("\n=== 3. O confundidor de sempre: PORTE ===")
    r_pop_lt, _ = spearman(df["populacao"], df["leitos_sus_por_mil"])
    r_pop_ic, _ = spearman(df["populacao"], df["pct_icsap"])
    print(f"  populacao x leitos SUS/mil : rho = {r_pop_lt:+.3f}")
    print(f"  populacao x %ICSAP         : rho = {r_pop_ic:+.3f}")
    ctrl = df[["populacao"]].assign(ivs_score=df["ivs_score"])
    r_p, n_p = partial_spearman(df["pct_icsap"], df["leitos_sus_por_mil"], ctrl)
    print(f"  leitos SUS/mil x %ICSAP | pop, IVS : rho_parcial = {r_p:+.3f}  (n={n_p:,})")

    print("\n=== 4. Dentro do quartil de porte (padrao-ouro do projeto) ===")
    df["porte_quartil"] = pd.qcut(df["populacao"], 4, labels=["Q1 (menores)", "Q2", "Q3", "Q4 (maiores)"])
    rhos = []
    for _, g in df.groupby("porte_quartil", observed=True):
        r_q, n_q = spearman(g["leitos_sus_por_mil"], g["pct_icsap"])
        rhos.append(r_q)
        print(f"  {g['porte_quartil'].iloc[0]:16s} n={n_q:5,}  leitos x %ICSAP: rho={r_q:+.3f}  "
              f"| mediana leitos/mil {g.leitos_sus_por_mil.median():.2f}, %ICSAP {g.pct_icsap.median():.1f}%")

    print("\n=== 5. Sem leito local x com leito, DENTRO de cada quartil de porte ===")
    for _, g in df.groupby("porte_quartil", observed=True):
        s, c = g[g.sem_leito], g[~g.sem_leito]
        if len(s) < 10 or len(c) < 10:
            print(f"  {g['porte_quartil'].iloc[0]:16s} amostra insuficiente "
                  f"(sem leito: {len(s)}, com leito: {len(c)})")
            continue
        print(f"  {g['porte_quartil'].iloc[0]:16s} sem leito n={len(s):4,} %ICSAP={s.pct_icsap.median():5.1f}% "
              f"intern/mil={s.internacoes_por_mil.median():5.1f} | "
              f"com leito n={len(c):4,} %ICSAP={c.pct_icsap.median():5.1f}% "
              f"intern/mil={c.internacoes_por_mil.median():5.1f}")

    print("\n=== Leitura ===")
    maior = max(abs(r) for r in rhos if not np.isnan(r))
    print(f"  parte (a) -- leitos x internacoes totais : rho={r_a:+.3f}")
    print(f"  parte (b) -- leitos x %ICSAP (bruto)     : rho={r_b:+.3f}")
    print(f"  parte (b) controlando porte e IVS        : rho={r_p:+.3f}")
    print(f"  maior |rho| dentro de quartil de porte   : {maior:.3f}")
    if abs(r_b) < 0.10 and maior < 0.10:
        print("  => a hipotese do preprint NAO se confirma nestes dados: a oferta local de")
        print("     leitos nao explica a variacao do %ICSAP entre municipios.")
    elif maior >= 0.10:
        print("  => ha associacao que sobrevive ao controle de porte -- a hipotese do")
        print("     preprint tem sustentacao empirica. Detalhar direcao e magnitude acima.")
    else:
        print("  => associacao bruta existe mas nao sobrevive ao controle de porte:")
        print("     era confundimento, nao o mecanismo proposto.")

    out = df[["municipio_cod", "municipio_nome", "uf_sigla", "regiao", "populacao",
              "leitos_total", "leitos_sus", "leitos_sus_por_mil", "sem_leito",
              "internacoes_total", "internacoes_por_mil", "internacoes_icsap",
              "pct_icsap", "icsap_100k", "ivs_score"]].copy()
    out["ano"] = ANO
    out.to_parquet(MARTS / "mart_leitos_icsap_municipio.parquet", compression="zstd", index=False)
    print(f"\n[mart] mart_leitos_icsap_municipio: {len(out):,} municipios")


if __name__ == "__main__":
    main()
