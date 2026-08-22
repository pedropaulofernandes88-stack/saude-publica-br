# ADR-006 — Backtesting obrigatório antes de publicar previsão

**Status:** Aceito
**Data:** 2026-08-22
**Substitui parcialmente:** [ADR-004](adr-004-prophet-anomaly.md) (arquivado)

## Problema

A plataforma publicava, em `/hospitalar` e num artigo público, uma projeção de
demanda mensal por estabelecimento. O método era tendência linear, descrito com
honestidade na metodologia — mas **nunca havia sido avaliado fora da amostra**.
Não existia backtest, baseline de comparação, medição de cobertura do intervalo
nem critério objetivo para decidir se uma previsão devia aparecer.

O campo exposto na API pública como `confianca` valia `"adequada"` quando o
hospital tinha ≥24 meses de série. É uma propriedade do **tamanho da série**, não
do acerto do modelo, mas o nome levava um consumidor a ler "o modelo prevê bem
este hospital".

Quando o backtest foi construído, ele encontrou quatro problemas concretos:

| problema | evidência |
|---|---|
| previsões retrospectivas publicadas | 786 linhas com `ano_mes_previsto` no passado (a mais antiga, 2022-07), rotuladas "mês previsto" |
| eixo temporal errado | `t = np.arange(n)` sobre linhas observadas; 833 de 4.848 hospitais têm buraco na série |
| intervalo subdeclarado | o IC "de 95%" cobria **85,0%** em 3 meses, piorando de 89,0% → 86,8% → 85,0% |
| rótulo sem lastro | `confianca` derivado só do comprimento da série |

A causa da primeira é estrutural: a carga usava upsert com
`resolution=merge-duplicates` sobre a chave `(cnes, ano_mes_previsto)`. Cada
execução deixava intactas as previsões da âncora anterior, que iam se acumulando
e envelhecendo.

## Alternativas consideradas

**A. Substituir o modelo por um sazonal.** Era a hipótese inicial, apoiada em
evidência real: na série nacional agregada, fevereiro fica 5,9% abaixo da
tendência e agosto 4,3% acima, e um híbrido sazonal+deriva reduzia o erro em ~45%
naquele agregado. **Refutada pelo backtest por hospital**: todos os modelos
sazonais ficaram piores (MASE 1,03 a 1,11 contra 0,92). A amplitude sazonal de
~6% é menor que o ruído de um estabelecimento isolado, e estimar doze efeitos
mensais com 24–36 pontos sobreajusta.

**B. Substituir por média móvel de 3 meses.** É o melhor método medido em todos
os horizontes (MASE 0,762 / 0,846 / 0,917). Mas no horizonte publicado de 3
meses a vantagem sobre a tendência linear é de **0,5%** — dentro do ruído. Trocar
um método já documentado publicamente por esse ganho seria mudança sem benefício
demonstrável.

**C. Adotar Prophet ou ARIMA.** O extra `[ml]` do projeto já traz Prophet. Com
24–36 pontos por série, modelos com mais parâmetros sobreajustam — o que o
`tendencia_sazonal` (13 parâmetros) demonstrou empiricamente ao ficar atrás da
reta de 2 parâmetros. Descartado por evidência, não por preferência.

**D. Manter o método e corrigir só os defeitos.** Escolhida.

## Decisão

1. **O método de previsão permanece a tendência linear**, porque supera o
   baseline sazonal em todos os horizontes e estratos (MASE 0,810 / 0,867 /
   0,922) e nenhuma alternativa mostrou ganho fora do ruído no horizonte
   publicado.

2. **O eixo do ajuste passa a ser o calendário**, não a posição da linha.

3. **O intervalo passa a ser intervalo de predição**, com fator de calibração
   empírico obtido do backtest (z = 2,42 / 2,64 / 2,80 no lugar de 1,96).

4. **Existe âncora única por execução**: toda previsão é posterior à última
   competência da base. Hospital cuja série não a alcança não é projetado.

5. **A tabela é substituída, não mesclada**, a cada carga.

6. **`confianca` dá lugar a `status_validacao` (A/B/C)**, derivado do erro
   medido no estrato de volume. Os limiares (30% e 50% de sMAPE) saem do ponto de
   quebra da distribuição observada — o erro dobra entre 21–100/mês (28,4%) e
   6–20/mês (45,4%) —, não de convenção.

7. **O pipeline recusa-se a publicar sem o relatório de backtest.** Sem
   `data/validacao/forecast_backtest.json`, ele encerra com erro.

## Justificativa

O ponto central não é qual modelo venceu — é que **agora existe um procedimento
que responde à pergunta**. O caso do modelo sazonal ilustra o valor: era a
melhoria óbvia, tinha evidência agregada a favor, e teria piorado o produto. Só o
backtest por unidade mostrou isso.

A decisão de manter o método também importa: validação não é pretexto para trocar
o que funciona. Três dos quatro problemas eram de **engenharia** (eixo, âncora,
upsert) e um de **calibração**. Nenhum era do estimador.

## Impacto

- 340 hospitais deixam de receber projeção (série não alcança a âncora);
- 147 deixam de ser publicados por erro alto (≤5 internações/mês);
- 235 continuam fora por série curta;
- 4.361 hospitais publicados: 3.732 em status A, 629 em B;
- o intervalo publicado **aumentou** de largura — a previsão não piorou, a
  incerteza deixou de ser subdeclarada;
- a coluna `confianca` continua sendo escrita, derivada do status, marcada como
  obsoleta: a API é pública e sem cadastro, e não há como avisar consumidores
  antes de remover.

## Riscos

- **O intervalo largo pode ser lido como "o modelo piorou".** Mitigado pelo texto
  na página e pelo model card, mas o risco de percepção é real.
- **A calibração empírica supõe que o erro futuro se pareça com o histórico.** Com
  3 anos de série, é uma suposição forte; ela deve ser reavaliada a cada nova
  competência.
- **Os limiares de status derivam de uma única rodada de backtest.** Devem ser
  recalculados quando a base crescer, não tratados como constantes.

## Possibilidade de reversão

Alta. `tendencia_linear_publicada` continua no registro de modelos, reproduzindo
exatamente o comportamento anterior — é o que permite medir o que a mudança
comprou. A migração V027 é aditiva e reversível por `DROP COLUMN`. Reverter os
números publicados é reexecutar o pipeline com o método antigo.

## Arquivos relacionados

```
scripts/_series_forecast.py                  núcleo compartilhado
scripts/validate_forecast.py                 backtest e relatório
scripts/forecast_demanda_hospitalar.py       publicação
tests/test_forecast_validacao.py             60 testes de invariante científica
migrations/V027__forecast_metadados_validacao.sql
docs/ML_VALIDATION.md                        metodologia oficial
docs/MODEL_CARD_FORECAST.md                  model card
site/app/hospitalar/hospitalar-cliente.tsx   apresentação
site/app/metodologia/page.tsx                §16
data/validacao/forecast_backtest.{md,json,csv}
```
