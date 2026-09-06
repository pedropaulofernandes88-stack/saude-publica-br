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
-- Cobre os schemas `public` e `alertas` — apenas ESTRUTURA, nenhuma linha de
-- dado. Não cobre: GRANTs de papel (auditados à parte), `storage` e `auth`
-- (geridos pelo Supabase), e o conteúdo, que vem dos Parquet em data/publicacoes/.
--
-- Extraído em: 2026-09-06 10:53 UTC
-- Objetos: 237
-- =============================================================================


-- ── Schemas ─────────────────────────────────────────────────────

create schema if not exists alertas;


-- ── Tabelas, colunas e constraints ──────────────────────────────

create table if not exists alertas.assinantes (
    id uuid not null default gen_random_uuid(),
    email text not null,
    uf text,
    token_confirmacao uuid not null default gen_random_uuid(),
    token_cancelamento uuid not null default gen_random_uuid(),
    confirmado_em timestamp with time zone,
    criado_em timestamp with time zone not null default now(),
    ultimo_envio_em timestamp with time zone,
    envios integer not null default 0,
    ultima_edicao_enviada text,
    constraint assinantes_pkey PRIMARY KEY (id),
    constraint assinantes_email_uf_unico UNIQUE (email, uf),
    constraint assinantes_email_valido CHECK ((email ~* '^[^@\s]+@[^@\s]+\.[^@\s]+$'::text)),
    constraint assinantes_uf_valida CHECK (((uf IS NULL) OR (uf = ANY (ARRAY['AC'::text, 'AL'::text, 'AP'::text, 'AM'::text, 'BA'::text, 'CE'::text, 'DF'::text, 'ES'::text, 'GO'::text, 'MA'::text, 'MT'::text, 'MS'::text, 'MG'::text, 'PA'::text, 'PB'::text, 'PR'::text, 'PE'::text, 'PI'::text, 'RJ'::text, 'RN'::text, 'RS'::text, 'RO'::text, 'RR'::text, 'SC'::text, 'SP'::text, 'SE'::text, 'TO'::text]))))
);

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

