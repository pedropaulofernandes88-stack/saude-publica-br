-- int_pop_municipio_mes.sql
-- Expande estimativas anuais para todos os meses (base para taxas por 10k)

{{ config(materialized='table', schema='intermediate') }}

SELECT
    p.municipio_cod,
    p.uf_sigla,
    p.ano_referencia,
    m.mes_num,
    -- Monta chave mes_competencia para join com SIA/PA
    (p.ano_referencia::VARCHAR || LPAD(m.mes_num::VARCHAR, 2, '0'))::VARCHAR(6)
        AS mes_competencia,
    p.populacao_estimada
FROM {{ ref('stg_ibge_populacao') }} p
CROSS JOIN (
    SELECT generate_series(1, 12) AS mes_num
) m
