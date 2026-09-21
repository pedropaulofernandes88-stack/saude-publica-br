-- V048 — SIA/APAC oncológico: quimioterapia e radioterapia viram tabela servida
--
-- MOTIVO
-- ------
-- Os três marts foram publicados como Parquet em 2026-09-21, a partir de 14
-- anos coletados do FTP do SIA/SUS: 2.448.054 linhas, 53.815.165 APACs,
-- R$ 36,6 bi, ZERO mês com falha de coleta. A decisão de SERVIR foi tomada
-- depois e explicitamente, como manda a regra que já valeu para o SISAGUA
-- (V045) e para o Painel de Oncologia: cabe no banco não é razão para entrar
-- no banco.
--
-- CUSTO, MEDIDO ANTES DE CRIAR
-- -----------------------------
-- Banco em 944 MB. Estimativa calibrada contra `mart_sisagua_municipio`, que
-- hoje ocupa 41 MB de heap e 33 MB de índice em 397.380 linhas:
--
--     tratamento  2.448.054 linhas × ~85 B  = ~208 MB heap + ~196 MB de PK
--     fluxo         313.587 linhas × ~96 B  =  ~30 MB heap +  ~25 MB de PK
--     cobertura         756 linhas          = desprezível
--     -----------------------------------------------------------------
--     total                                 = ~460 MB
--
-- Isso leva o banco de 944 MB para ~1,4 GB e ESTOURA o teto de 1.000 MB que
-- `diagnostico_banco.py` declara. O teto sobe junto com esta migração, que é
-- a decisão registrada que a própria regra do script exige ("sobe quando a
-- LINHA DE BASE muda por decisão registrada; não sobe quando só a folga
-- muda"). O limite físico é outro: o plano Pro tem 8 GB.
--
-- NENHUM ÍNDICE ALÉM DA CHAVE PRIMÁRIA, DE PROPÓSITO
-- ---------------------------------------------------
-- Um índice secundário nesta tabela custa ~196 MB — mais que a maior tabela do
-- banco inteiro hoje. A PK começa em `municipio_cod`, então consulta por
-- município já está servida. Índice por UF × ano viria a custar quase metade
-- do que a tabela toda custa, e este projeto já mediu que índice raro NÃO é
-- índice morto (idx_mm_uf_ano: 40 buscas, 42x de ganho) — o que significa que
-- a decisão de criá-lo precisa de uma consulta real que o justifique, não de
-- antecipação. Criar depois é barato; carregar 196 MB que ninguém usa, não.
--
-- A UNIDADE É A APAC, E NÃO A PESSOA
-- -----------------------------------
-- Uma APAC é uma autorização, tipicamente mensal. Paciente em quimioterapia
-- contínua gera várias por ano, e `AP_CNSPCN` — o único identificador de
-- pessoa na fonte — vem CRIPTOGRAFADO. A coluna se chama `apacs` por isso, e
-- qualquer leitura per capita sobre esta tabela está errada.
--
-- ESTA FONTE NÃO MEDE O PRAZO DA LEI DOS 60 DIAS
-- -----------------------------------------------
-- A subtração óbvia entre as datas disponíveis produz manchete falsa. Prazo
-- não é publicado aqui, e isso é decisão, não esquecimento. Ver o cabeçalho de
-- `scripts/sondar_siasus.py`.
--
-- NÃO CONFUNDIR COM `mart_oncologia_*`
-- -------------------------------------
-- `mart_oncologia_municipio` e `mart_oncologia_estadiamento` são do PAINEL DE
-- ONCOLOGIA: mesma janela (2013-2026), mesmo grão municipal, mesmo assunto, e
-- universo que não se compara. O Painel conta CASOS de pessoas diagnosticadas
-- e tem 51% de estadiamento ausente; estes contam AUTORIZAÇÕES e têm 12,3%.
-- Lidos lado a lado, a diferença pareceria uma melhora de quatro vezes no
-- registro. Daí o prefixo `mart_apac_`.
--
-- AUSÊNCIA DE ESTADIAMENTO TEM RÓTULO PRÓPRIO
-- --------------------------------------------
-- `estadiamento = 'ignorado'` nunca é somado ao estádio '0', que é carcinoma
-- in situ — diagnóstico REAL e precoce. A primeira coleta inteira foi
-- descartada exatamente por esse defeito: `_estadio("")` devolvia "0", e no
-- dado cru de PE em 2013-01 havia 1.119 vazios contra 446 zeros verdadeiros —
-- o estádio 0 saía inflado em 3,5 vezes.

create table if not exists public.mart_apac_oncologia_tratamento (
    municipio_cod   text     not null,
    municipio_nome  text,
    uf_sigla        text     not null,
    ano             smallint not null,
    modalidade      text     not null,
    cid3            text     not null,
    estadiamento    text     not null,
    apacs           integer  not null,
    valor_aprovado  numeric(14,2) not null,
    meses_cobertos  smallint,
    primary key (municipio_cod, ano, modalidade, cid3, estadiamento)
);

comment on table public.mart_apac_oncologia_tratamento is
    'APAC de quimioterapia e radioterapia do SIA/SUS, 2013-2026, por município '
    'de RESIDÊNCIA do paciente. A unidade é a AUTORIZAÇÃO, não a pessoa: '
    'paciente em tratamento contínuo gera várias por ano e o identificador de '
    'pessoa vem criptografado na fonte — nenhuma leitura per capita é válida '
    'aqui. Não é o Painel de Oncologia (mart_oncologia_*), que conta casos.';

comment on column public.mart_apac_oncologia_tratamento.municipio_nome is
    'NULO em 37 códigos que não são município do IBGE: UF+0000 (município '
    'ignorado dentro da UF), Regiões Administrativas do DF e municípios '
    'extintos. São 73.479 APACs (0,14%). Nulo é "não sei qual"; a uf_sigla '
    'continua preenchida porque a UF se sabe em todos eles.';

comment on column public.mart_apac_oncologia_tratamento.estadiamento is
    'Estádio 0 a 4 declarado na APAC, ou ''ignorado''. ATENÇÃO: ''0'' é '
    'carcinoma in situ, um diagnóstico REAL e precoce — ausência de '
    'estadiamento NUNCA é somada a ele. ''ignorado'' são ~12% das APACs.';

comment on column public.mart_apac_oncologia_tratamento.apacs is
    'Autorizações, NÃO pacientes. Ver o comentário da tabela.';

comment on column public.mart_apac_oncologia_tratamento.meses_cobertos is
    'Meses do ano publicados no FTP para esta modalidade, no país. 12 = ano '
    'fechado; menos = ano em andamento, cujo TOTAL não é comparável com o de '
    'um ano fechado. 2026 tem 7.';

alter table public.mart_apac_oncologia_tratamento enable row level security;

create policy leitura_publica on public.mart_apac_oncologia_tratamento
    for select to anon, authenticated using (true);


create table if not exists public.mart_apac_oncologia_fluxo (
    ano                smallint not null,
    modalidade         text     not null,
    municipio_res      text     not null,
    municipio_res_nome text,
    uf_res             text     not null,
    municipio_mov      text     not null,
    municipio_mov_nome text,
    uf_mov             text     not null,
    apacs              integer  not null,
    valor_aprovado     numeric(14,2) not null,
    meses_cobertos     smallint,
    primary key (municipio_res, municipio_mov, ano, modalidade)
);

comment on table public.mart_apac_oncologia_fluxo is
    'Deslocamento para tratamento oncológico: município de residência -> '
    'município do estabelecimento, por ano e modalidade. 55,4% das APACs são '
    'de paciente tratado FORA do próprio município — confundir os dois lados '
    'transformaria deslocamento em oferta local.';

comment on column public.mart_apac_oncologia_fluxo.meses_cobertos is
    'Meses do ano publicados no país para esta modalidade. 12 = ano fechado.';

alter table public.mart_apac_oncologia_fluxo enable row level security;

create policy leitura_publica on public.mart_apac_oncologia_fluxo
    for select to anon, authenticated using (true);


create table if not exists public.mart_apac_oncologia_cobertura (
    uf_sigla        text     not null,
    ano             smallint not null,
    modalidade      text     not null,
    meses_coletados smallint not null,
    meses_ausentes  smallint not null,
    meses_com_falha smallint not null,
    primary key (uf_sigla, ano, modalidade)
);

comment on table public.mart_apac_oncologia_cobertura is
    'O que foi coletado, por UF × ano × modalidade. É o que distingue AUSÊNCIA '
    'de FALHA: meses_ausentes são competências que o FTP não publicou (serviço '
    'inexistente ou sem faturamento — AP não teve radioterapia nenhuma de 2013 '
    'a 2021), e meses_com_falha são arquivos que existem e não foram lidos. '
    'meses_com_falha é ZERO nos 14 anos; se deixar de ser, a série daquele ano '
    'está incompleta e o total não vale.';

comment on column public.mart_apac_oncologia_cobertura.meses_ausentes is
    'Competência não publicada no FTP. É ACHADO, não defeito: 26 pares UF × '
    'ano × modalidade têm menos de 12 meses fora de 2026, e são UFs pequenas '
    'com serviço intermitente ou recém-inaugurado.';

alter table public.mart_apac_oncologia_cobertura enable row level security;

create policy leitura_publica on public.mart_apac_oncologia_cobertura
    for select to anon, authenticated using (true);
