{{
    config(
        materialized='table',
        schema='marts',
        unique_key=['ano_cmpt', 'mes_cmpt', 'uf', 'municipio_cod'],
        indexes=[
            {'columns': ['ano_cmpt', 'mes_cmpt']},
            {'columns': ['uf', 'municipio_cod']},
        ]
    )
}}

-- -----------------------------------------------------------------------
-- mart_capacidade_hospitalar
--
-- Agrega dados do CNES (estabelecimentos + leitos) por município/período.
-- Combina dois grups do CNES:
--   ST — visão geral do estabelecimento (capacidades somadas, serviços)
--   LT — granularidade por tipo/especialidade de leito
--
-- Para leitos, a tabela LT é a fonte primária (mais detalhada).
-- Os campos de leito da ST servem de fallback quando LT não está disponível.
-- -----------------------------------------------------------------------

WITH estab AS (
    SELECT
        ano_cmpt,
        mes_cmpt,
        uf,
        municipio_cod,

        -- Contagem de estabelecimentos
        COUNT(DISTINCT cnes)                                              AS total_estabelecimentos,
        COUNT(DISTINCT CASE WHEN vincula_sus THEN cnes END)              AS estab_vinculados_sus,

        -- Leitos reportados na ST (fallback)
        SUM(qt_leitos_sus)                                                AS qt_leitos_sus_st,
        SUM(qt_leitos_nao_sus)                                            AS qt_leitos_nao_sus_st,
        SUM(qt_leitos_total)                                              AS qt_leitos_total_st,

        -- Capacidade ambulatorial e de consultas
        SUM(qt_amb_sus)                                                   AS qt_amb_sus,
        SUM(qt_amb_nao_sus)                                               AS qt_amb_nao_sus,
        SUM(qt_cons_sus)                                                  AS qt_cons_sus,

        -- Estabelecimentos com serviços especializados (flag > 0)
        SUM(CASE WHEN serv_uti    > 0 THEN 1 ELSE 0 END)                 AS estab_com_uti,
        SUM(CASE WHEN serv_emer   > 0 THEN 1 ELSE 0 END)                 AS estab_com_emergencia,
        SUM(CASE WHEN serv_cirg   > 0 THEN 1 ELSE 0 END)                 AS estab_com_cirurgia,
        SUM(CASE WHEN serv_obstet > 0 THEN 1 ELSE 0 END)                 AS estab_com_obstetricia,
        SUM(CASE WHEN serv_hemot  > 0 THEN 1 ELSE 0 END)                 AS estab_com_hemoterapia,
        SUM(CASE WHEN serv_diag   > 0 THEN 1 ELSE 0 END)                 AS estab_com_diagnostico

    FROM {{ ref('stg_cnes_estabelecimentos') }}
    GROUP BY 1, 2, 3, 4
),

-- -----------------------------------------------------------------------
-- Leitos detalhados (grupo LT) — pivot por tp_leito_grupo
-- -----------------------------------------------------------------------

leitos AS (
    SELECT
        ano_cmpt,
        mes_cmpt,
        uf,
        municipio_cod,

        SUM(qt_exist)                                                     AS leitos_total_exist,
        SUM(qt_sus)                                                       AS leitos_sus,
        SUM(qt_nao_sus)                                                   AS leitos_nao_sus,
        SUM(qt_contr)                                                     AS leitos_contratualizados,

        -- Pivot por grupo de leito
        SUM(CASE WHEN tp_leito_grupo = 'Cirúrgico'     THEN qt_exist ELSE 0 END) AS leitos_cirurgico,
        SUM(CASE WHEN tp_leito_grupo = 'Clínico'       THEN qt_exist ELSE 0 END) AS leitos_clinico,
        SUM(CASE WHEN tp_leito_grupo = 'Complementar'  THEN qt_exist ELSE 0 END) AS leitos_complementar,
        SUM(CASE WHEN tp_leito_grupo = 'Obstétrico'    THEN qt_exist ELSE 0 END) AS leitos_obstetrico,
        SUM(CASE WHEN tp_leito_grupo = 'Pediátrico'    THEN qt_exist ELSE 0 END) AS leitos_pediatrico,
        SUM(CASE WHEN tp_leito_grupo = 'Reabilitação'  THEN qt_exist ELSE 0 END) AS leitos_reabilitacao,
        SUM(CASE WHEN tp_leito_grupo = 'Outro/Ignorado' THEN qt_exist ELSE 0 END) AS leitos_outro,

        -- Leitos SUS por tipo (para análise de cobertura SUS por especialidade)
        SUM(CASE WHEN tp_leito_grupo = 'Cirúrgico'     THEN qt_sus ELSE 0 END)   AS leitos_sus_cirurgico,
        SUM(CASE WHEN tp_leito_grupo = 'Clínico'       THEN qt_sus ELSE 0 END)   AS leitos_sus_clinico,
        SUM(CASE WHEN tp_leito_grupo = 'Complementar'  THEN qt_sus ELSE 0 END)   AS leitos_sus_complementar,
        SUM(CASE WHEN tp_leito_grupo = 'Obstétrico'    THEN qt_sus ELSE 0 END)   AS leitos_sus_obstetrico,
        SUM(CASE WHEN tp_leito_grupo = 'Pediátrico'    THEN qt_sus ELSE 0 END)   AS leitos_sus_pediatrico,
        SUM(CASE WHEN tp_leito_grupo = 'Reabilitação'  THEN qt_sus ELSE 0 END)   AS leitos_sus_reabilitacao

    FROM {{ ref('stg_cnes_leitos') }}
    GROUP BY 1, 2, 3, 4
)

