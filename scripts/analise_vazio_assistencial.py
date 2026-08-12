"""
analise_vazio_assistencial.py — viver em municipio sem leito aumenta a mortalidade?

Em 2024, 1.971 municipios (35,4%) nao tem NENHUM leito hospitalar
(scripts/pipeline_cnes_leitos.py). A pergunta obvia e se isso se traduz em
mais mortes. A resposta exige cuidado, porque duas coisas muito diferentes
podem parecer a mesma no dado agregado.

AS DUAS HIPOTESES, QUE PRECISAM SER SEPARADAS:
  (a) SOBREVIDA: sem leito perto, o paciente grave morre que sobreviveria.
      Assinatura esperada: taxa PADRONIZADA de mortalidade maior.
  (b) LOCAL DA MORTE: sem leito perto, a pessoa morre em casa em vez do
      hospital -- mesma morte, outro lugar. Assinatura: mais obitos
      domiciliares, mesma taxa total.
As duas tem implicacao de politica publica oposta. (a) pede leito; (b) pede
cuidado paliativo domiciliar e discussao sobre onde se quer morrer.

ARMADILHAS TRATADAS:
  1. IDADE. Municipio pequeno e envelhecido morre mais por composicao etaria,
     nao por falta de leito. Usamos a taxa PADRONIZADA por idade (metodo
     direto, padrao Brasil/Censo 2022), ja disponivel no mart.
  2. PORTE. Sem leito e quase sinonimo de municipio pequeno. Comparamos dentro
     de quartis de porte -- o padrao-ouro do projeto.
  3. SEMANTICA. Mortalidade e por municipio de RESIDENCIA; leitos, por
     municipio do ESTABELECIMENTO. Isso aqui e uma VANTAGEM, nao um problema:
     a pergunta e exatamente "morar num municipio sem leito faz diferenca?",
     e o obito do residente conta para a residencia dele onde quer que ocorra.
  4. SUB-REGISTRO. Municipio pequeno e remoto pode registrar menos obitos.
     Isso empurraria a taxa para BAIXO nos sem leito -- ou seja, viesa contra
     encontrar (a). Declarado, nao corrigido: nao ha como corrigir com dado
     aberto.

Ano de referencia: 2023 (consolidado). 2024 e preliminar no SIM e serve so
como checagem de robustez.

Uso:
  .venv311/Scripts/python scripts/analise_vazio_assistencial.py
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
ANO = 2023


def spearman(x: pd.Series, y: pd.Series) -> tuple[float, int]:
    d = pd.DataFrame({"x": x, "y": y}).dropna()
    if len(d) < 10:
        return float("nan"), len(d)
    return float(d["x"].corr(d["y"], method="spearman")), len(d)


def carregar(ano: int) -> pd.DataFrame:
    m = pd.read_parquet(MARTS / "mart_mortalidade_municipio.parquet")
    m = m[(m.ano == ano) & (m.capitulo_cid == "TOTAL") & (m.sexo == "TOTAL")][
        ["municipio_cod", "municipio_nome", "uf_sigla", "regiao", "obitos",
         "obitos_hospital", "obitos_domicilio", "populacao",
         "taxa_obitos_100k", "taxa_padronizada_100k"]]
    lt = pd.read_parquet(MARTS / "mart_leitos_municipio.parquet")
    lt = lt[lt.ano == ano][["municipio_cod", "leitos_total", "leitos_sus",
                             "leitos_uti", "leitos_sus_por_mil"]]
    ivs = pd.read_parquet(MARTS / "dim_ivs.parquet")[["municipio_cod", "ivs_score"]]

    df = m.merge(lt, on="municipio_cod", how="inner").merge(ivs, on="municipio_cod", how="left")
    df["sem_leito"] = df.leitos_total == 0
    df["pct_obito_domicilio"] = df.obitos_domicilio / df.obitos.replace(0, np.nan) * 100
    df["pct_obito_hospital"] = df.obitos_hospital / df.obitos.replace(0, np.nan) * 100
    df["porte_quartil"] = pd.qcut(df["populacao"], 4,
                                   labels=["Q1 (menores)", "Q2", "Q3", "Q4 (maiores)"])
    return df


def main() -> None:
    df = carregar(ANO)
    print(f"=== Amostra: {len(df):,} municipios, {ANO} (SIM consolidado) ===")
    print(f"sem nenhum leito local: {df.sem_leito.sum():,} ({df.sem_leito.mean()*100:.1f}%)")

    print("\n=== 1. HIPOTESE (a) — SOBREVIDA: a taxa padronizada e maior sem leito? ===")
    r, n = spearman(df["leitos_sus_por_mil"], df["taxa_padronizada_100k"])
    print(f"  leitos SUS/mil x taxa padronizada: rho = {r:+.3f}  (n={n:,})")
    com = df[~df.sem_leito].taxa_padronizada_100k.median()
    sem = df[df.sem_leito].taxa_padronizada_100k.median()
    print(f"  taxa padronizada mediana -- COM leito: {com:.1f} | SEM leito: {sem:.1f} "
          f"({(sem/com-1)*100:+.1f}%)")

    print("\n  ...dentro de cada quartil de porte (o teste que vale):")
    difs = []
    for _, g in df.groupby("porte_quartil", observed=True):
        s, c = g[g.sem_leito], g[~g.sem_leito]
        if len(s) < 20 or len(c) < 20:
            print(f"    {g['porte_quartil'].iloc[0]:16s} amostra insuficiente "
                  f"(sem {len(s)}, com {len(c)})")
            continue
        ds, dc = s.taxa_padronizada_100k.median(), c.taxa_padronizada_100k.median()
        difs.append(ds - dc)
        print(f"    {g['porte_quartil'].iloc[0]:16s} sem leito n={len(s):4,} taxa={ds:6.1f} | "
              f"com leito n={len(c):4,} taxa={dc:6.1f} | dif={ds-dc:+6.1f} ({(ds/dc-1)*100:+5.1f}%)")

    print("\n=== 2. HIPOTESE (b) — LOCAL DA MORTE: morre-se mais em casa sem leito? ===")
    com_d = df[~df.sem_leito].pct_obito_domicilio.median()
    sem_d = df[df.sem_leito].pct_obito_domicilio.median()
    print(f"  % obitos em DOMICILIO -- COM leito: {com_d:.1f}% | SEM leito: {sem_d:.1f}% "
          f"({sem_d-com_d:+.1f} p.p.)")
    com_h = df[~df.sem_leito].pct_obito_hospital.median()
    sem_h = df[df.sem_leito].pct_obito_hospital.median()
    print(f"  % obitos em HOSPITAL  -- COM leito: {com_h:.1f}% | SEM leito: {sem_h:.1f}% "
          f"({sem_h-com_h:+.1f} p.p.)")

    print("\n  ...dentro de cada quartil de porte:")
    difs_dom = []
    for _, g in df.groupby("porte_quartil", observed=True):
        s, c = g[g.sem_leito], g[~g.sem_leito]
        if len(s) < 20 or len(c) < 20:
            continue
        ds, dc = s.pct_obito_domicilio.median(), c.pct_obito_domicilio.median()
        difs_dom.append(ds - dc)
        print(f"    {g['porte_quartil'].iloc[0]:16s} domicilio sem leito={ds:5.1f}% | "
              f"com leito={dc:5.1f}% | dif={ds-dc:+5.1f} p.p.")

    print("\n=== 3. Checagem de sub-registro (viesa CONTRA achar efeito de sobrevida) ===")
    print("  se municipios sem leito registram menos obitos, a taxa deles cai")
    print("  artificialmente e um efeito real de sobrevida ficaria escondido.")
    for _, g in df.groupby("porte_quartil", observed=True):
        s, c = g[g.sem_leito], g[~g.sem_leito]
        if len(s) < 20 or len(c) < 20:
            continue
        print(f"    {g['porte_quartil'].iloc[0]:16s} obitos/1000 hab -- sem leito "
              f"{(s.obitos/s.populacao*1000).median():5.2f} | com leito "
              f"{(c.obitos/c.populacao*1000).median():5.2f}")

    print("\n=== Leitura ===")
    max_dif = max(abs(d) for d in difs) if difs else float("nan")
    max_dom = max(difs_dom) if difs_dom else float("nan")
    print(f"  maior diferenca de taxa padronizada entre grupos, dentro do porte: {max_dif:.1f}/100 mil")
    print(f"  maior diferenca de % obito domiciliar, dentro do porte: {max_dom:+.1f} p.p.")
    if abs(max_dif) < 30 and max_dom > 3:
        print("  => padrao compativel com (b) e NAO com (a): a mortalidade padronizada e")
        print("     semelhante, mas o LOCAL da morte muda. Sem leito perto, morre-se em casa.")
        print("     Implicacao de politica: e questao de cuidado no fim da vida e acesso,")
        print("     nao evidencia de que faltar leito local esteja matando mais.")
    elif abs(max_dif) >= 30:
        print("  => ha diferenca relevante de mortalidade padronizada — investigar (a) a fundo")
        print("     antes de concluir; checar sub-registro e composicao de causas.")
    else:
        print("  => nem (a) nem (b) aparecem com clareza nestes dados.")

    out = df[["municipio_cod", "municipio_nome", "uf_sigla", "regiao", "populacao",
              "porte_quartil", "leitos_total", "leitos_sus", "leitos_sus_por_mil", "sem_leito",
              "obitos", "obitos_hospital", "obitos_domicilio", "pct_obito_domicilio",
              "pct_obito_hospital", "taxa_obitos_100k", "taxa_padronizada_100k",
              "ivs_score"]].copy()
    out["ano"] = ANO
    out["porte_quartil"] = out["porte_quartil"].astype(str)
    out.to_parquet(MARTS / "mart_vazio_assistencial_municipio.parquet", compression="zstd", index=False)
    print(f"\n[mart] mart_vazio_assistencial_municipio: {len(out):,} municipios")

    # robustez: mesmo padrao em 2024 (preliminar)?
    print("\n=== Robustez: 2024 (SIM preliminar) reproduz o padrao? ===")
    d24 = carregar(2024)
    for rot, sub in [("COM leito", d24[~d24.sem_leito]), ("SEM leito", d24[d24.sem_leito])]:
        print(f"  {rot}: taxa padronizada mediana={sub.taxa_padronizada_100k.median():6.1f}  "
              f"% obito domiciliar={sub.pct_obito_domicilio.median():5.1f}%")


if __name__ == "__main__":
    main()
