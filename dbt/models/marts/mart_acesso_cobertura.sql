-- mart_acesso_cobertura.sql
-- Indicadores de acesso e equidade por município

{{ config(materialized='table', schema='marts') }}

WITH municipio_mes AS (
    SELECT
        mes_competencia,
        ano_competencia,
        uf_sigla,
        regiao,
        municipio_cod,
        nome_municipio,
        MAX(populacao_estimada)                          AS populacao,
        SUM(qtd_aprovada)                               AS total_proc,
        ROUND(SUM(qtd_aprovada) * 10000.0
              / NULLIF(MAX(populacao_estimada), 0), 2)  AS taxa_10k
    FROM {{ ref('int_sia_pa_enriched') }}
    GROUP BY 1, 2, 3, 4, 5, 6
),

estatisticas_uf AS (
    SELECT
        mes_competencia,
        uf_sigla,
        AVG(taxa_10k)                           AS media_taxa_uf,
        STDDEV(taxa_10k)                        AS desvio_taxa_uf,
        PERCENTILE_CONT(0.5) WITHIN GROUP
            (ORDER BY taxa_10k)                 AS mediana_taxa_uf,
        PERCENTILE_CONT(0.25) WITHIN GROUP
            (ORDER BY taxa_10k)                 AS q1_taxa_uf,
        PERCENTILE_CONT(0.75) WITHIN GROUP
            (ORDER BY taxa_10k)                 AS q3_taxa_uf,
        COUNT(*)                                AS qtd_municipios_uf
    FROM municipio_mes
    GROUP BY 1, 2
)

SELECT
    m.mes_competencia,
    m.ano_competencia,
    m.uf_sigla,
    m.regiao,
    m.municipio_cod,
    m.nome_municipio,
    m.populacao,
    m.total_proc,
    m.taxa_10k,
    e.media_taxa_uf,
    e.desvio_taxa_uf,
    e.mediana_taxa_uf,
    e.qtd_municipios_uf,

    -- Cobertura relativa (% da média estadual)
    ROUND(m.taxa_10k * 100.0 / NULLIF(e.media_taxa_uf, 0), 2)
        AS cobertura_relativa_pct,

    -- Z-score de acesso
    ROUND(
        (m.taxa_10k - e.media_taxa_uf) / NULLIF(e.desvio_taxa_uf, 0),
    3) AS zscore_acesso,

    -- Flags de alerta
    CASE
        WHEN m.taxa_10k < e.media_taxa_uf * {{ var('threshold_baixa_cobertura') }}
        THEN TRUE ELSE FALSE
    END AS flag_baixa_cobertura,

    CASE
        WHEN m.taxa_10k < e.q1_taxa_uf THEN 'Baixo (Q1)'
        WHEN m.taxa_10k <= e.q3_taxa_uf THEN 'Médio (Q2-Q3)'
        ELSE 'Alto (Q4)'
    END AS quartil_acesso

FROM municipio_mes m
JOIN estatisticas_uf e
    ON m.mes_competencia = e.mes_competencia
   AND m.uf_sigla        = e.uf_sigla
