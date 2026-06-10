{{ config(
    materialized='table',
    schema='intermediate',
    indexes=[
        {'columns': ['municipio_res', 'mes_competencia']},
        {'columns': ['uf_res', 'ano_obito']},
        {'columns': ['causabas_cap']},
    ]
) }}

/*
  int_obitos_enriched — Óbitos SIM enriquecidos com dimensões

  Faz o JOIN entre stg_sim_obitos e as tabelas de referência:
    • ref_ibge_municipios  → municipio_nome, regiao
    • ref_ibge_populacao   → populacao (para taxas brutas)

  Uma linha = um óbito individual enriquecido.
  Mart mart_mortalidade agrega este modelo.
*/

WITH obitos AS (
    SELECT * FROM {{ ref('stg_sim_obitos') }}
),

municipios AS (
    SELECT
        municipio_cod6,
        nome             AS municipio_nome,
        uf_sigla,
        regiao
    FROM {{ source('raw', 'ref_ibge_municipios') }}
),

populacao AS (
    SELECT
        municipio_cod6,
        ano_referencia,
        populacao_estimada
    FROM {{ source('raw', 'ref_ibge_populacao') }}
),

enriched AS (
    SELECT
        -- Identificação do óbito
        o.numerodo,
        o.tipobito,
        o.dtobito,
        o.ano_obito,
        o.mes_obito,
        o.mes_competencia,

        -- Causa
        o.causabas,
        o.causabas_cap,

        -- Localização do óbito
        o.municipio_ocor,
        o.uf_ocor,

        -- Localização de residência (chave principal para agregações)
        o.municipio_res                                         AS municipio_cod,
        COALESCE(m.municipio_nome, 'Desconhecido')              AS municipio_nome,
        COALESCE(m.uf_sigla, o.uf_res)                         AS uf_sigla,
        COALESCE(m.regiao, 'ND')                               AS regiao,

        -- Atributos do óbito
        o.sexo,
        o.idade_valor,
        o.idade_unidade,
        o.faixa_etaria,
        o.racacor,
        o.escolaridade,
        o.estadociv,
        o.lococor,
        o.local_obito_label,
        o.assistmed,
        o.is_fetal,
        o.uf_arquivo,
        o.ingested_at,

        -- Tipo de óbito (label)
        CASE o.tipobito
            WHEN '1' THEN 'fetal'
            WHEN '2' THEN 'nao_fetal'
            ELSE 'nd'
        END                                                     AS tipo_obito_label,

        -- Grupo da causa (2 primeiros chars do CID-10 agrupados)
        CASE
            WHEN o.causabas_cap IN ('A', 'B') THEN 'Infecciosas e Parasitárias'
            WHEN o.causabas_cap = 'C'         THEN 'Neoplasias'
            WHEN o.causabas_cap IN ('D')      THEN 'Sangue e Imunidade'
            WHEN o.causabas_cap = 'E'         THEN 'Endócrinas e Metabólicas'
            WHEN o.causabas_cap = 'F'         THEN 'Transtornos Mentais'
            WHEN o.causabas_cap = 'G'         THEN 'Sistema Nervoso'
            WHEN o.causabas_cap IN ('H')      THEN 'Olhos/Ouvidos'
            WHEN o.causabas_cap = 'I'         THEN 'Aparelho Circulatório'
            WHEN o.causabas_cap = 'J'         THEN 'Aparelho Respiratório'
            WHEN o.causabas_cap = 'K'         THEN 'Aparelho Digestivo'
            WHEN o.causabas_cap = 'L'         THEN 'Pele'
            WHEN o.causabas_cap = 'M'         THEN 'Osteomuscular'
            WHEN o.causabas_cap = 'N'         THEN 'Geniturinário'
            WHEN o.causabas_cap = 'O'         THEN 'Gravidez e Parto'
            WHEN o.causabas_cap = 'P'         THEN 'Afecções Perinatais'
            WHEN o.causabas_cap = 'Q'         THEN 'Malformações Congênitas'
            WHEN o.causabas_cap = 'R'         THEN 'Sinais e Sintomas'
            WHEN o.causabas_cap IN ('S', 'T') THEN 'Lesões e Envenenamentos'
            WHEN o.causabas_cap IN ('V', 'W', 'X', 'Y') THEN 'Causas Externas'
            WHEN o.causabas_cap = 'Z'         THEN 'Contatos com Serviços de Saúde'
            ELSE 'ND'
        END                                                     AS causabas_grupo,

        -- Populacao para taxas (LEFT JOIN — pode ser NULL)
        p.populacao_estimada                                    AS populacao

    FROM obitos o
    LEFT JOIN municipios m
        ON o.municipio_res = m.municipio_cod6
    LEFT JOIN populacao p
        ON o.municipio_res = p.municipio_cod6
        AND o.ano_obito = p.ano_referencia
)

SELECT * FROM enriched
