-- mart_producao_amb.sql
-- Produção ambulatorial mensal por município com taxas e variações

{{ config(
    materialized='table',
    schema='marts',
    indexes=[
        {'columns': ['mes_competencia', 'uf_sigla'], 'unique': false},
        {'columns': ['municipio_cod', 'mes_competencia'], 'unique': false},
    ]
) }}

WITH base AS (
    SELECT
        mes_competencia,
        ano_competencia,
        mes_num,
        uf_sigla,
        regiao,
        municipio_cod,
        nome_municipio,
        MAX(populacao_estimada)  AS populacao,
        SUM(qtd_aprovada)        AS total_procedimentos,
        SUM(valor_aprovado)      AS total_valor,
        COUNT(DISTINCT proc_id)  AS procedimentos_distintos,
        COUNT(DISTINCT cid_primario) AS cids_distintos
    FROM {{ ref('int_sia_pa_enriched') }}
    GROUP BY 1, 2, 3, 4, 5, 6, 7
),

com_variacoes AS (
    SELECT
        *,
        -- Taxa por 10.000 habitantes
        ROUND(
            total_procedimentos * 10000.0 / NULLIF(populacao, 0),
        2) AS taxa_proc_10k,

        -- Variação mês a mês (MoM)
        LAG(total_procedimentos) OVER (
            PARTITION BY municipio_cod ORDER BY mes_competencia
        ) AS proc_mes_anterior,

        -- Variação ano a ano (YoY)
        LAG(total_procedimentos, 12) OVER (
            PARTITION BY municipio_cod ORDER BY mes_competencia
        ) AS proc_ano_anterior
    FROM base
)

SELECT
    *,
    ROUND(
        (total_procedimentos - proc_mes_anterior) * 100.0
        / NULLIF(proc_mes_anterior, 0),
    2) AS var_mom_pct,

    ROUND(
        (total_procedimentos - proc_ano_anterior) * 100.0
        / NULLIF(proc_ano_anterior, 0),
    2) AS var_yoy_pct,

    -- Valor médio por procedimento
    ROUND(total_valor / NULLIF(total_procedimentos, 0), 2) AS valor_medio_proc,

    -- Investimento per capita (mensal)
    ROUND(total_valor / NULLIF(populacao, 0), 4) AS investimento_per_capita

FROM com_variacoes
