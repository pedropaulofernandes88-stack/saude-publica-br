-- =============================================================================
-- V008 — sih_aih_raw
-- Tabela de recepção bruta das Autorizações de Internação Hospitalar (SIH/RD)
-- do DataSUS. Alimentada pelo job ingestion/ingest_sih.py via COPY (bulk load).
-- Granularidade: um registro por internação hospitalar (AIH).
-- =============================================================================

CREATE TABLE IF NOT EXISTS sih_aih_raw (
    id                  BIGSERIAL        PRIMARY KEY,

    -- Identificação da AIH
    n_aih               TEXT,                        -- número da AIH
    ident               TEXT,                        -- identificação do tipo de AIH (1=normal, 5=longa perm.)

    -- Temporal
    dt_inter            TEXT,                        -- AAAMMDD data de internação
    dt_saida            TEXT,                        -- AAAMMDD data de saída
    ano_cmpt            SMALLINT         NOT NULL,
    mes_cmpt            SMALLINT         NOT NULL CHECK (mes_cmpt BETWEEN 1 AND 12),
    dias_perm           SMALLINT,                    -- dias de permanência

    -- Diagnóstico principal (CID-10)
    diag_princ          TEXT,                        -- diagnóstico principal (CID-10, 4 chars)
    diag_secun          TEXT,                        -- diagnóstico secundário
    diag_cap            TEXT,                        -- capítulo do CID-10 (letra)

    -- Procedimento
    proc_rea            TEXT,                        -- procedimento realizado (código SIGTAP)
    proc_sol            TEXT,                        -- procedimento solicitado

    -- Localização de ocorrência (estabelecimento)
    cnes                TEXT,                        -- código CNES do estabelecimento
    municipio_ocor      TEXT,                        -- código IBGE município ocorrência
    uf_ocor             TEXT,                        -- UF de ocorrência (2 letras)

    -- Localização de residência
    municipio_res       TEXT,                        -- código IBGE município residência
    uf_res              TEXT,                        -- UF de residência (2 letras)

    -- Características do paciente
    sexo                TEXT,                        -- M/F/I
    idade               SMALLINT,                    -- idade em anos
    nasc                TEXT,                        -- AAAMMDD data de nascimento
    raca_cor            TEXT,                        -- 1=branca,2=preta,3=amarela,4=parda,5=indígena

    -- Desfecho
    morte               SMALLINT,                    -- 0=não, 1=óbito
    cobranca            TEXT,                        -- tipo de cobrança

    -- Valores financeiros
    val_tot             NUMERIC(12, 2),              -- valor total aprovado (R$)
    val_sh              NUMERIC(12, 2),              -- valor serviços hospitalares
    val_sp              NUMERIC(12, 2),              -- valor serviços profissionais
    val_sadt            NUMERIC(12, 2),              -- valor SADT
    val_uci             NUMERIC(12, 2),              -- valor UTI/UCI

    -- Gestão
    gestor_cod          TEXT,                        -- código gestor
    instru              TEXT,                        -- instrução de cobrança
    car_int             TEXT,                        -- caráter da internação (1=eletivo,2=urgência,…)

    -- Metadados de ingestão
    uf_arquivo          TEXT             NOT NULL,   -- UF do arquivo fonte (sigla)
    ingested_at         TIMESTAMPTZ      NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE sih_aih_raw IS
    'Dados brutos das Autorizações de Internação Hospitalar (DataSUS SIH/RD). '
    'Um registro por AIH. Ingeridos via ingestion/ingest_sih.py. '
    'Base para mart_internacoes após transformação dbt.';

COMMENT ON COLUMN sih_aih_raw.morte IS
    '0 = paciente recebeu alta; 1 = óbito hospitalar. '
    'Usado para calcular taxa de mortalidade hospitalar.';

COMMENT ON COLUMN sih_aih_raw.car_int IS
    '1=eletivo, 2=urgência, 3=acidente, 4=parto, 5=acidente de trabalho, '
    '6=acidente de trânsito. Indica urgência/eletividade da internação.';

-- ---------------------------------------------------------------------------
-- Índices operacionais
-- ---------------------------------------------------------------------------

CREATE INDEX IF NOT EXISTS idx_sih_aih_municipio_res
    ON sih_aih_raw (municipio_res);

CREATE INDEX IF NOT EXISTS idx_sih_aih_ano_mes
    ON sih_aih_raw (ano_cmpt, mes_cmpt);

CREATE INDEX IF NOT EXISTS idx_sih_aih_diag_princ
    ON sih_aih_raw (diag_princ);

CREATE INDEX IF NOT EXISTS idx_sih_aih_uf_res
    ON sih_aih_raw (uf_res);

CREATE INDEX IF NOT EXISTS idx_sih_aih_morte
    ON sih_aih_raw (morte)
    WHERE morte = 1;

CREATE INDEX IF NOT EXISTS idx_sih_aih_proc_rea
    ON sih_aih_raw (proc_rea);
