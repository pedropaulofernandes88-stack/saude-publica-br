# Validação do forecast de demanda hospitalar

> Gerado por `scripts/validate_forecast.py`. Não editar à mão: qualquer
> alteração é sobrescrita na próxima execução.

| | |
|---|---|
| Gerado em | 2026-09-19 18:46 UTC |
| Commit | `5ac8a5d` |
| Fonte | `mart_demanda_mensal_hospital` |
| Período | 2022-01 a 2026-07 |
| Hospitais na fonte | 5,287 |
| Hospitais avaliados | 4,651 |
| Treino mínimo | 24 meses |
| Origens por hospital | mediana 28.4 |
| Validação | origem móvel (walk-forward), sem embaralhamento |

## Como ler

**MASE** é a régua: erro do modelo dividido pelo erro do ingênuo sazonal
dentro do treino. Abaixo de 1, o modelo acrescenta algo; acima, não.

**Cobertura** e **largura** andam juntas. Um intervalo pode cobrir 95%
por estar calibrado ou por ser largo demais para informar — só o par
distingue os dois casos.

**Horizontes são reportados separados** de propósito: uma média única
esconderia a deterioração do horizonte longo.

## Horizonte de 1 mês

| Modelo | MAE | RMSE | sMAPE % | WAPE % | MASE | Cobertura IC95 % | Largura IC % | z empírico | Veredito |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| `media_movel_3` | 35.2 | 75.7 | 19.89 | 12.73 | 0.736 | 92.7 | 106.5 | 2.24 | supera o baseline |
| `tendencia_linear` | 39.9 | 82.9 | 22.59 | 14.43 | 0.806 | 91.3 | 114.3 | 2.37 | supera o baseline |
| `tendencia_linear_publicada` | 39.9 | 82.9 | 22.59 | 14.44 | 0.806 | 89.9 | 104.3 | 2.51 | supera o baseline · *publicado hoje* |
| `naive` | 38.3 | 84.8 | 21.81 | 13.87 | 0.807 | 92.7 | 127.6 | 2.25 | supera o baseline |
| `tendencia_sazonal` | 45.6 | 95.2 | 25.89 | 16.48 | 0.909 | 91.5 | 3767561277166.4 | 2.32 | supera o baseline |
| `seasonal_naive` | 52.0 | 110.9 | 29.00 | 18.83 | 1.042 | 90.4 | 151.8 | 2.44 | baseline (MASE ≡ 1) |
| `snaive_drift` | 52.4 | 111.2 | 29.76 | 18.97 | 1.045 | 90.9 | 200.4 | 2.37 | **não supera o baseline** |


## Horizonte de 2 meses

| Modelo | MAE | RMSE | sMAPE % | WAPE % | MASE | Cobertura IC95 % | Largura IC % | z empírico | Veredito |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| `media_movel_3` | 38.7 | 82.4 | 21.61 | 13.96 | 0.811 | 96.3 | 144.0 | 1.76 | supera o baseline |
| `tendencia_linear` | 42.1 | 87.3 | 23.71 | 15.17 | 0.854 | 89.7 | 107.9 | 2.55 | supera o baseline |
| `tendencia_linear_publicada` | 42.1 | 87.4 | 23.72 | 15.18 | 0.854 | 88.1 | 103.6 | 2.72 | supera o baseline · *publicado hoje* |
| `naive` | 42.3 | 91.4 | 23.85 | 15.23 | 0.891 | 96.2 | 171.6 | 1.78 | supera o baseline |
| `tendencia_sazonal` | 47.4 | 99.0 | 26.68 | 17.07 | 0.948 | 90.1 | 78212.0 | 2.47 | supera o baseline |
| `seasonal_naive` | 52.2 | 111.5 | 28.94 | 18.80 | 1.055 | 89.9 | 150.4 | 2.51 | baseline (MASE ≡ 1) |
| `snaive_drift` | 53.6 | 113.9 | 30.19 | 19.30 | 1.073 | 89.9 | 169.9 | 2.49 | **não supera o baseline** |


## Horizonte de 3 meses

