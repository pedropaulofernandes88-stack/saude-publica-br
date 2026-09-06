"""
sondar_srag.py — a fonte de SRAG está pronta para ser ingerida?
================================================================

    .venv311/Scripts/python scripts/sondar_srag.py
    .venv311/Scripts/python scripts/sondar_srag.py --json

Sai com código 0 apenas quando TODAS as condições de aptidão passam. Enquanto
alguma reprovar, sai com ≠ 0 e diz qual — é portão de prontidão, não relatório.

POR QUE ESTE ARQUIVO EXISTE
---------------------------
A etapa 2 do plano pede "integrar SIVEP/InfoGripe". Ao ir buscar a fonte, as
duas rotas conhecidas estavam fechadas, cada uma por um motivo diferente, e
nenhum dos dois motivos é visível para quem só abre a URL no navegador:

  1. **Rota CSV (OpenDataSUS).** O portal inteiro responde **HTTP 500** —
     `/dataset/srag-2021-a-2024`, a raiz de `opendatasus.saude.gov.br` e a de
     `dadosabertos.saude.gov.br`. Medido duas vezes com ~1 h de intervalo em
     2026-09-06. Não é um conjunto fora do ar, é o portal.

  2. **Rota API (`apidadosabertos.saude.gov.br`).** Está no ar e devolve
     4.445.192 registros — mas com o campo de data **corrompido**:

         dt_notific  (notificação) .... 8 meses distintos numa amostra de 8.000
                                        registros, TODOS em dezembro (+ jan/2023)
         dt_sin_pri  (1os sintomas) ... 65 meses distintos, distribuídos de forma
                                        plausível pelas ondas da COVID
         notificação ANTES do sintoma . 98,2% dos registros

     Notificar antes de a pessoa adoecer é impossível. E `anomes_notific` — o
     único filtro temporal que a API documenta — chaveia exatamente nesse campo,
     então recortar por mês recorta por uma data quebrada.

O QUE ISSO TERIA CUSTADO SEM A SONDAGEM
---------------------------------------
Um coletor escrito a partir da documentação teria parecido funcionar. Ele
filtraria por `anomes_notific`, receberia HTTP 200 com lista vazia em 11 de cada
12 meses, e concluiria que não houve SRAG naqueles meses — publicando uma série
com 8 meses de dado e 88 de silêncio, com exit 0. É o defeito que o projeto já
pagou uma vez (Maranhão 2023, 5 meses perdidos): ausência tratada como fato.

DUAS ARMADILHAS DA DOCUMENTAÇÃO, MEDIDAS
----------------------------------------
* `limit`: a doc diz "menor ou igual a 100". Aceita **1000**, e acima disso
  trava em 1000 em silêncio, sem erro.
* `offset`: a doc diz "número da página". É deslocamento de **registro** —
  `offset=1` anda uma linha, não cem. Um coletor fiel à doc leria 99% de
  linhas repetidas e, como a contagem final bateria, nada acusaria.

O QUE USAR QUANDO A FONTE VOLTAR
--------------------------------
`dt_sin_pri` e `sem_pri` (data e semana epidemiológica dos primeiros sintomas).
Além de serem os campos sãos, são o padrão epidemiológico para SRAG — é o que o
InfoGripe usa —, porque a data de notificação depende do cartório
administrativo e a de sintoma depende da doença.

Depende de: nada. Só rede.
"""
from __future__ import annotations

import argparse
import collections
import json
import sys
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor

API = "https://apidadosabertos.saude.gov.br/vigilancia-e-meio-ambiente/srag-2019-2026"
CHAVE = "srag_2019_2026"
PORTAIS = (
    "https://opendatasus.saude.gov.br/",
    "https://dadosabertos.saude.gov.br/",
)

#: Quantos registros amostrar para julgar a sanidade das datas. 8.000 em 40
#: pontos uniformes do arquivo: o bastante para que um campo são mostre dezenas
#: de meses distintos, e barato o suficiente para rodar em CI.
AMOSTRA_LOTES = 40
AMOSTRA_POR_LOTE = 200

#: Abaixo disto, o campo de data não descreve uma série temporal. Uma fonte
#: mensal sã tem dezenas de meses; oito é sintoma, não variação.
MIN_MESES_DISTINTOS = 24

#: Notificação anterior ao primeiro sintoma é impossível. Uma pontinha de
#: digitação errada é esperada em base real; 5% já é defeito sistemático.
MAX_PCT_INVERTIDOS = 5.0


def _buscar(query: str, tentativas: int = 3, timeout: int = 120) -> list[dict]:
    """GET com repetição. Erro de rede LEVANTA — nunca vira lista vazia.

    É a distinção que o resto do script depende: `[]` significa "a fonte não
    tem", e exceção significa "não deu para perguntar". Confundir os dois é
    como se publica recorte incompleto com exit 0.
    """
    ultimo: Exception | None = None
    for i in range(tentativas):
        try:
            with urllib.request.urlopen(f"{API}?{query}", timeout=timeout) as r:
                return json.load(r)[CHAVE]
        except Exception as e:  # noqa: BLE001 — a causa vai no relatório
            ultimo = e
            if i < tentativas - 1:
                time.sleep(2 * (i + 1))
    raise RuntimeError(f"consulta falhou após {tentativas} tentativas: {ultimo}")


def portais_no_ar() -> dict[str, int | str]:
    """Estado da rota CSV. É a rota preferida: 1 arquivo contra 4.446 requisições."""
    saida: dict[str, int | str] = {}
    for url in PORTAIS:
        req = urllib.request.Request(url, method="GET")
        try:
            with urllib.request.urlopen(req, timeout=45) as r:
                saida[url] = r.status
        except urllib.error.HTTPError as e:
            saida[url] = e.code
        except Exception as e:  # noqa: BLE001
            saida[url] = f"erro: {type(e).__name__}"
    return saida


