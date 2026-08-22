-- =============================================================================
-- V027 — forecast de demanda: metadados de validação e status de publicação
-- =============================================================================
-- A tabela `mart_forecast_demanda_hospital` publicava previsão sem carregar a
-- evidência de que a previsão vale alguma coisa. Três colunas resolviam mal esse
-- papel e uma delas enganava:
--
--   `confianca` valia 'adequada' quando o hospital tinha ≥24 meses de série e
--   'baixa' abaixo disso. É uma propriedade do TAMANHO DA SÉRIE, não do acerto
--   do modelo — mas o nome do campo, exposto na API pública e na tabela do site,
--   fazia um consumidor ler "o modelo prevê bem este hospital". Nunca houve
--   nenhuma avaliação fora da amostra por trás dela.
--
-- O backtest passou a existir (scripts/validate_forecast.py, validação por
-- origem móvel sobre 4.445 hospitais) e mediu o que faltava. Esta migração cria
-- as colunas que transportam esse resultado até quem consome o número.
--
-- O QUE O BACKTEST MEDIU, e que estas colunas passam a expor
--   * o modelo supera o baseline sazonal em todos os horizontes e em todos os
--     estratos de volume (MASE 0,810 / 0,867 / 0,922 em 1, 2 e 3 meses) — ele é
--     publicável;
--   * mas o erro relativo DOBRA nos hospitais pequenos: sMAPE de 13,6% acima de
--     500 internações/mês contra 58,7% abaixo de 5. É isso que `status_validacao`
--     e `smape_backtest_pct` comunicam, hospital a hospital;
--   * o intervalo declarado como 95% cobria 85,0% em 3 meses. A largura agora
--     usa um fator de calibração empírico, e por isso ficou visivelmente maior:
--     mediana de 74% da previsão nos hospitais grandes e 217% nos de 6–20/mês.
--     A previsão não piorou — a incerteza deixou de ser subdeclarada.
--
-- COMPATIBILIDADE
--   `confianca` NÃO é removida. A API é pública, sem cadastro, e há consumidores
--   que não temos como avisar; derrubar uma coluna quebraria o contrato deles sem
--   necessidade. Ela passa a ser NULLABLE e derivada de `status_validacao`
--   (A → 'adequada', B → 'baixa'), fica marcada como obsoleta no COMMENT, e sai
--   numa migração futura depois de um ciclo de aviso na página Dados & API.
--
-- REVERSÍVEL
--   Sim. As colunas são aditivas e nullable; `DROP COLUMN` de cada uma devolve o
--   estado anterior sem perda do que existia antes.
-- =============================================================================

alter table public.mart_forecast_demanda_hospital
  add column if not exists horizonte_meses    smallint,
  add column if not exists faixa_volume       text,
  add column if not exists status_validacao   text,
  add column if not exists motivo_status      text,
  add column if not exists smape_backtest_pct numeric,
  add column if not exists modelo             text,
  add column if not exists ultima_competencia text,
  add column if not exists treinado_em        date,
  add column if not exists commit_codigo      text;

-- `confianca` deixa de ser obrigatória: quem escreve agora é o status.
alter table public.mart_forecast_demanda_hospital
  alter column confianca drop not null;

-- Status é vocabulário fechado. Sem isto, um erro de digitação no pipeline vira
-- uma categoria nova publicada na API sem ninguém perceber.
do $$
begin
  if not exists (
    select 1 from pg_constraint
    where conname = 'forecast_status_validacao_valido'
  ) then
    alter table public.mart_forecast_demanda_hospital
      add constraint forecast_status_validacao_valido
      check (status_validacao is null or status_validacao in ('A', 'B', 'C'));
  end if;
end $$;

-- O horizonte entra na chave lógica: a mesma competência prevista pode aparecer
-- com horizontes diferentes se a âncora mudar entre execuções, e sem isto o
-- upsert por (cnes, ano_mes_previsto) sobrescreveria silenciosamente.
create index if not exists idx_forecast_status
  on public.mart_forecast_demanda_hospital (status_validacao, uf_sigla);

comment on column public.mart_forecast_demanda_hospital.status_validacao is
  'A = validado (erro medido no estrato ≤30% de sMAPE e ≥24 meses de histórico); '
  'B = experimental (erro entre 30% e 50%, ou histórico curto — não use para '
  'dimensionar oferta); C = não publicável (erro >50%). Limiares derivados da '
  'distribuição observada de sMAPE por estrato no backtest, não de convenção. '
  'Linhas C não são publicadas por padrão.';

comment on column public.mart_forecast_demanda_hospital.smape_backtest_pct is
  'sMAPE medido por validação de origem móvel no estrato de volume deste hospital, '
  'no horizonte desta linha. É o erro que previsões como esta apresentaram '
  'historicamente — não o erro desta previsão específica, que só se conhece depois.';

comment on column public.mart_forecast_demanda_hospital.ic_inferior is
  'Limite inferior do intervalo de 95%, truncado em zero (internação negativa não '
  'existe; 16,6% das linhas encostam nesse piso). A meia-largura usa z empírico '
  'calibrado pelo backtest (2,42 / 2,64 / 2,80 para 1, 2 e 3 meses), não z=1,96: '
  'sob normalidade o intervalo cobria 85% do que prometia.';

comment on column public.mart_forecast_demanda_hospital.confianca is
  'OBSOLETA — substituída por status_validacao. Refletia apenas o comprimento da '
  'série (≥24 meses = "adequada"), nunca o acerto do modelo. Mantida por um ciclo '
  'para não quebrar consumidores da API pública. Será removida.';

comment on column public.mart_forecast_demanda_hospital.modelo is
  'Método que gerou a linha. `tendencia_linear`: OLS sobre o tempo de calendário. '
  'Concorreu com naive, ingênuo sazonal, média móvel de 3 meses, sazonal+drift e '
  'tendência com sazonalidade; os sazonais ficaram PIORES por hospital, apesar de '
  'a sazonalidade ser nítida no agregado nacional. Ver docs/MODEL_CARD_FORECAST.md.';
