"""
analise_equidade_aps.py — Equidade de acesso: pares de mesmo porte, nao ranking bruto
=====================================================================================

O Caso 3 do artigo "O que os indicadores nao comparam" mostrou que a cobertura
potencial da APS (%) e majoritariamente proxy de porte municipal: nao da para
comparar Sao Paulo com um municipio de 3 mil habitantes usando esse percentual.

Isso NAO significa que a pergunta de equidade seja invalida — significa que
ela precisa ser feita comparando cada municipio aos seus PARES DE MESMO PORTE,
nao ao Brasil inteiro. Esta analise faz isso:

1. Substitui a "cobertura potencial" (%) por uma medida que nao satura:
   equipes de Saude da Familia por 10 mil habitantes (densidade real de
   equipes, sem o teto artificial de capacidade padronizada).
2. Estratifica os municipios em quartis de porte populacional (Q1=menores).
3. Dentro de cada quartil de porte, calcula o percentil de cada municipio em
   densidade de ESF e em ICSAP/100k — comparando-o apenas aos seus pares.
4. Cruza com o quartil de vulnerabilidade social (IVS-proxy, Censo 2022).
5. Marca como "atencao" os municipios que, dentro do proprio quartil de
   porte, estao no terco inferior de densidade de ESF E no terco superior de
   ICSAP — ou seja, tem menos equipe que municipios comparaveis E mais
   internacao evitavel que municipios comparaveis.

Isso responde a pergunta de politica publica de forma valida (a mesma que a
cobertura bruta tentava responder e nao conseguia): existe uma populacao de
municipios que, mesmo comparados a pares do mesmo tamanho, tem menos atencao
primaria e mais consequencia disso — e essa populacao e desproporcionalmente
vulneravel?

Uso:
  .venv311/Scripts/python scripts/analise_equidade_aps.py
"""
from __future__ import annotations

import sys
from pathlib import Path

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
    d = pd.DataFrame({"x": x, "y": y}).dropna()
    if len(d) < 10:
        return float("nan"), len(d)
    return float(d["x"].corr(d["y"], method="spearman")), len(d)


