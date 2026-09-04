# Manuscrito — mortalidade por câncer

Rascunho de artigo sobre mortalidade por neoplasia maligna no Brasil, 2015–2024,
escrito a partir do levantamento executado em 2026-09-03.

| arquivo | o que é |
|---|---|
| `manuscrito.md` | **a fonte.** É aqui que se edita — menos as tabelas |
| `gerar_tabelas.py` | executa a análise e produz `tabelas/*.csv` |
| `tabelas/` | as quinze tabelas do artigo, em CSV |
| `manuscrito.html`, `manuscrito.pdf` | derivados — **não se editam à mão** |

```
.venv311/Scripts/python artigo-neoplasias/gerar_tabelas.py
.venv311/Scripts/python artigo/sincronizar_tabelas.py --dir artigo-neoplasias
.venv311/Scripts/python artigo/renderizar.py artigo-neoplasias
```

O sincronizador e o renderizador **moram em `artigo/`** e recebem a pasta como
argumento. Copiá-los para cá criaria duas versões que divergem em silêncio — o
mesmo motivo de `scripts/_sim_obitos.py` existir.

## Nenhum número do texto é digitado, e agora isso é testado

Cada valor citado no manuscrito existe em `tabelas/`, e cada tabela sai de
`gerar_tabelas.py`, que por sua vez executa `scripts/analise_neoplasias.py` —
o único lugar onde alguma taxa é calculada.

A regra vale para as tabelas **e para a prosa**. `tests/test_manuscrito.py`
confere as duas coisas:

- que nenhuma tabela embutida divergiu do seu CSV;
- que todo decimal com vírgula e todo inteiro com separador de milhar do texto
  corrido aparece em alguma tabela do próprio manuscrito.

A segunda guarda existe porque sincronizar a tabela **não** sincroniza o
parágrafo. No primeiro manuscrito foi exatamente assim que o total de óbitos
ficou desatualizado num dos três lugares em que aparecia: a tabela estava certa
e a frase, não. Há uma única exceção declarada — `29,4`, o valor **errado** que
a §2.2 cita como exemplo da armadilha que o método corrigiu.

**Ao alterar o dado, rodar `gerar_tabelas.py` e o sincronizador antes de reler o
texto.**

## O produtor da análise

O manuscrito não calcula nada, e `gerar_tabelas.py` também não — ele traduz
nomes de coluna e rótulos. Toda conta está em:

- `scripts/analise_neoplasias.py` — série nacional, decomposição, contrafactual,
  sítios, unidades da federação, quartis de vulnerabilidade e eixo social.

Se aparecer uma divisão em `gerar_tabelas.py`, ela está no lugar errado.

## Por que `gerar_tabelas.py` recalcula em vez de ler o disco

Ele roda a análise inteira antes de formatar (~40 s). Ler os CSVs que já estão
em `data/analises/neoplasias/` pareceria equivalente e não é: bastaria alguém
recoletar o SIM e esquecer de rodar a análise para o artigo passar a descrever
um dado que não existe mais, calado. Foi o que aconteceu no primeiro manuscrito
quando 2024 foi recoletado do `.dbc`.

`--sem-recalcular` existe para iterar formatação, nunca para gerar entrega.

## Autoria

**Coautoria a definir** na folha de rosto, de propósito. É rascunho de trabalho,
não submissão.
