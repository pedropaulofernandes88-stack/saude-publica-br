-- =============================================================================
-- V024 — mart_siops_municipio: gasto público municipal em saúde
-- =============================================================================
-- O projeto media desfecho (mortalidade, ICSAP, HSMR) e oferta física (leitos),
-- nunca o INSUMO FINANCEIRO. Esta tabela fecha a lacuna: é a única base nacional
-- com orçamento público de saúde por município, e é o que permite perguntar se
-- gastar mais está associado a internar menos por condição evitável.
--
-- ORIGEM — SIOPS, série histórica de indicadores municipais, extraída do TABNET
-- em siops-asp.datasus.gov.br. O SIOPS não está no FTP do DataSUS, não está na
-- API de dados abertos do Ministério (85 rotas, nenhuma financeira) e não está no
-- SICONFI: o Anexo 12 do RREO é transmitido pelo próprio SIOPS e não aparece na
-- API do Tesouro. Detalhes em scripts/pipeline_siops.py.
--
-- COMO NÃO LER ESTES NÚMEROS
--   * gasto NÃO é acesso nem qualidade. O SIOPS mede empenho orçamentário, não
--     produção assistencial, não necessidade e não desfecho;
--   * o dado é AUTODECLARADO pelo ente e homologado pelo gestor — não há
--     verificação externa das transações. Erro de classificação contábil entra
--     como se fosse gasto;
--   * é despesa EMPENHADA. Liquidada e paga são valores diferentes; comparar com
--     outra fonte exige a mesma fase;
--   * per capita em município pequeno OSCILA muito — uma obra num município de
--     3 mil habitantes desloca o indicador sem mudança estrutural. Comparar
--     dentro de faixa de porte, como o resto do projeto faz;
--   * capacidade fiscal difere brutalmente entre municípios. Ranquear por gasto
--     sem controlar receita própria e papel regional compara coisas distintas.
--
-- `abaixo_do_minimo_ec29` é NULL, e não FALSE, quando o município não declarou.
-- Ausência de declaração não é descumprimento, e afirmar isso seria acusação sem
-- base — o campo distingue "declarou e ficou abaixo" de "não sabemos".
--
-- Subfunções (atenção básica, assistência hospitalar) NÃO entram: existem no .def
-- mas vêm vazias de 2016 em diante. Seria a variável mais interessante para
-- cruzar com ICSAP, e não está disponível no período do projeto.
--
-- Fonte: R. F. Saldanha, "Sistemas de Informação em Saúde no Brasil", cap. SIOPS
-- https://rfsaldanha.github.io/sis/siops.html
-- =============================================================================

CREATE TABLE IF NOT EXISTS public.mart_siops_municipio (
  municipio_cod              TEXT    NOT NULL,
  municipio_nome             TEXT,
  uf_sigla                   TEXT,
  regiao                     TEXT,
  ano                        SMALLINT NOT NULL,
  populacao_siops            NUMERIC,
  gasto_proprio_saude_hab    NUMERIC,
  despesa_total_saude        NUMERIC,
  transf_sus_hab             NUMERIC,
  pct_receita_propria_saude  NUMERIC,
  abaixo_do_minimo_ec29      BOOLEAN,
  PRIMARY KEY (municipio_cod, ano)
);

CREATE INDEX IF NOT EXISTS idx_siops_uf_ano   ON public.mart_siops_municipio (uf_sigla, ano);
CREATE INDEX IF NOT EXISTS idx_siops_ano_gasto ON public.mart_siops_municipio (ano, gasto_proprio_saude_hab);

-- Leitura pública; escrita só para os pipelines (ver V022/V023).
ALTER TABLE public.mart_siops_municipio ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS siops_leitura_publica ON public.mart_siops_municipio;
CREATE POLICY siops_leitura_publica ON public.mart_siops_municipio FOR SELECT USING (true);

GRANT SELECT ON public.mart_siops_municipio TO anon, authenticated;
GRANT SELECT, INSERT, UPDATE, DELETE ON public.mart_siops_municipio TO service_role;

COMMENT ON TABLE public.mart_siops_municipio IS
  'Gasto publico municipal em saude (SIOPS/MS, serie historica de indicadores). Despesa EMPENHADA, dado AUTODECLARADO pelo ente. Gasto nao mede acesso nem qualidade.';

COMMENT ON COLUMN public.mart_siops_municipio.gasto_proprio_saude_hab IS
  'Despesa com recursos proprios em saude por habitante (R$). Oscila muito em municipio pequeno.';

COMMENT ON COLUMN public.mart_siops_municipio.pct_receita_propria_saude IS
  'Percentual da receita propria aplicado em ASPS. Piso constitucional de 15% (EC 29 / LC 141).';

COMMENT ON COLUMN public.mart_siops_municipio.abaixo_do_minimo_ec29 IS
  'TRUE se declarou abaixo de 15%. NULL quando nao declarou — ausencia de declaracao nao e descumprimento.';
