# Mortalidade por câncer no Brasil, 2015–2024: um aumento inteiramente demográfico, e um gradiente social que se inverte no colo do útero

**Pedro Paulo Fernandes**¹

¹ Saúde em Dado — saudeemdado.com · ORCID e afiliação a completar

*Coautoria a definir. Este é um rascunho de trabalho preparado a partir do levantamento executado em 2026-09-03.*

---

## Resumo

**Contexto.** O número de mortes por câncer no Brasil cresce ano a ano, e o crescimento é rotineiramente noticiado como avanço da doença. A população brasileira, no mesmo período, envelheceu depressa. Contagem de óbitos e risco de morrer são grandezas diferentes, e num país em transição demográfica elas podem apontar para lados opostos.

**Objetivo.** Separar, na mortalidade por neoplasia maligna registrada no Brasil entre 2015 e 2024, o que é crescimento e envelhecimento populacional do que é mudança de risco; e descrever como o risco remanescente se distribui por idade, sítio do tumor, território e posição social.

**Métodos.** Todos os óbitos por neoplasia maligna (CID-10 C00–C97, causa básica truncada em três caracteres) registrados no Sistema de Informações sobre Mortalidade entre 2015 e 2024, agregados por município de residência, ano, faixa etária e sexo (Tabela 1). Denominador pela Projeção da População do IBGE, revisão 2024, por idade simples. Taxas padronizadas pelo método direto com duas populações padrão — Brasil/Censo 2022 e padrão mundial da OMS —, esta última para permitir comparação externa. O aumento no número de óbitos foi decomposto em três termos — tamanho da população, estrutura etária e taxas específicas por idade — pela média das seis ordens de aplicação. O eixo social usa o microdado nacional de 2022–2023, único recorte em disco que traz cor/raça, escolaridade e local de ocorrência; o denominador por cor/raça vem da tabela 9606 do SIDRA (Censo 2022). O gradiente municipal usa quartis de um índice de vulnerabilidade social construído sobre analfabetismo e falta de água, com análise de sensibilidade por redistribuição pro-rata das causas mal definidas. A razão entre a mortalidade de 60 anos ou mais e a de 15 a 49, por capítulo e por sítio, é reportada em log2 com intervalo exato condicional. Como denominador independente do SIM, o Painel de Oncologia do DataSUS fornece os casos diagnosticados por município e ano de diagnóstico; a razão entre óbitos e casos é reportada bruta, padronizada por idade e sem os sítios C44 e C80, com um critério de refutação por sítio declarado antes da medida.

**Resultados.** Os óbitos por neoplasia maligna passaram de 205.998 em 2015 para 259.084 em 2024, enquanto a taxa padronizada por idade caiu de 123,04 para 120,18 por 100 mil pelo padrão brasileiro e de 84,56 para 81,43 pelo padrão mundial da OMS (Tabela 2). A decomposição atribui +47.314 óbitos ao envelhecimento e +11.390 ao crescimento populacional, contra −5.619 devidos à queda das taxas específicas (Tabela 4): o aumento é integralmente demográfico. A probabilidade de uma pessoa de 30 anos morrer de câncer antes dos 70 caiu de 7,428% para 7,138% (Tabela 16). Mantido o risco de 2019, teriam sido registrados mais 48.543 óbitos entre 2020 e 2024 (Tabela 5), com o déficit encolhendo de 5,3% para 2,1% ao longo do período. O sítio predominante muda com a idade — leucemias e encéfalo na infância, mama e colo do útero entre 30 e 44 anos, brônquios/pulmões e próstata depois dos 60 (Tabela 6). A mortalidade padronizada é maior onde há menos vulnerabilidade: 127,3 por 100 mil no quartil menos vulnerável contra 91,5 no mais vulnerável, com causas mal definidas em 4,09% e 7,24% dos óbitos respectivamente; redistribuídas as mal definidas, o gradiente cai de 39% para 35% e **persiste** (Tabela 9). Entre 23 sítios, seis são mais letais no quartil vulnerável, encabeçados pelo colo do útero (razão 1,27), enquanto o cólon é 0,33 (Tabela 10). O colo do útero é também o segundo sítio mais precoce entre os 43 examinados: a razão em log2 entre a mortalidade dos idosos e a dos jovens é de 1,92, contra 9,11 na próstata (Tabela 19). O mesmo padrão reaparece no recorte individual: a taxa padronizada é 132,7 entre pessoas brancas e 98,3 entre pretas, mas o colo do útero mata 10,54 por 100 mil entre indígenas e 5,73 entre brancas, e a próstata 19,82 entre pretos e 16,54 entre brancos (Tabelas 11 e 12). Os óbitos por caso diagnosticado no Painel de Oncologia sobem monotonicamente com a vulnerabilidade, de 0,494 [0,492–0,495] no quartil menos vulnerável a 0,593 [0,587–0,599] no mais vulnerável, resistindo à padronização por idade (0,495 contra 0,589) e à exclusão de C44 e C80 (0,579 contra 0,686); o viés do diagnóstico privado, com 34,6 vínculos de plano por 100 habitantes no Q1 contra 2,5 no Q4, atua no sentido de subestimar o gradiente (Tabela 20). O teste declarado de antemão para atribuir esse gradiente à detecção **reprovou**: a razão mediana é 1,248 nos sítios de apresentação clínica e 0,963 nos dependentes de rastreamento (Tabela 22).

**Conclusões.** O aumento das mortes por câncer no Brasil não é aumento de risco. O gradiente social da mortalidade registrada aparece invertido em relação à expectativa, e a razão entre óbitos e casos diagnosticados anda no sentido oposto ao dele — padrão compatível com diferença de captação, embora este desenho não estabeleça o mecanismo e o teste desenhado para isso tenha reprovado. Os sítios que dependem de rastreamento — colo do útero acima de todos — resistem a essa inversão e são os candidatos naturais a indicador de equidade oncológica no Brasil. O colo do útero acumula as quatro desigualdades medidas neste trabalho: território, vulnerabilidade municipal, cor/raça e idade ao morrer.

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

