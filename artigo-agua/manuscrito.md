# Mortes evitáveis por doença infecciosa intestinal no Brasil, 2015–2024: uma alta de 47%, e a vigilância da água que não a vê

**Pedro Paulo Fernandes**¹

¹ Saúde em Dado — saudeemdado.com · ORCID e afiliação a completar

*Coautoria a definir. Este é um rascunho de trabalho preparado a partir do levantamento executado em 2026-09-12.*

---

## Resumo

**Contexto.** A Lista Brasileira de Causas de Mortes Evitáveis é o instrumento oficial do Ministério da Saúde para classificar óbitos evitáveis por intervenção do SUS. O seu subgrupo 1.2 reúne as causas "reduzíveis por ações adequadas de promoção à saúde, prevenção, controle e atenção às doenças de causas infecciosas", e nele convivem, lado a lado, as **doenças infecciosas intestinais** (A00–A09) e as **infecções respiratórias, inclusive pneumonia e influenza** (J00–J06, J10–J22). A lista não nomeia a água em nenhum subgrupo: não existe categoria de saneamento nela.

**Objetivo.** Medir a evolução da mortalidade por doenças infecciosas intestinais no Brasil entre 2015 e 2024; testar se a alta observada é artefato de registro; e determinar se ela se associa à **vigilância da qualidade da água** — medida pelo Sistema de Informação de Vigilância da Qualidade da Água para Consumo Humano (SISAGUA) — de forma específica do caminho hídrico.

**Métodos.** Todos os 14.457.218 óbitos não fetais registrados no Sistema de Informações sobre Mortalidade entre 2015 e 2024, agregados por município de residência (Tabela 1). A exposição é a regularidade da vigilância: a mediana municipal de meses com análise reportada ao SISAGUA no período, em quatro classes ordenadas. O desfecho é a mortalidade por A00–A09; o **controle negativo** é a mortalidade pelas infecções respiratórias do mesmo subgrupo 1.2 — causas que partilham pobreza, desnutrição, acesso a serviço, qualidade de codificação e estrutura etária com o desfecho, e não partilham o caminho hídrico. A medida é a razão de razões (RRR) entre municípios sem vigilância e municípios com vigilância regular, com IC95% por bootstrap de município (2.000 reamostragens). Três critérios de refutação foram declarados antes de qualquer resultado: **IC95% do RRR incluindo 1 refuta a interpretação hídrica**; o RRR recalculado dentro de quartis de acesso à água pelo Censo, reunido por Mantel-Haenszel, incluindo 1 atribui o achado ao acesso e não à vigilância; e o gradiente entre as quatro classes é relatado como estiver. Um quarto teste, **não pré-declarado**, recalcula o RRR dentro de cada faixa etária.

**Resultados.** Os óbitos por A00–A09 passaram de 4.875 em 2019 para 7.177 em 2024 — alta de **47,2%** —, enquanto os óbitos totais subiram 13,5% (Tabela 2). Relativos ao total de óbitos, foram de 36,12 para 46,85 por 10 mil. A alta não é de um código (A04 +72%, A08 +120%, A09 +40,9%; Tabela 4), não é de uma faixa etária (entre +38,2% e +56,5% em seis das oito faixas; Tabela 3) e não é redistribuição de causas mal definidas: nos 946 municípios em que a proporção de mal definidas **não caiu**, a alta foi de **+43,5%**, contra +49,4% onde caiu (Tabela 5). Entre os 5.570 municípios analisáveis, 384 não reportaram análise alguma ao SISAGUA. Neles a mortalidade por A00–A09 é 1,158 vez a dos municípios com vigilância regular, enquanto a mortalidade por infecção respiratória é **0,558** — RRR de **2,075 [1,776–2,518]** (Tabelas 7 e 8). O gradiente entre as quatro classes é monotônico: 2,075, 1,525, 1,182 e 1. Ajustado por quartil de acesso à água, o RRR é **1,926 [1,618–2,225]**, e permanece acima de 1 nos quatro quartis, **inclusive naquele em que a mediana de domicílios sem ligação à rede é de 4,99%** (Tabela 11). Substituir o controle pela definição estrita de pneumonia e influenza dá 2,087 [1,785–2,535]. A padronização por idade, post-hoc, reduz o RRR para **1,767 [1,518–2,021]**, que permanece acima de 1 nas oito faixas etárias, com o máximo em crianças de 1 a 4 anos (2,432; Tabela 9).

