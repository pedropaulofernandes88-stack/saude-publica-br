# Saúde em Dado: uma plataforma aberta e reprodutível de indicadores epidemiológicos do SUS, com baseline de excesso de mortalidade robusto ao denominador populacional

**Pedro Paulo Fernandes**¹²³
ORCID: 0009-0008-6248-2486

¹ IAMSPE — Mestrado em Saúde Coletiva
² Hospital Sírio-Libanês — Pós-graduação em IA e Ciência de Dados em Saúde
³ Prefeitura Municipal de Penápolis — Diretoria de Tecnologia da Informação

Correspondência: pedropaulofernandes88@gmail.com

> **Status:** rascunho de nota de métodos (*methods paper*) para preprint
> (SciELO Preprints / medRxiv). Conteúdo ancorado na metodologia publicada em
> https://saudeemdado.com/metodologia. Versão em inglês a derivar.

---

## Resumo

**Contexto.** Os microdados do Sistema Único de Saúde (SUS) são públicos, mas a
distância entre o dado bruto e o indicador interpretável e reprodutível ainda é
grande. **Objetivo.** Descrever uma plataforma aberta e de custo zero que
transforma microdados do DataSUS e do IBGE em indicadores municipais validados,
com pipeline integralmente reprodutível, e relatar uma análise de sensibilidade
sobre o método de excesso de mortalidade. **Métodos.** Integramos cinco sistemas
de informação (SIM, SIH, SINAN, SINASC e Censo/IBGE), aplicando padronização
direta por idade (padrão Brasil, Censo 2022), intervalos de confiança exatos
(método gamma), e excesso de mortalidade com baseline 2015–2019. **Resultados.**
A plataforma cobre mortalidade (2015–2024), internações hospitalares (2022–2024),
dengue (2015–2024) e nascimentos (2021–2023), além de indicadores derivados
(ICSAP, fluxo intermunicipal, internações por agravo, visão hospitalar). Para o
excesso de mortalidade, substituímos o baseline "média × razão populacional" por
uma **tendência linear por mês civil**, que capta o envelhecimento populacional.
Em uma análise de sensibilidade, mostramos que uma variante padronizada por idade
**subestima** o excesso pandêmico (~505 mil vs. 643 mil) por contaminação do
denominador — a projeção populacional de 2018 superestima a população, e a série
pós-Censo 2022 introduz descontinuidade. **Conclusão.** O método de tendência,
por se apoiar apenas nos óbitos observados, é imune a esses problemas e foi
retido. Todo o dado agregado (CC BY 4.0), o código (MIT) e os checksums estão
publicados (DOI de conceito: 10.5281/zenodo.20706845).

**Palavras-chave:** saúde coletiva; DataSUS; mortalidade; excesso de mortalidade;
padronização por idade; dados abertos; reprodutibilidade; Brasil.

---

## 1. Introdução

A vigilância em saúde no Brasil produz alguns dos maiores conjuntos de microdados
de acesso público do mundo — o Sistema de Informações sobre Mortalidade (SIM), o
Sistema de Informações Hospitalares (SIH), o Sistema de Informação de Agravos de
Notificação (SINAN) e o Sistema de Informações sobre Nascidos Vivos (SINASC).
Apesar disso, transformar esses arquivos em indicadores comparáveis,
estatisticamente honestos e reprodutíveis exige etapas técnicas (decodificação de
arquivos `.dbc`, padronização etária, denominadores populacionais, intervalos de
confiança) que raramente são documentadas de forma auditável nos painéis
disponíveis.

Apresentamos a *Saúde em Dado*, uma plataforma aberta que (i) processa os
microdados oficiais por meio de um pipeline aberto e versionado; (ii) publica os
agregados em formato analítico (Parquet) com *checksums* e via API REST pública;
e (iii) documenta integralmente os métodos. O objetivo desta nota é descrever as
escolhas metodológicas e relatar uma análise de sensibilidade sobre o excesso de
mortalidade que tem implicações além desta plataforma.

## 2. Métodos

### 2.1 Fontes e processamento

- **Mortalidade (SIM):** microdados 2015–2024 (CSVs nacionais do OpenDataSUS para
  2022+; arquivos `.dbc` por UF/ano para 2015–2021). Óbitos fetais excluídos
  (`TIPOBITO=1`); município de residência (`CODMUNRES`); causa básica em CID-10.
- **Internações (SIH/AIH):** arquivos RD por UF/mês, 2022–2024 (rede SUS).
- **Dengue (SINAN):** arquivos nacionais `DENGBR`, 2015–2024.
- **Nascimentos (SINASC):** 2021–2023.
- **População:** IBGE — Censo 2022 e estimativas anuais (SIDRA); projeção 2018
  por idade/UF/ano para a análise de sensibilidade.

Os totais anuais são conferidos contra os volumes oficiais (p. ex., SIM 2015 =
1.264.175 óbitos) em integração contínua.

### 2.2 Padronização e incerteza

A taxa padronizada por idade usa o **método direto**, com população-padrão do
Brasil no Censo 2022 e 8 faixas etárias; óbitos com idade ignorada são
redistribuídos *pro rata*. A taxa bruta acompanha **IC95% pelo método gamma
(Poisson exato)**. Municípios com população < 10 mil habitantes são sinalizados,
dado que suas taxas são instáveis.

### 2.3 Excesso de mortalidade

Para cada UF e o Brasil, o número **esperado** de óbitos no mês *m* do ano *a* é
obtido por **regressão linear dos óbitos daquele mês civil contra o ano**, no
período 2015–2019, projetada para *a*. O **excesso** é a diferença entre o
observado e o esperado. Esse método capta empiricamente o crescimento e o
envelhecimento da população — que elevam o número esperado de óbitos ano a ano —
sem depender de um denominador populacional.

