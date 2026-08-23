-- =============================================================================
-- schema.sql — o esquema REAL do banco, extraído do catálogo
-- =============================================================================
-- GERADO por scripts/gerar_schema.py. Não editar à mão: a próxima execução
-- sobrescreve. Para mudar o esquema, escreva uma migração, aplique-a e regere.
--
-- Este arquivo existe porque migrations/ não reproduz este banco: das 57
-- migrações aplicadas em produção, 47 foram feitas ad-hoc e não têm arquivo no
-- repositório. As migrações registram a INTENÇÃO de cada mudança; este arquivo
-- registra o ESTADO. Um não substitui o outro.
--
-- Cobre o schema `public`. Não cobre: GRANTs de papel (auditados à parte),
-- os schemas `alertas`/`storage`/`auth`, e dados — o conteúdo vem dos Parquet
-- descritos em data/publicacoes/.
--
-- Extraído em: 2026-08-23 09:57 UTC
-- Objetos: 126
-- =============================================================================


-- ── Tabelas, colunas e constraints ──────────────────────────────

create table if not exists public.dim_cid10_capitulo (
    capitulo text not null,
    capitulo_num smallint not null,
    faixa text not null,
    descricao text not null,
    constraint dim_cid10_capitulo_pkey PRIMARY KEY (capitulo)
);

create table if not exists public.dim_cid10_categoria (
    causabas_3 text not null,
    descricao text not null,
    constraint dim_cid10_categoria_pkey PRIMARY KEY (causabas_3)
);

create table if not exists public.dim_cluster_municipio (
    municipio_cod text not null,
    municipio_nome text,
    uf_sigla text not null,
    regiao text,
    cluster smallint not null,
    perfil text not null,
    taxa_padronizada_100k numeric(10,2),
    ivs_score numeric(6,1),
    internacoes_100k numeric(10,1),
    constraint dim_cluster_municipio_pkey PRIMARY KEY (municipio_cod)
);

create table if not exists public.dim_ivs (
    municipio_cod text not null,
    municipio_nome text,
    uf_sigla text,
    regiao text,
    taxa_analfabetismo numeric(6,2),
    pct_sem_agua numeric(6,2),
    ivs_score numeric(5,1),
    ivs_quartil text,
    constraint dim_ivs_pkey PRIMARY KEY (municipio_cod)
);

create table if not exists public.dim_municipio (
    municipio_cod text not null,
    municipio_cod7 text,
    municipio_nome text not null,
    uf_sigla text not null,
    uf_nome text,
    regiao text not null,
    constraint dim_municipio_pkey PRIMARY KEY (municipio_cod),
    constraint dim_municipio_municipio_cod7_key UNIQUE (municipio_cod7)
);

create table if not exists public.dim_pop_faixa (
    municipio_cod text not null,
    faixa_etaria text not null,
    populacao integer not null,
    fonte text,
    constraint dim_pop_faixa_pkey PRIMARY KEY (municipio_cod, faixa_etaria)
);

create table if not exists public.dim_pop_padrao (
    faixa_etaria text not null,
    populacao bigint not null,
    fonte text,
    constraint dim_pop_padrao_pkey PRIMARY KEY (faixa_etaria)
);

create table if not exists public.dim_populacao (
    municipio_cod text not null,
    ano smallint not null,
    populacao integer not null,
    fonte text,
    constraint dim_populacao_pkey PRIMARY KEY (municipio_cod, ano)
);

create table if not exists public.mart_cnes_municipio (
    municipio_cod text not null,
    municipio_nome text,
    uf_sigla text,
    regiao text,
    estabelecimentos_total integer,
    estabelecimentos_hospitalares integer,
    publico integer,
    privado_lucrativo integer,
    sem_fins_lucrativos integer,
    pessoa_fisica integer,
    internacional integer,
    populacao integer,
    estab_por_10k numeric,
    estab_hosp_por_10k numeric,
    pct_publico numeric,
    ano_referencia smallint,
    constraint mart_cnes_municipio_pkey PRIMARY KEY (municipio_cod)
);

