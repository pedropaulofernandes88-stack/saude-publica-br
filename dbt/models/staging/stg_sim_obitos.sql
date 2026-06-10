-- stg_sim_obitos.sql
-- Padroniza e limpa dados brutos do SIM/DO (Declarações de Óbito).
-- Fonte: sim_do_raw (ingerida por ingestion/ingest_sim.py via PySUS).
-- Materialização: view — sem custo de storage, recalculada sob demanda.

{{ config(materialized='view', schema='staging') }}

WITH source AS (
    SELECT * FROM {{ source('raw', 'sim_do_raw') }}
),

cleaned AS (
    SELECT
        -- ── Identificação ──────────────────────────────────────────────────
        COALESCE(TRIM(numerodo), '')::TEXT          AS numerodo,
        UPPER(TRIM(tipobito))::VARCHAR(1)           AS tipobito,   -- 1=fetal, 2=não-fetal

        -- ── Temporal ───────────────────────────────────────────────────────
        TRIM(dtobito)::VARCHAR(8)                   AS dtobito,    -- DDMMAAAA
        ano_obito::SMALLINT                         AS ano_obito,
        -- Alguns registros chegam sem mês (óbitos antigos); padrão = 1
        COALESCE(NULLIF(mes_obito, 0), 1)::SMALLINT AS mes_obito,
        -- Chave de competência compatível com outros marts
        LPAD(ano_obito::TEXT, 4, '0')
            || LPAD(COALESCE(NULLIF(mes_obito,0),1)::TEXT, 2, '0')
            AS mes_competencia,                     -- AAAAMM

        -- ── Causa básica (CID-10) ──────────────────────────────────────────
        UPPER(TRIM(causabas))::VARCHAR(5)           AS causabas,
        UPPER(TRIM(causabas_cap))::VARCHAR(5)       AS causabas_cap,

        -- ── Localização de ocorrência ─────────────────────────────────────
        LPAD(TRIM(municipio_ocor), 6, '0')::VARCHAR(6)  AS municipio_ocor,
        UPPER(TRIM(uf_ocor))::VARCHAR(2)                AS uf_ocor,

        -- ── Localização de residência ─────────────────────────────────────
        LPAD(TRIM(municipio_res), 6, '0')::VARCHAR(6)   AS municipio_res,
        UPPER(TRIM(uf_res))::VARCHAR(2)                 AS uf_res,

        -- ── Características do falecido ───────────────────────────────────
        UPPER(TRIM(sexo))::VARCHAR(1)               AS sexo,       -- M/F/I
        COALESCE(idade_valor, 0)::SMALLINT          AS idade_valor,
        UPPER(TRIM(idade_unidade))::VARCHAR(1)      AS idade_unidade, -- A/M/D/H

        -- Faixa etária derivada (em anos) — usa idade_unidade para normalizar
        CASE
            WHEN idade_unidade = 'A' AND idade_valor BETWEEN 0  AND 4   THEN '0-4'
            WHEN idade_unidade = 'A' AND idade_valor BETWEEN 5  AND 14  THEN '5-14'
            WHEN idade_unidade = 'A' AND idade_valor BETWEEN 15 AND 29  THEN '15-29'
            WHEN idade_unidade = 'A' AND idade_valor BETWEEN 30 AND 59  THEN '30-59'
            WHEN idade_unidade = 'A' AND idade_valor >= 60               THEN '60+'
            WHEN idade_unidade IN ('M', 'D', 'H')                        THEN '0-4'  -- < 1 ano
            ELSE 'ND'
        END AS faixa_etaria,

        UPPER(TRIM(racacor))::VARCHAR(1)            AS racacor,
        UPPER(TRIM(escolaridade))::VARCHAR(1)       AS escolaridade,
        UPPER(TRIM(estadociv))::VARCHAR(1)          AS estadociv,

        -- ── Local e tipo de óbito ──────────────────────────────────────────
        UPPER(TRIM(lococor))::VARCHAR(1)            AS lococor,
        -- 1=hospital, 2=outro estab saúde, 3=domicílio, 4=via pública, 5=outros
        CASE TRIM(lococor)
            WHEN '1' THEN 'hospital'
            WHEN '2' THEN 'outro_estabelecimento'
            WHEN '3' THEN 'domicilio'
            WHEN '4' THEN 'via_publica'
            ELSE          'outros'
        END AS local_obito_label,

        UPPER(TRIM(assistmed))::VARCHAR(1)          AS assistmed,

        -- ── Flags de tipo ────────────────────────────────────────────────
        (tipobito = '1')::BOOLEAN                   AS is_fetal,

        -- ── Metadados ────────────────────────────────────────────────────
        UPPER(TRIM(uf_arquivo))::VARCHAR(2)         AS uf_arquivo,
        ingested_at

    FROM source

    -- Filtros de qualidade mínimos
    WHERE ano_obito IS NOT NULL
      AND ano_obito BETWEEN {{ var('ano_inicio') }} AND {{ var('ano_fim') }}
      AND municipio_res IS NOT NULL
      AND LENGTH(TRIM(municipio_res)) = 6
      AND municipio_res <> '000000'
      AND causabas IS NOT NULL
      AND LENGTH(TRIM(causabas)) >= 3
)

SELECT * FROM cleaned
