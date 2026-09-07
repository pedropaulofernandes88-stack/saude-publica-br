"""
analise_neoplasias.py — mortalidade por neoplasias: idade, sexo, sítio e desigualdade
=====================================================================================

Levantamento das mortes por neoplasia maligna (CID-10 C00–C97) no SIM, com
quatro eixos de recorte: **idade**, **sítio do tumor**, **território** e
**posição social** (cor/raça, escolaridade, vulnerabilidade municipal).

O QUE ESTA ANÁLISE ACHOU, EM UMA FRASE
--------------------------------------
O câncer mata 26% mais brasileiros do que em 2015 e o risco de morrer de câncer
**caiu**: o crescimento é inteiramente demográfico. E onde a mortalidade medida
é MAIOR o município é mais rico — exceto no colo do útero, o único sítio comum
que inverte o gradiente e que é, justamente, o evitável por rastreamento.

TRÊS DECISÕES DE MÉTODO QUE MUDAM O RESULTADO
----------------------------------------------

1. **Padronizar por idade não é refinamento, é o achado.** A taxa bruta sobe
   19,7% entre 2015 e 2024 (101,8 → 121,9 por 100 mil) e a padronizada CAI 2,3%
   (123,0 → 120,2). Quem publica a bruta publica a pirâmide etária do Brasil
   com nome de epidemiologia. A decomposição de três termos (tamanho da
   população, estrutura etária, taxas específicas) está em `tab03` e é a forma
   honesta de dizer isso.

2. **O esqueleto completo antes da padronização.** Padronizar somando só os
   estratos COM óbito renormaliza os pesos para as faixas presentes e infla
   sítios raros — na primeira medição a laringe apareceu com 29,4/100 mil,
   quatro vezes o real, porque só as faixas idosas entravam na conta. Toda taxa
   por sítio aqui parte de um `CROSS JOIN` estrato × causa e conta zero como
   zero.

3. **Escolaridade no atestado é confundida por coorte, e a confusão INVERTE o
   sinal.** Os óbitos por câncer de quem não tem escolaridade têm idade mediana
   76 anos; os de superior completo, 67. Não é câncer mais precoce entre os
   instruídos — é que quem não estudou no Brasil é quem já é velho. Por isso o
   eixo escolaridade só aparece como **mortalidade proporcional dentro de faixa
   etária fixa** (30–69) e como local do óbito, nunca como idade ao morrer.

O QUE A ANÁLISE NÃO PODE AFIRMAR
---------------------------------
* **Não é incidência.** Mortalidade menor pode ser menos câncer, mais sobrevida
  ou menos diagnóstico — e nos municípios do quartil mais vulnerável 7,2% dos
  óbitos são de causa mal definida contra 4,1% no menos vulnerável. `tab08` traz
  a taxa corrigida por redistribuição pro-rata das mal definidas como
  sensibilidade: o gradiente encolhe, não some.
* **Cor/raça tem viés numerador-denominador.** No SIM é declarada por terceiro
  (família, serviço); no Censo é autodeclarada. As duas fontes não classificam a
  mesma pessoa do mesmo jeito, e a razão entre elas carrega esse erro.
* **2025 é preliminar** e fica fora de tudo (ver `_sim_obitos.ANOS_CONSOLIDADOS`).

O QUE A AUDITORIA DE 2026-09-07 MUDOU
--------------------------------------
O numerador saía de `mart_mortalidade_causa_municipio_faixa`, que agrupa em oito
faixas e **perde 241 óbitos** sem idade declarada; o denominador saía da projeção
IBGE de **2018**, anterior ao Censo 2022, que superestima a população em 5,8% —
e de forma desigual por idade, o que desloca taxa padronizada. Havia ainda três
bases de denominador convivendo no mesmo artigo (projeção 2018, Censo municipal
e Censo por cor/raça), com a Tabela de UF e a de quartil em escalas diferentes.

Agora o numerador é derivado do SIM cru com **idade exata** (os 241 voltam, por
redistribuição pro-rata dentro do ano e da causa) e o denominador é a **Projeção
revisão 2024**, por idade simples, reconciliada com o Censo pela Pesquisa de
Pós-Enumeração. O eixo municipal usa forma do Censo e nível da projeção, de modo
que todas as tabelas ficam na mesma escala. Ver `pipeline_projecao_ibge.py`.

O achado não mudou de sinal: a padronizada caía 4,4% e cai 2,3%; a decomposição
atribuía −19,9% ao risco e atribui −10,6%; os seis sítios que invertem o
gradiente do IVS são **os mesmos seis**.

FONTES
------
* SIM/DataSUS pela união canônica de `_sim_obitos.sql_uniao_fontes` — `.dbc` por
  UF (2015–2021, 2024) e CSV nacional (2022–2023), com idade exata.
* `data/raw/SIM/DO22OPEN.csv`, `DO23OPEN.csv` — microdado com as variáveis
  sociais (RACACOR, ESC2010, LOCOCOR), que o recorte `.dbc` dos demais anos
  **não** traz. Por isso todo eixo social é 2022–2023.
* `data/refs/pop_proj2024_uf_ano_idade.parquet` — denominador oficial pós-Censo,
  por UF × ano × idade simples × sexo (`pipeline_projecao_ibge.py`).
* `dim_pop_padrao` — padrão Brasil/Censo 2022; `PADRAO_OMS` — padrão mundial da
  OMS 2000–2025, que torna a série comparável com INCA, IARC e GLOBOCAN.
* SIDRA t/9606 — população por cor/raça × sexo × idade, Censo 2022. Baixada uma
  vez e cacheada em `data/refs/pop_raca_idade_sexo_2022.parquet`.
* `mart_mortalidade_causa_municipio_faixa` — só para as séries de qualidade de
  registro (causa mal definida e C80), que não precisam de grão etário.

Uso: .venv311/Scripts/python scripts/analise_neoplasias.py
"""
from __future__ import annotations

import itertools
import sys
from pathlib import Path

import duckdb
import numpy as np
import pandas as pd

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parents[1]
MARTS = ROOT / "data" / "marts"
REFS = ROOT / "data" / "refs"
RAW = ROOT / "data" / "raw" / "SIM"
SAIDA = ROOT / "data" / "analises" / "neoplasias"

#: Capítulo II da CID-10 é C00–D48, mas D00–D48 são in situ, benignas e de
#: comportamento incerto — outra doença. "Morte por câncer" aqui é sempre
#: C00–C97, o recorte de neoplasia MALIGNA usado por INCA, IARC e OMS. A
#: diferença não é cosmética: D00–D48 responde por 2,0% dos óbitos do capítulo
#: (45.953 no período, medidos em `tab00_base`), e incluí-la faria a série do
#: projeto divergir de qualquer comparação externa. O valor estava aqui como
#: "~1,4%", estimado e nunca medido, até a revisão de 2026-09-04 — que é o
#: motivo de todo número do artigo ter de existir numa tabela.
CID_MALIGNA = ("C00", "C97")

#: Anos com microdado social em disco. Ver `_sim_obitos.ANOS_CSV` — 2024 saiu de
#: lá porque o `DO24OPEN.csv` trazia 6,9% menos óbitos que os `.dbc`; usar esse
#: arquivo para o eixo social importaria o mesmo buraco, e o buraco não é
#: uniforme entre UFs.
ANOS_SOCIAL = (2022, 2023)

#: Janela recente para os recortes territoriais e de sítio. Três anos dão massa
#: para categoria CID rara sem misturar o choque da pandemia no numerador.
ANOS_RECENTE = (2022, 2024)

RACAS = {"1": "Branca", "2": "Preta", "3": "Amarela", "4": "Parda", "5": "Indígena"}
ESCOL = {"0": "0 Sem escolaridade", "1": "1 Fundamental I", "2": "2 Fundamental II",
         "3": "3 Médio", "4": "4 Superior incompleto", "5": "5 Superior completo"}

#: Faixas da SIDRA agregadas nas sete faixas do projeto. `0-4` funde `<1` e
#: `1-4` porque o denominador por UF × ano não separa o primeiro ano de vida.
#: O `else` do CASE recolhe 75–79, 80–84, …, 100+ em `75+`.
SIDRA_FAIXA = {
    "0 a 4 anos": "0-4", "5 a 9 anos": "5-14", "10 a 14 anos": "5-14",
    "15 a 19 anos": "15-29", "20 a 24 anos": "15-29", "25 a 29 anos": "15-29",
    "30 a 34 anos": "30-44", "35 a 39 anos": "30-44", "40 a 44 anos": "30-44",
    "45 a 49 anos": "45-59", "50 a 54 anos": "45-59", "55 a 59 anos": "45-59",
    "60 a 64 anos": "60-74", "65 a 69 anos": "60-74", "70 a 74 anos": "60-74",
}

#: Ordem de exibição das faixas — alfabética coloca '5-14' depois de '45-59'.
ORDEM_FX = ("0-4", "5-14", "15-29", "30-44", "45-59", "60-74", "75+")