create table if not exists public.mart_cobertura_aps_municipio (
    municipio_cod text not null,
    municipio_nome text,
    uf_sigla text,
    regiao text,
    ano smallint not null,
    mes smallint not null,
    mes_competencia date not null,
    populacao integer,
    qt_esf integer,
    qt_eap20 integer,
    qt_eap30 integer,
    qt_esfr integer,
    qt_ecr integer,
    qt_eapp20 integer,
    qt_eapp30 integer,
    capacidade_equipe integer,
    cobertura_pct numeric,
    constraint mart_cobertura_aps_municipio_pkey PRIMARY KEY (municipio_cod, mes_competencia)
);

create table if not exists public.mart_cobertura_icsap_municipio (
    municipio_cod text not null,
    municipio_nome text,
    uf_sigla text,
    regiao text,
    ano smallint not null,
    populacao integer,
    cobertura_pct numeric,
    cobertura_efetiva numeric,
    qt_esf numeric,
    internacoes_total integer,
    internacoes_icsap integer,
    pct_icsap numeric,
    icsap_100k numeric,
    ivs_score numeric,
    constraint mart_cobertura_icsap_municipio_pkey PRIMARY KEY (municipio_cod, ano)
);

create table if not exists public.mart_demanda_mensal_hospital (
    cnes text not null,
    municipio_cod text,
    municipio_nome text,
    uf_sigla text,
    ano_mes text not null,
    internacoes integer not null,
    obitos integer not null,
    valor_total numeric not null,
    constraint mart_demanda_mensal_hospital_pkey PRIMARY KEY (cnes, ano_mes)
);

create table if not exists public.mart_dengue_municipio_ano (
    municipio_cod text not null,
    municipio_nome text,
    uf_sigla text not null,
    regiao text,
    ano_epi smallint not null,
    casos_provaveis integer not null,
    casos_graves integer not null,
    obitos integer not null,
    populacao integer,
    incidencia_100k numeric(10,1),
    letalidade_pct numeric(6,2),
    constraint mart_dengue_municipio_ano_pkey PRIMARY KEY (municipio_cod, ano_epi)
);

create table if not exists public.mart_dengue_semana (
    municipio_cod text not null,
    municipio_nome text,
    uf_sigla text not null,
    regiao text,
    ano_epi smallint not null,
    semana_epi smallint not null,
    casos_provaveis integer not null,
    casos_graves integer not null,
    obitos integer not null,
    constraint mart_dengue_semana_pkey PRIMARY KEY (municipio_cod, ano_epi, semana_epi)
);

create table if not exists public.mart_equidade_aps_municipio (
    municipio_cod text not null,
    municipio_nome text,
    uf_sigla text,
    regiao text,
    ano smallint not null,
    populacao integer,
    porte_quartil text,
    esf_por_10k numeric,
    pct_esf_no_porte numeric,
    pct_icsap numeric,
    icsap_100k numeric,
    pct_icsap_no_porte numeric,
    ivs_score numeric,
    ivs_quartil text,
    atencao boolean,
    constraint mart_equidade_aps_municipio_pkey PRIMARY KEY (municipio_cod, ano)
);

create table if not exists public.mart_excesso_uf_mes (
    uf_sigla text not null,
    ano smallint not null,
    mes smallint not null,
    mes_competencia date not null,
    obitos integer not null,
    esperado numeric(12,1) not null,
    excesso numeric(12,1) not null,
    pct_excesso numeric(8,2),
    constraint mart_excesso_uf_mes_pkey PRIMARY KEY (uf_sigla, mes_competencia)
);

create table if not exists public.mart_fluxo_intermunicipal (
    ano smallint not null,
    municipio_res text not null,
    municipio_res_nome text,
    uf_res text,
    municipio_mov text not null,
    municipio_mov_nome text,
    uf_mov text,
    internacoes integer not null,
    constraint mart_fluxo_intermunicipal_pkey PRIMARY KEY (ano, municipio_res, municipio_mov)
);

