-- =============================================================================
-- Migration V013 — Particionamento por UF: 27 estados (2026-05-23)
-- Estratégia: PostgreSQL declarative LIST partitioning por uf_sigla
-- Cobre: raw.sia_pa, raw.sim_do, raw.sih_aih, raw.sinan, raw.cnes
-- Cada tabela ganha 27 partições (uma por estado) + 1 partição DEFAULT
-- Pré-requisito: execute APENAS em database vazio ou após pg_dump/restore
-- Para produção com dados existentes: ver script de migração ao vivo em docs/
-- =============================================================================

BEGIN;

-- ---------------------------------------------------------------------------
-- 0. Schema e extensões
-- ---------------------------------------------------------------------------
CREATE SCHEMA IF NOT EXISTS raw;

-- Garante que a função de validação de UF existe
CREATE OR REPLACE FUNCTION raw.validate_uf(uf CHAR(2))
RETURNS BOOLEAN LANGUAGE SQL IMMUTABLE AS $$
  SELECT uf = ANY(ARRAY[
    'AC','AL','AM','AP','BA','CE','DF','ES','GO','MA',
    'MG','MS','MT','PA','PB','PE','PI','PR','RJ','RN',
    'RO','RR','RS','SC','SE','SP','TO'
  ]);
$$;

-- ---------------------------------------------------------------------------
-- 1. raw.sia_pa — Produção Ambulatorial
-- ---------------------------------------------------------------------------
DROP TABLE IF EXISTS raw.sia_pa CASCADE;

CREATE TABLE raw.sia_pa (
    id               BIGSERIAL,
    uf_sigla         CHAR(2)       NOT NULL CHECK (raw.validate_uf(uf_sigla)),
    municipio_codigo CHAR(6),
    competencia_ano  SMALLINT      NOT NULL CHECK (competencia_ano BETWEEN 2019 AND 2030),
    competencia_mes  SMALLINT      NOT NULL CHECK (competencia_mes BETWEEN 1 AND 12),
    procedimento_codigo VARCHAR(10),
    complexidade     VARCHAR(2),
    quantidade_aprovada INTEGER,
    valor_aprovado   NUMERIC(12,2),
    cns_pac          VARCHAR(15),
    dt_atendimento   DATE,
    _loaded_at       TIMESTAMPTZ   DEFAULT NOW(),
    PRIMARY KEY (id, uf_sigla)
) PARTITION BY LIST (uf_sigla);

-- Partições sia_pa
CREATE TABLE raw.sia_pa_ac PARTITION OF raw.sia_pa FOR VALUES IN ('AC');
CREATE TABLE raw.sia_pa_al PARTITION OF raw.sia_pa FOR VALUES IN ('AL');
CREATE TABLE raw.sia_pa_am PARTITION OF raw.sia_pa FOR VALUES IN ('AM');
CREATE TABLE raw.sia_pa_ap PARTITION OF raw.sia_pa FOR VALUES IN ('AP');
CREATE TABLE raw.sia_pa_ba PARTITION OF raw.sia_pa FOR VALUES IN ('BA');
CREATE TABLE raw.sia_pa_ce PARTITION OF raw.sia_pa FOR VALUES IN ('CE');
CREATE TABLE raw.sia_pa_df PARTITION OF raw.sia_pa FOR VALUES IN ('DF');
CREATE TABLE raw.sia_pa_es PARTITION OF raw.sia_pa FOR VALUES IN ('ES');
CREATE TABLE raw.sia_pa_go PARTITION OF raw.sia_pa FOR VALUES IN ('GO');
CREATE TABLE raw.sia_pa_ma PARTITION OF raw.sia_pa FOR VALUES IN ('MA');
CREATE TABLE raw.sia_pa_mg PARTITION OF raw.sia_pa FOR VALUES IN ('MG');
CREATE TABLE raw.sia_pa_ms PARTITION OF raw.sia_pa FOR VALUES IN ('MS');
CREATE TABLE raw.sia_pa_mt PARTITION OF raw.sia_pa FOR VALUES IN ('MT');
CREATE TABLE raw.sia_pa_pa PARTITION OF raw.sia_pa FOR VALUES IN ('PA');
CREATE TABLE raw.sia_pa_pb PARTITION OF raw.sia_pa FOR VALUES IN ('PB');
CREATE TABLE raw.sia_pa_pe PARTITION OF raw.sia_pa FOR VALUES IN ('PE');
CREATE TABLE raw.sia_pa_pi PARTITION OF raw.sia_pa FOR VALUES IN ('PI');
CREATE TABLE raw.sia_pa_pr PARTITION OF raw.sia_pa FOR VALUES IN ('PR');
CREATE TABLE raw.sia_pa_rj PARTITION OF raw.sia_pa FOR VALUES IN ('RJ');
CREATE TABLE raw.sia_pa_rn PARTITION OF raw.sia_pa FOR VALUES IN ('RN');
CREATE TABLE raw.sia_pa_ro PARTITION OF raw.sia_pa FOR VALUES IN ('RO');
CREATE TABLE raw.sia_pa_rr PARTITION OF raw.sia_pa FOR VALUES IN ('RR');
CREATE TABLE raw.sia_pa_rs PARTITION OF raw.sia_pa FOR VALUES IN ('RS');
CREATE TABLE raw.sia_pa_sc PARTITION OF raw.sia_pa FOR VALUES IN ('SC');
CREATE TABLE raw.sia_pa_se PARTITION OF raw.sia_pa FOR VALUES IN ('SE');
CREATE TABLE raw.sia_pa_sp PARTITION OF raw.sia_pa FOR VALUES IN ('SP');
CREATE TABLE raw.sia_pa_to PARTITION OF raw.sia_pa FOR VALUES IN ('TO');
CREATE TABLE raw.sia_pa_default PARTITION OF raw.sia_pa DEFAULT;

