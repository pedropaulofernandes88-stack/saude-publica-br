"""
analise_saude_suplementar_icsap.py — a saude suplementar explica o residuo do ICSAP?
======================================================================================

O preprint da cobertura da APS e a metodologia (SS15) ja declaravam esta limitacao
sem testa-la: "municipios com maior cobertura de saude suplementar podem ter ICSAP
subestimado, por razoes nao relacionadas a atencao primaria" — porque o ICSAP so
enxerga internacoes do SUS, e uma fatia da populacao coberta por plano de saude
pode internar pela rede privada e nunca aparecer no SIH/SUS.

Este script traz o dado que faltava (scripts/pipeline_ans_beneficiarios.py, ANS
Dados Abertos) e testa a hipotese de verdade, em vez de so declara-la:

1. Correlacao bruta entre vinculos a plano e ICSAP (bruto e %ICSAP).
2. O confundidor obvio: municipios maiores tem mais saude suplementar E menos
   ICSAP/100k (efeito de porte, ja documentado noutras analises do projeto) —
   testamos se a associacao sobrevive ao controle por populacao e IVS.
3. Estratificado por porte.
4. Sensibilidade a implausibilidade do indicador da ANS (secao 6 do output).

NOTA DE UNIDADE: a exposicao e `vinculos_plano_por_100_hab`, nao "% da populacao
com plano". O SIB/ANS conta VINCULOS e localiza pelo endereco do CONTRATO, entao
a razao pode passar de 100 e nao e uma proporcao de pessoas (cap. ANS de
https://rfsaldanha.github.io/sis/ans.html). Para este teste isso importa pouco —
Spearman usa apenas a ordem, e a distorcao teria de reordenar municipios, nao so
inflar valores — mas a secao 6 verifica isso em vez de assumir.

Uso:
  .venv311/Scripts/python scripts/analise_saude_suplementar_icsap.py
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

    ry, rx = resid(r["y"].to_numpy()), resid(r["x"].to_numpy())
    return float(np.corrcoef(ry, rx)[0, 1]), len(d)


def main() -> None:
    ss = pd.read_parquet(MARTS / "mart_saude_suplementar_municipio.parquet")
    ss = ss[ss.ano == ANO][["municipio_cod", "populacao", "vinculos_plano_por_100_hab",
                             "razao_implausivel"]]
    icsap = pd.read_parquet(MARTS / "mart_icsap_municipio.parquet")
    icsap = icsap[icsap.ano == ANO][["municipio_cod", "municipio_nome", "uf_sigla",
                                       "internacoes_total", "internacoes_icsap",
                                       "pct_icsap", "icsap_100k", "populacao"]]
    ivs = pd.read_parquet(MARTS / "dim_ivs.parquet")[["municipio_cod", "ivs_score"]]

    df = icsap.merge(ss[["municipio_cod", "vinculos_plano_por_100_hab", "razao_implausivel"]],
                      on="municipio_cod", how="left") \
              .merge(ivs, on="municipio_cod", how="left")

    print(f"=== Amostra: {len(df):,} municipios, {ANO} ===")
    print(f"vinculos a plano por 100 hab.: mediana {df.vinculos_plano_por_100_hab.median():.1f}, "
          f"media {df.vinculos_plano_por_100_hab.mean():.1f}, "
          f"sem nenhum vinculo: {(df.vinculos_plano_por_100_hab == 0).mean()*100:.1f}% dos municipios, "
          f"razao > 100 (implausivel como cobertura): {int(df.razao_implausivel.fillna(False).sum())}")

    print("\n=== 1. Associacao BRUTA (Spearman) ===")
    r1, n1 = spearman(df["vinculos_plano_por_100_hab"], df["icsap_100k"])
    r2, n2 = spearman(df["vinculos_plano_por_100_hab"], df["pct_icsap"])
    print(f"  vinc/100hab x ICSAP/100k : rho = {r1:+.3f}  (n={n1:,})")
    print(f"  vinc/100hab x %ICSAP     : rho = {r2:+.3f}  (n={n2:,})")

    print("\n=== 2. O confundidor obvio: TAMANHO do municipio ===")
    r_pop_ss, _ = spearman(df["populacao"], df["vinculos_plano_por_100_hab"])
    r_pop_ics, _ = spearman(df["populacao"], df["icsap_100k"])
    print(f"  populacao x vinc/100hab : rho = {r_pop_ss:+.3f}")
    print(f"  populacao x ICSAP/100k  : rho = {r_pop_ics:+.3f}")

    print("\n=== 3. Associacao PARCIAL (controlando populacao e IVS) ===")
    ctrl = df[["populacao"]].assign(ivs_score=df["ivs_score"])
    r3, n3 = partial_spearman(df["icsap_100k"], df["vinculos_plano_por_100_hab"], ctrl)
    r4, n4 = partial_spearman(df["pct_icsap"], df["vinculos_plano_por_100_hab"], ctrl)
    print(f"  vinc/100hab x ICSAP/100k | pop, IVS : rho_parcial = {r3:+.3f}  (n={n3:,})")
    print(f"  vinc/100hab x %ICSAP     | pop, IVS : rho_parcial = {r4:+.3f}  (n={n4:,})")

    print("\n=== 4. Estratificado por porte populacional ===")
    faixas = [(0, 10_000), (10_000, 50_000), (50_000, 200_000), (200_000, 10**9)]
    rotulos = ["< 10 mil", "10-50 mil", "50-200 mil", "> 200 mil"]
    for (lo, hi), rot in zip(faixas, rotulos):
        sub = df[(df.populacao >= lo) & (df.populacao < hi)]
        r_s, n_s = spearman(sub["vinculos_plano_por_100_hab"], sub["icsap_100k"])
        print(f"  {rot:12s} n={n_s:5,}  rho={r_s:+.3f}  "
              f"mediana vinc/100hab={sub.vinculos_plano_por_100_hab.median():5.1f}%  "
              f"mediana ICSAP/100k={sub.icsap_100k.median():7.1f}")

    # === 5. Teste dentro do quartil de porte (percentil), mesmo desenho de analise_equidade_aps.py ===
    # A correlacao parcial (item 3) controla porte via regressao linear sobre postos — mas se a
    # relacao porte->desfecho nao for linear/monotonica, sobra residuo de porte mal controlado.
    # Aqui comparamos cada municipio so aos pares do MESMO quartil de porte (grupos de tamanho
    # igual, ~1.392 cada), a forma mais rigorosa ja estabelecida no projeto.
    df["porte_quartil"] = pd.qcut(df["populacao"], 4, labels=["Q1 (menores)", "Q2", "Q3", "Q4 (maiores)"])
    df["pct_ss_no_porte"] = df.groupby("porte_quartil", observed=True)["vinculos_plano_por_100_hab"].rank(pct=True)
    df["pct_icsap_no_porte"] = df.groupby("porte_quartil", observed=True)["pct_icsap"].rank(pct=True)

    print("\n=== 5. Dentro do quartil de porte (percentil, n igual por grupo — como em analise_equidade_aps.py) ===")
    for _, g in df.groupby("porte_quartil", observed=True):
        r_q, n_q = spearman(g["vinculos_plano_por_100_hab"], g["pct_icsap"])
        print(f"  {g['porte_quartil'].iloc[0]:16s} n={n_q:4,}  "
              f"vinc/100hab x %ICSAP dentro do porte: rho={r_q:+.3f}")

    # co-ocorrencia: alto vinc/100hab (terco superior, dentro do porte) com baixo %ICSAP (terco inferior,
    # dentro do porte) — testa diretamente a hipotese "convenio mascara ICSAP do SUS"
    alto_ss = df["pct_ss_no_porte"] >= 2 / 3
    baixo_icsap = df["pct_icsap_no_porte"] <= 1 / 3
    obs = (alto_ss & baixo_icsap).mean()
    esp = alto_ss.mean() * baixo_icsap.mean()
    print(f"\n  co-ocorrencia (alto vinc/100hab + baixo %ICSAP, dentro do porte): observado={obs*100:.2f}%  "
          f"esperado sob independencia={esp*100:.2f}%  razao={obs/esp:.2f}x")

    # === 6. Sensibilidade a implausibilidade do indicador da ANS ===
    # O SIB conta vinculos e localiza pelo endereco do contrato, entao a exposicao pode estar
    # inflada em municipios pequenos que sediam empresas com plano coletivo. Se essa distorcao
    # bastasse para produzir o gradiente do item 5, o gradiente deveria sumir ao excluir os
    # municipios suspeitos. Dois cortes, do mais estrito ao mais amplo.
    print("\n=== 6. Sensibilidade a implausibilidade da exposicao (ANS) ===")
    suspeito_pequeno = (df["populacao"] < 20_000) & (df["vinculos_plano_por_100_hab"] > 40)
    cortes = [
        ("completo (sem exclusao)", pd.Series(True, index=df.index)),
        ("sem razao > 100", ~df["razao_implausivel"].fillna(False)),
        ("sem razao > 100 e sem <20k hab. com >40/100",
         ~df["razao_implausivel"].fillna(False) & ~suspeito_pequeno),
    ]
    for rot, mask in cortes:
        sub = df[mask]
        rhos = [spearman(g["vinculos_plano_por_100_hab"], g["pct_icsap"])[0]
                for _, g in sub.groupby("porte_quartil", observed=True)]
        excl = len(df) - len(sub)
        print(f"  {rot:48s} n={len(sub):5,} (-{excl:3d})  "
              f"rho por quartil de porte: {['%+.3f' % r for r in rhos]}")
    print(f"  ({int(suspeito_pequeno.sum())} municipios com <20 mil hab. e >40 vinculos/100 hab. —")
    print("   candidatos a artefato de endereco de contrato, nao necessariamente erro)")

    print("\n=== Leitura ===")
    rhos_quartil = [spearman(g["vinculos_plano_por_100_hab"], g["pct_icsap"])[0]
                     for _, g in df.groupby("porte_quartil", observed=True)]
    maior_quartil = max(abs(r) for r in rhos_quartil)
    sinais = set(np.sign(r) for r in rhos_quartil if not np.isnan(r) and abs(r) > 0.02)
    inconsistente = len(sinais) > 1

    if maior_quartil < 0.10 and abs(obs / esp - 1) < 0.15:
        print("  => a saude suplementar NAO explica a variacao do ICSAP entre municipios, mesmo")
        print("     comparando so pares do mesmo porte. A limitacao declarada no preprint e")
        print("     teoricamente valida mas nao tem sustentacao empirica robusta nestes dados.")
    elif inconsistente:
        print(f"  => ATENCAO: a correlacao parcial pooled (rho={r4:+.3f}) sugeria efeito fraco, mas")
        print(f"     dentro de cada quartil de porte o sinal MUDA de direcao ({[f'{r:+.2f}' for r in rhos_quartil]}) —")
        print("     inconsistente. Isso indica residuo de porte mal controlado pela regressao linear")
        print("     sobre postos (item 3), nao um efeito real e estavel de saude suplementar. A")
        print("     co-ocorrencia (razao {:.2f}x) tambem nao aponta um padrao decisivo. Conclusao:".format(obs/esp))
        print("     limitacao teoricamente valida, mas o teste NAO a confirma como robusta — tratar")
        print("     como efeito fraco/ambiguo, insuficiente para revisar o achado nulo APS x ICSAP.")
    else:
        print("  => ha associacao residual consistente entre saude suplementar e ICSAP mesmo dentro")
        print("     do mesmo porte — a limitacao declarada tem sustentacao empirica real.")

    out = df[["municipio_cod", "municipio_nome", "uf_sigla", "populacao",
              "vinculos_plano_por_100_hab", "razao_implausivel", "internacoes_total", "internacoes_icsap",
              "pct_icsap", "icsap_100k", "ivs_score"]].copy()
    out["ano"] = ANO
    out.to_parquet(MARTS / "mart_saude_suplementar_icsap_municipio.parquet", compression="zstd", index=False)
    print(f"\n[mart] mart_saude_suplementar_icsap_municipio: {len(out):,} municipios")


if __name__ == "__main__":
    main()