create table if not exists public.mart_forecast_demanda_hospital (
    cnes text not null,
    municipio_cod text,
    municipio_nome text,
    uf_sigla text,
    ano_mes_previsto text not null,
    internacoes_previstas numeric not null,
    ic_inferior numeric not null,
    ic_superior numeric not null,
    n_meses_historico integer not null,
    confianca text,
    horizonte_meses smallint,
    faixa_volume text,
    status_validacao text,
    motivo_status text,
    smape_backtest_pct numeric,
    modelo text,
    ultima_competencia text,
    treinado_em date,
    commit_codigo text,
    constraint mart_forecast_demanda_hospital_pkey PRIMARY KEY (cnes, ano_mes_previsto),
    constraint forecast_status_validacao_valido CHECK (((status_validacao IS NULL) OR (status_validacao = ANY (ARRAY['A'::text, 'B'::text, 'C'::text])))),
    constraint mart_forecast_demanda_hospital_confianca_check CHECK ((confianca = ANY (ARRAY['adequada'::text, 'baixa'::text])))
);

create table if not exists public.mart_hsmr_hospital (
    cnes text not null,
    municipio_cod text,
    municipio_nome text,
    uf_sigla text,
    ano smallint not null,
    internacoes integer not null,
    obitos_observados integer not null,
    obitos_esperados numeric not null,
    hsmr numeric,
    estavel boolean not null,
    hsmr_ic95_inf numeric,
    hsmr_ic95_sup numeric,
    significancia text,
    hsmr_pvalor numeric,
    hsmr_q_valor numeric,
    tem_uti boolean,
    leitos_total integer,
    leitos_uti integer,
    estrato text,
    fator_estrato numeric,
    obitos_esperados_estrato numeric,
    hsmr_estrato numeric,
    constraint mart_hsmr_hospital_pkey PRIMARY KEY (cnes, ano)
);

create table if not exists public.mart_icsap_municipio (
    municipio_cod text not null,
    municipio_nome text,
    uf_sigla text not null,
    regiao text,
    ano smallint not null,
    internacoes_total integer not null,
    internacoes_icsap integer not null,
    pct_icsap numeric(6,2),
    populacao integer,
    icsap_100k numeric(10,1),
    aih_continuacao integer,
    aih_continuacao_icsap integer,
    constraint mart_icsap_municipio_pkey PRIMARY KEY (municipio_cod, ano)
);

create table if not exists public.mart_internacoes_agravo (
    municipio_cod text not null,
    municipio_nome text,
    uf_sigla text,
    regiao text,
    ano integer not null,
    agravo text not null,
    agravo_label text,
    grupo text,
    internacoes integer,
    obitos integer,
    dias_permanencia integer,
    valor_total numeric,
    permanencia_media numeric,
    mortalidade_pct numeric,
    custo_medio numeric,
    populacao integer,
    internacoes_100k numeric,
    aih_continuacao integer,
    aih_normal integer,
    dias_permanencia_normal bigint,
    valor_normal numeric,
    constraint mart_internacoes_agravo_pkey PRIMARY KEY (municipio_cod, ano, agravo)
);

create table if not exists public.mart_internacoes_hospital (
    cnes text not null,
    municipio_cod text,
    municipio_nome text,
    uf_sigla text,
    regiao text,
    ano integer not null,
    capitulo_principal text,
    internacoes integer,
    obitos integer,
    dias_permanencia integer,
    valor_total numeric,
    permanencia_media numeric,
    mortalidade_pct numeric,
    custo_medio numeric,
    aih_continuacao integer,
    aih_normal integer,
    dias_permanencia_normal bigint,
    valor_normal numeric,
    constraint mart_internacoes_hospital_pkey PRIMARY KEY (cnes, ano)
);

