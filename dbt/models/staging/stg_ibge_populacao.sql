-- stg_ibge_populacao.sql
-- Padroniza estimativas populacionais IBGE

{{ config(materialized='view', schema='staging') }}

SELECT
    municipio_cod6::VARCHAR(6)          AS municipio_cod,
    UPPER(TRIM(uf_sigla))::VARCHAR(2)   AS uf_sigla,
    ano_referencia::SMALLINT            AS ano_referencia,
    populacao_estimada::INTEGER         AS populacao_estimada
FROM {{ source('raw', 'ref_ibge_populacao') }}
WHERE populacao_estimada > 0
  AND municipio_cod6 IS NOT NULL
