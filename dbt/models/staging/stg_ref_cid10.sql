-- stg_ref_cid10.sql
-- Padroniza tabela CID-10

{{ config(materialized='view', schema='staging') }}

SELECT
    UPPER(TRIM(codigo_cid))::VARCHAR(4)  AS codigo_cid,
    TRIM(descricao_cid)                  AS descricao_cid,
    UPPER(TRIM(grupo_cid))               AS grupo_cid,
    TRIM(nome_grupo_cid)                 AS nome_grupo_cid,
    UPPER(TRIM(capitulo_cid))            AS capitulo_cid,
    TRIM(nome_capitulo_cid)              AS nome_capitulo_cid
FROM {{ source('raw', 'ref_cid10') }}
WHERE codigo_cid IS NOT NULL
