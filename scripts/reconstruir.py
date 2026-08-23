"""
reconstruir.py — prova que o banco se reconstrói a partir do repositório
=========================================================================

Constrói um Postgres vazio a partir de dois artefatos versionados:

    migrations/schema/schema.sql     o esquema (200 objetos)
    data/publicacoes/{id}.json       o manifesto, que aponta os Parquet

e confere o resultado contra o manifesto. Se passar, "esquema integralmente
reproduzível" deixa de ser intenção e vira fato verificado.

    python scripts/reconstruir.py --destino postgresql://postgres:postgres@localhost:5432/postgres
    python scripts/reconstruir.py --destino ... --amostra 3

POR QUE ISTO É O TESTE QUE FALTAVA
----------------------------------
Saber que o esquema está versionado e que os dados estão em arquivo não prova
que os dois JUNTOS reconstroem o sistema. Só a execução prova. Enquanto ela não
existir, "reproduzível" é uma afirmação sobre arquivos, não sobre resultado.

E o teste já se pagou antes de existir: preparando este script apareceram três
lacunas no `schema.sql` que nenhuma contagem de linhas denunciaria —
`security_invoker=true` da view (correção de segurança da V025 que um rebuild
desfaria em silêncio), 57 comentários de tabela e coluna, e as 9 funções, das
quais 8 referenciam `alertas.assinantes` num schema que a extração nem cobria.

ONDE RODA
---------
Contra um Postgres DESCARTÁVEL — o serviço do CI, ou um contêiner local. NUNCA
contra produção: o script recusa-se a rodar se o destino for o host de produção,
e recusa-se a rodar num banco que já tenha tabelas, porque reconstruir por cima
de dado existente não prova nada e pode destruir muito.

O QUE ELE NÃO PROVA
-------------------
GRANTs de papel e configuração do Supabase (PostgREST, Storage, Auth) estão fora
do `schema.sql` e continuam fora daqui. Isto prova a reprodutibilidade do
ESQUEMA e do CONTEÚDO, não a do serviço gerenciado em volta deles.
"""
from __future__ import annotations

import argparse
import io
import re
import sys
import time
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _publicacao import (  # noqa: E402
    MARTS,
    baixar_do_storage,
    carregar_env,
    carregar_manifesto,
)

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = ROOT / "migrations" / "schema" / "schema.sql"

#: Papéis que o Supabase cria e das quais as policies dependem. Um Postgres
#: virgem não os tem, e `create policy ... to anon` falharia. Criá-los é parte de
#: reproduzir o ambiente, não um atalho.
PAPEIS = ("anon", "authenticated", "service_role")

#: Marcador de nulo no COPY. Vazio NÃO serve: com `NULL ''` um texto legitimamente
#: vazio viraria NULL, corrompendo dado em silêncio.
NULO = "\\N"

FALHAS: list[str] = []


def check(nome: str, ok: bool, detalhe: str = "") -> bool:
    print(f"[{'OK ' if ok else 'FALHOU'}] {nome} {detalhe}", flush=True)
    if not ok:
        FALHAS.append(nome)
    return ok


# ---------------------------------------------------------------------------
# Guardas
# ---------------------------------------------------------------------------

def proteger(dsn: str, env: dict) -> None:
    """Recusa destinos perigosos antes de qualquer escrita."""
    host_producao = env["SUPABASE_URL"].split("//")[-1].split(".")[0]
    if host_producao and host_producao in dsn:
        raise SystemExit(
            f"RECUSADO: o destino contém o identificador de produção ({host_producao}).\n"
            "Este script reconstrói do zero e nunca deve apontar para o banco publicado.")
    if "supabase.co" in dsn or "supabase.com" in dsn:
        raise SystemExit(
            "RECUSADO: destino parece ser um banco Supabase gerenciado.\n"
            "Use um Postgres descartável (serviço do CI ou contêiner local).")


def exigir_banco_vazio(cur) -> None:
    cur.execute("""
        select count(*) from information_schema.tables
        where table_schema not in ('pg_catalog','information_schema')
    """)
    (n,) = cur.fetchone()
    if n:
        raise SystemExit(
            f"RECUSADO: o destino já tem {n} tabela(s).\n"
            "Reconstruir por cima de dado existente não prova reprodutibilidade "
            "e pode destruir o que estava lá. Use um banco vazio.")


# ---------------------------------------------------------------------------
# Etapas
# ---------------------------------------------------------------------------

