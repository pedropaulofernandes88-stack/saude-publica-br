# Mortalidade por doenças infecciosas intestinais nos municípios brasileiros, 2015 a 2024: a alta, e o que a ausência de vigilância da qualidade da água não explica

**Pedro Paulo Fernandes**¹

¹ Saúde em Dado — saudeemdado.com · ORCID e afiliação a completar

*Coautoria a definir. Este é um rascunho de trabalho preparado a partir do levantamento executado em 2026-09-12.*

---

## Resumo

**Contexto.** A Lista Brasileira de Causas de Mortes Evitáveis é o instrumento oficial do Ministério da Saúde para classificar óbitos evitáveis por intervenção do SUS. O seu subgrupo 1.2 reúne as causas "reduzíveis por ações adequadas de promoção à saúde, prevenção, controle e atenção às doenças de causas infecciosas", e nele convivem, lado a lado, as **doenças infecciosas intestinais** (A00–A09) e as **infecções respiratórias, inclusive pneumonia e influenza** (J00–J06, J10–J22). A lista não nomeia a água em nenhum subgrupo: não existe categoria de saneamento nela.

**Objetivo.** Medir a evolução da mortalidade por doenças infecciosas intestinais no Brasil entre 2015 e 2024; testar se a alta observada é artefato de registro; e testar se ela se associa à **ausência de vigilância da qualidade da água** — medida pelo Sistema de Informação de Vigilância da Qualidade da Água para Consumo Humano (SISAGUA) — num desenho capaz de separar variação **dentro** do município de variação **entre** municípios.

**Métodos.** Todos os 14.457.218 óbitos não fetais registrados no Sistema de Informações sobre Mortalidade entre 2015 e 2024 com município de residência utilizável (Tabela 1). A **análise primária é um painel**: 5.570 municípios por 9 anos de desfecho, 50.130 linhas município-ano e 1.880.954.497 pessoas-ano (Tabela P1). A exposição é binária e **defasada** — o município não reportou análise alguma ao SISAGUA no ano anterior —, e ocorre em 9.492 linhas município-ano. O estimador é o Poisson condicional de efeitos fixos de município com indicadoras de ano, que absorve todo confundidor constante no tempo, medido ou não; os IC95% vêm de bootstrap de município, com 400 reamostragens. A mesma medida é repetida para **quatro causas-controle**, e quatro critérios de refutação foram escritos no cabeçalho do script antes de qualquer resultado. O desenho transversal da versão anterior — razão de razões entre classes de vigilância, com controle negativo — é mantido e reportado para comparação.

**Resultados.** Os óbitos por A00–A09 passaram de 4.875 em 2019 para 7.177 em 2024 (Tabela P4). Contra uma tendência log-linear ajustada **somente em 2015–2019** — plana, com desvios entre −2,5% e +2,7% —, 2024 está **26,6% acima** quando medido por 10 mil óbitos do ano e **36% acima** quando medido por milhão de habitantes. A alta não é de um código, não é de uma faixa etária e não é redistribuição de causas mal definidas (Tabelas 3 a 5). **No painel, porém, não se observa associação detectável:** o IRR da ausência de vigilância no ano anterior é **0,99 [0,943–1,041]** para A00–A09, e 0,984, 0,996, 1,006 e 1,002 para os quatro controles — nenhum exclui 1 (Tabela P2). Sem o efeito fixo, no mesmo painel e com o mesmo código, o IRR é 1,074 para A00–A09 e **0,773** para o controle respiratório, uma razão de razões de **1,39**; com o efeito fixo, ela cai para **1,006** (Tabela P3). As causas externas, que não partilham caminho hídrico algum, produzem razão de razões de **1,339** sem o efeito fixo. O resultado se mantém nos dez recortes de robustez, inclusive sem o Distrito Federal e sem municípios pequenos (Tabela P5). O desenho transversal, em contraste, produzia razão de razões de 2,075 [1,776–2,518], e a sua aparente dose-resposta é monotônica na coluna do **controle** (0,558; 0,886; 0,903; 1) e não na do desfecho (1,158; 1,351; 1,068; 1) (Tabela 7).

**Conclusões.** A alta da mortalidade por doenças infecciosas intestinais é real, sobrevive a dois denominadores e não é artefato de registro. A hipótese de que a **ausência de registro de vigilância** da qualidade da água a explique não encontra apoio: dentro do município, ao longo do tempo, a exposição não antecede mortalidade detectavelmente maior por nenhuma causa, inclusive a da hipótese. O estimando é o registro anual no SISAGUA, e não a vigilância efetivamente realizada nem a qualidade da água — um município pode analisar e não reportar, e o desenho não separa as duas coisas. A associação transversal é composição entre municípios, e o controle negativo não era neutro — ele carregava associação própria em sentido oposto, que a razão de razões converteu em especificidade aparente. A ausência de registro de vigilância continua útil como **marcador** que identifica municípios, e não como determinante.

**Palavras-chave.** Mortalidade evitável; doenças infecciosas intestinais; vigilância da qualidade da água; SISAGUA; estudos de painel; controle negativo; Brasil.

---

## 1. Introdução

A morte por diarreia é o caso mais antigo da saúde pública. Foi ela que fundou a epidemiologia moderna quando John Snow removeu a bomba de Broad Street em 1854, e é ela que a engenharia sanitária do século XX tratou como problema resolvido nos países que construíram redes de água e esgoto. No Brasil, a mortalidade por doenças infecciosas intestinais caiu de forma sustentada ao longo de décadas, e a literatura nacional descreve essa queda como parte de uma transição epidemiológica em curso — com ressalva para o Norte e o Nordeste, onde ela seria mais lenta.

Este artigo reporta que a queda parou e inverteu, e reporta também que a explicação mais natural para a inversão não resiste ao teste.

O achado tem duas propriedades que merecem enquadramento antes dos métodos. A primeira é que **A00–A09 é uma causa oficialmente evitável no Brasil**: ela está no subgrupo 1.2 da Lista Brasileira de Causas de Mortes Evitáveis, instrumento do Ministério da Saúde publicado em 2007 e revisto entre 2010 e 2011. Não se trata, portanto, de um agravo emergente ou de um desfecho sobre o qual o sistema de saúde não tenha responsabilidade declarada. Trata-se de uma categoria que o próprio Estado brasileiro se comprometeu a reduzir.

A segunda é que **a Lista não nomeia a água**. Percorrida inteira, ela não tem subgrupo de saneamento ambiental. As doenças infecciosas intestinais aparecem sob o rótulo "reduzíveis por ações adequadas de promoção à saúde, prevenção, controle e atenção às doenças de causas infecciosas", ao lado de HIV, tuberculose respiratória, sífilis, doença inflamatória pélvica e infecção do trato urinário. O mecanismo pelo qual essas mortes são evitadas — água tratada e vigiada — não está escrito no instrumento que as declara evitáveis.

Esse silêncio tem consequência operacional. O Brasil mantém, desde 2014, um sistema nacional de vigilância da qualidade da água para consumo humano, o SISAGUA, alimentado pelos municípios. A literatura que usa esse sistema é escassa e trata o não-reporte como limitação de dado: um levantamento de contaminação por agrotóxicos registra que 53% dos municípios não enviaram dados de monitoramento; outro, anterior, que apenas 9% a 17% registravam. Até a busca dirigida realizada em setembro de 2026 — PubMed, SciELO e portais oficiais, descrita na §4.5 — não identificamos trabalho publicado que usasse a **ausência de registro de vigilância como variável de exposição** ligada à mortalidade por doença infecciosa intestinal em escala municipal nacional. A busca não foi sistemática e não demonstra ineditismo; ela delimita o que foi procurado.

É essa inversão que este artigo faz — e o resultado dela é negativo. A pergunta não é "a água está contaminada?", que o SISAGUA não responde onde ninguém mediu. A pergunta é se o município que **deixa de registrar** análises passa a morrer diferente, e a resposta, num painel que acompanha cada município ao longo de nove anos, é que não se observa diferença detectável.

Reportar isso tem valor por duas razões. A primeira é que a alta existe e continua sem explicação: retirar do caminho uma hipótese plausível é trabalho de eliminação, não trabalho perdido. A segunda é metodológica, e é a contribuição que este artigo pretende oferecer com mais confiança que a primeira: um desenho transversal com controle negativo cuidadosamente extraído do instrumento oficial, aprovado em ajuste por acesso à água, em definição estrita do controle e em padronização por idade, produziu uma associação forte, específica e com dose-resposta — **e ela não existe**. A §4.2 mostra por quê, e o motivo é de interesse geral para quem usa controles negativos em epidemiologia ecológica.