#: População padrão mundial da OMS (2000–2025), em grupos quinquenais, somando
#: 1.000.000. Ahmad OB, Boschi-Pinto C, Lopez AD, Murray CJL, Lozano R, Inoue M.
#: *Age standardization of rates: a new WHO standard*. Genebra: OMS; 2001 (GPE
#: Discussion Paper 31). Valores conforme a tabela publicada pelo SEER/NCI.
#:
#: Existe aqui, e não em `data/refs/`, porque é constante publicada e fechada:
#: um arquivo poderia divergir da referência sem que nada avisasse, e a chave é
#: a idade inicial do grupo, que o código usa diretamente. Os grupos de 90 em
#: diante são fundidos porque a projeção do IBGE termina em "90 ou mais".
PADRAO_OMS = {
    0: 88_569, 5: 86_870, 10: 85_970, 15: 84_670, 20: 82_171, 25: 79_272,
    30: 76_073, 35: 71_475, 40: 65_877, 45: 60_379, 50: 53_681, 55: 45_484,
    60: 37_187, 65: 29_590, 70: 22_092, 75: 15_195, 80: 9_097, 85: 4_398,
    90: 1_500 + 400 + 50,
}

#: Decodifica o campo IDADE do SIM (unidade no 1º dígito) em anos completos.
#: Mesma regra de `_sim_obitos.criar_obitos_t`; repetida aqui porque este script
#: lê o CSV cru, e não `obitos_t`. Se uma das duas mudar, os totais divergem.
SQL_IDADE = """
 case when {c}='' or {c} is null then null
   when substr(lpad({c},3,'0'),1,1)='4' then try_cast(substr(lpad({c},3,'0'),2,2) as int)
   when substr(lpad({c},3,'0'),1,1)='5' then 100+coalesce(try_cast(substr(lpad({c},3,'0'),2,2) as int),0)
   when substr(lpad({c},3,'0'),1,1) in ('0','1','2','3') then 0 else null end"""

SQL_FAIXA = """
 case when {c} < 5 then '0-4' when {c} < 15 then '5-14' when {c} < 30 then '15-29'
      when {c} < 45 then '30-44' when {c} < 60 then '45-59' when {c} < 75 then '60-74'
      else '75+' end"""


def _sql_ordem(coluna: str) -> str:
    casos = " ".join(f"when '{f}' then {i}" for i, f in enumerate(ORDEM_FX))
    return f"case {coluna} {casos} end"


def taxa_padronizada_ic(obitos, pessoas_ano, peso, por: float = 1e5
                        ) -> tuple[float, float, float]:
    """Taxa padronizada pelo método direto com IC95% de Fay–Feuer.

    POR QUE ESTE INTERVALO, E NÃO O NORMAL
    --------------------------------------
    A aproximação normal exige contagem grande em CADA estrato, e aqui há
    estratos com dezenas de óbitos: o câncer de cólon entre pessoas indígenas
    soma 28 mortes no biênio, contra 18.904 entre brancas. Uma razão de 5x entre
    duas taxas, uma delas apoiada em 28 eventos, não é um achado até que se saiba
    a largura do intervalo — e com o normal ela sairia simétrica e estreita
    demais.

    Fay & Feuer (1997) generalizam para a taxa padronizada o mesmo intervalo
    gamma/Poisson exato que `pipeline_v2.py` já usa na taxa bruta, tratando a
    soma ponderada como uma gama com o peso máximo corrigindo a cauda superior.
    É o intervalo adotado pelo SEER/NCI para taxas de câncer, o que também torna
    esta série comparável em método com a literatura oncológica.

    `obitos`, `pessoas_ano` e `peso` são vetores alinhados por estrato etário —
    `peso` é a população padrão da faixa, não normalizada.
    """
    from scipy.stats import gamma as gamma_dist

    d = np.asarray(obitos, dtype=float)
    n = np.asarray(pessoas_ano, dtype=float)
    w = np.asarray(peso, dtype=float)
    w = w / w.sum()

    taxa = float((w * d / n).sum())
    var = float(((w / n) ** 2 * d).sum())
    if taxa <= 0 or var <= 0:
        return 0.0, 0.0, float(gamma_dist.ppf(0.975, 1) * (w / n).max() * por)
    w_max = float((w / n).max())
    inf = gamma_dist.ppf(0.025, taxa**2 / var, scale=var / taxa)
    sup = gamma_dist.ppf(0.975, (taxa + w_max) ** 2 / (var + w_max**2),
                         scale=(var + w_max**2) / (taxa + w_max))
    return taxa * por, float(inf) * por, float(sup) * por


def razao_taxas_ic(d1, n1, d2, n2, alfa: float = 0.05) -> tuple[float, float, float]:
    """Razão entre duas taxas de Poisson, com IC exato condicional.

    `d1/n1` é a taxa do grupo no numerador (aqui, os idosos) e `d2/n2` a do
    denominador (os jovens). Devolve (razão, inferior, superior).

    POR QUE O INTERVALO É EXATO, E NÃO NORMAL
    ------------------------------------------
    Condicionando no total de óbitos T = d1 + d2, o número de óbitos do primeiro
    grupo é **binomial** com T ensaios e probabilidade p = n1·λ1 / (n1·λ1 +
    n2·λ2). Isso é exato, não aproximação — e a razão sai de p por

        RR = p/(1−p) · n2/n1

    Basta então um intervalo exato de Clopper–Pearson para p e transformá-lo. O
    método não depende de contagem grande, o que importa aqui: por sítio, alguns
    capítulos têm poucas centenas de óbitos na faixa jovem, e a aproximação
    normal do log da razão devolveria intervalo simétrico e estreito demais.

    É o mesmo princípio do intervalo de Fay–Feuer usado nas taxas padronizadas:
    condicionar no que é fixo e usar a distribuição exata do que varia.
    """
    from scipy.stats import beta

    d1, d2 = float(d1), float(d2)
    total = d1 + d2
    if total == 0 or n1 <= 0 or n2 <= 0:
        return float("nan"), float("nan"), float("nan")
    escala = n2 / n1
    razao = (d1 / n1) / (d2 / n2) if d2 > 0 else float("inf")
    p_inf = 0.0 if d1 == 0 else float(beta.ppf(alfa / 2, d1, total - d1 + 1))
    p_sup = 1.0 if d1 == total else float(beta.ppf(1 - alfa / 2, d1 + 1, total - d1))
    inf = p_inf / (1 - p_inf) * escala if p_inf < 1 else float("inf")
    sup = p_sup / (1 - p_sup) * escala if p_sup < 1 else float("inf")
    return razao, inf, sup


def escrever(df: pd.DataFrame, nome: str) -> pd.DataFrame:
    SAIDA.mkdir(parents=True, exist_ok=True)
    df.to_csv(SAIDA / f"{nome}.csv", index=False, encoding="utf-8")
    print(f"[csv] {nome}: {len(df):,} linhas")
    return df


def pop_raca(con: duckdb.DuckDBPyConnection) -> None:
    """População por cor/raça × sexo × faixa (Censo 2022), da SIDRA t/9606.

    Cacheia em `data/refs/`. É o ÚNICO denominador oficial por cor/raça com grão
    etário; sem ele o eixo racial vira mortalidade proporcional, que responde a
    outra pergunta. A guarda de 200 milhões existe porque a API do SIDRA devolve
    HTTP 200 com recorte parcial quando um id de categoria é inválido — resposta
    curta e bem formada é o modo silencioso de errar aqui.
    """
    destino = REFS / "pop_raca_idade_sexo_2022.parquet"
    if not destino.exists():
        import requests
        idades = ("93070,93084,93085,93086,93087,93088,93089,93090,93091,93092,"
                  "93093,93094,93095,93096,93097,93098,49108,49109,60040,60041,6653")
        url = ("https://servicodados.ibge.gov.br/api/v3/agregados/9606/periodos/2022"
               "/variaveis/93?localidades=N1[all]&classificacao=86[2776,2777,2778,2779,2780]"
               f"|287[{idades}]|2[4,5]")
        print("[sidra] baixando população por cor/raça × sexo × idade (t/9606)…")
        r = requests.get(url, timeout=180)
        if r.status_code != 200:
            raise SystemExit(f"SIDRA t/9606: HTTP {r.status_code} — sem denominador por "
                             "cor/raça o eixo racial não pode ser calculado.")
        linhas = []
        for var in r.json():
            for res in var["resultados"]:
                d = {c["nome"]: list(c["categoria"].values())[0] for c in res["classificacoes"]}
                for s in res["series"]:
                    linhas.append({**d, "valor": s["serie"]["2022"]})
        df = pd.DataFrame(linhas)
        df["valor"] = pd.to_numeric(df["valor"], errors="coerce")
        if df["valor"].sum() < 200e6:
            raise SystemExit(f"SIDRA t/9606 devolveu {df['valor'].sum():,.0f} pessoas — "
                             "o Censo 2022 tem 203 milhões; recorte incompleto.")
        df.to_parquet(destino)
        print(f"[sidra] {destino.name}: {df['valor'].sum():,.0f} pessoas")

    mapa = ", ".join(f"'{k}':'{v}'" for k, v in SIDRA_FAIXA.items())
    con.execute(f"""create or replace table pop_raca as
      select "Cor ou raça" raca,
             case Sexo when 'Homens' then 'M' else 'F' end sexo,
             coalesce(map_extract(map {{{mapa}}}, Idade)[1], '75+') fx,
             sum(valor) pop
      from '{destino.as_posix()}' group by 1,2,3""")


