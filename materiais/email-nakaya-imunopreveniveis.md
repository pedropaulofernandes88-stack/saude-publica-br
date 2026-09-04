# E-mail ao Helder Nakaya — artigo das mortes imunopreveníveis

**Rascunho, escrito em 2026-09-04. Ainda não enviado.**

Acompanha o envio de `artigo-imunopreveniveis/manuscrito.pdf` e
`artigo-imunopreveniveis/dados-do-artigo.zip`.

Fica aqui, e não em `saida/`, pela mesma razão que `briefing-nakaya.html` fica:
é material pontual de uma conversa específica, escrito à mão e não gerado por
script. `saida/` é para o que já foi entregue a terceiros e cujos bytes exatos
precisam sobreviver.

## O que este e-mail é, e por que ele é diferente do anterior

O primeiro manuscrito do repositório executou um **desenho que o Nakaya passou**.
Este não: a pergunta é do Pedro, e por acaso caiu no campo dele — vacinologia.

A diferença muda o enquadramento. Não dá para mandar como "fiz o que o senhor
pediu"; e mandar como entrega pronta seria pior, porque converteria a relação em
fornecimento de material. O e-mail é escrito como rascunho para crítica, com a
folha de rosto do manuscrito em "coautoria a definir" de propósito.

## O gancho, e por que é ele

O artigo tem três achados. O que abre porta para colaboração é o terceiro, e não
o maior: **a correção central que o artigo propõe é um argumento imunológico,
não epidemiológico.**

A Lista Brasileira mantém tuberculose miliar e do sistema nervoso no subgrupo de
imunoprevenção, e a revisão de 2011 declara o motivo — a vacina BCG. O critério
não restringe idade; a evidência que o fundamenta, sim. Metade do que o
instrumento oficial reporta como morte evitável por vacina é tuberculose de
adulto.

Medir a consequência disso é o que a base faz. Julgar se o critério se sustenta
é trabalho de quem estuda mecanismo. Essa é uma divisão de trabalho de verdade —
e é a diferença entre coautoria em pergunta científica e "me manda a tabela",
que é o modo específico de perder mesmo com o interlocutor interessado.

O gancho secundário é operacional e serve ao grupo dele diretamente: o PNI/RNDS
registra 16,6 milhões de doses de influenza em 2023 contra 54,2 milhões em 2024,
com o total de imunobiológicos praticamente igual. Quem usar a RNDS como
denominador em 2023 mede integração, não vacinação.

## O que ficou de fora, de propósito

- **o inventário da base** (39 tabelas, 5,3 milhões de linhas). Ele já viu na
  reunião de 01/09, e repetir desloca o e-mail de pergunta científica para
  catálogo de fornecedor;
- **a comparação com o primeiro manuscrito**, além da primeira linha. Este texto
  precisa se sustentar sozinho;
- **adjetivo sobre o tamanho do achado.** Os números fazem o trabalho; "inédito"
  ou "importante" só tirariam força de um texto cuja credibilidade vem de
  declarar limites.

A página dos limites foi o que mais trabalhou a favor no material da reunião.
Por isso os dois limites e o resultado nulo ficam no corpo, e não num anexo.

Ver `.claude` — o contexto completo da relação está na memória do projeto, em
`nakaya-colaboracao`.

---

## O texto

**Assunto:** Um segundo rascunho — mortes evitáveis por vacina, e um instrumento que parou em 2010

Prof. Helder,

Depois do manuscrito que saiu do desenho que o senhor passou, fui atrás de uma pergunta minha. Ela caiu no seu campo, e é por isso que mando.

A pergunta era simples: quantas pessoas morrem no Brasil de doença que uma vacina previne. Existe resposta oficial — o subgrupo 1.1 da Lista Brasileira de Causas de Mortes Evitáveis, do Ministério da Saúde. Apliquei aos 14.484.496 óbitos do SIM entre 2015 e 2024.

Ela identifica **5.832 óbitos**: quatro em cada dez mil, e o número não se move há uma década. Não é porque o Brasil resolveu o problema. São três propriedades do instrumento, cada uma mensurável:

