# ADR-002 — dbt-core + Supabase/PostgreSQL como camada de transformação e armazenamento

**Status:** Aceito  
**Data:** 2024-09-15  
**Autores:** saude-publica-br team  

---

## Contexto

Após a ingestão em Parquet, precisamos de:
1. Transformações reproduzíveis e versionadas (staging → marts)
2. Um banco de dados que sirva como backend da API REST
3. Testes de qualidade de dados declarativos
4. Documentação automática dos modelos

## Decisão

Usar **dbt-core** com o adapter **dbt-postgres** para transformações, e **Supabase** (PostgreSQL 15 gerenciado) como banco de dados de produção.

## Consequências

### Positivas
- dbt garante reprodutibilidade: qualquer mart pode ser recriado do zero com `dbt run`
- Testes declarativos (`not_null`, `unique`, `relationships`) detectam erros de dados automaticamente
- `dbt docs generate` cria documentação de linhagem automática
- Supabase oferece PostgreSQL 15 + PostgREST + Auth + Storage — sem operação de infra
- Supabase Pro (~$25/mês) suporta ~480M registros com índices adequados
- Migrações versionadas (V001–V010) garantem evolução do schema auditável

### Negativas
- dbt não é um orquestrador — precisa do Prefect para scheduling
- Supabase tem limitações de conexões no plano Pro (60 conexões diretas) — mitigado pelo pool asyncpg da API
- Tempo de `dbt run` completo: ~15-30 min para 3 estados (escala linearmente)

### Riscos
- Lock-in no Supabase: mitigado pelo uso de PostgreSQL padrão — migração para outro provider é possível com dump/restore
- Schema migrations: todas feitas via arquivo SQL versionado (`migrations/V00X__*.sql`), nunca via dbt diretamente

## Alternativas consideradas

| Alternativa | Motivo da rejeição |
|------------|-------------------|
| BigQuery | Custo por query imprevisível em cargas analíticas pesadas |
| Redshift | Muito caro para projeto open-source |
| MotherDuck (DuckDB cloud) | Sem suporte nativo a conexões concorrentes de API REST |
| SQLAlchemy Core (sem dbt) | Sem linhagem, sem testes declarativos, sem documentação automática |
