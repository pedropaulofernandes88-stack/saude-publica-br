-- =============================================================================
-- V039 — a correlação entre causas passa a ter recorte por grupo
-- =============================================================================
--
-- A V038 criou `mart_correlacao_causas` com uma linha por par de CID, calculada
-- sobre a série mensal NACIONAL. A pergunta do desenho, porém, era outra: "em
-- cada GRUPO de municípios, quais CIDs estão correlacionados?". A tabela
-- nacional não a responde.
--
-- A chave primária passa a incluir `grupo`: -1 para o recorte nacional, e
-- 0, 1, 2 para os grupos de `mart_perfil_mortalidade_municipio`. São 164.164
-- linhas — 41.041 pares × 4 recortes.
--
-- O RESULTADO É O MOTIVO DA MIGRAÇÃO
--
-- Pares significativos (FDR 1%) em cada recorte:
--
--     grupo 0    771 municípios    2.632 pares    índice de inespecificidade 0,180
--     grupo 1  1.202 municípios    7.937 pares    índice 0,244
--     grupo 2  1.457 municípios    8.636 pares    índice 0,231
--
-- Onde a codificação é mais precisa, as causas se movem de forma MAIS
-- independente — um terço dos pares correlacionados do grupo mais impreciso.
-- Isso é coerente com o achado da V037 e o reforça por outro caminho: boa parte
-- da "associação entre causas" que uma análise nacional encontraria é
-- co-variação da decisão de codificar, não co-ocorrência biológica.
--
-- As diferenças par a par entre grupos, por teste z de Fisher com FDR 1%, são
-- 203 pares entre os grupos 0 e 2, 156 entre 0 e 1, e apenas 44 entre 1 e 2 —
-- ou seja, o grupo 0 é o que destoa. As maiores diferenças envolvem justamente
-- códigos imprecisos: E14 (diabetes NE) com I10, I49 e F17, todas muito mais
-- correlacionadas no grupo 2 que no 0. E I63 x I67 inverte de sinal: -0,77 no
-- grupo 0 contra +0,14 no grupo 2, o padrão de substituição que se espera
-- quando dois códigos disputam a mesma morte.
--
-- Reversão: recriar pela V038 e reexecutar analise_perfil_mortalidade.py.
-- =============================================================================

DROP TABLE IF EXISTS public.mart_correlacao_causas;

create table if not exists public.mart_correlacao_causas (
    -- -1 = nacional; 0,1,2 = grupos de mart_perfil_mortalidade_municipio
    grupo          smallint not null,
    cid_a          text     not null,
    cid_b          text     not null,
    r              numeric  not null,
    p              numeric  not null,
    significativo  boolean  not null default false,
    constraint mart_correlacao_causas_pkey PRIMARY KEY (grupo, cid_a, cid_b)
);

CREATE INDEX IF NOT EXISTS idx_corr_causas_sig
    ON public.mart_correlacao_causas (grupo, significativo) WHERE significativo;

alter table public.mart_correlacao_causas enable row level security;
create policy leitura_publica on public.mart_correlacao_causas
    for select to anon, authenticated using (true);

COMMENT ON TABLE public.mart_correlacao_causas IS
  'Correlacao contemporanea entre pares de CID nas series mensais 2015-2024, sem tendencia e sem efeito de mes civil, com marca de FDR 1%. Uma linha por par POR RECORTE. Controle positivo: A90 x A91 (dengue), o par de maior |r| da matriz (V039).';
COMMENT ON COLUMN public.mart_correlacao_causas.grupo IS
  'Recorte de municipios: -1 = nacional; 0,1,2 = os grupos de mart_perfil_mortalidade_municipio. O numero de pares significativos difere MUITO entre grupos (2.632, 7.937 e 8.636), e acompanha o indice de inespecificidade de codificacao de cada grupo.';
COMMENT ON COLUMN public.mart_correlacao_causas.r IS
  'Correlacao no lag ZERO. A versao defasada foi testada e NAO se sustenta: o pico de |r| se concentra nas bordas da janela de -6 a +6 meses, assinatura de busca sobreajustada.';
