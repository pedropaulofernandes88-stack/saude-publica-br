-- int_sia_pa_enriched.sql
-- ⭐ MODELO CENTRAL: SIA/PA enriquecido com todas as referências
-- Todos os marts derivam deste modelo

{{ config(
    materialized='table',
    schema='intermediate',
    indexes=[
        {'columns': ['mes_competencia', 'uf_sigla']},
        {'columns': ['mes_competencia', 'municipio_cod']},
        {'columns': ['proc_id', 'mes_competencia']},
        {'columns': ['capitulo_cid', 'mes_competencia', 'uf_sigla']},
    ]
) }}

SELECT
    -- Dimensão temporal
    pa.mes_competencia,
    pa.ano_competencia,
    pa.mes_num,

    -- Procedimento
    pa.proc_id,
    pa.qtd_aprovada,
    pa.valor_aprovado,
    pa.tipo_financiamento,
    pa.categoria_atendimento,

    -- CID
    pa.cid_primario,
    c.descricao_cid,
    c.grupo_cid,
    c.nome_grupo_cid,
    c.capitulo_cid,
    c.nome_capitulo_cid,

    -- SIGTAP
    s.nome_procedimento,
    s.complexidade,
    s.complexidade_label,
    s.peso_complexidade,
    s.valor_sp,
    s.grupo_proc,
    s.nome_grupo  AS nome_grupo_proc,

    -- Localização
    pa.municipio_cod,
    pa.uf_sigla,
    m.nome_municipio,
    m.uf_nome,
    m.regiao,
    m.capital,
    m.latitude,
    m.longitude,

    -- Paciente
    pa.sexo,
    pa.faixa_etaria,

    -- População (para taxas por 10k)
    p.populacao_estimada

FROM {{ ref('stg_sia_pa') }} pa

-- SIGTAP: enriquece com nome, complexidade, valores
LEFT JOIN {{ ref('int_proc_complexidade') }} s
    ON pa.proc_id = s.proc_id

-- CID-10: enriquece com descrição, grupo, capítulo
LEFT JOIN {{ ref('stg_ref_cid10') }} c
    ON pa.cid_primario = c.codigo_cid

-- Municípios: nome, UF, região, coordenadas
LEFT JOIN {{ ref('stg_ibge_municipios') }} m
    ON pa.municipio_cod = m.municipio_cod

-- População: estimativa do ano de competência
LEFT JOIN {{ ref('int_pop_municipio_mes') }} p
    ON pa.municipio_cod  = p.municipio_cod
   AND pa.mes_competencia = p.mes_competencia

WHERE pa.ano_competencia BETWEEN {{ var('ano_inicio') }} AND {{ var('ano_fim') }}
