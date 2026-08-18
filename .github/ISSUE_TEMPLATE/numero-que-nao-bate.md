---
name: Um número não bate
about: Um indicador do site, da API ou do MCP diverge de outra fonte
title: ''
labels: dado
---

## O número

Onde você viu, e qual valor apareceu.

- Página, endpoint ou ferramenta MCP:
- Filtros aplicados (UF, ano, capítulo CID, sexo, faixa etária):
- Valor mostrado:

## O número esperado

De onde vem a comparação — TabNet, painel do Ministério, artigo publicado, outro
cálculo seu.

- Fonte:
- Valor esperado:

## Antes de abrir

Três causas respondem pela maioria das divergências. Vale conferir:

- [ ] **Subtotais somados junto com as partes.** Linhas com `capitulo_cid`,
      `sexo` ou `faixa_etaria` iguais a `TOTAL` já são a soma. Ver
      [Valores sentinela](https://saudeemdado.com/dados/#sentinelas).
- [ ] **Códigos agregados contados como município.** `110000` é "Rondônia sem
      município identificado", não uma cidade.
- [ ] **Anos preliminares.** A vigência de cada base está em
      [Dados & API](https://saudeemdado.com/dados/) — SIM, SIH, SINAN e SINASC
      têm cobertura e atualidade diferentes entre si.

Se já checou os três e a diferença permanece, é exatamente o tipo de relato que
interessa. Abra sem receio.
