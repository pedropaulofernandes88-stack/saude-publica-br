-- =============================================================================
-- V007 — sim_do_raw
-- Tabela de recepção bruta das Declarações de Óbito (SIM/DO) do DataSUS.
-- Alimentada pelo job ingestion/ingest_sim.py via COPY (bulk load).
-- Granularidade: um registro por óbito individual.
-- =============================================================================

CREATE TABLE IF NOT EXISTS sim_do_raw (
    id                  BIGSERIAL        PRIMARY KEY,

    -- Identificação do óbito
    numerodo            TEXT,                        -- número sequencial da DO
    tipobito            TEXT,                        -- 1=fetal, 2=não-fetal

    -- Temporal
    dtobito             TEXT,                        -- DDMMAAAA (data do óbito)
    ano_obito           SMALLINT         NOT NULL,
    mes_obito           SMALLINT         NOT NULL CHECK (mes_obito BETWEEN 1 AND 12),

    -- Causa básica (CID-10)
    causabas            TEXT,                        -- causa básica (CID-10, 4 chars)
    causabas_cap        TEXT,                        -- capítulo do CID-10 (letra)

    -- Localização de ocorrência
    municipio_ocor      TEXT,                        -- código IBGE município ocorrência
    uf_ocor             TEXT,                        -- UF de ocorrência (2 letras)

    -- Localização de residência
    municipio_res       TEXT,                        -- código IBGE município residência
    uf_res              TEXT,                        -- UF de residência (2 letras)

    -- Características do falecido
    sexo                TEXT,                        -- M/F/I
    idade_valor         SMALLINT,                    -- valor numérico da idade
    idade_unidade       TEXT,                        -- A=anos, M=meses, D=dias, H=horas
    racacor             TEXT,                        -- 1=branca,2=preta,3=amarela,4=parda,5=indígena
    escolaridade        TEXT,                        -- grau de instrução
    estadociv           TEXT,                        -- estado civil

    -- Local e tipo de óbito
    lococor             TEXT,                        -- local de ocorrência (1=hospital)
    assistmed           TEXT,                        -- recebeu assistência médica (S/N)

    -- Metadados de ingestão
    uf_arquivo          TEXT             NOT NULL,   -- UF do arquivo fonte (sigla)
    ingested_at         TIMESTAMPTZ      NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE sim_do_raw IS
    'Dados brutos das Declarações de Óbito (DataSUS SIM). '
    'Um registro por óbito. Ingeridos via ingestion/ingest_sim.py. '
    'Base para mart_mortalidade após transformação dbt.';

-- ---------------------------------------------------------------------------
-- Índices operacionais
-- ---------------------------------------------------------------------------

CREATE INDEX IF NOT EXISTS idx_sim_do_municipio_res
    ON sim_do_raw (municipio_res);

CREATE INDEX IF NOT EXISTS idx_sim_do_ano_mes
    ON sim_do_raw (ano_obito, mes_obito);

CREATE INDEX IF NOT EXISTS idx_sim_do_causabas
    ON sim_do_raw (causabas);

CREATE INDEX IF NOT EXISTS idx_sim_do_uf_res
    ON sim_do_raw (uf_res);
