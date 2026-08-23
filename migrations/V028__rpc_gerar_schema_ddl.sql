-- =============================================================================
-- V028 — gerar_schema_ddl(): o esquema descreve a si mesmo, por script
-- =============================================================================
-- POR QUE
--
-- `migrations/` não reproduz este banco. Medido em 2026-08-23: 57 migrações
-- aplicadas, 47 delas com nome ad-hoc e sem arquivo no repositório; 13 arquivos
-- do repositório nunca aplicados. Quem clonar e aplicar migrations/ em ordem
-- obtém outro banco.
--
-- A correção é um `schema.sql` extraído do catálogo e versionado. Mas extrair
-- exige ler `pg_catalog`, e o projeto não tem — de propósito — senha de banco
-- em lugar nenhum: só chaves de API. Sem esta função, a extração viraria um
-- passo manual no painel do Supabase, e passo manual é exatamente o que produziu
-- as 47 migrações ad-hoc.
--
-- Com ela, `scripts/gerar_schema.py` regenera o arquivo por RPC, e a
-- reprodutibilidade do esquema passa a ser verificável em CI em vez de
-- depender de alguém lembrar.
--
-- SEGURANÇA
--
-- SECURITY DEFINER porque `anon` não enxerga `pg_catalog` por completo. Não há
-- superfície de injeção: a função não recebe parâmetro e devolve saída fixa.
-- A execução é revogada de `anon` e `authenticated` e concedida apenas a
-- `service_role` — o DDL das tabelas públicas já é descobrível pelo OpenAPI do
-- PostgREST, mas menor privilégio é o padrão certo mesmo quando o dado não é
-- secreto.
--
-- `search_path` fixo em pg_catalog, public: função SECURITY DEFINER sem
-- search_path fixo é vetor clássico de escalada.
--
-- REVERSÍVEL: `drop function public.gerar_schema_ddl();`
-- =============================================================================

create or replace function public.gerar_schema_ddl()
returns table (secao smallint, objeto text, ddl text)
language sql
stable
security definer
set search_path = pg_catalog, public
as $$
    with cols as (
        select c.relname as objeto, 1 as secao, a.attnum as ord,
               '    ' || quote_ident(a.attname) || ' ' || format_type(a.atttypid, a.atttypmod)
               || case when a.attnotnull then ' not null' else '' end
               || coalesce(' default ' || pg_get_expr(d.adbin, d.adrelid), '') as linha
        from pg_class c
        join pg_namespace n on n.oid = c.relnamespace and n.nspname = 'public'
        join pg_attribute a on a.attrelid = c.oid and a.attnum > 0 and not a.attisdropped
        left join pg_attrdef d on d.adrelid = c.oid and d.adnum = a.attnum
        where c.relkind = 'r'
    ),
    cons as (
        select c.relname as objeto, 1 as secao,
               9000 + case con.contype when 'p' then 1 when 'u' then 2
                                       when 'c' then 3 else 4 end as ord,
               '    constraint ' || quote_ident(con.conname) || ' '
               || pg_get_constraintdef(con.oid) as linha
        from pg_constraint con
        join pg_class c on c.oid = con.conrelid
        join pg_namespace n on n.oid = c.relnamespace and n.nspname = 'public'
        where con.contype in ('p', 'u', 'c', 'f')
    ),
    tabelas as (
        select objeto, secao,
               'create table if not exists public.' || quote_ident(objeto) || E' (\n'
               || string_agg(linha, E',\n' order by ord) || E'\n);' as ddl
        from (select * from cols union all select * from cons) t
        group by objeto, secao
    )
    select secao::smallint, objeto, ddl from tabelas

    union all
    select 2::smallint, tablename || ':' || indexname, indexdef || ';'
    from pg_indexes
    where schemaname = 'public'
      and indexname not in (select conname from pg_constraint where contype in ('p', 'u'))

    union all
    select 3::smallint, c.relname,
           'alter table public.' || quote_ident(c.relname)
           || ' enable row level security;'
    from pg_class c
    join pg_namespace n on n.oid = c.relnamespace and n.nspname = 'public'
    where c.relkind = 'r' and c.relrowsecurity

    union all
    select 4::smallint, c.relname || ':' || p.polname,
           'create policy ' || quote_ident(p.polname)
           || ' on public.' || quote_ident(c.relname)
           || ' for ' || case p.polcmd when 'r' then 'select' when 'a' then 'insert'
                                       when 'w' then 'update' when 'd' then 'delete'
                                       else 'all' end
           || ' to ' || coalesce((select string_agg(quote_ident(r.rolname), ', ')
                                  from unnest(p.polroles) pr join pg_roles r on r.oid = pr),
                                 'public')
           || coalesce(' using (' || pg_get_expr(p.polqual, p.polrelid) || ')', '')
           || coalesce(' with check (' || pg_get_expr(p.polwithcheck, p.polrelid) || ')', '')
           || ';'
    from pg_policy p
    join pg_class c on c.oid = p.polrelid
    join pg_namespace n on n.oid = c.relnamespace and n.nspname = 'public'

    union all
    select 5::smallint, viewname,
           'create or replace view public.' || quote_ident(viewname)
           || ' as ' || definition
    from pg_views where schemaname = 'public'

    order by 1, 2;
$$;

revoke all on function public.gerar_schema_ddl() from public, anon, authenticated;
grant execute on function public.gerar_schema_ddl() to service_role;

comment on function public.gerar_schema_ddl() is
  'Emite o DDL do schema public (tabelas, constraints, índices, RLS, policies, '
  'views) para que scripts/gerar_schema.py versione migrations/schema/schema.sql. '
  'Existe porque migrations/ não reproduz este banco: 47 das 57 migrações '
  'aplicadas foram feitas ad-hoc, sem arquivo. Só service_role executa.';