create table if not exists public.mart_internacoes_municipio (
    municipio_cod text not null,
    municipio_nome text,
    uf_sigla text not null,
    regiao text,
    ano smallint not null,
    capitulo_cid text not null,
    internacoes integer not null,
    obitos integer not null,
    dias_permanencia bigint not null,
    valor_total numeric(16,2) not null,
    permanencia_media numeric(8,2),
    mortalidade_pct numeric(6,2),
    custo_medio numeric(12,2),
    internacoes_100k numeric(10,1),
    populacao integer,
    aih_continuacao integer,
    aih_normal integer,
    dias_permanencia_normal bigint,
    valor_normal numeric,
    constraint mart_internacoes_municipio_pkey PRIMARY KEY (municipio_cod, ano, capitulo_cid)
);

create table if not exists public.mart_leitos_icsap_municipio (
    municipio_cod text not null,
    municipio_nome text,
    uf_sigla text,
    regiao text,
    populacao integer,
    leitos_total integer,
    leitos_sus integer,
    leitos_sus_por_mil numeric,
    sem_leito boolean,
    internacoes_total integer,
    internacoes_por_mil numeric,
    internacoes_icsap integer,
    pct_icsap numeric,
    icsap_100k numeric,
    ivs_score numeric,
    ano smallint not null,
    constraint mart_leitos_icsap_municipio_pkey PRIMARY KEY (municipio_cod, ano)
);

create table if not exists public.mart_leitos_municipio (
    municipio_cod text not null,
    municipio_nome text,
    uf_sigla text,
    regiao text,
    ano smallint not null,
    leitos_total integer,
    leitos_sus integer,
    leitos_nao_sus integer,
    leitos_cirurgico integer,
    leitos_clinico integer,
    leitos_complementar integer,
    leitos_obstetrico integer,
    leitos_pediatrico integer,
    leitos_outras_especialidades integer,
    leitos_hospital_dia integer,
    leitos_uti integer,
    leitos_uti_sus integer,
    populacao integer,
    leitos_por_mil numeric,
    leitos_sus_por_mil numeric,
    leitos_uti_por_100k numeric,
    pct_leitos_sus numeric,
    constraint mart_leitos_municipio_pkey PRIMARY KEY (municipio_cod, ano)
);

create table if not exists public.mart_los_hospital (
    cnes text not null,
    municipio_cod text,
    municipio_nome text,
    uf_sigla text,
    ano smallint not null,
    cid3 text not null,
    capitulo_cid text,
    internacoes integer not null,
    mediana_hospital_dias numeric,
    mediana_nacional_dias numeric,
    desvio_dias numeric,
    constraint mart_los_hospital_pkey PRIMARY KEY (cnes, ano, cid3)
);

create table if not exists public.mart_mortalidade_causa (
    ano smallint not null,
    uf_sigla text not null,
    causabas_3 text not null,
    capitulo_cid text,
    obitos integer not null,
    constraint mart_mortalidade_causa_pkey PRIMARY KEY (ano, uf_sigla, causabas_3)
);

create table if not exists public.mart_mortalidade_infantil_uf (
    uf_sigla text not null,
    ano smallint not null,
    nascidos integer not null,
    obitos_menor1 integer,
    tmi_por_mil numeric(8,2),
    constraint mart_mortalidade_infantil_uf_pkey PRIMARY KEY (uf_sigla, ano)
);

create table if not exists public.mart_mortalidade_municipio (
    municipio_cod text not null,
    municipio_nome text,
    uf_sigla text not null,
    regiao text,
    ano smallint not null,
    capitulo_cid text not null,
    sexo text not null,
    obitos integer not null,
    obitos_hospital integer,
    obitos_domicilio integer,
    populacao integer,
    taxa_obitos_100k numeric(10,2),
    taxa_padronizada_100k numeric(10,2),
    ic95_inf numeric(10,2),
    ic95_sup numeric(10,2),
    constraint mart_mortalidade_municipio_pkey PRIMARY KEY (municipio_cod, ano, capitulo_cid, sexo)
);