**Conclusões.** A mortalidade por doenças infecciosas intestinais — causa que o instrumento oficial brasileiro classifica como evitável — subiu 47% em cinco anos, e a alta não é artefato de registro. A ausência de vigilância da qualidade da água distingue essa causa de outra que o mesmo instrumento trata como equivalente, com especificidade que sobrevive ao ajuste por acesso à água e à padronização por idade. O desenho é ecológico e não estabelece que o indivíduo que morreu consumiu água não vigiada; ausência de vigilância é ausência da prova, não prova de contaminação. O achado aponta uma lacuna no próprio instrumento: a Lista Brasileira declara a morte por diarreia evitável sem nomear o mecanismo pelo qual ela é evitada.

**Palavras-chave.** Mortalidade evitável; doenças infecciosas intestinais; vigilância da qualidade da água; SISAGUA; estudos ecológicos; Brasil.

---

## 1. Introdução

A morte por diarreia é o caso mais antigo da saúde pública. Foi ela que fundou a epidemiologia moderna quando John Snow removeu a bomba de Broad Street em 1854, e é ela que a engenharia sanitária do século XX tratou como problema resolvido nos países que construíram redes de água e esgoto. No Brasil, a mortalidade por doenças infecciosas intestinais caiu de forma sustentada ao longo de décadas, e a literatura nacional descreve essa queda como parte de uma transição epidemiológica em curso — com ressalva para o Norte e o Nordeste, onde ela seria mais lenta.

Este artigo reporta que a queda parou e inverteu. Entre 2019 e 2024, os óbitos por A00–A09 subiram 47,2% no país.

O achado tem duas propriedades que merecem enquadramento antes dos métodos. A primeira é que **A00–A09 é uma causa oficialmente evitável no Brasil**: ela está no subgrupo 1.2 da Lista Brasileira de Causas de Mortes Evitáveis, instrumento do Ministério da Saúde publicado em 2007 e revisto entre 2010 e 2011. Não se trata, portanto, de um agravo emergente ou de um desfecho sobre o qual o sistema de saúde não tenha responsabilidade declarada. Trata-se de uma categoria que o próprio Estado brasileiro se comprometeu a reduzir.

A segunda é que **a Lista não nomeia a água**. Percorrida inteira, ela não tem subgrupo de saneamento ambiental. As doenças infecciosas intestinais aparecem sob o rótulo "reduzíveis por ações adequadas de promoção à saúde, prevenção, controle e atenção às doenças de causas infecciosas", ao lado de HIV, tuberculose respiratória, sífilis, doença inflamatória pélvica e infecção do trato urinário. O mecanismo pelo qual essas mortes são evitadas — água tratada e vigiada — não está escrito no instrumento que as declara evitáveis.

Esse silêncio tem consequência operacional. O Brasil mantém, desde 2014, um sistema nacional de vigilância da qualidade da água para consumo humano, o SISAGUA, alimentado pelos municípios. A literatura que usa esse sistema é escassa e trata o não-reporte como limitação de dado: um levantamento de contaminação por agrotóxicos registra que 53% dos municípios não enviaram dados de monitoramento; outro, anterior, que apenas 9% a 17% registravam. Nenhum trabalho publicado usou a **ausência de vigilância como variável de exposição**, e nenhum ligou o SISAGUA à mortalidade por doença infecciosa intestinal em escala municipal nacional.