create table if not exists public.dim_cid10_informativo (
    causabas_3 text not null,
    capitulo_cid text not null,
    obitos_total integer not null,
    municipios_com_registro integer not null,
    ano_min smallint not null,
    ano_max smallint not null,
    prevalencia_municipal numeric not null,
    is_mal_definida boolean not null default false,
    is_covid boolean not null default false,
    informativo boolean not null default false,
    descricao text,
    constraint dim_cid10_informativo_pkey PRIMARY KEY (causabas_3)
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
    estrato_cod text,
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

create table if not exists public.mart_anomalia_causa_municipio (
    municipio_cod text not null,
    ano smallint not null,
    causabas_3 text not null,
    municipio_nome text not null,
    uf_sigla text not null,
    obitos integer not null,
    esperado numeric not null,
    esperado_relativo numeric not null,
    razao numeric not null,
    p_proprio numeric not null,
    p_relativo numeric not null,
    excesso_proprio boolean not null default false,
    excesso_relativo boolean not null default false,
    constraint mart_anomalia_causa_municipio_pkey PRIMARY KEY (municipio_cod, ano, causabas_3)
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

create table if not exists public.mart_cobertura_vacinal_uf (
    uf_sigla text not null,
    ano smallint not null,
    indicador text not null,
    doses integer not null,
    nascidos integer not null,
    cobertura_pct numeric(5,1),
    constraint mart_cobertura_vacinal_uf_pkey PRIMARY KEY (uf_sigla, ano, indicador)
);

create table if not exists public.mart_contexto_social_municipio (
    municipio_cod text not null,
    spc1 numeric,
    spc2 numeric,
    spc3 numeric,
    spc4 numeric,
    taxa_analfabetismo numeric,
    ivs_score numeric,
    estab_por_10k numeric,
    vinculos_plano_por_100_hab numeric,
    gasto_proprio_saude_hab numeric,
    pct_prenatal_7mais numeric,
    cobertura_pct numeric,
    leitos_sus_por_mil numeric,
    hosp_por_10k numeric,
    log_pop numeric,
    constraint mart_contexto_social_municipio_pkey PRIMARY KEY (municipio_cod)
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
    constraint mart_forecast_demanda_hospital_confianca_check CHECK ((confianca = ANY (ARRAY['adequada'::text, 'baixa'::text]))),
    constraint forecast_status_validacao_valido CHECK (((status_validacao IS NULL) OR (status_validacao = ANY (ARRAY['A'::text, 'B'::text, 'C'::text]))))
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
    internacoes_g1 integer,
    g1_100k numeric(10,1),
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

create table if not exists public.mart_perfil_mortalidade_municipio (
    municipio_cod text not null,
    municipio_nome text not null,
    uf_sigla text not null,
    regiao text not null,
    obitos_periodo integer not null,
    grupo smallint not null,
    indice_inespecificidade numeric not null,
    pc1 numeric,
    pc2 numeric,
    pc3 numeric,
    pc4 numeric,
    pc5 numeric,
    pc6 numeric,
    constraint mart_perfil_mortalidade_municipio_pkey PRIMARY KEY (municipio_cod)
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

create table if not exists public.mart_vacinacao_uf_mes (
    competencia text not null,
    uf_sigla text not null,
    imunobiologico text not null,
    doses integer not null,
    constraint mart_vacinacao_uf_mes_pkey PRIMARY KEY (competencia, uf_sigla, imunobiologico)
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

CREATE INDEX assinantes_confirmados_uf_idx ON alertas.assinantes USING btree (uf) WHERE (confirmado_em IS NOT NULL);

CREATE UNIQUE INDEX assinantes_token_canc_idx ON alertas.assinantes USING btree (token_cancelamento);

CREATE UNIQUE INDEX assinantes_token_conf_idx ON alertas.assinantes USING btree (token_confirmacao);

CREATE INDEX dim_cid10_informativo_informativo_idx ON public.dim_cid10_informativo USING btree (informativo) WHERE informativo;

CREATE INDEX idx_cluster_perfil ON public.dim_cluster_municipio USING btree (cluster);

CREATE INDEX idx_cluster_uf ON public.dim_cluster_municipio USING btree (uf_sigla);

CREATE INDEX idx_anomalia_causa_ano ON public.mart_anomalia_causa_municipio USING btree (causabas_3, ano);

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

CREATE INDEX idx_perfil_mort_grupo ON public.mart_perfil_mortalidade_municipio USING btree (grupo);

CREATE INDEX idx_siops_ano_gasto ON public.mart_siops_municipio USING btree (ano, gasto_proprio_saude_hab);

CREATE INDEX idx_siops_uf_ano ON public.mart_siops_municipio USING btree (uf_sigla, ano);

CREATE INDEX idx_vac_ufmes_comp ON public.mart_vacinacao_uf_mes USING btree (competencia);


-- ── Funções ─────────────────────────────────────────────────────

CREATE OR REPLACE FUNCTION alertas.purgar_nao_confirmados()
 RETURNS integer
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'alertas', 'pg_catalog'
AS $function$
declare removidos integer;
begin
  delete from alertas.assinantes
   where confirmado_em is null
     and criado_em < now() - interval '7 days';
  get diagnostics removidos = row_count;
  return removidos;
end;
$function$
;

CREATE OR REPLACE FUNCTION public.alerta_assinar(p_email text, p_uf text DEFAULT NULL::text)
 RETURNS jsonb
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'alertas', 'public', 'pg_catalog'
AS $function$
declare
  v_email text := lower(trim(p_email));
  v_uf    text := nullif(upper(trim(coalesce(p_uf, ''))), '');
  v_rec   alertas.assinantes%rowtype;
begin
  if v_email !~* '^[^@\s]+@[^@\s]+\.[^@\s]+$' then
    return jsonb_build_object('ok', false, 'motivo', 'email_invalido');
  end if;

  select * into v_rec from alertas.assinantes
   where email = v_email and uf is not distinct from v_uf;

  if found then
    if v_rec.confirmado_em is not null then
      -- Já confirmado: nada a fazer. O chamador não deve revelar isso.
      return jsonb_build_object('ok', true, 'ja_confirmado', true);
    end if;
    -- Anti-abuso: no máximo um e-mail de confirmação por hora.
    if v_rec.criado_em > now() - interval '1 hour' then
      return jsonb_build_object('ok', true, 'throttled', true);
    end if;
    update alertas.assinantes
       set token_confirmacao = gen_random_uuid(), criado_em = now()
     where id = v_rec.id
     returning * into v_rec;
  else
    insert into alertas.assinantes (email, uf) values (v_email, v_uf)
    returning * into v_rec;
  end if;

  return jsonb_build_object(
    'ok', true,
    'token_confirmacao', v_rec.token_confirmacao,
    'uf', v_rec.uf
  );
end;
$function$
;

CREATE OR REPLACE FUNCTION public.alerta_cancelar(p_token uuid)
 RETURNS jsonb
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'alertas', 'public', 'pg_catalog'
AS $function$
declare v_uf text;
begin
  delete from alertas.assinantes
   where token_cancelamento = p_token
   returning uf into v_uf;

  if not found then
    return jsonb_build_object('ok', false, 'motivo', 'token_invalido');
  end if;
  return jsonb_build_object('ok', true, 'uf', v_uf);
end;
$function$
;

CREATE OR REPLACE FUNCTION public.alerta_confirmar(p_token uuid)
 RETURNS jsonb
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'alertas', 'public', 'pg_catalog'
AS $function$
declare v_rec alertas.assinantes%rowtype;
begin
  update alertas.assinantes
     set confirmado_em = coalesce(confirmado_em, now())
   where token_confirmacao = p_token
   returning * into v_rec;

  if not found then
    return jsonb_build_object('ok', false, 'motivo', 'token_invalido');
  end if;
  return jsonb_build_object('ok', true, 'uf', v_rec.uf,
                            'token_cancelamento', v_rec.token_cancelamento);
end;
$function$
;

CREATE OR REPLACE FUNCTION public.alerta_desfazer_pendente(p_token uuid)
 RETURNS boolean
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'alertas', 'public', 'pg_catalog'
AS $function$
declare removidos integer;
begin
  delete from alertas.assinantes
   where token_confirmacao = p_token
     and confirmado_em is null;   -- nunca remove quem já confirmou
  get diagnostics removidos = row_count;
  return removidos > 0;
end;
$function$
;

CREATE OR REPLACE FUNCTION public.alerta_destinatarios(p_ufs text[])
 RETURNS TABLE(email text, uf text, token_cancelamento uuid)
 LANGUAGE sql
 SECURITY DEFINER
 SET search_path TO 'alertas', 'public', 'pg_catalog'
AS $function$
  select a.email, a.uf, a.token_cancelamento
    from alertas.assinantes a
   where a.confirmado_em is not null
     and (a.uf is null or a.uf = any(p_ufs))
   order by a.uf nulls first, a.email;
$function$
;

CREATE OR REPLACE FUNCTION public.alerta_destinatarios(p_ufs text[], p_edicao text DEFAULT NULL::text)
 RETURNS TABLE(email text, uf text, token_cancelamento uuid)
 LANGUAGE sql
 SECURITY DEFINER
 SET search_path TO 'alertas', 'public', 'pg_catalog'
AS $function$
  select a.email, a.uf, a.token_cancelamento
    from alertas.assinantes a
   where a.confirmado_em is not null
     and (a.uf is null or a.uf = any(p_ufs))
     and (p_edicao is null or a.ultima_edicao_enviada is distinct from p_edicao)
   order by a.uf nulls first, a.email;
$function$
;

CREATE OR REPLACE FUNCTION public.alerta_marcar_envio(p_emails text[])
 RETURNS integer
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'alertas', 'public', 'pg_catalog'
AS $function$
declare n integer;
begin
  update alertas.assinantes
     set ultimo_envio_em = now(), envios = envios + 1
   where email = any(p_emails) and confirmado_em is not null;
  get diagnostics n = row_count;
  return n;
end;
$function$
;

CREATE OR REPLACE FUNCTION public.alerta_marcar_envio(p_emails text[], p_edicao text DEFAULT NULL::text)
 RETURNS integer
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'alertas', 'public', 'pg_catalog'
AS $function$
declare n integer;
begin
  update alertas.assinantes
     set ultimo_envio_em = now(),
         envios = envios + 1,
         ultima_edicao_enviada = coalesce(p_edicao, ultima_edicao_enviada)
   where email = any(p_emails) and confirmado_em is not null;
  get diagnostics n = row_count;
  return n;
end;
$function$
;

CREATE OR REPLACE FUNCTION public.diagnostico_banco()
 RETURNS TABLE(categoria text, objeto text, linhas bigint, bytes bigint, bytes_por_linha numeric, detalhe text)
 LANGUAGE sql
 STABLE SECURITY DEFINER
 SET search_path TO 'pg_catalog', 'public'
AS $function$
    select 'banco'::text, current_database()::text, null::bigint,
           pg_database_size(current_database()),
           null::numeric,
           'tamanho total do banco'::text
    union all
    select 'tabela', c.relname, s.n_live_tup,
           pg_total_relation_size(c.oid),
           round(pg_relation_size(c.oid)::numeric / nullif(s.n_live_tup, 0), 1),
           'mortas=' || s.n_dead_tup
           || ' heap=' || pg_size_pretty(pg_relation_size(c.oid))
           || ' indices=' || pg_size_pretty(pg_indexes_size(c.oid))
    from pg_class c
    join pg_namespace n on n.oid = c.relnamespace and n.nspname = 'public'
    join pg_stat_user_tables s on s.relid = c.oid
    where c.relkind = 'r'
    union all
    select 'inchaco', c.relname, s.n_dead_tup,
           pg_relation_size(c.oid),
           round(100.0 * s.n_dead_tup / nullif(s.n_live_tup + s.n_dead_tup, 0), 1),
           'pct de tuplas mortas'
    from pg_class c
    join pg_namespace n on n.oid = c.relnamespace and n.nspname = 'public'
    join pg_stat_user_tables s on s.relid = c.oid
    where c.relkind = 'r' and s.n_dead_tup > 1000
    union all
    select 'indice_ocioso', si.relname || '.' || si.indexrelname, si.idx_scan,
           pg_relation_size(si.indexrelid),
           null::numeric,
           'buscas desde ' || (select stats_reset::date::text from pg_stat_database
                               where datname = current_database())
    from pg_stat_user_indexes si
    join pg_index i on i.indexrelid = si.indexrelid
    join pg_class c on c.oid = si.relid
    join pg_namespace n on n.oid = c.relnamespace and n.nspname = 'public'
    where not i.indisprimary and not i.indisunique
      and si.idx_scan < 50 and pg_relation_size(si.indexrelid) > 512 * 1024
    order by 1, 4 desc;
$function$
;

CREATE OR REPLACE FUNCTION public.gerar_schema_ddl()
 RETURNS TABLE(secao smallint, objeto text, ddl text)
 LANGUAGE sql
 STABLE SECURITY DEFINER
 SET search_path TO 'pg_catalog', 'public'
AS $function$
    with alvo as (select unnest(array['public','alertas']) as ns),
    cols as (
        select n.nspname as ns, c.relname as objeto, a.attnum as ord,
               '    ' || quote_ident(a.attname) || ' ' || format_type(a.atttypid, a.atttypmod)
               || case when a.attnotnull then ' not null' else '' end
               || coalesce(' default ' || pg_get_expr(d.adbin, d.adrelid), '') as linha
        from pg_class c
        join pg_namespace n on n.oid = c.relnamespace
        join alvo on alvo.ns = n.nspname
        join pg_attribute a on a.attrelid = c.oid and a.attnum > 0 and not a.attisdropped
        left join pg_attrdef d on d.adrelid = c.oid and d.adnum = a.attnum
        where c.relkind = 'r'
    ),
    cons as (
        select n.nspname as ns, c.relname as objeto,
               9000 + case con.contype when 'p' then 1 when 'u' then 2
                                       when 'c' then 3 else 4 end as ord,
               '    constraint ' || quote_ident(con.conname) || ' '
               || pg_get_constraintdef(con.oid) as linha
        from pg_constraint con
        join pg_class c on c.oid = con.conrelid
        join pg_namespace n on n.oid = c.relnamespace
        join alvo on alvo.ns = n.nspname
        where con.contype in ('p','u','c','f')
    )
    select 0::smallint, ns, 'create schema if not exists ' || quote_ident(ns) || ';'
    from alvo where ns <> 'public'
    union all
    select 1::smallint, ns || '.' || objeto,
           'create table if not exists ' || quote_ident(ns) || '.' || quote_ident(objeto) || E' (\n'
           || string_agg(linha, E',\n' order by ord) || E'\n);'
    from (select * from cols union all select * from cons) t
    group by ns, objeto
    union all
    select 2::smallint, schemaname || '.' || tablename || ':' || indexname, indexdef || ';'
    from pg_indexes
    where schemaname in ('public','alertas')
      and indexname not in (select conname from pg_constraint where contype in ('p','u'))
    union all
    select 3::smallint, n.nspname || '.' || p.proname
           || '(' || pg_get_function_identity_arguments(p.oid) || ')',
           pg_get_functiondef(p.oid) || ';'
    from pg_proc p
    join pg_namespace n on n.oid = p.pronamespace
    join alvo on alvo.ns = n.nspname
    where p.prokind = 'f'
    union all
    select 4::smallint, n.nspname || '.' || c.relname,
           'alter table ' || quote_ident(n.nspname) || '.' || quote_ident(c.relname)
           || ' enable row level security;'
    from pg_class c
    join pg_namespace n on n.oid = c.relnamespace
    join alvo on alvo.ns = n.nspname
    where c.relkind = 'r' and c.relrowsecurity
    union all
    select 5::smallint, n.nspname || '.' || c.relname || ':' || p.polname,
           'create policy ' || quote_ident(p.polname)
           || ' on ' || quote_ident(n.nspname) || '.' || quote_ident(c.relname)
           || ' for ' || case p.polcmd when 'r' then 'select' when 'a' then 'insert'
                                       when 'w' then 'update' when 'd' then 'delete'
                                       else 'all' end
           || ' to ' || coalesce((select string_agg(quote_ident(r.rolname), ', ')
                                  from unnest(p.polroles) pr join pg_roles r on r.oid = pr),
                                 'public')
           || coalesce(' using (' || pg_get_expr(p.polqual, p.polrelid) || ')', '')
           || coalesce(' with check (' || pg_get_expr(p.polwithcheck, p.polrelid) || ')', '')
           || ';'
    from pg_policy p
    join pg_class c on c.oid = p.polrelid
    join pg_namespace n on n.oid = c.relnamespace
    join alvo on alvo.ns = n.nspname
    union all
    select 6::smallint, n.nspname || '.' || c.relname,
           'create or replace view ' || quote_ident(n.nspname) || '.' || quote_ident(c.relname)
           || coalesce(' with (' || array_to_string(c.reloptions, ', ') || ')', '')
           || ' as ' || pg_get_viewdef(c.oid, true)
    from pg_class c
    join pg_namespace n on n.oid = c.relnamespace
    join alvo on alvo.ns = n.nspname
    where c.relkind = 'v'
    union all
    select 7::smallint, n.nspname || '.' || c.relname || coalesce(':' || a.attname, ''),
           'comment on ' || case when d.objsubid = 0 then
                    case c.relkind when 'v' then 'view' else 'table' end
                else 'column' end
           || ' ' || quote_ident(n.nspname) || '.' || quote_ident(c.relname)
           || coalesce('.' || quote_ident(a.attname), '')
           || ' is ' || quote_literal(d.description) || ';'
    from pg_description d
    join pg_class c on c.oid = d.objoid
    join pg_namespace n on n.oid = c.relnamespace
    join alvo on alvo.ns = n.nspname
    left join pg_attribute a on a.attrelid = c.oid and a.attnum = d.objsubid and d.objsubid > 0
    where c.relkind in ('r','v')
    order by 1, 2;
$function$
;


-- ── Row Level Security ──────────────────────────────────────────

alter table alertas.assinantes enable row level security;

alter table public.dim_cid10_capitulo enable row level security;

alter table public.dim_cid10_categoria enable row level security;

alter table public.dim_cid10_informativo enable row level security;

alter table public.dim_cluster_municipio enable row level security;

alter table public.dim_ivs enable row level security;

alter table public.dim_municipio enable row level security;

alter table public.dim_pop_faixa enable row level security;

alter table public.dim_pop_padrao enable row level security;

alter table public.dim_populacao enable row level security;

alter table public.mart_anomalia_causa_municipio enable row level security;

alter table public.mart_cnes_municipio enable row level security;

alter table public.mart_cobertura_aps_municipio enable row level security;

alter table public.mart_cobertura_icsap_municipio enable row level security;

alter table public.mart_cobertura_vacinal_uf enable row level security;

alter table public.mart_contexto_social_municipio enable row level security;

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

alter table public.mart_perfil_mortalidade_municipio enable row level security;

alter table public.mart_qualidade_registro_municipio enable row level security;

alter table public.mart_saude_suplementar_municipio enable row level security;

alter table public.mart_siops_municipio enable row level security;

alter table public.mart_vacinacao_uf_mes enable row level security;

alter table public.mart_vazio_assistencial_municipio enable row level security;

alter table public.meta_dataset enable row level security;


-- ── Policies ────────────────────────────────────────────────────

create policy leitura_publica on public.dim_cid10_capitulo for select to anon, authenticated using (true);

create policy leitura_publica on public.dim_cid10_categoria for select to anon, authenticated using (true);

create policy leitura_publica on public.dim_cid10_informativo for select to anon, authenticated using (true);

create policy leitura_publica on public.dim_cluster_municipio for select to anon, authenticated using (true);

create policy leitura_publica on public.dim_ivs for select to anon, authenticated using (true);

create policy leitura_publica on public.dim_municipio for select to anon, authenticated using (true);

create policy leitura_publica on public.dim_pop_faixa for select to anon, authenticated using (true);

create policy leitura_publica on public.dim_pop_padrao for select to anon, authenticated using (true);

create policy leitura_publica on public.dim_populacao for select to anon, authenticated using (true);

create policy leitura_publica on public.mart_anomalia_causa_municipio for select to anon, authenticated using (true);

create policy leitura_publica on public.mart_cnes_municipio for select to public using (true);

create policy leitura_publica on public.mart_cobertura_aps_municipio for select to public using (true);

create policy leitura_publica on public.mart_cobertura_icsap_municipio for select to public using (true);

create policy leitura_publica on public.mart_cobertura_vacinal_uf for select to anon, authenticated using (true);

create policy leitura_publica on public.mart_contexto_social_municipio for select to anon, authenticated using (true);

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

create policy leitura_publica on public.mart_perfil_mortalidade_municipio for select to anon, authenticated using (true);

create policy leitura_publica on public.mart_qualidade_registro_municipio for select to anon, authenticated using (true);

create policy leitura_publica on public.mart_saude_suplementar_municipio for select to public using (true);

create policy siops_leitura_publica on public.mart_siops_municipio for select to public using (true);

create policy leitura_publica on public.mart_vacinacao_uf_mes for select to anon, authenticated using (true);

create policy leitura_publica on public.mart_vazio_assistencial_municipio for select to public using (true);

create policy leitura_publica on public.meta_dataset for select to anon, authenticated using (true);


-- ── Views ───────────────────────────────────────────────────────

create or replace view public.mart_icsap_pares with (security_invoker=on) as  WITH parametros AS (
         SELECT sum(mart_internacoes_agravo.valor_normal) / NULLIF(sum(mart_internacoes_agravo.aih_normal), 0)::numeric AS custo_medio,
            sum(mart_internacoes_agravo.dias_permanencia_normal) / NULLIF(sum(mart_internacoes_agravo.aih_normal), 0)::numeric AS permanencia_media
           FROM mart_internacoes_agravo
          WHERE mart_internacoes_agravo.agravo = ANY (ARRAY['asma'::text, 'dpoc'::text, 'pneumonia'::text, 'diabetes'::text, 'icc'::text, 'avc'::text])
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
                    WHEN c.estrato_cod IS NOT NULL THEN 'estrato:'::text || c.estrato_cod
                    ELSE (i.regiao || '_'::text) ||
                    CASE
                        WHEN i.populacao < 10000 THEN 'ate10k'::text
                        WHEN i.populacao < 50000 THEN '10a50k'::text
                        WHEN i.populacao < 100000 THEN '50a100k'::text
                        WHEN i.populacao < 500000 THEN '100a500k'::text
                        ELSE '500k+'::text
                    END
                END AS grupo_id,
                CASE
                    WHEN c.estrato_cod IS NOT NULL THEN 'estrato de saúde (tercis fixos)'::text
                    ELSE 'faixa populacional × região'::text
                END AS criterio_pares
           FROM mart_icsap_municipio i
             LEFT JOIN dim_cluster_municipio c ON c.municipio_cod = i.municipio_cod
        ), medianas AS (
         SELECT base.grupo_id,
            base.ano,
            percentile_cont(0.5::double precision) WITHIN GROUP (ORDER BY (base.pct_icsap::double precision)) AS mediana_pct_icsap,
            percentile_cont(0.25::double precision) WITHIN GROUP (ORDER BY (base.pct_icsap::double precision)) AS p25_pct_icsap,
            count(*) AS n_pares
           FROM base
          WHERE base.internacoes_total >= 100 AND base.pct_icsap IS NOT NULL
          GROUP BY base.grupo_id, base.ano
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
            GREATEST(0::double precision, b.internacoes_total::double precision * (b.pct_icsap::double precision - m.mediana_pct_icsap) / 100.0::double precision) AS excedente,
            GREATEST(0::double precision, b.internacoes_total::double precision * (b.pct_icsap::double precision - m.p25_pct_icsap) / 100.0::double precision) AS excedente_p25
           FROM base b
             JOIN medianas m ON m.grupo_id = b.grupo_id AND m.ano = b.ano
             CROSS JOIN parametros p
          WHERE b.pct_icsap IS NOT NULL
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
    round(mediana_pct_icsap::numeric, 2) AS mediana_pares_pct,
    round(p25_pct_icsap::numeric, 2) AS p25_pares_pct,
    round((pct_icsap::double precision - mediana_pct_icsap)::numeric, 2) AS diferenca_pp,
    round(excedente::numeric, 0) AS internacoes_acima_pares,
    round(excedente_p25::numeric, 0) AS internacoes_acima_p25,
    round((excedente * custo_medio::double precision)::numeric, 0) AS custo_associado_reais,
    round((excedente * permanencia_media::double precision)::numeric, 0) AS leitos_dia_associados,
    round((excedente * permanencia_media::double precision / 365.0::double precision)::numeric, 1) AS leitos_equivalentes_ano,
    round(custo_medio, 2) AS custo_medio_icsap_ref,
    round(permanencia_media, 2) AS permanencia_media_icsap_ref,
    internacoes_total < 100 AS amostra_pequena
   FROM calc;


-- ── Comentários ─────────────────────────────────────────────────

comment on table alertas.assinantes is 'Assinantes do alerta epidemiológico. Schema fora do PostgREST: inacessível via API pública. Opt-in duplo; cancelamento apaga a linha.';

comment on table public.dim_cid10_capitulo is 'Capítulos da CID-10 (causa básica de óbito).';

comment on table public.dim_cid10_categoria is 'Descrições das categorias CID-10 (3 caracteres).';

comment on table public.dim_cid10_informativo is 'Vocabulario das 1.571 categorias da CID-10 presentes no SIM 2015-2024, com prevalencia municipal e as marcas is_mal_definida, is_covid e informativo. B34 e COVID-19 neste dado: o SIM brasileiro nunca usou U07 (V036).';

comment on table public.dim_cluster_municipio is 'Arquétipo (estrato) de saúde municipal: tercis de mortalidade padronizada (SIM 2023), vulnerabilidade-proxy (Censo 2022) e internações/100k (SIH 2023), com cortes congelados no repositório. Determinístico: o estrato depende apenas dos valores do próprio município. Substituiu o k-means em 2026-08-29, reprovado em teste de estabilidade.';

comment on column public.dim_cluster_municipio.cluster is 'Id do estrato, 1..27, derivado como (tercil_mortalidade-1)*9 + (tercil_vulnerabilidade-1)*3 + tercil_internacao. NÃO é rótulo de k-means — o nome da coluna é mantido por compatibilidade de contrato.';

comment on column public.dim_cluster_municipio.estrato_cod is 'Código legível do estrato, ex. M2V3I1 = mortalidade no tercil 2, vulnerabilidade no 3, internação no 1.';

comment on column public.dim_cluster_municipio.perfil is 'Rótulo do estrato em palavras. É 1-para-1 com cluster/estrato_cod — o pipeline aborta se deixar de ser.';

comment on table public.dim_ivs is 'Vulnerabilidade social municipal (PROXY, Censo 2022/IBGE): composição z-score de analfabetismo (t/9543) e falta de água encanada (t/6803). NÃO é o IVS oficial do IPEA. Método z-score inspirado no LabSUS (UFT).';

comment on table public.dim_municipio is 'Municípios brasileiros (IBGE). Chave: código IBGE de 6 dígitos, como usado nos sistemas DataSUS.';

comment on table public.dim_pop_faixa is 'População por faixa etária e município — Censo 2022 (IBGE SIDRA t/9514). Estrutura etária usada na padronização.';

comment on table public.dim_pop_padrao is 'População padrão para padronização direta de taxas: Brasil, Censo 2022.';

comment on table public.dim_populacao is 'População residente por município e ano (IBGE — estimativas e Censo 2022).';

comment on table public.mart_anomalia_causa_municipio is 'Celulas municipio x CID x ano (2020-2024) com excesso sobre a historia propria 2015-2019, por binomial negativa com FDR 1%. Controles positivos: COVID em 2020-2021 e dengue apenas em 2024 (V037).';

comment on table public.mart_cobertura_aps_municipio is 'Cobertura potencial da Atencao Primaria (ESF/EAP/eSFR/eCR/EAPP) por municipio e mes, 2021-atual. Fonte: API publica do relatorio de Cobertura da APS (Ministerio da Saude / e-Gestor AB), relatorioaps.saude.gov.br. cobertura_pct pode superar 100% em municipios pequenos (capacidade instalada por equipe supera a populacao local) — comportamento documentado do indicador oficial, nao erro.';

comment on table public.mart_cobertura_icsap_municipio is 'Painel cruzado: cobertura potencial da APS x internacoes por condicoes sensiveis a atencao primaria (ICSAP), por municipio, 2024. ACHADO: a associacao entre os dois e praticamente nula (Spearman +0,004 bruto; +0,018 controlando porte e vulnerabilidade). A cobertura potencial satura acima de 100% em 86% dos municipios e correlaciona-se fortemente com o PORTE (rho -0,54 com populacao) — e, empiricamente, mais um proxy de tamanho do municipio do que uma medida de forca da atencao primaria. Nao usar para ranquear municipios.';

comment on table public.mart_cobertura_vacinal_uf is 'Cobertura vacinal em menores de 1 ano por UF e ano, apenas para cinco indicadores da atencao basica e apenas nos anos com nascidos vivos definitivos. BCG e hepatite B ao nascer excluidas: aplicadas na maternidade, sem denominador adequado.';

comment on table public.mart_contexto_social_municipio is 'Eixos de contexto social e de sistema de saude por municipio (15 variaveis: IVS, APS, leitos, SIOPS, suplementar, CNES, natalidade, porte). Os quatro eixos somam 61,5% da variancia. O maior |r| com os eixos de perfil de causas e 0,46 — as duas leituras sao parcialmente redundantes (V040).';

comment on column public.mart_contexto_social_municipio.spc1 is 'Eixo de vulnerabilidade: positivo em IVS, analfabetismo e cobertura de APS; negativo em plano de saude, estabelecimentos per capita e gasto proprio. Correlaciona -0,46 com o PC1 de mortalidade.';

comment on table public.mart_demanda_mensal_hospital is 'Série mensal de internações por estabelecimento (CNES): volume, óbitos e valor aprovado. Base para a projeção de demanda (mart_forecast_demanda_hospital). Fonte: SIH/DataSUS.';

comment on table public.mart_dengue_municipio_ano is 'Dengue (SINAN) anual por município: casos, incidência por 100 mil hab. e letalidade. Fonte: SINAN/DataSUS + IBGE.';

comment on table public.mart_dengue_semana is 'Dengue (SINAN): casos prováveis, graves e óbitos por município e semana epidemiológica (data dos primeiros sintomas). Casos prováveis = notificações exceto descartadas.';

comment on table public.mart_equidade_aps_municipio is 'Teste de robustez do Caso 3 (indicadores nao comparam): compara cada municipio apenas aos pares do MESMO quartil de porte populacional, usando densidade de ESF por 10k hab. (nao a cobertura % que satura) e %ICSAP (nao ICSAP/100k, que embute o confundimento de acesso hospitalar geral). RESULTADO: nulo. A correlacao esf_por_10k x %ICSAP dentro do porte e proxima de zero (rho entre -0.02 e +0.18 conforme o quartil); a co-ocorrencia observada de baixa densidade de equipe + alto %ICSAP (campo atencao) e 0,94x o que a independencia estatistica preveria — ou seja, nao ha sinergia real, e a leve associacao com vulnerabilidade (IVS) e explicada pela alocacao de equipes (que ja responde a vulnerabilidade), nao por uma relacao causal ICSAP-vulnerabilidade. NAO usar o campo atencao como ranking ou flag de prioridade municipal — a razao observado/esperado de 0,94 mostra que a co-ocorrencia e estatisticamente indistinguivel do acaso.';

comment on table public.mart_excesso_uf_mes is 'Excesso de mortalidade (todas as causas, não fetais): observado vs esperado (média 2015–2019 do mês, ajustada pela população do ano).';

comment on table public.mart_fluxo_intermunicipal is 'Fluxo de pacientes do SUS: internações por município de residência → município de atendimento (SIH, 2024). Apenas fluxos intermunicipais com 5+ internações. Inspirado no LabSUS (UFT).';

comment on table public.mart_forecast_demanda_hospital is 'Projeção de internações mensais por hospital (tendência linear sobre mart_demanda_mensal_hospital), com faixa de incerteza indicativa. confianca=baixa quando o hospital tem menos de 24 meses de histórico. Fonte: SIH/DataSUS (derivado).';

comment on column public.mart_forecast_demanda_hospital.confianca is 'OBSOLETA - substituida por status_validacao. Refletia apenas o comprimento da serie (>=24 meses = adequada), nunca o acerto do modelo. Mantida por um ciclo para nao quebrar consumidores da API publica. Sera removida.';

comment on column public.mart_forecast_demanda_hospital.ic_inferior is 'Limite inferior do intervalo de 95%, truncado em zero. A meia-largura usa z empirico calibrado pelo backtest (2,42 / 2,64 / 2,80 para 1, 2 e 3 meses), nao z=1,96: sob normalidade o intervalo cobria 85% do que prometia.';

comment on column public.mart_forecast_demanda_hospital.modelo is 'Metodo que gerou a linha. tendencia_linear: OLS sobre o tempo de calendario. Concorreu com naive, ingenuo sazonal, media movel de 3 meses, sazonal+drift e tendencia com sazonalidade; os sazonais ficaram PIORES por hospital. Ver docs/MODEL_CARD_FORECAST.md.';

comment on column public.mart_forecast_demanda_hospital.smape_backtest_pct is 'sMAPE medido por validacao de origem movel no estrato de volume deste hospital, no horizonte desta linha. E o erro que previsoes como esta apresentaram historicamente - nao o erro desta previsao especifica.';

comment on column public.mart_forecast_demanda_hospital.status_validacao is 'A = validado (erro medido no estrato <=30% de sMAPE e >=24 meses de historico); B = experimental (erro entre 30% e 50%, ou historico curto - nao use para dimensionar oferta); C = nao publicavel (erro >50%). Limiares derivados da distribuicao observada de sMAPE por estrato no backtest, nao de convencao. Linhas C nao sao publicadas por padrao.';

comment on table public.mart_hsmr_hospital is 'HSMR (razão de mortalidade hospitalar padronizada) por estabelecimento (CNES): óbitos observados vs. esperados, ajustado por faixa etária x capítulo CID-10 (padronização indireta). estavel=false quando óbitos esperados < 5 (razão instável, não oculta). Fonte: SIH/DataSUS.';

comment on column public.mart_hsmr_hospital.hsmr_estrato is 'HSMR recalibrado dentro do estrato de complexidade (com/sem UTI). O ajuste por capitulo CID-10 nao captura gravidade: em 2024 o O/E agregado era 1,163 (com UTI) e 0,542 (sem UTI). A classificacao usa esta coluna. VIES RESIDUAL DECLARADO: o HSMR mediano ainda cresce com o porte (0,39 nos menores a 0,93 nos maiores) mesmo dentro do estrato.';

comment on column public.mart_hsmr_hospital.hsmr_ic95_inf is 'Limite inferior do IC95% do HSMR (metodo gamma/Poisson exato, mesmo das taxas brutas do projeto).';

comment on column public.mart_hsmr_hospital.hsmr_ic95_sup is 'Limite superior do IC95% do HSMR.';

comment on column public.mart_hsmr_hospital.hsmr_pvalor is 'P-valor bilateral exato de Poisson (H0: taxa observada = esperada).';

comment on column public.mart_hsmr_hospital.hsmr_q_valor is 'P-valor ajustado por multiplas comparacoes (Benjamini-Hochberg, por ano civil). A classificacao significancia usa q<0.05, nao o p bruto — em ~4.600 testes simultaneos por ano, p<0.05 sem correcao produz falsos positivos por acaso.';

comment on column public.mart_hsmr_hospital.significancia is 'acima / abaixo / esperado / indeterminado — baseado no q-valor (FDR, Benjamini-Hochberg por ano), nao apenas no IC95% bruto. ATENCAO: o ajuste por faixa etaria x capitulo CID-10 e grosseiro; hospitais terciarios concentram casos graves dentro do mesmo capitulo e tendem sistematicamente a HSMR maior (case-mix residual). Nao usar para ranquear hospitais.';

comment on table public.mart_icsap_municipio is 'Internações por Condições Sensíveis à Atenção Primária (aproximação da Lista Brasileira de ICSAP, CID-10 3 caracteres) por município (SIH, 2024). Proporção alta sugere fragilidade da atenção básica.';

comment on column public.mart_icsap_municipio.aih_continuacao is 'AIHs de continuacao (IDENT=5) dentro de internacoes_total. Efeito no pct_icsap e pequeno (+0,93% relativo na amostra de 2024): so I69 e G40 da lista brasileira geram continuacao em volume.';

comment on column public.mart_icsap_municipio.g1_100k is 'Internacoes do grupo 1 por 100 mil habitantes. E o lado populacional do impacto vacinal, cruzavel com as doses aplicadas do PNI.';

comment on column public.mart_icsap_municipio.internacoes_g1 is 'Internacoes do grupo 1 da Lista Brasileira de ICSAP: doencas preveniveis por imunizacao e condicoes sensiveis (tuberculoses, tetano, difteria, coqueluche, sifilis, febre amarela, sarampo, rubeola, hepatite B, parotidite, malaria, ascaridiase, meningite, febre reumatica). Subconjunto de internacoes_icsap.';

comment on view public.mart_icsap_pares is 'Distância de cada município até a mediana dos seus pares em internações sensíveis à atenção primária (ICSAP), traduzida em internações, custo, leitos-dia e leitos equivalentes/ano. Pares = estrato de saúde (tercis fixos de mortalidade × vulnerabilidade × internação) NO MESMO ANO; sem estrato, faixa populacional × região. n_pares conta municípios do grupo naquele ano (V042; antes contava município-ano). security_invoker=true: lê com a permissão de quem consulta (ver V025). NÃO é economia garantida: alcançar a mediana exige investimento em atenção primária, nem toda ICSAP é evitável, e a associação é ecológica (municipal), não individual.';

comment on table public.mart_internacoes_municipio is 'Internações SUS (SIH/AIH) por município, ano e capítulo CID-10: volume, permanência média, mortalidade intra-hospitalar e custo médio. Fonte: SIH/DataSUS + IBGE.';

comment on column public.mart_internacoes_municipio.aih_continuacao is 'AIHs de continuacao (IDENT=5) incluidas em `internacoes`. Uma internacao prolongada emite varias AIHs; use `aih_normal` como denominador de medias por episodio.';

comment on column public.mart_internacoes_municipio.aih_normal is 'internacoes - aih_continuacao. Denominador de permanencia_media e custo_medio.';

comment on column public.mart_internacoes_municipio.dias_permanencia_normal is 'Soma de DIAS_PERM restrita a AIH normal (IDENT<>5).';

comment on column public.mart_internacoes_municipio.valor_normal is 'Soma de VAL_TOT restrita a AIH normal (IDENT<>5).';

comment on table public.mart_leitos_icsap_municipio is 'Cruzamento leitos (CNES-LT) x ICSAP (SIH) por municipio, 2024. ATENCAO: ICSAP e por municipio de RESIDENCIA do paciente; leitos por municipio do ESTABELECIMENTO. sem_leito = sem oferta LOCAL, nao sem acesso.';

comment on table public.mart_leitos_municipio is 'Leitos hospitalares por municipio e ano (CNES grupo LT, FTP DataSUS, competencia de dezembro). Cadastro fotografado mensalmente: cada linha e um SNAPSHOT anual, nunca soma de competencias. UTI identificada por lista explicita de codigos da tabela oficial de dominios.';

comment on table public.mart_los_hospital is 'Tempo de permanência (LOS) esperado por diagnóstico (CID-10, 3 caracteres): mediana do hospital vs. mediana nacional, aproximadas por histograma de faixas de dias. desvio_dias > 0 = hospital interna por mais tempo que a mediana nacional. Fonte: SIH/DataSUS.';

comment on table public.mart_mortalidade_causa is 'Óbitos por causa básica (CID-10, 3 caracteres) por UF e ano. Fonte: SIM/DataSUS.';

comment on table public.mart_mortalidade_infantil_uf is 'Taxa de Mortalidade Infantil por UF e ano: óbitos <1 ano (SIM) / nascidos vivos (SINASC) × 1000.';

comment on table public.mart_mortalidade_municipio is 'Óbitos por município, ano, capítulo CID-10 e sexo. Fonte: SIM/DataSUS. Inclui linhas TOTAL para subtotais.';

comment on column public.mart_mortalidade_municipio.ic95_inf is 'IC95%% inferior da taxa bruta (método gamma/Poisson exato).';

comment on column public.mart_mortalidade_municipio.ic95_sup is 'IC95%% superior da taxa bruta (método gamma/Poisson exato).';

comment on column public.mart_mortalidade_municipio.taxa_padronizada_100k is 'Taxa padronizada por idade (método direto; padrão = Brasil Censo 2022). Apenas em linhas capitulo_cid=TOTAL e sexo=TOTAL.';

comment on table public.mart_mortalidade_uf_mes is 'Série mensal de óbitos por UF, capítulo CID-10, sexo e faixa etária. Fonte: SIM/DataSUS.';

comment on table public.mart_natalidade_municipio is 'Nascidos vivos (SINASC/DataSUS) por município e ano: volume, % baixo peso (<2500g), % prematuro (<37 sem), % com 7+ consultas pré-natal, idade média da mãe.';

comment on table public.mart_perfil_mortalidade_municipio is 'Coordenadas do perfil de causas de morte por municipio (2015-2024), apos remover porte, estrutura etaria, qualidade do registro e COVID. Seis componentes acima do nulo multinomial (V037).';

comment on column public.mart_perfil_mortalidade_municipio.grupo is 'Discretizacao declarada de um continuo, NAO tipologia: ARI 0,93 entre subamostras mas silhueta 0,17. Use pc1..pc6 para analise; use grupo apenas para exposicao.';

comment on column public.mart_perfil_mortalidade_municipio.indice_inespecificidade is 'Fracao dos obitos codificada em CID impreciso (NE/NCOP/SOE), excluido B34 que e COVID. Correlaciona -0,54 com o PC1 e apenas +0,37 com o indicador classico de causas mal definidas.';

comment on column public.mart_saude_suplementar_municipio.razao_implausivel is 'TRUE quando vinculos_plano_por_100_hab > 100 - o municipio nao suporta leitura como cobertura populacional (provavel artefato de endereco de contrato).';

comment on column public.mart_saude_suplementar_municipio.vinculos_medico_hospitalar is 'Vinculos ativos a plano medico-hospitalar (ANS/SIB, QT_BENEFICIARIO_ATIVO, competencia dez). Vinculo != pessoa: uma pessoa com dois produtos conta duas vezes.';

comment on column public.mart_saude_suplementar_municipio.vinculos_plano_por_100_hab is 'Vinculos medico-hospitalares por 100 habitantes. NAO e o percentual da populacao com plano: o SIB conta vinculos e localiza pelo endereco do contrato, nao pela residencia. Pode passar de 100.';

comment on table public.mart_siops_municipio is 'Gasto publico municipal em saude (SIOPS/MS, serie historica de indicadores). Despesa EMPENHADA, dado AUTODECLARADO pelo ente. Gasto nao mede acesso nem qualidade.';

comment on column public.mart_siops_municipio.abaixo_do_minimo_ec29 is 'TRUE se declarou abaixo de 15%. NULL quando nao declarou - ausencia de declaracao nao e descumprimento.';

comment on column public.mart_siops_municipio.gasto_proprio_saude_hab is 'Despesa com recursos proprios em saude por habitante (R$). Oscila muito em municipio pequeno.';

comment on column public.mart_siops_municipio.pct_receita_propria_saude is 'Percentual da receita propria aplicado em ASPS. Piso constitucional de 15% (EC 29 / LC 141).';

comment on table public.mart_vacinacao_uf_mes is 'Doses aplicadas do PNI por competencia mensal, UF e imunobiologico. Fonte mais atual do projeto, com cerca de um mes de defasagem.';

comment on table public.mart_vazio_assistencial_municipio is 'Cruzamento leitos (CNES-LT) x mortalidade (SIM) por municipio, 2023. Testa se viver em municipio sem leito local eleva a mortalidade padronizada (nao) ou muda o local do obito (efeito bruto era confundido por porte).';

comment on table public.meta_dataset is 'Metadados do dataset: fontes, datas de atualização, licença, cobertura.';
