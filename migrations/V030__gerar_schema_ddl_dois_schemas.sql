-- =============================================================================
-- V030 — gerar_schema_ddl() cobre `public` E `alertas`
-- =============================================================================
-- A V029 restringia a extração ao schema `public`, justificando a exclusão de
-- `alertas` porque ele "tem dado de assinante e não deve ser reproduzido por
-- clone". A justificativa confundia ESQUEMA com DADO: a estrutura da tabela não
-- é dado pessoal; as linhas é que são. Esta função nunca emitiu uma única
-- linha de dado, e continua não emitindo — só DDL.
--
-- O erro aparecia no rebuild: as oito funções de alerta em `public`
-- (alerta_assinar, alerta_confirmar, alerta_destinatarios, alerta_marcar_envio…)
-- referenciam `alertas.assinantes` em 12 pontos. Um banco reconstruído a partir
-- de um schema.sql sem `alertas` falha ao criar essas funções — e um rebuild que
-- falha não prova reprodutibilidade nenhuma.
--
-- `alertas` é pequeno: uma tabela e cinco índices.
--
-- Também passa a qualificar todo objeto com o schema, agora que são dois, e
-- emite `create schema if not exists` na seção 0.
--
-- O QUE CONTINUA DE FORA
--   * dados — de qualquer schema. O conteúdo público vem dos Parquet descritos
--     em data/publicacoes/; o de `alertas` não é reproduzível por desenho;
--   * GRANTs de papel, auditados à parte;
--   * `storage` e `auth`, geridos pelo próprio Supabase.
--
-- REVERSÍVEL: reaplicar a V029 devolve a versão anterior.
-- =============================================================================

create or replace function public.gerar_schema_ddl()
returns table (secao smallint, objeto text, ddl text)
language sql
stable
security definer
set search_path = pg_catalog, public
as $$
    with alvo as (select unnest(array['public','alertas']) as ns),
    cols as (
        select n.nspname as ns, c.relname as objeto, a.attnum as ord,
               '    ' || quote_ident(a.attname) || ' ' || format_type(a.atttypid, a.atttypmod)
               || case when a.attnotnull then ' not null' else '' end
               || coalesce(' default ' || pg_get_expr(d.adbin, d.adrelid), '') as linha
        from pg_class c
        join pg_namespace n on n.oid = c.relnamespace
        join alvo on alvo.ns = n.nspname
        join pg_attribute a on a.attrelid = c.oid and a.attnum > 0 and not a.attisdropped
        left join pg_attrdef d on d.adrelid = c.oid and d.adnum = a.attnum
        where c.relkind = 'r'
    ),
    cons as (
        select n.nspname as ns, c.relname as objeto,
               9000 + case con.contype when 'p' then 1 when 'u' then 2
                                       when 'c' then 3 else 4 end as ord,
               '    constraint ' || quote_ident(con.conname) || ' '
               || pg_get_constraintdef(con.oid) as linha
        from pg_constraint con
        join pg_class c on c.oid = con.conrelid
        join pg_namespace n on n.oid = c.relnamespace
        join alvo on alvo.ns = n.nspname
        where con.contype in ('p','u','c','f')
    )
    select 0::smallint, ns, 'create schema if not exists ' || quote_ident(ns) || ';'
    from alvo where ns <> 'public'
    union all
    select 1::smallint, ns || '.' || objeto,
           'create table if not exists ' || quote_ident(ns) || '.' || quote_ident(objeto) || E' (\n'
           || string_agg(linha, E',\n' order by ord) || E'\n);'
    from (select * from cols union all select * from cons) t
    group by ns, objeto
    union all
    select 2::smallint, schemaname || '.' || tablename || ':' || indexname, indexdef || ';'
    from pg_indexes
    where schemaname in ('public','alertas')
      and indexname not in (select conname from pg_constraint where contype in ('p','u'))
    union all
    select 3::smallint, n.nspname || '.' || p.proname
           || '(' || pg_get_function_identity_arguments(p.oid) || ')',
           pg_get_functiondef(p.oid) || ';'
    from pg_proc p
    join pg_namespace n on n.oid = p.pronamespace
    join alvo on alvo.ns = n.nspname
    where p.prokind = 'f'
    union all
    select 4::smallint, n.nspname || '.' || c.relname,
           'alter table ' || quote_ident(n.nspname) || '.' || quote_ident(c.relname)
           || ' enable row level security;'
    from pg_class c
    join pg_namespace n on n.oid = c.relnamespace
    join alvo on alvo.ns = n.nspname
    where c.relkind = 'r' and c.relrowsecurity
    union all
    select 5::smallint, n.nspname || '.' || c.relname || ':' || p.polname,
           'create policy ' || quote_ident(p.polname)
           || ' on ' || quote_ident(n.nspname) || '.' || quote_ident(c.relname)
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
    join pg_namespace n on n.oid = c.relnamespace
    join alvo on alvo.ns = n.nspname
    union all
    select 6::smallint, n.nspname || '.' || c.relname,
           'create or replace view ' || quote_ident(n.nspname) || '.' || quote_ident(c.relname)
           || coalesce(' with (' || array_to_string(c.reloptions, ', ') || ')', '')
           || ' as ' || pg_get_viewdef(c.oid, true)
    from pg_class c
    join pg_namespace n on n.oid = c.relnamespace
    join alvo on alvo.ns = n.nspname
    where c.relkind = 'v'
    union all
    select 7::smallint, n.nspname || '.' || c.relname || coalesce(':' || a.attname, ''),
           'comment on ' || case when d.objsubid = 0 then
                    case c.relkind when 'v' then 'view' else 'table' end
                else 'column' end
           || ' ' || quote_ident(n.nspname) || '.' || quote_ident(c.relname)
           || coalesce('.' || quote_ident(a.attname), '')
           || ' is ' || quote_literal(d.description) || ';'
    from pg_description d
    join pg_class c on c.oid = d.objoid
    join pg_namespace n on n.oid = c.relnamespace
    join alvo on alvo.ns = n.nspname
    left join pg_attribute a on a.attrelid = c.oid and a.attnum = d.objsubid and d.objsubid > 0
    where c.relkind in ('r','v')
    order by 1, 2;
$$;

revoke all on function public.gerar_schema_ddl() from public, anon, authenticated;
grant execute on function public.gerar_schema_ddl() to service_role;
