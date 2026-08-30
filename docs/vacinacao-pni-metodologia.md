# Vacinação (PNI/RNDS): o que dá para medir e o que não dá

Nota longa de metodologia, escrita em 30/08/2026. A versão condensada está
publicada na seção 16 de /metodologia; este arquivo guarda os números que não
cabem na página.

## A fonte

Doses aplicadas do Programa Nacional de Imunizações, alimentado pela Rede
Nacional de Dados em Saúde (RNDS). A RNDS em si não é fonte consumível: exige
CNES, certificado ICP-Brasil e credenciamento no DATASUS, e trafega registro
individual identificado sob LGPD. O que é aberto é o **derivado**: um arquivo
mensal por competência, com registro individual pseudonimizado (`co_paciente`
é hash de 64 caracteres), publicado no portal de dados abertos do SUS.

Processamos **jan/2023 a ago/2026**: 638.312.271 doses, 78,9 GB comprimidos,
lidos em streaming sem materializar os ~320 GB de CSV.

**Atualidade.** O arquivo de agosto de 2026 estava disponível em agosto de
2026. É a fonte mais recente do projeto — mais fresca que o InfoDengue, e três
anos à frente da mortalidade consolidada.

## Integridade verificada

Quarenta e quatro arquivos mensais independentes, cada um conferido:

| guarda | resultado |
|---|---|
| duplicatas de `co_documento` dentro do mês | **0** em 638 milhões |
| duplicatas entre competências distintas | **0 pares** |
| registros fora da própria competência | **0** |
| municípios presentes em todos os meses | **5.571 de 5.571** |
| doses sem município do paciente | 1,11% a 1,81% por mês |

O recorte mensal é limpo: a série pode ser montada por concatenação, sem a
reconciliação de calendário que o SIH exigiu.

**Validação externa.** Em agosto de 2026, São Bernardo do Campo registra 127,6
doses de tríplice viral por mil habitantes, Guarulhos 92,4 e São Paulo 85,0,
contra 2,3 no Rio de Janeiro. Os três municípios somam 13× o resto do estado —
e são exatamente os três nomeados pelo Ministério da Saúde em julho de 2026 ao
ampliar a recomendação contra sarampo. O dado reproduz um evento público
datado, com a geografia e a magnitude certas.

## Limpeza do vocabulário

O campo de imunobiológico traz **115 rótulos**, e nem todos são vacina:

- **11 diluentes** (`DILBCG`, `DILSCR`, `NaCl 0,9%`, …) — 1.381 doses. Não é
  imunobiológico administrado.
- **18 soros e imunoglobulinas** (`SAT`, `SAR`, `IGHAT`, …) — 420.905 doses.
  São profilaxia pós-exposição, não vacinação.
- **3 rótulos que não classificamos com segurança** (`FTp`, `Fta`, `Tétano`) —
  26.707 doses, 0,004%. Ficam de fora e são listados aqui em vez de sumirem em
  silêncio.

Ao todo 1,455% das doses saem da contagem de vacinação.

## O que publicamos

**Contagem de doses por município e ano**, e **por UF e mês**. Contagem não
depende de denominador, e por isso não herda nenhum dos problemas da seção
seguinte.

**Cobertura vacinal por UF e ano**, apenas para 2023 e 2024 — os anos em que
existem nascidos vivos definitivos (SINASC), e apenas para cinco indicadores:
pentavalente, poliomielite, rotavírus, pneumocócica e meningocócica.

Cada indicador declara **qual tipo de dose conta**. Somar tipos diferentes
conta a mesma criança duas vezes: um conjunto genérico de "1ª dose, única,
dose" produziu 110,6% de cobertura de BCG. Cobertura acima de 100% é usada
como guarda automática de erro de composição.

## O que NÃO publicamos, e por quê

### Cobertura vacinal municipal

Testada e reprovada. O critério foi fixado antes de olhar o resultado: se a
correlação da cobertura municipal entre 2023 e 2024 ficasse abaixo de 0,50, o
indicador seria ruído.