---

## 2. Métodos

### 2.1 Fonte e recorte

Todos os óbitos não fetais registrados no Sistema de Informações sobre Mortalidade (SIM) entre 2015 e 2024, agregados por município de residência, ano e categoria de três caracteres da CID-10. O ano de 2025 aparece nas figuras e na Tabela 2 identificado como preliminar, e **não entra em nenhuma estimativa**: ele é mostrado porque omitir o dado mais recente seria esconder informação, e é marcado porque colá-lo à série consolidada afirmaria uma completude que não existe.

O denominador populacional é a Projeção da População do IBGE, revisão 2024, somada sobre os anos do recorte para produzir pessoas-ano.

**Dois totais, e por que eles diferem.** O mart do SIM traz 14.484.496 óbitos no período. Deles, **27.278 estão em 25 códigos do tipo `110000` ou `120000`** — "município ignorado" dentro da unidade da federação. Esses códigos não são municípios: não têm classe de vigilância, não têm população e não podem entrar em nenhuma razão por habitante. Excluídos, restam **14.457.218**, e é sobre esse conjunto que toda estimativa deste artigo é calculada.

A distinção precisa ser explícita porque as duas pontas do funil aparecem no material suplementar: a Tabela 1 traz o conjunto analisável, e a Tabela 2 traz a série anual sobre o mart inteiro. A Tabela 1 mostra o funil completo, com a perda nomeada, justamente para que a diferença não seja lida como inconsistência. A perda no desfecho é pequena — 21 óbitos por A00–A09 e 994 por infecção respiratória — e não se concentra em nenhum ano.

O manuscrito irmão sobre imunoprevenção, que não depende de município, usa o total de **14.484.496**. Os dois números descrevem o mesmo SIM e a mesma versão dos microdados; o que difere é a exigência de município de residência utilizável, que só um dos dois desenhos faz.

### 2.2 O painel, e a exposição defasada

A unidade de análise é o **município-ano**. O painel cobre 9 anos de desfecho (2016 a 2024) para os 5.570 municípios com denominador populacional utilizável, o que dá 50.130 linhas, e é **balanceado**: todos os municípios têm todos os anos. O script aborta se não for, porque supor balanceamento onde ele não existe embaralharia município com ano sem que nada acuse.

A exposição é **binária e defasada**: o município não reportou nenhum mês com análise ao SISAGUA no ano **anterior** ao do óbito. Duas escolhas estão embutidas nessa frase, e as duas são deliberadas.

**Por que defasada.** A vigilância do ano corrente é contemporânea ao desfecho, e a contaminação que mataria em janeiro não pode ser prevenida por uma análise de dezembro. A defasagem de um ano também protege contra causalidade reversa na direção óbvia: surto de diarreia num município pode **provocar** coleta de amostras, e uma exposição contemporânea leria isso como vigilância associada a mais morte.

**Por que binária, e não as quatro classes.** O desenho transversal usava a mediana municipal de meses com análise em quatro classes. Essa medida é definida sobre o período inteiro e, por construção, quase não varia dentro do município — e exposição que não varia dentro do município é apagada inteira pelo efeito fixo. A forma binária por ano é a que tem variação interna: 9.492 das 50.130 linhas (18,9%) estão expostas.

**Ausência de linha é zero, não é ausente.** Município-ano sem registro no mart do SISAGUA entra com zero mês, e não como dado faltante — é exatamente o que "não reportou" significa, e tratá-lo como faltante removeria da análise justamente a categoria de interesse.

**O estimando, dito por extenso.** O que este desenho estima é a razão de taxas de mortalidade associada a **um município não ter registrado nenhuma análise no SISAGUA no ano anterior**, comparado ao mesmo município em anos em que registrou. Não é a razão associada a não haver vigilância, porque um município pode analisar e não reportar; não é a razão associada a água fora do padrão, porque o sistema não mede onde ninguém mediu; e não é efeito causal, porque o desenho é ecológico e o efeito fixo não remove confundimento que varie no tempo dentro do município. O SISAGUA registra controle e vigilância em módulos distintos [7], e a exposição aqui é o ato administrativo de reportar, não a atividade reportada. Erro de classificação não diferencial nessa medida atenua qualquer efeito real em direção a 1, e essa direção é declarada porque ela favorece o resultado obtido.

### 2.3 O estimador, e por que efeito fixo de município

Municípios diferem em tudo: renda, urbanização, estrutura etária, acesso a serviço de saúde, qualidade de codificação de causa básica. Um efeito fixo de município absorve **todo** confundidor que não varia no tempo, medido ou não — é a única forma de controle que não depende de o autor ter pensado na variável certa, e é por isso que ela substitui aqui o ajuste por covariáveis da versão anterior.

O estimador é o Poisson condicional de Hausman, Hall e Griliches (1984). Condicionando na soma de óbitos do município, as contagens dos seus anos seguem uma multinomial cujas probabilidades não contêm o intercepto do município; a verossimilhança condicional não tem, portanto, um parâmetro por município, o que importa num painel de 5.570 unidades. Indicadoras de ano entram no desenho para absorver o que é comum ao país — inclusive a pandemia.

Implementar estimador à mão só se justifica se ele for demonstrado. `tests/test_poisson_fe.py` simula painéis com efeito **conhecido** e exige recuperação dentro de tolerância; um dos testes mostra que o mesmo código **sem** os efeitos fixos devolve viés grande quando a exposição é correlacionada com o nível do município, que é o caso real. Os intervalos de confiança não saem do estimador: vêm de **bootstrap de município**, com 400 reamostragens, porque a unidade de reamostragem tem de ser a unidade de análise.

**O que o efeito fixo cobra.** Ele descarta os municípios cuja exposição nunca muda. Dos 5.570, **3.332 vigiaram em todos os anos** e **400 não vigiaram em nenhum**: esses municípios não contribuem para a estimativa. Ela vem inteira dos **1.838 que mudaram de estado** durante o período (Tabela P1).

Há um segundo desconto, e ele é específico de cada causa. Município cuja contagem total é zero tem multinomial condicional degenerada e também sai da verossimilhança. Para a causa da hipótese, **4.488 municípios têm ao menos um óbito por A00–A09 no período, e apenas 1.468 desses também mudam de exposição** — é esse o conjunto que de fato identifica o IRR, e não os 1.838. Nos controles o desconto é muito menor, porque são causas mais frequentes: 1.835 nas respiratórias, 1.837 nas isquêmicas e 1.838 nas causas externas (Tabela P1). Reportar apenas quem muda de exposição superestimaria a informação disponível justamente na causa que importa, e essa distinção não se lê no intervalo de confiança sozinho.

### 2.4 Os quatro critérios, declarados antes

Os critérios foram escritos no cabeçalho de `scripts/analise_agua_painel.py` antes de qualquer resultado ser observado, e o script imprime o veredito sozinho ao final:

> **Critério 1 — especificidade.** A mesma medida é repetida em cinco grupos de causa: a hipótese (A00–A09), o controle respiratório do mesmo subgrupo 1.2, as demais infecciosas do subgrupo, as isquêmicas do coração e as causas externas. Se o IRR da hipótese não excluir 1, **ou** se não for maior que o de todos os controles, a leitura hídrica está refutada e o achado é sobre fragilidade geral de sistema.
>
> **Critério 2 — o que o efeito fixo remove.** O mesmo IRR é estimado com e sem o efeito fixo de município, sobre o mesmo painel. A diferença é a parte da associação atribuível a diferenças fixas entre municípios.
>
> **Critério 3 — tendência.** A série nacional é projetada a partir de uma tendência log-linear ajustada **somente em 2015–2019**, em dois denominadores, e o excesso de cada ano posterior é reportado como estiver.
>
> **Critério 4 — robustez.** O IRR da hipótese é recalculado sem o Distrito Federal, sem municípios com menos de 5.000 habitantes, sem os dois, e dentro de cada região.

Os dois denominadores do critério 3 existem porque nenhum dos dois basta. A proporção dos óbitos do ano cancela sub-registro e é frágil à pandemia, que inflou o divisor com COVID-19; a taxa por habitante é o contrário. Se as duas apontarem na mesma direção, a conclusão não depende de qual o leitor prefere.

### 2.5 O desenho transversal, mantido para comparação

A versão anterior deste trabalho mediu a mesma pergunta com um desenho transversal, e ele é preservado no material suplementar (Tabelas 6 a 11) porque a comparação entre os dois **é** um dos resultados.

