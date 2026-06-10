{{ config(materialized='view', schema='staging') }}

WITH source AS (
    SELECT * FROM {{ source('raw', 'cnes_estabelecimentos') }}
),

cleaned AS (
    SELECT
        -- Identificação
        COALESCE(TRIM(cnes), '')::TEXT                AS cnes,
        ano_cmpt::SMALLINT                            AS ano_cmpt,
        mes_cmpt::SMALLINT                            AS mes_cmpt,
        UPPER(TRIM(uf))::CHAR(2)                     AS uf,

        -- Localização
        TRIM(municipio_cod)::TEXT                     AS municipio_cod,
        TRIM(municipio_nome)::TEXT                    AS municipio_nome,
        TRIM(cep)::TEXT                               AS cep,
        TRIM(tp_unid)::TEXT                           AS tp_unid,
        TRIM(tp_unid_desc)::TEXT                      AS tp_unid_desc,

        -- Identificação do prestador
        TRIM(cnpj_mantenedora)::TEXT                  AS cnpj_mantenedora,
        UPPER(TRIM(pf_pj))::CHAR(1)                  AS pf_pj,
        TRIM(tp_prest)::TEXT                          AS tp_prest,

        -- Esfera administrativa
        TRIM(esfera_adm)::TEXT                        AS esfera_adm,
        TRIM(ret_obrig)::TEXT                         AS ret_obrig,

        -- Natureza jurídica e nível
        TRIM(nat_jur)::TEXT                           AS nat_jur,
        TRIM(nivel_dep)::TEXT                         AS nivel_dep,
        UPPER(TRIM(tp_gestao))::TEXT                  AS tp_gestao,

        -- Capacidades
        COALESCE(qt_leitos_sus,   0)::SMALLINT        AS qt_leitos_sus,
        COALESCE(qt_leitos_nao_sus, 0)::SMALLINT      AS qt_leitos_nao_sus,
        COALESCE(qt_amb_sus,      0)::SMALLINT        AS qt_amb_sus,
        COALESCE(qt_amb_nao_sus,  0)::SMALLINT        AS qt_amb_nao_sus,
        COALESCE(qt_cons_sus,     0)::SMALLINT        AS qt_cons_sus,

        -- Serviços especializados (flags 0/1)
        COALESCE(serv_uti,    0)::SMALLINT            AS serv_uti,
        COALESCE(serv_emer,   0)::SMALLINT            AS serv_emer,
        COALESCE(serv_cirg,   0)::SMALLINT            AS serv_cirg,
        COALESCE(serv_obstet, 0)::SMALLINT            AS serv_obstet,
        COALESCE(serv_hemot,  0)::SMALLINT            AS serv_hemot,
        COALESCE(serv_diag,   0)::SMALLINT            AS serv_diag,

        -- Vínculo SUS
        UPPER(TRIM(vinc_sus))::CHAR(1)               AS vinc_sus,

        -- Metadados
        UPPER(TRIM(uf_arquivo))::CHAR(2)             AS uf_arquivo,

        -- Colunas derivadas
        (qt_leitos_sus + qt_leitos_nao_sus)           AS qt_leitos_total,

        CASE esfera_adm
            WHEN '1' THEN 'Federal'
            WHEN '2' THEN 'Estadual'
            WHEN '3' THEN 'Municipal'
            WHEN '4' THEN 'Privado'
            ELSE 'Outro/Ignorado'
        END                                           AS esfera_adm_desc,

        CASE tp_gestao
            WHEN 'E' THEN 'Estadual'
            WHEN 'M' THEN 'Municipal'
            WHEN 'D' THEN 'Dupla'
            WHEN 'S' THEN 'Sem gestão'
            ELSE 'Outro/Ignorado'
        END                                           AS tp_gestao_desc,

        (UPPER(TRIM(vinc_sus)) = 'S')::BOOLEAN       AS vincula_sus

    FROM source
    WHERE cnes IS NOT NULL
      AND ano_cmpt IS NOT NULL
      AND ano_cmpt BETWEEN {{ var('ano_inicio') }} AND {{ var('ano_fim') }}
      AND uf IS NOT NULL
      AND municipio_cod IS NOT NULL
      AND LENGTH(TRIM(municipio_cod)) = 6
)

SELECT * FROM cleaned
