-- V044 — dengue semanal por UF: 1,95% do tamanho, 100% do que se consultava
--
-- MOTIVO
-- ------
-- `mart_dengue_semana` ocupa 95 MB no Postgres (64 heap + 26 do pkey + 5,9 do
-- índice de UF) — a segunda maior tabela do banco, num banco com 10 MB de folga
-- sobre o teto de 750.
--
-- Ao medir QUEM a consulta, apareceu o desenho errado: dos quatro consumidores,
-- TRÊS só usam o grão de UF e agregam no servidor a cada chamada.
--
--   mcp_server canal_endemico_dengue   select ano_epi,semana_epi,casos.sum() where uf_sigla=eq.X
--   site/scripts/build-boletim.mjs     select uf_sigla,ano_epi,semana_epi,...sum()
--   site/scripts/build-static-data.mjs select uf_sigla,ano_epi,semana_epi,...sum()
--
-- Ou seja: 848 mil linhas municipais no banco para servir 16.496 linhas de
-- resposta, reagregadas a cada requisição. O grão municipal continua existindo
-- e continua publicado — como Parquet citável, com SHA-256 —, que é o caminho
-- certo para quem precisa dele.
--
--   847.927 linhas municipais  ->  16.496 por UF × ano × semana  (1,95%)
--
-- FIDELIDADE
-- ----------
-- `semana_epi` vai de 1 a 53 na origem: NÃO existe semana 0. Os três
-- consumidores filtravam `semana_epi=gte.1`, filtro que sempre foi inócuo —
-- então a agregação não precisou decidir nada sobre registro sem semana, e as
-- somas batem linha a linha com o que eles calculavam.
--
-- `uf_sigla` preserva 'ND' (2.557 linhas municipais): município que não casa
-- com a dimensão territorial. Somar 'ND' dentro de uma UF de verdade inventaria
-- casos onde não há; virar zero apagaria notificação que existe.
--
-- O QUE ESTA TABELA NÃO SERVE
-- ---------------------------
-- Ranking municipal, mapa por município e qualquer recorte abaixo da UF. Para
-- isso existe `mart_dengue_municipio_ano` (anual, servida) e o Parquet
-- `mart_dengue_semana` (semanal municipal, publicado e não servido).

create table if not exists public.mart_dengue_uf_semana (
    uf_sigla text not null,
    ano_epi smallint not null,
    semana_epi smallint not null,
    casos_provaveis integer not null,
    casos_graves integer not null,
    obitos integer not null,
    -- Espalhamento: quantos municípios daquela UF notificaram na semana. Não
    -- dava para derivar somando linhas municipais depois que elas saem do
    -- banco, então é calculado na agregação e viaja junto.
    municipios_com_casos smallint not null,
    constraint mart_dengue_uf_semana_pkey primary key (uf_sigla, ano_epi, semana_epi)
);

comment on table public.mart_dengue_uf_semana is
    'Dengue (SINAN) agregada por UF de residência × ano × semana epidemiológica '
    '(data dos primeiros sintomas). Casos prováveis = notificações exceto '
    'descartadas. Substitui o uso de mart_dengue_semana pela API: o grão '
    'municipal semanal continua publicado como Parquet, fora do Postgres.';

comment on column public.mart_dengue_uf_semana.municipios_com_casos is
    'Municípios da UF com ao menos um caso provável naquela semana.';

alter table public.mart_dengue_uf_semana enable row level security;

create policy leitura_publica on public.mart_dengue_uf_semana
    for select to anon, authenticated using (true);

-- Sem índice além da PK: a chave já começa por uf_sigla, que é o filtro de
-- todas as consultas conhecidas, e a tabela inteira cabe em poucas páginas.
