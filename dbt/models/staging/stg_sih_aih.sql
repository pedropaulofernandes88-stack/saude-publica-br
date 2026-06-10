{{ config(materialized='view', schema='staging') }}

/*
  stg_sih_aih — Staging do SIH/AIH (Sistema de Informações Hospitalares)

  Limpa, padroniza e deriva campos do raw sih_aih_raw.
  Cada linha representa uma AIH (Autorização de Internação Hospitalar).

  Derivações principais:
    • mes_competencia  : AAAAMM concatenado
    • faixa_etaria     : bandas etárias a partir de `idade` (anos inteiros)
    • car_int_grupo    : agrupamento do caráter de internação
    • local_nasc_label : decodificação do campo `nasc`

  Filtros de qualidade:
    • Apenas competências dentro do período configurado (ano_inicio / ano_fim)
    • municipio_res não nulo, LENGTH = 6 e diferente de '000000'
    • diag_princ não nulo e length >= 3
*/

WITH source AS (
    SELECT * FROM {{ source('raw', 'sih_aih_raw') }}
),

cleaned AS (
    SELECT
        -- ── Identificação ──────────────────────────────────────────────
        COALESCE(TRIM(n_aih), '')::TEXT                        AS n_aih,
        UPPER(TRIM(ident))::VARCHAR(2)                        AS ident,

        -- ── Datas ─────────────────────────────────────────────────────
        TRIM(dt_inter)::VARCHAR(8)                             AS dt_inter,
        TRIM(dt_saida)::VARCHAR(8)                             AS dt_saida,

        -- ── Competência ───────────────────────────────────────────────
        ano_cmpt::SMALLINT                                     AS ano_cmpt,
        mes_cmpt::SMALLINT                                     AS mes_cmpt,
        LPAD(ano_cmpt::TEXT, 4, '0')
            || LPAD(mes_cmpt::TEXT, 2, '0')                   AS mes_competencia,

        -- ── Permanência e diagnóstico ──────────────────────────────────
        GREATEST(COALESCE(dias_perm, 0), 0)::SMALLINT         AS dias_perm,
        UPPER(TRIM(diag_princ))::VARCHAR(5)                   AS diag_princ,
        UPPER(TRIM(diag_secun))::VARCHAR(5)                   AS diag_secun,
        UPPER(TRIM(diag_cap))::VARCHAR(1)                     AS diag_cap,
        UPPER(TRIM(proc_rea))::VARCHAR(10)                    AS proc_rea,
        UPPER(TRIM(proc_sol))::VARCHAR(10)                    AS proc_sol,

        -- ── Estabelecimento e localização ─────────────────────────────
        LPAD(TRIM(cnes), 7, '0')::VARCHAR(7)                  AS cnes,
        LPAD(TRIM(municipio_ocor), 6, '0')::VARCHAR(6)        AS municipio_ocor,
        UPPER(TRIM(uf_ocor))::VARCHAR(2)                      AS uf_ocor,
        LPAD(TRIM(municipio_res), 6, '0')::VARCHAR(6)         AS municipio_res,
        UPPER(TRIM(uf_res))::VARCHAR(2)                       AS uf_res,

        -- ── Paciente ──────────────────────────────────────────────────
        UPPER(TRIM(sexo))::VARCHAR(1)                         AS sexo,
        COALESCE(idade, 0)::SMALLINT                          AS idade,

        -- Faixa etária (anos inteiros, diferente do SIM que usa UAAA)
        CASE
            WHEN COALESCE(idade, 0) BETWEEN 0  AND 4   THEN '0-4'
            WHEN COALESCE(idade, 0) BETWEEN 5  AND 14  THEN '5-14'
            WHEN COALESCE(idade, 0) BETWEEN 15 AND 29  THEN '15-29'
            WHEN COALESCE(idade, 0) BETWEEN 30 AND 59  THEN '30-59'
            WHEN COALESCE(idade, 0) >= 60               THEN '60+'
            ELSE 'ND'
        END                                                    AS faixa_etaria,

        TRIM(nasc)::VARCHAR(8)                                AS nasc,
        UPPER(TRIM(raca_cor))::VARCHAR(1)                     AS raca_cor,

        -- ── Desfecho ──────────────────────────────────────────────────
        COALESCE(morte, 0)::SMALLINT                          AS morte,
        (COALESCE(morte, 0) = 1)::BOOLEAN                     AS is_obito,

        -- ── Financeiro ────────────────────────────────────────────────
        UPPER(TRIM(cobranca))::VARCHAR(2)                     AS cobranca,
        COALESCE(val_tot,  0.0)::NUMERIC(12, 2)               AS val_tot,
        COALESCE(val_sh,   0.0)::NUMERIC(12, 2)               AS val_sh,
        COALESCE(val_sp,   0.0)::NUMERIC(12, 2)               AS val_sp,
        COALESCE(val_sadt, 0.0)::NUMERIC(12, 2)               AS val_sadt,
        COALESCE(val_uci,  0.0)::NUMERIC(12, 2)               AS val_uci,

        -- ── Caráter de internação ─────────────────────────────────────
        LPAD(TRIM(car_int), 2, '0')::VARCHAR(2)               AS car_int,
        CASE LPAD(TRIM(car_int), 2, '0')
            WHEN '01' THEN 'ELETIVO'
            WHEN '06' THEN 'ELETIVO'
            WHEN '02' THEN 'URGENCIA'
            WHEN '03' THEN 'URGENCIA'
            WHEN '04' THEN 'URGENCIA'
            WHEN '05' THEN 'URGENCIA'
            WHEN '08' THEN 'PARTO'
            WHEN '09' THEN 'PARTO'
            ELSE 'OUTROS'
        END                                                    AS car_int_grupo,

        -- ── Gestão ────────────────────────────────────────────────────
        UPPER(TRIM(gestor_cod))::VARCHAR(6)                   AS gestor_cod,
        UPPER(TRIM(instru))::VARCHAR(1)                       AS instru,

        -- ── Arquivo origem ────────────────────────────────────────────
        UPPER(TRIM(uf_arquivo))::VARCHAR(2)                   AS uf_arquivo,
        ingested_at

    FROM source
    WHERE
        -- Período configurado (variáveis dbt)
        ano_cmpt IS NOT NULL
        AND ano_cmpt BETWEEN {{ var('ano_inicio') }} AND {{ var('ano_fim') }}
        AND mes_cmpt IS NOT NULL
        AND mes_cmpt BETWEEN 1 AND 12

        -- Qualidade mínima de localização
        AND municipio_res IS NOT NULL
        AND LENGTH(TRIM(municipio_res)) = 6
        AND TRIM(municipio_res) <> '000000'

        -- Diagnóstico principal obrigatório
        AND diag_princ IS NOT NULL
        AND LENGTH(TRIM(diag_princ)) >= 3
)

SELECT * FROM cleaned