### 2.8 A razão idoso/jovem, e o intervalo exato

A §3.3 compara a mortalidade de 60 anos ou mais com a de 15 a 49, por capítulo da CID-10 e por sítio do tumor, em log2.

O recorte tem três decisões declaradas. A faixa jovem **começa aos 15 anos**: abaixo disso o perfil de causa é outro — perinatal, malformação, leucemia da infância — e misturá-lo diluiria exatamente o que a pergunta procura. Há um **intervalo morto de 50 a 59 anos** entre os dois grupos, porque faixas contíguas fazem a razão pender de onde se corta; a última coluna das Tabelas 18 e 19 traz o mesmo cálculo com esses dez anos incluídos no grupo jovem, como sensibilidade. E a faixa idosa é **aberta em 60 ou mais**, de modo que a razão mistura "ocorre mais tarde" com "ocorre em idade muito avançada" — propriedade da pergunta, não defeito, mas necessária para comparar dois capítulos.

A razão é crua dentro de cada faixa, sem padronização interna. Como as duas faixas usam a mesma população para todas as causas, a composição etária interna é idêntica entre capítulos: padronizar deslocaria todos os valores na mesma direção sem alterar o ordenamento, que é o que a pergunta usa.

O intervalo é **exato**, e não normal. Condicionando no total de óbitos das duas faixas, o número de óbitos entre os idosos é binomial, e a razão se obtém da probabilidade dessa binomial por uma transformação fechada; basta então um intervalo de Clopper–Pearson. O método não depende de contagem grande — e por sítio há categorias com poucas centenas de óbitos na faixa jovem, onde a aproximação normal do logaritmo devolveria intervalo simétrico e estreito demais. É o mesmo princípio do intervalo de Fay–Feuer da §2.6: condicionar no que é fixo e usar a distribuição exata do que varia.

### 2.9 O denominador que o SIM não tem

Toda a análise até aqui é de mortalidade, e mortalidade não separa "menos câncer" de "menos diagnóstico". A separação exige um denominador de casos, e a escolha dele é o ponto delicado desta seção.

A **Estimativa de Incidência de Câncer no Brasil**, do INCA, não serve para isso — não por qualidade, mas por construção. O método calcula razões incidência/mortalidade (I/M) nas áreas com Registro de Câncer de Base Populacional de boa qualidade e **aplica essas razões aos óbitos corrigidos do SIM** para estimar os casos onde não há registro [12]. A incidência estimada é, portanto, derivada da mortalidade observada; confrontar uma com a outra seria confrontar o SIM consigo mesmo. Mais importante para o que se pergunta aqui: o método **pressupõe que a razão I/M é geograficamente estável** dentro da região — exatamente a suposição que se gostaria de testar.

O denominador adotado é o **Painel de Oncologia** do DataSUS (`painel_oncologia/Dados/POBR<ano>.dbc`), que registra caso por município de residência e ano de diagnóstico a partir do vínculo determinístico entre a produção ambulatorial, a autorização de procedimento de alta complexidade e o Cartão Nacional de Saúde. Ele erra por motivos próprios, e nenhum deles é o do SIM.

O indicador é **óbitos registrados por caso diagnosticado**, na janela de 2022 a 2024, por quartil de vulnerabilidade municipal. Três decisões o definem:

- **O recorte de causa é o mesmo dos dois lados.** O Painel inclui `D00–D48` — `D48` é o segundo sítio mais frequente de 2023 —, e a análise restringe as duas pontas a `C00–C97`. Sem isso o denominador contaria uma doença que o numerador não conta.
- **A razão sai também padronizada por idade**, com a mesma população padrão aplicada ao numerador e ao denominador, porque os municípios menos vulneráveis são mais velhos e idade eleva a letalidade.
- **`C44` e `C80` entram como sensibilidade, não no principal.** O primeiro é pele não melanoma, de letalidade baixíssima e diagnóstico proporcional à oferta de dermatologista; o segundo é sítio primário não especificado, e um óbito assim codificado é ele mesmo medida de investigação ausente.

O intervalo de confiança usa a mesma construção binomial exata da §2.8, e cabe dizer que ele supõe as duas contagens independentes — o que não são, já que a mesma pessoa pode ser caso de um ano e óbito do seguinte. Entra por convenção; com dezenas de milhares de óbitos em cada quartil, não é o erro amostral que limita a leitura.

**O critério de refutação foi escrito antes de os números existirem.** Se o mecanismo por trás de uma razão maior nos municípios vulneráveis fosse **detecção** — pessoas que nunca foram diagnosticadas —, o efeito teria de ser maior nos tumores cuja descoberta depende de programa de rastreamento ou de imagem, e menor nos que chegam sintomáticos ao serviço de qualquer forma. Se fosse **sub-registro administrativo** — o caso existe e o papel não chega ao Painel —, o efeito seria aproximadamente uniforme entre sítios, porque papelada não distingue pâncreas de mama. A classificação dos sítios nos dois grupos está em `scripts/analise_neoplasias.py` e foi versionada antes da primeira execução da tabela.

### 2.10 O que este desenho não faz

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

### 3.3 Onde o câncer se situa entre as causas, e qual câncer mata cedo

A pergunta "o câncer está matando mais jovens?" tem duas partes, e a §3.1 respondeu só a primeira — a do tempo. A segunda é de posição: quão precoce é o câncer *em relação às demais causas*, e quais tumores puxam essa posição.

A medida é a razão entre a taxa específica de 60 anos ou mais e a de 15 a 49, em log2. Zero significa que a causa mata igualmente nas duas faixas; cada unidade é uma duplicação. O intervalo é exato, condicional no total de óbitos (§2.8).

**Tabela 18. Razão entre a mortalidade de 60 anos ou mais e a de 15 a 49 anos, por capítulo da CID-10, 2022–2024 (`tabela_18_razao_capitulo.csv`).**