Nele, a exposição é a mediana municipal de meses com análise em quatro classes, de "sem vigilância" (384 municípios) a "vigilância regular" (3.627).

**Por que 384 aqui e 400 na §2.3.** Os dois números contam municípios que nunca reportaram, em janelas diferentes. O desenho transversal olha o período inteiro, 2015 a 2024; o painel olha a janela **defasada**, 2015 a 2023, porque a exposição de um ano é a vigilância do anterior e 2024 não é exposição de ano nenhum dentro do recorte. O conjunto menor está contido no maior, e a diferença são 16 municípios que reportaram pela primeira vez em 2024. Nenhum dos dois números está errado; o que seria errado é apresentá-los sem dizer que contam coisas diferentes. A medida é a **razão de razões** entre a mortalidade por A00–A09 e a mortalidade pelo controle negativo — as infecções respiratórias do mesmo subgrupo 1.2, que partilham pobreza, desnutrição, acesso a serviço, qualidade de codificação e estrutura etária com o desfecho, e não partilham o caminho hídrico. O contraste não é entre duas causas que os autores escolheram parecidas: é entre duas entradas que o instrumento oficial trata como equivalentes.

Esse desenho foi submetido a três critérios pré-declarados e a um teste post-hoc — ajuste por quartil de acesso à água pelo Censo 2022, definição estrita do controle e padronização por idade —, **e passou em todos** (Tabela 8). A §3.7 e a §4.2 explicam por que isso não bastou.

---

## 3. Resultados

### 3.1 A alta, em dois denominadores

Os óbitos por doenças infecciosas intestinais passaram de 4.875 em 2019 para 7.177 em 2024 (Tabela P4). Medidos por 10 mil óbitos do ano, foram de 36,12 para 46,85; por milhão de habitantes, de 23,45 para 33,76.

A tendência de 2015 a 2019 é plana. Ajustada log-linearmente apenas nesse intervalo, ela deixa resíduos entre −2,5% e +2,7% na medida por óbitos e entre −3,3% e +4,1% na medida por habitante — ou seja, o período pré-pandêmico não tem inclinação que projete a alta posterior.

Contra essa projeção, 2020 e 2021 ficam abaixo, e o tamanho da queda depende do denominador: −27% e −40,1% por óbitos do ano, contra −16,7% e −20,4% por habitante. A diferença é o efeito esperado da COVID-19 sobre o divisor, e é a razão de reportar as duas séries. As duas convergem em direção a partir de 2023, e em 2024 ficam **+26,6% por óbitos do ano e +36% por habitante** (Figura P3). Os dois denominadores concordam de sinal em todos os anos; o que muda entre eles é a magnitude, e ela difere mais em 2022 — −11,6% por óbitos do ano contra −2,1% por habitante —, ano em que a COVID-19 ainda inflava o total de óbitos que serve de divisor à primeira medida.

### 3.2 A alta não é artefato de registro

A alta não é de um código (A04 +72%, A08 +120%, A09 +40,9%; Tabela 4), não é de uma faixa etária (Tabela 3) e não é redistribuição de causas mal definidas: nos 946 municípios em que a proporção de mal definidas **não caiu** entre 2019 e 2024, a alta foi de **+43,5%**, contra +49,4% onde caiu (Tabela 5). Se a alta fosse reclassificação, ela deveria concentrar-se onde as mal definidas recuaram, e não é o que se observa.

### 3.3 No painel, não se observa associação detectável (critério 1)

O IRR da ausência de vigilância no ano anterior sobre a mortalidade por A00–A09 é **0,99, com IC95% de 0,943 a 1,041** (Tabela P2, Figura P1). O intervalo contém 1 e é estreito: com 45.060 óbitos pela causa da hipótese e 1.468 municípios que mudam de exposição e têm óbito pela causa, o intervalo é estreito por informação, e não por acaso.

Os quatro controles dão 0,984 [0,955–1,013] para as respiratórias do subgrupo 1.2, 0,996 [0,973–1,02] para as demais infecciosas do subgrupo, 1,006 [0,982–1,034] para as isquêmicas do coração e 1,002 [0,977–1,023] para as causas externas. Nenhum exclui 1, e o maior de todos é o das isquêmicas — isto é, a causa da hipótese não só não se afasta de 1 como **não é a que mais se afasta**.

O critério 1 exigia as duas coisas. Ele está reprovado, e o script imprime a reprovação.

**O que o intervalo exclui, e o que ele não exclui.** Um intervalo que contém 1 não é evidência de ausência de associação; é ausência de evidência de associação **da magnitude que o desenho consegue detectar**. O intervalo vai de 0,943 a 1,041, e são esses dois limites que delimitam a leitura: efeitos maiores que eles são incompatíveis com estes dados, e efeitos menores que eles não são descartados. Se uma razão de taxas dentro dessa faixa for considerada relevante em saúde pública, este trabalho não a exclui.

Nenhuma margem de equivalência foi pré-declarada, e por isso o resultado **não** é apresentado como demonstração de equivalência. Ele é apresentado como o que é: a associação forte que o desenho transversal media — razão de razões de 2,075 — não sobrevive ao confronto com a variação dentro do município, e isso é afirmação sobre aquela associação, não sobre a existência de qualquer efeito.

### 3.4 O que o efeito fixo remove (critério 2)

Estimado sem o efeito fixo de município, sobre o mesmo painel, com o mesmo código e o mesmo dado, o IRR da exposição é **1,074** para A00–A09 e **0,773** para o controle respiratório. A razão de razões implícita é **1,39**. Com o efeito fixo, os dois vão para 0,99 e 0,984, e a razão cai para **1,006** (Tabela P3, Figura P2).

A direção do movimento é o resultado. As quatro causas que não são a hipótese estavam **abaixo** de 1 sem o efeito fixo — 0,773, 0,847 e 0,858 —, e sobem para junto de 1 quando ele entra. Sem efeito fixo, o município que não vigia a água aparenta ter **menos** morte respiratória, menos outras infecciosas e menos isquêmica do coração. Isso não é proteção: é composição — municípios menores, mais jovens, com menos diagnóstico hospitalar e menos certificação de causa.

A razão de razões converteu esse déficit do denominador em excesso aparente do numerador. E a prova de que a conversão não tinha nada de específico está na última linha da tabela: as **causas externas** — acidentes de transporte, quedas, homicídios e suicídios, que não partilham caminho hídrico com nada — produzem razão de razões de **1,339** contra o mesmo controle respiratório, quase tanto quanto a hipótese.

### 3.5 A tendência (critério 3)

Reportada na §3.1 e na Tabela P4. A alta é real e não depende do denominador; o critério não a refuta.

### 3.6 Robustez (critério 4)

O resultado não se move. Sem o Distrito Federal, 0,989 [0,94–1,036]; sem os municípios com menos de 5.000 habitantes, 0,994 [0,947–1,038]; sem os dois, 0,993 [0,943–1,051]. Por região, os cinco intervalos contêm 1: Centro-Oeste 0,925, Nordeste 1,008, Norte 1,01, Sudeste 0,979 e Sul 0,848 (Tabela P5, Figura P4). Os dois extremos regionais são também os de intervalo mais largo, o que é o esperado com 467 e 1.191 municípios.

A exclusão do Distrito Federal merece nota porque ela foi pedida na revisão do desenho anterior, onde o DF é uma unidade com quase três milhões de habitantes classificada como um único município. No painel, retirá-lo move o IRR de 0,99 para 0,989.

**O denominador municipal, e o recorte que ele exige.** O *offset* do painel é a população municipal, e essa série troca de base em 2022: estimativas anuais até 2021, Censo em 2022, interpolação em 2023. A parte da troca que é comum ao país é absorvida pelas indicadoras de ano; a parte que é própria de cada município — e o Censo reviu municípios em direções diferentes — não é, e vira erro de medida no *offset*. Não existe série municipal harmonizada com que reconstruir o denominador, de modo que o que cabe é medir a dependência: removidos 2022 e 2023, o IRR é **0,988 [0,939–1,045]**, contra 0,99 [0,943–1,041] no painel completo (Tabela P5). A troca de base não explica o resultado.

A série **nacional** da §3.1, que não tem efeito fixo para absorver a emenda, foi reconstruída sobre a Projeção da População do IBGE, Revisão 2024, reconciliada com a Pesquisa de Pós-Enumeração [9] — a mesma série que os trabalhos irmãos deste repositório adotam. A diferença não é acadêmica: com a série remendada, 2022 aparecia acima da tendência; com a série oficial, aparece abaixo.