def _sql_faixa7(coluna: str) -> str:
    """As sete faixas do projeto, a partir de idade em anos completos."""
    return f"""case when {coluna} < 5 then '0-4' when {coluna} < 15 then '5-14'
        when {coluna} < 30 then '15-29' when {coluna} < 45 then '30-44'
        when {coluna} < 60 then '45-59' when {coluna} < 75 then '60-74'
        else '75+' end"""


def _sql_quinquenal(coluna: str) -> str:
    """Grupos quinquenais até 90 ou mais, o grão do padrão mundial da OMS."""
    return f"case when {coluna} >= 90 then 90 else ({coluna} / 5)::int * 5 end"


def obitos_idade_exata(con: duckdb.DuckDBPyConnection) -> None:
    """`ob_uf_idade` — óbitos por UF, ano, sexo, categoria da CID e IDADE EXATA.

    POR QUE NÃO SAI MAIS DO MART DE FAIXA
    --------------------------------------
    `mart_mortalidade_causa_municipio_faixa` traz o óbito já agrupado em oito
    faixas, três delas de quinze anos e a última aberta em 75. Auditado em
    2026-09-07, ele também **perde 241 óbitos** por neoplasia maligna na década
    — os que não têm idade declarada, que não cabem em faixa nenhuma e somem sem
    aviso (0,0105% da série, e a reconstrução a partir da fonte devolve
    exatamente 2.293.075, que é o total do mart municipal).

    Derivar daqui resolve as duas coisas de uma vez: recupera os 241 por
    redistribuição pro-rata dentro do ano, e devolve a idade exata, sem a qual
    não existe nem grupo quinquenal nem o recorte de 30 a 69 anos da OMS.

    A união das fontes vem de `_sim_obitos.sql_uniao_fontes`, que é a definição
    única de "o que conta como óbito" neste projeto — este script escolhe o
    agrupamento, nunca a regra.
    """
    sys.path.insert(0, str(ROOT / "scripts"))
    from _sim_obitos import ANOS_CONSOLIDADOS, sql_uniao_fontes

    uniao = sql_uniao_fontes(list(ANOS_CONSOLIDADOS))
    a0, a1 = ANOS_CONSOLIDADOS[0], ANOS_CONSOLIDADOS[-1]
    con.execute(f"""create table ob_bruto as
      with t as (
        select lpad(DTOBITO, 8, '0') dt,
               upper(coalesce(trim(CAUSABAS), '')) cb,
               trim(coalesce(SEXO, '')) sx,
               coalesce(nullif(trim(CODMUNRES), ''), '000000') mun,
               {SQL_IDADE.format(c="trim(coalesce(IDADE,''))")} ia
        from ({uniao})
        where coalesce(nullif(trim(TIPOBITO), ''), '2') <> '1')
      select try_cast(substr(dt, 5, 4) as smallint) ano,
             substr(cb, 1, 3) causabas_3,
             case sx when '1' then 'M' when '2' then 'F' else 'I' end sexo,
             mun municipio_cod, ia idade, count(*) ob
      from t
      where try_cast(substr(dt, 5, 4) as smallint) between {a0} and {a1}
      group by 1,2,3,4,5""")

    # Redistribuição pro-rata da idade ignorada, DENTRO do mesmo ano e da mesma
    # categoria de causa: o óbito sem idade entra na distribuição etária que os
    # óbitos com idade daquela causa e ano descrevem. É o tratamento que
    # `pipeline_v2` já usa; descartá-los seria perder 241 mortes em silêncio, e
    # atribuí-los a uma faixa qualquer seria pior.
    con.execute(f"""create table ob_uf_idade as
      with com as (select ano, causabas_3, sexo, municipio_cod, idade, ob
                   from ob_bruto where idade is not null),
      sem as (select ano, causabas_3, sum(ob) ob from ob_bruto
              where idade is null group by 1,2),
      -- A fração é DECIMAL, e não DOUBLE, por reprodutibilidade: a soma paralela
      -- de ponto flutuante não é associativa, e duas execuções do mesmo código
      -- sobre o mesmo dado devolviam contagens que diferiam em UM óbito quando
      -- o valor caía em cima do arredondamento. Medido em 2026-09-07 — quatro
      -- tabelas do artigo mudavam de bytes sem nada ter mudado no dado.
      peso as (select c.ano, c.causabas_3, c.sexo, c.municipio_cod, c.idade,
                      c.ob::decimal(18,6)
                        / sum(c.ob) over (partition by c.ano, c.causabas_3) fr
               from com c)
      select p.ano, coalesce(m.uf_sigla, u.uf_sigla, 'ND') uf_sigla, p.sexo,
             p.causabas_3, p.municipio_cod, p.idade,
             sum((c.ob + coalesce(s.ob, 0) * p.fr)::decimal(18,6)) ob
      from peso p
        join com c on c.ano=p.ano and c.causabas_3=p.causabas_3 and c.sexo=p.sexo
                  and c.municipio_cod=p.municipio_cod and c.idade=p.idade
        left join sem s on s.ano=p.ano and s.causabas_3=p.causabas_3
        left join '{(MARTS / 'dim_municipio.parquet').as_posix()}' m
               on m.municipio_cod = p.municipio_cod
        -- Códigos terminados em 0000 são "município ignorado" DENTRO de uma UF
        -- (330000 = Rio de Janeiro, município ignorado). Não existem no
        -- `dim_municipio`, e cair no 'ND' jogaria fora 378 óbitos por câncer que
        -- têm unidade da federação perfeitamente conhecida — os dois primeiros
        -- dígitos. Perder o município é inevitável; perder a UF, não.
        left join (select distinct substr(municipio_cod, 1, 2) uf2, uf_sigla
                   from '{(MARTS / 'dim_municipio.parquet').as_posix()}') u
               on u.uf2 = substr(p.municipio_cod, 1, 2)
      group by 1,2,3,4,5,6""")


def preparar(con: duckdb.DuckDBPyConnection) -> None:
    """Views e tabelas base: óbitos com idade exata, denominador e padrões."""
    con.execute("create view faixa as select * from "
                f"'{(MARTS / 'mart_mortalidade_causa_municipio_faixa.parquet').as_posix()}'")
    con.execute(f"create view cat as select * from '{(MARTS / 'dim_cid10_categoria.parquet').as_posix()}'")
    con.execute(f"create view ivs as select * from '{(MARTS / 'dim_ivs.parquet').as_posix()}'")
    con.execute("create view pop_mun_fx as select * from "
                f"'{(MARTS / 'dim_pop_faixa.parquet').as_posix()}'")

    # ── numerador ────────────────────────────────────────────────────────────
    obitos_idade_exata(con)
    con.execute(f"""create table ob_br as
      select ano, sexo, {_sql_faixa7('idade')} fx, causabas_3, sum(ob) ob
      from ob_uf_idade
      where causabas_3 between '{CID_MALIGNA[0]}' and '{CID_MALIGNA[1]}'
      group by 1,2,3,4""")

    # ── denominador ──────────────────────────────────────────────────────────
    # Projeção revisão 2024 do IBGE, por idade simples: a única série com o
    # total reconciliado com o Censo 2022 (via Pesquisa de Pós-Enumeração) E a
    # estrutura etária oficial. Ver `scripts/pipeline_projecao_ibge.py` para a
    # medida que descarta as outras duas candidatas.
    proj = REFS / "pop_proj2024_uf_ano_idade.parquet"
    if not proj.exists():
        raise SystemExit(
            f"{proj.relative_to(ROOT).as_posix()} não existe. Rode "
            "`python scripts/pipeline_projecao_ibge.py` — sem o denominador "
            "oficial pós-Censo a análise usaria a projeção de 2018, que é "
            "anterior ao Censo 2022 e superestima a população em 5,8%.")
    con.execute(f"create table pop_idade as select * from '{proj.as_posix()}'")
    con.execute(f"""create table pop_uf as
      select uf_sigla, ano, {_sql_faixa7('idade')} fx, sum(populacao) pop
      from pop_idade where sexo='T' group by 1,2,3""")
    con.execute("create table pop_br as select ano, fx, sum(pop) pop from pop_uf group by 1,2")

    # ── populações padrão ────────────────────────────────────────────────────
    # Duas, de propósito. A do Brasil mantém a série comparável com o resto da
    # plataforma; a da OMS torna as taxas comparáveis com INCA, IARC e qualquer
    # série internacional — que era limitação declarada da primeira versão.
    con.execute(f"""create table padrao as
      select case when faixa_etaria in ('<1','1-4') then '0-4' else faixa_etaria end fx,
             sum(populacao) w
      from '{(MARTS / 'dim_pop_padrao.parquet').as_posix()}' group by 1""")
    con.execute("create table padrao_mun as select faixa_etaria fx, populacao w from "
                f"'{(MARTS / 'dim_pop_padrao.parquet').as_posix()}'")
    con.execute("create table padrao_oms (g5 integer, w bigint)")
    con.executemany("insert into padrao_oms values (?,?)", list(PADRAO_OMS.items()))
    total_oms = con.execute("select sum(w) from padrao_oms").fetchone()[0]
    if total_oms != 1_000_000:
        raise SystemExit(f"padrão mundial da OMS soma {total_oms:,}, não 1.000.000.")


