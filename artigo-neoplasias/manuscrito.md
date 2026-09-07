# Mortalidade por câncer no Brasil, 2015–2024: um aumento inteiramente demográfico, e um gradiente social que se inverte no colo do útero

**Pedro Paulo Fernandes**¹

¹ Saúde em Dado — saudeemdado.com · ORCID e afiliação a completar

*Coautoria a definir. Este é um rascunho de trabalho preparado a partir do levantamento executado em 2026-09-03.*

---

## Resumo

**Contexto.** O número de mortes por câncer no Brasil cresce ano a ano, e o crescimento é rotineiramente noticiado como avanço da doença. A população brasileira, no mesmo período, envelheceu depressa. Contagem de óbitos e risco de morrer são grandezas diferentes, e num país em transição demográfica elas podem apontar para lados opostos.

**Objetivo.** Separar, na mortalidade por neoplasia maligna registrada no Brasil entre 2015 e 2024, o que é crescimento e envelhecimento populacional do que é mudança de risco; e descrever como o risco remanescente se distribui por idade, sítio do tumor, território e posição social.

**Métodos.** Todos os óbitos por neoplasia maligna (CID-10 C00–C97, causa básica truncada em três caracteres) registrados no Sistema de Informações sobre Mortalidade entre 2015 e 2024, agregados por município de residência, ano, faixa etária e sexo (Tabela 1). Denominador pela Projeção da População do IBGE, revisão 2024, por idade simples. Taxas padronizadas pelo método direto com duas populações padrão — Brasil/Censo 2022 e padrão mundial da OMS —, esta última para permitir comparação externa. O aumento no número de óbitos foi decomposto em três termos — tamanho da população, estrutura etária e taxas específicas por idade — pela média das seis ordens de aplicação. O eixo social usa o microdado nacional de 2022–2023, único recorte em disco que traz cor/raça, escolaridade e local de ocorrência; o denominador por cor/raça vem da tabela 9606 do SIDRA (Censo 2022). O gradiente municipal usa quartis de um índice de vulnerabilidade social construído sobre analfabetismo e falta de água, com análise de sensibilidade por redistribuição pro-rata das causas mal definidas.

**Resultados.** Os óbitos por neoplasia maligna passaram de 205.998 em 2015 para 259.084 em 2024, enquanto a taxa padronizada por idade caiu de 123,04 para 120,18 por 100 mil pelo padrão brasileiro e de 84,56 para 81,43 pelo padrão mundial da OMS (Tabela 2). A decomposição atribui +47.314 óbitos ao envelhecimento e +11.390 ao crescimento populacional, contra −5.619 devidos à queda das taxas específicas (Tabela 4): o aumento é integralmente demográfico. A probabilidade de uma pessoa de 30 anos morrer de câncer antes dos 70 caiu de 7,428% para 7,138% (Tabela 16). Mantido o risco de 2019, teriam sido registrados mais 48.543 óbitos entre 2020 e 2024 (Tabela 5), com o déficit encolhendo de 5,3% para 2,1% ao longo do período. O sítio predominante muda com a idade — leucemias e encéfalo na infância, mama e colo do útero entre 30 e 44 anos, brônquios/pulmões e próstata depois dos 60 (Tabela 6). A mortalidade padronizada é maior onde há menos vulnerabilidade: 127,3 por 100 mil no quartil menos vulnerável contra 91,5 no mais vulnerável, com causas mal definidas em 4,09% e 7,24% dos óbitos respectivamente; redistribuídas as mal definidas, o gradiente cai de 39% para 35% e **persiste** (Tabela 9). Entre 23 sítios, seis são mais letais no quartil vulnerável, encabeçados pelo colo do útero (razão 1,27), enquanto o cólon é 0,33 (Tabela 10). O mesmo padrão reaparece no recorte individual: a taxa padronizada é 132,7 entre pessoas brancas e 98,3 entre pretas, mas o colo do útero mata 10,54 por 100 mil entre indígenas e 5,73 entre brancas, e a próstata 19,82 entre pretos e 16,54 entre brancos (Tabelas 11 e 12).

**Conclusões.** O aumento das mortes por câncer no Brasil não é aumento de risco. O gradiente social da mortalidade registrada é dominado por diferenças de detecção e de risco competitivo, e por isso aparece invertido em relação à expectativa; os sítios que dependem de rastreamento — colo do útero acima de todos — resistem a essa inversão e são os candidatos naturais a indicador de equidade oncológica no Brasil.

**Palavras-chave:** neoplasias; mortalidade; padronização por idade; desigualdades em saúde; sistemas de informação em saúde; colo do útero.

---

## 1. Introdução

Entre 2015 e 2024, o número anual de mortes por câncer registradas no Brasil cresceu em torno de um quarto. A leitura imediata desse número — a de que o câncer avança — é a que circula, e é a que este trabalho examina.

O problema com ela não é estatístico, é demográfico. Câncer é, em quase todos os seus sítios, uma doença de idade avançada: a taxa de mortalidade por 100 mil habitantes separa por duas ordens de grandeza a primeira infância dos maiores de 74 anos (Tabela 3). Um país cuja pirâmide etária se inverte registra mais mortes por câncer ainda que nenhum indivíduo adoeça mais do que antes. Contar óbitos e medir risco, nesse contexto, são operações que podem apontar para lados opostos — e a padronização por idade, longe de ser um refinamento técnico, é o que separa uma leitura da outra.

Há uma segunda camada. Mortalidade por câncer registrada não é incidência de câncer. Ela é o produto de três coisas que a base não separa: quanto câncer existe, quanto dele é diagnosticado e corretamente codificado, e quanto tempo as pessoas sobrevivem depois do diagnóstico. Onde o acesso ao diagnóstico é pior, a mortalidade *registrada* por câncer pode ser menor — e a mortalidade por causa mal definida, maior. Um gradiente social lido sem essa ressalva pode ser exatamente do sinal contrário ao que a intuição sugere, e este trabalho encontra precisamente esse caso.

A pergunta que organiza o texto tem três partes, portanto:

1. quanto do aumento observado é população, envelhecimento e risco?
2. o risco remanescente se distribui como? por idade, por sítio, por território, por posição social?
3. onde o gradiente social observado é epidemiologia e onde é detecção?

A terceira é a mais difícil, e a única estratégia honesta disponível com dado de mortalidade é **procurar o sítio que desobedece**. Se toda a diferença entre municípios ricos e pobres fosse subdiagnóstico, ela seria aproximadamente uniforme entre os tipos de tumor. Um sítio que inverta o gradiente é um sítio cuja mortalidade não está sendo governada por detecção — e é onde o achado social sobrevive.

---

## 2. Métodos

### 2.1 Dados e recorte de causa

**Tabela 1. Enquadramento do estudo (`tabela_1_base.csv`).**

| Item | Valor |
|---|---|
| Fonte dos óbitos | SIM/DataSUS — .dbc por UF (2015–2021, 2024) e CSV nacional do OpenDataSUS (2022–2023) |
| Período consolidado | 2015–2024 |
| Recorte de causa | CID-10 C00–C97 (neoplasias malignas), causa básica truncada em três caracteres |
| Óbitos em D00–D48, excluídos do recorte | 45.953 |
| D00–D48 como fração do capítulo II | 2,0% |
| Óbitos por neoplasia maligna | 2.293.075 |
| Óbitos sem idade declarada, redistribuídos pro-rata | 241 |
| Óbitos com sexo ignorado | 121 |
| Óbitos com município ignorado, UF recuperada do código | 378 |
| Denominador populacional | IBGE — Projeções da População, revisão 2024 (por UF, ano e idade simples) |
| População padrão | Brasil, Censo 2022, e padrão mundial da OMS 2000–2025 (método direto, as duas) |
| Período do eixo social | 2022–2023 |
| Óbitos no microdado social (todas as causas) | 3.005.666 |
| Óbitos por neoplasia maligna no microdado social | 488.535 |
| Sem cor/raça declarada, entre os óbitos por câncer | 1,6% |
| Sem escolaridade declarada, entre os óbitos por câncer | 13,2% |
| Denominador por cor/raça | IBGE — Censo 2022, SIDRA t/9606 (cor/raça × sexo × idade) |
| Óbitos fetais | excluídos na fonte — TIPOBITO = 2 em 100% dos registros |
| Ano preliminar excluído | 2025 (SIM/PRELIM/DORES) |

O capítulo II da CID-10 vai de C00 a D48, mas D00–D48 reúne neoplasias in situ, benignas e de comportamento incerto — outra doença, com outra história natural. O recorte adotado é **C00–C97**, o de neoplasia maligna usado pelo Instituto Nacional de Câncer, pela Agência Internacional de Pesquisa em Câncer e pela Organização Mundial da Saúde. A diferença não é cosmética: os 45.953 óbitos de D00–D48 no período são 2% do capítulo, e incluí-los tornaria a série incomparável com qualquer publicação externa.

