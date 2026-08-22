# Metodologia de validação de modelos preditivos

Como a plataforma decide se uma previsão pode ser publicada. Vale para o
forecast de demanda hospitalar e para qualquer modelo preditivo que venha depois.

> Documento de método. Os resultados de cada rodada ficam em
> `data/validacao/forecast_backtest.md`, gerado por
> [`scripts/validate_forecast.py`](../scripts/validate_forecast.py). O model card
> do modelo em produção é [`MODEL_CARD_FORECAST.md`](MODEL_CARD_FORECAST.md).

---

## 1. A regra

**Nenhuma previsão é publicada sem avaliação fora da amostra.**

Não é aspiração: está no código. `forecast_demanda_hospitalar.py` lê
`data/validacao/forecast_backtest.json` para obter o fator de calibração do
intervalo e o erro por estrato. Sem esse arquivo, ele encerra com erro e a
instrução de rodar o validador. Publicar sem validar exige apagar código, não
apenas esquecer um passo.

## 2. Por que isto existe

A plataforma publicava, em `/hospitalar`, uma projeção de demanda por
estabelecimento descrita em artigo público. Ela nunca havia sido avaliada fora
da amostra. Quando o backtest foi construído, encontrou:

| defeito | evidência |
|---|---|
| previsões retrospectivas no ar | 786 linhas com `ano_mes_previsto` no passado, algumas de 2022, rotuladas "mês previsto" |
| eixo temporal errado | `t = np.arange(n)` sobre linhas observadas; 833 de 4.848 hospitais têm buraco na série |
| intervalo subdeclarado | o IC "de 95%" cobria **85,0%** em 3 meses, e piorava com o horizonte |
| rótulo de confiança sem lastro | `confianca = "adequada"` significava só "≥24 meses de série" |

Nenhum deles apareceria em teste unitário, em type-check ou em revisão de código.
Todos apareceram na primeira execução do backtest.

## 3. Separação temporal

### Origem móvel (walk-forward)

Para cada série e cada origem `o` a partir de um mínimo de treino:

```
treino = série[:o]                    ← tudo que o modelo vê
teste  = série[o], série[o+1], ...    ← nunca passado ao modelo
```

A origem avança um mês por vez, e o modelo é reajustado do zero em cada uma.

**A garantia é estrutural.** Toda função de previsão tem a assinatura
`(y_treino, h) -> Previsao`: ela não recebe o futuro, então não pode lê-lo. Não
depende de ninguém lembrar de fatiar corretamente.

### O que é proibido

- `train_test_split` aleatório. Embaralhar série temporal treina o modelo com o
  futuro e produz métrica que não se realiza em produção. Não existe no código.
- Normalizar, imputar ou escolher hiperparâmetro usando a série inteira. Qualquer
  estatística derivada dos dados tem de sair só do treino da origem corrente —
  inclusive o denominador do MASE e o fator de calibração do intervalo.
- Escolher o modelo olhando o teste e depois reportar o teste como validação.

### Como isso é testado

`tests/test_forecast_validacao.py` roda duas séries idênticas até o mês 30 e
radicalmente diferentes depois. As previsões de todas as origens ≤30 têm de
coincidir dígito a dígito. Se algum modelo passar a enxergar o futuro, o teste
cai — e é o tipo de erro que nenhuma métrica denuncia, porque só melhora o
resultado.

### Treino mínimo

24 meses (dois ciclos anuais). É o mínimo para um modelo sazonal ser
identificável; com menos, metade dos concorrentes não pode ser estimada e a
comparação passaria a envolver conjuntos diferentes de origens.

## 4. Baselines

**Todo modelo é comparado com métodos triviais.** Obrigatórios:

- `naive` — repete o último valor;
- `seasonal_naive` — repete o mês homólogo do ano anterior;
- `media_movel_3` — média dos três últimos meses;
- tendência linear.

E, quando a série sustentar, métodos sazonais (`snaive_drift`,
`tendencia_sazonal`).

