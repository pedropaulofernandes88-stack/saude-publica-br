-- V050 — Registro Hospitalar de Câncer (INCA): a cobertura vai ao banco, o
-- caso não
--
-- MOTIVO
-- ------
-- O RHC entrou como 16ª fonte em 2026-09-21. Ele é a PRIMEIRA fonte oncológica
-- do projeto cuja unidade é a PESSOA na origem: a APAC conta autorização, e o
-- Painel de Oncologia, embora conte caso, é construído do próprio SIA. O RHC
-- vem de registro hospitalar com confirmação histopatológica, e traz três
-- variáveis que nenhuma das outras tem — escolaridade, raça/cor declarada, e o
-- primeiro tratamento de QUALQUER modalidade, que é o que a Lei 12.732/2012
-- efetivamente conta.
--
-- DUAS TABELAS, DUAS DECISÕES DIFERENTES
-- ---------------------------------------
-- `mart_rhc_caso` tem 1.018.079 linhas e fica **só em Parquet**, na lista
-- NAO_SERVIDAS. O critério é o de sempre — não há tela nem ferramenta MCP que
-- a consulte — e aqui o espaço confirma: ~71 MB de heap mais índice de PK
-- sobre cinco colunas de texto, contra 91 MB de folga medidos hoje (banco em
-- 1.359 MB, teto declarado em 1.450). Servir é um passo separado, e barato de
-- dar depois.
--
-- `mart_rhc_cobertura` tem 274 linhas e ENTRA, porque ela não é acessório: é
-- onde moram o carimbo de ano incompleto e as contagens que dizem o que o
-- número significa. Publicar o caso sem a cobertura seria publicar série sem a
-- ressalva que muda a leitura dela.
--
-- O ANO É O DA PRIMEIRA CONSULTA, E ISSO NÃO É DETALHE
-- -----------------------------------------------------
-- O arquivo anual do INCA agrupa por ano da PRIMEIRA CONSULTA no hospital, não
-- por ano do diagnóstico. Medido em 2019: `ANOPRIDI` diverge do ano do arquivo
-- em 21,7% dos registros, e 15.230 trazem `9999`. A coluna se chama
-- `ano_primeira_consulta` por isso, e `ano_diagnostico_difere` publica a
-- divergência em vez de escondê-la. É a mesma armadilha já documentada no
-- SINAN, onde o ano do arquivo é notificação na sífilis e diagnóstico na
-- tuberculose.
--
-- O RHC SE ENCHE AO LONGO DE ANOS
-- --------------------------------
-- 2023 traz 142.038 casos contra 461.166 em 2022. Lido como série, isso é um
-- colapso de 69% na detecção de câncer no Brasil. **Não é**: são 15 UFs e 69
-- hospitais contra 25 e 189, porque hospital envia quando fecha o registro. A
-- coluna `ano_incompleto` carimba isso em CADA LINHA, das duas tabelas, pela
-- mesma razão que `meses_cobertos` existe no SIH e no mart da sífilis — este
-- projeto já publicou série com 63% de um mês faltando, e ela passou em toda
-- guarda de forma.
--
-- NÃO CONFUNDIR COM AS OUTRAS DUAS FONTES ONCOLÓGICAS
-- ----------------------------------------------------
--   mart_rhc_*              CASOS, registro hospitalar, ~53% sem estadiamento
--   mart_oncologia_*        CASOS, Painel (deriva do SIA), ~51% sem estadiamento
--   mart_apac_oncologia_*   AUTORIZAÇÕES, SIA direto, ~12% sem estadiamento
--
-- Os 12% da APAC não são um registro melhor: são outro universo. Lidos lado a
-- lado sem essa nota, a diferença pareceria melhora de quatro vezes.

create table if not exists mart_rhc_cobertura (
    ano_primeira_consulta   smallint not null,
    uf_sigla                text     not null,
    casos                   integer  not null,
    analiticos              integer  not null,
    nao_analiticos          integer  not null,
    sem_estadiamento        integer  not null,
    sem_prazo               integer  not null,
    ano_diagnostico_difere  integer  not null,
    hospitais               integer  not null,
    municipios              integer  not null,
    ano_incompleto          boolean  not null,
    primary key (ano_primeira_consulta, uf_sigla)
);

comment on table mart_rhc_cobertura is
    'RHC/INCA: o que entrou em cada ano e UF, e o que faltou. A unidade é a '
    'PESSOA (caso com confirmação histopatológica), não a autorização. O ano é '
    'o da PRIMEIRA CONSULTA no hospital, não o do diagnóstico.';

comment on column mart_rhc_cobertura.ano_primeira_consulta is
    'Ano da primeira consulta no hospital, que é como o INCA agrupa os '
    'arquivos. NÃO é o ano do diagnóstico: os dois divergem em ~22% dos '
    'registros (ver ano_diagnostico_difere).';

comment on column mart_rhc_cobertura.analiticos is
    'Casos que chegaram ao hospital SEM diagnóstico e tratamento completos '
    'feitos fora. É o universo que a literatura usa (Jomar et al. 2023 exclui '
    'os não analíticos). Somar analíticos e não analíticos mede a rede, não o '
    'hospital.';

comment on column mart_rhc_cobertura.sem_estadiamento is
    'Casos cujo ESTADIAM é 88, 99 ou vazio — códigos que NÃO existem no '
    'dicionário r_estadiam.cnv do próprio INCA. São ~53% dos registros, e '
    'somá-los ao estádio 0 (carcinoma in situ, diagnóstico real e precoce) '
    'inventaria uma distribuição.';

comment on column mart_rhc_cobertura.sem_prazo is
    'Casos sem uma das duas datas, ou com intervalo negativo, ou acima de 365 '
    'dias — o corte de outlier que Jomar et al. 2023 adotam. Ausência de data '
    'e intervalo impossível ficam na MESMA coluna, e nenhuma delas vira zero '
    'dia.';

comment on column mart_rhc_cobertura.hospitais is
    'Estabelecimentos (CNES) que enviaram registro naquele ano e UF. É esta '
    'contagem, e não o volume de casos, que denuncia ano incompleto: em 2023 '
    'ela cai para 69 contra um platô de ~224.';

comment on column mart_rhc_cobertura.ano_incompleto is
    'true quando a contagem de hospitais do ano está abaixo de 90% do platô '
    'dos anos assentados. O RHC se enche ao longo de anos; sem este carimbo, '
    '2022 e 2023 se leem como queda na detecção de câncer em vez de cauda de '
    'reporte.';

alter table mart_rhc_cobertura enable row level security;

drop policy if exists leitura_publica on mart_rhc_cobertura;
create policy leitura_publica on mart_rhc_cobertura for select using (true);