É essa inversão que este artigo faz. A pergunta não é "a água está contaminada?" — o SISAGUA não responde isso onde ninguém mediu. A pergunta é se o município que **não vigia** morre diferente do que vigia, e se essa diferença é específica do caminho hídrico ou apenas mais um efeito da pobreza.

---

## 2. Métodos

### 2.1 Fonte e recorte

Todos os óbitos não fetais registrados no Sistema de Informações sobre Mortalidade (SIM) entre 2015 e 2024, agregados por município de residência, ano e categoria de três caracteres da CID-10. O ano de 2025 aparece nas figuras e na Tabela 2 identificado como preliminar, e **não entra em nenhuma estimativa**: ele é mostrado porque omitir o dado mais recente seria esconder informação, e é marcado porque colá-lo à série consolidada afirmaria uma completude que não existe.

O denominador populacional é a Projeção da População do IBGE, revisão 2024, somada sobre os dez anos para produzir pessoas-ano.

**Dois totais, e por que eles diferem.** O mart do SIM traz 14.484.496 óbitos no período. Deles, **27.278 estão em 25 códigos do tipo `110000` ou `120000`** — "município ignorado" dentro da unidade da federação. Esses códigos não são municípios: não têm classe de vigilância, não têm população e não podem entrar em nenhuma razão por habitante. Excluídos, restam **14.457.218**, e é sobre esse conjunto que toda estimativa deste artigo é calculada.

A distinção precisa ser explícita porque as duas pontas do funil aparecem no material suplementar: a Tabela 1 traz o conjunto analisável, e a Tabela 2 traz a série anual sobre o mart inteiro. A Tabela 1 mostra o funil completo, com a perda nomeada, justamente para que a diferença não seja lida como inconsistência. A perda no desfecho é pequena — 21 óbitos por A00–A09 e 994 por infecção respiratória — e não se concentra em nenhum ano.

O manuscrito irmão sobre imunoprevenção, que não depende de município, usa o total de **14.484.496**. Os dois números descrevem o mesmo SIM e a mesma versão dos microdados; o que difere é a exigência de município de residência utilizável, que só um dos dois desenhos faz. A Tabela 1 traz o recorte fechado: 14.457.218 óbitos, 49.429 deles por A00–A09, 831.816 pelo controle, sobre 2.085.404.546 pessoas-ano.

### 2.2 A exposição, e o que ela não é

O SISAGUA registra, por município e mês, análises de parâmetros básicos da água distribuída — cloro residual, turbidez, cor, coliformes totais, *Escherichia coli*, pH, fluoreto e outros. A coleta nacional deste trabalho percorreu os 5.571 municípios brasileiros e recuperou 117.764.680 registros; um município não teve denominador populacional utilizável e ficou fora, restando 5.570.

A exposição é a **mediana municipal de meses com análise reportada**, calculada sobre ano × parâmetro no período, em quatro classes:

| classe | definição | municípios |
|---|---|---|
| sem vigilância | nenhuma análise reportada em 2015–2024 | 384 |
| vigilância rara | mediana de até 6 meses | 511 |
| vigilância parcial | mediana de 7 a 11 meses | 1.048 |
| vigilância regular | mediana de 12 meses | 3.627 |

O SISAGUA prevê controle **mensal**, de modo que 12 é o previsto e não o excepcional.

Três distinções são deliberadas e importam para a leitura. **Primeira:** ausência de vigilância não é ausência de água encanada. As duas coisas são medidas por fontes diferentes, e a Tabela 6 mostra que a mediana de domicílios sem ligação à rede é de 29,265% na classe sem vigilância e 15,67% na classe regular — diferentes, mas longe de coincidentes. **Segunda:** ausência de vigilância não é água contaminada. É ausência da prova, e o artigo não afirma nada além disso. **Terceira:** município que a coleta não alcançou ficou **fora** da análise, e não foi classificado como "sem vigilância" — chamar falha de coleta de exposição baixa inventaria dado.

