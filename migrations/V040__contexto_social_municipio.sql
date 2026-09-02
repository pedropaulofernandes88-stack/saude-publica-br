-- =============================================================================
-- V040 — o outro espaço de atributos: contexto social e sistema de saúde
-- =============================================================================
--
-- O desenho de análise oferecia duas matérias-primas para a parte não
-- supervisionada: mortalidade **ou contexto social**. A V037 fez a primeira.
-- Esta faz a segunda, e sustenta o cruzamento entre elas.
--
-- Quinze variáveis municipais, de sete tabelas já publicadas: analfabetismo,
-- domicílios sem água e IVS; cobertura da atenção primária; leitos SUS por mil;
-- gasto próprio, transferência SUS e receita própria em saúde; vínculos de
-- plano por 100 habitantes; estabelecimentos e hospitais por 10 mil; baixo
-- peso, prematuridade e pré-natal com sete ou mais consultas; log da população.
--
-- Quatro eixos somam 61,5% da variância. O primeiro, com 29,5%, é o gradiente
-- de vulnerabilidade: positivo em IVS, analfabetismo e cobertura de APS,
-- negativo em plano de saúde, estabelecimentos per capita e gasto próprio.
--
-- O CRUZAMENTO
--
-- O maior |r| entre os seis eixos de perfil de causas e os quatro sociais é
-- **0,46** — entre o PC1 de mortalidade e o eixo de vulnerabilidade. As duas
-- leituras se sobrepõem em cerca de 21% da variância e divergem no resto: nem
-- o perfil de mortalidade é redundante com o IVS, nem independente dele.
--
-- O TESTE QUE ESTA TABELA EXISTE PARA PERMITIR
--
-- A V037 concluiu que quase um terço do eixo principal do perfil de causas é
-- imprecisão de codificação, e deixou declarada uma interpretação alternativa:
-- imprecisão pode ser falta de recurso diagnóstico, não artefato de registro.
-- As colunas de infraestrutura estão aqui para que esse teste seja refeito por
-- quem quiser. O resultado medido:
--
--     analfabetismo                +0,56      leitos SUS por mil    -0,09
--     IVS                          +0,48      hospitais por 10 mil  -0,02
--     estabelecimentos por 10 mil  -0,42      log da população      +0,01
--     vínculos de plano            -0,42
--
-- A imprecisão acompanha vulnerabilidade social e densidade de atenção
-- AMBULATORIAL, e é indiferente a leito hospitalar e a porte. Isso desfavorece
-- a leitura de "falta de equipamento hospitalar". Não separa artefato de acesso
-- real — essa separação exige informação que a base não contém, e continua
-- declarada como limitação.
--
-- Reversão: DROP TABLE public.mart_contexto_social_municipio;
-- =============================================================================

create table if not exists public.mart_contexto_social_municipio (
    municipio_cod               text    not null,
    spc1 numeric, spc2 numeric, spc3 numeric, spc4 numeric,
    taxa_analfabetismo          numeric,
    ivs_score                   numeric,
    estab_por_10k               numeric,
    vinculos_plano_por_100_hab  numeric,
    gasto_proprio_saude_hab     numeric,
    pct_prenatal_7mais          numeric,
    cobertura_pct               numeric,
    leitos_sus_por_mil          numeric,
    hosp_por_10k                numeric,
    log_pop                     numeric,
    constraint mart_contexto_social_municipio_pkey PRIMARY KEY (municipio_cod)
);

alter table public.mart_contexto_social_municipio enable row level security;
create policy leitura_publica on public.mart_contexto_social_municipio
    for select to anon, authenticated using (true);

COMMENT ON TABLE public.mart_contexto_social_municipio IS
  'Eixos de contexto social e de sistema de saude por municipio (15 variaveis: IVS, APS, leitos, SIOPS, suplementar, CNES, natalidade, porte). Os quatro eixos somam 61,5% da variancia. O maior |r| com os eixos de perfil de causas e 0,46 — as duas leituras sao parcialmente redundantes (V040).';
COMMENT ON COLUMN public.mart_contexto_social_municipio.spc1 IS
  'Eixo de vulnerabilidade: positivo em IVS, analfabetismo e cobertura de APS; negativo em plano de saude, estabelecimentos per capita e gasto proprio. Correlaciona -0,46 com o PC1 de mortalidade.';