A fonte dos óbitos segue a rota já estabelecida na plataforma que sustenta este trabalho: arquivos `.dbc` por unidade da federação para 2015–2021 e 2024, e o CSV nacional do OpenDataSUS para 2022–2023, anos em que as duas rotas coincidem exatamente. Para 2024 a rota do CSV foi abandonada porque trazia 6,9% menos óbitos que a do FTP, com a ausência concentrada nos últimos meses do ano.

O ano de 2025 existe na base, marcado como preliminar, e **fica fora de todos os cálculos**. Dado preliminar tem a cauda incompleta e, o que importa mais aqui, tem excesso de imprecisão diagnóstica: a investigação de óbito converte causa mal definida em diagnóstico específico ao longo de meses. Como a precisão da codificação é uma das dimensões medidas neste trabalho (§3.6), misturar versões de vintages diferentes leria como variação geográfica o que seria variação de tempo desde o óbito.

### 2.2 Denominadores e padronização

O denominador é a **Projeção da População, revisão 2024, do IBGE** [8]: população por unidade da federação, ano e **idade simples**, de 0 a 90 ou mais. É a série oficial posterior ao Censo 2022, e o seu total de 2022 — 210.862.983 — não coincide com os 203.080.756 que o Censo enumerou: a diferença é a subcontagem censitária medida pela Pesquisa de Pós-Enumeração, que o IBGE reconcilia. Para uma taxa de mortalidade essa reconciliação não é opcional. O numerador conta o óbito de quem o recenseamento não encontrou exatamente como conta o dos demais; usar a contagem bruta como denominador superestimaria toda taxa deste artigo, e a Tabela 17 mostra o quanto.

A escolha foi feita depois de refazer o estudo inteiro sob cada alternativa (Tabela 17, no apêndice). A projeção anterior (revisão 2018), que a plataforma vinha usando, é **anterior ao Censo** e põe 214.828.540 pessoas em 2022, com o excesso concentrado nas idades jovens. Uma série reconciliada construída internamente acerta o total e erra a **forma**: ela desloca massa para a primeira infância e retira da faixa de 60 a 74 anos, que é onde o câncer mata — um denominador baixo ali infla a taxa padronizada sem que o total denuncie nada. E a contagem censitária bruta, que é estática, não serve de denominador para série temporal alguma: com ela a taxa padronizada **sobe 25,8%**, porque um denominador parado devolve a taxa bruta com outro nome.

Ter idade simples também resolve duas limitações declaradas na primeira versão deste trabalho: a padronização pelo padrão mundial passa a ser possível no grão quinquenal em que ele é publicado, e o recorte de 30 a 69 anos da OMS (§3.2) deixa de ser impossível de montar.

As taxas padronizadas usam o **método direto** com **duas** populações padrão, publicadas lado a lado. A do **Brasil (Censo 2022)** em sete faixas mantém a comparabilidade interna com o resto da plataforma. A do **padrão mundial da OMS 2000–2025** [9], em grupos quinquenais, é a que torna esta série comparável com o INCA, a IARC e o GLOBOCAN — a primeira versão deste artigo declarava essa incomparabilidade como limitação, e ela deixa de existir. As duas colunas usam exatamente os mesmos óbitos.

Uma armadilha de implementação merece registro, porque produziu um resultado falso e plausível na primeira medição. Ao padronizar uma taxa por sítio, os estratos sem nenhum óbito não existem no dado agregado; somar apenas os estratos presentes renormaliza os pesos para as faixas em que o tumor ocorre, e infla o resultado. O câncer de laringe apareceu assim com 29,4 óbitos por 100 mil habitantes — cerca de quatro vezes o valor real — porque só as faixas idosas entravam na conta. Toda taxa por sítio neste trabalho parte de um produto cartesiano completo entre estrato e causa, com zero contado como zero.

### 2.3 O que a auditoria do dado encontrou, e o que foi corrigido

Os números deste artigo mudaram entre a primeira e a segunda versão, e a razão não foi dado novo do DataSUS: foi auditoria do que já estava em uso. Registram-se aqui os achados, porque cada um deles é um modo de errar que sobrevive a revisão por pares.

**O numerador perdia 241 óbitos.** A tabela agregada por faixa etária que servia de origem não tem onde pôr o óbito sem idade declarada, e ele desaparecia — cerca de um em cada dez mil, sempre para menos. Reconstruído da fonte, o total é 2.293.075 e bate exatamente com a tabela municipal do próprio projeto. Os 241 voltam por redistribuição pro-rata dentro do mesmo ano e da mesma causa.

**Três bases de denominador conviviam no mesmo artigo.** A série nacional e a de unidades da federação usavam a projeção de 2018; o recorte por quartil de vulnerabilidade usava o Censo municipal; o de cor/raça, o Censo do SIDRA. A Tabela de unidades da federação e a de quartis, que o leitor compara lado a lado, estavam em escalas diferentes.

E a diferença entre bases **não é um deslocamento uniforme**. Medida unidade por unidade da federação, ela vai de negativa a mais de quinze por cento, e trocar uma base pela outra move dezoito das vinte e sete unidades de posição no ordenamento, com saltos de até treze lugares. Os extremos — Rio Grande do Sul no topo, Maranhão na base — não se movem em nenhuma das duas, e é só sobre eles que o texto da §3.6 se apoia.

Agora há uma só base. O eixo municipal usa **forma do Censo e nível da projeção**: cada município mantém a composição etária enumerada e é escalado pelo fator da sua unidade da federação, ano a ano.

**Duas perdas menores, ambas declaradas na Tabela 1.** 121 óbitos por câncer têm sexo ignorado, e ficam fora apenas do recorte por sexo. E 378 estão registrados em códigos de município terminados em `0000` — "município ignorado" dentro de uma unidade da federação —, que não existem na tabela de municípios; o município se perde, a unidade da federação não, porque está nos dois primeiros dígitos do código.

**O que a correção mudou, e o que não mudou.** A Tabela 17 traz a taxa padronizada refeita sob as quatro séries: das três que servem como denominador de série temporal, todas dão queda, entre 2,3% e 4,4%. A decomposição continua atribuindo o aumento inteiro à demografia e sinal negativo ao risco; o gradiente por quartil de vulnerabilidade continua próximo de 40%; e os seis sítios que desobedecem a esse gradiente continuam sendo **os mesmos seis**.

Nenhum sinal se inverteu. A conclusão do trabalho não dependia da base do denominador — as magnitudes dependiam, e eram publicadas sem essa ressalva.

### 2.4 Decomposição do aumento

O número de óbitos de um ano é o produto de três fatores: o tamanho da população, sua distribuição por faixa etária e as taxas específicas por faixa. A variação entre 2015 e 2024 foi decomposta nesses três termos substituindo-os um a um pelos valores do ano final.

Os efeitos não são aditivos, e o valor atribuído a cada termo depende da ordem em que os três são substituídos. Fixar uma ordem embutiria uma preferência arbitrária no resultado; adota-se a **média das seis ordens possíveis**, e é ela que a Tabela 4 reporta. É a mesma exigência de simetria que Das Gupta [2] formaliza para decomposições de mais de dois fatores — aqui na forma mais simples, a média não ponderada sobre as ordens, que para três fatores é transparente e dispensa a álgebra do caso geral.

### 2.5 O contrafactual de 2019

A Tabela 5 compara os óbitos observados de 2020 a 2024 com os que teriam ocorrido se as taxas específicas por idade de 2019 tivessem se mantido, aplicadas à população efetivamente observada de cada ano.

Isto **não é uma estimativa de mortes evitadas**, e a distinção é o ponto. É a diferença entre o observado e um cenário em que o risco por idade tivesse ficado onde estava às vésperas da pandemia. Ao menos três mecanismos produzem essa diferença e o dado não os separa: risco competitivo (pessoas com câncer que morreram de COVID-19 antes), seleção de mortalidade na coorte mais frágil, e melhora real de prevenção ou tratamento. O quarto mecanismo candidato — piora do registro — pode ser descartado, e é o único que pode: a fração de óbitos por causa mal definida no país caiu ao longo do período, de modo que o déficit não vem de câncer que passou a ser codificado como outra coisa.

### 2.6 O eixo social, e por que ele é 2022–2023

Cor/raça, escolaridade e local de ocorrência do óbito são campos do microdado individual do SIM. O recorte de colunas em disco para 2015–2021 e 2024 não os traz; o arquivo nacional completo, sim, para 2022 e 2023. Todo o eixo social deste trabalho é, portanto, bienal, e a Tabela 1 registra o tamanho dessa base e a fração de registros sem declaração em cada campo.