def main() -> None:
    cruz = pd.read_parquet(MARTS / "mart_cobertura_icsap_municipio.parquet")
    df = cruz[cruz.ano == ANO].copy()

    # 1) medida que nao satura: densidade de equipes, nao percentual de capacidade
    df["esf_por_10k"] = (df["qt_esf"] / df["populacao"] * 10_000).round(3)

    # 2) quartis de PORTE (Q1 = menores municipios)
    df["porte_quartil"] = pd.qcut(df["populacao"], 4, labels=["Q1 (menores)", "Q2", "Q3", "Q4 (maiores)"])

    # 3) percentil DENTRO do proprio quartil de porte (compara pares, nao o Brasil).
    # Usamos %ICSAP (proporcao do total de internacoes do proprio municipio), NAO
    # ICSAP/100k habitantes: testamos e o ICSAP/100k cai com a vulnerabilidade so
    # porque o TOTAL de internacoes tambem cai (barreira geral de acesso hospitalar
    # em municipios vulneraveis/remotos) — nao porque a atencao primaria seja melhor.
    # %ICSAP normaliza pelo proprio volume de internacoes do municipio e remove esse
    # confundimento: e praticamente constante entre quartis de vulnerabilidade
    # (~19-20%), enquanto ICSAP/100k cai de 1.490 (Q1) a 1.222 (Q4).
    df["pct_esf_no_porte"] = df.groupby("porte_quartil", observed=True)["esf_por_10k"].rank(pct=True)
    df["pct_icsap_no_porte"] = df.groupby("porte_quartil", observed=True)["pct_icsap"].rank(pct=True)

    # 4) quartil de vulnerabilidade (Q4 = mais vulneravel, convencao do projeto)
    df["ivs_quartil"] = pd.qcut(df["ivs_score"].rank(method="first"), 4,
                                 labels=["Q1 (menos vulnerável)", "Q2", "Q3", "Q4 (mais vulnerável)"])

    # 5) flag de atencao: pior terco em equipe E pior terco (= maior) em ICSAP, DENTRO do porte
    df["atencao"] = (df["pct_esf_no_porte"] <= 1 / 3) & (df["pct_icsap_no_porte"] >= 2 / 3)

    print(f"=== Amostra: {len(df):,} municipios, {ANO} ===")
    print(f"municipios em 'atencao' (pior terco ESF + pior terco ICSAP, no proprio porte): "
          f"{df.atencao.sum():,} ({df.atencao.mean()*100:.1f}%)")

    print("\n=== Densidade de ESF x %ICSAP, dentro de cada quartil de porte ===")
    for _, g in df.groupby("porte_quartil", observed=True):
        r, n = spearman(g["esf_por_10k"], g["pct_icsap"])
        print(f"  {g['porte_quartil'].iloc[0]:16s} n={n:4,}  "
              f"esf_10k x %ICSAP dentro do porte: rho={r:+.3f}")

    print("\n=== Checagem de confundimento: %ICSAP normaliza o acesso hospitalar geral? ===")
    for _, g in df.groupby("ivs_quartil", observed=True):
        print(f"  {g['ivs_quartil'].iloc[0]:24s} n={len(g):4,}  "
              f"ICSAP/100k mediana={g.icsap_100k.median():7.1f}  %ICSAP mediana={g.pct_icsap.median():5.1f}%")
    print("  (ICSAP/100k cai com a vulnerabilidade porque o acesso hospitalar GERAL cai;")
    print("   %ICSAP, que normaliza pelo proprio volume de internacoes, fica praticamente")
    print("   constante — por isso e a metrica usada na flag de 'atencao' abaixo, nao ICSAP/100k.)")

    print("\n=== A pergunta de equidade: 'atencao' e desproporcionalmente vulneravel? ===")
    tab = pd.crosstab(df["ivs_quartil"], df["atencao"], normalize="index") * 100
    print(tab.round(1).to_string())
    taxa_geral = df.atencao.mean() * 100
    taxa_q4 = df[df.ivs_quartil == "Q4 (mais vulnerável)"].atencao.mean() * 100
    taxa_q1 = df[df.ivs_quartil == "Q1 (menos vulnerável)"].atencao.mean() * 100
    print(f"\n  taxa geral de 'atencao'          : {taxa_geral:.1f}%")
    print(f"  taxa no quartil MAIS vulneravel  : {taxa_q4:.1f}%")
    print(f"  taxa no quartil MENOS vulneravel : {taxa_q1:.1f}%")
    print(f"  razao Q4/Q1                      : {taxa_q4/taxa_q1:.2f}x" if taxa_q1 > 0 else "")

    r_ivs_atencao, n = spearman(df["ivs_score"], df["pct_icsap_no_porte"] - df["pct_esf_no_porte"])
    print(f"\n  correlacao IVS x (desvantagem dentro do porte): rho={r_ivs_atencao:+.3f} (n={n:,})")

    out = df[["municipio_cod", "municipio_nome", "uf_sigla", "regiao", "populacao",
              "porte_quartil", "esf_por_10k", "pct_esf_no_porte", "pct_icsap", "icsap_100k",
              "pct_icsap_no_porte", "ivs_score", "ivs_quartil", "atencao"]].copy()
    out["ano"] = ANO
    out["porte_quartil"] = out["porte_quartil"].astype(str)
    out["ivs_quartil"] = out["ivs_quartil"].astype(str)
    out["pct_esf_no_porte"] = (out["pct_esf_no_porte"] * 100).round(1)
    out["pct_icsap_no_porte"] = (out["pct_icsap_no_porte"] * 100).round(1)
    escrever_parquet(
        out, MARTS / "mart_equidade_aps_municipio.parquet",
        origem="pipeline", produtor="scripts/analise_equidade_aps.py")
    print(f"\n[mart] mart_equidade_aps_municipio: {len(out):,} municipios")


if __name__ == "__main__":
    main()