def serie_nacional(con: duckdb.DuckDBPyConnection) -> None:
    """tab01/tab02 — a série que separa 'mais mortes' de 'mais risco'."""
    escrever(con.execute(f"""
      with a as (select o.ano, o.fx, sum(o.ob) ob, any_value(p.pop) pop
                 from (select ano, fx, sum(ob) ob from ob_br group by 1,2) o
                 join pop_br p on p.ano=o.ano and p.fx=o.fx group by 1,2)
      select ano, fx faixa_etaria, round(ob)::bigint obitos, pop populacao,
             round(1e5*ob/pop, 2) taxa_100k
      from a order by {_sql_ordem('fx')}, ano""").df(), "tab02_taxa_por_faixa_ano")

    # As duas colunas de registro NÃO são enfeite: elas sustentam a leitura do
    # degrau de 2020 (§3.3 do manuscrito). Um degrau para baixo na mortalidade
    # por câncer seria trivialmente explicado por piora de codificação — câncer
    # que passa a ser registrado como causa mal definida. Sem a série ao lado,
    # a hipótese fica em aberto; com ela, é descartável, porque a imprecisão
    # CAIU no período. Afirmação de prosa que depende de número tem de trazer o
    # número junto.
    tab01 = escrever(con.execute(f"""
      with a as (select o.ano, o.fx, sum(o.ob) ob, any_value(p.pop) pop
                 from (select ano, fx, sum(ob) ob from ob_br group by 1,2) o
                 join pop_br p on p.ano=o.ano and p.fx=o.fx group by 1,2),
      reg as (select ano,
                100.0*sum(case when causabas_3 between 'R00' and 'R99' then obitos else 0 end)
                  /sum(obitos) maldef,
                100.0*sum(case when causabas_3='C80' then obitos else 0 end)
                  /nullif(sum(case when causabas_3 between 'C00' and 'C97'
                                   then obitos else 0 end),0) c80
              from faixa where not preliminar group by 1),
      -- Padronização pelo padrão MUNDIAL da OMS, em grupos quinquenais. É o que
      -- torna esta série comparável com INCA, IARC e GLOBOCAN; a coluna do
      -- padrão brasileiro, ao lado, mantém a comparabilidade interna com o
      -- resto da plataforma. As duas usam os mesmos óbitos.
      oms as (select q.ano,
                1e5*sum(q.ob/q.pop*s.w)/sum(s.w) padr_oms
              from (select o.ano, o.g5, sum(o.ob) ob, any_value(p.pop) pop from
                      (select ano, {_sql_quinquenal('idade')} g5, sum(ob) ob
                       from ob_uf_idade
                       where causabas_3 between '{CID_MALIGNA[0]}' and '{CID_MALIGNA[1]}'
                       group by 1,2) o
                    join (select ano, {_sql_quinquenal('idade')} g5, sum(populacao) pop
                          from pop_idade where sexo='T' group by 1,2) p
                      on p.ano=o.ano and p.g5=o.g5
                    group by 1,2) q
              join padrao_oms s on s.g5=q.g5 group by 1)
      select a.ano, round(sum(a.ob))::bigint obitos, sum(a.pop) populacao,
             round(1e5*sum(a.ob)/sum(a.pop), 2) taxa_bruta_100k,
             round(1e5*sum(a.ob/a.pop*w.w)/sum(w.w), 2) taxa_padronizada_100k,
             round(any_value(o.padr_oms), 2) taxa_padronizada_oms_100k,
             round(any_value(r.maldef), 2) pct_causa_mal_definida,
             round(any_value(r.c80), 2) pct_c80_entre_neoplasias
      from a join padrao w on w.fx=a.fx join reg r on r.ano=a.ano
             join oms o on o.ano=a.ano
      group by 1 order by 1""").df(), "tab01_serie_nacional")

    p = tab01.set_index("ano")
    for rot, col in [("óbitos", "obitos"), ("taxa bruta", "taxa_bruta_100k"),
                     ("taxa padronizada", "taxa_padronizada_100k")]:
        ini, fim = p[col][2015], p[col][2024]
        print(f"  {rot:18s} {ini:>10,.1f} → {fim:>10,.1f}  ({100*(fim/ini-1):+5.1f}%)")


def razao_idoso_jovem(con: duckdb.DuckDBPyConnection) -> None:
    """tab17/tab18 — o quanto cada causa é doença de velho, com intervalo.

    Razão entre a taxa específica de 60 anos ou mais e a de 15 a 49, por
    capítulo da CID-10 e, dentro das neoplasias, por sítio. Reportada em log2:
    zero significa que a causa mata igualmente nas duas faixas, e cada unidade é
    uma duplicação.

    AS TRÊS ESCOLHAS DO RECORTE, E O QUE CADA UMA CUSTA
    ----------------------------------------------------
    **A faixa jovem começa em 15**, não em zero. Abaixo disso o perfil de causa é
    outro — perinatal, malformação, leucemia da infância — e misturá-lo diluiria
    justamente o que a pergunta quer ver: quem morre cedo na vida adulta.

    **Há um intervalo morto de 50 a 59 anos.** Faixas contíguas fazem a razão
    depender de onde exatamente se corta; deixar dez anos entre elas separa os
    grupos sem que o resultado penda do limiar. A sensibilidade a essa escolha
    está na coluna `razao_50_59_incluidos`.

    **A faixa idosa é aberta em 60+.** Consequência: a razão mistura "ocorre mais
    tarde" com "ocorre em idade muito avançada", e uma causa concentrada aos 85
    anos aparece mais alta que outra concentrada aos 62. É propriedade da
    pergunta, não defeito — mas quem comparar dois capítulos precisa saber.

    A razão é **crua dentro de cada faixa**, sem padronizar: como as duas faixas
    usam a mesma população para todas as causas, a composição etária interna é
    idêntica entre capítulos, e padronizar mudaria todos os valores na mesma
    direção sem alterar o ordenamento — que é o que a pergunta pede.
    """
    a0, a1 = ANOS_RECENTE
    pop = con.execute(f"""
      select sum(case when idade between 15 and 49 then populacao else 0 end) jovem,
             sum(case when idade between 15 and 59 then populacao else 0 end) jovem_amplo,
             sum(case when idade >= 60 then populacao else 0 end) idoso
      from pop_idade where sexo='T' and ano between {a0} and {a1}""").fetchone()

    con.execute("create or replace table cap10 "
                "(capitulo varchar, num smallint, ini varchar, fim varchar, descricao varchar)")
    sys.path.insert(0, str(ROOT / "scripts"))
    from _sim_obitos import CID10_CAPITULOS
    con.executemany("insert into cap10 values (?,?,?,?,?)", CID10_CAPITULOS)

    def _montar(sql: str, rotulo: str, chave: str, minimo: int) -> pd.DataFrame:
        d = con.execute(sql).df()
        linhas = []
        for r in d.itertuples():
            if r.ob_jovem < minimo or r.ob_idoso < minimo:
                continue
            razao, inf, sup = razao_taxas_ic(r.ob_idoso, pop[2], r.ob_jovem, pop[0])
            amplo, _, _ = razao_taxas_ic(r.ob_idoso, pop[2], r.ob_jovem_amplo, pop[1])
            linhas.append({
                chave: getattr(r, chave), rotulo: r.descricao,
                "obitos_15_49": int(round(r.ob_jovem)),
                "obitos_60_mais": int(round(r.ob_idoso)),
                "taxa_15_49_100k": round(1e5 * r.ob_jovem / pop[0], 2),
                "taxa_60_mais_100k": round(1e5 * r.ob_idoso / pop[2], 2),
                "log2_razao": round(np.log2(razao), 2),
                "ic95_inf": round(np.log2(inf), 2),
                "ic95_sup": round(np.log2(sup), 2),
                "razao_50_59_incluidos": round(np.log2(amplo), 2),
            })
        return pd.DataFrame(linhas).sort_values("log2_razao", ignore_index=True)

    cap = _montar(f"""
      select coalesce(c.capitulo,'N/D') capitulo, any_value(c.descricao) descricao,
             sum(case when o.idade between 15 and 49 then o.ob else 0 end) ob_jovem,
             sum(case when o.idade between 15 and 59 then o.ob else 0 end) ob_jovem_amplo,
             sum(case when o.idade >= 60 then o.ob else 0 end) ob_idoso
      from ob_uf_idade o
        left join cap10 c on o.causabas_3 >= c.ini and o.causabas_3 <= c.fim
      where o.ano between {a0} and {a1} group by 1""", "descricao", "capitulo", 500)
    escrever(cap, "tab17_razao_idoso_jovem_capitulo")

    sitio = _montar(f"""
      select o.causabas_3 causabas_3, any_value(d.descricao) descricao,
             sum(case when o.idade between 15 and 49 then o.ob else 0 end) ob_jovem,
             sum(case when o.idade between 15 and 59 then o.ob else 0 end) ob_jovem_amplo,
             sum(case when o.idade >= 60 then o.ob else 0 end) ob_idoso
      from ob_uf_idade o left join cat d using(causabas_3)
      where o.ano between {a0} and {a1}
        and o.causabas_3 between '{CID_MALIGNA[0]}' and '{CID_MALIGNA[1]}'
      group by 1""", "descricao", "causabas_3", 300)
    escrever(sitio, "tab18_razao_idoso_jovem_sitio")

    ii = cap[cap.capitulo == "II"].iloc[0]
    print(f"  capítulos: {cap.iloc[0].capitulo} ({cap.iloc[0].descricao[:28]}) é o mais jovem, "
          f"log2 {cap.iloc[0].log2_razao} [{cap.iloc[0].ic95_inf}, {cap.iloc[0].ic95_sup}]")
    print(f"  neoplasias (cap. II): log2 {ii.log2_razao} [{ii.ic95_inf}, {ii.ic95_sup}] "
          f"— {2 ** ii.log2_razao:.0f}x mais no idoso")
    print(f"  sítios: mais jovem {sitio.iloc[0].causabas_3} ({sitio.iloc[0].log2_razao}), "
          f"mais idoso {sitio.iloc[-1].causabas_3} ({sitio.iloc[-1].log2_razao})")


