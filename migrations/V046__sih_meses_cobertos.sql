-- V046 — SIH: a linha passa a dizer de quantos meses ela veio
--
-- MOTIVO
-- ------
-- O checkpoint do SIH sempre soube quais meses o produziram — `saude_em_dado.
-- meses`, gravado por `gravar_checkpoint` desde a correção de 2026-08-11 — e
-- essa informação MORRIA na agregação. O mart saía com o total do ano e nada,
-- em lugar nenhum do dado publicado, dizia de quantos meses ele veio.
--
-- Foi assim que MA 2023 publicou 7 de 12 meses (-41% das internações) com o
-- pipeline terminando em código 0. Aquela correção fechou o caso em que a
-- coleta falha: hoje `_process_uf` aborta se um mês publicado no FTP não for
-- coletado, e o checkpoint não é gravado.
--
-- Resta o outro caso, que nenhuma guarda alcança porque não é defeito: quando o
-- PRÓPRIO FTP só publicou 7 meses, a coleta está certa, o checkpoint está
-- certo, e o total do ano continua não sendo comparável com o de um ano
-- fechado. Sem carimbo, a leitura fácil é a errada — exatamente o que aconteceu
-- com a dengue de 2026 ("despencou 73%", ver V043).
--
-- DESENHO
-- -------
-- `meses_cobertos` é por UF e ano, repetido em cada linha do município daquela
-- UF. Redundante de propósito: quem lê UMA linha — pelo Parquet, pela API ou
-- pelo CSV — vê a ressalva junto do número que ela qualifica, sem depender de
-- rodapé que o consumidor do Parquet nunca lê.
--
-- Grão mais fino que o da dengue (`semanas_cobertas`, nacional) porque aqui o
-- arquivo é por UF × mês: o incidente do MA foi de uma UF só, e um carimbo
-- nacional o teria diluído em 26 UFs completas.
--
-- Em `mart_fluxo_intermunicipal` o valor é o MÍNIMO entre residência e
-- movimento: a internação cruza os dois municípios, e o par só é tão completo
-- quanto o lado menos completo.
--
-- FORA DESTA MIGRAÇÃO, DE PROPÓSITO
-- ----------------------------------
-- `mart_demanda_mensal_hospital` tem grão MENSAL: ano parcial já aparece como
-- competência faltando, e uma coluna repetiria o que a chave já diz.
-- `mart_hsmr_hospital`, `mart_los_hospital`, `mart_forecast_demanda_hospital` e
-- `mart_icsap_pares` são derivados dos marts abaixo — o carimbo chega neles
-- pela origem quando forem recalculados, e duplicá-lo aqui criaria uma segunda
-- definição para manter em dia.
--
-- NULA ATÉ O REPROCESSAMENTO
-- ---------------------------
-- Linhas antigas ficam nulas até o pipeline reexportar aquele ano; por isso a
-- coluna não é NOT NULL. Nulo é "não sei de quantos meses veio", que é
-- honesto. Zero afirmaria que nenhum mês contribuiu, que é falso.
-- Ano fechado traz 12.

alter table public.mart_internacoes_municipio
    add column if not exists meses_cobertos smallint;

alter table public.mart_internacoes_agravo
    add column if not exists meses_cobertos smallint;

alter table public.mart_internacoes_hospital
    add column if not exists meses_cobertos smallint;

alter table public.mart_icsap_municipio
    add column if not exists meses_cobertos smallint;

alter table public.mart_fluxo_intermunicipal
    add column if not exists meses_cobertos smallint;

comment on column public.mart_internacoes_municipio.meses_cobertos is
    'Meses do ano presentes no FTP e coletados para a UF deste município. '
    '12 = ano fechado; menos que isso = ano em andamento, cujo TOTAL não é '
    'comparável com o de um ano fechado. NULO = linha anterior ao carimbo.';

comment on column public.mart_internacoes_agravo.meses_cobertos is
    'Meses do ano coletados para a UF deste município. 12 = ano fechado; '
    'menos = ano em andamento. NULO = linha anterior ao carimbo.';

comment on column public.mart_internacoes_hospital.meses_cobertos is
    'Meses do ano coletados para a UF deste hospital. 12 = ano fechado; '
    'menos = ano em andamento. NULO = linha anterior ao carimbo.';

comment on column public.mart_icsap_municipio.meses_cobertos is
    'Meses do ano coletados para a UF deste município. 12 = ano fechado; '
    'menos = ano em andamento — e a taxa de ICSAP do ano parcial não é '
    'comparável com a de um ano fechado. NULO = linha anterior ao carimbo.';

comment on column public.mart_fluxo_intermunicipal.meses_cobertos is
    'MÍNIMO entre a cobertura da UF de residência e a da UF de movimento: o '
    'par de municípios só é tão completo quanto o lado menos completo. '
    '12 = ano fechado. NULO = linha anterior ao carimbo.';