**Um modelo complexo só se mantém se superar consistentemente os simples.** No
forecast hospitalar essa regra produziu um resultado inesperado: os modelos
sazonais, mais sofisticados, ficaram **piores** (MASE 1,03–1,11 contra 0,92 da
tendência simples), apesar de a sazonalidade ser nítida no agregado nacional
(fevereiro 5,9% abaixo da tendência). Por hospital, a amplitude sazonal de ~6% é
menor que o ruído, e estimar doze efeitos mensais com 24–36 pontos sobreajusta.

Fica o princípio: **o que é verdade no agregado não transfere automaticamente
para a unidade**. Foi o backtest que impediu a troca por um modelo pior.

## 5. Métricas

| métrica | papel |
|---|---|
| MAE | erro médio na unidade do dado |
| RMSE | penaliza erro grande |
| sMAPE | erro relativo, robusto a valor pequeno |
| WAPE | erro ponderado por volume — o que interessa a quem olha a rede |
| **MASE** | **a régua**: erro ÷ erro do ingênuo sazonal no treino |
| cobertura | % de observações dentro do IC declarado |
| largura | largura média do IC como % da previsão |
| z empírico | z que entregaria a cobertura nominal de verdade |

### Sobre o MAPE

Não é reportado. 290 dos 5.083 hospitais têm mediana ≤5 internações/mês. Com real
próximo de zero, o MAPE mede o denominador, não o modelo. sMAPE e WAPE ocupam o
lugar.

### Sobre o MASE

`MASE < 1` significa que o modelo supera o ingênuo sazonal calculado **dentro do
treino de cada origem**. É o critério de valor: um modelo que não passa dele não
está acrescentando nada a repetir o ano anterior.

Quando a série é exatamente periódica o denominador é zero e o MASE é indefinido
— devolver `NaN` é correto, porque dividir por zero produziria um "ganho
infinito" que o relatório publicaria como mérito.

### Intervalos: cobertura **e** largura, sempre juntas

Cobertura sozinha não diz nada. Um intervalo cobre 95% por estar calibrado ou por
ser largo demais para informar. Só o par distingue os dois casos, e o relatório
publica os dois.

O **z empírico** torna a subdeclaração legível: é o quantil 95% de |erro| / σ. Sob
normalidade daria 1,96. No método anterior dava **3,05** no horizonte de 3 meses
— o intervalo estava 56% estreito demais.

### Calibração empírica

Quando o z empírico se afasta do teórico, o intervalo publicado passa a usar o
empírico. É legítimo porque o conjunto de calibração é o **passado** (o histórico
de backtest) e a aplicação é o futuro. O fator aplicado fica registrado no model
card e nas linhas publicadas.

## 6. Horizontes

Avaliados e reportados **separadamente**. Uma métrica agregada esconderia a
deterioração do horizonte longo, que é justamente o que interessa a quem planeja.

No forecast hospitalar, do horizonte 1 para o 3: MASE de 0,810 para 0,922, e
cobertura do método anterior de 89,0% para 85,0%. Uma média teria escondido as
duas curvas.

## 7. Estratificação e números pequenos

Métrica agregada esconde desempenho em série esparsa. O forecast hospitalar é
avaliado por faixa de volume mensal mediano:

| faixa | hospitais | sMAPE % (3m) |
|---|---:|---:|
| >500/mês | 630 | 13,6 |
| 101–500/mês | 1.673 | 18,3 |
| 21–100/mês | 1.471 | 28,4 |
| 6–20/mês | 517 | 45,4 |
| ≤5/mês | 109 | 58,7 |

Sem estratificar, o número único de 24,7% sugeriria qualidade uniforme. Ela não é
uniforme: o erro mais que quadruplica entre os extremos.

Para série esparsa: agregar, suprimir ou marcar. **Nunca publicar previsão
pontual com aparência de precisão sobre contagem baixa.**

## 8. Completude e atraso de notificação

SIM, SINAN e SIH revisam dado já publicado. Queda recente pode ser queda real ou
registro incompleto, e **o modelo não distingue** — a não ser que a plataforma o
impeça de tentar.

Regras:

- mês ausente entra como **NaN**, nunca zero;
- competência recente incompleta não entra no treino;
- há **âncora única** por execução: todas as previsões são posteriores à última
  competência da base, nunca ao último mês de cada série;