def criar_papeis(cur) -> None:
    for papel in PAPEIS:
        cur.execute(
            "do $$ begin if not exists (select 1 from pg_roles where rolname=%s) "
            "then execute format('create role %%I nologin', %s); end if; end $$;",
            (papel, papel))
    print(f"[1/4] papéis garantidos: {', '.join(PAPEIS)}", flush=True)


def _instrucoes(sql: str) -> list[str]:
    """Separa o arquivo em instruções, respeitando corpos $$…$$ das funções.

    Um split ingênuo por ';' quebraria toda função: o corpo tem ponto-e-vírgula
    dentro. Nove das dez funções deste esquema seriam truncadas.
    """
    def util(texto: str) -> bool:
        """Só é instrução o que tem alguma linha que não seja comentário nem vazia."""
        return bool(texto) and any(
            ln.strip() and not ln.strip().startswith("--") for ln in texto.splitlines())

    partes, atual, dentro = [], [], None
    for linha in sql.splitlines():
        atual.append(linha)
        for marca in re.findall(r"\$[A-Za-z_]*\$", linha):
            dentro = None if dentro == marca else (dentro or marca)
        if dentro is None and linha.rstrip().endswith(";"):
            texto = "\n".join(atual).strip()
            if util(texto):
                partes.append(texto)
            atual = []
    # O resto passa pelo MESMO filtro: um rabo de comentários no fim do arquivo
    # virava "instrução" e seria enviado ao banco como se fosse DDL.
    resto = "\n".join(atual).strip()
    if util(resto):
        partes.append(resto)
    return partes


def aplicar_schema(cur) -> int:
    if not SCHEMA.exists():
        raise SystemExit(f"{SCHEMA.relative_to(ROOT)} não existe — rode scripts/gerar_schema.py")
    instrucoes = _instrucoes(SCHEMA.read_text(encoding="utf-8"))
    for i, instrucao in enumerate(instrucoes, 1):
        try:
            cur.execute(instrucao)
        except Exception as exc:
            raise SystemExit(
                f"schema.sql falhou na instrução {i}/{len(instrucoes)}:\n"
                f"{instrucao[:300]}\n\n{exc}") from exc
    print(f"[2/4] schema.sql aplicado: {len(instrucoes)} instruções", flush=True)
    return len(instrucoes)


def _parquet(nome: str, env: dict) -> pd.DataFrame:
    local = MARTS / f"{nome}.parquet"
    if local.exists():
        return pd.read_parquet(local)
    return pd.read_parquet(io.BytesIO(baixar_do_storage(f"{nome}.parquet", env)))


def carregar_dados(cur, man, env: dict, amostra: int | None, quieto: bool) -> int:
    tabelas = sorted(man.tabelas)
    if amostra:
        tabelas = tabelas[:amostra]
    total = 0
    for nome in tabelas:
        # A view é derivada: ela se materializa sozinha a partir das tabelas.
        # Tentar carregá-la seria escrever numa view sem trigger.
        cur.execute("select relkind from pg_class c join pg_namespace n "
                    "on n.oid=c.relnamespace where n.nspname='public' and c.relname=%s", (nome,))
        linha = cur.fetchone()
        if not linha or linha[0] != "r":
            if not quieto:
                print(f"      {nome}: view — derivada do esquema, não carregada", flush=True)
            continue

        df = _parquet(nome, env)
        buf = io.StringIO()
        df.to_csv(buf, index=False, header=False, na_rep=NULO)
        buf.seek(0)
        colunas = ", ".join(f'"{c}"' for c in df.columns)
        with cur.copy(
            f'copy public."{nome}" ({colunas}) from stdin '
            f"with (format csv, null '{NULO}')"
        ) as copy:
            copy.write(buf.read())
        total += len(df)
        if not quieto:
            print(f"      {nome}: {len(df):,} linhas", flush=True)
    print(f"[3/4] dados carregados: {total:,} linhas em {len(tabelas)} tabelas", flush=True)
    return total


