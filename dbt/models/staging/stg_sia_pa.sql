-- stg_sia_pa.sql
-- Padroniza e limpa dados brutos SIA/PA
-- Materialização: view (sem custo de storage)

{{ config(materialized='view', schema='staging') }}

WITH source AS (
    SELECT * FROM {{ source('raw', 'sia_pa_raw') }}
),

cleaned AS (
    SELECT
        -- Dimensão temporal
        LPAD(mes_competencia, 6, '0')::VARCHAR(6)  AS mes_competencia,
        CAST(LEFT(LPAD(mes_competencia, 6, '0'), 4) AS SMALLINT)  AS ano_competencia,
        CAST(RIGHT(LPAD(mes_competencia, 6, '0'), 2) AS SMALLINT) AS mes_num,

        -- Localização
        LPAD(TRIM(municipio_cod), 6, '0')::VARCHAR(6)  AS municipio_cod,
        UPPER(TRIM(uf_sigla))::VARCHAR(2)               AS uf_sigla,

        -- Procedimento
        LPAD(TRIM(proc_id), 10, '0')::VARCHAR(10)   AS proc_id,
        UPPER(TRIM(cid_primario))::VARCHAR(4)        AS cid_primario,

        -- Quantidades e valores
        COALESCE(qtd_aprovada, 0)::INTEGER           AS qtd_aprovada,
        COALESCE(valor_aprovado, 0)::NUMERIC(12,2)   AS valor_aprovado,

        -- Atributos do atendimento
        UPPER(TRIM(tipo_financiamento))::VARCHAR(2)     AS tipo_financiamento,
        UPPER(TRIM(categoria_atendimento))::VARCHAR(2)  AS categoria_atendimento,
        UPPER(TRIM(sexo))::VARCHAR(1)                   AS sexo,
        COALESCE(faixa_etaria, 0)::SMALLINT             AS faixa_etaria

    FROM source

    -- Filtros de qualidade básicos
    WHERE qtd_aprovada > 0
      AND municipio_cod IS NOT NULL
      AND LENGTH(TRIM(municipio_cod)) = 6
      AND mes_competencia IS NOT NULL
      AND LENGTH(TRIM(mes_competencia)) = 6
)

SELECT * FROM cleaned
