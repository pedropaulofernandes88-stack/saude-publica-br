-- =============================================================================
-- V019 — ANS: a unidade é o VÍNCULO, não a pessoa (renomeia colunas do mart)
-- =============================================================================
-- O SIB/ANS registra VÍNCULOS (beneficiário × produto × operadora), não pessoas
-- únicas, e localiza cada registro pelo ENDEREÇO DO CONTRATO, não pela residência
-- efetiva. Consequências:
--
--   * uma pessoa com dois produtos conta duas vezes;
--   * um contrato coletivo empresarial pode alocar vínculos ao município da sede
--     da empresa, não ao município onde o beneficiário mora.
--
-- Logo, a razão vínculos/população NÃO é uma proporção de pessoas cobertas e pode
-- legitimamente ultrapassar 100. E ultrapassa: Belém/AL (4.226 hab.) registrou
-- 115,9 vínculos por 100 hab. em 2021 — 1 caso em 22.284 município-ano.
--
-- O nome antigo (`pct_saude_suplementar`) afirmava uma proporção que o dado não
-- sustenta. Esta migração corrige o rótulo e adiciona a flag de confiabilidade,
-- no mesmo padrão de mart_qualidade_registro_municipio.
--
-- ISTO NÃO CORRIGE VIÉS — corrige LEITURA. Os testes que usam esta coluna são de
-- posto (Spearman); excluir o caso implausível e os 33 municípios com <20 mil hab.
-- e >40 vínculos/100 hab. move ρ de +0,054 para +0,061 no quartil de menor porte
-- e deixa o quartil superior inalterado em −0,286. Ver
-- scripts/analise_saude_suplementar_icsap.py (seção 6).
--
-- Fundamentação: R. F. Saldanha, "Sistemas de Informação em Saúde no Brasil",
-- capítulo ANS — https://rfsaldanha.github.io/sis/ans.html
--
-- BREAKING CHANGE da API pública: consumidores de
-- mart_saude_suplementar_municipio que filtrem/ordenem por `pct_saude_suplementar`
-- ou `beneficiarios_medico_hospitalar` precisam usar os novos nomes.
--
-- Depende de: mart_saude_suplementar_municipio
-- =============================================================================

ALTER TABLE public.mart_saude_suplementar_municipio
  RENAME COLUMN beneficiarios_medico_hospitalar TO vinculos_medico_hospitalar;

ALTER TABLE public.mart_saude_suplementar_municipio
  RENAME COLUMN pct_saude_suplementar TO vinculos_plano_por_100_hab;

ALTER TABLE public.mart_saude_suplementar_municipio
  ADD COLUMN IF NOT EXISTS razao_implausivel BOOLEAN NOT NULL DEFAULT FALSE;

-- COALESCE porque ha municipio sem populacao no denominador (ex.: Boa Esperanca
-- do Norte/MT, instalado apos a base de estimativas): razao NULL nao e implausivel,
-- e apenas indeterminada.
UPDATE public.mart_saude_suplementar_municipio
   SET razao_implausivel = COALESCE(vinculos_plano_por_100_hab > 100, FALSE);

COMMENT ON COLUMN public.mart_saude_suplementar_municipio.vinculos_medico_hospitalar IS
  'Vínculos ativos a plano médico-hospitalar (ANS/SIB, QT_BENEFICIARIO_ATIVO, competência dez). Vínculo != pessoa: uma pessoa com dois produtos conta duas vezes.';

COMMENT ON COLUMN public.mart_saude_suplementar_municipio.vinculos_plano_por_100_hab IS
  'Vínculos médico-hospitalares por 100 habitantes. NÃO é o percentual da população com plano: o SIB conta vínculos e localiza pelo endereço do contrato, não pela residência. Pode passar de 100.';

COMMENT ON COLUMN public.mart_saude_suplementar_municipio.razao_implausivel IS
  'TRUE quando vinculos_plano_por_100_hab > 100 — o município não suporta leitura como cobertura populacional (provável artefato de endereço de contrato).';
