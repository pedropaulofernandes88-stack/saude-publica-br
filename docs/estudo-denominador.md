# Estudo — Reconciliação do denominador populacional do Brasil (2015–2024)

**Problema (que a nossa análise de sensibilidade expôs).** A população anual por
idade do Brasil em 2015–2024 é internamente inconsistente, e isso enviesa **toda
taxa padronizada por idade** do período — em qualquer estudo, não só neste projeto:

- A **projeção IBGE 2018** superestima a população (o Censo 2022 a revisou para
  baixo em ~8–11 milhões), com viés crescente ao longo do tempo.
- A série de **estimativas pós-Censo** corrige o nível, mas introduz uma
  **descontinuidade em 2022** (≈211 mi em 2020 → 203 mi no Censo), que distorce os
  esperados/taxas ao redor do rebasing.

**Contribuição pretendida.** Produzir e publicar, aberta e reproduzível, uma
**série populacional por idade × UF × ano (2015–2024) reconciliada** — sem o
overcount da projeção e sem o degrau do Censo — e demonstrar seu efeito sobre
indicadores padronizados. É um insumo que o campo inteiro precisa.

## Métodos candidatos
1. **Reescalonamento simples** (forma etária da projeção × total pós-Censo).
   Já testado; herda o degrau de 2022. *Insuficiente.*
2. **Interpolação intercensitária ancorada (recomendado).** Usar as estruturas
   etárias observadas do **Censo 2010 e do Censo 2022** como âncoras; interpolar a
   estrutura por faixa entre os censos (log-linear ou por *cohort shift*); calibrar
   cada ano ao **total das estimativas anuais** (já pós-Censo). Resultado: série
   suave que capta o envelhecimento real, sem overcount e sem degrau.
3. **Método componente-coorte / reconstrução demográfica.** Reconstrói a população
   a partir de nascimentos (SINASC), óbitos (SIM) e migração. Mais rigoroso e mais
   complexo; candidato a versão 2.

## Plano (método 2)
1. Obter estrutura etária por UF do **Censo 2010** (SIDRA) e **Censo 2022** (já temos).
2. Interpolar a proporção de cada faixa etária entre 2010 e 2022 (e extrapolar com
   cautela até 2024), por UF.
3. Multiplicar as proporções interpoladas pelo **total populacional anual** de cada
   UF (estimativas IBGE, pós-Censo) → população por idade/UF/ano reconciliada.
4. Publicar `pop_idade_uf_ano_reconciliada.parquet` + método documentado.

## Validação
- **Consistência:** soma das faixas = total da estimativa anual (por construção).
- **Ancoragem:** estrutura reconstruída em 2022 ≈ estrutura observada do Censo 2022.
- **Ausência de degrau:** verificar suavidade da série de % de idosos 2015–2024.
- **Teste de convergência (o mais importante):** recomputar o **excesso de
  mortalidade** com a série reconciliada. Hipótese: o excesso padronizado passa a
  convergir para o método de tendência (~643 mil no biênio pandêmico) e deixa de
  ficar negativo em 2023–2024. Se convergir, a reconciliação resolveu o problema do
  denominador; se não, aprendemos algo novo. Ambos são publicáveis.

## Escopo honesto
- **Nível UF: factível** com dados existentes (censos + estimativas).
- **Nível município anual por idade: não existe** (só há por idade nos anos
  censitários). Extensão exige métodos de **pequena área** (estrutura municipal do
  Censo 2022 fixa como aproximação declarada, ou modelagem bayesiana espacial) — é a
  versão 2 e uma limitação a declarar.

## Impacto e entregáveis
- **Interno:** todas as taxas padronizadas do saudeemdado passam a usar a série
  reconciliada (nível UF), com nota metodológica.
- **Externo:** dataset aberto + DOI + **nota de métodos (preprint)** — "Uma série
  populacional por idade reconciliada para o Brasil pós-Censo 2022 e seu efeito
  sobre indicadores padronizados". Contribuição citável ao campo.
- Conecta-se ao artigo de sensibilidade do excesso já publicado como a *solução*
  do problema que aquele artigo *diagnosticou*.
