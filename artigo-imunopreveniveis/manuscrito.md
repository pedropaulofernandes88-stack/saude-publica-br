# Óbitos por doenças imunopreveníveis no Brasil, 2015–2024: perda de sensibilidade de um instrumento oficial por delimitação etária, defasagem tecnológica e especificidade etiológica do registro

**Pedro Paulo Fernandes**¹

¹ Saúde em Dado — saudeemdado.com · ORCID e afiliação a completar

*Coautoria a definir. Este é um rascunho de trabalho preparado a partir do levantamento executado em 2026-09-03.*

---

## Resumo

**Contexto.** A Lista Brasileira de Causas de Mortes Evitáveis é o instrumento oficial do Ministério da Saúde para classificar óbitos evitáveis por intervenção do SUS, e o seu subgrupo 1.1 reúne as causas "reduzíveis pelas ações de imunoprevenção". A lista foi publicada em 2007 e revista pela última vez entre 2010 e 2011. Desde então o Programa Nacional de Imunizações incorporou rotavírus, meningocócica C e ACWY, pneumocócica conjugada, varicela, HPV e, sobretudo, as vacinas contra a COVID-19.

**Objetivo.** Medir quantos óbitos o subgrupo 1.1 identifica no Brasil entre 2015 e 2024; comparar esse total com o conjunto de óbitos por doenças que têm vacina disponível no país; e caracterizar as razões estruturais da diferença.

**Métodos.** Todos os óbitos não fetais registrados no Sistema de Informações sobre Mortalidade entre 2015 e 2024, com a causa básica preservada em quatro caracteres da CID-10 — grão exigido pela própria lista oficial, que nomeia G00.0, P35.0 e P35.3, e pelo código que o Brasil usa para COVID-19, B34.2. O subgrupo 1.1 foi transcrito literalmente das notas técnicas do TabNet/DataSUS, nas suas duas versões etárias, e aplicado com a idade que cada versão determina. Um conjunto ampliado reúne, além dele, as demais doenças com vacina disponível no país, cada uma anotada com o ano de entrada no PNI; um terceiro grupo, de latência longa, é reportado à parte e nunca somado. Um cruzamento ecológico entre óbitos por influenza em 60 anos ou mais e doses de influenza por habitante dessa faixa, por unidade da federação, teve o critério de nulidade declarado antes da análise.

**Resultados.** Em 14.484.496 óbitos, o subgrupo 1.1 identifica 5.832 — 4,03 por 10 mil óbitos, sem tendência na década (Tabela 3). O conjunto ampliado sem COVID-19 — que é um **teto**, não uma estimativa de mortes evitáveis — soma 27.917 óbitos, razão de 4,79 sobre o instrumento oficial, e a COVID-19 sozinha soma 718.811 (Tabela 4). Três limitações estruturais explicam a diferença. A lista termina aos 74 anos, e 267.276 óbitos por causas com vacina — 35,8% do conjunto — ocorreram acima dessa idade, invisíveis por construção (Tabela 5). Ela antecede as vacinas incorporadas depois de 2010 e classifica influenza fora da imunoprevenção. E 3.189 dos 5.832 óbitos que ela conta são tuberculose miliar ou do sistema nervoso, dos quais 3.092 entre 5 e 74 anos — faixa em que a relação entre o óbito e a vacinação infantil é bem mais incerta do que a que a justificativa da lista invoca, ainda que a proteção conferida na infância possa persistir décadas [10]; excluída a tuberculose, restam 2.643 óbitos em dez anos (Tabela 6). O teto de medição é de codificação, não de epidemiologia: há 631.108 óbitos por pneumonia sem agente identificado (J18) contra 809 atribuídos ao pneumococo (J13), razão de 780,1 (Tabelas 12 e 13). O cruzamento ecológico deu nulo pelo critério declarado — correlação de Spearman +0,389 em 2023 e −0,056 em 2024 —, e a própria fonte explica parte disso: o PNI/RNDS registra 16.621.107 doses de influenza em 2023 contra 54.215.093 em 2024 (Tabela 15).

**Conclusões.** O instrumento oficial brasileiro de evitabilidade por imunoprevenção não está errado: está defasado, e de três formas que se somam. Ele descreve um calendário vacinal que não é mais o do país, ignora a faixa etária onde a mortalidade por doença imunoprevenível se concentra, e é dominado internamente por uma causa cuja evitabilidade por vacina não se sustenta na idade em que ela ocorre. Atualizá-lo é decisão de vigilância, não exercício estatístico. Independentemente disso, a ausência de investigação etiológica na declaração de óbito impõe um teto ao que qualquer lista consegue medir.

**Palavras-chave:** imunização; mortes evitáveis; sistemas de informação em saúde; classificação internacional de doenças; Programa Nacional de Imunizações; vigilância epidemiológica.

---

## 1. Introdução

Perguntar quantas pessoas morrem no Brasil de doenças que uma vacina previne parece uma pergunta de epidemiologia, e é em boa parte uma pergunta de instrumento. Existe uma resposta oficial: a Lista Brasileira de Causas de Mortes Evitáveis, construída por grupo de trabalho coordenado pelo Ministério da Saúde, publicada em 2007 [1], revista em 2010 [2] e, para a faixa de cinco a setenta e quatro anos, em 2011 [3], e distribuída como nota técnica do TabNet/DataSUS em duas versões etárias [4, 5] — menores de cinco anos e de cinco a setenta e quatro anos. O primeiro subgrupo de ambas reúne as causas "reduzíveis pelas ações de imunoprevenção". Ele é o que o Brasil usa quando precisa dizer, com respaldo institucional, que uma morte poderia ter sido evitada por vacina.

Entre a última revisão da lista e hoje, o Programa Nacional de Imunizações mudou. Entraram a vacina contra rotavírus, a meningocócica C e depois a ACWY, a pneumocócica 10-valente, a varicela, o HPV. E entrou, em janeiro de 2021, a vacinação contra a COVID-19, que é a maior campanha da história do programa e responde à doença que mais matou brasileiros no período coberto por este trabalho. Uma lista de evitabilidade cujo último ajuste é anterior a tudo isso não descreve o que o SUS oferece hoje.

**Duas ausências são de naturezas diferentes, e só uma é esperada.** A ausência da COVID-19 não é crítica ao instrumento: a vacina não existia quando a lista foi revista, e nenhuma classificação poderia tê-la previsto. Já a **pneumocócica conjugada** entrou no PNI em 2010 e a **meningocócica C** em 2010, ambas no intervalo da própria revisão — que foi publicada entre 2010 e 2011. A ausência dessas duas do subgrupo de imunoprevenção não se explica por defasagem temporal, e merece exame à parte.

A hipótese mais parcimoniosa, e a que os resultados deste trabalho sustentam, é que a ausência delas é consequência do problema de codificação e não de esquecimento: doença pneumocócica invasiva praticamente não aparece como causa básica no SIM — 809 óbitos em J13 contra 631.108 em J18 (§3.9) —, e uma causa que o registro não identifica não produz indicador utilizável, ainda que a vacina esteja no calendário. Se essa leitura estiver certa, ela reforça a conclusão central: o teto do instrumento é de investigação etiológica, não de escolha de códigos.

A questão não é retórica. Listas de evitabilidade são usadas para monitorar desempenho de sistema de saúde, para priorizar território e para avaliar programa. Um instrumento que enxerga uma fração pequena e estável da carga de doença imunoprevenível produz, ano após ano, a mesma leitura tranquilizadora — e a produz não porque a carga seja pequena, mas porque a régua é curta.

Este trabalho mede a distância entre a régua e o que ela deveria medir. A pergunta tem três partes:

- quantos óbitos o subgrupo 1.1 identifica no Brasil, e como esse número se comporta ao longo de uma década?
- quantos óbitos ocorreram, no mesmo período, por doenças para as quais existe vacina disponível no país?
- a diferença entre os dois números é epidemiologia, ou é propriedade do instrumento?

A terceira é a que organiza o texto, e responder a ela exige separar três coisas que se confundem com facilidade: a doença ter vacina, a vacina estar no calendário público, e a morte ter sido evitável. Este trabalho estabelece as duas primeiras com precisão e recusa a terceira. Contar óbitos por doenças com vacina disponível produz um **teto**; converter esse teto em mortes evitadas exigiria eficácia vacinal e situação vacinal individual, e o Sistema de Informações sobre Mortalidade não traz nenhuma das duas.