create table if not exists public.mart_mortalidade_uf_mes (
    uf_sigla text not null,
    regiao text,
    ano smallint not null,
    mes smallint not null,
    mes_competencia date not null,
    capitulo_cid text not null,
    sexo text not null,
    faixa_etaria text not null,
    obitos integer not null,
    constraint mart_mortalidade_uf_mes_pkey PRIMARY KEY (uf_sigla, mes_competencia, capitulo_cid, sexo, faixa_etaria)
);

create table if not exists public.mart_natalidade_municipio (
    municipio_cod text not null,
    municipio_nome text,
    uf_sigla text not null,
    regiao text,
    ano smallint not null,
    nascidos integer not null,
    pct_baixo_peso numeric(6,2),
    pct_prematuro numeric(6,2),
    pct_prenatal_7mais numeric(6,2),
    idade_media_mae numeric(5,1),
    constraint mart_natalidade_municipio_pkey PRIMARY KEY (municipio_cod, ano)
);

create table if not exists public.mart_qualidade_registro_municipio (
    municipio_cod text not null,
    municipio_nome text,
    uf_sigla text,
    regiao text,
    periodo text,
    obitos_total bigint,
    obitos_mal_definidas bigint,
    pct_mal_definidas numeric,
    classificacao text,
    populacao integer,
    constraint mart_qualidade_registro_municipio_pkey PRIMARY KEY (municipio_cod)
);

create table if not exists public.mart_saude_suplementar_municipio (
    municipio_cod text not null,
    municipio_nome text,
    uf_sigla text,
    regiao text,
    ano smallint not null,
    populacao integer,
    vinculos_medico_hospitalar integer,
    vinculos_plano_por_100_hab numeric,
    razao_implausivel boolean not null default false,
    constraint mart_saude_suplementar_municipio_pkey PRIMARY KEY (municipio_cod, ano)
);

create table if not exists public.mart_siops_municipio (
    municipio_cod text not null,
    municipio_nome text,
    uf_sigla text,
    regiao text,
    ano smallint not null,
    populacao_siops numeric,
    gasto_proprio_saude_hab numeric,
    despesa_total_saude numeric,
    transf_sus_hab numeric,
    pct_receita_propria_saude numeric,
    abaixo_do_minimo_ec29 boolean,
    constraint mart_siops_municipio_pkey PRIMARY KEY (municipio_cod, ano)
);

create table if not exists public.mart_vazio_assistencial_municipio (
    municipio_cod text not null,
    municipio_nome text,
    uf_sigla text,
    regiao text,
    populacao integer,
    porte_quartil text,
    leitos_total integer,
    leitos_sus integer,
    leitos_sus_por_mil numeric,
    sem_leito boolean,
    obitos integer,
    obitos_hospital integer,
    obitos_domicilio integer,
    pct_obito_domicilio numeric,
    pct_obito_hospital numeric,
    taxa_obitos_100k numeric,
    taxa_padronizada_100k numeric,
    ivs_score numeric,
    ano smallint not null,
    constraint mart_vazio_assistencial_municipio_pkey PRIMARY KEY (municipio_cod, ano)
);

create table if not exists public.meta_dataset (
    chave text not null,
    valor text not null,
    constraint meta_dataset_pkey PRIMARY KEY (chave)
);


-- ── Índices (os de PK e UNIQUE saem junto com a constraint) ─────

CREATE INDEX idx_cluster_perfil ON public.dim_cluster_municipio USING btree (cluster);

CREATE INDEX idx_cluster_uf ON public.dim_cluster_municipio USING btree (uf_sigla);

CREATE INDEX idx_dengueano_uf ON public.mart_dengue_municipio_ano USING btree (uf_sigla, ano_epi);

CREATE INDEX idx_dengue_uf_ano ON public.mart_dengue_semana USING btree (uf_sigla, ano_epi);

CREATE INDEX idx_fluxo_mov ON public.mart_fluxo_intermunicipal USING btree (municipio_mov, ano);

