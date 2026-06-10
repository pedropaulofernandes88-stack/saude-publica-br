{{
    config(
        materialized='table',
        schema='marts',
        unique_key=['agravo', 'ano_notif', 'mes_notif', 'uf_notif', 'municipio_notif', 'faixa_etaria', 'cs_sexo'],
        indexes=[
            {'columns': ['agravo', 'ano_notif', 'mes_notif']},
            {'columns': ['uf_notif', 'municipio_notif']},
            {'columns': ['faixa_etaria']},
        ]
    )
}}

WITH base AS (
    SELECT
        agravo,
        agravo_label,
        ano_notif,
        mes_notif,
        uf_notif,
        municipio_notif,
        faixa_etaria,
        cs_sexo,
        classi_fin,
        evolucao,
        is_obito,
        febre,
        mialgia,
        cefaleia,
        exantema,
        vomito,
        artralgia,
        artrite,
        sorotipo,
        resul_ns1,
        resul_soro,
        resul_pcr
    FROM {{ ref('stg_sinan_notificacoes') }}
),

-- -----------------------------------------------------------------------
-- Agregação principal: agravo / período / UF / município / faixa / sexo
-- -----------------------------------------------------------------------

detalhado AS (
    SELECT
        agravo,
        agravo_label,
        ano_notif,
        mes_notif,
        uf_notif,
        municipio_notif,
        faixa_etaria,
        cs_sexo,
        COUNT(*)                                          AS total_notificacoes,
        SUM(CASE WHEN is_obito THEN 1 ELSE 0 END)        AS total_obitos,
        SUM(CASE WHEN classi_fin = 1 THEN 1 ELSE 0 END)  AS casos_confirmados,
        SUM(CASE WHEN classi_fin = 2 THEN 1 ELSE 0 END)  AS casos_alarme,
        SUM(CASE WHEN classi_fin = 3 THEN 1 ELSE 0 END)  AS casos_graves,
        -- Manifestações clínicas (dengue/chikungunya)
        SUM(CASE WHEN febre    = 1 THEN 1 ELSE 0 END)    AS c_febre,
        SUM(CASE WHEN mialgia  = 1 THEN 1 ELSE 0 END)    AS c_mialgia,
        SUM(CASE WHEN cefaleia = 1 THEN 1 ELSE 0 END)    AS c_cefaleia,
        SUM(CASE WHEN exantema = 1 THEN 1 ELSE 0 END)    AS c_exantema,
        SUM(CASE WHEN vomito   = 1 THEN 1 ELSE 0 END)    AS c_vomito,
        SUM(CASE WHEN artralgia= 1 THEN 1 ELSE 0 END)    AS c_artralgia,
        SUM(CASE WHEN artrite  = 1 THEN 1 ELSE 0 END)    AS c_artrite,
        -- Resultados laboratoriais (dengue)
        SUM(CASE WHEN resul_ns1  = 1 THEN 1 ELSE 0 END)  AS lab_ns1_pos,
        SUM(CASE WHEN resul_soro = 1 THEN 1 ELSE 0 END)  AS lab_soro_pos,
        SUM(CASE WHEN resul_pcr  = 1 THEN 1 ELSE 0 END)  AS lab_pcr_pos,
        -- Sorotipo predominante (dengue)
        MODE() WITHIN GROUP (ORDER BY sorotipo)           AS sorotipo_predominante
    FROM base
    GROUP BY 1, 2, 3, 4, 5, 6, 7, 8
),

-- -----------------------------------------------------------------------
-- Subtotal por sexo (faixa_etaria = 'Total')
-- -----------------------------------------------------------------------

subtotal_sexo AS (
    SELECT
        agravo,
        agravo_label,
        ano_notif,
        mes_notif,
        uf_notif,
        municipio_notif,
        'Total'     AS faixa_etaria,
        cs_sexo,
        SUM(total_notificacoes)    AS total_notificacoes,
        SUM(total_obitos)          AS total_obitos,
        SUM(casos_confirmados)     AS casos_confirmados,
        SUM(casos_alarme)          AS casos_alarme,
        SUM(casos_graves)          AS casos_graves,
        SUM(c_febre)               AS c_febre,
        SUM(c_mialgia)             AS c_mialgia,
        SUM(c_cefaleia)            AS c_cefaleia,
        SUM(c_exantema)            AS c_exantema,
        SUM(c_vomito)              AS c_vomito,
        SUM(c_artralgia)           AS c_artralgia,
        SUM(c_artrite)             AS c_artrite,
        SUM(lab_ns1_pos)           AS lab_ns1_pos,
        SUM(lab_soro_pos)          AS lab_soro_pos,
        SUM(lab_pcr_pos)           AS lab_pcr_pos,
        NULL::SMALLINT             AS sorotipo_predominante
    FROM detalhado
    GROUP BY 1, 2, 3, 4, 5, 6, 8
),

