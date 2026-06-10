{{ config(
    materialized='table',
    schema='intermediate',
    indexes=[
        {'columns': ['municipio_res', 'mes_competencia']},
        {'columns': ['uf_res', 'ano_cmpt']},
        {'columns': ['diag_cap']},
        {'columns': ['car_int_grupo']},
    ]
) }}

/*
  int_internacoes_enriched — AIH SIH enriquecidas com dimensões

  Faz o JOIN entre stg_sih_aih e as tabelas de referência:
    • ref_ibge_municipios  → municipio_nome, regiao
    • ref_ibge_populacao   → populacao (para taxas de internação)

  Uma linha = uma AIH individual enriquecida.
  Mart mart_internacoes agrega este modelo.
*/

WITH aih AS (
    SELECT * FROM {{ ref('stg_sih_aih') }}
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
        -- Identificação da AIH
        a.n_aih,
        a.ident,
        a.dt_inter,
        a.dt_saida,

        -- Competência
        a.ano_cmpt,
        a.mes_cmpt,
        a.mes_competencia,

        -- Diagnóstico
        a.diag_princ,
        a.diag_secun,
        a.diag_cap,
        a.proc_rea,
        a.proc_sol,

        -- Estabelecimento
        a.cnes,
        a.municipio_ocor,
        a.uf_ocor,

        -- Residência (chave principal para agregações)
        a.municipio_res                                         AS municipio_cod,
        COALESCE(m.municipio_nome, 'Desconhecido')              AS municipio_nome,
        COALESCE(m.uf_sigla, a.uf_res)                         AS uf_sigla,
        a.uf_res,
        COALESCE(m.regiao, 'ND')                               AS regiao,

        -- Paciente
        a.sexo,
        a.idade,
        a.faixa_etaria,
        a.nasc,
        a.raca_cor,

        -- Desfecho
        a.morte,
        a.is_obito,
        a.dias_perm,

        -- Financeiro
        a.cobranca,
        a.val_tot,
        a.val_sh,
        a.val_sp,
        a.val_sadt,
        a.val_uci,

        -- Caráter de internação
        a.car_int,
        a.car_int_grupo,

        -- Gestão
        a.gestor_cod,
        a.instru,

        -- Arquivo
        a.uf_arquivo,
        a.ingested_at,

        -- Grupo do diagnóstico principal (mesmo mapeamento do SIM)
        CASE a.diag_cap
            WHEN 'A' THEN 'Infecciosas e Parasitárias'
            WHEN 'B' THEN 'Infecciosas e Parasitárias'
            WHEN 'C' THEN 'Neoplasias'
            WHEN 'D' THEN 'Sangue e Imunidade'
            WHEN 'E' THEN 'Endócrinas e Metabólicas'
            WHEN 'F' THEN 'Transtornos Mentais'
            WHEN 'G' THEN 'Sistema Nervoso'
            WHEN 'H' THEN 'Olhos/Ouvidos'
            WHEN 'I' THEN 'Aparelho Circulatório'
            WHEN 'J' THEN 'Aparelho Respiratório'
            WHEN 'K' THEN 'Aparelho Digestivo'
            WHEN 'L' THEN 'Pele'
            WHEN 'M' THEN 'Osteomuscular'
            WHEN 'N' THEN 'Geniturinário'
            WHEN 'O' THEN 'Gravidez e Parto'
            WHEN 'P' THEN 'Afecções Perinatais'
            WHEN 'Q' THEN 'Malformações Congênitas'
            WHEN 'R' THEN 'Sinais e Sintomas'
            WHEN 'S' THEN 'Lesões e Envenenamentos'
            WHEN 'T' THEN 'Lesões e Envenenamentos'
            WHEN 'V' THEN 'Causas Externas'
            WHEN 'W' THEN 'Causas Externas'
            WHEN 'X' THEN 'Causas Externas'
            WHEN 'Y' THEN 'Causas Externas'
            WHEN 'Z' THEN 'Contatos com Serviços de Saúde'
            ELSE 'ND'
        END                                                     AS diag_grupo,

        -- Populacao para taxas
        p.populacao_estimada                                    AS populacao

    FROM aih a
    LEFT JOIN municipios m
        ON a.municipio_res = m.municipio_cod6
    LEFT JOIN populacao p
        ON a.municipio_res = p.municipio_cod6
        AND a.ano_cmpt = p.ano_referencia
)

SELECT * FROM enriched
