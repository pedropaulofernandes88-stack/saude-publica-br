{{
  config(
    materialized='table',
    schema='marts',
    alias='nacional_doencas',
    indexes=[
      {'columns': ['uf_sigla', 'ano'], 'unique': False},
      {'columns': ['regiao', 'ano'], 'unique': False},
      {'columns': ['agravo', 'ano'], 'unique': False},
      {'columns': ['ano', 'semana_epidemiologica'], 'unique': False},
    ]
  )
}}

/*
  Mart Nacional de Doenças e Agravos
  Fontes:
    - raw.sinan  (Sistema de Informação de Agravos de Notificação)
    - raw.sih_aih (Sistema de Informações Hospitalares — internações por CID)
  Granularidade: UF × Ano × Semana epidemiológica × Agravo/CID-10
  Escopo: todos os 27 estados, 2019–2024
*/

-- ============================================================
-- SINAN: Notificações de agravos
-- ============================================================
with sinan_raw as (

    select
        uf_sigla,
        ano,
        semana_epidemiologica,
        mes,

        -- Agravo normalizado
        upper(coalesce(agravo, 'IGNORADO'))  as agravo,

        -- CID-10 do agravo
        upper(left(coalesce(cid10, 'XXX'), 3)) as cid10_grupo,

        -- Evolução do caso
        case
            when evolucao = '1' then 'Cura'
            when evolucao = '2' then 'Óbito pelo agravo'
            when evolucao = '3' then 'Óbito por outras causas'
            when evolucao = '4' then 'Óbito em investigação'
            when evolucao = '5' then 'Ignorado'
            else                     'Ignorado'
        end as evolucao,

        count(*)                                    as notificacoes,
        count(*) filter (where evolucao = '2')      as obitos_agravo,
        count(*) filter (where confirmado = true)   as casos_confirmados,
        count(*) filter (where hospitalizado = '1') as hospitalizados

    from {{ source('raw', 'sinan') }}
    where ano between 2019 and 2024
      and uf_sigla is not null
    group by 1, 2, 3, 4, 5, 6, 7

),

-- ============================================================
-- SIH/AIH: Internações por causa principal (CID-10)
-- ============================================================
sih_raw as (

    select
        uf_sigla,
        ano,
        mes,

        -- CID-10 principal (3 chars)
        upper(left(coalesce(diag_princ, 'XXX'), 3)) as cid10_grupo,

        -- Complexidade da internação
        coalesce(complexidade, 'ND') as complexidade,

        count(*)                               as internacoes,
        count(*) filter (where obito = true)   as obitos_internacao,
        sum(val_tot)                            as valor_total_brl,
        round(avg(dias_perm)::numeric, 1)       as media_dias_internacao,
        sum(dias_perm)                          as total_dias_internacao

    from {{ source('raw', 'sih_aih') }}
    where ano between 2019 and 2024
      and uf_sigla is not null
    group by 1, 2, 3, 4, 5

),

-- ============================================================
-- Cruzar SINAN com SIH para agravos com internação
-- ============================================================
agravos_internacoes as (

    select
        s.uf_sigla,
        s.ano,
        s.semana_epidemiologica,
        s.mes,
        s.agravo,
        s.cid10_grupo,
        s.evolucao,
        s.notificacoes,
        s.obitos_agravo,
        s.casos_confirmados,
        s.hospitalizados,

        -- Dados de internação do SIH (JOIN por UF + Ano + Mês + CID)
        coalesce(h.internacoes, 0)              as internacoes_sih,
        coalesce(h.obitos_internacao, 0)        as obitos_internacao_sih,
        coalesce(h.valor_total_brl, 0)          as valor_internacoes_brl,
        h.media_dias_internacao,
        coalesce(h.total_dias_internacao, 0)    as total_dias_internacao,
        h.complexidade

    from sinan_raw s
    left join sih_raw h
        on  s.uf_sigla   = h.uf_sigla
        and s.ano        = h.ano
        and s.mes        = h.mes
        and s.cid10_grupo = h.cid10_grupo

),

regioes as (

    select
        sigla_uf          as uf_sigla,
        nome_uf,
        regiao,
        populacao_estimada
    from {{ ref('dim_estados') }}

),