def sensibilidade_denominador(con: duckdb.DuckDBPyConnection) -> None:
    """tab16 — o estudo inteiro refeito sob os quatro denominadores candidatos.

    A auditoria de 2026-09-07 achou três séries populacionais em uso simultâneo
    e trocou todas por uma. Uma troca dessas muda **todos** os números do artigo,
    e afirmar em prosa que "o achado sobreviveu" seria pedir confiança: aqui ele
    é refeito sob cada candidata, e a tabela é a evidência.

    As quatro:

      projeção rev. 2024   adotada. Oficial, pós-Censo, reconciliada com a
                           Pesquisa de Pós-Enumeração
      projeção rev. 2018   a que a plataforma usava. Anterior ao Censo
      Censo 2022           a contagem bruta, sem correção de subcontagem;
                           estática, replicada em todos os anos
      reconciliada interna total certo, forma etária aproximada pela projeção
                           de 2018

    As duas últimas não têm série anual por idade que sustente a decomposição,
    então entram só com o que dá para calcular. É informação, não omissão: uma
    candidata que não permite decompor já se desqualifica para este artigo.
    """
    padroes = {
        "Projeção rev. 2024 (adotada)":
            "select ano, fx, pop from pop_br",
        "Projeção rev. 2018 (anterior)":
            f"select ano, faixa fx, sum(populacao) pop from "
            f"'{(REFS / 'pop_idade_uf_ano.parquet').as_posix()}' group by 1,2",
        "Reconciliada interna":
            f"select ano, fx, sum(pop) pop from "
            f"'{(REFS / 'pop_idade_uf_ano_reconciliada.parquet').as_posix()}' group by 1,2",
        "Censo 2022 (contagem bruta)":
            "select a.ano, c.fx, c.pop from (select distinct ano from pop_br) a cross join "
            "(select case when faixa_etaria in ('<1','1-4') then '0-4' else faixa_etaria end fx,"
            " sum(populacao) pop from pop_mun_fx group by 1) c",
    }
    linhas = []
    for nome, sql in padroes.items():
        d = con.execute(f"""with p as ({sql}),
          a as (select o.ano, o.fx, sum(o.ob) ob, any_value(p.pop) pop
                from (select ano, fx, sum(ob) ob from ob_br group by 1,2) o
                join p on p.ano=o.ano and p.fx=o.fx group by 1,2)
          select a.ano, sum(a.pop) pop, 1e5*sum(a.ob/a.pop*w.w)/sum(w.w) padr
          from a join padrao w on w.fx=a.fx group by 1 order by 1""").df()
        if d.empty:
            continue
        ini, fim = d[d.ano == 2015].iloc[0], d[d.ano == 2024].iloc[0]
        pop22 = d[d.ano == 2022].iloc[0]["pop"]
        linhas.append({"denominador": nome, "populacao_2022": int(round(pop22)),
                       "taxa_padr_2015": round(ini.padr, 2),
                       "taxa_padr_2024": round(fim.padr, 2),
                       "variacao_pct": round(100 * (fim.padr / ini.padr - 1), 1)})
    escrever(pd.DataFrame(linhas), "tab16_sensibilidade_denominador")
    for r in linhas:
        print(f"  {r['denominador']:32s} pop2022 {r['populacao_2022']:>12,}  "
              f"padr {r['taxa_padr_2015']:>6} → {r['taxa_padr_2024']:>6}  "
              f"({r['variacao_pct']:+.1f}%)")


def prematura_30_69(con: duckdb.DuckDBPyConnection) -> None:
    """tab15 — probabilidade de morrer de câncer entre 30 e 70 anos.

    É o indicador de mortalidade prematura por doença crônica não transmissível
    da OMS, alvo do ODS 3.4: a probabilidade **incondicional** de uma pessoa de
    30 anos morrer da causa antes dos 70, calculada por tábua de vida sobre as
    taxas quinquenais:

        ₅q_x = 5·m_x / (1 + 2,5·m_x)      ⁴⁰q₃₀ = 1 − Π(1 − ₅q_x)

    Não existia na primeira versão desta análise, e não por escolha: o
    denominador do projeto tinha faixas de quinze anos (45–59, 60–74) e não
    permitia recortar 30–69. A projeção revisão 2024, por idade simples,
    destrava o recorte — que é o que torna esta série comparável com a base de
    indicadores da OMS e com a meta brasileira do ODS 3.4.

    Diferente de uma taxa padronizada, esta quantidade não depende de população
    padrão nenhuma: é uma probabilidade sintética, e por isso comparável entre
    países sem convenção de padrão.
    """
    d = con.execute(f"""
      with o as (select ano, {_sql_quinquenal('idade')} g5, sum(ob) ob
                 from ob_uf_idade
                 where causabas_3 between '{CID_MALIGNA[0]}' and '{CID_MALIGNA[1]}'
                   and idade between 30 and 69 group by 1,2),
      p as (select ano, {_sql_quinquenal('idade')} g5, sum(populacao) pop
            from pop_idade where sexo='T' and idade between 30 and 69 group by 1,2)
      select o.ano, o.g5, o.ob, p.pop from o join p on p.ano=o.ano and p.g5=o.g5
      order by 1,2""").df()

    linhas = []
    for ano, g in d.groupby("ano"):
        m = (g.ob / g["pop"]).values
        q5 = 5 * m / (1 + 2.5 * m)
        q = 1 - np.prod(1 - q5)
        linhas.append({"ano": int(ano), "obitos_30_69": int(round(g.ob.sum())),
                       "populacao_30_69": int(g["pop"].sum()),
                       "taxa_bruta_30_69_100k": round(1e5 * g.ob.sum() / g["pop"].sum(), 1),
                       "prob_morrer_30_69_pct": round(100 * q, 3)})
    tab = escrever(pd.DataFrame(linhas), "tab15_prematura_30_69")
    ini, fim = tab.iloc[0], tab.iloc[-1]
    print(f"  probabilidade de morrer de câncer entre 30 e 70: "
          f"{ini.prob_morrer_30_69_pct}% ({int(ini.ano)}) → "
          f"{fim.prob_morrer_30_69_pct}% ({int(fim.ano)})"
          f"  ({100 * (fim.prob_morrer_30_69_pct / ini.prob_morrer_30_69_pct - 1):+.1f}%)")


def decomposicao(con: duckdb.DuckDBPyConnection) -> None:
    """tab03 — quanto do aumento é população, envelhecimento e risco.

    Decomposição de três termos com **média sobre as seis ordens** de aplicação.
    A ordem importa (os efeitos não são aditivos) e escolher uma só embutiria uma
    preferência arbitrária no resultado.
    """
    d = con.execute("""
      select o.ano, o.fx, sum(o.ob) ob, any_value(p.pop) pop
      from (select ano, fx, sum(ob) ob from ob_br group by 1,2) o
      join pop_br p on p.ano=o.ano and p.fx=o.fx group by 1,2""").df()
    d["m"] = d.ob / d["pop"]
    ini, fim = d[d.ano == 2015].set_index("fx"), d[d.ano == 2024].set_index("fx")
    fx = sorted(ini.index)
    pop_i, pop_f = ini.loc[fx, "pop"].values, fim.loc[fx, "pop"].values
    taxa_i, taxa_f = ini.loc[fx, "m"].values, fim.loc[fx, "m"].values
    est_i, est_f = pop_i / pop_i.sum(), pop_f / pop_f.sum()
    n_i, n_f = pop_i.sum(), pop_f.sum()

    acum: dict[str, list[float]] = {"N": [], "S": [], "M": []}
    for ordem in itertools.permutations("NSM"):
        n, est, taxa = n_i, est_i, taxa_i
        base = (n * est * taxa).sum()
        for k in ordem:
            n, est, taxa = ((n_f, est, taxa) if k == "N" else
                            (n, est_f, taxa) if k == "S" else (n, est, taxa_f))
            novo = (n * est * taxa).sum()
            acum[k].append(novo - base)
            base = novo
    total = (pop_f * taxa_f).sum() - (pop_i * taxa_i).sum()
    rot = {"N": "crescimento populacional", "S": "envelhecimento (estrutura etária)",
           "M": "risco (taxas específicas por idade)"}
    tab = pd.DataFrame([{"componente": rot[k], "obitos": round(sum(v) / len(v)),
                         "pct_da_variacao": round(100 * (sum(v) / len(v)) / total, 1)}
                        for k, v in acum.items()])
    tab.loc[len(tab)] = ["variação total 2015→2024", round(total), 100.0]
    escrever(tab, "tab03_decomposicao")
    for _, r in tab.iterrows():
        print(f"  {r.componente:42s} {r.obitos:+9,.0f}  ({r.pct_da_variacao:+5.1f}%)")