| capitulo | Capítulo | Óbitos 15–49 | Óbitos 60+ | Taxa 15–49 | Taxa 60+ | log2 da razão | IC95% | log2 com 50–59 no jovem |
|---|---|---|---|---|---|---|---|---|
| XX | Causas externas de morbidade e de mortalidade | 273.764 | 128.485 | 81,8 | 129,76 | 0,67 | 0,66 a 0,68 | 0,71 |
| XVII | Malformações congênitas, deformidades e anomalias cromossômicas | 3.009 | 1.754 | 0,9 | 1,77 | 0,98 | 0,89 a 1,06 | 0,87 |
| V | Transtornos mentais e comportamentais | 13.923 | 32.553 | 4,16 | 32,88 | 2,98 | 2,95 a 3,01 | 2,45 |
| III | Doenças do sangue e dos órgãos hematopoéticos e transtornos imunitários | 4.640 | 14.103 | 1,39 | 14,24 | 3,36 | 3,31 a 3,41 | 3,06 |
| I | Algumas doenças infecciosas e parasitárias | 47.728 | 193.999 | 14,26 | 195,93 | 3,78 | 3,77 a 3,79 | 3,34 |
| XIII | Doenças do sistema osteomuscular e do tecido conjuntivo | 3.838 | 15.703 | 1,15 | 15,86 | 3,79 | 3,74 a 3,84 | 3,37 |
| XVIII | Sintomas, sinais e achados anormais não classificados em outra parte | 37.237 | 154.490 | 11,13 | 156,03 | 3,81 | 3,79 a 3,83 | 3,32 |
| XI | Doenças do aparelho digestivo | 35.614 | 160.472 | 10,64 | 162,07 | 3,93 | 3,91 a 3,95 | 3,19 |
| II | Neoplasias (tumores) | 86.255 | 558.175 | 25,77 | 563,72 | 4,45 | 4,44 a 4,46 | 3,52 |
| VI | Doenças do sistema nervoso | 16.854 | 141.666 | 5,04 | 143,07 | 4,83 | 4,81 a 4,85 | 4,51 |
| IV | Doenças endócrinas, nutricionais e metabólicas | 21.943 | 218.903 | 6,56 | 221,08 | 5,08 | 5,06 a 5,10 | 4,14 |
| IX | Doenças do aparelho circulatório | 91.877 | 964.588 | 27,45 | 974,18 | 5,15 | 5,14 a 5,16 | 4,18 |
| XII | Doenças da pele e do tecido subcutâneo | 2.385 | 26.982 | 0,71 | 27,25 | 5,26 | 5,20 a 5,32 | 4,41 |
| XIV | Doenças do aparelho geniturinário | 10.788 | 152.716 | 3,22 | 154,23 | 5,58 | 5,55 a 5,61 | 4,77 |
| X | Doenças do aparelho respiratório | 32.272 | 461.311 | 9,64 | 465,9 | 5,59 | 5,58 a 5,61 | 4,8 |

A escala vai de **0,67** nas causas externas a **5,59** nas doenças do aparelho respiratório — de uma causa que mata quase igualmente nas duas faixas a uma que mata 48 vezes mais no idoso. As neoplasias ficam em **4,45** (IC95% 4,44 a 4,46), ou 22 vezes mais no idoso: câncer é, sem ambiguidade, doença de idade avançada, e o aumento de risco descrito na §3.1 não altera essa posição.

Duas leituras merecem registro. A primeira é que **causa externa é o que mata jovem no Brasil**, e por uma margem que nenhuma causa clínica se aproxima: 273.764 óbitos entre 15 e 49 anos no triênio, contra 128.485 entre os de 60 ou mais. A segunda é que os transtornos mentais (2,98) aparecem como a causa clínica mais precoce — posição que, dado o peso do capítulo, merece exame que este trabalho não faz.

Dentro do câncer, porém, a dispersão é quase tão grande quanto entre capítulos.

**Tabela 19. Razão entre a mortalidade de 60 anos ou mais e a de 15 a 49 anos, por sítio do tumor, 2022–2024 (`tabela_19_razao_sitio.csv`).**

