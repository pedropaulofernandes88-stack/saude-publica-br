-- =============================================================================
-- gerar_schema.sql — emite o DDL completo do schema `public`
-- =============================================================================
-- POR QUE ESTE ARQUIVO EXISTE
--
-- O diretório migrations/ NÃO reproduz este banco. Medido em 2026-08-23:
--
--   * 57 migrações estão aplicadas em produção;
--   * 47 delas foram aplicadas com nome ad-hoc, direto no painel, e não têm
--     arquivo correspondente no repositório;
--   * 22 das 57 são apenas abre/fecha de permissão de escrita, não esquema;
--   * 13 arquivos do repositório nunca foram aplicados — entre eles V007–V015,
--     que criam as tabelas de microdado da arquitetura antiga, e V026, cuja
--     tabela `snapshot_publicacao` não existe em produção.
--
-- Quem clonar o repositório e aplicar migrations/ em ordem NÃO obtém o banco que
-- está no ar. Obtém outro banco.
--
-- A saída deste arquivo é o estado REAL, extraído do catálogo. Ela é o insumo de
-- `migrations/schema/schema.sql`, que é o artefato versionado e a única
-- descrição confiável do esquema.
--
-- COMO REGERAR
--
--   1. rode este arquivo contra o banco (editor SQL do Supabase, psql, ou
--      qualquer cliente com acesso de leitura ao catálogo);
--   2. salve a coluna `ddl` em migrations/schema/schema.sql, na ordem retornada;
--   3. versione o resultado e registre no commit o que mudou.
--
-- Não precisa de permissão de escrita: só lê pg_catalog.
--
-- O QUE A SAÍDA COBRE
--   tabelas, colunas, tipos, nulidade, defaults, PK, UNIQUE, CHECK, FK,
--   índices não implícitos, RLS, policies e views.
--
-- O QUE ELA NÃO COBRE, DE PROPÓSITO
--   * GRANTs de papel — mudam por migração de permissão e são auditados à parte;
--   * schemas fora de `public` (`alertas`, `storage`, `auth`) — o primeiro tem
--     dado de assinante e não deve ser reproduzido por clone; os outros são
--     geridos pelo próprio Supabase;
--   * dados. Esquema e conteúdo são camadas separadas: o conteúdo vem dos
--     Parquet publicados, descritos em data/publicacoes/.
-- =============================================================================

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
select secao, objeto, ddl from tabelas

union all
-- Índices que não vêm de constraint (os de PK/UNIQUE já saíram acima).
select 2, tablename || ':' || indexname, indexdef || ';'
from pg_indexes
where schemaname = 'public'
  and indexname not in (select conname from pg_constraint where contype in ('p', 'u'))

union all
select 3, c.relname,
       'alter table public.' || quote_ident(c.relname) || ' enable row level security;'
from pg_class c
join pg_namespace n on n.oid = c.relnamespace and n.nspname = 'public'
where c.relkind = 'r' and c.relrowsecurity

union all
select 4, c.relname || ':' || p.polname,
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
select 5, viewname,
       'create or replace view public.' || quote_ident(viewname) || ' as ' || definition
from pg_views where schemaname = 'public'

order by 1, 2;
