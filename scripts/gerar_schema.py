"""
gerar_schema.py — extrai o esquema real do banco e o versiona
==============================================================

Escreve `migrations/schema/schema.sql` a partir do catálogo do Postgres, via a
função `public.gerar_schema_ddl()` (migração V028).

    .venv311/Scripts/python scripts/gerar_schema.py
    .venv311/Scripts/python scripts/gerar_schema.py --conferir

POR QUE ESTE ARQUIVO EXISTE
---------------------------
`migrations/` NÃO reproduz este banco. Medido em 2026-08-23:

  * 57 migrações aplicadas em produção;
  * 47 delas com nome ad-hoc, aplicadas direto no painel, sem arquivo no
    repositório;
  * 22 das 57 são apenas abre/fecha de permissão de escrita, não esquema;
  * 13 arquivos do repositório nunca foram aplicados — entre eles V007–V015, que
    criam as tabelas de microdado da arquitetura antiga. A V026 também nunca foi
    aplicada e agora está aposentada em `migrations/archive/`.

Quem clonar o repositório e aplicar `migrations/` em ordem obtém **outro banco**.

`schema.sql` passa a ser a descrição confiável: extraída do que está no ar, e
não da soma de intenções registradas ao longo de dois meses.

MIGRAÇÕES CONTINUAM VALENDO
---------------------------
Elas registram a *intenção* e o *porquê* de cada mudança — é o histórico
editorial, e os comentários de V020, V022 e V027 valem por si. `schema.sql`
registra o *estado*. Um não substitui o outro; o que não existia era o segundo.

`--conferir` não escreve: compara o arquivo versionado com o banco e sai com
código ≠ 0 se divergirem. É o modo de CI — detecta que alguém aplicou DDL sem
versionar, que é como as 47 migrações ad-hoc surgiram.
"""
from __future__ import annotations

import argparse
import difflib
import sys
from datetime import UTC, datetime
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _publicacao import carregar_env  # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parents[1]
DESTINO = ROOT / "migrations" / "schema" / "schema.sql"

SECOES = {
    0: "Schemas",
    1: "Tabelas, colunas e constraints",
    2: "Índices (os de PK e UNIQUE saem junto com a constraint)",
    3: "Funções",
    4: "Row Level Security",
    5: "Policies",
    6: "Views",
    7: "Comentários",
}


def obter_ddl(env: dict[str, str]) -> list[dict]:
    """Chama a RPC. Exige a chave de serviço: a função é revogada de anon."""
    chave = env.get("SUPABASE_SERVICE_ROLE_KEY")
    if not chave:
        raise SystemExit(
            "SUPABASE_SERVICE_ROLE_KEY ausente — gerar_schema_ddl() só é executável "
            "por service_role (ver migrations/V028)")
    url = env["SUPABASE_URL"].rstrip("/")
    r = requests.post(f"{url}/rest/v1/rpc/gerar_schema_ddl",
                      headers={"apikey": chave, "Content-Type": "application/json"},
                      json={}, timeout=180)
    if r.status_code == 404:
        raise SystemExit(
            "gerar_schema_ddl() não existe no banco — aplique migrations/V028 antes")
    r.raise_for_status()
    return r.json()


def montar(linhas: list[dict]) -> str:
    cabecalho = [
        "-- =============================================================================",
        "-- schema.sql — o esquema REAL do banco, extraído do catálogo",
        "-- =============================================================================",
        "-- GERADO por scripts/gerar_schema.py. Não editar à mão: a próxima execução",
        "-- sobrescreve. Para mudar o esquema, escreva uma migração, aplique-a e regere.",
        "--",
        "-- Este arquivo existe porque migrations/ não reproduz este banco: das 57",
        "-- migrações aplicadas em produção, 47 foram feitas ad-hoc e não têm arquivo no",
        "-- repositório. As migrações registram a INTENÇÃO de cada mudança; este arquivo",
        "-- registra o ESTADO. Um não substitui o outro.",
        "--",
        "-- Cobre os schemas `public` e `alertas` — apenas ESTRUTURA, nenhuma linha de",
        "-- dado. Não cobre: GRANTs de papel (auditados à parte), `storage` e `auth`",
        "-- (geridos pelo Supabase), e o conteúdo, que vem dos Parquet em data/publicacoes/.",
        "--",
        f"-- Extraído em: {datetime.now(UTC).strftime('%Y-%m-%d %H:%M UTC')}",
        f"-- Objetos: {len(linhas)}",
        "-- =============================================================================",
        "",
    ]
    partes = ["\n".join(cabecalho)]
    secao_atual = None
    for linha in linhas:
        secao = int(linha["secao"])
        if secao != secao_atual:
            secao_atual = secao
            partes.append(
                f"\n-- ── {SECOES.get(secao, secao)} "
                + "─" * max(4, 60 - len(SECOES.get(secao, str(secao))))
                + "\n")
        partes.append(linha["ddl"].rstrip() + "\n")
    return "\n".join(partes).rstrip() + "\n"


def main() -> None:
    ap = argparse.ArgumentParser(description="Versiona o esquema real do banco.")
    ap.add_argument("--conferir", action="store_true",
                    help="não escreve; falha se o arquivo versionado divergir do banco")
    args = ap.parse_args()

    env = carregar_env()
    linhas = obter_ddl(env)
    texto = montar(linhas)

    por_secao: dict[int, int] = {}
    for linha in linhas:
        por_secao[int(linha["secao"])] = por_secao.get(int(linha["secao"]), 0) + 1
    print(f"[schema] {len(linhas)} objetos: "
          + " · ".join(f"{SECOES[s].split('(')[0].strip().lower()}={n}"
                       for s, n in sorted(por_secao.items())), flush=True)

    if not args.conferir:
        DESTINO.parent.mkdir(parents=True, exist_ok=True)
        DESTINO.write_text(texto, encoding="utf-8", newline="\n")
        print(f"[ok] {DESTINO.relative_to(ROOT)} ({len(texto):,} bytes) — versione-o", flush=True)
        return

    if not DESTINO.exists():
        raise SystemExit(f"{DESTINO.relative_to(ROOT)} não existe — rode sem --conferir")

    # A data de extração muda a cada execução e não é divergência de esquema.
    def sem_data(t: str) -> list[str]:
        return [ln for ln in t.splitlines() if not ln.startswith("-- Extraído em:")]

    versionado, atual = sem_data(DESTINO.read_text(encoding="utf-8")), sem_data(texto)
    if versionado == atual:
        print("[ok] schema.sql versionado corresponde ao banco", flush=True)
        return

    print("\n❌ o esquema do banco divergiu do arquivo versionado:\n", flush=True)
    for linha in list(difflib.unified_diff(
            versionado, atual, "schema.sql (git)", "banco (agora)", lineterm=""))[:60]:
        print("   " + linha, flush=True)
    print("\n   alguém aplicou DDL sem versionar. Rode scripts/gerar_schema.py "
          "e commite o resultado.", flush=True)
    sys.exit(1)


if __name__ == "__main__":
    main()
