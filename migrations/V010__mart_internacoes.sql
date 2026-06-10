-- =============================================================================
-- V010 — mart_internacoes
-- Mart agregado de internações hospitalares por município × competência ×
-- diagnóstico principal. Populado pelo modelo dbt marts/mart_internacoes.sql
-- via transformação de sih_aih_raw → stg_sih_aih → int_internacoes_enriched.
-- Consultado pelo endpoint GET /internacoes/series e /internacoes/ranking.
-- =============================================================================

CREATE TABLE IF NOT EXISTS mart_internacoes (
    id                          BIGSERIAL        PRIMARY KEY,

    -- Dimensão geográfica
    municipio_cod               TEXT             NOT NULL,
    municipio_nome              TEXT,
    uf_sigla                    TEXT             NOT NULL,
    regiao                      TEXT,

    -- Dimensão temporal (granularidade mensal)
    ano                         SMALLINT         NOT NULL CHECK (ano BETWEEN 2000 AND 2099),
    mes                         SMALLINT         NOT NULL CHECK (mes BETWEEN 1 AND 12),
    mes_competencia             TEXT             NOT NULL,   -- formato AAAAMM, ex: 202401

    -- Dimensão de diagnóstico (CID-10)
    diag_cap                    TEXT,                        -- capítulo (letra A–Z)
    diag_grupo                  TEXT,                        -- grupo CID-10 (3 chars, ex: J18)

    -- Dimensão demográfica
    sexo                        TEXT,                        -- M / F / I / TOTAL
    faixa_etaria                TEXT,                        -- 0-4 / 5-14 / 15-29 / 30-59 / 60+ / TOTAL

    -- Caráter de internação
    car_int_grupo               TEXT,                        -- ELETIVO / URGENCIA / PARTO / OUTROS / TOTAL

    -- Métricas de volume
    total_internacoes           INTEGER          NOT NULL DEFAULT 0,
    total_obitos_hosp           INTEGER          NOT NULL DEFAULT 0,  -- morte = 1

    -- Métricas de permanência (dias)
    media_dias_perm             NUMERIC(8, 2),
    mediana_dias_perm           NUMERIC(8, 2),
    total_dias_perm             INTEGER,

    -- Métricas financeiras (R$)
    valor_total                 NUMERIC(16, 2),
    valor_medio_aih             NUMERIC(12, 2),

    -- Taxas derivadas
    taxa_mortalidade_hosp       NUMERIC(10, 4),   -- óbitos / internações * 100
    taxa_internacao_100k        NUMERIC(10, 4),   -- internações / pop * 100000

    -- Controle dbt
    dbt_updated_at              TIMESTAMPTZ      NOT NULL DEFAULT NOW(),

    -- Unicidade
    CONSTRAINT uq_intern_municipio_comp_diag_sexo_faixa_car
        UNIQUE (municipio_cod, mes_competencia, diag_cap, sexo, faixa_etaria, car_int_grupo)
);

COMMENT ON TABLE mart_internacoes IS
    'Mart de internações hospitalares agregado por município/mês/diagnóstico/'
    'sexo/faixa-etária/caráter. Populado pelo pipeline dbt a partir de '
    'sih_aih_raw. Consultado pelos endpoints GET /internacoes/*.';

COMMENT ON COLUMN mart_internacoes.total_obitos_hosp IS
    'Óbitos ocorridos durante a internação (campo MORTE=1 na AIH). '
    'Diferente de óbitos do SIM — cobre apenas mortalidade hospitalar.';

COMMENT ON COLUMN mart_internacoes.taxa_mortalidade_hosp IS
    'total_obitos_hosp / total_internacoes * 100. '
    'Indica a letalidade hospitalar do diagnóstico/período.';

COMMENT ON COLUMN mart_internacoes.taxa_internacao_100k IS
    'Internações por 100.000 habitantes. '
    'Calculada com população IBGE estimada (tabela dim_populacao_ibge).';

-- ---------------------------------------------------------------------------
-- Índices de suporte às queries frequentes
-- ---------------------------------------------------------------------------

-- Série temporal de um município
CREATE INDEX IF NOT EXISTS idx_intern_municipio_comp
    ON mart_internacoes (municipio_cod, mes_competencia);

-- Filtragem por UF
CREATE INDEX IF NOT EXISTS idx_intern_uf_comp
    ON mart_internacoes (uf_sigla, mes_competencia);

-- Filtragem por capítulo CID-10
CREATE INDEX IF NOT EXISTS idx_intern_diag_cap
    ON mart_internacoes (diag_cap, mes_competencia);

-- Ranking por volume de internações
CREATE INDEX IF NOT EXISTS idx_intern_total
    ON mart_internacoes (total_internacoes DESC, mes_competencia);

-- Totais consolidados (linhas de agregação completa)
CREATE INDEX IF NOT EXISTS idx_intern_totais
    ON mart_internacoes (municipio_cod, mes_competencia)
    WHERE sexo = 'TOTAL' AND faixa_etaria = 'TOTAL' AND car_int_grupo = 'TOTAL';

-- Óbitos hospitalares (subconjunto crítico para alertas)
CREATE INDEX IF NOT EXISTS idx_intern_obitos_hosp
    ON mart_internacoes (total_obitos_hosp DESC, mes_competencia)
    WHERE total_obitos_hosp > 0;
