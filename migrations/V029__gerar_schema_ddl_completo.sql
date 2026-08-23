-- =============================================================================
-- V029 — gerar_schema_ddl() passa a cobrir o que a V028 deixava cair
-- =============================================================================
-- A V028 extraía tabelas, constraints, índices, RLS, policies e views. Ao
-- preparar o rebuild — reconstruir o banco a partir de schema.sql e dos Parquet
-- publicados — três lacunas apareceram, e a primeira é de SEGURANÇA:
--
--   1. OPÇÕES DA VIEW. `mart_icsap_pares` tem `security_invoker=true`, imposto
--      pela V025 justamente para que a view respeite as permissões de quem
--      consulta em vez das do dono. `pg_views.definition` NÃO devolve as
--      reloptions, então um rebuild recriaria a view sem essa opção e
--      desfaria a correção de segurança em silêncio.
--
--   2. COMENTÁRIOS. 32 de tabela e 25 de coluna. Não são decoração: os da V027
--      documentam que `status_validacao` é derivado de erro medido, que
--      `confianca` está obsoleta e que `ic_inferior` usa z calibrado. Perder
--      isso num rebuild transformaria a API pública em colunas sem semântica.
--
--   3. FUNÇÕES. Nove no schema public, incluindo as RPCs de alerta
--      (`alerta_destinatarios`, `alerta_marcar_envio`) das quais a Edge Function
--      depende. Um banco reconstruído sem elas parece completo e quebra no
--      primeiro envio de boletim.
--
-- Nada disso apareceria num teste de contagem de linhas. Só apareceria quando
-- alguém tentasse usar o banco reconstruído — que é tarde demais.
--
-- ORDEM DA SAÍDA importa para replay: tabelas, índices, funções, RLS, policies,
-- views e por último comentários, que referenciam objetos que precisam existir.
--
-- REVERSÍVEL: reaplicar a V028 devolve a versão anterior.
-- =============================================================================

create or replace function public.gerar_schema_ddl()
returns table (secao smallint, objeto text, ddl text)
language sql
stable
security definer
set search_path = pg_catalog, public
as $$
    with cols as (
        select c.relname as objeto, a.attnum as ord,
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
        select c.relname as objeto,
               9000 + case con.contype when 'p' then 1 when 'u' then 2
                                       when 'c' then 3 else 4 end as ord,
               '    constraint ' || quote_ident(con.conname) || ' '
               || pg_get_constraintdef(con.oid) as linha
        from pg_constraint con
        join pg_class c on c.oid = con.conrelid
        join pg_namespace n on n.oid = c.relnamespace and n.nspname = 'public'
        where con.contype in ('p', 'u', 'c', 'f')
    )
    select 1::smallint, objeto,
           'create table if not exists public.' || quote_ident(objeto) || E' (\n'
           || string_agg(linha, E',\n' order by ord) || E'\n);'
    from (select * from cols union all select * from cons) t
    group by objeto

    union all
    select 2::smallint, tablename || ':' || indexname, indexdef || ';'
    from pg_indexes
    where schemaname = 'public'
      and indexname not in (select conname from pg_constraint where contype in ('p', 'u'))

    union all
    -- Funções antes de RLS e views: uma policy ou uma view podem chamá-las.
    select 3::smallint, p.proname || '(' || pg_get_function_identity_arguments(p.oid) || ')',
           pg_get_functiondef(p.oid) || ';'
    from pg_proc p
    join pg_namespace n on n.oid = p.pronamespace and n.nspname = 'public'
    where p.prokind = 'f'

    union all
    select 4::smallint, c.relname,
           'alter table public.' || quote_ident(c.relname) || ' enable row level security;'
    from pg_class c
    join pg_namespace n on n.oid = c.relnamespace and n.nspname = 'public'
    where c.relkind = 'r' and c.relrowsecurity

    union all
    select 5::smallint, c.relname || ':' || p.polname,
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
    -- As reloptions da view entram junto com o CREATE: `security_invoker=true`
    -- perdido é a correção da V025 desfeita.
    select 6::smallint, c.relname,
           'create or replace view public.' || quote_ident(c.relname)
           || coalesce(' with (' || array_to_string(c.reloptions, ', ') || ')', '')
           || ' as ' || pg_get_viewdef(c.oid, true)
    from pg_class c
    join pg_namespace n on n.oid = c.relnamespace and n.nspname = 'public'
    where c.relkind = 'v'

    union all
    -- Comentários por último: referenciam objetos que precisam existir.
    select 7::smallint, c.relname || coalesce(':' || a.attname, ''),
           'comment on ' || case when d.objsubid = 0 then
                    case c.relkind when 'v' then 'view' else 'table' end
                else 'column' end
           || ' public.' || quote_ident(c.relname)
           || coalesce('.' || quote_ident(a.attname), '')
           || ' is ' || quote_literal(d.description) || ';'
    from pg_description d
    join pg_class c on c.oid = d.objoid
    join pg_namespace n on n.oid = c.relnamespace and n.nspname = 'public'
    left join pg_attribute a on a.attrelid = c.oid and a.attnum = d.objsubid
                                and d.objsubid > 0
    where c.relkind in ('r', 'v')

    order by 1, 2;
$$;

revoke all on function public.gerar_schema_ddl() from public, anon, authenticated;
grant execute on function public.gerar_schema_ddl() to service_role;