| causabas_3 | Sítio | Óbitos 15–49 | Óbitos 60+ | Taxa 15–49 | Taxa 60+ | log2 da razão | IC95% | log2 com 50–59 no jovem |
|---|---|---|---|---|---|---|---|---|
| C81 | Doença de Hodgkin | 731 | 765 | 0,22 | 0,77 | 1,82 | 1,67 a 1,97 | 1,73 |
| C53 | Colo do útero | 8.123 | 9.116 | 2,43 | 9,21 | 1,92 | 1,88 a 1,97 | 1,58 |
| C49 | Tecido conjuntivo e outros tecidos moles | 1.380 | 2.482 | 0,41 | 2,51 | 2,6 | 2,51 a 2,70 | 2,24 |
| C91 | Leucemia linfoide | 1.509 | 3.130 | 0,45 | 3,16 | 2,81 | 2,72 a 2,90 | 2,65 |
| C41 | Ossos e cartilagens articulares | 1.296 | 3.368 | 0,39 | 3,4 | 3,13 | 3,04 a 3,23 | 2,68 |
| C50 | Mama | 13.113 | 34.613 | 3,92 | 34,96 | 3,16 | 3,13 a 3,19 | 2,44 |
| C92 | Leucemia mieloide | 2.582 | 7.116 | 0,77 | 7,19 | 3,22 | 3,15 a 3,29 | 2,89 |
| C83 | Linfoma não-Hodgkin difuso | 624 | 1.811 | 0,19 | 1,83 | 3,29 | 3,16 a 3,43 | 2,88 |
| C71 | Encéfalo | 5.112 | 15.247 | 1,53 | 15,4 | 3,33 | 3,29 a 3,38 | 2,67 |
| C72 | Medula espinhal e outros do sistema nervoso central | 721 | 2.166 | 0,22 | 2,19 | 3,34 | 3,22 a 3,47 | 2,71 |
| C55 | Útero, porção não especificada | 1.077 | 3.431 | 0,32 | 3,47 | 3,43 | 3,33 a 3,53 | 2,76 |
| C38 | Coração, mediastino e pleura | 497 | 1.681 | 0,15 | 1,7 | 3,51 | 3,37 a 3,66 | 2,94 |
| C56 | Ovário | 2.169 | 8.330 | 0,65 | 8,41 | 3,7 | 3,63 a 3,77 | 2,82 |
| C85 | Linfoma não-Hodgkin | 1.456 | 6.428 | 0,44 | 6,49 | 3,9 | 3,82 a 3,98 | 3,31 |
| C95 | Leucemia de tipo celular não especificado | 598 | 2.781 | 0,18 | 2,81 | 3,97 | 3,85 a 4,10 | 3,57 |
| C21 | Ânus e canal anal | 377 | 1.827 | 0,11 | 1,85 | 4,03 | 3,87 a 4,20 | 3,11 |
| C43 | Melanoma maligno da pele | 865 | 4.256 | 0,26 | 4,3 | 4,06 | 3,95 a 4,16 | 3,31 |
| C48 | Tecidos moles do retroperitônio e peritônio | 730 | 3.830 | 0,22 | 3,87 | 4,15 | 4,03 a 4,26 | 3,24 |
| C02 | Outras partes da língua | 553 | 2.936 | 0,17 | 2,96 | 4,16 | 4,03 a 4,30 | 2,89 |
| C10 | Orofaringe | 715 | 4.402 | 0,21 | 4,45 | 4,38 | 4,26 a 4,49 | 2,83 |
| C79 | Metástase em outras localizações | 565 | 3.483 | 0,17 | 3,52 | 4,38 | 4,25 a 4,51 | 3,42 |
| C20 | Reto | 2.063 | 13.090 | 0,62 | 13,22 | 4,42 | 4,36 a 4,49 | 3,36 |
| C16 | Estômago | 5.061 | 32.176 | 1,51 | 32,5 | 4,43 | 4,38 a 4,47 | 3,48 |
| C76 | Outras localizações e mal definidas | 1.731 | 11.533 | 0,52 | 11,65 | 4,49 | 4,42 a 4,57 | 3,39 |
| C19 | Junção retossigmoide | 586 | 4.192 | 0,18 | 4,23 | 4,6 | 4,47 a 4,72 | 3,48 |
| C06 | Outras partes da boca | 311 | 2.462 | 0,09 | 2,49 | 4,74 | 4,57 a 4,92 | 3,31 |
| C18 | Cólon | 4.399 | 35.258 | 1,31 | 35,61 | 4,76 | 4,71 a 4,81 | 3,69 |
| C80 | Sem especificação de localização | 1.601 | 13.055 | 0,48 | 13,19 | 4,78 | 4,71 a 4,86 | 3,69 |
| C64 | Rim | 1.140 | 9.466 | 0,34 | 9,56 | 4,81 | 4,72 a 4,90 | 3,63 |
| C78 | Metástase em órgãos respiratórios e digestivos | 602 | 5.187 | 0,18 | 5,24 | 4,86 | 4,74 a 4,99 | 3,66 |
| C17 | Intestino delgado | 436 | 4.029 | 0,13 | 4,07 | 4,96 | 4,82 a 5,11 | 3,89 |
| C15 | Esôfago | 1.961 | 18.199 | 0,59 | 18,38 | 4,97 | 4,90 a 5,04 | 3,32 |
| C26 | Outros órgãos digestivos e mal definidos | 1.061 | 10.257 | 0,32 | 10,36 | 5,03 | 4,94 a 5,12 | 3,88 |
| C22 | Fígado e vias biliares intra-hepáticas | 2.411 | 26.117 | 0,72 | 26,38 | 5,19 | 5,13 a 5,25 | 3,89 |
| C54 | Corpo do útero | 535 | 5.911 | 0,16 | 5,97 | 5,22 | 5,09 a 5,35 | 3,87 |
| C32 | Laringe | 900 | 10.231 | 0,27 | 10,33 | 5,26 | 5,17 a 5,36 | 3,49 |
| C24 | Outras partes das vias biliares | 601 | 6.848 | 0,18 | 6,92 | 5,27 | 5,15 a 5,39 | 3,97 |
| C25 | Pâncreas | 2.617 | 32.188 | 0,78 | 32,51 | 5,38 | 5,32 a 5,44 | 3,99 |
| C90 | Mieloma múltiplo | 654 | 9.483 | 0,2 | 9,58 | 5,61 | 5,50 a 5,73 | 4,05 |
| C44 | Outras neoplasias malignas da pele | 518 | 9.348 | 0,15 | 9,44 | 5,93 | 5,80 a 6,06 | 4,85 |
| C34 | Brônquios e pulmões | 4.191 | 77.507 | 1,25 | 78,28 | 5,97 | 5,92 a 6,01 | 4,36 |
| C67 | Bexiga | 370 | 14.421 | 0,11 | 14,56 | 7,04 | 6,89 a 7,19 | 5,38 |
| C61 | Próstata | 300 | 49.205 | 0,09 | 49,69 | 9,11 | 8,95 a 9,28 | 6,46 |

O intervalo vai de **1,82** na doença de Hodgkin a **9,11** na próstata — de um tumor que mata 3,5 vezes mais no idoso a outro que mata 550 vezes mais. E o segundo sítio mais precoce de todos, entre os 43 com massa suficiente, é o **colo do útero**: log2 de **1,92** (IC95% 1,88 a 1,97), com 8.123 óbitos entre 15 e 49 anos contra 9.116 entre os de 60 ou mais.

