# Estrutura do perfil municipal de causas de morte no Brasil, 2015–2024: um contínuo, e o quanto dele é codificação

**Pedro Paulo Fernandes**¹

¹ Saúde em Dado — saudeemdado.com · ORCID e afiliação a completar

*Coautoria a definir. Este é um rascunho de trabalho preparado a partir de um desenho de análise proposto em 2026-09-01.*

---

## Resumo

**Contexto.** Análises não supervisionadas de mortalidade municipal — clusterizar municípios por "padrão de mortes" — são frequentes na epidemiologia descritiva brasileira. São também análises que nunca falham: a análise de componentes principais sempre devolve componentes, o *k-means* sempre devolve grupos, e a busca por defasagem sempre encontra um *lag* de pico. O risco não é a análise não rodar; é rodar e produzir estrutura que não existe.

**Objetivo.** Determinar se o perfil de causas de morte separa os municípios brasileiros em grupos, quantos eixos de variação existem acima do ruído amostral, e quanto dessa variação é epidemiologia e quanto é prática de codificação.

**Métodos.** Todos os 14.378.827 óbitos não fetais registrados no Sistema de Informações sobre Mortalidade entre 2015 e 2024, agregados por município de residência e categoria de três caracteres da CID-10 (Tabela 1). Analisamos os 3.438 municípios com ao menos 500 óbitos no período e as 287 categorias presentes em pelo menos 25% deles. A composição de causas de cada município foi residualizada por quatro confundidores — logaritmo da população, fração com 60 anos ou mais, percentual de causas mal definidas e fração de B34 — antes de qualquer decomposição. Cada etapa foi comparada com um **nulo multinomial** no qual cada município sorteia os seus próprios óbitos da composição nacional. A estabilidade da partição foi medida pelo índice Rand ajustado entre subamostras de 80%, e a separação, pela silhueta. Correlações entre causas foram calculadas em séries mensais nacionais sem tendência linear e sem efeito de mês civil, com controle de taxa de descoberta falsa. Desvios do padrão próprio foram testados por binomial negativa com dispersão estimada pela variação ano a ano dentro do município.

**Resultados.** Seis componentes superam duas vezes o nulo multinomial, mas o primeiro explica apenas 3,3% da variância após os controles, contra 6,3% antes (Tabela 3) — quase metade do que pareceria "padrão de mortalidade" era porte, estrutura etária, qualidade do registro e pandemia. Os municípios **não se separam em grupos discretos**: a partição em três grupos se reproduz entre subamostras (Rand ajustado 0,93) mas não separa (silhueta 0,17), e a soma de quadrados não explicada cai sem cotovelo de k=2 a k=12 (Tabela 5). O primeiro componente correlaciona **−0,54** com um índice de inespecificidade diagnóstica, enquanto o indicador clássico de qualidade — percentual de causas mal definidas — correlaciona apenas **+0,37** com esse índice. A correlação entre causas recupera o controle positivo esperado (dengue e dengue hemorrágica, r = +0,97), mas a versão com defasagem não se sustenta: o pico de |r| concentra-se nas bordas da janela testada. A detecção de desvios recupera COVID-19 em 2020–2021 e dengue exclusivamente em 2024, com São Paulo registrando 422 óbitos por dengue contra 6,5 esperados; o restante do que ela sinaliza é, majoritariamente, deriva de codificação. Repetida **dentro de cada grupo**, a análise de correlação mostra que o grupo de codificação mais precisa tem **um terço** dos pares correlacionados dos demais (2.632 contra 7.937 e 8.636). Um espaço alternativo de atributos, construído com quinze variáveis de contexto social e de sistema de saúde, alinha-se ao eixo principal de mortalidade em r = −0,46; e o índice de inespecificidade correlaciona +0,56 com analfabetismo mas apenas −0,09 com leitos hospitalares e +0,01 com o porte do município.

**Conclusões.** O perfil municipal de causas de morte no Brasil é um contínuo estruturado, não uma tipologia. Uma parcela substancial do seu eixo principal é precisão de codificação diagnóstica, dimensão que o indicador de qualidade em uso não captura. Análises de agrupamento que não controlem essa dimensão descrevem, em boa parte, cultura de registro médico — e tendem a ser lidas como epidemiologia.

**Palavras-chave:** mortalidade; sistemas de informação em saúde; análise de agrupamento; qualidade de dados; classificação internacional de doenças.

---

## 1. Introdução

A pergunta que motiva este trabalho tem forma simples: se cada município brasileiro for representado pela composição das causas de morte de sua população, municípios com "padrão de mortes" parecido se agrupam? E, dentro de cada grupo, quais causas se movem juntas ao longo do tempo?

É um desenho reconhecível de epidemiologia descritiva, e tem valor: agrupar unidades por perfil de desfecho é o primeiro passo para gerar hipóteses sobre determinantes compartilhados. Mas é também um desenho com uma propriedade incômoda — **nenhuma de suas etapas falha**. A decomposição em componentes principais sempre devolve componentes ordenados por variância. O *k-means* sempre devolve exatamente o número de grupos que se pedir. Uma busca de correlação cruzada sempre encontra um *lag* de pico. Em nenhum desses casos o método sinaliza que não havia estrutura para encontrar; ele apenas descreve o ruído com a mesma sintaxe com que descreveria o sinal.

No caso brasileiro há três razões concretas para desconfiar antes de interpretar.

