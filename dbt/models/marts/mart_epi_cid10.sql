-- mart_epi_cid10.sql
-- Perfil epidemiológico por capítulo CID-10

{{ config(materialized='table', schema='marts') }}

WITH atend_capitulo AS (
    SELECT
        mes_competencia,
        ano_competencia,
        mes_num,
        uf_sigla,
        regiao,
        capitulo_cid,
        nome_capitulo_cid,
        SUM(qtd_aprovada)    AS total_atendimentos,
        SUM(valor_aprovado)  AS total_valor_cid,
        COUNT(DISTINCT municipio_cod) AS municipios_com_atend
    FROM {{ ref('int_sia_pa_enriched') }}
    WHERE capitulo_cid IS NOT NULL
    GROUP BY 1, 2, 3, 4, 5, 6, 7
),

pop_uf AS (
    SELECT
        mes_competencia,
        uf_sigla,
        SUM(populacao_estimada) AS populacao_uf
    FROM {{ ref('int_pop_municipio_mes') }}
    GROUP BY 1, 2
),

total_uf AS (
    SELECT
        mes_competencia,
        uf_sigla,
        SUM(total_atendimentos) AS total_atend_uf
    FROM atend_capitulo
    GROUP BY 1, 2
)

SELECT
    -- Dimensões — aliases alinhados com api/schemas.py EpiCid10Item
    a.uf_sigla,
    a.ano_competencia                                        AS ano,
    a.mes_competencia,
    a.mes_num,
    a.regiao,
    a.capitulo_cid                                           AS capitulo_cid10,
    a.nome_capitulo_cid                                      AS descricao_capitulo,

    -- Métricas brutas
    a.total_atendimentos                                     AS total_procedimentos,
    a.total_valor_cid,
    a.municipios_com_atend,

    -- Populacão da UF (join)
    p.populacao_uf,

    -- Taxa por 10.000 hab na UF
    ROUND(a.total_atendimentos * 10000.0 / NULLIF(p.populacao_uf, 0), 2)
        AS taxa_10k_uf,

    -- % do total de atendimentos da UF no mês
    ROUND(a.total_atendimentos * 100.0 / NULLIF(t.total_atend_uf, 0), 2)
        AS pct_atend_uf,

    -- Ranking do capítulo na UF (1 = mais frequente)
    RANK() OVER (
        PARTITION BY a.mes_competencia, a.uf_sigla
        ORDER BY a.total_atendimentos DESC
    ) AS rank_capitulo_uf,

    -- Variação YoY (alias alinhado com api/schemas.py)
    LAG(a.total_atendimentos, 12) OVER (
        PARTITION BY a.uf_sigla, a.capitulo_cid
        ORDER BY a.mes_competencia
    ) AS atend_ano_anterior,

    ROUND(
        (a.total_atendimentos - LAG(a.total_atendimentos, 12) OVER (
            PARTITION BY a.uf_sigla, a.capitulo_cid
            ORDER BY a.mes_competencia
        )) * 100.0
        / NULLIF(LAG(a.total_atendimentos, 12) OVER (
            PARTITION BY a.uf_sigla, a.capitulo_cid
            ORDER BY a.mes_competencia
        ), 0),
    2) AS variacao_anual_pct

FROM atend_capitulo a
LEFT JOIN pop_uf p
    ON a.mes_competencia = p.mes_competencia
   AND a.uf_sigla        = p.uf_sigla
LEFT JOIN total_uf t
    ON a.mes_competencia = t.mes_competencia
   AND a.uf_sigla        = t.uf_sigla