É o mesmo sítio que inverte o gradiente de vulnerabilidade municipal (§3.8), o mesmo que inverte o gradiente de cor/raça (§3.9) e o mesmo cuja mortalidade separa o Amazonas de Minas Gerais por mais de quatro vezes (§3.7). **As quatro desigualdades recaem sobre o mesmo tumor**, e é o tumor com programa de rastreamento.

A mama vem em seguida entre os sítios comuns (3,16), o que fecha a leitura da §3.1: as duas faixas etárias em que o risco subiu na década são justamente aquelas em que os dois cânceres mais precoces dominam a mortalidade.

A última coluna das duas tabelas mede quanto o resultado depende de onde se corta a faixa jovem. Incluindo os 50 a 59 anos no grupo jovem, todos os valores caem — o que é aritmético, já que a faixa acrescentada é mais velha — mas o **ordenamento se preserva**, e é o ordenamento que a pergunta usa.

### 3.4 A decomposição

**Tabela 4. Decomposição do aumento de óbitos entre 2015 e 2024 (`tabela_4_decomposicao.csv`).**

| Componente | Óbitos | % da variação |
|---|---|---|
| Crescimento populacional | 11.390 | 21,5 |
| Envelhecimento (estrutura etária) | 47.314 | 89,1 |
| Risco (taxas específicas por idade) | -5.619 | -10,6 |
| Variação total 2015→2024 | 53.086 | 100 |

O envelhecimento da população responde por 89,1% do aumento e o crescimento populacional por 21,5%; a queda das taxas específicas devolve 10,6%, com sinal negativo. Somados, os dois termos demográficos explicam mais que a totalidade do aumento observado, e o risco atua no sentido contrário.

Não há, nesta série, um componente de "avanço da doença" a ser explicado. Há uma população que envelheceu.

### 3.5 O degrau que a pandemia deixou

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

### 3.6 Cada idade tem o seu câncer

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

### 3.7 O território

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

### 3.8 O gradiente municipal, e o que sobrevive à correção

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

### 3.9 Cor e raça

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

### 3.10 Escolaridade, e onde se morre

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

### 3.11 Óbitos por caso diagnosticado, e o teste que reprovou

Todas as seções anteriores mediram mortalidade. Esta divide a mortalidade pelo número de casos que a assistência oncológica pública registrou no mesmo período, e o resultado anda no sentido oposto ao da taxa.

**Tabela 20. Óbitos por câncer por caso diagnosticado no Painel de Oncologia, por quartil de vulnerabilidade municipal, 2022–2024 (`tabela_20_obito_por_caso.csv`).**

| Quartil | Óbitos | Casos no Painel | Óbitos por caso | Padronizada por idade | Sem C44 e C80 | % com estádio informado | % em estádio III/IV | Planos por 100 hab. |
|---|---|---|---|---|---|---|---|---|
| Q1 (menos vulnerável) | 511.966 | 1.036.847 | 0,494 [0,492–0,495] | 0,495 | 0,579 | 32,9 | 62,1 | 34,6 |
| Q2 | 106.157 | 211.826 | 0,501 [0,497–0,505] | 0,505 | 0,603 | 36,6 | 63,4 | 14,3 |
| Q3 | 71.390 | 123.455 | 0,578 [0,573–0,584] | 0,576 | 0,66 | 39,5 | 64,3 | 5,8 |
| Q4 (mais vulnerável) | 58.054 | 97.939 | 0,593 [0,587–0,599] | 0,589 | 0,686 | 38,7 | 65,9 | 2,5 |
O gradiente é monotônico e vai de **0,494 [0,492–0,495]** no quartil menos vulnerável a **0,593 [0,587–0,599]** no mais vulnerável — cerca de 20% a mais. Os intervalos não se aproximam, o que era esperado com 511.966 e 58.054 óbitos nos extremos, e é por isso que a largura deles não é o que sustenta a leitura.

O que sustenta é o comportamento sob as três perturbações que poderiam desfazê-lo, todas declaradas antes da medida:

- **Idade.** Os municípios menos vulneráveis são mais velhos, e idade eleva letalidade; a padronização deveria, portanto, encolher o gradiente. Ela o move de 0,494/0,593 para **0,495/0,589**, uma diferença de um ponto percentual.
- **Sítios problemáticos.** Retirando `C44` e `C80`, os níveis sobem para **0,579** e **0,686**, e a distância entre os quartis se mantém.
- **Diagnóstico privado.** É o viés mais forte, e ele age **contra** o achado. Quem é diagnosticado fora do SUS não entra no Painel, mas seu óbito entra no SIM — de modo que a razão do quartil menos vulnerável está inflada, não deprimida. A exposição a esse viés é de **34,6** vínculos de plano por 100 habitantes no Q1 contra **2,5** no Q4. No limite aritmético em que todo conveniado escapasse do denominador, a razão verdadeira do Q1 cairia para cerca de 0,32 e a distância entre os quartis mais que triplicaria. O número medido é piso.

**Aqui o teste pré-especificado da §2.9 reprova, e reprova com clareza.**

**Tabela 22. O contraste entre os dois grupos de sítios, definidos antes da medida (`tabela_22_contraste_deteccao.csv`).**

| Grupo pré-especificado | Sítios | Óbitos | Razão Q4/Q1 mediana |
|---|---|---|---|
| apresentação clínica | 7 | 274.614 | 1,248 |
| depende de detecção | 7 | 227.538 | 0,963 |
A previsão era razão maior nos tumores dependentes de detecção. O observado é o inverso: mediana **1,248** entre os sítios de apresentação clínica e **0,963** entre os dependentes de rastreamento ou imagem — ou seja, ausência de gradiente exatamente onde a hipótese de detecção o exigia.

**Tabela 21. Óbitos por caso diagnosticado por sítio do tumor, quartis extremos, 2022–2024 (`tabela_21_obito_por_caso_sitio.csv`).**

