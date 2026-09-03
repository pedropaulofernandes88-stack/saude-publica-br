"""
pipeline_mortalidade_causa_municipio.py — mortalidade por CAUSA e MUNICÍPIO
===========================================================================

Óbitos por município × categoria da CID-10 (`causabas_3`) × ano, e a mesma coisa
por mês. É o grão que faltava: até aqui a base tinha as duas metades separadas,

    mart_mortalidade_municipio   município × CAPÍTULO × ano   (22 capítulos)
    mart_mortalidade_causa       CID-3 × ano, mas só por UF

e nenhuma tabela cruzava município com CID. Ela nunca exigiu coleta nova — o
grão já existia dentro de `obitos_t` e era agregado para cima antes de virar
mart. Ver `_sim_obitos.py`, que agora guarda a derivação para os dois usarem.

PARA QUE SERVE
--------------
Análise não supervisionada de perfil de mortalidade municipal: cada município
vira um ponto, as coordenadas são a composição de causas, e a clusterização diz
quem morre de forma parecida. Também alimenta correlação cruzada longitudinal
(daí o grão mensal) e detecção de mudança de padrão por CID.

TRÊS ARMADILHAS MEDIDAS, E O QUE SE FEZ COM CADA UMA
----------------------------------------------------
**1. B34 é COVID-19, não "infecção viral não especificada".** O SIM brasileiro
NUNCA usou U07.1 — zero registros em 2015–2024. Codificou COVID como B34.2, que
truncado em três caracteres vira B34:

    2015–2019   60 a 240 óbitos por ano
    2020        213.233
    2021        425.218
    2024          5.414

Pela descrição da CID, B34 é exatamente o tipo de código que um filtro de
"causas inespecíficas" descartaria — e descartá-lo apaga a pandemia da matriz.
Por isso `dim_cid10_informativo` marca `is_covid`, e a guarda `conferir_covid()`
ABORTA se U07 aparecer: se o DataSUS recodificar, o rótulo precisa mudar junto.

**2. Qualidade do registro é confundidor de primeira ordem.** A proporção de
causas mal definidas varia de 0,64% a 14,86% entre municípios (P5–P95), 23
vezes. Clusterizar composição de causa recupera, em parte, *quem registra bem* —
não *quem adoece diferente*. `is_mal_definida` marca o capítulo XVIII, e
`mart_qualidade_registro_municipio` já mede o indicador por município: quem
analisar deve controlar, não ignorar.

**3. Número pequeno.** A mediana é 77 óbitos por município-ano. Com 1.571
categorias de CID, o perfil do município mediano é quase todo zero-ou-um, e
ruído multinomial se parece com estrutura. É o que a guarda do modelo nulo
existe para medir — ver abaixo.

A TABELA SAI COMPLETA; O FILTRO É DADO, NÃO CORTE
--------------------------------------------------
Seria fácil publicar já filtrada pelos CIDs "informativos". Não se faz isso: o
limiar é escolha analítica, e cravá-lo no dado publicado esconde a escolha de
quem baixa. Medido, filtrar também não economiza nada — restringir aos CIDs
presentes em >=25% dos municípios leva o grão mensal de 7.700.720 para 7.081.939
células, porque CID raro contribui com poucas células de qualquer forma.

Então tudo é publicado, e `dim_cid10_informativo` traz por CID a prevalência
municipal e as marcas, para o filtro ser reproduzível e discutível.

A GUARDA DO MODELO NULO
-----------------------
`guarda_modelo_nulo()` roda o PCA que a tabela existe para permitir e o compara
com um nulo multinomial: cada município sorteia os SEUS N óbitos da composição
NACIONAL. Se o observado não superar o nulo, o que o PCA acharia seria ruído de
amostragem, não epidemiologia.

Medido nesta base (semente fixa, municípios com >=500 óbitos no período):

    grão CID-3 (366 CIDs)   PC1 = 5,3%   nulo 0,5%   ->  10,2x
    grão capítulo (20)      PC1 = 19,7%  nulo 6,9%   ->   2,9x

O capítulo tem variância explicada MAIOR e sinal MENOR. É o resultado que
justifica usar CID e não capítulo, e ele só aparece contra o nulo: PC1 de 5,3%
lido sozinho parece ausência de estrutura, e seria rejeitado.

A razão vai para `achados.json` a cada execução, com a mtime dos marts que a
originaram — para o número não envelhecer em silêncio quando o dado mudar.

Uso:
  .venv311/Scripts/python scripts/pipeline_mortalidade_causa_municipio.py
  .venv311/Scripts/python scripts/pipeline_mortalidade_causa_municipio.py --no-upload
  .venv311/Scripts/python scripts/pipeline_mortalidade_causa_municipio.py --anos 2023 2024
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

import duckdb
import numpy as np
import pandas as pd
import requests

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _achados import registrar  # noqa: E402
from _publicacao import carregar_env, conferir_chave_unica, escrever_parquet  # noqa: E402
from _sim_obitos import (  # noqa: E402
    ANOS_COBERTOS,
    ANOS_CONSOLIDADOS,
    ANOS_PRELIMINARES,
    contar_fetais,
    criar_obitos_t,
    criar_tabela_capitulos,
)
from _supabase_key import chave_escrita  # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parents[1]
MARTS = ROOT / "data" / "marts"
PRODUTOR = "scripts/pipeline_mortalidade_causa_municipio.py"

#: A base COBRE o preliminar; quem analisa recorta. Ver ANOS_CONSOLIDADOS.
ANOS = list(ANOS_COBERTOS)

#: Capítulo XVIII (R00–R99): sintomas, sinais e achados anormais. É o balde de
#: "não se sabe", e o mesmo que `mart_qualidade_registro_municipio` mede.
CAPITULO_MAL_DEFINIDAS = "XVIII"

#: COVID-19 no SIM brasileiro. Ver a nota de cabeçalho — não é escolha, é o que
#: o dado traz.
CID_COVID = "B34"
ANO_COVID_INICIO = 2020

#: Prevalência municipal mínima para um CID entrar como "informativo".
#: 25% dos municípios deixa 297 CIDs de 1.571; 10% deixaria 510 e 50%, 153.
#: O corte é sugestão publicada, não filtro aplicado ao dado.
PREVALENCIA_INFORMATIVO = 0.25

#: Teto para óbitos sem faixa etária no grão etário. O medido em 2015–2024 é
#: 0,17%; 1% já seria alta suficiente para enviesar padronização por idade.
IGNORADO_MAXIMO = 0.01

#: Parâmetros da guarda do modelo nulo. A semente é fixa porque a razão vai
#: para `achados.json` e um número que muda a cada execução não é conferível.
NULO_CORTE_OBITOS = 500
NULO_SEMENTE = 7
#: Abaixo disto a matriz não tem mais estrutura que ruído multinomial, e algo
#: quebrou na construção — o valor medido é 10,2x.
NULO_LIMIAR = 2.0


# ---------------------------------------------------------------------------
# Construção
# ---------------------------------------------------------------------------

def construir(anos: list[int]) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    con = duckdb.connect()
    criar_tabela_capitulos(con)

    print(f"[sim] derivando óbitos {min(anos)}–{max(anos)}...", flush=True)
    criar_obitos_t(con, anos)
    n = con.execute("SELECT count(*) FROM obitos_t").fetchone()[0]
    fetais = contar_fetais(con, anos)
    print(f"[sim] {n:,} óbitos não fetais | {fetais:,} fetais removidos pelo filtro",
          flush=True)
    if fetais:
        print("[sim] ATENÇÃO: a metodologia afirma que a exclusão de óbito fetal vem da "
              "FONTE, não do filtro. Isso deixou de ser verdade — corrija o texto em "
              "site/app/metodologia/page.tsx e docs/preprint/.", flush=True)

    dim = pd.read_parquet(MARTS / "dim_municipio.parquet")
    con.register("dim_municipio", dim)

    print("[mart] anual: município × CID × ano...", flush=True)
    anual = con.execute("""
        SELECT o.municipio_cod,
               m.municipio_nome, m.uf_sigla, m.regiao,
               o.ano, o.causabas_3, o.capitulo_cid,
               count(*)::INT                    AS obitos,
               sum(o.is_hospital)::INT          AS obitos_hospital,
               sum(o.is_domicilio)::INT         AS obitos_domicilio
        FROM obitos_t o LEFT JOIN dim_municipio m USING (municipio_cod)
        GROUP BY 1,2,3,4,5,6,7
        ORDER BY 1,5,6
    """).df()

    print("[mart] mensal: município × CID × ano × mês...", flush=True)
    mensal = con.execute("""
        SELECT o.municipio_cod, m.uf_sigla,
               o.ano, o.mes, o.mes_competencia, o.causabas_3,
               count(*)::INT AS obitos
        FROM obitos_t o LEFT JOIN dim_municipio m USING (municipio_cod)
        GROUP BY 1,2,3,4,5,6
        ORDER BY 1,3,4,6
    """).df()

    print("[mart] etário: município × CID × ano × faixa...", flush=True)
    # Óbito com idade ignorada (0,17% do total) fica FORA desta tabela e só
    # dela: mantê-lo criaria uma faixa 'IGN' que nenhuma padronização sabe
    # ponderar, e removê-lo das outras quebraria a reconciliação.
    etario = con.execute("""
        SELECT o.municipio_cod, m.uf_sigla, o.ano, o.causabas_3, o.faixa_etaria, o.sexo,
               count(*)::INT AS obitos
        FROM obitos_t o LEFT JOIN dim_municipio m USING (municipio_cod)
        WHERE o.faixa_etaria <> 'IGN'
        GROUP BY 1,2,3,4,5,6
        ORDER BY 1,3,4,5
    """).df()

    print("[dim] vocabulário de CID com prevalência...", flush=True)
    # O DICIONÁRIO cobre tudo — inclusive códigos que só existem no ano
    # preliminar, como o A97 da dengue —, mas a PREVALÊNCIA e a marca
    # `informativo` são calculadas SÓ sobre os anos consolidados.
    #
    # Sem essa separação o preliminar entrava na análise pela porta do
    # vocabulário: ao acrescentar 2025, o conjunto de CIDs informativos passou
    # de 289 para 302 sem que ninguém tivesse mudado critério nenhum. Um filtro
    # cujo conteúdo depende de dado que a análise exclui não é um filtro, é um
    # vazamento com nome de filtro.
    consolidados = ",".join(str(a) for a in ANOS_CONSOLIDADOS)
    dimcid = con.execute(f"""
        SELECT o.causabas_3,
               any_value(o.capitulo_cid)              AS capitulo_cid,
               count(*)::INT                          AS obitos_total,
               count(DISTINCT o.municipio_cod) FILTER (WHERE o.ano IN ({consolidados}))::INT
                                                      AS municipios_com_registro,
               min(o.ano)::SMALLINT                   AS ano_min,
               max(o.ano)::SMALLINT                   AS ano_max
        FROM obitos_t o GROUP BY 1 ORDER BY 3 DESC
    """).df()
    con.close()

    n_mun = anual[anual.ano.isin(ANOS_CONSOLIDADOS)].municipio_cod.nunique()
    dimcid["prevalencia_municipal"] = (dimcid.municipios_com_registro / n_mun).round(4)
    dimcid["is_mal_definida"] = dimcid.capitulo_cid == CAPITULO_MAL_DEFINIDAS
    dimcid["is_covid"] = dimcid.causabas_3 == CID_COVID
    dimcid["informativo"] = (~dimcid.is_mal_definida
                             & (dimcid.prevalencia_municipal >= PREVALENCIA_INFORMATIVO))

    cats = MARTS / "dim_cid10_categoria.parquet"
    if cats.exists():
        dimcid = dimcid.merge(pd.read_parquet(cats), on="causabas_3", how="left")
    else:
        dimcid["descricao"] = None

    for df in (anual, mensal, etario):
        df["uf_sigla"] = df["uf_sigla"].fillna("ND")
        # A marca viaja no DADO, não num README. Quem baixa a tabela precisa
        # poder distinguir ano fechado de ano em consolidação sem consultar
        # nada — foi a ausência dessa distinção que deixou o 2024 truncado
        # circular por meses como se fosse definitivo.
        df["preliminar"] = df["ano"].isin(ANOS_PRELIMINARES)
    anual["municipio_nome"] = anual["municipio_nome"].fillna("Não identificado")
    anual["regiao"] = anual["regiao"].fillna("ND")
    mensal["mes_competencia"] = pd.to_datetime(mensal["mes_competencia"]).dt.date
    return anual, mensal, etario, dimcid


# ---------------------------------------------------------------------------
# Guardas
# ---------------------------------------------------------------------------

def conferir_reconciliacao(anual: pd.DataFrame) -> None:
    """Aborta se o total por município e ano divergir do mart já publicado.

    É a guarda mais forte do arquivo: `mart_mortalidade_municipio` foi
    publicado, baixado e tem checksum. Uma tabela nova derivada do mesmo SIM que
    não somasse o mesmo total estaria errada — ou estaria denunciando que a
    definição de óbito divergiu entre os dois produtores, que é justamente o
    risco que `_sim_obitos.py` existe para eliminar.
    """
    pub = pd.read_parquet(MARTS / "mart_mortalidade_municipio.parquet")
    pub = (pub[(pub.capitulo_cid == "TOTAL") & (pub.sexo == "TOTAL")]
           .groupby(["municipio_cod", "ano"], as_index=False).obitos.sum()
           .rename(columns={"obitos": "publicado"}))
    novo = anual.groupby(["municipio_cod", "ano"], as_index=False).obitos.sum()
    j = pub.merge(novo, on=["municipio_cod", "ano"], how="outer").fillna(0)
    dif = j[j.publicado != j.obitos]
    if len(dif):
        print(dif.head(10).to_string(index=False), flush=True)
        raise SystemExit(
            f"reconciliação: {len(dif):,} pares município×ano divergem de "
            "mart_mortalidade_municipio. A tabela NÃO será publicada.")
    print(f"[guarda] reconcilia com o publicado: {len(j):,} pares município×ano, "
          f"{int(j.publicado.sum()):,} óbitos", flush=True)


def conferir_covid(anual: pd.DataFrame) -> None:
    """Aborta se o SIM passar a usar U07, ou se B34 deixar de parecer COVID.

    As duas metades importam. Se U07 aparecer, o rótulo `is_covid=B34` fica
    errado e precisa mudar. Se B34 sumir dos anos de pandemia sem U07 aparecer,
    alguma coisa quebrou na derivação.
    """
    u07 = anual[anual.causabas_3.str.startswith("U0", na=False)]
    if len(u07):
        raise SystemExit(
            f"U07 apareceu no SIM ({int(u07.obitos.sum()):,} óbitos). O projeto "
            "assume COVID codificada como B34.2 — reveja `is_covid` em "
            "dim_cid10_informativo e a nota de cabeçalho ANTES de publicar.")

    if ANO_COVID_INICIO not in set(anual.ano):
        return
    pandemia = anual[(anual.causabas_3 == CID_COVID) & (anual.ano.between(2020, 2021))]
    total = int(pandemia.obitos.sum())
    if total < 100_000:
        raise SystemExit(
            f"B34 soma apenas {total:,} óbitos em 2020–2021; o esperado é "
            "centenas de milhares (COVID). A derivação provavelmente quebrou.")
    print(f"[guarda] B34 = COVID confirmado: {total:,} óbitos em 2020–2021, "
          "nenhum U07", flush=True)


def conferir_faixa_etaria(anual: pd.DataFrame, etario: pd.DataFrame) -> None:
    """Confere o grão etário contra o anual, descontando a idade ignorada.

    O grão etário é o ÚNICO que exclui óbito sem idade, e é por isso que ele
    não pode ser conferido pela igualdade simples que vale para os outros. A
    diferença tem de ser exatamente a contagem de `IGN` — nem mais, nem menos.

    Se a diferença crescer, ou o parser de idade quebrou ou o SIM passou a
    registrar idade pior; nos dois casos a padronização por idade que esta
    tabela existe para permitir fica enviesada, e em silêncio.
    """
    total_anual = int(anual.obitos.sum())
    total_etario = int(etario.obitos.sum())
    ignorados = total_anual - total_etario
    fracao = ignorados / total_anual
    print(f"[guarda] grão etário: {total_etario:,} óbitos, {ignorados:,} com idade "
          f"ignorada ({fracao:.3%})", flush=True)
    if ignorados < 0:
        raise SystemExit(
            f"grão etário tem {-ignorados:,} óbitos A MAIS que o anual — impossível, "
            "já que ele é um subconjunto. A agregação está errada.")
    if fracao > IGNORADO_MAXIMO:
        raise SystemExit(
            f"{fracao:.2%} dos óbitos sem faixa etária, acima do teto de "
            f"{IGNORADO_MAXIMO:.2%}. O medido em 2015–2024 é 0,17%; uma alta "
            "enviesaria qualquer padronização por idade.")

    # E a reconciliação por município e ano, que é onde um erro de join apareceria.
    a = anual.groupby(["municipio_cod", "ano"], as_index=False).obitos.sum()
    e = etario.groupby(["municipio_cod", "ano"], as_index=False).obitos.sum()
    j = a.merge(e, on=["municipio_cod", "ano"], how="outer",
                suffixes=("_anual", "_etario")).fillna(0)
    piores = j[j.obitos_etario > j.obitos_anual]
    if len(piores):
        print(piores.head(5).to_string(index=False), flush=True)
        raise SystemExit(
            f"{len(piores):,} pares município×ano têm mais óbitos no grão etário "
            "que no anual. A tabela NÃO será publicada.")


def conferir_vocabulario(dimcid: pd.DataFrame) -> None:
    """Reporta CIDs sem capítulo.

    Não aborta por existirem: são códigos inválidos do próprio SIM, e removê-los
    quebraria a reconciliação com o mart publicado. Aborta se virarem muitos,
    porque aí o problema é a tabela de capítulos, não o dado.
    """
    orfaos = dimcid[dimcid.capitulo_cid == "N/D"]
    if not len(orfaos):
        return
    n = int(orfaos.obitos_total.sum())
    print(f"[guarda] {len(orfaos)} CIDs fora da CID-10 ({n:,} óbitos): "
          f"{', '.join(orfaos.causabas_3)}", flush=True)
    if n > 1000:
        raise SystemExit(
            f"{n:,} óbitos com CID fora da CID-10 — acima do ruído esperado "
            "(2 óbitos em 2015–2024). Confira a tabela de capítulos.")


def _variancia_pcs(proporcoes: np.ndarray, k: int = 5) -> np.ndarray:
    """Fração da variância dos k primeiros componentes de uma matriz composicional.

    Padroniza cada coluna antes do SVD. Sem isso, o PC1 seria dominado pelas
    causas mais frequentes só por terem variância absoluta maior — a pergunta é
    qual causa DESVIA do padrão nacional, não qual mata mais.
    """
    centrado = proporcoes - proporcoes.mean(axis=0)
    desvio = centrado.std(axis=0)
    z = centrado[:, desvio > 0] / desvio[desvio > 0]
    z = z - z.mean(axis=0)
    valores = np.linalg.svd(z, full_matrices=False, compute_uv=False) ** 2
    return (valores / valores.sum())[:k]


def guarda_modelo_nulo(anual: pd.DataFrame, dimcid: pd.DataFrame) -> float:
    """Compara o PCA observado com um nulo multinomial e devolve a razão.

    O nulo preserva o que NÃO é epidemiologia: quantos óbitos cada município
    teve. Cada um sorteia os seus N da composição nacional. O que sobra acima
    disso é o que a clusterização pode legitimamente encontrar.
    """
    informativos = set(dimcid[dimcid.informativo].causabas_3)
    # Só o consolidado. A razão vai para `achados.json` e é comparada entre
    # execuções; misturar um ano preliminar — cuja cauda muda a cada reescrita
    # do DataSUS — faria o número oscilar por motivo que não é o dado.
    base = anual[anual.causabas_3.isin(informativos)
                 & anual.ano.isin(ANOS_CONSOLIDADOS)]
    matriz = base.pivot_table(index="municipio_cod", columns="causabas_3",
                              values="obitos", aggfunc="sum", fill_value=0)
    matriz = matriz[matriz.sum(axis=1) >= NULO_CORTE_OBITOS]
    if matriz.empty:
        raise SystemExit("modelo nulo: nenhum município acima do corte — matriz vazia")

    contagens = matriz.sum(axis=1).values
    obs = _variancia_pcs(matriz.div(matriz.sum(axis=1), axis=0).values)

    p_nacional = (matriz.sum(axis=0) / matriz.sum(axis=0).sum()).values
    rng = np.random.default_rng(NULO_SEMENTE)
    sim = np.vstack([rng.multinomial(n, p_nacional) for n in contagens]).astype(float)
    nulo = _variancia_pcs(sim / sim.sum(axis=1, keepdims=True))

    razao = float(obs[0] / nulo[0])
    print(f"[nulo] {matriz.shape[0]:,} municípios × {matriz.shape[1]} CIDs informativos "
          f"(>={NULO_CORTE_OBITOS} óbitos)", flush=True)
    print(f"[nulo] PC1 observado {obs[0]:.3f} | nulo {nulo[0]:.3f} | razão {razao:.2f}x",
          flush=True)
    print(f"[nulo] PC1-5 observado {np.round(obs, 3)}", flush=True)
    if razao < NULO_LIMIAR:
        raise SystemExit(
            f"modelo nulo: PC1 observado é apenas {razao:.2f}x o ruído multinomial "
            f"(limiar {NULO_LIMIAR}). A matriz perdeu estrutura — não publique sem "
            "entender o que mudou.")
    return razao


# ---------------------------------------------------------------------------
# Publicação
# ---------------------------------------------------------------------------

def subir(nome: str, df: pd.DataFrame, env: dict[str, str]) -> None:
    url, key = env["SUPABASE_URL"].rstrip("/"), chave_escrita(env)
    h = {"apikey": key, "Authorization": f"Bearer {key}",
         "Content-Type": "application/json",
         "Prefer": "return=minimal,resolution=merge-duplicates"}
    recs = df.astype(object).where(pd.notna(df), None).to_dict("records")
    for i in range(0, len(recs), 5000):
        corpo = json.dumps(recs[i:i + 5000], allow_nan=False,
                           default=lambda o: o.item() if hasattr(o, "item") else str(o))
        r = requests.post(f"{url}/rest/v1/{nome}", headers=h, data=corpo, timeout=300)
        if r.status_code not in (200, 201):
            raise RuntimeError(f"{nome}: HTTP {r.status_code} {r.text[:200]}")
    print(f"[supabase]   {nome}: {len(recs):,} OK", flush=True)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--no-upload", action="store_true")
    ap.add_argument("--anos", nargs="+", type=int, default=ANOS)
    args = ap.parse_args()
    anos = sorted(args.anos)

    anual, mensal, etario, dimcid = construir(anos)

    # Guardas antes de gravar: arquivo errado gravado já é arquivo errado.
    if anos == ANOS:
        conferir_reconciliacao(anual)
    else:
        print("[guarda] recorte parcial de anos — reconciliação pulada", flush=True)
    conferir_covid(anual)
    conferir_vocabulario(dimcid)
    conferir_chave_unica("mart_mortalidade_causa_municipio", anual,
                         ["municipio_cod", "ano", "causabas_3"])
    conferir_chave_unica("mart_mortalidade_causa_municipio_mes", mensal,
                         ["municipio_cod", "ano", "mes", "causabas_3"])
    conferir_chave_unica("mart_mortalidade_causa_municipio_faixa", etario,
                         ["municipio_cod", "ano", "causabas_3", "faixa_etaria", "sexo"])
    conferir_faixa_etaria(anual, etario)
    razao = guarda_modelo_nulo(anual, dimcid)

    for nome, df in (("mart_mortalidade_causa_municipio", anual),
                     ("mart_mortalidade_causa_municipio_mes", mensal),
                     ("mart_mortalidade_causa_municipio_faixa", etario),
                     ("dim_cid10_informativo", dimcid)):
        escrever_parquet(df, MARTS / f"{nome}.parquet", origem="pipeline", produtor=PRODUTOR)
        mb = (MARTS / f"{nome}.parquet").stat().st_size / 1e6
        print(f"[parquet] {nome}: {len(df):,} linhas, {mb:.1f} MB", flush=True)

    registrar("pca_mortalidade_razao_nulo", razao,
              fontes=["mart_mortalidade_causa_municipio"],
              descricao=("PC1 da composição de causas por município dividido pelo PC1 de "
                         f"um nulo multinomial de mesma contagem (semente {NULO_SEMENTE}, "
                         f"municípios com >={NULO_CORTE_OBITOS} óbitos, CIDs informativos)"))

    if args.no_upload:
        return

    # As duas tabelas de fato NÃO sobem ao Postgres: 3,6 e 7,7 milhões de linhas
    # estourariam o orçamento do cache (ver LIMITE_PADRAO_MB em diagnostico_banco.py). Ficam publicadas em Parquet
    # com checksum, `servida=False` no manifesto. Ver V036 e V034.
    env = carregar_env()
    subir("dim_cid10_informativo", dimcid, env)
    url, key = env["SUPABASE_URL"].rstrip("/"), chave_escrita(env)
    requests.post(f"{url}/rest/v1/meta_dataset",
                  headers={"apikey": key, "Authorization": f"Bearer {key}",
                           "Content-Type": "application/json",
                           "Prefer": "return=minimal,resolution=merge-duplicates"},
                  data=json.dumps(construir_meta(anos)), timeout=60)
    print("[done] mortalidade por causa e município concluída.", flush=True)


def construir_meta(anos) -> list[dict]:
    """As chaves de metadado deste pipeline, derivadas dos mesmos constantes.

    Extraída de `main()` pelo motivo em `pipeline_v2.construir_meta`: rodar o
    pipeline com `--no-upload` deixa o `meta_dataset` publicado descrevendo uma
    cobertura que já mudou, e a alternativa — reescrever as strings à mão —
    cria uma segunda definição que diverge da primeira sem avisar.
    """
    return [
                      {"chave": "fonte_mortalidade_causa_municipio",
                       "valor": ("SIM/DataSUS — óbitos por município e categoria da CID-10 "
                                 f"({min(anos)}–{max(anos)}), grão anual e mensal. "
                                 "COVID-19 aparece como B34; U07 não é usado no Brasil.")},
                      {"chave": "anos_preliminares",
                       "valor": (f"{', '.join(str(a) for a in sorted(ANOS_PRELIMINARES))} — "
                                 "coletados de SIM/PRELIM/DORES, ainda não fechados pelo "
                                 "DataSUS. Marcados na coluna `preliminar` e EXCLUÍDOS de "
                                 "toda análise publicada, que usa "
                                 f"{ANOS_CONSOLIDADOS[0]}–{ANOS_CONSOLIDADOS[-1]}. Ano em "
                                 "consolidação tem a codificação por resolver: entre o "
                                 "preliminar e o consolidado de 2024, R99 perdeu 6.944 "
                                 "registros e I21 ganhou 7.948.")},
                      {"chave": "gerado_em",
                       "valor": datetime.now().isoformat(timespec="seconds")},
    ]


if __name__ == "__main__":
    main()
