-- mart_sazonalidade.sql
-- Padrões sazonais históricos por procedimento/UF (base para anomaly detection)

{{ config(materialized='table', schema='marts') }}

WITH mensal AS (
    SELECT
        proc_id,
        nome_procedimento,
        uf_sigla,
        regiao,
        complexidade,
        complexidade_label,
        ano_competencia,
        mes_num,
        SUM(qtd_aprovada) AS qtd_mensal
    FROM {{ ref('int_sia_pa_enriched') }}
    GROUP BY 1, 2, 3, 4, 5, 6, 7, 8
)

SELECT
    proc_id,
    nome_procedimento,
    uf_sigla,
    regiao,
    complexidade,
    complexidade_label,
    mes_num,

    -- Estatísticas históricas para o mês
    COUNT(*)           AS anos_observados,
    AVG(qtd_mensal)    AS media_historica,
    STDDEV(qtd_mensal) AS desvio_historico,
    MIN(qtd_mensal)    AS minimo_historico,
    MAX(qtd_mensal)    AS maximo_historico,

    -- Limites para detecção de anomalia (±2.5σ)
    ROUND(AVG(qtd_mensal) + {{ var('threshold_anomalia_sigma') }}
          * COALESCE(STDDEV(qtd_mensal), 0), 0)  AS limite_superior,
    ROUND(GREATEST(AVG(qtd_mensal) - {{ var('threshold_anomalia_sigma') }}
          * COALESCE(STDDEV(qtd_mensal), 0), 0), 0) AS limite_inferior,

    -- Coeficiente de variação (CV) — indica estabilidade do procedimento
    ROUND(STDDEV(qtd_mensal) * 100.0 / NULLIF(AVG(qtd_mensal), 0), 2)
        AS coef_variacao_pct

FROM mensal
GROUP BY 1, 2, 3, 4, 5, 6, 7

-- Mínimo de anos para calcular sazonalidade com confiança
HAVING COUNT(*) >= {{ var('min_anos_sazonalidade') }}