O denominador por cor/raça vem da tabela 9606 do SIDRA (Censo 2022, população por cor ou raça, sexo e idade), agregada nas mesmas sete faixas. Quando o recorte é por sexo, a padronização usa os pesos do **mesmo sexo**: aplicar os pesos de ambos os sexos a estratos sexo-específicos soma a população duas vezes e dobra a taxa — foi o primeiro resultado obtido nesta análise, e era falso.

É o único recorte deste trabalho com contagens pequenas o bastante para que o acaso amostral importe: o câncer de cólon entre pessoas indígenas soma 28 óbitos no biênio, contra 18.904 entre brancas. As taxas das Tabelas 11 e 12 vêm, portanto, com **intervalo de 95% de Fay & Feuer** [1] — a generalização, para a taxa padronizada, do mesmo intervalo gama/Poisson exato que a plataforma já usa na taxa bruta, e o intervalo adotado pelo programa SEER do National Cancer Institute para taxas de câncer. A escolha também torna estas estimativas comparáveis em método, e não só em conteúdo, com a literatura oncológica.

Escolaridade recebe um tratamento diferente, e o motivo é confundimento de coorte. A idade mediana ao morrer de câncer é mais alta entre quem não tem escolaridade do que entre quem tem ensino superior, e ler isso como câncer mais precoce entre os instruídos seria erro elementar: quem não estudou, no Brasil, é quem já é velho. O eixo escolaridade aparece aqui apenas como **mortalidade proporcional dentro de faixa etária fixa** (30 a 69 anos) e como local de ocorrência do óbito — nunca como idade ao morrer.

### 2.7 Vulnerabilidade municipal e a correção por causa mal definida

Os municípios brasileiros foram ordenados por um índice de vulnerabilidade social construído sobre taxa de analfabetismo e percentual de domicílios sem água, e divididos em quartis. Os óbitos de 2022 a 2024 foram atribuídos ao quartil do município de residência; o denominador é a população municipal por faixa do Censo 2022, replicada nos três anos da janela — aproximação declarada, que afeta os quatro quartis no mesmo sentido.

Como a hipótese concorrente ao gradiente é a qualidade do registro, a Tabela 9 traz uma **taxa corrigida** ao lado da observada: as mortes por causa mal definida (R00–R99) de cada estrato são redistribuídas pro-rata sobre as causas definidas do mesmo estrato, o que equivale a supor que os óbitos sem diagnóstico se distribuem como os diagnosticados. É a correção mais favorável possível à hipótese de subdiagnóstico, e serve como teste: se o gradiente sobrevive a ela, não é só registro.

### 2.8 O que este desenho não faz

Não há teste de hipótese nem modelo de regressão neste trabalho, e o intervalo de confiança aparece só onde a contagem o exige (§2.7). Nos demais recortes o menor grupo comparado tem dezenas de milhares de óbitos, e o que limita a interpretação não é erro amostral: é confundimento estrutural — detecção, sobrevida e classificação. Um intervalo estreito em torno de uma taxa que mede parcialmente o acesso ao diagnóstico daria falsa impressão de precisão sobre a quantidade errada, e é por isso que as comparações centrais deste artigo se apoiam no **comportamento sítio a sítio**, e não na largura de um intervalo.

---

## 3. Resultados

### 3.1 Mais mortes, menos risco

**Tabela 2. Mortalidade por neoplasia maligna, Brasil, 2015–2024 (`tabela_2_serie_nacional.csv`).**

| Ano | Óbitos | População | Taxa bruta | Padronizada (Brasil) | Padronizada (OMS) | % causa mal definida | % C80 entre os cânceres |
|---|---|---|---|---|---|---|---|
| 2015 | 205.998 | 202.403.642 | 101,78 | 123,04 | 84,56 | 5,63 | 3,1 |
| 2016 | 211.343 | 203.871.925 | 103,66 | 122,57 | 84,13 | 5,76 | 2,92 |
| 2017 | 217.697 | 205.211.557 | 106,08 | 122,68 | 83,9 | 5,43 | 2,62 |
| 2018 | 223.757 | 206.529.038 | 108,34 | 122,47 | 83,54 | 5,33 | 2,44 |
| 2019 | 231.038 | 207.900.099 | 111,13 | 122,81 | 83,59 | 5,53 | 2,39 |
| 2020 | 224.829 | 209.164.889 | 107,49 | 116,22 | 78,98 | 5,78 | 2,38 |
| 2021 | 230.764 | 210.103.642 | 109,83 | 116,46 | 79,06 | 5,11 | 2,43 |
| 2022 | 238.623 | 210.862.983 | 113,16 | 117,49 | 79,76 | 5,32 | 2,4 |
| 2023 | 249.942 | 211.695.158 | 118,07 | 119,55 | 81,06 | 4,82 | 2,21 |
| 2024 | 259.084 | 212.583.750 | 121,87 | 120,18 | 81,43 | 4,48 | 2,32 |

Os óbitos por câncer passaram de 205.998 para 259.084 entre as pontas da série. No mesmo intervalo, a taxa bruta subiu de 101,78 para 121,87 por 100 mil habitantes — e a taxa padronizada por idade **caiu**, de 123,04 para 120,18 pelo padrão brasileiro e de 84,56 para 81,43 pelo padrão mundial da OMS. As duas padronizações discordam do nível e concordam do sinal, que é o que uma população padrão faz.

As duas taxas usam exatamente os mesmos óbitos e a mesma população. A única diferença entre elas é que a padronizada aplica a todos os anos a mesma estrutura etária, de modo que o que sobra seja risco. Publicar a bruta, num país em transição demográfica, é publicar a pirâmide etária com nome de epidemiologia.

A coluna do padrão mundial é a que permite sair do Brasil: 81,43 por 100 mil em 2024 é diretamente comparável com as séries do INCA, da IARC e do GLOBOCAN, o que a primeira versão deste artigo declarava impossível.

As duas últimas colunas são a defesa contra a explicação mais barata de qualquer queda de mortalidade específica: a de que a doença deixou de ser registrada. A fração de óbitos por causa mal definida caiu de 5,63% para 4,48% no período, e a fração de cânceres sem especificação de localização (C80), de 3,1% para 2,32%. O registro brasileiro ficou **mais** preciso, não menos.

O detalhe por faixa mostra que a queda não é uniforme.

**Tabela 3. Taxa específica por faixa etária, 2015 e 2024, por 100 mil habitantes da faixa (`tabela_3_taxa_por_faixa.csv`).**

| Faixa etária | Óbitos 2024 | Taxa 2015 | Taxa 2024 | Variação (%) |
|---|---|---|---|---|
| 0 a 4 | 533 | 4,16 | 4,09 | -1,7 |
| 5 a 14 | 1.039 | 4,02 | 3,58 | -10,9 |
| 15 a 29 | 3.425 | 7,11 | 7,25 | 2 |
| 30 a 44 | 14.553 | 27,67 | 29,51 | 6,6 |
| 45 a 59 | 48.413 | 136,16 | 121,64 | -10,7 |
| 60 a 74 | 103.126 | 415,2 | 410,62 | -1,1 |
| 75 ou mais | 87.996 | 972,52 | 971,81 | -0,1 |

Cai onde há mais massa — 10,9% entre 5 e 14 anos, 10,7% entre 45 e 59 — e é praticamente estável nas duas faixas idosas, que concentram os óbitos: −1,1% entre 60 e 74 anos e −0,1% entre os de 75 ou mais. E **sobe** nas faixas adultas jovens: 2% entre 15 e 29 anos e 6,6% entre 30 e 44. São as duas únicas faixas etárias do país em que o risco de morrer de câncer aumentou na década, e juntas respondem por parcela pequena dos óbitos, o que as torna invisíveis em qualquer agregado.

### 3.2 A probabilidade de morrer de câncer antes dos 70

**Tabela 16. Mortalidade prematura por câncer, 30 a 69 anos, Brasil (`tabela_16_prematura.csv`).**

| Ano | Óbitos de 30 a 69 | População de 30 a 69 | Taxa bruta | Prob. de morrer antes dos 70 (%) |
|---|---|---|---|---|
| 2015 | 110.317 | 95.049.605 | 116,1 | 7,428 |
| 2016 | 113.007 | 96.858.590 | 116,7 | 7,419 |
| 2017 | 115.730 | 98.562.641 | 117,4 | 7,386 |
| 2018 | 118.009 | 100.151.730 | 117,8 | 7,384 |
| 2019 | 121.006 | 101.667.451 | 119 | 7,407 |
| 2020 | 117.377 | 103.078.466 | 113,9 | 6,989 |
| 2021 | 119.299 | 104.298.056 | 114,4 | 6,979 |
| 2022 | 122.143 | 105.482.848 | 115,8 | 6,997 |
| 2023 | 126.929 | 106.732.086 | 118,9 | 7,127 |
| 2024 | 129.580 | 107.954.487 | 120 | 7,138 |

