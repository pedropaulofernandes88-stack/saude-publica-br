# ADR-005 — nginx + Prometheus/Grafana como camada de produção

**Status:** Aceito  
**Data:** 2025-01-15  
**Autores:** saude-publica-br team  

---

## Contexto

Em produção, precisamos de:
1. TLS termination e HTTPS
2. Rate limiting para evitar abuso da API pública
3. Observabilidade: métricas de throughput, latência, error rate
4. Dashboards operacionais para monitoramento

## Decisão

Usar **nginx** como reverse proxy (TLS 1.2/1.3, rate limiting), **Prometheus** para coleta de métricas e **Grafana** para visualização, tudo orquestrado via docker-compose.

## Consequências

### Positivas
- nginx lida com TLS fora da aplicação — sem configuração SSL no FastAPI
- Rate limiting (`limit_req_zone`) previne abuso: 10 r/s API, 30 r/s global
- `prometheus-fastapi-instrumentator` instrumenta todos os endpoints sem código adicional
- `nginx-prometheus-exporter` sidecar converte `stub_status` para métricas Prometheus
- Grafana provisioning via YAML: dashboards e datasources carregam automaticamente
- Separação de responsabilidades: api e frontend sem portas expostas ao host

### Configuração de rate limiting nginx

```nginx
# Zona de 10MB = ~160k endereços IP simultâneos
limit_req_zone $binary_remote_addr zone=api:10m rate=10r/s;
limit_req_zone $binary_remote_addr zone=global:10m rate=30r/s;

# Bursts permitem picos sem rejeição imediata
limit_req zone=api burst=20 nodelay;
limit_req zone=global burst=50 nodelay;
```

### Decisão sobre `/metrics`

O endpoint `/metrics` do FastAPI é restrito por IP no nginx (`allow 127.0.0.1; allow <prometheus_container_ip>; deny all;`), nunca exposto publicamente, evitando vazamento de informações internas.

### Negativas
- Adiciona 2 containers ao docker-compose (nginx-exporter, prometheus) além do Grafana
- Configuração de nginx.conf tem curva de aprendizado
- Prometheus retém 15 dias de dados localmente — sem alerting externo nesta fase (Fase 10)

## Alternativas consideradas

| Alternativa | Motivo da rejeição |
|------------|-------------------|
| Traefik | Curva de aprendizado maior, menos docs em PT-BR |
| Caddy | Excelente para TLS automático, mas menos flexível para rate limiting avançado |
| Datadog / New Relic | Custo ($$$) incompatível com projeto open-source |
| CloudWatch | Vendor lock-in AWS |
| OpenTelemetry | Overhead e complexidade desnecessários nesta fase |
