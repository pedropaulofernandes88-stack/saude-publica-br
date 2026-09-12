"""
analise_agua_mortalidade.py — o subgrupo 1.2 da Lista, e o que a água explica
==============================================================================

    .venv311/Scripts/python scripts/analise_agua_mortalidade.py

Grava `data/analises/agua/tab*.csv`. Nenhuma conta mora no artigo.

O ACHADO QUE MOTIVA A ANÁLISE
------------------------------
Os óbitos por **doenças infecciosas intestinais** (CID-10 A00–A09) subiram 47%
no Brasil entre 2019 e 2024 — 4.875 para 7.177 —, enquanto a mortalidade total
subiu 13,5%. A alta sobrevive aos quatro testes óbvios: 2024 é ano CONSOLIDADO,
ela aparece em A04, A08 e A09, é uniforme entre faixas etárias, e persiste onde
a codificação NÃO melhorou.

A00–A09 não é causa qualquer: a **Lista Brasileira de Causas de Mortes
Evitáveis** — instrumento oficial do Ministério da Saúde — a classifica como
evitável, no subgrupo 1.2. A nota técnica está em
`data/refs/Obitos_Evitaveis_5_a_74_anos.pdf`, transcrita abaixo no que importa.

O CONTROLE NEGATIVO SAI DO PRÓPRIO INSTRUMENTO
-----------------------------------------------
Esta é a razão de o desenho ser forte, e não foi escolha estética. O subgrupo
1.2 da Lista contém, lado a lado:

    Doenças infecciosas intestinais ................. A00-A09
    Infecções respiratórias, inclusive pneumonia
    e influenza ........... J00-J01, J02.8-J02.9, J03.8-J03.9,
                            J04-J05, J06, J10-J22

O Ministério da Saúde declara as duas evitáveis **pelo mesmo tipo de ação**.
Elas partilham pobreza, desnutrição, acesso a serviço, qualidade de codificação
e estrutura etária. Não partilham o **caminho hídrico**.

Então o contraste não é entre duas causas que eu escolhi parecer: é entre duas
entradas que o instrumento oficial trata como equivalentes. Se a ausência de
vigilância da água separar as duas, separou dentro da própria categoria do
Ministério.

E há um achado no instrumento, de graça: **não existe subgrupo de saneamento na
Lista**. Ela chama a morte por diarreia de evitável sem nunca nomear a água.

OS CRITÉRIOS, DECLARADOS ANTES DE QUALQUER RESULTADO
-----------------------------------------------------
Cruzamento ecológico entre saneamento e mortalidade infecciosa NUNCA falha. Vai
dar associação, e ela vai ser confundível com pobreza. Por isso:

  CRITÉRIO 1 — ESPECIFICIDADE (o que refuta)
    RRR = RR(A00–A09) / RR(controle), sem vigilância vs. vigilância regular.
    **IC95% incluindo 1 REFUTA a interpretação hídrica.** A associação existiria,
    mas seria indistinguível de marcador geral de precariedade.

  CRITÉRIO 2 — ACESSO À ÁGUA NÃO PODE EXPLICAR
    `dim_ivs.pct_sem_agua` é o Censo: INFRAESTRUTURA. O SISAGUA é VIGILÂNCIA.
    O RRR recalculado dentro de quartis de acesso, reunido por Mantel-Haenszel.
    **Se passar a incluir 1, o achado é sobre acesso e não sobre vigilância.**

  CRITÉRIO 3 — GRADIENTE
    Quatro classes ordenadas. Não-monotonicidade não refuta sozinha; é relatada.

  CRITÉRIO 4 — IDADE (acrescentado em 2026-09-12, e ele NÃO foi pré-declarado)
    Pneumonia mata sobretudo idoso; diarreia tem distribuição mais plana, e
    município sem vigilância tem população mais jovem. O RRR é recalculado
    DENTRO de cada faixa etária. Este teste nasceu depois de eu ver o controle
    deprimido — é post-hoc, vale menos que os três acima, e vai rotulado assim
    no artigo. Ele reduziu o efeito e não o derrubou.

O QUE ESTE DESENHO NÃO PODE DIZER
----------------------------------
É ECOLÓGICO. Município não é pessoa: nada aqui autoriza dizer que quem morreu
bebeu água não vigiada. E "sem vigilância" NÃO é "água contaminada" — é ausência
da prova, exatamente como no resto do mart do SISAGUA.

MÉTODO
------
Contagens por município, 2015–2024, pessoas-ano pela projeção do IBGE. Sem
modelo paramétrico: razões brutas e estratificadas com IC95% por **bootstrap de
município**. A unidade de reamostragem é a de análise — reamostrar óbitos daria
intervalo estreito por construção.

Depende de: data/marts/{mart_mortalidade_causa_municipio,
mart_mortalidade_causa_municipio_faixa, mart_sisagua_municipio,
mart_sisagua_cobertura, dim_populacao, dim_ivs}.parquet
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
MARTS = ROOT / "data" / "marts"
SAIDA = ROOT / "data" / "analises" / "agua"

ANOS = list(range(2015, 2025))   # consolidados; 2025 e' preliminar
REPS = 2000
SEMENTE = 20260912

#: Doencas infecciosas intestinais, subgrupo 1.2 da Lista Brasileira.
HIDRICA = r"^A0[0-9]$"

#: Infeccoes respiratorias do MESMO subgrupo 1.2. A nota tecnica lista
#: J00-J01, J02.8-J02.9, J03.8-J03.9, J04-J05, J06, J10-J22; em tres
#: caracteres isso e' J00-J06 e J10-J22. A diferenca sao subcategorias de
#: amigdalite e faringite estreptococica, que praticamente nao matam.
CONTROLE = r"^J(0[0-6]|1[0-9]|2[0-2])$"

#: Sensibilidade: so pneumonia e influenza, o nucleo letal do grupo.
CONTROLE_ESTRITO = r"^J1[0-8]$"

#: Causas mal definidas (capitulo XVIII), para o teste de redistribuicao.
MAL_DEFINIDAS = r"^R"

SEM = "sem vigilancia"
RARA = "vigilancia rara (ate 6 meses)"
PARCIAL = "vigilancia parcial (7 a 11)"
REGULAR = "vigilancia regular (12)"
CLASSES = [SEM, RARA, PARCIAL, REGULAR]
REFERENCIA = REGULAR


# ── montagem ───────────────────────────────────────────────────────────────
def _classificar(m: float) -> str:
    if pd.isna(m):
        return SEM
    if m <= 6:
        return RARA
    if m < 12:
        return PARCIAL
    return REGULAR


def montar() -> pd.DataFrame:
    """Um municipio por linha, com exposicao, desfecho e confundidores."""
    mort = pd.read_parquet(MARTS / "mart_mortalidade_causa_municipio.parquet",
                           columns=["municipio_cod", "ano", "causabas_3", "obitos"])
    mort = mort[mort.ano.isin(ANOS)]

    def soma(padrao: str, nome: str) -> pd.Series:
        return (mort[mort.causabas_3.str.match(padrao)]
                .groupby("municipio_cod").obitos.sum().rename(nome))

    pecas = [soma(HIDRICA, "hidrica"), soma(CONTROLE, "controle"),
             soma(CONTROLE_ESTRITO, "controle_estrito"),
             soma(MAL_DEFINIDAS, "mal_definidas"),
             mort.groupby("municipio_cod").obitos.sum().rename("obitos_total")]

    pop = (pd.read_parquet(MARTS / "dim_populacao.parquet")
           .query("ano in @ANOS").groupby("municipio_cod")
           .populacao.sum().rename("pessoas_ano"))

    cob = pd.read_parquet(MARTS / "mart_sisagua_cobertura.parquet")
    sis = pd.read_parquet(MARTS / "mart_sisagua_municipio.parquet",
                          columns=["municipio_cod", "ano", "meses_com_analise"])
    mediana = (sis[sis.ano.isin(ANOS)].groupby("municipio_cod")
               .meses_com_analise.median())

    ivs = pd.read_parquet(MARTS / "dim_ivs.parquet")[
        ["municipio_cod", "pct_sem_agua", "taxa_analfabetismo"]]
    dim = pd.read_parquet(MARTS / "dim_municipio.parquet")[
        ["municipio_cod", "municipio_nome", "uf_sigla", "regiao"]]

    d = cob[["municipio_cod", "coletado", "registros_brutos"]].copy()
    for p in pecas:
        d = d.join(p, on="municipio_cod")
    d = (d.join(pop, on="municipio_cod").join(mediana, on="municipio_cod")
           .merge(ivs, on="municipio_cod", how="left")
           .merge(dim, on="municipio_cod", how="left"))
    for c in ("hidrica", "controle", "controle_estrito", "mal_definidas", "obitos_total"):
        d[c] = d[c].fillna(0)
    d["classe"] = d.meses_com_analise.map(_classificar)

    antes = len(d)
    # Municipio nao coletado fica FORA: nao sabemos a vigilancia dele, e
    # chama-lo de "sem vigilancia" seria inventar exposicao. Sem pessoas-ano
    # tambem sai: ausencia de denominador nao e' exposicao baixa.
    d = d[d.coletado & d.pessoas_ano.notna() & (d.pessoas_ano > 0)].copy()
    d["q_agua"] = pd.qcut(d.pct_sem_agua, 4, labels=["Q1", "Q2", "Q3", "Q4"],
                          duplicates="drop")
    print(f"[base] {antes:,} municipios -> {len(d):,} analisaveis", flush=True)
    return d


# ── razoes ─────────────────────────────────────────────────────────────────
def _rr(d: pd.DataFrame, col: str) -> float:
    g = d.groupby("classe", observed=True).agg(ob=(col, "sum"), py=("pessoas_ano", "sum"))
    if SEM not in g.index or REFERENCIA not in g.index:
        return np.nan
    a, b = g.loc[SEM], g.loc[REFERENCIA]
    if a.py <= 0 or b.py <= 0 or b.ob <= 0:
        return np.nan
    return (a.ob / a.py) / (b.ob / b.py)


def rrr(d: pd.DataFrame, controle: str = "controle") -> float:
    return _rr(d, "hidrica") / _rr(d, controle)


def rrr_por_acesso(d: pd.DataFrame) -> float:
    """RRR dentro de quartis de pct_sem_agua, reunido por Mantel-Haenszel."""
    num = den = 0.0
    for _, s in d.groupby("q_agua", observed=True):
        r = rrr(s)
        if not np.isfinite(r) or r <= 0:
            continue
        g = s.groupby("classe", observed=True).agg(h=("hidrica", "sum"),
                                                   c=("controle", "sum"))
        if SEM not in g.index or REFERENCIA not in g.index:
            continue
        cont = [g.loc[SEM].h, g.loc[SEM].c, g.loc[REFERENCIA].h, g.loc[REFERENCIA].c]
        if min(cont) <= 0:
            continue
        peso = 1.0 / sum(1.0 / c for c in cont)
        num += peso * np.log(r)
        den += peso
    return float(np.exp(num / den)) if den > 0 else np.nan


def ic(d: pd.DataFrame, fn, reps: int = REPS) -> tuple[float, float, float]:
    """IC95% por reamostragem de MUNICIPIOS, nao de obitos."""
    rng = np.random.default_rng(SEMENTE)
    idx = np.arange(len(d))
    vals = []
    for _ in range(reps):
        v = fn(d.iloc[rng.choice(idx, size=len(idx), replace=True)])
        if np.isfinite(v):
            vals.append(v)
    a = np.array(vals)
    return fn(d), float(np.percentile(a, 2.5)), float(np.percentile(a, 97.5))


# ── tabelas ────────────────────────────────────────────────────────────────
def tab01_base(d: pd.DataFrame) -> pd.DataFrame:
    """O FUNIL, nao so' o recorte final.

    A primeira versao desta tabela dava apenas os totais do conjunto analisavel,
    e a Tabela 2 — que le o mart inteiro, ano a ano — dava outros. As duas
    estavam certas e o manuscrito nao dizia que eram recortes diferentes: um
    revisor leu 49.429 aqui e somou 49.450 ali, e viu inconsistencia onde havia
    omissao. A diferenca sao 25 codigos do tipo `110000`, `120000` — "municipio
    ignorado" dentro da UF —, que nao sao municipios e por isso nao tem classe
    de vigilancia nem denominador populacional.

    Agora as duas pontas do funil aparecem na mesma tabela, com a perda nomeada.
    """
    m = pd.read_parquet(MARTS / "mart_mortalidade_causa_municipio.parquet",
                        columns=["municipio_cod", "ano", "causabas_3", "obitos"])
    m = m[m.ano.isin(ANOS)]
    codigos_reais = set(pd.read_parquet(MARTS / "dim_municipio.parquet")
                        .municipio_cod.astype(str))
    fora = m[~m.municipio_cod.astype(str).isin(codigos_reais)]

    def soma(tab, padrao=None):
        return int(tab[tab.causabas_3.str.match(padrao)].obitos.sum() if padrao
                   else tab.obitos.sum())

    return pd.DataFrame([
        ("Municipios do pais (dim_municipio)", 5571),
        ("Coletados pelo SISAGUA", int(d.coletado.sum())),
        ("Analisaveis (coletados e com denominador)", len(d)),
        ("--- obitos, o funil ---", None),
        ("Obitos no mart, 2015-2024", soma(m)),
        ("(-) em codigo de municipio ignorado (25 codigos)", -soma(fora)),
        ("= Obitos no conjunto analisavel", int(d.obitos_total.sum())),
        ("--- desfecho e controle, no conjunto analisavel ---", None),
        ("Obitos por A00-A09 (subgrupo 1.2)", int(d.hidrica.sum())),
        ("(dos quais perdidos em municipio ignorado)", -soma(fora, HIDRICA)),
        ("Obitos por infeccao respiratoria (subgrupo 1.2)", int(d.controle.sum())),
        ("(dos quais perdidos em municipio ignorado)", -soma(fora, CONTROLE)),
        ("Pessoas-ano", int(d.pessoas_ano.sum())),
    ], columns=["Recorte", "Valor"])


def tab02_serie(anos: list[int]) -> pd.DataFrame:
    m = pd.read_parquet(MARTS / "mart_mortalidade_causa_municipio.parquet",
                        columns=["ano", "causabas_3", "obitos", "preliminar"])
    m = m[m.ano.isin(anos)]
    g = m.groupby("ano").agg(total=("obitos", "sum"),
                             preliminar=("preliminar", "max"))
    for nome, padrao in (("hidrica", HIDRICA), ("controle", CONTROLE),
                         ("mal_definidas", MAL_DEFINIDAS)):
        g[nome] = m[m.causabas_3.str.match(padrao)].groupby("ano").obitos.sum()
    g = g.reset_index()
    g["hidrica_por_10k_obitos"] = (1e4 * g.hidrica / g.total).round(2)
    g["mal_definidas_pct"] = (100 * g.mal_definidas / g.total).round(2)
    return g.rename(columns={
        "ano": "Ano", "total": "Obitos totais", "hidrica": "A00-A09",
        "controle": "Infeccao respiratoria", "mal_definidas": "Mal definidas",
        "preliminar": "Ano preliminar",
        "hidrica_por_10k_obitos": "A00-A09 por 10 mil obitos",
        "mal_definidas_pct": "% mal definidas"})


def tab03_por_faixa() -> pd.DataFrame:
    f = pd.read_parquet(MARTS / "mart_mortalidade_causa_municipio_faixa.parquet",
                        columns=["ano", "causabas_3", "faixa_etaria", "obitos"])
    f = f[f.ano.isin([2019, 2024]) & f.causabas_3.str.match(HIDRICA)]
    p = f.pivot_table(index="faixa_etaria", columns="ano", values="obitos",
                      aggfunc="sum", fill_value=0).reset_index()
    p["Variacao %"] = (100 * (p[2024] - p[2019]) / p[2019].replace(0, np.nan)).round(1)
    ordem = ["<1", "1-4", "5-14", "15-29", "30-44", "45-59", "60-74", "75+"]
    p["_o"] = p.faixa_etaria.map({v: i for i, v in enumerate(ordem)})
    return (p.sort_values("_o").drop(columns="_o")
            .rename(columns={"faixa_etaria": "Faixa etaria", 2019: "2019", 2024: "2024"}))


def tab04_por_codigo() -> pd.DataFrame:
    m = pd.read_parquet(MARTS / "mart_mortalidade_causa_municipio.parquet",
                        columns=["ano", "causabas_3", "obitos"])
    m = m[m.ano.isin([2019, 2024]) & m.causabas_3.str.match(HIDRICA)]
    p = m.pivot_table(index="causabas_3", columns="ano", values="obitos",
                      aggfunc="sum", fill_value=0).reset_index()
    p["Variacao %"] = (100 * (p[2024] - p[2019]) / p[2019].replace(0, np.nan)).round(1)
    nomes = {"A00": "Colera", "A01": "Febres tifoide e paratifoide",
             "A02": "Outras infeccoes por Salmonella", "A03": "Shiguelose",
             "A04": "Outras infeccoes intestinais bacterianas",
             "A05": "Intoxicacoes alimentares bacterianas",
             "A06": "Amebiase", "A07": "Outras doencas intestinais por protozoarios",
             "A08": "Infeccoes intestinais virais",
             "A09": "Diarreia e gastroenterite de origem infecciosa presumivel"}
    p.insert(1, "Descricao", p.causabas_3.map(nomes))
    return p.rename(columns={"causabas_3": "CID-10", 2019: "2019", 2024: "2024"})


def tab05_teste_codificacao() -> pd.DataFrame:
    """A alta persiste onde a codificacao NAO melhorou? (criterio declarado)"""
    m = pd.read_parquet(MARTS / "mart_mortalidade_causa_municipio.parquet",
                        columns=["municipio_cod", "ano", "causabas_3", "obitos"])
    m = m[m.ano.isin([2019, 2024])]
    m["hid"] = m.causabas_3.str.match(HIDRICA)
    m["mal"] = m.causabas_3.str.match(MAL_DEFINIDAS)
    g = (m.groupby(["municipio_cod", "ano"])
         .apply(lambda x: pd.Series({"tot": x.obitos.sum(),
                                     "hid": x.loc[x.hid, "obitos"].sum(),
                                     "mal": x.loc[x.mal, "obitos"].sum()}),
                include_groups=False).reset_index())
    w = g.pivot(index="municipio_cod", columns="ano", values=["tot", "hid", "mal"]).dropna()
    w.columns = [f"{a}_{b}" for a, b in w.columns]
    w = w[(w.tot_2019 >= 100) & (w.tot_2024 >= 100)]
    w["d"] = w.mal_2024 / w.tot_2024 - w.mal_2019 / w.tot_2019

    def alta(s):
        return round(100 * (s.hid_2024.sum() - s.hid_2019.sum()) / max(s.hid_2019.sum(), 1), 1)

    linhas = [("Todos os municipios com base suficiente", w),
              ("Onde as mal definidas NAO cairam", w[w.d >= 0]),
              ("Onde as mal definidas cairam", w[w.d < 0])]
    return pd.DataFrame([{"Recorte": n, "Municipios": len(s),
                          "A00-A09 2019": int(s.hid_2019.sum()),
                          "A00-A09 2024": int(s.hid_2024.sum()),
                          "Variacao %": alta(s)} for n, s in linhas])


def tab06_exposicao(d: pd.DataFrame) -> pd.DataFrame:
    g = d.groupby("classe", observed=True).agg(
        municipios=("municipio_cod", "size"), pessoas_ano=("pessoas_ano", "sum"),
        hidrica=("hidrica", "sum"), controle=("controle", "sum"),
        obitos_total=("obitos_total", "sum"),
        pct_sem_agua=("pct_sem_agua", "median"),
        analfabetismo=("taxa_analfabetismo", "median")).reindex(CLASSES).reset_index()
    g["Taxa A00-A09 por 100 mil"] = (1e5 * g.hidrica / g.pessoas_ano).round(2)
    g["Taxa respiratoria por 100 mil"] = (1e5 * g.controle / g.pessoas_ano).round(1)
    g["Mortalidade geral por 100 mil"] = (1e5 * g.obitos_total / g.pessoas_ano).round(0)
    g["A00-A09 por 10 mil obitos"] = (1e4 * g.hidrica / g.obitos_total).round(1)
    return g.rename(columns={"classe": "Classe de vigilancia",
                             "municipios": "Municipios", "pessoas_ano": "Pessoas-ano",
                             "hidrica": "Obitos A00-A09", "controle": "Obitos respiratorios",
                             "obitos_total": "Obitos totais",
                             "pct_sem_agua": "% sem agua (mediana)",
                             "analfabetismo": "Analfabetismo % (mediana)"})


def tab07_gradiente(d: pd.DataFrame) -> pd.DataFrame:
    g = d.groupby("classe", observed=True).agg(
        h=("hidrica", "sum"), c=("controle", "sum"), py=("pessoas_ano", "sum")).reindex(CLASSES)
    ref = g.loc[REFERENCIA]
    linhas = []
    for cl in CLASSES:
        rh = (g.loc[cl].h / g.loc[cl].py) / (ref.h / ref.py)
        rc = (g.loc[cl].c / g.loc[cl].py) / (ref.c / ref.py)
        linhas.append({"Classe de vigilancia": cl, "RR A00-A09": round(rh, 3),
                       "RR respiratoria": round(rc, 3), "RRR": round(rh / rc, 3)})
    return pd.DataFrame(linhas)


def tab08_criterios(d: pd.DataFrame) -> pd.DataFrame:
    linhas = []
    for nome, fn, pre in (
            ("1. Especificidade (bruto)", lambda x: rrr(x), "sim"),
            ("2. Ajustado por acesso a agua (MH)", rrr_por_acesso, "sim"),
            ("Sensibilidade: controle so pneumonia/influenza",
             lambda x: rrr(x, "controle_estrito"), "sim")):
        v, lo, hi = ic(d, fn)
        linhas.append({"Criterio": nome, "Pre-declarado": pre, "RRR": round(v, 3),
                       "IC95% inferior": round(lo, 3), "IC95% superior": round(hi, 3),
                       "Exclui 1": "sim" if lo > 1 else "NAO"})
        print(f"   {nome}: {v:.3f} [{lo:.3f}, {hi:.3f}]", flush=True)
    return pd.DataFrame(linhas)


def tab09_por_idade(d: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """RRR DENTRO de cada faixa etaria. Post-hoc, e rotulado como tal."""
    f = pd.read_parquet(MARTS / "mart_mortalidade_causa_municipio_faixa.parquet",
                        columns=["municipio_cod", "ano", "causabas_3", "faixa_etaria", "obitos"])
    f = f[f.ano.isin(ANOS)].merge(d[["municipio_cod", "classe"]], on="municipio_cod")
    f["tipo"] = np.where(f.causabas_3.str.match(HIDRICA), "hid",
                         np.where(f.causabas_3.str.match(CONTROLE), "ctr", "outro"))
    w = (f.groupby(["municipio_cod", "classe", "faixa_etaria", "tipo"], observed=True)
         .obitos.sum().unstack("tipo").fillna(0).reset_index())
    for c in ("hid", "ctr", "outro"):
        if c not in w:
            w[c] = 0.0
    w["total"] = w.hid + w.ctr + w.outro
    w = w[w.classe.isin([SEM, REFERENCIA])]

    def mh(tab):
        g = tab.groupby(["faixa_etaria", "classe"], observed=True)[["hid", "ctr", "total"]].sum()
        num = den = 0.0
        for fx in g.index.get_level_values(0).unique():
            try:
                a, b = g.loc[(fx, SEM)], g.loc[(fx, REFERENCIA)]
            except KeyError:
                continue
            if min(a.hid, b.hid, a.ctr, b.ctr) <= 0 or a.total <= 0 or b.total <= 0:
                continue
            rh = (a.hid / a.total) / (b.hid / b.total)
            rc = (a.ctr / a.total) / (b.ctr / b.total)
            p = 1.0 / sum(1.0 / x for x in (a.hid, b.hid, a.ctr, b.ctr))
            num += p * np.log(rh / rc)
            den += p
        return float(np.exp(num / den)) if den else np.nan

    g = w.groupby(["faixa_etaria", "classe"], observed=True)[["hid", "ctr", "total"]].sum()
    ordem = ["<1", "1-4", "5-14", "15-29", "30-44", "45-59", "60-74", "75+"]
    linhas = []
    for fx in ordem:
        try:
            a, b = g.loc[(fx, SEM)], g.loc[(fx, REFERENCIA)]
        except KeyError:
            continue
        rh = (a.hid / a.total) / (b.hid / b.total)
        rc = (a.ctr / a.total) / (b.ctr / b.total)
        linhas.append({"Faixa etaria": fx, "A00-A09 sem vigilancia": int(a.hid),
                       "A00-A09 vigilancia regular": int(b.hid),
                       "RR A00-A09": round(rh, 3), "RR respiratoria": round(rc, 3),
                       "RRR": round(rh / rc, 3)})

    munis = w.municipio_cod.unique()
    rng = np.random.default_rng(SEMENTE)
    porm = {m: w[w.municipio_cod.values == m] for m in munis}
    vals = [mh(pd.concat([porm[m] for m in rng.choice(munis, len(munis), True)],
                         ignore_index=True)) for _ in range(400)]
    v = np.array([x for x in vals if np.isfinite(x)])
    resumo = {"rrr": round(mh(w), 3), "lo": round(float(np.percentile(v, 2.5)), 3),
              "hi": round(float(np.percentile(v, 97.5)), 3), "reps": len(v)}
    print(f"   4. Idade (post-hoc): {resumo['rrr']} [{resumo['lo']}, {resumo['hi']}]", flush=True)
    return pd.DataFrame(linhas), resumo


def tab10_sem_vigilancia(d: pd.DataFrame) -> pd.DataFrame:
    s = d[d.classe == SEM]
    g = (s.groupby("uf_sigla").agg(municipios=("municipio_cod", "size"),
                                   hidrica=("hidrica", "sum"),
                                   pessoas_ano=("pessoas_ano", "sum"))
         .sort_values("municipios", ascending=False).reset_index())
    g["Taxa A00-A09 por 100 mil"] = (1e5 * g.hidrica / g.pessoas_ano).round(2)
    total = d.groupby("uf_sigla").municipio_cod.size().rename("total")
    g = g.merge(total, on="uf_sigla")
    g["% da UF sem vigilancia"] = (100 * g.municipios / g.total).round(1)
    return g.rename(columns={"uf_sigla": "UF", "municipios": "Municipios sem vigilancia",
                             "hidrica": "Obitos A00-A09", "total": "Municipios na UF"})


def tab11_por_quartil_agua(d: pd.DataFrame) -> pd.DataFrame:
    linhas = []
    for q, s in d.groupby("q_agua", observed=True):
        r = rrr(s)
        linhas.append({"Quartil de acesso (Censo)": str(q),
                       "Municipios": len(s),
                       "% sem agua (mediana)": round(s.pct_sem_agua.median(), 2),
                       "Obitos A00-A09": int(s.hidrica.sum()),
                       "RRR no estrato": round(r, 3) if np.isfinite(r) else None})
    return pd.DataFrame(linhas)


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    SAIDA.mkdir(parents=True, exist_ok=True)
    d = montar()

    print("\n[criterios]", flush=True)
    t08 = tab08_criterios(d)
    t09, resumo_idade = tab09_por_idade(d)
    t08 = pd.concat([t08, pd.DataFrame([{
        "Criterio": "4. Padronizado por idade (POST-HOC)", "Pre-declarado": "nao",
        "RRR": resumo_idade["rrr"], "IC95% inferior": resumo_idade["lo"],
        "IC95% superior": resumo_idade["hi"],
        "Exclui 1": "sim" if resumo_idade["lo"] > 1 else "NAO"}])], ignore_index=True)

    tabelas = {
        "tab01_base": tab01_base(d),
        "tab02_serie_anual": tab02_serie(list(range(2015, 2026))),
        "tab03_alta_por_faixa": tab03_por_faixa(),
        "tab04_alta_por_codigo": tab04_por_codigo(),
        "tab05_teste_codificacao": tab05_teste_codificacao(),
        "tab06_exposicao": tab06_exposicao(d),
        "tab07_gradiente": tab07_gradiente(d),
        "tab08_criterios": t08,
        "tab09_rrr_por_idade": t09,
        "tab10_sem_vigilancia_por_uf": tab10_sem_vigilancia(d),
        "tab11_por_quartil_de_acesso": tab11_por_quartil_agua(d),
    }
    for nome, t in tabelas.items():
        t.to_csv(SAIDA / f"{nome}.csv", index=False, encoding="utf-8")
        print(f"   {nome}: {len(t)} linhas", flush=True)
    print(f"\n[ok] {len(tabelas)} tabelas em {SAIDA.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
