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
   18% entre 2015 e 2024 (101,2 → 119,0 por 100 mil) e a padronizada CAI 4,4%
   (122,5 → 117,2). Quem publica a bruta publica a pirâmide etária do Brasil
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

FONTES
------
* `mart_mortalidade_causa_municipio_faixa` — óbitos por município × ano ×
  categoria CID × faixa × sexo, 2015–2024 consolidados.
* `data/raw/SIM/DO22OPEN.csv`, `DO23OPEN.csv` — microdado com as variáveis
  sociais (RACACOR, ESC2010, LOCOCOR), que o recorte `.dbc` dos demais anos
  **não** traz. Por isso todo eixo social é 2022–2023.
* `data/refs/pop_idade_uf_ano.parquet` — denominador por UF × ano × faixa.
* `dim_pop_padrao` — população padrão (Censo 2022, Brasil) do método direto.
* SIDRA t/9606 — população por cor/raça × sexo × idade, Censo 2022. Baixada uma
  vez e cacheada em `data/refs/pop_raca_idade_sexo_2022.parquet`.

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


def preparar(con: duckdb.DuckDBPyConnection) -> None:
    """Views e tabelas base: óbitos agregados, denominadores e população padrão."""
    con.execute("create view faixa as select * from "
                f"'{(MARTS / 'mart_mortalidade_causa_municipio_faixa.parquet').as_posix()}'")
    con.execute(f"create view cat as select * from '{(MARTS / 'dim_cid10_categoria.parquet').as_posix()}'")
    con.execute(f"create view ivs as select * from '{(MARTS / 'dim_ivs.parquet').as_posix()}'")
    con.execute("create view pop_mun_fx as select * from "
                f"'{(MARTS / 'dim_pop_faixa.parquet').as_posix()}'")
    # A população padrão vem em oito faixas; o denominador anual por UF, em sete.
    # Padronizar com pesos de um recorte e taxas de outro seria erro mudo.
    con.execute(f"""create table padrao as
      select case when faixa_etaria in ('<1','1-4') then '0-4' else faixa_etaria end fx,
             sum(populacao) w
      from '{(MARTS / 'dim_pop_padrao.parquet').as_posix()}' group by 1""")
    con.execute("create table padrao_mun as select faixa_etaria fx, populacao w from "
                f"'{(MARTS / 'dim_pop_padrao.parquet').as_posix()}'")
    con.execute("create table pop_uf as select uf_sigla, ano, faixa fx, populacao pop from "
                f"'{(REFS / 'pop_idade_uf_ano.parquet').as_posix()}'")
    con.execute("create table pop_br as select ano, fx, sum(pop) pop from pop_uf group by 1,2")
    con.execute("""create table ob_br as
      select ano, sexo,
             case when faixa_etaria in ('<1','1-4') then '0-4' else faixa_etaria end fx,
             causabas_3, sum(obitos) ob
      from faixa
      where not preliminar and causabas_3 between ? and ?
      group by 1,2,3,4""", list(CID_MALIGNA))


