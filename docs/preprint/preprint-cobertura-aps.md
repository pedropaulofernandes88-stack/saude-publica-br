# Cobertura potencial da Atenção Primária no Brasil: um indicador que mede porte municipal, não desempenho assistencial

**Pedro Paulo Fernandes**¹²³
ORCID: https://orcid.org/0009-0008-6248-2486

¹ IAMSPE — Mestrado em Saúde Coletiva
² Hospital Sírio-Libanês — Pós-graduação em IA e Ciência de Dados em Saúde
³ Prefeitura Municipal de Penápolis — Diretoria de Tecnologia da Informação

Correspondência: pedropaulofernandes88@gmail.com

> **Status:** rascunho de nota de pesquisa para preprint (SciELO Preprints). Ancorado
> nos dados públicos da plataforma Saúde em Dado (https://saudeemdado.com) e
> reprodutível a partir do repositório aberto do projeto.

---

## Resumo

**Contexto.** O Ministério da Saúde publica mensalmente, para todos os municípios
brasileiros, a *cobertura potencial da Atenção Primária à Saúde* (APS): a capacidade
de atendimento estimada das equipes credenciadas dividida pela população municipal.
É o indicador oficial mais usado para avaliar a extensão da atenção primária no país.
**Objetivo.** Testar se a cobertura potencial da APS se associa a um desfecho que
ela deveria prevenir — internações por Condições Sensíveis à Atenção Primária
(ICSAP) — e, em caso negativo, identificar a causa estrutural da ausência de
associação. **Métodos.** Cruzamos a cobertura potencial da APS (relatório público
e-Gestor AB/SAPS, competência de 2024) com o ICSAP (SIH/DataSUS, 2024) e um
índice-proxy de vulnerabilidade social (Censo 2022) para os 5.570 municípios
brasileiros. Calculamos correlação de postos (Spearman) bruta, parcial (controlando
porte populacional e vulnerabilidade) e estratificada por quartil de porte.
Testamos a robustez do achado substituindo a cobertura (percentual, sujeito a
saturação) por densidade real de equipes por 10 mil habitantes, comparando cada
município apenas aos pares do próprio quartil de porte, e substituindo ICSAP por
100 mil habitantes por %ICSAP (proporção sobre o total de internações do próprio
município, que remove o confundimento de acesso hospitalar geral). **Resultados.**
A cobertura potencial ultrapassa 100% em 86,1% dos municípios (mediana 149,1%,
máximo 803,21%) e correlaciona-se fortemente com o porte populacional
(ρ = −0,54), mas não com o ICSAP por 100 mil habitantes (ρ bruto = +0,004; ρ
parcial, controlando porte e vulnerabilidade = +0,018). Municípios com menos de
10 mil habitantes têm simultaneamente a maior cobertura mediana (167,1%) e o maior
ICSAP — o oposto da hipótese de política pública. O teste de robustez confirma o
achado nulo com um desenho mais estrito: a correlação entre densidade de equipes e
%ICSAP dentro do mesmo quartil de porte varia entre ρ = −0,02 e +0,18; a
co-ocorrência de baixa densidade de equipes com alto %ICSAP é 0,94 vezes o que a
independência estatística prevê — abaixo, não acima, do acaso. Um painel
longitudinal 2021-2024 (5.568 municípios) testando efeito de equipes recém-
implantadas, com efeito fixo duplo (município e ano) para remover uma tendência
nacional comum de alta em ambas as variáveis no período, confirmou o achado
nulo (|ρ| ≤ 0,032 em todos os desenhos: contemporâneo, diferença ano a ano e
defasado em 1 ano). O cruzamento com leitos hospitalares (CNES) mostrou que o
próprio desfecho responde à oferta local: ter leito no município quase dobra a
internação por ICSAP (+85% no 3º quartil de porte) sem alterar as demais —
oferta induzindo demanda nas internações que o indicador mede. Testando a
limitação de que o ICSAP (restrito ao SUS)
poderia estar subestimado onde a saúde suplementar é relevante (dados de
beneficiários, ANS), encontramos um efeito real, porém concentrado nos
municípios de maior porte (ρ = −0,29 no quartil superior, dentro do porte;
desprezível nos demais três quartis). **Conclusão.** A
cobertura potencial da APS, como calculada e publicada oficialmente, é
estatisticamente mais um proxy do tamanho do município do que uma medida do
desempenho da atenção primária, e não deve ser usada para ranquear municípios ou
inferir qualidade assistencial nesse uso agregado.

**Palavras-chave:** atenção primária à saúde; indicadores de saúde; internações
sensíveis à atenção ambulatorial; equidade em saúde; Brasil; validade de
constructo.

---

## Abstract

**Background.** Brazil's Ministry of Health publishes, monthly, for every
municipality, the *potential coverage of Primary Health Care*: estimated care
capacity of credentialed teams divided by municipal population. It is the most
widely used official indicator of primary care extent in the country.
**Objective.** To test whether potential PHC coverage is associated with an
outcome it should plausibly prevent — hospital admissions for Ambulatory Care
Sensitive Conditions (ACSC) — and, if not, to identify the structural cause.
**Methods.** We cross-referenced potential PHC coverage (public e-Gestor AB/SAPS
report, 2024) with ACSC admissions (Brazilian Hospital Information System, 2024)
and a social vulnerability proxy index (2022 Census) for all 5,570 Brazilian
municipalities. We computed Spearman rank correlations (crude, partial —
controlling for population size and vulnerability — and stratified by population
quartile). We tested robustness by replacing the saturating coverage percentage
with actual team density per 10,000 inhabitants, comparing each municipality only
to peers in its own population quartile, and replacing ACSC per 100,000 population
with %ACSC (share of the municipality's own total admissions, which removes the
confound of differential overall hospital access). **Results.** Potential coverage
exceeds 100% in 86.1% of municipalities (median 149.1%, maximum 803.21%) and
correlates strongly with population size (ρ = −0.54), but not with ACSC per
100,000 (crude ρ = +0.004; partial ρ, controlling for size and vulnerability =
+0.018). Municipalities under 10,000 inhabitants show simultaneously the highest
median coverage (167.1%) and the highest ACSC rate — the opposite of the policy
hypothesis. The robustness test confirms the null finding under a stricter design:
correlation between team density and %ACSC within the same population quartile
ranges from ρ = −0.02 to +0.18; co-occurrence of low team density with high %ACSC
is 0.94 times what statistical independence would predict — below, not above,
chance. A 2021-2024 longitudinal panel (5,568 municipalities) testing for a
delayed effect of newly implemented teams, using two-way fixed effects
(municipality and year) to remove a shared national upward trend in both
variables over the period, confirmed the null finding (|ρ| ≤ 0.032 across all
specifications: contemporaneous, year-over-year difference, and 1-year lag).
Cross-referencing with hospital beds (CNES) showed that the outcome itself
responds strongly to local supply: having a hospital bed in the municipality
nearly doubles ACSC admissions (+85% in the 3rd population quartile) while
leaving other admissions unchanged — supply inducing demand precisely in the
admissions the indicator measures.
Testing the limitation that ACSC (SUS-restricted) may be underestimated where
private health coverage is relevant (ANS beneficiary data), we found a real
but size-concentrated effect (ρ = −0.29 in the top population quartile,
within-quartile; negligible in the other three quartiles).
**Conclusion.** Potential PHC coverage, as officially calculated and
published, is statistically more a proxy for municipal size than a measure of
primary care performance, and should not be used to rank municipalities or infer
assistance quality in this aggregate form.

**Keywords:** primary health care; health status indicators; ambulatory care
sensitive conditions; health equity; Brazil; construct validity.

---

## 1. Introdução

Internações por Condições Sensíveis à Atenção Primária (ICSAP) — hospitalizações
que uma atenção básica efetiva poderia ter evitado — são um dos indicadores mais
usados internacionalmente para avaliar indiretamente o desempenho da atenção
primária [1,2]. No Brasil, o Ministério da Saúde publica paralelamente, desde
2021, um indicador direto de extensão da atenção primária: a **cobertura potencial
da APS**, calculada mensalmente para cada município a partir do número de equipes
credenciadas (Estratégia Saúde da Família, Equipes de Atenção Primária, equipes
ribeirinhas, consultórios na rua) e de suas capacidades de atendimento
padronizadas.

A expectativa de política pública é direta: mais cobertura de atenção primária
deveria associar-se a menos internações evitáveis. Esta nota testa essa
expectativa com os dados públicos oficiais dos dois sistemas, para todos os
municípios brasileiros, e relata um achado negativo com uma explicação estrutural
identificável — que tem implicação prática para qualquer gestor ou pesquisador que
use a cobertura potencial da APS como métrica de desempenho.

## 2. Métodos

### 2.1 Fontes de dados

- **Cobertura potencial da APS:** relatório público de Cobertura da Atenção
  Primária (Ministério da Saúde / SAPS / e-Gestor AB), competências mensais de
  janeiro de 2021 à mais recente disponível; nesta análise, a competência de 2024
  (média das 12 competências do ano). Cobre 5.571 municípios.
- **ICSAP:** classificação do diagnóstico principal de cada internação do
  Sistema de Informações Hospitalares (SIH/DataSUS), 2024, segundo aproximação da
  Lista Brasileira de ICSAP (Portaria SAS/MS 221/2008) no nível de CID-10 de 3
  caracteres.
- **Vulnerabilidade social:** índice-proxy por z-score de taxa de analfabetismo e
  percentual de domicílios sem rede geral de água (Censo Demográfico 2022,
  IBGE/SIDRA) — não o IVS oficial do IPEA (ano-base 2010, 16 indicadores).

### 2.2 Definição do indicador testado

A cobertura potencial é definida oficialmente como a capacidade de atendimento
estimada das equipes credenciadas, dividida pela população do município. Cada
tipo de equipe (ESF, EAP 20h, EAP 30h, eSFR, eCR, EAPP) tem uma capacidade de
atendimento padronizada nacionalmente, independente do tamanho do município onde
atua.

### 2.3 Análise estatística

Calculamos a correlação de postos de Spearman entre cobertura potencial (bruta e
"efetiva", truncada em 100%) e ICSAP por 100 mil habitantes, em três níveis:

1. **Bruta**, para os 5.570 municípios.
2. **Parcial**, controlando população municipal e o índice de vulnerabilidade,
   via regressão linear sobre os postos das três variáveis (equivalente a
   correlação parcial de Spearman).
3. **Estratificada**, em quatro faixas de porte populacional (< 10 mil; 10–50 mil;
   50–200 mil; > 200 mil habitantes).

### 2.4 Teste de robustez com desenho pareado por porte

Para eliminar a hipótese de que a comparação só seria inválida *entre* portes
diferentes — mas válida *dentro* do mesmo porte —, refizemos a análise substituindo:

- a cobertura percentual (sujeita a saturação acima de 100%) pela **densidade real
  de equipes de Saúde da Família por 10 mil habitantes**, que não tem teto;
- o ICSAP por 100 mil habitantes pelo **%ICSAP** (proporção do total de
  internações do próprio município), que normaliza pelo volume de acesso
  hospitalar geral do município — um passo necessário porque, como relatado
  abaixo, o acesso hospitalar geral varia com a vulnerabilidade social
  independentemente do ICSAP.

Municípios foram estratificados em quartis de população, e o percentil de cada
um em densidade de equipes e em %ICSAP foi calculado **dentro do próprio
quartil de porte** (não em relação ao Brasil inteiro). Testamos se a co-ocorrência
de baixa densidade de equipes (terço inferior) com alto %ICSAP (terço superior)
excede o que a independência estatística entre as duas variáveis prediria
(produto das taxas marginais).

### 2.5 Teste longitudinal com efeito fixo municipal (2021-2024)

Para testar diretamente a principal limitação do desenho transversal — a
possibilidade de que equipes recém-implantadas ainda não tenham tido tempo de
afetar o desfecho —, reprocessamos o ICSAP por município para 2021, 2022 e 2023
(2024 já disponível a partir da análise principal), construindo um painel
balanceado de 5.568 municípios ao longo de 4 anos (22.272 observações
município-ano). Aplicamos efeito fixo municipal — subtraindo, para cada
município, sua própria média no período — à densidade de ESF e ao %ICSAP,
testando a correlação contemporânea "dentro do município". Testamos também a
primeira diferença ano a ano e uma versão defasada em 1 ano (densidade de ESF
no ano *t* explicando %ICSAP no ano *t*+1), ambas as formas de aproximar o
efeito de implantação recente de equipes.

### 2.6 Teste da limitação de saúde suplementar

O ICSAP, por depender do SIH/SUS, não captura internações da rede privada —
uma limitação declarada na Seção 5, mas até então não testada. Trouxemos o
número de **vínculos ativos a plano de saúde médico-hospitalar por 100
habitantes** por município (ANS, Dados Abertos, competência de dezembro de
2024, sem autenticação) e testamos se ele explica parte da variação do ICSAP:
correlação bruta, parcial (controlando porte e vulnerabilidade) e — o teste
decisivo — dentro de cada quartil de porte (mesmo desenho da Seção 2.4), já
que uma correlação parcial por regressão linear sobre postos pode não remover
completamente um efeito de porte não-linear.

A unidade importa e é declarada aqui em vez de assumida: o SIB/ANS registra
*vínculos* (beneficiário × produto × operadora), não pessoas únicas, e
localiza cada registro pelo **endereço do contrato**, não pela residência
[Saldanha, cap. ANS]. A razão vínculos/população não é, portanto, uma
proporção de pessoas cobertas e pode ultrapassar 100 — ocorre em 1 dos 22.284
município-ano da série (Belém/AL, 2021: 115,9 vínculos/100 hab. para 4.226
habitantes). Como os testes desta seção são de posto (Spearman), a distorção
só importaria se reordenasse municípios, e não apenas inflasse valores;
verificamos isso na análise de sensibilidade da Seção 3.7 em vez de supor.

### 2.7 Teste da influência da oferta hospitalar sobre o desfecho

Para verificar se o próprio ICSAP responde à disponibilidade de leitos,
processamos o grupo LT do CNES (FTP do DataSUS, competência de dezembro de
2024), que traz leitos por estabelecimento, tipo e vínculo SUS. Agregamos por
município e cruzamos com o ICSAP. Além das correlações (bruta, parcial e por
quartil de porte), decompusemos as internações em ICSAP e não-ICSAP por
habitante, comparando municípios com e sem leito hospitalar próprio dentro de
cada quartil — essa decomposição distingue um efeito sobre o numerador
(mais internações sensíveis) de um efeito sobre o denominador (menos
internações de outros tipos), que é a diferença entre as duas explicações
concorrentes.

## 3. Resultados

### 3.1 O indicador satura

A cobertura potencial da APS ultrapassa 100% em **86,1%** dos municípios
brasileiros (mediana 149,1%; máximo 803,21%). Isso não é um artefato — é
consequência direta da definição oficial: como a capacidade de cada equipe é
padronizada nacionalmente, poucas equipes já saturam o indicador em municípios
pequenos.

### 3.2 Ausência de associação com ICSAP

| Correlação (Spearman) | ρ |
|---|--:|
| Cobertura bruta × ICSAP/100k | +0,004 |
| Cobertura efetiva (truncada em 100%) × ICSAP/100k | +0,096 |
| Cobertura bruta × ICSAP/100k, parcial (controlando porte e IVS) | +0,018 |
| Cobertura efetiva × ICSAP/100k, parcial | +0,124 |
| População × cobertura bruta | **−0,538** |
| População × ICSAP/100k | −0,076 |

**Tabela 1.** Correlações entre cobertura potencial da APS e ICSAP, Brasil, 2024
(n = 5.570 municípios).

A correlação entre cobertura e população (ρ = −0,538) é a mais forte da tabela —
mais forte que qualquer correlação entre cobertura e o desfecho que ela deveria
prever.

### 3.3 Estratificação por porte: o gradiente é de tamanho, não de atenção primária

| Porte | Municípios | Cobertura mediana | Saturados (>100%) | ICSAP/100k mediano |
|---|--:|--:|--:|--:|
| < 10 mil hab. | 2.466 | 167,1% | 97% | 1.467,8 |
| 10–50 mil | 2.429 | 142,0% | 88% | 1.545,9 |
| 50–200 mil | 517 | 97,1% | 46% | 1.219,7 |
| > 200 mil | 158 | 78,7% | 13% | 959,8 |

**Tabela 2.** Cobertura potencial e ICSAP por porte municipal, Brasil, 2024.

Os municípios de menor porte têm, simultaneamente, a maior cobertura mediana e o
maior ICSAP. Se a cobertura potencial medisse força da atenção primária, o
gradiente de ICSAP seria inverso ao de cobertura; ele acompanha, na prática, o
porte.

### 3.4 O teste de robustez confirma o achado, com desenho mais estrito

Substituindo cobertura por densidade de equipes e ICSAP/100k por %ICSAP, e
comparando cada município apenas a seus pares de mesmo porte:

| Quartil de porte | n | ρ (densidade de ESF × %ICSAP, dentro do porte) |
|---|--:|--:|
| Q1 (menores) | 1.393 | −0,009 |
| Q2 | 1.392 | −0,001 |
| Q3 | 1.392 | −0,020 |
| Q4 (maiores) | 1.393 | +0,182 |

**Tabela 3.** Correlação entre densidade de equipes de Saúde da Família e %ICSAP,
dentro de cada quartil de porte populacional.

A taxa de co-ocorrência entre baixa densidade de equipes (terço inferior, dentro
do porte) e alto %ICSAP (terço superior, dentro do porte) foi de 10,50% dos
municípios. Sob independência estatística entre as duas variáveis, o valor
esperado seria 11,12% (33,3% × 33,4%). A razão observado/esperado é **0,94** —
a co-ocorrência não apenas não excede o acaso, fica ligeiramente abaixo dele.

### 3.5 Por que o ICSAP por 100 mil habitantes cai em municípios vulneráveis — e por que isso não é o que parece

Ao cruzar com o índice-proxy de vulnerabilidade social, o ICSAP por 100 mil
habitantes cai monotonicamente do quartil menos vulnerável (mediana 1.490,3) ao
mais vulnerável (mediana 1.221,9). Isolado, esse padrão sugeriria que municípios
vulneráveis têm melhor desempenho relativo de atenção primária. Encontramos,
porém, que as **internações totais por mil habitantes** também caem com a
vulnerabilidade (78,6 no quartil menos vulnerável; 63,4 no mais vulnerável) — um
padrão consistente com barreira de acesso hospitalar geral, não com melhor
atenção primária especificamente. Ao normalizar pelo próprio volume de internações
(%ICSAP), a diferença desaparece: 18,9%, 20,9%, 20,6% e 19,7% nos quatro quartis
de vulnerabilidade, sem gradiente identificável.

A densidade de equipes de Saúde da Família, por sua vez, **aumenta** com a
vulnerabilidade dentro de cada quartil de porte (percentil médio de 32,2 no
quartil menos vulnerável a 64,5 no mais vulnerável) — um sinal de que a alocação
de equipes responde à vulnerabilidade social, mesmo que essa alocação não se
traduza, nestes dados transversais de um ano, em diferença mensurável de %ICSAP.

### 3.6 Confirmação longitudinal — e um sexto caso do confundimento por tendência comum

O primeiro teste longitudinal (efeito fixo municipal simples) produziu
ρ = +0,132 — um sinal aparente, na direção oposta à hipótese de política
pública, e crescente com o porte (de +0,046 no menor quartil a +0,213 no
maior). A investigação da causa revelou outro confundimento: tanto a
densidade de ESF quanto o %ICSAP cresceram nacionalmente no período 2021-2024
(ESF: média 3,67 → 4,05 por 10 mil hab.; %ICSAP: média 17,9% → 21,2%),
provavelmente por retomada pós-pandemia de atendimentos adiados — uma
tendência de calendário comum às duas variáveis, sem relação causal entre si.

| Desenho | ρ |
|---|--:|
| Efeito fixo municipal (uma via) | +0,132 |
| Efeito fixo duplo (município + ano) | **+0,006** |
| Primeira diferença ano a ano (demeada por ano) | entre −0,032 e +0,015 |
| Efeito fixo duplo, defasado em 1 ano | +0,012 |

**Tabela 4.** Densidade de ESF × %ICSAP, painel 2021-2024 (n = 22.272
observações município-ano; 5.568 municípios).

Ao remover também o efeito de ano (efeito fixo duplo), ρ caiu para +0,006. A
primeira diferença ano a ano (demeada por ano, para não herdar o mesmo viés de
tendência comum) e a versão defasada em 1 ano confirmaram: |ρ| ≤ 0,032 em
todos os desenhos corretamente especificados.

Esse episódio é, em si, uma instância do problema central deste programa de
pesquisa: uma tendência temporal compartilhada produz associação espúria do
mesmo modo que um confundidor transversal (porte municipal) produzia
associação espúria na análise principal deste preprint. A correção — efeito
fixo duplo, não apenas municipal — é o equivalente temporal do desenho pareado
por porte da Seção 2.4. Com essa correção, o painel longitudinal **confirma**,
em vez de qualificar, o achado nulo transversal: não há associação
mensurável entre densidade de ESF e %ICSAP, nem contemporânea nem defasada em
1 ano, dentro do mesmo município ao longo de 2021-2024.

### 3.7 A limitação de saúde suplementar é real, mas concentrada nos grandes municípios

A densidade mediana de vínculos a plano é baixa e quase invariante nos
municípios menores (4,5 e 4,1 por 100 hab. nos dois primeiros quartis de
porte) e alta e heterogênea nos maiores (mediana 31,9 no quartil superior).
Essa diferença de variância já antecipa onde um efeito, se existir, poderia
aparecer.

| Quartil de porte | n | ρ (vínculos/100 hab. × %ICSAP, dentro do porte) | ρ excluindo suspeitos |
|---|--:|--:|--:|
| Q1 (menores) | 1.393 | +0,05 | +0,06 |
| Q2 | 1.392 | −0,00 | +0,01 |
| Q3 | 1.392 | −0,08 | −0,08 |
| Q4 (maiores) | 1.393 | **−0,29** | **−0,29** |

**Tabela 5.** Correlação entre densidade de vínculos a plano e %ICSAP, dentro
de cada quartil de porte populacional, 2024. A última coluna repete o teste
excluindo os municípios em que o indicador da ANS é suspeito de artefato de
endereço de contrato (razão > 100, e municípios com menos de 20 mil habitantes
e mais de 40 vínculos/100 hab.; 33 exclusões, 0,6% da amostra). O gradiente é
insensível à exclusão.

O padrão não é ruído aleatório trocando de sinal — é um **gradiente
monotônico por porte**, praticamente nulo nos municípios pequenos e moderado,
na direção teoricamente esperada (mais saúde suplementar, menos ICSAP
registrado no SUS), nos maiores. A correlação parcial pooled, controlando
porte por regressão linear sobre postos (ρ = −0,102, Seção 2.6), subestimava
essa estrutura ao tentar resumir um efeito não-linear-por-porte em um único
coeficiente. A co-ocorrência de alta saúde suplementar com baixo %ICSAP,
dentro do porte, é **1,00×** o esperado sob independência estatística — nula
no agregado nacional, porque a maioria dos municípios brasileiros (Q1-Q3, ~75%
da amostra) tem cobertura de saúde suplementar baixa demais e homogênea demais
para gerar variação detectável.

**Leitura:** a limitação declarada — ICSAP subestimado onde a saúde
suplementar é relevante — é empiricamente real, mas **localizada**: relevante
para interpretar o ICSAP de grandes municípios (Q4, tipicamente capitais e
regiões metropolitanas), e irrelevante para a grande maioria dos municípios
brasileiros, que é onde a discussão de cobertura da APS e equidade neste
preprint se concentra. Isso não muda a conclusão principal (ausência de
associação entre cobertura potencial da APS e ICSAP), mas qualifica onde o
ICSAP como desfecho deve ser lido com mais cautela.

### 3.8 O ICSAP responde à oferta hospitalar local — e o efeito é grande

Uma objeção recorrente ao uso do ICSAP diz que a proporção estaria inflada
onde falta leito, porque a internação eletiva desapareceria e a fatia de ICSAP
subiria mecanicamente. Testamos essa hipótese cruzando o ICSAP com os leitos
hospitalares por município (CNES grupo LT, dezembro de 2024, 5.570
municípios). O resultado contradiz a hipótese na direção **e** no mecanismo.

A correlação entre leitos SUS por mil habitantes e %ICSAP é **positiva**:
ρ = +0,32 bruta, +0,34 controlando porte populacional e vulnerabilidade, e
entre +0,15 e +0,47 dentro de cada quartil de porte (positiva nos quatro).
Municípios sem leito local têm %ICSAP **menor** (mediana 17,7%), não maior,
que os municípios com leito (21,4%).

A decomposição das internações identifica o mecanismo:

| Porte | Oferta local | ICSAP /100 mil | Não-ICSAP /100 mil | %ICSAP |
|---|---|--:|--:|--:|
| Q2 | sem leito | 1.156 | 5.483 | 17,3% |
| Q2 | com leito | **1.745** (+51%) | 5.887 (+7%) | 22,8% |
| Q3 | sem leito | 961 | 5.145 | 15,4% |
| Q3 | com leito | **1.782** (+85%) | 5.728 (+11%) | 23,5% |
| Q4 | sem leito | 877 | 5.604 | 14,6% |
| Q4 | com leito | **1.343** (+53%) | 5.571 (−1%) | 19,4% |

**Tabela 6.** Internações por 100 mil habitantes segundo a existência de leito
hospitalar no próprio município, dentro de cada quartil de porte, 2024.

O efeito da presença de leito local incide quase inteiramente sobre o
numerador: a internação por condições sensíveis à atenção primária praticamente
dobra, enquanto as demais internações mal se alteram. Não é a internação
eletiva que desaparece por falta de leito — é a internação sensível que
**aparece** quando existe leito na cidade. Pneumonia, desidratação e
descompensação de insuficiência cardíaca são exatamente o perfil que um
hospital de pequeno porte interna; sem leito local, esses casos são manejados
ambulatorialmente ou não motivam deslocamento, enquanto o caso complexo se
desloca de todo modo. Trata-se de oferta induzindo demanda, concentrada nas
internações discricionárias que o ICSAP mede.

A implicação é direta e simétrica ao achado central deste preprint: assim como
a cobertura potencial da APS mede porte municipal, o %ICSAP mede, em parte
relevante, **a existência de leito hospitalar no município**. Um município que
inaugura um hospital de pequeno porte verá seu %ICSAP subir e, pela leitura
convencional do indicador, seria classificado como tendo piorado sua atenção
primária — quando o que mudou foi a oferta hospitalar.

Ressalva semântica: o ICSAP é medido por município de *residência* do paciente
e os leitos por município do *estabelecimento*. "Sem leito" significa ausência
de oferta **local**, não ausência de acesso — o residente interna-se em outro
município e a internação é contabilizada em sua residência. O efeito medido
opera, portanto, por barreira de deslocamento.

## 4. Discussão

O achado central — ausência de associação entre cobertura potencial da APS e
ICSAP — sobreviveu a quatro tentativas progressivamente mais rigorosas de
encontrá-la — e um teste adicional revelou que o próprio desfecho responde
fortemente à oferta hospitalar local (Seção 3.8), reforçando o argumento
central por outra via: tanto o indicador de insumo (cobertura) quanto o de
desfecho (%ICSAP) medem, em boa parte, características estruturais do
município e não desempenho assistencial. As quatro tentativas foram:
correlação bruta, correlação parcial controlando os confundidores
óbvios, um desenho pareado por porte com métricas que não saturam nem herdam o
confundimento de acesso hospitalar geral, e um painel longitudinal 2021-2024
com efeito fixo municipal e de ano. Isso reduz substancialmente a
possibilidade de que o resultado nulo seja artefato de uma escolha metodológica
específica ou da janela temporal de um único ano.

A explicação estrutural é direta: a cobertura potencial, por definição, é uma
razão entre capacidade padronizada e população. Ela responde primariamente à
pergunta "quantas pessoas este município tem, dado o número de equipes que
recebeu" — não à pergunta "esta atenção primária funciona bem". As duas perguntas
foram tratadas, na política pública corrente, como a mesma pergunta.

A implicação prática é dupla. Primeiro, para gestores e pesquisadores: a
cobertura potencial da APS, no uso agregado por município, não deve ser
interpretada como proxy de qualidade ou desempenho assistencial, e comparações
entre municípios de portes diferentes usando esse indicador devem ser evitadas.
Seu uso válido — acompanhar a evolução de um mesmo município ao longo do tempo, e
contar equipes credenciadas — permanece intacto. Segundo, para o desenho de
indicadores: a alocação de recursos (equipes) parece responder à vulnerabilidade
social de forma mais consistente do que o desfecho equivalente (ICSAP) reflete —
uma divergência entre insumo e resultado que, mesmo testada com painel
longitudinal 2021-2024 (Seção 3.6), permanece sem associação mensurável com
%ICSAP nesse período de observação.

## 5. Limitações

O índice de vulnerabilidade é um proxy de duas dimensões (Censo 2022), não o
IVS oficial do IPEA. O ICSAP é uma aproximação da Lista Brasileira no nível de
CID-10 de 3 caracteres e cobre apenas a rede SUS — municípios com maior
cobertura de saúde suplementar podem ter ICSAP subestimado por razões não
relacionadas à atenção primária. Testamos essa limitação diretamente (Seção
3.7): o efeito é real, mas concentrado nos municípios de maior porte (ρ =
−0,29 no quartil superior, dentro do porte), sendo desprezível nos ~75% dos
municípios brasileiros de menor porte, que concentram a discussão deste
preprint. A cobertura potencial reflete equipes credenciadas e sua capacidade
nominal, não a qualidade do cuidado prestado por cada equipe. O painel
longitudinal cobre 4 anos (2021-2024): não se pode excluir um efeito de
equipes recém-implantadas com defasagem superior a 1 ano, embora o padrão
observado (nenhum sinal em nenhuma defasagem testada) não sugira essa
hipótese. Ao vetar fontes de dado sobre saúde suplementar, descartamos o
conjunto `taxa_de_cobertura_de_planos_de_saude` da ANS (indicador pronto por
município): a amostra verificada trazia apenas o período corrente e taxas
zeradas mesmo para São Paulo, sugerindo problema de qualidade nesse recorte
específico; optamos pelo cadastro de beneficiários (`informacoes_consolidadas_
de_beneficiarios`), mais granular mas com histórico íntegro desde 2021.

## 6. Disponibilidade de dados e código

- **Plataforma:** https://saudeemdado.com/atencao-basica
- **Código:** https://github.com/pedropaulofernandes88-stack/saude-publica-br
  (MIT) — `scripts/analise_cobertura_icsap.py`, `scripts/analise_equidade_aps.py`,
  `scripts/analise_equidade_aps_longitudinal.py`,
  `scripts/pipeline_ans_beneficiarios.py`, `scripts/analise_saude_suplementar_icsap.py`,
  `scripts/pipeline_cnes_leitos.py`, `scripts/analise_leitos_icsap.py`
- **Dados agregados:** Parquet com checksum SHA-256 e API REST pública (CC BY 4.0)
  — `mart_cobertura_aps_municipio`, `mart_cobertura_icsap_municipio`,
  `mart_equidade_aps_municipio`, `mart_equidade_aps_longitudinal`,
  `mart_saude_suplementar_municipio`, `mart_saude_suplementar_icsap_municipio`,
  `mart_leitos_municipio`, `mart_leitos_icsap_municipio`
- **Dados originais:** domínio público (Ministério da Saúde/SAPS; DATASUS; IBGE;
  ANS Dados Abertos)

## Conflito de interesses

O autor declara não haver conflito de interesses.

## Financiamento

A pesquisa não recebeu financiamento específico de agências de fomento dos
setores público, privado ou sem fins lucrativos.

## Referências

1. Billings J. et al. Impact of socioeconomic status on hospital use in New York
   City. Health Affairs. 1993.
2. Alfradique M.E. et al. Internações por condições sensíveis à atenção primária:
   a construção da lista brasileira como ferramenta para medir o desempenho do
   sistema de saúde. Cadernos de Saúde Pública. 2009.
3. Brasil, Ministério da Saúde. Portaria SAS/MS 221/2008 (Lista Brasileira de
   ICSAP).
4. Brasil, Ministério da Saúde, Secretaria de Atenção Primária à Saúde. Relatório
   de Cobertura da Atenção Primária. relatorioaps.saude.gov.br.
5. IBGE. Censo Demográfico 2022. SIDRA.
6. Saldanha R.F. Sistemas de Informação em Saúde no Brasil.
   rfsaldanha.github.io/sis (cap. ANS, cap. SIH).
7. Saúde em Dado. mart_cobertura_aps_municipio, mart_cobertura_icsap_municipio,
   mart_equidade_aps_municipio. saudeemdado.com/atencao-basica.
