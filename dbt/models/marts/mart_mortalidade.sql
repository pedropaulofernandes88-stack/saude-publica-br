{{ config(
    materialized='table',
    schema='marts',
    indexes=[
        {'columns': ['municipio_cod', 'mes_competencia']},
        {'columns': ['uf_sigla', 'ano_obito']},
        {'columns': ['causabas_cap', 'causabas_grupo']},
        {'columns': ['sexo', 'faixa_etaria']},
    ],
    unique_key=['municipio_cod', 'mes_competencia', 'causabas_cap', 'sexo', 'faixa_etaria']
) }}

/*
  mart_mortalidade — Mortalidade agregada por município / competência / causa / demográfico

  Fonte: int_obitos_enriched
  Granularidade: (municipio_cod, mes_competencia, causabas_cap, sexo, faixa_etaria)

  Contagens expostas:
    • total_obitos         — todos os óbitos
    • obitos_fetais        — TIPOBITO = '1'
    • obitos_naofetais     — TIPOBITO = '2'
    • obitos_hospital      — local do óbito = hospital
    • obitos_domicilio     — local do óbito = domicílio
    • obitos_outros_local  — demais locais
    • taxa_mortalidade_bruta — óbitos / populacao * 1000 (por mil hab)

  UNION: linhas com sexo = 'TOTAL' e faixa_etaria = 'TOTAL' para subtotais de API.
*/

WITH base AS (
    SELECT * FROM {{ ref('int_obitos_enriched') }}
),

-- ── Agregação completa ────────────────────────────────────────────────────
agregado AS (

    -- Detalhado: sexo x faixa_etaria
    SELECT
        municipio_cod,
        municipio_nome,
        uf_sigla,
        regiao,
        ano_obito,
        mes_obito,
        mes_competencia,
        causabas_cap,
        causabas_grupo,
        sexo,
        faixa_etaria,

        COUNT(*)                                              AS total_obitos,
        COUNT(*) FILTER (WHERE is_fetal)                      AS obitos_fetais,
        COUNT(*) FILTER (WHERE NOT is_fetal)                  AS obitos_naofetais,
        COUNT(*) FILTER (WHERE lococor = '2')                 AS obitos_hospital,
        COUNT(*) FILTER (WHERE lococor = '1')                 AS obitos_domicilio,
        COUNT(*) FILTER (WHERE lococor NOT IN ('1', '2')
                            OR lococor IS NULL)               AS obitos_outros_local,
        MAX(populacao)                                        AS populacao

    FROM base
    GROUP BY
        municipio_cod, municipio_nome, uf_sigla, regiao,
        ano_obito, mes_obito, mes_competencia,
        causabas_cap, causabas_grupo,
        sexo, faixa_etaria

    UNION ALL

    -- Subtotal por causa: sexo = 'TOTAL', faixa_etaria detalhada
    SELECT
        municipio_cod,
        municipio_nome,
        uf_sigla,
        regiao,
        ano_obito,
        mes_obito,
        mes_competencia,
        causabas_cap,
        causabas_grupo,
        'TOTAL'                                               AS sexo,
        faixa_etaria,

        COUNT(*)                                              AS total_obitos,
        COUNT(*) FILTER (WHERE is_fetal)                      AS obitos_fetais,
        COUNT(*) FILTER (WHERE NOT is_fetal)                  AS obitos_naofetais,
        COUNT(*) FILTER (WHERE lococor = '2')                 AS obitos_hospital,
        COUNT(*) FILTER (WHERE lococor = '1')                 AS obitos_domicilio,
        COUNT(*) FILTER (WHERE lococor NOT IN ('1', '2')
                            OR lococor IS NULL)               AS obitos_outros_local,
        MAX(populacao)                                        AS populacao

    FROM base
    GROUP BY
        municipio_cod, municipio_nome, uf_sigla, regiao,
        ano_obito, mes_obito, mes_competencia,
        causabas_cap, causabas_grupo, faixa_etaria

    UNION ALL

    -- Subtotal por causa: faixa_etaria = 'TOTAL', sexo detalhado
    SELECT
        municipio_cod,
        municipio_nome,
        uf_sigla,
        regiao,
        ano_obito,
        mes_obito,
        mes_competencia,
        causabas_cap,
        causabas_grupo,
        sexo,
        'TOTAL'                                               AS faixa_etaria,

        COUNT(*)                                              AS total_obitos,
        COUNT(*) FILTER (WHERE is_fetal)                      AS obitos_fetais,
        COUNT(*) FILTER (WHERE NOT is_fetal)                  AS obitos_naofetais,
        COUNT(*) FILTER (WHERE lococor = '2')                 AS obitos_hospital,
        COUNT(*) FILTER (WHERE lococor = '1')                 AS obitos_domicilio,
        COUNT(*) FILTER (WHERE lococor NOT IN ('1', '2')
                            OR lococor IS NULL)               AS obitos_outros_local,
        MAX(populacao)                                        AS populacao

    FROM base
    GROUP BY
        municipio_cod, municipio_nome, uf_sigla, regiao,
        ano_obito, mes_obito, mes_competencia,
        causabas_cap, causabas_grupo, sexo

    UNION ALL

    -- Grand total: sexo = 'TOTAL', faixa_etaria = 'TOTAL'
    SELECT
        municipio_cod,
        municipio_nome,
        uf_sigla,
        regiao,
        ano_obito,
        mes_obito,
        mes_competencia,
        causabas_cap,
        causabas_grupo,
        'TOTAL'                                               AS sexo,
        'TOTAL'                                               AS faixa_etaria,

        COUNT(*)                                              AS total_obitos,
        COUNT(*) FILTER (WHERE is_fetal)                      AS obitos_fetais,
        COUNT(*) FILTER (WHERE NOT is_fetal)                  AS obitos_naofetais,
        COUNT(*) FILTER (WHERE lococor = '2')                 AS obitos_hospital,
        COUNT(*) FILTER (WHERE lococor = '1')                 AS obitos_domicilio,
        COUNT(*) FILTER (WHERE lococor NOT IN ('1', '2')
                            OR lococor IS NULL)               AS obitos_outros_local,
        MAX(populacao)                                        AS populacao

    FROM base
    GROUP BY
        municipio_cod, municipio_nome, uf_sigla, regiao,
        ano_obito, mes_obito, mes_competencia,
        causabas_cap, causabas_grupo
),

final AS (
    SELECT
        municipio_cod,
        municipio_nome,
        uf_sigla,
        regiao,
        ano_obito,
        mes_obito,
        mes_competencia,
        causabas_cap,
        causabas_grupo,
        sexo,
        faixa_etaria,
        total_obitos,
        obitos_fetais,
        obitos_naofetais,
        obitos_hospital,
        obitos_domicilio,
        obitos_outros_local,
        populacao,

        -- Taxa de mortalidade bruta por 1.000 habitantes
        CASE
            WHEN COALESCE(populacao, 0) > 0
            THEN ROUND(
                (total_obitos::NUMERIC / populacao) * 1000,
                4
            )
            ELSE NULL
        END                                                   AS taxa_mortalidade_bruta,

        -- Proporção óbitos hospitalares
        CASE
            WHEN total_obitos > 0
            THEN ROUND(obitos_hospital::NUMERIC / total_obitos * 100, 2)
            ELSE NULL
        END                                                   AS pct_obitos_hospital,

        CURRENT_TIMESTAMP                                     AS dbt_updated_at

    FROM agregado
)

SELECT * FROM final
