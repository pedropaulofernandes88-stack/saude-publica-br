"""
analise_equidade_aps_longitudinal.py — Painel 2021-2024: efeito fixo municipal
===============================================================================

O teste de equidade pareado por porte (analise_equidade_aps.py, corte 2024)
achou associacao nula entre densidade de ESF e %ICSAP mesmo comparando so
pares do mesmo porte. Limitacao declarada no preprint: um corte transversal
nao capta o efeito de equipes RECEM-IMPLANTADAS — o beneficio de uma equipe
nova pode levar 1-2 anos para aparecer na taxa de internacao evitavel.

Este script testa isso com um desenho longitudinal (2021-2024), usando dois
metodos complementares:

1. Efeito fixo municipal (within-transformation): para cada municipio, subtrai
   a media do proprio municipio nos 4 anos de esf_10k e %ICSAP. Isso remove
   qualquer confundidor municipal que NAO MUDA no tempo (geografia, perfil
   cronico, distancia de centro de referencia, etc.) — e exatamente o tipo de
   controle que a comparacao transversal por quartil de porte nao conseguia
   fazer de forma perfeita.
2. Primeira diferenca ano-a-ano (delta): compara a VARIACAO de esf_10k com a
   VARIACAO de %ICSAP no mesmo municipio, de um ano para o outro — a forma
   mais direta de perguntar "quando um municipio ganha equipe, sua internacao
   evitavel cai?"
3. Versao defasada (lag +1 ano): esf_10k no ano t explica %ICSAP no ano t+1?
   Testa especificamente a hipotese de que o efeito de equipe nova demora a
   aparecer.

Uso:
  .venv311/Scripts/python scripts/analise_equidade_aps_longitudinal.py
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
MARTS = ROOT / "data" / "marts"
ANOS = [2021, 2022, 2023, 2024]


def spearman(x: pd.Series, y: pd.Series) -> tuple[float, int]:
    d = pd.DataFrame({"x": x, "y": y}).dropna()
    if len(d) < 10:
        return float("nan"), len(d)
    return float(d["x"].corr(d["y"], method="spearman")), len(d)


def montar_painel() -> pd.DataFrame:
    cob = pd.read_parquet(MARTS / "mart_cobertura_aps_municipio.parquet")
    icsap = pd.read_parquet(MARTS / "mart_icsap_municipio.parquet")

    cob = cob[cob.ano.isin(ANOS)]
    cob_ano = (cob.groupby(["municipio_cod", "ano"], as_index=False)
               .agg(qt_esf=("qt_esf", "mean"), populacao=("populacao", "mean")))

    icsap = icsap[icsap.ano.isin(ANOS)][
        ["municipio_cod", "municipio_nome", "uf_sigla", "regiao", "ano", "pct_icsap", "icsap_100k"]]

    painel = cob_ano.merge(icsap, on=["municipio_cod", "ano"], how="inner")
    painel["esf_10k"] = painel["qt_esf"] / painel["populacao"] * 10_000
    return painel


def main() -> None:
    painel = montar_painel()

    # Painel balanceado: so municipios com os 4 anos presentes (evita viés de composição)
    contagem = painel.groupby("municipio_cod")["ano"].nunique()
    balanceados = contagem[contagem == len(ANOS)].index
    painel_bal = painel[painel.municipio_cod.isin(balanceados)].copy()
    print("=== Painel 2021-2024 ===")
    print(f"municipios com os 4 anos completos: {len(balanceados):,} de {painel.municipio_cod.nunique():,} "
          f"({len(balanceados)/painel.municipio_cod.nunique()*100:.1f}%)")
    print(f"observacoes municipio-ano no painel balanceado: {len(painel_bal):,}")

    # porte de referencia = populacao media 2021 (evita usar populacao "pos-tratamento")
    porte_2021 = painel_bal[painel_bal.ano == 2021][["municipio_cod", "populacao"]].rename(
        columns={"populacao": "populacao_2021"})
    painel_bal = painel_bal.merge(porte_2021, on="municipio_cod", how="left")
    painel_bal["porte_quartil"] = pd.qcut(painel_bal["populacao_2021"], 4,
                                           labels=["Q1 (menores)", "Q2", "Q3", "Q4 (maiores)"])

    # === 1. Efeito fixo municipal (within-transformation, uma via) ===
    g = painel_bal.groupby("municipio_cod")
    painel_bal["esf_10k_within"] = painel_bal["esf_10k"] - g["esf_10k"].transform("mean")
    painel_bal["pct_icsap_within"] = painel_bal["pct_icsap"] - g["pct_icsap"].transform("mean")

    print("\n=== 1. Efeito fixo municipal (within-transformation, uma via) ===")
    r, n = spearman(painel_bal["esf_10k_within"], painel_bal["pct_icsap_within"])
    print(f"  esf_10k (dentro do municipio) x %ICSAP (dentro do municipio): rho={r:+.3f}  (n={n:,} municipio-ano)")
    print("  (correlaciona o DESVIO de cada municipio em relacao a sua propria media 2021-2024;")
    print("   remove qualquer fator que nao muda no tempo — geografia, perfil cronico, etc.)")

    for _, sub in painel_bal.groupby("porte_quartil", observed=True):
        r_q, n_q = spearman(sub["esf_10k_within"], sub["pct_icsap_within"])
        print(f"    {sub['porte_quartil'].iloc[0]:16s} n={n_q:5,}  rho={r_q:+.3f}")

    # === 1b. Efeito fixo DUPLO (municipio + ano) — remove tendencia nacional comum ===
    # Achado: ha uma tendencia de calendario clara subindo nas duas variaveis ao mesmo
    # tempo (esf_10k medio 3.67->4.05, %ICSAP medio 17.9%->21.2%, 2021-2024 — salto
    # concentrado em 2021->2022, provavel retomada pos-pandemia de internacoes adiadas).
    # Isso por si so ja produz uma correlacao "dentro do municipio" positiva espuria se
    # nao removermos tambem o efeito de ANO. Este e o teste correto.
    ga = painel_bal.groupby("ano")
    painel_bal["esf_10k_fe2"] = painel_bal["esf_10k_within"] - ga["esf_10k_within"].transform("mean")
    painel_bal["pct_icsap_fe2"] = painel_bal["pct_icsap_within"] - ga["pct_icsap_within"].transform("mean")

    print("\n=== 1b. Efeito fixo DUPLO (municipio + ano) — remove tendencia nacional comum ===")
    r2, n2 = spearman(painel_bal["esf_10k_fe2"], painel_bal["pct_icsap_fe2"])
    print(f"  esf_10k (FE duplo) x %ICSAP (FE duplo): rho={r2:+.3f}  (n={n2:,} municipio-ano)")
    for _, sub in painel_bal.groupby("porte_quartil", observed=True):
        r_q, n_q = spearman(sub["esf_10k_fe2"], sub["pct_icsap_fe2"])
        print(f"    {sub['porte_quartil'].iloc[0]:16s} n={n_q:5,}  rho={r_q:+.3f}")

    # === 2. Primeira diferenca ano-a-ano ===
    painel_bal = painel_bal.sort_values(["municipio_cod", "ano"])
    painel_bal["d_esf"] = painel_bal.groupby("municipio_cod")["esf_10k"].diff()
    painel_bal["d_icsap"] = painel_bal.groupby("municipio_cod")["pct_icsap"].diff()
    deltas = painel_bal.dropna(subset=["d_esf", "d_icsap"])

    print("\n=== 2. Primeira diferenca ano-a-ano (delta esf_10k x delta %ICSAP) ===")
    r_d, n_d = spearman(deltas["d_esf"], deltas["d_icsap"])
    print(f"  todas as transicoes (2021->22, 22->23, 23->24): rho={r_d:+.3f}  (n={n_d:,})")
    for ano_t in [2022, 2023, 2024]:
        sub = deltas[deltas.ano == ano_t]
        r_t, n_t = spearman(sub["d_esf"], sub["d_icsap"])
        print(f"    transicao para {ano_t}: rho={r_t:+.3f}  (n={n_t:,})")

    # demeia o delta pelo proprio ano antes de estratificar por porte — senao o pooling das
    # 3 transicoes (cada uma com um deslocamento nacional medio diferente) pode contaminar
    # a correlacao por porte do mesmo jeito que o FE de uma via contaminou o item 1.
    gd = deltas.groupby("ano")
    deltas = deltas.copy()
    deltas["d_esf_dm"] = deltas["d_esf"] - gd["d_esf"].transform("mean")
    deltas["d_icsap_dm"] = deltas["d_icsap"] - gd["d_icsap"].transform("mean")

    print("\n  ...estratificado por porte (Q1=menores, baseado na populacao 2021; delta demeado por ano):")
    for _, sub in deltas.groupby("porte_quartil", observed=True):
        r_q, n_q = spearman(sub["d_esf_dm"], sub["d_icsap_dm"])
        print(f"    {sub['porte_quartil'].iloc[0]:16s} n={n_q:5,}  rho={r_q:+.3f}")

    # === 3. Versao defasada: esf em t explica %ICSAP em t+1? (usa FE duplo, sem tendencia) ===
    lag = painel_bal[["municipio_cod", "ano", "esf_10k_fe2"]].copy()
    lag["ano_alvo"] = lag["ano"] + 1
    alvo = painel_bal[["municipio_cod", "ano", "pct_icsap_fe2"]].rename(columns={"ano": "ano_alvo"})
    defasado = lag.merge(alvo, on=["municipio_cod", "ano_alvo"], how="inner")

    print("\n=== 3. Defasagem: esf_10k (FE duplo) no ano t x %ICSAP (FE duplo) em t+1 ===")
    r_lag, n_lag = spearman(defasado["esf_10k_fe2"], defasado["pct_icsap_fe2"])
    print(f"  rho={r_lag:+.3f}  (n={n_lag:,})")
    print("  (testa especificamente se o efeito de equipe nova demora um ano para aparecer,")
    print("   ja livre da tendencia nacional comum de 2021-2024)")

    # === Leitura ===
    # r  (FE municipal, uma via)   -> confundido por tendencia nacional comum (ver 1b)
    # r2 (FE duplo: municipio+ano) -> estimativa contemporanea correta
    # r_d (diferenca por transicao)-> ja imune a tendencia (correlacao dentro do mesmo ano)
    # r_lag (FE duplo defasado)    -> estimativa defasada correta
    print("\n=== Leitura ===")
    achados_corretos = {"FE duplo (contemporaneo)": r2, "FE duplo (defasado +1 ano)": r_lag}
    for ano_t in [2022, 2023, 2024]:
        sub = deltas[deltas.ano == ano_t]
        r_t, _ = spearman(sub["d_esf"], sub["d_icsap"])
        achados_corretos[f"diferenca {ano_t-1}->{ano_t}"] = r_t
    maior = max(abs(v) for v in achados_corretos.values())
    print(f"  ATENCAO 1 (FE municipal simples, rho={r:+.3f}) era confundida por tendencia nacional comum:")
    print("    esf_10k medio subiu 3.67->4.05 e %ICSAP medio subiu 17.9%->21.2% entre 2021-2024,")
    print("    ambos por razoes nao-relacionadas a atencao primaria (provavel retomada pos-pandemia).")
    print(f"    Ao remover tambem o efeito de ano (FE duplo), rho cai para {r2:+.3f}.")
    print(f"  maior |rho| entre os desenhos corretos (FE duplo, diferencas por ano, defasagem): {maior:.3f}")
    if maior < 0.10:
        print("  => depois de remover a tendencia nacional comum, os desenhos longitudinais CONFIRMAM")
        print("     o achado nulo do corte transversal: nao ha associacao real dentro do municipio,")
        print("     nem contemporanea nem defasada, entre densidade de ESF e %ICSAP.")
    else:
        print("  => ATENCAO: mesmo apos remover a tendencia nacional, algum desenho mostra |rho| > 0.10 —")
        print("     revisar antes de generalizar. Nao publicar sem reanalise.")

    out = painel_bal[["municipio_cod", "municipio_nome", "uf_sigla", "regiao", "ano",
                       "populacao", "porte_quartil", "esf_10k", "pct_icsap", "icsap_100k",
                       "esf_10k_within", "pct_icsap_within", "esf_10k_fe2", "pct_icsap_fe2",
                       "d_esf", "d_icsap"]].copy()
    out["porte_quartil"] = out["porte_quartil"].astype(str)
    out.to_parquet(MARTS / "mart_equidade_aps_longitudinal.parquet", compression="zstd", index=False)
    print(f"\n[mart] mart_equidade_aps_longitudinal: {len(out):,} linhas municipio-ano "
          f"({painel_bal.municipio_cod.nunique():,} municipios)")


if __name__ == "__main__":
    main()