---

## 2. Métodos

### 2.1 Delineamento, fonte e definição de óbito

Estudo ecológico descritivo de série temporal, com unidade de análise o óbito registrado. A fonte são os microdados do Sistema de Informações sobre Mortalidade (SIM), obtidos por duas rotas do DataSUS: os arquivos por unidade da federação do FTP (`.dbc`) para 2015–2021, 2024 e 2025, e os arquivos nacionais do OpenDataSUS para 2022 e 2023 [7], que conferem exatamente com a rota do FTP nesses dois anos.

A definição de óbito não foi escrita para este trabalho. Ela é a de `scripts/_sim_obitos.py`, módulo compartilhado por todos os pipelines de mortalidade do repositório, e determina: exclusão de óbito fetal pelo campo `TIPOBITO`, decodificação do campo `IDADE` em anos completos, e município de residência preservado como `000000` quando ausente, para não desaparecer em junção. Compartilhar a definição em vez de reescrevê-la é decisão deliberada — duas cópias da mesma regra divergem em silêncio, e a divergência apareceria como um total de óbitos que não bate entre duas tabelas publicadas.

O ano de 2025 aparece nas tabelas marcado como preliminar e **não entra em nenhum total do texto**. Dado preliminar tem a cauda incompleta: os seus valores só crescem, o que os torna piso e não estimativa.

### 2.2 Por que quatro caracteres da CID-10

Os produtos publicados deste projeto trabalham com a causa básica truncada em três caracteres, o grão de categoria da CID-10. Aqui isso não serve, por três razões simultâneas:

- a própria lista oficial nomeia códigos de quatro caracteres — **G00.0** (meningite por *Haemophilus*), **P35.0** (síndrome da rubéola congênita) e **P35.3** (hepatite viral congênita) —, e truncá-los os confunde com as demais meningites bacterianas e com as demais infecções congênitas;
- o SIM brasileiro codifica COVID-19 como **B34.2**, e não como U07 da atualização da CID-10; truncada em três caracteres, a pandemia inteira vira "infecção viral não especificada";
- a septicemia pneumocócica é **A40.3**, indistinguível de A40 sem o quarto caractere.

A agregação foi refeita a partir do microdado preservando os quatro caracteres, mantendo intactas as demais regras de derivação.

### 2.3 O instrumento oficial

O subgrupo 1.1 foi transcrito literalmente das duas notas técnicas do TabNet/DataSUS [4, 5] (`Obitos_Evitaveis_0_a_4_anos.pdf` e `Obitos_Evitaveis_5_a_74_anos.pdf`), e não reconstruído de memória nem de artigo secundário. As notas implementam a lista de 2007 [1] com as revisões de 2010 [2] e 2011 [3]. As duas versões diferem em cinco códigos, todos preservados: a versão de menores de cinco anos inclui tétano neonatal (A33), caxumba (B26), síndrome da rubéola congênita (P35.0) e hepatite viral congênita (P35.3), e exclui tétano obstétrico (A34), que só aparece na versão de 5 a 74 anos (Tabela 2).

A aplicação respeita a idade que cada versão determina. Um óbito de menor de cinco anos é avaliado pela lista de menores de cinco; um óbito entre 5 e 74 anos, pela outra. **Óbitos com 75 anos ou mais não são avaliados por nenhuma lista**, porque nenhuma existe — o que é propriedade do instrumento e não recorte deste estudo, e cuja consequência quantitativa é medida na §3.3.

O limite superior é explícito na própria revisão que o fixou: o título de 2011 é "Atualização da lista de causas de mortes evitáveis (5 a 74 anos de idade) por intervenções do Sistema Único de Saúde do Brasil" [3]. Não é omissão da nota técnica nem convenção de tabulação — é a delimitação declarada do instrumento.

### 2.4 O conjunto ampliado e o critério de disponibilidade

O conjunto ampliado reúne, além dos códigos do subgrupo 1.1, as demais doenças para as quais existe vacina, com os códigos de causa básica que as identificam sem ambiguidade. **Ele é um teto, não uma estimativa de mortes evitáveis.** O que ele mede é a carga de óbitos por doenças para as quais existe vacina no país — grandeza que não desconta eficácia vacinal, não conhece a situação vacinal de quem morreu, e não verifica se a vacina era recomendada para aquela idade ou aquele território. Nenhum número do conjunto ampliado deve ser lido como o de mortes que teriam sido evitadas; todos devem ser lidos como o limite superior do que a vacinação poderia, no melhor caso, ter alcançado. Cada causa carrega um campo de **disponibilidade**, que registra desde quando a vacina existe na rede pública brasileira, e esse campo faz trabalho analítico, não decorativo: ele separa "a doença tem vacina" de "o SUS oferecia a vacina". O herpes zoster é o caso que obriga a distinção — tem vacina licenciada no Brasil, ela **não** está no PNI, e contar os seus óbitos como evitáveis pelo SUS seria falso. Por isso a Tabela 7 traz dois subtotais, com e sem ele.

A COVID-19 recebe tratamento próprio pelo mesmo motivo: a vacina passou a existir em janeiro de 2021, e nenhum óbito de 2020 poderia ter sido evitado por ela. Os totais do conjunto ampliado são sempre apresentados com e sem COVID-19.

**Quatro níveis de disponibilidade, e o que este trabalho consegue separar.** "Vacina disponível" não é um estado único. Ela se decompõe em pelo menos quatro condições, e elas não coincidem:

1. **licenciada** no país pela Anvisa;
2. **incorporada** ao SUS, isto é, ofertada pela rede pública;
3. **recomendada para aquela idade**, porque o calendário é etário e a maioria das vacinas tem janela;
4. **recomendada para aquele território**, porque parte das recomendações é geográfica.

O campo de disponibilidade deste trabalho separa com segurança os níveis 1 e 2 — é o que exclui o herpes zoster do núcleo do conjunto ampliado. Os níveis 3 e 4 **não** são aplicados óbito a óbito, e isso é uma limitação declarada, não um detalhe: um óbito por COVID-19 em 2021 numa faixa que só entrou na campanha meses depois conta no conjunto ampliado do mesmo modo que um óbito de quem já tinha a vacina à disposição.

A febre amarela é o caso que torna o nível 4 visível: a vacina existe desde 1937 e é de dose única, mas a recomendação era territorial, e os 452 óbitos de 2017–2018 ocorreram em municípios que só entraram na área com recomendação **depois** do surto (§3.6). Contá-los como "vacina disponível" é correto no nível 2 e falso no nível 4.

Os anos de entrada foram compilados do Calendário Nacional de Vacinação do Ministério da Saúde e do seu histórico [6]. Eles são anotação de contexto, não variável de análise: nenhum resultado deste artigo depende do ano exato, e a §4.4 registra que não foram auditados ato normativo a ato normativo.

### 2.5 O grupo de latência longa

Três causas com relação estabelecida com vacina ficam **fora de qualquer soma** e são reportadas à parte (Tabela 16): câncer de colo do útero (C53), câncer de fígado (C22) e hepatite B crônica e cirrose (B18.0–B18.1). O motivo é o intervalo entre a exposição evitável e a morte. A vacina contra HPV entrou no PNI em 2014 e a progressão da infecção ao carcinoma leva décadas: nenhuma morte por câncer de colo do útero registrada em 2024 poderia ter sido evitada por uma campanha de 2014, e somá-las inflaria o total com mortes que nenhuma política vacinal atual alcançaria. Para o fígado, some-se que a fração atribuível ao vírus da hepatite B não é separável na causa básica.

Estas três causas estão no artigo porque são o argumento mais forte a favor da vacinação de hoje, e porque omiti-las esconderia esse argumento. Elas não estão nos totais porque somá-las seria a forma mais fácil de tornar o número grande e errado.

### 2.6 O cruzamento ecológico e o critério declarado antes da análise

Para testar se a variação territorial da mortalidade por influenza guarda relação com a intensidade da vacinação, foram cruzados, por unidade da federação e para 2023 e 2024, os óbitos por influenza (J09–J11) em pessoas de 60 anos ou mais, os denominadores populacionais dessa faixa [9] e as doses de influenza (`INF3`) registradas no PNI/RNDS [8] (Tabela 14).