A verificação que a análise faz sobre essa série merece registro, porque a primeira versão dela era insuficiente de um modo instrutivo. Conferir **continuidade** — abortar se a variação anual passar de 2% — detecta a emenda entre Censo e projeção, mas não distingue duas séries suaves de revisões diferentes: uma tentativa intermediária de conserto usou a projeção de 2018, anterior ao Censo, que é perfeitamente contínua e passou na conferência. A análise passa a conferir **procedência**, comparando os totais nacionais contra valores-âncora publicados da Revisão 2024; a projeção de 2018 é reprovada por essa comparação. Suavidade de curva não é identidade de fonte.

### 3.7 O que o desenho transversal media

O desenho transversal produzia razão de razões de **2,075 [1,776–2,518]**, ajustada por acesso à água 1,926 [1,618–2,225], com controle estrito 2,087 [1,785–2,535] e padronizada por idade 1,767 [1,518–2,021] — todas excluindo 1 (Tabela 8). Ele também produzia gradiente aparentemente monotônico entre as quatro classes de vigilância: 2,075, 1,525, 1,182 e 1.

A Tabela 7 mostra de onde vinha esse gradiente. A coluna do **controle** é perfeitamente ordenada — 0,558, 0,886, 0,903 e 1 —, e a coluna do **desfecho** não é: 1,158, 1,351, 1,068 e 1. O maior risco relativo de mortalidade intestinal está na classe de vigilância *rara* (1,351), e não na de vigilância nenhuma (1,158). A dose-resposta que o desenho apresentava como apoio à hipótese hídrica era a dose-resposta do controle negativo.

---

### 3.8 Quando a exposição deixa de ser papelada (extensão exploratória)

A objeção mais forte ao resultado acima é que a exposição mede um ato
administrativo. Um município pode analisar a água e não reportar, e o desenho
não separa as duas coisas — de modo que um nulo poderia ser apenas erro de
classificação da exposição.

Esta seção testa a versão da pergunta que não tem essa saída. Entre os
município-anos em que **houve** amostra analisada e reportada, a exposição passa
a ser o **resultado** do laboratório: encontrou-se *Escherichia coli* na água
distribuída no ano anterior, ou não. O estimador, os cinco grupos de causa e o
bootstrap são os mesmos.

O recorte é condicional a reportar, e essa seleção é parte do estimando: são
5.170 municípios e 40.638 linhas município-ano, contra os 5.570 e 50.130 do
painel principal, e nada nesta seção se aplica a quem não reporta. Em 8.791
linhas — 21,6% — houve detecção. O conjunto que identifica o efeito é maior que
o do painel principal: 2.343 municípios mudam de estado de detecção **e** têm
óbito por A00–A09, contra 1.468 lá (Tabela E1).

**O resultado é o mesmo.** O IRR da detecção de *E. coli* sobre a mortalidade
por A00–A09 é **0,991 [0,944–1,037]**, e os quatro controles dão 1,009, 0,995,
1,018 e 0,997 — nenhum exclui 1, e o maior de todos é novamente o das isquêmicas
do coração (Tabela E2, Figura E1). Sem o efeito fixo de município, a associação
das demais infecciosas do subgrupo 1.2 sobe para 1,207 e colapsa para 0,995 com
ele, repetindo o padrão de confundimento entre municípios da §3.4 (Tabela E3).

Um artefato previsível foi testado e não é o caso: quem coleta mais amostras
encontra mais *E. coli* por acaso, e incluir o logaritmo do número de amostras
analisadas no desenho move o IRR da hipótese de 0,991 para 0,985, sem mudar de
direção em nenhum dos cinco grupos (Tabela E4). A robustez também não se move
(Tabela E5).

**Esta extensão é exploratória e não pré-especificada.** Ela foi concebida
depois de observar o resultado do painel principal, a partir de uma auditoria
externa; os seus quatro critérios foram escritos antes de qualquer número dela
ser calculado, o que não é a mesma coisa que pré-especificação anterior aos
dados, e vai dito com essas palavras.

O que ela acrescenta é a remoção de uma explicação alternativa. O nulo do painel
principal poderia ser erro de medida na exposição administrativa; aqui a
exposição é a medida, e o nulo persiste.

## 4. Discussão

### 4.1 O que foi medido, e o que foi refutado

Entre 2015 e 2019 a mortalidade brasileira por doenças infecciosas intestinais foi estável; em 2024 ela está entre 26,6% e 36% acima do que essa estabilidade projetava, conforme o denominador. A alta sobrevive ao exame das explicações alternativas de registro conhecidas e permanece **sem explicação identificada**.

A hipótese de que a **ausência de registro de vigilância** da qualidade da água a explique não encontra apoio nestes dados. Ela foi testada no desenho com maior poder de controle de confundimento disponível para dado municipal brasileiro — efeito fixo de município, que absorve todo confundidor constante no tempo sem exigir que ele tenha sido medido ou sequer imaginado — e o resultado é um intervalo estreito em torno de 1, replicado em dez recortes e indistinguível do obtido em quatro causas-controle.

Três distinções impedem que isso seja lido como refutação da hipótese hídrica em geral. A primeira é que a exposição medida é o **registro**, e não a vigilância nem a qualidade da água (§2.2). A segunda é que a defasagem testada é de um ano: um mecanismo que opere em prazo maior — deterioração de infraestrutura ao longo de anos — não aparece num desenho com indicadoras anuais. A terceira é que um intervalo que contém 1 delimita magnitudes, e não demonstra ausência (§3.3). O que está refutado é uma coisa mais estreita e bem definida: que a associação de 2,075 medida entre municípios reflita um efeito da exposição, porque ela não reaparece quando cada município é comparado consigo mesmo.

### 4.2 A lição sobre controle negativo

Esta é a parte do artigo cuja generalidade excede o seu objeto.

O controle negativo foi escolhido pelo melhor motivo disponível: o instrumento oficial brasileiro declara as duas causas evitáveis pelo mesmo tipo de ação, o que elimina a suspeita de que os autores tenham selecionado um comparador conveniente. Ele partilha com o desfecho pobreza, desnutrição, acesso a serviço e qualidade de codificação, e não partilha o caminho hídrico. É exatamente o que a literatura de controles negativos recomenda.

Ele ainda assim falhou, e falhou de um modo que nenhum dos três critérios pré-declarados podia detectar: **o controle carregava associação própria, em sentido oposto ao do desfecho.** A razão de razões pressupõe que o controle seja neutro em relação à exposição — que o seu risco relativo seja 1 na ausência de efeito. Quando ele é 0,558, a razão de razões não mede a especificidade do desfecho: ela mede a soma de dois desvios, e atribui os dois ao numerador.

Três consequências práticas decorrem disso, e nenhuma delas depende deste artigo ser sobre água.

**Primeira: reportar sempre as duas razões separadamente, e não apenas a sua divisão.** Aqui, 1,158 e 0,558 estão na Tabela 7 desde a primeira versão, e a inspeção da coluna teria mostrado que o controle se afastava de 1 mais do que o desfecho. O número composto escondia o que as suas partes diziam.

**Segunda: um controle adicional que não partilhe nada.** As causas externas entraram neste trabalho como quarta causa-controle e produziram razão de razões de 1,339 contra o mesmo comparador, sem efeito fixo. Um desenho que inclua uma causa reconhecidamente sem relação com a exposição converte a falha silenciosa em falha visível: se ela também "responde", o problema é do comparador.

**Terceira: passar em testes de sensibilidade não é evidência de validade quando todos eles compartilham o mesmo desenho.** O ajuste por quartil de acesso, a definição estrita do controle e a padronização por idade foram concebidos honestamente e aprovados com folga. Os três são variações do mesmo contraste entre municípios, e nenhum deles podia detectar o que estava errado nesse contraste. A robustez que eles mediram era real e irrelevante.

### 4.3 O que este desenho não autoriza

O painel não autoriza afirmar que a vigilância da água **não tem efeito** sobre mortalidade por diarreia. Ele autoriza afirmar, com o poder que 1.468 municípios informativos conferem, que **a ausência de registro anual no SISAGUA não antecede aumento detectável de mortalidade por A00–A09 dentro do município**. As duas frases diferem, e três limitações explicam por quê.

