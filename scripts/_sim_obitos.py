"""
_sim_obitos.py — a definição única de "o que conta como óbito" no SIM
======================================================================

Extraído de `pipeline_v2.py`, que continua sendo o dono do dado, para que
`pipeline_mortalidade_causa_municipio.py` derive a MESMA tabela intermediária
em vez de reescrever a regra.

POR QUE COMPARTILHAR EM VEZ DE COPIAR
-------------------------------------
A derivação parece trivial — quatro `substr` e um filtro — e é exatamente por
isso que copiá-la seria perigoso. Ela codifica decisões que não são óbvias
olhando o resultado:

  * óbito fetal (`TIPOBITO = 1`) fica de fora, e ausente conta como não fetal —
    filtro correto que HOJE não remove nada, porque as duas fontes trazem 100%
    de `TIPOBITO = 2`; o óbito fetal está em `SIM/CID10/DOFET`, não coletado.
    Vale como defesa, não como recorte ativo;
  * a causa básica é truncada em 3 caracteres, o grão de *categoria* da CID-10;
  * `CODMUNRES` vazio vira '000000' em vez de NULL, para não sumir num join;
  * a data vem de `DTOBITO` em DDMMAAAA, com `lpad` porque o campo perde o
    zero à esquerda em janeiro–setembro.

Duas cópias dessas regras divergem em silêncio, e a divergência apareceria como
um total de óbitos que não bate entre duas tabelas publicadas — o tipo de
defeito que ninguém encontra olhando um número só. É o mesmo motivo de
`_publicacao.py` e `_series_forecast.py` existirem.

O contrato é `obitos_t`: uma linha por óbito, com ano, mês, município,
`causabas_3`, capítulo, sexo e faixa etária. Quem quiser um grão novo agrega
daqui — não redefine o óbito.
"""
from __future__ import annotations

from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw" / "SIM"
RAW_DBC = RAW / "dbc"

#: Anos servidos pelo CSV nacional do OpenDataSUS; os demais vêm de .dbc por UF.
#:
#: 2024 SAIU daqui em 2026-09-02, e o motivo é dado faltando, não preferência.
#: O `DO24OPEN.csv` que estava em disco trazia **1.426.346** óbitos; os 27
#: arquivos `.dbc` do DORES trazem **1.532.015**. São 105.669 óbitos a menos,
#: 6,9% do ano, e a diferença aparece SÓ em 2024 — 2015 a 2023 batem exatamente
#: entre as duas rotas, o que descarta divergência de definição.
#:
#: O efeito não era cosmético. Com o CSV, 2024 ficava 0,6% ABAIXO da tendência
#: 2015–2019 e parecia "volta ao normal" depois da pandemia; com o dado
#: completo, fica 6,7% ACIMA, mais alto que 2023. A leitura epidemiológica se
#: inverte.
#:
#: Some-se que o S3 do OpenDataSUS passou a responder 403 a HEAD e GET nesse
#: caminho: a rota do CSV está quebrada de qualquer forma. 2022 e 2023 seguem
#: aqui porque conferem exatamente com o `.dbc` e os arquivos já estão em disco;
#: migrá-los é limpeza, não correção.
ANOS_CSV = {2022, 2023}

#: Categorias da CID-10 para dengue, incluindo a que o Brasil passou a usar.
#:
#: Medido em 2026-09-03, comparando 2024 e 2025 na mesma rota do FTP:
#:
#:     2024   A90 = 5.237   A91 = 1.504   A97 = 0
#:     2025   A90 = 0       A91 = 0       A97 = 2.024
#:
#: É uma troca COMPLETA, não uma migração gradual. O Brasil adotou o A97 da
#: atualização da CID-10 (A97.0 sem sinais de alarme, A97.1 com sinais, A97.2
#: grave, A97.9 não especificada) e abandonou A90/A91 de uma vez.
#:
#: Nada quebrou ainda porque toda análise publicada é 2015–2024. O dia em que
#: alguém estender a série sem isto, a dengue simplesmente SOME — e some sem
#: erro, que é o pior modo de sumir. É o mesmo tipo de armadilha do B34: o
#: código não diz o que a doença é.
CIDS_DENGUE = ("A90", "A91", "A97")

