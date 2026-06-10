# ADR-001 — PySUS + Apache Parquet como camada de ingestão

**Status:** Aceito  
**Data:** 2024-09-01  
**Autores:** saude-publica-br team  

---

## Contexto

Os dados do DATASUS são distribuídos em arquivos DBF comprimidos (`.dbc`), fragmentados por estado e competência mensal. Para 27 estados × 5 anos × 12 meses = 1.620 arquivos por sistema (SIA, SIM, SIH). É necessária uma camada de ingestão que:

1. Baixe os arquivos de forma confiável (FTP/HTTP)
2. Converta `.dbc` → formato analítico eficiente
3. Permita processamento incremental (novos meses sem re-processar tudo)
4. Escale para centenas de milhões de registros

## Decisão

Usar **PySUS** para download e leitura dos arquivos `.dbc`, e **Apache Parquet** (via PyArrow) como formato de armazenamento intermediário, particionado por `estado/ano/mes`.

## Consequências

### Positivas
- PySUS abstrai as idiossincrasias do FTP do DATASUS (URLs inconsistentes, formatos legados)
- Parquet suporta leitura colunar — queries analíticas 10–100× mais rápidas que CSV
- Particionamento `estado/ano/mes` permite processamento incremental por hive partition
- Parquet é compatível com DuckDB, Spark, Pandas, Polars, Athena — sem vendor lock-in
- Compressão Snappy reduz tamanho em ~70% vs CSV

### Negativas
- PySUS tem dependência de `dbfread` e lógica customizada por sistema — manutenção necessária
- Parquet requer PyArrow como dependência pesada (~100MB)
- Não há suporte nativo a streaming incremental por linha (Parquet é orientado a arquivos)

### Riscos
- PySUS é um projeto com poucos maintainers — pode ficar desatualizado se o DATASUS mudar URLs
- Mitigação: wrapper próprio em `pipeline/loaders/` que usa PySUS como biblioteca, não como dependência de runtime crítica

## Alternativas consideradas

| Alternativa | Motivo da rejeição |
|------------|-------------------|
| CSV direto | 10× maior, sem tipagem, sem compressão |
| Delta Lake | Overhead operacional desnecessário para esta escala |
| DuckDB como store | DuckDB é in-process, não serve como store distribuído |
| dbfread direto | PySUS já encapsula isso com lógica adicional de normalização |