### 2.3 O controle negativo, e por que ele sai do instrumento

Um cruzamento ecológico entre indicador de saneamento e mortalidade infecciosa nunca falha. Ele vai produzir associação, e a associação vai ser confundível com pobreza: município que não vigia a água é município pobre, e município pobre morre mais de tudo. Uma análise que reportasse apenas "encontramos associação" não teria como separar mecanismo de marcador socioeconômico.

O discriminador adotado é um **controle negativo**, e ele não foi escolhido por conveniência. O subgrupo 1.2 da Lista Brasileira contém, como entradas vizinhas:

```
Doenças infecciosas intestinais ................ A00-A09
Infecções respiratórias, inclusive pneumonia
e influenza .......... J00-J01, J02.8-J02.9, J03.8-J03.9,
                       J04-J05, J06, J10-J22
```

O Ministério da Saúde declara as duas evitáveis pelo mesmo tipo de ação. Elas partilham praticamente todo confundidor relevante — pobreza, desnutrição, acesso a serviço de saúde, qualidade de codificação, estrutura etária — e não partilham o caminho hídrico. Em três caracteres, a definição oficial corresponde a J00–J06 e J10–J22; a diferença são subcategorias de amigdalite e faringite estreptocócica, que praticamente não matam. Uma análise de sensibilidade repete a medida com a definição estrita de pneumonia e influenza (J10–J18).

O contraste, portanto, não é entre duas causas que os autores escolheram parecidas. É entre duas entradas que o instrumento oficial trata como equivalentes.

### 2.4 A medida, e os critérios declarados antes

A medida é a razão de razões:

$$\text{RRR} = \frac{\text{RR}(\text{A00–A09})}{\text{RR}(\text{infecção respiratória})}$$

onde cada RR compara a classe sem vigilância à classe de vigilância regular. A RRR tem uma propriedade que o desenho explora: **tudo o que infla ou deprime as duas causas por igual cancela**. Sub-registro de óbito, erro no denominador populacional e variação geral de qualidade do registro afetam numerador e denominador na mesma proporção e desaparecem da razão. O que a RRR não cancela é o que afeta as duas causas de forma **diferente** — e é por isso que a idade precisa de tratamento próprio (§2.5).

Sem modelo paramétrico. Os intervalos de confiança de 95% vêm de **bootstrap de município**, com 2.000 reamostragens com reposição. A unidade de reamostragem é a unidade de análise: óbitos dentro do mesmo município não são independentes, e reamostrá-los produziria intervalo estreito por construção.

Os critérios foram escritos no cabeçalho do script de análise antes de qualquer resultado ser observado, e o script imprime aprovação ou reprovação de cada um:

> **Critério 1 — especificidade.** Se o IC95% do RRR incluir 1, a interpretação hídrica está **refutada**. A associação existiria, mas seria indistinguível de um marcador geral de precariedade, e seria reportada assim.
>
> **Critério 2 — acesso não pode explicar.** O RRR é recalculado dentro de quartis de `pct_sem_agua` do Censo 2022 e reunido pelos pesos de Mantel-Haenszel. Se passar a incluir 1, o achado é sobre **acesso** e não sobre **vigilância**.
>
> **Critério 3 — gradiente.** As quatro classes são ordenadas. Não-monotonicidade não refuta sozinha; é reportada como estiver.

### 2.5 O quarto teste, que não foi pré-declarado

Após observar que a mortalidade geral é 30% menor na classe sem vigilância (492 contra 709 por 100 mil; Tabela 6) — compatível com estrutura etária mais jovem, e não com sub-registro —, acrescentou-se um quarto teste: recalcular o RRR **dentro de cada faixa etária**, usando o total de óbitos da faixa como denominador. Isso neutraliza a composição etária sem exigir denominador populacional por idade.

