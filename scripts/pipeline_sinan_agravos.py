"""
pipeline_sinan_agravos.py — notificação compulsória por agravo, município e ano
================================================================================

    .venv311/Scripts/python scripts/pipeline_sinan_agravos.py --todos
    .venv311/Scripts/python scripts/pipeline_sinan_agravos.py --agravos TUBE HANS

Produz `data/marts/mart_sinan_agravo_municipio.parquet` no grão
**agravo × município de residência × ano do arquivo**, a partir de
`SINAN/DADOS/FINAIS`.

O QUE ESTE MART CONTA, E O QUE ELE NÃO CONTA
---------------------------------------------
Conta **notificação**. Não conta caso confirmado, não conta óbito, não conta
desfecho. Essa restrição não é preguiça: é o que a fonte permite dizer sobre 40
agravos ao mesmo tempo.

A sondagem de `scripts/sondar_sinan_agravos.py` mediu os 44 agravos de FINAIS,
um arquivo cada, e o resultado proíbe qualquer coisa mais ambiciosa:

    campos presentes em TODOS os 44 .... DT_NOTIFIC, ID_MUNICIP, NU_ANO, SG_UF_NOT
    ID_MN_RESI ......................... 40/44
    EVOLUCAO ........................... 35/44
    CLASSI_FIN ......................... 25/44
    CRITERIO ........................... 23/44

`CLASSI_FIN` existe em pouco mais da metade. Quem filtrasse por confirmação
zeraria dezenove agravos — entre eles tuberculose e hanseníase, que não têm o
campo. E onde existe, o significado MUDA: em sífilis congênita `EVOLUCAO=2` é
"óbito por sífilis congênita" e `5` é "natimorto"; em dengue `2` é óbito pelo
agravo. Somar os dois como "óbitos" inventaria uma série.

QUATRO AGRAVOS FICAM DE FORA, POR UNIDADE DE ANÁLISE
------------------------------------------------------
ESPO, NTRA, SDTA e TRAC não têm `ID_MN_RESI` — e não é lacuna de preenchimento.
Eles trazem `CS_INQUERI`, `NU_CASOEXA`, `NU_CASOPOS`, `QT_TOTAL_C`: a linha é um
**surto ou inquérito com contagem de casos**, não uma pessoa. Contar linha ali
seria contar surto como se fosse caso, misturado com agravos em que a linha é
uma notificação individual. (O TRAC ainda usa `ID_MUNI_RE`, outro nome.)

Ficam de fora declarados, com o motivo — não por serem inconvenientes.

O QUE O ANO SIGNIFICA MUDA ENTRE AGRAVOS — E O MART DIZ QUAL É
----------------------------------------------------------------
O ano é o do ARQUIVO, que é como o SINAN organiza a série. O que esse ano
representa, porém, não é o mesmo em todo agravo:

  * em SIFA/SIFG/SIFC o arquivo é de NOTIFICAÇÃO — `NU_ANO` bate com
    `year(DT_NOTIFIC)` em 100% dos registros;
  * em TUBE é de DIAGNÓSTICO — `TUBEBR18` tem 3.328 de 94.735 notificados entre
    2019 e 2023, e `DT_DIAG` é 2018 em **todos** os 94.735.

Por isso `mart_sinan_agravo_cobertura` traz `referencia_do_ano`, medida por
agravo: contra qual data o ano do arquivo se alinha. Sem essa coluna, somar
tuberculose com sífilis por "ano" somaria coortes de coisas diferentes.

A guarda aborta quando NENHUMA das duas datas se alinha ao ano do arquivo: aí
não se sabe o que aquele ano é, e publicar sem saber é inventar a série. A
primeira versão dela comparava só `DT_NOTIFIC` e reprovou a tuberculose inteira
por 3,5% que não eram divergência nenhuma — subir a tolerância teria escondido
a descoberta em vez de fazê-la.

DENGUE E SÍFILIS NÃO ENTRAM AQUI
----------------------------------
Têm pipeline próprio, com dicionário conferido e indicadores que este mart não
pode ter (`mart_dengue_*`, `mart_sifilis_municipio`). Duplicá-las aqui criaria
duas contagens da mesma coisa, que é como um número passa a divergir de si.
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _datasus_ftp import ArquivoAusente, FalhaDeColeta, baixar, listar, registros_dbc  # noqa: E402
from _publicacao import escrever_parquet  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
MARTS = ROOT / "data" / "marts"
SONDAGEM = ROOT / "data" / "refs" / "sondagem_sinan.json"
DIR_FTP = "/dissemin/publicos/SINAN/DADOS/FINAIS"

#: Já têm pipeline próprio, com dicionário conferido.
COM_PIPELINE_PROPRIO = {"DENG"}

#: Unidade de análise incompatível: a linha é surto/inquérito com contagem de
#: casos, não notificação individual. Medido pela sondagem, não suposto.
SURTO_OU_INQUERITO = {"ESPO", "NTRA", "SDTA", "TRAC"}

#: Alinhamento mínimo entre o ano do arquivo e a melhor das duas datas. Abaixo
#: disso o arquivo não é o que o nome promete, e o ano dele não significa nada
#: que dê para escrever numa coluna.
PISO_ALINHAMENTO = 0.90


def _cod(valor) -> str:
    """Código categórico sem o espaço que o SINAN às vezes deixa à esquerda."""
    return "" if valor is None else str(valor).strip()


def _municipio(valor) -> str | None:
    m = _cod(valor)
    return m[:6] if len(m) >= 6 and m[:6].isdigit() else None


def agravos_elegiveis() -> list[str]:
    """Os agravos que a sondagem mostrou ter município de RESIDÊNCIA."""
    if not SONDAGEM.exists():
        raise SystemExit(
            "[sinan] falta data/refs/sondagem_sinan.json — rode "
            "scripts/sondar_sinan_agravos.py antes. Sem a sondagem não há como "
            "saber quais agravos têm ID_MN_RESI, e supor é o defeito que ela evita.")
    d = json.loads(SONDAGEM.read_text(encoding="utf-8"))
    fora = []
    for a in d["sondados"]:
        nome = a["agravo"]
        if nome in COM_PIPELINE_PROPRIO or nome in SURTO_OU_INQUERITO:
            continue
        if "ID_MN_RESI" not in a["campos"]:
            continue
        fora.append(nome)
    return sorted(fora)


def anos_de(agravo: str, catalogo: dict[str, list[int]]) -> list[int]:
    return catalogo.get(agravo, [])


def agregar(registros, agravo: str, ano_arquivo: int) -> tuple[pd.DataFrame, Counter]:
    """Conta um arquivo anual no grão agravo × município de residência × ano."""
    linhas: dict[str, int] = defaultdict(int)
    rel: Counter = Counter()
    for r in registros:
        rel["lidos"] += 1
        for campo in ("DT_NOTIFIC", "DT_DIAG"):
            d = r.get(campo)
            if d is not None:
                rel[f"tem:{campo}"] += 1
                if getattr(d, "year", None) == ano_arquivo:
                    rel[f"bate:{campo}"] += 1
        mun = _municipio(r.get("ID_MN_RESI"))
        if mun is None:
            rel["sem_residencia"] += 1
            continue
        linhas[mun] += 1

    # O QUE O ANO DO ARQUIVO SIGNIFICA MUDA ENTRE AGRAVOS.
    #
    # Em SIFA/SIFG/SIFC o ano do arquivo é o da NOTIFICAÇÃO: NU_ANO bate com
    # year(DT_NOTIFIC) em 100% dos registros. Em TUBE não: TUBEBR18 tem 3.328
    # de 94.735 notificados entre 2019 e 2023 — e DT_DIAG é 2018 em TODOS os
    # 94.735. O arquivo é uma COORTE DE DIAGNÓSTICO.
    #
    # A primeira versão desta guarda comparava só DT_NOTIFIC e reprovou a
    # tuberculose inteira por 3,5% de "divergência" que não era divergência
    # nenhuma. Subir a tolerância teria escondido a descoberta; o certo era
    # descobrir CONTRA O QUE o ano do arquivo se alinha.
    rel["ano_arquivo"] = ano_arquivo

    # A pergunta é "com QUAL data o ano do arquivo alinha melhor?", não "alinha
    # acima de X?". A primeira versão usava limiar fixo de 98% e reprovou HANT
    # 2020 com 487/499 = 97,6% — doze notificações tardias num arquivo de 499
    # registros. O limiar estava medindo tamanho de amostra, não alinhamento.
    #
    # Escolher o MELHOR entre as duas datas responde a pergunta certa e não
    # depende de o arquivo ser grande. O piso existe só para o caso em que
    # nenhuma das duas alinha de verdade — aí realmente não se sabe o que o ano
    # é, e publicar sem saber é inventar a série.
    alinhamentos = {}
    for campo, nome in (("DT_NOTIFIC", "notificacao"), ("DT_DIAG", "diagnostico")):
        tem = rel[f"tem:{campo}"]
        if tem:
            alinhamentos[nome] = rel[f"bate:{campo}"] / tem

    referencia, melhor = "indeterminado", 0.0
    if alinhamentos:
        referencia, melhor = max(alinhamentos.items(), key=lambda kv: kv[1])
    rel["referencia"] = referencia          # type: ignore[assignment]
    rel["alinhamento_pct"] = round(melhor * 100, 1)   # type: ignore[assignment]

    if rel["lidos"] and melhor < PISO_ALINHAMENTO:
        raise SystemExit(
            f"[sinan] {agravo} {ano_arquivo}: nenhuma data se alinha ao ano do arquivo "
            f"({ {k: f'{v:.1%}' for k, v in alinhamentos.items()} or 'sem data'}) — "
            "não dá para dizer o que este ano significa, e publicar sem saber é "
            "inventar a série.")

    df = pd.DataFrame(
        [{"agravo": agravo, "municipio_cod": m, "ano": ano_arquivo, "notificacoes": n}
         for m, n in linhas.items()],
        columns=["agravo", "municipio_cod", "ano", "notificacoes"])
    return df, rel


#: Fração máxima de notificações em código que não é município da dimensão.
#: Medido em 2026-09-08: 3.301 de 26.700.522 = 0,012%.
TETO_FORA_DA_DIMENSAO = 0.001


def fora_da_dimensao(df: pd.DataFrame) -> pd.DataFrame:
    """As linhas cujo código não é município do IBGE — e não são lixo.

    São 94 códigos, 0,012% das notificações, em três famílias:

      UF+0000 (27 códigos, 1.304 notificações)
          "município ignorado" dentro daquela UF. É informação: a UF se sabe.
      53xxxx (38 códigos, 1.916)
          Regiões Administrativas do DF — Ceilândia, Taguatinga e afins. O
          DataSUS as codifica à parte; a dimensão IBGE tem só 530010 (Brasília).
      resto (30 códigos, 87)
          municípios extintos e códigos históricos, sobretudo 52xxxx (Goiás,
          antes do desmembramento do Tocantins em 1988).

    Ficam no mart: são notificações que aconteceram, e descartá-las perderia
    3.301 registros em silêncio. O que não podem é passar por município da
    dimensão — foi isso que fez o log anunciar "5.665 municípios" num país de
    5.570, número que teria ido para a tela sem ninguém notar.
    """
    alvo = MARTS / "dim_municipio.parquet"
    if not alvo.exists():
        return df.iloc[0:0]
    dim = set(pd.read_parquet(alvo)["municipio_cod"].astype(str))
    return df[~df["municipio_cod"].isin(dim)]


def guardas(df: pd.DataFrame, cobertura: pd.DataFrame) -> None:
    """Aborta antes de gravar."""
    if df.empty:
        raise SystemExit("[sinan] agregação vazia — não grava.")
    if (df["notificacoes"] <= 0).any():
        raise SystemExit("[sinan] há linhas com notificacoes <= 0.")
    ruim = df[~df["municipio_cod"].str.fullmatch(r"\d{6}")]
    if len(ruim):
        raise SystemExit(f"[sinan] {len(ruim)} linhas com municipio_cod fora de 6 dígitos.")
    dup = df.duplicated(subset=["agravo", "municipio_cod", "ano"]).sum()
    if dup:
        raise SystemExit(f"[sinan] {dup} chaves (agravo, município, ano) repetidas.")
    # Todo agravo com linha no mart precisa aparecer na cobertura, e vice-versa:
    # é o que impede um agravo de sumir sem deixar rastro.
    no_mart = set(df["agravo"])
    na_cobertura = set(cobertura[cobertura["arquivos_lidos"] > 0]["agravo"])
    if no_mart - na_cobertura:
        raise SystemExit(f"[sinan] agravos no mart e fora da cobertura: {no_mart - na_cobertura}")

    # Código fora da dimensão é aceitável em dose pequena — ver
    # `fora_da_dimensao`. Crescer aí significaria que a leitura de ID_MN_RESI
    # mudou, e nada mais avisaria: o mart continuaria "completo".
    ruins = fora_da_dimensao(df)
    if len(ruins):
        frac = ruins["notificacoes"].sum() / df["notificacoes"].sum()
        if frac > TETO_FORA_DA_DIMENSAO:
            raise SystemExit(
                f"[sinan] {frac:.3%} das notificações em código fora de dim_municipio "
                f"({ruins['municipio_cod'].nunique()} códigos) — acima do teto de "
                f"{TETO_FORA_DA_DIMENSAO:.1%}. Era 0,012%; se subiu, a leitura de "
                "ID_MN_RESI mudou.")


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    ap = argparse.ArgumentParser(description="Mart de notificações do SINAN por agravo.")
    ap.add_argument("--agravos", nargs="+")
    ap.add_argument("--todos", action="store_true")
    ap.add_argument("--desde", type=int, default=2010,
                    help="primeiro ano a coletar (padrão: 2010)")
    args = ap.parse_args()

    catalogo = json.loads(SONDAGEM.read_text(encoding="utf-8"))["catalogo"]
    alvos = args.agravos or (agravos_elegiveis() if args.todos else [])
    if not alvos:
        ap.error("informe --agravos ou --todos")

    print(f"[sinan] {len(alvos)} agravos, de {args.desde} em diante", flush=True)

    partes: list[pd.DataFrame] = []
    cobertura: list[dict] = []
    for i, agravo in enumerate(alvos, 1):
        anos = [a for a in anos_de(agravo, catalogo) if a >= args.desde]
        lidos = sem_resid = arquivos = 0
        ausentes: list[int] = []
        referencias: set[str] = set()
        datas_ruins = 0
        alinhamento_min = 100.0
        for ano in anos:
            nome = f"{agravo}BR{ano % 100:02d}.dbc"
            try:
                dados = baixar(DIR_FTP, nome)
            except ArquivoAusente:
                ausentes.append(ano)
                continue
            except FalhaDeColeta as e:
                raise SystemExit(f"[sinan] {nome} existe e a coleta falhou: {e}") from e
            contador: Counter = Counter()
            df, rel = agregar(registros_dbc(dados, nome, contador), agravo, ano)
            # Data impossível SÓ importa nos campos que este mart LÊ.
            #
            # BOTUBR10 tem 26 delas, e a primeira versão desta checagem abortou
            # os 40 agravos por causa disso. Medidas uma a uma, são datas
            # digitadas em formato brasileiro num campo DBF de 8 bytes que
            # espera AAAAMMDD — e várias truncadas pelo tamanho: b"8/3/2010",
            # b"27/2/201", b"21/10/20". Todas em campos CLÍNICOS: DTALTA,
            # DTSORO, DTFEZESCOL, DTELETRO, DT_COLOUT.
            #
            # Nenhuma em DT_NOTIFIC nem em DT_DIAG, que são as duas datas que o
            # mart usa para saber a que o ano do arquivo se refere. Derrubar a
            # coleta inteira por defeito em campo que não se lê é guarda que
            # ensina a ser desligada; ignorá-lo por completo seria apagar um
            # fato sobre a qualidade da fonte. Então: aborta se sujar o que
            # importa, e conta o resto.
            usados = contador["impossivel:DT_NOTIFIC"] + contador["impossivel:DT_DIAG"]
            if usados:
                raise SystemExit(
                    f"[sinan] {nome}: {usados} datas impossíveis em DT_NOTIFIC/DT_DIAG — "
                    "são as duas que definem a referência do ano deste arquivo.")
            datas_ruins += contador["impossivel"]
            if not df.empty:
                partes.append(df)
            lidos += rel["lidos"]
            sem_resid += rel["sem_residencia"]
            if rel["lidos"]:
                referencias.add(str(rel["referencia"]))
                alinhamento_min = min(alinhamento_min, float(rel["alinhamento_pct"]))
            arquivos += 1
        cobertura.append({"agravo": agravo, "anos_pedidos": len(anos),
                          "arquivos_lidos": arquivos, "anos_ausentes": len(ausentes),
                          "registros_lidos": lidos, "sem_residencia": sem_resid,
                          "referencia_do_ano": "/".join(sorted(referencias)) or "sem dado",
                          "datas_impossiveis_fora_do_uso": datas_ruins,
                          "alinhamento_min_pct": round(alinhamento_min, 1)})
        print(f"[{i:2d}/{len(alvos)}] {agravo}: {arquivos} arquivos · {lidos:,} registros · "
              f"{sem_resid:,} sem residência", flush=True)

    if not partes:
        raise SystemExit("[sinan] nada agregado — não grava.")

    out = (pd.concat(partes, ignore_index=True)
           .groupby(["agravo", "municipio_cod", "ano"], as_index=False)["notificacoes"].sum()
           .sort_values(["agravo", "municipio_cod", "ano"]).reset_index(drop=True))
    cob = pd.DataFrame(cobertura)
    guardas(out, cob)

    ruins = fora_da_dimensao(out)
    print(f"\n[sinan] {len(out):,} linhas · {out['agravo'].nunique()} agravos · "
          f"{out['municipio_cod'].nunique() - ruins['municipio_cod'].nunique():,} municípios "
          f"da dimensão · {out['notificacoes'].sum():,} notificações")
    if len(ruins):
        print(f"[sinan] {ruins['municipio_cod'].nunique()} códigos fora da dimensão "
              f"({ruins['notificacoes'].sum():,} notificações, "
              f"{ruins['notificacoes'].sum() / out['notificacoes'].sum():.3%}): "
              "município ignorado (UF+0000), Regiões Administrativas do DF e "
              "municípios extintos. Ficam no mart, mas não são municípios do IBGE.")
    print(f"[sinan] fora por unidade de análise (surto/inquérito): {sorted(SURTO_OU_INQUERITO)}")
    print(f"[sinan] fora por ter pipeline próprio: {sorted(COM_PIPELINE_PROPRIO)}")
    refs = cob.groupby("referencia_do_ano")["agravo"].count().to_dict()
    print(f"[sinan] referência do ano, por agravo: {refs}")
    print("[nota] o ano é o do ARQUIVO. O que ele representa muda entre agravos "
          "(notificação na sífilis, diagnóstico na tuberculose) — ver a coluna "
          "referencia_do_ano em mart_sinan_agravo_cobertura antes de somar agravos.")

    MARTS.mkdir(parents=True, exist_ok=True)
    escrever_parquet(out, MARTS / "mart_sinan_agravo_municipio.parquet",
                     origem="pipeline", produtor="scripts/pipeline_sinan_agravos.py")
    escrever_parquet(cob, MARTS / "mart_sinan_agravo_cobertura.parquet",
                     origem="pipeline", produtor="scripts/pipeline_sinan_agravos.py")
    print(f"[ok] mart_sinan_agravo_municipio.parquet em {MARTS}")


if __name__ == "__main__":
    main()