A primeira é o **tamanho da contagem**. A mediana nacional é de 77 óbitos por município-ano, com quartil inferior em 38 (Tabela 1). Distribuídos por mais de mil categorias da CID-10, o perfil de um município mediano é quase inteiramente composto de zeros e uns. A variação multinomial entre municípios de mesmo tamanho, sozinha, produz matrizes que se decompõem em componentes aparentemente interpretáveis.

A segunda é a **codificação da COVID-19**. O Sistema de Informações sobre Mortalidade brasileiro não utilizou o código U07 em nenhum registro entre 2015 e 2024. A COVID-19 foi codificada como B34.2 — que, truncada em três caracteres, torna-se B34, cuja descrição oficial na CID-10 é "doença por vírus de localização não especificada" (Tabela 2). Um filtro razoável de "causas inespecíficas" removeria, portanto, a pandemia inteira da matriz de análise.

A terceira é a **qualidade heterogênea do registro**. O percentual de óbitos por causas mal definidas varia de 0,64% a 14,86% entre os municípios brasileiros (percentis 5 e 95), uma amplitude de vinte e três vezes. Agrupar municípios por composição de causa recupera, necessariamente, parte de *quem registra bem*, e não apenas de *quem adoece de quê*.

Este trabalho executa o desenho proposto, mas subordina cada etapa a uma comparação explícita com um modelo nulo, e relata com o mesmo peso o que a análise sustenta e o que ela não sustenta.

---

## 2. Métodos

### 2.1 Dados

Utilizamos a totalidade dos registros de óbito do Sistema de Informações sobre Mortalidade (SIM/DataSUS) entre 2015 e 2024, excluídos os óbitos fetais. Para 2022–2024 a fonte é o arquivo nacional em CSV do OpenDataSUS; para 2015–2021, os arquivos `.dbc` por unidade da federação do FTP do DataSUS. A causa básica foi truncada em três caracteres, o grão de *categoria* da CID-10, e a unidade geográfica é o município de residência.

O grão município × categoria não existia previamente na plataforma que sustenta esta análise: havia município × capítulo (22 categorias) e categoria × unidade da federação, nunca os dois cruzados. A tabela construída soma 3.591.937 células no grão anual e 7.700.720 no mensal, e reconcilia exatamente — divergência zero em 55.938 pares município-ano — com a tabela de mortalidade por capítulo já publicada e verificada.

Duas categorias inválidas (D96 e K99), somando dois óbitos em dez anos, foram mantidas para preservar essa reconciliação.

### 2.2 Recorte analítico

Restringimos a análise aos municípios com pelo menos 500 óbitos no período (3.438 dos 5.595 presentes) e às categorias presentes em pelo menos 25% dos municípios e não pertencentes ao capítulo XVIII (287 das 1.571). O corte de municípios não é um julgamento sobre relevância: abaixo dele, o perfil é dominado por variação multinomial, e incluir esses municípios adicionaria ruído sem adicionar informação.

Deliberadamente, a tabela publicada **não** é filtrada. O limiar de informatividade é uma escolha analítica, e cravá-la no dado distribuído esconderia essa escolha de quem o baixa. Publicamos a matriz completa e, ao lado, um dicionário com prevalência municipal e marcas por categoria.

### 2.3 Confundidores removidos antes da decomposição

Cada proporção de causa foi regredida linearmente, entre municípios, sobre quatro covariáveis, e o resíduo foi o objeto de toda análise subsequente:

| Covariável | Fonte | Razão |
|---|---|---|
| log₁₀ da população (2022) | IBGE | municípios grandes têm perfil distinto por serem grandes |
| fração com 60 anos ou mais | Censo 2022 | estrutura etária domina qualquer perfil de mortalidade |
| % de causas mal definidas | SIM, 2022–2024 | qualidade do registro varia 23× entre municípios |
| fração de B34 | SIM | COVID-19 foi o maior choque do período |

A estrutura etária entra como característica estática do município, o que é uma aproximação declarada (seção 5).

### 2.4 O modelo nulo

Para cada análise construímos um conjunto de dados nulo com a seguinte propriedade: **preserva tudo o que não é epidemiologia e destrói o que é**. Cada município sorteia, de uma distribuição multinomial sobre a composição nacional de causas, exatamente o mesmo número de óbitos que efetivamente teve. O nulo preserva, portanto, o tamanho do município e a frequência relativa nacional das causas; o que ele elimina é qualquer diferença sistemática entre municípios. Os mesmos quatro confundidores foram removidos do nulo, pelo mesmo procedimento.

Retivemos os componentes cuja variância explicada supera duas vezes a do componente de mesma ordem no nulo.

### 2.5 Agrupamento e sua avaliação

Aplicamos *k-means* sobre os escores dos componentes retidos, para k de 2 a 12. Avaliamos cada k por três medidas complementares:

- **reprodutibilidade** — índice Rand ajustado entre as partições de duas subamostras independentes de 80% dos municípios, na interseção delas, em dez repetições;
- **separação** — silhueta média;
- **ganho sobre o nulo** — razão entre a fração de soma de quadrados não explicada no dado observado e no nulo, no mesmo k.

A distinção entre as duas primeiras é o ponto metodológico central desta seção. Um gradiente contínuo produz partições **altamente reprodutíveis**: o mesmo corte reaparece a cada subamostra porque a direção do gradiente é estável. O índice Rand ajustado, sozinho, não distingue "corte reprodutível" de "grupo real". Quem distingue é a silhueta.

### 2.6 Correlação entre causas