O critério de interpretação foi fixado **antes** de observar o resultado: correlação de Spearman com módulo inferior a 0,30, ou sinal diferente entre os dois anos, seria tratada como ausência de sinal — e ausência de sinal seria reportada como resultado, não como convite a procurar outro recorte. Declarar o critério antes é o que separa um achado nulo de uma busca por especificação que produza significância.

### 2.7 Guardas computacionais

Quatro verificações interrompem a execução, em vez de emitir aviso, porque cada uma invalida um número do texto em vez de apenas torná-lo impreciso:

- **aparecimento de U07.** Se o DataSUS recodificar COVID-19 para o código da atualização da CID-10, o predicado baseado em B34.2 passa a contar a pandemia duas vezes ou nenhuma. A Tabela 1 reporta o valor observado, que é zero;
- **desaparecimento de B34.2**, que indicaria rota de coleta quebrada;
- **ano sem nenhum óbito**, que indicaria coleta incompleta silenciosa;
- **código da lista transcrita ausente do dicionário da CID-10**. Erro de digitação numa lista copiada à mão não se manifesta como erro: manifesta-se como zero óbitos, que é indistinguível de "ninguém morreu desta causa".

### 2.8 Aspectos éticos

O trabalho usa exclusivamente dados de domínio público, agregados, sem identificação individual, dispensando apreciação por Comitê de Ética em Pesquisa nos termos da Resolução CNS nº 510/2016. Nenhum microdado individual é publicado.

---

## 3. Resultados

### 3.1 A base

**Tabela 1 — A base analisada (`tabela_1_base.csv`).**

| Item | Valor |
|---|---|
| Óbitos não fetais, 2015–2024 | 14.484.496 |
| Óbitos não fetais, 2025 (preliminar) | 1.534.588 |
| Códigos de município de residência distintos | 5.595 |
| Códigos da CID-10 (4 caracteres) presentes | 7.746 |
| Óbitos com causa mal definida (R00–R99) | 772.173 |
| Óbitos com idade ignorada | 25.344 |
| Óbitos codificados em U07 (COVID-19 da CID-10) | 0 |
| Óbitos codificados em B34.2 (COVID-19 no SIM brasileiro) | 718.811 |
| Causas mal definidas, em % dos óbitos | 5,33 |

A guarda de U07 não disparou: zero óbitos nesse código em dez anos, e 718.811 em B34.2. O total de 14.484.496 óbitos inclui os registros cujo município de residência não é identificável — 27.278 óbitos em 25 códigos do tipo `110000`, "município ignorado" dentro da unidade da federação. Este desenho **não** agrega por município e por isso os mantém; o manuscrito irmão sobre vigilância da água, que agrega por município, os exclui e trabalha com 14.457.218. Os dois números descrevem a mesma versão dos microdados, e a diferença é inteiramente a exigência de município utilizável. A proporção de causas mal definidas, 5,33%, é o confundidor de fundo de todo este trabalho e volta na §4.3.

### 3.2 O instrumento oficial identifica 4,03 óbitos por 10 mil

**Tabela 2 — Os códigos do subgrupo 1.1 da Lista Brasileira, por versão etária (`tabela_2_codigos_subgrupo_1_1.csv`).**

| Doença | CID-10 | Menores de 5 anos | 5 a 74 anos | Óbitos 2015–2024, todas as idades |
|---|---|---|---|---|
| Tuberculose do sistema nervoso | A17 | sim | sim | 1.081 |
| Tuberculose miliar | A19 | sim | sim | 2.430 |
| Tétano neonatal | A33 | sim | não | 4 |
| Tétano obstétrico | A34 | não | sim | 0 |
| Tétano (outras formas) | A35 | sim | sim | 692 |
| Difteria | A36 | sim | sim | 46 |
| Coqueluche | A37 | sim | sim | 110 |
| Poliomielite aguda | A80 | sim | sim | 0 |
| Sarampo | B05 | sim | sim | 41 |
| Rubéola | B06 | sim | sim | 23 |
| Hepatite aguda B | B16 | sim | sim | 2.013 |
| Caxumba | B26 | sim | não | 105 |
| Meningite por Haemophilus | G00.0 | sim | sim | 108 |
| Síndrome da rubéola congênita | P35.0 | sim | não | 23 |
| Hepatite viral congênita | P35.3 | sim | não | 14 |

Duas leituras saltam da Tabela 2. A primeira é a distribuição interna: tuberculose miliar (2.430 óbitos) e do sistema nervoso (1.081) e hepatite aguda B (2.013) concentram a maior parte do total, enquanto sarampo, rubéola, difteria e caxumba somam, juntos, pouco mais de duzentos óbitos em dez anos. A segunda é a poliomielite: **zero óbitos em toda a série**, o que é a confirmação de um sucesso de saúde pública e, ao mesmo tempo, um código que ocupa lugar na lista sem contribuir com informação.

**Tabela 3 — Óbitos do subgrupo 1.1 por ano, e o mesmo conjunto de códigos acima de 74 anos (`tabela_3_subgrupo_1_1_por_ano.csv`).**

| Ano | Óbitos do subgrupo 1.1 | Mesmos códigos em 75 anos ou mais | Óbitos totais do ano | Subgrupo 1.1 por 10 mil óbitos |
|---|---|---|---|---|
| 2015 | 585 | 70 | 1.264.175 | 4,63 |
| 2016 | 580 | 68 | 1.309.774 | 4,43 |
| 2017 | 586 | 81 | 1.312.663 | 4,46 |
| 2018 | 632 | 67 | 1.316.719 | 4,8 |
| 2019 | 580 | 72 | 1.349.801 | 4,3 |
| 2020 | 560 | 71 | 1.556.824 | 3,6 |
| 2021 | 539 | 76 | 1.832.649 | 2,94 |
| 2022 | 552 | 74 | 1.544.266 | 3,57 |
| 2023 | 589 | 88 | 1.465.610 | 4,02 |
| 2024 | 629 | 79 | 1.532.015 | 4,11 |
| 2015–2024 | 5.832 | 746 | 14.484.496 | 4,03 |

Em dez anos, o instrumento oficial identifica 5.832 óbitos, 4,03 por 10 mil óbitos registrados. A série não tem tendência: 4,63 por 10 mil em 2015 e 4,11 em 2024, com o mínimo de 2,94 em 2021 — mínimo que é artefato do denominador, porque 2021 é o ano de maior mortalidade da série brasileira, e não sinal de melhora.

A terceira coluna da Tabela 3 antecipa o resultado seguinte: os **mesmos códigos** produzem 746 óbitos adicionais em pessoas de 75 anos ou mais, que a lista não conta porque não os alcança.

### 3.3 Um terço da carga está acima da idade que a lista cobre

**Tabela 4 — Panorama dos conjuntos, 2015–2024 (`tabela_4_panorama.csv`).**

| Conjunto | Óbitos 2015–2024 | Por 10 mil óbitos do período | Razão sobre o subgrupo 1.1 |
|---|---|---|---|
| Subgrupo 1.1 da Lista Brasileira (o instrumento oficial) | 5.832 | 4,03 | 1 |
| Conjunto ampliado, sem COVID-19 | 27.917 | 19,27 | 4,79 |
| Conjunto ampliado, sem COVID-19 e sem herpes zoster | 26.674 | 18,42 | 4,57 |
| COVID-19 (B34.2) | 718.811 | 496,26 | 123,25 |
| Latência longa (colo do útero, fígado e hepatite B crônica) | 174.100 | 120,2 | 29,85 |

**Tabela 5 — Estrutura etária dos óbitos por causas com vacina disponível (`tabela_5_estrutura_etaria.csv`).**

| Faixa etária | Subgrupo 1.1 | Ampliado sem COVID-19 | COVID-19 | Total | % do total |
|---|---|---|---|---|---|
| Menores de 5 anos | 355 | 2.067 | 1.802 | 3.869 | 0,5 |
| 5 a 74 anos | 5.477 | 16.654 | 458.845 | 475.499 | 63,7 |
| 75 anos ou mais | 0 | 9.183 | 258.093 | 267.276 | 35,8 |
| Idade ignorada | 0 | 13 | 71 | 84 | 0 |
| Todas as idades | 5.832 | 27.917 | 718.811 | 746.728 | 100 |

