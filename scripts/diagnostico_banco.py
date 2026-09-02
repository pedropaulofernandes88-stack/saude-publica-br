"""
diagnostico_banco.py — mede o tamanho do banco e avisa quando ele incha
=======================================================================

    python scripts/diagnostico_banco.py              # mede E reprova acima de 700 MB
    python scripts/diagnostico_banco.py --limite-mb 0  # só mede, sem veredito
    python scripts/diagnostico_banco.py --json

POR QUE ESTE ARQUIVO EXISTE
---------------------------
Em 2026-08-23 o banco foi de **740 MB para 607 MB** — 133 MB (18%) recuperados
por `VACUUM FULL`, sem perder uma linha. `mart_internacoes_agravo` sozinha caiu
de 61 MB para 35 MB; `mart_internacoes_municipio` reportava 411 mil linhas vivas
tendo 334.769, com 76 mil fantasmas de inchaço.

Ganho de faxina volta. Os pipelines fazem upsert e, no caso do forecast,
DELETE + INSERT a cada execução: espaço morto se acumula sozinho. Sem medir, o
banco engorda de novo em silêncio, e ninguém descobre até o plano estourar.

O QUE É AUTOMATIZÁVEL, E O QUE NÃO É
------------------------------------
A **medição** é automatizável por RPC (`public.diagnostico_banco()`, V031). A
**ação** não: `VACUUM` não roda dentro de função nem de transação, e o projeto
não guarda senha de banco em lugar nenhum — só chaves de API. Então este script
mede e avisa; compactar continua sendo um comando manual, e o aviso diz quais
tabelas valem a pena.

Fingir que isso é automático seria pior que declarar a limitação.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _publicacao import carregar_env  # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

#: Acima disto, a tabela entra na sugestão de compactação. 15% é onde o ganho
#: começa a compensar o bloqueio exclusivo que o VACUUM FULL tira.
PCT_INCHACO_RELEVANTE = 15.0

#: Teto do banco, e o PADRÃO da flag `--limite-mb`.
#:
#: Ser padrão, e não opção, é o ponto. Enquanto o limite era opt-in, o CI o
#: passava e a execução local não — e a assimetria cobrou: a tabela de
#: correlação levou o banco a 703 MB, e o diagnóstico rodado à mão imprimiu o
#: número sem veredito nenhum. Quem lia via "banco: 703 MB" e seguia adiante. O
#: defeito só apareceu quando alguém rodou com a flag, dias depois. Ver V041.
#:
#: Guarda que só protege quando alguém lembra de pedir não é guarda. Agora ela
#: vale por omissão nos dois lugares, e desligá-la exige dizer `--limite-mb 0`,
#: que é um ato deliberado e visível no comando.
#:
#: O valor tem folga proposital sobre o uso corrente: alarme que toca por
#: variação normal é alarme que se aprende a ignorar.
LIMITE_PADRAO_MB = 700.0


def mb(n: float) -> str:
    return f"{n / 1e6:,.0f} MB".replace(",", ".")


def obter(env: dict) -> list[dict]:
    chave = env.get("SUPABASE_SERVICE_ROLE_KEY")
    if not chave:
        raise SystemExit(
            "SUPABASE_SERVICE_ROLE_KEY ausente — diagnostico_banco() só é executável "
            "por service_role (ver migrations/V031)")
    url = env["SUPABASE_URL"].rstrip("/")
    r = requests.post(f"{url}/rest/v1/rpc/diagnostico_banco",
                      headers={"apikey": chave, "Content-Type": "application/json"},
                      json={}, timeout=120)
    if r.status_code == 404:
        raise SystemExit("diagnostico_banco() não existe — aplique migrations/V031")
    r.raise_for_status()
    return r.json()


def main() -> None:
    ap = argparse.ArgumentParser(description="Diagnóstico de tamanho do banco.")
    ap.add_argument("--limite-mb", type=float, default=LIMITE_PADRAO_MB,
                    help=f"sai com código ≠ 0 se o banco passar deste tamanho "
                         f"(padrão: {LIMITE_PADRAO_MB:,.0f} MB; use 0 para só medir)")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    linhas = obter(carregar_env())
    if args.json:
        print(json.dumps(linhas, ensure_ascii=False, indent=2))
        return

    banco = next((x for x in linhas if x["categoria"] == "banco"), None)
    tabelas = [x for x in linhas if x["categoria"] == "tabela"]
    inchaco = [x for x in linhas if x["categoria"] == "inchaco"]
    ociosos = [x for x in linhas if x["categoria"] == "indice_ocioso"]

    total = float(banco["bytes"]) if banco else 0.0
    print(f"banco: {mb(total)}")
    print(f"tabelas: {len(tabelas)} · "
          f"{sum(int(t['linhas'] or 0) for t in tabelas):,} linhas\n")

    print("maiores tabelas:")
    for t in sorted(tabelas, key=lambda x: -int(x["bytes"]))[:8]:
        print(f"   {t['objeto']:38s} {mb(float(t['bytes'])):>9s}  "
              f"{int(t['linhas'] or 0):>10,} linhas  {t['detalhe']}")

    relevante = [x for x in inchaco
                 if float(x["bytes_por_linha"] or 0) >= PCT_INCHACO_RELEVANTE]
    if relevante:
        print(f"\ninchaço acima de {PCT_INCHACO_RELEVANTE:.0f}% — vale compactar:")
        for x in sorted(relevante, key=lambda x: -float(x["bytes_por_linha"] or 0)):
            print(f"   {x['objeto']:38s} {float(x['bytes_por_linha']):>5.1f}% morto  "
                  f"({int(x['linhas']):,} tuplas)")
        print("\n   VACUUM não roda por RPC nem dentro de transação. Rode à mão,")
        print("   uma tabela por vez (o bloqueio é exclusivo, mas dura segundos):")
        for x in relevante[:5]:
            print(f"       vacuum (full, analyze) public.{x['objeto']};")
    else:
        print("\ninchaço: nada acima do limiar")

    if ociosos:
        print("\níndices pouco usados (avaliar, não dropar às cegas —")
        print("um índice raro pode servir a uma ferramenta rara):")
        for x in sorted(ociosos, key=lambda x: -int(x["bytes"])):
            print(f"   {x['objeto']:44s} {mb(float(x['bytes'])):>8s}  "
                  f"{int(x['linhas']):>6,} buscas  ({x['detalhe']})")

    if args.limite_mb and total / 1e6 > args.limite_mb:
        print(f"\n❌ banco em {mb(total)}, acima do limite de {args.limite_mb:,.0f} MB")
        sys.exit(1)
    if args.limite_mb:
        print(f"\n✅ banco em {mb(total)}, dentro do limite de {args.limite_mb:,.0f} MB")


if __name__ == "__main__":
    main()
