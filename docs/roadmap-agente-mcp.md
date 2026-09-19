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

**Estado em 2026-09-19: 41 ferramentas, e os 35 marts publicados têm alguma.** O
desenho abaixo é o de origem; a forma que sobreviveu foi uma ferramenta por
recorte de fonte, e não um `indicador(municipio, indicador, ano)` genérico — o
genérico obrigaria o modelo a conhecer um vocabulário de nomes de indicador que
nada valida, enquanto a ferramenta nomeada carrega a ressalva na própria
descrição.

- ~~`indicador(municipio, indicador, ano)`~~ → substituído por ferramentas
  nomeadas por fonte e recorte.
- ~~`serie_temporal(municipio, indicador, anos)`~~ → `serie_mensal_obitos`,
  `demanda_mensal_hospital`, `vacinacao_doses`, `dengue_semanal`.
- ~~`ranking(indicador, uf, n)`~~ → o piso de volume e a ordenação ficaram dentro
  de cada ferramenta (`hospitais`, `hsmr_hospital`, `icsap_distancia_dos_pares`).
- **feito** `detectar_anomalias(municipio)` — e o sinal de ICSAP passou a vir com
  a oferta local de leitos ao lado, depois que a §19 refutou a leitura anterior.
- **feito** `qualidade_registro(municipio)`.
- **feito** `comparar_com_pares(municipio)` — com estratos determinísticos por
  tercis, depois que o k-means foi reprovado em teste de estabilidade.
- **feito, e virou a peça central** `metodologia(indicador)` — devolve muito mais
  que a definição: numerador, denominador, unidade, defasagem, o que o indicador
  **não** mede, as ressalvas obrigatórias e as leituras **já testadas e
  refutadas** aqui. Serve `metodologia.json`, com 28 indicadores, e é o que
  permitiu encolher o campo `instructions`, que crescia a cada armadilha nova.

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