Construímos séries mensais nacionais por categoria (120 pontos, 2015–2024) e removemos de cada uma tendência linear e efeito de mês civil por regressão. Sem essa remoção, 23,3% dos 41.041 pares excedem |r| = 0,5; depois dela, 10,8% — a maior parte da "associação entre causas" que uma análise direta encontraria é sazonalidade compartilhada.

Correlações contemporâneas foram testadas por transformação de Fisher com graus de liberdade ajustados pelo número de termos removidos, e a taxa de descoberta falsa foi controlada pelo procedimento de Benjamini-Hochberg a 1%.

Para a versão com defasagem, calculamos a correlação em *lags* de −6 a +6 meses e registramos, para cada par, o *lag* de |r| máximo. O diagnóstico relevante é a distribuição desses *lags* de pico.

### 2.7 Detecção de desvio do padrão próprio

Para cada célula município × categoria × ano de 2020 a 2024, o valor esperado é a proporção histórica do município (2015–2019) multiplicada pelo total de óbitos do município naquele ano. A proporção histórica sofre **encolhimento bayesiano** em direção à proporção nacional, com peso equivalente a 2.000 óbitos de exposição.

O encolhimento não é refinamento: sem ele, um município sem nenhum óbito de determinada causa no período base tem esperado zero e é excluído do teste — ou seja, exatamente onde a causa **surgiu** é onde ela não pode ser detectada.

O teste é binomial negativa, não z-score. A distribuição normal não aproxima contagens cuja moda é zero, e a variância excede a média. A dispersão φ foi estimada por categoria a partir da variação **ano a ano dentro do mesmo município** no período base (mediana 1,23; percentil 95 igual a 3,38). Uma estimativa alternativa, tomando a média nacional como referência, produz φ próximo de 20 porque absorve como ruído a diferença real entre municípios — que é o sinal, não o erro.

Reportamos dois escores: contra a história própria do município, e o mesmo descontada a variação nacional da categoria naquele ano. Taxa de descoberta falsa controlada a 1% sobre 947.319 testes.

---

## 3. Resultados

### 3.1 A base

**Tabela 1 — Descrição da base analisada.** (`tabela_1_base.csv`)

| Item | Valor |
|---|---|
| Período | 2015–2024 |
| Óbitos não fetais | 14.378.827 |
| Municípios | 5.595 |
| Categorias da CID-10 (3 caracteres) | 1.571 |
| Células município × CID × ano | 3.591.937 |
| Células município × CID × ano × mês | 7.700.720 |
| Óbitos por município-ano (mediana) | 77 |
| Óbitos por município-ano (P25–P75) | 38–170 |
| CIDs informativos | 287 |
| Municípios analisados (≥500 óbitos) | 3.438 |

### 3.2 A COVID-19 está codificada como B34

**Tabela 2 — Óbitos em B34 e U07 por ano.** (`tabela_2_covid_b34.csv`)

| Ano | B34 | U07 | Total | B34 (% do total) |
|---|---|---|---|---|
| 2015 | 91 | 0 | 1.264.175 | 0,01 |
| 2019 | 60 | 0 | 1.349.801 | 0,00 |
| 2020 | 213.233 | 0 | 1.556.824 | 13,70 |
| 2021 | 425.218 | 0 | 1.832.649 | 23,20 |
| 2022 | 66.113 | 0 | 1.544.266 | 4,28 |
| 2024 | 5.414 | 0 | 1.426.346 | 0,38 |

Não há um único registro em U07 em dez anos. O achado é operacional antes de ser interpretativo: qualquer análise que trate B34 pela sua descrição na CID-10 — "doença por vírus de localização não especificada" — e o descarte como código inespecífico terá removido 23,2% de todos os óbitos brasileiros de 2021.

### 3.3 Seis eixos acima do ruído, e quase metade do primeiro era confundidor

**Tabela 3 — Variância explicada por componente.** (`tabela_3_variancia.csv`)

| Componente | Bruto (%) | Residualizado (%) | Nulo multinomial (%) | Razão resid./nulo |
|---|---|---|---|---|
| PC1 | 6,30 | 3,29 | 0,63 | **5,24** |
| PC2 | 2,98 | 2,43 | 0,61 | **3,97** |
| PC3 | 1,95 | 1,86 | 0,61 | **3,04** |
| PC4 | 1,88 | 1,60 | 0,61 | **2,63** |
| PC5 | 1,51 | 1,48 | 0,61 | **2,44** |
| PC6 | 1,41 | 1,30 | 0,60 | **2,17** |
| PC7 | 1,10 | 1,07 | 0,59 | 1,81 |
| PC8 | 0,98 | 1,02 | 0,59 | 1,73 |

Duas leituras importam aqui, e elas puxam em direções opostas.

A primeira: **os quatro confundidores consomem quase metade do primeiro componente** (6,30% → 3,29%). Porte, idade, qualidade do registro e pandemia respondiam por boa parte do que se leria como perfil epidemiológico municipal.

A segunda: **a estrutura sobrevive**. Seis componentes superam duas vezes o nulo. Um leitor que visse apenas "PC1 explica 3,3% da variância" concluiria que não há estrutura alguma; a comparação com o nulo mostra que 3,3% é mais de cinco vezes o que a amostragem sozinha produziria. Nesta matriz, a variância explicada absoluta é uma medida enganosa — é preciso o nulo para interpretá-la.

**Tabela 3b — Categoria contra capítulo, no mesmo desenho.** (`tabela_3b_grao.csv`)

| Grão | Categorias | PC1 observado (%) | PC1 nulo (%) | Razão | Componentes acima de 2× |
|---|---|---|---|---|---|
| Categoria (3 caracteres) | 287 | 3,29 | 0,63 | **5,24** | **6** |
| Capítulo | 20 | 11,05 | 7,05 | **1,57** | **1** |

