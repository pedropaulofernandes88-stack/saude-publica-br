-- =============================================================================
-- V047 — `mart_correlacao_causas` e `mart_dengue_semana` voltam ao Postgres
-- =============================================================================
--
-- Reverte a V041 e a V044b. As duas saíram pelo MESMO motivo, escrito nelas com
-- todas as letras: o teto do banco mordeu e "quem sai é a tabela, não o limite",
-- porque subir o teto "trocaria uma restrição real — o free tier — por um número
-- mais confortável, e o número não paga a conta".
--
-- Em 2026-09-20 o projeto passou ao plano Pro. A cota de banco foi de 500 MB
-- para 8 GB. A restrição real que justificou os dois drops deixou de existir, e
-- as duas voltam por decisão explícita.
--
-- O QUE MUDOU, E O QUE NÃO MUDOU — a distinção importa para quem ler depois
--
-- Mudou o custo. NÃO mudou a evidência de uso, e seria desonesto deixar esta
-- migração sugerir que mudou:
--
--   * `mart_correlacao_causas` acumulou ZERO buscas no índice enquanto esteve
--     servida. Nenhuma tela do site a lê e nenhuma ferramenta do MCP a expõe. O
--     consumidor conhecido dela lê o Parquet, e continua lendo — recarregá-la
--     aqui não muda uma linha daquele script. Some-se o formato: matriz de
--     correlação existe para ser carregada inteira, e o PostgREST devolve 1.000
--     linhas por requisição, o que são 125 requisições para reproduzir um
--     arquivo de 1,6 MB.
--   * `mart_dengue_semana` saiu depois de se MEDIR que 3 dos 4 consumidores
--     pediam grão de UF, não municipal. `mart_dengue_uf_semana` continua sendo a
--     rota certa para esses três, e continua no ar.
--
-- Então o que esta migração entrega é OPÇÃO, não demanda atendida: quem quiser a
-- série semanal municipal de dengue pela API passa a tê-la sem baixar 848 mil
-- linhas de Parquet, e a matriz de correlação volta a ser consultável por
-- filtro. Se daqui a alguns meses o índice das duas seguir com zero buscas, a
-- conclusão honesta será que o espaço nunca foi o que as impedia de servir.
--
-- CUSTO MEDIDO: ~116 MB (95 da dengue municipal — 64 de heap, 26 da PK e 5,9 do
-- índice de UF —, 21 da correlação). O teto de `diagnostico_banco.py` sobe junto,
-- e é o caso que a doutrina daquele arquivo autoriza: uso corrente correto que
-- mudou por decisão explícita, com o crescimento conferido antes.
--
-- REVERSÃO: `drop table` nas duas e devolvê-las a `NAO_SERVIDAS` em
--           `scripts/_publicacao.py`. O Parquet das duas segue publicado com
--           SHA-256 em qualquer cenário — aqui o que entra e sai é a API, nunca
--           o registro.
-- =============================================================================

-- -----------------------------------------------------------------------------
-- 1. Matriz de correlação entre causas (DDL da V038, alargado pela V039)
-- -----------------------------------------------------------------------------
create table if not exists public.mart_correlacao_causas (
    grupo          smallint not null,
    cid_a          text     not null,
    cid_b          text     not null,
    r              numeric  not null,
    p              numeric  not null,
    significativo  boolean  not null default false,
    constraint mart_correlacao_causas_pkey primary key (grupo, cid_a, cid_b)
);

comment on table public.mart_correlacao_causas is
    'Correlação de Spearman entre pares de causas (CID-10, 3 caracteres) sobre '
    'as taxas municipais. Uma linha por par POR RECORTE: `grupo` distingue o '
    'nacional dos três grupos de municípios. `significativo` já embute a '
    'correção de múltiplas comparações — não refazer o corte por `p` sozinho.';

create index if not exists idx_corr_causas_sig
    on public.mart_correlacao_causas (grupo, significativo)
    where significativo;

alter table public.mart_correlacao_causas enable row level security;

create policy leitura_publica on public.mart_correlacao_causas
    for select to anon, authenticated using (true);

-- -----------------------------------------------------------------------------
-- 2. Dengue semanal MUNICIPAL
-- -----------------------------------------------------------------------------
-- `municipio_nome` e `regiao` são NULLABLE de propósito: 2.557 das 847.927
-- linhas não têm correspondência na dimensão municipal. São códigos de
-- município que o SINAN traz e que o IBGE não reconhece (município extinto,
-- código de fora do país, ignorado). Preencher com texto vazio apagaria a
-- distinção entre "sem nome" e "nome em branco"; descartá-las mudaria os
-- totais. Ficam nulas, e quem agrupa por nome tem de decidir o que fazer.
create table if not exists public.mart_dengue_semana (
    municipio_cod    text     not null,
    ano_epi          smallint not null,
    semana_epi       smallint not null,
    casos_provaveis  integer  not null,
    casos_graves     integer  not null,
    obitos           integer  not null,
    municipio_nome   text,
    uf_sigla         text     not null,
    regiao           text,
    constraint mart_dengue_semana_pkey primary key (municipio_cod, ano_epi, semana_epi)
);

comment on table public.mart_dengue_semana is
    'Dengue (SINAN) por município de residência × ano × semana epidemiológica '
    '(data dos primeiros sintomas). Casos prováveis = notificações exceto '
    'descartadas. Para leitura por UF prefira mart_dengue_uf_semana, que é o '
    'grão que 3 dos 4 consumidores medidos pediam e responde em uma requisição.';

-- A PK começa por `municipio_cod`, então consulta por UF não a aproveita. Este
-- índice é o mesmo que existia antes da V044b, e custava 5,9 MB.
create index if not exists idx_dengue_semana_uf
    on public.mart_dengue_semana (uf_sigla, ano_epi, semana_epi);

alter table public.mart_dengue_semana enable row level security;

create policy leitura_publica on public.mart_dengue_semana
    for select to anon, authenticated using (true);