Dos 746.728 óbitos por causas com vacina disponível registrados na década, 267.276 — 35,8% — ocorreram em pessoas de 75 anos ou mais. Para essa faixa, a coluna do subgrupo 1.1 é **zero por construção**: não existe lista brasileira de evitabilidade acima dos 74 anos. A faixa que o instrumento cobre inteira, a de menores de cinco anos, responde por 3.869 óbitos, 0,5% do conjunto.

O corte etário tem origem conceitual conhecida — listas de evitabilidade nasceram para monitorar mortalidade prematura —, e a consequência é específica desta aplicação: influenza, doença pneumocócica e COVID-19 matam predominantemente idosos. Um instrumento que exclui a idade em que a doença mata não subestima a carga por descuido de medida; ele a define para fora.

### 3.4 Metade do que o instrumento conta é tuberculose de adulto

**Tabela 6 — Composição interna do subgrupo 1.1 (`tabela_6_composicao_subgrupo_1_1.csv`).**

| Componente | Óbitos 2015–2024 | % do subgrupo 1.1 | Óbitos por ano |
|---|---|---|---|
| Subgrupo 1.1, total | 5.832 | 100 | 583,2 |
| Tuberculose miliar e do sistema nervoso, no subgrupo 1.1 | 3.189 | 54,7 | 318,9 |
| … destes, em menores de 5 anos (idade da indicação da BCG) | 97 | 1,7 | 9,7 |
| … destes, em 5 a 74 anos (relação com a BCG infantil incerta) | 3.092 | 53 | 309,2 |
| Subgrupo 1.1 excluída a tuberculose | 2.643 | 45,3 | 264,3 |

Dos 5.832 óbitos do subgrupo 1.1, 3.189 são tuberculose miliar ou do sistema nervoso — 54,7% do total do instrumento. Destes, apenas 97 ocorreram em menores de cinco anos; 3.092, ou 53% de todo o subgrupo, ocorreram entre 5 e 74 anos.

A distinção importa porque a evitabilidade atribuída a essas duas causas vem da BCG — e isso não é interpretação deste trabalho. É o que a revisão de 2011 declara ao explicar por que manteve A17 e A19 no subgrupo 1.1 e mandou os demais códigos de tuberculose para outro: "por serem as causas evitáveis de morte pela vacina BCG" [3]. A indicação estabelecida da BCG, e a justificativa que a própria revisão invoca, é a proteção contra as **formas graves da tuberculose na criança**. Não se trata, porém, de afirmar que a BCG não proteja adultos: um seguimento de 60 anos de coorte vacinada na infância encontrou eficácia de 52% (IC95% 27%–69%) persistindo por 50 a 60 anos, sem redução estatisticamente significativa ao longo do tempo [10]. O problema é outro, e é de correspondência entre critério e indicador: o critério enunciado pelos autores não restringe idade, e o indicador que dele resulta é **dominado por morte adulta**, cuja relação com a vacinação infantil é muito mais incerta do que a de uma forma grave em criança não vacinada — e depende de cepa, de esquema, de idade à vacinação e do contexto epidemiológico, nenhum dos quais o SIM registra. Manter A17 e A19 no subgrupo de imunoprevenção sem restrição etária faz com que mais da metade do que o instrumento oficial reporta como "morte evitável por vacina" seja tuberculose de adulto, para a qual a intervenção evitável é diagnóstico e tratamento — que a própria Lista Brasileira classifica em outro subgrupo, o 1.2, quando se trata das demais formas de tuberculose.

Excluída a tuberculose, o núcleo do instrumento oficial fica em 2.643 óbitos em dez anos, 264,3 por ano no país inteiro.

### 3.5 O conjunto ampliado, causa a causa

**Tabela 7 — Óbitos por causas com vacina disponível, 2015–2024, com o ano de entrada da vacina na rede pública (`tabela_7_ampliado_por_causa.csv`).**

| Causa | Disponibilidade da vacina | Óbitos 2015–2024 | 2024 | 2025 (preliminar) |
|---|---|---|---|---|
| COVID-19 | PNI a partir de 2021 | 718.811 | 5.605 | 2.568 |
| Influenza | campanha anual desde 1999 | 14.622 | 2.458 | 4.575 |
| Tuberculose miliar e do SNC | BCG (formas graves na criança) | 3.511 | 425 | 491 |
| Hepatite B aguda | PNI (todo o período) | 2.013 | 179 | 171 |
| Doença meningocócica | PNI (MenC 2010; ACWY 2020) | 1.531 | 140 | 183 |
| Herpes zoster | FORA do PNI (rede privada) | 1.243 | 181 | 196 |
| Meningite pneumocócica | PNI (VPC10 2010; VPP23 idosos) | 1.121 | 182 | 186 |
| Pneumonia pneumocócica | PNI (VPC10 2010; VPP23 idosos) | 809 | 62 | 85 |
| Sepse pneumocócica | PNI (VPC10 2010; VPP23 idosos) | 793 | 81 | 49 |
| Tétano | PNI (todo o período) | 696 | 58 | 50 |
| Febre amarela | PNI (área ampliada 2017-2020) | 500 | 3 | 41 |
| Varicela | PNI a partir de 2013 | 408 | 29 | 13 |
| Sepse/pneumonia Haemophilus | PNI (Hib 1999) | 146 | 31 | 24 |
| Coqueluche | PNI (dTpa gestante 2014) | 110 | 22 | 9 |
| Meningite por Haemophilus | PNI (Hib 1999) | 108 | 16 | 13 |
| Caxumba | PNI (todo o período) | 105 | 15 | 11 |
| Rubéola e SRC | PNI (todo o período) | 46 | 2 | 7 |
| Rotavírus | PNI a partir de 2006 | 46 | 18 | 2 |
| Difteria | PNI (todo o período) | 46 | 4 | 1 |
| Sarampo | PNI (todo o período) | 41 | 0 | 0 |
| Raiva | PNI (profilaxia pós-exposição) | 22 | 2 | 0 |
| Poliomielite | PNI (todo o período) | 0 | 0 | 0 |
| Subtotal, sem COVID-19 | — | 27.917 | 3.908 | 6.107 |
| Subtotal, sem COVID-19 e sem herpes zoster | — | 26.674 | 3.727 | 5.911 |

Sem a COVID-19, o conjunto ampliado soma 27.917 óbitos, razão de 4,79 sobre o instrumento oficial (Tabela 4); excluído também o herpes zoster, que tem vacina fora do PNI, ficam 26.674 e a razão cai para 4,57. Quatro causas ausentes do subgrupo 1.1 respondem sozinhas por mais óbitos do que ele inteiro: influenza (14.622), doença meningocócica (1.531), meningite pneumocócica (1.121) e pneumonia pneumocócica (809).

A composição por disponibilidade é o que dá sentido ao número. Das causas com maior contagem, a influenza tem campanha anual desde 1999 e está classificada pela Lista Brasileira no subgrupo 1.2, entre as doenças infecciosas, e não no de imunoprevenção. A meningocócica ACWY, de 2020, não teria como constar de uma lista revista em 2011. A meningocócica C e a pneumocócica 10-valente, ambas incorporadas em 2010, teriam — e não constam. A defasagem, portanto, não é só o tempo que passou desde a última revisão: parte dela já existia no dia em que ela foi feita.

### 3.6 Três eventos em que a vacina existia e a doença matou

**Tabela 8 — Série anual dos três eventos, com o recorte de menores de 1 ano onde ele é decisivo (`tabela_8_eventos_serie_anual.csv`).**

| Ano | Febre amarela | Sarampo | Sarampo em menores de 1 ano | Coqueluche | Coqueluche em menores de 1 ano |
|---|---|---|---|---|---|
| 2015 | 4 | 0 | 0 | 42 | 40 |
| 2016 | 8 | 1 | 0 | 9 | 8 |
| 2017 | 195 | 2 | 0 | 17 | 17 |
| 2018 | 257 | 8 | 5 | 8 | 8 |
| 2019 | 18 | 11 | 5 | 6 | 6 |
| 2020 | 2 | 15 | 6 | 5 | 3 |
| 2021 | 8 | 3 | 3 | 1 | 1 |
| 2022 | 2 | 0 | 0 | 0 | 0 |
| 2023 | 3 | 1 | 0 | 0 | 0 |
| 2024 | 3 | 0 | 0 | 22 | 21 |
| 2025 | 41 | 0 | 0 | 9 | 6 |

