-- =============================================================================
-- V032 — arquétipos de saúde: k-means sai, estratificação determinística entra
-- =============================================================================
-- O agrupamento por k-means (k=5, semente 42) foi submetido a teste de
-- estabilidade e reprovado:
--   * silhueta caindo monotonicamente a partir de K=2 — os dados não têm cinco
--     grumos, têm um contínuo que o algoritmo era obrigado a cortar;
--   * ARI de 0,571 entre reamostragens;
--   * 280 municípios (16%) trocavam de grupo SEM QUE O DADO DELES MUDASSE.
--
-- Um município que consultasse o boletim duas vezes podia ler dois arquétipos
-- diferentes. Para uma base que pede para ser citada, isso é defeito, não ruído.
--
-- Entra no lugar a estratificação por tercis com CORTES CONGELADOS no
-- repositório (scripts/pipeline_estratos.py). O estrato passa a ser função
-- apenas dos três valores do próprio município contra três constantes:
--   ARI 1,000 por construção; reamostrando e recalculando os cortes, ARI 0,899
--   (p10 0,846) e apenas 10 municípios (0,6%) trocariam em mais da metade das
--   reamostragens.
--
-- O que muda para quem consome:
--   * dim_cluster_municipio.cluster deixa de ser rótulo de k-means (0..4) e
--     passa a ser id determinístico de estrato (1..27). O NOME da coluna e da
--     tabela fica — são contrato público, e o MCP publicado no PyPI depende
--     deles. O COMMENT abaixo diz o que a coluna é de fato.
--   * nova coluna estrato_cod ('M2V3I1'), que torna o método legível sem
--     consultar documentação: tercil de mortalidade, de vulnerabilidade e de
--     internação.
--   * mart_icsap_pares passa a agrupar pares por estrato. São 27 grupos no
--     lugar de 5 — mais homogêneos e ainda grandes (o menor estrato tem 40
--     municípios; o menor conjunto de pares elegíveis à mediana tem 160).
--
-- NÃO muda nesta migração: o tratamento de ano na mediana dos pares. A CTE
-- `medianas` continua agrupando só por grupo_id, ou seja, a mediana de
-- referência mistura 2021–2024. Isso é anterior a esta mudança e tem efeito
-- próprio (a mediana nacional de pct_icsap foi 16,53 em 2021 contra ~20 nos
-- anos seguintes), mas corrigir junto tornaria impossível medir o efeito de
-- uma coisa e de outra. Fica registrado para decisão separada.
--
-- DIVERGENCIA ENCONTRADA AO APLICAR (2026-08-29)
-- A view que estava NO AR nao era a do arquivo V021. O banco usava faixas
-- populacionais 'ate10k'/'10a50k' e prefixo 'k'||cluster; o arquivo do
-- repositorio dizia 'ate20k'/'20a50k' e 'arquetipo:'||cluster. E o caso que o
-- cabecalho de scripts/gerar_schema.py descreve: migracao aplicada direto no
-- painel, sem arquivo. Reescrever a view a partir do ARQUIVO teria trocado, de
-- graca, o grupo de pares de 3.842 municipios sem estrato -- efeito colateral
-- fora do escopo desta mudanca, e invisivel se ninguem medisse.
-- Esta migracao preserva as faixas COMO ESTAVAM NO BANCO. A unica alteracao de
-- agrupamento e a do ramo do estrato.
-- Licao: antes de CREATE OR REPLACE numa view viva, comparar com
-- migrations/schema/schema.sql (gerado do banco), nao com a migracao anterior.
--
-- Depende de: V016 (view original), V021 (base de AIH normal), V025 (invoker)
-- =============================================================================

ALTER TABLE public.dim_cluster_municipio
  ADD COLUMN IF NOT EXISTS estrato_cod text;

COMMENT ON TABLE public.dim_cluster_municipio IS
  'Arquétipo (estrato) de saúde municipal: tercis de mortalidade padronizada (SIM 2023), vulnerabilidade-proxy (Censo 2022) e internações/100k (SIH 2023), com cortes congelados no repositório. Determinístico: o estrato depende apenas dos valores do próprio município. Substituiu o k-means em 2026-08-29, reprovado em teste de estabilidade.';

COMMENT ON COLUMN public.dim_cluster_municipio.cluster IS
  'Id do estrato, 1..27, derivado como (tercil_mortalidade-1)*9 + (tercil_vulnerabilidade-1)*3 + tercil_internacao. NÃO é rótulo de k-means — o nome da coluna é mantido por compatibilidade de contrato.';

COMMENT ON COLUMN public.dim_cluster_municipio.estrato_cod IS
  'Código legível do estrato, ex. M2V3I1 = mortalidade no tercil 2, vulnerabilidade no 3, internação no 1.';

COMMENT ON COLUMN public.dim_cluster_municipio.perfil IS
  'Rótulo do estrato em palavras. É 1-para-1 com cluster/estrato_cod — o pipeline aborta se deixar de ser.';

-- -----------------------------------------------------------------------------
-- View: única mudança é a chave de agrupamento e o texto do critério.
-- -----------------------------------------------------------------------------
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
      -- estrato_cod no lugar do id numérico: quem inspecionar a view lê o
      -- critério direto do valor, sem precisar de tabela de-para.
      WHEN c.estrato_cod IS NOT NULL THEN 'estrato:' || c.estrato_cod
      -- ATENCAO: estas faixas sao as que estavam NO BANCO, nao as do arquivo
      -- V021. Ver a nota "divergencia" no cabecalho.
      ELSE (i.regiao || '_') ||
           CASE WHEN i.populacao <  10000 THEN 'ate10k'
                WHEN i.populacao <  50000 THEN '10a50k'
                WHEN i.populacao < 100000 THEN '50a100k'
                WHEN i.populacao < 500000 THEN '100a500k'
                ELSE '500k+' END
    END AS grupo_id,
    CASE WHEN c.estrato_cod IS NOT NULL THEN 'estrato de saúde (tercis fixos)'
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
-- quem consulta. Com security_invoker a view executa como QUEM consulta.
-- CREATE OR REPLACE preserva as opções da view, mas reafirmamos para que esta
-- migração não dependa de a anterior ter sido aplicada.
ALTER VIEW public.mart_icsap_pares SET (security_invoker = on);

COMMENT ON VIEW public.mart_icsap_pares IS
  'Distância de cada município até a mediana dos seus pares em internações sensíveis à atenção primária (ICSAP), traduzida em internações, custo, leitos-dia e leitos equivalentes/ano. Pares = estrato de saúde (tercis fixos de mortalidade × vulnerabilidade × internação); sem estrato, faixa populacional × região. NÃO é economia garantida: alcançar a mediana exige investimento em atenção primária, nem toda ICSAP é evitável, e a associação é ecológica (municipal), não individual.';

GRANT SELECT ON public.mart_icsap_pares TO anon, authenticated;