A exposição é ausência de **registro**, não ausência de vigilância: um município pode analisar e não reportar. A medida capta o ato administrativo, e um efeito real da vigilância diluído por erro de classificação apareceria atenuado. A defasagem adotada é de um ano; se o mecanismo operar em prazo maior — deterioração de infraestrutura ao longo de anos —, um efeito fixo com indicadoras de ano não o vê. E o desenho continua **ecológico**: nada aqui autoriza afirmar coisa alguma sobre a pessoa que morreu.

Por fim, um nulo num painel de efeitos fixos não exclui confundimento que **varie no tempo** dentro do município na direção oposta ao efeito. Essa é a limitação simétrica da força do método, e é honesto declará-la.

### 4.4 A lacuna no instrumento

O achado secundário sobre a Lista Brasileira sobrevive à refutação da hipótese hídrica, porque não dependia dela. A Lista classifica as doenças infecciosas intestinais como evitáveis e as agrupa sob "promoção à saúde, prevenção, controle e atenção às doenças de causas infecciosas", ao lado de HIV, tuberculose e infecção urinária. O mecanismo pelo qual a morte por diarreia é evitada — água tratada e saneamento — **não aparece em nenhum subgrupo da lista**.

Isso importa além da nomenclatura. Um instrumento de mortalidade evitável é lido como agenda: ele diz ao gestor onde a morte pode ser impedida e por qual via. Ao não nomear o saneamento, a Lista deixa a resposta à morte por diarreia dentro do vocabulário da atenção à saúde, quando parte do determinante é de infraestrutura, exercida por outro setor e com outro orçamento.

Esta observação é irmã de outra, já reportada em trabalho anterior dos mesmos autores sobre o subgrupo 1.1 da mesma Lista, cujo conteúdo descreve o calendário vacinal de 2010. Os dois achados apontam para o mesmo lugar por caminhos diferentes — um instrumento que envelheceu no conteúdo, e outro que é silencioso quanto ao mecanismo.

### 4.5 Relação com a literatura

A literatura brasileira que relaciona saneamento e mortalidade por diarreia usa, como exposição, o **acesso** à infraestrutura. Um trabalho próximo em desenho — ecológico, com 3.467 municípios e binomial negativa [3] — mede acesso à água, esgoto e coleta de resíduos combinados a transferência condicionada de renda, restringe o desfecho a menores de 5 anos e termina a série em 2016. Outro, de cobertura municipal nacional, analisa a prevalência de diarreia grave contra características domiciliares e conclui que a gestão de resíduos pesa mais que água e esgoto [4] — um resultado que este artigo não contradiz e que reforça a cautela contra atribuir ao caminho hídrico o que pode ser de outro caminho ambiental. Outro estudo relaciona investimento em saneamento a internações por doenças de veiculação hídrica em nível estadual. Uma avaliação da vigilância na região metropolitana do Rio de Janeiro correlacionou achados microbiológicos do SISAGUA com prevalência de protozoose intestinal, sem desfecho de mortalidade.

O uso do SISAGUA é raro. Uma busca no PubMed recupera doze artigos que o mencionam; deles, dois ligam o sistema a um desfecho de saúde — cárie dentária por cobertura de fluoretação, e mortalidade por câncer em 203 municípios da bacia do Rio Doce após o rompimento da barragem de Fundão. Os demais descrevem o sistema, avaliam completude de dados ou reportam contaminação química.

Vários desses trabalhos registram o não-reporte como **limitação**. Este artigo o tratou como **exposição** e mediu o resultado: no contraste entre municípios ele produz associação forte, e dentro do município ele não produz nenhuma. Ambas as metades são contribuição, e a segunda é a que faltava.

### 4.6 Implicações

A implicação operacional muda de natureza com o resultado. Os municípios sem registro de vigilância continuam sendo um conjunto identificável e nominal, distribuído por unidade da federação na Tabela 10, e continuam morrendo mais de doença infecciosa intestinal do que os que vigiam — mas a diferença não reaparece quando cada município é comparado consigo mesmo ao longo do tempo, o que é compatível com ela ser característica desses municípios e não consequência da falta de registro. Isso preserva o valor **diagnóstico** da ausência de reporte, como sinalizador de municípios cuja mortalidade por causa evitável se comporta de modo anômalo, e retira o apoio que o desenho anterior daria a uma leitura **causal** dela.

E deixa em aberto a pergunta que o artigo abriu e não fechou: por que a mortalidade por uma causa oficialmente evitável, estável por cinco anos, está em 2024 mais de um quarto acima do que essa estabilidade projetava. Responder a isso exige exposição que varie dentro do município e seja medida com menos ruído administrativo do que o ato de reportar ao SISAGUA.

---

## 5. Material suplementar

As dezesseis tabelas que sustentam cada número deste manuscrito estão publicadas como material suplementar, em CSV. As cinco do painel (`tabela_pN`) vêm de `scripts/analise_agua_painel.py` e são transportadas por `artigo-agua/gerar_tabelas_painel.py`, que confere as colunas que o texto cita; as onze do desenho transversal (`tabela_N`) são regeradas por `artigo-agua/gerar_tabelas.py`, que **reexecuta a análise** antes de formatar. As nove figuras saem dos dois geradores correspondentes, sem nenhum cálculo próprio.

Os dados primários — o mart municipal do SISAGUA (397.380 linhas) e a sua tabela de cobertura (5.571 linhas, uma por município do país) — estão publicados com SHA-256 e são citáveis. A nota técnica da Lista Brasileira usada para transcrever o subgrupo 1.2 está arquivada em `data/refs/Obitos_Evitaveis_5_a_74_anos.pdf`.

O estimador de painel está em `scripts/_poisson_fe.py` e os testes que o demonstram, em `tests/test_poisson_fe.py`.

### Figuras

**Figura P1.** Razão de taxas (IRR) da ausência de registro de vigilância da água no ano anterior, por grupo de causa, em Poisson condicional de efeitos fixos de município com indicadoras de ano. IC95% por bootstrap de município (400 reamostragens). *Fonte: Tabela P2.*

**Figura P2.** O mesmo IRR estimado sem e com efeito fixo de município. O marcador vazado é a estimativa que compara municípios entre si; o cheio, a que compara cada município consigo mesmo ao longo do tempo. O comprimento da seta é a parte da associação atribuível a diferenças fixas entre municípios. *Fonte: Tabela P3.*

**Figura P3.** Óbitos por doenças infecciosas intestinais (A00–A09), observados e projetados a partir da tendência log-linear ajustada apenas em 2015 a 2019, em dois denominadores: por 10 mil óbitos do ano e por milhão de habitantes. *Fonte: Tabela P4.*

**Figura P4.** IRR da ausência de vigilância sobre a mortalidade por A00–A09 em cada recorte de sensibilidade. *Fonte: Tabela P5.*

**Figura E1.** Razão de taxas (IRR) da detecção de *Escherichia coli* na água no ano anterior, por grupo de causa, entre os município-anos em que houve amostra analisada e reportada. Mesma gramática da Figura P1, para comparação direta. *Fonte: Tabela E2.*

**Figura 1.** Óbitos por doenças infecciosas intestinais, Brasil, 2015–2025, em contagem absoluta e por 10 mil óbitos do ano. O ano preliminar aparece com marcador vazado e linha pontilhada. *Fonte: Tabela 2.*

**Figura 2.** Variação dos óbitos por A00–A09 entre 2019 e 2024, por faixa etária. *Fonte: Tabela 3.*

**Figura 3.** Razão de mortalidade contra a classe de vigilância regular, para as duas entradas do subgrupo 1.2 da Lista Brasileira. A coluna do controle é monotônica e a do desfecho não é; ver §3.7. *Fonte: Tabela 7.*

**Figura 4.** Razão de razões e IC95% para os quatro critérios do desenho transversal. Marcador cheio indica critério declarado antes da análise; marcador vazado indica teste post-hoc. Todos passam, e a §4.2 explica por que isso não bastou. *Fonte: Tabela 8.*

**Figura 5.** Razão de razões do desenho transversal dentro de cada faixa etária. *Fonte: Tabela 9.*

### Tabelas

**Tabela P1. O painel: municípios, anos, exposição e óbitos (`tabela_p1_painel.csv`).**

