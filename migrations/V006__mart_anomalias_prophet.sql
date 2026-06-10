-- =============================================================================
-- V006 — mart_anomalias_prophet
-- Tabela de anomalias pré-computadas pelo modelo Prophet (ml/batch_scorer.py).
-- Alimentada pelo job assíncrono; consultada pelo endpoint /indicadores/anomalias
-- no modo method=prophet e method=auto.
-- =============================================================================

-- ---------------------------------------------------------------------------
-- Tabela principal
-- ---------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS mart_anomalias_prophet (
    id                   BIGSERIAL        PRIMARY KEY,

    -- Identificação
    municipio_cod        TEXT             NOT NULL,
    municipio_nome       TEXT,
    uf_sigla             TEXT             NOT NULL,

    -- Temporal (granularidade mensal)
    mes_competencia      TEXT             NOT NULL,   -- formato AAAAMM, ex: 202401
    ano                  INTEGER          NOT NULL CHECK (ano BETWEEN 2000 AND 2099),
    mes                  INTEGER          NOT NULL CHECK (mes BETWEEN 1 AND 12),

    -- Produção observada
    total_procedimentos  INTEGER,

    -- Previsão do modelo Prophet
    yhat                 DOUBLE PRECISION,            -- valor central previsto
    yhat_lower           DOUBLE PRECISION,            -- limite inferior IC 95%
    yhat_upper           DOUBLE PRECISION,            -- limite superior IC 95%

    -- Score de anomalia
    z_score              DOUBLE PRECISION,            -- Z-score residual: (y - yhat) / std(resid)
    tipo_anomalia        TEXT,                        -- 'alta' | 'baixa' | NULL (sem anomalia)
    pct_desvio           DOUBLE PRECISION,            -- % (y - yhat) / yhat * 100
    is_anomaly           BOOLEAN          NOT NULL DEFAULT FALSE,

    -- Metadados do modelo
    metodo               TEXT             NOT NULL DEFAULT 'prophet',  -- 'prophet' | 'zscore'
    n_pontos             INTEGER,                     -- tamanho da série histórica usada

    -- Controle de atualização
    scored_at            TIMESTAMPTZ      NOT NULL DEFAULT NOW(),

    -- Unicidade: um score por município × competência
    CONSTRAINT uq_anomalia_prophet UNIQUE (municipio_cod, mes_competencia)
);

COMMENT ON TABLE mart_anomalias_prophet IS
    'Anomalias de produção ambulatorial pré-computadas pelo modelo Prophet '
    '(ml/batch_scorer.py). Populada via batch job assíncrono; consultada '
    'pelo endpoint GET /indicadores/anomalias com method=prophet|auto.';

COMMENT ON COLUMN mart_anomalias_prophet.z_score IS
    'Z-score calculado sobre os resíduos do Prophet: (y - yhat) / std(y - yhat). '
    'Mais informativo que o Z-score puro pois remove tendência e sazonalidade.';

COMMENT ON COLUMN mart_anomalias_prophet.metodo IS
    'prophet = modelo Prophet com >= 24 pontos mensais; '
    'zscore  = fallback de Z-score simples quando série curta (< 24 meses).';

-- ---------------------------------------------------------------------------
-- Índices de suporte às queries frequentes
-- ---------------------------------------------------------------------------

-- Filtro por UF (query mais comum)
CREATE INDEX IF NOT EXISTS idx_anomalias_prophet_uf
    ON mart_anomalias_prophet (uf_sigla);

-- Filtro por competência (corte temporal)
CREATE INDEX IF NOT EXISTS idx_anomalias_prophet_competencia
    ON mart_anomalias_prophet (mes_competencia);

-- Dashboard de anomalias ativas por UF (IS_ANOMALY = TRUE é a query mais cara)
CREATE INDEX IF NOT EXISTS idx_anomalias_prophet_ativas
    ON mart_anomalias_prophet (is_anomaly, uf_sigla, mes_competencia)
    WHERE is_anomaly = TRUE;

-- Ordenação por magnitude do desvio (ORDER BY ABS(z_score) DESC)
CREATE INDEX IF NOT EXISTS idx_anomalias_prophet_zscore_abs
    ON mart_anomalias_prophet (ABS(z_score) DESC)
    WHERE is_anomaly = TRUE;

-- Lookup por município (para séries de um único município)
CREATE INDEX IF NOT EXISTS idx_anomalias_prophet_municipio
    ON mart_anomalias_prophet (municipio_cod, mes_competencia);