#: Anos que o DataSUS ainda NÃO fechou. Moram em `SIM/PRELIM/DORES`, não em
#: `CID10/DORES`, e a distinção é analítica, não de caminho.
#:
#: Dado preliminar tem a cauda incompleta — foi ela que, no CSV de 2024, fez o
#: número de pares de causa significativos saltar de 7.030 para 20.234 e inverteu
#: a leitura do excesso do ano. Por isso o ano preliminar entra na base MARCADO,
#: e quem analisa filtra por `ANOS_CONSOLIDADOS` de propósito, não por descuido.
ANOS_PRELIMINARES = {2025}

#: A série fechada. É o que o artigo analisa, e o que qualquer análise deve usar
#: salvo decisão explícita em contrário.
ANOS_CONSOLIDADOS = tuple(range(2015, 2025))

#: Tudo que a base cobre, do mais antigo ao mais recente.
ANOS_COBERTOS = tuple(sorted(set(ANOS_CONSOLIDADOS) | ANOS_PRELIMINARES))

#: Colunas mínimas que a derivação exige das duas fontes.
COLUNAS = ["TIPOBITO", "DTOBITO", "IDADE", "SEXO", "CODMUNRES", "LOCOCOR", "CAUSABAS"]


#: Faixas dos capítulos da CID-10, usadas para traduzir `causabas_3` em capítulo.
#:
#: Mora aqui, e não em `pipeline_v2.py`, por duas razões. A primeira é a mesma
#: do resto do módulo: uma definição só. A segunda é operacional — importar de
#: `pipeline_v2` arrastaria `scipy`, `requests` e a árvore inteira de coleta
#: para dentro de qualquer teste que toque nesta derivação, e `scipy` não está
#: em `requirements-test.txt`. O CI quebraria por uma dependência que a
#: derivação não usa.
#:
#: O capítulo XXII existe na lista e NÃO aparece no dado: o SIM brasileiro nunca
#: usou U07 para COVID-19, codificando-a como B34.2. Ver
#: `pipeline_mortalidade_causa_municipio.py`.
CID10_CAPITULOS = [
    ("I",     1, "A00", "B99", "Algumas doenças infecciosas e parasitárias"),
    ("II",    2, "C00", "D48", "Neoplasias (tumores)"),
    ("III",   3, "D50", "D89", "Doenças do sangue e dos órgãos hematopoéticos e transtornos imunitários"),
    ("IV",    4, "E00", "E90", "Doenças endócrinas, nutricionais e metabólicas"),
    ("V",     5, "F00", "F99", "Transtornos mentais e comportamentais"),
    ("VI",    6, "G00", "G99", "Doenças do sistema nervoso"),
    ("VII",   7, "H00", "H59", "Doenças do olho e anexos"),
    ("VIII",  8, "H60", "H95", "Doenças do ouvido e da apófise mastóide"),
    ("IX",    9, "I00", "I99", "Doenças do aparelho circulatório"),
    ("X",    10, "J00", "J99", "Doenças do aparelho respiratório"),
    ("XI",   11, "K00", "K93", "Doenças do aparelho digestivo"),
    ("XII",  12, "L00", "L99", "Doenças da pele e do tecido subcutâneo"),
    ("XIII", 13, "M00", "M99", "Doenças do sistema osteomuscular e do tecido conjuntivo"),
    ("XIV",  14, "N00", "N99", "Doenças do aparelho geniturinário"),
    ("XV",   15, "O00", "O99", "Gravidez, parto e puerpério"),
    ("XVI",  16, "P00", "P96", "Algumas afecções originadas no período perinatal"),
    ("XVII", 17, "Q00", "Q99", "Malformações congênitas, deformidades e anomalias cromossômicas"),
    ("XVIII",18, "R00", "R99", "Sintomas, sinais e achados anormais não classificados em outra parte"),
    ("XIX",  19, "S00", "T98", "Lesões, envenenamento e algumas outras consequências de causas externas"),
    ("XX",   20, "V01", "Y98", "Causas externas de morbidade e de mortalidade"),
    ("XXI",  21, "Z00", "Z99", "Fatores que influenciam o estado de saúde e o contato com os serviços de saúde"),
    ("XXII", 22, "U00", "U99", "Códigos para propósitos especiais (inclui COVID-19: U07)"),
]