| Recorte | Valor |
|---|---|
| Municipios no painel | 5.570 |
| Anos de desfecho | 9 |
| Linhas municipio-ano | 50.130 |
| Pessoas-ano | 1.880.954.497 |
| Municipio-ano sem vigilancia no ano anterior | 9.492 |
| Obitos: A00-A09 intestinais (hipotese) | 45.060 |
| Obitos: J00-J22 respiratorias (subgrupo 1.2) | 753.518 |
| Obitos: outras infecciosas do subgrupo 1.2 | 223.903 |
| Obitos: I20-I25 isquemicas do coracao | 1.046.920 |
| Obitos: V01-Y98 causas externas | 1.357.405 |
| Municipios com vigilancia em TODOS os anos | 3.332 |
| Municipios sem vigilancia em TODOS os anos | 400 |
| Municipios que MUDARAM de estado no periodo | 1.838 |
| Municipio-ano sem vigilancia no ano anterior (%) | 18,9 |
| Municipios com algum obito: A00-A09 intestinais (hipotese) | 4.488 |
| Municipios que mudam E tem obito: A00-A09 intestinais (hipotese) | 1.468 |
| Municipios com algum obito: J00-J22 respiratorias (subgrupo 1.2) | 5.563 |
| Municipios que mudam E tem obito: J00-J22 respiratorias (subgrupo 1.2) | 1.835 |
| Municipios com algum obito: outras infecciosas do subgrupo 1.2 | 5.325 |
| Municipios que mudam E tem obito: outras infecciosas do subgrupo 1.2 | 1.765 |
| Municipios com algum obito: I20-I25 isquemicas do coracao | 5.569 |
| Municipios que mudam E tem obito: I20-I25 isquemicas do coracao | 1.837 |
| Municipios com algum obito: V01-Y98 causas externas | 5.570 |
| Municipios que mudam E tem obito: V01-Y98 causas externas | 1.838 |

**Tabela P2. Critério 1 — IRR da ausência de vigilância no ano anterior, por grupo de causa, com efeito fixo de município (`tabela_p2_especificidade.csv`).**

| Grupo de causa | IRR | IC95% inferior | IC95% superior | Exclui 1 |
|---|---|---|---|---|
| A00-A09 intestinais (hipotese) | 0,99 | 0,943 | 1,041 | nao |
| J00-J22 respiratorias (subgrupo 1.2) | 0,984 | 0,955 | 1,013 | nao |
| outras infecciosas do subgrupo 1.2 | 0,996 | 0,973 | 1,02 | nao |
| I20-I25 isquemicas do coracao | 1,006 | 0,982 | 1,034 | nao |
| V01-Y98 causas externas | 1,002 | 0,977 | 1,023 | nao |

**Tabela P3. Critério 2 — o mesmo IRR com e sem efeito fixo, e a razão de razões implícita contra o controle respiratório (`tabela_p3_efeito_fixo.csv`).**

| Grupo de causa | IRR sem efeito fixo | IRR com efeito fixo | Removido pelo efeito fixo | RRR contra o controle, sem efeito fixo | RRR contra o controle, com efeito fixo |
|---|---|---|---|---|---|
| A00-A09 intestinais (hipotese) | 1,074 | 0,99 | 0,085 | 1,39 | 1,006 |
| J00-J22 respiratorias (subgrupo 1.2) | 0,773 | 0,984 | -0,211 | 1 | 1 |
| outras infecciosas do subgrupo 1.2 | 0,847 | 0,996 | -0,149 | 1,096 | 1,012 |
| I20-I25 isquemicas do coracao | 0,858 | 1,006 | -0,148 | 1,11 | 1,023 |
| V01-Y98 causas externas | 1,035 | 1,002 | 0,033 | 1,339 | 1,019 |

**Tabela P4. Critério 3 — observado contra a tendência de 2015–2019, em dois denominadores (`tabela_p4_tendencia.csv`).**

| Ano | Óbitos por A00–A09 | Observado por 10 mil óbitos | Projetado por 10 mil óbitos | Excesso relativo % (óbitos) | Observado por milhão de habitantes | Projetado por milhão de habitantes | Excesso relativo % (habitantes) | Base do ajuste |
|---|---|---|---|---|---|---|---|---|
| 2015 | 4.372 | 34,58 | 35,45 | -2,5 | 21,6 | 22,33 | -3,3 | sim |
| 2016 | 4.793 | 36,59 | 35,62 | 2,7 | 23,51 | 22,59 | 4,1 | sim |
| 2017 | 4.795 | 36,53 | 35,79 | 2,1 | 23,37 | 22,86 | 2,2 | sim |
| 2018 | 4.633 | 35,19 | 35,96 | -2,2 | 22,43 | 23,13 | -3 | sim |
| 2019 | 4.875 | 36,12 | 36,13 | -0,1 | 23,45 | 23,4 | 0,2 | sim |
| 2020 | 4.126 | 26,5 | 36,31 | -27 | 19,73 | 23,68 | -16,7 | nao |
| 2021 | 4.005 | 21,85 | 36,48 | -40,1 | 19,06 | 23,96 | -20,4 | nao |
| 2022 | 5.003 | 32,4 | 36,65 | -11,6 | 23,73 | 24,24 | -2,1 | nao |
| 2023 | 5.671 | 38,69 | 36,83 | 5,1 | 26,79 | 24,53 | 9,2 | nao |
| 2024 | 7.177 | 46,85 | 37 | 26,6 | 33,76 | 24,82 | 36 | nao |

**Tabela P5. Critério 4 — robustez do IRR da hipótese por recorte (`tabela_p5_robustez.csv`).**

| Recorte | Municípios | IRR | IC95% inferior | IC95% superior |
|---|---|---|---|---|
| Painel completo | 5.570 | 0,99 | 0,943 | 1,041 |
| Sem o Distrito Federal | 5.569 | 0,989 | 0,94 | 1,036 |
| Sem municipios com menos de 5.000 hab. | 4.319 | 0,994 | 0,947 | 1,038 |
| Sem o DF e sem municipios pequenos | 4.318 | 0,993 | 0,943 | 1,051 |
| Somente Centro-Oeste | 467 | 0,925 | 0,681 | 1,232 |
| Somente Nordeste | 1.794 | 1,008 | 0,944 | 1,08 |
| Somente Norte | 450 | 1,01 | 0,872 | 1,12 |
| Somente Sudeste | 1.668 | 0,979 | 0,851 | 1,098 |
| Somente Sul | 1.191 | 0,848 | 0,701 | 1,027 |
| Sem 2022 e 2023 (troca de base populacional) | 5.570 | 0,988 | 0,939 | 1,045 |

**Tabela E1. A extensão microbiológica: universo condicional a reportar (`tabela_e1_painel.csv`).**

| Recorte | Valor |
|---|---|
| Municipios com alguma amostra reportada | 5.170 |
| Municipio-ano no recorte (condicional a reportar) | 40.638 |
| Municipio-ano com E. coli detectada no ano anterior | 8.791 |
| Municipio-ano com E. coli detectada (%) | 21,6 |
| Amostras analisadas no periodo | 792.990.201 |
| Deteccoes de E. coli no periodo | 62.461 |
| Municipios que MUDARAM de estado de deteccao | 2.879 |
| Obitos: A00-A09 intestinais (hipotese) | 39.011 |
| Municipios que mudam E tem obito: A00-A09 intestinais (hipotese) | 2.343 |
| Obitos: J00-J22 respiratorias (subgrupo 1.2) | 677.663 |
| Municipios que mudam E tem obito: J00-J22 respiratorias (subgrupo 1.2) | 2.874 |
| Obitos: outras infecciosas do subgrupo 1.2 | 199.472 |
| Municipios que mudam E tem obito: outras infecciosas do subgrupo 1.2 | 2.751 |
| Obitos: I20-I25 isquemicas do coracao | 931.269 |
| Municipios que mudam E tem obito: I20-I25 isquemicas do coracao | 2.877 |
| Obitos: V01-Y98 causas externas | 1.180.164 |
| Municipios que mudam E tem obito: V01-Y98 causas externas | 2.879 |

**Tabela E2. IRR da detecção de *E. coli* no ano anterior, por grupo de causa (`tabela_e2_especificidade.csv`).**

| Grupo de causa | IRR | IC95% inferior | IC95% superior | Exclui 1 |
|---|---|---|---|---|
| A00-A09 intestinais (hipotese) | 0,991 | 0,944 | 1,037 | nao |
| J00-J22 respiratorias (subgrupo 1.2) | 1,009 | 0,986 | 1,032 | nao |
| outras infecciosas do subgrupo 1.2 | 0,995 | 0,975 | 1,021 | nao |
| I20-I25 isquemicas do coracao | 1,018 | 0,999 | 1,042 | nao |
| V01-Y98 causas externas | 0,997 | 0,981 | 1,014 | nao |

**Tabela E3. O mesmo IRR com e sem efeito fixo de município (`tabela_e3_efeito_fixo.csv`).**

