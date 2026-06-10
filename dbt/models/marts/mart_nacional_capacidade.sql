{{
  config(
    materialized='table',
    schema='marts',
    alias='nacional_capacidade',
    indexes=[
      {'columns': ['uf_sigla', 'ano'], 'unique': False},
      {'columns': ['regiao', 'ano'], 'unique': False},
      {'columns': ['tipo_unidade', 'ano'], 'unique': False},
      {'columns': ['ano'], 'unique': False},
    ]
  )
}}

/*
  Mart Nacional de Capacidade Instalada
  Fonte: raw.cnes (Cadastro Nacional de Estabelecimentos de Saúde)
  Granularidade: UF × Ano × Tipo de unidade
  Escopo: todos os 27 estados, 2019–2024
*/

with cnes_raw as (

    select
        uf_sigla,
        ano,
        mes,

        -- Tipo de unidade padronizado
        coalesce(tp_unidade, '00') as tipo_unidade_cod,

        -- Código CNES único por estabelecimento
        codigo_cnes,

        -- Leitos
        coalesce(leitos_sus, 0)              as leitos_sus,
        coalesce(leitos_nao_sus, 0)          as leitos_nao_sus,
        coalesce(leitos_complementares, 0)   as leitos_complementares,

        -- UTIs
        coalesce(uti_adulto_sus, 0)          as uti_adulto_sus,
        coalesce(uti_neonatal_sus, 0)        as uti_neonatal_sus,
        coalesce(uti_pediatrica_sus, 0)      as uti_pediatrica_sus,

        -- Recursos humanos
        coalesce(medicos, 0)                 as medicos,
        coalesce(enfermeiros, 0)             as enfermeiros,
        coalesce(tecnicos_enfermagem, 0)     as tecnicos_enfermagem,

        -- Equipamentos (campos representativos)
        coalesce(equipamentos_tomografia, 0) as equipamentos_tomografia,
        coalesce(equipamentos_mamografia, 0) as equipamentos_mamografia,
        coalesce(equipamentos_ultrassom, 0)  as equipamentos_ultrassom,

        -- Indicador de atividade
        coalesce(ativa, true)                as ativa

    from {{ source('raw', 'cnes') }}
    where ano between 2019 and 2024
      and uf_sigla is not null

),

-- Agregar ao nível UF × Ano × Mês × Tipo (usar mês 12 ou máximo disponível como snapshot anual)
cnes_snapshot_anual as (

    -- Último mês disponível por ano como snapshot de capacidade
    select distinct on (uf_sigla, ano, tipo_unidade_cod)
        uf_sigla,
        ano,
        tipo_unidade_cod,
        mes
    from cnes_raw
    order by uf_sigla, ano, tipo_unidade_cod, mes desc

),

cnes_agregado as (

    select
        c.uf_sigla,
        c.ano,
        c.tipo_unidade_cod,
        s.mes as mes_referencia,

        -- Contagem de estabelecimentos únicos
        count(distinct c.codigo_cnes)                              as estabelecimentos,
        count(distinct c.codigo_cnes) filter (where c.ativa)       as estabelecimentos_ativos,

        -- Leitos
        sum(c.leitos_sus)                                          as leitos_sus,
        sum(c.leitos_nao_sus)                                      as leitos_nao_sus,
        sum(c.leitos_complementares)                               as leitos_complementares,
        sum(c.leitos_sus + c.leitos_nao_sus)                       as leitos_totais,

        -- UTI SUS
        sum(c.uti_adulto_sus)                                      as uti_adulto_sus,
        sum(c.uti_neonatal_sus)                                    as uti_neonatal_sus,
        sum(c.uti_pediatrica_sus)                                  as uti_pediatrica_sus,
        sum(c.uti_adulto_sus + c.uti_neonatal_sus + c.uti_pediatrica_sus) as uti_total_sus,

        -- RH
        sum(c.medicos)                                             as medicos,
        sum(c.enfermeiros)                                         as enfermeiros,
        sum(c.tecnicos_enfermagem)                                 as tecnicos_enfermagem,

        -- Equipamentos
        sum(c.equipamentos_tomografia)                             as equipamentos_tomografia,
        sum(c.equipamentos_mamografia)                             as equipamentos_mamografia,
        sum(c.equipamentos_ultrassom)                              as equipamentos_ultrassom

    from cnes_raw c
    inner join cnes_snapshot_anual s
        on  c.uf_sigla          = s.uf_sigla
        and c.ano               = s.ano
        and c.tipo_unidade_cod  = s.tipo_unidade_cod
        and c.mes               = s.mes
    group by 1, 2, 3, 4

),

regioes as (

    select
        sigla_uf          as uf_sigla,
        nome_uf,
        regiao,
        populacao_estimada
    from {{ ref('dim_estados') }}

),