**Febre amarela.** O surto de 2017 e 2018 produziu 452 óbitos, contra 4 em 2015 e 8 em 2016. O perfil é o clássico do ciclo silvestre: 86,5% no sexo masculino, idade média de 48,9 anos (Tabela 9). A vacina existe desde 1937 e é de dose única. O que faltava não era a vacina, era o **mapa** — as áreas atingidas de Minas Gerais, Espírito Santo, São Paulo e Rio de Janeiro não estavam na recomendação de vacinação de rotina, que foi ampliada durante e depois do surto, até a recomendação nacional. É o caso mais nítido do conjunto: um óbito evitável não por adesão do indivíduo, mas por delimitação territorial da vigilância. O valor preliminar de 2025 na Tabela 8 merece acompanhamento.

**Tabela 9 — Febre amarela, 2017–2018, por unidade da federação com cinco ou mais óbitos (`tabela_9_febre_amarela_uf.csv`).**

| Ano | UF | Óbitos | Idade média | % do sexo masculino |
|---|---|---|---|---|
| 2017 | ES | 88 | 47,3 | 88,6 |
| 2017 | MG | 74 | 49,6 | 89,2 |
| 2017 | SP | 13 | 49,3 | 61,5 |
| 2017 | PA | 6 | 17,5 | 100 |
| 2017 | RJ | 5 | 53 | 60 |
| 2018 | MG | 95 | 50,7 | 88,4 |
| 2018 | RJ | 79 | 52,5 | 81 |
| 2018 | SP | 78 | 46,3 | 92,3 |
| 2017–2018 | Brasil | 452 | 48,9 | 86,5 |

**Sarampo.** Depois de três óbitos em 2015–2017, vieram 37 entre 2018 e 2021, com 19 deles em menores de 1 ano — crianças que ainda não tinham idade para a primeira dose da tríplice viral e dependiam inteiramente da imunidade coletiva. Foi o período em que o Brasil perdeu o certificado de eliminação do sarampo. A leitura relevante não é a magnitude, que é pequena, mas a direção: uma doença sem óbito no início da série volta a matar, e mata sobretudo quem não podia ser protegido diretamente.

**Coqueluche.** A série mostra um padrão que a leitura apressada inverteria. Não é um evento de 2024: são 42 óbitos em 2015, 40 deles em menores de 1 ano, caindo continuamente até 1 óbito em 2021 e nenhum em 2022 e 2023 — declínio compatível com a introdução da dTpa na gestante em 2014, cuja proteção alcança o lactente antes da primeira dose da pentavalente. O que 2024 mostra é o **retorno**: 22 óbitos, 21 deles em menores de 1 ano. A assinatura etária é a mesma do início da série, e é a assinatura de falha na vacinação da gestante somada a esquema básico atrasado.

### 3.7 Influenza: a série cresce e o instrumento não a vê

**Tabela 10 — Óbitos por influenza (J09–J11) por faixa etária (`tabela_10_influenza_por_faixa.csv`).**

| Ano | Menores de 5 anos | 5 a 59 anos | 60 a 74 anos | 75 anos ou mais | Total |
|---|---|---|---|---|---|
| 2015 | 8 | 85 | 46 | 161 | 301 |
| 2016 | 122 | 993 | 358 | 283 | 1.756 |
| 2017 | 26 | 157 | 108 | 294 | 585 |
| 2018 | 110 | 514 | 242 | 349 | 1.215 |
| 2019 | 118 | 434 | 227 | 345 | 1.125 |
| 2020 | 38 | 298 | 315 | 535 | 1.186 |
| 2021 | 43 | 302 | 381 | 687 | 1.413 |
| 2022 | 101 | 571 | 779 | 1.798 | 3.249 |
| 2023 | 133 | 377 | 257 | 567 | 1.334 |
| 2024 | 121 | 617 | 540 | 1.179 | 2.458 |
| 2025 | 132 | 988 | 1.295 | 2.160 | 4.575 |

A influenza é a única causa deste conjunto cuja janela de oportunidade se fecha e reabre todo ano. Os óbitos passam de 301 em 2015 a 2.458 em 2024, com pico intermediário de 3.249 em 2022 — ano em que 1.798 dos óbitos ocorreram em pessoas de 75 anos ou mais. O valor preliminar de 2025, 4.575 óbitos com 2.160 acima de 74 anos, já é o maior da série de onze anos, e por ser preliminar só pode crescer.

Nenhum desses óbitos entra no subgrupo 1.1, por duas razões independentes e cumulativas: a Lista Brasileira classifica infecções respiratórias, inclusive influenza, no subgrupo 1.2; e a maior parte deles está acima da idade que a lista alcança.

### 3.8 COVID-19 depois que a vacina existia

**Tabela 11 — Óbitos por COVID-19 (B34.2) por faixa etária, a partir de 2021 (`tabela_11_covid_por_faixa.csv`).**

| Ano | Menores de 5 anos | 5 a 59 anos | 60 a 74 anos | 75 anos ou mais | Total |
|---|---|---|---|---|---|
| 2021 | 557 | 150.350 | 149.671 | 123.852 | 424.461 |
| 2022 | 510 | 9.638 | 17.725 | 37.876 | 65.764 |
| 2023 | 166 | 1.461 | 2.749 | 5.897 | 10.274 |
| 2024 | 123 | 853 | 1.428 | 3.201 | 5.605 |
| 2025 | 77 | 389 | 656 | 1.445 | 2.568 |
| 2022–2024 | 799 | 11.952 | 21.902 | 46.974 | 81.643 |

A COVID-19 distorce qualquer comparação de série no período, e por isso aparece separada em todo este trabalho. Há, no entanto, um recorte que não é distorção. Em 2022, 2023 e 2024 — anos em que a vacinação estava disponível para toda a população brasileira, com esquema primário e reforços — foram registrados 81.643 óbitos por COVID-19, dos quais 46.974 em pessoas de 75 anos ou mais.

Esse número é um teto e não uma estimativa de mortes evitáveis, pela mesma razão declarada na Introdução: a eficácia vacinal não é total e boa parte dessas pessoas estava vacinada. O que ele mede é a carga que persistiu depois que a ferramenta existia. Para efeito de comparação, em 2021 — ano em que a vacinação começou em janeiro e alcançou a população geral ao longo do segundo semestre — foram 424.461 óbitos, dos quais 150.350 entre 5 e 59 anos e 123.852 acima de 74.

### 3.9 O teto de medição é de codificação

**Tabela 12 — Óbitos segundo a presença de agente etiológico na causa básica, 2015–2024 (`tabela_12_teto_codificacao.csv`).**

| Código e descrição | Óbitos 2015–2024 | Agente etiológico nomeado |
|---|---|---|
| R00–R99 — causas mal definidas | 772.173 | não |
| J18 — pneumonia, agente não especificado | 631.108 | não |
| A41.9 — septicemia não especificada | 204.190 | não |
| J15 — outra pneumonia bacteriana | 160.949 | não |
| J13 — pneumonia por Streptococcus pneumoniae | 809 | sim |
| A40.3 — septicemia por Streptococcus pneumoniae | 793 | sim |
| J14 — pneumonia por Haemophilus influenzae | 88 | sim |

**Tabela 13 — Razões entre código inespecífico e código com agente nomeado (`tabela_13_razoes_de_especificidade.csv`).**

| Par de códigos | Óbitos sem agente | Óbitos com agente | Razão |
|---|---|---|---|
| Pneumonia sem agente (J18) sobre pneumonia pneumocócica (J13) | 631.108 | 809 | 780,1 |
| Septicemia não especificada (A41.9) sobre septicemia pneumocócica (A40.3) | 204.190 | 793 | 257,5 |
| Pneumonia sem agente (J18) sobre pneumonia por Haemophilus (J14) | 631.108 | 88 | 7.171,7 |

