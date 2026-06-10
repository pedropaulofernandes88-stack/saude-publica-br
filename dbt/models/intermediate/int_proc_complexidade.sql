-- int_proc_complexidade.sql
-- Procedimentos com peso numérico de complexidade

{{ config(materialized='table', schema='intermediate') }}

SELECT
    proc_id,
    nome_procedimento,
    complexidade,
    complexidade_label,
    CASE complexidade
        WHEN '01' THEN {{ var('peso_ab') }}
        WHEN '02' THEN {{ var('peso_mc') }}
        WHEN '03' THEN {{ var('peso_ac') }}
        ELSE 0
    END::SMALLINT AS peso_complexidade,
    grupo_proc,
    nome_grupo,
    valor_sp,
    valor_sh
FROM {{ ref('stg_ref_sigtap') }}
