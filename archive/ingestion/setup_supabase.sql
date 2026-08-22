-- =============================================================================
-- setup_supabase.sql
-- DDL completo para inicializar o projeto no Supabase
-- Execute via: psql $DATABASE_URL -f ingestion/setup_supabase.sql
-- =============================================================================

-- Habilita extensões úteis
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";   -- Busca por similaridade de texto

-- =============================================================================
-- TABELA DE CONTROLE
-- =============================================================================

CREATE TABLE IF NOT EXISTS public.ingestion_log (
    id              BIGSERIAL PRIMARY KEY,
    estado          VARCHAR(2)   NOT NULL,
    ano             SMALLINT     NOT NULL,
    mes             SMALLINT     NOT NULL,
    sistema         VARCHAR(20)  NOT NULL DEFAULT 'SIA_PA',
    status          VARCHAR(10)  NOT NULL DEFAULT 'pending'
                    CHECK (status IN ('pending','running','success','error','skipped')),
    loaded_at       TIMESTAMPTZ,
    qtd_registros   INTEGER,
    error_msg       TEXT,
    elapsed_sec     NUMERIC(8,2),
    created_at      TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    UNIQUE (estado, ano, mes, sistema)
);

CREATE INDEX IF NOT EXISTS idx_ingest_estado_ano ON public.ingestion_log (estado, ano, sistema);
CREATE INDEX IF NOT EXISTS idx_ingest_status     ON public.ingestion_log (status);

COMMENT ON TABLE public.ingestion_log IS
    'Controle incremental de ingestão DataSUS. '
    'Chave: (estado, ano, mes, sistema). Status=success = não reprocessar.';

-- =============================================================================
-- DADOS BRUTOS SIA/PA
-- =============================================================================

CREATE TABLE IF NOT EXISTS public.sia_pa_raw (
    id                    BIGSERIAL,
    mes_competencia       VARCHAR(6)   NOT NULL,
    ano_competencia       SMALLINT     NOT NULL,
    mes_num               SMALLINT     NOT NULL,
    municipio_cod         VARCHAR(6),
    proc_id               VARCHAR(10),
    cid_primario          VARCHAR(4),
    qtd_aprovada          INTEGER,
    valor_aprovado        NUMERIC(12,2),
    tipo_financiamento    VARCHAR(2),
    categoria_atendimento VARCHAR(2),
    sexo                  VARCHAR(1),
    faixa_etaria          SMALLINT,
    uf_sigla              VARCHAR(2)   NOT NULL
) PARTITION BY LIST (uf_sigla);

-- Índices na tabela pai (propagados para partições)
CREATE INDEX IF NOT EXISTS idx_sia_pa_competencia   ON public.sia_pa_raw (mes_competencia);
CREATE INDEX IF NOT EXISTS idx_sia_pa_municipio     ON public.sia_pa_raw (municipio_cod);
CREATE INDEX IF NOT EXISTS idx_sia_pa_proc          ON public.sia_pa_raw (proc_id);
CREATE INDEX IF NOT EXISTS idx_sia_pa_cid           ON public.sia_pa_raw (cid_primario);

COMMENT ON TABLE public.sia_pa_raw IS
    'Dados brutos SIA/PA do DataSUS. Particionada por UF. '
    'Populada via COPY bulk load pelo pipeline de ingestão Python. '
    'NÃO modificar manualmente — use os marts para análises.';

-- Cria partições para cada UF
DO $$
DECLARE
    ufs TEXT[] := ARRAY[
        'AC','AL','AP','AM','BA','CE','DF','ES','GO',
        'MA','MT','MS','MG','PA','PB','PR','PE','PI',
        'RJ','RN','RS','RO','RR','SC','SP','SE','TO'
    ];
    uf TEXT;
BEGIN
    FOREACH uf IN ARRAY ufs LOOP
        EXECUTE format(
            'CREATE TABLE IF NOT EXISTS public.sia_pa_%s '
            'PARTITION OF public.sia_pa_raw FOR VALUES IN (%L)',
            lower(uf), uf
        );
    END LOOP;