def total_de_registros() -> int:
    """Fim do arquivo por busca binária — a API não devolve contagem."""
    lo, hi = 0, 1
    while _buscar(f"limit=1&offset={hi}"):
        lo, hi = hi, hi * 2
        if hi > 50_000_000:
            raise RuntimeError("arquivo maior que 50 milhões — limite de sanidade")
    while lo < hi:
        meio = (lo + hi) // 2
        if _buscar(f"limit=1&offset={meio}"):
            lo = meio + 1
        else:
            hi = meio
    return lo


def amostrar(total: int) -> list[dict]:
    """Amostra uniforme ao longo do arquivo, não só o começo.

    Ler as primeiras N linhas mediria a ordenação, não o conteúdo: este arquivo
    vem ordenado por data, e as mil primeiras linhas são todas do mesmo mês.
    """
    offs = [int(total * i / AMOSTRA_LOTES) for i in range(AMOSTRA_LOTES)]
    with ThreadPoolExecutor(max_workers=4) as ex:
        lotes = list(ex.map(lambda o: _buscar(f"limit={AMOSTRA_POR_LOTE}&offset={o}"), offs))
    return [r for lote in lotes for r in lote]


def avaliar(regs: list[dict]) -> dict:
    """Os números que decidem, sem veredito ainda."""
    meses_notif: collections.Counter[str] = collections.Counter()
    meses_sint: collections.Counter[str] = collections.Counter()
    invertidos = comparaveis = 0
    for x in regs:
        dn = x.get("dt_notific") or ""
        ds = x.get("dt_sin_pri") or ""
        if dn:
            meses_notif[dn[:7]] += 1
        if ds:
            meses_sint[ds[:7]] += 1
        if dn and ds:
            comparaveis += 1
            if dn < ds:
                invertidos += 1
    pct = (invertidos / comparaveis * 100) if comparaveis else 0.0
    return {
        "registros_amostrados": len(regs),
        "meses_distintos_dt_notific": len(meses_notif),
        "meses_distintos_dt_sin_pri": len(meses_sint),
        "pct_notificacao_antes_do_sintoma": round(pct, 1),
        "meses_dt_notific": sorted(meses_notif),
    }


def veredito(portais: dict, total: int, m: dict) -> list[str]:
    """As reprovações, em texto. Lista vazia = fonte apta."""
    falhas: list[str] = []

    if not any(v == 200 for v in portais.values()):
        falhas.append(
            "rota CSV indisponível: nenhum portal do OpenDataSUS respondeu 200 "
            f"({portais}). É a rota preferida — 1 arquivo contra "
            f"{-(-total // 1000):,} requisições."
        )

    if m["meses_distintos_dt_notific"] < MIN_MESES_DISTINTOS:
        falhas.append(
            f"dt_notific cobre apenas {m['meses_distintos_dt_notific']} meses distintos "
            f"em {m['registros_amostrados']:,} registros amostrados "
            f"(mínimo {MIN_MESES_DISTINTOS}) — {m['meses_dt_notific']}. "
            "O filtro `anomes_notific` chaveia neste campo, então recortar por mês "
            "recortaria por uma data quebrada."
        )

    if m["pct_notificacao_antes_do_sintoma"] > MAX_PCT_INVERTIDOS:
        falhas.append(
            f"{m['pct_notificacao_antes_do_sintoma']}% dos registros têm notificação "
            f"ANTES dos primeiros sintomas (máximo tolerado {MAX_PCT_INVERTIDOS}%). "
            "Notificar antes de adoecer é impossível: a data de notificação está corrompida."
        )

    return falhas


def main() -> None:
    # O console do Windows abre em cp1252 e estoura em "❌"/"✅" — e o traceback
    # sairia DEPOIS de o veredito já ter sido impresso pela metade, que é a
    # forma mais confusa possível de um portão falhar. Mesmo tratamento de
    # `_baixar_mart_completo.py` e `_citacao.py`.
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    ap = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    ap.add_argument("--json", action="store_true", help="saída em JSON, para CI")
    args = ap.parse_args()

    portais = portais_no_ar()
    total = total_de_registros()
    medidas = avaliar(amostrar(total))
    falhas = veredito(portais, total, medidas)

    if args.json:
        print(json.dumps(
            {"portais": portais, "total_registros": total, **medidas,
             "apta": not falhas, "falhas": falhas},
            ensure_ascii=False, indent=2))
    else:
        print("[srag] rota CSV (preferida):")
        for u, s in portais.items():
            print(f"        {s}  {u}")
        print(f"[srag] rota API: {total:,} registros "
              f"({-(-total // 1000):,} requisições a 1000/página)")
        print(f"[srag] dt_notific : {medidas['meses_distintos_dt_notific']:>3} meses distintos")
        print(f"[srag] dt_sin_pri : {medidas['meses_distintos_dt_sin_pri']:>3} meses distintos")
        print(f"[srag] notificação antes do sintoma: "
              f"{medidas['pct_notificacao_antes_do_sintoma']}%")
        print()
        if falhas:
            for f in falhas:
                print(f"❌ {f}\n")
            print("Fonte NÃO apta para ingestão. Nada foi coletado.")
        else:
            print("✅ Fonte apta. Use dt_sin_pri/sem_pri (primeiros sintomas) como eixo "
                  "temporal — é o campo são e o padrão epidemiológico para SRAG.")

    sys.exit(1 if falhas else 0)


if __name__ == "__main__":
    main()
