# Validação do forecast de demanda hospitalar

> Gerado por `scripts/validate_forecast.py`. Não editar à mão: qualquer
> alteração é sobrescrita na próxima execução.

| | |
|---|---|
| Gerado em | 2026-08-22 19:28 UTC |
| Commit | `3f0d313` |
| Fonte | `mart_demanda_mensal_hospital` |
| Período | 2022-01 a 2024-12 |
| Hospitais na fonte | 5,083 |
| Hospitais avaliados | 4,445 |
| Treino mínimo | 24 meses |
| Origens por hospital | mediana 11.4 |
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
| `media_movel_3` | 35.4 | 75.7 | 20.16 | 12.96 | 0.762 | 92.1 | 103.8 | 2.30 | supera o baseline |
| `tendencia_linear_publicada` | 39.2 | 81.8 | 22.32 | 14.35 | 0.810 | 89.0 | 96.7 | 2.60 | supera o baseline · *publicado hoje* |
| `tendencia_linear` | 39.2 | 81.8 | 22.33 | 14.35 | 0.810 | 90.8 | 103.9 | 2.42 | supera o baseline |
| `naive` | 38.0 | 83.5 | 21.80 | 13.91 | 0.824 | 92.5 | 125.7 | 2.28 | supera o baseline |
| `tendencia_sazonal` | 46.6 | 99.3 | 26.57 | 17.03 | 0.937 | 91.0 | 129.7 | 2.38 | supera o baseline |
| `snaive_drift` | 51.7 | 114.4 | 29.46 | 18.90 | 1.022 | 90.6 | 163.1 | 2.40 | **não supera o baseline** |
| `seasonal_naive` | 53.1 | 116.7 | 28.96 | 19.42 | 1.038 | 89.4 | 146.1 | 2.52 | baseline (MASE ≡ 1) |


## Horizonte de 2 meses

| Modelo | MAE | RMSE | sMAPE % | WAPE % | MASE | Cobertura IC95 % | Largura IC % | z empírico | Veredito |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| `media_movel_3` | 39.2 | 82.3 | 21.89 | 14.22 | 0.846 | 96.0 | 140.0 | 1.83 | supera o baseline |
| `tendencia_linear_publicada` | 41.8 | 86.5 | 23.59 | 15.16 | 0.867 | 86.8 | 100.7 | 2.85 | supera o baseline · *publicado hoje* |
| `tendencia_linear` | 41.8 | 86.5 | 23.58 | 15.16 | 0.867 | 88.9 | 108.7 | 2.64 | supera o baseline |
| `naive` | 42.5 | 90.3 | 24.03 | 15.44 | 0.924 | 95.9 | 167.3 | 1.83 | supera o baseline |
| `tendencia_sazonal` | 48.8 | 103.8 | 27.37 | 17.68 | 0.982 | 89.4 | 185816.3 | 2.54 | supera o baseline |
| `seasonal_naive` | 53.3 | 117.7 | 28.80 | 19.36 | 1.056 | 88.7 | 144.0 | 2.60 | baseline (MASE ≡ 1) |
| `snaive_drift` | 53.4 | 118.6 | 30.01 | 19.37 | 1.061 | 89.2 | 169.5 | 2.55 | **não supera o baseline** |


## Horizonte de 3 meses

| Modelo | MAE | RMSE | sMAPE % | WAPE % | MASE | Cobertura IC95 % | Largura IC % | z empírico | Veredito |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| `media_movel_3` | 41.8 | 86.4 | 23.18 | 15.03 | 0.917 | 97.1 | 165.7 | 1.61 | supera o baseline |
| `tendencia_linear` | 43.9 | 90.3 | 24.68 | 15.79 | 0.922 | 87.5 | 109.2 | 2.80 | supera o baseline |
| `tendencia_linear_publicada` | 43.9 | 90.3 | 24.69 | 15.79 | 0.922 | 85.0 | 100.5 | 3.05 | supera o baseline · *publicado hoje* |
| `naive` | 46.1 | 95.4 | 25.65 | 16.54 | 1.013 | 97.1 | 198.9 | 1.63 | **não supera o baseline** |
| `tendencia_sazonal` | 50.8 | 107.9 | 28.09 | 18.25 | 1.032 | 88.0 | 41414.8 | 2.68 | **não supera o baseline** |
| `seasonal_naive` | 53.7 | 118.0 | 28.63 | 19.30 | 1.081 | 88.3 | 142.0 | 2.68 | baseline (MASE ≡ 1) |
| `snaive_drift` | 55.1 | 122.2 | 30.53 | 19.78 | 1.105 | 87.9 | 170.1 | 2.68 | **não supera o baseline** |