Este teste **não estava entre os critérios declarados**. Ele nasceu de observar o resultado, e vale menos que os três acima; está rotulado como post-hoc na Tabela 8 e desenhado com marcador vazado na Figura 4. Ele reduziu o efeito e não o derrubou, o que é a direção que um teste post-hoc pode ter sem se tornar suspeito — mas a ordem em que ele foi concebido fica declarada, e não escondida.

---

## 3. Resultados

### 3.1 A alta

Os óbitos por doenças infecciosas intestinais passaram de 4.875 em 2019 para 7.177 em 2024, alta de **47,2%** (Tabela 2, Figura 1). No mesmo período os óbitos totais do país subiram 13,5%. Relativos ao total, os óbitos por A00–A09 foram de 36,12 para 46,85 por 10 mil — alta de 29,7% na medida que já desconta o crescimento geral da mortalidade.

A série de 2015 a 2019 é plana, entre 34,58 e 36,59 por 10 mil. Os anos de 2020 e 2021 caem para 26,5 e 21,85, compatível com o efeito conhecido da pandemia sobre a circulação de patógenos entéricos e com a inflação do denominador. A partir de 2022 a série sobe de forma contínua, e 2024 é o maior valor da década por margem larga. O ano preliminar de 2025 registra 6.885 óbitos.

### 3.2 A alta não é artefato

Quatro explicações alternativas foram examinadas.

**Não é ano preliminar.** 2024 é ano consolidado no SIM; apenas 2025 é preliminar, e ele não entra em nenhuma estimativa.

**Não é um código.** A alta aparece em toda a faixa (Tabela 4): A04 (outras infecções intestinais bacterianas) sobe 72%, A08 (infecções intestinais virais) sobe 120% e A09 (diarreia e gastroenterite de origem infecciosa presumível) sobe 40,9%. A09 é o código de maior volume e o mais dependente de prática de codificação; que a alta apareça também em A04 e A08, que exigem identificação de agente, argumenta contra artefato de rotulagem.

**Não é envelhecimento.** A alta é distribuída entre faixas etárias (Tabela 3, Figura 2): +56,5% em 5–14 anos, +54,8% em 15–29, +52% em 75 ou mais, +51,7% em 60–74, +49,1% em 45–59, +38,2% em 30–44. Apenas os menores de 1 ano (+7,3%) e a faixa de 1–4 anos (+24%) sobem menos. Uma alta impulsionada por envelhecimento populacional se concentraria nas faixas idosas; esta não se concentra em lugar nenhum.

**Não é redistribuição de causas mal definidas.** Esta é a explicação concorrente mais forte, porque a proporção de causas mal definidas caiu no período — de 5,55% em 2019 para 4,51% em 2024 (Tabela 2) —, e o ganho de A00–A09 caberia dentro dessa queda. O teste, com critério declarado antes, restringe a comparação aos 2.176 municípios com pelo menos 100 óbitos em ambos os anos e separa os que melhoraram a codificação dos que não melhoraram (Tabela 5):

| recorte | municípios | 2019 | 2024 | variação |
|---|---|---|---|---|
| todos com base suficiente | 2.176 | 4.275 | 6.304 | **+47,5%** |
| onde as mal definidas **não** caíram | 946 | 1.378 | 1.977 | **+43,5%** |
| onde as mal definidas caíram | 1.230 | 2.897 | 4.327 | **+49,4%** |

A alta onde a codificação não melhorou é 43,5%, contra 49,4% onde melhorou. A diferença entre as duas é pequena diante da magnitude da alta: a redistribuição explica uma fração, não o fenômeno.

### 3.3 A exposição

Dos 5.570 municípios analisáveis, **384 não reportaram uma única análise de água ao SISAGUA entre 2015 e 2024**. Outros 511 reportaram em mediana de até seis meses por ano, 1.048 entre sete e onze, e 3.627 nos doze meses previstos (Tabela 6).

