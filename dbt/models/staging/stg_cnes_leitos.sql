{{ config(materialized='view', schema='staging') }}

WITH source AS (
    SELECT * FROM {{ source('raw', 'cnes_leitos') }}
),

cleaned AS (
    SELECT
        -- Identificação
        COALESCE(TRIM(cnes), '')::TEXT                AS cnes,
        ano_cmpt::SMALLINT                            AS ano_cmpt,
        mes_cmpt::SMALLINT                            AS mes_cmpt,
        UPPER(TRIM(uf))::CHAR(2)                     AS uf,

        -- Localização
        TRIM(municipio_cod)::TEXT                     AS municipio_cod,

        -- Tipo de leito
        TRIM(tp_leito)::TEXT                          AS tp_leito,
        TRIM(tp_leito_desc)::TEXT                     AS tp_leito_desc,

        -- Especialidade
        TRIM(cod_espec)::TEXT                         AS cod_espec,
        TRIM(cod_espec_desc)::TEXT                    AS cod_espec_desc,

        -- Quantidades
        COALESCE(qt_exist,   0)::SMALLINT             AS qt_exist,
        COALESCE(qt_sus,     0)::SMALLINT             AS qt_sus,
        COALESCE(qt_nao_sus, 0)::SMALLINT             AS qt_nao_sus,
        COALESCE(qt_contr,   0)::SMALLINT             AS qt_contr,

        -- Metadados
        UPPER(TRIM(uf_arquivo))::CHAR(2)             AS uf_arquivo,

        -- Colunas derivadas
        CASE tp_leito
            WHEN '01' THEN 'Cirúrgico'
            WHEN '02' THEN 'Clínico'
            WHEN '03' THEN 'Complementar'
            WHEN '04' THEN 'Obstétrico'
            WHEN '05' THEN 'Pediátrico'
            WHEN '07' THEN 'Reabilitação'
            ELSE 'Outro/Ignorado'
        END                                           AS tp_leito_grupo,

        -- Proporção SUS sobre total existente (NULL se qt_exist = 0)
        CASE
            WHEN COALESCE(qt_exist, 0) > 0
            THEN ROUND(qt_sus::NUMERIC / qt_exist, 4)
            ELSE NULL
        END                                           AS pct_sus

    FROM source
    WHERE cnes IS NOT NULL
      AND ano_cmpt IS NOT NULL
      AND ano_cmpt BETWEEN {{ var('ano_inicio') }} AND {{ var('ano_fim') }}
      AND uf IS NOT NULL
      AND municipio_cod IS NOT NULL
      AND LENGTH(TRIM(municipio_cod)) = 6
)

SELECT * FROM cleaned