O contraste é instrutivo. No grão de capítulo — o grão em que a mortalidade municipal costuma ser publicada — o primeiro componente explica **três vezes mais** variância (11,05% contra 3,29%). Mas o nulo correspondente explica 7,05%, porque com apenas vinte categorias a variação multinomial se concentra em poucas dimensões. A razão contra o nulo cai de 5,24 para 1,57, e o número de componentes que sobrevivem cai de seis para um.

Ou seja: **o grão que parece ter mais sinal tem menos.** A variância explicada aumenta por redução de dimensionalidade, não por ganho de informação. Uma análise conduzida em capítulos, avaliada pelo critério usual da variância explicada, pareceria mais bem-sucedida e teria descartado cinco dos seis eixos reais. Essa conclusão é invisível sem o nulo.

### 3.4 Não há grupos discretos

**Tabela 5 — Estabilidade e separação por número de grupos.** (`tabela_5_agrupamento.csv`)

| k | Rand ajustado | Silhueta | SQ não explicada (obs.) | SQ não explicada (nulo) | Razão |
|---|---|---|---|---|---|
| 2 | 0,958 | 0,177 | 0,8205 | 0,9090 | 0,903 |
| 3 | 0,925 | 0,166 | 0,7118 | 0,8444 | 0,843 |
| 4 | 0,868 | 0,155 | 0,6476 | 0,7954 | 0,814 |
| 5 | 0,805 | 0,165 | 0,5966 | 0,7530 | 0,792 |
| 6 | 0,925 | 0,168 | 0,5480 | 0,7170 | 0,764 |
| 8 | 0,698 | 0,165 | 0,4804 | 0,6560 | 0,732 |
| 10 | 0,700 | 0,165 | 0,4327 | 0,6175 | 0,701 |
| 12 | 0,792 | 0,158 | 0,3994 | 0,5848 | 0,683 |

O agrupamento observado é consistentemente mais compacto que o do nulo — a razão fica entre 0,68 e 0,90 em todo o intervalo, ou seja, há estrutura real a ser particionada. Mas as outras duas colunas negam a existência de grupos:

- a **reprodutibilidade é alta** (Rand ajustado 0,93 em k=3), o que isoladamente pareceria confirmar uma tipologia;
- a **separação é baixa em todo k** (silhueta entre 0,155 e 0,177), sem qualquer máximo local;
- a soma de quadrados não explicada **cai monotonicamente sem cotovelo**, de 0,82 a 0,40, sem indicar um k natural.

A combinação de partição reprodutível com silhueta baixa é a assinatura de um **gradiente contínuo**. O mesmo corte reaparece a cada subamostra porque a direção do gradiente é estável, não porque existam agregados separados por vazios. Reportar "três tipos de município" a partir destes dados seria afirmar uma separação que a silhueta nega.

Por essa razão, o produto publicado desta análise são as **coordenadas** dos seis componentes, e o rótulo de grupo acompanha explicitamente marcado como discretização de conveniência.

### 3.5 O primeiro eixo é, em quase um terço, precisão de codificação

As cargas do primeiro componente (Tabela 4, `tabela_4_cargas.csv`) opõem I64, I10, E14 e V29, no polo negativo, a C18, C34, C25 e C43, no positivo. Lida como doença, a oposição seria "cerebrovascular e metabólico" contra "neoplásico". Lida pelo texto da classificação, é outra coisa: **acidente vascular cerebral não especificado como hemorrágico ou isquêmico**, **hipertensão essencial**, **diabetes mellitus não especificado**, **motociclista traumatizado em acidente não especificado** — contra quatro neoplasias de sítio preciso.

O polo negativo é composto de diagnósticos imprecisos. O positivo, de diagnósticos precisos.

Para quantificar, construímos um índice de inespecificidade: a fração dos óbitos do município codificada em categorias cuja descrição na CID-10 contém as marcas *NE* (não especificado), *NCOP* (não classificado em outra parte) ou *SOE* (sem outra especificação), **excluído B34**, que casa com o padrão textual mas é COVID-19 e não imprecisão. O índice vale, na mediana, 0,225 entre os municípios analisados, com percentis 5 e 95 em 0,154 e 0,313.

Já removidos os quatro confundidores — inclusive o percentual de causas mal definidas:

| Correlação | r | r² |
|---|---|---|
| PC1 × índice de inespecificidade | **−0,536** | 0,287 |
| PC2 × índice | −0,151 | 0,023 |
| PC3 × índice | −0,070 | 0,005 |
| % causas mal definidas × índice | **+0,366** | 0,134 |

Dois resultados se somam. Primeiro: **aproximadamente 29% do primeiro componente do perfil municipal de causas é precisão de codificação diagnóstica**, e não perfil de doença. Segundo, e mais consequente: **o indicador clássico de qualidade do registro não captura essa dimensão**. O percentual de causas mal definidas correlaciona apenas +0,37 com o índice; os dois medem coisas distintas. O primeiro mede o balde do capítulo XVIII — o óbito para o qual não se declarou doença alguma. O segundo mede a granularidade de todo o resto: o infarto cerebral codificado como acidente vascular não especificado, o diabetes tipo 2 codificado como diabetes não especificado.

Incluir o percentual de causas mal definidas entre os controles, como fizemos, **não é suficiente**. O eixo de codificação sobrevive a ele.

