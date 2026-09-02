-- =============================================================================
-- V038 — correlação entre causas nas séries mensais
-- =============================================================================
--
-- Terceira tabela de `scripts/analise_perfil_mortalidade.py`, separada da V037
-- porque tem grão diferente: a linha aqui é um PAR de CIDs, não um município.
--
-- Responde à segunda pergunta do desenho de análise — "quais CIDs estão
-- correlacionados?" — sobre as séries mensais nacionais 2015–2024, 120 pontos,
-- retirados tendência linear e efeito de mês civil.
--
-- POR QUE A DESAZONALIZAÇÃO NÃO É DETALHE
--
-- Na série bruta, 23,3% dos 41.041 pares passam de |r| = 0,5. Depois de tirar
-- tendência e mês civil, 10,8%. A maior parte da "associação entre causas" que
-- uma análise ingênua encontraria é simplesmente inverno: causas respiratórias,
-- circulatórias e infecciosas sobem juntas em julho porque é julho.
--
-- O CONTROLE POSITIVO PASSOU
--
-- O par de maior |r| de toda a matriz é **A90 x A91 = +0,97** — dengue e dengue
-- hemorrágica. É o único par do qual se pode afirmar de antemão que TEM de
-- correlacionar, e ele está no topo. Aparecem em seguida C34xC50 e C34xC25
-- (cânceres), J18xJ44 e J44xJ43 (respiratórias), G30xI69 (Alzheimer e sequela
-- cerebrovascular), e as correlações NEGATIVAS de B34 com I21 e N39, que são a
-- substituição de causa durante a pandemia.
--
-- A DEFASAGEM FOI TESTADA E REPROVADA — ESTE É UM ACHADO NEGATIVO PUBLICADO
--
-- O desenho original previa correlação cruzada longitudinal, procurando qual
-- causa antecede qual. Foi feito, numa janela de -6 a +6 meses, e não se
-- sustenta. O histograma do lag em que |r| é máximo se concentra em zero e nas
-- BORDAS: 4.413 pares empilhados em -6 e +6, contra uma média de 1.287 por lag
-- intermediário. Pico na borda da janela é assinatura de busca sobreajustada —
-- a busca escolhe o extremo porque é onde a sobreposição das séries é menor e
-- a correlação amostral, mais volátil.
--
-- Os pares que a defasagem "revelava" confirmam: câncer de cólon precedendo
-- câncer de ânus em cinco meses, câncer de rim precedendo inalação de conteúdo
-- gástrico em seis. Não são hipóteses, são ruído.
--
-- Por isso a coluna `r` guarda o lag ZERO e só ele, e o comentário da coluna
-- diz por quê. Publicar a versão defasada seria distribuir indicador
-- antecedente inventado.
--
-- Reversão: DROP TABLE public.mart_correlacao_causas;
-- =============================================================================

create table if not exists public.mart_correlacao_causas (
    cid_a          text    not null,
    cid_b          text    not null,
    r              numeric not null,
    p              numeric not null,
    significativo  boolean not null default false,
    constraint mart_correlacao_causas_pkey PRIMARY KEY (cid_a, cid_b)
);

CREATE INDEX IF NOT EXISTS idx_corr_causas_sig
    ON public.mart_correlacao_causas (significativo) WHERE significativo;

alter table public.mart_correlacao_causas enable row level security;
create policy leitura_publica on public.mart_correlacao_causas
    for select to anon, authenticated using (true);

COMMENT ON TABLE public.mart_correlacao_causas IS
  'Correlacao contemporanea entre pares de CID nas series mensais nacionais 2015-2024, sem tendencia e sem efeito de mes civil, com marca de FDR 1%. Controle positivo: A90 x A91 (dengue) e o par de maior |r| da matriz, +0,97 (V038).';
COMMENT ON COLUMN public.mart_correlacao_causas.r IS
  'Correlacao no lag ZERO. A versao defasada foi testada e NAO se sustenta: o pico de |r| se concentra nas bordas da janela de -6 a +6 meses, assinatura de busca sobreajustada, e os pares revelados sao clinicamente implausiveis.';
