# Manuscrito — mortes por doenças imunopreveníveis

Rascunho de artigo sobre a cobertura do instrumento oficial brasileiro de
evitabilidade por imunoprevenção, escrito a partir do levantamento executado em
2026-09-03.

**O achado, em uma frase:** a Lista Brasileira de Causas de Mortes Evitáveis
identifica 4,03 óbitos por 10 mil no Brasil e não se move há uma década — não
porque a carga seja pequena, mas porque o instrumento para aos 74 anos,
descreve o calendário vacinal anterior a 2011 e é dominado internamente por
tuberculose em idade sem proteção estabelecida pela BCG.

| arquivo | o que é |
|---|---|
| `manuscrito.md` | **a fonte.** É aqui que se edita |
| `gerar_tabelas.py` | produz `tabelas/*.csv` reagregando o microdado do SIM |
| `empacotar.py` | produz `dados-do-artigo.zip` — material suplementar |
| `tabelas/` | as dezesseis tabelas do artigo, em CSV |
| `manuscrito.html`, `manuscrito.pdf` | derivados — **não se editam à mão** |
| `dados-do-artigo.zip` | derivado — manuscrito, tabelas, análises e código |

```
.venv311/Scripts/python artigo-imunopreveniveis/gerar_tabelas.py
.venv311/Scripts/python artigo/sincronizar_tabelas.py --dir artigo-imunopreveniveis
.venv311/Scripts/python artigo/renderizar.py artigo-imunopreveniveis
.venv311/Scripts/python artigo-imunopreveniveis/empacotar.py
```

`sincronizar_tabelas.py` e `renderizar.py` são compartilhados pelos manuscritos
do repositório e recebem a pasta como argumento. Os outros dois são deste.

## Nenhum número do texto é digitado

Cada valor citado na prosa existe em `tabelas/`, e cada tabela sai de
`gerar_tabelas.py`. A regra tem regressão: `tests/test_manuscrito.py` confere
que as quinze tabelas embutidas batem com os seus CSVs.

O mesmo arquivo tem um segundo teste,
`test_todo_numero_da_prosa_existe_em_alguma_tabela`, que varre a prosa atrás de
decimal com vírgula e de inteiro com separador de milhar, decompõe cada célula
das tabelas nos números que contém e compara por **igualdade** — não por
substring, que aprovaria `6,9` por causa de um `16,9` alheio. Ele é
parametrizado por `COM_PROCEDENCIA` e cobre esta pasta.

Este manuscrito o satisfaz com uma única exceção, medida e deliberada:

- `0,30` — o limiar de nulidade declarado antes da análise (§2.6). É parâmetro
  de decisão, não medida; cravá-lo numa tabela seria fingir que foi observado.
  Está em `DECIMAIS_SEM_TABELA["artigo-imunopreveniveis"]`, com o motivo.

A guarda foi vista reprovando: trocar `4,03` por `4,07` no texto reprova
nomeando a pasta e o valor. Foi assim, aliás, que se descobriu que citação
múltipla no estilo `[4,5]` casa com o padrão de decimal — daí o espaço em
`[4, 5]` ao longo do texto.

`tabela_14_influenza_doses_uf.csv` é citada em prosa e **não** é embutida: são
53 linhas de dado por unidade da federação, que a página não comporta e que
nenhum número do texto usa diretamente. O sincronizador reporta essa exceção a
cada execução, para que ela não passe a existir em silêncio.

## Os produtores da análise

O manuscrito não calcula nada. Ele descreve o que estes arquivos produzem:

- `scripts/_sim_obitos.py` — a definição de óbito e a união das fontes do SIM,
  compartilhada com todos os pipelines de mortalidade;
- `scripts/analise_mortes_imunopreveniveis.py` — as listas de CID-10
  transcritas das notas técnicas do TabNet, a derivação em quatro caracteres,
  as quatro guardas e as tabelas de análise em `data/analises/`;
- `artigo-imunopreveniveis/gerar_tabelas.py` — importa as listas do anterior e
  formata as dezesseis tabelas. **Não define nenhuma lista própria**: se
  aparecer um código de CID aqui, são duas listas que vão divergir sem avisar.

## O grão é de quatro caracteres, e isso é o ponto

O resto do projeto trunca a causa básica em três caracteres. Aqui não dá:
`G00.0`, `P35.0` e `P35.3` são nomeados pela própria lista oficial, `A40.3` é a
septicemia pneumocócica, e **`B34.2` é como o SIM brasileiro codifica
COVID-19** — truncada, a pandemia inteira vira "infecção viral não
especificada". Metade da pergunta some no truncamento.

## O que este artigo deliberadamente não afirma

Ele conta óbitos por doenças com vacina disponível. Isso **não** é contar
mortes evitáveis, e a diferença está declarada na Introdução, nos Métodos e na
§4.4: faltam a eficácia vacinal e a situação vacinal de quem morreu, que o SIM
não registra. Todo total é teto.

Por isso o herpes zoster aparece nas tabelas marcado como fora do PNI e sai dos
subtotais, e por isso câncer de colo do útero, câncer de fígado e hepatite B
crônica ficam num grupo de latência longa que nunca é somado.

## Autoria

O manuscrito traz **coautoria a definir** na folha de rosto, de propósito. É
rascunho de trabalho, não submissão.

## As referências foram conferidas na fonte, não citadas de memória

Os três artigos que propõem e revisam a Lista Brasileira foram baixados do
SciELO e lidos antes de virarem referência — volume, número, páginas e lista de
autores saíram do PDF. Foi o que permitiu citar, na §3.4, a justificativa que os
próprios autores dão para manter A17 e A19 no subgrupo de imunoprevenção: a
vacina BCG. O argumento do artigo passou a incidir sobre o critério declarado
por quem escreveu a lista, e não sobre uma suposição a respeito dele.

O `WebFetch` não alcança esses PDFs — ele promove a URL para HTTPS e
`scielo.iec.gov.br` só fala HTTP, devolvendo `ECONNREFUSED`, que se lê como
"fora do ar" e não é. `curl` na porta 80 baixa em segundos.