-- -----------------------------------------------------------------------
-- Resultado final: estabelecimentos LEFT JOIN leitos
-- -----------------------------------------------------------------------

SELECT
    e.ano_cmpt,
    e.mes_cmpt,
    e.uf,
    e.municipio_cod,

    -- ── Estabelecimentos ──────────────────────────────────────────────
    e.total_estabelecimentos,
    e.estab_vinculados_sus,
    CASE
        WHEN e.total_estabelecimentos > 0
        THEN ROUND(e.estab_vinculados_sus::NUMERIC / e.total_estabelecimentos * 100, 2)
        ELSE NULL
    END                                                                   AS pct_estab_sus,

    -- ── Capacidade ambulatorial ───────────────────────────────────────
    e.qt_amb_sus,
    e.qt_amb_nao_sus,
    (e.qt_amb_sus + e.qt_amb_nao_sus)                                     AS qt_amb_total,
    e.qt_cons_sus,

    -- ── Serviços especializados ───────────────────────────────────────
    e.estab_com_uti,
    e.estab_com_emergencia,
    e.estab_com_cirurgia,
    e.estab_com_obstetricia,
    e.estab_com_hemoterapia,
    e.estab_com_diagnostico,

    -- ── Leitos totais (LT preferencial, ST como fallback) ─────────────
    COALESCE(l.leitos_total_exist, e.qt_leitos_total_st)                  AS leitos_total,
    COALESCE(l.leitos_sus,         e.qt_leitos_sus_st)                    AS leitos_sus,
    COALESCE(l.leitos_nao_sus,     e.qt_leitos_nao_sus_st)                AS leitos_nao_sus,
    l.leitos_contratualizados,
    CASE
        WHEN COALESCE(l.leitos_total_exist, e.qt_leitos_total_st) > 0
        THEN ROUND(
            COALESCE(l.leitos_sus, e.qt_leitos_sus_st)::NUMERIC
            / COALESCE(l.leitos_total_exist, e.qt_leitos_total_st) * 100, 2)
        ELSE NULL
    END                                                                   AS pct_leitos_sus,

    -- ── Leitos por grupo (só disponível via LT) ───────────────────────
    l.leitos_cirurgico,
    l.leitos_clinico,
    l.leitos_complementar,
    l.leitos_obstetrico,
    l.leitos_pediatrico,
    l.leitos_reabilitacao,
    l.leitos_outro,

    -- ── Leitos SUS por grupo ─────────────────────────────────────────
    l.leitos_sus_cirurgico,
    l.leitos_sus_clinico,
    l.leitos_sus_complementar,
    l.leitos_sus_obstetrico,
    l.leitos_sus_pediatrico,
    l.leitos_sus_reabilitacao

FROM estab e
LEFT JOIN leitos l
    ON  e.ano_cmpt     = l.ano_cmpt
    AND e.mes_cmpt     = l.mes_cmpt
    AND e.uf           = l.uf
    AND e.municipio_cod = l.municipio_cod
