"""
pipeline_projecao_ibge.py — o denominador oficial pós-Censo, por idade simples
==============================================================================

Coleta as **Projeções da População, Revisão 2024** do IBGE — população por
unidade da federação, ano (2000–2070), idade simples (0 a 90+) e sexo — e grava
`data/refs/pop_proj2024_uf_ano_idade.parquet`.

POR QUE ESTA SÉRIE EXISTE, E POR QUE ELA SUBSTITUI AS OUTRAS DUAS
------------------------------------------------------------------
Auditado em 2026-09-07, o projeto tinha **três** denominadores conviviendo na
mesma análise, e nenhum servia sozinho:

    série                        Brasil 2022    estrutura etária
    pop_idade_uf_ano (proj. 2018)  214.828.540  coerente, mas PRÉ-Censo
    Censo 2022 (dim_pop_faixa)     203.080.756  enumerada, sem correção de
                                                subcontagem
    reconciliada (do projeto)      203.080.756  total certo, forma etária
                                                APROXIMADA — erra +9,1% em
                                                0–4 e −5,1% em 60–74
    projeção rev. 2024 (esta)      210.862.983  oficial, reconciliada com a
                                                Pesquisa de Pós-Enumeração

O erro da reconciliada é o que mais importa aqui e é o menos visível: ela acerta
o total e desloca a massa etária, com o maior desvio negativo exatamente em
60–74, que é onde o câncer mata. Um denominador 5% baixo nessa faixa infla a
taxa padronizada sem que nada no total denuncie.

E a diferença entre Censo e projeção **não é erro do Censo**: a Pesquisa de
Pós-Enumeração mede a subcontagem censitária, e o IBGE reconcilia. Para uma taxa
de mortalidade o denominador correto é a população em risco — inclusive quem o
recenseamento não encontrou —, porque o numerador conta o óbito dessa pessoa do
mesmo jeito. Usar a contagem bruta superestima toda taxa em ~3,8%.

O EFEITO É SELETIVO, E É POR ISSO QUE A TROCA IMPORTA
------------------------------------------------------
A reconciliação acrescenta população quase toda em idade jovem e adulta: em
2022 o total sobe 3,8% sobre o Censo e a faixa de 75 ou mais **cai** 1,07%.
Consequência medida: a taxa BRUTA de câncer desce com a troca, e a
PADRONIZADA quase não se move — o que é a forma correta de um denominador
melhor se comportar, e serve de verificação.

O QUE A IDADE SIMPLES DESTRAVA
-------------------------------
As sete faixas do projeto (três delas de quinze anos, a última aberta em 75)
eram limitação declarada do artigo de neoplasias. Com idade simples dá para
padronizar em grupos quinquenais e para montar o recorte **30 a 69 anos**, que é
a definição da OMS de mortalidade prematura por doença crônica não transmissível
e que nenhuma faixa do projeto permitia recortar.

Fonte: https://ftp.ibge.gov.br/Projecao_da_Populacao/Projecao_da_Populacao_2024/
Relatório metodológico: Série Relatórios Metodológicos v. 40, 3ª edição.

Uso: .venv311/Scripts/python scripts/pipeline_projecao_ibge.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import duckdb

from _publicacao import sha256_de
from _saida import Resultado

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw" / "IBGE"
REFS = ROOT / "data" / "refs"
DESTINO = REFS / "pop_proj2024_uf_ano_idade.parquet"

URL = ("https://ftp.ibge.gov.br/Projecao_da_Populacao/Projecao_da_Populacao_2024/"
       "projecoes_2024_tab1_idade_simples.xlsx")

#: As 27 unidades da federação. A planilha traz também Brasil e as cinco grandes
#: regiões nas mesmas colunas; filtrar por esta lista é o que impede somar o país
#: duas vezes — o modo silencioso de errar aqui, porque o total simplesmente
#: dobra sem nenhuma linha parecer estranha.
UFS = ("RO", "AC", "AM", "RR", "PA", "AP", "TO", "MA", "PI", "CE", "RN", "PB",
       "PE", "AL", "SE", "BA", "MG", "ES", "RJ", "SP", "PR", "SC", "RS", "MS",
       "MT", "GO", "DF")

#: Cabeçalho na linha 6 da planilha; as três primeiras são título e subtítulo.
#: `BZ` cobre as 71 colunas de ano (2000–2070) mais as cinco de identificação.
FAIXA_PLANILHA = "A6:BZ12000"

#: População do Brasil em 2024 publicada pelo IBGE nesta revisão. Serve de
#: verificação contra fonte externa: se a extração devolver outro número, ou o
#: arquivo mudou ou o recorte está errado, e nos dois casos a série não deve ser
#: gravada. É a mesma disciplina da guarda de 200 milhões em `analise_neoplasias`.
BRASIL_2024 = 212_583_750

#: 91 idades (0 a 90+) x 3 sexos x 33 locais (Brasil, 5 regiões, 27 UFs).
LINHAS_ESPERADAS = 91 * 3 * 33


def baixar() -> Path:
    """Baixa a planilha se não estiver em disco. `data/raw/` não entra no git."""
    RAW.mkdir(parents=True, exist_ok=True)
    alvo = RAW / "projecoes_2024_tab1_idade_simples.xlsx"
    if alvo.exists():
        print(f"[cache] {alvo.name} ({alvo.stat().st_size / 1e6:.1f} MB)")
        return alvo
    import requests
    print(f"[ibge] baixando {URL.rsplit('/', 1)[1]}…", flush=True)
    r = requests.get(URL, timeout=600, stream=True)
    if r.status_code != 200:
        raise SystemExit(f"IBGE: HTTP {r.status_code} — sem a projeção revisão 2024 "
                         "o denominador oficial não pode ser construído.")
    with open(alvo, "wb") as fh:
        for pedaco in r.iter_content(1 << 20):
            fh.write(pedaco)
    print(f"[ibge] {alvo.name}: {alvo.stat().st_size / 1e6:.1f} MB")
    return alvo


def extrair(con: duckdb.DuckDBPyConnection, planilha: Path) -> None:
    """Desempilha os 71 anos-coluna em linhas (uf, ano, idade, sexo, populacao)."""
    con.execute("INSTALL excel; LOAD excel;")
    con.execute(f"""create table bruto as
      select * from read_xlsx('{planilha.as_posix()}', header=true,
                              range='{FAIXA_PLANILHA}', all_varchar=true)""")

    n = con.execute("select count(*) from bruto "
                    "where SEXO is not null and try_cast(IDADE as int) is not null"
                    ).fetchone()[0]
    if n != LINHAS_ESPERADAS:
        raise SystemExit(f"planilha do IBGE: {n:,} linhas úteis, esperadas "
                         f"{LINHAS_ESPERADAS:,} (91 idades x 3 sexos x 33 locais). "
                         "O leiaute mudou; conferir antes de gravar.")

    anos = [c[0] for c in con.execute("describe bruto").fetchall() if c[0].isdigit()]
    if len(anos) != 71:
        raise SystemExit(f"planilha do IBGE: {len(anos)} colunas de ano, esperadas 71.")

    # UNPIVOT em vez de 71 UNION ALL: uma varredura, e o nome da coluna vira dado.
    ufs = ", ".join(f"'{u}'" for u in UFS)
    colunas = ", ".join(f'"{a}"' for a in anos)
    con.execute(f"""create table proj as
      select SIGLA as uf_sigla,
             try_cast(ano as smallint) as ano,
             try_cast(IDADE as smallint) as idade,
             case SEXO when 'Homens' then 'M' when 'Mulheres' then 'F' else 'T' end as sexo,
             try_cast(populacao as bigint) as populacao
      from (select * from bruto where SIGLA in ({ufs}) and SEXO is not null
                                  and try_cast(IDADE as int) is not null)
      UNPIVOT (populacao for ano in ({colunas}))""")


def conferir(con: duckdb.DuckDBPyConnection) -> None:
    """Três verificações que falham alto em vez de gravar série errada."""
    nulos = con.execute("select count(*) from proj where populacao is null").fetchone()[0]
    if nulos:
        raise SystemExit(f"{nulos:,} células sem valor numérico na projeção.")

    soma_sexo = con.execute("""
      select sum(case when sexo='T' then populacao else 0 end),
             sum(case when sexo in ('M','F') then populacao else 0 end)
      from proj""").fetchone()
    if soma_sexo[0] != soma_sexo[1]:
        raise SystemExit(f"homens + mulheres ({soma_sexo[1]:,}) não fecham com ambos "
                         f"os sexos ({soma_sexo[0]:,}).")

    br24 = con.execute("select sum(populacao) from proj where ano=2024 and sexo='T'"
                       ).fetchone()[0]
    if br24 != BRASIL_2024:
        raise SystemExit(f"Brasil 2024 pela soma das 27 UFs: {br24:,}. O IBGE publica "
                         f"{BRASIL_2024:,} nesta revisão. A extração não confere.")
    print(f"[confere] soma das 27 UFs em 2024 = {br24:,}, igual ao publicado")
    print(f"[confere] homens + mulheres = ambos os sexos ({soma_sexo[0]:,} pessoas-ano)")


def main() -> int:
    res = Resultado("scripts/pipeline_projecao_ibge.py")
    con = duckdb.connect()
    extrair(con, baixar())
    conferir(con)

    REFS.mkdir(parents=True, exist_ok=True)
    # A escrita é um COPY do DuckDB, não passa pelo `escrever_parquet` — então o
    # sha256 é tirado à mão, antes e depois, para responder a mesma pergunta.
    antes = sha256_de(DESTINO) if DESTINO.exists() else None
    con.execute(f"""copy (select * from proj order by uf_sigla, ano, sexo, idade)
                    to '{DESTINO.as_posix()}' (format parquet, compression zstd)""")
    res.registrar(DESTINO.stem, sha256_de(DESTINO) != antes)
    linhas = con.execute("select count(*) from proj").fetchone()[0]
    print(f"[parquet] {DESTINO.name}: {linhas:,} linhas, "
          f"{DESTINO.stat().st_size / 1e6:.2f} MB")

    print("\n  Brasil, ambos os sexos, pela soma das UFs:")
    for ano, pop in con.execute("""select ano, sum(populacao) from proj
        where sexo='T' and ano in (2015, 2019, 2022, 2024) group by 1 order by 1""").fetchall():
        print(f"    {ano}: {pop:>15,}")
    print("\n  para comparação — Censo 2022 enumerou 203.080.756; a diferença é a "
          "\n  subcontagem medida pela Pesquisa de Pós-Enumeração, não erro de extração.")
    return res.relatar()


if __name__ == "__main__":
    sys.exit(main())