O indicador de mortalidade prematura por doença crônica não transmissível da OMS, alvo do Objetivo de Desenvolvimento Sustentável 3.4, é a probabilidade de uma pessoa de 30 anos morrer da causa antes dos 70. Para o câncer no Brasil ela era de **7,428%** em 2015 e é de **7,138%** em 2024 — uma queda de 3,9%.

A quantidade merece destaque por uma propriedade que nenhuma outra tabela deste artigo tem: ela **não depende de população padrão nenhuma**. É uma probabilidade sintética construída por tábua de vida sobre as taxas quinquenais, e por isso comparável entre países sem que seja preciso combinar antes qual população servirá de padrão — o problema que a §2.2 discute. Um leitor que desconfie das duas colunas padronizadas da Tabela 2 pode ler esta.

O perfil no tempo repete o das taxas padronizadas, inclusive o degrau: 7,407% em 2019, 6,989% em 2020, e recuperação lenta até 7,138% em 2024.

### 3.3 A decomposição

**Tabela 4. Decomposição do aumento de óbitos entre 2015 e 2024 (`tabela_4_decomposicao.csv`).**

| Componente | Óbitos | % da variação |
|---|---|---|
| Crescimento populacional | 11.390 | 21,5 |
| Envelhecimento (estrutura etária) | 47.314 | 89,1 |
| Risco (taxas específicas por idade) | -5.619 | -10,6 |
| Variação total 2015→2024 | 53.086 | 100 |

O envelhecimento da população responde por 89,1% do aumento e o crescimento populacional por 21,5%; a queda das taxas específicas devolve 10,6%, com sinal negativo. Somados, os dois termos demográficos explicam mais que a totalidade do aumento observado, e o risco atua no sentido contrário.

Não há, nesta série, um componente de "avanço da doença" a ser explicado. Há uma população que envelheceu.

### 3.4 O degrau que a pandemia deixou

**Tabela 5. Óbitos observados e esperados sob o risco por idade de 2019 (`tabela_5_contrafactual.csv`).**

| Ano | Observado | Esperado (risco de 2019) | Diferença | % |
|---|---|---|---|---|
| 2020 | 224.828 | 237.532 | -12.703 | -5,3 |
| 2021 | 230.763 | 243.321 | -12.557 | -5,2 |
| 2022 | 238.622 | 249.414 | -10.791 | -4,3 |
| 2023 | 249.942 | 256.752 | -6.810 | -2,7 |
| 2024 | 259.083 | 264.766 | -5.682 | -2,1 |
| 2020–2024 | 1.203.238 | 1.251.785 | -48.543 | -3,9 |

Mantido o risco de 2019, teriam sido registrados 48.543 óbitos por câncer a mais entre 2020 e 2024 — 3,9% acima do observado. O déficit encolhe monotonicamente: 5,3% em 2020, 4,3% em 2022, **2,1% em 2024**.

A forma da curva é informativa, e ela mudou de leitura com o denominador corrigido. A taxa padronizada era estável entre 2015 e 2019 — variando entre 122,47 e 123,04 — e cai para 116,22 em 2020. O que a série descreve é um degrau coincidente com a pandemia seguido de **recuperação em curso**: o déficit de 2024 é a metade do de 2020 e continua encolhendo. Sob a base anterior, o déficit parecia estacionar em 3,9%, e a leitura de "patamar novo" era defensável; ela não é mais.

A quarta explicação candidata é a que a Tabela 2 descarta. Se o degrau fosse artefato de registro — câncer que passou a ser codificado como causa mal definida —, a fração de causas mal definidas teria de subir em 2020 e permanecer alta. Ela sobe de 5,53% para 5,78% em 2020, volta a 5,11% em 2021 e chega a 4,48% em 2024, o menor valor da série; a fração de C80 entre os cânceres cai de 2,39% para 2,32% no mesmo intervalo. O degrau da mortalidade não é acompanhado por degrau nenhum na imprecisão. As três leituras da §2.5 permanecem abertas, e provavelmente todas contribuem.

### 3.5 Cada idade tem o seu câncer

**Tabela 6. Os três sítios mais letais em cada faixa etária, 2020–2024 (`tabela_6_sitios_por_faixa.csv`).**

| Faixa etária | 1º sítio | 2º sítio | 3º sítio |
|---|---|---|---|
| 0 a 4 | C91 Leucemia linfoide (576; 20,3%) | C71 Encéfalo (572; 20,2%) | C92 Leucemia mieloide (308; 10,9%) |
| 5 a 14 | C71 Encéfalo (1.209; 23,2%) | C91 Leucemia linfoide (1.188; 22,8%) | C92 Leucemia mieloide (439; 8,4%) |
| 15 a 29 | C71 Encéfalo (1.743; 10,4%) | C92 Leucemia mieloide (1.286; 7,7%) | C91 Leucemia linfoide (1.254; 7,5%) |
| 30 a 44 | C50 Mama (12.325; 17,6%) | C53 Colo do útero (8.312; 11,9%) | C16 Estômago (4.558; 6,5%) |
| 45 a 59 | C50 Mama (29.414; 12,4%) | C34 Brônquios e pulmões (22.894; 9,7%) | C16 Estômago (14.852; 6,3%) |
| 60 a 74 | C34 Brônquios e pulmões (72.950; 15,4%) | C50 Mama (31.253; 6,6%) | C16 Estômago (28.925; 6,1%) |
| 75 ou mais | C61 Próstata (52.435; 13,1%) | C34 Brônquios e pulmões (51.024; 12,8%) | C18 Cólon (25.756; 6,4%) |

"Câncer" é um agregado de dezenas de doenças com epidemiologias distintas, e o sítio predominante muda inteiramente ao longo da vida. Na primeira infância e na adolescência são as leucemias e os tumores do encéfalo, que juntos respondem por metade dos óbitos da faixa. Entre 30 e 44 anos, mama e colo do útero somam quase 30% de todas as mortes por câncer. Depois dos 60, brônquios e pulmões assumem, e entre os maiores de 74 anos a próstata é o primeiro sítio.

Dos sítios que aparecem nessa tabela, o do colo do útero é o único **evitável por rastreamento de rotina**, e é ele que reaparece em todos os recortes de desigualdade das seções seguintes.

**Tabela 7. Os dez sítios mais letais por sexo, 2020–2024 (`tabela_7_sitios_por_sexo.csv`).**

| Posição | Mulheres | Óbitos (F) | % (F) | Homens | Óbitos (M) | % (M) |
|---|---|---|---|---|---|---|
| 1 | C50 Mama | 96.080 | 16,5 | C61 Próstata | 83.653 | 13,5 |
| 2 | C34 Brônquios e pulmões | 68.832 | 11,8 | C34 Brônquios e pulmões | 81.641 | 13,1 |
| 3 | C18 Cólon | 36.951 | 6,4 | C16 Estômago | 45.675 | 7,3 |
| 4 | C53 Colo do útero | 34.917 | 6 | C18 Cólon | 35.130 | 5,6 |
| 5 | C25 Pâncreas | 32.653 | 5,6 | C15 Esôfago | 33.324 | 5,4 |
| 6 | C16 Estômago | 26.512 | 4,6 | C25 Pâncreas | 31.750 | 5,1 |
| 7 | C22 Fígado e vias biliares intra-hepáticas | 23.204 | 4 | C22 Fígado e vias biliares intra-hepáticas | 31.657 | 5,1 |
| 8 | C56 Ovário | 21.183 | 3,6 | C71 Encéfalo | 22.352 | 3,6 |
| 9 | C71 Encéfalo | 20.370 | 3,5 | C32 Laringe | 20.071 | 3,2 |
| 10 | C80 Sem especificação de localização | 14.246 | 2,5 | C67 Bexiga | 16.919 | 2,7 |

Entre mulheres, a mama lidera com 16,5% dos óbitos por câncer, seguida de brônquios e pulmões com 11,8%; o colo do útero é o quarto sítio, com 6%. Entre homens, próstata (13,5%) e brônquios e pulmões (13,1%) lideram praticamente empatados. A categoria "sem especificação de localização" (C80) figura entre os dez sítios femininos, com 2,5%, o que é uma medida de imprecisão diagnóstica ocupando lugar de doença.

### 3.6 O território

**Tabela 8. Taxa de mortalidade por câncer por unidade da federação, 2022–2024 (`tabela_8_uf.csv`).**