def criar_tabela_capitulos(con: duckdb.DuckDBPyConnection,
                           nome: str = "cid10_cap") -> None:
    """Materializa `CID10_CAPITULOS` na conexão, para o join da derivação."""
    con.execute(f"CREATE OR REPLACE TABLE {nome} "
                "(capitulo TEXT, capitulo_num SMALLINT, ini TEXT, fim TEXT, descricao TEXT)")
    con.executemany(f"INSERT INTO {nome} VALUES (?,?,?,?,?)", CID10_CAPITULOS)


def sql_uniao_fontes(anos: list[int]) -> str:
    """SQL que une CSV nacional e .dbc por UF cobrindo `anos`.

    Levanta se algum ano pedido não tiver arquivo — ausência de fonte é falha
    de coleta, não recorte silencioso. Ver [[coleta-ausencia-vs-falha]].
    """
    anos_csv = sorted(set(anos) & ANOS_CSV)
    anos_dbc = sorted(set(anos) - ANOS_CSV)

    faltando = [a for a in anos_csv if not (RAW / f"DO{str(a)[2:]}OPEN.csv").exists()]
    faltando += [a for a in anos_dbc if not list(RAW_DBC.glob(f"DO??{a}.parquet"))]
    if faltando:
        raise SystemExit(
            f"SIM: sem arquivo local para {faltando}. Rode `pipeline_v2.py` para "
            "baixar antes de derivar — processar o que existe publicaria um "
            "recorte incompleto com exit 0.")

    fontes = []
    if anos_csv:
        files = ", ".join(f"'{RAW / f'DO{str(a)[2:]}OPEN.csv'}'" for a in anos_csv)
        fontes.append(f"""
            SELECT {', '.join(COLUNAS)}
            FROM read_csv([{files}], delim=';', header=true, quote='"',
                          all_varchar=true, union_by_name=true)""")
    if anos_dbc:
        globs = ", ".join(f"'{RAW_DBC}/DO??{a}.parquet'" for a in anos_dbc)
        fontes.append(f"""
            SELECT {', '.join(COLUNAS)}
            FROM read_parquet([{globs}])""")
    return " UNION ALL ".join(fontes)


def contar_fetais(con: duckdb.DuckDBPyConnection, anos: list[int]) -> int:
    """Quantos registros das fontes são óbito fetal.

    Existe para a metodologia não mentir por omissão. Ela afirma que a base não
    tem óbito fetal, e a razão é a FONTE, não o filtro: o óbito fetal mora em
    `SIM/CID10/DOFET`, arquivo separado que este projeto não coleta. Medido em
    2026-09-02, os 14.378.827 registros das duas origens trazem 100% de
    `TIPOBITO = 2`.

    Se um dia isto devolver diferente de zero, a afirmação da metodologia passa
    a ser sobre o filtro, e o texto precisa mudar junto. É o mesmo motivo de a
    guarda de U07 existir em `pipeline_mortalidade_causa_municipio.py`.
    """
    union = sql_uniao_fontes(anos)
    return int(con.execute(
        f"SELECT count(*) FROM ({union}) WHERE trim(COALESCE(TIPOBITO,'')) = '1'"
    ).fetchone()[0])


