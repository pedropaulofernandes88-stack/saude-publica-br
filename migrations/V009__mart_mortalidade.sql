-- =============================================================================
-- V009 — mart_mortalidade
-- Mart agregado de mortalidade por município × competência × causa básica.
-- Populado pelo modelo dbt marts/mart_mortalidade.sql via transformação de
-- sim_do_raw → stg_sim_obitos → int_obitos_enriched → mart_mortalidade.
-- Consultado pelo endpoint GET /mortalidade/series e /mortalidade/ranking.
-- =============================================================================

CREATE TABLE IF NOT EXISTS mart_mortalidade (
    id                      BIGSERIAL        PRIMARY KEY,

    -- Dimensão geográfica
    municipio_cod           TEXT             NOT NULL,
    municipio_nome          TEXT,
    uf_sigla                TEXT             NOT NULL,
    regiao                  TEXT,

    -- Dimensão temporal (granularidade mensal)
    ano                     SMALLINT         NOT NULL CHECK (ano BETWEEN 2000 AND 2099),
    mes                     SMALLINT         NOT NULL CHECK (mes BETWEEN 1 AND 12),
    mes_competencia         TEXT             NOT NULL,   -- formato AAAAMM, ex: 202401

    -- Dimensão de causa (CID-10)
    causabas_cap            TEXT,                        -- capítulo (letra A–Z)
    causabas_grupo          TEXT,                        -- grupo CID-10 (3 chars, ex: J18)

    -- Dimensão demográfica (agregações)
    sexo                    TEXT,                        -- M / F / I / TOTAL
    faixa_etaria            TEXT,                        -- 0-4 / 5-14 / 15-29 / 30-59 / 60+ / TOTAL

    -- Métricas de óbitos
    total_obitos            INTEGER          NOT NULL DEFAULT 0,
    obitos_fet              INTEGER          NOT NULL DEFAULT 0,   -- óbitos fetais
    obitos_naofet           INTEGER          NOT NULL DEFAULT 0,   -- óbitos não-fetais

    -- Métricas de local de ocorrência
    obitos_hospital         INTEGER          NOT NULL DEFAULT 0,   -- lococor = 1
    obitos_domicilio        INTEGER          NOT NULL DEFAULT 0,   -- lococor = 2
    obitos_outros           INTEGER          NOT NULL DEFAULT 0,

    -- Taxa de mortalidade bruta (por 100 mil hab.)
    -- Calculada pelo dbt usando população IBGE estimada
    taxa_mortalidade_bruta  NUMERIC(10, 4),

    -- Controle dbt
    dbt_updated_at          TIMESTAMPTZ      NOT NULL DEFAULT NOW(),

    -- Unicidade: uma linha por município × competência × causa × sexo × faixa
    CONSTRAINT uq_mort_municipio_comp_causa_sexo_faixa
        UNIQUE (municipio_cod, mes_competencia, causabas_cap, sexo, faixa_etaria)
);

COMMENT ON TABLE mart_mortalidade IS
    'Mart de mortalidade agregado por município/mês/causa/sexo/faixa-etária. '
    'Populado pelo pipeline dbt a partir de sim_do_raw. '
    'Consultado pelos endpoints GET /mortalidade/*.';

COMMENT ON COLUMN mart_mortalidade.causabas_cap IS
    'Capítulo do CID-10 da causa básica do óbito. '
    'Ex: I=Doenças cardiovasculares, J=Doenças respiratórias, C=Neoplasias, '
    'NULL=todos os capítulos (linha de total).';

COMMENT ON COLUMN mart_mortalidade.taxa_mortalidade_bruta IS
    'Óbitos por 100.000 habitantes. '
    'Calculada com população IBGE estimada (tabela dim_populacao_ibge).';

-- ---------------------------------------------------------------------------
-- Índices de suporte às queries frequentes
-- ---------------------------------------------------------------------------

-- Série temporal de um município
CREATE INDEX IF NOT EXISTS idx_mort_municipio_comp
    ON mart_mortalidade (municipio_cod, mes_competencia);

-- Filtragem por UF (query mais comum no painel)
CREATE INDEX IF NOT EXISTS idx_mort_uf_comp
    ON mart_mortalidade (uf_sigla, mes_competencia);

-- Filtragem por capítulo CID-10
CREATE INDEX IF NOT EXISTS idx_mort_causa_cap
    ON mart_mortalidade (causabas_cap, mes_competencia);

-- Ranking de municípios por volume de óbitos
CREATE INDEX IF NOT EXISTS idx_mort_total_obitos
    ON mart_mortalidade (total_obitos DESC, mes_competencia);

-- Totais consolidados (sexo=TOTAL e faixa=TOTAL)
CREATE INDEX IF NOT EXISTS idx_mort_totais
    ON mart_mortalidade (municipio_cod, mes_competencia)
    WHERE sexo = 'TOTAL' AND faixa_etaria = 'TOTAL';