Sem excluir B34 do índice, a correlação seria −0,565; a exclusão é conservadora e o resultado é robusto a ela.

### 3.6 Os grupos, se descritos, descrevem região e codificação

**Tabela 6 — Caracterização da partição em três grupos.** (`tabela_6_grupos.csv`)

| Grupo | Municípios | Pop. mediana | % 60+ | IVS mediano | % mal definidas | Índice de inespecificidade | Região predominante |
|---|---|---|---|---|---|---|---|
| 0 | 771 | 18.997 | 17,3 | 30,9 | 3,56 | **0,180** | Sul (69,8%) |
| 1 | 1.202 | 19.941 | 16,1 | 47,8 | 5,03 | **0,244** | Nordeste (54,3%) + Norte (17,6%) |
| 2 | 1.457 | 20.131 | 16,3 | 36,2 | 5,38 | **0,231** | Sudeste (54,4%) + Nordeste (38,0%) |

As populações medianas são praticamente idênticas — o porte foi removido pelos controles, como esperado. O que separa os grupos é geografia, vulnerabilidade social e, de forma marcada, o índice de inespecificidade: 0,180 no grupo majoritariamente sulista e de menor vulnerabilidade, contra 0,244 no grupo do Norte e Nordeste.

Este resultado é coerente com a seção anterior e reforça a mesma advertência: uma tipologia de município por perfil de mortalidade apresentada sem o controle de codificação seria, em parte substancial, uma tipologia de qualidade de registro com nomes de doença.

### 3.7 Correlação entre causas: o contemporâneo se sustenta

**Tabela 7 — Pares de maior correlação entre os significativos.** (`tabela_7_correlacao.csv`)

| CID A | CID B | Descrição | r |
|---|---|---|---|
| A90 | A91 | dengue × dengue hemorrágica | **+0,974** |
| C34 | C50 | pulmão × mama | +0,915 |
| J18 | J44 | pneumonia × DPOC | +0,911 |
| F10 | I10 | transtornos por álcool × hipertensão | +0,911 |
| E14 | I10 | diabetes NE × hipertensão | +0,910 |
| G30 | I69 | Alzheimer × sequela cerebrovascular | +0,905 |
| C25 | C34 | pâncreas × pulmão | +0,893 |
| B34 | J12 | COVID-19 × pneumonia viral | +0,882 |

Dos 41.041 pares testados, 20.234 são significativos com controle de taxa de descoberta falsa a 1%.

O **controle positivo é satisfeito de forma inequívoca**: o par de maior correlação de toda a matriz é dengue com dengue hemorrágica, r = +0,974 — o único par sobre o qual se pode afirmar, antes de qualquer análise, que precisa correlacionar. Aparecem também associações negativas fortes de B34 com I21 (infarto agudo do miocárdio, r = −0,90) e N39, compatíveis com substituição de causa durante a pandemia.

Uma ressalva interpretativa é necessária. Vários dos pares mais fortes — F10×I10, E14×I10, F17×I10, E11×I10 — reúnem causas crônicas cuja codificação variou sistematicamente na década, e as mesmas categorias lideram a lista de desvios da seção seguinte. A remoção de tendência é linear e não elimina uma mudança não linear de prática de registro. **A leitura conservadora é que parte destas associações contemporâneas reflete co-deriva de codificação, não co-ocorrência biológica.**

### 3.8 Correlação cruzada com defasagem: achado negativo

A busca do *lag* de |r| máximo em janela de −6 a +6 meses concentra-se em duas regiões: no zero (23.758 dos 41.041 pares) e nas **bordas** da janela (2.209 pares em −6 e 2.204 em +6, contra aproximadamente 1.287 por *lag* intermediário).

Pico na borda de uma janela de busca é assinatura de sobreajuste: nos *lags* extremos, a sobreposição entre as séries é menor, a correlação amostral é mais volátil, e o máximo migra para lá. Não é evidência de precedência temporal.

O exame dos pares nos quais a defasagem produz maior "ganho" sobre o *lag* zero confirma: câncer de cólon precedendo câncer de ânus em cinco meses; câncer de rim precedendo inalação de conteúdo gástrico em seis. São correlações espúrias.

**Conclusão negativa, e a reportamos como tal:** com 120 pontos mensais em séries nacionais agregadas, não é possível sustentar relações de precedência entre causas de morte. A busca por indicadores antecedentes exigiria maior resolução temporal ou desenho longitudinal por unidade, e é uma questão em aberto.

### 3.9 Desvios do padrão próprio

Dos 947.319 testes, 2.167 células apresentam excesso significativo sobre a história própria do município, e 1.648 sobre a história própria descontada a tendência nacional.

**Controle positivo — dengue (Tabela 8c, `tabela_8c_dengue_2024.csv`).** Sinalizada exclusivamente em 2024, o ano da maior epidemia registrada no Brasil (6,56 milhões de casos prováveis contra 1,65 milhão em 2023, segundo o SINAN):

| Município | UF | CID | Óbitos | Esperado | Razão |
|---|---|---|---|---|---|
| São Paulo | SP | A90 | 422 | 6,5 | **64,7×** |
| Guarulhos | SP | A90 | 95 | 2,4 | 40,2× |
| São José dos Campos | SP | A90 | 97 | 3,1 | 31,1× |
| Brasília | DF | A90 | 293 | 15,7 | 18,7× |
| Belo Horizonte | MG | A91 | 93 | 7,6 | 12,2× |

**Controle positivo — COVID-19.** B34 é sinalizada em 74 município-anos, concentrados em 2020–2021.