def criar_obitos_t(con: duckdb.DuckDBPyConnection, anos: list[int],
                   tabela_capitulos: str = "cid10_cap") -> None:
    """Cria `obitos_t`: uma linha por óbito não fetal, já derivada.

    `tabela_capitulos` precisa existir na conexão com (capitulo, ini, fim) —
    é o que traduz `causabas_3` em capítulo da CID-10.
    """
    union = sql_uniao_fontes(anos)
    con.execute(f"""
        CREATE OR REPLACE TABLE obitos_t AS
        WITH t AS (
            SELECT
                lpad(DTOBITO, 8, '0')                           AS dt,
                COALESCE(NULLIF(trim(CODMUNRES), ''), '000000') AS municipio_cod,
                upper(COALESCE(trim(CAUSABAS), ''))             AS causabas,
                trim(COALESCE(SEXO, ''))                        AS sexo_raw,
                trim(COALESCE(LOCOCOR, ''))                     AS lococor,
                trim(COALESCE(IDADE, ''))                       AS idade_raw
            FROM ({union})
            WHERE COALESCE(NULLIF(trim(TIPOBITO), ''), '2') <> '1'
        ),
        d AS (
            SELECT
                TRY_CAST(substr(dt, 5, 4) AS SMALLINT)  AS ano,
                TRY_CAST(substr(dt, 3, 2) AS SMALLINT)  AS mes,
                municipio_cod,
                substr(causabas, 1, 3)                  AS causabas_3,
                CASE sexo_raw WHEN '1' THEN 'M' WHEN '2' THEN 'F'
                              WHEN 'M' THEN 'M' WHEN 'F' THEN 'F'
                              ELSE 'I' END              AS sexo,
                lococor,
                CASE
                    WHEN idade_raw = '' THEN NULL
                    WHEN substr(lpad(idade_raw, 3, '0'), 1, 1) = '4'
                        THEN TRY_CAST(substr(lpad(idade_raw, 3, '0'), 2, 2) AS INT)
                    WHEN substr(lpad(idade_raw, 3, '0'), 1, 1) = '5'
                        THEN 100 + COALESCE(TRY_CAST(substr(lpad(idade_raw, 3, '0'), 2, 2) AS INT), 0)
                    WHEN substr(lpad(idade_raw, 3, '0'), 1, 1) IN ('0','1','2','3') THEN 0
                    ELSE NULL
                END                                     AS idade_anos
            FROM t
        )
        SELECT
            d.ano, d.mes,
            make_date(d.ano, d.mes, 1)                  AS mes_competencia,
            d.municipio_cod, d.causabas_3,
            COALESCE(c.capitulo, 'N/D')                 AS capitulo_cid,
            d.sexo,
            CASE
                WHEN d.idade_anos IS NULL THEN 'IGN'
                WHEN d.idade_anos < 1   THEN '<1'
                WHEN d.idade_anos <= 4  THEN '1-4'
                WHEN d.idade_anos <= 14 THEN '5-14'
                WHEN d.idade_anos <= 29 THEN '15-29'
                WHEN d.idade_anos <= 44 THEN '30-44'
                WHEN d.idade_anos <= 59 THEN '45-59'
                WHEN d.idade_anos <= 74 THEN '60-74'
                ELSE '75+'
            END                                         AS faixa_etaria,
            (d.lococor = '1')                           AS is_hospital,
            (d.lococor = '3')                           AS is_domicilio
        FROM d
        LEFT JOIN {tabela_capitulos} c
               ON d.causabas_3 >= c.ini AND d.causabas_3 <= c.fim
        WHERE d.ano IN ({','.join(str(a) for a in anos)}) AND d.mes BETWEEN 1 AND 12
    """)


def caminho_populacao(refs) -> Path:
    """Resolve o parquet de população pelo padrão, nunca pelo ano literal.

    O arquivo é nomeado com a janela que contém (`populacao_2015_2025.parquet`),
    então estender a série RENOMEIA o arquivo. Dois scripts vivos —
    `reconciliacao_denominador` e `sensibilidade_excesso_idade` — carregavam
    `populacao_2015_2024.parquet` como literal e passaram a apontar para um
    arquivo que deixou de existir no momento em que 2025 entrou.

    Ano cravado em caminho é uma bomba com data marcada: não quebra quando se
    escreve, quebra quando alguém estende a série meses depois. Aqui a janela
    mais recente vence, e a ausência é um erro alto, não um `FileNotFoundError`
    a trinta linhas de distância.
    """
    refs = Path(refs)
    achados = sorted(refs.glob("populacao_*_*.parquet"))
    if not achados:
        raise SystemExit(
            f"[populacao] nenhum populacao_*_*.parquet em {refs} — "
            "rode `python scripts/pipeline_v2.py` para reconstruir o denominador")
    return max(achados, key=lambda p: int(p.stem.rsplit("_", 1)[1]))