| CID | Sítio | Óbitos | Casos | Óbitos/caso Q1 | Óbitos/caso Q4 | Razão Q4/Q1 | Grupo pré-especificado |
|---|---|---|---|---|---|---|---|
| C76 | Outras localizações e mal definidas | 16.159 | 20.795 | 0,547 | 2,883 | 5,274 | não classificado |
| C26 | Outros órgãos digestivos e mal definidos | 13.130 | 4.853 | 2,012 | 9,556 | 4,749 | não classificado |
| C44 | Outras neoplasias malignas da pele | 10.692 | 200.562 | 0,042 | 0,132 | 3,145 | fora do contraste |
| C16 | Estômago | 44.077 | 58.734 | 0,647 | 1,354 | 2,093 | apresentação clínica |
| C22 | Fígado e vias biliares intra-hepáticas | 33.498 | 10.461 | 3,013 | 4,427 | 1,469 | apresentação clínica |
| C53 | Colo do útero | 21.683 | 63.763 | 0,306 | 0,449 | 1,466 | depende de detecção |
| C61 | Próstata | 51.508 | 137.218 | 0,346 | 0,502 | 1,449 | depende de detecção |
| C24 | Outras partes das vias biliares | 8.657 | 3.908 | 2,132 | 3,08 | 1,445 | não classificado |
| C15 | Esôfago | 25.733 | 22.330 | 1,04 | 1,446 | 1,39 | apresentação clínica |
| C34 | Brônquios e pulmões | 93.090 | 42.054 | 2,128 | 2,656 | 1,248 | apresentação clínica |
| C32 | Laringe | 14.001 | 15.321 | 0,883 | 1,099 | 1,245 | não classificado |
| C71 | Encéfalo | 26.190 | 14.809 | 1,714 | 1,984 | 1,157 | apresentação clínica |
| C85 | Linfoma não-Hodgkin | 9.172 | 5.516 | 1,655 | 1,764 | 1,065 | não classificado |
| C25 | Pâncreas | 40.531 | 13.408 | 3,08 | 3,191 | 1,036 | apresentação clínica |
| C20 | Reto | 18.340 | 36.169 | 0,521 | 0,514 | 0,987 | depende de detecção |
| C67 | Bexiga | 15.854 | 23.364 | 0,687 | 0,661 | 0,963 | depende de detecção |
| C50 | Mama | 60.887 | 190.082 | 0,327 | 0,309 | 0,947 | depende de detecção |
| C92 | Leucemia mieloide | 11.495 | 11.810 | 0,997 | 0,944 | 0,947 | apresentação clínica |
| C64 | Rim | 12.775 | 15.072 | 0,872 | 0,823 | 0,943 | depende de detecção |
| C56 | Ovário | 13.226 | 21.584 | 0,65 | 0,566 | 0,871 | não classificado |
| C18 | Cólon | 46.491 | 79.005 | 0,614 | 0,534 | 0,869 | depende de detecção |
| C90 | Mieloma múltiplo | 11.845 | 13.611 | 0,916 | 0,746 | 0,815 | não classificado |
| C80 | Sem especificação de localização | 17.249 | 62.711 | 0,325 | 0,179 | 0,552 | fora do contraste |
O detalhe por sítio mostra por que a mediana do grupo esconde mais do que revela. Entre os dependentes de detecção, colo do útero (**1,466**) e próstata (**1,449**) vão na direção prevista, enquanto mama (**0,947**), cólon (**0,869**), reto (**0,987**), rim (**0,943**) e bexiga (**0,963**) não vão a lugar nenhum. E as duas maiores razões da tabela inteira são `C76` (**5,274**) e `C26` (**4,749**), ambas categorias de **localização mal definida** — um óbito codificado assim já é, em si, medida de investigação diagnóstica ausente, de modo que o topo do ranking é um achado sobre codificação e não sobre biologia.

Há ainda um confundidor que a classificação da §2.9 não previu e que a atravessa: o Painel conta diagnósticos da **mesma janela** dos óbitos. Para tumor rápido — pâncreas, pulmão, fígado, esôfago, estômago — morto e diagnosticado são quase a mesma pessoa; para tumor lento — mama, cólon, próstata —, os óbitos de 2022 a 2024 vêm de casos diagnosticados antes da janela. Os dois grupos pré-especificados estão correlacionados com a velocidade do tumor, e a comparação testa as duas coisas de uma vez. O teste, portanto, não apenas reprovou: ele estava mal construído, e isso só ficou visível depois.

Um resíduo aponta na direção da detecção por via independente, e é fraco. Entre os casos com estádio informado, **65,9%** estão em estádio III ou IV no quartil mais vulnerável contra **62,1%** no menos vulnerável. Mas o campo de estadiamento é preenchido em **32,9%** dos casos no Q1 e **38,7%** no Q4 — proporções que a literatura brasileira de registros de câncer classifica como completude "muito ruim" —, e uma diferença de menos de quatro pontos percentuais medida sobre um terço dos casos não sustenta conclusão. Sustenta uma frase com ressalva, que é o que ela é aqui.

---

## 4. Discussão

### 4.1 O aumento que não é aumento

O resultado central deste trabalho é aritmético e não é novo em epidemiologia; é, no entanto, sistematicamente perdido na comunicação pública. As mortes por câncer no Brasil aumentaram um quarto em dez anos e o risco de morrer de câncer diminuiu. As duas afirmações são verdadeiras simultaneamente porque a população brasileira envelheceu no intervalo, e a decomposição da Tabela 4 mostra que os termos demográficos explicam mais que a totalidade do aumento.

A consequência prática é de planejamento, não de retórica. Um sistema de saúde que precisa dimensionar oncologia enfrenta o número absoluto: são 53 mil mortes por ano a mais que em 2015, com a demanda por diagnóstico, tratamento e cuidado paliativo que isso implica, e essa demanda continuará crescendo mesmo que o risco individual continue caindo. Um sistema que precisa avaliar se sua política de prevenção funciona precisa da taxa padronizada, e ela diz outra coisa.

### 4.2 O gradiente invertido, e por que ele não é uma boa notícia