## Por faixa de volume

Vinte por cento dos hospitais têm até 20 internações por mês. Agregar
tudo numa métrica só deixaria o desempenho nesses invisível atrás do
peso dos grandes.

### ≤5/mês — horizonte de 1 mês

| Modelo | MAE | RMSE | sMAPE % | WAPE % | MASE | Cobertura IC95 % | Largura IC % | z empírico | Veredito |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| `tendencia_linear` | 2.1 | 3.1 | 53.64 | 48.11 | 0.846 | 92.0 | 270.7 | 2.40 | supera o baseline |
| `media_movel_3` | 2.1 | 3.0 | 47.31 | 47.64 | 0.846 | 91.9 | 235.8 | 2.18 | supera o baseline |
| `tendencia_linear_publicada` | 2.1 | 3.1 | 53.79 | 48.15 | 0.846 | 90.3 | 280.5 | 2.57 | supera o baseline · *publicado hoje* |
| `naive` | 2.4 | 3.4 | 52.09 | 53.45 | 0.950 | 91.7 | 300.7 | 2.21 | supera o baseline |
| `tendencia_sazonal` | 2.5 | 3.5 | 65.95 | 56.27 | 1.000 | 90.8 | 327.7 | 2.41 | supera o baseline |
| `seasonal_naive` | 2.7 | 3.9 | 60.54 | 60.00 | 1.049 | 89.5 | 354.3 | 2.47 | baseline (MASE ≡ 1) |
| `snaive_drift` | 2.8 | 3.9 | 73.21 | 62.79 | 1.100 | 88.8 | 758.4 | 2.47 | **não supera o baseline** |


### 6–20/mês — horizonte de 1 mês

| Modelo | MAE | RMSE | sMAPE % | WAPE % | MASE | Cobertura IC95 % | Largura IC % | z empírico | Veredito |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| `media_movel_3` | 4.9 | 7.7 | 36.37 | 34.27 | 0.810 | 91.5 | 180.3 | 2.33 | supera o baseline |
| `tendencia_linear_publicada` | 5.3 | 8.1 | 40.37 | 36.90 | 0.843 | 89.0 | 180.0 | 2.61 | supera o baseline · *publicado hoje* |
| `tendencia_linear` | 5.3 | 8.1 | 40.41 | 36.89 | 0.844 | 90.7 | 202.4 | 2.45 | supera o baseline |
| `naive` | 5.4 | 8.2 | 40.83 | 37.87 | 0.906 | 92.2 | 223.1 | 2.32 | supera o baseline |
| `tendencia_sazonal` | 6.2 | 9.3 | 49.26 | 43.13 | 0.972 | 91.2 | 252.3 | 2.37 | supera o baseline |
| `seasonal_naive` | 6.7 | 10.8 | 49.31 | 46.77 | 1.044 | 90.5 | 257.2 | 2.45 | baseline (MASE ≡ 1) |
| `snaive_drift` | 6.8 | 10.4 | 54.08 | 47.20 | 1.056 | 90.4 | 367.3 | 2.41 | **não supera o baseline** |


### 21–100/mês — horizonte de 1 mês

