"""
analise_mortes_imunopreveniveis.py — óbitos por causas que uma vacina previne
=============================================================================

Pergunta: quantas pessoas morreram no Brasil, 2015–2024, de doença para a qual
existe vacina — e o que o instrumento oficial brasileiro enxerga disso.

A resposta curta é que o instrumento oficial enxerga **0,04% dos óbitos do
país e nada mais que isso há uma década**, enquanto o conjunto de causas com
vacina disponível no calendário do PNI soma ordens de grandeza a mais. A
diferença não é epidemiologia: é a data da lista.

O QUE É "EVITÁVEL POR VACINA" AQUI — E O QUE NÃO É
---------------------------------------------------
Este script conta **óbitos cuja causa básica é uma doença com vacina
disponível**. Isso NÃO é o mesmo que "mortes que teriam sido evitadas". Faltam
três coisas para a segunda afirmação, e nenhuma delas sai da CID-10:

  * eficácia da vacina, que nunca é 100%;
  * situação vacinal de quem morreu — se a pessoa era vacinada, a morte não é
    falha de imunização, é falha de proteção;
  * elegibilidade — herpes zoster tem vacina e ela NÃO está no PNI; contar
    esses óbitos como "evitáveis pelo SUS" seria mentira.

Por isso a saída é um **teto**, e cada causa carrega quando a vacina entrou no
PNI. Quem quiser a fração evitável precisa de eficácia e cobertura individuais,
que este dado não tem.

O INSTRUMENTO OFICIAL, E POR QUE ELE ENVELHECEU
------------------------------------------------
A `Lista Brasileira de Causas de Mortes Evitáveis` (Malta et al., 2007; revista
2010–2011) é o padrão do Ministério da Saúde e está publicada como nota técnica
do TabNet/DATASUS. Ela tem um subgrupo 1.1 "reduzível pelas ações de
imunoprevenção", em duas versões etárias — e as duas foram transcritas daqui,
literalmente, das notas técnicas:

    http://tabnet.datasus.gov.br/cgi/sim/Obitos_Evitaveis_0_a_4_anos.pdf
    http://tabnet.datasus.gov.br/cgi/sim/Obitos_Evitaveis_5_a_74_anos.pdf

Três limites estruturais dela, medidos abaixo:

**1. Ela para nos 74 anos.** Não é recorte deste script: é a lista. Não existe
lista de evitabilidade para 75 anos ou mais — a idade avançada foi tratada como
inevitabilidade quando a lista foi escrita. Só que é exatamente onde morrem as
pessoas de influenza e de COVID-19. No conjunto ampliado, cerca de **um terço
dos óbitos está acima de 74 anos**, invisível ao instrumento por construção.

**2. Ela é de 2010.** Não tem COVID-19 (vacina em 2021), não tem rotavírus
(PNI 2006), não tem meningocócica C (2010) nem ACWY (2020), não tem
pneumocócica 10-valente (2010), não tem HPV (2014), não tem varicela (2013).
E classifica **influenza no subgrupo 1.2** — "doenças de causas infecciosas" —,
não no de imunoprevenção, embora a campanha anual exista desde 1999.

**3. O que ela cobre praticamente sumiu.** Dos códigos da lista de 5–74 anos,
dois — tuberculose miliar e do sistema nervoso — respondem por metade dos
óbitos, e são as formas que a BCG previne em criança, não em adulto.
Poliomielite: **zero óbitos em onze anos**. Sarampo, rubéola, difteria e
caxumba somam menos de 25 óbitos por ano no país inteiro.

O TETO DE MEDIÇÃO NÃO É EPIDEMIOLÓGICO, É DE CODIFICAÇÃO
---------------------------------------------------------
O achado que mais restringe qualquer estudo deste tipo no Brasil não está na
lista, está na declaração de óbito. Em 2015–2024:

    J18  pneumonia, agente NÃO especificado      631.108 óbitos
    J15  outra pneumonia bacteriana              160.949
    J13  pneumonia POR PNEUMOCOCO                    809

São centenas de óbitos de pneumonia sem agente para cada um atribuído ao
pneumococo. A literatura atribui ao pneumococo uma fração grande da pneumonia
adulta; o SIM não permite recuperá-la, porque a etiologia não é investigada nem
registrada. O mesmo vale para septicemia: `A41.9` (não especificada) é ~90% de
todo o A41.

Consequência prática: a doença pneumocócica invasiva, alvo de duas vacinas do
PNI, é **estruturalmente incontável** por causa básica. Qualquer número deste
script para pneumococo é piso, e um piso muito abaixo do real. É por isso que
"conjunto ampliado" aqui não vira "carga evitável" — a carga real não está
codificada.

O QUE FOI TESTADO E DEU NULO
-----------------------------
Cruzamento ecológico entre **óbitos por influenza em 60 anos ou mais** e
**doses de influenza aplicadas por habitante de 60+**, por UF, 2023 e 2024
(PNI/RNDS). Critério declarado ANTES de olhar: |ρ| < 0,30, ou troca de sinal
entre os dois anos, seria ausência de sinal.

Resultado: ρ = +0,39 em 2023 e ρ = −0,06 em 2024. Troca de sinal e um ano
abaixo do limiar — **sem sinal**. E há razão para não insistir: a campanha
responde ao surto (causalidade reversa), a unidade é a UF (falácia ecológica),
e o próprio numerador de 2023 está incompleto — 16,6 milhões de doses de INF3
contra 54,2 milhões em 2024, na mesma base. Dose de influenza de 2023 no
PNI/RNDS não serve de denominador de nada.

O QUE SOBRA, E É SÓLIDO
------------------------
Três eventos em que a vacina existia, a doença matou, e o número é grande o
bastante para não ser ruído:

  * **febre amarela, 452 óbitos em 2017–2018** — 86% homens, idade média 49
    anos, concentrados em MG, ES, SP e RJ. A vacina é de 1937. O que faltava
    não era vacina, era o mapa: aquelas áreas só entraram na recomendação
    DEPOIS do surto;
  * **sarampo, 37 óbitos em 2018–2021** contra 3 em 2015–2017 — PA, AM, RR, AP,
    CE, PE, RO, RJ e SP, e 19 deles em menores de 1 ano, que ainda não tinham
    idade de tomar a tríplice viral e dependiam da imunidade de quem estava em
    volta;
  * **coqueluche, 22 óbitos em 2024** depois de zero em 2022 e 2023 — **21 dos
    22 em menores de 1 ano**. É a assinatura da falha de dTpa na gestante somada
    a pentavalente atrasada.

E um alerta que ainda está aberto: **influenza em 2025 já tem 4.575 óbitos com
o dado PRELIMINAR**, o maior da série de onze anos, sendo 2.160 em 75 anos ou
mais. Dado preliminar só cresce.

USO
---
    python scripts/analise_mortes_imunopreveniveis.py            # tudo
    python scripts/analise_mortes_imunopreveniveis.py --sem-cruzamento

Lê `data/raw/SIM` pelas mesmas regras de `_sim_obitos.py` — a definição de
óbito não é redefinida aqui — e grava CSV em `data/analises/`.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import duckdb
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _achados import registrar  # noqa: E402
from _sim_obitos import ANOS_CONSOLIDADOS, ANOS_PRELIMINARES, sql_uniao_fontes  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
MARTS = ROOT / "data" / "marts"
REFS = ROOT / "data" / "refs"
SAIDA = ROOT / "data" / "analises"

#: Subgrupo 1.1 da Lista Brasileira, versão 5–74 anos, transcrito da nota
#: técnica do TabNet/DATASUS. NÃO editar sem trocar a fonte junto.
OFICIAL_5A74 = ("A17", "A19", "A34", "A35", "A36", "A37", "A80", "B05", "B06", "B16")
OFICIAL_5A74_4 = ("G000",)

#: Subgrupo 1.1, versão menores de 5 anos. Difere da outra em quatro pontos:
#: entra tétano neonatal (A33) e sai tétano obstétrico (A34), e entram caxumba
#: (B26), rubéola congênita (P35.0) e hepatite viral congênita (P35.3).
OFICIAL_0A4 = ("A17", "A19", "A33", "A35", "A36", "A37", "A80", "B05", "B06", "B16", "B26")
OFICIAL_0A4_4 = ("G000", "P350", "P353")

#: Conjunto ampliado: uma linha por doença com vacina, com QUANDO a vacina
#: passou a existir na rede pública brasileira. O campo de disponibilidade é o
#: que separa "existe vacina" de "o SUS oferecia a vacina", e é ele que impede
#: a soma preguiçosa — herpes zoster está aqui e está FORA do PNI.
#:
#: (rótulo, predicado SQL sobre `causabas`, disponibilidade)
AMPLIADO: tuple[tuple[str, str, str], ...] = (
    ("COVID-19",                    "causabas = 'B342'",                                 "PNI a partir de 2021"),
    ("Influenza",                   "substr(causabas,1,3) IN ('J09','J10','J11')",       "campanha anual desde 1999"),
    ("Pneumonia pneumocócica",      "substr(causabas,1,3) = 'J13'",                      "PNI (VPC10 2010; VPP23 idosos)"),
    ("Sepse pneumocócica",          "causabas = 'A403'",                                 "PNI (VPC10 2010; VPP23 idosos)"),
    ("Meningite pneumocócica",      "causabas = 'G001'",                                 "PNI (VPC10 2010; VPP23 idosos)"),
    ("Doença meningocócica",        "substr(causabas,1,3) = 'A39'",                      "PNI (MenC 2010; ACWY 2020)"),
    ("Meningite por Haemophilus",   "causabas = 'G000'",                                 "PNI (Hib 1999)"),
    ("Sepse/pneumonia Haemophilus", "causabas = 'A413' OR substr(causabas,1,3) = 'J14'", "PNI (Hib 1999)"),
    ("Rotavírus",                   "causabas = 'A080'",                                 "PNI a partir de 2006"),
    ("Varicela",                    "substr(causabas,1,3) = 'B01'",                      "PNI a partir de 2013"),
    ("Herpes zoster",               "substr(causabas,1,3) = 'B02'",                      "FORA do PNI (rede privada)"),
    ("Febre amarela",               "substr(causabas,1,3) = 'A95'",                      "PNI (área ampliada 2017-2020)"),
    ("Raiva",                       "substr(causabas,1,3) = 'A82'",                      "PNI (profilaxia pós-exposição)"),
    ("Tuberculose miliar e do SNC", "substr(causabas,1,3) IN ('A17','A19')",             "BCG (formas graves na criança)"),
    ("Tétano",                      "substr(causabas,1,3) IN ('A33','A34','A35')",       "PNI (todo o período)"),
    ("Coqueluche",                  "substr(causabas,1,3) = 'A37'",                      "PNI (dTpa gestante 2014)"),
    ("Difteria",                    "substr(causabas,1,3) = 'A36'",                      "PNI (todo o período)"),
    ("Sarampo",                     "substr(causabas,1,3) = 'B05'",                      "PNI (todo o período)"),
    ("Rubéola e SRC",               "substr(causabas,1,3) = 'B06' OR causabas = 'P350'", "PNI (todo o período)"),
    ("Caxumba",                     "substr(causabas,1,3) = 'B26'",                      "PNI (todo o período)"),
    ("Hepatite B aguda",            "substr(causabas,1,3) = 'B16'",                      "PNI (todo o período)"),
    ("Poliomielite",                "substr(causabas,1,3) = 'A80'",                      "PNI (todo o período)"),
)

#: Latência longa: a vacina de hoje não muda o óbito de hoje. Ficam FORA de
#: qualquer soma e são reportados à parte, porque somá-los infla o número com
#: mortes que nenhuma campanha atual poderia ter evitado — o câncer de colo que
#: mata em 2024 vem de infecção de vinte anos antes.
LATENCIA_LONGA: tuple[tuple[str, str, str], ...] = (
    ("Câncer de colo do útero (HPV)", "substr(causabas,1,3) = 'C53'", "HPV no PNI desde 2014; latência de décadas"),
    ("Hepatite B crônica/cirrose",    "causabas IN ('B180','B181')",  "fração atribuível ao HBV não separável na CID"),
    ("Câncer de fígado",              "substr(causabas,1,3) = 'C22'", "fração atribuível ao HBV não separável na CID"),
)


def _predicado_oficial() -> str:
    """SQL do subgrupo 1.1 com a idade que a lista manda usar em cada versão."""
    c04 = ",".join(f"'{c}'" for c in OFICIAL_0A4)
    c04_4 = ",".join(f"'{c}'" for c in OFICIAL_0A4_4)
    c574 = ",".join(f"'{c}'" for c in OFICIAL_5A74)
    c574_4 = ",".join(f"'{c}'" for c in OFICIAL_5A74_4)
    return (f"((idade_anos < 5 AND (substr(causabas,1,3) IN ({c04}) OR causabas IN ({c04_4})))"
            f" OR (idade_anos BETWEEN 5 AND 74 AND (substr(causabas,1,3) IN ({c574})"
            f" OR causabas IN ({c574_4}))))")


def _predicado_ampliado(*, incluir_covid: bool = True, so_pni: bool = False) -> str:
    partes = [p for rot, p, disp in AMPLIADO
              if (incluir_covid or rot != "COVID-19")
              and (not so_pni or not disp.startswith("FORA"))]
    return "(" + " OR ".join(f"({p})" for p in partes) + ")"


def carregar(con: duckdb.DuckDBPyConnection, anos: list[int]) -> None:
    """Agrega o SIM em ano × mês × município × CID-10 de 4 caracteres.

    O grão de 4 caracteres é o ponto: `_sim_obitos.criar_obitos_t` trunca em 3,
    e três caracteres perdem G00.0 (meningite por Haemophilus, que a lista
    oficial cita nominalmente), P35.0, P35.3, A40.3 e B34.2 — o COVID-19 do SIM
    brasileiro. Metade da pergunta some no truncamento.

    A regra de "o que conta como óbito" continua sendo a de `_sim_obitos`:
    mesma união de fontes, mesmo filtro de óbito fetal, mesma decodificação de
    IDADE. Só a causa é preservada inteira.
    """
    union = sql_uniao_fontes(anos)
    con.execute(f"""
        CREATE OR REPLACE TABLE obitos4 AS
        WITH t AS (
            SELECT lpad(DTOBITO, 8, '0')                            AS dt,
                   COALESCE(NULLIF(trim(CODMUNRES), ''), '000000')  AS municipio_cod,
                   upper(COALESCE(trim(CAUSABAS), ''))              AS causabas,
                   trim(COALESCE(SEXO, ''))                         AS sexo_raw,
                   trim(COALESCE(IDADE, ''))                        AS idade_raw
            FROM ({union})
            WHERE COALESCE(NULLIF(trim(TIPOBITO), ''), '2') <> '1'
        ), d AS (
            SELECT TRY_CAST(substr(dt, 5, 4) AS SMALLINT) AS ano,
                   TRY_CAST(substr(dt, 3, 2) AS SMALLINT) AS mes,
                   municipio_cod, causabas,
                   CASE sexo_raw WHEN '1' THEN 'M' WHEN '2' THEN 'F'
                                 WHEN 'M' THEN 'M' WHEN 'F' THEN 'F' ELSE 'I' END AS sexo,
                   CASE
                     WHEN idade_raw = '' THEN NULL
                     WHEN substr(lpad(idade_raw,3,'0'),1,1) = '4'
                       THEN TRY_CAST(substr(lpad(idade_raw,3,'0'),2,2) AS INT)
                     WHEN substr(lpad(idade_raw,3,'0'),1,1) = '5'
                       THEN 100 + COALESCE(TRY_CAST(substr(lpad(idade_raw,3,'0'),2,2) AS INT), 0)
                     WHEN substr(lpad(idade_raw,3,'0'),1,1) IN ('0','1','2','3') THEN 0
                     ELSE NULL END                                  AS idade_anos
            FROM t
        )
        SELECT ano, mes, municipio_cod, causabas, sexo, idade_anos, count(*)::INT AS obitos
        FROM d
        WHERE ano IN ({','.join(str(a) for a in anos)}) AND mes BETWEEN 1 AND 12
        GROUP BY ALL
    """)


def guardas(con: duckdb.DuckDBPyConnection, anos: list[int]) -> None:
    """Aborta se um pressuposto do rótulo deixou de valer.

    Guarda que só avisa é guarda que ninguém lê. Estas param o script, porque
    cada uma invalida um número publicado, não o deixa apenas impreciso.
    """
    u07 = con.execute("SELECT COALESCE(sum(obitos),0) FROM obitos4 "
                      "WHERE substr(causabas,1,3) = 'U07'").fetchone()[0]
    b342 = con.execute("SELECT COALESCE(sum(obitos),0) FROM obitos4 "
                       "WHERE causabas = 'B342'").fetchone()[0]
    if u07:
        raise SystemExit(
            f"GUARDA: apareceram {u07:,} óbitos em U07. O SIM brasileiro codificava "
            "COVID-19 como B34.2 e nunca usou U07; se recodificou, o predicado de "
            "COVID-19 em AMPLIADO precisa mudar junto — senão a pandemia é contada "
            "duas vezes ou nenhuma.")
    if not b342:
        raise SystemExit("GUARDA: zero óbitos em B34.2. A rota de COVID-19 quebrou.")

    faltando = set(anos) - set(con.execute("SELECT DISTINCT ano FROM obitos4").df().ano)
    if faltando:
        raise SystemExit(f"GUARDA: sem óbito nenhum em {sorted(faltando)} — coleta incompleta.")

    # Cada código da lista oficial precisa ser CID-10 de verdade. Erro de
    # digitação numa lista transcrita à mão não aparece como erro: aparece como
    # zero óbitos, que é indistinguível de "a doença não matou ninguém".
    dim = MARTS / "dim_cid10_categoria.parquet"
    if dim.exists():
        validos = set(con.execute(f"SELECT causabas_3 FROM '{dim}'").df().causabas_3)
        declarados = (set(OFICIAL_0A4) | set(OFICIAL_5A74)
                      | {c[:3] for c in OFICIAL_0A4_4 + OFICIAL_5A74_4})
        invalidos = sorted(declarados - validos)
        if invalidos:
            raise SystemExit(
                f"GUARDA: {invalidos} não existem em dim_cid10_categoria. Código "
                "inexistente devolve zero óbitos, que se lê como 'ninguém morreu'.")


def tabela_oficial(con, anos_cons) -> pd.DataFrame:
    faixa = ",".join(str(a) for a in anos_cons)
    cids_5a74 = ",".join(f"'{c}'" for c in OFICIAL_5A74)
    return con.execute(f"""
        SELECT ano,
               sum(CASE WHEN {_predicado_oficial()} THEN obitos ELSE 0 END)::INT AS oficial_1_1,
               sum(CASE WHEN idade_anos >= 75
                         AND (substr(causabas,1,3) IN ({cids_5a74}) OR causabas = 'G000')
                    THEN obitos ELSE 0 END)::INT                                 AS mesmos_cids_75_mais,
               sum(obitos)::INT                                                  AS obitos_totais,
               round(10000.0 * sum(CASE WHEN {_predicado_oficial()} THEN obitos ELSE 0 END)
                     / sum(obitos), 2)                                           AS por_10mil_obitos
        FROM obitos4 WHERE ano IN ({faixa}) GROUP BY 1 ORDER BY 1
    """).df()


def tabela_ampliado(con, anos_todos) -> pd.DataFrame:
    sel = ",\n".join(f'sum(CASE WHEN {pred} THEN obitos ELSE 0 END)::INT AS "{rot}"'
                     for rot, pred, _ in AMPLIADO + LATENCIA_LONGA)
    largo = con.execute(f"SELECT ano, {sel} FROM obitos4 GROUP BY 1 ORDER BY 1").df()
    d = largo.set_index("ano").T.reset_index().rename(columns={"index": "causa"})
    disp = {r: v for r, _, v in AMPLIADO + LATENCIA_LONGA}
    d.insert(1, "disponibilidade", d.causa.map(disp))
    d.insert(2, "grupo", ["ampliado"] * len(AMPLIADO) + ["latencia_longa"] * len(LATENCIA_LONGA))
    cons = [a for a in anos_todos if a in ANOS_CONSOLIDADOS]
    d.insert(3, f"total_{cons[0]}_{cons[-1]}", d[cons].sum(axis=1))
    return d


def tabela_idade(con, anos_cons) -> pd.DataFrame:
    faixa = ",".join(str(a) for a in anos_cons)
    return con.execute(f"""
        SELECT CASE WHEN idade_anos IS NULL THEN 'idade ignorada'
                    WHEN idade_anos < 5    THEN '0-4 anos'
                    WHEN idade_anos <= 74  THEN '5-74 anos'
                    ELSE '75 anos ou mais' END                                   AS faixa,
               sum(CASE WHEN causabas = 'B342' THEN obitos ELSE 0 END)::INT      AS covid,
               sum(CASE WHEN causabas <> 'B342'
                         AND {_predicado_ampliado(incluir_covid=False)}
                    THEN obitos ELSE 0 END)::INT                                 AS ampliado_sem_covid,
               sum(CASE WHEN {_predicado_oficial()} THEN obitos ELSE 0 END)::INT AS lista_oficial
        FROM obitos4 WHERE ano IN ({faixa}) GROUP BY 1 ORDER BY 1
    """).df()


def tabela_teto_codificacao(con, anos_cons) -> pd.DataFrame:
    """Quanto da causa infecciosa chega ao SIM sem agente etiológico.

    Não é digressão: é o limite superior do que qualquer estudo de
    imunoprevenção consegue medir no Brasil por causa básica.
    """
    faixa = ",".join(str(a) for a in anos_cons)
    linhas = [
        ("J18 pneumonia, agente não especificado", "substr(causabas,1,3) = 'J18'"),
        ("J15 outra pneumonia bacteriana",         "substr(causabas,1,3) = 'J15'"),
        ("J13 pneumonia POR pneumococo",           "substr(causabas,1,3) = 'J13'"),
        ("J14 pneumonia POR Haemophilus",          "substr(causabas,1,3) = 'J14'"),
        ("A41.9 septicemia não especificada",      "causabas = 'A419'"),
        ("A40.3 septicemia POR pneumococo",        "causabas = 'A403'"),
        ("R00-R99 causas mal definidas",           "substr(causabas,1,1) = 'R'"),
    ]
    sql = " UNION ALL ".join(
        f"SELECT '{rot}' AS codigo, sum(CASE WHEN {p} THEN obitos ELSE 0 END)::INT AS obitos "
        f"FROM obitos4 WHERE ano IN ({faixa})" for rot, p in linhas)
    return con.execute(f"SELECT * FROM ({sql}) ORDER BY obitos DESC").df()


def cruzamento_influenza(con) -> tuple[pd.DataFrame, dict[int, float]]:
    """Óbitos por influenza em 60+ contra doses de influenza por 60+, por UF.

    CRITÉRIO DECLARADO ANTES DE OLHAR: |ρ| < 0,30, ou sinal diferente entre
    2023 e 2024, é ausência de sinal — e ausência de sinal é o resultado, não
    um convite para procurar outro recorte.
    """
    from scipy.stats import spearmanr  # noqa: PLC0415

    con.execute(f"CREATE OR REPLACE VIEW mun AS SELECT * FROM '{MARTS / 'dim_municipio.parquet'}'")
    con.execute(f"CREATE OR REPLACE VIEW popi AS SELECT * FROM '{REFS / 'pop_idade_uf_ano.parquet'}'")
    con.execute(f"CREATE OR REPLACE VIEW pni AS SELECT * FROM '{MARTS / 'mart_vacinacao_uf_mes.parquet'}'")
    d = con.execute("""
        WITH ob AS (
          SELECT m.uf_sigla, o.ano, sum(o.obitos)::INT AS obitos
          FROM obitos4 o JOIN mun m USING (municipio_cod)
          WHERE substr(o.causabas,1,3) IN ('J09','J10','J11')
            AND o.idade_anos >= 60 AND o.ano IN (2023, 2024)
          GROUP BY 1,2),
        pop AS (SELECT uf_sigla, ano, sum(populacao) AS pop60 FROM popi
                WHERE faixa IN ('60-74','75+') AND ano IN (2023,2024) GROUP BY 1,2),
        dose AS (SELECT uf_sigla, CAST(substr(competencia,1,4) AS INT) AS ano, sum(doses) AS inf3
                 FROM pni WHERE imunobiologico = 'INF3'
                   AND substr(competencia,1,4) IN ('2023','2024') GROUP BY 1,2)
        SELECT ob.uf_sigla, ob.ano, ob.obitos, pop.pop60, dose.inf3,
               round(1e5*ob.obitos/pop.pop60, 2) AS obitos_100k_60mais,
               round(1.0*dose.inf3/pop.pop60, 3) AS doses_por_60mais
        FROM ob JOIN pop USING (uf_sigla, ano) JOIN dose USING (uf_sigla, ano)
        ORDER BY 2, 6 DESC
    """).df()
    rhos = {}
    for ano in (2023, 2024):
        s = d[d.ano == ano]
        rhos[ano] = float(spearmanr(s.doses_por_60mais, s.obitos_100k_60mais).statistic)
    return d, rhos


def eventos(con) -> dict[str, pd.DataFrame]:
    """Os quatro recortes em que o número é grande o bastante para significar algo."""
    con.execute(f"CREATE OR REPLACE VIEW mun AS SELECT * FROM '{MARTS / 'dim_municipio.parquet'}'")
    febre_amarela = con.execute("""
        SELECT o.ano, m.uf_sigla, sum(o.obitos)::INT AS obitos,
               round(avg(o.idade_anos), 1) AS idade_media,
               round(100.0*sum(CASE WHEN o.sexo='M' THEN o.obitos ELSE 0 END)
                     / sum(o.obitos), 1) AS pct_masculino
        FROM obitos4 o JOIN mun m USING (municipio_cod)
        WHERE substr(o.causabas,1,3) = 'A95' AND o.ano BETWEEN 2016 AND 2019
        GROUP BY 1,2 HAVING sum(o.obitos) >= 5 ORDER BY 1, 3 DESC""").df()
    sarampo = con.execute("""
        SELECT o.ano, sum(o.obitos)::INT AS obitos,
               sum(CASE WHEN o.idade_anos = 0 THEN o.obitos ELSE 0 END)::INT AS menores_de_1_ano,
               string_agg(DISTINCT m.uf_sigla, ' ') AS ufs
        FROM obitos4 o JOIN mun m USING (municipio_cod)
        WHERE substr(o.causabas,1,3) = 'B05' GROUP BY 1 ORDER BY 1""").df()
    coqueluche = con.execute("""
        SELECT ano, sum(obitos)::INT AS obitos,
               sum(CASE WHEN idade_anos = 0 THEN obitos ELSE 0 END)::INT AS menores_de_1_ano
        FROM obitos4 WHERE substr(causabas,1,3) = 'A37' GROUP BY 1 ORDER BY 1""").df()
    influenza = con.execute("""
        SELECT ano,
               sum(CASE WHEN idade_anos < 5 THEN obitos ELSE 0 END)::INT               AS f_0_4,
               sum(CASE WHEN idade_anos BETWEEN 5 AND 59 THEN obitos ELSE 0 END)::INT  AS f_5_59,
               sum(CASE WHEN idade_anos BETWEEN 60 AND 74 THEN obitos ELSE 0 END)::INT AS f_60_74,
               sum(CASE WHEN idade_anos >= 75 THEN obitos ELSE 0 END)::INT             AS f_75_mais,
               sum(obitos)::INT                                                        AS total
        FROM obitos4 WHERE substr(causabas,1,3) IN ('J09','J10','J11')
        GROUP BY 1 ORDER BY 1""").df()
    covid = con.execute("""
        SELECT ano,
               sum(CASE WHEN idade_anos BETWEEN 5 AND 59 THEN obitos ELSE 0 END)::INT  AS f_5_59,
               sum(CASE WHEN idade_anos BETWEEN 60 AND 74 THEN obitos ELSE 0 END)::INT AS f_60_74,
               sum(CASE WHEN idade_anos >= 75 THEN obitos ELSE 0 END)::INT             AS f_75_mais,
               sum(obitos)::INT                                                        AS total
        FROM obitos4 WHERE causabas = 'B342' AND ano >= 2021 GROUP BY 1 ORDER BY 1""").df()
    return {"febre_amarela": febre_amarela, "sarampo": sarampo, "coqueluche": coqueluche,
            "influenza_por_idade": influenza, "covid_pos_vacina": covid}


def main() -> None:
    ap = argparse.ArgumentParser(description="Óbitos por causas com vacina disponível, SIM 2015+.")
    ap.add_argument("--sem-cruzamento", action="store_true",
                    help="pula o cruzamento ecológico com o PNI (dispensa scipy e os marts)")
    ap.add_argument("--sem-registro", action="store_true",
                    help="não grava em data/marts/achados.json")
    args = ap.parse_args()

    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    anos_cons = list(ANOS_CONSOLIDADOS)
    anos_todos = sorted(set(anos_cons) | set(ANOS_PRELIMINARES))
    SAIDA.mkdir(parents=True, exist_ok=True)

    con = duckdb.connect()
    con.execute("PRAGMA threads=6")
    print(f"[sim] agregando {anos_todos[0]}-{anos_todos[-1]} em CID-10 de 4 caracteres...", flush=True)
    carregar(con, anos_todos)
    guardas(con, anos_todos)
    n = con.execute("SELECT sum(obitos) FROM obitos4").fetchone()[0]
    print(f"[sim] {int(n):,} obitos nao fetais. Guardas OK.\n", flush=True)

    ofic = tabela_oficial(con, anos_cons)
    amp = tabela_ampliado(con, anos_todos)
    idade = tabela_idade(con, anos_cons)
    teto = tabela_teto_codificacao(con, anos_cons)
    evt = eventos(con)

    print("== 1. A lista oficial (subgrupo 1.1), por ano ==")
    print(ofic.to_string(index=False), "\n")
    print("== 2. Conjunto ampliado: causas com vacina, por ano ==")
    print(amp.to_string(index=False), "\n")
    print("== 3. Estrutura etaria - o que a lista nao alcanca ==")
    print(idade.to_string(index=False), "\n")
    print("== 4. Teto de codificacao: o agente nao e registrado ==")
    print(teto.to_string(index=False), "\n")
    for nome, df in evt.items():
        print(f"== 5. {nome} ==")
        print(df.to_string(index=False), "\n")

    tabelas = {"lista_oficial_por_ano": ofic, "ampliado_por_causa_ano": amp,
               "estrutura_etaria": idade, "teto_codificacao": teto, **evt}

    rhos: dict[int, float] = {}
    if not args.sem_cruzamento:
        cruz, rhos = cruzamento_influenza(con)
        tabelas["influenza_x_doses_uf"] = cruz
        print("== 6. Cruzamento influenza x doses (criterio: |rho|<0,30 ou troca de sinal = nulo) ==")
        print(cruz.to_string(index=False))
        for ano, r in rhos.items():
            print(f"   rho Spearman {ano}: {r:+.3f}")
        nulo = (min(rhos.values()) < 0 < max(rhos.values())
                or min(abs(r) for r in rhos.values()) < 0.30)
        print(f"   veredito: {'NULO' if nulo else 'SINAL'}\n")

    for nome, df in tabelas.items():
        df.to_csv(SAIDA / f"imunopreveniveis_{nome}.csv", index=False, encoding="utf-8")
    print(f"[saida] {len(tabelas)} CSV em {SAIDA}", flush=True)

    if args.sem_registro:
        return
    total_col = f"total_{anos_cons[0]}_{anos_cons[-1]}"
    linha_ofic = int(ofic.oficial_1_1.sum())
    amp_sem_covid = int(amp.loc[(amp.grupo == "ampliado") & (amp.causa != "COVID-19"),
                                total_col].sum())
    j18 = int(teto.loc[teto.codigo.str.startswith("J18"), "obitos"].iloc[0])
    j13 = int(teto.loc[teto.codigo.str.startswith("J13"), "obitos"].iloc[0])
    fontes = ["dim_municipio", "mart_vacinacao_uf_mes", "dim_cid10_categoria"]
    registrar("imuno_razao_ampliado_sobre_oficial", amp_sem_covid / linha_ofic, fontes=fontes,
              descricao="óbitos do conjunto ampliado sem COVID-19 divididos pelos do subgrupo "
                        "1.1 da Lista Brasileira, 2015-2024 — quanto a lista oficial deixa de fora")
    registrar("imuno_pneumonia_sem_agente_por_pneumococo", j18 / j13, fontes=fontes,
              descricao="óbitos por pneumonia sem agente (J18) para cada um atribuído ao "
                        "pneumococo (J13), 2015-2024 — teto de codificação do SIM")
    for ano, r in rhos.items():
        registrar(f"imuno_influenza_x_doses_uf_{ano}", r, fontes=fontes,
                  descricao=f"ρ de Spearman entre doses de influenza por habitante de 60+ e "
                            f"óbitos por influenza em 60+, por UF, {ano} — resultado nulo")
    print("[done] analise de mortes imunopreveniveis concluida.", flush=True)


if __name__ == "__main__":
    main()
