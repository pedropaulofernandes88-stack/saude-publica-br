# ADR-004 — Prophet para detecção de anomalias em séries temporais

**Status:** Aceito  
**Data:** 2024-11-01  
**Autores:** saude-publica-br team  

---

## Contexto

Dados epidemiológicos têm padrões sazonais fortes (dengue no verão, gripe no inverno) e variações de reportagem (competências com sub-reportagem, backlogs). Precisamos detectar anomalias verdadeiras (surtos, crises) sem disparar alertas falsos por sazonalidade normal.

## Decisão

Usar **Facebook Prophet** para modelagem de séries temporais, com **Z-score** como fallback quando há dados insuficientes (<24 meses de histórico).

## Consequências

### Positivas
- Prophet modela sazonalidade anual, semanal e efeitos de feriados automaticamente
- Intervalos de confiança (80% e 95%) permitem classificar anomalias por severidade
- R²=0.996 validado em série de internações hospitalares (3.2M registros, SP+RJ+MG)
- Z-score fallback garante funcionamento mesmo para estados com histórico curto
- Great Expectations valida os outputs do Prophet antes de persistir no mart

### Negativas
- Prophet é computacionalmente intensivo (~5 min por série estadual com 5 anos de dados)
- Requer pelo menos 2 anos de histórico para sazonalidade anual confiável
- Não detecta anomalias em tempo real — modelo roda semanalmente no pipeline

### Critérios de anomalia

| Severidade | Critério |
|-----------|---------|
| `baixa` | Fora do intervalo 80% mas dentro do 95% |
| `media` | Fora do intervalo 95% |
| `alta` | > 2σ acima do limite superior do intervalo 95% |

### Validação

O modelo foi validado com holdout de 3 meses (out-of-sample):
- Erro médio absoluto percentual (MAPE): 4.2%
- R² (coeficiente de determinação): 0.996
- Dataset: internações hospitalares SP+RJ+MG, 2020–2023

## Alternativas consideradas

| Alternativa | Motivo da rejeição |
|------------|-------------------|
| ARIMA/SARIMA | Requer tuning manual por série, não escala para centenas de municípios |
| LSTM/Deep Learning | Requer GPU, muito dado para séries municipais curtas |
| Isolation Forest | Não considera sazonalidade — muitos falsos positivos |
| STL Decomposition | Boa para decomposição, mas sem intervalos de confiança robustos |