-- Índices sia_pa (criados na tabela pai — propagam para partições)
CREATE INDEX idx_sia_pa_uf_ano    ON raw.sia_pa (uf_sigla, competencia_ano);
CREATE INDEX idx_sia_pa_municipio ON raw.sia_pa (municipio_codigo);
CREATE INDEX idx_sia_pa_proc      ON raw.sia_pa (procedimento_codigo);
CREATE INDEX idx_sia_pa_loaded    ON raw.sia_pa (_loaded_at);

-- ---------------------------------------------------------------------------
-- 2. raw.sim_do — Sistema de Informações sobre Mortalidade
-- ---------------------------------------------------------------------------
DROP TABLE IF EXISTS raw.sim_do CASCADE;

CREATE TABLE raw.sim_do (
    id               BIGSERIAL,
    uf_sigla         CHAR(2)       NOT NULL CHECK (raw.validate_uf(uf_sigla)),
    municipio_codigo CHAR(6),
    ano_obito        SMALLINT      NOT NULL CHECK (ano_obito BETWEEN 2019 AND 2030),
    mes_obito        SMALLINT      CHECK (mes_obito BETWEEN 1 AND 12),
    causa_basica     VARCHAR(4),   -- CID-10
    causa_cap1       VARCHAR(4),
    sexo             CHAR(1)       CHECK (sexo IN ('M','F','I')),
    idade_anos       SMALLINT      CHECK (idade_anos >= 0),
    raca_cor         VARCHAR(2),
    escolaridade     VARCHAR(2),
    _loaded_at       TIMESTAMPTZ   DEFAULT NOW(),
    PRIMARY KEY (id, uf_sigla)
) PARTITION BY LIST (uf_sigla);

