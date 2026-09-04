# Manuscrito

Rascunho de artigo sobre a estrutura do perfil municipal de causas de morte,
escrito a partir de um desenho de análise proposto em 2026-09-01.

| arquivo | o que é |
|---|---|
| `manuscrito.md` | **a fonte.** É aqui que se edita |
| `gerar_tabelas.py` | produz `tabelas/*.csv` a partir dos marts publicados |
| `renderizar.py` | produz `manuscrito.html` e `manuscrito.pdf` a partir do `.md` |
| `tabelas/` | as tabelas do artigo, em CSV |
| `manuscrito.html`, `manuscrito.pdf` | derivados — **não se editam à mão** |

```
.venv311/Scripts/python artigo/gerar_tabelas.py
.venv311/Scripts/python artigo/sincronizar_tabelas.py
.venv311/Scripts/python artigo/renderizar.py
```

`sincronizar_tabelas.py` e `renderizar.py` servem aos **dois** manuscritos do
repositório e recebem a pasta como argumento (`--dir` e posicional). Sem
argumento, agem sobre este. O outro é `artigo-neoplasias/`.

## Nenhum número do texto é digitado

Cada valor citado no manuscrito existe em `tabelas/`, e cada tabela sai de
`gerar_tabelas.py` lendo os Parquet publicados com SHA-256 no manifesto. Um
número no texto que não esteja em nenhum CSV é um número sem procedência.

É a mesma disciplina de `scripts/_achados.py`, e pela mesma razão: prosa não
tem quem a contradiga, e por isso envelhece em silêncio. Já aconteceu neste
projeto de um coeficiente publicado descrever um dado que fora corrigido.

**Ao alterar o dado, rodar `gerar_tabelas.py` antes de reler o texto.** As
tabelas se atualizam sozinhas; os números escritos em prosa, não.

## Os produtores das análises

O manuscrito não calcula nada. Ele descreve o que estes três scripts produzem:

- `scripts/pipeline_mortalidade_causa_municipio.py` — a tabela município × CID
- `scripts/analise_perfil_mortalidade.py` — eixos, grupos e correlações
- `scripts/analise_anomalia_causas.py` — desvios do padrão próprio
- `scripts/analise_contexto_social.py` — o espaço social e o cruzamento

## Por que um renderizador próprio

O `.md` usa um subconjunto pequeno e estável — títulos, parágrafos, listas,
tabelas, ênfase, código inline. Um conversor genérico traria dependência e
devolveria menos controle sobre tipografia e quebra de página.

Uma armadilha real, encontrada e corrigida: ênfase que atravessa um trecho de
código (``**Texto (`arquivo.csv`).**``) quebrava quando cada pedaço era
processado isoladamente, e os asteriscos vazavam para a página. Os trechos de
código agora viram marcador e só voltam no fim.

## Autoria

O manuscrito traz **coautoria a definir** na folha de rosto, de propósito. É
rascunho de trabalho, não submissão.
