/**
 * artigos.tsx — conteúdo da seção de Análises (artigos assinados).
 *
 * Cada artigo é dado estruturado (resumo, seções, referências) renderizado por
 * um template consistente. Números citados vêm dos marts do próprio projeto
 * (SIM, SINAN, SIH, SINASC, IVS-proxy), validados contra fontes oficiais.
 */

export const AUTHOR = {
  nome: "Pedro Fernandes",
  // Preencha as URLs; os botões só aparecem quando preenchidos.
  lattes: "",
  linkedin: "",
  credenciais: [
    "Mestrando em Saúde Coletiva (IAMSPE)",
    "Pós-graduando em Inteligência Artificial e Ciência de Dados em Saúde (Hospital Sírio-Libanês)",
    "Diretor de Tecnologia da Informação — Prefeitura Municipal de Penápolis (SP)",
  ],
  resumoBio:
    "Pesquisador na interseção entre saúde coletiva, ciência de dados e gestão pública. Concebeu e mantém a plataforma Saúde em Dado.",
};

export interface Secao {
  titulo?: string;
  paragrafos: string[];
  lista?: string[];
}

export interface Artigo {
  slug: string;
  titulo: string;
  dek: string;
  data: string;        // ISO
  leituraMin: number;
  tags: string[];
  resumo: string;
  secoes: Secao[];
  referencias: string[];
}

