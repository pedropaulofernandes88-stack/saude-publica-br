"""
pipeline_sisagua.py — vigilância da água: volume e regularidade das análises
=============================================================================

    .venv311/Scripts/python scripts/pipeline_sisagua.py
    .venv311/Scripts/python scripts/pipeline_sisagua.py --ufs SP --parcial

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
* o mart carrega, ao lado, `data/marts/mart_sisagua_cobertura.parquet`, com uma
  linha para **cada município do país**, coletado ou não. Sem esse arquivo, quem
  usa o mart não tem como distinguir "não analisou" de "não coletei".

ELE AGREGA O CACHE; NÃO COLETA
-------------------------------
A coleta mora em `_sisagua.coletar_por_municipio` e é longa — dezenas de horas
para os 5.571 municípios. Separá-la da agregação é o que permite agregar em
minutos sobre o que já está em disco, quantas vezes for preciso, sem tocar na
fonte. Município que não está em cache faz o pipeline **recusar-se a gravar**,
a menos que `--parcial` diga explicitamente que é para gravar assim.

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
* `uf` NÃO tem índice e estoura em 502 sempre; `codigo_ibge` tem. A coleta é
  por município, e a varredura por UF foi removida de `_sisagua.py`;
* fatia que falha aborta a coleta inteira, em vez de produzir um mart a que
  falta um município sem que nada acuse.

Depende de: `scripts/_sisagua.py`, `scripts/_publicacao.py`.
"""
from __future__ import annotations

import argparse
import sys
from collections.abc import Iterable
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _publicacao import escrever_parquet  # noqa: E402
from _sisagua import FalhaDeColeta, municipios_em_cache, registros_do_cache  # noqa: E402

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


def _acumular(registros: Iterable[dict], acc: dict[tuple, dict]) -> int:
    """Soma os registros dentro de `acc`. Devolve quantos leu.

    Recebe um ITERÁVEL, não uma lista, e escreve num acumulador de fora: as
    duas coisas existem para que a agregação nacional nunca precise dos
    registros todos ao mesmo tempo. Medido em 2026-09-09, sobre 3.795 dos 5.571
    municípios: **62.197.586 registros brutos**, lidos em 31 minutos. Nenhuma
    lista Python cabe nisso — era o mesmo defeito que a coleta página a página
    resolveu do outro lado do processo.
    """
    lidos = 0
    for r in registros:
        lidos += 1
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
    return lidos


def _fechar(acc: dict[tuple, dict]) -> list[dict]:
    """Converte o acumulador em linhas prontas, resolvendo os campos derivados."""
    linhas = []
    for d in acc.values():
        meses = d.pop("_meses")
        formas = d.pop("_formas")
        d["meses_com_analise"] = len(meses)
        d["formas_de_abastecimento"] = ",".join(sorted(formas)) or None
        linhas.append(d)
    return linhas


def _montar(linhas: list[dict]) -> pd.DataFrame:
    df = pd.DataFrame(linhas)
    if df.empty:
        return df
    return df.sort_values(["uf_sigla", "municipio_cod", "ano", "parametro"]).reset_index(drop=True)


def agregar(registros: Iterable[dict]) -> pd.DataFrame:
    """Município × ano × parâmetro: volume, regularidade e presença.

    `meses_com_analise` é o coração do indicador. O SISAGUA prevê controle
    MENSAL: um município que analisou em 2 dos 12 meses não tem "pouco dado",
    tem uma lacuna de vigilância — e isso não aparece no total de amostras,
    porque uma campanha única de 300 amostras num mês soma mais que 12 meses
    de 10. Volume e regularidade medem coisas diferentes e vão os dois.
    """
    acc: dict[tuple, dict] = {}
    _acumular(registros, acc)
    return _montar(_fechar(acc))


