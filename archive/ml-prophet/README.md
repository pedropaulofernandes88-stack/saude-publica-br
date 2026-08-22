# `ml/` — detecção de anomalias com Prophet

**Nada aqui está implantado, é executado por CI ou alimenta o site.** Arquivado
em 2026-08-22.

## Por que saiu

O módulo detectava anomalias em séries mensais de **produção ambulatorial
(SIA/PA)** usando Meta Prophet, com Z-score como fallback para séries curtas.
Era a camada de ML da primeira arquitetura, junto com a API FastAPI que hoje
vive em `archive/api/`.

Quatro verificações, todas negativas:

| verificação | resultado |
|---|---|
| algum script de `scripts/` importa `ml/`? | não |
| o site consulta anomalias? | não — nenhuma referência em `site/` |
| `mart_anomalias_prophet` existe em produção? | **não** — `to_regclass` devolve `null`; a migração V006 nunca foi aplicada |
| SIA está no pipeline atual? | não — as fontes são SIM, SINAN, SIH, SINASC, CNES, SIOPS |

O efeito colateral visível eram **7 testes permanentemente skipados** por
ausência do extra `[ml]`. A leitura natural desse skip é "falta instalar a
dependência"; a leitura correta era "este código não tem consumidor". Instalar
Prophet no CI para exercitá-los custaria minutos de execução por commit para
validar software que nada executa.

## O que veio no lugar

Nada, e de propósito. A camada preditiva que a plataforma de fato publica é o
**forecast de demanda hospitalar** (`scripts/forecast_demanda_hospitalar.py`),
que nunca usou Prophet — usa tendência linear e passou a ter backtesting próprio
em `scripts/validate_forecast.py`. É lá que o esforço de validação de modelo
passou a ser aplicado.

O `tendencia_sazonal` do novo núcleo (`scripts/_series_forecast.py`) cobre a
única capacidade que o Prophet acrescentaria aqui — decomposição tendência +
sazonalidade — e o backtest mostrou que, **por hospital**, ela fica pior que a
tendência simples: MASE 1,032 contra 0,922 em 3 meses. A sazonalidade existe no
agregado nacional, mas é menor que o ruído de um estabelecimento isolado.

## O que está aqui

```
ml/                                 módulo original (anomaly_detector, batch_scorer)
test_ml_anomaly_detector.py         os 7 testes que ficavam skipados
V006__mart_anomalias_prophet.sql    migração nunca aplicada em produção
suite_mart_anomalias_prophet.py     suite Great Expectations do mart inexistente
```

O ADR original continua em `docs/architecture/adr-004-prophet-anomaly.md`, com
nota de arquivamento — a decisão foi real e o registro dela é útil.

## Como reviver

Se a detecção de anomalias voltar (sobre SIH ou SINAN, que estão no pipeline),
o caminho é: mover de volta, aplicar a V006 adaptada ao mart de destino,
reintroduzir a suite em `validation/suites/__init__.py`, e **criar um job de CI
que instale `[ml]` e rode os testes de verdade** — porque aí eles passariam a
proteger código publicado.