1. **A lista termina aos 74 anos** — não existe lista brasileira acima disso. 267.276 óbitos por causas com vacina, 35,8% do total, ficam fora por definição, justamente onde influenza, pneumococo e COVID-19 matam.
2. **Ela é de 2010:** sem COVID-19, rotavírus, meningococo, pneumococo, varicela e HPV, e com influenza classificada fora da imunoprevenção.
3. **Metade do que ela conta — 3.189 de 5.832 — é tuberculose miliar e do sistema nervoso**, sendo 3.092 entre 5 e 74 anos. A revisão de 2011 diz explicitamente por que os manteve: "por serem as causas evitáveis de morte pela vacina BCG".

O terceiro ponto é o que me fez escrever. Ele não é epidemiológico, é imunológico: a proteção estabelecida da BCG é contra formas graves na criança, e o critério da lista não restringe idade. Eu consigo medir a consequência; quem decide se o critério se sustenta é quem trabalha com mecanismo. É aí que vejo pergunta comum.

Fora do instrumento, na mesma década: febre amarela com 452 óbitos em 2017–2018, em áreas que só entraram na recomendação depois do surto; sarampo com 37 óbitos entre 2018 e 2021, 19 deles em menores de 1 ano; coqueluche com 22 em 2024, 21 em menores de 1 ano; e influenza com o maior valor de onze anos em 2025, ainda preliminar.

Dois limites que prefiro declarar antes de o senhor perguntar:

- o que conto são óbitos por doença **com vacina disponível**, e isso não é "morte evitável". Faltam eficácia e situação vacinal individual, que o SIM não traz — todo total é teto;
- o teto real é de codificação: há 631.108 óbitos por pneumonia sem agente identificado contra 809 atribuídos ao pneumococo. Doença pneumocócica invasiva é incontável por causa básica no Brasil.

Testei também se a mortalidade por influenza em 60+ acompanha as doses aplicadas, por UF, com o critério de nulidade declarado antes de olhar. Deu nulo (ρ = +0,389 em 2023 e −0,056 em 2024) e vai publicado assim. No caminho apareceu algo que talvez interesse ao seu grupo: o PNI/RNDS registra 16,6 milhões de doses de influenza em 2023 contra 54,2 milhões em 2024, com o total de imunobiológicos praticamente igual. A campanha de 2023 não chegou inteira ao registro — quem usar a RNDS como denominador naquele ano mede integração, não vacinação.

Seguem o manuscrito (21 páginas, 16 tabelas) e um zip com as tabelas, as saídas de análise e o código que as gera. Não é entrega pronta: é rascunho para o senhor criticar, e a folha de rosto está com coautoria a definir de propósito.

O que eu queria não é um parecer geral, é uma escolha: vale transformar isso numa proposta de atualização da lista, com o critério imunológico entrando junto? Ou o senhor vê uso melhor para o material? E se for mais simples começar pequeno, um aluno seu usar a base num piloto já me serve.

Abraço,
Pedro Paulo

---

## Procedência dos números citados

Todos saem de `artigo-imunopreveniveis/tabelas/`, pelas mesmas tabelas que o
manuscrito embute:

| número | tabela |
|---|---|
| 14.484.496 óbitos | `tabela_1_base.csv` |
| 5.832 e 4,03 por 10 mil | `tabela_3_subgrupo_1_1_por_ano.csv` |
| 267.276 e 35,8% | `tabela_5_estrutura_etaria.csv` |
| 3.189 e 3.092 | `tabela_6_composicao_subgrupo_1_1.csv` |
| 452, 37, 19, 22, 21 | `tabela_8_eventos_serie_anual.csv` |
| 4.575 de 2025 | `tabela_10_influenza_por_faixa.csv` |
| 631.108 e 809 | `tabela_12_teto_codificacao.csv` |
| ρ = +0,389 e −0,056 | `tabela_15_correlacao_por_ano.csv` |
| 16,6 e 54,2 milhões de doses | arredondados de 16.621.107 e 54.215.093, na mesma tabela |

Se o dado for recoletado, rodar `gerar_tabelas.py` e **reler este texto**: as
tabelas se atualizam sozinhas, os números escritos em prosa não. É a mesma
armadilha que `tests/test_manuscrito.py` existe para pegar dentro do manuscrito
— e que aqui, num arquivo solto, não tem quem pegue.