doencas_com_regiao as (

    select
        a.*,
        r.nome_uf,
        r.regiao,
        r.populacao_estimada,

        -- Taxa de incidência por 100 mil hab
        round(
            a.casos_confirmados::numeric / nullif(r.populacao_estimada, 0) * 100000,
            2
        ) as taxa_incidencia_100k,

        -- Taxa de notificação por 100 mil hab
        round(
            a.notificacoes::numeric / nullif(r.populacao_estimada, 0) * 100000,
            2
        ) as taxa_notificacao_100k,

        -- Proporção de hospitalização
        round(
            a.hospitalizados::numeric / nullif(a.casos_confirmados, 0) * 100,
            1
        ) as taxa_hospitalizacao_pct,

        -- Letalidade (óbitos / confirmados)
        round(
            a.obitos_agravo::numeric / nullif(a.casos_confirmados, 0) * 100,
            2
        ) as taxa_letalidade_pct,

        -- Custo médio por internação
        round(
            a.valor_internacoes_brl / nullif(a.internacoes_sih, 0),
            2
        ) as custo_medio_internacao_brl

    from agravos_internacoes a
    left join regioes r using (uf_sigla)

),

yoy as (

    select
        *,

        -- Notificações YoY
        lag(notificacoes) over (
            partition by uf_sigla, agravo, semana_epidemiologica
            order by ano
        ) as notificacoes_ano_anterior,

        -- Casos confirmados YoY
        lag(casos_confirmados) over (
            partition by uf_sigla, agravo, semana_epidemiologica
            order by ano
        ) as casos_confirmados_ano_anterior,

        -- Taxa incidência YoY
        lag(taxa_incidencia_100k) over (
            partition by uf_sigla, agravo, semana_epidemiologica
            order by ano
        ) as taxa_incidencia_ano_anterior

    from doencas_com_regiao

),

final as (

    select
        -- Dimensões geográficas
        uf_sigla,
        nome_uf,
        regiao,

        -- Dimensões temporais
        ano,
        semana_epidemiologica,
        mes,

        -- Dimensões de agravo / doença
        agravo,
        cid10_grupo,
        evolucao,
        complexidade,

        -- Métricas absolutas SINAN
        notificacoes,
        casos_confirmados,
        hospitalizados,
        obitos_agravo,

        -- Métricas absolutas SIH
        internacoes_sih,
        obitos_internacao_sih,
        total_dias_internacao,
        media_dias_internacao,
        valor_internacoes_brl,

        -- Métricas combinadas
        obitos_agravo + obitos_internacao_sih as total_obitos_estimado,

        -- Taxas e proporções
        populacao_estimada,
        taxa_incidencia_100k,
        taxa_notificacao_100k,
        taxa_hospitalizacao_pct,
        taxa_letalidade_pct,
        custo_medio_internacao_brl,

        -- Variação YoY: notificações
        notificacoes - notificacoes_ano_anterior as variacao_notificacoes_yoy,
        case
            when notificacoes_ano_anterior > 0
            then round(
                (notificacoes - notificacoes_ano_anterior)::numeric
                / notificacoes_ano_anterior * 100, 2
            )
        end as variacao_notificacoes_yoy_pct,

        -- Variação YoY: casos confirmados
        casos_confirmados - casos_confirmados_ano_anterior as variacao_casos_yoy,
        case
            when casos_confirmados_ano_anterior > 0
            then round(
                (casos_confirmados - casos_confirmados_ano_anterior)::numeric
                / casos_confirmados_ano_anterior * 100, 2
            )
        end as variacao_casos_yoy_pct,

        -- Variação YoY: taxa de incidência
        round(
            taxa_incidencia_100k - taxa_incidencia_ano_anterior, 2
        ) as variacao_taxa_incidencia_yoy,

        -- Alerta epidemiológico (se incidência YoY > 20%)
        case
            when casos_confirmados_ano_anterior > 0
             and (casos_confirmados - casos_confirmados_ano_anterior)::numeric
                 / casos_confirmados_ano_anterior > 0.20
            then true
            else false
        end as alerta_epidemiologico,

        -- Metadados
        current_timestamp as atualizado_em

    from yoy

)

select * from final
