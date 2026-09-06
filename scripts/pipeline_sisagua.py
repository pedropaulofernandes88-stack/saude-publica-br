"""
pipeline_sisagua.py — vigilância da água: volume e regularidade das análises
=============================================================================

    .venv311/Scripts/python scripts/pipeline_sisagua.py --ufs SP --anos 2024
    .venv311/Scripts/python scripts/pipeline_sisagua.py --todas-as-ufs --anos 2023 2024

Produz `data/marts/mart_sisagua_municipio.parquet` no grão
**município × ano × parâmetro**, a partir do controle mensal do SISAGUA
(`/sisagua/controle-mensal-parametros-basicos` da API de dados abertos do MS).

O QUE ESTE INDICADOR É, E O QUE NÃO É
-------------------------------------
É **volume e regularidade de análise**, e conformidade só onde a própria fonte
declara o limiar. NÃO é potabilidade, e não deve ser lido como tal.

A distinção não é acadêmica. O município que não analisa a água aparece na
fonte como **ausência**, e ausência de análise é o oposto de água comprovada:
é a falta da prova. Um mart que preenchesse esses casos com zero — ou que os
omitisse sem dizer — transformaria "não mediu" em "não achou problema", que é
o erro mais caro possível numa camada ambiental.

Daí duas decisões:

* município-ano sem linha na fonte **não vira linha zerada**. Ele fica de fora
  do mart, e a cobertura (abaixo) registra que ele ficou;
* o mart carrega, ao lado, `data/marts/mart_sisagua_cobertura.parquet`, que diz
  quais UF-ano foram coletados e quais vieram vazios. Sem esse arquivo, quem
  usa o mart não tem como distinguir "não analisou" de "não coletei".

LIMIARES SAEM DA FONTE, NÃO DA MINHA CABEÇA
--------------------------------------------
O campo `campo` do SISAGUA já traz o corte aplicado: "Número de dados > 5,0 uT",
"N de amostras com presença para Escherichia coli". Este pipeline SOMA esses
campos como a fonte os nomeia; não recalcula conformidade a partir de valores
brutos, e não aplica portaria de cabeça. Onde a fonte não declara limiar, o
mart traz só o volume analisado.

Para Escherichia coli o critério é o mais simples e o menos ambíguo da norma —
ausência em 100% das amostras —, então `amostras_com_presenca` para esse
parâmetro é interpretável direto. Para turbidez, cor e cloro, os cortes variam
com o tipo de tratamento, e por isso ficam como contagem rotulada, sem virar
um "% fora do padrão" agregado que misturaria réguas diferentes.

O QUE A API IMPÕE — MEDIDO, NÃO LIDO
-------------------------------------
Ver `_sisagua.py` para o detalhe. O resumo operacional:

* `limit` **tem de ser 1000**. Medido com `uf=SP&ano_de_referencia=2024`:
  limites 50, 100, 250 e 500 falharam com HTTP 502 em 16 de 16 tentativas, e
  1000 respondeu em 4 de 4. A página maior passa onde a menor estoura — é
  contraintuitivo e é o que a fonte faz;
* HTTP 502 é frequente e intermitente. Repetir, nunca interpretar como fim;
* fatia que falha aborta a coleta inteira, em vez de produzir um mart a que
  falta uma UF sem que nada acuse.

Depende de: `scripts/_sisagua.py`, `scripts/_publicacao.py`.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _publicacao import escrever_parquet  # noqa: E402
from _sisagua import FalhaDeColeta, Relatorio, _get, coletar  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
MARTS = ROOT / "data" / "marts"
ENDPOINT = "controle-mensal-parametros-basicos"

UFS = [
    "AC", "AL", "AM", "AP", "BA", "CE", "DF", "ES", "GO", "MA", "MG", "MS",
    "MT", "PA", "PB", "PE", "PI", "PR", "RJ", "RN", "RO", "RR", "RS", "SC",
    "SE", "SP", "TO",
]

#: O campo que conta amostra analisada. Está escrito exatamente como a fonte o
#: escreve — comparar por prefixo ou por "contém" casaria também com
#: "N de amostras com presença...", que é outra coisa.
CAMPO_ANALISADAS = "Número de amostras analisadas"

#: Campos de PRESENÇA microbiológica. Presença de E. coli é não conformidade
#: direta pela norma (ausência exigida em 100% das amostras); coliformes totais
#: é indicador de alerta, não de não conformidade por si só.
CAMPOS_PRESENCA = {
    "N de amostras com presença para Escherichia coli": "escherichia_coli",
    "N de amostras com presença de coliformes totais": "coliformes_totais",
}


def _num(v: object) -> float | None:
    """Valor numérico, ou `None`. Texto não numérico NÃO vira zero."""
    if v is None:
        return None
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    return None if f != f else f  # NaN fora


def agregar(registros: list[dict]) -> pd.DataFrame:
    """Município × ano × parâmetro: volume, regularidade e presença.

    `meses_com_analise` é o coração do indicador. O SISAGUA prevê controle
    MENSAL: um município que analisou em 2 dos 12 meses não tem "pouco dado",
    tem uma lacuna de vigilância — e isso não aparece no total de amostras,
    porque uma campanha única de 300 amostras num mês soma mais que 12 meses
    de 10. Volume e regularidade medem coisas diferentes e vão os dois.
    """
    acc: dict[tuple, dict] = {}
    for r in registros:
        cod = str(r.get("codigo_ibge") or "").strip()
        param = r.get("parametro")
        ano = r.get("ano_de_referencia")
        if not cod or not param or ano is None:
            continue
        chave = (cod, int(ano), str(param))
        d = acc.setdefault(chave, {
            "municipio_cod": cod,
            "municipio_nome": r.get("municipio"),
            "uf_sigla": r.get("uf"),
            "regiao": r.get("regiao_geografica"),
            "ano": int(ano),
            "parametro": str(param),
            "amostras_analisadas": 0.0,
            "escherichia_coli": None,
            "coliformes_totais": None,
            "_meses": set(),
            "_formas": set(),
        })

        campo = str(r.get("campo") or "")
        v = _num(r.get("valor"))

        if campo == CAMPO_ANALISADAS and v is not None:
            d["amostras_analisadas"] += v
            if v > 0 and r.get("mes_de_referencia") is not None:
                d["_meses"].add(int(r["mes_de_referencia"]))
        elif campo in CAMPOS_PRESENCA and v is not None:
            col = CAMPOS_PRESENCA[campo]
            d[col] = (d[col] or 0.0) + v

        if r.get("tipo_da_forma_de_abastecimento"):
            d["_formas"].add(str(r["tipo_da_forma_de_abastecimento"]))

    linhas = []
    for d in acc.values():
        meses = d.pop("_meses")
        formas = d.pop("_formas")
        d["meses_com_analise"] = len(meses)
        d["formas_de_abastecimento"] = ",".join(sorted(formas)) or None
        linhas.append(d)

    df = pd.DataFrame(linhas)
    if df.empty:
        return df
    return df.sort_values(["uf_sigla", "municipio_cod", "ano", "parametro"]).reset_index(drop=True)


def cobertura(rel: Relatorio) -> pd.DataFrame:
    """O que foi coletado, e o que veio vazio — para o mart poder ser lido.

    Sem isto, quem consome o Parquet não tem como saber se a ausência de um
    município significa "não analisou" ou "não coletamos aquela UF". As duas
    coisas produzem exatamente a mesma ausência de linha.
    """
    return pd.DataFrame([
        {"uf_sigla": f.uf, "ano": f.ano,
         "registros_brutos": len(f.registros),
         "paginas": f.paginas,
         "vazia_de_fato": f.vazia_de_fato}
        for f in rel.fatias
    ]).sort_values(["uf_sigla", "ano"]).reset_index(drop=True)


def guardas(df: pd.DataFrame, cob: pd.DataFrame) -> None:
    """Aborta antes de gravar. Cada uma nasceu de um defeito conhecido."""
    if df.empty:
        raise SystemExit(
            "[sisagua] agregação vazia com fatias coletadas — não grava.\n"
            "          Isto é falha de leitura, não ausência de dado: o recorte "
            "trouxe registros brutos mas nenhum virou linha.")

    negativos = df[df["amostras_analisadas"] < 0]
    if len(negativos):
        raise SystemExit(f"[sisagua] {len(negativos)} linhas com amostras negativas — dado corrompido.")

    fora = df[df["meses_com_analise"] > 12]
    if len(fora):
        raise SystemExit(
            f"[sisagua] {len(fora)} linhas com mais de 12 meses de análise num ano. "
            "Ou o mês vem fora de 1–12, ou a chave de agregação está errada.")

    # Presença não pode exceder o analisado: se exceder, os dois campos estão
    # sendo somados em recortes diferentes e a razão entre eles seria absurda.
    for col in ("escherichia_coli", "coliformes_totais"):
        mau = df[df[col].notna() & (df[col] > df["amostras_analisadas"])]
        if len(mau):
            ex = mau.iloc[0]
            raise SystemExit(
                f"[sisagua] {len(mau)} linhas com {col} > amostras analisadas "
                f"(ex.: {ex['municipio_cod']} {ex['ano']} {ex['parametro']}: "
                f"{ex[col]:.0f} > {ex['amostras_analisadas']:.0f}).")

    if not len(cob):
        raise SystemExit("[sisagua] cobertura vazia — o mart não poderia ser lido sem ela.")


def preflight() -> None:
    """Recusa iniciar se a fonte não conseguir entregar a SEGUNDA página.

    POR QUE ISTO É A GUARDA MAIS IMPORTANTE DESTE ARQUIVO
    -----------------------------------------------------
    Uma primeira página cheia — 1000 linhas — é indistinguível de uma coleta
    completa. Se a página 2 falhar, um coletor sem esta checagem entrega um
    mart que parece íntegro e no qual faltam justamente os MAIORES municípios,
    porque são exatamente eles que passam de 1000 linhas. O erro seria
    silencioso, sistemático e enviesado para as capitais.

    Medido em 2026-09-06 (todos com `limit=1000`):

        sem filtro,        offset 0 ......... 200 em  3,2 s
        sem filtro,        offset 800.000 ... 200 em 26,6 s
        sem filtro,        offset 2.000.000 . 502 aos 60 s
        uf=AC,             offset 0 ......... 200 em 41,6 s
        uf=AC + ano,       offset 0 ......... 502 aos 60 s
        codigo_ibge=SP,    offset 0 ......... 200 em 14,5 s
        codigo_ibge=SP,    offset 1000 ...... 502 aos 60 s   <- o muro

    A API pagina só por `offset`, sem cursor, e o custo do offset cresce com a
    profundidade até estourar o timeout de 60 s do proxy. Filtrar não ajuda:
    não há índice em `uf` nem em `ano_de_referencia`, então o filtro força
    varredura e fica MAIS lento que a consulta sem filtro.
    """
    print("[sisagua] preflight: a fonte entrega a segunda página?", flush=True)
    # São Paulo capital tem mais de 1000 linhas — é o caso em que a segunda
    # página é obrigatória, e por isso o teste certo.
    alvo = {"codigo_ibge": "355030", "limit": 1000}
    try:
        p1 = _get(ENDPOINT, {**alvo, "offset": 0})
    except FalhaDeColeta as e:
        raise SystemExit(f"[sisagua] preflight: nem a PRIMEIRA página respondeu — {e}") from e

    if len(p1) < 1000:
        print(f"[sisagua] preflight: município de teste cabe numa página ({len(p1)} linhas); "
              "não dá para testar a segunda por aqui — seguindo.", flush=True)
        return

    try:
        _get(ENDPOINT, {**alvo, "offset": 1000})
    except FalhaDeColeta as e:
        raise SystemExit(
            "[sisagua] preflight REPROVOU: a primeira página veio cheia (1000 linhas) e a "
            f"SEGUNDA não respondeu.\n          {e}\n"
            "          Coletar assim truncaria em silêncio exatamente os maiores municípios,\n"
            "          que são os que passam de 1000 linhas — e um mart truncado desse jeito\n"
            "          é indistinguível de um completo. Nada foi coletado.\n"
            "          Quando o portal do OpenDataSUS voltar, prefira o arquivo em massa:\n"
            "          um download contra milhares de requisições paginadas."
        ) from e
    print("[sisagua] preflight: OK, a segunda página respondeu.", flush=True)


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    ap = argparse.ArgumentParser(description="Mart de vigilância da água (SISAGUA).")
    ap.add_argument("--ufs", nargs="+", help="siglas de UF a coletar")
    ap.add_argument("--todas-as-ufs", action="store_true")
    ap.add_argument("--anos", nargs="+", type=int, required=True)
    ap.add_argument("--quieto", action="store_true")
    args = ap.parse_args()

    ufs = UFS if args.todas_as_ufs else (args.ufs or [])
    if not ufs:
        ap.error("informe --ufs ou --todas-as-ufs")
    desconhecidas = [u for u in ufs if u not in UFS]
    if desconhecidas:
        ap.error(f"UF desconhecida: {desconhecidas}")

    preflight()

    print(f"[sisagua] coletando {len(ufs)} UF(s) x {len(args.anos)} ano(s) "
          f"= {len(ufs) * len(args.anos)} fatias", flush=True)
    try:
        rel = coletar(ENDPOINT, ufs, sorted(args.anos), quieto=args.quieto)
    except FalhaDeColeta as e:
        raise SystemExit(
            f"[sisagua] coleta ABORTADA: {e}\n"
            "          Nada foi gravado. Fatia que falha não pode virar mart "
            "incompleto: refaça o recorte que falhou.") from e

    print(f"\n[sisagua] {rel.registros:,} registros brutos em {len(rel.fatias)} fatias")
    if rel.vazias:
        print(f"[sisagua] {len(rel.vazias)} fatias VAZIAS DE FATO (a fonte respondeu, "
              f"sem linhas): {rel.vazias[:8]}{'…' if len(rel.vazias) > 8 else ''}")

    df = agregar([r for f in rel.fatias for r in f.registros])
    cob = cobertura(rel)
    guardas(df, cob)

    print(f"[sisagua] {len(df):,} linhas município×ano×parâmetro | "
          f"{df['municipio_cod'].nunique():,} municípios | "
          f"{df['parametro'].nunique()} parâmetros")
    print(f"[sisagua] regularidade: mediana de {df['meses_com_analise'].median():.0f} "
          f"meses com análise (de 12 previstos); "
          f"{(df['meses_com_analise'] <= 2).mean() * 100:.1f}% das linhas com 2 ou menos")

    MARTS.mkdir(parents=True, exist_ok=True)
    escrever_parquet(df, MARTS / "mart_sisagua_municipio.parquet",
                     origem="pipeline", produtor="scripts/pipeline_sisagua.py")
    escrever_parquet(cob, MARTS / "mart_sisagua_cobertura.parquet",
                     origem="pipeline", produtor="scripts/pipeline_sisagua.py")
    print(f"[ok] mart_sisagua_municipio.parquet e mart_sisagua_cobertura.parquet em {MARTS}")
    print("[nota] ausência de município NÃO significa água conforme: significa que ele "
          "não analisou, ou que a UF-ano não foi coletada. A cobertura diz qual dos dois.")


if __name__ == "__main__":
    main()
