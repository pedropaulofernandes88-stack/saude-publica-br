-- =============================================================================
-- V020 — SIH: separar AIH normal de AIH de continuação (IDENT)
-- =============================================================================
-- O arquivo RD do SIH mistura AIH normal (IDENT=1) com AIH de CONTINUAÇÃO
-- (IDENT=5), emitida quando a internação se prolonga além do período coberto pela
-- AIH anterior. Uma mesma internação longa gera, portanto, várias linhas.
--
-- Contar linhas é a aproximação operacional correta para PRODUÇÃO aprovada — e
-- continua sendo o que `internacoes` mede. Mas distorce qualquer MÉDIA POR
-- EPISÓDIO. Medido em amostra de 808.470 AIHs (SP, MG, BA, PA, RS; 2024):
-- IDENT=5 é 1,26% das linhas e 6,57% dos dias de permanência, concentrado em
-- dois capítulos:
--
--   cap. VI (sistema nervoso)     internações −19,9%  permanência 10,98 → 6,21 d
--   cap. V  (transtornos mentais) internações −23,7%  permanência 14,43 → 11,72 d
--   demais 17 capítulos           |Δ internações| ≤ 0,8%  |Δ permanência| ≤ 2,1%
--
-- REGRA ADOTADA — manter o volume total e publicar os contadores restritos à AIH
-- normal, para que a média por episódio seja calculável sem perder a produção:
--
--   internacoes              todas as AIHs aprovadas (inalterado)
--   aih_continuacao          quantas delas são IDENT=5
--   aih_normal               internacoes − aih_continuacao
--   dias_permanencia         soma de DIAS_PERM, todas as AIHs (inalterado)
--   dias_permanencia_normal  soma de DIAS_PERM, só AIH normal
--   valor_total              soma de VAL_TOT, todas as AIHs (inalterado)
--   valor_normal             soma de VAL_TOT, só AIH normal
--
-- `permanencia_media` e `custo_medio` passam a usar a base normal. Nenhuma coluna
-- existente muda de nome ou de definição — o que muda é o valor de duas médias,
-- e só de forma perceptível nos capítulos V e VI.
--
-- mart_hsmr_hospital e mart_los_hospital não ganham colunas: passam a ser
-- calculados apenas sobre AIH normal, porque HSMR e mediana de permanência são
-- métricas por episódio. mart_demanda_mensal_hospital e mart_fluxo_intermunicipal
-- seguem contando todas as AIHs (produção).
--
-- Fundamentação: R. F. Saldanha, "Sistemas de Informação em Saúde no Brasil",
-- cap. SIH — "estadias prolongadas podem exigir regras de continuidade para
-- evitar fracionamento artificial". https://rfsaldanha.github.io/sis/sih.html
--
-- Depende de: mart_internacoes_municipio, mart_internacoes_agravo,
--             mart_internacoes_hospital, mart_icsap_municipio
-- =============================================================================

ALTER TABLE public.mart_internacoes_municipio
  ADD COLUMN IF NOT EXISTS aih_continuacao          INTEGER,
  ADD COLUMN IF NOT EXISTS aih_normal               INTEGER,
  ADD COLUMN IF NOT EXISTS dias_permanencia_normal  BIGINT,
  ADD COLUMN IF NOT EXISTS valor_normal             NUMERIC;

ALTER TABLE public.mart_internacoes_agravo
  ADD COLUMN IF NOT EXISTS aih_continuacao          INTEGER,
  ADD COLUMN IF NOT EXISTS aih_normal               INTEGER,
  ADD COLUMN IF NOT EXISTS dias_permanencia_normal  BIGINT,
  ADD COLUMN IF NOT EXISTS valor_normal             NUMERIC;

ALTER TABLE public.mart_internacoes_hospital
  ADD COLUMN IF NOT EXISTS aih_continuacao          INTEGER,
  ADD COLUMN IF NOT EXISTS aih_normal               INTEGER,
  ADD COLUMN IF NOT EXISTS dias_permanencia_normal  BIGINT,
  ADD COLUMN IF NOT EXISTS valor_normal             NUMERIC;

ALTER TABLE public.mart_icsap_municipio
  ADD COLUMN IF NOT EXISTS aih_continuacao       INTEGER,
  ADD COLUMN IF NOT EXISTS aih_continuacao_icsap INTEGER;

COMMENT ON COLUMN public.mart_internacoes_municipio.aih_continuacao IS
  'AIHs de continuacao (IDENT=5) incluidas em `internacoes`. Uma internacao prolongada emite varias AIHs; use `aih_normal` como denominador de medias por episodio.';

COMMENT ON COLUMN public.mart_internacoes_municipio.aih_normal IS
  'internacoes - aih_continuacao. Denominador de permanencia_media e custo_medio.';

COMMENT ON COLUMN public.mart_internacoes_municipio.dias_permanencia_normal IS
  'Soma de DIAS_PERM restrita a AIH normal (IDENT<>5).';

COMMENT ON COLUMN public.mart_internacoes_municipio.valor_normal IS
  'Soma de VAL_TOT restrita a AIH normal (IDENT<>5).';

COMMENT ON COLUMN public.mart_icsap_municipio.aih_continuacao IS
  'AIHs de continuacao (IDENT=5) dentro de internacoes_total. Efeito no pct_icsap e pequeno (+0,93% relativo na amostra de 2024): so I69 e G40 da lista brasileira geram continuacao em volume.';