**O resultado mais relevante, contudo, é outro (Tabelas 8a e 8b).** As categorias mais frequentemente sinalizadas não são epidêmicas:

| CID | Descrição | Município-anos |
|---|---|---|
| N39 | outros transtornos do trato urinário | 171 |
| E11 | diabetes mellitus não insulino-dependente | 109 |
| G30 | doença de Alzheimer | 109 |
| I10 | hipertensão essencial | 103 |
| A41 | outras septicemias | 103 |

E o número de sinais cresce monotonicamente ao longo do período: 203 (2020), 233 (2021), 487 (2022), 600 (2023), 644 (2024). Epidemias não produzem crescimento monótono de cinco anos; mudança de prática de registro produz. Descontada a tendência nacional de cada categoria, o gradiente se atenua substancialmente (205, 299, 359, 389, 396), confirmando que boa parte do crescimento é nacional e não local.

Estas são as mesmas categorias que dominam as correlações contemporâneas mais fortes da seção 3.7, e o mesmo eixo identificado na seção 3.5. **Os três resultados convergem sobre a mesma dimensão: a codificação diagnóstica variou no espaço e no tempo, e essa variação é grande o suficiente para dominar análises de perfil de mortalidade.**

### 3.10 Correlação **dentro de cada grupo**: a resposta difere, e a diferença é o achado

A pergunta do desenho não era pela correlação nacional, e sim: *em cada grupo de municípios, quais CIDs estão correlacionados?* Repetimos o procedimento da seção 3.7 restringindo a série a cada um dos três grupos.

**Tabela 11a — Pares correlacionados por recorte.** (`tabela_11a_correlacao_por_grupo.csv`)

| Recorte | Municípios | Índice de inespecificidade (mediana) | Pares significativos (FDR 1%) |
|---|---|---|---|
| Nacional | 3.430 | — | 20.234 |
| Grupo 0 | 771 | **0,180** | **2.632** |
| Grupo 1 | 1.202 | **0,244** | **7.937** |
| Grupo 2 | 1.457 | **0,231** | **8.636** |

O resultado não é a lista de pares de cada grupo — é a comparação entre as listas. **O grupo de codificação mais precisa tem um terço dos pares correlacionados dos outros dois.** Onde os diagnósticos são específicos, as causas de morte se movem de maneira mais independente; onde são imprecisos, movem-se juntas.

A leitura direta é que boa parte da "associação entre causas" não é co-ocorrência biológica, e sim co-variação da decisão de codificar. Quando o atestante hesita entre dois códigos, as duas séries passam a compartilhar a mesma fonte de variação.

O teste par a par entre grupos (z de Fisher, taxa de descoberta falsa a 1%) confirma que o grupo 0 é o que destoa: 203 pares diferem entre os grupos 0 e 2, 156 entre 0 e 1, e apenas 44 entre 1 e 2.

**Tabela 11b — Onde os grupos mais discordam.** (`tabela_11b_discordancia.csv`)

| Par | Descrição | r no grupo 0 (preciso) | r no grupo 1 (impreciso) |
|---|---|---|---|
| I63 × I67 | infarto cerebral × outras doenças cerebrovasculares | **−0,77** | **+0,38** |
| E14 × I64 | diabetes NE × AVC não especificado | −0,15 | **+0,66** |
| C16 × I67 | neoplasia de estômago × outras cerebrovasculares | −0,09 | +0,66 |
| E11 × I25 | diabetes tipo 2 × doença isquêmica crônica | **+0,68** | −0,17 |
| I10 × I25 | hipertensão essencial × doença isquêmica crônica | +0,43 | −0,38 |
| W17 × Y34 | queda × evento de intenção não determinada | +0,17 | **−0,61** |

O par I63 × I67 é o exemplo mais limpo. No grupo de codificação precisa a correlação é **fortemente negativa** (−0,77): os dois códigos são **substitutos**, e usar um implica não usar o outro para a mesma morte. No grupo impreciso a relação desaparece e inverte de sinal (+0,38), porque a escolha entre eles deixa de ser sistemática.

Praticamente todos os pares discordantes envolvem ao menos um código impreciso — I67, I64, E14, Y29, Y34. Este é, por um caminho inteiramente distinto, o mesmo achado da seção 3.5.

### 3.11 Contexto social como espaço alternativo, e o teste da interpretação concorrente

O desenho previa que a análise não supervisionada usasse mortalidade **ou contexto social**. Executamos também a segunda: quinze variáveis municipais de vulnerabilidade e de sistema de saúde — analfabetismo, domicílios sem água, IVS, cobertura da atenção primária, leitos SUS por mil, gasto próprio em saúde, transferências SUS, receita própria, vínculos de plano de saúde, estabelecimentos e hospitais por 10 mil habitantes, baixo peso ao nascer, prematuridade, pré-natal com sete ou mais consultas e log da população.

**Tabela 9a — Eixos do contexto social.** (`tabela_9a_eixos_sociais.csv`)

| Eixo | Variância | Polo negativo | Polo positivo |
|---|---|---|---|
| SPC1 | 29,5% | plano de saúde, estabelecimentos per capita, gasto próprio | IVS, analfabetismo, cobertura de APS |
| SPC2 | 13,1% | hospitais per capita, pré-natal 7+, gasto próprio | população, sem água, plano de saúde |
| SPC3 | 9,7% | prematuridade, baixo peso, hospitais per capita | pré-natal 7+, receita própria, gasto próprio |
| SPC4 | 9,2% | receita própria, gasto próprio, sem água | leitos SUS, transferência SUS, estabelecimentos |

