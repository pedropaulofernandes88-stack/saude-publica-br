-- V049 — APAC oncológico: índice por UF e ano
--
-- MOTIVO
-- ------
-- A V048 criou as tabelas SEM índice secundário, e escreveu por quê: a
-- estimativa de então dizia que um índice nesta tabela custaria ~125 MB — mais
-- que a maior tabela do banco inteiro — e a regra do projeto é que índice se
-- cria quando há consulta que o justifique, não por antecipação. A consulta
-- apareceu: filtro por UF e ano.
--
-- A ESTIMATIVA DE ~125 MB ESTAVA ERRADA, E PELO MESMO MOTIVO DE SEMPRE
-- --------------------------------------------------------------------
-- Ela veio de aplicar ~51 B/entrada (o custo medido da PK desta tabela) às
-- 2.448.054 linhas. Mas o custo por entrada NÃO é uma constante da tabela: ele
-- depende de quantos valores DISTINTOS a chave tem, por causa da deduplicação
-- de B-tree do Postgres 13+, que guarda cada valor uma vez com a lista de TIDs
-- que o contêm.
--
-- E esta chave é o caso extremo favorável: `uf_sigla` tem 27 valores, `ano` tem
-- 14, e juntas dão **378 combinações distintas** em 2,4 milhões de linhas. O
-- índice guarda 378 chaves e ~2,4 milhões de TIDs de 6 bytes — a ordem de
-- grandeza é de dezenas de MB, não de 125.
--
-- Fica registrado o encadeamento dos três erros, porque ele é o aprendizado:
--
--   1. a regra antiga do projeto dizia ~80 B/entrada e superestimou a PK;
--   2. corrigi para os 51 B MEDIDOS na PK — e apliquei esse número a uma chave
--      de cardinalidade completamente diferente, que é o mesmo erro com outro
--      valor;
--   3. a lição não é "o número certo é X": é que o custo de um índice depende
--      da CARDINALIDADE da chave, e por isso se mede depois de criar.
--
-- MEDIDO DEPOIS DE CRIAR
-- -----------------------
-- 17 MB, ou **7,0 bytes por linha** — praticamente o tamanho de um TID (6 B).
-- A previsão de "dezenas de MB" bateu; a de 125 MB errava por 7 vezes.
--
-- Ganho, em `where uf_sigla = 'PE' and ano = 2024` com group by estadiamento:
--
--     sem índice   976 ms   27.370 buffers   Parallel Seq Scan, 2 workers,
--                                            2.440.015 linhas descartadas
--     com índice   186 ms      279 buffers   Index Scan, 8.039 linhas
--
-- O número que importa é o de BUFFERS (98x), não o de milissegundos: tempo
-- varia com o que está em cache, leitura não. E a varredura ainda ocupava dois
-- workers paralelos para jogar fora 99,7% do que lia.
--
-- POR QUE (uf_sigla, ano) E NÃO (ano, uf_sigla)
-- ----------------------------------------------
-- Nesta ordem o índice serve tanto "uma UF em todos os anos" quanto "uma UF num
-- ano"; na ordem inversa, só serviria consulta que traga o ano. Consulta por UF
-- sozinha é a mais provável numa tela de estado, e consulta por ano sozinho
-- varre o país inteiro de qualquer jeito.
--
-- O FLUXO FICA DE FORA, DE PROPÓSITO
-- -----------------------------------
-- `mart_apac_oncologia_fluxo` tem 313.587 linhas e 47 MB: uma varredura
-- sequencial ali é barata, e a tabela tem DOIS lados (uf_res e uf_mov) — indexar
-- "por UF" exigiria decidir qual, ou dois índices. Essa decisão precisa da
-- consulta real, que ainda não existe.

create index if not exists idx_apac_onco_uf_ano
    on public.mart_apac_oncologia_tratamento (uf_sigla, ano);

comment on index public.idx_apac_onco_uf_ano is
    'Filtro por UF, com ou sem ano. A PK começa em municipio_cod e já serve '
    'consulta municipal; esta cobre a leitura estadual.';