| UF | Óbitos | Taxa bruta | Taxa padronizada | Colo do útero (padr.) |
|---|---|---|---|---|
| RS | 61.599 | 182,9 | 152 | 3,62 |
| SC | 31.771 | 133,6 | 136,6 | 3,24 |
| PR | 48.928 | 138,7 | 135,1 | 3,25 |
| SP | 181.966 | 132,3 | 126,3 | 2,38 |
| MS | 9.493 | 110 | 122,6 | 3,33 |
| RJ | 70.060 | 135,7 | 120,6 | 3,13 |
| ES | 14.755 | 120,7 | 120,4 | 4,25 |
| RR | 1.441 | 69,1 | 118 | 7,18 |
| CE | 30.532 | 110,7 | 116 | 3,77 |
| AP | 1.625 | 67,8 | 114,2 | 6,18 |
| GO | 22.366 | 102,5 | 113,9 | 3,54 |
| DF | 8.707 | 97,8 | 113,8 | 3,7 |
| RN | 11.455 | 111,1 | 113,7 | 4,25 |
| AC | 1.922 | 73,1 | 113,1 | 8,59 |
| MG | 79.085 | 124,1 | 112,8 | 2,2 |
| PE | 30.104 | 105,5 | 111,8 | 4,44 |
| MT | 9.889 | 87,2 | 111,2 | 4,09 |
| AM | 8.949 | 70,3 | 110,7 | 9,55 |
| RO | 4.581 | 87,7 | 110,7 | 4,17 |
| PB | 13.484 | 109 | 109,3 | 3,16 |
| BA | 45.374 | 102 | 104,3 | 3,4 |
| SE | 6.210 | 90,7 | 102,7 | 3,72 |
| TO | 4.007 | 85,2 | 102,4 | 4,52 |
| AL | 8.154 | 84,4 | 97,7 | 4,97 |
| PI | 9.278 | 91,9 | 94,7 | 5,11 |
| PA | 17.573 | 68 | 92,7 | 6,03 |
| MA | 14.330 | 68,2 | 84,5 | 6,27 |

Padronizada por idade, a mortalidade por câncer vai de 152 por 100 mil no Rio Grande do Sul a 84,5 no Maranhão. As três maiores taxas do país são as dos três estados do Sul.

Ninguém sustentaria que se adoece 80% menos de câncer no Maranhão do que no Rio Grande do Sul. A coluna seguinte da mesma tabela mostra por quê, e mostra invertendo o mapa: a mortalidade padronizada por câncer de colo do útero vai de 9,55 no Amazonas a 2,2 em Minas Gerais, com Acre, Roraima, Maranhão e Pará entre as cinco maiores. Duas colunas da mesma tabela, sobre a mesma população e com a mesma padronização, ordenam as unidades da federação em sentidos aproximadamente opostos.

(A taxa de colo do útero está calculada sobre a população total, e não apenas a feminina, porque o denominador por unidade da federação não tem grão de sexo. Ela serve para comparar unidades entre si, não como taxa de mortalidade feminina.)

### 3.7 O gradiente municipal, e o que sobrevive à correção

**Tabela 9. Mortalidade por câncer e qualidade do registro por quartil de vulnerabilidade social, 2022–2024 (`tabela_9_vulnerabilidade.csv`).**

| Quartil | Óbitos por câncer | Taxa padronizada | Taxa corrigida | % causa mal definida | % dos óbitos por câncer |
|---|---|---|---|---|---|
| Q1 (menos vulnerável) | 511.966 | 127,3 | 132,8 | 4,09 | 17,8 |
| Q2 | 106.157 | 114,8 | 121,7 | 5,58 | 15,2 |
| Q3 | 71.390 | 102,1 | 109,2 | 6,39 | 13,9 |
| Q4 (mais vulnerável) | 58.054 | 91,5 | 98,6 | 7,24 | 12,9 |

A mortalidade padronizada por câncer é de 127,3 por 100 mil no quartil menos vulnerável e 91,5 no mais vulnerável — 39% mais alta onde há menos vulnerabilidade social. Na mesma tabela, e no sentido oposto, a fração de óbitos por causa mal definida vai de 4,09% a 7,24%, e a fração dos óbitos totais atribuída a câncer, de 17,8% a 12,9%.

A correção por redistribuição das causas mal definidas move os quatro valores para cima — 132,8 no primeiro quartil e 98,6 no quarto — e **preserva o gradiente**. Sob a suposição mais favorável possível à hipótese de subdiagnóstico, portanto, a diferença encolhe de 39% para 35% e não desaparece.

Se a diferença remanescente fosse detecção, ela deveria ser aproximadamente uniforme entre os tipos de tumor. Não é.

**Tabela 10. Razão entre as taxas padronizadas do quartil mais vulnerável e do menos vulnerável, por sítio, 2022–2024 (`tabela_10_sitio_por_vulnerabilidade.csv`).**

| CID | Sítio | Óbitos | Taxa Q1 | Taxa Q4 | Razão Q4/Q1 |
|---|---|---|---|---|---|
| C44 | Outras neoplasias malignas da pele | 10.692 | 1,54 | 2,18 | 1,42 |
| C53 | Colo do útero | 21.682 | 3,2 | 4,07 | 1,27 |
| C76 | Outras localizações e mal definidas | 16.159 | 2,35 | 2,88 | 1,22 |
| C15 | Esôfago | 25.733 | 3,83 | 4,01 | 1,05 |
| C61 | Próstata | 51.507 | 7,92 | 8,23 | 1,04 |
| C16 | Estômago | 44.076 | 7 | 7,17 | 1,03 |
| C32 | Laringe | 14.001 | 2,23 | 2,07 | 0,93 |
| C22 | Fígado e vias biliares intra-hepáticas | 33.497 | 5,57 | 4,54 | 0,81 |
| C71 | Encéfalo | 26.190 | 4,41 | 3,14 | 0,71 |
| C26 | Outros órgãos digestivos e mal definidos | 13.130 | 2,14 | 1,48 | 0,69 |
| C34 | Brônquios e pulmões | 93.089 | 16,09 | 10,54 | 0,65 |
| C24 | Outras partes das vias biliares | 8.656 | 1,54 | 0,98 | 0,64 |
| C56 | Ovário | 13.226 | 2,4 | 1,39 | 0,58 |
| C92 | Leucemia mieloide | 11.495 | 2,07 | 1,2 | 0,58 |
| C80 | Sem especificação de localização | 17.248 | 3,02 | 1,73 | 0,57 |
| C50 | Mama | 60.886 | 11,07 | 5,85 | 0,53 |
| C90 | Mieloma múltiplo | 11.845 | 2,18 | 1,08 | 0,5 |
| C25 | Pâncreas | 40.531 | 7,51 | 3,69 | 0,49 |
| C64 | Rim | 12.775 | 2,38 | 1,15 | 0,48 |
| C67 | Bexiga | 15.854 | 2,91 | 1,35 | 0,46 |
| C20 | Reto | 18.340 | 3,4 | 1,53 | 0,45 |
| C85 | Linfoma não-Hodgkin | 9.172 | 1,71 | 0,76 | 0,45 |
| C18 | Cólon | 46.490 | 9,09 | 2,97 | 0,33 |

Dos 23 sítios com pelo menos 8 mil óbitos no período, **seis matam mais no quartil vulnerável** — e são os mesmos seis antes e depois da troca de denominador descrita na §2.3. O primeiro é uma categoria de pele (C44, razão 1,42); o segundo é o **colo do útero**, com razão 1,27. Esôfago, próstata e estômago aparecem próximos da unidade. No extremo oposto, o cólon tem razão 0,33, a mama 0,53 e o pâncreas 0,49 — os tumores cuja detecção depende mais diretamente de colonoscopia, mamografia e imagem de alta complexidade.

Duas linhas dessa tabela não são doença e sim codificação, e apontam em sentidos contrários: "outras localizações e mal definidas" (C76) tem razão 1,22, enquanto "sem especificação de localização" (C80) tem 0,57. Se o quartil vulnerável simplesmente codificasse pior, as duas subiriam juntas. Elas divergem, o que sugere práticas de codificação **distintas** — categorias residuais diferentes, escolhidas por serviços diferentes — e não apenas piores.

### 3.8 Cor e raça

**Tabela 11. Taxa de mortalidade por câncer por cor ou raça, 2022–2023 (`tabela_11_raca.csv`).**

| Cor ou raça | Óbitos | Taxa bruta | Taxa padronizada | IC95% |
|---|---|---|---|---|
| Branca | 271.405 | 153,8 | 132,7 | 132,2–133,2 |
| Amarela | 3.197 | 188 | 107,3 | 103,4–111,4 |
| Parda | 164.647 | 89,4 | 104,7 | 104,2–105,3 |
| Preta | 40.313 | 97,6 | 98,3 | 97,4–99,3 |
| Indígena | 944 | 38,4 | 58,5 | 54,8–62,5 |

O padrão do recorte municipal reaparece no recorte individual, e com a mesma direção contraintuitiva: a taxa padronizada é de 132,7 por 100 mil entre pessoas brancas, 107,3 entre amarelas, 104,7 entre pardas, 98,3 entre pretas e 58,5 entre indígenas.