-- Partições sim_do
CREATE TABLE raw.sim_do_ac PARTITION OF raw.sim_do FOR VALUES IN ('AC');
CREATE TABLE raw.sim_do_al PARTITION OF raw.sim_do FOR VALUES IN ('AL');
CREATE TABLE raw.sim_do_am PARTITION OF raw.sim_do FOR VALUES IN ('AM');
CREATE TABLE raw.sim_do_ap PARTITION OF raw.sim_do FOR VALUES IN ('AP');
CREATE TABLE raw.sim_do_ba PARTITION OF raw.sim_do FOR VALUES IN ('BA');
CREATE TABLE raw.sim_do_ce PARTITION OF raw.sim_do FOR VALUES IN ('CE');
CREATE TABLE raw.sim_do_df PARTITION OF raw.sim_do FOR VALUES IN ('DF');
CREATE TABLE raw.sim_do_es PARTITION OF raw.sim_do FOR VALUES IN ('ES');
CREATE TABLE raw.sim_do_go PARTITION OF raw.sim_do FOR VALUES IN ('GO');
CREATE TABLE raw.sim_do_ma PARTITION OF raw.sim_do FOR VALUES IN ('MA');
CREATE TABLE raw.sim_do_mg PARTITION OF raw.sim_do FOR VALUES IN ('MG');
CREATE TABLE raw.sim_do_ms PARTITION OF raw.sim_do FOR VALUES IN ('MS');
CREATE TABLE raw.sim_do_mt PARTITION OF raw.sim_do FOR VALUES IN ('MT');
CREATE TABLE raw.sim_do_pa PARTITION OF raw.sim_do FOR VALUES IN ('PA');
CREATE TABLE raw.sim_do_pb PARTITION OF raw.sim_do FOR VALUES IN ('PB');
CREATE TABLE raw.sim_do_pe PARTITION OF raw.sim_do FOR VALUES IN ('PE');
CREATE TABLE raw.sim_do_pi PARTITION OF raw.sim_do FOR VALUES IN ('PI');
CREATE TABLE raw.sim_do_pr PARTITION OF raw.sim_do FOR VALUES IN ('PR');
CREATE TABLE raw.sim_do_rj PARTITION OF raw.sim_do FOR VALUES IN ('RJ');
CREATE TABLE raw.sim_do_rn PARTITION OF raw.sim_do FOR VALUES IN ('RN');
CREATE TABLE raw.sim_do_ro PARTITION OF raw.sim_do FOR VALUES IN ('RO');
CREATE TABLE raw.sim_do_rr PARTITION OF raw.sim_do FOR VALUES IN ('RR');
CREATE TABLE raw.sim_do_rs PARTITION OF raw.sim_do FOR VALUES IN ('RS');
CREATE TABLE raw.sim_do_sc PARTITION OF raw.sim_do FOR VALUES IN ('SC');
CREATE TABLE raw.sim_do_se PARTITION OF raw.sim_do FOR VALUES IN ('SE');
CREATE TABLE raw.sim_do_sp PARTITION OF raw.sim_do FOR VALUES IN ('SP');
CREATE TABLE raw.sim_do_to PARTITION OF raw.sim_do FOR VALUES IN ('TO');
CREATE TABLE raw.sim_do_default PARTITION OF raw.sim_do DEFAULT;

CREATE INDEX idx_sim_do_uf_ano ON raw.sim_do (uf_sigla, ano_obito);
CREATE INDEX idx_sim_do_cid    ON raw.sim_do (causa_basica);
CREATE INDEX idx_sim_do_sexo   ON raw.sim_do (sexo);
CREATE INDEX idx_sim_do_loaded ON raw.sim_do (_loaded_at);

-- ---------------------------------------------------------------------------
-- 3. raw.sih_aih — Sistema de Informações Hospitalares
-- ---------------------------------------------------------------------------
DROP TABLE IF EXISTS raw.sih_aih CASCADE;

CREATE TABLE raw.sih_aih (
    id                   BIGSERIAL,
    uf_sigla             CHAR(2)     NOT NULL CHECK (raw.validate_uf(uf_sigla)),
    municipio_codigo     CHAR(6),
    competencia_ano      SMALLINT    NOT NULL CHECK (competencia_ano BETWEEN 2019 AND 2030),
    competencia_mes      SMALLINT    NOT NULL CHECK (competencia_mes BETWEEN 1 AND 12),
    diag_principal       VARCHAR(4),  -- CID-10
    diag_secundario      VARCHAR(4),
    procedimento_realizado VARCHAR(10),
    carater_internacao   CHAR(2),
    dias_permanencia     SMALLINT    CHECK (dias_permanencia >= 0),
    valor_total          NUMERIC(12,2),
    valor_servicos       NUMERIC(12,2),
    obito                BOOLEAN,
    sexo                 CHAR(1)     CHECK (sexo IN ('M','F','I')),
    idade_anos           SMALLINT    CHECK (idade_anos >= 0),
    _loaded_at           TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (id, uf_sigla)
) PARTITION BY LIST (uf_sigla);