Há 631.108 óbitos por pneumonia sem agente identificado (J18) e 809 atribuídos ao pneumococo (J13): razão de 780,1. Somando J15, "outra pneumonia bacteriana", são mais 160.949 óbitos sem agente nomeado. Em septicemia o padrão se repete, com 204.190 óbitos em A41.9 contra 793 em A40.3, razão de 257,5.

A literatura internacional atribui ao pneumococo uma fração substancial da pneumonia adulta hospitalizada, e o SIM não permite recuperá-la, porque a etiologia não é investigada na maior parte dos óbitos e, quando é, não chega à declaração. A consequência é direta: **a doença pneumocócica invasiva, alvo de duas vacinas do PNI, é estruturalmente incontável por causa básica no Brasil.** Todo valor deste artigo para pneumococo é piso, e um piso muito abaixo do real — o que torna o conjunto ampliado, ele próprio, um limite inferior.

### 3.10 O cruzamento ecológico com o PNI dá nulo

**Tabela 14 — Óbitos por influenza em 60 anos ou mais e doses aplicadas, por unidade da federação e ano (`tabela_14_influenza_doses_uf.csv`).**

| UF | Ano | Óbitos por influenza em 60 anos ou mais | População de 60 anos ou mais | Doses de influenza (INF3) | Óbitos por 100 mil de 60 anos ou mais | Doses por habitante de 60 anos ou mais |
|---|---|---|---|---|---|---|
| AM | 2023 | 44 | 372.862 | 505.699 | 11,8 | 1,356 |
| SE | 2023 | 27 | 294.498 | 264.895 | 9,17 | 0,899 |
| AC | 2023 | 7 | 80.387 | 187.650 | 8,71 | 2,334 |
| MS | 2023 | 24 | 417.899 | 317.944 | 5,74 | 0,761 |
| RR | 2023 | 3 | 52.443 | 100.733 | 5,72 | 1,921 |
| PA | 2023 | 42 | 888.869 | 895.263 | 4,73 | 1,007 |
| MA | 2023 | 38 | 805.286 | 169.265 | 4,72 | 0,21 |
| TO | 2023 | 9 | 191.769 | 78.683 | 4,69 | 0,41 |
| CE | 2023 | 50 | 1.306.181 | 838.017 | 3,83 | 0,642 |
| PI | 2023 | 17 | 457.473 | 119.491 | 3,72 | 0,261 |
| RN | 2023 | 19 | 518.910 | 156.172 | 3,66 | 0,301 |
| PB | 2023 | 19 | 611.543 | 92.845 | 3,11 | 0,152 |
| PR | 2023 | 59 | 2.002.790 | 1.406.836 | 2,95 | 0,702 |
| GO | 2023 | 29 | 990.111 | 263.126 | 2,93 | 0,266 |
| RO | 2023 | 6 | 205.227 | 198.707 | 2,92 | 0,968 |
| DF | 2023 | 11 | 405.058 | 123.202 | 2,72 | 0,304 |
| RS | 2023 | 62 | 2.371.583 | 400.193 | 2,61 | 0,169 |
| ES | 2023 | 17 | 672.790 | 194.042 | 2,53 | 0,288 |
| SC | 2023 | 28 | 1.261.013 | 1.413.322 | 2,22 | 1,121 |
| BA | 2023 | 44 | 2.179.226 | 586.821 | 2,02 | 0,269 |
| AL | 2023 | 8 | 423.252 | 98.007 | 1,89 | 0,232 |
| SP | 2023 | 143 | 8.129.891 | 4.983.472 | 1,76 | 0,613 |
| RJ | 2023 | 52 | 3.296.229 | 926.390 | 1,58 | 0,281 |
| PE | 2023 | 18 | 1.384.121 | 318.896 | 1,3 | 0,23 |
| MG | 2023 | 45 | 3.835.764 | 1.455.311 | 1,17 | 0,379 |
| MT | 2023 | 3 | 454.414 | 442.515 | 0,66 | 0,974 |
| MS | 2024 | 55 | 435.081 | 859.593 | 12,64 | 1,976 |
| SE | 2024 | 29 | 306.213 | 587.317 | 9,47 | 1,918 |
| PR | 2024 | 176 | 2.079.282 | 3.315.223 | 8,46 | 1,594 |
| SC | 2024 | 111 | 1.318.261 | 2.016.059 | 8,42 | 1,529 |
| RS | 2024 | 187 | 2.445.607 | 2.930.841 | 7,65 | 1,198 |
| AM | 2024 | 26 | 389.849 | 1.057.086 | 6,67 | 2,712 |
| MA | 2024 | 53 | 828.156 | 1.594.161 | 6,4 | 1,925 |
| TO | 2024 | 12 | 199.179 | 332.623 | 6,02 | 1,67 |
| GO | 2024 | 62 | 1.031.555 | 1.651.311 | 6,01 | 1,601 |
| AL | 2024 | 26 | 437.892 | 856.259 | 5,94 | 1,955 |
| PA | 2024 | 50 | 923.024 | 2.146.129 | 5,42 | 2,325 |
| PB | 2024 | 34 | 630.338 | 1.084.650 | 5,39 | 1,721 |
| PI | 2024 | 24 | 470.052 | 878.901 | 5,11 | 1,87 |
| SP | 2024 | 425 | 8.419.113 | 11.757.953 | 5,05 | 1,397 |
| ES | 2024 | 35 | 699.859 | 1.279.837 | 5 | 1,829 |
| AC | 2024 | 4 | 83.767 | 212.263 | 4,78 | 2,534 |
| CE | 2024 | 64 | 1.351.285 | 2.552.384 | 4,74 | 1,889 |
| RO | 2024 | 10 | 214.904 | 381.143 | 4,65 | 1,774 |
| RN | 2024 | 20 | 539.796 | 961.265 | 3,71 | 1,781 |
| DF | 2024 | 13 | 426.238 | 820.725 | 3,05 | 1,926 |
| BA | 2024 | 67 | 2.248.921 | 3.258.528 | 2,98 | 1,449 |
| MG | 2024 | 103 | 3.967.762 | 6.294.465 | 2,6 | 1,586 |
| RJ | 2024 | 88 | 3.396.135 | 3.888.597 | 2,59 | 1,145 |
| MT | 2024 | 12 | 475.784 | 920.727 | 2,52 | 1,935 |
| PE | 2024 | 31 | 1.431.590 | 2.215.288 | 2,17 | 1,547 |
| RR | 2024 | 1 | 55.343 | 157.012 | 1,81 | 2,837 |
| AP | 2024 | 1 | 74.228 | 204.753 | 1,35 | 2,758 |

**Tabela 15 — Correlação entre doses de influenza por habitante de 60 anos ou mais e óbitos por influenza nessa faixa, por unidade da federação (`tabela_15_correlacao_por_ano.csv`).**

| Ano | Unidades da federação no cruzamento | Doses de influenza no país (INF3) | Óbitos por influenza em 60 anos ou mais | Correlação de Spearman | Valor de p |
|---|---|---|---|---|---|
| 2023 | 26 | 16.621.107 | 824 | 0,389 | 0,05 |
| 2024 | 27 | 54.215.093 | 1.719 | -0,056 | 0,783 |

Pelo critério declarado na §2.6, o resultado é **nulo**: a correlação de Spearman é +0,389 em 2023 e −0,056 em 2024, com troca de sinal entre os anos e um deles abaixo do limiar de módulo. O dado por unidade da federação que sustenta o teste está em `tabela_14_influenza_doses_uf.csv`.

Três razões desaconselham insistir com outra especificação. A campanha responde ao surto, o que inverte a direção causal esperada. A unidade de análise é a unidade da federação, sujeita à falácia ecológica com menos de trinta pontos por ano (Tabela 15). E, decisiva, a fonte do denominador está incompleta em um dos dois anos: o PNI/RNDS registra 16.621.107 doses de influenza em 2023 contra 54.215.093 em 2024, enquanto o total de doses de todos os imunobiológicos quase não varia entre os dois anos. Não é queda de campanha; é a campanha de 2023 que não chegou inteira ao registro nacional. Dose de influenza de 2023 nessa base não serve de denominador — observação que vale para além deste artigo.

### 3.11 O grupo de latência longa