Duas dessas linhas exigem cautela que as outras não exigem. A taxa do grupo amarelo repousa em 3.197 óbitos e tem intervalo de 103,4 a 111,4, largo o bastante para não sustentar ordenação fina contra o grupo pardo. E a taxa do grupo indígena, a mais baixa da tabela, é também a que menos se pode ler como risco: a subnotificação de óbitos indígenas no SIM é documentada, e opera **no numerador** — a taxa observada é um piso, não uma estimativa. Voltaremos a isso em §4.4, e ela importa porque o achado seguinte vai na direção oposta.

O agregado esconde inversões.

**Tabela 12. Taxa padronizada por sítio e cor ou raça, 2022–2023, por 100 mil habitantes (`tabela_12_sitio_por_raca.csv`).**

| Sítio | Cor ou raça | Óbitos | Taxa padronizada | IC95% |
|---|---|---|---|---|
| Colo do útero (C53) | Indígena | 87 | 10,54 | 8,42–13,06 |
| Colo do útero (C53) | Parda | 6.793 | 8 | 7,81–8,19 |
| Colo do útero (C53) | Preta | 1.224 | 5,82 | 5,49–6,16 |
| Colo do útero (C53) | Branca | 5.741 | 5,73 | 5,58–5,88 |
| Colo do útero (C53) | Amarela | 64 | 5,26 | 3,99–6,99 |
| Mama (C50) | Branca | 22.306 | 21,31 | 21,03–21,60 |
| Mama (C50) | Preta | 3.398 | 16,4 | 15,85–16,96 |
| Mama (C50) | Amarela | 217 | 16,14 | 13,94–18,77 |
| Mama (C50) | Parda | 12.680 | 15,35 | 15,09–15,63 |
| Mama (C50) | Indígena | 49 | 6,18 | 4,56–8,21 |
| Próstata (C61) | Preta | 3.898 | 19,82 | 19,20–20,46 |
| Próstata (C61) | Parda | 12.196 | 16,57 | 16,28–16,87 |
| Próstata (C61) | Branca | 16.739 | 16,54 | 16,29–16,79 |
| Próstata (C61) | Amarela | 199 | 10,5 | 9,04–12,37 |
| Próstata (C61) | Indígena | 68 | 9,16 | 7,11–11,63 |
| Estômago (C16) | Amarela | 246 | 7,74 | 6,74–8,94 |
| Estômago (C16) | Parda | 11.616 | 7,41 | 7,27–7,55 |
| Estômago (C16) | Preta | 2.820 | 6,88 | 6,62–7,14 |
| Estômago (C16) | Branca | 13.905 | 6,79 | 6,68–6,91 |
| Estômago (C16) | Indígena | 79 | 5,09 | 4,02–6,36 |
| Cólon (C18) | Amarela | 305 | 9,96 | 8,81–11,32 |
| Cólon (C18) | Branca | 18.904 | 9,18 | 9,05–9,31 |
| Cólon (C18) | Parda | 8.005 | 5,12 | 5,01–5,24 |
| Cólon (C18) | Preta | 2.061 | 5,02 | 4,81–5,25 |
| Cólon (C18) | Indígena | 28 | 1,85 | 1,22–2,68 |

O câncer de colo do útero mata 10,54 por 100 mil entre mulheres indígenas (IC95% 8,42–13,06) e 5,73 entre brancas (5,58–5,88) — o único dos cinco sítios examinados em que o grupo branco não está entre os dois primeiros, e uma diferença cujos intervalos não se tocam apesar de a estimativa indígena repousar em 87 óbitos. O câncer de próstata mata 19,82 entre homens pretos (19,20–20,46) contra 16,54 entre brancos (16,29–16,79), também sem sobreposição. Já o cólon é o sítio mais desigual da tabela e o mais claramente ordenado por acesso: 9,18 entre brancas e brancos contra 1,85 entre indígenas — este último apoiado em 28 óbitos, com intervalo de 1,22 a 2,68, largo em termos relativos e ainda assim distante de qualquer outro grupo.

O contraste entre os dois achados indígenas é o ponto. **A mesma população, na mesma base e no mesmo biênio, tem a menor mortalidade por cólon e a maior por colo do útero.** Subnotificação de óbito não produz esse padrão: ela deprimiria os dois. O que produz é uma diferença de acesso específica ao tipo de tumor — e, no caso do colo do útero, a subnotificação torna o achado conservador, porque o valor verdadeiro só pode ser maior que o observado.

Mama e cólon seguem o gradiente do agregado; colo do útero e próstata o desobedecem. São exatamente os dois sítios cuja mortalidade a literatura associa, respectivamente, à ausência de rastreamento e ao diagnóstico tardio em populações com menor acesso.

### 3.9 Escolaridade, e onde se morre

**Tabela 13. Óbitos de 30 a 69 anos por escolaridade, 2022–2023 (`tabela_13_escolaridade.csv`).**

| Escolaridade | Óbitos (todas as causas) | % por câncer | % causa mal definida | % em hospital | % em domicílio |
|---|---|---|---|---|---|
| Sem escolaridade | 109.249 | 15,6 | 6,54 | 71 | 22,4 |
| Fundamental I | 328.245 | 20,3 | 5,3 | 78,7 | 15 |
| Fundamental II | 241.850 | 19,5 | 4,96 | 82,1 | 11,9 |
| Médio | 237.819 | 24,2 | 4,5 | 85,3 | 9,7 |
| Superior incompleto | 17.024 | 27,1 | 4,59 | 87,7 | 8,6 |
| Superior completo | 74.698 | 33,2 | 4,09 | 87,6 | 9,5 |
| Ignorado | 173.590 | 18 | 6,9 | 82 | 11,7 |

Entre os brasileiros de 30 a 69 anos que morreram no biênio, o câncer foi a causa básica de 15,6% das mortes de quem não tinha escolaridade e de 33,2% das de quem tinha superior completo. A leitura direta — mais câncer entre os instruídos — é inválida: mortalidade proporcional é uma divisão, e quem tem mais escolaridade morre menos de todas as outras causas, o que faz a fração do câncer subir sem que o risco de câncer suba. Na mesma tabela, a fração de causa mal definida vai de 6,54% a 4,09% no sentido inverso, de modo que parte da diferença é câncer que, na base da distribuição de escolaridade, não chega a ser nomeado.

A última coluna, essa sim, não depende de denominador nenhum e não admite leitura ambígua: entre os que morreram de câncer, morreram **em casa** 22,4% dos sem escolaridade e 9,5% dos com superior completo. A fração que morreu em hospital vai de 71% a 87,6% no sentido oposto.

**Tabela 14. Cor ou raça, local do óbito e qualidade do registro, 30 a 69 anos, 2022–2023 (`tabela_14_raca_acesso.csv`).**

| Cor ou raça | Óbitos por câncer | % por câncer | % em hospital | % em domicílio | % causa mal definida | % C80 entre os cânceres |
|---|---|---|---|---|---|---|
| Branca | 126.570 | 24,6 | 83,3 | 11,5 | 4,47 | 2,19 |
| Parda | 93.722 | 18,2 | 80 | 14,2 | 5,8 | 2,28 |
| Preta | 22.922 | 18,4 | 80,5 | 12,4 | 6,75 | 2,6 |
| Ignorado | 4.182 | 22,4 | 81,8 | 11,4 | 6,23 | 2,13 |
| Amarela | 1.156 | 24,5 | 83,5 | 11,8 | 4,96 | 1,9 |
| Indígena | 504 | 13,9 | 73,6 | 20 | 7,56 | 2,78 |

O mesmo gradiente aparece por cor/raça, mais estreito: 83,3% de morte hospitalar entre pessoas brancas e 73,6% entre indígenas, com 20% de morte domiciliar neste último grupo. A fração de causa mal definida acompanha — 4,47% entre brancas e brancos, 7,56% entre indígenas.

**Tabela 15. Local de ocorrência do óbito por câncer, por faixa etária, 2022–2023 (`tabela_15_local_obito.csv`).**

| Faixa etária | Óbitos por câncer | % em hospital | % em domicílio | % em outros locais |
|---|---|---|---|---|
| 0 a 4 | 1.138 | 95,5 | 2,6 | 1,8 |
| 5 a 14 | 2.084 | 93,9 | 4,1 | 2,1 |
| 15 a 29 | 6.797 | 90,2 | 6,2 | 3,6 |
| 30 a 44 | 28.263 | 86,2 | 9,4 | 4,4 |
| 45 a 59 | 95.259 | 82,4 | 12,1 | 5,5 |
| 60 a 74 | 192.439 | 79,6 | 14,4 | 6 |
| 75 ou mais | 162.555 | 72,3 | 21,5 | 6,2 |

A morte domiciliar cresce monotonicamente com a idade, de 2,6% na primeira infância a 21,5% entre os maiores de 74 anos. O dado registra o **local**, não a intenção: cuidado paliativo domiciliar planejado e ausência de acesso a leito produzem o mesmo código, e as duas coisas convivem dentro desse número. É a razão pela qual a Tabela 15 é apresentada como descrição e não como indicador de qualidade assistencial.