| Modelo | MAE | RMSE | sMAPE % | WAPE % | MASE | Cobertura IC95 % | Largura IC % | z empírico | Veredito |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| `media_movel_3` | 41.4 | 86.9 | 22.86 | 14.84 | 0.869 | 97.5 | 170.2 | 1.54 | supera o baseline |
| `tendencia_linear` | 44.1 | 90.9 | 24.66 | 15.81 | 0.896 | 88.5 | 111.9 | 2.69 | supera o baseline |
| `tendencia_linear_publicada` | 44.1 | 91.0 | 24.68 | 15.82 | 0.896 | 86.6 | 105.2 | 2.88 | supera o baseline · *publicado hoje* |
| `naive` | 45.8 | 96.8 | 25.45 | 16.41 | 0.963 | 97.4 | 203.1 | 1.57 | supera o baseline |
| `tendencia_sazonal` | 49.0 | 102.1 | 27.33 | 17.57 | 0.982 | 89.0 | 106543.3 | 2.57 | supera o baseline |
| `seasonal_naive` | 52.3 | 111.5 | 28.82 | 18.74 | 1.064 | 89.6 | 149.2 | 2.56 | baseline (MASE ≡ 1) |
| `snaive_drift` | 54.6 | 115.9 | 30.54 | 19.58 | 1.098 | 89.1 | 161.6 | 2.57 | **não supera o baseline** |


## Por faixa de volume

Vinte por cento dos hospitais têm até 20 internações por mês. Agregar
tudo numa métrica só deixaria o desempenho nesses invisível atrás do
peso dos grandes.

### ≤5/mês — horizonte de 1 mês

| Modelo | MAE | RMSE | sMAPE % | WAPE % | MASE | Cobertura IC95 % | Largura IC % | z empírico | Veredito |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| `media_movel_3` | 2.2 | 3.2 | 45.76 | 44.22 | 0.862 | 91.8 | 232.6 | 2.30 | supera o baseline |
| `tendencia_linear_publicada` | 2.3 | 3.4 | 51.87 | 46.80 | 0.898 | 89.8 | 278.2 | 2.60 | supera o baseline · *publicado hoje* |
| `tendencia_linear` | 2.3 | 3.4 | 51.93 | 46.82 | 0.899 | 91.4 | 325.6 | 2.47 | supera o baseline |
| `naive` | 2.4 | 3.6 | 50.54 | 49.25 | 0.958 | 92.1 | 296.2 | 2.26 | supera o baseline |
| `tendencia_sazonal` | 2.6 | 3.8 | 61.21 | 53.95 | 1.030 | 90.7 | 190518327615877.8 | 2.41 | **não supera o baseline** |
| `seasonal_naive` | 3.0 | 4.6 | 60.62 | 61.01 | 1.157 | 89.6 | 337.5 | 2.59 | baseline (MASE ≡ 1) |
| `snaive_drift` | 3.0 | 4.5 | 67.90 | 61.49 | 1.176 | 89.4 | 532.4 | 2.60 | **não supera o baseline** |


### 6–20/mês — horizonte de 1 mês

| Modelo | MAE | RMSE | sMAPE % | WAPE % | MASE | Cobertura IC95 % | Largura IC % | z empírico | Veredito |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| `media_movel_3` | 4.9 | 7.9 | 36.37 | 33.83 | 0.787 | 92.6 | 184.7 | 2.23 | supera o baseline |
| `tendencia_linear` | 5.4 | 8.5 | 41.10 | 37.24 | 0.845 | 91.4 | 229.5 | 2.35 | supera o baseline |
| `tendencia_linear_publicada` | 5.4 | 8.5 | 41.07 | 37.29 | 0.845 | 90.1 | 190.2 | 2.49 | supera o baseline · *publicado hoje* |
| `naive` | 5.5 | 9.1 | 41.05 | 38.03 | 0.884 | 92.4 | 229.2 | 2.27 | supera o baseline |
| `tendencia_sazonal` | 6.1 | 9.4 | 47.31 | 42.13 | 0.952 | 91.7 | 154240.9 | 2.31 | supera o baseline |
| `seasonal_naive` | 7.0 | 11.1 | 50.37 | 47.95 | 1.077 | 90.8 | 265.8 | 2.38 | baseline (MASE ≡ 1) |
| `snaive_drift` | 7.1 | 11.0 | 53.85 | 48.63 | 1.093 | 90.7 | 690.5 | 2.39 | **não supera o baseline** |


