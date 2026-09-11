-- V045 — SISAGUA: vigilância da qualidade da água, servida pela API
--
-- MOTIVO
-- ------
-- O mart foi publicado como Parquet em 2026-09-11 e entrou como NÃO servido,
-- pela regra que o projeto já aplicava à oncologia e à sífilis: cabe no banco,
-- mas servir antes de existir consumidor gasta o teto por antecipação. A
-- decisão de servir foi tomada depois, explicitamente.
--
-- CUSTO, MEDIDO ANTES DE CRIAR
-- -----------------------------
-- Banco em 650 MB de 750. O mart tem 397.380 linhas × ~115 B/linha de heap
-- (soma dos campos + cabeçalho de tupla), mais ~15 MB de índice da PK:
--
--     heap estimado ......... 43 MB
--     índice da PK .......... 15 MB
--     total ................. ~59 MB   ->  banco em ~709 MB
--
-- A estimativa é conservadora: `escherichia_coli` e `coliformes_totais` são
-- NULL em 86% das linhas (só fazem sentido nas linhas do parâmetro
-- correspondente), e NULL custa um bit no bitmap, não 8 bytes.
--
-- RECARGA USA --truncar, NÃO upsert. O pipeline reescreve o mart inteiro a cada
-- execução, e upsert deixaria uma tupla morta por linha reescrita — 43 MB de
-- inchaço transitório que levaria o banco a ~752 MB, acima do teto. Foi
-- exatamente assim que a dengue semanal estourou o limite em 2026-09-06.
--
-- POR QUE AS CONTAGENS SÃO double precision, E NÃO integer
-- ---------------------------------------------------------
-- Porque a fonte emite fração onde deveria haver contagem. Medido: 356 das
-- 397.380 linhas (0,090%) têm `amostras_analisadas` fracionário — 236 em pH,
-- 97 em turbidez; ex.: LAURO DE FREITAS 2025, pH, 32,32 "amostras analisadas".
-- Contagem de amostras não tem meio. É ruído da fonte, não do pipeline.
--
-- Declarar `integer` obrigaria a arredondar, e aí a tabela servida passaria a
-- divergir em silêncio do Parquet publicado com SHA-256 — o arquivo diria
-- 32,32 e a API diria 32. Entre um tipo mais largo e duas versões do mesmo
-- número, o tipo mais largo. `double precision` preserva o valor como ele foi
-- publicado, e quem consome vê a fração e pode julgá-la.
--
-- O QUE ESTA TABELA NÃO É
-- ------------------------
-- NÃO é potabilidade. É volume e regularidade de ANÁLISE. Município ausente do
-- mart não tem água comprovada: tem falta de prova — e `mart_sisagua_cobertura`
-- é o que distingue "não analisou" de "não foi coletado". As duas andam juntas
-- de propósito; servir uma sem a outra deixaria quem consulta sem como ler a
-- ausência.

create table if not exists public.mart_sisagua_municipio (
    municipio_cod text not null,
    municipio_nome text,
    uf_sigla text,
    regiao text,
    ano smallint not null,
    parametro text not null,
    -- Soma do campo "Número de amostras analisadas" da fonte, no ano.
    amostras_analisadas double precision,
    -- Amostras com PRESENÇA. NULL fora das linhas do parâmetro correspondente:
    -- ausência de medida, não zero medido.
    escherichia_coli double precision,
    coliformes_totais double precision,
    -- Regularidade: em quantos dos 12 meses previstos houve análise. É o
    -- coração do indicador — uma campanha única de 300 amostras num mês soma
    -- mais que 12 meses de 10, e só esta coluna distingue as duas.
    meses_com_analise smallint not null,
    -- SAA, SAC ou ambas. Sistema de abastecimento e solução alternativa
    -- coletiva têm pontos de monitoramento distintos na origem.
    formas_de_abastecimento text,
    constraint mart_sisagua_municipio_pkey
        primary key (municipio_cod, ano, parametro)
);

comment on table public.mart_sisagua_municipio is
    'SISAGUA (controle mensal de parâmetros básicos) por município de '
    'referência × ano × parâmetro. VOLUME E REGULARIDADE DE ANÁLISE, não '
    'potabilidade: ausência de município significa que ele não analisou ou não '
    'foi coletado — ver mart_sisagua_cobertura. 2014–2026, 10 parâmetros.';

comment on column public.mart_sisagua_municipio.meses_com_analise is
    'Meses do ano com ao menos uma amostra analisada (0 a 12). O SISAGUA prevê '
    'controle MENSAL: valor baixo é lacuna de vigilância, não pouco dado.';

comment on column public.mart_sisagua_municipio.amostras_analisadas is
    'double precision porque a fonte emite fração em 0,09% das linhas. O valor '
    'é preservado como publicado no Parquet, sem arredondar.';

alter table public.mart_sisagua_municipio enable row level security;

create policy leitura_publica on public.mart_sisagua_municipio
    for select to anon, authenticated using (true);

-- Recorte por UF e ano é a consulta óbvia de um painel territorial, e a PK
-- começa por município — não serve para isso. Índice pequeno (~10 MB) sobre
-- uma tabela que vai ser consultada por mapa.
create index if not exists idx_sisagua_uf_ano
    on public.mart_sisagua_municipio (uf_sigla, ano);


-- COBERTURA — obrigatória junto, não acessória
-- --------------------------------------------
-- Uma linha para CADA município do país, coletado ou não. 336 municípios foram
-- coletados e não têm nenhuma linha no mart: a fonte respondeu 200 com zero
-- registros, o que é fato sobre o município (não reportou análise nenhuma entre
-- 2014 e 2026), e não falha de coleta. Sem esta tabela, quem consulta a API lê
-- as duas situações como a mesma ausência — e a leitura fácil é a otimista.

create table if not exists public.mart_sisagua_cobertura (
    municipio_cod text not null,
    uf_sigla text,
    coletado boolean not null,
    -- NULL quando não coletado: "não sei", que é diferente de "zero registros".
    registros_brutos bigint,
    linhas_no_mart integer,
    constraint mart_sisagua_cobertura_pkey primary key (municipio_cod)
);

comment on table public.mart_sisagua_cobertura is
    'Cobertura da coleta do SISAGUA: uma linha por município do país. '
    'coletado=false significa que não conseguimos coletar; coletado=true com '
    'linhas_no_mart=0 significa que o município não reportou análise alguma. '
    'As duas produzem a mesma ausência em mart_sisagua_municipio.';

alter table public.mart_sisagua_cobertura enable row level security;

create policy leitura_publica on public.mart_sisagua_cobertura
    for select to anon, authenticated using (true);