-- Partições sih_aih
CREATE TABLE raw.sih_aih_ac PARTITION OF raw.sih_aih FOR VALUES IN ('AC');
CREATE TABLE raw.sih_aih_al PARTITION OF raw.sih_aih FOR VALUES IN ('AL');
CREATE TABLE raw.sih_aih_am PARTITION OF raw.sih_aih FOR VALUES IN ('AM');
CREATE TABLE raw.sih_aih_ap PARTITION OF raw.sih_aih FOR VALUES IN ('AP');
CREATE TABLE raw.sih_aih_ba PARTITION OF raw.sih_aih FOR VALUES IN ('BA');
CREATE TABLE raw.sih_aih_ce PARTITION OF raw.sih_aih FOR VALUES IN ('CE');
CREATE TABLE raw.sih_aih_df PARTITION OF raw.sih_aih FOR VALUES IN ('DF');
CREATE TABLE raw.sih_aih_es PARTITION OF raw.sih_aih FOR VALUES IN ('ES');
CREATE TABLE raw.sih_aih_go PARTITION OF raw.sih_aih FOR VALUES IN ('GO');
CREATE TABLE raw.sih_aih_ma PARTITION OF raw.sih_aih FOR VALUES IN ('MA');
CREATE TABLE raw.sih_aih_mg PARTITION OF raw.sih_aih FOR VALUES IN ('MG');
CREATE TABLE raw.sih_aih_ms PARTITION OF raw.sih_aih FOR VALUES IN ('MS');
CREATE TABLE raw.sih_aih_mt PARTITION OF raw.sih_aih FOR VALUES IN ('MT');
CREATE TABLE raw.sih_aih_pa PARTITION OF raw.sih_aih FOR VALUES IN ('PA');
CREATE TABLE raw.sih_aih_pb PARTITION OF raw.sih_aih FOR VALUES IN ('PB');
CREATE TABLE raw.sih_aih_pe PARTITION OF raw.sih_aih FOR VALUES IN ('PE');
CREATE TABLE raw.sih_aih_pi PARTITION OF raw.sih_aih FOR VALUES IN ('PI');
CREATE TABLE raw.sih_aih_pr PARTITION OF raw.sih_aih FOR VALUES IN ('PR');
CREATE TABLE raw.sih_aih_rj PARTITION OF raw.sih_aih FOR VALUES IN ('RJ');
CREATE TABLE raw.sih_aih_rn PARTITION OF raw.sih_aih FOR VALUES IN ('RN');
CREATE TABLE raw.sih_aih_ro PARTITION OF raw.sih_aih FOR VALUES IN ('RO');
CREATE TABLE raw.sih_aih_rr PARTITION OF raw.sih_aih FOR VALUES IN ('RR');
CREATE TABLE raw.sih_aih_rs PARTITION OF raw.sih_aih FOR VALUES IN ('RS');
CREATE TABLE raw.sih_aih_sc PARTITION OF raw.sih_aih FOR VALUES IN ('SC');
CREATE TABLE raw.sih_aih_se PARTITION OF raw.sih_aih FOR VALUES IN ('SE');
CREATE TABLE raw.sih_aih_sp PARTITION OF raw.sih_aih FOR VALUES IN ('SP');
CREATE TABLE raw.sih_aih_to PARTITION OF raw.sih_aih FOR VALUES IN ('TO');
CREATE TABLE raw.sih_aih_default PARTITION OF raw.sih_aih DEFAULT;

CREATE INDEX idx_sih_aih_uf_ano  ON raw.sih_aih (uf_sigla, competencia_ano);
CREATE INDEX idx_sih_aih_diag    ON raw.sih_aih (diag_principal);
CREATE INDEX idx_sih_aih_obito   ON raw.sih_aih (obito) WHERE obito = TRUE;
CREATE INDEX idx_sih_aih_loaded  ON raw.sih_aih (_loaded_at);

-- ---------------------------------------------------------------------------
-- 4. raw.sinan — Sistema Nacional de Agravos de Notificação
-- ---------------------------------------------------------------------------
DROP TABLE IF EXISTS raw.sinan CASCADE;