Os quatro eixos somam 61,5% da variância. O primeiro é o gradiente clássico de vulnerabilidade.

**Tabela 9b — Cruzamento entre os dois espaços.** (`tabela_9b_cruzamento.csv`)

| | SPC1 | SPC2 | SPC3 | SPC4 |
|---|---|---|---|---|
| PC1 mortalidade | **−0,456** | −0,097 | 0,033 | −0,141 |
| PC2 mortalidade | 0,130 | 0,030 | 0,039 | 0,125 |
| PC3 mortalidade | 0,111 | 0,036 | 0,067 | 0,073 |
| PC4 mortalidade | −0,097 | −0,129 | −0,046 | 0,088 |
| PC5 mortalidade | −0,044 | 0,059 | −0,060 | 0,064 |
| PC6 mortalidade | 0,044 | 0,009 | −0,116 | 0,009 |

O maior alinhamento entre os dois espaços é de −0,46, entre o eixo principal de mortalidade e o de vulnerabilidade social — cerca de 21% de variância compartilhada. Os demais cruzamentos ficam abaixo de 0,15.

A leitura é intermediária e importa para o desenho de estudos futuros: **as duas representações não são redundantes nem independentes**. Substituir o perfil de causas pelo IVS perderia quatro quintos da informação; tratá-los como dimensões separadas ignoraria um quinto compartilhado.

#### O teste da interpretação concorrente

A seção 3.5 estabeleceu que o eixo principal do perfil de causas é, em quase um terço, imprecisão de codificação. Restava uma interpretação alternativa legítima: imprecisão diagnóstica pode não ser artefato de registro, e sim **falta de recurso diagnóstico** — sem tomografia não se distingue acidente vascular isquêmico de hemorrágico, e o óbito é codificado como I64.

As variáveis de infraestrutura permitem testar isso diretamente.

**Tabela 10 — O índice de inespecificidade contra o contexto.** (`tabela_10_inespecificidade_contexto.csv`)

| Variável | r com o índice de inespecificidade |
|---|---|
| Taxa de analfabetismo | **+0,558** |
| Índice de vulnerabilidade social | **+0,484** |
| Cobertura da atenção primária (%) | +0,267 |
| **log₁₀ da população** | **+0,012** |
| **Hospitais por 10 mil hab.** | **−0,016** |
| **Leitos SUS por mil hab.** | **−0,094** |
| Pré-natal com 7+ consultas (%) | −0,296 |
| Gasto próprio em saúde por hab. | −0,389 |
| Vínculos de plano por 100 hab. | −0,420 |
| Estabelecimentos de saúde por 10 mil hab. | −0,423 |

O padrão é específico e as **correlações nulas são as mais informativas**. A imprecisão diagnóstica:

- acompanha fortemente **vulnerabilidade socioeconômica** — analfabetismo é o correlato mais forte de toda a lista;
- acompanha, em magnitude semelhante e sinal oposto, a **densidade de atenção ambulatorial e privada** (estabelecimentos per capita, plano de saúde, gasto municipal em saúde);
- é **indiferente a leito hospitalar** (−0,09) e a **hospital por habitante** (−0,02);
- é **indiferente ao porte do município** (+0,01), o que confirma que os controles da seção 2.3 funcionaram.

A ausência de associação com capacidade hospitalar desfavorece a leitura de "falta de equipamento". Se a imprecisão fosse principalmente consequência de não haver tomógrafo ou laboratório para tipificar, esperaríamos gradiente com leitos e hospitais — e ele não existe. O que existe é gradiente com escolaridade da população e com densidade da rede ambulatorial.

Isto **não resolve** a questão de artefato versus acesso: escolaridade e densidade de rede são determinantes tanto da qualidade do registro quanto da saúde da população, e permanecem confundidas. O que os dados sustentam é mais estreito e ainda assim útil: a dimensão existe, é grande, não é explicada por tamanho do município nem por capacidade hospitalar instalada, e não é capturada pelo indicador de qualidade em uso.


---

## 4. Discussão

O desenho proposto foi executado integralmente e produziu três resultados de naturezas diferentes.

**Existe estrutura.** Seis eixos de variação do perfil municipal de causas superam o ruído multinomial por fatores de 2,2 a 5,2, mesmo após remover porte, estrutura etária, qualidade do registro e pandemia. A afirmação é modesta e sólida: a composição de causas difere sistematicamente entre municípios de formas que a amostragem não explica.

**Não existem grupos.** A discordância entre reprodutibilidade alta e separação baixa é informativa, não ambígua. Estudos que reportam tipologias municipais de mortalidade a partir de *k-means* raramente reportam silhueta ao lado do índice de estabilidade; a nossa leitura é que a estabilidade elevada, sozinha, é rotineiramente sobreinterpretada. Um gradiente estável produz partições estáveis.

A implicação prática é direta: para uso posterior — estratificação de análises, seleção de municípios-sentinela, ajuste de modelos —, as coordenadas contínuas são preferíveis a um rótulo categórico, que descarta informação e sugere uma descontinuidade inexistente.

**A codificação é um confundidor de primeira ordem, e o indicador em uso não a mede.** Este é o achado com maior consequência para além deste conjunto de dados. O percentual de causas mal definidas é o indicador padrão de qualidade do registro de óbito, usado para excluir municípios, ponderar análises e sinalizar necessidade de qualificação. Ele mede uma coisa real — o óbito sem doença declarada. Mas correlaciona apenas +0,37 com a granularidade diagnóstica do restante dos registros, e é essa granularidade que domina o eixo principal do perfil municipal.