| Modelo | MAE | RMSE | sMAPE % | WAPE % | MASE | Cobertura IC95 % | Largura IC % | z empírico | Veredito |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| `media_movel_3` | 12.6 | 21.1 | 22.92 | 21.49 | 0.793 | 91.5 | 117.8 | 2.37 | supera o baseline |
| `tendencia_linear_publicada` | 13.7 | 22.0 | 25.57 | 23.46 | 0.838 | 88.4 | 107.6 | 2.68 | supera o baseline · *publicado hoje* |
| `tendencia_linear` | 13.7 | 22.0 | 25.58 | 23.47 | 0.838 | 90.2 | 115.3 | 2.48 | supera o baseline |
| `naive` | 13.4 | 23.3 | 24.51 | 22.91 | 0.855 | 91.9 | 143.3 | 2.37 | supera o baseline |
| `tendencia_sazonal` | 16.0 | 25.1 | 30.11 | 27.35 | 0.966 | 90.9 | 149.8 | 2.40 | supera o baseline |
| `snaive_drift` | 17.8 | 28.1 | 33.45 | 30.42 | 1.052 | 90.5 | 170.4 | 2.43 | **não supera o baseline** |
| `seasonal_naive` | 18.1 | 29.6 | 32.61 | 31.00 | 1.058 | 89.7 | 167.2 | 2.52 | baseline (MASE ≡ 1) |


### 101–500/mês — horizonte de 1 mês

| Modelo | MAE | RMSE | sMAPE % | WAPE % | MASE | Cobertura IC95 % | Largura IC % | z empírico | Veredito |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| `media_movel_3` | 37.8 | 61.7 | 15.24 | 14.46 | 0.733 | 92.3 | 79.8 | 2.27 | supera o baseline |
| `naive` | 40.2 | 67.6 | 16.21 | 15.37 | 0.783 | 92.6 | 95.0 | 2.25 | supera o baseline |
| `tendencia_linear_publicada` | 41.8 | 66.6 | 16.62 | 15.99 | 0.786 | 89.1 | 71.1 | 2.57 | supera o baseline · *publicado hoje* |
| `tendencia_linear` | 41.8 | 66.6 | 16.62 | 15.98 | 0.786 | 90.9 | 75.9 | 2.39 | supera o baseline |
| `tendencia_sazonal` | 49.9 | 82.7 | 19.74 | 19.07 | 0.912 | 91.0 | 93.1 | 2.35 | supera o baseline |
| `snaive_drift` | 55.7 | 98.0 | 21.91 | 21.28 | 0.999 | 90.8 | 105.0 | 2.38 | supera o baseline |
| `seasonal_naive` | 57.3 | 99.4 | 23.10 | 21.92 | 1.031 | 88.6 | 111.1 | 2.56 | baseline (MASE ≡ 1) |


### >500/mês — horizonte de 1 mês

| Modelo | MAE | RMSE | sMAPE % | WAPE % | MASE | Cobertura IC95 % | Largura IC % | z empírico | Veredito |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| `media_movel_3` | 107.0 | 165.7 | 11.22 | 10.60 | 0.725 | 93.3 | 60.9 | 2.19 | supera o baseline |
| `tendencia_linear_publicada` | 119.3 | 179.3 | 12.42 | 11.82 | 0.780 | 90.0 | 53.7 | 2.49 | supera o baseline · *publicado hoje* |
| `tendencia_linear` | 119.3 | 179.3 | 12.43 | 11.82 | 0.780 | 91.7 | 57.5 | 2.34 | supera o baseline |
| `naive` | 116.0 | 183.2 | 12.19 | 11.49 | 0.783 | 93.9 | 71.0 | 2.12 | supera o baseline |
| `tendencia_sazonal` | 141.5 | 216.1 | 14.57 | 14.02 | 0.901 | 91.3 | 68.1 | 2.39 | supera o baseline |
| `snaive_drift` | 156.2 | 246.8 | 16.19 | 15.47 | 0.978 | 91.0 | 75.6 | 2.40 | supera o baseline |
| `seasonal_naive` | 160.8 | 252.1 | 16.87 | 15.93 | 1.008 | 89.8 | 80.5 | 2.47 | baseline (MASE ≡ 1) |

