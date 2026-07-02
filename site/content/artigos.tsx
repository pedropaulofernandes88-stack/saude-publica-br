/**
 * artigos.tsx — conteúdo da seção de Análises (artigos assinados).
 *
 * Cada artigo é dado estruturado (resumo, seções, referências) renderizado por
 * um template consistente. Números citados vêm dos marts do próprio projeto
 * (SIM, SINAN, SIH, SINASC, IVS-proxy), validados contra fontes oficiais.
 */

export const AUTHOR = {
  nome: "Pedro Fernandes",
  orcid: "https://orcid.org/0009-0008-6248-2486",
  lattes: "http://lattes.cnpq.br/6641343625206093",
  linkedin: "https://www.linkedin.com/in/pedro-f-540154408/",
  credenciais: [
    "Mestrando em Saúde Coletiva (IAMSPE)",
    "Pós-graduando em Inteligência Artificial e Ciência de Dados em Saúde (Hospital Sírio-Libanês)",
    "Diretor de Tecnologia da Informação — Prefeitura Municipal de Penápolis (SP)",
  ],
  resumoBio:
    "Pesquisador na interseção entre saúde coletiva, ciência de dados e gestão pública. Concebeu e mantém a plataforma Saúde em Dado.",
};

export interface TabelaArtigo {
  titulo?: string;
  colunas: string[];
  linhas: (string | number)[][];
  nota?: string;
}