As classes diferem socialmente, como esperado: a mediana de domicílios sem ligação à rede geral vai de 29,265% na classe sem vigilância a 15,67% na regular, e a taxa de analfabetismo, de 18,415% a 7,34%. Diferem também na mortalidade geral — 492 por 100 mil na classe sem vigilância contra 709 na regular —, diferença compatível com estrutura etária mais jovem nos municípios pequenos do Norte e Nordeste que compõem a classe.

### 3.4 O gradiente, e o que ele separa

A Tabela 7 e a Figura 3 trazem o resultado central. Comparados aos municípios de vigilância regular, os sem vigilância têm:

- **mortalidade por A00–A09 1,158 vez maior**;
- **mortalidade por infecção respiratória 0,558 vez**, isto é, 44% menor.

As duas causas pertencem ao mesmo subgrupo do mesmo instrumento oficial, e se movem em direções opostas. A razão de razões é **2,075**.

O gradiente é monotônico ao longo das quatro classes: 2,075 na ausência de vigilância, 1,525 na vigilância rara, 1,182 na parcial, 1 na regular.

### 3.5 Os critérios

A Tabela 8 e a Figura 4 trazem os quatro testes com intervalo de confiança:

| critério | pré-declarado | RRR | IC95% | exclui 1 |
|---|---|---|---|---|
| 1. especificidade | sim | **2,075** | 1,776–2,518 | sim |
| 2. ajustado por acesso à água | sim | **1,926** | 1,618–2,225 | sim |
| sensibilidade (só pneumonia e influenza) | sim | 2,087 | 1,785–2,535 | sim |
| 4. padronizado por idade | **não** | **1,767** | 1,518–2,021 | sim |

Os três critérios declarados antes foram aprovados. O ajuste por acesso à água custou 7% do efeito; a padronização por idade, post-hoc, custou outros 15%. O que resta — 1,767 — permanece com intervalo que exclui 1 por margem confortável.

A análise de sensibilidade merece nota. Trocar o controle oficial pela definição estrita de pneumonia e influenza produz 2,087 contra 2,075 — praticamente o mesmo valor. O achado não depende da escolha do comparador dentro do subgrupo.

### 3.6 O ajuste por acesso, quartil a quartil

O critério 2 é o que separa **vigilância** de **acesso**, e a Tabela 11 mostra por que ele sobrevive. Dentro de cada quartil de domicílios sem ligação à rede, o RRR é:

| quartil | mediana sem água | óbitos A00–A09 | RRR |
|---|---|---|---|
| Q1 | 4,99% | 26.984 | **2,008** |
| Q2 | 13,30% | 8.628 | 1,415 |
| Q3 | 24,51% | 7.341 | 1,781 |
| Q4 | 43,89% | 6.476 | 2,149 |

O RRR é maior que 1 nos quatro quartis, e o valor no **Q1 é 2,008** — isto é, entre os municípios em que praticamente todos os domicílios têm ligação à rede, a ausência de vigilância ainda separa as duas causas por um fator de dois. Ter água encanada e não verificá-la não é equivalente a verificá-la.

O padrão não é monotônico ao longo dos quartis, e isso vai relatado como está: a associação não cresce com a precariedade do acesso, o que é um argumento adicional contra a leitura de que ela seja apenas gradiente socioeconômico.

### 3.7 O formato por idade

A Tabela 9 e a Figura 5 trazem o RRR dentro de cada faixa etária. Ele é maior que 1 em **todas as oito**, e o máximo está em **crianças de 1 a 4 anos (2,432)**, seguido por 15–29 (2,151) e 45–59 (2,086). A razão para A00–A09 isoladamente também tem o seu máximo em 1–4 anos (2,518).

Esse formato é, na avaliação dos autores, a evidência mais informativa do conjunto — mais do que o valor agregado ou o intervalo de confiança. A faixa de 1 a 4 anos é aquela em que a doença diarreica por água insegura mata com maior intensidade reconhecida na literatura internacional, e é a faixa em que a associação é mais forte. Nem artefato de codificação nem gradiente de pobreza têm razão para escolher precisamente essa faixa.

