# ADR-003 — FastAPI + Redis como camada de API

**Status:** Aceito  
**Data:** 2024-10-01  
**Autores:** saude-publica-br team  

---

## Contexto

A API precisa:
1. Servir dados dos marts dbt com baixa latência
2. Suportar múltiplos clientes simultâneos (dashboard, pesquisadores externos)
3. Evitar sobrecarga no Supabase (60 conexões máx. no Pro)
4. Documentação OpenAPI automática

## Decisão

Usar **FastAPI** com **asyncpg** (pool de conexões assíncrono) e **Redis** para cache com TTL configurável.

## Consequências

### Positivas
- FastAPI gera Swagger UI e ReDoc automaticamente — zero esforço de documentação
- asyncpg é 3–5× mais rápido que psycopg2 em operações assíncronas
- Pool de conexões asyncpg (min: 2, max: 10) mantém Supabase confortável
- Redis com TTL 6h (dados recentes) / 24h (histórico) reduz queries ao Supabase em ~95%
- Pydantic v2 valida respostas com overhead mínimo (<1ms por request)
- `prometheus-fastapi-instrumentator` instrumenta todos os endpoints automaticamente

### Negativas
- Redis é um ponto de falha adicional — API degrada graciosamente (sem cache) se Redis cair
- asyncpg não usa SQLAlchemy ORM — queries são SQL puro com `$1, $2` — mais verboso mas mais controlável
- Cache de invalidação manual necessário após `dbt run` semanal

### Decisões de cache

| Endpoint | TTL | Justificativa |
|---------|-----|---------------|
| `/producao`, `/mortalidade`, `/internacoes` | 6h | Dados mudam semanalmente, mas toleramos 6h de defasagem |
| `/epidemiologia/cid10` | 24h | Dados históricos estáveis |
| `/ranking/{uf}` | 6h | Potencialmente mais consultado |
| `/health` | sem cache | Sempre em tempo real |
| `/info` | 24h | Metadados raramente mudam |

## Alternativas consideradas

| Alternativa | Motivo da rejeição |
|------------|-------------------|
| Django REST Framework | Overhead síncrono, menos adequado para I/O-bound concorrente |
| Flask + SQLAlchemy | Sem suporte nativo a async, sem geração automática de OpenAPI |
| GraphQL (Strawberry) | Complexidade desnecessária para dados tabulares estruturados |
| Memcached | Sem suporte a TTL por chave com wildcards — Redis mais flexível |