def contrafactual(con: duckdb.DuckDBPyConnection) -> None:
    """tab04 — observado contra a taxa específica de 2019 mantida.

    NÃO é "mortes evitadas". É a diferença entre o observado e um cenário em que
    o risco por idade tivesse ficado onde estava às vésperas da pandemia. Cabem
    ao menos três leituras — risco competitivo da COVID, seleção de mortalidade
    entre pacientes frágeis, e melhora real —, e este dado não as separa. O que
    ele descarta é a quarta: piora de registro, porque a fração de causa mal
    definida CAIU no período (5,5% em 2019 → 4,5% em 2024).
    """
    d = con.execute("""
      select o.ano, o.fx, sum(o.ob) ob, any_value(p.pop) pop
      from (select ano, fx, sum(ob) ob from ob_br group by 1,2) o
      join pop_br p on p.ano=o.ano and p.fx=o.fx group by 1,2""").df()
    d["m"] = d.ob / d["pop"]
    m19 = d[d.ano == 2019].set_index("fx")["m"]
    linhas = []
    for y in range(2020, 2025):
        esp = (d[d.ano == y].set_index("fx")["pop"] * m19).sum()
        obs = d[d.ano == y].ob.sum()
        linhas.append({"ano": y, "obitos_observados": int(obs),
                       "obitos_esperados_taxa_2019": round(esp),
                       "diferenca": round(obs - esp), "pct": round(100 * (obs - esp) / esp, 1)})
    tab = escrever(pd.DataFrame(linhas), "tab04_contrafactual_2019")
    print(f"  2020–2024 acumulado: {tab.diferenca.sum():+,.0f} óbitos "
          f"({100*tab.diferenca.sum()/tab.obitos_esperados_taxa_2019.sum():+.1f}%)")


def sitios(con: duckdb.DuckDBPyConnection) -> None:
    """tab05/tab06 — o tumor que mata muda com a idade e com o sexo."""
    escrever(con.execute(f"""
      with t as (select fx, causabas_3, sum(ob) ob from ob_br
                 where ano between 2020 and 2024 group by 1,2),
      r as (select *, row_number() over(partition by fx order by ob desc) rk,
                   100.0*ob/sum(ob) over(partition by fx) pct from t)
      select r.fx faixa_etaria, r.rk posicao, r.causabas_3,
             trim(regexp_replace(c.descricao, '^C[0-9]+\\s+', '')) sitio,
             r.ob obitos, round(r.pct,1) pct_da_faixa
      from r left join cat c using(causabas_3)
      where r.rk <= 5 order by {_sql_ordem('r.fx')}, posicao""").df(), "tab05_sitios_por_faixa")

    escrever(con.execute("""
      with t as (select sexo, causabas_3, sum(ob) ob from ob_br
                 where ano between 2020 and 2024 and sexo in ('M','F') group by 1,2),
      r as (select *, row_number() over(partition by sexo order by ob desc) rk,
                   100.0*ob/sum(ob) over(partition by sexo) pct from t)
      select r.sexo, r.rk posicao, r.causabas_3,
             trim(regexp_replace(c.descricao, '^C[0-9]+\\s+', '')) sitio,
             r.ob obitos, round(r.pct,1) pct_do_sexo
      from r left join cat c using(causabas_3) where r.rk <= 10
      order by sexo, posicao""").df(), "tab06_sitios_por_sexo")


def territorio(con: duckdb.DuckDBPyConnection) -> None:
    """tab07 — taxa padronizada por UF, com o colo do útero ao lado.

    As duas colunas contam histórias opostas de propósito: a taxa total ordena as
    UFs mais ou menos por renda, e a do colo do útero as ordena ao contrário. A
    taxa de C53 é por 100 mil habitantes de AMBOS os sexos — o denominador por UF
    não tem grão de sexo —, então serve para comparar UFs entre si, não para ser
    citada como taxa de mortalidade feminina.
    """
    a0, a1 = ANOS_RECENTE
    tab = escrever(con.execute(f"""
      with ob as (select uf_sigla, ano, {_sql_faixa7('idade')} fx,
                    sum(case when causabas_3 between '{CID_MALIGNA[0]}' and '{CID_MALIGNA[1]}'
                             then ob else 0 end) ob,
                    sum(case when causabas_3='C53' then ob else 0 end) c53
                  from ob_uf_idade where ano between {a0} and {a1} group by 1,2,3),
      a as (select p.uf_sigla, p.fx, sum(p.pop) py,
                   sum(coalesce(o.ob,0)) ob, sum(coalesce(o.c53,0)) c53
            from pop_uf p left join ob o
              on o.uf_sigla=p.uf_sigla and o.ano=p.ano and o.fx=p.fx
            where p.ano between {a0} and {a1} group by 1,2)
      select a.uf_sigla, sum(a.ob) obitos,
             round(1e5*sum(a.ob)/sum(a.py),1) taxa_bruta_100k,
             round(1e5*sum(a.ob/a.py*w.w)/sum(w.w),1) taxa_padronizada_100k,
             sum(a.c53) obitos_colo_utero,
             round(1e5*sum(a.c53/a.py*w.w)/sum(w.w),2) taxa_padr_colo_utero_100k
      from a join padrao w on w.fx=a.fx group by 1
      order by taxa_padronizada_100k desc, uf_sigla""").df(), "tab07_uf")

    print(f"  maior taxa padronizada: {tab.iloc[0].uf_sigla} {tab.iloc[0].taxa_padronizada_100k}"
          f" · menor: {tab.iloc[-1].uf_sigla} {tab.iloc[-1].taxa_padronizada_100k} "
          f"({tab.iloc[0].taxa_padronizada_100k/tab.iloc[-1].taxa_padronizada_100k:.2f}x)")
    c = tab.sort_values("taxa_padr_colo_utero_100k", ascending=False)
    print(f"  colo do útero — maior: {c.iloc[0].uf_sigla} {c.iloc[0].taxa_padr_colo_utero_100k}"
          f" · menor: {c.iloc[-1].uf_sigla} {c.iloc[-1].taxa_padr_colo_utero_100k} "
          f"({c.iloc[0].taxa_padr_colo_utero_100k/c.iloc[-1].taxa_padr_colo_utero_100k:.2f}x)")


