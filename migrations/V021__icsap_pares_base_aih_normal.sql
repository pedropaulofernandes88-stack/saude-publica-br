-- =============================================================================
-- V021 — mart_icsap_pares: parâmetros de custo/permanência sobre AIH normal
-- =============================================================================
-- A view derivava custo_medio e permanencia_media de sum(valor_total)/sum(internacoes)
-- sobre mart_internacoes_agravo — ou seja, incluindo a AIH de continuação (IDENT=5),
-- a definição antiga. Anular as colunas do mart não a atingia, porque ela recalcula
-- a partir das somas. Passa a usar a base de AIH normal, como o resto do projeto.
--
-- Enquanto o reprocessamento do SIH não termina, valor_normal/aih_normal são NULL e a
-- view devolve NULL em permanencia_media_icsap_ref, custo_medio_icsap_ref,
-- custo_associado_reais, leitos_dia_associados e leitos_equivalentes_ano — que é o
-- comportamento desejado: melhor vazio do que número com a definição errada. A
-- comparação epidemiológica em si (pct_icsap, internacoes_acima_pares) segue intacta.
--
-- Depende de: V016 (definição original), V020 (colunas por IDENT)
-- =============================================================================

CREATE OR REPLACE VIEW public.mart_icsap_pares AS
WITH parametros AS (
  -- Custo e permanência por internação ICSAP, derivados dos agravos traçadores
  -- que constam da Lista Brasileira (Portaria MS 221/2008). Fica como CTE, e não
  -- como constante, para acompanhar o dado quando o SIH for atualizado.
  -- VIÉS CONHECIDO: estes 6 traçadores pendem para o lado caro da lista (AVC e
  -- ICC são caros e volumosos) e as condições baratas da lista completa
  -- (gastroenterite, infecção urinária, anemia) não estão representadas. O valor
  -- em reais é um TETO, não uma média fiel.
  -- Base de AIH normal (IDENT<>5): a AIH de continuação fraciona uma internação
  -- longa em várias linhas e inflaria a permanência por episódio.
  SELECT
    sum(valor_normal) / nullif(sum(aih_normal), 0)                     AS custo_medio,
    sum(dias_permanencia_normal)::numeric / nullif(sum(aih_normal), 0) AS permanencia_media
  FROM mart_internacoes_agravo
  WHERE agravo IN ('asma','dpoc','pneumonia','diabetes','icc','avc')
),
base AS (
  SELECT
    i.municipio_cod, i.municipio_nome, i.uf_sigla, i.regiao, i.ano,
    i.internacoes_total, i.internacoes_icsap, i.pct_icsap, i.icsap_100k, i.populacao,
    c.cluster, c.perfil,
    CASE
      WHEN c.cluster IS NOT NULL THEN 'arquetipo:' || c.cluster::text
      ELSE 'faixa:' || coalesce(i.regiao, '?') || '|' ||
           CASE WHEN i.populacao IS NULL  THEN '?'
                WHEN i.populacao <  20000 THEN 'ate20k'
                WHEN i.populacao <  50000 THEN '20a50k'
                WHEN i.populacao < 100000 THEN '50a100k'
                WHEN i.populacao < 500000 THEN '100a500k'
                ELSE '500k+' END
    END AS grupo_id,
    CASE WHEN c.cluster IS NOT NULL THEN 'arquétipo de saúde (k-means)'
         ELSE 'faixa populacional × região' END AS criterio_pares
  FROM mart_icsap_municipio i
  LEFT JOIN dim_cluster_municipio c ON c.municipio_cod = i.municipio_cod
),
medianas AS (
  -- Municípios com pouquíssimas internações têm proporção instável e
  -- contaminariam a referência do grupo; ficam fora do cálculo da mediana, mas
  -- continuam recebendo a própria comparação (sinalizada em amostra_pequena).
  SELECT grupo_id,
         percentile_cont(0.5)  WITHIN GROUP (ORDER BY pct_icsap) AS mediana_pct_icsap,
         percentile_cont(0.25) WITHIN GROUP (ORDER BY pct_icsap) AS p25_pct_icsap,
         count(*) AS n_pares
  FROM base
  WHERE internacoes_total >= 100 AND pct_icsap IS NOT NULL
  GROUP BY grupo_id
),
calc AS (
  SELECT
    b.*, m.n_pares, m.mediana_pct_icsap, m.p25_pct_icsap,
    p.custo_medio, p.permanencia_media,
    greatest(0, b.internacoes_total * (b.pct_icsap - m.mediana_pct_icsap) / 100.0) AS excedente,
    greatest(0, b.internacoes_total * (b.pct_icsap - m.p25_pct_icsap) / 100.0)     AS excedente_p25
  FROM base b
  JOIN medianas m ON m.grupo_id = b.grupo_id
  CROSS JOIN parametros p
  WHERE b.pct_icsap IS NOT NULL
)
SELECT
  municipio_cod, municipio_nome, uf_sigla, regiao, ano,
  populacao, internacoes_total, internacoes_icsap, pct_icsap, icsap_100k,
  perfil AS arquetipo, criterio_pares, n_pares,
  round(mediana_pct_icsap::numeric, 2) AS mediana_pares_pct,
  round(p25_pct_icsap::numeric, 2)     AS p25_pares_pct,
  round((pct_icsap - mediana_pct_icsap)::numeric, 2) AS diferenca_pp,
  round(excedente::numeric, 0)                       AS internacoes_acima_pares,
  round(excedente_p25::numeric, 0)                   AS internacoes_acima_p25,
  round((excedente * custo_medio)::numeric, 0)       AS custo_associado_reais,
  round((excedente * permanencia_media)::numeric, 0) AS leitos_dia_associados,
  -- Leitura mais concreta para gestão: leitos que ficariam ocupados o ano
  -- inteiro por essas internações a mais.
  round((excedente * permanencia_media / 365.0)::numeric, 1) AS leitos_equivalentes_ano,
  round(custo_medio::numeric, 2)       AS custo_medio_icsap_ref,
  round(permanencia_media::numeric, 2) AS permanencia_media_icsap_ref,
  (internacoes_total < 100) AS amostra_pequena
FROM calc;

-- Por padrão uma view do Postgres executa com os privilégios do DONO, o que faz
-- dela um SECURITY DEFINER de fato: o RLS das tabelas de base é IGNORADO para
-- quem consulta. Hoje não expõe nada (as três tabelas são de leitura pública por
-- desenho), mas é risco latente — se o RLS de qualquer uma for restringido, a
-- view continuaria entregando os dados por cima da restrição, em silêncio.
-- Com security_invoker a view executa como QUEM consulta e o RLS volta a valer.
ALTER VIEW public.mart_icsap_pares SET (security_invoker = on);

COMMENT ON VIEW public.mart_icsap_pares IS
  'Distância de cada município até a mediana dos seus pares em internações sensíveis à atenção primária (ICSAP), traduzida em internações, custo, leitos-dia e leitos equivalentes/ano. NÃO é economia garantida: alcançar a mediana exige investimento em atenção primária, nem toda ICSAP é evitável, e a associação é ecológica (municipal), não individual.';

GRANT SELECT ON public.mart_icsap_pares TO anon, authenticated;
