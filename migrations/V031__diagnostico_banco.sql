-- =============================================================================
-- V031 — diagnostico_banco(): medir o tamanho para que ele não volte a inchar
-- =============================================================================
-- CONTEXTO
--
-- Em 2026-08-23 o banco foi de **740 MB para 607 MB** — 133 MB (18%)
-- recuperados por VACUUM FULL, sem perder uma única linha:
--
--     mart_internacoes_agravo       61 MB → 35 MB   (323 → 194 bytes/linha)
--     mart_internacoes_municipio   111 MB → 67 MB   (200 → 154 bytes/linha)
--     mart_los_hospital             59 MB → 31 MB   (180 →  95 bytes/linha)
--
-- `mart_internacoes_municipio` chegou a reportar 411 mil linhas vivas tendo
-- 334.769 — 76 mil fantasmas de espaço morto.
--
-- POR QUE MEDIR, E NÃO SÓ LIMPAR
--
-- Ganho de faxina volta. Os pipelines fazem upsert, e o de forecast faz
-- DELETE + INSERT a cada execução: espaço morto se acumula sozinho. Sem
-- medição periódica, o banco engorda de novo em silêncio e ninguém descobre
-- até o plano estourar.
--
-- O QUE NÃO DÁ PARA AUTOMATIZAR, E POR QUÊ
--
-- A medição é automatizável por RPC. A AÇÃO não: `VACUUM` não roda dentro de
-- função nem de transação, e o projeto não guarda senha de banco em lugar
-- nenhum — só chaves de API. `scripts/diagnostico_banco.py` mede, avisa e
-- imprime os comandos exatos; compactar continua manual.
--
-- Declarar essa limitação é melhor que fingir automação que não existe.
--
-- SEGURANÇA
--
-- Mesmo desenho da V028–V030: SECURITY DEFINER com search_path fixo, sem
-- parâmetro (portanto sem superfície de injeção), execução revogada de anon e
-- authenticated e concedida apenas a service_role. A função devolve apenas
-- metadados de tamanho — nenhuma linha de dado.
--
-- REVERSÍVEL: `drop function public.diagnostico_banco();`
-- =============================================================================

create or replace function public.diagnostico_banco()
returns table (
  categoria text,
  objeto text,
  linhas bigint,
  bytes bigint,
  bytes_por_linha numeric,
  detalhe text
)
language sql
stable
security definer
set search_path = pg_catalog, public
as $$
    select 'banco'::text, current_database()::text, null::bigint,
           pg_database_size(current_database()),
           null::numeric,
           'tamanho total do banco'::text
    union all
    select 'tabela', c.relname, s.n_live_tup,
           pg_total_relation_size(c.oid),
           round(pg_relation_size(c.oid)::numeric / nullif(s.n_live_tup, 0), 1),
           'mortas=' || s.n_dead_tup
           || ' heap=' || pg_size_pretty(pg_relation_size(c.oid))
           || ' indices=' || pg_size_pretty(pg_indexes_size(c.oid))
    from pg_class c
    join pg_namespace n on n.oid = c.relnamespace and n.nspname = 'public'
    join pg_stat_user_tables s on s.relid = c.oid
    where c.relkind = 'r'
    union all
    select 'inchaco', c.relname, s.n_dead_tup,
           pg_relation_size(c.oid),
           round(100.0 * s.n_dead_tup / nullif(s.n_live_tup + s.n_dead_tup, 0), 1),
           'pct de tuplas mortas'
    from pg_class c
    join pg_namespace n on n.oid = c.relnamespace and n.nspname = 'public'
    join pg_stat_user_tables s on s.relid = c.oid
    where c.relkind = 'r' and s.n_dead_tup > 1000
    union all
    select 'indice_ocioso', si.relname || '.' || si.indexrelname, si.idx_scan,
           pg_relation_size(si.indexrelid),
           null::numeric,
           'buscas desde ' || (select stats_reset::date::text from pg_stat_database
                               where datname = current_database())
    from pg_stat_user_indexes si
    join pg_index i on i.indexrelid = si.indexrelid
    join pg_class c on c.oid = si.relid
    join pg_namespace n on n.oid = c.relnamespace and n.nspname = 'public'
    where not i.indisprimary and not i.indisunique
      and si.idx_scan < 50 and pg_relation_size(si.indexrelid) > 512 * 1024
    order by 1, 4 desc;
$$;

revoke all on function public.diagnostico_banco() from public, anon, authenticated;
grant execute on function public.diagnostico_banco() to service_role;

comment on function public.diagnostico_banco() is
  'Mede tamanho, inchaco e indices ociosos do schema public. Existe porque o projeto nao tem senha de banco: a MEDICAO e automatizavel por RPC, mas VACUUM nao roda dentro de funcao nem de transacao, entao a ACAO continua manual. Ver docs/ARQUITETURA_DADOS.md.';