**Tabela 16 — Causas com relação estabelecida com vacina e latência longa, reportadas fora de qualquer total (`tabela_16_latencia_longa.csv`).**

| Causa | Relação com a vacina | Óbitos 2015–2024 | 2015 | 2024 | Variação de 2015 a 2024, em % |
|---|---|---|---|---|---|
| Câncer de colo do útero (HPV) | HPV no PNI desde 2014; latência de décadas | 65.999 | 5.727 | 7.493 | 30,8 |
| Hepatite B crônica/cirrose | fração atribuível ao HBV não separável na CID | 2.083 | 262 | 182 | -30,5 |
| Câncer de fígado | fração atribuível ao HBV não separável na CID | 106.018 | 9.711 | 11.688 | 20,4 |

O câncer de colo do útero soma 65.999 óbitos na década e cresce 30,8% entre 2015 e 2024; o câncer de fígado, 106.018 óbitos e crescimento de 20,4%. Ambos têm relação estabelecida com agentes contra os quais o PNI vacina — HPV desde 2014, hepatite B desde os anos 1990. Nenhum dos dois pode ser lido como falha vacinal contemporânea: as mortes de hoje decorrem de infecções de décadas atrás, e é justamente por isso que o efeito da vacinação atual sobre esses números só será observável em torno de 2040.

Registrá-los fora da soma preserva as duas verdades ao mesmo tempo: que são a maior justificativa de longo prazo para a vacinação em curso, e que não pertencem a nenhuma contagem de mortalidade evitável no presente.

---

## 4. Discussão

### 4.1 O achado principal

O instrumento oficial brasileiro para mortes evitáveis por imunoprevenção identifica 4,03 óbitos por 10 mil no país, sem tendência ao longo de dez anos. O número não decorre de o Brasil ter resolvido a mortalidade por doença imunoprevenível — decorre de três propriedades do instrumento que se somam, cada uma delas mensurável e nenhuma delas erro de cálculo.

A primeira é o corte etário. Um terço da carga por causas com vacina disponível está acima dos 74 anos, faixa para a qual não existe lista brasileira de evitabilidade. Não é subestimação: é exclusão definicional.

A segunda é a data. A lista descreve o calendário vacinal anterior a 2011, e o calendário mudou. Ela não tem como conter COVID-19, e isso é justo; mas também não contém rotavírus, meningococo, pneumococo, varicela e HPV, e classifica influenza fora da imunoprevenção apesar de a campanha anual ser anterior à própria lista.

A terceira é interna. Mais da metade do que ela conta é tuberculose miliar e do sistema nervoso em pessoas de 5 a 74 anos, atribuída à imunoprevenção por conta da BCG — critério que a revisão de 2011 enuncia explicitamente [3] e que não restringe a idade, embora a proteção estabelecida da vacina seja contra as formas graves na criança. Não é um detalhe de classificação: é a maior componente do indicador.

### 4.2 O que muda se o instrumento for atualizado

A comparação entre o subgrupo 1.1 e o conjunto ampliado dá a ordem de grandeza do que está fora: razão de 4,79 para o conjunto sem a COVID-19, e de 123,25 para a COVID-19 sozinha (Tabela 4). Mas a implicação mais útil não é o total: é que os componentes de fora são **os que se movem**.

O subgrupo 1.1 é composto de causas raras e estáveis, e por isso não responde a política vacinal alguma no horizonte de uma década. As causas de fora, ao contrário, produziram na mesma década um surto de febre amarela com 452 óbitos, a perda do certificado de eliminação do sarampo, o retorno da coqueluche em lactentes e uma série de influenza cujo maior valor é o do ano mais recente, ainda preliminar. Uma lista atualizada não seria apenas maior; seria sensível — mostraria variação onde a atual mostra ruído.

Três acréscimos são consequências diretas dos resultados: incluir influenza no subgrupo de imunoprevenção, incluir doença meningocócica e doença pneumocócica invasiva, e estender a lista acima dos 74 anos ou explicitar que o indicador é de mortalidade prematura e não de evitabilidade. A restrição etária de A17 e A19 aos menores de cinco anos é a quarta, e a mais barata: não exige dado novo, apenas coerência com o mecanismo que fundamenta a inclusão.

### 4.3 O limite que nenhuma lista atravessa

A atualização da lista não resolve o problema de fundo. Com 631.108 óbitos por pneumonia sem agente identificado contra 809 atribuídos ao pneumococo, e 772.173 óbitos em causas mal definidas, o que se pode contar por causa básica é uma fração pequena e enviesada do que existe. Incluir doença pneumocócica invasiva numa lista atualizada é correto e, sozinho, produzirá um número pequeno — não porque o pneumococo mate pouco, mas porque ele quase nunca é nomeado.

Isso desloca parte do problema da vigilância para o registro. O ganho de sensibilidade viria menos de reclassificar códigos e mais de investigação etiológica nos óbitos por pneumonia e septicemia — e, na ausência dela, de métodos de redistribuição de causas inespecíficas, que este trabalho deliberadamente não aplicou por não haver base empírica brasileira para as proporções de redistribuição neste recorte.

### 4.4 O que este desenho não pode dizer

A limitação central não é de método: é de fonte, e vale para toda a literatura de evitabilidade construída sobre declaração de óbito.

- **Contar óbitos por doença com vacina não é contar mortes evitáveis.** Faltam a eficácia vacinal, que nunca é total, e a situação vacinal individual, que o SIM não registra. Uma pessoa vacinada que morre da doença representa falha de proteção, não falha de imunização, e as duas exigem respostas de política diferentes. Todos os totais aqui são teto.
- **A causa básica é uma escolha de codificação.** Óbitos com doença imunoprevenível como causa contribuinte, e não básica, não aparecem — situação frequente na COVID-19 e na influenza em pessoas com comorbidade. A direção do viés é conhecida: subcontagem.
- **O grupo de latência longa foi excluído por argumento, não por medida.** A fração de câncer de fígado atribuível ao vírus da hepatite B não foi estimada aqui; ela existe na literatura e sua incorporação exigiria premissas que este desenho não sustenta.
- **A disponibilidade da vacina é nacional e por ano.** Ela não captura variação territorial de recomendação — que é exatamente o mecanismo do surto de febre amarela — nem descontinuidade de estoque. Uma versão futura poderia usar a recomendação vigente por município e ano, dado que existe em normativa e não em base estruturada.
- **Os anos de entrada no PNI não foram auditados um a um.** Foram compilados do Calendário Nacional de Vacinação [6], e não da sequência de portarias e notas informativas que os instituíram. Servem para separar "tem vacina" de "o SUS oferecia a vacina", que é o uso que o artigo lhes dá, e não sustentariam uma análise de tempo até a incorporação.
- **O cruzamento ecológico é ecológico.** Ainda que a fonte de 2023 estivesse íntegra, correlação entre agregados por unidade da federação não sustenta inferência sobre indivíduos.

---

## 5. Conclusão

O Brasil dispõe de um instrumento oficial para contar mortes evitáveis por vacina, e ele identifica quatro óbitos em cada dez mil registrados, número que não se move há uma década. A estabilidade não é epidemiológica. Ela decorre de o instrumento parar aos 74 anos, classificar a evitabilidade com as evidências e as tecnologias disponíveis antes da expansão recente do PNI e ser dominado internamente por uma causa cuja evitabilidade por vacina não se sustenta na idade em que ocorre.

No mesmo período, doenças com vacina disponível produziram um surto de febre amarela com 452 óbitos em áreas fora da recomendação vigente — essa, sim, ausente do subgrupo 1.1 —, a perda do certificado de eliminação do sarampo com 19 óbitos em lactentes, o retorno da coqueluche em menores de 1 ano e uma série de influenza cujo valor mais recente é o maior de onze anos. **Sarampo e coqueluche já constam da lista**, e ressurgiram assim mesmo: o problema do instrumento não se reduz a quais códigos ele inclui. Um indicador de evitabilidade que não registra nenhum desses eventos não está medindo mal: está medindo outra coisa.

Atualizar a Lista Brasileira é decisão de vigilância, não exercício estatístico, e as quatro mudanças que os resultados sustentam são explícitas. Nenhuma delas, porém, atravessa o teto imposto pela ausência de investigação etiológica na declaração de óbito — que continua sendo, no Brasil, o fator que mais limita o que qualquer lista de causas evitáveis consegue enxergar.