capacidade_com_regiao as (

    select
        ca.*,
        r.nome_uf,
        r.regiao,
        r.populacao_estimada,

        -- Taxas por 1.000 habitantes
        round(ca.leitos_sus::numeric        / nullif(r.populacao_estimada, 0) * 1000, 3) as taxa_leitos_sus_1k,
        round(ca.leitos_totais::numeric     / nullif(r.populacao_estimada, 0) * 1000, 3) as taxa_leitos_totais_1k,
        round(ca.uti_total_sus::numeric     / nullif(r.populacao_estimada, 0) * 1000, 3) as taxa_uti_sus_1k,
        round(ca.medicos::numeric           / nullif(r.populacao_estimada, 0) * 1000, 3) as taxa_medicos_1k,
        round(ca.estabelecimentos::numeric  / nullif(r.populacao_estimada, 0) * 10000, 3) as taxa_estab_10k

    from cnes_agregado ca
    left join regioes r using (uf_sigla)

),

yoy as (

    select
        *,

        -- Leitos SUS YoY
        lag(leitos_sus) over (
            partition by uf_sigla, tipo_unidade_cod
            order by ano
        ) as leitos_sus_ano_anterior,

        -- Médicos YoY
        lag(medicos) over (
            partition by uf_sigla, tipo_unidade_cod
            order by ano
        ) as medicos_ano_anterior,

        -- Estabelecimentos YoY
        lag(estabelecimentos) over (
            partition by uf_sigla, tipo_unidade_cod
            order by ano
        ) as estabelecimentos_ano_anterior

    from capacidade_com_regiao

),

final as (

    select
        -- Dimensões geográficas
        uf_sigla,
        nome_uf,
        regiao,

        -- Dimensões temporais
        ano,
        mes_referencia,

        -- Dimensão de tipo de unidade
        tipo_unidade_cod,

        case tipo_unidade_cod
            when '01' then 'Posto de Saúde'
            when '02' then 'Centro de Saúde / Unidade Básica'
            when '04' then 'Policlínica'
            when '05' then 'Hospital Geral'
            when '06' then 'Hospital Especializado'
            when '07' then 'Centro de Reabilitação'
            when '15' then 'UPA / Pronto Atendimento'
            when '20' then 'Pronto-Socorro Geral'
            when '21' then 'Pronto-Socorro Especializado'
            when '36' then 'Clínica / Centro de Especialidade'
            when '39' then 'CAPS'
            when '61' then 'Centro de Saúde Mental'
            when '69' then 'Centro de Atenção Hemoterapia / Hematológica'
            when '70' then 'Centro de Atenção Psicossocial Álcool e Drogas'
            when '71' then 'Centro de Atenção Psicossocial Infanto Juvenil'
            when '72' then 'UBS Fluvial'
            when '73' then 'Academia da Saúde'
            when '74' then 'Central de Regulação Médica das Urgências'
            when '75' then 'Telessaúde'
            when '76' then 'Central de Regulação'
            when '78' then 'UBS - Unidade Básica Saúde'
            when '79' then 'Oficina Ortopédica'
            when '80' then 'Laboratório de Saúde Pública'
            when '81' then 'Laboratório Central de Saúde Pública'
            when '82' then 'Farmácia'
            when '85' then 'CEREST'
            else          concat('Tipo ', tipo_unidade_cod)
        end as tipo_unidade_descricao,

        -- Estabelecimentos
        estabelecimentos,
        estabelecimentos_ativos,
        round(
            estabelecimentos_ativos::numeric / nullif(estabelecimentos, 0) * 100, 1
        ) as pct_estabelecimentos_ativos,

        -- Leitos
        leitos_sus,
        leitos_nao_sus,
        leitos_complementares,
        leitos_totais,

        -- UTI SUS
        uti_adulto_sus,
        uti_neonatal_sus,
        uti_pediatrica_sus,
        uti_total_sus,

        -- Recursos humanos
        medicos,
        enfermeiros,
        tecnicos_enfermagem,
        round(enfermeiros::numeric / nullif(medicos, 0), 2) as razao_enfermeiros_medicos,

        -- Equipamentos
        equipamentos_tomografia,
        equipamentos_mamografia,
        equipamentos_ultrassom,

        -- População de referência
        populacao_estimada,

        -- Taxas por habitante
        taxa_leitos_sus_1k,
        taxa_leitos_totais_1k,
        taxa_uti_sus_1k,
        taxa_medicos_1k,
        taxa_estab_10k,

        -- Variação YoY: leitos SUS
        leitos_sus - leitos_sus_ano_anterior as variacao_leitos_sus_yoy,
        case
            when leitos_sus_ano_anterior > 0
            then round(
                (leitos_sus - leitos_sus_ano_anterior)::numeric
                / leitos_sus_ano_anterior * 100, 2
            )
        end as variacao_leitos_sus_yoy_pct,

        -- Variação YoY: médicos
        medicos - medicos_ano_anterior as variacao_medicos_yoy,
        case
            when medicos_ano_anterior > 0
            then round(
                (medicos - medicos_ano_anterior)::numeric
                / medicos_ano_anterior * 100, 2
            )
        end as variacao_medicos_yoy_pct,

        -- Variação YoY: estabelecimentos
        estabelecimentos - estabelecimentos_ano_anterior as variacao_estabelecimentos_yoy,

        -- Metadados
        current_timestamp as atualizado_em

    from yoy

)

select * from final