### 21–100/mês — horizonte de 1 mês

| Modelo | MAE | RMSE | sMAPE % | WAPE % | MASE | Cobertura IC95 % | Largura IC % | z empírico | Veredito |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| `media_movel_3` | 12.0 | 19.6 | 22.32 | 20.76 | 0.746 | 92.7 | 121.5 | 2.25 | supera o baseline |
| `tendencia_linear` | 13.6 | 21.8 | 25.51 | 23.41 | 0.816 | 91.3 | 126.3 | 2.38 | supera o baseline |
| `tendencia_linear_publicada` | 13.6 | 21.8 | 25.51 | 23.43 | 0.816 | 89.9 | 118.3 | 2.52 | supera o baseline · *publicado hoje* |
| `naive` | 13.1 | 21.5 | 24.33 | 22.50 | 0.819 | 92.7 | 144.6 | 2.28 | supera o baseline |
| `tendencia_sazonal` | 15.5 | 24.3 | 29.34 | 26.72 | 0.927 | 91.5 | 148.9 | 2.32 | supera o baseline |
| `seasonal_naive` | 18.0 | 29.4 | 32.69 | 30.99 | 1.063 | 90.5 | 172.1 | 2.44 | baseline (MASE ≡ 1) |
| `snaive_drift` | 18.1 | 28.8 | 33.81 | 31.23 | 1.070 | 90.8 | 175.5 | 2.38 | **não supera o baseline** |


### 101–500/mês — horizonte de 1 mês

| Modelo | MAE | RMSE | sMAPE % | WAPE % | MASE | Cobertura IC95 % | Largura IC % | z empírico | Veredito |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| `media_movel_3` | 36.7 | 59.3 | 15.11 | 14.24 | 0.717 | 92.6 | 82.1 | 2.25 | supera o baseline |
| `naive` | 39.7 | 65.8 | 16.33 | 15.41 | 0.777 | 92.7 | 96.1 | 2.26 | supera o baseline |
| `tendencia_linear` | 41.7 | 65.7 | 17.13 | 16.21 | 0.795 | 91.1 | 82.2 | 2.38 | supera o baseline |
| `tendencia_linear_publicada` | 41.8 | 65.8 | 17.13 | 16.22 | 0.795 | 89.7 | 78.1 | 2.51 | supera o baseline · *publicado hoje* |
| `tendencia_sazonal` | 47.7 | 74.5 | 19.54 | 18.51 | 0.895 | 91.4 | 91.1 | 2.33 | supera o baseline |
| `snaive_drift` | 55.2 | 86.9 | 22.62 | 21.42 | 1.029 | 91.0 | 113.7 | 2.36 | **não supera o baseline** |
| `seasonal_naive` | 54.9 | 87.2 | 22.90 | 21.33 | 1.033 | 90.1 | 117.2 | 2.47 | baseline (MASE ≡ 1) |


### >500/mês — horizonte de 1 mês

| Modelo | MAE | RMSE | sMAPE % | WAPE % | MASE | Cobertura IC95 % | Largura IC % | z empírico | Veredito |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| `media_movel_3` | 105.6 | 164.7 | 11.39 | 10.57 | 0.706 | 93.1 | 62.3 | 2.22 | supera o baseline |
| `tendencia_linear_publicada` | 119.6 | 179.4 | 12.81 | 11.96 | 0.773 | 90.2 | 55.7 | 2.46 | supera o baseline · *publicado hoje* |
| `tendencia_linear` | 119.6 | 179.4 | 12.81 | 11.96 | 0.773 | 91.6 | 58.7 | 2.33 | supera o baseline |
| `naive` | 115.8 | 185.0 | 12.50 | 11.59 | 0.779 | 93.3 | 74.9 | 2.17 | supera o baseline |
| `tendencia_sazonal` | 136.7 | 207.2 | 14.48 | 13.67 | 0.863 | 91.8 | 67.3 | 2.30 | supera o baseline |
| `snaive_drift` | 155.9 | 242.2 | 16.59 | 15.60 | 0.981 | 91.5 | 79.9 | 2.33 | supera o baseline |
| `seasonal_naive` | 154.5 | 240.9 | 16.80 | 15.45 | 0.982 | 90.7 | 88.1 | 2.40 | baseline (MASE ≡ 1) |

