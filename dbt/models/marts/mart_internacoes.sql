{{ config(
    materialized='table',
    schema='marts',
    indexes=[
        {'columns': ['municipio_cod', 'mes_competencia']},
        {'columns': ['uf_sigla', 'ano_cmpt']},
        {'columns': ['diag_cap', 'diag_grupo']},
        {'columns': ['car_int_grupo']},
        {'columns': ['sexo', 'faixa_etaria']},
    ],
    unique_key=['municipio_cod', 'mes_competencia', 'diag_cap', 'sexo', 'faixa_etaria', 'car_int_grupo']
) }}

/*
  mart_internacoes — Internações hospitalares agregadas por município / competência /
                     diagnóstico / caráter de internação / demográfico

  Fonte: int_internacoes_enriched
  Granularidade: (municipio_cod, mes_competencia, diag_cap, sexo, faixa_etaria, car_int_grupo)

  Métricas expostas:
    • total_internacoes       — AIHs no período
    • total_obitos_internados — internações com desfecho óbito
    • dias_perm_total         — soma dos dias de permanência
    • dias_perm_medio         — média de dias de permanência
    • val_tot_total           — valor total (R$) aprovado
    • val_tot_medio           — valor médio por internação
    • taxa_internacao         — internações / populacao * 1000
    • taxa_mortalidade_intra  — óbitos / internações * 100 (%)

  UNION: subtotais com sexo = 'TOTAL', faixa_etaria = 'TOTAL', car_int_grupo = 'TOTAL'.
*/

WITH base AS (
    SELECT * FROM {{ ref('int_internacoes_enriched') }}
),

-- ── Agregação completa ────────────────────────────────────────────────────
agregado AS (

    -- Detalhado: sexo x faixa_etaria x car_int_grupo
    SELECT
        municipio_cod,
        municipio_nome,
        uf_sigla,
        regiao,
        ano_cmpt,
        mes_cmpt,
        mes_competencia,
        diag_cap,
        diag_grupo,
        sexo,
        faixa_etaria,
        car_int_grupo,

        COUNT(*)                                                AS total_internacoes,
        COUNT(*) FILTER (WHERE is_obito)                        AS total_obitos_internados,
        SUM(dias_perm)                                          AS dias_perm_total,
        ROUND(AVG(dias_perm)::NUMERIC, 2)                       AS dias_perm_medio,
        SUM(val_tot)                                            AS val_tot_total,
        ROUND(AVG(val_tot)::NUMERIC, 2)                         AS val_tot_medio,
        MAX(populacao)                                          AS populacao

    FROM base
    GROUP BY
        municipio_cod, municipio_nome, uf_sigla, regiao,
        ano_cmpt, mes_cmpt, mes_competencia,
        diag_cap, diag_grupo,
        sexo, faixa_etaria, car_int_grupo

    UNION ALL

    -- Subtotal: sexo = 'TOTAL'
    SELECT
        municipio_cod,
        municipio_nome,
        uf_sigla,
        regiao,
        ano_cmpt,
        mes_cmpt,
        mes_competencia,
        diag_cap,
        diag_grupo,
        'TOTAL'                                                 AS sexo,
        faixa_etaria,
        car_int_grupo,

        COUNT(*)                                                AS total_internacoes,
        COUNT(*) FILTER (WHERE is_obito)                        AS total_obitos_internados,
        SUM(dias_perm)                                          AS dias_perm_total,
        ROUND(AVG(dias_perm)::NUMERIC, 2)                       AS dias_perm_medio,
        SUM(val_tot)                                            AS val_tot_total,
        ROUND(AVG(val_tot)::NUMERIC, 2)                         AS val_tot_medio,
        MAX(populacao)                                          AS populacao

    FROM base
    GROUP BY
        municipio_cod, municipio_nome, uf_sigla, regiao,
        ano_cmpt, mes_cmpt, mes_competencia,
        diag_cap, diag_grupo, faixa_etaria, car_int_grupo

    UNION ALL

    -- Subtotal: faixa_etaria = 'TOTAL'
    SELECT
        municipio_cod,
        municipio_nome,
        uf_sigla,
        regiao,
        ano_cmpt,
        mes_cmpt,
        mes_competencia,
        diag_cap,
        diag_grupo,
        sexo,
        'TOTAL'                                                 AS faixa_etaria,
        car_int_grupo,

        COUNT(*)                                                AS total_internacoes,
        COUNT(*) FILTER (WHERE is_obito)                        AS total_obitos_internados,
        SUM(dias_perm)                                          AS dias_perm_total,
        ROUND(AVG(dias_perm)::NUMERIC, 2)                       AS dias_perm_medio,
        SUM(val_tot)                                            AS val_tot_total,
        ROUND(AVG(val_tot)::NUMERIC, 2)                         AS val_tot_medio,
        MAX(populacao)                                          AS populacao

    FROM base
    GROUP BY
        municipio_cod, municipio_nome, uf_sigla, regiao,
        ano_cmpt, mes_cmpt, mes_competencia,
        diag_cap, diag_grupo, sexo, car_int_grupo

    UNION ALL

    -- Grand total: sexo = 'TOTAL', faixa_etaria = 'TOTAL', car_int_grupo = 'TOTAL'
    SELECT
        municipio_cod,
        municipio_nome,
        uf_sigla,
        regiao,
        ano_cmpt,
        mes_cmpt,
        mes_competencia,
        diag_cap,
        diag_grupo,
        'TOTAL'                                                 AS sexo,
        'TOTAL'                                                 AS faixa_etaria,
        'TOTAL'                                                 AS car_int_grupo,

        COUNT(*)                                                AS total_internacoes,
        COUNT(*) FILTER (WHERE is_obito)                        AS total_obitos_internados,
        SUM(dias_perm)                                          AS dias_perm_total,
        ROUND(AVG(dias_perm)::NUMERIC, 2)                       AS dias_perm_medio,
        SUM(val_tot)                                            AS val_tot_total,
        ROUND(AVG(val_tot)::NUMERIC, 2)                         AS val_tot_medio,
        MAX(populacao)                                          AS populacao

    FROM base
    GROUP BY
        municipio_cod, municipio_nome, uf_sigla, regiao,
        ano_cmpt, mes_cmpt, mes_competencia,
        diag_cap, diag_grupo
),

final AS (
    SELECT
        municipio_cod,
        municipio_nome,
        uf_sigla,
        regiao,
        ano_cmpt,
        mes_cmpt,
        mes_competencia,
        diag_cap,
        diag_grupo,
        sexo,
        faixa_etaria,
        car_int_grupo,
        total_internacoes,
        total_obitos_internados,
        dias_perm_total,
        dias_perm_medio,
        val_tot_total,
        val_tot_medio,
        populacao,

        -- Taxa de internação por 1.000 habitantes
        CASE
            WHEN COALESCE(populacao, 0) > 0
            THEN ROUND(
                (total_internacoes::NUMERIC / populacao) * 1000,
                4
            )
            ELSE NULL
        END                                                     AS taxa_internacao,

        -- Taxa de mortalidade intra-hospitalar (%)
        CASE
            WHEN total_internacoes > 0
            THEN ROUND(
                total_obitos_internados::NUMERIC / total_internacoes * 100,
                4
            )
            ELSE NULL
        END                                                     AS taxa_mortalidade_intra,

        CURRENT_TIMESTAMP                                       AS dbt_updated_at

    FROM agregado
)

SELECT * FROM final
