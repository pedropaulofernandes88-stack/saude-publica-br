{{
  config(
    materialized  = 'table',
    schema        = 'marts',
    alias         = 'nacional_producao',
    indexes       = [
      {'columns': ['uf_sigla', 'ano'], 'unique': false},
      {'columns': ['regiao', 'ano'],   'unique': false},
      {'columns': ['ano', 'mes'],      'unique': false},
    ],
    tags          = ['nacional', 'producao', 'fase10'],
  )
}}

/*
  mart_nacional_producao
  ======================
  Produção Ambulatorial (SIA/PA) agregada para todos os 27 estados, 2019–2024.
  Granularidade: UF × Ano × Mês × Complexidade

  Métricas:
    - procedimentos_total    : soma de procedimentos aprovados
    - valor_total_brl        : soma do valor aprovado em R$
    - valor_medio_proc       : ticket médio por procedimento
    - atendimentos_estimados : proxy de atendimentos únicos (por CNS)
    - variacao_yoy_pct       : variação ano-a-ano em procedimentos
*/

with

-- Staging base: produção ambulatorial
producao_raw as (
    select
        uf_sigla,
        competencia_ano                              as ano,
        competencia_mes                              as mes,
        coalesce(complexidade, 'NA')                 as complexidade,
        sum(quantidade_aprovada)                     as procedimentos,
        sum(valor_aprovado)                          as valor_brl,
        count(distinct cns_pac)                      as pacientes_unicos,
        count(*)                                     as registros_raw
    from {{ source('raw', 'sia_pa') }}
    where
        competencia_ano between 2019 and 2024
        and uf_sigla is not null
        and quantidade_aprovada > 0
    group by 1, 2, 3, 4
),

-- Mapa UF → Região
regioes as (
    select uf_sigla, regiao, populacao_estimada
    from {{ ref('dim_estados') }}
),

-- Agrega com atributos geográficos
producao_com_regiao as (
    select
        p.*,
        r.regiao,
        r.populacao_estimada,
        round(p.valor_brl::numeric / nullif(p.procedimentos, 0), 2)
            as valor_medio_proc
    from producao_raw p
    left join regioes r using (uf_sigla)
),

-- Variação Ano-a-Ano (window function sobre UF × Mês × Complexidade)
yoy as (
    select
        *,
        lag(procedimentos) over (
            partition by uf_sigla, mes, complexidade
            order by ano
        ) as procedimentos_ano_anterior,
        lag(valor_brl) over (
            partition by uf_sigla, mes, complexidade
            order by ano
        ) as valor_ano_anterior
    from producao_com_regiao
),

-- Cálculo final
final as (
    select
        uf_sigla,
        regiao,
        ano,
        mes,
        complexidade,
        procedimentos                                           as procedimentos_total,
        round(valor_brl::numeric, 2)                           as valor_total_brl,
        valor_medio_proc,
        pacientes_unicos                                        as atendimentos_estimados,
        populacao_estimada,
        round(
            (procedimentos::numeric / nullif(populacao_estimada, 0)) * 1000,
            2
        )                                                       as taxa_proc_por_1k_hab,
        case
            when procedimentos_ano_anterior > 0
            then round(
                (procedimentos::numeric - procedimentos_ano_anterior)
                / procedimentos_ano_anterior * 100,
                2
            )
        end                                                     as variacao_yoy_pct,
        registros_raw,
        now()                                                   as _dbt_updated_at
    from yoy
)

select * from final
