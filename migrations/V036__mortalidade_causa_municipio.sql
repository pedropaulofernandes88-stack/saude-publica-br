-- =============================================================================
-- V036 — mortalidade por causa e município: o vocabulário entra, os fatos não
-- =============================================================================
--
-- `pipeline_mortalidade_causa_municipio.py` passa a produzir três tabelas:
--
--     mart_mortalidade_causa_municipio       3.591.937 linhas    9,9 MB
--     mart_mortalidade_causa_municipio_mes   7.700.720 linhas   14,2 MB
--     dim_cid10_informativo                      1.571 linhas    0,1 MB
--
-- Só a terceira entra no Postgres. Esta migração cria essa, e registra por
-- escrito a decisão sobre as outras duas.
--
-- POR QUE OS DOIS FATOS FICAM FORA
--
-- Elas são as maiores do projeto em LINHAS e das menores em BYTES — 11,3
-- milhões de linhas em 24 MB de Parquet, porque contagem inteira em coluna
-- ordenada comprime quase a zero. No Postgres essa mesma economia não existe:
-- cada linha carrega cabeçalho de tupla, e a chave primária composta
-- (município, ano, CID) precisa de índice. A estimativa é de centenas de MB num
-- banco que a V034 já deixou em 646 MB de um teto de 700.
--
-- Mas o argumento decisivo não é tamanho, é USO. Estas são tabelas de ANÁLISE:
-- existem para ser baixadas inteiras e lidas em memória por quem vai rodar PCA,
-- clusterização ou correlação cruzada. Ninguém as consulta linha a linha, e
-- nenhuma tela do site as lê. Servi-las pelo PostgREST — que devolve 1.000
-- linhas por requisição — seriam 11.293 requisições para reproduzir um arquivo
-- de 24 MB.
--
-- É o mesmo contrato da V034: `servida: false` no manifesto, Parquet datado com
-- SHA-256, download aberto. `validar_camadas.py` e `reconstruir.py` conferem o
-- contrário do usual — que elas NÃO estão no banco. Se aparecerem, alguém as
-- carregou sem atualizar o contrato.
--
-- POR QUE A DIMENSÃO ENTRA
--
-- `dim_cid10_informativo` é o vocabulário: para cada uma das 1.571 categorias
-- da CID-10, quantos óbitos, em quantos municípios, e três marcas. Cabe em 1.571
-- linhas, responde perguntas sem baixar nada, e é o que torna o filtro de
-- "CIDs informativos" reproduzível em vez de escolha privada de cada análise.
--
-- A MARCA is_covid EXISTE POR UM MOTIVO ESPECÍFICO
--
-- O SIM brasileiro nunca usou U07.1 — zero registros em 2015–2024. COVID-19 foi
-- codificada como B34.2, que truncada em três caracteres vira B34, cuja
-- descrição oficial na CID-10 é "Doenc p/virus de localiz NE". Os números:
--
--     2015–2019      60 a 240 óbitos por ano
--     2020         213.233
--     2021         425.218
--
-- Sem a marca, qualquer filtro razoável de "causas inespecíficas" apagaria a
-- pandemia da matriz de análise. A guarda `conferir_covid()` no pipeline ABORTA
-- se U07 aparecer: se o DataSUS recodificar retroativamente, esta marca fica
-- errada e precisa mudar junto.
--
-- Reversão: DROP TABLE public.dim_cid10_informativo; e retirar as três de
--           TABELAS em scripts/publicar.py e de NAO_SERVIDAS em _publicacao.py.
-- =============================================================================

CREATE TABLE IF NOT EXISTS public.dim_cid10_informativo (
    causabas_3               TEXT     NOT NULL,
    capitulo_cid             TEXT     NOT NULL,
    obitos_total             INTEGER  NOT NULL,
    municipios_com_registro  INTEGER  NOT NULL,
    ano_min                  SMALLINT NOT NULL,
    ano_max                  SMALLINT NOT NULL,
    -- Fração dos municípios com pelo menos um óbito por esta causa no período.
    -- É o eixo do "pouco frequente em todos os municípios": CID que aparece em
    -- 2% dos municípios não sustenta comparação entre eles.
    prevalencia_municipal    NUMERIC  NOT NULL,
    -- Capítulo XVIII (R00–R99). Não é doença, é ausência de diagnóstico — e
    -- varia 23 vezes entre municípios (0,64% a 14,86%, P5–P95), o que a torna
    -- confundidor de primeira ordem em qualquer clusterização por causa.
    is_mal_definida          BOOLEAN  NOT NULL DEFAULT false,
    -- Ver a nota acima. B34 é COVID-19 neste dado.
    is_covid                 BOOLEAN  NOT NULL DEFAULT false,
    -- Sugestão publicada, não filtro aplicado: não mal definida E presente em
    -- pelo menos 25% dos municípios. Deixa 287 CIDs de 1.571.
    informativo              BOOLEAN  NOT NULL DEFAULT false,
    descricao                TEXT,
    CONSTRAINT dim_cid10_informativo_pkey PRIMARY KEY (causabas_3)
);

CREATE INDEX IF NOT EXISTS dim_cid10_informativo_informativo_idx
    ON public.dim_cid10_informativo (informativo)
    WHERE informativo;

alter table public.dim_cid10_informativo enable row level security;

create policy leitura_publica on public.dim_cid10_informativo
    for select to anon, authenticated using (true);

COMMENT ON TABLE public.dim_cid10_informativo IS
  'Vocabulario das 1.571 categorias da CID-10 presentes no SIM 2015-2024, com prevalencia municipal e as marcas is_mal_definida, is_covid e informativo. B34 e COVID-19 neste dado: o SIM brasileiro nunca usou U07 (V036).';