A exceção é a faixa de menores de 1 ano (RRR 1,529), em que o controle respiratório se comporta de modo diferente (RR 1,43, o único acima de 1 entre as faixas). A mortalidade infantil precoce é dominada por causas perinatais e por um padrão de acesso a serviço distinto do restante da vida, e a leitura das duas causas ali não é comparável à das demais faixas.

---

## 4. Discussão

### 4.1 O que foi medido

Entre 2019 e 2024, a mortalidade brasileira por doenças infecciosas intestinais subiu 47%. A alta sobrevive ao exame das quatro explicações alternativas conhecidas, e é acompanhada por uma associação específica com a ausência de vigilância da qualidade da água, medida contra um controle negativo extraído do próprio instrumento oficial de mortalidade evitável.

### 4.2 O que este desenho não autoriza

É um estudo **ecológico**. A unidade é o município, e nada aqui autoriza afirmar que a pessoa que morreu consumiu água não vigiada; a falácia ecológica é um risco real e declarado. A exposição é **ausência de registro de vigilância**, que não é ausência de vigilância — um município pode analisar e não reportar — e muito menos é água contaminada. É ausência da prova.

O desenho não estabelece mecanismo. Ele estabelece que duas causas que o instrumento oficial trata como equivalentes se comportam de modo diferente conforme a vigilância da água, e que essa diferença resiste ao ajuste por acesso e por idade.

Há ainda um confundidor que o desenho não elimina: municípios que não reportam ao SISAGUA podem ter sistemas de vigilância em saúde mais frágeis em geral, o que afetaria a detecção e a codificação de causas específicas. O controle negativo protege parcialmente contra isso — fragilidade geral de registro deprimiria as duas causas —, mas não protege contra fragilidade que atinja diferencialmente o diagnóstico de doença entérica.

### 4.3 A lacuna no instrumento

O achado secundário é sobre a Lista Brasileira. Ela classifica as doenças infecciosas intestinais como evitáveis e as agrupa sob "promoção à saúde, prevenção, controle e atenção às doenças de causas infecciosas", ao lado de HIV, tuberculose e infecção urinária. O mecanismo pelo qual a morte por diarreia é evitada — água tratada e vigiada — **não aparece em nenhum subgrupo da lista**.

Isso importa além da nomenclatura. Um instrumento de mortalidade evitável é lido como agenda: ele diz ao gestor onde a morte pode ser impedida e por qual via. Ao não nomear o saneamento, a Lista deixa a resposta à morte por diarreia dentro do vocabulário da atenção à saúde — promoção, prevenção, controle — quando o determinante é de infraestrutura e de vigilância ambiental, exercido por outro setor e com outro orçamento.

Esta observação é irmã de outra, já reportada em trabalho anterior dos mesmos autores sobre o subgrupo 1.1 da mesma Lista: o subgrupo de imunoprevenção descreve o calendário vacinal de 2010 e identifica 4,03 óbitos por 10 mil, número que não se move há uma década. Os dois achados apontam para o mesmo lugar por caminhos diferentes — um instrumento que envelheceu no conteúdo, e outro que é cego ao mecanismo.

### 4.4 Relação com a literatura

A literatura brasileira que relaciona saneamento e mortalidade por diarreia usa, como exposição, o **acesso** à infraestrutura. O trabalho mais próximo em desenho — ecológico, com 3.467 municípios e binomial negativa — mede acesso à água, esgoto e coleta de resíduos combinados a transferência condicionada de renda, restringe o desfecho a menores de 5 anos e termina a série em 2016. Outro estudo relaciona investimento em saneamento a internações por doenças de veiculação hídrica em nível estadual. Uma avaliação da vigilância na região metropolitana do Rio de Janeiro correlacionou achados microbiológicos do SISAGUA com prevalência de protozoose intestinal, sem desfecho de mortalidade.

