-- =============================================================================
-- V022 — Revoga escrita de `anon` nas tabelas de mart
-- =============================================================================
-- A chave `anon` do Supabase é PÚBLICA por desenho: o README a divulga como chave
-- de leitura da API e ela está no .env.example. Mesmo assim, 18 das 35 tabelas
-- concediam INSERT, UPDATE, DELETE e TRUNCATE ao papel `anon` — ou seja, qualquer
-- pessoa com o repositório aberto podia sobrescrever ou esvaziar os dados
-- publicados. As outras 17 (mortalidade, dengue, internações municipais, dims,
-- meta_dataset) já estavam corretas, o que sugere um endurecimento parcial feito
-- em algum momento e não propagado aos marts de SIH e das análises.
--
-- ORDEM IMPORTA. Esta migration só pode ser aplicada DEPOIS que os pipelines
-- estiverem escrevendo com a chave service_role (scripts/_supabase_key.py, que
-- lê SUPABASE_SERVICE_ROLE_KEY do .env). Aplicar antes derruba toda a publicação:
-- os 16 scripts que fazem POST passariam a receber 401.
--
-- `authenticated` recebe o mesmo tratamento: o projeto não usa login para
-- escrita, e deixar o papel com INSERT só reabriria o mesmo buraco por outra
-- porta se algum dia houver cadastro de usuário.
--
-- `service_role` mantém tudo — é o papel dos pipelines.
-- SELECT permanece para todos: a API pública de leitura não muda.
--
-- Como verificar depois de aplicar:
--   SELECT table_name, grantee, privilege_type
--     FROM information_schema.role_table_grants
--    WHERE table_schema='public' AND grantee='anon'
--      AND privilege_type IN ('INSERT','UPDATE','DELETE','TRUNCATE');
--   -- deve voltar zero linhas
--
-- Depende de: scripts/_supabase_key.py (chave de escrita), V019-V021
-- =============================================================================

REVOKE INSERT, UPDATE, DELETE, TRUNCATE ON public.dim_cluster_municipio FROM anon;
REVOKE INSERT, UPDATE, DELETE, TRUNCATE ON public.dim_cluster_municipio FROM authenticated;

REVOKE INSERT, UPDATE, DELETE, TRUNCATE ON public.mart_cnes_municipio FROM anon;
REVOKE INSERT, UPDATE, DELETE, TRUNCATE ON public.mart_cnes_municipio FROM authenticated;

REVOKE INSERT, UPDATE, DELETE, TRUNCATE ON public.mart_cobertura_aps_municipio FROM anon;
REVOKE INSERT, UPDATE, DELETE, TRUNCATE ON public.mart_cobertura_aps_municipio FROM authenticated;

REVOKE INSERT, UPDATE, DELETE, TRUNCATE ON public.mart_cobertura_icsap_municipio FROM anon;
REVOKE INSERT, UPDATE, DELETE, TRUNCATE ON public.mart_cobertura_icsap_municipio FROM authenticated;

REVOKE INSERT, UPDATE, DELETE, TRUNCATE ON public.mart_demanda_mensal_hospital FROM anon;
REVOKE INSERT, UPDATE, DELETE, TRUNCATE ON public.mart_demanda_mensal_hospital FROM authenticated;

REVOKE INSERT, UPDATE, DELETE, TRUNCATE ON public.mart_equidade_aps_municipio FROM anon;
REVOKE INSERT, UPDATE, DELETE, TRUNCATE ON public.mart_equidade_aps_municipio FROM authenticated;

REVOKE INSERT, UPDATE, DELETE, TRUNCATE ON public.mart_fluxo_intermunicipal FROM anon;
REVOKE INSERT, UPDATE, DELETE, TRUNCATE ON public.mart_fluxo_intermunicipal FROM authenticated;

REVOKE INSERT, UPDATE, DELETE, TRUNCATE ON public.mart_forecast_demanda_hospital FROM anon;
REVOKE INSERT, UPDATE, DELETE, TRUNCATE ON public.mart_forecast_demanda_hospital FROM authenticated;

REVOKE INSERT, UPDATE, DELETE, TRUNCATE ON public.mart_hsmr_hospital FROM anon;
REVOKE INSERT, UPDATE, DELETE, TRUNCATE ON public.mart_hsmr_hospital FROM authenticated;

REVOKE INSERT, UPDATE, DELETE, TRUNCATE ON public.mart_icsap_municipio FROM anon;
REVOKE INSERT, UPDATE, DELETE, TRUNCATE ON public.mart_icsap_municipio FROM authenticated;

REVOKE INSERT, UPDATE, DELETE, TRUNCATE ON public.mart_internacoes_agravo FROM anon;
REVOKE INSERT, UPDATE, DELETE, TRUNCATE ON public.mart_internacoes_agravo FROM authenticated;

REVOKE INSERT, UPDATE, DELETE, TRUNCATE ON public.mart_internacoes_hospital FROM anon;
REVOKE INSERT, UPDATE, DELETE, TRUNCATE ON public.mart_internacoes_hospital FROM authenticated;

REVOKE INSERT, UPDATE, DELETE, TRUNCATE ON public.mart_leitos_icsap_municipio FROM anon;
REVOKE INSERT, UPDATE, DELETE, TRUNCATE ON public.mart_leitos_icsap_municipio FROM authenticated;

REVOKE INSERT, UPDATE, DELETE, TRUNCATE ON public.mart_leitos_municipio FROM anon;
REVOKE INSERT, UPDATE, DELETE, TRUNCATE ON public.mart_leitos_municipio FROM authenticated;

REVOKE INSERT, UPDATE, DELETE, TRUNCATE ON public.mart_los_hospital FROM anon;
REVOKE INSERT, UPDATE, DELETE, TRUNCATE ON public.mart_los_hospital FROM authenticated;

REVOKE INSERT, UPDATE, DELETE, TRUNCATE ON public.mart_qualidade_registro_municipio FROM anon;
REVOKE INSERT, UPDATE, DELETE, TRUNCATE ON public.mart_qualidade_registro_municipio FROM authenticated;

REVOKE INSERT, UPDATE, DELETE, TRUNCATE ON public.mart_saude_suplementar_municipio FROM anon;
REVOKE INSERT, UPDATE, DELETE, TRUNCATE ON public.mart_saude_suplementar_municipio FROM authenticated;

REVOKE INSERT, UPDATE, DELETE, TRUNCATE ON public.mart_vazio_assistencial_municipio FROM anon;
REVOKE INSERT, UPDATE, DELETE, TRUNCATE ON public.mart_vazio_assistencial_municipio FROM authenticated;
-- Impede que tabelas novas nasçam com o mesmo buraco.
ALTER DEFAULT PRIVILEGES IN SCHEMA public
  REVOKE INSERT, UPDATE, DELETE, TRUNCATE ON TABLES FROM anon;
ALTER DEFAULT PRIVILEGES IN SCHEMA public
  REVOKE INSERT, UPDATE, DELETE, TRUNCATE ON TABLES FROM authenticated;
