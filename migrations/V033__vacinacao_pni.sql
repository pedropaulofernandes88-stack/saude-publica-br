-- =============================================================================
-- V033 — Vacinação (PNI/RNDS): três tabelas publicadas
-- =============================================================================
--
-- Décima fonte do projeto. Doses aplicadas do Programa Nacional de Imunizações,
-- alimentadas pela Rede Nacional de Dados em Saúde. 638 milhões de doses de
-- janeiro de 2023 a agosto de 2026, processadas em streaming a partir dos
-- arquivos mensais do portal de dados abertos do SUS.
--
-- POR QUE TRÊS TABELAS, E NÃO UMA DE COBERTURA MUNICIPAL
--
-- A tabela que todo mundo espera — cobertura vacinal por município — foi
-- construída, testada e REPROVADA antes de chegar aqui. O critério foi fixado
-- antes de olhar o resultado: correlação abaixo de 0,50 entre 2023 e 2024
-- significaria ruído. Deu 0,591 de Pearson e 0,529 de Spearman, e o detalhe por
-- porte mostrou o motivo: a cobertura mediana cai de 102,7% nos municípios com
-- 50 a 100 nascidos para 86,2% nos com mais de 5 mil. Ruído não tem direção;
-- isso é viés sistemático de denominador.
--
-- A hipótese óbvia foi testada e refutada: suspeitávamos de descasamento
-- geográfico entre o município da dose e o do nascimento. O agregado de fluxo
-- mostra que a mediana dos municípios aplica 15,8% das doses dos seus
-- residentes fora do território — mas a correlação disso com o excesso de
-- cobertura é +0,002. Não explica nada, porque o numerador já é por residência.
--
-- Por isso o recorte municipal aqui é CONTAGEM DE DOSES, não taxa. Contagem
-- não depende de denominador e não herda nenhum desses problemas.
--
-- BCG e hepatite B ao nascer também ficam fora da cobertura, mesmo por UF:
-- aplicadas na maternidade, chegam a 127,8% (CE) e 121,0% (AL) em 2024,
-- enquanto as cinco de atenção básica ficam contidas em 104,2%.
--
-- Ver docs/vacinacao-pni-metodologia.md.
--
-- Reversão: DROP TABLE public.mart_vacinacao_municipio,
--           public.mart_vacinacao_uf_mes, public.mart_cobertura_vacinal_uf;
-- =============================================================================

-- Contagem de doses por município e ano. Chave inclui o imunobiológico porque
-- é o que dá utilidade: "quantas doses de pentavalente meu município aplicou".
create table if not exists public.mart_vacinacao_municipio (
    municipio_cod text not null,
    municipio_nome text,
    uf_sigla text not null,
    regiao text,
    ano smallint not null,
    imunobiologico text not null,
    doses integer not null,
    constraint mart_vacinacao_municipio_pkey
        PRIMARY KEY (municipio_cod, ano, imunobiologico)
);

-- Onde mora a atualidade: vai até o mês corrente, com cerca de um mês de
-- defasagem. É a série mais recente do projeto — mais fresca que a vigilância
-- de arboviroses e três anos à frente da mortalidade consolidada.
create table if not exists public.mart_vacinacao_uf_mes (
    competencia text not null,          -- AAAA-MM
    uf_sigla text not null,
    imunobiologico text not null,
    doses integer not null,
    constraint mart_vacinacao_uf_mes_pkey
        PRIMARY KEY (competencia, uf_sigla, imunobiologico)
);

-- Cobertura só por UF, só nos anos com nascidos vivos DEFINITIVOS (SINASC), e
-- só para os cinco indicadores da atenção básica. `nascidos` viaja junto do
-- percentual de propósito: quem consome consegue refazer a conta e ver de qual
-- denominador ela saiu.
create table if not exists public.mart_cobertura_vacinal_uf (
    uf_sigla text not null,
    ano smallint not null,
    indicador text not null,
    doses integer not null,
    nascidos integer not null,
    cobertura_pct numeric(5,1),
    constraint mart_cobertura_vacinal_uf_pkey PRIMARY KEY (uf_sigla, ano, indicador)
);

CREATE INDEX IF NOT EXISTS idx_vac_mun_uf_ano
    ON public.mart_vacinacao_municipio USING btree (uf_sigla, ano);
CREATE INDEX IF NOT EXISTS idx_vac_mun_imuno
    ON public.mart_vacinacao_municipio USING btree (imunobiologico, ano);
CREATE INDEX IF NOT EXISTS idx_vac_ufmes_comp
    ON public.mart_vacinacao_uf_mes USING btree (competencia);

alter table public.mart_vacinacao_municipio enable row level security;
alter table public.mart_vacinacao_uf_mes enable row level security;
alter table public.mart_cobertura_vacinal_uf enable row level security;

create policy leitura_publica on public.mart_vacinacao_municipio
    for select to anon, authenticated using (true);
create policy leitura_publica on public.mart_vacinacao_uf_mes
    for select to anon, authenticated using (true);
create policy leitura_publica on public.mart_cobertura_vacinal_uf
    for select to anon, authenticated using (true);

COMMENT ON TABLE public.mart_vacinacao_municipio IS
  'Doses aplicadas do PNI (alimentado pela RNDS) por municipio, ano e imunobiologico. CONTAGEM, nao taxa: cobertura municipal foi testada e reprovada por vies sistematico de denominador (V033).';
COMMENT ON TABLE public.mart_vacinacao_uf_mes IS
  'Doses aplicadas do PNI por competencia mensal, UF e imunobiologico. Fonte mais atual do projeto, com cerca de um mes de defasagem.';
COMMENT ON TABLE public.mart_cobertura_vacinal_uf IS
  'Cobertura vacinal em menores de 1 ano por UF e ano, apenas para cinco indicadores da atencao basica e apenas nos anos com nascidos vivos definitivos. BCG e hepatite B ao nascer excluidas: aplicadas na maternidade, sem denominador adequado.';