---

## 4. Discussão

### 4.1 O aumento que não é aumento

O resultado central deste trabalho é aritmético e não é novo em epidemiologia; é, no entanto, sistematicamente perdido na comunicação pública. As mortes por câncer no Brasil aumentaram um quarto em dez anos e o risco de morrer de câncer diminuiu. As duas afirmações são verdadeiras simultaneamente porque a população brasileira envelheceu no intervalo, e a decomposição da Tabela 4 mostra que os termos demográficos explicam mais que a totalidade do aumento.

A consequência prática é de planejamento, não de retórica. Um sistema de saúde que precisa dimensionar oncologia enfrenta o número absoluto: são 53 mil mortes por ano a mais que em 2015, com a demanda por diagnóstico, tratamento e cuidado paliativo que isso implica, e essa demanda continuará crescendo mesmo que o risco individual continue caindo. Um sistema que precisa avaliar se sua política de prevenção funciona precisa da taxa padronizada, e ela diz outra coisa.

### 4.2 O gradiente invertido, e por que ele não é uma boa notícia

Municípios menos vulneráveis registram mais mortes por câncer. Pessoas brancas morrem mais de câncer, por 100 mil, que pessoas pretas e pardas. Os dois achados têm a mesma forma e provavelmente as mesmas causas, e nenhuma delas é "menos câncer entre os pobres".

Três mecanismos concorrem. O primeiro é **detecção**: câncer que não é diagnosticado não é codificado como câncer, e os quartis vulneráveis têm quase o dobro da fração de causas mal definidas. A análise de sensibilidade da Tabela 9 limita esse mecanismo, sem eliminá-lo: redistribuir todas as causas mal definidas encolhe o gradiente e o mantém. O segundo é **risco competitivo**: câncer é doença de idade avançada, e populações que morrem antes de outras causas têm menos oportunidade de morrer de câncer — mecanismo que a padronização por idade atenua, porque compara faixas com faixas, mas não elimina, porque opera *dentro* de cada faixa. O terceiro é **exposição diferencial** genuína, de sinal variável por sítio: tabagismo, dieta, obesidade e reprodução distribuem-se de modo desigual e não na mesma direção.

O que permite avançar sobre essa mistura, sem dado individual de incidência, é o comportamento sítio a sítio. Um efeito puro de detecção produziria gradiente aproximadamente uniforme; o que se observa na Tabela 10 é uma dispersão de razões entre 0,33 e 1,42, com significado clínico legível: os sítios que dependem de exame de rastreamento ou imagem de alta complexidade (cólon, mama, pâncreas, rim, bexiga, reto) concentram-se abaixo de 1, e os que se manifestam clinicamente sem depender de programa organizado de detecção concentram-se perto ou acima de 1.

### 4.3 O colo do útero como indicador de equidade

Entre todos os sítios examinados, o do colo do útero é o que se comporta de maneira mais consistente com desigualdade de acesso, e ele o faz nos três recortes independentes deste trabalho: entre unidades da federação (9,55 no Amazonas contra 2,2 em Minas Gerais, Tabela 8), entre quartis de vulnerabilidade municipal (razão 1,27, Tabela 10) e entre grupos de cor/raça (10,54 entre indígenas contra 5,73 entre brancas, Tabela 12). Os três recortes usam populações diferentes, denominadores diferentes e níveis de agregação diferentes, e apontam na mesma direção.

A coerência importa porque o colo do útero é um caso quase experimental dentro da oncologia: tem etiologia infecciosa estabelecida, vacina disponível, história natural longa o bastante para que a detecção precoce mude o desfecho, e é o único tumor para o qual a Organização Mundial da Saúde definiu uma **meta de eliminação** — incidência abaixo de 4 casos por 100 mil mulheres ao ano, sustentada pelas metas 90–70–90 de vacinação, rastreamento e tratamento até 2030 [3]. Mortalidade elevada por câncer de colo do útero mede, com pouca ambiguidade, ausência de programa alcançando aquela população — e não maior ocorrência da doença por acaso geográfico. É, por isso, o candidato natural a indicador-síntese de equidade oncológica no Brasil, papel que a mortalidade total por câncer não pode cumprir pelas razões da seção anterior.

O achado tem validação externa por uma via independente. A Estimativa de Incidência de Câncer no Brasil para 2023–2025 [4], construída a partir dos Registros de Câncer de Base Populacional e não do SIM, aponta a Região Norte como a de maior incidência de câncer do colo do útero e o registra como **o tumor mais incidente** no Amazonas e no Amapá. Duas bases que não compartilham numerador, denominador nem método concordam em qual unidade da federação está no topo. É a concordância que se esperaria se o sinal fosse doença, e não artefato de codificação do SIM.

O achado da Tabela 3 — aumento do risco justamente nas faixas de 15 a 29 e de 30 a 44 anos — merece leitura conjunta com este, ainda que o presente desenho não estabeleça a ligação. São as faixas em que mama e colo do útero mais pesam — entre 30 e 44 anos eles são os dois primeiros sítios, com quase 30% dos óbitos por câncer da faixa (Tabela 6) —, e são as únicas em que o risco subiu na década.

O sentido do achado é o mesmo de uma tendência internacional já descrita: a análise do Global Burden of Disease para 204 países registra aumento de 79% nos casos de câncer em pessoas de 14 a 49 anos entre 1990 e 2019, com a mama respondendo pelo maior número de casos e óbitos da faixa [6]. O dado brasileiro aqui é de mortalidade e não de incidência, e a magnitude não é comparável; o que se pode dizer é que o Brasil não constitui exceção ao padrão, e que a faixa em que ele aparece é a mesma.

### 4.4 O que a mortalidade não pode dizer

A limitação central deste trabalho não é de método e sim de fonte. Mortalidade não é incidência, e nenhuma quantidade de padronização separa "menos doença" de "menos diagnóstico" ou de "mais sobrevida". A separação exigiria registros de câncer de base populacional com cobertura nacional, que o Brasil tem apenas parcialmente, ou vinculação entre o SIM e as bases de tratamento oncológico, que este trabalho não faz.

Seis limitações menores, quase todas com direção conhecida:

- **Cor/raça tem viés numerador-denominador.** No SIM o campo é declarado por terceiro — familiar ou serviço de saúde —, e no Censo é autodeclarado; as duas fontes não classificam necessariamente a mesma pessoa do mesmo modo, e a razão entre elas carrega esse erro. Não há fatores de correção por cor/raça disponíveis para o Brasil, e a literatura documenta tanto a incompletude do campo quanto o efeito de mudanças no seu registro sobre indicadores de desigualdade [5]. A direção esperada — subdeclaração de pretos, pardos e indígenas no óbito — **atenuaria** as taxas desses grupos, tornando conservadores os achados de colo do útero e de próstata, que apontam no sentido contrário. É o mesmo argumento de §3.7: um viés que deprime todas as causas de um grupo não explica um grupo com a menor taxa num sítio e a maior noutro.
- **As faixas largas sobrevivem nos eixos sociais.** A série nacional, o recorte por unidade da federação e a mortalidade prematura da §3.2 usam grupos quinquenais, porque o denominador tem idade simples. Os eixos de cor/raça e de vulnerabilidade municipal continuam em sete faixas, três delas de quinze anos e a última aberta em 75, porque as fontes que dão o recorte social — o Censo por cor/raça e a população municipal — não têm grão mais fino. Grupos com longevidades diferentes têm idades médias diferentes *dentro* de 75 ou mais, e a padronização não remove essa parcela do confundimento. O efeito favorece o grupo mais longevo — o branco —, o que reforça, e não explica, o gradiente invertido do agregado.
- **O intervalo de Fay & Feuer é conservador.** Ele garante cobertura de pelo menos 95%, mas é mais largo que o necessário em contagens pequenas; a modificação de Tiwari, Clegg e Zou [7], adotada pelo SEER a partir de 2006, tem cobertura mais eficiente. Como as conclusões deste artigo se apoiam em intervalos que **não** se sobrepõem, o intervalo mais largo é a escolha conservadora, e trocá-lo só os estreitaria.
- **A composição municipal é censitária; só o nível é anual.** A população municipal por faixa etária só existe no ano do Censo. Ela é escalada, ano a ano, pelo fator da sua unidade da federação na projeção revisão 2024 (§2.3), de modo que o patamar acompanha a série oficial — mas a *forma* etária de cada município continua sendo a de 2022. Municípios que envelheceram mais rápido que a média da sua unidade da federação ficam com denominador ligeiramente jovem demais, e o efeito não tem direção conhecida entre quartis.
- **O eixo social cobre dois anos.** Não há série histórica de cor/raça e escolaridade neste recorte, e portanto nada aqui sustenta afirmação sobre tendência de desigualdade — apenas sobre o seu nível em 2022–2023.
- **A projeção é projeção.** O denominador adotado é a série oficial, mas continua sendo um modelo demográfico: 2015 a 2021 são retroprojeção reconciliada, não contagem. A alternativa seria a contagem censitária, que existe para um ano só e, usada como série, produz o artefato da última linha da Tabela 17.