---

## 6. Figuras

As seis figuras são geradas por `artigo-imunopreveniveis/gerar_figuras.py` a
partir das mesmas tabelas deste manuscrito, sem nenhum cálculo próprio. Cada
legenda aponta a tabela de origem, de modo que todo valor lido no gráfico pode
ser conferido no número exato.

**Figura 1.** Óbitos do subgrupo 1.1 por ano, em contagem absoluta e por 10 mil
óbitos do ano, com a linha dos mesmos códigos em 75 anos ou mais — a faixa que o
instrumento não alcança. *Fonte: Tabela 3.*

**Figura 2.** O que o subgrupo 1.1 conta, comparado ao conjunto ampliado de
doenças com vacina disponível e à COVID-19. Escala logarítmica, porque a
COVID-19 está duas ordens de grandeza acima do resto e uma escala linear
achataria a comparação que importa. *Fonte: Tabela 4.*

**Figura 3.** Distribuição etária dos óbitos por causas com vacina disponível.
A lista termina aos 74 anos, e 35,8% dos óbitos estão acima desse corte.
*Fonte: Tabela 5.*

**Figura 4.** Composição interna do subgrupo 1.1. Em vermelho, a tuberculose em
idade em que a relação entre o óbito e a vacinação infantil é incerta; em azul, o que resta. *Fonte: Tabela 6.*

**Figura 5.** Febre amarela, sarampo e coqueluche ano a ano. A parte hachurada é
a fração em menores de 1 ano. **Sarampo (B05) e coqueluche (A37) já constam do
subgrupo 1.1**; a febre amarela não. As duas primeiras ressurgiram no período
com a lista já as incluindo — o que indica que a limitação do instrumento não se
resolve apenas acrescentando códigos. *Fonte: Tabela 8.*

**Figura 6.** O teto de codificação: óbitos por código com agente etiológico
nomeado (azul) e sem (cinza). Escala logarítmica. *Fonte: Tabela 12.*

---

## 7. Disponibilidade de dados e código

Todas as fontes são de domínio público. Os microdados do Sistema de Informações sobre Mortalidade são distribuídos pelo DataSUS e pelo OpenDataSUS; as doses aplicadas, pelo PNI/RNDS via OpenDataSUS; os denominadores populacionais, pelo IBGE. As duas notas técnicas que definem a Lista Brasileira estão publicadas pelo TabNet/DataSUS [4, 5], e os artigos que a propõem e revisam, na revista *Epidemiologia e Serviços de Saúde* [1-3]. Nenhum dado individual é publicado — apenas agregados.

Os cálculos são reproduzidos por dois scripts abertos:

- `scripts/analise_mortes_imunopreveniveis.py` — contém as listas de CID-10 transcritas, a derivação do óbito em quatro caracteres, as guardas e as tabelas de análise, gravadas em `data/analises/`;
- `artigo-imunopreveniveis/gerar_tabelas.py` — importa as definições do anterior, reagrega o microdado e formata as dezesseis tabelas deste manuscrito em `artigo-imunopreveniveis/tabelas/`.

Nenhum número deste texto é digitado: cada valor citado existe em um dos CSVs de `artigo-imunopreveniveis/tabelas/`, e as tabelas do manuscrito são regeradas a partir deles por `artigo/sincronizar_tabelas.py --dir artigo-imunopreveniveis`, com regressão em `tests/test_manuscrito.py`. Um número no texto que não esteja em nenhum CSV é um número sem procedência.

---

## 8. Notas sobre o que ainda não foi feito

Itens conhecidos e não resolvidos, listados para que não sejam confundidos com decisões:

- **a causa contribuinte não foi examinada.** O SIM traz as linhas da declaração de óbito além da causa básica, e elas permitiriam medir quantos óbitos têm doença imunoprevenível como causa associada. É o caminho mais direto para transformar o teto deste artigo em faixa, com piso e limite superior, e exige recoletar colunas que o recorte em disco não traz;
- **a série do PNI anterior a 2020 não foi incorporada.** O legado do SI-PNI está no FTP do DataSUS (prefixos `DPNI` e `CPNI`, 1994–2019) e permitiria estender o eixo de doses para além de 2023. Há quebra metodológica em 2020, na migração para a RNDS: são duas séries, não uma, e tratá-las como contínuas produziria tendência falsa;
- **a recomendação de febre amarela por município e ano não está estruturada.** Ela existe em normativa do Ministério da Saúde e é o dado que converteria a §3.6 de argumento em medida: permitiria classificar cada óbito conforme a área estivesse ou não sob recomendação na data;
- **a fração atribuível não foi aplicada a nenhuma causa.** Para pneumococo em pneumonia sem agente, e para hepatite B em câncer de fígado, existem estimativas na literatura. Aplicá-las produziria a única estimativa de carga com ordem de grandeza realista, ao custo de premissas importadas de outras populações — decisão que merece ser tomada explicitamente, e não por conveniência;
- **a mortalidade não foi padronizada por idade nem apresentada como taxa populacional.** Como o objeto do artigo é a cobertura do instrumento, e não a comparação entre territórios, os números são contagens e proporções sobre o total de óbitos. Uma versão que compare unidades da federação exigiria padronização, e o repositório já dispõe do denominador por faixa;
- **a situação vacinal individual é o dado que falta e existe.** O PNI/RNDS registra dose com identificador pseudonimizado do paciente; o SIM registra óbito. A vinculação entre as duas bases não é possível com os dados públicos e transformaria todo este desenho — de contagem de teto em medida de falha de proteção.

---

## 9. Referências

- **[1]** Malta DC, Duarte EC, Almeida MF, Dias MAS. Lista de causas de mortes evitáveis por intervenções do Sistema Único de Saúde do Brasil. *Epidemiologia e Serviços de Saúde*. 2007;16(4):233-244.
- **[2]** Malta DC, Sardinha LMV, Moura L, Lansky S, Leal MC, Szwarcwald CL, França E. Atualização da lista de causas de mortes evitáveis por intervenções do Sistema Único de Saúde do Brasil. *Epidemiologia e Serviços de Saúde*. 2010;19(2):173-176.
- **[3]** Malta DC, França E, Abreu DX, Oliveira H, Monteiro RA, Sardinha LMV, Duarte EC, Silva GA. Atualização da lista de causas de mortes evitáveis (5 a 74 anos de idade) por intervenções do Sistema Único de Saúde do Brasil. *Epidemiologia e Serviços de Saúde*. 2011;20(3):409-412.
- **[4]** Brasil. Ministério da Saúde. DATASUS. *Óbitos por causas evitáveis — 0 a 4 anos: notas técnicas*. Disponível em `tabnet.datasus.gov.br/cgi/sim/Obitos_Evitaveis_0_a_4_anos.pdf`
- **[5]** Brasil. Ministério da Saúde. DATASUS. *Óbitos por causas evitáveis — 5 a 74 anos: notas técnicas*. Disponível em `tabnet.datasus.gov.br/cgi/sim/Obitos_Evitaveis_5_a_74_anos.pdf`
- **[6]** Brasil. Ministério da Saúde. *Calendário Nacional de Vacinação*. Disponível em `gov.br/saude/pt-br/vacinacao/calendario`
- **[7]** Brasil. Ministério da Saúde. *Sistema de Informações sobre Mortalidade (SIM): microdados*. DATASUS e OpenDataSUS. Arquivos por unidade da federação e nacionais, competências de 2015 a 2025.
- **[8]** Brasil. Ministério da Saúde. *Programa Nacional de Imunizações: doses aplicadas*. OpenDataSUS, competências mensais de 2023 a 2026.
- **[9]** Instituto Brasileiro de Geografia e Estatística. *Censo Demográfico 2022* e *Estimativas da população residente*. Rio de Janeiro: IBGE.
- **[10]** Aronson NE, Santosham M, Comstock GW, Howard RS, Moulton LH, Rhoades ER, Harrison LH. Long-term efficacy of BCG vaccine in American Indians and Alaska Natives: a 60-year follow-up study. *JAMA*. 2004;291(17):2086–91. doi:10.1001/jama.291.17.2086
