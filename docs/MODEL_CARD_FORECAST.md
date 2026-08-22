# Model card — forecast de demanda hospitalar

**Modelo:** `tendencia_linear` · **Versão:** 2 · **Data:** 2026-08-22
**Código:** [`scripts/forecast_demanda_hospitalar.py`](../scripts/forecast_demanda_hospitalar.py) ·
[`scripts/_series_forecast.py`](../scripts/_series_forecast.py)
**Validação:** [`scripts/validate_forecast.py`](../scripts/validate_forecast.py) →
`data/validacao/forecast_backtest.md`
**Tabela publicada:** `mart_forecast_demanda_hospital` ·
**Página:** [saudeemdado.com/hospitalar](https://saudeemdado.com/hospitalar/)

---

## Objetivo

Projetar o volume mensal de internações (AIH aprovadas) de cada estabelecimento
do SUS para os três meses seguintes à última competência disponível, com uma
faixa de incerteza que corresponda ao erro efetivamente observado.

## Uso pretendido

- Dar **ordem de grandeza** da demanda esperada de um hospital no curtíssimo prazo.
- Servir de ponto de partida para conversa sobre capacidade — sempre pela faixa,
  nunca pelo ponto.
- Ser auditável: cada linha publicada carrega o modelo, a competência de treino,
  o commit do código e o erro medido no seu estrato.

## Usos **não** recomendados

- **Dimensionar leitos, escalas ou orçamento.** O intervalo de 95% tem largura
  mediana de 74% da previsão nos hospitais grandes e 217% nos de 6–20
  internações/mês. Não há precisão para isso, e a largura declarada é o aviso.
- **Comparar hospitais.** O modelo é ajustado por estabelecimento, sem ajuste de
  case-mix, porte ou área de captação.
- **Ler queda prevista como piora assistencial.** A projeção segue a tendência
  observada, que mistura demanda, oferta, credenciamento e registro.
- **Qualquer horizonte além de 3 meses.** Não foi validado além disso.
- **Hospitais com menos de 5 internações/mês.** Não são publicados: o erro medido
  ali passa de 50% de sMAPE.

## Dados

| | |
|---|---|
| Fonte | SIH/SUS (AIH), via `mart_demanda_mensal_hospital` |
| Unidade | estabelecimento (CNES) × mês |
| Período | 2022-01 a 2024-12 (36 meses) |
| Linhas | 164.039 |
| Hospitais na fonte | 5.083 |
| Hospitais publicados | 4.361 |
| Variável | `internacoes` = AIHs **aprovadas**, não pacientes nem episódios |

`internacoes` conta AIHs aprovadas. Uma internação longa emite várias AIHs
(continuação), e a AIH pública não tem identificador de paciente. A série
prevista é de **produção**, não de pessoas.

### População excluída da publicação, e por quê

| motivo | hospitais |
|---|---:|
| série com menos de 6 meses observados | 235 |
| série não alcança a última competência (2024-12) | 340 |
| estrato de erro alto (≤5 internações/mês, status C) | 147 |

A exclusão por **não alcançar a âncora** é a correção de um defeito, não uma
escolha estatística: a versão anterior projetava a partir do último mês *daquele
hospital*, o que publicava previsões para meses já passados — 786 linhas com
`ano_mes_previsto` anterior a 2025 estavam no ar, rotuladas "mês previsto".

## Método

Regressão linear por mínimos quadrados de `internacoes` sobre o **tempo de
calendário**, ajustada separadamente para cada hospital.

Intervalo: intervalo de predição da regressão — que cresce com a distância da
extrapolação e incorpora a incerteza dos coeficientes — multiplicado por um
**fator de calibração empírico** obtido do backtest:

| horizonte | z aplicado | z sob normalidade |
|---|---:|---:|
| 1 mês | 2,42 | 1,96 |
| 2 meses | 2,64 | 1,96 |
| 3 meses | 2,80 | 1,96 |

O fator é o quantil 95% de |erro| / σ observado na validação. Ele existe porque
os resíduos não são normais: são contagens, assimétricas à direita.

## Validação

**Origem móvel (walk-forward).** Para cada hospital e cada origem a partir de 24
meses de treino, o modelo vê apenas `série[:origem]` e prevê 1, 2 e 3 meses à
frente. As funções de previsão recebem só o passado — a separação é estrutural,
garantida pela assinatura, não por disciplina.

Nenhum `train_test_split` aleatório é usado, e nenhum existe no código.

- **Hospitais avaliados:** 4.445
- **Origens por hospital:** mediana de 11
- **Previsões avaliadas:** ~915 mil (7 modelos × 3 horizontes)

## Baselines

Seis métodos concorreram nas mesmas origens:

| método | ideia |
|---|---|
| `naive` | repete o último mês |
| `seasonal_naive` | repete o mesmo mês do ano anterior — **referência do MASE** |
| `media_movel_3` | média dos 3 últimos meses |
| `tendencia_linear_publicada` | réplica exata do método anterior, com seus defeitos |
| `tendencia_linear` | **o publicado** — eixo de calendário e intervalo de predição |
| `snaive_drift` | sazonal ingênuo corrigido pela tendência anual |
| `tendencia_sazonal` | tendência + 11 dummies mensais |

## Métricas

Horizonte de 3 meses, todos os hospitais:

| modelo | MAE | sMAPE % | MASE | Cobertura IC95 % | z empírico |
|---|---:|---:|---:|---:|---:|
| `media_movel_3` | 41,8 | 23,18 | **0,917** | 97,1 | 1,61 |
| `tendencia_linear` *(publicado)* | 43,9 | 24,68 | 0,922 | 87,5 | 2,80 |
| `tendencia_linear_publicada` *(anterior)* | 43,9 | 24,69 | 0,922 | **85,0** | 3,05 |
| `naive` | 46,1 | 25,65 | 1,013 | 97,1 | 1,63 |
| `tendencia_sazonal` | 50,8 | 28,09 | 1,032 | 88,0 | 2,68 |
| `seasonal_naive` | 53,7 | 28,63 | 1,081 | 88,3 | 2,68 |
| `snaive_drift` | 55,1 | 30,53 | 1,105 | 87,9 | 2,68 |

MASE por horizonte do modelo publicado: **0,810 / 0,867 / 0,922** (1, 2 e 3
meses). Abaixo de 1 em todos — ele supera o baseline sazonal.

MAPE não é reportado: 290 hospitais têm mediana ≤5 internações/mês, e com real
próximo de zero o MAPE mede o denominador, não o modelo. Em seu lugar, sMAPE e
WAPE.

### Por estrato de volume (3 meses)

| faixa | hospitais | sMAPE % | MASE | status |
|---|---:|---:|---:|---|
| >500/mês | 630 | 13,6 | 0,875 | A |
| 101–500/mês | 1.673 | 18,3 | 0,892 | A |
| 21–100/mês | 1.471 | 28,4 | 0,964 | A |
| 6–20/mês | 517 | 45,4 | 0,967 | B |
| ≤5/mês | 109 | 58,7 | 0,944 | **C — não publicado** |

O modelo supera o baseline em **todos** os estratos. O que separa publicável de
não publicável aqui não é a comparação relativa — é a magnitude do erro.

## Critérios de publicação

| status | critério | efeito |
|---|---|---|
| **A — validado** | sMAPE do estrato ≤30% e ≥24 meses de histórico | publicado |
| **B — experimental** | sMAPE entre 30% e 50%, ou histórico curto | publicado com aviso |
| **C — não publicável** | sMAPE >50% | descartado |

Os cortes de 30% e 50% saem da distribuição observada: o erro aproximadamente
**dobra** ao passar de 21–100/mês (28,4%) para 6–20/mês (45,4%). O corte foi
posto nesse ponto de quebra, não escolhido por convenção.

Distribuição publicada: **3.732 hospitais em A**, **629 em B**, 147 descartados
em C.

## Limitações

1. **Três anos de histórico.** 2022–2024. Não há como avaliar comportamento
   sobre ciclos longos nem sobre choque estrutural.
2. **Sem sazonalidade, por evidência.** No agregado nacional a sazonalidade é
   nítida — fevereiro fica 5,9% abaixo da tendência, agosto 4,3% acima. **Por
   hospital, todos os modelos sazonais ficaram piores** (MASE 1,03 a 1,11 contra
   0,92). A amplitude de ~6% é menor que o ruído de um estabelecimento isolado, e
   estimar doze efeitos mensais com 24–36 pontos sobreajusta. O que é verdade no
   agregado não transferiu para a unidade.
3. **Intervalo largo.** É o resultado honesto, não um defeito da apresentação: a
   demanda mensal de um hospital é intrinsecamente ruidosa.
4. **Ecológico e retrospectivo.** Descreve produção registrada, não necessidade
   de saúde.
5. **Só rede SUS.** Internação privada não aparece no SIH.
6. **Sem case-mix.** A série é de volume total.

## Tratamento de incompletude

Mês sem AIH entra como **ausente (NaN)**, nunca como zero. Preencher com zero
diria ao modelo que houve demanda nula, quando o que houve foi ausência de
registro — a distinção que o resto da metodologia da plataforma mantém.

833 dos 4.848 hospitais elegíveis têm buraco na série. É por causa deles que o
eixo precisou virar calendário: a versão anterior numerava as linhas observadas
em sequência, comprimindo o eixo e inflando a inclinação por passo. Numa série
sintética sem ruído com quatro meses faltando, o método antigo erra 3,1%; o novo
recupera o valor exato.

## Tratamento da pandemia

A série começa em 2022-01, depois do choque agudo de 2020–21 mas dentro da
recuperação. **Nenhum ponto foi removido.** Excluir período "atípico" sem
critério é a forma mais fácil de fabricar um resultado bom, e a validação por
origem móvel já expõe o desempenho por origem.

## Riscos

- **Ler o ponto e ignorar a faixa.** É o risco principal, e por isso o intervalo
  ganhou o mesmo destaque visual do ponto na página.
- **Interpretar exclusão como fechamento.** Um hospital ausente da tabela pode
  ter parado de reportar, mudado de código CNES ou sido descredenciado — a
  plataforma não distingue.
- **Extrapolar tendência recente como se fosse estrutural.** O modelo é
  deliberadamente simples e não detecta mudança de regime.

## Interpretabilidade

Duas retas por hospital (nível e inclinação) e um intervalo. Reprodutível à mão
a partir da série publicada em `mart_demanda_mensal_hospital`.

## Atualização

Reprocessado a cada nova competência do SIH. **O pipeline recusa-se a publicar
sem o backtest**: se `data/validacao/forecast_backtest.json` não existir, ele
falha com instrução para rodar `validate_forecast.py`. Não é possível voltar ao
estado de publicar previsão sem avaliação fora da amostra.

A tabela é **substituída**, não mesclada, a cada execução — foi o upsert por
merge que acumulou as 786 previsões retrospectivas.

## Versionamento

| versão | data | mudança |
|---|---|---|
| 1 | — | tendência linear sobre posição da linha; banda de resíduo constante; `confianca` pelo tamanho da série; sem validação |
| **2** | 2026-08-22 | eixo de calendário; intervalo de predição com calibração empírica; âncora única; status derivado do erro medido; backtest obrigatório |

Cada linha publicada carrega `modelo`, `ultima_competencia`, `treinado_em` e
`commit_codigo`.