CREATE INDEX idx_fluxo_res ON public.mart_fluxo_intermunicipal USING btree (municipio_res, ano);

CREATE INDEX idx_forecast_status ON public.mart_forecast_demanda_hospital USING btree (status_validacao, uf_sigla);

CREATE INDEX idx_icsap_uf ON public.mart_icsap_municipio USING btree (uf_sigla, ano);

CREATE INDEX idx_intern_cap ON public.mart_internacoes_municipio USING btree (capitulo_cid, ano);

CREATE INDEX idx_intern_uf_ano ON public.mart_internacoes_municipio USING btree (uf_sigla, ano);

CREATE INDEX idx_mc_causa ON public.mart_mortalidade_causa USING btree (causabas_3);

CREATE INDEX idx_mm_cap ON public.mart_mortalidade_municipio USING btree (capitulo_cid, ano);

CREATE INDEX idx_mm_uf_ano ON public.mart_mortalidade_municipio USING btree (uf_sigla, ano);

CREATE INDEX idx_mum_comp ON public.mart_mortalidade_uf_mes USING btree (mes_competencia);

CREATE INDEX idx_nat_uf_ano ON public.mart_natalidade_municipio USING btree (uf_sigla, ano);

CREATE INDEX idx_siops_ano_gasto ON public.mart_siops_municipio USING btree (ano, gasto_proprio_saude_hab);

CREATE INDEX idx_siops_uf_ano ON public.mart_siops_municipio USING btree (uf_sigla, ano);


-- ── Row Level Security ──────────────────────────────────────────

alter table public.dim_cid10_capitulo enable row level security;

alter table public.dim_cid10_categoria enable row level security;

alter table public.dim_cluster_municipio enable row level security;

alter table public.dim_ivs enable row level security;

alter table public.dim_municipio enable row level security;

alter table public.dim_pop_faixa enable row level security;

alter table public.dim_pop_padrao enable row level security;

alter table public.dim_populacao enable row level security;

alter table public.mart_cnes_municipio enable row level security;

alter table public.mart_cobertura_aps_municipio enable row level security;

alter table public.mart_cobertura_icsap_municipio enable row level security;

alter table public.mart_demanda_mensal_hospital enable row level security;

alter table public.mart_dengue_municipio_ano enable row level security;

alter table public.mart_dengue_semana enable row level security;

alter table public.mart_equidade_aps_municipio enable row level security;

alter table public.mart_excesso_uf_mes enable row level security;

alter table public.mart_fluxo_intermunicipal enable row level security;

alter table public.mart_forecast_demanda_hospital enable row level security;

alter table public.mart_hsmr_hospital enable row level security;

alter table public.mart_icsap_municipio enable row level security;

alter table public.mart_internacoes_agravo enable row level security;

alter table public.mart_internacoes_hospital enable row level security;

alter table public.mart_internacoes_municipio enable row level security;

alter table public.mart_leitos_icsap_municipio enable row level security;

alter table public.mart_leitos_municipio enable row level security;

alter table public.mart_los_hospital enable row level security;

alter table public.mart_mortalidade_causa enable row level security;

alter table public.mart_mortalidade_infantil_uf enable row level security;

alter table public.mart_mortalidade_municipio enable row level security;

alter table public.mart_mortalidade_uf_mes enable row level security;

alter table public.mart_natalidade_municipio enable row level security;

alter table public.mart_qualidade_registro_municipio enable row level security;

alter table public.mart_saude_suplementar_municipio enable row level security;

alter table public.mart_siops_municipio enable row level security;

alter table public.mart_vazio_assistencial_municipio enable row level security;

alter table public.meta_dataset enable row level security;


-- ── Policies ────────────────────────────────────────────────────

create policy leitura_publica on public.dim_cid10_capitulo for select to anon, authenticated using (true);

create policy leitura_publica on public.dim_cid10_categoria for select to anon, authenticated using (true);

create policy leitura_publica on public.dim_cluster_municipio for select to anon, authenticated using (true);

create policy leitura_publica on public.dim_ivs for select to anon, authenticated using (true);

