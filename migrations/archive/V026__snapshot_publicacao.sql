-- =============================================================================
-- V026 — snapshot_publicacao: a memória das próprias revisões
-- =============================================================================
-- O DataSUS revisa dado já publicado. Uma competência entra incompleta, recebe
-- óbitos que chegaram atrasados, corrige causa mal-definida, e o número muda sem
-- aviso. Quem citou o valor de ontem não tem como saber que ele mudou.
--
-- Nenhuma fonte pública guarda essa série. O TABNET entrega o número de hoje e
-- não tem memória: consultar SIM 2024 em fevereiro e em agosto devolve valores
-- diferentes, sem nenhum registro de que diferiram. O projeto já declara "2024
-- preliminar" em toda a documentação — esta tabela é o que transforma esse aviso
-- qualitativo em quantidade.
--
-- A PERGUNTA QUE ELA RESPONDE
--   Preliminar quanto? Falta 1% ou 8%? Estabiliza em quantos meses? Hoje ninguém
--   consegue responder, inclusive este projeto: uma verificação sobre os dois
--   snapshots de junho/2026 disponíveis no repositório deu variação de 0,00%,
--   o que com dois pontos a 17 dias não distingue "dado estável" de "pipeline
--   não reingeriu". Medir é o objetivo, não o pressuposto.
--
-- COMO NÃO LER ESTES NÚMEROS
--   * uma revisão NÃO é erro corrigido. Óbito registrado com atraso é o
--     funcionamento normal do SIM, não falha do sistema. Ler `pct_revisao` como
--     "margem de erro do DataSUS" inverte o sentido do indicador;
--   * `extraido_em` é quando ESTE projeto leu a fonte, não quando o Ministério
--     publicou. Duas extrações iguais podem significar que a fonte não mudou OU
--     que o pipeline não reingeriu — a tabela sozinha não separa os dois casos;
--   * as linhas com origem `git:` foram reconstruídas do histórico de
--     `site/public/sdata/`, que é gerado no build. A data é a do commit, e um
--     build sem reingestão repete o valor anterior. São âncoras, não medições;
--   * série curta não prevê. Enquanto houver menos de ~4 extrações espaçadas de
--     uma mesma competência, qualquer projeção de "quanto ainda falta" é chute
--     com aparência de estatística. A view expõe `n_extracoes` para que o
--     consumidor decida;
--   * UF pequena oscila mais em termos percentuais pelo denominador. Comparar
--     magnitude de revisão entre AC e SP sem isso em conta compara ruído.
--
-- GRANULARIDADE — UF × competência, não município. O objetivo é medir o
-- comportamento da FONTE, e no município a variação de poucos óbitos domina o
-- percentual sem dizer nada sobre estabilidade do sistema. Também mantém a
-- tabela pequena: ~27 UF × ~130 competências × 2 bases por extração.
-- =============================================================================

CREATE TABLE IF NOT EXISTS public.snapshot_publicacao (
  base         TEXT    NOT NULL,   -- 'SIM' | 'SINAN'
  metrica      TEXT    NOT NULL,   -- 'obitos' | 'casos_provaveis'
  competencia  TEXT    NOT NULL,   -- 'AAAA-MM' mensal; 'AAAA-Www' semana epidemiológica
  uf_sigla     TEXT    NOT NULL,   -- sigla IBGE; 'BR' para o agregado nacional
  valor        NUMERIC NOT NULL,
  extraido_em  DATE    NOT NULL,   -- quando ESTE projeto leu a fonte
  origem       TEXT    NOT NULL,   -- 'pipeline' | 'git:<sha> <caminho>'
  PRIMARY KEY (base, metrica, competencia, uf_sigla, extraido_em)
);

CREATE INDEX IF NOT EXISTS idx_snapshot_serie
  ON public.snapshot_publicacao (base, metrica, uf_sigla, competencia, extraido_em);
CREATE INDEX IF NOT EXISTS idx_snapshot_extracao
  ON public.snapshot_publicacao (extraido_em);

ALTER TABLE public.snapshot_publicacao ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS snapshot_leitura_publica ON public.snapshot_publicacao;
CREATE POLICY snapshot_leitura_publica ON public.snapshot_publicacao FOR SELECT USING (true);
GRANT SELECT ON public.snapshot_publicacao TO anon, authenticated;
GRANT SELECT, INSERT, UPDATE, DELETE ON public.snapshot_publicacao TO service_role;

COMMENT ON TABLE public.snapshot_publicacao IS
  'Serie das proprias extracoes: o valor que cada competencia tinha em cada leitura da fonte. Permite medir quanto um numero preliminar ainda se move. Revisao nao e erro: obito registrado com atraso e o funcionamento normal do SIM.';
COMMENT ON COLUMN public.snapshot_publicacao.extraido_em IS
  'Quando ESTE projeto leu a fonte, nao quando o Ministerio publicou. Valores iguais em duas datas podem significar fonte estavel OU pipeline que nao reingeriu.';
COMMENT ON COLUMN public.snapshot_publicacao.origem IS
  'pipeline = gravado na execucao. git:<sha> = reconstruido do historico de site/public/sdata/, que e gerado no build — ancora, nao medicao.';

-- ── Revisão entre extrações consecutivas ────────────────────────────────────
-- Uma linha por (competência, UF, extração) a partir da SEGUNDA extração: sem
-- valor anterior não há revisão a reportar.
DROP VIEW IF EXISTS public.vw_revisao_publicacao;
CREATE VIEW public.vw_revisao_publicacao AS
WITH ordenado AS (
  SELECT
    base, metrica, competencia, uf_sigla, extraido_em, valor,
    LAG(valor)        OVER janela AS valor_anterior,
    LAG(extraido_em)  OVER janela AS extraido_anterior,
    FIRST_VALUE(valor) OVER janela AS valor_primeira_extracao,
    COUNT(*)          OVER (PARTITION BY base, metrica, competencia, uf_sigla) AS n_extracoes
  FROM public.snapshot_publicacao
  WINDOW janela AS (
    PARTITION BY base, metrica, competencia, uf_sigla ORDER BY extraido_em
  )
)
SELECT
  base, metrica, competencia, uf_sigla,
  extraido_anterior, extraido_em,
  (extraido_em - extraido_anterior)                          AS dias_entre,
  valor_anterior, valor,
  (valor - valor_anterior)                                   AS delta,
  CASE WHEN valor_anterior > 0
       THEN ROUND((valor / valor_anterior - 1) * 100, 3) END AS pct_revisao,
  CASE WHEN valor_primeira_extracao > 0
       THEN ROUND((valor / valor_primeira_extracao - 1) * 100, 3) END AS pct_desde_a_primeira,
  n_extracoes
FROM ordenado
WHERE valor_anterior IS NOT NULL;

-- security_invoker: le com a permissao de quem consulta, mesma decisao da V025.
ALTER VIEW public.vw_revisao_publicacao SET (security_invoker = true);
GRANT SELECT ON public.vw_revisao_publicacao TO anon, authenticated;

COMMENT ON VIEW public.vw_revisao_publicacao IS
  'Revisao entre extracoes consecutivas. n_extracoes < 4 significa serie curta demais para projetar quanto ainda falta. pct_revisao positivo e o caso comum: registro que chegou atrasado.';
