-- =============================================================================
-- V042 — a mediana dos pares passa a ser do ANO, não de 2021–2024 somados
-- =============================================================================
-- Corrige a pendência que a V032 registrou no próprio cabeçalho e deixou para
-- decisão separada: a CTE `medianas` agrupava só por `grupo_id`, então a
-- referência contra a qual cada município era medido misturava os quatro anos.
--
-- Um município de 2021 era comparado com a mediana de um período que inclui
-- 2022, 2023 e 2024. Isso não é comparação com pares — é comparação com o
-- futuro e com o passado deles. E a proporção de ICSAP não é estável no
-- intervalo: 2021 é o ano da COVID, quando a internação eletiva desabou e a
-- composição do denominador mudou em todo o país.
--
-- A prosa da metodologia (§17, "Pares") já dizia "no ano". Quem lia a
-- documentação e quem lia a view não estavam olhando para a mesma coisa.
--
-- POR QUE AGORA, E NÃO NA V032
-- A V032 adiou de propósito, para poder medir separadamente o efeito da troca
-- do k-means pelos estratos. Esse efeito foi medido e publicado. O motivo do
-- adiamento expirou.
--
-- CRITÉRIO DE DESISTÊNCIA, DECLARADO ANTES DE MEDIR
-- Somar os anos poderia estar comprando poder estatístico: grupos pequenos
-- demais num único ano não sustentam mediana. Duas condições fariam esta
-- migração ser abandonada:
--   (a) algum grupo elegível cair abaixo de 20 municípios em algum ano;
--   (b) alguma linha município-ano perder a mediana e sair da view.
-- Nenhuma das duas ocorreu. Por ano, são os mesmos 37 grupos, o menor com 40
-- municípios (mediana 73, maior 766), nenhum abaixo de 20; e as 22.280 linhas
-- (5.570 × 4) permanecem 22.280. Somar os anos não comprava poder nenhum.
--
-- O QUE MUDA PARA QUEM CONSOME
-- A contagem de linhas NÃO muda — e é justamente por isso que ela não serve de
-- guarda aqui. O que muda são os valores:
--
--   * `n_pares` deixa de contar município-ANO e passa a contar município. O
--     estrato de Penápolis era publicado como "272 pares"; são 68 municípios,
--     contados quatro vezes. O maior grupo cai de 3.029 para 739/761/766/763.
--   * `mediana_pares_pct`, `p25_pares_pct`, `diferenca_pp`,
--     `internacoes_acima_pares`, `internacoes_acima_p25`,
--     `custo_associado_reais`, `leitos_dia_associados` e
--     `leitos_equivalentes_ano` mudam em 2021, 2022 e 2023. Em 2024 a maioria
--     dos grupos quase não se move — o ano domina a mediana somada por ser o
--     mais recente e o mais completo.
--   * 945 municípios TROCAM DE LADO em 2021 (erro médio de 2,83 pp), 366 em
--     2022, 353 em 2023, 275 em 2024. "Trocar de lado" é passar de abaixo da
--     mediana dos pares para acima, ou o contrário — a leitura se inverte.
--   * O total nacional de internações acima dos pares em 2021 vai de 146.800
--     para 273.435 (R$ 239 mi → R$ 445 mi). Nos demais anos cai: 2022 de
--     389.728 para 314.690, 2023 de 412.430 para 336.773, 2024 de 385.172 para
--     332.811. O sentido é o esperado: em 2021, com a proporção nacional mais
--     baixa, a mediana somada era alta demais e fazia os municípios parecerem
--     melhores do que os pares contemporâneos.
--
-- Caso citado externamente (briefing Nakaya), para conferência:
--   Penápolis 2022 — pct 20,73; mediana 20,42 → 22,10; diferença +0,31 →
--   −1,37 pp; internações acima 14 → 0; custo R$ 22.751 → R$ 0. O município
--   estava sendo apresentado como acima dos pares num ano em que estava
--   abaixo. Penápolis 2024 não muda (mediana 20,42 nos dois cálculos).
--   Araçatuba 2021 — diferença +4,72 → +6,45 pp; 390 → 533 internações.
--
-- Números conferidos em 2026-09-06 contra o banco, antes de aplicar.
--
-- Depende de: V032 (estratos determinísticos), V025 (security_invoker)
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
      -- estrato_cod no lugar do id numérico: quem inspecionar a view lê o
      -- critério direto do valor, sem precisar de tabela de-para.
      WHEN c.estrato_cod IS NOT NULL THEN 'estrato:' || c.estrato_cod
      -- ATENCAO: estas faixas sao as que estavam NO BANCO, nao as do arquivo
      -- V021. Ver a nota "divergencia" no cabecalho da V032.
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
  --
  -- `ano` no GROUP BY é a correção desta migração: a mediana de referência é a
  -- do grupo NAQUELE ano. Sem ele, `n_pares` contava município-ano e a
  -- comparação atravessava o tempo. Ver o cabeçalho.
  SELECT grupo_id, ano,
         percentile_cont(0.5)  WITHIN GROUP (ORDER BY pct_icsap) AS mediana_pct_icsap,
         percentile_cont(0.25) WITHIN GROUP (ORDER BY pct_icsap) AS p25_pct_icsap,
         count(*) AS n_pares
  FROM base
  WHERE internacoes_total >= 100 AND pct_icsap IS NOT NULL
  GROUP BY grupo_id, ano
),
calc AS (
  SELECT
    b.*, m.n_pares, m.mediana_pct_icsap, m.p25_pct_icsap,
    p.custo_medio, p.permanencia_media,
    greatest(0, b.internacoes_total * (b.pct_icsap - m.mediana_pct_icsap) / 100.0) AS excedente,
    greatest(0, b.internacoes_total * (b.pct_icsap - m.p25_pct_icsap) / 100.0)     AS excedente_p25
  FROM base b
  JOIN medianas m ON m.grupo_id = b.grupo_id AND m.ano = b.ano
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
  'Distância de cada município até a mediana dos seus pares em internações sensíveis à atenção primária (ICSAP), traduzida em internações, custo, leitos-dia e leitos equivalentes/ano. Pares = estrato de saúde (tercis fixos de mortalidade × vulnerabilidade × internação) NO MESMO ANO; sem estrato, faixa populacional × região. n_pares conta municípios do grupo naquele ano (V042; antes contava município-ano). security_invoker=true: lê com a permissão de quem consulta (ver V025). NÃO é economia garantida: alcançar a mediana exige investimento em atenção primária, nem toda ICSAP é evitável, e a associação é ecológica (municipal), não individual.';

GRANT SELECT ON public.mart_icsap_pares TO anon, authenticated;