END $$;

-- =============================================================================
-- TABELAS DE REFERÊNCIA
-- =============================================================================

CREATE TABLE IF NOT EXISTS public.ref_cid10 (
    codigo_cid         VARCHAR(4)   PRIMARY KEY,
    descricao_cid      TEXT,
    grupo_cid          VARCHAR(10),
    nome_grupo_cid     TEXT,
    capitulo_cid       VARCHAR(5),
    nome_capitulo_cid  TEXT
);

CREATE TABLE IF NOT EXISTS public.ref_sigtap (
    proc_id            VARCHAR(10)  PRIMARY KEY,
    nome_procedimento  TEXT,
    complexidade       VARCHAR(2),
    grupo_proc         VARCHAR(2),
    nome_grupo         TEXT,
    subgrupo_proc      VARCHAR(4),
    valor_sp           NUMERIC(10,4),
    valor_sh           NUMERIC(10,4),
    competencia_ref    VARCHAR(6)
);

CREATE TABLE IF NOT EXISTS public.ref_ibge_municipios (
    municipio_cod   VARCHAR(7)   PRIMARY KEY,
    municipio_cod6  VARCHAR(6),
    nome_municipio  TEXT,
    uf_sigla        VARCHAR(2),
    uf_nome         TEXT,
    regiao          VARCHAR(20),
    capital         BOOLEAN  DEFAULT FALSE,
    latitude        NUMERIC(9,6),
    longitude       NUMERIC(9,6)
);
CREATE INDEX IF NOT EXISTS idx_mun_cod6 ON public.ref_ibge_municipios (municipio_cod6);
CREATE INDEX IF NOT EXISTS idx_mun_uf   ON public.ref_ibge_municipios (uf_sigla);

CREATE TABLE IF NOT EXISTS public.ref_ibge_populacao (
    municipio_cod6      VARCHAR(6),
    uf_sigla            VARCHAR(2),
    ano_referencia      SMALLINT,
    populacao_estimada  INTEGER,
    fonte               VARCHAR(20)  DEFAULT 'IBGE_ESTIMATIVA',
    PRIMARY KEY (municipio_cod6, ano_referencia)
);

COMMENT ON TABLE public.ref_cid10             IS 'CID-10 — Classificação Internacional de Doenças';
COMMENT ON TABLE public.ref_sigtap            IS 'SIGTAP — Tabela de Procedimentos do SUS';
COMMENT ON TABLE public.ref_ibge_municipios   IS 'Municípios brasileiros (IBGE)';
COMMENT ON TABLE public.ref_ibge_populacao    IS 'Estimativas populacionais anuais por município (IBGE)';

-- =============================================================================
-- ROW LEVEL SECURITY (Supabase)
-- Para leitura pública dos marts (dados agregados — sem dados pessoais)
-- =============================================================================

ALTER TABLE public.ingestion_log     ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.sia_pa_raw        ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.ref_cid10         ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.ref_sigtap        ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.ref_ibge_municipios ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.ref_ibge_populacao  ENABLE ROW LEVEL SECURITY;

-- Apenas service_role pode escrever (ingestão)
-- anon pode ler referências
CREATE POLICY IF NOT EXISTS "refs_leitura_publica" ON public.ref_cid10
    FOR SELECT USING (true);
CREATE POLICY IF NOT EXISTS "refs_leitura_publica" ON public.ref_sigtap
    FOR SELECT USING (true);
CREATE POLICY IF NOT EXISTS "refs_leitura_publica" ON public.ref_ibge_municipios
    FOR SELECT USING (true);
CREATE POLICY IF NOT EXISTS "refs_leitura_publica" ON public.ref_ibge_populacao
    FOR SELECT USING (true);

SELECT 'Setup Supabase concluído com sucesso!' AS resultado;
