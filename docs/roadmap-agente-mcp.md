# Roadmap — Agente epidemiológico público (MCP)

**Visão:** "Pergunte à saúde do Brasil." Um agente de IA que *raciocina* sobre os
dados do saudeemdado — consulta, detecta anomalias, pondera qualidade do dado e
narra para um gestor — em vez de um dashboard que o usuário precisa saber operar.

**Por que é disruptivo:** não existe dado de saúde brasileiro nativo para agentes
de IA. O movimento é a fronteira de 2025–2026 (Data Commons MCP do Google; ARIES,
vigilância epidemiológica multi-agente; MCPmed em bioinformática). Seríamos o
*primeiro data commons epidemiológico do SUS consultável por agentes*.

## O que já existe (a base)
- Marts agregados (mortalidade, SIH, dengue, natalidade, ICSAP, fluxo, agravo,
  hospital, excesso, **qualidade do registro**).
- API REST pública (PostgREST) — o agente consome sem credencial.
- Servidor MCP inicial. Pipeline reprodutível e DOI.

## Arquitetura
```
Usuário → Claude (raciocínio) → Ferramentas MCP → API PostgREST → marts
                                      ↑
                         camada de confiabilidade (🥉)
```
- **Claude** decide quais indicadores olhar, interpreta a estatística e escreve.
- **Ferramentas MCP** (tools) encapsulam consultas seguras à API. O modelo *nunca*
  escreve SQL livre; chama tools tipadas.
- **Camada de confiabilidade:** antes de responder um número, o agente consulta
  `mart_qualidade_registro_municipio` e sinaliza se o município tem registro Ruim.

## Ferramentas (tools) a expor
- `indicador(municipio, indicador, ano)` → valor + fonte + IC (quando houver).
- `serie_temporal(municipio, indicador, anos)`.
- `ranking(indicador, uf, n)` → top/bottom com piso de volume.
- `detectar_anomalias(municipio)` → ICSAP outlier (Wilson), canal endêmico rompido
  (dengue), excesso de mortalidade, red flags de qualidade.
- `qualidade_registro(municipio)` → classe Bom/Regular/Ruim + %.
- `comparar_pares(municipio, indicador)`.
- `metodologia(indicador)` → devolve a definição documentada (evita o modelo inventar método).

## Anti-alucinação — o requisito inegociável (número de saúde)
1. **Grounding obrigatório:** todo número na resposta vem de uma tool call. Proibido
   "estimar de cabeça". Se não há tool, o agente diz que não sabe.
2. **Citação do valor exato + fonte:** cada número acompanha o endpoint/mart de onde
   veio e o ano. Auditável.
3. **Saída estruturada:** valores retornam em campos (JSON), não embutidos em prosa
   gerada — reduz a chance de o texto "arredondar errado".
4. **Guardrails de escopo:** recusa inferência causal, extrapolação além do dado, e
   qualquer recomendação clínica individual. Sempre marca dado ecológico/retrospectivo.
5. **Sinalização de incerteza:** IC quando aplicável; aviso automático de baixa
   confiabilidade via 🥉; aviso de dado preliminar (ano corrente).
6. **Suíte de avaliação (regression):** um conjunto de ~50 perguntas com respostas
   conhecidas (ex.: "TMI de RR em 2022" = 18,8‰). Roda a cada mudança de prompt/tool.
   Só sobe ao público com ≥ meta de acurácia factual.

## Fases de entrega
- **Fase 0 — endurecer o MCP.** Tools tipadas + tool de *descoberta* ("que dados
  você tem sobre o município X?") + tool de metodologia. Deploy do MCP público
  (qualquer cliente compatível, ex.: Claude Desktop).
- **Fase 1 — Q&A ancorado.** Agente read-only responde perguntas em linguagem
  natural com grounding + citação + confiabilidade. Suíte de avaliação verde.
- **Fase 2 — briefing + anomalias.** Dado um município, gera um resumo semanal de
  1 página priorizado (o "copiloto do gestor").
- **Fase 3 — proativo.** Alertas (e-mail/WhatsApp) quando um sinal cruza limiar.

## Riscos e trade-offs (honestidade de engenharia)
- **Custo:** deixa de ser custo-zero — precisa de chave de LLM e orçamento de tokens.
  Mitigação: cache de respostas comuns; roteamento (perguntas simples → tool direta
  sem LLM); orçamento mensal com corte.
- **Escala do free-tier:** um agente popular multiplica o egress do Supabase.
  Mitigação: servir do `sdata` estático quando possível; CDN.
- **Uso indevido:** decisão clínica/política sem supervisão. Mitigação: guardrails +
  nota de uso ético já existente.
- **Alucinação residual:** nenhuma mitigação é 100%. Por isso a suíte de avaliação e
  a citação auditável de cada número são condição de publicação.

## Métrica de sucesso
Acurácia factual na suíte de avaliação; % de respostas com fonte citada (meta 100%);
e o teste de fogo: um gestor sem epidemiologista consegue, em 1 pergunta, saber o que
mudou na saúde do seu município e o que fazer.