---

## 5. Conclusão

O aumento das mortes por câncer no Brasil entre 2015 e 2024 é inteiramente atribuível ao crescimento e ao envelhecimento da população; o risco de morrer de câncer, ajustado por idade, caiu. Comunicar o número absoluto como avanço da doença é comunicar a demografia brasileira com nome errado.

O gradiente social da mortalidade por câncer registrada aparece invertido em relação à expectativa — mais mortes onde há menos vulnerabilidade — e a inversão é, em boa parte, artefato de detecção e de risco competitivo, não epidemiologia. O que atravessa essa camada são os sítios que não dependem de programa de detecção para se manifestar, e sobretudo o colo do útero, que inverte o gradiente nos três recortes independentes examinados. Uma política de equidade oncológica avaliada pela mortalidade total por câncer estaria medindo, em parte, o próprio acesso ao diagnóstico que pretende corrigir; avaliada pela mortalidade por colo do útero, mede o que se propõe a medir.

---

## 6. Referências

1. Fay MP, Feuer EJ. Confidence intervals for directly standardized rates: a method based on the gamma distribution. *Statistics in Medicine*. 1997;16(7):791–801.
2. Das Gupta P. *Standardization and Decomposition of Rates: A User's Manual*. Washington: U.S. Bureau of the Census; 1993. (Current Population Reports, Series P-23, No. 186.)
3. World Health Organization. *Global strategy to accelerate the elimination of cervical cancer as a public health problem*. Genebra: OMS; 2020. ISBN 978-92-4-001410-7.
4. Instituto Nacional de Câncer. *Estimativa 2023: incidência de câncer no Brasil*. Rio de Janeiro: INCA; 2022.
5. Caldas ADR, Santos RV, Cardoso AM. Iniquidades étnico-raciais na mortalidade infantil: implicações de mudanças do registro de cor/raça nos sistemas nacionais de informação em saúde no Brasil. *Cadernos de Saúde Pública*. 2022;38(4):e00101721. doi:10.1590/0102-311X00101721.
6. Zhao J, Xu L, Sun J, Song M, Wang L, Yuan S, et al. Global trends in incidence, death, burden and risk factors of early-onset cancer from 1990 to 2019. *BMJ Oncology*. 2023;2:e000049. doi:10.1136/bmjonc-2023-000049.
7. Tiwari RC, Clegg LX, Zou Z. Efficient interval estimation for age-adjusted cancer rates. *Statistical Methods in Medical Research*. 2006;15(6):547–569.
8. Instituto Brasileiro de Geografia e Estatística. *Projeções da população: Brasil e unidades da federação — revisão 2024*. Rio de Janeiro: IBGE; 2024. (Série Relatórios Metodológicos, v. 40, 3ª ed.)
9. Ahmad OB, Boschi-Pinto C, Lopez AD, Murray CJL, Lozano R, Inoue M. *Age standardization of rates: a new WHO standard*. Genebra: Organização Mundial da Saúde; 2001. (GPE Discussion Paper Series, n. 31.)

---

## 7. Disponibilidade de dados e código

Todas as fontes são de domínio público. Os microdados do Sistema de Informações sobre Mortalidade são distribuídos pelo DataSUS e pelo OpenDataSUS; os denominadores populacionais e a tabela 9606 do Censo 2022, pelo IBGE via SIDRA. Nenhum dado individual é publicado — apenas agregados.

Os cálculos deste artigo são reproduzidos por dois scripts abertos:

- `scripts/pipeline_projecao_ibge.py` — coleta e valida a Projeção da População do IBGE, revisão 2024, por idade simples, e grava `data/refs/pop_proj2024_uf_ano_idade.parquet`;
- `scripts/analise_neoplasias.py` — produz as dezessete tabelas de análise em `data/analises/neoplasias/`, a partir do SIM cru com idade exata, do denominador oficial e do SIDRA;
- `artigo-neoplasias/gerar_tabelas.py` — executa o anterior e formata as dezessete tabelas deste manuscrito em `artigo-neoplasias/tabelas/`.

Nenhum número deste texto é digitado: cada valor citado existe em um dos CSVs de `artigo-neoplasias/tabelas/`, e as tabelas do manuscrito são regeradas a partir deles por `artigo/sincronizar_tabelas.py --dir artigo-neoplasias`, com regressão em `tests/test_manuscrito.py`. Um número no texto que não esteja em nenhum CSV é um número sem procedência.

---

## 8. Apêndice — o estudo sob os quatro denominadores

**Tabela 17. Taxa padronizada de mortalidade por câncer sob cada série populacional candidata (`tabela_17_sensibilidade.csv`).**

| Série populacional | População em 2022 | Taxa padronizada 2015 | Taxa padronizada 2024 | Variação (%) |
|---|---|---|---|---|
| Projeção rev. 2024 (adotada) | 210.862.983 | 123,04 | 120,18 | -2,3 |
| Projeção rev. 2018 (anterior) | 214.828.540 | 122,55 | 117,17 | -4,4 |
| Reconciliada interna | 203.080.756 | 127,33 | 124,12 | -2,5 |
| Censo 2022 (contagem bruta) | 203.080.756 | 101,44 | 127,58 | 25,8 |

A tabela existe porque a §2.3 afirma que a troca de denominador não inverteu nenhum achado, e afirmação dessas tem de ser verificável. As três primeiras linhas são séries anuais e concordam: a taxa padronizada cai, entre 2,3% e 4,4%. A quarta é a contagem censitária replicada em todos os anos, e serve de controle negativo — sem variação no denominador, a "padronizada" apenas reproduz a bruta e sobe 25,8%.

Está numerada depois das tabelas de resultado, e não antes, para não renumerar as dezesseis que a prosa já citava. É troca deliberada entre ordem de leitura e estabilidade das referências.

---

## 9. Notas sobre o que ainda não foi feito

Itens conhecidos e não resolvidos, listados para que não sejam confundidos com decisões:

- **~~a faixa etária é grossa demais para o indicador da OMS~~ — resolvido na segunda versão.** A projeção revisão 2024 traz idade simples, e o indicador de mortalidade prematura de 30 a 69 anos passou a existir (§3.2, Tabela 16). Fica o resíduo descrito em §4.4: os eixos de cor/raça e de vulnerabilidade municipal continuam em sete faixas, porque as fontes que dão o recorte social não têm grão mais fino;
- **cor/raça e escolaridade não têm série.** Os campos existem no microdado nacional de 2022–2023 e não no recorte de colunas dos demais anos em disco. Baixar o arquivo completo para 2015–2021 e 2024 é operação de coleta, não de análise, e daria série de dez anos para os dois eixos sociais — inclusive para testar se a desigualdade por sítio se estreitou ou se ampliou;
- **a razão mortalidade/incidência não foi calculada.** É o indicador que separaria detecção de letalidade, e exige os Registros de Câncer de Base Populacional do INCA, que cobrem parte das capitais. Para as capitais cobertas, o cruzamento é viável e mudaria a força da §4.2 de argumento indireto para medida direta;
- **a redistribuição das causas mal definidas é pro-rata, e há métodos melhores.** A redistribuição proporcional supõe que os óbitos sem diagnóstico se distribuem como os diagnosticados, o que é conhecidamente conservador para câncer. Métodos de redistribuição baseados em padrões de codificação por idade e sexo dariam correção mais realista, e provavelmente **aumentariam** a taxa corrigida dos quartis vulneráveis mais do que a correção adotada;
- **a diferença entre versões do mesmo ano mediria capacidade de investigação póstuma.** A conversão de causa mal definida em diagnóstico específico entre a versão preliminar e a consolidada do mesmo ano é um instrumento direto para o mecanismo discutido na §4.2, e exige guardar as duas versões de cada ano — prática que o projeto adotou, mas não retroativamente;
- **a comparação com incidência ainda é indireta, e agora dá para tentá-la.** Com a coluna do padrão mundial (Tabela 2) a série deste artigo passou a ser comparável com as publicações do INCA e da IARC. Confrontar a taxa de mortalidade padronizada pelo padrão mundial com a incidência estimada, unidade da federação por unidade da federação, dá uma razão mortalidade/incidência aproximada — inferior ao cálculo com os registros de base populacional, mas disponível hoje e suficiente para ordenar as unidades por letalidade aparente;
- o sítio C44 ("outras neoplasias malignas da pele") lidera a Tabela 10 e não é discutido no texto: a categoria mistura carcinomas de baixa letalidade com tumores agressivos, e sua mortalidade elevada em municípios vulneráveis merece exame próprio, com desagregação que a categoria de três caracteres não permite.