def vulnerabilidade(con: duckdb.DuckDBPyConnection) -> None:
    """tab08/tab09 — quartil de vulnerabilidade municipal (IVS).

    O denominador é o Censo 2022 multiplicado pelos anos da janela; a população
    municipal por faixa só existe no ano censitário. É aproximação declarada, e
    afeta os quatro quartis no mesmo sentido.

    `taxa_padr_corrigida_100k` redistribui as mortes de causa mal definida
    (R00–R99) pro-rata sobre as causas definidas do mesmo estrato. É o teste de
    que o gradiente não é só qualidade de registro — e ele sobrevive ao teste.
    """
    a0, a1 = ANOS_RECENTE

    # O denominador municipal é o Censo 2022 — é a única fonte com grão de
    # município por faixa. Mas o Censo é a CONTAGEM, e o resto desta análise usa
    # a projeção revisão 2024, que reconcilia a subcontagem medida pela Pesquisa
    # de Pós-Enumeração. Publicar as duas lado a lado deixaria a Tabela 8 (UF) e
    # a Tabela 9 (quartil) em escalas diferentes por ~4%, e o leitor as compara.
    #
    # A saída é a que o próprio `pipeline_v2` já usa para anos não censitários:
    # **forma do Censo, nível da projeção**. Cada município é escalado pelo fator
    # da sua UF e faixa, ano a ano. A composição municipal continua sendo a
    # enumerada; só o patamar passa a ser o oficial.
    con.execute(f"""create table fator_uf as
      with cen as (select m.uf_sigla,
                     case when p.faixa_etaria in ('<1','1-4') then '0-4'
                          else p.faixa_etaria end fx,
                     sum(p.populacao) pop
                   from pop_mun_fx p
                   join '{(MARTS / 'dim_municipio.parquet').as_posix()}' m using(municipio_cod)
                   group by 1,2)
      select u.uf_sigla, u.ano, u.fx, u.pop / cen.pop k
      from pop_uf u join cen on cen.uf_sigla=u.uf_sigla and cen.fx=u.fx
      where u.ano between {a0} and {a1}""")
    con.execute(f"""create table denom_q as
      select i.ivs_quartil q, p.faixa_etaria fx,
             sum(p.populacao * f.k) py
      from pop_mun_fx p
        join ivs i using(municipio_cod)
        join '{(MARTS / 'dim_municipio.parquet').as_posix()}' m using(municipio_cod)
        join fator_uf f on f.uf_sigla=m.uf_sigla
                       and f.fx = case when p.faixa_etaria in ('<1','1-4') then '0-4'
                                       else p.faixa_etaria end
      group by 1,2""")
    # O numerador vem da mesma tabela de idade exata que o resto da análise, e
    # não do mart de faixa: assim os 241 óbitos sem idade declarada entram aqui
    # também, e não há dois numeradores com totais diferentes no mesmo artigo.
    # A faixa `<1`/`1-4` é reconstruída porque a população padrão municipal
    # (`padrao_mun`) tem oito faixas, não sete.
    con.execute(f"""create table ob_q as
      select i.ivs_quartil q,
             case when o.idade < 1 then '<1' when o.idade < 5 then '1-4'
                  else {_sql_faixa7('o.idade')} end fx,
             o.causabas_3, sum(o.ob) ob
      from ob_uf_idade o join ivs i using(municipio_cod)
      where o.ano between {a0} and {a1} group by 1,2,3""")

    tab08 = escrever(con.execute(f"""
      with a as (select d.q, d.fx, d.py,
                   sum(case when o.causabas_3 between '{CID_MALIGNA[0]}' and '{CID_MALIGNA[1]}'
                            then o.ob else 0 end) neo,
                   sum(case when o.causabas_3 between 'R00' and 'R99' then o.ob else 0 end) maldef,
                   sum(case when o.causabas_3='C80' then o.ob else 0 end) c80,
                   sum(o.ob) tot
                 from denom_q d left join ob_q o on o.q=d.q and o.fx=d.fx group by 1,2,3)
      select a.q quartil_ivs, sum(a.neo) obitos_neoplasia, sum(a.tot) obitos_totais,
             round(1e5*sum(a.neo)/sum(a.py),1) taxa_bruta_100k,
             round(1e5*sum(a.neo/a.py*w.w)/sum(w.w),1) taxa_padronizada_100k,
             round(1e5*sum((a.neo*a.tot/nullif(a.tot-a.maldef,0))/a.py*w.w)/sum(w.w),1)
               taxa_padr_corrigida_100k,
             round(100.0*sum(a.maldef)/sum(a.tot),2) pct_causa_mal_definida,
             round(100.0*sum(a.c80)/sum(a.neo),2) pct_c80_entre_neoplasias,
             round(100.0*sum(a.neo)/sum(a.tot),1) pct_obitos_por_neoplasia
      from a join padrao_mun w on w.fx=a.fx group by 1 order by 1""").df(), "tab08_vulnerabilidade")

    q1, q4 = tab08.iloc[0], tab08.iloc[-1]
    print(f"  Q1 (menos vulnerável) {q1.taxa_padronizada_100k} vs Q4 {q4.taxa_padronizada_100k}"
          f" — {100*(q1.taxa_padronizada_100k/q4.taxa_padronizada_100k-1):+.0f}%")
    print(f"  redistribuindo mal definidas: {q1.taxa_padr_corrigida_100k} vs "
          f"{q4.taxa_padr_corrigida_100k} — "
          f"{100*(q1.taxa_padr_corrigida_100k/q4.taxa_padr_corrigida_100k-1):+.0f}%")

    tab09 = escrever(con.execute("""
      with skel as (select d.q, d.fx, c.causabas_3
                    from denom_q d cross join (select distinct causabas_3 from ob_q) c),
      r as (select s.q, s.causabas_3, sum(coalesce(o.ob,0)) ob,
                   1e5*sum(coalesce(o.ob,0)/d.py*w.w)/sum(w.w) padr
            from skel s
              join denom_q d on d.q=s.q and d.fx=s.fx
              join padrao_mun w on w.fx=s.fx
              left join ob_q o on o.q=s.q and o.fx=s.fx and o.causabas_3=s.causabas_3
            group by 1,2),
      tot as (select causabas_3, sum(ob) ob from r group by 1)
      select r.causabas_3, trim(regexp_replace(c.descricao, '^C[0-9]+\\s+', '')) sitio,
             t.ob obitos,
             round(max(case when r.q='Q1' then r.padr end),2) taxa_Q1_menos_vulneravel,
             round(max(case when r.q='Q4' then r.padr end),2) taxa_Q4_mais_vulneravel,
             round(max(case when r.q='Q4' then r.padr end)
                   /nullif(max(case when r.q='Q1' then r.padr end),0),2) razao_Q4_Q1
      from r join tot t using(causabas_3) left join cat c using(causabas_3)
      where t.ob >= 8000 and r.causabas_3 between 'C00' and 'C97'
      group by 1,2,3
      order by razao_Q4_Q1 desc, causabas_3""").df(), "tab09_sitio_por_vulnerabilidade")

    piores = tab09[tab09.razao_Q4_Q1 > 1]
    print(f"  sítios com mortalidade MAIOR no quartil vulnerável: "
          f"{', '.join(piores.causabas_3) or '(nenhum)'}")


def social(con: duckdb.DuckDBPyConnection) -> None:
    """tab10–tab14 — cor/raça, escolaridade e local do óbito (2022–2023)."""
    arquivos = [RAW / f"DO{str(a)[2:]}OPEN.csv" for a in ANOS_SOCIAL]
    faltando = [f.name for f in arquivos if not f.exists()]
    if faltando:
        raise SystemExit(f"SIM: {faltando} ausente(s) — o eixo social depende do microdado "
                         "nacional, que é a única fonte com RACACOR/ESC2010 em disco. "
                         "Rode `pipeline_v2.py` antes; processar sem eles publicaria um "
                         "recorte incompleto com exit 0.")
    lista = ", ".join(f"'{f.as_posix()}'" for f in arquivos)
    con.execute(f"""create table micro as
      with b as (
        select try_cast(substr(lpad(DTOBITO,8,'0'),5,4) as smallint) ano,
               substr(upper(trim(CAUSABAS)),1,3) c3,
               trim(coalesce(SEXO,'')) sexo, trim(coalesce(RACACOR,'')) racacor,
               trim(coalesce(ESC2010,'')) esc, trim(coalesce(LOCOCOR,'')) lococor,
               {SQL_IDADE.format(c="trim(coalesce(IDADE,''))")} idade_anos
        from read_csv([{lista}], delim=';', header=true, quote='"',
                      all_varchar=true, union_by_name=true)
        where coalesce(nullif(trim(TIPOBITO),''),'2') <> '1')
      select ano, c3, sexo, racacor, esc, lococor, idade_anos,
             {SQL_FAIXA.format(c='idade_anos')} fx,
             (c3 between '{CID_MALIGNA[0]}' and '{CID_MALIGNA[1]}') neoplasia,
             (c3 between 'R00' and 'R99') mal_definida
      from b where idade_anos is not null""")
    n = con.execute("select count(*), sum(neoplasia::int) from micro").fetchone()
    print(f"  microdado {ANOS_SOCIAL[0]}–{ANOS_SOCIAL[-1]}: {n[0]:,} óbitos, "
          f"{n[1]:,} por neoplasia maligna")

    pop_raca(con)
    caso = " ".join(f"when '{k}' then '{v}'" for k, v in RACAS.items())
    con.execute(f"""create table ob_raca as
      select case racacor {caso} else 'Ignorado' end raca,
             case sexo when '1' then 'M' when '2' then 'F' else 'I' end sexo, fx,
             sum(neoplasia::int) ob,
             sum((c3='C53')::int) c53, sum((c3='C50')::int) c50,
             sum((c3='C61')::int) c61, sum((c3='C18')::int) c18, sum((c3='C16')::int) c16
      from micro group by 1,2,3""")
    anos = len(ANOS_SOCIAL)

    # Padronização com pesos do MESMO sexo quando o recorte é por sexo; usar o
    # peso de ambos os sexos em estrato sexo-específico soma a população duas
    # vezes e dobra a taxa — foi o primeiro resultado desta análise, e era falso.
    #
    # A taxa sai daqui em Python, e não em SQL como nas demais, por causa do
    # intervalo: Fay–Feuer precisa dos estratos separados para calcular a
    # variância, e agregá-los no SQL os perderia. É o recorte com as menores
    # contagens da análise, e portanto o único em que o intervalo decide se há
    # achado.
    def _por_estrato(coluna: str, sexo: str | None) -> pd.DataFrame:
        filtro = f"where p.sexo='{sexo}'" if sexo else ""
        return con.execute(f"""
          select p.raca, p.fx, sum(p.pop)*{anos} py, sum(coalesce(o.{coluna},0)) ob,
                 any_value(w.w) w
          from pop_raca p
            left join ob_raca o on o.raca=p.raca and o.fx=p.fx and o.sexo=p.sexo
            join (select fx, sum(pop) w from pop_raca
                  {"where sexo='" + sexo + "'" if sexo else ""} group by 1) w on w.fx=p.fx
          {filtro} group by 1,2""").df()

    def _tabela(coluna: str, sexo: str | None, casas: int) -> pd.DataFrame:
        d = _por_estrato(coluna, sexo)
        linhas = []
        for raca, g in d.groupby("raca"):
            taxa, inf, sup = taxa_padronizada_ic(g.ob, g.py, g.w)
            linhas.append({"raca": raca, "obitos": int(g.ob.sum()),
                           "taxa_bruta_100k": round(1e5 * g.ob.sum() / g.py.sum(), casas),
                           "taxa_padronizada_100k": round(taxa, casas),
                           "ic95_inf": round(inf, casas), "ic95_sup": round(sup, casas)})
        # Desempate por nome: `sort_values` numa coluna só devolve ordens
        # diferentes para valores iguais, e duas execuções do mesmo código
        # passariam a gerar bytes diferentes. Ver a nota em `ob_uf_idade`.
        return (pd.DataFrame(linhas)
                .sort_values(["taxa_padronizada_100k", "raca"],
                             ascending=[False, True], ignore_index=True))

    escrever(_tabela("ob", None, 1), "tab10_raca")

    partes = []
    for col, sitio, sx in [("c53", "Colo do útero (C53)", "F"), ("c50", "Mama (C50)", "F"),
                           ("c61", "Próstata (C61)", "M"), ("c16", "Estômago (C16)", None),
                           ("c18", "Cólon (C18)", None)]:
        d = _tabela(col, sx, 2).drop(columns=["taxa_bruta_100k"])
        d.insert(0, "sitio", sitio)
        partes.append(d)
    escrever(pd.concat(partes, ignore_index=True), "tab11_sitio_por_raca")

    caso_e = " ".join(f"when '{k}' then '{v}'" for k, v in ESCOL.items())
    escrever(con.execute(f"""
      select case esc {caso_e} else '9 Ignorado' end escolaridade,
             count(*) obitos_totais,
             round(100.0*sum(neoplasia::int)/count(*),1) pct_obitos_por_neoplasia,
             round(100.0*sum(mal_definida::int)/count(*),2) pct_causa_mal_definida,
             round(100.0*sum((neoplasia and lococor='1')::int)/nullif(sum(neoplasia::int),0),1)
               pct_neo_morre_em_hospital,
             round(100.0*sum((neoplasia and lococor='3')::int)/nullif(sum(neoplasia::int),0),1)
               pct_neo_morre_em_domicilio
      from micro where idade_anos between 30 and 69 group by 1 order by 1""").df(),
             "tab12_escolaridade_30_69")

    escrever(con.execute(f"""
      select case racacor {caso} else 'Ignorado' end raca,
             sum(neoplasia::int) obitos_neoplasia,
             round(100.0*sum(neoplasia::int)/count(*),1) pct_obitos_por_neoplasia,
             round(100.0*sum((neoplasia and lococor='1')::int)/nullif(sum(neoplasia::int),0),1)
               pct_morre_em_hospital,
             round(100.0*sum((neoplasia and lococor='3')::int)/nullif(sum(neoplasia::int),0),1)
               pct_morre_em_domicilio,
             round(100.0*sum(mal_definida::int)/count(*),2) pct_causa_mal_definida,
             round(100.0*sum((neoplasia and c3='C80')::int)/nullif(sum(neoplasia::int),0),2)
               pct_c80_entre_neoplasias
      from micro where idade_anos between 30 and 69 group by 1
      order by obitos_neoplasia desc, raca""").df(), "tab13_raca_acesso_30_69")

    escrever(con.execute(f"""
      select fx faixa_etaria, sum(neoplasia::int) obitos_neoplasia,
             round(100.0*sum((neoplasia and lococor='1')::int)/nullif(sum(neoplasia::int),0),1) pct_hospital,
             round(100.0*sum((neoplasia and lococor='3')::int)/nullif(sum(neoplasia::int),0),1) pct_domicilio,
             round(100.0*sum((neoplasia and lococor not in ('1','3') and lococor<>'')::int)
                   /nullif(sum(neoplasia::int),0),1) pct_outros
      from micro group by 1 order by {_sql_ordem('fx')}""").df(), "tab14_local_obito_por_faixa")


