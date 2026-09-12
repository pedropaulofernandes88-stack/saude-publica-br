"""
analise_agua_mortalidade.py — vigilância da água e morte por infecção intestinal
=================================================================================

    .venv311/Scripts/python scripts/analise_agua_mortalidade.py

A PERGUNTA
----------
Os óbitos por doenças infecciosas intestinais (CID-10 A00–A09) subiram 47% no
Brasil entre 2019 e 2024 — 4.875 para 7.177 —, enquanto a mortalidade total
subiu 13,5%. A alta sobrevive aos quatro testes óbvios: 2024 é ano consolidado,
ela aparece em A04 (+72%), A08 (+120%) e A09 (+41%), é uniforme entre faixas
etárias (+52% em 75+, +56% em 5–14) e persiste onde a codificação NÃO melhorou
(+43,8% nos 948 municípios em que a proporção de causas mal definidas não caiu,
contra +49,2% onde caiu).

Esta análise pergunta se a **vigilância da qualidade da água** — medida pelo
SISAGUA, e não pela infraestrutura declarada no Censo — se associa a essa
mortalidade, e se a associação é ESPECÍFICA do caminho hídrico.

POR QUE ESTA ANÁLISE PRECISA DE CRITÉRIO DECLARADO ANTES
---------------------------------------------------------
Cruzamento ecológico entre indicador de saneamento e mortalidade infecciosa
NUNCA falha. Vai dar associação, e a associação vai ser confundível com pobreza:
município que não vigia a água é município pobre, e município pobre morre mais
de tudo. Uma análise que só reportasse "encontramos associação" não teria como
distinguir mecanismo de proxy socioeconômico, e o achado seria indefensável.

Por isso os critérios abaixo estão escritos ANTES de qualquer resultado ser
olhado, e o script imprime aprovação ou reprovação de cada um.

  CRITÉRIO 1 — ESPECIFICIDADE (é o que refuta o achado)
  ------------------------------------------------------
  Controle negativo: infecções respiratórias baixas (J12–J18). Elas partilham
  quase todo confundidor com A00–A09 — pobreza, desnutrição, acesso a serviço,
  qualidade de codificação, estrutura etária — e NÃO partilham o caminho
  hídrico. É o controle negativo certo justamente por ser tão parecido.

  Mede-se a razão de razões:

      RRR = RR(A00–A09) / RR(J12–J18),  sem vigilância vs. vigilância regular

  **Se o IC95% de RRR incluir 1, a interpretação hídrica está REFUTADA.** A
  associação existiria, mas seria indistinguível de um marcador geral de
  precariedade, e é assim que seria reportada.

  CRITÉRIO 2 — ACESSO À ÁGUA NÃO PODE EXPLICAR
  ----------------------------------------------
  `dim_ivs.pct_sem_agua` é o Censo: quantos domicílios não têm abastecimento.
  Isso é INFRAESTRUTURA. O SISAGUA é VIGILÂNCIA — se a água que existe é
  analisada. São coisas diferentes e são rotineiramente confundidas.

  O RRR é recalculado dentro de quartis de `pct_sem_agua` e reunido pelos pesos
  de Mantel-Haenszel. **Se o RRR ajustado passar a incluir 1, o achado é sobre
  acesso à água e não sobre vigilância** — e aí não é inédito.

  CRITÉRIO 3 — GRADIENTE, NÃO SÓ CONTRASTE
  ------------------------------------------
  A exposição entra em quatro classes ordenadas. Relação de causa costuma deixar
  gradiente; artefato de agrupamento costuma deixar só o extremo diferente.
  Não-monotonicidade não refuta sozinha — é reportada como está.

O QUE ESTE DESENHO NÃO PODE DIZER
----------------------------------
É ECOLÓGICO. Município não é pessoa: nada aqui autoriza dizer que o indivíduo
que morreu bebeu água não vigiada. E "sem vigilância" NÃO é "água contaminada" —
é ausência da prova, exatamente como no resto do mart do SISAGUA.

MÉTODO
------
Contagens por município, 2015–2024, com pessoas-ano pela projeção do IBGE.
Sem modelo paramétrico: razões brutas e estratificadas, com IC95% por
**bootstrap de município** (2.000 reamostragens com reposição). O bootstrap por
unidade absorve superdispersão e dependência dentro do município sem exigir que
eu escolha uma família de distribuição.

Depende de: data/marts/{mart_mortalidade_causa_municipio, mart_sisagua_municipio,
mart_sisagua_cobertura, dim_populacao, dim_ivs}.parquet
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
MARTS = ROOT / "data" / "marts"

ANOS = list(range(2015, 2025))          # consolidados; 2025 e' preliminar
HIDRICA = r"A0[0-9]"                    # infecciosas intestinais
CONTROLE = r"J1[2-8]"                   # infeccoes respiratorias baixas
REPS = 2000
SEMENTE = 20260912

#: Classes de vigilancia, da pior para a melhor. A referencia e' a melhor.
#: `meses_com_analise` e' a mediana do municipio sobre ano x parametro em
#: 2015-2024; o SISAGUA preve controle MENSAL, entao 12 e' o previsto.
SEM = "sem vigilancia"
RARA = "vigilancia rara (<=6 meses)"
PARCIAL = "vigilancia parcial (7-11)"
REGULAR = "vigilancia regular (12)"
CLASSES = [SEM, RARA, PARCIAL, REGULAR]
REFERENCIA = REGULAR


def montar() -> pd.DataFrame:
    mort = pd.read_parquet(MARTS / "mart_mortalidade_causa_municipio.parquet",
                           columns=["municipio_cod", "ano", "causabas_3", "obitos"])
    mort = mort[mort.ano.isin(ANOS)]
    hid = (mort[mort.causabas_3.str.match(HIDRICA)]
           .groupby("municipio_cod").obitos.sum().rename("obitos_hidrica"))
    ctr = (mort[mort.causabas_3.str.match(CONTROLE)]
           .groupby("municipio_cod").obitos.sum().rename("obitos_controle"))

    pop = pd.read_parquet(MARTS / "dim_populacao.parquet")
    pop = (pop[pop.ano.isin(ANOS)].groupby("municipio_cod").populacao.sum()
           .rename("pessoas_ano"))

    cob = pd.read_parquet(MARTS / "mart_sisagua_cobertura.parquet")
    sis = pd.read_parquet(MARTS / "mart_sisagua_municipio.parquet",
                          columns=["municipio_cod", "ano", "meses_com_analise"])
    sis = sis[sis.ano.isin(ANOS)]
    mediana = sis.groupby("municipio_cod").meses_com_analise.median()

    ivs = pd.read_parquet(MARTS / "dim_ivs.parquet")[
        ["municipio_cod", "pct_sem_agua", "taxa_analfabetismo", "regiao"]]

    d = (cob[["municipio_cod", "coletado"]]
         .join(hid, on="municipio_cod").join(ctr, on="municipio_cod")
         .join(pop, on="municipio_cod").join(mediana, on="municipio_cod")
         .merge(ivs, on="municipio_cod", how="left"))
    d[["obitos_hidrica", "obitos_controle"]] = d[
        ["obitos_hidrica", "obitos_controle"]].fillna(0)

    def classificar(m):
        if pd.isna(m):
            return SEM
        if m <= 6:
            return RARA
        if m < 12:
            return PARCIAL
        return REGULAR

    d["classe"] = d.meses_com_analise.map(classificar)
    # Municipio sem pessoas-ano nao entra: ausencia de denominador nao e'
    # exposicao baixa. Municipio nao coletado tambem nao: nao sabemos a
    # vigilancia dele, e chamar isso de "sem vigilancia" seria inventar.
    antes = len(d)
    d = d[d.pessoas_ano.notna() & (d.pessoas_ano > 0) & d.coletado].copy()
    print(f"[base] {antes:,} municipios -> {len(d):,} com denominador e coleta",
          flush=True)
    return d


def _rr(d: pd.DataFrame, col: str) -> float:
    g = d.groupby("classe").agg(ob=(col, "sum"), py=("pessoas_ano", "sum"))
    if SEM not in g.index or REFERENCIA not in g.index:
        return np.nan
    a, b = g.loc[SEM], g.loc[REFERENCIA]
    if a.py <= 0 or b.py <= 0 or b.ob <= 0:
        return np.nan
    return (a.ob / a.py) / (b.ob / b.py)


def rrr_bruto(d: pd.DataFrame) -> float:
    return _rr(d, "obitos_hidrica") / _rr(d, "obitos_controle")


def rrr_ajustado(d: pd.DataFrame) -> float:
    """RRR dentro de quartis de pct_sem_agua, reunido por Mantel-Haenszel.

    Peso de cada estrato: o inverso da soma dos inversos das contagens que
    entram na razao — o peso de MH reduzido, que da' mais peso ao estrato com
    mais informacao e nao explode quando um estrato tem contagem pequena.
    """
    num = den = 0.0
    for _, s in d.groupby("q_agua", observed=True):
        r = rrr_bruto(s)
        if not np.isfinite(r) or r <= 0:
            continue
        g = s.groupby("classe").agg(h=("obitos_hidrica", "sum"),
                                    c=("obitos_controle", "sum"))
        if SEM not in g.index or REFERENCIA not in g.index:
            continue
        contagens = [g.loc[SEM].h, g.loc[SEM].c, g.loc[REFERENCIA].h,
                     g.loc[REFERENCIA].c]
        if min(contagens) <= 0:
            continue
        peso = 1.0 / sum(1.0 / c for c in contagens)
        num += peso * np.log(r)
        den += peso
    return float(np.exp(num / den)) if den > 0 else np.nan


def ic_bootstrap(d: pd.DataFrame, fn, reps: int = REPS) -> tuple[float, float, float]:
    """IC95% por reamostragem de MUNICIPIOS, nao de obitos.

    A unidade de reamostragem tem de ser a unidade de analise: obitos dentro do
    mesmo municipio nao sao independentes, e reamostra-los daria intervalo
    estreito demais por construcao.
    """
    rng = np.random.default_rng(SEMENTE)
    idx = np.arange(len(d))
    vals = []
    for _ in range(reps):
        v = fn(d.iloc[rng.choice(idx, size=len(idx), replace=True)])
        if np.isfinite(v):
            vals.append(v)
    a = np.array(vals)
    return fn(d), float(np.percentile(a, 2.5)), float(np.percentile(a, 97.5))


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    d = montar()
    d["q_agua"] = pd.qcut(d.pct_sem_agua, 4, labels=["Q1", "Q2", "Q3", "Q4"],
                          duplicates="drop")

    print("\n== exposicao ==")
    g = d.groupby("classe").agg(municipios=("municipio_cod", "size"),
                                pessoas_ano=("pessoas_ano", "sum"),
                                hidrica=("obitos_hidrica", "sum"),
                                controle=("obitos_controle", "sum"))
    g = g.reindex([c for c in CLASSES if c in g.index])
    g["tx_hidrica"] = (1e5 * g.hidrica / g.pessoas_ano).round(2)
    g["tx_controle"] = (1e5 * g.controle / g.pessoas_ano).round(1)
    print(g.to_string())

    ref = g.loc[REFERENCIA]
    print("\n== CRITERIO 3: gradiente ==")
    for c in CLASSES:
        if c not in g.index:
            continue
        rh = (g.loc[c].hidrica / g.loc[c].pessoas_ano) / (ref.hidrica / ref.pessoas_ano)
        rc = (g.loc[c].controle / g.loc[c].pessoas_ano) / (ref.controle / ref.pessoas_ano)
        print(f"   {c:<28} RR hidrica {rh:5.2f}   RR controle {rc:5.2f}   "
              f"razao {rh/rc:5.2f}")

    print("\n== CRITERIO 1: especificidade ==", flush=True)
    rh = _rr(d, "obitos_hidrica")
    rc = _rr(d, "obitos_controle")
    print(f"   RR hidrica (sem vigilancia vs regular) .... {rh:.3f}")
    print(f"   RR controle (J12-J18) ..................... {rc:.3f}")
    v, lo, hi = ic_bootstrap(d, rrr_bruto)
    print(f"   RRR = {v:.3f}  IC95% [{lo:.3f}, {hi:.3f}]")
    passou1 = lo > 1.0
    print(f"   -> {'APROVADO' if passou1 else 'REFUTADO'}: "
          f"{'o IC exclui 1' if passou1 else 'o IC inclui 1; associacao nao e especifica do caminho hidrico'}")

    print("\n== CRITERIO 2: sobrevive ao acesso a agua? ==", flush=True)
    print("   quartis de pct_sem_agua (Censo):")
    print(d.groupby("q_agua", observed=True).pct_sem_agua.agg(["min", "max", "size"]).round(2).to_string())
    v2, lo2, hi2 = ic_bootstrap(d, rrr_ajustado)
    print(f"   RRR ajustado = {v2:.3f}  IC95% [{lo2:.3f}, {hi2:.3f}]")
    passou2 = lo2 > 1.0
    print(f"   -> {'APROVADO' if passou2 else 'REFUTADO'}: "
          f"{'sobrevive' if passou2 else 'o achado e sobre acesso a agua, nao sobre vigilancia'}")

    print("\n== VEREDITO ==")
    if passou1 and passou2:
        print("   Associacao ESPECIFICA do caminho hidrico e independente do acesso.")
    else:
        print("   Interpretacao hidrica NAO se sustenta pelos criterios declarados.")


if __name__ == "__main__":
    main()
