-- =============================================================================
-- V023 — Fecha o que a V022 deixou passar: TRUNCATE e views
-- =============================================================================
-- A auditoria que originou a V022 classificou como "somente leitura" as tabelas
-- em que `anon` não tinha INSERT/UPDATE/DELETE. O filtro estava incompleto de
-- duas maneiras:
--
--   1. TRUNCATE ficou de fora do teste. Dezessete tabelas tidas como seguras
--      — incluindo mart_mortalidade_municipio, mart_dengue_semana, todas as
--      dim_* e meta_dataset — mantinham TRUNCATE para `anon`. Sem INSERT não dá
--      para adulterar um número, mas dá para APAGAR a tabela inteira, o que é
--      pior: adulteração deixa rastro no dado, TRUNCATE deixa o vazio.
--
--   2. O levantamento filtrou table_type='BASE TABLE' e não enxergou views.
--      mart_icsap_pares (V016/V021) tinha DELETE, INSERT, TRUNCATE e UPDATE
--      para `anon`.
--
-- Em vez de enumerar objeto por objeto de novo — que foi justamente o que falhou
-- —, esta migration revoga em bloco no schema inteiro. `ALL TABLES IN SCHEMA`
-- no Postgres cobre tabelas E views, então não há terceira categoria esquecida.
--
-- SELECT permanece intacto: a API pública de leitura não muda. `service_role`
-- não é tocado — é o papel dos pipelines.
--
-- Verificação (deve voltar zero linhas):
--   SELECT table_name, privilege_type FROM information_schema.role_table_grants
--    WHERE table_schema='public' AND grantee IN ('anon','authenticated')
--      AND privilege_type IN ('INSERT','UPDATE','DELETE','TRUNCATE');
--
-- Depende de: V022
-- =============================================================================

REVOKE INSERT, UPDATE, DELETE, TRUNCATE ON ALL TABLES IN SCHEMA public FROM anon;
REVOKE INSERT, UPDATE, DELETE, TRUNCATE ON ALL TABLES IN SCHEMA public FROM authenticated;

-- A V022 já cuidou dos privilégios padrão para tabelas novas; repetido aqui para
-- que esta migration seja suficiente sozinha se alguém reconstruir o banco.
ALTER DEFAULT PRIVILEGES IN SCHEMA public
  REVOKE INSERT, UPDATE, DELETE, TRUNCATE ON TABLES FROM anon;
ALTER DEFAULT PRIVILEGES IN SCHEMA public
  REVOKE INSERT, UPDATE, DELETE, TRUNCATE ON TABLES FROM authenticated;