Municípios menos vulneráveis registram mais mortes por câncer. Pessoas brancas morrem mais de câncer, por 100 mil, que pessoas pretas e pardas. Os dois achados têm a mesma forma e provavelmente as mesmas causas, e nenhuma delas é "menos câncer entre os pobres".

Nada disso é novo, e convém dizê-lo antes de discuti-lo. O gradiente invertido da mortalidade por câncer no Brasil já está descrito: um estudo ecológico em 268 municípios acima de 80 mil habitantes, com óbitos de 2010 a 2012, encontrou as maiores taxas justamente onde a renda e a esperança de vida eram maiores, com correlação positiva com renda e negativa com analfabetismo [10]. E a divisão por sítio que a Tabela 10 reproduz — próstata, mama e cólon acompanhando o nível socioeconômico para cima; esôfago, estômago, laringe e colo do útero para baixo — já aparecia numa revisão de 32 estudos ecológicos publicados entre 1998 e 2008 [11], que também apontava a detecção como explicação candidata, usando a difusão do PSA como exemplo. O que este trabalho acrescenta ao eixo social não é o gradiente: é a década, a cobertura de todos os municípios, o denominador pós-Censo — e, sobretudo, a medida da seção seguinte.

Três mecanismos concorrem. O primeiro é **detecção**: câncer que não é diagnosticado não é codificado como câncer, e os quartis vulneráveis têm quase o dobro da fração de causas mal definidas. A análise de sensibilidade da Tabela 9 limita esse mecanismo, sem eliminá-lo: redistribuir todas as causas mal definidas encolhe o gradiente e o mantém. O segundo é **risco competitivo**: câncer é doença de idade avançada, e populações que morrem antes de outras causas têm menos oportunidade de morrer de câncer — mecanismo que a padronização por idade atenua, porque compara faixas com faixas, mas não elimina, porque opera *dentro* de cada faixa. O terceiro é **exposição diferencial** genuína, de sinal variável por sítio: tabagismo, dieta, obesidade e reprodução distribuem-se de modo desigual e não na mesma direção.

A Tabela 20 permite dizer algo que a mortalidade sozinha não permitia. Para cada caso que a assistência oncológica pública registrou, morre-se cerca de 20% mais no quartil mais vulnerável — gradiente de sentido oposto ao da taxa de mortalidade, robusto à idade, à retirada dos sítios de codificação problemática, e **subestimado** pelo viés do diagnóstico privado. As duas afirmações convivem sem contradição: onde a mortalidade registrada é menor, a razão entre mortes e casos conhecidos é maior. É o padrão que se esperaria se parte da diferença de taxas fosse diferença de captação, e não de doença.

O que a Tabela 20 **não** faz é estabelecer o mecanismo, e o teste desenhado para isso reprovou. Se a captação faltante fosse ausência de diagnóstico, o efeito deveria concentrar-se nos tumores que dependem de programa de rastreamento; ele se concentra nos que chegam sintomáticos (Tabela 22). Três leituras seguem abertas — sub-registro administrativo do caso, mortalidade antes de qualquer contato com o serviço de oncologia, e o descompasso entre casos e óbitos da mesma janela para tumores de velocidades diferentes — e este desenho não as separa. Registrar isso importa mais do que escolher uma: a leitura de detecção é a mais confortável para a tese do artigo, e é justamente a que o teste pré-especificado não sustentou.

Há uma consequência metodológica que independe do mecanismo. A Estimativa de Incidência do INCA aplica razões I/M aos óbitos corrigidos do SIM e supõe essas razões geograficamente estáveis dentro de cada região [12]. A medida da Tabela 20 é um proxy independente dessa razão, e ele varia de modo sistemático com a vulnerabilidade municipal. O proxy tem vieses próprios e não autoriza dizer que a suposição está errada; autoriza dizer que ela é **testável com dado já público**, e que vale testá-la.

O que permite avançar sobre a mistura de mecanismos, sem dado individual de incidência, é o comportamento sítio a sítio. Um efeito puro de detecção produziria gradiente aproximadamente uniforme; o que se observa na Tabela 10 é uma dispersão de razões entre 0,33 e 1,42, com significado clínico legível: os sítios que dependem de exame de rastreamento ou imagem de alta complexidade (cólon, mama, pâncreas, rim, bexiga, reto) concentram-se abaixo de 1, e os que se manifestam clinicamente sem depender de programa organizado de detecção concentram-se perto ou acima de 1.

### 4.3 O colo do útero como indicador de equidade

Entre todos os sítios examinados, o do colo do útero é o que se comporta de maneira mais consistente com desigualdade de acesso, e ele o faz nos três recortes independentes deste trabalho: entre unidades da federação (9,55 no Amazonas contra 2,2 em Minas Gerais, Tabela 8), entre quartis de vulnerabilidade municipal (razão 1,27, Tabela 10) e entre grupos de cor/raça (10,54 entre indígenas contra 5,73 entre brancas, Tabela 12). Os três recortes usam populações diferentes, denominadores diferentes e níveis de agregação diferentes, e apontam na mesma direção.

A coerência importa porque o colo do útero é um caso quase experimental dentro da oncologia: tem etiologia infecciosa estabelecida, vacina disponível, história natural longa o bastante para que a detecção precoce mude o desfecho, e é o único tumor para o qual a Organização Mundial da Saúde definiu uma **meta de eliminação** — incidência abaixo de 4 casos por 100 mil mulheres ao ano, sustentada pelas metas 90–70–90 de vacinação, rastreamento e tratamento até 2030 [3]. Mortalidade elevada por câncer de colo do útero mede, com pouca ambiguidade, ausência de programa alcançando aquela população — e não maior ocorrência da doença por acaso geográfico. É, por isso, o candidato natural a indicador-síntese de equidade oncológica no Brasil, papel que a mortalidade total por câncer não pode cumprir pelas razões da seção anterior.

