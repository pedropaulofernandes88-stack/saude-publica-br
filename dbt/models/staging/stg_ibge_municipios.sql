-- stg_ibge_municipios.sql
-- Padroniza tabela de municípios IBGE

{{ config(materialized='view', schema='staging') }}

SELECT
    municipio_cod6::VARCHAR(6)            AS municipio_cod,
    INITCAP(TRIM(nome_municipio))         AS nome_municipio,
    UPPER(TRIM(uf_sigla))::VARCHAR(2)     AS uf_sigla,
    TRIM(uf_nome)                         AS uf_nome,
    TRIM(regiao)                          AS regiao,
    COALESCE(capital, FALSE)              AS capital,
    latitude::NUMERIC(9,6)               AS latitude,
    longitude::NUMERIC(9,6)              AS longitude
FROM {{ source('raw', 'ref_ibge_municipios') }}
WHERE municipio_cod6 IS NOT NULL
