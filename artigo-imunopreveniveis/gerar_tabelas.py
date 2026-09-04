"""
gerar_tabelas.py — as dezesseis tabelas do artigo sobre mortes imunopreveníveis
===============================================================================

Nenhum número do manuscrito é digitado. Cada tabela sai daqui, e daqui sai de
`scripts/analise_mortes_imunopreveniveis.py`, que é o único lugar onde as listas
de CID-10 e a derivação do óbito existem. É a mesma disciplina de
`artigo/gerar_tabelas.py` e de `artigo-neoplasias/gerar_tabelas.py`, e pela mesma
razão: prosa não tem quem a contradiga, e por isso envelhece em silêncio.

POR QUE ESTE SCRIPT RECALCULA A PARTIR DO MICRODADO
----------------------------------------------------
Ele reagrega o SIM (cerca de 15 segundos) em vez de ler os CSVs já gravados em
`data/analises/`. A alternativa parece equivalente e não é: bastaria alguém
recoletar o SIM e esquecer de rodar a análise para o artigo passar a descrever
um dado que não existe mais, sem que nada avisasse. Foi exatamente o que
aconteceu no primeiro manuscrito do repositório quando 2024 foi recoletado do
`.dbc` — doze tabelas divergiram de uma vez, em silêncio.

O QUE ELE **NÃO** FAZ
----------------------
Não define lista de CID, não decide o que é óbito, não escolhe faixa etária.
Tudo isso é importado de `analise_mortes_imunopreveniveis`. Se aparecer aqui uma
lista de códigos, ela está no lugar errado — seriam duas listas que divergem
sem avisar, que é a classe de defeito que este repositório mais persegue.

As contas que ELE faz são de apresentação: razão entre dois totais já contados,
percentual de composição, subtotal. Nenhuma delas muda o que foi medido.

Uso:
  .venv311/Scripts/python artigo-imunopreveniveis/gerar_tabelas.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import duckdb
import pandas as pd

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parents[1]
SAIDA = Path(__file__).resolve().parent / "tabelas"
sys.path.insert(0, str(ROOT / "scripts"))

from _sim_obitos import ANOS_CONSOLIDADOS, ANOS_PRELIMINARES  # noqa: E402
from analise_mortes_imunopreveniveis import (  # noqa: E402
    AMPLIADO,
    LATENCIA_LONGA,
    OFICIAL_0A4,
    OFICIAL_0A4_4,
    OFICIAL_5A74,
    OFICIAL_5A74_4,
    _predicado_ampliado,
    _predicado_oficial,
    carregar,
    cruzamento_influenza,
    guardas,
)

MARTS = ROOT / "data" / "marts"

ANOS_CONS = list(ANOS_CONSOLIDADOS)
ANOS_TODOS = sorted(set(ANOS_CONS) | set(ANOS_PRELIMINARES))
FAIXA_CONS = ",".join(str(a) for a in ANOS_CONS)

#: Nome legível de cada código do subgrupo 1.1, na ordem em que a nota técnica
#: do TabNet os lista. Mora aqui, e não na análise, porque é rótulo de página:
#: a análise trabalha com o código, que é o que não muda.
NOME_CID = {
    "A17": "Tuberculose do sistema nervoso",
    "A19": "Tuberculose miliar",
    "A33": "Tétano neonatal",
    "A34": "Tétano obstétrico",
    "A35": "Tétano (outras formas)",
    "A36": "Difteria",
    "A37": "Coqueluche",
    "A80": "Poliomielite aguda",
    "B05": "Sarampo",
    "B06": "Rubéola",
    "B16": "Hepatite aguda B",
    "B26": "Caxumba",
    "G000": "Meningite por Haemophilus",
    "P350": "Síndrome da rubéola congênita",
    "P353": "Hepatite viral congênita",
}

#: Ordem de apresentação, idêntica à da nota técnica.
ORDEM_CID = ("A17", "A19", "A33", "A34", "A35", "A36", "A37", "A80",
             "B05", "B06", "B16", "B26", "G000", "P350", "P353")


def _um(con: duckdb.DuckDBPyConnection, sql: str) -> float:
    return float(con.execute(sql).fetchone()[0] or 0)


def _obitos(con, predicado: str, anos: str = FAIXA_CONS) -> int:
    return int(_um(con, f"SELECT COALESCE(sum(obitos),0) FROM obitos4 "
                        f"WHERE ano IN ({anos}) AND ({predicado})"))


def _pred_codigo(codigo: str) -> str:
    """Predicado de um código, respeitando se ele tem 3 ou 4 caracteres."""
    return (f"causabas = '{codigo}'" if len(codigo) == 4
            else f"substr(causabas,1,3) = '{codigo}'")


# --------------------------------------------------------------------------- #
# 1. A base                                                                    #
# --------------------------------------------------------------------------- #
def tabela_1_base(con) -> pd.DataFrame:
    prelim = ",".join(str(a) for a in sorted(ANOS_PRELIMINARES))
    itens = [
        ("Óbitos não fetais, 2015–2024", _um(con, f"SELECT sum(obitos) FROM obitos4 WHERE ano IN ({FAIXA_CONS})")),
        ("Óbitos não fetais, 2025 (preliminar)", _um(con, f"SELECT sum(obitos) FROM obitos4 WHERE ano IN ({prelim})")),
        ("Códigos de município de residência distintos", _um(con, f"SELECT count(DISTINCT municipio_cod) FROM obitos4 WHERE ano IN ({FAIXA_CONS})")),
        ("Códigos da CID-10 (4 caracteres) presentes", _um(con, f"SELECT count(DISTINCT causabas) FROM obitos4 WHERE ano IN ({FAIXA_CONS})")),
        ("Óbitos com causa mal definida (R00–R99)", _um(con, f"SELECT sum(obitos) FROM obitos4 WHERE ano IN ({FAIXA_CONS}) AND substr(causabas,1,1) = 'R'")),
        ("Óbitos com idade ignorada", _um(con, f"SELECT COALESCE(sum(obitos),0) FROM obitos4 WHERE ano IN ({FAIXA_CONS}) AND idade_anos IS NULL")),
        ("Óbitos codificados em U07 (COVID-19 da CID-10)", _um(con, f"SELECT COALESCE(sum(obitos),0) FROM obitos4 WHERE ano IN ({FAIXA_CONS}) AND substr(causabas,1,3) = 'U07'")),
        ("Óbitos codificados em B34.2 (COVID-19 no SIM brasileiro)", _um(con, f"SELECT sum(obitos) FROM obitos4 WHERE ano IN ({FAIXA_CONS}) AND causabas = 'B342'")),
    ]
    d = pd.DataFrame(itens, columns=["Item", "Valor"])
    total = itens[0][1]
    mal = itens[4][1]
    d.loc[len(d)] = ["Causas mal definidas, em % dos óbitos", round(100 * mal / total, 2)]
    return d


# --------------------------------------------------------------------------- #
# 2. Os códigos do subgrupo 1.1                                                #
# --------------------------------------------------------------------------- #
def tabela_2_codigos(con) -> pd.DataFrame:
    linhas = []
    for cod in ORDEM_CID:
        em_0a4 = cod in OFICIAL_0A4 or cod in OFICIAL_0A4_4
        em_5a74 = cod in OFICIAL_5A74 or cod in OFICIAL_5A74_4
        rotulo = cod if len(cod) == 3 else f"{cod[:3]}.{cod[3]}"
        linhas.append({
            "Doença": NOME_CID[cod],
            "CID-10": rotulo,
            "Menores de 5 anos": "sim" if em_0a4 else "não",
            "5 a 74 anos": "sim" if em_5a74 else "não",
            "Óbitos 2015–2024, todas as idades": _obitos(con, _pred_codigo(cod)),
        })
    return pd.DataFrame(linhas)


# --------------------------------------------------------------------------- #
# 3. O subgrupo 1.1 ano a ano                                                  #
# --------------------------------------------------------------------------- #
def tabela_3_oficial_por_ano(con) -> pd.DataFrame:
    cids = ",".join(f"'{c}'" for c in OFICIAL_5A74)
    d = con.execute(f"""
        SELECT ano AS "Ano",
               sum(CASE WHEN {_predicado_oficial()} THEN obitos ELSE 0 END)::INT AS "Óbitos do subgrupo 1.1",
               sum(CASE WHEN idade_anos >= 75
                         AND (substr(causabas,1,3) IN ({cids}) OR causabas = 'G000')
                    THEN obitos ELSE 0 END)::INT                                 AS "Mesmos códigos em 75 anos ou mais",
               sum(obitos)::INT                                                  AS "Óbitos totais do ano",
               round(10000.0 * sum(CASE WHEN {_predicado_oficial()} THEN obitos ELSE 0 END)
                     / sum(obitos), 2)                                           AS "Subgrupo 1.1 por 10 mil óbitos"
        FROM obitos4 WHERE ano IN ({FAIXA_CONS}) GROUP BY 1 ORDER BY 1
    """).df()
    d["Ano"] = d["Ano"].astype(object)
    tot = d.iloc[:, 1:4].sum()
    d.loc[len(d)] = ["2015–2024", int(tot.iloc[0]), int(tot.iloc[1]), int(tot.iloc[2]),
                     round(10000 * tot.iloc[0] / tot.iloc[2], 2)]
    return d


# --------------------------------------------------------------------------- #
# 4. Panorama dos conjuntos                                                    #
# --------------------------------------------------------------------------- #
def tabela_4_panorama(con) -> pd.DataFrame:
    """Os quatro conjuntos lado a lado. É a tabela que carrega o achado."""
    total_obitos = _um(con, f"SELECT sum(obitos) FROM obitos4 WHERE ano IN ({FAIXA_CONS})")
    oficial = _obitos(con, _predicado_oficial())
    covid = _obitos(con, "causabas = 'B342'")
    amp_sem_covid = _obitos(con, _predicado_ampliado(incluir_covid=False))
    amp_pni = _obitos(con, _predicado_ampliado(incluir_covid=False, so_pni=True))
    latencia = _obitos(con, "(" + " OR ".join(f"({p})" for _, p, _ in LATENCIA_LONGA) + ")")

    linhas = [
        ("Subgrupo 1.1 da Lista Brasileira (o instrumento oficial)", oficial),
        ("Conjunto ampliado, sem COVID-19", amp_sem_covid),
        ("Conjunto ampliado, sem COVID-19 e sem herpes zoster", amp_pni),
        ("COVID-19 (B34.2)", covid),
        ("Latência longa (colo do útero, fígado e hepatite B crônica)", latencia),
    ]
    d = pd.DataFrame(linhas, columns=["Conjunto", "Óbitos 2015–2024"])
    d["Por 10 mil óbitos do período"] = [round(10000 * v / total_obitos, 2) for _, v in linhas]
    d["Razão sobre o subgrupo 1.1"] = [round(v / oficial, 2) for _, v in linhas]
    return d


# --------------------------------------------------------------------------- #
# 5. Estrutura etária                                                          #
# --------------------------------------------------------------------------- #
def tabela_5_estrutura_etaria(con) -> pd.DataFrame:
    d = con.execute(f"""
        SELECT CASE WHEN idade_anos IS NULL THEN 'Idade ignorada'
                    WHEN idade_anos < 5    THEN 'Menores de 5 anos'
                    WHEN idade_anos <= 74  THEN '5 a 74 anos'
                    ELSE '75 anos ou mais' END                                   AS "Faixa etária",
               sum(CASE WHEN {_predicado_oficial()} THEN obitos ELSE 0 END)::INT AS "Subgrupo 1.1",
               sum(CASE WHEN {_predicado_ampliado(incluir_covid=False)}
                    THEN obitos ELSE 0 END)::INT                                 AS "Ampliado sem COVID-19",
               sum(CASE WHEN causabas = 'B342' THEN obitos ELSE 0 END)::INT      AS "COVID-19"
        FROM obitos4 WHERE ano IN ({FAIXA_CONS}) GROUP BY 1
        ORDER BY CASE "Faixa etária" WHEN 'Menores de 5 anos' THEN 1
                                     WHEN '5 a 74 anos' THEN 2
                                     WHEN '75 anos ou mais' THEN 3 ELSE 4 END
    """).df()
    d["Total"] = d["Ampliado sem COVID-19"] + d["COVID-19"]
    total = d["Total"].sum()
    d["% do total"] = (100 * d["Total"] / total).round(1)
    d.loc[len(d)] = ["Todas as idades", d["Subgrupo 1.1"].sum(),
                     d["Ampliado sem COVID-19"].sum(), d["COVID-19"].sum(),
                     int(total), 100.0]
    return d


# --------------------------------------------------------------------------- #
# 6. Composição interna do subgrupo 1.1                                        #
# --------------------------------------------------------------------------- #
def tabela_6_composicao(con) -> pd.DataFrame:
    """Quanto do instrumento oficial é tuberculose, e em que idade."""
    tb = "substr(causabas,1,3) IN ('A17','A19')"
    oficial = _obitos(con, _predicado_oficial())
    tb_0a4 = _obitos(con, f"idade_anos < 5 AND {tb}")
    tb_5a74 = _obitos(con, f"idade_anos BETWEEN 5 AND 74 AND {tb}")
    linhas = [
        ("Subgrupo 1.1, total", oficial),
        ("Tuberculose miliar e do sistema nervoso, no subgrupo 1.1", tb_0a4 + tb_5a74),
        ("… destes, em menores de 5 anos (idade em que a BCG protege)", tb_0a4),
        ("… destes, em 5 a 74 anos (sem proteção estabelecida pela BCG)", tb_5a74),
        ("Subgrupo 1.1 excluída a tuberculose", oficial - tb_0a4 - tb_5a74),
    ]
    d = pd.DataFrame(linhas, columns=["Componente", "Óbitos 2015–2024"])
    d["% do subgrupo 1.1"] = [round(100 * v / oficial, 1) for _, v in linhas]
    d["Óbitos por ano"] = [round(v / len(ANOS_CONS), 1) for _, v in linhas]
    return d


# --------------------------------------------------------------------------- #
# 7. O conjunto ampliado, causa a causa                                        #
# --------------------------------------------------------------------------- #
def tabela_7_ampliado(con) -> pd.DataFrame:
    prelim = ",".join(str(a) for a in sorted(ANOS_PRELIMINARES))
    linhas = []
    for rotulo, pred, disp in AMPLIADO:
        linhas.append({
            "Causa": rotulo,
            "Disponibilidade da vacina": disp,
            "Óbitos 2015–2024": _obitos(con, pred),
            "2024": _obitos(con, pred, "2024"),
            "2025 (preliminar)": _obitos(con, pred, prelim),
        })
    d = pd.DataFrame(linhas).sort_values("Óbitos 2015–2024", ascending=False).reset_index(drop=True)
    sem_covid = _obitos(con, _predicado_ampliado(incluir_covid=False))
    so_pni = _obitos(con, _predicado_ampliado(incluir_covid=False, so_pni=True))
    d.loc[len(d)] = ["Subtotal, sem COVID-19", "—", sem_covid,
                     _obitos(con, _predicado_ampliado(incluir_covid=False), "2024"),
                     _obitos(con, _predicado_ampliado(incluir_covid=False), prelim)]
    d.loc[len(d)] = ["Subtotal, sem COVID-19 e sem herpes zoster", "—", so_pni,
                     _obitos(con, _predicado_ampliado(incluir_covid=False, so_pni=True), "2024"),
                     _obitos(con, _predicado_ampliado(incluir_covid=False, so_pni=True), prelim)]
    return d


# --------------------------------------------------------------------------- #
# 8. Os três eventos, série anual                                              #
# --------------------------------------------------------------------------- #
def tabela_8_eventos(con) -> pd.DataFrame:
    d = con.execute("""
        SELECT ano AS "Ano",
               sum(CASE WHEN substr(causabas,1,3) = 'A95' THEN obitos ELSE 0 END)::INT AS "Febre amarela",
               sum(CASE WHEN substr(causabas,1,3) = 'B05' THEN obitos ELSE 0 END)::INT AS "Sarampo",
               sum(CASE WHEN substr(causabas,1,3) = 'B05' AND idade_anos = 0
                    THEN obitos ELSE 0 END)::INT                                       AS "Sarampo em menores de 1 ano",
               sum(CASE WHEN substr(causabas,1,3) = 'A37' THEN obitos ELSE 0 END)::INT AS "Coqueluche",
               sum(CASE WHEN substr(causabas,1,3) = 'A37' AND idade_anos = 0
                    THEN obitos ELSE 0 END)::INT                                       AS "Coqueluche em menores de 1 ano"
        FROM obitos4 GROUP BY 1 ORDER BY 1
    """).df()
    d["Ano"] = d["Ano"].astype(object)
    return d


# --------------------------------------------------------------------------- #
# 9. Febre amarela por UF                                                      #
# --------------------------------------------------------------------------- #
def tabela_9_febre_amarela(con) -> pd.DataFrame:
    con.execute(f"CREATE OR REPLACE VIEW mun AS SELECT * FROM '{MARTS / 'dim_municipio.parquet'}'")
    d = con.execute("""
        SELECT o.ano AS "Ano", m.uf_sigla AS "UF", sum(o.obitos)::INT AS "Óbitos",
               round(avg(o.idade_anos), 1) AS "Idade média",
               round(100.0*sum(CASE WHEN o.sexo = 'M' THEN o.obitos ELSE 0 END)
                     / sum(o.obitos), 1) AS "% do sexo masculino"
        FROM obitos4 o JOIN mun m USING (municipio_cod)
        WHERE substr(o.causabas,1,3) = 'A95' AND o.ano BETWEEN 2017 AND 2018
        GROUP BY 1,2 HAVING sum(o.obitos) >= 5 ORDER BY 1, 3 DESC
    """).df()
    d["Ano"] = d["Ano"].astype(object)
    br = con.execute("""
        SELECT sum(obitos)::INT AS o, round(avg(idade_anos),1) AS i,
               round(100.0*sum(CASE WHEN sexo='M' THEN obitos ELSE 0 END)/sum(obitos),1) AS m
        FROM obitos4 WHERE substr(causabas,1,3) = 'A95' AND ano BETWEEN 2017 AND 2018
    """).df().iloc[0]
    d.loc[len(d)] = ["2017–2018", "Brasil", int(br.o), float(br.i), float(br.m)]
    return d


# --------------------------------------------------------------------------- #
# 10 e 11. Influenza e COVID-19 por faixa etária                               #
# --------------------------------------------------------------------------- #
def _por_faixa(con, predicado: str, desde: int) -> pd.DataFrame:
    d = con.execute(f"""
        SELECT ano AS "Ano",
               sum(CASE WHEN idade_anos < 5 THEN obitos ELSE 0 END)::INT               AS "Menores de 5 anos",
               sum(CASE WHEN idade_anos BETWEEN 5 AND 59 THEN obitos ELSE 0 END)::INT  AS "5 a 59 anos",
               sum(CASE WHEN idade_anos BETWEEN 60 AND 74 THEN obitos ELSE 0 END)::INT AS "60 a 74 anos",
               sum(CASE WHEN idade_anos >= 75 THEN obitos ELSE 0 END)::INT             AS "75 anos ou mais",
               sum(obitos)::INT                                                        AS "Total"
        FROM obitos4 WHERE ({predicado}) AND ano >= {desde} GROUP BY 1 ORDER BY 1
    """).df()
    d["Ano"] = d["Ano"].astype(object)
    return d


def tabela_10_influenza(con) -> pd.DataFrame:
    return _por_faixa(con, "substr(causabas,1,3) IN ('J09','J10','J11')", ANOS_CONS[0])


def tabela_11_covid(con) -> pd.DataFrame:
    d = _por_faixa(con, "causabas = 'B342'", 2021)
    pos = d[d.Ano.isin([2022, 2023, 2024])]
    d.loc[len(d)] = ["2022–2024", int(pos["Menores de 5 anos"].sum()),
                     int(pos["5 a 59 anos"].sum()), int(pos["60 a 74 anos"].sum()),
                     int(pos["75 anos ou mais"].sum()), int(pos["Total"].sum())]
    return d


# --------------------------------------------------------------------------- #
# 12 e 13. O teto de codificação                                               #
# --------------------------------------------------------------------------- #
CODIGOS_TETO = [
    ("R00–R99 — causas mal definidas", "substr(causabas,1,1) = 'R'", "não"),
    ("J18 — pneumonia, agente não especificado", "substr(causabas,1,3) = 'J18'", "não"),
    ("A41.9 — septicemia não especificada", "causabas = 'A419'", "não"),
    ("J15 — outra pneumonia bacteriana", "substr(causabas,1,3) = 'J15'", "não"),
    ("J13 — pneumonia por Streptococcus pneumoniae", "substr(causabas,1,3) = 'J13'", "sim"),
    ("A40.3 — septicemia por Streptococcus pneumoniae", "causabas = 'A403'", "sim"),
    ("J14 — pneumonia por Haemophilus influenzae", "substr(causabas,1,3) = 'J14'", "sim"),
]


def tabela_12_teto(con) -> pd.DataFrame:
    linhas = [{"Código e descrição": rot, "Óbitos 2015–2024": _obitos(con, pred),
               "Agente etiológico nomeado": nomeado}
              for rot, pred, nomeado in CODIGOS_TETO]
    return pd.DataFrame(linhas)


def tabela_13_razoes(con) -> pd.DataFrame:
    pares = [
        ("Pneumonia sem agente (J18) sobre pneumonia pneumocócica (J13)",
         "substr(causabas,1,3) = 'J18'", "substr(causabas,1,3) = 'J13'"),
        ("Septicemia não especificada (A41.9) sobre septicemia pneumocócica (A40.3)",
         "causabas = 'A419'", "causabas = 'A403'"),
        ("Pneumonia sem agente (J18) sobre pneumonia por Haemophilus (J14)",
         "substr(causabas,1,3) = 'J18'", "substr(causabas,1,3) = 'J14'"),
    ]
    linhas = []
    for rot, ines, esp in pares:
        a, b = _obitos(con, ines), _obitos(con, esp)
        linhas.append({"Par de códigos": rot, "Óbitos sem agente": a,
                       "Óbitos com agente": b, "Razão": round(a / b, 1)})
    return pd.DataFrame(linhas)


# --------------------------------------------------------------------------- #
# 14 e 15. O cruzamento ecológico                                              #
# --------------------------------------------------------------------------- #
def tabelas_14_15_cruzamento(con) -> tuple[pd.DataFrame, pd.DataFrame]:
    from scipy.stats import spearmanr  # noqa: PLC0415

    bruto, rhos = cruzamento_influenza(con)
    d = bruto.rename(columns={
        "uf_sigla": "UF", "ano": "Ano", "obitos": "Óbitos por influenza em 60 anos ou mais",
        "pop60": "População de 60 anos ou mais", "inf3": "Doses de influenza (INF3)",
        "obitos_100k_60mais": "Óbitos por 100 mil de 60 anos ou mais",
        "doses_por_60mais": "Doses por habitante de 60 anos ou mais"})
    d["Ano"] = d["Ano"].astype(object)
    d["População de 60 anos ou mais"] = d["População de 60 anos ou mais"].astype(int)
    d["Doses de influenza (INF3)"] = d["Doses de influenza (INF3)"].astype(int)

    # A dose do ano vem do PNI inteiro, não do subconjunto que entrou no join.
    # A diferença é pequena e importa: uma UF sem óbito de influenza em 60+ some
    # do cruzamento e não deve sumir da descrição da fonte.
    nacional = con.execute(f"""
        SELECT CAST(substr(competencia,1,4) AS INT) AS ano, sum(doses)::BIGINT AS inf3
        FROM '{MARTS / 'mart_vacinacao_uf_mes.parquet'}'
        WHERE imunobiologico = 'INF3' AND substr(competencia,1,4) IN ('2023','2024')
        GROUP BY 1""").df().set_index("ano").inf3.to_dict()

    resumo = []
    for ano in sorted(rhos):
        s = bruto[bruto.ano == ano]
        r = spearmanr(s.doses_por_60mais, s.obitos_100k_60mais)
        resumo.append({
            "Ano": ano,
            "Unidades da federação no cruzamento": len(s),
            "Doses de influenza no país (INF3)": int(nacional[ano]),
            "Óbitos por influenza em 60 anos ou mais": int(s.obitos.sum()),
            "Correlação de Spearman": round(float(r.statistic), 3),
            "Valor de p": round(float(r.pvalue), 3),
        })
    return d, pd.DataFrame(resumo)


# --------------------------------------------------------------------------- #
# 16. Latência longa                                                           #
# --------------------------------------------------------------------------- #
def tabela_16_latencia(con) -> pd.DataFrame:
    linhas = []
    for rotulo, pred, obs in LATENCIA_LONGA:
        a, b = _obitos(con, pred, "2015"), _obitos(con, pred, "2024")
        linhas.append({
            "Causa": rotulo,
            "Relação com a vacina": obs,
            "Óbitos 2015–2024": _obitos(con, pred),
            "2015": a,
            "2024": b,
            "Variação de 2015 a 2024, em %": round(100 * (b - a) / a, 1),
        })
    return pd.DataFrame(linhas)


# --------------------------------------------------------------------------- #
def main() -> None:
    SAIDA.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect()
    con.execute("PRAGMA threads=6")
    print(f"[sim] reagregando {ANOS_TODOS[0]}–{ANOS_TODOS[-1]} em CID-10 de 4 caracteres…",
          flush=True)
    carregar(con, ANOS_TODOS)
    guardas(con, ANOS_TODOS)
    print("[sim] guardas OK", flush=True)

    cruz, corr = tabelas_14_15_cruzamento(con)
    tabelas = {
        "tabela_1_base": tabela_1_base(con),
        "tabela_2_codigos_subgrupo_1_1": tabela_2_codigos(con),
        "tabela_3_subgrupo_1_1_por_ano": tabela_3_oficial_por_ano(con),
        "tabela_4_panorama": tabela_4_panorama(con),
        "tabela_5_estrutura_etaria": tabela_5_estrutura_etaria(con),
        "tabela_6_composicao_subgrupo_1_1": tabela_6_composicao(con),
        "tabela_7_ampliado_por_causa": tabela_7_ampliado(con),
        "tabela_8_eventos_serie_anual": tabela_8_eventos(con),
        "tabela_9_febre_amarela_uf": tabela_9_febre_amarela(con),
        "tabela_10_influenza_por_faixa": tabela_10_influenza(con),
        "tabela_11_covid_por_faixa": tabela_11_covid(con),
        "tabela_12_teto_codificacao": tabela_12_teto(con),
        "tabela_13_razoes_de_especificidade": tabela_13_razoes(con),
        "tabela_14_influenza_doses_uf": cruz,
        "tabela_15_correlacao_por_ano": corr,
        "tabela_16_latencia_longa": tabela_16_latencia(con),
    }
    for nome, d in tabelas.items():
        d.to_csv(SAIDA / f"{nome}.csv", index=False, encoding="utf-8")
        print(f"[csv] {nome}.csv — {len(d)} linhas", flush=True)
    print(f"[done] {len(tabelas)} tabelas em {SAIDA}", flush=True)


if __name__ == "__main__":
    main()