create policy leitura_publica on public.dim_municipio for select to anon, authenticated using (true);

create policy leitura_publica on public.dim_pop_faixa for select to anon, authenticated using (true);

create policy leitura_publica on public.dim_pop_padrao for select to anon, authenticated using (true);

create policy leitura_publica on public.dim_populacao for select to anon, authenticated using (true);

create policy leitura_publica on public.mart_cnes_municipio for select to public using (true);

create policy leitura_publica on public.mart_cobertura_aps_municipio for select to public using (true);

create policy leitura_publica on public.mart_cobertura_icsap_municipio for select to public using (true);

create policy leitura_publica on public.mart_demanda_mensal_hospital for select to public using (true);

create policy leitura_publica on public.mart_dengue_municipio_ano for select to anon, authenticated using (true);

create policy leitura_publica on public.mart_dengue_semana for select to anon, authenticated using (true);

create policy leitura_publica on public.mart_equidade_aps_municipio for select to public using (true);

create policy leitura_publica on public.mart_excesso_uf_mes for select to anon, authenticated using (true);

create policy leitura_publica on public.mart_fluxo_intermunicipal for select to anon, authenticated using (true);

create policy leitura_publica on public.mart_forecast_demanda_hospital for select to public using (true);

create policy leitura_publica on public.mart_hsmr_hospital for select to public using (true);

create policy leitura_publica on public.mart_icsap_municipio for select to anon, authenticated using (true);

create policy leitura_publica on public.mart_internacoes_agravo for select to anon, authenticated using (true);

create policy leitura_publica on public.mart_internacoes_hospital for select to anon, authenticated using (true);

create policy leitura_publica on public.mart_internacoes_municipio for select to anon, authenticated using (true);

create policy leitura_publica on public.mart_leitos_icsap_municipio for select to public using (true);

create policy leitura_publica on public.mart_leitos_municipio for select to public using (true);

create policy leitura_publica on public.mart_los_hospital for select to public using (true);

create policy leitura_publica on public.mart_mortalidade_causa for select to anon, authenticated using (true);

create policy leitura_publica on public.mart_mortalidade_infantil_uf for select to anon, authenticated using (true);

create policy leitura_publica on public.mart_mortalidade_municipio for select to anon, authenticated using (true);

create policy leitura_publica on public.mart_mortalidade_uf_mes for select to anon, authenticated using (true);

create policy leitura_publica on public.mart_natalidade_municipio for select to anon, authenticated using (true);

create policy leitura_publica on public.mart_qualidade_registro_municipio for select to anon, authenticated using (true);

create policy leitura_publica on public.mart_saude_suplementar_municipio for select to public using (true);

create policy siops_leitura_publica on public.mart_siops_municipio for select to public using (true);

create policy leitura_publica on public.mart_vazio_assistencial_municipio for select to public using (true);

create policy leitura_publica on public.meta_dataset for select to anon, authenticated using (true);


-- ── Views ───────────────────────────────────────────────────────

