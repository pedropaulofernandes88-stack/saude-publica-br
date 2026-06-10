-- stg_ref_sigtap.sql
-- Padroniza tabela SIGTAP

{{ config(materialized='view', schema='staging') }}

SELECT
    LPAD(TRIM(proc_id), 10, '0')::VARCHAR(10)  AS proc_id,
    TRIM(nome_procedimento)                     AS nome_procedimento,
    LPAD(TRIM(complexidade), 2, '0')::VARCHAR(2) AS complexidade,
    CASE LPAD(TRIM(complexidade), 2, '0')
        WHEN '01' THEN 'Atenção Básica'
        WHEN '02' THEN 'Média Complexidade'
        WHEN '03' THEN 'Alta Complexidade'
        ELSE 'Não classificado'
    END                                          AS complexidade_label,
    TRIM(grupo_proc)::VARCHAR(2)                 AS grupo_proc,
    TRIM(nome_grupo)                             AS nome_grupo,
    TRIM(subgrupo_proc)::VARCHAR(4)              AS subgrupo_proc,
    COALESCE(valor_sp, 0)::NUMERIC(10,4)         AS valor_sp,
    COALESCE(valor_sh, 0)::NUMERIC(10,4)         AS valor_sh,
    competencia_ref
FROM {{ source('raw', 'ref_sigtap') }}
WHERE proc_id IS NOT NULL
