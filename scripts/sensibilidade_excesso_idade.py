"""
sensibilidade_excesso_idade.py — Análise de sensibilidade do excesso de mortalidade
====================================================================================

Compara o método PUBLICADO de excesso (tendência linear por mês civil sobre os
óbitos observados 2015–2019) com uma variante PADRONIZADA POR IDADE, em duas
versões de denominador:
  - B cru        : população por idade/UF/ano da projeção IBGE 2018 (SIDRA t/7358)
  - B reescalado : forma etária da projeção × total pós-Censo (populacao_2015_2024)

Conclusão (ver metodologia §6): ambas as versões de B subestimam o pico pandêmico
(~505 mil vs 643 mil do método de tendência e ~680 mil do consenso independente),
porque o denominário populacional anual do Brasil é problemático em 2015–2024 (a
projeção 2018 superestima; a série pós-Censo tem descontinuidade em 2022). O método
de tendência foi retido por se apoiar apenas nos óbitos observados — imune ao
denominador.

Lê os marts publicados via PostgREST (anon) e a projeção via API v3 do IBGE.
Uso: .venv311/Scripts/python scripts/sensibilidade_excesso_idade.py
"""
from __future__ import annotations

import os
from pathlib import Path

import numpy as np
import pandas as pd
import requests

ROOT = Path(__file__).resolve().parents[1]
REFS = ROOT / "data" / "refs"

UFCOD = {11: "RO", 12: "AC", 13: "AM", 14: "RR", 15: "PA", 16: "AP", 17: "TO",
         21: "MA", 22: "PI", 23: "CE", 24: "RN", 25: "PB", 26: "PE", 27: "AL",
         28: "SE", 29: "BA", 31: "MG", 32: "ES", 33: "RJ", 35: "SP", 41: "PR",
         42: "SC", 43: "RS", 50: "MS", 51: "MT", 52: "GO", 53: "DF"}

# grupos quinquenais (classificação SIDRA 287) -> faixa de 7 grupos
GRUPOS = {"0-4": [93070], "5-14": [93084, 93085], "15-29": [93086, 93087, 93088],
          "30-44": [93089, 93090, 93091], "45-59": [93092, 93093, 93094],
          "60-74": [93095, 93096, 93097]}  # 75+ = Total − soma(0-74)
TOTAL_287 = 100362


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


def fetch_pop_idade_ano() -> pd.DataFrame:
    """População por idade/UF/ano (projeção IBGE 2018, SIDRA t/7358 via API v3)."""
    cache = REFS / "pop_idade_uf_ano.parquet"
    if cache.exists():
        return pd.read_parquet(cache)
    base = "https://servicodados.ibge.gov.br/api/v3/agregados/7358/periodos/2018/variaveis/606"
    anos = {2015 + i: 49031 + i for i in range(10)}  # ano -> categoria 1933
    cats = [TOTAL_287] + [c for ids in GRUPOS.values() for c in ids]
    url = (f"{base}?localidades=N3[all]&classificacao=2[6794]"
           f"|287[{','.join(map(str, cats))}]|1933[{','.join(str(v) for v in anos.values())}]")
    j = requests.get(url, timeout=120).json()
    inv = {str(v): k for k, v in anos.items()}

    def catof(clist, cid):
        for c in clist:
            if str(c["id"]) == str(cid):
                return list(c["categoria"].keys())[0]
        return None

    rows = []
    for res in j[0]["resultados"]:
        cl = res["classificacoes"]
        cat = int(catof(cl, 287)); ano = inv[str(catof(cl, 1933))]
        for s in res["series"]:
            uf = UFCOD.get(int(s["localidade"]["id"]))
            val = s["serie"].get("2018")
            rows.append((uf, ano, cat, float(val) if val not in (None, "...", "-", "X") else 0.0))
    df = pd.DataFrame(rows, columns=["uf_sigla", "ano", "cat", "pop"])
    c2f = {c: fx for fx, ids in GRUPOS.items() for c in ids}
    df["fx"] = df["cat"].map(c2f)
    tot = df[df.cat == TOTAL_287].groupby(["uf_sigla", "ano"])["pop"].sum()
    grp = df[df.fx.notna()].groupby(["uf_sigla", "ano", "fx"])["pop"].sum().unstack()
    grp["75+"] = tot - grp.sum(axis=1)
    out = grp.reset_index().melt(id_vars=["uf_sigla", "ano"], var_name="faixa", value_name="populacao")
    out["populacao"] = out["populacao"].round().astype(int)
    REFS.mkdir(parents=True, exist_ok=True)
    out.to_parquet(cache, index=False)
    return out