CREATE TABLE raw.sinan (
    id               BIGSERIAL,
    uf_sigla         CHAR(2)       NOT NULL CHECK (raw.validate_uf(uf_sigla)),
    municipio_codigo CHAR(6),
    ano_notificacao  SMALLINT      NOT NULL CHECK (ano_notificacao BETWEEN 2019 AND 2030),
    semana_epidemio  SMALLINT      CHECK (semana_epidemio BETWEEN 1 AND 53),
    agravo_codigo    VARCHAR(4),   -- CID-10 / código agravo
    classificacao    VARCHAR(2),
    evolucao         VARCHAR(2),
    sexo             CHAR(1)       CHECK (sexo IN ('M','F','I')),
    idade_anos       SMALLINT      CHECK (idade_anos >= 0),
    raca_cor         VARCHAR(2),
    _loaded_at       TIMESTAMPTZ   DEFAULT NOW(),
    PRIMARY KEY (id, uf_sigla)
) PARTITION BY LIST (uf_sigla);

-- Partições sinan
CREATE TABLE raw.sinan_ac PARTITION OF raw.sinan FOR VALUES IN ('AC');
CREATE TABLE raw.sinan_al PARTITION OF raw.sinan FOR VALUES IN ('AL');
CREATE TABLE raw.sinan_am PARTITION OF raw.sinan FOR VALUES IN ('AM');
CREATE TABLE raw.sinan_ap PARTITION OF raw.sinan FOR VALUES IN ('AP');
CREATE TABLE raw.sinan_ba PARTITION OF raw.sinan FOR VALUES IN ('BA');
CREATE TABLE raw.sinan_ce PARTITION OF raw.sinan FOR VALUES IN ('CE');
CREATE TABLE raw.sinan_df PARTITION OF raw.sinan FOR VALUES IN ('DF');
CREATE TABLE raw.sinan_es PARTITION OF raw.sinan FOR VALUES IN ('ES');
CREATE TABLE raw.sinan_go PARTITION OF raw.sinan FOR VALUES IN ('GO');
CREATE TABLE raw.sinan_ma PARTITION OF raw.sinan FOR VALUES IN ('MA');
CREATE TABLE raw.sinan_mg PARTITION OF raw.sinan FOR VALUES IN ('MG');
CREATE TABLE raw.sinan_ms PARTITION OF raw.sinan FOR VALUES IN ('MS');
CREATE TABLE raw.sinan_mt PARTITION OF raw.sinan FOR VALUES IN ('MT');
CREATE TABLE raw.sinan_pa PARTITION OF raw.sinan FOR VALUES IN ('PA');
CREATE TABLE raw.sinan_pb PARTITION OF raw.sinan FOR VALUES IN ('PB');
CREATE TABLE raw.sinan_pe PARTITION OF raw.sinan FOR VALUES IN ('PE');
CREATE TABLE raw.sinan_pi PARTITION OF raw.sinan FOR VALUES IN ('PI');
CREATE TABLE raw.sinan_pr PARTITION OF raw.sinan FOR VALUES IN ('PR');
CREATE TABLE raw.sinan_rj PARTITION OF raw.sinan FOR VALUES IN ('RJ');
CREATE TABLE raw.sinan_rn PARTITION OF raw.sinan FOR VALUES IN ('RN');
CREATE TABLE raw.sinan_ro PARTITION OF raw.sinan FOR VALUES IN ('RO');
CREATE TABLE raw.sinan_rr PARTITION OF raw.sinan FOR VALUES IN ('RR');
CREATE TABLE raw.sinan_rs PARTITION OF raw.sinan FOR VALUES IN ('RS');
CREATE TABLE raw.sinan_sc PARTITION OF raw.sinan FOR VALUES IN ('SC');
CREATE TABLE raw.sinan_se PARTITION OF raw.sinan FOR VALUES IN ('SE');
CREATE TABLE raw.sinan_sp PARTITION OF raw.sinan FOR VALUES IN ('SP');
CREATE TABLE raw.sinan_to PARTITION OF raw.sinan FOR VALUES IN ('TO');
CREATE TABLE raw.sinan_default PARTITION OF raw.sinan DEFAULT;

CREATE INDEX idx_sinan_uf_ano  ON raw.sinan (uf_sigla, ano_notificacao);
CREATE INDEX idx_sinan_agravo  ON raw.sinan (agravo_codigo);
CREATE INDEX idx_sinan_semana  ON raw.sinan (semana_epidemio);
CREATE INDEX idx_sinan_loaded  ON raw.sinan (_loaded_at);

-- ---------------------------------------------------------------------------
-- 5. raw.cnes — Cadastro Nacional de Estabelecimentos de Saúde
-- ---------------------------------------------------------------------------
DROP TABLE IF EXISTS raw.cnes CASCADE;