O achado tem validação externa por uma via independente. A Estimativa de Incidência de Câncer no Brasil para 2023–2025 [4], construída a partir dos Registros de Câncer de Base Populacional e não do SIM, aponta a Região Norte como a de maior incidência de câncer do colo do útero e o registra como **o tumor mais incidente** no Amazonas e no Amapá. Duas bases que não compartilham numerador, denominador nem método concordam em qual unidade da federação está no topo. É a concordância que se esperaria se o sinal fosse doença, e não artefato de codificação do SIM.

Há um quarto recorte, e ele fecha o argumento. Entre os 43 sítios com massa suficiente, o colo do útero é o **segundo mais precoce** do país: a razão entre a mortalidade dos idosos e a dos jovens é de 1,92 em log2, contra 9,11 na próstata e 5,97 no pulmão (Tabela 19). O mesmo tumor que inverte o gradiente municipal, o gradiente de cor/raça e o mapa entre unidades da federação é também aquele que mata mais cedo.

Isso não é coincidência de quatro medidas independentes: é o que se espera de um tumor cuja prevenção depende de um programa que alcança desigualmente. Onde o rastreamento não chega, o câncer de colo do útero não é apenas mais frequente na morte — ele mata mulheres em idade produtiva, e mata as mais pobres, as não brancas e as do Norte. As quatro desigualdades recaem sobre o mesmo alvo, e é o alvo com maior potencial de prevenção conhecido em oncologia.

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
- **O Painel não é registro de câncer, e a razão da §3.11 herda três limites.** O primeiro é de cobertura: quem foi diagnosticado fora do SUS não está no denominador, e o efeito é desigual no território — mas ele deprime a razão do quartil vulnerável em relação ao rico, tornando o gradiente medido um piso. O segundo é que a razão não distingue "nunca foi diagnosticado" de "foi diagnosticado e o registro não chegou ao Painel"; as duas coisas são falhas do mesmo sistema alcançando aquela população, o que basta para um argumento de equidade e não basta para um argumento clínico. O terceiro é o descompasso temporal: numerador e denominador cobrem a mesma janela, e para tumores de evolução lenta os óbitos vêm de casos diagnosticados antes dela, de modo que o nível da razão por sítio não é comparável entre sítios de velocidades diferentes. A comparação que o artigo faz é sempre **entre quartis dentro do mesmo sítio ou do mesmo agregado**, nunca entre sítios.

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
10. Barbosa IR, Costa ICC, Bernal Pérez MM, Souza DLB. Desigualdades socioeconômicas e mortalidade por câncer: um estudo ecológico no Brasil. *Revista Brasileira em Promoção da Saúde*. 2016;29(3):350–356. doi:10.5020/18061230.2016.p350.
11. Ribeiro AA, Nardocci AC. Desigualdades socioeconômicas na incidência e mortalidade por câncer: revisão de estudos ecológicos, 1998-2008. *Saúde e Sociedade*. 2013;22(3):878–891. doi:10.1590/S0104-12902013000300020.
12. Jardim BC, Junger WL, Daumas RP, Azevedo e Silva G. Estimativa de incidência de câncer no Brasil e regiões em 2018: aspectos metodológicos. *Cadernos de Saúde Pública*. 2024;40(6):e00131623. doi:10.1590/0102-311XPT131623.

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
- **~~a razão mortalidade/incidência não foi calculada~~ — parcialmente resolvido nesta versão.** A §3.11 traz óbitos por caso diagnosticado, com o Painel de Oncologia no denominador. Não é razão mortalidade/incidência: o Painel não é registro de câncer, não vê quem foi diagnosticado fora do SUS nem quem nunca chegou a serviço algum. O que fica em aberto é o cruzamento com os Registros de Câncer de Base Populacional, que cobrem parte das capitais e permitiriam calibrar o proxy contra a razão I/M verdadeira nas mesmas áreas — é o passo que transformaria "o proxy varia com a vulnerabilidade" em "a razão I/M varia com a vulnerabilidade";
- **o mecanismo por trás da razão óbito/caso continua indeterminado.** O teste pré-especificado da §2.9 reprovou e, revisto, estava mal construído: a classificação de sítios por dependência de detecção correlaciona-se com a velocidade do tumor, e o Painel conta diagnósticos da mesma janela dos óbitos. Um desenho que separe as duas coisas exige coorte de casos com seguimento — vínculo entre o Painel e o SIM por indivíduo —, e não agregado municipal;
- **a redistribuição das causas mal definidas é pro-rata, e há métodos melhores.** A redistribuição proporcional supõe que os óbitos sem diagnóstico se distribuem como os diagnosticados, o que é conhecidamente conservador para câncer. Métodos de redistribuição baseados em padrões de codificação por idade e sexo dariam correção mais realista, e provavelmente **aumentariam** a taxa corrigida dos quartis vulneráveis mais do que a correção adotada;
- **a diferença entre versões do mesmo ano mediria capacidade de investigação póstuma.** A conversão de causa mal definida em diagnóstico específico entre a versão preliminar e a consolidada do mesmo ano é um instrumento direto para o mecanismo discutido na §4.2, e exige guardar as duas versões de cada ano — prática que o projeto adotou, mas não retroativamente;
- **a comparação com incidência ainda é indireta, e agora dá para tentá-la.** Com a coluna do padrão mundial (Tabela 2) a série deste artigo passou a ser comparável com as publicações do INCA e da IARC. Confrontar a taxa de mortalidade padronizada pelo padrão mundial com a incidência estimada, unidade da federação por unidade da federação, dá uma razão mortalidade/incidência aproximada — inferior ao cálculo com os registros de base populacional, mas disponível hoje e suficiente para ordenar as unidades por letalidade aparente;
- o sítio C44 ("outras neoplasias malignas da pele") lidera a Tabela 10 e não é discutido no texto: a categoria mistura carcinomas de baixa letalidade com tumores agressivos, e sua mortalidade elevada em municípios vulneráveis merece exame próprio, com desagregação que a categoria de três caracteres não permite.