-- -----------------------------------------------------------------------
-- Subtotal por faixa etária (cs_sexo = 'T')
-- -----------------------------------------------------------------------

subtotal_faixa AS (
    SELECT
        agravo,
        agravo_label,
        ano_notif,
        mes_notif,
        uf_notif,
        municipio_notif,
        faixa_etaria,
        'T'         AS cs_sexo,
        SUM(total_notificacoes)    AS total_notificacoes,
        SUM(total_obitos)          AS total_obitos,
        SUM(casos_confirmados)     AS casos_confirmados,
        SUM(casos_alarme)          AS casos_alarme,
        SUM(casos_graves)          AS casos_graves,
        SUM(c_febre)               AS c_febre,
        SUM(c_mialgia)             AS c_mialgia,
        SUM(c_cefaleia)            AS c_cefaleia,
        SUM(c_exantema)            AS c_exantema,
        SUM(c_vomito)              AS c_vomito,
        SUM(c_artralgia)           AS c_artralgia,
        SUM(c_artrite)             AS c_artrite,
        SUM(lab_ns1_pos)           AS lab_ns1_pos,
        SUM(lab_soro_pos)          AS lab_soro_pos,
        SUM(lab_pcr_pos)           AS lab_pcr_pos,
        NULL::SMALLINT             AS sorotipo_predominante
    FROM detalhado
    GROUP BY 1, 2, 3, 4, 5, 6, 7
),

-- -----------------------------------------------------------------------
-- Grand total: faixa = 'Total', sexo = 'T'
-- -----------------------------------------------------------------------

grand_total AS (
    SELECT
        agravo,
        agravo_label,
        ano_notif,
        mes_notif,
        uf_notif,
        municipio_notif,
        'Total'     AS faixa_etaria,
        'T'         AS cs_sexo,
        SUM(total_notificacoes)    AS total_notificacoes,
        SUM(total_obitos)          AS total_obitos,
        SUM(casos_confirmados)     AS casos_confirmados,
        SUM(casos_alarme)          AS casos_alarme,
        SUM(casos_graves)          AS casos_graves,
        SUM(c_febre)               AS c_febre,
        SUM(c_mialgia)             AS c_mialgia,
        SUM(c_cefaleia)            AS c_cefaleia,
        SUM(c_exantema)            AS c_exantema,
        SUM(c_vomito)              AS c_vomito,
        SUM(c_artralgia)           AS c_artralgia,
        SUM(c_artrite)             AS c_artrite,
        SUM(lab_ns1_pos)           AS lab_ns1_pos,
        SUM(lab_soro_pos)          AS lab_soro_pos,
        SUM(lab_pcr_pos)           AS lab_pcr_pos,
        NULL::SMALLINT             AS sorotipo_predominante
    FROM detalhado
    GROUP BY 1, 2, 3, 4, 5, 6
),

uniao AS (
    SELECT * FROM detalhado
    UNION ALL
    SELECT * FROM subtotal_sexo
    UNION ALL
    SELECT * FROM subtotal_faixa
    UNION ALL
    SELECT * FROM grand_total
)

SELECT
    *,
    -- Taxa de letalidade (óbitos / notificações × 100)
    CASE
        WHEN total_notificacoes > 0
        THEN ROUND(total_obitos::NUMERIC / total_notificacoes * 100, 4)
        ELSE NULL
    END AS taxa_letalidade_pct,

    -- Proporção confirmados
    CASE
        WHEN total_notificacoes > 0
        THEN ROUND(casos_confirmados::NUMERIC / total_notificacoes * 100, 2)
        ELSE NULL
    END AS pct_confirmados

FROM uniao
