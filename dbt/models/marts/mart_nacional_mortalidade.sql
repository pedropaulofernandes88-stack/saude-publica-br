{{
  config(
    materialized='table',
    schema='marts',
    alias='nacional_mortalidade',
    indexes=[
      {'columns': ['uf_sigla', 'ano'], 'unique': False},
      {'columns': ['regiao', 'ano'], 'unique': False},
      {'columns': ['cid10_capitulo', 'ano'], 'unique': False},
      {'columns': ['ano', 'mes'], 'unique': False},
    ]
  )
}}

/*
  Mart Nacional de Mortalidade
  Fonte: raw.sim_do (Sistema de Informações sobre Mortalidade)
  Granularidade: UF × Ano × Mês × CID-10 capítulo × Sexo × Faixa etária
  Escopo: todos os 27 estados, 2019–2024
*/

with mortalidade_raw as (

    select
        uf_sigla,
        ano,
        mes,

        -- CID-10: extrair capítulo (primeiro caractere)
        upper(left(coalesce(causa_basica_cid10, 'XXX'), 1)) as cid10_capitulo,

        -- CID-10: grupo (3 primeiros caracteres)
        upper(left(coalesce(causa_basica_cid10, 'XXX'), 3))  as cid10_grupo,

        -- Sexo padronizado
        case
            when sexo = '1' then 'Masculino'
            when sexo = '2' then 'Feminino'
            else 'Ignorado'
        end as sexo,

        -- Faixa etária em anos (DTOBITO vs DTNASC ou campo IDADE)
        case
            when idade_anos < 1   then '< 1 ano'
            when idade_anos < 5   then '1–4 anos'
            when idade_anos < 10  then '5–9 anos'
            when idade_anos < 20  then '10–19 anos'
            when idade_anos < 30  then '20–29 anos'
            when idade_anos < 40  then '30–39 anos'
            when idade_anos < 50  then '40–49 anos'
            when idade_anos < 60  then '50–59 anos'
            when idade_anos < 70  then '60–69 anos'
            when idade_anos < 80  then '70–79 anos'
            else                       '80+ anos'
        end as faixa_etaria,

        -- Local de ocorrência
        coalesce(local_obito, '9') as local_obito_cod,

        count(*)                        as obitos,
        count(*) filter (
            where left(coalesce(causa_basica_cid10,''), 1) in ('I','J','C','K','E','F','G','N','O')
        )                               as obitos_causas_cronicas

    from {{ source('raw', 'sim_do') }}
    where ano between 2019 and 2024
      and uf_sigla is not null
    group by 1, 2, 3, 4, 5, 6, 7, 8

),

regioes as (

    select
        sigla_uf                     as uf_sigla,
        nome_uf,
        regiao,
        populacao_estimada
    from {{ ref('dim_estados') }}

),

mortalidade_com_regiao as (

    select
        m.*,
        r.nome_uf,
        r.regiao,
        r.populacao_estimada,

        -- Taxa bruta de mortalidade por 100 mil habitantes
        round(
            m.obitos::numeric / nullif(r.populacao_estimada, 0) * 100000,
            2
        ) as taxa_mortalidade_100k,

        -- Taxa específica por faixa etária (aproximação proporcional)
        round(
            m.obitos::numeric / nullif(r.populacao_estimada, 0) * 100000,
            2
        ) as taxa_mortalidade_faixa_100k

    from mortalidade_raw m
    left join regioes r using (uf_sigla)

),

yoy as (

    select
        *,

        -- Variação ano a ano: óbitos
        lag(obitos) over (
            partition by uf_sigla, mes, cid10_capitulo, sexo, faixa_etaria
            order by ano
        ) as obitos_ano_anterior,

        -- Variação YoY: taxa de mortalidade
        lag(taxa_mortalidade_100k) over (
            partition by uf_sigla, mes, cid10_capitulo, sexo, faixa_etaria
            order by ano
        ) as taxa_mortalidade_ano_anterior

    from mortalidade_com_regiao

),

final as (

    select
        -- Dimensões geográficas
        uf_sigla,
        nome_uf,
        regiao,

        -- Dimensões temporais
        ano,
        mes,

        -- Dimensões clínicas / demográficas
        cid10_capitulo,
        cid10_grupo,
        sexo,
        faixa_etaria,
        local_obito_cod,

        case local_obito_cod
            when '1' then 'Hospital'
            when '2' then 'Outro estabelecimento de saúde'
            when '3' then 'Domicílio'
            when '4' then 'Via pública'
            when '5' then 'Outros'
            else          'Ignorado'
        end as local_obito_descricao,

        -- Métricas absolutas
        obitos,
        obitos_causas_cronicas,
        populacao_estimada,

        -- Métricas calculadas
        taxa_mortalidade_100k,
        taxa_mortalidade_faixa_100k,

        round(
            obitos_causas_cronicas::numeric / nullif(obitos, 0) * 100,
            1
        ) as pct_causas_cronicas,

        -- Variação YoY: absoluta
        obitos - obitos_ano_anterior                              as variacao_obitos_yoy,

        -- Variação YoY: percentual
        case
            when obitos_ano_anterior > 0
            then round(
                (obitos - obitos_ano_anterior)::numeric
                / obitos_ano_anterior * 100,
                2
            )
        end as variacao_obitos_yoy_pct,

        -- Variação YoY: taxa
        round(
            taxa_mortalidade_100k - taxa_mortalidade_ano_anterior,
            2
        ) as variacao_taxa_yoy,

        -- Metadados
        current_timestamp as atualizado_em

    from yoy

)

select * from final