create or replace view public.mart_icsap_pares as  WITH parametros AS (
         SELECT (sum(mart_internacoes_agravo.valor_normal) / (NULLIF(sum(mart_internacoes_agravo.aih_normal), 0))::numeric) AS custo_medio,
            (sum(mart_internacoes_agravo.dias_permanencia_normal) / (NULLIF(sum(mart_internacoes_agravo.aih_normal), 0))::numeric) AS permanencia_media
           FROM mart_internacoes_agravo
          WHERE (mart_internacoes_agravo.agravo = ANY (ARRAY['asma'::text, 'dpoc'::text, 'pneumonia'::text, 'diabetes'::text, 'icc'::text, 'avc'::text]))
        ), base AS (
         SELECT i.municipio_cod,
            i.municipio_nome,
            i.uf_sigla,
            i.regiao,
            i.ano,
            i.internacoes_total,
            i.internacoes_icsap,
            i.pct_icsap,
            i.icsap_100k,
            i.populacao,
            c.cluster,
            c.perfil,
                CASE
                    WHEN (c.cluster IS NOT NULL) THEN ('k'::text || c.cluster)
                    ELSE ((i.regiao || '_'::text) ||
                    CASE
                        WHEN (i.populacao < 10000) THEN 'ate10k'::text
                        WHEN (i.populacao < 50000) THEN '10a50k'::text
                        WHEN (i.populacao < 100000) THEN '50a100k'::text
                        WHEN (i.populacao < 500000) THEN '100a500k'::text
                        ELSE '500k+'::text
                    END)
                END AS grupo_id,
                CASE
                    WHEN (c.cluster IS NOT NULL) THEN 'arquétipo de saúde (k-means)'::text
                    ELSE 'faixa populacional × região'::text
                END AS criterio_pares
           FROM (mart_icsap_municipio i
             LEFT JOIN dim_cluster_municipio c ON ((c.municipio_cod = i.municipio_cod)))
        ), medianas AS (
         SELECT base.grupo_id,
            percentile_cont((0.5)::double precision) WITHIN GROUP (ORDER BY ((base.pct_icsap)::double precision)) AS mediana_pct_icsap,
            percentile_cont((0.25)::double precision) WITHIN GROUP (ORDER BY ((base.pct_icsap)::double precision)) AS p25_pct_icsap,
            count(*) AS n_pares
           FROM base
          WHERE ((base.internacoes_total >= 100) AND (base.pct_icsap IS NOT NULL))
          GROUP BY base.grupo_id
        ), calc AS (
         SELECT b.municipio_cod,
            b.municipio_nome,
            b.uf_sigla,
            b.regiao,
            b.ano,
            b.internacoes_total,
            b.internacoes_icsap,
            b.pct_icsap,
            b.icsap_100k,
            b.populacao,
            b.cluster,
            b.perfil,
            b.grupo_id,
            b.criterio_pares,
            m.n_pares,
            m.mediana_pct_icsap,
            m.p25_pct_icsap,
            p.custo_medio,
            p.permanencia_media,
            GREATEST((0)::double precision, (((b.internacoes_total)::double precision * ((b.pct_icsap)::double precision - m.mediana_pct_icsap)) / (100.0)::double precision)) AS excedente,
            GREATEST((0)::double precision, (((b.internacoes_total)::double precision * ((b.pct_icsap)::double precision - m.p25_pct_icsap)) / (100.0)::double precision)) AS excedente_p25
           FROM ((base b
             JOIN medianas m ON ((m.grupo_id = b.grupo_id)))
             CROSS JOIN parametros p)
          WHERE (b.pct_icsap IS NOT NULL)
        )
 SELECT municipio_cod,
    municipio_nome,
    uf_sigla,
    regiao,
    ano,
    populacao,
    internacoes_total,
    internacoes_icsap,
    pct_icsap,
    icsap_100k,
    perfil AS arquetipo,
    criterio_pares,
    n_pares,
    round((mediana_pct_icsap)::numeric, 2) AS mediana_pares_pct,
    round((p25_pct_icsap)::numeric, 2) AS p25_pares_pct,
    round((((pct_icsap)::double precision - mediana_pct_icsap))::numeric, 2) AS diferenca_pp,
    round((excedente)::numeric, 0) AS internacoes_acima_pares,
    round((excedente_p25)::numeric, 0) AS internacoes_acima_p25,
    round(((excedente * (custo_medio)::double precision))::numeric, 0) AS custo_associado_reais,
    round(((excedente * (permanencia_media)::double precision))::numeric, 0) AS leitos_dia_associados,
    round((((excedente * (permanencia_media)::double precision) / (365.0)::double precision))::numeric, 1) AS leitos_equivalentes_ano,
    round(custo_medio, 2) AS custo_medio_icsap_ref,
    round(permanencia_media, 2) AS permanencia_media_icsap_ref,
    (internacoes_total < 100) AS amostra_pequena
   FROM calc;