| Grupo de causa | IRR sem efeito fixo | IRR com efeito fixo | Removido pelo efeito fixo | RRR contra o controle, sem efeito fixo | RRR contra o controle, com efeito fixo |
|---|---|---|---|---|---|
| A00-A09 intestinais (hipotese) | 1,021 | 0,991 | 0,03 | 1,007 | 0,982 |
| J00-J22 respiratorias (subgrupo 1.2) | 1,014 | 1,009 | 0,005 | 1 | 1 |
| outras infecciosas do subgrupo 1.2 | 1,207 | 0,995 | 0,212 | 1,19 | 0,986 |
| I20-I25 isquemicas do coracao | 1,041 | 1,018 | 0,023 | 1,027 | 1,009 |
| V01-Y98 causas externas | 0,928 | 0,997 | -0,07 | 0,915 | 0,988 |

**Tabela E4. O IRR quando o esforço de amostragem entra no desenho (`tabela_e4_intensidade.csv`).**

| Grupo de causa | IRR sem ajuste por amostras | IRR ajustado por log(amostras) | Deslocamento | Muda de direção |
|---|---|---|---|---|
| A00-A09 intestinais (hipotese) | 0,991 | 0,985 | -0,006 | nao |
| J00-J22 respiratorias (subgrupo 1.2) | 1,009 | 1,013 | 0,004 | nao |
| outras infecciosas do subgrupo 1.2 | 0,995 | 1,002 | 0,007 | sim |
| I20-I25 isquemicas do coracao | 1,018 | 1,023 | 0,004 | nao |
| V01-Y98 causas externas | 0,997 | 0,999 | 0,002 | nao |

**Tabela E5. Robustez do IRR da detecção por recorte (`tabela_e5_robustez.csv`).**

| Recorte | Municípios | IRR | IC95% inferior | IC95% superior |
|---|---|---|---|---|
| Painel completo | 5.170 | 0,991 | 0,944 | 1,037 |
| Sem o Distrito Federal | 5.170 | 0,991 | 0,944 | 1,037 |
| Sem municipios com menos de 5.000 hab. | 4.008 | 0,99 | 0,943 | 1,038 |
| Sem o DF e sem municipios pequenos | 4.008 | 0,99 | 0,943 | 1,038 |
| Somente Centro-Oeste | 448 | 0,921 | 0,8 | 1,035 |
| Somente Nordeste | 1.574 | 0,97 | 0,897 | 1,058 |
| Somente Norte | 335 | 1,142 | 0,828 | 1,268 |
| Somente Sudeste | 1.624 | 0,972 | 0,924 | 1,033 |
| Somente Sul | 1.189 | 1,042 | 0,962 | 1,119 |

**Tabela 1. O recorte do desenho transversal: municípios, óbitos e pessoas-ano, 2015–2024 (`tabela_1_base.csv`).**

| Recorte | Valor |
|---|---|
| Municipios do pais (dim_municipio) | 5.571 |
| Coletados pelo SISAGUA | 5.570 |
| Analisaveis (coletados e com denominador) | 5.570 |
| --- obitos, o funil --- | — |
| Obitos no mart, 2015-2024 | 14.484.496 |
| (-) em codigo de municipio ignorado (25 codigos) | -27.278 |
| = Obitos no conjunto analisavel | 14.457.218 |
| --- desfecho e controle, no conjunto analisavel --- | — |
| Óbitos por A00–A09 (subgrupo 1.2) | 49.429 |
| (dos quais perdidos em municipio ignorado) | -21 |
| Óbitos por infecção respiratória (subgrupo 1.2) | 831.816 |
| (dos quais perdidos em municipio ignorado) | -994 |
| Pessoas-ano | 2.085.404.546 |

**Tabela 2. Óbitos por A00–A09, controle respiratório e causas mal definidas, Brasil, 2015–2025 (`tabela_2_serie_anual.csv`).**

| Ano | Óbitos totais | Ano preliminar | A00-A09 | Infecção respiratória | Mal definidas | A00-A09 por 10 mil óbitos | % mal definidas |
|---|---|---|---|---|---|---|---|
| 2015 | 1.264.175 | 0 | 4.372 | 78.450 | 71.713 | 34,58 | 5,67 |
| 2016 | 1.309.774 | 0 | 4.793 | 84.068 | 75.869 | 36,59 | 5,79 |
| 2017 | 1.312.663 | 0 | 4.795 | 80.946 | 71.822 | 36,53 | 5,47 |
| 2018 | 1.316.719 | 0 | 4.633 | 81.200 | 70.505 | 35,19 | 5,35 |
| 2019 | 1.349.801 | 0 | 4.875 | 85.095 | 74.972 | 36,12 | 5,55 |
| 2020 | 1.556.824 | 0 | 4.126 | 69.509 | 90.345 | 26,5 | 5,8 |
| 2021 | 1.832.649 | 0 | 4.005 | 69.683 | 94.134 | 21,85 | 5,14 |
| 2022 | 1.544.266 | 0 | 5.003 | 91.377 | 82.597 | 32,4 | 5,35 |
| 2023 | 1.465.610 | 0 | 5.671 | 88.756 | 71.128 | 38,69 | 4,85 |
| 2024 | 1.532.015 | 0 | 7.177 | 103.726 | 69.088 | 46,85 | 4,51 |
| 2025 | 1.534.588 | 1 | 6.885 | 106.372 | 69.172 | 44,87 | 4,51 |

**Tabela 3. Variação dos óbitos por A00–A09 entre 2019 e 2024, por faixa etária (`tabela_3_alta_por_faixa.csv`).**

| Faixa etária | 2019 | 2024 | Variação % |
|---|---|---|---|
| <1 | 355 | 381 | 7,3 |
| 1-4 | 150 | 186 | 24 |
| 5-14 | 62 | 97 | 56,5 |
| 15-29 | 73 | 113 | 54,8 |
| 30-44 | 157 | 217 | 38,2 |
| 45-59 | 381 | 568 | 49,1 |
| 60-74 | 1.031 | 1.564 | 51,7 |
| 75+ | 2.665 | 4.051 | 52 |

**Tabela 4. Variação dos óbitos por A00–A09 entre 2019 e 2024, por código da CID-10 (`tabela_4_alta_por_codigo.csv`).**

| CID-10 | Descrição | 2019 | 2024 | Variação % |
|---|---|---|---|---|
| A01 | Febres tifoide e paratifoide | 1 | 1 | 0 |
| A02 | Outras infecções por Salmonella | 16 | 40 | 150 |
| A03 | Shiguelose | 1 | 2 | 100 |
| A04 | Outras infecções intestinais bacterianas | 807 | 1.388 | 72 |
| A05 | Intoxicações alimentares bacterianas | 23 | 22 | -4,3 |
| A06 | Amebíase | 52 | 33 | -36,5 |
| A07 | Outras doenças intestinais por protozoários | 4 | 6 | 50 |
| A08 | Infecções intestinais virais | 115 | 253 | 120 |
| A09 | Diarreia e gastroenterite de origem infecciosa presumível | 3.856 | 5.432 | 40,9 |

**Tabela 5. Teste de redistribuição de causas mal definidas, municípios com ao menos 100 óbitos em 2019 e 2024 (`tabela_5_teste_codificacao.csv`).**

| Recorte | Municípios | A00-A09 2019 | A00-A09 2024 | Variação % |
|---|---|---|---|---|
| Todos os municípios com base suficiente | 2.176 | 4.275 | 6.304 | 47,5 |
| Onde as mal definidas NÃO caíram | 946 | 1.378 | 1.977 | 43,5 |
| Onde as mal definidas caíram | 1.230 | 2.897 | 4.327 | 49,4 |

**Tabela 6. As quatro classes de vigilância do SISAGUA: perfil social e mortalidade (`tabela_6_exposicao.csv`).**

| Classe de vigilância | Municípios | Pessoas-ano | Óbitos A00–A09 | Óbitos respiratórios | Óbitos totais | % sem água (mediana) | Analfabetismo % (mediana) | Taxa A00-A09 por 100 mil | Taxa respiratória por 100 mil | Mortalidade geral por 100 mil | A00-A09 por 10 mil óbitos |
|---|---|---|---|---|---|---|---|---|---|---|---|
| sem vigilância | 384 | 86.450.766 | 2.285 | 19.986 | 425.694 | 29,265 | 18,415 | 2,64 | 23,1 | 492 | 53,7 |
| vigilância rara (até 6 meses) | 511 | 139.489.204 | 4.303 | 51.229 | 880.758 | 22,5 | 17,38 | 3,08 | 36,7 | 631 | 48,9 |
| vigilância parcial (7 a 11 meses) | 1.048 | 249.935.248 | 6.095 | 93.566 | 1.746.593 | 24,24 | 12,64 | 2,44 | 37,4 | 699 | 34,9 |
| vigilância regular (12 meses) | 3.627 | 1.609.529.328 | 36.746 | 667.035 | 11.404.173 | 15,67 | 7,34 | 2,28 | 41,4 | 709 | 32,2 |