**Resultado: 0,591 de Pearson, 0,529 de Spearman** — nem ruído puro nem sinal
utilizável. O detalhe por porte mostra por quê:

| nascidos no ano | municípios | cobertura mediana | acima de 100% | correlação 23×24 |
|---|---|---|---|---|
| 50–100 | 988 | 102,7% | 56,0% | 0,42 |
| 100–250 | 1.539 | 100,9% | 52,3% | 0,58 |
| 250–500 | 862 | 98,1% | 43,3% | 0,69 |
| 500–1.000 | 440 | 94,4% | 28,0% | 0,74 |
| 1.000–5.000 | 372 | 91,2% | 13,7% | 0,63 |
| 5.000+ | 64 | 86,2% | 4,7% | 0,79 |

A mediana cai de 102,7% para 86,2% conforme o município cresce. Ruído não tem
direção; isso é **viés sistemático de denominador**, que superestima cobertura
em município pequeno e subestima em grande. Mesmo acima de 300 nascidos, onde
a correlação passa de 0,70, quase 30% dos municípios seguem acima de 100% — ou
seja, onde o indicador é estável, o nível continua errado.

**A hipótese óbvia foi testada e refutada.** Suspeitávamos de descasamento
geográfico: o numerador conta a dose pela residência declarada na vacinação, o
denominador conta o nascimento pela residência da mãe no parto. Medimos o
fluxo — a mediana dos municípios aplica 15,8% das doses dos seus residentes
fora do próprio território, p90 de 23,1%. A correlação desse fluxo com o
excesso de cobertura é **+0,002**. Não explica nada. Faz sentido: o numerador
já é por residência, não por local de aplicação.

Também testamos o local de nascimento, comparando BCG (aplicada na
maternidade) com pentavalente (aplicada na unidade básica). Se o problema
fosse atribuição ao município da maternidade, a diferença entre as duas
cresceria nos municípios pequenos. Ela fica entre 0,8 e 2,6 pontos em todas as
faixas de porte.

O descasamento de coorte — criança nascida em dezembro, vacinada em janeiro —
existe e é mensurável, mas pequeno: com a natalidade caindo 3,7% ao ano, ele
infla a cobertura em **+0,5% em 2023 e +3,1% em 2024**. Explica parte do nível
nacional, nada da dispersão municipal.

Este é o quinto achado nulo bem testado do projeto — a metodologia já conta
vazio assistencial, cobertura da APS, saúde suplementar e gasto público (SIOPS)
como os quatro anteriores sobre o %ICSAP.

### BCG e hepatite B ao nascer, mesmo por UF

Os dois são aplicados na maternidade, e por UF chegam a **127,8% (Ceará)** e
**121,0% (Alagoas)** em 2024. As cinco vacinas aplicadas na atenção básica
ficam contidas: pentavalente vai a no máximo 104,2%, poliomielite a 95,1%.
Onde a dose é dada no local de nascimento, o denominador por residência da mãe
não serve.

## Incerteza que permanece

A **composição do indicador** move o número mais do que gostaríamos. Incluir
hexavalente e pentavalente acelular na cobertura de pentavalente levou 2024 de
92,2% para 96,4% — quatro pontos por uma decisão de rótulo. Antes de publicar,
a composição precisa vir da definição oficial do PNI, não da nossa leitura.

Há também uma pergunta em aberto sobre **setor privado**: o arquivo inclui
doses de estabelecimentos privados integrados à RNDS, e não sabemos se a
cobertura oficial as considera. Isso pode explicar parte da diferença entre
nossos números e os publicados.

## Reprodução

Os agregados por competência, os checkpoints por mês e os metadados de origem
(tamanho do arquivo, `Last-Modified`) permitem refazer qualquer número.
A escolha da chave de agregação está registrada com as cardinalidades medidas
que a sustentam.