CREATE TABLE raw.cnes (
    id                   BIGSERIAL,
    uf_sigla             CHAR(2)     NOT NULL CHECK (raw.validate_uf(uf_sigla)),
    cnes_codigo          VARCHAR(7)  NOT NULL,
    municipio_codigo     CHAR(6),
    nome_estabelecimento VARCHAR(150),
    tipo_unidade         VARCHAR(4),
    gestao               CHAR(1)     CHECK (gestao IN ('M','E','D')),
    leitos_sus           INTEGER     DEFAULT 0,
    leitos_nao_sus       INTEGER     DEFAULT 0,
    medicos              INTEGER     DEFAULT 0,
    enfermeiros          INTEGER     DEFAULT 0,
    equipamentos_tc      INTEGER     DEFAULT 0,
    equipamentos_rm      INTEGER     DEFAULT 0,
    competencia_ano      SMALLINT    NOT NULL CHECK (competencia_ano BETWEEN 2019 AND 2030),
    competencia_mes      SMALLINT    NOT NULL CHECK (competencia_mes BETWEEN 1 AND 12),
    latitude             NUMERIC(10,7),
    longitude            NUMERIC(10,7),
    _loaded_at           TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (id, uf_sigla)
) PARTITION BY LIST (uf_sigla);

-- Partições cnes
CREATE TABLE raw.cnes_ac PARTITION OF raw.cnes FOR VALUES IN ('AC');
CREATE TABLE raw.cnes_al PARTITION OF raw.cnes FOR VALUES IN ('AL');
CREATE TABLE raw.cnes_am PARTITION OF raw.cnes FOR VALUES IN ('AM');
CREATE TABLE raw.cnes_ap PARTITION OF raw.cnes FOR VALUES IN ('AP');
CREATE TABLE raw.cnes_ba PARTITION OF raw.cnes FOR VALUES IN ('BA');
CREATE TABLE raw.cnes_ce PARTITION OF raw.cnes FOR VALUES IN ('CE');
CREATE TABLE raw.cnes_df PARTITION OF raw.cnes FOR VALUES IN ('DF');
CREATE TABLE raw.cnes_es PARTITION OF raw.cnes FOR VALUES IN ('ES');
CREATE TABLE raw.cnes_go PARTITION OF raw.cnes FOR VALUES IN ('GO');
CREATE TABLE raw.cnes_ma PARTITION OF raw.cnes FOR VALUES IN ('MA');
CREATE TABLE raw.cnes_mg PARTITION OF raw.cnes FOR VALUES IN ('MG');
CREATE TABLE raw.cnes_ms PARTITION OF raw.cnes FOR VALUES IN ('MS');
CREATE TABLE raw.cnes_mt PARTITION OF raw.cnes FOR VALUES IN ('MT');
CREATE TABLE raw.cnes_pa PARTITION OF raw.cnes FOR VALUES IN ('PA');
CREATE TABLE raw.cnes_pb PARTITION OF raw.cnes FOR VALUES IN ('PB');
CREATE TABLE raw.cnes_pe PARTITION OF raw.cnes FOR VALUES IN ('PE');
CREATE TABLE raw.cnes_pi PARTITION OF raw.cnes FOR VALUES IN ('PI');
CREATE TABLE raw.cnes_pr PARTITION OF raw.cnes FOR VALUES IN ('PR');
CREATE TABLE raw.cnes_rj PARTITION OF raw.cnes FOR VALUES IN ('RJ');
CREATE TABLE raw.cnes_rn PARTITION OF raw.cnes FOR VALUES IN ('RN');
CREATE TABLE raw.cnes_ro PARTITION OF raw.cnes FOR VALUES IN ('RO');
CREATE TABLE raw.cnes_rr PARTITION OF raw.cnes FOR VALUES IN ('RR');
CREATE TABLE raw.cnes_rs PARTITION OF raw.cnes FOR VALUES IN ('RS');
CREATE TABLE raw.cnes_sc PARTITION OF raw.cnes FOR VALUES IN ('SC');
CREATE TABLE raw.cnes_se PARTITION OF raw.cnes FOR VALUES IN ('SE');
CREATE TABLE raw.cnes_sp PARTITION OF raw.cnes FOR VALUES IN ('SP');
CREATE TABLE raw.cnes_to PARTITION OF raw.cnes FOR VALUES IN ('TO');
CREATE TABLE raw.cnes_default PARTITION OF raw.cnes DEFAULT;

