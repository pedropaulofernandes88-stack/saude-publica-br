## O que muda, e por quê

<!-- O problema que existia antes. Se a mudança altera um número publicado,
     diga isso na primeira linha. -->

## Como verificar

<!-- O comando ou o caminho que outra pessoa segue para confirmar. Resultado
     observado, não "testei localmente". -->

- [ ] `npm test` e `npx tsc --noEmit` em `site/` (se tocou o site)
- [ ] `pytest tests/` (se tocou pipeline, validação ou MCP)
- [ ] Conferido em 375px e em desktop (se mudou layout)

## Número publicado

- [ ] Esta mudança **não** altera nenhum indicador já publicado
- [ ] Altera — e o valor antigo, o novo e a causa estão descritos acima

## Duplicação

Este repositório já quebrou várias vezes pela mesma regra viver em dois lugares
que concordam até deixarem de concordar — a versão do `mcp`, a regra de
completude, a licença.

- [ ] A regra que eu mudei tem **um** lugar só, ou listei aqui todos os lugares
      que precisaram acompanhar
