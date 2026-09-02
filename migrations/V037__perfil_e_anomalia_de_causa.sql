-- =============================================================================
-- V037 — perfil de mortalidade e anomalia de causa por município
-- =============================================================================
--
-- Duas tabelas de ANÁLISE derivadas de `mart_mortalidade_causa_municipio`
-- (V036). Diferente das tabelas de fato daquela migração, estas são pequenas
-- — 3.430 e ~2.600 linhas — e entram no Postgres normalmente.
--
--     mart_perfil_mortalidade_municipio   scripts/analise_perfil_mortalidade.py
--     mart_anomalia_causa_municipio       scripts/analise_anomalia_causas.py
--
-- O QUE `grupo` É, E O QUE NÃO É
--
-- É uma DISCRETIZAÇÃO DECLARADA de um contínuo, não uma tipologia descoberta.
-- Duas medidas dizem isso, e elas discordam de um jeito que só tem uma leitura:
--
--     ARI entre subamostras de 80% (k=3)   0,93   a partição se reproduz
--     silhueta média (k=3)                 0,17   os grupos não se separam
--
-- Partição reprodutível com silhueta baixa é a assinatura de um gradiente: o
-- mesmo corte reaparece porque a direção é real, não porque existam ilhas. A
-- fração de soma de quadrados não explicada também cai sem cotovelo de k=2 a
-- k=20 — não há número natural de grupos.
--
-- Por isso as colunas que valem são `pc1`…`pc6`, as coordenadas. Quem usar
-- `grupo` como se fosse tipo de município estará afirmando uma separação que a
-- silhueta nega. O comentário da coluna repete isso no banco, para quem chega
-- pela API e não lê o script.
--
-- POR QUE SEIS COMPONENTES
--
-- São os que superam duas vezes um nulo multinomial em que cada município
-- sorteia os SEUS óbitos da composição nacional. Antes disso, quatro
-- confundidores são removidos por regressão de cada proporção de CID: log da
-- população, fração com 60 anos ou mais, percentual de causas mal definidas e
-- fração de B34 (COVID). Com os quatro controles o PC1 cai de 6,3% para 3,3%
-- da variância — quase metade do "padrão de mortalidade" municipal era idade,
-- porte, registro e pandemia. A estrutura sobrevive assim mesmo.
--
-- `indice_inespecificidade` É O ACHADO METODOLÓGICO DESTA MIGRAÇÃO
--
-- Fração dos óbitos do município codificada em CID cuja descrição traz NE, NCOP
-- ou SOE — diagnóstico impreciso —, excluído o B34, que casa com o padrão mas
-- é COVID-19, não imprecisão.
--
--     correlação com o PC1                             -0,54  (r² = 0,29)
--     correlação com o % de causas mal definidas       +0,37
--
-- Ou seja: quase um terço do eixo principal do "perfil de mortalidade"
-- municipal brasileiro é PRECISÃO DE CODIFICAÇÃO, e o indicador clássico de
-- qualidade capta só um terço disso. Ele mede o balde do R99; este mede a
-- granularidade de todo o resto. Uma clusterização publicada sem esse controle
-- descreveria cultura de codificação médica e seria lida como epidemiologia.
--
-- OS DOIS ESCORES DE ANOMALIA
--
--     excesso_proprio    mudou em relação à história do próprio município?
--     excesso_relativo   mudou mais do que o CID mudou no Brasil naquele ano?
--
-- O primeiro é o pedido literal; o segundo é o que serve para vigilância. Sem
-- descontar a tendência nacional o que mais aparece é deriva de codificação
-- (N39, E11, G30, I10 encabeçam), com sinais crescendo de 203 em 2020 para 644
-- em 2024 — padrão de mudança de prática de registro, não de epidemia.
--
-- O teste é binomial negativa, não z-score: a mediana é de 77 óbitos por
-- município-ano e a maioria das células é 0, 1 ou 2. A dispersão φ é estimada
-- pela variação ano a ano DENTRO do município (mediana 1,23, P95 3,38);
-- estimá-la contra a média nacional inflava φ para perto de 20 e cegava a
-- detecção, porque absorvia como ruído a diferença real entre municípios.
--
-- Reversão: DROP TABLE public.mart_perfil_mortalidade_municipio;
--           DROP TABLE public.mart_anomalia_causa_municipio;
-- =============================================================================

create table if not exists public.mart_perfil_mortalidade_municipio (
    municipio_cod            text     not null,
    municipio_nome           text     not null,
    uf_sigla                 text     not null,
    regiao                   text     not null,
    obitos_periodo           integer  not null,
    -- DISCRETIZAÇÃO de um contínuo, não tipologia. Ver a nota acima.
    grupo                    smallint not null,
    -- Fração dos óbitos em CID impreciso (NE/NCOP/SOE), sem B34.
    indice_inespecificidade  numeric  not null,
    -- As coordenadas: é aqui que mora a informação.
    pc1 numeric, pc2 numeric, pc3 numeric,
    pc4 numeric, pc5 numeric, pc6 numeric,
    constraint mart_perfil_mortalidade_municipio_pkey PRIMARY KEY (municipio_cod)
);

create table if not exists public.mart_anomalia_causa_municipio (
    municipio_cod       text     not null,
    ano                 smallint not null,
    causabas_3          text     not null,
    municipio_nome      text     not null,
    uf_sigla            text     not null,
    obitos              integer  not null,
    esperado            numeric  not null,
    esperado_relativo   numeric  not null,
    razao               numeric  not null,
    p_proprio           numeric  not null,
    p_relativo          numeric  not null,
    excesso_proprio     boolean  not null default false,
    excesso_relativo    boolean  not null default false,
    constraint mart_anomalia_causa_municipio_pkey
        PRIMARY KEY (municipio_cod, ano, causabas_3)
);

CREATE INDEX IF NOT EXISTS idx_perfil_mort_grupo
    ON public.mart_perfil_mortalidade_municipio USING btree (grupo);
CREATE INDEX IF NOT EXISTS idx_anomalia_causa_ano
    ON public.mart_anomalia_causa_municipio USING btree (causabas_3, ano);

alter table public.mart_perfil_mortalidade_municipio enable row level security;
alter table public.mart_anomalia_causa_municipio enable row level security;

create policy leitura_publica on public.mart_perfil_mortalidade_municipio
    for select to anon, authenticated using (true);
create policy leitura_publica on public.mart_anomalia_causa_municipio
    for select to anon, authenticated using (true);

COMMENT ON TABLE public.mart_perfil_mortalidade_municipio IS
  'Coordenadas do perfil de causas de morte por municipio (2015-2024), apos remover porte, estrutura etaria, qualidade do registro e COVID. Seis componentes acima do nulo multinomial (V037).';
COMMENT ON COLUMN public.mart_perfil_mortalidade_municipio.grupo IS
  'Discretizacao declarada de um continuo, NAO tipologia: ARI 0,93 entre subamostras mas silhueta 0,17. Use pc1..pc6 para analise; use grupo apenas para exposicao.';
COMMENT ON COLUMN public.mart_perfil_mortalidade_municipio.indice_inespecificidade IS
  'Fracao dos obitos codificada em CID impreciso (NE/NCOP/SOE), excluido B34 que e COVID. Correlaciona -0,54 com o PC1 e apenas +0,37 com o indicador classico de causas mal definidas.';
COMMENT ON TABLE public.mart_anomalia_causa_municipio IS
  'Celulas municipio x CID x ano (2020-2024) com excesso sobre a historia propria 2015-2019, por binomial negativa com FDR 1%. Controles positivos: COVID em 2020-2021 e dengue apenas em 2024 (V037).';