def obitos_mensais_faixa(env) -> pd.DataFrame:
    """Óbitos mensais por (uf, ano, mes, faixa de 7 grupos), IGN redistribuído pro-rata."""
    url, key = env["SUPABASE_URL"].rstrip("/"), env["SUPABASE_ANON_KEY"]
    h = {"apikey": key, "Authorization": f"Bearer {key}"}
    rows, off = [], 0
    q = ("mart_mortalidade_uf_mes?capitulo_cid=eq.TOTAL&sexo=eq.TOTAL&faixa_etaria=neq.TOTAL"
         "&select=uf_sigla,ano,mes,faixa_etaria,obitos&order=uf_sigla,ano,mes,faixa_etaria")
    while True:  # paginação COM ordenação determinística (obrigatório no PostgREST)
        r = requests.get(f"{url}/rest/v1/{q}", headers={**h, "Range-Unit": "items",
                         "Range": f"{off}-{off + 999}"}, timeout=90)
        r.raise_for_status(); c = r.json(); rows += c
        if len(c) < 1000:
            break
        off += 1000
    d = pd.DataFrame(rows); d["obitos"] = d["obitos"].astype(int)
    m7 = {"<1": "0-4", "1-4": "0-4", "5-14": "5-14", "15-29": "15-29", "30-44": "30-44",
          "45-59": "45-59", "60-74": "60-74", "75+": "75+"}
    ign = d[d.faixa_etaria == "IGN"].groupby(["uf_sigla", "ano", "mes"])["obitos"].sum().rename("ign")
    d = d[d.faixa_etaria != "IGN"].copy(); d["fx"] = d.faixa_etaria.map(m7)
    g = (d.groupby(["uf_sigla", "ano", "mes", "fx"], as_index=False)["obitos"].sum()
         .merge(ign, on=["uf_sigla", "ano", "mes"], how="left").fillna({"ign": 0}))
    tc = g.groupby(["uf_sigla", "ano", "mes"])["obitos"].transform("sum")
    g["obitos"] = (g["obitos"] + g["ign"] * g["obitos"] / tc.replace(0, np.nan)).fillna(0)
    return g


def excesso_padronizado(g, pop, popcol) -> pd.DataFrame:
    base = g[g.ano.between(2015, 2019)].groupby(["uf_sigla", "mes", "fx"], as_index=False)["obitos"].sum().rename(columns={"obitos": "ob"})
    pb = pop[pop.ano.between(2015, 2019)].groupby(["uf_sigla", "fx"], as_index=False)[popcol].sum().rename(columns={popcol: "pb"})
    rate = base.merge(pb, on=["uf_sigla", "fx"]); rate["taxa"] = rate.ob / rate.pb
    e = rate.merge(pop, on=["uf_sigla", "fx"]); e["esp"] = e.taxa * e[popcol]
    esp = e.groupby(["ano", "mes"], as_index=False)["esp"].sum()
    obs = g.groupby(["ano", "mes"], as_index=False)["obitos"].sum().rename(columns={"obitos": "obs"})
    return esp.merge(obs, on=["ano", "mes"]).assign(exc=lambda x: x.obs - x.esp)


def main() -> None:
    env = load_env()
    g = obitos_mensais_faixa(env)
    proj = fetch_pop_idade_ano().rename(columns={"faixa": "fx", "populacao": "pop"})

    # B reescalado: forma etária da projeção × total pós-Censo
    pr = pd.read_parquet(REFS / "populacao_2015_2024.parquet")
    pr["uf_sigla"] = pr.municipio_cod.astype(str).str[:2].astype(int).map(UFCOD)
    tot = pr.groupby(["uf_sigla", "ano"])["populacao"].sum().rename("tot").reset_index()
    proj["share"] = proj["pop"] / proj.groupby(["uf_sigla", "ano"])["pop"].transform("sum")
    resc = proj.merge(tot, on=["uf_sigla", "ano"]); resc["pop_resc"] = resc.share * resc.tot

    B_cru = excesso_padronizado(g, proj, "pop")
    B_resc = excesso_padronizado(g, resc, "pop_resc")

    # A (tendência) — método publicado
    obs = g.groupby(["ano", "mes"], as_index=False)["obitos"].sum().rename(columns={"obitos": "obs"})
    trA = {}
    for mes in range(1, 13):
        s = obs[(obs.mes == mes) & (obs.ano.between(2015, 2019))]
        b, a0 = np.polyfit(s.ano, s.obs, 1)
        for ano in range(2020, 2025):
            trA[(ano, mes)] = b * ano + a0

    def sA(anos):
        return sum(obs[(obs.ano == a) & (obs.mes == m)].obs.values[0] - trA[(a, m)]
                   for a in anos for m in range(1, 13))

    def sX(df, anos):
        return df[df.ano.isin(anos)].exc.sum()

    print(f"{'Período':<12}{'A tendência':>13}{'B cru(proj)':>13}{'B reescal.':>13}")
    for rot, anos in [("2020-2021", [2020, 2021]), ("2022", [2022]), ("2023", [2023]),
                      ("2024", [2024]), ("2020-2024", list(range(2020, 2025)))]:
        print(f"{rot:<12}{sA(anos):>13,.0f}{sX(B_cru, anos):>13,.0f}{sX(B_resc, anos):>13,.0f}")


if __name__ == "__main__":
    main()