Um município pode ter percentual baixo de causas mal definidas e, ainda assim, codificar sistematicamente acidente vascular cerebral como I64 em vez de I63/I61, diabetes como E14 em vez de E11, hipertensão como causa básica em vez da complicação que a matou. Nenhum desses óbitos entra no indicador clássico, e todos deslocam o município no eixo principal.

A convergência das três análises sobre a mesma dimensão reforça a interpretação: o eixo aparece na decomposição (seção 3.5), na caracterização dos grupos (3.6), entre as correlações contemporâneas mais fortes (3.7) e no topo das categorias com desvio temporal (3.9).

**Sobre o achado negativo da defasagem.** Reportá-lo importa. A correlação cruzada longitudinal é atrativa porque promete indicadores antecedentes, e a busca sobre uma janela de *lags* quase sempre devolve algo. O diagnóstico do histograma de *lags* de pico — concentração nas bordas — é barato, e recomendamos que acompanhe qualquer análise desse tipo.

**A convergência é a evidência mais forte.** O mesmo eixo aparece por cinco caminhos independentes: nas cargas do primeiro componente (3.5), na caracterização dos grupos (3.6), entre as correlações contemporâneas mais fortes (3.7), no número de pares correlacionados dentro de cada grupo (3.10) e no topo das categorias com desvio temporal (3.9). Nenhum desses caminhos foi construído para achar codificação; todos acharam.

**Limitação da própria conclusão.** Não afirmamos que o eixo de inespecificidade seja *apenas* artefato. Diferenças reais de acesso diagnóstico — a disponibilidade de tomografia que distingue acidente vascular isquêmico de hemorrágico, de laboratório que tipifica diabetes — produzem simultaneamente pior codificação e desfechos distintos. Precisão diagnóstica e qualidade da atenção são parcialmente a mesma coisa. O que o dado sustenta é que a dimensão existe, é grande e não é capturada pelo indicador em uso; separar sua parcela de artefato da de acesso real exige informação que este conjunto não contém.

---

## 5. Limitações

1. **Desenho ecológico.** Todas as unidades são municípios. Nada aqui autoriza inferência sobre indivíduos.
2. **Recorte de municípios.** Os 2.157 municípios com menos de 500 óbitos no período estão fora. Eles não são irrelevantes; seus perfis são estatisticamente indistinguíveis do ruído multinomial neste grão.
3. **Estrutura etária estática.** A fração com 60 anos ou mais vem do Censo 2022 e é aplicada a todo o período. A estrutura etária muda lentamente, mas não é constante ao longo de dez anos.
4. **O índice de inespecificidade depende de texto.** Ele é construído a partir das marcas *NE*, *NCOP* e *SOE* nas descrições da CID-10, não de uma classificação oficial de imprecisão diagnóstica. É uma aproximação transparente, e reprodutível, mas é uma aproximação.
5. **Três caracteres da CID.** O truncamento agrupa códigos que poderiam ser informativos separadamente e, em alguns casos, agrupa categorias heterogêneas.
6. **Migração de residência e local do óbito.** A unidade é o município de residência declarado; deslocamentos para atendimento em outro município não são tratados aqui.
7. **A remoção de sazonalidade é linear e paramétrica.** Uma mudança não linear de prática de registro sobrevive a ela, como discutido na seção 3.7.

---

## 6. Disponibilidade de dados e código

Todas as tabelas derivadas estão publicadas em formato Parquet, com SHA-256 por arquivo e histórico datado imutável, em **saudeemdado.com/dados**, sob licença CC BY 4.0. O código é aberto sob licença MIT.

| Produto | Conteúdo |
|---|---|
| `mart_mortalidade_causa_municipio` | 3.591.937 células município × CID × ano |
| `mart_mortalidade_causa_municipio_mes` | 7.700.720 células, grão mensal |
| `dim_cid10_informativo` | dicionário de 1.571 categorias com prevalência e marcas |
| `mart_perfil_mortalidade_municipio` | coordenadas dos seis componentes, por município |
| `mart_correlacao_causas` | 164.164 linhas: 41.041 pares × 4 recortes (nacional e três grupos) |
| `mart_contexto_social_municipio` | quatro eixos sociais e dez variáveis de contexto, por município |
| `mart_anomalia_causa_municipio` | células sinalizadas, com os dois escores |

Produtores, todos reexecutáveis:

- `scripts/pipeline_mortalidade_causa_municipio.py`
- `scripts/analise_perfil_mortalidade.py`
- `scripts/analise_anomalia_causas.py`
- `scripts/analise_contexto_social.py`
- `artigo/gerar_tabelas.py` — regera todas as tabelas deste manuscrito

A metodologia detalhada, com âncora citável por seção, está em **saudeemdado.com/metodologia**, seção 23.

---

## 7. Notas sobre o que ainda não foi feito

Itens conhecidos e não resolvidos, listados para que não sejam confundidos com decisões:

- a estrutura etária poderia entrar de forma dinâmica, com estimativas anuais por faixa;
- a resolução mensal por município é a única via plausível para reexaminar precedência temporal, e exige tratamento explícito de contagens pequenas;
- a comparação entre grupos usa teste z de Fisher assumindo independência entre os recortes, o que é razoável por serem municípios distintos, mas ignora correlação espacial residual;
- separar artefato de registro de acesso diagnóstico real exigiria informação individual sobre o processo de certificação do óbito, que a base não contém — é a limitação central da seção 3.11.