export const ARTIGOS: Artigo[] = [
  {
    slug: "epidemia-dengue-2024-anatomia-recorde",
    titulo: "A epidemia de dengue de 2024: anatomia de um recorde",
    dek: "Com 6,56 milhões de casos prováveis, 2024 foi o maior surto de dengue já registrado no Brasil. O que os microdados do SINAN revelam sobre escala, sazonalidade e letalidade.",
    data: "2026-03-04",
    leituraMin: 7,
    tags: ["dengue", "SINAN", "epidemiologia", "vigilância"],
    resumo:
      "Analisamos 6.564.924 casos prováveis de dengue notificados ao SINAN em 2024, contra uma média de ~1,3 milhão/ano na década anterior. A magnitude do surto, sua concentração no primeiro semestre e a distribuição espacial são examinadas à luz do canal endêmico construído a partir da série 2015–2023.",
    secoes: [
      {
        paragrafos: [
          "A dengue é doença de notificação compulsória no Brasil desde a década de 1990, e o Sistema de Informação de Agravos de Notificação (SINAN) é a sua principal fonte de vigilância. Em 2024, os microdados nacionais registraram 6.564.924 casos prováveis — definidos como notificações não descartadas após investigação — um valor sem precedentes na série histórica.",
          "Para dimensionar o evento, comparamos esse total com os anos anteriores processados nesta plataforma: 2015 (1,62 milhão), 2019 (1,55 milhão) e 2023 (1,65 milhão) figuravam entre os mais intensos até então. O ano de 2024 multiplica por aproximadamente quatro o pior ano prévio recente, configurando não uma flutuação, mas uma ruptura de patamar.",
        ],
      },
      {
        titulo: "O canal endêmico como termômetro",
        paragrafos: [
          "Para distinguir variação sazonal esperada de surto, construímos um diagrama de controle (canal endêmico): para cada semana epidemiológica, calculamos a mediana e os quartis (P25–P75) dos casos no período 2015–2023. A faixa interquartil define o comportamento esperado; valores acima do P75 sinalizam atividade epidêmica.",
          "Em 2024, a curva observada rompe o limite superior já nas primeiras semanas do ano e permanece acima dele por todo o primeiro semestre, com pico nas semanas de fevereiro a abril — o padrão clássico do verão brasileiro, porém em amplitude inédita. A ferramenta interativa do projeto permite reproduzir esse diagrama para cada unidade federativa.",
        ],
      },
      {
        titulo: "Gravidade e letalidade",
        paragrafos: [
          "Casos graves (dengue com sinais de alarme ou dengue grave, na classificação vigente) e óbitos pelo agravo acompanham, com defasagem, o volume de casos. Em números absolutos, 2024 registrou a maior quantidade de óbitos da série. Ainda assim, a letalidade — óbitos divididos por casos prováveis — permaneceu baixa, abaixo de 0,1% no agregado nacional, comportamento esperado para a dengue quando há capacidade assistencial preservada.",
          "Essa aparente contradição (recorde de óbitos com baixa letalidade) é estatística e não clínica: quando o denominador cresce de forma explosiva, mesmo letalidades pequenas produzem grandes números absolutos. A leitura correta exige sempre os dois indicadores juntos.",
        ],
      },
      {
        titulo: "Implicações para a vigilância",
        paragrafos: [
          "A escala de 2024 reacende o debate sobre fatores estruturais — urbanização, saneamento, circulação de sorotipos, El Niño e clima — e sobre a necessidade de sistemas de alerta precoce. A disponibilização dos microdados agregados em formato aberto e consultável, como nesta plataforma, é condição para que pesquisadores e gestores municipais respondam mais rápido na próxima temporada.",
        ],
      },
    ],
    referencias: [
      "BRASIL. Ministério da Saúde. SINAN — Sistema de Informação de Agravos de Notificação. Microdados de dengue, 2015–2024.",
      "Saúde em Dado. mart_dengue_semana e mart_dengue_municipio_ano. saudeemdado.com.",
      "Organização Pan-Americana da Saúde. Diretrizes para diagrama de controle e canal endêmico.",
    ],
  },
  {
    slug: "excesso-mortalidade-pos-pandemia",
    titulo: "Excesso de mortalidade no Brasil (2020–2024): o que sobrou da pandemia",
    dek: "Comparando o observado ao esperado pela média 2015–2019, estimamos 702 mil óbitos em excesso no biênio pandêmico — e analisamos o retorno gradual ao patamar histórico.",
    data: "2026-02-10",
    leituraMin: 8,
    tags: ["mortalidade", "SIM", "excesso de mortalidade", "COVID-19"],
    resumo:
      "O excesso de mortalidade é a métrica mais robusta para medir o impacto total de uma crise sanitária, pois independe da causa declarada. Construímos um baseline 2015–2019 ajustado por população e quantificamos o excesso mensal por UF e Brasil de 2020 a 2024.",
    secoes: [
      {
        paragrafos: [
          "Durante emergências sanitárias, a contagem direta de mortes por uma causa específica subestima o impacto real: há subdiagnóstico, sobrecarga dos serviços e mortes indiretas. O excesso de mortalidade — diferença entre os óbitos observados e os esperados na ausência da crise — contorna esses vieses e é hoje o padrão internacional de avaliação.",
          "Nossa estimativa do esperado parte da média de óbitos do mesmo mês civil no período 2015–2019, multiplicada pela razão entre a população do ano e a população média do baseline. É um método transparente e replicável, deliberadamente simples; não modela tendência secular nem mudanças na estrutura etária além do ajuste populacional — limitações que declaramos explicitamente.",
        ],
      },
      {
        titulo: "O biênio 2020–2021",
        paragrafos: [
          "O excesso concentrou-se em 2020 e 2021, somando aproximadamente 702.871 óbitos acima do esperado no agregado nacional — magnitude compatível com as estimativas independentes publicadas para o período. Os picos mensais acompanham as ondas da pandemia, com destaque para o primeiro semestre de 2021, o mais letal da série.",
          "A desagregação por unidade federativa, disponível na plataforma, revela forte heterogeneidade regional no tempo e na intensidade — reflexo de diferenças em estrutura etária, acesso a leitos, momento de circulação viral e cobertura vacinal.",
        ],
      },
      {
        titulo: "2022–2024: normalização com ressalvas",
        paragrafos: [
          "A partir de 2022, o excesso recua de forma consistente, aproximando-se de zero — indício de retorno ao regime pré-pandêmico. Contudo, a interpretação do ano mais recente exige cautela: dados de 2024 ainda são preliminares e sujeitos a revisão pelo Ministério da Saúde, e parte da tendência de longo prazo reflete melhora histórica na captação de óbitos pelo SIM.",
        ],
      },
      {
        titulo: "Por que isso importa",
        paragrafos: [
          "O excesso de mortalidade é um indicador-síntese de resiliência do sistema de saúde. Mantê-lo monitorado, com séries longas e abertas, permite avaliar não só pandemias, mas ondas de calor, colapsos assistenciais e o efeito de políticas públicas. A reprodutibilidade — qualquer pessoa pode recalcular a partir dos microdados oficiais — é o que separa vigilância de opinião.",
        ],
      },
    ],
    referencias: [
      "BRASIL. Ministério da Saúde. SIM — Sistema de Informações sobre Mortalidade. Microdados 2015–2024.",
      "Saúde em Dado. mart_excesso_uf_mes (baseline 2015–2019). saudeemdado.com/tendencias.",
      "Karlinsky A., Kobak D. Excess mortality during the COVID-19 pandemic: World Mortality Dataset. eLife, 2021.",
    ],
  },
  {
    slug: "taxa-bruta-vs-padronizada-rankings-municipais",
    titulo: "Taxa bruta versus padronizada: por que rankings municipais enganam",
    dek: "Comparar municípios pela taxa bruta de mortalidade premia cidades jovens e pune as envelhecidas. A padronização por idade — e o intervalo de confiança — corrigem o engano.",
    data: "2026-01-22",
    leituraMin: 6,
    tags: ["metodologia", "padronização etária", "estatística", "mortalidade"],
    resumo:
      "Demonstramos, com os dados municipais de 2023, como a estrutura etária distorce comparações de mortalidade e por que a taxa padronizada pelo método direto e o intervalo de confiança de 95% são indispensáveis para rankings responsáveis.",
    secoes: [
      {
        paragrafos: [
          "A taxa bruta de mortalidade — óbitos divididos pela população — é intuitiva e profundamente enganosa quando usada para comparar lugares. A mortalidade cresce exponencialmente com a idade; portanto, um município com população mais velha terá taxa bruta maior mesmo que sua saúde, idade a idade, seja idêntica ou melhor que a de um município jovem.",
          "Cidades litorâneas e do interior com forte migração de aposentados, por exemplo, exibem taxas brutas elevadas que nada dizem sobre a qualidade da atenção à saúde — dizem apenas que ali vivem mais idosos.",
        ],
      },
      {
        titulo: "A correção: padronização direta",
        paragrafos: [
          "A padronização por idade resolve o problema aplicando as taxas específicas por faixa etária de cada município a uma população-padrão comum — neste projeto, a do Brasil no Censo 2022. O resultado é a taxa que o município teria se sua composição etária fosse a do país. Só então a comparação é legítima.",
          "Tratamos ainda a idade ignorada (registros sem idade) redistribuindo-a proporcionalmente entre as faixas conhecidas, evitando subestimação. A plataforma expõe lado a lado a taxa bruta e a padronizada — e a diferença entre elas é, muitas vezes, a diferença entre uma conclusão correta e uma equivocada.",
        ],
      },
      {
        titulo: "Incerteza: o intervalo de confiança",
        paragrafos: [
          "Em municípios pequenos, poucos óbitos a mais ou a menos alteram drasticamente a taxa. Por isso, toda taxa bruta é acompanhada de um intervalo de confiança de 95% calculado pelo método gama (Poisson exato), e a interface sinaliza municípios com menos de 10 mil habitantes, onde as taxas são instáveis.",
          "A regra prática: nunca leia uma taxa municipal sem olhar seu intervalo. Uma taxa 'alta' com intervalo amplo pode ser indistinguível da média — é ruído, não sinal.",
        ],
      },
    ],
    referencias: [
      "Ahmad O.B. et al. Age standardization of rates: a new WHO standard. GPE Discussion Paper, WHO, 2001.",
      "Saúde em Dado. mart_mortalidade_municipio (taxa_padronizada_100k, ic95). saudeemdado.com/metodologia.",
      "IBGE. Censo Demográfico 2022 — população por idade (população-padrão).",
    ],
  },
  {
    slug: "mortalidade-infantil-gradiente-regional",
    titulo: "Mortalidade infantil no Brasil: um gradiente que persiste",
    dek: "A taxa nacional ronda 12,6 por mil nascidos vivos — mas esconde uma distância de duas vezes entre o Sul e o Norte/Nordeste. Cruzando SINASC e SIM.",
    data: "2026-04-08",
    leituraMin: 7,
    tags: ["mortalidade infantil", "SINASC", "SIM", "desigualdade"],
    resumo:
      "Combinando nascidos vivos do SINASC com óbitos de menores de 1 ano do SIM, estimamos a Taxa de Mortalidade Infantil (TMI) por UF. A média nacional de ~12,6‰ convive com extremos que vão de ~9‰ a ~20‰, expondo um gradiente socioespacial persistente.",
    secoes: [
      {
        paragrafos: [
          "A Taxa de Mortalidade Infantil — óbitos de menores de 1 ano por mil nascidos vivos — é um dos indicadores mais sensíveis de desenvolvimento e qualidade da atenção materno-infantil. Calculá-la corretamente exige duas fontes: o numerador (óbitos infantis) vem do SIM; o denominador (nascidos vivos), do SINASC.",
          "Para os anos com ambas as bases consolidadas, a TMI nacional situou-se em torno de 12,6 por mil — patamar que coloca o Brasil em posição intermediária no contexto latino-americano e ainda distante das menores taxas mundiais (abaixo de 3‰).",
        ],
      },
      {
        titulo: "O gradiente Norte–Sul",
        paragrafos: [
          "A média nacional, porém, é uma abstração. A desagregação por UF revela amplitude de cerca de duas vezes: estados do Sul e Sudeste aproximam-se de 9–10‰, enquanto unidades do Norte e Nordeste alcançam 18–20‰. Esse gradiente acompanha, de perto, indicadores de renda, saneamento e cobertura de pré-natal.",
          "Parte da mortalidade infantil é evitável por intervenções conhecidas e de baixo custo: pré-natal adequado, atenção ao parto e vacinação. O componente neonatal (primeiros 28 dias), hoje majoritário, depende sobretudo da qualidade assistencial no parto e nas primeiras horas de vida.",
        ],
      },
      {
        titulo: "Sinais na porta de entrada",
        paragrafos: [
          "Os próprios dados do SINAStratuC antecipam risco: proporção de baixo peso ao nascer (<2.500 g), prematuridade (<37 semanas) e cobertura de sete ou mais consultas de pré-natal variam fortemente entre municípios e ajudam a explicar diferenças na TMI. A plataforma disponibiliza esses indicadores por município, permitindo focalizar a ação.",
        ],
      },
      {
        titulo: "Ressalvas",
        paragrafos: [
          "A TMI municipal é instável em localidades com poucos nascimentos; por isso a apresentamos preferencialmente por UF. Além disso, o SINASC tem defasagem de consolidação maior que o SIM, o que limita o ano mais recente disponível para o cálculo.",
        ],
      },
    ],
    referencias: [
      "BRASIL. Ministério da Saúde. SINASC e SIM — microdados.",
      "Saúde em Dado. mart_mortalidade_infantil_uf e mart_natalidade_municipio. saudeemdado.com/nascimentos.",
      "RIPSA. Indicadores básicos para a saúde no Brasil: conceitos e aplicações.",
    ],
  },
  {
    slug: "internacoes-sus-para-onde-vao-63-bilhoes",
    titulo: "Internações pelo SUS: para onde vão R$ 63 bilhões",
    dek: "Quase 40 milhões de internações em três anos. Uma leitura do volume, da permanência, da mortalidade hospitalar e do custo por capítulo da CID-10.",
    data: "2026-03-25",
    leituraMin: 8,
    tags: ["SIH", "internações", "gestão", "custos"],
    resumo:
      "A partir das Autorizações de Internação Hospitalar (SIH/AIH) de 2022 a 2024 — 39,9 milhões de internações e R$ 63,2 bilhões aprovados —, analisamos permanência média (~5 dias), mortalidade intra-hospitalar (~4,4%) e a composição do gasto por grupo de causas.",
    secoes: [
      {
        paragrafos: [
          "O Sistema de Informações Hospitalares (SIH) registra cada internação paga pelo SUS por meio da Autorização de Internação Hospitalar (AIH). É a principal janela para entender a produção e o custo da assistência hospitalar pública — que cobre a maioria dos brasileiros, embora não a rede privada/suplementar.",
          "No triênio 2022–2024, contabilizamos 39.883.796 internações por residência do paciente, com valor total aprovado de R$ 63,2 bilhões. Só em 2024 foram 14,2 milhões de internações.",
        ],
      },
      {
        titulo: "Três indicadores de eficiência e desfecho",
        paragrafos: [
          "A permanência média situou-se em torno de 5,0 dias — número que sintetiza perfil de casos e eficiência de fluxo. A mortalidade intra-hospitalar ficou em cerca de 4,4%, variando enormemente por causa: internações por causas externas e por doenças circulatórias têm desfechos muito distintos de partos ou procedimentos eletivos.",
          "O custo médio por internação, derivável do valor aprovado, é um insumo direto para planejamento. Mas atenção: o valor da AIH reflete a tabela SUS, não o custo real do procedimento — uma limitação importante para análises econômicas.",
        ],
      },
      {
        titulo: "A composição por capítulo da CID-10",
        paragrafos: [
          "Agrupando o diagnóstico principal pelos capítulos da CID-10, emergem os grandes blocos: gravidez/parto e puerpério (alto volume, baixa mortalidade), doenças do aparelho circulatório e respiratório (alta mortalidade), lesões e causas externas, e neoplasias. Cada bloco demanda respostas de rede distintas — da obstetrícia à oncologia.",
          "A plataforma permite ordenar municípios por volume, permanência, mortalidade ou custo, e filtrar por capítulo — útil para gestores compararem seu município com pares e identificarem desvios.",
        ],
      },
      {
        titulo: "Limites",
        paragrafos: [
          "O SIH cobre apenas a rede SUS; serviços exclusivamente privados não aparecem. Além disso, a AIH é unidade administrativa, não paciente: reinternações contam múltiplas vezes. Lemos volume de internações, não de pessoas internadas.",
        ],
      },
    ],
    referencias: [
      "BRASIL. Ministério da Saúde. SIH/SUS — AIH. Microdados 2022–2024.",
      "Saúde em Dado. mart_internacoes_municipio. saudeemdado.com/internacoes.",
      "Ministério da Saúde. Manual técnico do SIH e tabela de procedimentos SUS.",
    ],
  },
  {
    slug: "vulnerabilidade-mortalidade-paradoxo-subregistro",
    titulo: "Vulnerabilidade e mortalidade: o paradoxo do sub-registro",
    dek: "Seria de esperar que municípios mais vulneráveis tivessem maior mortalidade. O dado mostra correlação fraca e até negativa — e a explicação é metodológica.",
    data: "2026-05-06",
    leituraMin: 7,
    tags: ["desigualdade", "determinantes sociais", "qualidade do dado", "metodologia"],
    resumo:
      "Cruzando um índice-proxy de vulnerabilidade social (Censo 2022) com a taxa de mortalidade padronizada em 3.089 municípios, encontramos correlação de Pearson de aproximadamente −0,18. Argumentamos que o resultado revela menos sobre saúde e mais sobre a qualidade do registro de óbitos.",
    secoes: [
      {
        paragrafos: [
          "Os determinantes sociais da saúde preveem que pobreza, baixa escolaridade e falta de saneamento se traduzam em pior saúde — e, portanto, maior mortalidade. Ao cruzar nosso índice-proxy de vulnerabilidade social (composto por analfabetismo e ausência de água encanada no Censo 2022, via z-score) com a mortalidade padronizada de 2023, esperávamos correlação positiva.",
          "O que encontramos foi uma correlação de Pearson de cerca de −0,18: fraca e na direção oposta. Em vez de descartar o achado, ele merece ser explicado — e é aqui que a análise se torna interessante.",
        ],
      },
      {
        titulo: "Três explicações plausíveis",
        paragrafos: [
          "Primeiro, sub-registro de óbitos. Municípios mais vulneráveis, sobretudo no Norte e Nordeste, historicamente captam menos óbitos no SIM. Menos óbitos registrados produzem taxa mensurada artificialmente baixa — um viés que pode inverter a relação verdadeira.",
          "Segundo, a padronização por idade. Áreas vulneráveis tendem a ser demograficamente mais jovens; ao padronizar, removemos o efeito idade, mas não corrigimos a subnotificação. Terceiro, garbage codes: causas mal definidas (capítulo R da CID-10) são mais frequentes onde a infraestrutura de informação é precária.",
        ],
      },
      {
        titulo: "A lição",
        paragrafos: [
          "Este é um exemplo didático de que correlação não é causalidade — e de que um dado 'limpo' pode esconder um viés sistemático. A leitura honesta não é 'vulnerabilidade protege'; é 'a mortalidade medida é menos confiável justamente onde a vulnerabilidade é maior'. O sinal a investigar é a qualidade do registro, não um efeito protetor inexistente.",
          "Reconhecer o limite do índice também é parte do rigor: trata-se de um proxy de duas dimensões do Censo 2022, não do IVS oficial do IPEA. A incorporação do índice oficial está no roadmap e tende a refinar — não a anular — esta discussão.",
        ],
      },
    ],
    referencias: [
      "Saúde em Dado. Cruzamento vulnerabilidade × mortalidade. saudeemdado.com/tendencias.",
      "IBGE. Censo Demográfico 2022 (alfabetização e abastecimento de água).",
      "Szwarcwald C.L. et al. Busca ativa de óbitos e nascimentos no Nordeste e na Amazônia Legal. Ministério da Saúde.",
    ],
  },
  {
    slug: "principais-causas-de-morte-brasil-cid10",
    titulo: "As principais causas de morte no Brasil pela CID-10",
    dek: "Doenças do coração lideram, seguidas por neoplasias e causas respiratórias. Uma leitura das categorias que mais matam e do que elas revelam sobre transição epidemiológica.",
    data: "2026-02-26",
    leituraMin: 6,
    tags: ["mortalidade", "CID-10", "transição epidemiológica"],
    resumo:
      "Classificando 14,4 milhões de óbitos (2015–2024) pelos capítulos e categorias da CID-10, descrevemos o perfil de causas do Brasil contemporâneo: predomínio de doenças crônicas não transmissíveis, com infarto (I21) e pneumonia (J18) entre as categorias mais frequentes.",
    secoes: [
      {
        paragrafos: [
          "A Classificação Internacional de Doenças (CID-10) organiza a causa básica de cada óbito em 22 capítulos e milhares de categorias. Processar a causa básica de 14,4 milhões de óbitos entre 2015 e 2024 permite desenhar o mapa do que mata no Brasil — e como isso muda.",
          "No agregado, o capítulo IX (doenças do aparelho circulatório) lidera, seguido pelo capítulo II (neoplasias) e pelo capítulo X (doenças do aparelho respiratório). É a assinatura de um país que completou, em grande medida, a transição epidemiológica: as crônicas não transmissíveis suplantaram as infecciosas como principal causa de morte.",
        ],
      },
      {
        titulo: "Do capítulo à categoria",
        paragrafos: [
          "Descer ao nível da categoria de três caracteres é revelador. O infarto agudo do miocárdio (I21) figura sistematicamente no topo das causas específicas; a pneumonia (J18) e a doença pulmonar obstrutiva crônica (J44) aparecem com força, assim como o diabetes (E14) e causas do aparelho geniturinário (N39). Em São Paulo, em 2024, essa ordem se confirma nos dados da plataforma.",
          "O capítulo XVIII (sintomas e achados mal definidos, com destaque para R99) merece vigilância: sua participação é um marcador inverso da qualidade da informação — quanto mais óbitos 'mal definidos', menos confiável o perfil de causas daquela localidade.",
        ],
      },
      {
        titulo: "Por que mapear causas importa",
        paragrafos: [
          "O perfil de causas orienta prioridades: prevenção cardiovascular, rastreamento de câncer, manejo de doenças respiratórias crônicas. Disponibilizar essa distribuição por município, ano e sexo — de forma aberta — aproxima o planejamento da realidade local, em vez de aplicar médias nacionais a contextos heterogêneos.",
        ],
      },
    ],
    referencias: [
      "OMS. Classificação Estatística Internacional de Doenças e Problemas Relacionados à Saúde (CID-10).",
      "Saúde em Dado. mart_mortalidade_causa e mart_mortalidade_municipio. saudeemdado.com.",
      "Schramm J.M.A. et al. Transição epidemiológica e o estudo de carga de doença no Brasil. Ciência & Saúde Coletiva.",
    ],
  },
  {
    slug: "arquitetura-dados-abertos-custo-zero",
    titulo: "Inteligência epidemiológica a custo zero: a arquitetura por trás da plataforma",
    dek: "Como transformar gigabytes de microdados do DataSUS em uma API pública, reproduzível e gratuita — uma nota técnica na fronteira entre saúde coletiva e engenharia de dados.",
    data: "2026-05-20",
    leituraMin: 9,
    tags: ["ciência de dados", "engenharia de dados", "dados abertos", "reprodutibilidade"],
    resumo:
      "Descrevemos as decisões de arquitetura que permitem servir indicadores de cinco sistemas do DataSUS sem custo de manutenção: agregação local em DuckDB, publicação apenas de marts agregados, API automática via PostgREST e front-end estático. Uma discussão metodológica sobre como infraestrutura define o que é possível em pesquisa.",
    secoes: [
      {
        paragrafos: [
          "Os dados do SUS são públicos, mas a barreira de acesso é técnica: microdados em formato DBC proprietário, fragmentados por unidade federativa e competência, somando dezenas de gigabytes. A maior parte do esforço de qualquer estudo epidemiológico no Brasil é gasta antes da análise — em obtenção e limpeza.",
          "A tese desta plataforma é que a infraestrutura determina a pesquisa possível. Reduzir a barreira de acesso a zero — uma consulta de API em vez de semanas de engenharia — muda o que pesquisadores, jornalistas e gestores conseguem perguntar.",
        ],
      },
      {
        titulo: "Princípio 1: agregar localmente, publicar o essencial",
        paragrafos: [
          "Os microdados (mais de 1,5 GB só para um ano de óbitos) são processados localmente com DuckDB, um motor analítico em processo que executa agregações sobre arquivos colunares em segundos. Para o banco em nuvem sobem apenas os marts agregados — município × período × categoria — com algumas centenas de milhares de linhas.",
          "Essa escolha tem duplo benefício: cabe no nível gratuito de um Postgres gerenciado e, por publicar somente agregados, elimina qualquer risco de reidentificação. Privacidade por desenho, não por promessa.",
        ],
      },
      {
        titulo: "Princípio 2: sem servidores para manter",
        paragrafos: [
          "A API REST é gerada automaticamente pelo PostgREST sobre o Postgres; o site é estático, servido por CDN; os dados de navegação comum são congelados em JSON no momento do build, levando o tráfego ao banco praticamente a zero. Não há servidor de aplicação para cair, atualizar ou pagar.",
          "A consequência é estratégica: projetos acadêmicos costumam morrer quando acaba a verba ou o tempo do mantenedor. Uma arquitetura de custo marginal nulo foi desenhada para sobreviver ao abandono — uma forma de sustentabilidade que raramente é discutida em metodologia.",
        ],
      },
      {
        titulo: "Princípio 3: reprodutibilidade radical",
        paragrafos: [
          "Cada número publicado pode ser regenerado a partir das fontes oficiais por um único script aberto, e uma rotina de validação confere âncoras conhecidas (totais anuais oficiais, conciliação entre marts) a cada atualização. A ferramenta é, ela própria, auditável — condição para que seus resultados sejam citáveis.",
          "Na confluência entre saúde coletiva e ciência de dados, a lição é que o método não termina no modelo estatístico: começa na engenharia que torna o dado acessível, íntegro e verificável. É esse alicerce que sustenta todas as análises desta seção.",
        ],
      },
    ],
    referencias: [
      "Raasveldt M., Mühleisen H. DuckDB: an embeddable analytical database. SIGMOD, 2019.",
      "PostgREST. REST API automática sobre PostgreSQL. postgrest.org.",
      "Saúde em Dado. Pipelines e validação (código aberto). github.com/pedropaulofernandes88-stack/saude-publica-br.",
    ],
  },
];

export function getArtigo(slug: string): Artigo | undefined {
  return ARTIGOS.find((a) => a.slug === slug);
}
