"""
diagnostico_banco.py — mede o tamanho do banco e avisa quando ele incha
=======================================================================

    python scripts/diagnostico_banco.py              # mede E reprova acima do teto (LIMITE_PADRAO_MB)
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
#:
#: 2026-09-03 — de 700 para 750 MB, e o motivo fica aqui porque teto que sobe
#: sem justificativa registrada deixa de ser teto. A base passou a cobrir 2025
#: (`SIM/PRELIM/DORES`), e o ano novo acrescenta 330.887 linhas às três marts
#: servidas — 201.760 em `mart_mortalidade_municipio`, 108.076 em
#: `mart_mortalidade_uf_mes`, 21.051 em `mart_mortalidade_causa` —, cerca de
#: 47 MB. O banco vai de 663 para ~710 MB.
#:
#: A distinção que autoriza mexer: este alarme mede FOLGA SOBRE O USO CORRENTE,
#: e o uso corrente correto mudou por decisão explícita, com o crescimento
#: conferido linha a linha. Não é o caso de afrouxar uma trava para caber —
#: quando a guarda de qualidade acusou divergência no dado publicado, o certo
#: foi `--aceitar-mudanca MOTIVO`, não baixar o limiar. Aqui é o contrário:
#: manter 700 depois de a linha de base subir faria o alarme tocar todo dia por
#: uma razão já conhecida, que é exatamente como um alarme morre.
#:
#: 750 preserva a mesma proporção de folga que 700 tinha sobre os 663 MB de
#: antes (~5,6%), e fica abaixo dos 740 MB que o banco já sustentou em agosto
#: sem incidente — ou seja, não é território novo. Antes de subir de novo,
#: procurar o que remover: em 2026-08-23 uma compactação devolveu 133 MB.
#:
#: 2026-09-19 — de 750 para 875 MB. O SIH passou a cobrir 2025 e 2026 (até a
#: competência 2026-07), e as oito marts servidas que dependem dele receberam
#: **+666.626 linhas**. Conferido DEPOIS de publicar e compactar: o banco foi de
#: 717 para **828 MB**, +111 MB. 875 devolve ~5,6% de folga sobre o uso corrente,
#: a mesma proporção dos tetos anteriores.
#:
#: ERREI ISTO UMA VEZ ANTES DE ACERTAR, e o erro fica aqui porque é fácil de
#: repetir: `pg_size_pretty` devolve **MiB** (base 1024) e este arquivo divide
#: por **1e6** (MB decimal). Li 684 no `pg_size_pretty`, somei a estimativa em MB
#: decimal e fixei o teto em 820 — mas o banco já estava em 717 MB NA UNIDADE
#: DESTE ARQUIVO, e 820 nasceu pequeno demais para a carga que ele mesmo
#: autorizava. Os dois números sempre descreveram o mesmo banco; a régua é que
#: era outra. Ao mexer neste valor, medir com `pg_database_size()/1e6`.
#:
#: PROCUREI O QUE REMOVER, e o resultado contrariou a expectativa. `VACUUM FULL`
#: em `mart_mortalidade_municipio` — 211 MB, 3,26 milhões de updates acumulados e
#: nenhuma compactação manual na história — devolveu **zero bytes**. A maior
#: tabela do projeto é dado vivo, não inchaço. O recuperável estava no que foi
#: escrito hoje, e voltou: `mart_internacoes_municipio` 128,7 → 113 MB,
#: `mart_demanda_mensal_hospital` 45,8 → 30,4, `mart_fluxo_intermunicipal`
#: 44,2 → 33,1, `mart_forecast_demanda_hospital` 7,9 → 3,8.
#:
#: A causa daquele inchaço é do PIPELINE, não do dado: `_subir_mart.py` reenvia o
#: mart inteiro, e cada linha já existente vira UPDATE — tupla nova, tupla velha
#: morta, arquivo dobrado. Nas duas maiores a carga foi feita só com as linhas de
#: 2025 em diante, depois de conferir que as antigas eram idênticas em disco e no
#: banco: `mart_internacoes_agravo` foi de 39,3 para 65,1 MB com ZERO tuplas
#: mortas — proporcional, sem vacuum. Ver [[upload-upsert-incha-a-tabela]].
#:
#: 2026-09-20 — o TETO NÃO MUDA, e a razão de ele não mudar é a parte que
#: importa. O projeto saiu do plano free para o Pro: a cota de banco foi de
#: 500 MB para **8 GB**, e o banco ocupa ~10% disso. Havia espaço para levar este
#: número a qualquer lugar, e ele fica em 875.
#:
#: Porque a pergunta que este teto responde nunca foi "cabe no plano?". Ele mede
#: FOLGA SOBRE O USO CORRENTE — ele existe para avisar que o banco cresceu mais
#: do que alguém esperava, e esse aviso é igualmente útil com 8 GB livres. Subir
#: para 7 GB "porque cabe" desligaria a guarda sem desligá-la no papel, que é a
#: forma mais cara de perder um alarme.
#:
#: O que mudou foi a CONSEQUÊNCIA de cruzá-lo, e quem lê precisa saber disso: até
#: ontem, estourar significava risco de o provedor restringir o projeto e derrubar
#: o site; hoje significa crescimento acima do previsto e, depois dos 8 GB,
#: US$ 0,125 por GB/mês. Deixou de ser risco de disponibilidade e passou a ser
#: risco de conta. Continua valendo investigar antes de subir o número.
#:
#: Fica registrado o que este comentário dizia até hoje, e não é mais verdade: que
#: o plano era free, que a cota eram 500 MB e que o projeto operava acima dela por
#: tolerância do provedor.
#:
#: 2026-09-20, mais tarde — de 875 para 1.000 MB, e esta subida NÃO contradiz o
#: parágrafo acima. A diferença entre os dois casos é a única coisa que este
#: comentário precisa deixar clara:
#:
#:   * algumas horas atrás a pergunta era "posso subir o teto porque agora cabe?"
#:     — e a resposta foi não, porque caber não é razão: o teto mede surpresa de
#:     crescimento, e afrouxá-lo sem o dado crescer só desliga o alarme;
#:   * agora a pergunta é outra: o dado CRESCEU, por decisão explícita e com o
#:     tamanho conferido antes. `mart_correlacao_causas` e `mart_dengue_semana`
#:     voltaram ao Postgres pela V047, +116 MB medidos (95 da dengue municipal,
#:     21 da correlação), e o banco foi de 828 para **944 MB**. Manter 875 faria
#:     o alarme tocar todo dia por uma razão já conhecida, que é exatamente como
#:     um alarme morre.
#:
#: A regra que separa os dois casos, e que vale para a próxima vez: sobe quando a
#: LINHA DE BASE muda por decisão registrada; não sobe quando só a folga muda.
LIMITE_PADRAO_MB = 1_000.0


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
