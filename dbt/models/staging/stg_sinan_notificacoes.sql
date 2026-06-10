{{ config(materialized='view', schema='staging') }}

WITH source AS (
    SELECT * FROM {{ source('raw', 'sinan_notificacoes') }}
),

cleaned AS (
    SELECT
        -- Identificação
        COALESCE(TRIM(nu_notific), '')::TEXT          AS nu_notific,
        UPPER(TRIM(agravo))::TEXT                     AS agravo,

        -- Temporal
        TRIM(dt_notific)::TEXT                        AS dt_notific,
        ano_notif::SMALLINT                           AS ano_notif,
        mes_notif::SMALLINT                           AS mes_notif,

        -- Localização de notificação
        UPPER(TRIM(uf_notif))::CHAR(2)               AS uf_notif,
        TRIM(municipio_notif)::TEXT                   AS municipio_notif,
        TRIM(cnes_unidade)::TEXT                      AS cnes_unidade,

        -- Localização de residência
        UPPER(TRIM(uf_res))::CHAR(2)                 AS uf_res,
        TRIM(municipio_res)::TEXT                     AS municipio_res,

        -- Dados do paciente
        TRIM(dt_sin_pri)::TEXT                        AS dt_sin_pri,
        TRIM(dt_nasc)::TEXT                           AS dt_nasc,
        nu_idade_n::SMALLINT                          AS nu_idade_n,
        idade_anos::SMALLINT                          AS idade_anos,
        UPPER(TRIM(cs_sexo))::CHAR(1)                AS cs_sexo,
        cs_raca::SMALLINT                             AS cs_raca,
        cs_gestant::SMALLINT                          AS cs_gestant,

        -- Classificação e desfecho
        classi_fin::SMALLINT                          AS classi_fin,
        criterio::SMALLINT                            AS criterio,
        evolucao::SMALLINT                            AS evolucao,
        TRIM(dt_obito)::TEXT                          AS dt_obito,
        TRIM(dt_encerra)::TEXT                        AS dt_encerra,

        -- Manifestações clínicas
        febre::SMALLINT                               AS febre,
        mialgia::SMALLINT                             AS mialgia,
        cefaleia::SMALLINT                            AS cefaleia,
        exantema::SMALLINT                            AS exantema,
        vomito::SMALLINT                              AS vomito,
        artralgia::SMALLINT                           AS artralgia,
        artrite::SMALLINT                             AS artrite,

        -- Exames laboratoriais
        sorotipo::SMALLINT                            AS sorotipo,
        resul_ns1::SMALLINT                           AS resul_ns1,
        resul_prnt::SMALLINT                          AS resul_prnt,
        resul_soro::SMALLINT                          AS resul_soro,
        resul_pcr::SMALLINT                           AS resul_pcr,
        TRIM(dt_soro)::TEXT                           AS dt_soro,
        TRIM(dt_pcr)::TEXT                            AS dt_pcr,

        -- Metadados
        UPPER(TRIM(uf_arquivo))::CHAR(2)             AS uf_arquivo,

        -- Colunas derivadas
        CASE agravo
            WHEN 'DENG' THEN 'dengue'
            WHEN 'CHIK' THEN 'chikungunya'
            WHEN 'ZIKA' THEN 'zika'
            ELSE agravo
        END                                           AS agravo_label,

        CASE
            WHEN idade_anos BETWEEN 0  AND 4  THEN '0-4'
            WHEN idade_anos BETWEEN 5  AND 14 THEN '5-14'
            WHEN idade_anos BETWEEN 15 AND 29 THEN '15-29'
            WHEN idade_anos BETWEEN 30 AND 59 THEN '30-59'
            WHEN idade_anos >= 60             THEN '60+'
            ELSE 'ND'
        END                                           AS faixa_etaria,

        (evolucao IN (2, 3))::BOOLEAN                AS is_obito

    FROM source
    WHERE agravo IS NOT NULL
      AND uf_notif IS NOT NULL
      AND ano_notif IS NOT NULL
      AND ano_notif BETWEEN {{ var('ano_inicio') }} AND {{ var('ano_fim') }}
)

SELECT * FROM cleaned