def agregar_do_cache(municipios: list[tuple[str, str]],
                     quieto: bool = False) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Agrega o cache município a município, sem nunca carregar o país inteiro.

    Cada município é lido, somado e DESCARTADO antes do próximo. Isso é possível
    porque a chave de agregação — código IBGE, ano, parâmetro — é interna ao
    município: quando a fatia acaba, aquelas linhas estão fechadas e não vão
    mais receber soma de ninguém.

    O que isso limita é a LEITURA, não o total: as linhas já fechadas continuam
    acumulando até o fim, porque são o produto. Em 2026-09-09 o processo foi
    observado em 536 MB no meio da rodada — 62 milhões de registros passaram
    por ele, e o mart resultante ocupa 31 MB em pandas. Dizer que "o pico vira
    o de um município" seria bonito e falso.

    Devolve também a cobertura, com uma linha para CADA município do país,
    coletado ou não. É o que impede o mart parcial de parecer completo: sem
    esse arquivo, "município sem linha" e "município não coletado" produzem a
    mesma ausência, e a segunda leitura é catastroficamente otimista.
    """
    # A lista de quem ESTÁ em cache é consultada antes, e não deduzida de uma
    # exceção. `registros_do_cache` levanta o mesmo `FalhaDeColeta` para dois
    # fatos opostos: "esta fatia não existe" e "esta fatia existe e está pela
    # metade". Capturar os dois no mesmo `except` rebaixaria a corrupção — que
    # tem de abortar — a uma linha de cobertura dizendo "não coletado", e o mart
    # sairia com aparência de completo em cima de um cache quebrado.
    em_cache = municipios_em_cache(ENDPOINT)

    linhas: list[dict] = []
    cob: list[dict] = []
    for i, (cod, uf) in enumerate(municipios, 1):
        if cod not in em_cache:
            cob.append({"municipio_cod": cod, "uf_sigla": uf, "coletado": False,
                        "registros_brutos": None, "linhas_no_mart": 0})
            continue
        acc: dict[tuple, dict] = {}
        brutos = _acumular(registros_do_cache(ENDPOINT, cod), acc)
        novas = _fechar(acc)
        linhas.extend(novas)
        cob.append({"municipio_cod": cod, "uf_sigla": uf, "coletado": True,
                    "registros_brutos": brutos, "linhas_no_mart": len(novas)})
        if not quieto and i % 500 == 0:
            print(f"   {i:,}/{len(municipios):,} municípios · {len(linhas):,} linhas",
                  flush=True)

    cobdf = pd.DataFrame(cob).sort_values(["uf_sigla", "municipio_cod"]).reset_index(drop=True)
    # Inteiro NULÁVEL, não float: sem isso o `None` do município não coletado
    # vira NaN e a coluna inteira vira float, deixando "0 registros" e "não sei"
    # a um passo de se confundirem na leitura.
    for col in ("registros_brutos", "linhas_no_mart"):
        cobdf[col] = cobdf[col].astype("Int64")
    return _montar(linhas), cobdf


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

    # A cobertura só cumpre o papel dela se falar de TODO município do recorte,
    # inclusive os que ficaram de fora. Se ela listasse apenas os coletados,
    # seria uma lista de presença — e a ausência voltaria a ser invisível.
    if cob["municipio_cod"].duplicated().any():
        raise SystemExit("[sisagua] cobertura com município repetido — a chave está errada.")

    # Município no mart e ausente da cobertura significa que as duas metades
    # foram construídas sobre recortes diferentes, e aí nenhuma das duas
    # descreve a outra.
    orfaos = set(df["municipio_cod"]) - set(cob.loc[cob["coletado"], "municipio_cod"])
    if orfaos:
        raise SystemExit(
            f"[sisagua] {len(orfaos)} municípios têm linha no mart e não constam como "
            f"coletados na cobertura (ex.: {sorted(orfaos)[:5]}).")


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    ap = argparse.ArgumentParser(description="Mart de vigilância da água (SISAGUA).")
    ap.add_argument("--ufs", nargs="+", help="restringe a agregação a estas UFs")
    ap.add_argument("--parcial", action="store_true",
                    help="grava mesmo com municípios faltando no cache")
    ap.add_argument("--quieto", action="store_true")
    args = ap.parse_args()

    ufs = args.ufs or UFS
    desconhecidas = [u for u in ufs if u not in UFS]
    if desconhecidas:
        ap.error(f"UF desconhecida: {desconhecidas}")

    dim = pd.read_parquet(MARTS / "dim_municipio.parquet")
    alvo = [(str(r.municipio_cod), str(r.uf_sigla)) for r in dim.itertuples()
            if str(r.uf_sigla) in ufs]
    if not alvo:
        raise SystemExit(f"[sisagua] nenhum município para {ufs} em dim_municipio.parquet")

    em_cache = municipios_em_cache(ENDPOINT)
    faltando = [c for c, _ in alvo if c not in em_cache]
    print(f"[sisagua] {len(alvo):,} municípios no recorte · "
          f"{len(alvo) - len(faltando):,} em cache · {len(faltando):,} faltando", flush=True)

    if faltando and not args.parcial:
        raise SystemExit(
            f"[sisagua] {len(faltando):,} municípios do recorte NÃO estão em cache — não grava.\n"
            "          Um mart a que faltam municípios é indistinguível de um em que\n"
            "          esses municípios não analisaram a água, e a segunda leitura é a\n"
            "          otimista. Complete o cache, ou passe --parcial para gravar\n"
            "          assumindo isso (a cobertura registra quais ficaram de fora).")

    df, cob = agregar_do_cache(alvo, quieto=args.quieto)
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
    nao_coletados = int((~cob["coletado"]).sum())
    if nao_coletados:
        print(f"[PARCIAL] {nao_coletados:,} dos {len(cob):,} municípios do recorte NÃO foram "
              f"coletados. Eles estão na cobertura com coletado=False; sem consultá-la, a "
              f"ausência deles no mart se lê como 'não analisou'.")
    print("[nota] ausência de município NÃO significa água conforme: significa que ele "
          "não analisou, ou que não foi coletado. A cobertura diz qual dos dois.")


if __name__ == "__main__":
    main()
