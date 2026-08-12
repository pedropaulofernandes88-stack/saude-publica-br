-- =============================================================================
-- V025 — mart_icsap_pares passa a rodar com a permissão de quem consulta
-- =============================================================================
-- O linter do Supabase aponta a view como SECURITY DEFINER (nível ERROR). Uma
-- view sem `security_invoker` roda com os direitos de quem a CRIOU — aqui,
-- `postgres`, o superusuário. Na prática ela vira um túnel: qualquer coisa que
-- o dono enxerga passa a ser legível por quem tiver SELECT na view, ignorando
-- o RLS e os grants do papel que está consultando.
--
-- Hoje isso NÃO expõe nada. A view lê três tabelas — dim_cluster_municipio,
-- mart_icsap_municipio e mart_internacoes_agravo — e `anon` já tem SELECT nas
-- três, com policy `USING (true)`. O problema é de estrutura, não de vazamento
-- atual: enquanto a view for definer, uma futura tabela restrita que entrar no
-- FROM fica pública sem que ninguém precise conceder nada. A permissão deixa de
-- ser decidida no grant e passa a ser decidida por descuido.
--
-- `security_invoker = true` devolve a decisão para o lugar certo: a view passa a
-- ver exatamente o que o papel que consulta pode ver. Como as três tabelas já
-- são legíveis por anon, o site não muda de comportamento — conferido antes de
-- escrever esta migration.
--
-- Reversão: ALTER VIEW public.mart_icsap_pares SET (security_invoker = false);
-- =============================================================================

ALTER VIEW public.mart_icsap_pares SET (security_invoker = true);

COMMENT ON VIEW public.mart_icsap_pares IS
  'Pares de municipios comparaveis para ICSAP. security_invoker=true: le com a permissao de quem consulta, nao com a do dono (ver V025).';
