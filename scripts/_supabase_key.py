"""
_supabase_key.py — escolhe a chave certa para cada tipo de acesso ao Supabase.

Contexto: a chave `anon` e PUBLICA por desenho — o README a divulga como chave de
leitura e ela esta no .env.example. Durante muito tempo os pipelines tambem
escreveram com ela, o que so funcionava porque o papel `anon` tinha INSERT/UPDATE/
DELETE nas tabelas de mart. Isso significa que qualquer pessoa com o repositorio
aberto podia sobrescrever ou esvaziar os dados publicados.

A correcao tem duas metades, e elas precisam entrar nesta ordem:
  1. os pipelines passam a ESCREVER com a chave service_role (este modulo);
  2. so entao se revoga a escrita de `anon` (migration V022).

Inverter a ordem derruba a publicacao inteira.

Uso:
    from _supabase_key import chave_escrita, chave_leitura
    url, key = env["SUPABASE_URL"], chave_escrita(env)

Leitura continua usando `anon`: e o mesmo acesso que qualquer pessoa tem pela API
publica, entao ler com service_role so aumentaria o estrago de um vazamento.
"""
from __future__ import annotations

import os

VAR_ESCRITA = "SUPABASE_SERVICE_ROLE_KEY"
VAR_LEITURA = "SUPABASE_ANON_KEY"
_avisado = False


def chave_leitura(env: dict[str, str]) -> str:
    k = env.get(VAR_LEITURA) or os.environ.get(VAR_LEITURA)
    if not k:
        raise SystemExit(f"Defina {VAR_LEITURA} no .env")
    return k


def chave_escrita(env: dict[str, str]) -> str:
    """Chave para POST/PATCH/DELETE. Prefere service_role; aceita anon com aviso
    enquanto a revogacao dos grants nao foi aplicada."""
    global _avisado
    k = env.get(VAR_ESCRITA) or os.environ.get(VAR_ESCRITA)
    if k:
        return k
    k = env.get(VAR_LEITURA) or os.environ.get(VAR_LEITURA)
    if not k:
        raise SystemExit(
            f"Defina {VAR_ESCRITA} no .env para publicar "
            f"(a chave {VAR_LEITURA} e publica e nao deve ter permissao de escrita)."
        )
    if not _avisado:
        _avisado = True
        print(
            f"[supabase] AVISO: escrevendo com {VAR_LEITURA}, que e uma chave PUBLICA. "
            f"Isso so funciona nas tabelas em que `anon` ainda tem INSERT/UPDATE — "
            f"um buraco que a migration V022 fecha. Defina {VAR_ESCRITA} no .env.",
            flush=True,
        )
    return k
