# Materiais de apresentação

Geradores dos documentos que saem do projeto para fora dele — apresentação,
documentação e resumo. **São código, não anexo de e-mail:** o `.pptx` e o `.pdf`
não se editam à mão, se regeram daqui.

## Por que existem três documentos e não um

Eles têm leitores e situações de leitura diferentes, e misturá-los piora os três.

| gerador | saída | para quê |
|---|---|---|
| `gerar_apresentacao.js` | `Saude-em-Dado-apresentacao.pptx` | **narrado**, 16 slides, ~20 min, com notas de orador. Tem arco: monta a hipótese, mostra o dado que a derruba, depois a implicação. Depende de alguém na sala. |
| `gerar_resumo.js` | `Saude-em-Dado-resumo.pptx` | **entregue**, 7 páginas. Lido sozinho depois, possivelmente por quem não esteve na conversa. Cada página se sustenta isolada — nada de "como vimos". |
| `gerar_documentacao.js` | `Saude-em-Dado-documentacao.docx` | **referência**, ~22 páginas, tudo por extenso e sem abreviatura. Explica o que foi feito e por quê, com sumário navegável. |

`apresentacao-artefato.html` é a mesma apresentação como página web navegável por
teclado, publicada como artefato para enviar por link. `briefing-nakaya.html` é a
folha de consulta rápida, para celular, de uma conversa específica.

## Como regerar

```
cd materiais
npm install                      # pptxgenjs e docx
node gerar_apresentacao.js
node gerar_resumo.js
node gerar_documentacao.js
```

As saídas vão para `saida/`. O `.pptx` vira `.pdf` pelo PowerPoint; o `.docx`
vira `.pdf` por um caminho diferente, explicado abaixo.

### Do `.docx` para o PDF

```
python docx_para_html.py         # lê saida/*.docx, escreve saida/documentacao.html
chrome --headless --disable-gpu --no-pdf-header-footer \
       --print-to-pdf=saida/Saude-em-Dado-documentacao.pdf saida/documentacao.html
```

**Por que esse desvio.** A exportação de PDF do Word por COM **trava** em
contexto não interativo — a do PowerPoint não. Descoberto travando. O conversor
não é genérico: cobre exatamente o que este documento usa (três níveis de
título, negrito, listas, tabelas, a nota lateral e a quebra de página), e gera um
sumário de verdade porque o índice do Word é campo e não renderiza em HTML.

### Exportando o `.pptx`

Ao automatizar o PowerPoint, **matar só o processo que a própria execução criou**.
Um `Stop-Process -Force` em todos os `POWERPNT` já derrubou um processo do
usuário que rodava havia dias. Guardar os PIDs antes e filtrar depois.

## As saídas estão versionadas de propósito

`saida/` entra no git, ainda que seja regenerável. O motivo é que estes arquivos
**foram entregues a terceiros**: quando alguém disser "o PDF que você me mandou",
os bytes exatos precisam existir. Regerar meses depois pode produzir arquivo
diferente — versão do PowerPoint, fontes disponíveis, dado atualizado.

É a mesma razão de as publicações de dado guardarem cópia imutável por data.

Uma ressalva: `.pptx` e `.docx` são ZIP e carregam data de modificação, então
**os bytes mudam a cada build ainda que o conteúdo não mude**. O arquivo com
valor de arquivo aqui é o **PDF** — é ele que foi enviado. Os `.pptx` no
repositório servem para editar, não como prova do que foi entregue.

## Cuidado com o número escrito em prosa

Estes documentos repetem números que vivem no site e no banco — contagem de
tabelas, de testes, coeficientes. Eles **envelhecem em silêncio**: já aconteceu
de o deck dizer nove fontes depois de a décima entrar, e de a documentação trazer
coeficiente de um dado que fora corrigido.

Duas armadilhas concretas ao atualizar:

1. **A documentação escreve os números por extenso** ("dezessete vírgula oito").
   Busca numérica não os encontra. Procurar as duas formas.
2. Parte dos números tem guarda automática em `tests/test_numeros_do_site.py`,
   mas ela cobre o **site**, não estes documentos. Aqui a conferência é manual.

Antes de entregar qualquer versão, conferir contra `data/publicacoes/atual.json`
e `data/marts/achados.json`.