- série que não alcança a âncora **não é projetada**. Não sabemos se o
  estabelecimento fechou, descredenciou ou está atrasado, e as três hipóteses
  levam a leituras diferentes.

## 9. Pandemia e mudança estrutural

2020–2022 não é comportamento epidemiológico normal, e **não é removido
automaticamente**. Excluir período atípico sem critério é a forma mais fácil de
fabricar um resultado bom.

Qualquer tratamento adotado é declarado no model card. No caso atual não há
nenhum: a série do SIH hospitalar começa em 2022-01, e todos os pontos entram.

## 10. Critérios de publicação

| status | significado |
|---|---|
| **A — validado** | supera o baseline, erro aceitável no estrato, volume e completude suficientes |
| **B — experimental** | funcional e promissor, evidência insuficiente para apoio decisório |
| **C — não publicar** | erro alto, instabilidade, volume insuficiente ou inferior ao baseline |

**Os limiares saem de análise empírica, não de convenção.** No forecast
hospitalar, o corte veio da distribuição observada de sMAPE por estrato: o erro
aproximadamente dobra entre 21–100/mês (28,4%) e 6–20/mês (45,4%), e os cortes de
30% e 50% foram postos nesse ponto de quebra.

Um limiar redondo escolhido antes de olhar os dados seria arbitrário com
aparência de rigor.

## 11. Linguagem

Previsão nunca é apresentada como certeza.

| usar | evitar |
|---|---|
| "o modelo estima" | "vai ocorrer" |
| "o intervalo previsto é" | "serão registrados" |
| "cenário esperado" | "acontecerá" |
| "previsões deste porte erraram X% historicamente" | "precisão de X%" |

A página `/hospitalar` diz literalmente: *"O número do meio é uma estimativa, não
uma previsão do que vai ocorrer"*, seguido do erro histórico do estrato.

## 12. Metadados obrigatórios

Toda previsão publicada carrega:

`modelo` · `ultima_competencia` · `treinado_em` · `commit_codigo` ·
`horizonte_meses` · `n_meses_historico` · `faixa_volume` · `status_validacao` ·
`motivo_status` · `smape_backtest_pct` · `ic_inferior` · `ic_superior`

É o que permite a alguém, meses depois, reconstruir exatamente como um número foi
produzido.

## 13. Reprodutibilidade

```bash
python scripts/validate_forecast.py
```

Gera CSV, JSON e Markdown em `data/validacao/`. Sem aleatoriedade e sem rede:
duas execuções sobre a mesma base produzem números idênticos. A amostragem do
`--amostra` é determinística (primeiros CNES em ordem), não sorteada, pela mesma
razão.

Modelos estocásticos, se vierem, usarão `random_state` explícito e a semente será
registrada no model card.

## 14. Regressão científica

`tests/test_forecast_validacao.py` protege as invariantes que nenhum type-check
pega:

- previsão não retorna NaN inesperado, e retorna NaN quando **deve** (série curta);
- `ic_inferior ≤ previsão ≤ ic_superior`, inclusive com truncamento em zero;
- previsão de contagem nunca é negativa;
- σ do intervalo de predição **cresce** com o horizonte;
- alterar o futuro não muda a previsão da origem (ausência de vazamento);
- modelos são determinísticos;
- MASE vale exatamente 1 no ponto de indiferença;
- sMAPE e WAPE toleram zero;
- o modelo publicado está no registro avaliado — o relatório mede o método real,
  não uma idealização dele.

Tolerâncias são justificadas caso a caso. Diferença estatisticamente irrelevante
não bloqueia mudança; o que bloqueia é quebra de invariante.

## 15. Para o próximo modelo

Ordem mínima antes de publicar qualquer previsão:

1. escreva o backtest de origem móvel **antes** do modelo;
2. rode os baselines triviais primeiro — eles podem vencer;
3. meça cobertura e largura, não só erro pontual;
4. estratifique por volume;
5. derive os limiares de publicação da distribuição observada;
6. escreva o model card, incluindo o que o modelo **não** pode responder;
7. faça o pipeline recusar-se a publicar sem o relatório de validação.
