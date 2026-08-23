"""
Testes do reconstrutor (scripts/reconstruir.py).

O rebuild é o que transforma "esquema reproduzível" de afirmação sobre arquivos
em fato verificado. A execução completa exige um Postgres descartável e roda no
CI; aqui ficam as partes que se testam sem banco — e a mais arriscada delas é o
separador de instruções.

Um split ingênuo por `;` truncaria TODA função: o corpo entre `$$…$$` tem
ponto-e-vírgula dentro, e este esquema tem nove funções, a maior com 5.070
caracteres. Um schema.sql que aplica pela metade é pior que um que falha: ele
cria um banco parecido com o certo.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from reconstruir import _instrucoes, proteger  # noqa: E402

pytestmark = pytest.mark.unit

SCHEMA = Path(__file__).resolve().parents[1] / "migrations" / "schema" / "schema.sql"


def test_corpo_de_funcao_nao_e_partido_no_ponto_e_virgula() -> None:
    sql = """
create table t (a int);
create function f() returns int language sql as $$
    select 1;
    select 2;
$$;
create table u (b int);
"""
    ins = _instrucoes(sql)
    assert len(ins) == 3
    corpo = [i for i in ins if "function" in i][0]
    assert corpo.count("$$") == 2
    assert "select 1;" in corpo and "select 2;" in corpo


def test_marcadores_nomeados_tambem_sao_respeitados() -> None:
    """`pg_get_functiondef` emite `$function$`, não `$$`."""
    sql = """
create function f() returns int language sql as $function$
    select 1;
$function$;
create table t (a int);
"""
    ins = _instrucoes(sql)
    assert len(ins) == 2
    assert ins[0].count("$function$") == 2


def test_comentario_solto_nao_vira_instrucao() -> None:
    ins = _instrucoes("-- só um comentário\n\n-- outro\n")
    assert ins == []


@pytest.mark.skipif(not SCHEMA.exists(), reason="schema.sql ainda não foi gerado")
def test_schema_real_separa_sem_truncar_nenhuma_funcao() -> None:
    """O teste que importa: o arquivo de verdade, não um sintético."""
    ins = _instrucoes(SCHEMA.read_text(encoding="utf-8"))
    assert len(ins) > 150, f"só {len(ins)} instruções — o parser engoliu algo"
    funcoes = [i for i in ins if "FUNCTION" in i.upper()]
    assert funcoes, "nenhuma função encontrada no schema.sql"
    for f in funcoes:
        for marca in ("$function$", "$$"):
            if marca in f:
                assert f.count(marca) % 2 == 0, (
                    f"função truncada: {marca} desbalanceado em {f[:80]}")
                break


def test_guarda_recusa_o_host_de_producao() -> None:
    """Reconstruir do zero apontando para produção apagaria o que está no ar."""
    env = {"SUPABASE_URL": "https://zekjhmxjamatlxpkykde.supabase.co"}
    with pytest.raises(SystemExit, match="RECUSADO"):
        proteger("postgresql://u:p@db.zekjhmxjamatlxpkykde.supabase.co:5432/postgres", env)


def test_guarda_recusa_qualquer_supabase_gerenciado() -> None:
    env = {"SUPABASE_URL": "https://outro-projeto.supabase.co"}
    with pytest.raises(SystemExit, match="RECUSADO"):
        proteger("postgresql://u:p@db.terceiro.supabase.co:5432/postgres", env)


def test_guarda_permite_postgres_descartavel() -> None:
    env = {"SUPABASE_URL": "https://zekjhmxjamatlxpkykde.supabase.co"}
    proteger("postgresql://postgres:postgres@localhost:5432/postgres", env)
