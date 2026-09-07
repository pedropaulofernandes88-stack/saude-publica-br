-- V043 — dengue: o ano em andamento passa a dizer que está em andamento
--
-- MOTIVO
-- ------
-- 2026 entrou na base de dengue com 449.101 casos prováveis, ao lado dos
-- 1.643.215 de 2025 e dos 6.564.924 de 2024. Sem qualificação, a leitura óbvia
-- é "a dengue despencou 73%" — e ela mistura duas coisas diferentes:
--
--   o arquivo DENGBR26 cobre 34 semanas epidemiológicas, não 52;
--   as semanas 1–34 concentram de 84% a 97% do total de um ano fechado.
--
-- Ou seja: a queda é REAL (no mesmo recorte de semanas 1–34, 2026 tem 449.101
-- contra 1.517.074 de 2025, e empata com 2021, a mínima anterior da série),
-- mas o total do ano NÃO é comparável com o de um ano fechado. As duas
-- afirmações precisam viajar juntas, e a segunda só viaja se estiver no dado.
--
-- Medido em 2026-09-07: só a semana 34 mostra a borda de truncamento (3.825
-- casos contra média 5.847 de 2019–2025). As semanas 30–33 de 2026 estão acima
-- da média histórica, então não estão truncadas.
--
-- DESENHO
-- -------
-- `semanas_cobertas` é NACIONAL por ano, repetida em cada linha do município.
-- É redundante de propósito: quem lê uma linha isolada — pelo CSV, pela API ou
-- pelo Parquet — vê a ressalva junto do número que ela qualifica, sem precisar
-- de rodapé. Contar por município seria outra coisa e mediria outra coisa: um
-- município pequeno pode legitimamente notificar em poucas semanas sem que o
-- ano esteja incompleto.
--
-- Mesmo desenho de `meses_cobertos` em mart_sifilis_municipio (2026-09-06).
--
-- Nula nas linhas antigas até a reexportação do pipeline preenchê-la; por isso
-- a coluna não é NOT NULL. Ano fechado traz 52 ou 53 (2020 e 2025 têm 53).

alter table public.mart_dengue_municipio_ano
    add column if not exists semanas_cobertas smallint;

comment on column public.mart_dengue_municipio_ano.semanas_cobertas is
    'Semanas epidemiológicas com notificação no arquivo daquele ano, nacional. '
    '52 ou 53 = ano fechado; menos que isso = ano em andamento, cujo TOTAL não '
    'é comparável com o de um ano fechado (compare semana a semana).';