def serie_nacional(con: duckdb.DuckDBPyConnection) -> None:
    """tab01/tab02 — a série que separa 'mais mortes' de 'mais risco'."""
    escrever(con.execute(f"""
      with a as (select o.ano, o.fx, sum(o.ob) ob, any_value(p.pop) pop
                 from (select ano, fx, sum(ob) ob from ob_br group by 1,2) o
                 join pop_br p on p.ano=o.ano and p.fx=o.fx group by 1,2)
      select ano, fx faixa_etaria, ob obitos, pop populacao, round(1e5*ob/pop, 2) taxa_100k
      from a order by {_sql_ordem('fx')}, ano""").df(), "tab02_taxa_por_faixa_ano")

    # As duas colunas de registro NÃO são enfeite: elas sustentam a leitura do
    # degrau de 2020 (§3.3 do manuscrito). Um degrau para baixo na mortalidade
    # por câncer seria trivialmente explicado por piora de codificação — câncer
    # que passa a ser registrado como causa mal definida. Sem a série ao lado,
    # a hipótese fica em aberto; com ela, é descartável, porque a imprecisão
    # CAIU no período. Afirmação de prosa que depende de número tem de trazer o
    # número junto.
    tab01 = escrever(con.execute("""
      with a as (select o.ano, o.fx, sum(o.ob) ob, any_value(p.pop) pop
                 from (select ano, fx, sum(ob) ob from ob_br group by 1,2) o
                 join pop_br p on p.ano=o.ano and p.fx=o.fx group by 1,2),
      reg as (select ano,
                100.0*sum(case when causabas_3 between 'R00' and 'R99' then obitos else 0 end)
                  /sum(obitos) maldef,
                100.0*sum(case when causabas_3='C80' then obitos else 0 end)
                  /nullif(sum(case when causabas_3 between 'C00' and 'C97'
                                   then obitos else 0 end),0) c80
              from faixa where not preliminar group by 1)
      select a.ano, sum(a.ob) obitos, sum(a.pop) populacao,
             round(1e5*sum(a.ob)/sum(a.pop), 2) taxa_bruta_100k,
             round(1e5*sum(a.ob/a.pop*w.w)/sum(w.w), 2) taxa_padronizada_100k,
             round(any_value(r.maldef), 2) pct_causa_mal_definida,
             round(any_value(r.c80), 2) pct_c80_entre_neoplasias
      from a join padrao w on w.fx=a.fx join reg r on r.ano=a.ano
      group by 1 order by 1""").df(), "tab01_serie_nacional")

    p = tab01.set_index("ano")
    for rot, col in [("óbitos", "obitos"), ("taxa bruta", "taxa_bruta_100k"),
                     ("taxa padronizada", "taxa_padronizada_100k")]:
        ini, fim = p[col][2015], p[col][2024]
        print(f"  {rot:18s} {ini:>10,.1f} → {fim:>10,.1f}  ({100*(fim/ini-1):+5.1f}%)")


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
      with ob as (select uf_sigla, ano,
                    case when faixa_etaria in ('<1','1-4') then '0-4' else faixa_etaria end fx,
                    sum(case when causabas_3 between '{CID_MALIGNA[0]}' and '{CID_MALIGNA[1]}'
                             then obitos else 0 end) ob,
                    sum(case when causabas_3='C53' then obitos else 0 end) c53
                  from faixa where not preliminar and ano between {a0} and {a1} group by 1,2,3),
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
      order by taxa_padronizada_100k desc""").df(), "tab07_uf")

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
    anos = a1 - a0 + 1
    con.execute(f"""create table denom_q as
      select i.ivs_quartil q, p.faixa_etaria fx, sum(p.populacao)*{anos} py
      from pop_mun_fx p join ivs i using(municipio_cod) group by 1,2""")
    con.execute(f"""create table ob_q as
      select i.ivs_quartil q, f.faixa_etaria fx, f.causabas_3, sum(f.obitos) ob
      from faixa f join ivs i using(municipio_cod)
      where f.ano between {a0} and {a1} and not f.preliminar group by 1,2,3""")

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
      group by 1,2,3 order by razao_Q4_Q1 desc""").df(), "tab09_sitio_por_vulnerabilidade")

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
        return (pd.DataFrame(linhas)
                .sort_values("taxa_padronizada_100k", ascending=False, ignore_index=True))

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
      order by obitos_neoplasia desc""").df(), "tab13_raca_acesso_30_69")

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
    return f"{int(n):,}".replace(",", ".")


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
    linhas = [
        ("Fonte dos óbitos", "SIM/DataSUS — .dbc por UF (2015–2021, 2024) e "
                             "CSV nacional do OpenDataSUS (2022–2023)"),
        ("Período consolidado", f"{ini}–{fim}"),
        ("Recorte de causa", "CID-10 C00–C97 (neoplasias malignas), causa básica "
                             "truncada em três caracteres"),
        ("Óbitos em D00–D48, excluídos do recorte", _br(dd48[0])),
        ("D00–D48 como fração do capítulo II", f"{100 * dd48[1]:.1f}%".replace(".", ",")),
        ("Óbitos por neoplasia maligna", _br(tot)),
        ("Denominador populacional", "IBGE — população por UF, ano e faixa etária"),
        ("População padrão", "Brasil, Censo 2022 (método direto)"),
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
    print("\n=== 2. decomposição do aumento 2015→2024 ===")
    decomposicao(con)
    print("\n=== 3. contrafactual: risco de 2019 mantido ===")
    contrafactual(con)
    print("\n=== 4. sítios por idade e por sexo ===")
    sitios(con)
    print("\n=== 5. território ===")
    territorio(con)
    print("\n=== 6. vulnerabilidade municipal ===")
    vulnerabilidade(con)
    print("\n=== 7. eixo social (microdado 2022–2023) ===")
    social(con)
    print("\n=== 8. números de enquadramento ===")
    base(con)
    print(f"\n[done] tabelas em {SAIDA.relative_to(ROOT).as_posix()}")


if __name__ == "__main__":
    main()