def conferir(cur, man, amostra: int | None) -> None:
    print("\n[4/4] conferindo o banco reconstruído contra o manifesto\n", flush=True)
    tabelas = sorted(man.tabelas)
    if amostra:
        tabelas = tabelas[:amostra]

    for nome in tabelas:
        cur.execute("select relkind from pg_class c join pg_namespace n "
                    "on n.oid=c.relnamespace where n.nspname='public' and c.relname=%s", (nome,))
        linha = cur.fetchone()
        if not check(f"{nome}: objeto existe", bool(linha)):
            continue
        if linha[0] != "r":
            cur.execute(f'select count(*) from public."{nome}"')
            (n,) = cur.fetchone()
            check(f"{nome}: view materializa linhas", n > 0, f"{n:,}")
            continue
        cur.execute(f'select count(*) from public."{nome}"')
        (n,) = cur.fetchone()
        esperado = man.tabelas[nome].linhas
        check(f"{nome}: linhas == manifesto", n == esperado,
              f"reconstruído={n:,} manifesto={esperado:,}")

    if amostra:
        print("\n(amostra: checagens de esquema puladas)", flush=True)
        return

    print()
    cur.execute("select count(*) from pg_policy p join pg_class c on c.oid=p.polrelid "
                "join pg_namespace n on n.oid=c.relnamespace where n.nspname='public'")
    (n_pol,) = cur.fetchone()
    check("policies recriadas", n_pol == 36, f"{n_pol} de 36")

    cur.execute("select reloptions from pg_class c join pg_namespace n on n.oid=c.relnamespace "
                "where n.nspname='public' and c.relname='mart_icsap_pares'")
    (opts,) = cur.fetchone() or (None,)
    # A V025 impôs security_invoker; um rebuild que o perdesse desfaria a
    # correção sem falhar em nada mais.
    check("view mantém security_invoker", bool(opts) and "security_invoker=true" in opts,
          str(opts))

    cur.execute("select count(*) from pg_description d join pg_class c on c.oid=d.objoid "
                "join pg_namespace n on n.oid=c.relnamespace where n.nspname in ('public','alertas')")
    (n_com,) = cur.fetchone()
    check("comentários preservados", n_com >= 55, f"{n_com}")

    cur.execute("select count(*) from pg_proc p join pg_namespace n on n.oid=p.pronamespace "
                "where n.nspname='public' and p.prokind='f'")
    (n_fn,) = cur.fetchone()
    check("funções recriadas", n_fn == 10, f"{n_fn} de 10")

    cur.execute("select count(*) from information_schema.tables where table_schema='alertas'")
    (n_al,) = cur.fetchone()
    check("schema alertas reconstruído", n_al == 1, f"{n_al} tabela(s)")

    cur.execute("select count(*) from pg_class c join pg_namespace n on n.oid=c.relnamespace "
                "where n.nspname='public' and c.relkind='r' and c.relrowsecurity")
    (n_rls,) = cur.fetchone()
    check("RLS habilitado nas tabelas", n_rls == 36, f"{n_rls} de 36")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[1])
    ap.add_argument("--destino", required=True, help="DSN de um Postgres DESCARTÁVEL")
    ap.add_argument("--amostra", type=int, default=None,
                    help="carrega só as N primeiras tabelas (execução rápida)")
    ap.add_argument("--quieto", action="store_true")
    args = ap.parse_args()

    try:
        import psycopg
    except ImportError:
        raise SystemExit("psycopg não instalado — pip install 'psycopg[binary]'") from None

    env = carregar_env()
    proteger(args.destino, env)

    man = carregar_manifesto()
    if man is None:
        raise SystemExit("nenhuma publicação em data/publicacoes/ — rode scripts/publicar.py")

    print(f"reconstruindo a partir da publicação {man.id}")
    print(f"esquema: {SCHEMA.relative_to(ROOT)}")
    r = man.resumo()
    print(f"manifesto: {r['n_tabelas']} tabelas · {r['n_linhas']:,} linhas\n")

    t0 = time.time()
    with psycopg.connect(args.destino, autocommit=True) as conn, conn.cursor() as cur:
        exigir_banco_vazio(cur)
        criar_papeis(cur)
        aplicar_schema(cur)
        carregar_dados(cur, man, env, args.amostra, args.quieto)
        cur.execute("analyze")
        conferir(cur, man, args.amostra)

    print(f"\ntempo: {time.time() - t0:.0f}s")
    if FALHAS:
        print(f"❌ {len(FALHAS)} divergência(s): {FALHAS[:8]}"
              + (" …" if len(FALHAS) > 8 else ""))
        sys.exit(1)
    print("✅ o banco foi reconstruído do repositório e confere com o manifesto")


if __name__ == "__main__":
    main()