**Tabela 7. Razão de mortalidade contra a vigilância regular, para as duas entradas do subgrupo 1.2 (`tabela_7_gradiente.csv`).**

| Classe de vigilância | RR A00-A09 | RR respiratória | RRR |
|---|---|---|---|
| sem vigilância | 1,158 | 0,558 | 2,075 |
| vigilância rara (até 6 meses) | 1,351 | 0,886 | 1,525 |
| vigilância parcial (7 a 11 meses) | 1,068 | 0,903 | 1,182 |
| vigilância regular (12 meses) | 1 | 1 | 1 |

**Tabela 8. Os quatro critérios do desenho transversal, com IC95% por bootstrap de município (`tabela_8_criterios.csv`).**

| Critério | Pré-declarado | RRR | IC95% inferior | IC95% superior | Exclui 1 |
|---|---|---|---|---|---|
| 1. Especificidade (bruto) | sim | 2,075 | 1,776 | 2,518 | sim |
| 2. Ajustado por acesso à água (MH) | sim | 1,926 | 1,618 | 2,225 | sim |
| Sensibilidade: controle só pneumonia/influenza | sim | 2,087 | 1,785 | 2,535 | sim |
| 4. Padronizado por idade (POST-HOC) | nao | 1,767 | 1,518 | 2,021 | sim |

**Tabela 9. Razão de razões do desenho transversal dentro de cada faixa etária (`tabela_9_rrr_por_idade.csv`).**

| Faixa etária | A00–A09 sem vigilância | A00–A09 vigilância regular | RR A00-A09 | RR respiratória | RRR |
|---|---|---|---|---|---|
| <1 | 366 | 2.336 | 2,187 | 1,43 | 1,529 |
| 1-4 | 205 | 918 | 2,518 | 1,035 | 2,432 |
| 5-14 | 48 | 374 | 1,664 | 1,182 | 1,407 |
| 15-29 | 63 | 513 | 2,346 | 1,091 | 2,151 |
| 30-44 | 82 | 1.170 | 1,454 | 0,739 | 1,966 |
| 45-59 | 184 | 2.996 | 1,688 | 0,81 | 2,086 |
| 60-74 | 372 | 7.790 | 1,463 | 0,847 | 1,727 |
| 75+ | 965 | 20.643 | 1,353 | 0,797 | 1,698 |

**Tabela 10. Municípios sem registro de vigilância, por unidade da federação (`tabela_10_sem_vigilancia_por_uf.csv`).**

| UF | Municípios sem vigilância | Óbitos A00–A09 | pessoas_ano | Taxa A00-A09 por 100 mil | Municípios na UF | % da UF sem vigilância |
|---|---|---|---|---|---|---|
| PI | 98 | 287 | 6.888.718 | 4,17 | 224 | 43,8 |
| MA | 69 | 277 | 12.684.671 | 2,18 | 217 | 31,8 |
| PA | 56 | 302 | 16.032.701 | 1,88 | 144 | 38,9 |
| MG | 38 | 25 | 1.472.867 | 1,7 | 853 | 4,5 |
| AM | 37 | 466 | 9.005.555 | 5,17 | 62 | 59,7 |
| RO | 14 | 19 | 1.831.989 | 1,04 | 52 | 26,9 |
| PB | 14 | 19 | 938.357 | 2,02 | 223 | 6,3 |
| GO | 9 | 8 | 420.622 | 1,9 | 246 | 3,7 |
| PE | 8 | 53 | 1.287.074 | 4,12 | 185 | 4,3 |
| MT | 7 | 23 | 537.404 | 4,28 | 141 | 5 |
| RN | 7 | 30 | 820.055 | 3,66 | 167 | 4,2 |
| BA | 7 | 55 | 1.477.832 | 3,72 | 417 | 1,7 |
| CE | 6 | 42 | 1.477.597 | 2,84 | 184 | 3,3 |
| TO | 3 | 9 | 467.492 | 1,93 | 139 | 2,2 |
| AC | 3 | 16 | 380.850 | 4,2 | 22 | 13,6 |
| AL | 2 | 9 | 321.205 | 2,8 | 102 | 2 |
| RJ | 2 | 10 | 455.465 | 2,2 | 92 | 2,2 |
| ES | 1 | 1 | 92.874 | 1,08 | 78 | 1,3 |
| DF | 1 | 634 | 29.771.234 | 2,13 | 1 | 100 |
| PR | 1 | 0 | 56.854 | 0 | 399 | 0,3 |
| RS | 1 | 0 | 29.350 | 0 | 497 | 0,2 |

**Tabela 11. Razão de razões dentro de cada quartil de acesso à água (Censo 2022) (`tabela_11_por_quartil_de_acesso.csv`).**

| Quartil de acesso (Censo) | Municípios | % sem água (mediana) | Óbitos A00–A09 | RRR no estrato |
|---|---|---|---|---|
| Q1 | 1.394 | 4,99 | 26.984 | 2,008 |
| Q2 | 1.392 | 13,3 | 8.628 | 1,415 |
| Q3 | 1.391 | 24,51 | 7.341 | 1,781 |
| Q4 | 1.393 | 43,89 | 6.476 | 2,149 |

---

## 6. Referências

- **[1]** Malta DC, França E, Abreu DX, Oliveira H, Monteiro RA, Sardinha LMV, Duarte EC, Silva GA. Atualização da lista de causas de mortes evitáveis (5 a 74 anos de idade) por intervenções do Sistema Único de Saúde do Brasil. *Epidemiologia e Serviços de Saúde*. 2011;20(3):409-412.
- **[2]** Brasil. Ministério da Saúde. DATASUS. *Óbitos por causas evitáveis — 5 a 74 anos: notas técnicas*. Arquivada neste pacote em `referencia/Obitos_Evitaveis_5_a_74_anos.pdf`.
- **[3]** Souza EA, et al. Combination of conditional cash transfer program and environmental health interventions reduces child mortality: an ecological study of Brazilian municipalities. *PLoS ONE*. 2021;16(3):e0248676. doi:10.1371/journal.pone.0248676
- **[4]** Juvakoski A, Rantanen H, Mulas M, Corona F, Vahala R, Varis O, Mellin I. Evidence of waste management impacting severe diarrhea prevalence more than WASH: an exhaustive analysis with Brazilian municipal-level data. *Water Research*. 2023;247:120805. doi:10.1016/j.watres.2023.120805
- **[5]** Hausman J, Hall BH, Griliches Z. Econometric models for count data with an application to the patents–R&D relationship. *Econometrica*. 1984;52(4):909-938.
- **[6]** Lipsitch M, Tchetgen Tchetgen E, Cohen T. Negative controls: a tool for detecting confounding and bias in observational studies. *Epidemiology*. 2010;21(3):383-388. doi:10.1097/EDE.0b013e3181d61eeb
- **[7]** Brasil. Ministério da Saúde. *Vigiagua e Sisagua — Sistema de Informação de Vigilância da Qualidade da Água para Consumo Humano*. Disponível em `gov.br/saude/pt-br/composicao/svsa/saude-ambiental/vigiagua/sisagua`. Acesso em 12 set. 2026.
- **[8]** Brasil. Ministério da Saúde. *Sistema de Informações sobre Mortalidade (SIM): microdados*. DATASUS e OpenDataSUS, competências de 2015 a 2025.
- **[9]** Instituto Brasileiro de Geografia e Estatística. *Projeções da população do Brasil e unidades da federação por sexo e idade: revisão 2024*. Rio de Janeiro: IBGE; 2024.

*As referências acima cobrem as afirmações metodológicas e as fontes de dado. As passagens da §4.5 que descrevem trabalhos sem chamada numerada — investimento em saneamento e internações, protozoose na região metropolitana do Rio de Janeiro, fluoretação e cárie, mortalidade por câncer na bacia do Rio Doce — resultam da busca dirigida descrita nessa seção e precisam de citação formal antes da submissão. Estão declaradas aqui como pendência, e não omitidas.*