O uso do SISAGUA é raro. Uma busca no PubMed recupera doze artigos que o mencionam; deles, dois ligam o sistema a um desfecho de saúde — cárie dentária por cobertura de fluoretação, e mortalidade por câncer em 203 municípios da bacia do Rio Doce após o rompimento da barragem de Fundão. Os demais descrevem o sistema, avaliam completude de dados ou reportam contaminação química.

Vários desses trabalhos registram o não-reporte como **limitação**. Este artigo o trata como **exposição**. É a mesma observação lida ao contrário, e é a contribuição metodológica que ele pretende oferecer.

### 4.5 Implicações

Se a associação medida refletir mecanismo, a implicação é direta: os 384 municípios sem qualquer registro de vigilância no período constituem um alvo identificável e nominal, e a Tabela 10 os distribui por unidade da federação. Se ela refletir apenas marcador, o valor do achado passa a ser diagnóstico: a ausência de reporte ao SISAGUA identifica municípios em que a mortalidade por causa evitável se comporta de modo anômalo, e isso é informação de vigilância mesmo sem relação causal.

Nos dois casos, a recomendação operacional é a mesma e é modesta: **medir**. Um município que não reporta não é um município sobre o qual nada se sabe — é um município sobre o qual o sistema nacional escolheu não saber.

---

## 5. Material suplementar

As onze tabelas que sustentam cada número deste manuscrito estão publicadas como material suplementar, em CSV, e são regeradas por `artigo-agua/gerar_tabelas.py`, que **reexecuta a análise** antes de formatar. As cinco figuras são geradas por `artigo-agua/gerar_figuras.py` a partir das mesmas tabelas, sem nenhum cálculo próprio.

Os dados primários — o mart municipal do SISAGUA (397.380 linhas) e a sua tabela de cobertura (5.571 linhas, uma por município do país) — estão publicados com SHA-256 e são citáveis. A nota técnica da Lista Brasileira usada para transcrever o subgrupo 1.2 está arquivada em `data/refs/Obitos_Evitaveis_5_a_74_anos.pdf`.

### Figuras

**Figura 1.** Óbitos por doenças infecciosas intestinais, Brasil, 2015–2025, em contagem absoluta e por 10 mil óbitos do ano. O ano preliminar aparece com marcador vazado e linha pontilhada. *Fonte: Tabela 2.*

**Figura 2.** Variação dos óbitos por A00–A09 entre 2019 e 2024, por faixa etária. *Fonte: Tabela 3.*

**Figura 3.** Razão de mortalidade contra a classe de vigilância regular, para as duas entradas do subgrupo 1.2 da Lista Brasileira. *Fonte: Tabela 7.*

**Figura 4.** Razão de razões e IC95% para os quatro critérios. Marcador cheio indica critério declarado antes da análise; marcador vazado indica teste post-hoc. *Fonte: Tabela 8.*

**Figura 5.** Razão de razões dentro de cada faixa etária. *Fonte: Tabela 9.*

### Tabelas

**Tabela 1. O recorte: municípios, óbitos e pessoas-ano, 2015–2024 (`tabela_1_base.csv`).**

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

**Tabela 8. Os quatro critérios, com IC95% por bootstrap de município (`tabela_8_criterios.csv`).**

| Critério | Pré-declarado | RRR | IC95% inferior | IC95% superior | Exclui 1 |
|---|---|---|---|---|---|
| 1. Especificidade (bruto) | sim | 2,075 | 1,776 | 2,518 | sim |
| 2. Ajustado por acesso à água (MH) | sim | 1,926 | 1,618 | 2,225 | sim |
| Sensibilidade: controle só pneumonia/influenza | sim | 2,087 | 1,785 | 2,535 | sim |
| 4. Padronizado por idade (POST-HOC) | nao | 1,767 | 1,518 | 2,021 | sim |

**Tabela 9. Razão de razões dentro de cada faixa etária (`tabela_9_rrr_por_idade.csv`).**

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