def _br(n: float) -> str:
    """Inteiro com separador de milhar do português.

    A Tabela 1 do artigo tem duas colunas — Item e Valor — e toda coluna que
    mistura texto e número vira texto: o formatador do manuscrito não teria como
    saber que "2292834" é contagem. O número sai daqui já formatado, e o mesmo
    valor serve à prosa e à tabela.
    """
    return f"{round(n):,}".replace(",", ".")


def base(con: duckdb.DuckDBPyConnection) -> None:
    """tab00 — os números de enquadramento, medidos em vez de escritos.

    Total de óbitos, cobertura, tamanho do microdado social. Existem como tabela
    porque são os números que a prosa mais repete, e prosa não tem quem a
    contradiga: é o mesmo motivo de `artigo/tabelas/tabela_1_base.csv`. Depende
    de `social()` já ter criado `micro`.
    """
    tot = con.execute("select sum(ob) from ob_br").fetchone()[0]
    ini, fim = con.execute("select min(ano), max(ano) from ob_br").fetchone()
    mic = con.execute("select count(*), sum(neoplasia::int), count(distinct c3) "
                      "from micro").fetchone()
    ign = con.execute("select sum((racacor not in ('1','2','3','4','5'))::int), "
                      "sum((esc not in ('0','1','2','3','4','5'))::int) "
                      "from micro where neoplasia").fetchone()
    # D00–D48 medido, e não estimado: a §2.1 do manuscrito afirma o tamanho da
    # diferença entre "capítulo II" e "neoplasia maligna", e afirmação com
    # número precisa do número.
    dd48 = con.execute("""
      select sum(case when causabas_3 between 'D00' and 'D48' then obitos else 0 end),
             sum(case when causabas_3 between 'D00' and 'D48' then obitos else 0 end)
               / nullif(sum(case when causabas_3 between 'C00' and 'D48'
                                 then obitos else 0 end), 0)
      from faixa where not preliminar""").fetchone()

    # As três perdas que a auditoria de 2026-09-07 mediu. Entram na tabela em vez
    # de ficarem numa nota porque a soma delas é a diferença entre o total deste
    # artigo e o do mart municipal — e um leitor que conferisse os dois sem esta
    # linha encontraria 241 óbitos sem explicação.
    sem_idade = con.execute(
        f"select sum(ob) from ob_bruto where idade is null "
        f"and causabas_3 between '{CID_MALIGNA[0]}' and '{CID_MALIGNA[1]}'").fetchone()[0]
    sem_sexo = con.execute(
        f"select sum(ob) from ob_uf_idade where sexo='I' "
        f"and causabas_3 between '{CID_MALIGNA[0]}' and '{CID_MALIGNA[1]}'").fetchone()[0]
    sem_mun = con.execute(
        f"select sum(ob) from ob_uf_idade where right(municipio_cod,4)='0000' "
        f"and causabas_3 between '{CID_MALIGNA[0]}' and '{CID_MALIGNA[1]}'").fetchone()[0]
    linhas = [
        ("Fonte dos óbitos", "SIM/DataSUS — .dbc por UF (2015–2021, 2024) e "
                             "CSV nacional do OpenDataSUS (2022–2023)"),
        ("Período consolidado", f"{ini}–{fim}"),
        ("Recorte de causa", "CID-10 C00–C97 (neoplasias malignas), causa básica "
                             "truncada em três caracteres"),
        ("Óbitos em D00–D48, excluídos do recorte", _br(dd48[0])),
        ("D00–D48 como fração do capítulo II", f"{100 * dd48[1]:.1f}%".replace(".", ",")),
        ("Óbitos por neoplasia maligna", _br(tot)),
        ("Óbitos sem idade declarada, redistribuídos pro-rata", _br(sem_idade)),
        ("Óbitos com sexo ignorado", _br(sem_sexo)),
        ("Óbitos com município ignorado, UF recuperada do código", _br(sem_mun)),
        ("Denominador populacional", "IBGE — Projeções da População, revisão 2024 "
                                     "(por UF, ano e idade simples)"),
        ("População padrão", "Brasil, Censo 2022, e padrão mundial da OMS "
                             "2000–2025 (método direto, as duas)"),
        ("Período do eixo social", f"{ANOS_SOCIAL[0]}–{ANOS_SOCIAL[-1]}"),
        ("Óbitos no microdado social (todas as causas)", _br(mic[0])),
        ("Óbitos por neoplasia maligna no microdado social", _br(mic[1])),
        ("Sem cor/raça declarada, entre os óbitos por câncer",
         f"{100 * ign[0] / mic[1]:.1f}%".replace(".", ",")),
        ("Sem escolaridade declarada, entre os óbitos por câncer",
         f"{100 * ign[1] / mic[1]:.1f}%".replace(".", ",")),
        ("Denominador por cor/raça", "IBGE — Censo 2022, SIDRA t/9606 "
                                     "(cor/raça × sexo × idade)"),
        ("Óbitos fetais", "excluídos na fonte — TIPOBITO = 2 em 100% dos registros"),
        ("Ano preliminar excluído", "2025 (SIM/PRELIM/DORES)"),
    ]
    escrever(pd.DataFrame(linhas, columns=["Item", "Valor"]), "tab00_base")


def main() -> None:
    con = duckdb.connect()
    preparar(con)
    print("\n=== 1. série nacional: mais mortes, menos risco ===")
    serie_nacional(con)
    print("\n=== 2. sensibilidade ao denominador (auditoria de 2026-09-07) ===")
    sensibilidade_denominador(con)
    print("\n=== 3. mortalidade prematura, 30 a 69 anos (OMS / ODS 3.4) ===")
    prematura_30_69(con)
    print("\n=== 3b. razão idoso/jovem por capítulo e por sítio ===")
    razao_idoso_jovem(con)
    print("\n=== 4. decomposição do aumento 2015→2024 ===")
    decomposicao(con)
    print("\n=== 5. contrafactual: risco de 2019 mantido ===")
    contrafactual(con)
    print("\n=== 6. sítios por idade e por sexo ===")
    sitios(con)
    print("\n=== 7. território ===")
    territorio(con)
    print("\n=== 8. vulnerabilidade municipal ===")
    vulnerabilidade(con)
    print("\n=== 9. eixo social (microdado 2022–2023) ===")
    social(con)
    print("\n=== 10. números de enquadramento ===")
    base(con)
    print(f"\n[done] tabelas em {SAIDA.relative_to(ROOT).as_posix()}")


if __name__ == "__main__":
    main()
