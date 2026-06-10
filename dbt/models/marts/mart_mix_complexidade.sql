-- mart_mix_complexidade.sql
-- Mix AB/MC/AC e índice de complexidade por município

{{ config(materialized='table', schema='marts') }}

SELECT
    mes_competencia,
    ano_competencia,
    uf_sigla,
    regiao,
    municipio_cod,
    nome_municipio,
    MAX(populacao_estimada)  AS populacao,

    SUM(qtd_aprovada)        AS total_proc,
    SUM(valor_aprovado)      AS total_valor,

    -- Volumes por complexidade
    SUM(CASE WHEN complexidade = '01' THEN qtd_aprovada ELSE 0 END) AS proc_ab,
    SUM(CASE WHEN complexidade = '02' THEN qtd_aprovada ELSE 0 END) AS proc_mc,
    SUM(CASE WHEN complexidade = '03' THEN qtd_aprovada ELSE 0 END) AS proc_ac,
    SUM(CASE WHEN complexidade IS NULL THEN qtd_aprovada ELSE 0 END) AS proc_nao_classificado,

    -- Percentuais por complexidade
    ROUND(SUM(CASE WHEN complexidade = '01' THEN qtd_aprovada ELSE 0 END)
          * 100.0 / NULLIF(SUM(qtd_aprovada), 0), 2) AS pct_ab,
    ROUND(SUM(CASE WHEN complexidade = '02' THEN qtd_aprovada ELSE 0 END)
          * 100.0 / NULLIF(SUM(qtd_aprovada), 0), 2) AS pct_mc,
    ROUND(SUM(CASE WHEN complexidade = '03' THEN qtd_aprovada ELSE 0 END)
          * 100.0 / NULLIF(SUM(qtd_aprovada), 0), 2) AS pct_ac,

    -- Índice de complexidade ponderado: (1×AB + 2×MC + 3×AC) / total
    ROUND(
        ({{ var('peso_ab') }} * SUM(CASE WHEN complexidade = '01' THEN qtd_aprovada ELSE 0 END)
       + {{ var('peso_mc') }} * SUM(CASE WHEN complexidade = '02' THEN qtd_aprovada ELSE 0 END)
       + {{ var('peso_ac') }} * SUM(CASE WHEN complexidade = '03' THEN qtd_aprovada ELSE 0 END))
        / NULLIF(SUM(qtd_aprovada), 0),
    3) AS indice_complexidade,

    -- Valor médio por complexidade
    ROUND(SUM(CASE WHEN complexidade = '01' THEN valor_aprovado ELSE 0 END)
          / NULLIF(SUM(CASE WHEN complexidade = '01' THEN qtd_aprovada ELSE 0 END), 0), 2)
        AS valor_medio_ab,
    ROUND(SUM(CASE WHEN complexidade = '02' THEN valor_aprovado ELSE 0 END)
          / NULLIF(SUM(CASE WHEN complexidade = '02' THEN qtd_aprovada ELSE 0 END), 0), 2)
        AS valor_medio_mc,
    ROUND(SUM(CASE WHEN complexidade = '03' THEN valor_aprovado ELSE 0 END)
          / NULLIF(SUM(CASE WHEN complexidade = '03' THEN qtd_aprovada ELSE 0 END), 0), 2)
        AS valor_medio_ac

FROM {{ ref('int_sia_pa_enriched') }}
GROUP BY 1, 2, 3, 4, 5, 6
