-- mart_ranking_municipios.sql
-- Ranking composto de municípios por desempenho em saúde ambulatorial

{{ config(materialized='table', schema='marts') }}

WITH indicadores AS (
    SELECT
        p.mes_competencia,
        p.ano_competencia,
        p.uf_sigla,
        p.regiao,
        p.municipio_cod,
        p.nome_municipio,
        p.populacao,
        p.total_procedimentos,
        p.taxa_proc_10k,
        p.investimento_per_capita,
        p.var_yoy_pct,
        a.zscore_acesso,
        a.cobertura_relativa_pct,
        a.flag_baixa_cobertura,
        a.quartil_acesso,
        m.indice_complexidade,
        m.pct_ab,
        m.pct_mc,
        m.pct_ac
    FROM {{ ref('mart_producao_amb') }} p
    LEFT JOIN {{ ref('mart_acesso_cobertura') }} a
        ON p.mes_competencia = a.mes_competencia
       AND p.municipio_cod   = a.municipio_cod
    LEFT JOIN {{ ref('mart_mix_complexidade') }} m
        ON p.mes_competencia = m.mes_competencia
       AND p.municipio_cod   = m.municipio_cod
),

zscores AS (
    SELECT
        *,
        -- Z-score de taxa (vs média estadual)
        (taxa_proc_10k - AVG(taxa_proc_10k) OVER (
            PARTITION BY mes_competencia, uf_sigla
        )) / NULLIF(STDDEV(taxa_proc_10k) OVER (
            PARTITION BY mes_competencia, uf_sigla
        ), 0) AS z_taxa,

        -- Z-score de investimento per capita
        (investimento_per_capita - AVG(investimento_per_capita) OVER (
            PARTITION BY mes_competencia, uf_sigla
        )) / NULLIF(STDDEV(investimento_per_capita) OVER (
            PARTITION BY mes_competencia, uf_sigla
        ), 0) AS z_invest,

        -- Z-score de complexidade (mais alta = mais especializada)
        (indice_complexidade - AVG(indice_complexidade) OVER (
            PARTITION BY mes_competencia, uf_sigla
        )) / NULLIF(STDDEV(indice_complexidade) OVER (
            PARTITION BY mes_competencia, uf_sigla
        ), 0) AS z_complexidade
    FROM indicadores
)

ranked AS (
    SELECT
        -- Dimensões — aliases alinhados com api/schemas.py RankingMunicipioItem
        mes_competencia,
        ano_competencia                                                AS ano,
        uf_sigla,
        regiao,
        municipio_cod,
        nome_municipio                                                 AS municipio_nome,
        populacao,
        total_procedimentos,
        taxa_proc_10k,
        investimento_per_capita,
        var_yoy_pct,
        zscore_acesso,
        cobertura_relativa_pct,
        flag_baixa_cobertura,
        quartil_acesso,
        indice_complexidade,
        pct_ab,
        pct_mc,
        pct_ac,
        z_taxa,
        z_invest,
        z_complexidade,

        -- Score composto — exposto como score_acesso para a API
        ROUND(
            (COALESCE(z_taxa, 0)
           + COALESCE(z_invest, 0)
           + COALESCE(z_complexidade, 0)) / 3.0,
        3) AS score_acesso,

        -- Ranking estadual (1 = melhor desempenho)
        RANK() OVER (
            PARTITION BY mes_competencia, uf_sigla
            ORDER BY (COALESCE(z_taxa, 0) + COALESCE(z_invest, 0) + COALESCE(z_complexidade, 0)) DESC
        ) AS ranking_estadual,

        -- Ranking nacional
        RANK() OVER (
            PARTITION BY mes_competencia
            ORDER BY (COALESCE(z_taxa, 0) + COALESCE(z_invest, 0) + COALESCE(z_complexidade, 0)) DESC
        ) AS ranking_nacional,

        -- Percentil estadual (0-100, maior = melhor)
        ROUND(
            PERCENT_RANK() OVER (
                PARTITION BY mes_competencia, uf_sigla
                ORDER BY (COALESCE(z_taxa, 0) + COALESCE(z_invest, 0) + COALESCE(z_complexidade, 0))
            ) * 100,
        1) AS percentil_estadual,

        -- Percentil nacional
        ROUND(
            PERCENT_RANK() OVER (
                PARTITION BY mes_competencia
                ORDER BY (COALESCE(z_taxa, 0) + COALESCE(z_invest, 0) + COALESCE(z_complexidade, 0))
            ) * 100,
        1) AS percentil_nacional

    FROM zscores
)

SELECT
    *,
    -- Categoria textual baseada no percentil estadual
    CASE
        WHEN percentil_estadual >= 75 THEN 'Excelente'
        WHEN percentil_estadual >= 50 THEN 'Bom'
        WHEN percentil_estadual >= 25 THEN 'Regular'
        ELSE 'Crítico'
    END AS categoria

FROM ranked
