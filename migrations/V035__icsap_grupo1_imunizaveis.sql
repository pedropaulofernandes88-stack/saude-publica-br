-- =============================================================================
-- V035 — ICSAP: lista corrigida e o grupo 1 (imunopreveníveis) publicado
-- =============================================================================
--
-- Duas mudanças, e a primeira é uma CORREÇÃO DE DADO JÁ PUBLICADO.
--
-- 1. A Lista Brasileira de ICSAP estava incompleta no grupo 1. Faltavam catorze
--    códigos: tuberculose pulmonar e outras (A15, A16, A18), sífilis (A51–A53),
--    malária (B50–B54) e febre reumática (I00–I02).
--
--    Medido antes de corrigir: a lista antiga capturava apenas **20,7% do grupo
--    1 em São Paulo e 14,3% no Rio de Janeiro** em 2024, porque tuberculose
--    pulmonar sozinha é cerca de 65% do grupo — e era exatamente ela que
--    faltava. Publicar "internações por doença prevenível por vacina" sem a
--    doença que a BCG previne não seria imprecisão, seria o contrário do nome.
--
--    Efeito no %ICSAP total, por ano: +1,21% / +1,04% / +1,09% / +1,07%
--    (2021–2024). Pequeno, porque o grupo 1 é 1,3% a 1,5% do ICSAP.
--
--    Os três achados publicados foram REFEITOS sobre o dado corrigido, não
--    presumidos — a correção é espacialmente estruturada (tuberculose urbana,
--    malária amazônica), que é justamente o padrão capaz de mover correlação:
--
--      leitos SUS/mil x %ICSAP        +0,32  ->  +0,319
--      idem, parcial (porte, IVS)     +0,34  ->  +0,340
--      sem leito vs com leito        17,7/21,4 -> 17,8/21,5
--      cobertura APS x ICSAP (bruta) +0,004 ->  +0,002
--      idem, parcial                 +0,018 ->  +0,017
--
--    Nenhum se move. O achado nulo do gradiente por vulnerabilidade também
--    segue plano na mediana entre municípios (19,1 / 21,1 / 20,6 / 19,8).
--
-- 2. O grupo 1 passa a ser publicado, como COLUNAS desta tabela e não como
--    tabela nova. O banco tem 71 MB de folga depois da V034 e o indicador
--    pertence ao lado do %ICSAP com que vai ser comparado; criar tabela para
--    22 mil linhas gastaria orçamento sem ganho.
--
-- O que NÃO mudou, e está dito no código: a aproximação por CID-10 de 3
-- caracteres continua, e em alguns pontos é mais larga que a portaria (G00
-- inclui toda meningite bacteriana quando a lista pede só G00.0). Estreitar
-- isso mexeria nos dezenove grupos e é outra decisão. Aqui se corrigiu ausência
-- de código, não granularidade.
--
-- Reversão: ALTER TABLE public.mart_icsap_municipio
--             DROP COLUMN internacoes_g1, DROP COLUMN g1_100k;
--           (e reverter ICSAP_G1/ICSAP3 em scripts/pipeline_sih_fluxo.py, mais
--            reprocessar — os checkpoints _v3 têm a contagem corrigida)
-- =============================================================================

ALTER TABLE public.mart_icsap_municipio
    ADD COLUMN IF NOT EXISTS internacoes_g1 integer,
    ADD COLUMN IF NOT EXISTS g1_100k numeric(10,1);

COMMENT ON COLUMN public.mart_icsap_municipio.internacoes_g1 IS
  'Internacoes do grupo 1 da Lista Brasileira de ICSAP: doencas preveniveis por imunizacao e condicoes sensiveis (tuberculoses, tetano, difteria, coqueluche, sifilis, febre amarela, sarampo, rubeola, hepatite B, parotidite, malaria, ascaridiase, meningite, febre reumatica). Subconjunto de internacoes_icsap.';
COMMENT ON COLUMN public.mart_icsap_municipio.g1_100k IS
  'Internacoes do grupo 1 por 100 mil habitantes. E o lado populacional do impacto vacinal, cruzavel com as doses aplicadas do PNI.';