CREATE INDEX idx_cnes_uf_ano    ON raw.cnes (uf_sigla, competencia_ano);
CREATE INDEX idx_cnes_codigo    ON raw.cnes (cnes_codigo);
CREATE INDEX idx_cnes_tipo      ON raw.cnes (tipo_unidade);
CREATE INDEX idx_cnes_municipio ON raw.cnes (municipio_codigo);
CREATE INDEX idx_cnes_loaded    ON raw.cnes (_loaded_at);

-- ---------------------------------------------------------------------------
-- 6. Tabela de controle de ingestão por estado/sistema/ano
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS raw.ingestao_controle (
    id              BIGSERIAL PRIMARY KEY,
    uf_sigla        CHAR(2)      NOT NULL,
    sistema         VARCHAR(10)  NOT NULL,  -- 'SIA/PA', 'SIM/DO', 'SIH/AIH', 'SINAN', 'CNES'
    ano             SMALLINT     NOT NULL,
    mes             SMALLINT,
    status          VARCHAR(20)  NOT NULL DEFAULT 'pending',  -- pending/running/done/error
    registros_raw   INTEGER,
    registros_carga INTEGER,
    erro_mensagem   TEXT,
    iniciado_em     TIMESTAMPTZ,
    concluido_em    TIMESTAMPTZ,
    _created_at     TIMESTAMPTZ  DEFAULT NOW(),
    UNIQUE (uf_sigla, sistema, ano, mes)
);

CREATE INDEX idx_ingestao_uf_sistema ON raw.ingestao_controle (uf_sigla, sistema, ano);
CREATE INDEX idx_ingestao_status     ON raw.ingestao_controle (status);

-- ---------------------------------------------------------------------------
-- 7. View de progresso nacional de ingestão
-- ---------------------------------------------------------------------------
CREATE OR REPLACE VIEW raw.v_progresso_ingestao AS
SELECT
    sistema,
    ano,
    COUNT(*) FILTER (WHERE status = 'done')    AS estados_concluidos,
    COUNT(*) FILTER (WHERE status = 'running') AS estados_em_progresso,
    COUNT(*) FILTER (WHERE status = 'error')   AS estados_com_erro,
    COUNT(*) FILTER (WHERE status = 'pending') AS estados_pendentes,
    SUM(registros_carga) FILTER (WHERE status = 'done') AS total_registros,
    ROUND(
        COUNT(*) FILTER (WHERE status = 'done')::numeric / 27 * 100, 1
    ) AS pct_completo
FROM raw.ingestao_controle
GROUP BY sistema, ano
ORDER BY sistema, ano;

-- ---------------------------------------------------------------------------
-- 8. Comentários descritivos
-- ---------------------------------------------------------------------------
COMMENT ON TABLE raw.sia_pa IS 'SIA/PA — Produção Ambulatorial. Particionado por uf_sigla (27 estados). ~60-180M registros esperados.';
COMMENT ON TABLE raw.sim_do IS 'SIM/DO — Mortalidade. Particionado por uf_sigla. ~6-18M registros esperados.';
COMMENT ON TABLE raw.sih_aih IS 'SIH/AIH — Internações Hospitalares. Particionado por uf_sigla. ~12-36M registros esperados.';
COMMENT ON TABLE raw.sinan IS 'SINAN — Agravos de Notificação. Particionado por uf_sigla. ~5-15M registros esperados.';
COMMENT ON TABLE raw.cnes IS 'CNES — Estabelecimentos de Saúde. Particionado por uf_sigla. ~8-24M registros esperados.';
COMMENT ON TABLE raw.ingestao_controle IS 'Tabela de controle de ingestão: rastreia status por UF/sistema/ano para idempotência e retry.';
COMMENT ON FUNCTION raw.validate_uf IS 'Valida se a sigla corresponde a um dos 27 estados brasileiros.';

COMMIT;

-- ---------------------------------------------------------------------------
-- Verificação pós-migration (executar após COMMIT)
-- ---------------------------------------------------------------------------
-- SELECT schemaname, tablename, pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename))
-- FROM pg_tables WHERE schemaname = 'raw' ORDER BY tablename;