export interface Secao {
  titulo?: string;
  paragrafos: string[];
  lista?: string[];
  tabela?: TabelaArtigo;
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
    slug: "643-mil-nao-702-mil-baseline-excesso-mortalidade",
    titulo: "643 mil, não 702 mil: como a escolha do baseline muda a história da pandemia",
    dek: "Corrigir o esperado pelo envelhecimento reduz o excesso pandêmico e quase zera o 'excesso persistente' de 2022–2024. Mas testar a alternativa mais sofisticada revelou por que ela falha no Brasil — e por que o método mais simples é o mais robusto.",
    data: "2026-06-29",
    leituraMin: 9,
    tags: ["excesso de mortalidade", "SIM", "COVID-19", "métodos", "análise de sensibilidade"],
    resumo:
      "O excesso de mortalidade é a métrica-síntese do impacto de uma crise, mas depende inteiramente do 'esperado'. Mostramos como trocar um baseline de média por um de tendência corrige um viés de envelhecimento (excesso 2020–2021: 702.871 → 643.482) e faz o 'excesso persistente' pós-pandemia encolher. E documentamos uma análise de sensibilidade: a variante padronizada por idade subestima o excesso (~505 mil) porque o denominador populacional anual do Brasil é problemático — expondo por que o método que não usa população é o mais confiável.",
    secoes: [
      {
        paragrafos: [
          "Quantos brasileiros morreram a mais por causa da pandemia? A resposta parece uma questão de contar mortes, mas na verdade depende de uma escolha metodológica raramente examinada: o que teria sido o 'normal'. Excesso de mortalidade é a diferença entre os óbitos observados e os esperados na ausência da crise — e todo o peso recai sobre esse 'esperado'.",
          "Nossa estimativa inicial usava um baseline simples: a média de óbitos de cada mês em 2015–2019, ajustada pelo crescimento da população. É transparente, mas tem um defeito: ignora que a população brasileira envelhece. Mais idosos significam mais óbitos esperados a cada ano — e um baseline que não capta isso subestima o esperado nos anos recentes, superestimando o excesso.",
        ],
      },
      {
        titulo: "A correção: de média para tendência",
        paragrafos: [
          "Substituímos a média por uma tendência linear ajustada a cada mês civil de 2015–2019 e projetada adiante. Essa tendência embute empiricamente tudo o que crescia na mortalidade de base — inclusive o envelhecimento — sem precisar modelá-lo explicitamente.",
          "O efeito é revelador. O pico pandêmico permanece robusto: o excesso de 2020–2021 passa de 702.871 para 643.482 óbitos — uma redução de cerca de 8%, ainda plenamente compatível com as estimativas internacionais independentes (~660–680 mil). A história da pandemia não muda.",
          "O que muda é o depois. Pelo método antigo, o Brasil parecia carregar um 'excesso persistente' em 2022 e 2023. Pela tendência, esse excedente encolhe drasticamente — de 260 mil para 145 mil em 2022, de 152 mil para 48 mil em 2023 — e 2024 fica essencialmente em zero. Em outras palavras: boa parte do 'excesso persistente' era um artefato de não descontar o envelhecimento, não um efeito real da pandemia.",
        ],
      },
      {
        titulo: "O teste que quase inverteu tudo — e por que não inverteu",
        paragrafos: [
          "A epidemiologia clássica recomendaria ir além: padronizar por idade, aplicando taxas de mortalidade por faixa etária à estrutura populacional de cada ano. Testamos essa variante usando a população por idade da projeção do IBGE de 2018. Ela deveria ser superior — e produziu números drasticamente menores: excesso pandêmico de apenas ~505 mil, e excesso fortemente negativo a partir de 2023.",
          "Antes de adotar o resultado 'mais sofisticado', investigamos a discrepância. E o problema não era o método, era o denominador. A projeção de 2018 superestima a população brasileira — o Censo 2022 revisou o total para baixo em cerca de 8 a 11 milhões de pessoas. Uma população idosa inflada infla o número esperado de óbitos e, portanto, esconde o excesso. Reescalar para o total pós-Censo não resolve: a série do Censo introduz uma descontinuidade em 2022 que distorce os anos ao redor.",
          "A conclusão é contraintuitiva e importante: no Brasil de 2015–2024, o dado populacional anual por idade é frágil demais para sustentar um excesso padronizado confiável. O método de tendência, justamente por se apoiar apenas nos óbitos observados e nunca tocar a população, é imune a esse problema — e é o que concorda com as estimativas independentes. O 'mais simples' venceu por ser o mais robusto.",
        ],
        tabela: {
          titulo: "Excesso de mortalidade no Brasil por método (óbitos)",
          colunas: ["Período", "Tendência (publicado)", "Padronizado (projeção)", "Padronizado (reescalado)"],
          linhas: [
            ["2020–2021", "643.482", "503.913", "510.243"],
            ["2022", "144.541", "36.182", "121.406"],
            ["2023", "48.065", "−88.267", "−24.681"],
            ["2024", "−9.018", "−174.699", "−134.195"],
            ["2020–2024", "827.070", "277.129", "472.774"],
          ],
          nota: "As duas variantes padronizadas por idade usam a projeção IBGE 2018 (cru e reescalado ao total pós-Censo). Reprodutível em scripts/sensibilidade_excesso_idade.py. Elaboração: Saúde em Dado.",
        },
      },
      {
        titulo: "Por que isso importa além do número",
        paragrafos: [
          "Este episódio é um argumento a favor da transparência metodológica como método. Não escolhemos o baseline que dava o número mais impressionante nem o mais sofisticado; escolhemos o que sobrevive ao escrutínio, e publicamos a comparação inteira — inclusive o script que qualquer pessoa pode rodar para reproduzir a tabela.",
          "Para quem lê indicadores de saúde, a lição é prática: desconfie de 'excesso persistente' e de qualquer número de excesso sem saber como o esperado foi construído. A escolha do baseline pode mudar a conclusão em centenas de milhares de vidas — e, no limite, inverter o sinal.",
        ],
      },
    ],
    referencias: [
      "Saúde em Dado. mart_excesso_uf_mes (baseline por tendência 2015–2019) e scripts/sensibilidade_excesso_idade.py. saudeemdado.com/metodologia.",
      "Karlinsky A., Kobak D. Excess mortality during the COVID-19 pandemic: World Mortality Dataset. eLife, 2021.",
      "IBGE. Censo Demográfico 2022; Projeções da População (revisão 2018). SIDRA.",
      "Organização Mundial da Saúde. Global excess deaths associated with COVID-19, 2020–2021.",
    ],
  },
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
        titulo: "Dados e métodos",
        paragrafos: [
          "Fonte: SINAN — arquivos nacionais DENGBR (bases FINAIS e PRELIM), 2015–2024, por município de residência (ID_MN_RESI) e semana epidemiológica dos primeiros sintomas (SEM_PRI). Caso provável = notificação não descartada após investigação (CLASSI_FIN ≠ 5), convenção da vigilância; óbito por dengue = EVOLUCAO = 2; letalidade = óbitos ÷ casos prováveis.",
          "A dengue é de notificação compulsória desde os anos 1990, e o SINAN é sua principal fonte de vigilância. Em 2024, os microdados nacionais registraram 6.564.924 casos prováveis e 6.337 óbitos — valores sem precedentes na série.",
        ],
      },
      {
        titulo: "A série 2015–2024",
        paragrafos: [
          "A tabela mostra a magnitude do rompimento de patamar: 2024 multiplica por ~4 o pior ano prévio (2023) e concentra mais óbitos do que os cinco anos anteriores somados. A letalidade sobe para 0,097% — a maior da série —, mas permanece baixa em termos absolutos: o recorde de óbitos é efeito do denominador explosivo, não de piora clínica.",
        ],
        tabela: {
          titulo: "Dengue no Brasil por ano epidemiológico (SINAN)",
          colunas: ["Ano", "Casos prováveis", "Óbitos", "Letalidade (%)"],
          linhas: [
            ["2015", "1.623.172", "972", "0,060"],
            ["2016", "1.450.074", "704", "0,049"],
            ["2017", "239.395", "188", "0,079"],
            ["2018", "262.611", "203", "0,077"],
            ["2019", "1.546.252", "843", "0,055"],
            ["2020", "975.842", "587", "0,060"],
            ["2021", "540.049", "279", "0,052"],
            ["2022", "1.405.095", "1.056", "0,075"],
            ["2023", "1.645.956", "1.192", "0,072"],
            ["2024", "6.564.924", "6.337", "0,097"],
          ],
          nota: "Fonte: SINAN/DataSUS (DENGBR). Casos prováveis = CLASSI_FIN ≠ 5. Elaboração: Saúde em Dado.",
        },
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
    dek: "Comparando o observado ao esperado por uma tendência 2015–2019, estimamos cerca de 643 mil óbitos em excesso no biênio pandêmico — e analisamos o retorno ao patamar histórico.",
    data: "2026-02-10",
    leituraMin: 8,
    tags: ["mortalidade", "SIM", "excesso de mortalidade", "COVID-19"],
    resumo:
      "O excesso de mortalidade é a métrica mais robusta para medir o impacto total de uma crise sanitária, pois independe da causa declarada. Construímos um baseline de tendência 2015–2019 — que capta crescimento e envelhecimento da população — e quantificamos o excesso mensal por UF e Brasil de 2020 a 2024.",
    secoes: [
      {
        paragrafos: [
          "Durante emergências sanitárias, a contagem direta de mortes por uma causa específica subestima o impacto real: há subdiagnóstico, sobrecarga dos serviços e mortes indiretas. O excesso de mortalidade — diferença entre os óbitos observados e os esperados na ausência da crise — contorna esses vieses e é hoje o padrão internacional de avaliação.",
          "Nossa estimativa do esperado vem de uma tendência linear ajustada a cada mês civil no período 2015–2019, projetada para o ano-alvo. Diferente de uma simples média do baseline, ela capta o crescimento e o envelhecimento da população — que elevam o número esperado de óbitos ano a ano —, evitando superestimar o excesso nos anos recentes. É um método transparente e replicável; sua principal limitação é assumir que a tendência pré-pandemia teria continuado (não modela harvesting nem mudanças bruscas de estrutura etária).",
        ],
      },
      {
        titulo: "Resultados: excesso por ano",
        paragrafos: [
          "O excesso concentrou-se em 2020 e 2021, somando 643.482 óbitos acima do esperado no agregado nacional — magnitude compatível com as estimativas independentes para o período (~660–680 mil; World Mortality Dataset, OMS). O pico foi o primeiro semestre de 2021, o mais letal da série.",
          "A partir de 2022 o excesso recua de forma consistente e 2024 fica essencialmente em zero, indicando retorno ao regime pré-pandêmico. A desagregação por UF, na plataforma, revela forte heterogeneidade regional — reflexo de estrutura etária, acesso a leitos, momento de circulação viral e cobertura vacinal.",
        ],
        tabela: {
          titulo: "Excesso de mortalidade no Brasil por ano (baseline por tendência 2015–2019)",
          colunas: ["Ano", "Excesso (óbitos)", "% sobre o esperado"],
          linhas: [
            ["2020", "192.739", "+14,1"],
            ["2021", "450.744", "+32,6"],
            ["2022", "144.541", "+10,3"],
            ["2023", "48.065", "+3,4"],
            ["2024 (prelim.)", "−9.018", "−0,6"],
            ["2020–2021", "643.482", "—"],
          ],
          nota: "Fonte: SIM/DataSUS; esperado por regressão linear 2015–2019 por mês civil. 2024 preliminar e sujeito à extrapolação; ver análise de sensibilidade. Elaboração: Saúde em Dado.",
        },
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
      "Demonstramos, com quatro municípios grandes em 2023, como a estrutura etária inverte rankings de mortalidade: cidades envelhecidas parecem 'piores' pela taxa bruta e cidades jovens parecem 'melhores', quando a taxa padronizada revela o oposto. Explicamos a padronização direta e o intervalo de confiança gama.",
    secoes: [
      {
        titulo: "Dados e métodos",
        paragrafos: [
          "A taxa bruta de mortalidade — óbitos divididos pela população — é intuitiva e profundamente enganosa para comparar lugares. A mortalidade cresce exponencialmente com a idade; um município mais velho terá taxa bruta maior mesmo que sua saúde, idade a idade, seja igual ou melhor que a de um município jovem.",
          "A padronização direta corrige isso aplicando as taxas específicas por faixa etária de cada município a uma população-padrão comum (aqui, o Brasil no Censo 2022): é a taxa que o município teria se sua composição etária fosse a do país. Idade ignorada é redistribuída pro rata. Toda taxa bruta acompanha IC95% pelo método gama (Poisson exato). Fonte: mart_mortalidade_municipio, 2023, capítulo TOTAL.",
        ],
      },
      {
        titulo: "O efeito em números: a inversão do ranking",
        paragrafos: [
          "A tabela mostra dois municípios envelhecidos (Santos, Niterói) e dois jovens (Parauapebas, Boa Vista), todos com mais de 280 mil habitantes. Pela taxa bruta, Santos (1.012/100 mil) parece quase três vezes 'pior' que Parauapebas (359/100 mil). Padronizada por idade, a relação se inverte: Parauapebas (770) tem mortalidade maior que Santos (638). O ranking bruto não estava só impreciso — estava de cabeça para baixo.",
        ],
        tabela: {
          titulo: "Taxa bruta × padronizada por idade — municípios selecionados, 2023 (por 100 mil hab.)",
          colunas: ["Município", "População", "Taxa bruta", "Taxa padronizada"],
          linhas: [
            ["Santos (SP) — envelhecido", "424.088", "1.012", "638"],
            ["Niterói (RJ) — envelhecido", "499.234", "943", "657"],
            ["Parauapebas (PA) — jovem", "283.345", "359", "770"],
            ["Boa Vista (RR) — jovem", "441.828", "486", "811"],
          ],
          nota: "Fonte: SIM/DataSUS e IBGE, 2023. Padrão: Brasil, Censo 2022. Elaboração: Saúde em Dado.",
        },
      },
      {
        titulo: "Incerteza: o intervalo de confiança",
        paragrafos: [
          "Em municípios pequenos, poucos óbitos a mais ou a menos alteram drasticamente a taxa. Por isso cada taxa bruta acompanha um IC95% (método gama), e a interface sinaliza municípios com menos de 10 mil habitantes, onde as taxas são instáveis.",
          "A regra prática: nunca leia uma taxa municipal sem olhar seu intervalo. Uma taxa 'alta' com intervalo amplo pode ser indistinguível da média — é ruído, não sinal.",
        ],
      },
      {
        titulo: "Limitações",
        paragrafos: [
          "A padronização remove o efeito da idade, mas não corrige sub-registro de óbitos nem causas mal definidas — vieses que afetam sobretudo municípios com infraestrutura de informação mais frágil. Padronizar torna as comparações legítimas quanto à idade, não quanto à qualidade do dado.",
        ],
      },
    ],
    referencias: [
      "Ahmad OB, Boschi-Pinto C, Lopez AD, et al. Age standardization of rates: a new WHO standard. GPE Discussion Paper No. 31. WHO, 2001.",
      "Saúde em Dado. mart_mortalidade_municipio (taxa_padronizada_100k, ic95_inf/sup) (v3.1.0). saudeemdado.com/metodologia.",
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
        titulo: "Dados e métodos",
        paragrafos: [
          "A Taxa de Mortalidade Infantil (TMI) — óbitos de menores de 1 ano por mil nascidos vivos — é um dos indicadores mais sensíveis de desenvolvimento e de qualidade da atenção materno-infantil. Seu cálculo combina duas fontes: o numerador (óbitos de menores de 1 ano) do SIM e o denominador (nascidos vivos) do SINASC, ambos por município/UF de residência da mãe.",
          "Apresentamos a TMI por UF para o ano mais recente com ambas as bases consolidadas (2022). A TMI nacional situou-se em 12,6 por mil — posição intermediária no contexto latino-americano e ainda distante das menores taxas mundiais (abaixo de 3‰).",
        ],
      },
      {
        titulo: "O gradiente Norte–Sul",
        paragrafos: [
          "A média nacional é uma abstração. A desagregação por UF revela amplitude de ~1,9 vez entre os extremos — de 9,8‰ (Santa Catarina) a 18,8‰ (Roraima). O gradiente acompanha de perto renda, saneamento e cobertura de pré-natal, e separa nitidamente Sul/Sudeste do Norte/Nordeste.",
        ],
        tabela: {
          titulo: "TMI por UF — extremos e nacional, 2022 (óbitos <1 ano por mil nascidos vivos)",
          colunas: ["UF", "TMI (‰)"],
          linhas: [
            ["Roraima (RR)", "18,8"],
            ["Amapá (AP)", "18,1"],
            ["Sergipe (SE)", "17,6"],
            ["Acre (AC)", "17,2"],
            ["Piauí (PI)", "15,8"],
            ["— Brasil —", "12,6"],
            ["Espírito Santo (ES)", "10,8"],
            ["Rio Grande do Sul (RS)", "10,5"],
            ["Paraná (PR)", "10,3"],
            ["Distrito Federal (DF)", "10,1"],
            ["Santa Catarina (SC)", "9,8"],
          ],
          nota: "Fonte: SIM (óbitos <1 ano) e SINASC (nascidos vivos), 2022. Cinco maiores e cinco menores UFs. Elaboração: Saúde em Dado.",
        },
      },
      {
        titulo: "Evitabilidade e sinais na porta de entrada",
        paragrafos: [
          "Parte da mortalidade infantil é evitável por intervenções conhecidas e de baixo custo: pré-natal adequado, atenção qualificada ao parto e vacinação. O componente neonatal (primeiros 28 dias), hoje majoritário, depende sobretudo da assistência ao parto e às primeiras horas de vida.",
          "Os próprios dados do SINASC antecipam risco: baixo peso ao nascer (<2.500 g), prematuridade (<37 semanas) e cobertura de sete ou mais consultas de pré-natal variam fortemente entre municípios e ajudam a explicar diferenças na TMI. A plataforma disponibiliza esses indicadores por município, permitindo focalizar a ação.",
        ],
      },
      {
        titulo: "Limitações",
        paragrafos: [
          "A TMI municipal é instável em localidades com poucos nascimentos; por isso a apresentamos por UF. O SINASC tem defasagem de consolidação maior que o SIM, limitando o ano mais recente disponível. E o sub-registro de óbitos infantis, historicamente maior no Norte/Nordeste, pode atenuar o gradiente real — ou seja, a desigualdade verdadeira tende a ser ainda maior que a medida.",
        ],
      },
    ],
    referencias: [
      "BRASIL. Ministério da Saúde. SINASC e SIM — microdados 2021–2023. DATASUS.",
      "Saúde em Dado. mart_mortalidade_infantil_uf e mart_natalidade_municipio (v3.1.0). saudeemdado.com/nascimentos.",
      "RIPSA. Indicadores e Dados Básicos para a Saúde no Brasil (IDB): conceitos e aplicações. 2ª ed.",
      "França EB et al. Mortalidade infantil no Brasil: tendências e desigualdades. Rev Bras Epidemiol.",
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
      "A partir das Autorizações de Internação Hospitalar (SIH/AIH) de 2022 a 2024 — 39,9 milhões de internações e R$ 63,2 bilhões aprovados —, descrevemos volume, permanência média, mortalidade intra-hospitalar e custo por capítulo da CID-10, evidenciando que o gasto se concentra nas doenças circulatórias e que a mortalidade hospitalar varia de <0,1% (parto) a 13% (infecciosas).",
    secoes: [
      {
        titulo: "Dados e métodos",
        paragrafos: [
          "Fonte: SIH/SUS — arquivos RD (AIH aprovadas), microdados 2022–2024, processados por município de residência do paciente (MUNIC_RES). Foram contabilizadas 39.883.796 internações no triênio (14.171.364 apenas em 2024), com valor total aprovado de R$ 63,2 bilhões.",
          "Definições: a causa é o capítulo da CID-10 do diagnóstico principal (DIAG_PRINC); a permanência média é a soma de DIAS_PERM dividida pelo número de internações; a mortalidade intra-hospitalar é a razão entre AIH com MORTE=1 e o total; o custo é o valor total aprovado (VAL_TOT). Este artigo detalha o ano de 2024 (preliminar).",
        ],
      },
      {
        titulo: "Resultados: os oito maiores capítulos (2024)",
        paragrafos: [
          "A tabela ordena, por volume, os oito capítulos que mais internam. Três padrões se destacam: gravidez/parto lidera em volume mas tem a menor permanência, mortalidade e custo; as doenças do aparelho circulatório, embora não sejam o maior volume, concentram o maior gasto (R$ 5,1 bilhões) e um custo médio quase seis vezes o do parto; e as doenças infecciosas apresentam a maior mortalidade intra-hospitalar (13%) e a maior permanência (7,6 dias).",
        ],
        tabela: {
          titulo: "Internações SUS por capítulo CID-10 — Brasil, 2024",
          colunas: ["Capítulo (CID-10)", "Internações", "Perm. (dias)", "Mort. (%)", "Custo médio (R$)", "Gasto (R$ bi)"],
          linhas: [
            ["XV — Gravidez, parto e puerpério", "2.115.667", "2,6", "0,04", "610", "1,29"],
            ["XIX — Lesões e causas externas", "1.580.034", "4,9", "2,09", "1.457", "2,30"],
            ["XI — Aparelho digestivo", "1.501.891", "3,5", "2,91", "1.409", "2,12"],
            ["X — Aparelho respiratório", "1.361.054", "6,0", "8,89", "1.467", "2,00"],
            ["IX — Aparelho circulatório", "1.333.288", "6,4", "8,07", "3.824", "5,10"],
            ["II — Neoplasias", "1.105.852", "4,4", "7,29", "2.490", "2,75"],
            ["XIV — Aparelho geniturinário", "1.073.282", "4,3", "3,21", "1.232", "1,32"],
            ["I — Infecciosas e parasitárias", "967.291", "7,6", "13,04", "1.910", "1,85"],
          ],
          nota: "Fonte: SIH/SUS (AIH aprovadas), 2024 preliminar. Mortalidade e custo são brutos, sem ajuste por perfil de casos. Elaboração: Saúde em Dado.",
        },
      },
      {
        titulo: "Interpretação para a gestão",
        paragrafos: [
          "A leitura conjunta dos quatro indicadores é o que dá sentido gerencial. Volume alto com baixo custo e baixa mortalidade (parto) indica linha de cuidado de rotina; volume moderado com custo e mortalidade altos (circulatório) sinaliza onde a alocação de recursos e a organização da rede de urgência mais pesam. A plataforma permite reproduzir esta tabela por município e ordenar por qualquer coluna, viabilizando benchmarking entre pares.",
          "Uma ressalva de interpretação: a mortalidade intra-hospitalar bruta reflete fortemente o perfil de casos (case-mix) — um hospital terciário concentra casos graves e, por isso, mortalidade maior, sem que isso signifique pior qualidade. Comparações de mortalidade entre serviços exigem ajuste de risco, que não fazemos aqui.",
        ],
      },
      {
        titulo: "Limitações",
        paragrafos: [
          "O SIH cobre apenas a rede SUS; como cerca de um quarto da população tem plano privado, concentrado em municípios mais ricos, comparações de internações por habitante entre municípios são confundidas pela cobertura suplementar. A AIH é unidade administrativa, não paciente — reinternações contam múltiplas vezes. O valor aprovado segue a tabela SUS, não o custo econômico real. E 2024 é preliminar.",
        ],
      },
    ],
    referencias: [
      "BRASIL. Ministério da Saúde. SIH/SUS — Autorização de Internação Hospitalar (AIH). Microdados 2022–2024. DATASUS.",
      "Saúde em Dado. mart_internacoes_municipio (v3.1.0). DOI: 10.5281/zenodo.20706845. saudeemdado.com/internacoes.",
      "Ministério da Saúde. Manual técnico do SIH/SUS e Tabela de Procedimentos, Medicamentos e OPM do SUS.",
      "Iezzoni LI. Risk Adjustment for Measuring Health Care Outcomes. 4ª ed. Health Administration Press, 2013.",
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
      "Cruzando um índice-proxy de vulnerabilidade social (Censo 2022) com a taxa de mortalidade padronizada nos 5.570 municípios, encontramos correlação de Pearson de −0,125 — fraca e na direção oposta à esperada. Argumentamos que o resultado revela menos sobre saúde e mais sobre a qualidade do registro de óbitos.",
    secoes: [
      {
        titulo: "Dados e métodos",
        paragrafos: [
          "Os determinantes sociais da saúde preveem que pobreza, baixa escolaridade e falta de saneamento se traduzam em pior saúde — e maior mortalidade. Cruzamos nosso índice-proxy de vulnerabilidade social (analfabetismo + ausência de água encanada no Censo 2022, combinados por z-score, em quartis Q1–Q4) com a taxa de mortalidade padronizada por idade de 2023, nos 5.570 municípios.",
          "Esperávamos correlação positiva. O que encontramos foi uma correlação de Pearson de −0,125 (n = 5.570): fraca e na direção oposta. Em vez de descartar o achado, ele merece ser explicado — e é aqui que a análise se torna interessante.",
        ],
        tabela: {
          titulo: "Mortalidade padronizada média por quartil de vulnerabilidade (2023)",
          colunas: ["Quartil de vulnerabilidade", "Municípios (n)", "Mortalidade padronizada média (/100 mil)"],
          linhas: [
            ["Q1 — menos vulnerável", "1.403", "706"],
            ["Q2", "1.392", "721"],
            ["Q3", "1.388", "696"],
            ["Q4 — mais vulnerável", "1.387", "663"],
          ],
          nota: "Fonte: dim_ivs (proxy Censo 2022) × mart_mortalidade_municipio (taxa padronizada, 2023). O quartil mais vulnerável tem a menor mortalidade medida — o paradoxo. Elaboração: Saúde em Dado.",
        },
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