### 2.4 Indicadores derivados de internação

Sobre o SIH 2024, classificamos cada internação pelo diagnóstico principal e
derivamos: **ICSAP** (Internações por Condições Sensíveis à Atenção Primária,
aproximação da Lista Brasileira no nível de CID-10 de 3 caracteres), com
estimativa de **gasto potencialmente evitável** (nº de internações ICSAP × custo
médio das condições sensíveis) e **sinalização de outlier** (limite inferior do
IC95% de Wilson da proporção de ICSAP acima da média do recorte); **fluxo
intermunicipal** de pacientes (residência → atendimento); **internações por
agravo traçador** (CID-3); e **visão por estabelecimento (CNES)**.

## 3. Análise de sensibilidade: tendência vs. padronização por idade no excesso

A literatura de excesso de mortalidade frequentemente recomenda métodos que
ajustam pela estrutura etária. Testamos uma variante do esperado **padronizada
por idade**: taxas de mortalidade específicas por faixa etária (pooled 2015–2019,
por UF e mês civil) aplicadas à população por idade do ano-alvo, com a população
por idade/UF/ano da **projeção IBGE 2018** (SIDRA t/7358), em duas versões — cru
e reescalado ao total populacional pós-Censo.

**Resultado.** Ambas as versões padronizadas estimam o pico pandêmico (2020–2021)
em **~505–510 mil** óbitos em excesso, valor **inferior** tanto ao método de
tendência (**643 mil**) quanto ao consenso de estimativas independentes para o
Brasil (~660–680 mil; *World Mortality Dataset*; OMS), e produzem excesso
fortemente negativo a partir de 2023 (Tabela 1).

**Tabela 1.** Excesso de mortalidade no Brasil por método (óbitos).

| Período | Tendência (publicado) | Padronizado (projeção) | Padronizado (reescalado) |
|---|--:|--:|--:|
| 2020–2021 | 643.482 | 503.913 | 510.243 |
| 2022 | 144.541 | 36.182 | 121.406 |
| 2023 | 48.065 | −88.267 | −24.681 |
| 2024 | −9.018 | −174.699 | −134.195 |
| 2020–2024 | 827.070 | 277.129 | 472.774 |

**Diagnóstico.** A discrepância não decorre do método, mas do **denominador
populacional anual do Brasil em 2015–2024**:

1. A **projeção IBGE 2018 superestima** a população — o Censo 2022 a revisou para
   baixo (≈ 215 milhões projetados vs. 203 milhões recenseados). Uma população
   idosa inflada eleva o esperado e subestima o excesso, com viés que cresce ao
   longo do tempo.
2. A série **pós-Censo** corrige o nível, mas introduz uma **descontinuidade em
   2022** (≈ 211 milhões em 2020 → 203 milhões no Censo), que distorce os
   esperados em torno do rebasing.

Algebricamente, padronizar por idade com uma estrutura etária invariante no tempo
reduz-se exatamente ao método "média × razão populacional"; o ganho da
padronização depende inteiramente da qualidade da estrutura etária **anual**, que
para o Brasil neste período é justamente o elo fraco.

**Decisão.** O método de **tendência sobre os óbitos observados** não toca a
população e é, portanto, imune ao overcount pré-Censo e à descontinuidade de
2022. Por concordar melhor com as estimativas independentes e por sua robustez,
foi **retido como método publicado**. O código e a base desta análise estão no
repositório (`scripts/sensibilidade_excesso_idade.py`).

## 4. Resultados selecionados

- Excesso de mortalidade pandêmico (Brasil, 2020–2021): **643.482** óbitos
  (~8% abaixo do baseline anterior, por correção do envelhecimento); retorno ao
  patamar histórico a partir de 2022; 2024 próximo de zero (preliminar).
- ICSAP nacional 2024: proporção em torno de um quinto das internações, com
  estimativa de gasto evitável da ordem de bilhões de reais (ordem de grandeza).
- Cobertura: SIM 2015–2024; SIH 2022–2024; SINAN 2015–2024; SINASC 2021–2023.

## 5. Limitações

Cobertura e qualidade de registro do SIM variam regionalmente; ~5% dos óbitos têm
causa mal-definida e não são redistribuídos. As internações cobrem apenas a rede
SUS — comparações municipais são confundidas pela cobertura de planos privados. A
mortalidade hospitalar é bruta (não ajustada por *case-mix*). Indicadores
municipais são ecológicos. O baseline de excesso assume continuidade da tendência
pré-pandemia e não modela *harvesting*.

## 6. Disponibilidade de dados e código

- **Plataforma:** https://saudeemdado.com
- **Código:** https://github.com/pedropaulofernandes88-stack/saude-publica-br (MIT)
- **Dados agregados:** Parquet com checksum SHA-256 e API REST pública (CC BY 4.0)
- **DOI (conceito, todas as versões):** 10.5281/zenodo.20706845
- **Dados originais:** domínio público (DATASUS/Ministério da Saúde; IBGE)

Inspirações metodológicas creditadas ao projeto LabSUS (Lucas Amaral Dourado,
Universidade Federal do Tocantins).

## Referências (a completar na submissão)

1. Brasil, Ministério da Saúde / DATASUS. Microdados SIM, SIH, SINAN, SINASC.
2. IBGE. Censo Demográfico 2022; Estimativas e Projeções da População.
3. Karlinsky A, Kobak D. Excess mortality during the COVID-19 pandemic: World
   Mortality Dataset. *eLife*. 2021.
4. Organização Mundial da Saúde. Global excess deaths associated with COVID-19.
5. Brasil, Ministério da Saúde. Portaria SAS/MS 221/2008 (Lista Brasileira de
   ICSAP).
