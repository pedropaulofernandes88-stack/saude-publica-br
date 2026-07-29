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
          "E fomos além: reconciliamos o próprio denominador, interpolando a população por UF entre os Censos de 2010 e 2022 para eliminar tanto o excesso da projeção quanto o degrau de 2022 (a população de 2020, por exemplo, cai de 211,8 para ~200,9 milhões). Mesmo com o denominador corrigido, o excesso padronizado subiu apenas para ~530 mil — ainda longe dos 643 mil da tendência. A lição final é mais forte que a inicial: o problema não era só o dado populacional, era metodológico. Corrigir o denominador não salvou a padronização — e confirmou, por eliminação, que a tendência é o método a manter.",
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
      "Classificando os óbitos de 2024 (1,43 milhão) pelos capítulos e categorias da CID-10, descrevemos o perfil de causas do Brasil contemporâneo: as doenças do aparelho circulatório respondem por 25,7% das mortes, seguidas de neoplasias (17,1%) e respiratórias (13,0%). No nível de categoria, o infarto (I21) lidera — mas as causas mal definidas (R99) aparecem em terceiro, um alerta sobre a qualidade do registro.",
    secoes: [
      {
        titulo: "Dados e métodos",
        paragrafos: [
          "Fonte: SIM/DataSUS, óbitos não fetais de 2024 (1.426.346 no total), classificados pela causa básica em capítulos (I–XXII) e categorias de 3 caracteres da CID-10. Percentuais calculados sobre o total de óbitos com capítulo definido.",
          "A CID-10 organiza a causa básica em 22 capítulos e milhares de categorias. Mapear essa distribuição desenha o perfil do que mata no Brasil — e revela o grau de transição epidemiológica.",
        ],
      },
      {
        titulo: "O perfil por capítulo (2024)",
        paragrafos: [
          "As doenças do aparelho circulatório lideram com folga (um quarto das mortes), seguidas de neoplasias e respiratórias. É a assinatura de um país que completou, em grande medida, a transição epidemiológica — as crônicas não transmissíveis suplantaram as infecciosas. Duas exceções pedem leitura crítica: as causas externas (10%), marcador de violência e trânsito; e o capítulo XVIII (mal definidas, 5,4%), que não é uma 'doença', mas um indicador inverso da qualidade da informação.",
        ],
        tabela: {
          titulo: "Óbitos por capítulo CID-10 — Brasil, 2024 (oito maiores)",
          colunas: ["Capítulo", "Óbitos", "% do total"],
          linhas: [
            ["IX — Aparelho circulatório", "365.952", "25,7"],
            ["II — Neoplasias", "243.935", "17,1"],
            ["X — Aparelho respiratório", "184.926", "13,0"],
            ["XX — Causas externas", "143.547", "10,1"],
            ["IV — Endócrinas/metabólicas", "80.291", "5,6"],
            ["XVIII — Sintomas e sinais mal definidos", "77.657", "5,4"],
            ["XI — Aparelho digestivo", "75.232", "5,3"],
            ["I — Infecciosas e parasitárias", "72.382", "5,1"],
          ],
          nota: "Fonte: SIM/DataSUS, 2024 preliminar. Elaboração: Saúde em Dado.",
        },
      },
      {
        titulo: "Do capítulo à categoria específica",
        paragrafos: [
          "Descer ao nível de 3 caracteres é ainda mais revelador. O infarto agudo do miocárdio (I21) lidera isoladamente, seguido da pneumonia (J18). O achado que merece vigilância é o terceiro lugar: R99 (causas mal definidas), com quase 49 mil óbitos — sinal de que, para uma fração relevante das mortes, sequer sabemos a causa. DPOC (J44), diabetes (E14), AVC (I64), insuficiência cardíaca (I50) e hipertensão (I10) completam o topo, confirmando o peso cardiometabólico e respiratório.",
        ],
        tabela: {
          titulo: "Categorias CID-10 (3 caracteres) mais frequentes — Brasil, 2024",
          colunas: ["Categoria", "Descrição", "Óbitos"],
          linhas: [
            ["I21", "Infarto agudo do miocárdio", "86.300"],
            ["J18", "Pneumonia", "74.676"],
            ["R99", "Causas mal definidas", "48.773"],
            ["J44", "DPOC", "45.146"],
            ["E14", "Diabetes mellitus", "40.142"],
            ["I64", "AVC (não especificado)", "32.455"],
            ["I50", "Insuficiência cardíaca", "31.598"],
            ["I10", "Hipertensão essencial", "31.055"],
            ["C34", "Neoplasia de brônquios/pulmão", "29.822"],
            ["N39", "Transtornos do trato urinário", "28.719"],
          ],
          nota: "Fonte: SIM/DataSUS, 2024 preliminar. R99 não é doença: é ausência de diagnóstico. Elaboração: Saúde em Dado.",
        },
      },
      {
        titulo: "Por que mapear causas importa (e suas limitações)",
        paragrafos: [
          "O perfil de causas orienta prioridades — prevenção cardiovascular, rastreamento de câncer, manejo de crônicas respiratórias — e, disponibilizado por município/ano/sexo, aproxima o planejamento da realidade local em vez de aplicar médias nacionais a contextos heterogêneos.",
          "Limitações: 2024 é preliminar; as causas mal definidas (R99 e capítulo XVIII) não são redistribuídas, o que subestima levemente as causas específicas onde o registro é pior (Norte/Nordeste); e a causa básica, embora padronizada, depende da qualidade do preenchimento da declaração de óbito.",
        ],
      },
    ],
    referencias: [
      "OMS. Classificação Estatística Internacional de Doenças e Problemas Relacionados à Saúde (CID-10). 10ª rev.",
      "Saúde em Dado. mart_mortalidade_causa e mart_mortalidade_uf_mes (v3.1.0). saudeemdado.com.",
      "Schramm JMA et al. Transição epidemiológica e o estudo de carga de doença no Brasil. Ciência & Saúde Coletiva, 2004.",
      "GBD Brazil Collaborators. Burden of disease in Brazil, 1990–2016. The Lancet, 2018.",
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
        titulo: "O problema e a tese",
        paragrafos: [
          "Os dados do SUS são públicos, mas a barreira de acesso é técnica: microdados em formato DBC proprietário, fragmentados por unidade federativa e competência, somando dezenas de gigabytes. A maior parte do esforço de qualquer estudo epidemiológico no Brasil é gasta antes da análise — em obtenção e limpeza.",
          "A tese desta plataforma é que a infraestrutura determina a pesquisa possível. Reduzir a barreira de acesso a zero — uma consulta de API em vez de semanas de engenharia — muda o que pesquisadores, jornalistas e gestores conseguem perguntar. A tabela resume a pilha que torna isso sustentável sem custo de manutenção.",
        ],
        tabela: {
          titulo: "A pilha de custo zero",
          colunas: ["Camada", "Tecnologia", "Papel", "Custo"],
          linhas: [
            ["Processamento", "DuckDB (local)", "agrega microdados → marts", "R$ 0"],
            ["Banco", "Supabase / PostgreSQL (free)", "serve os marts agregados", "R$ 0"],
            ["API", "PostgREST", "REST automática sobre o Postgres", "R$ 0"],
            ["Front-end", "Next.js estático + CDN", "site + JSON congelado no build", "R$ 0"],
            ["Citação", "Zenodo + GitHub Releases", "DOI versionado, reprodutibilidade", "R$ 0"],
          ],
          nota: "Egress ao banco é minimizado congelando as consultas comuns em JSON no build. Elaboração: Saúde em Dado.",
        },
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
  {
    slug: "visao-hospitalar-hsmr-los-forecast",
    titulo: "Visão hospitalar: o que há de novo no Saúde em Dado, e como a plataforma inteira funciona",
    dek: "HSMR, permanência esperada e previsão de demanda por estabelecimento (CNES), com três anos de SIH e uma regra simples: nenhum indicador é publicado sem declarar, com o mesmo destaque, o que ele não pode responder.",
    data: "2026-07-15",
    leituraMin: 12,
    tags: ["hospitalar", "HSMR", "SIH", "case-mix", "previsão de demanda", "arquitetura"],
    resumo:
      "Descrevemos a plataforma Saúde em Dado — cinco sistemas do DataSUS, pipeline aberto, API pública gratuita — e detalhamos seu módulo mais recente: a Visão Hospitalar. Por estabelecimento (CNES), publicamos mortalidade ajustada por case-mix (HSMR, padronização indireta), tempo de permanência esperado por diagnóstico e uma projeção de demanda mensal. Com três anos de SIH (2022–2024, 14.197 registros hospital-ano), o HSMR agregado calibra em 1,0000 nos três anos — a prova estrutural de que a padronização está correta — e a confiança do forecast salta de 0% para 92,3% de previsões 'adequadas' ao passar de 12 para 36 meses de histórico. Também explicamos, com a mesma ênfase, o que a plataforma deliberadamente não calcula: risco de readmissão por paciente, porque a AIH pública não tem identificador estável de indivíduo.",
    secoes: [
      {
        titulo: "O que é o Saúde em Dado",
        paragrafos: [
          "Saúde em Dado é uma plataforma aberta e de custo zero que transforma microdados do DataSUS e do IBGE em indicadores municipais e hospitalares validados, com pipeline integralmente reprodutível. Integra cinco sistemas de informação: SIM (mortalidade, 2015–2024, mais de 13 milhões de óbitos), SIH (internações hospitalares, 2022–2024), SINAN (dengue, 2015–2024), SINASC (nascimentos, 2021–2023) e as bases de população e malha do IBGE.",
          "A arquitetura é deliberadamente simples: agregação local (DuckDB), publicação apenas de marts já agregados — nunca microdado individual —, API REST automática (PostgREST/Supabase) e um site estático servido por CDN. Nenhuma peça dessa pilha tem custo de manutenção, o que é uma escolha metodológica tanto quanto técnica: projetos de dados abertos costumam morrer quando acaba o financiamento ou o tempo do mantenedor. Detalhes da arquitetura estão em outro artigo desta seção; aqui o foco é o módulo mais novo.",
        ],
      },
      {
        titulo: "A lacuna: dado por município não é dado por hospital",
        paragrafos: [
          "Até aqui, a plataforma descrevia internações por município — volume, permanência média, mortalidade bruta, custo — e uma visão hospitalar (CNES) com esses mesmos agregados brutos. Mortalidade bruta, porém, é enganosa quando se compara hospitais: um terciário de alta complexidade internando casos graves tem mortalidade maior que uma maternidade, sem que isso signifique pior assistência. Faltava um ajuste pelo perfil de caso — o que a literatura de gestão hospitalar chama de case-mix.",
          "A Visão Hospitalar (saudeemdado.com/hospitalar) fecha essa lacuna com três indicadores por estabelecimento: mortalidade ajustada (HSMR), permanência esperada por diagnóstico (LOS) e uma projeção de demanda mensal — todos derivados do mesmo SIH já publicado, sem coleta adicional.",
        ],
      },
      {
        titulo: "HSMR: padronização indireta, não opinião",
        paragrafos: [
          "HSMR (Hospital Standardized Mortality Ratio) é a razão entre óbitos observados e óbitos esperados de um hospital, dado seu perfil de casos. Calculamos o esperado por padronização indireta: para cada estrato definido por faixa etária (9 faixas, de menor de 1 ano a 80+) e capítulo CID-10 (22 capítulos), obtemos a taxa de mortalidade nacional daquele estrato e a aplicamos ao volume de internações do hospital no mesmo estrato. A soma desses óbitos esperados por estrato é o denominador; HSMR = observado / esperado.",
          "A interpretação é direta: HSMR acima de 1 indica mortalidade acima do esperado para aquele case-mix; abaixo de 1, o inverso. Não é veredito de qualidade assistencial — é um ponto de partida para investigação, exatamente como o método é usado por sistemas de saúde que o publicam há décadas (Reino Unido, Canadá).",
          "Por construção, a soma nacional de óbitos observados sobre a soma nacional de óbitos esperados converge a 1,0000 — é a verificação estrutural do método, não uma coincidência. Rodamos essa checagem para os três anos disponíveis antes de publicar cada um, e o resultado é exato:",
        ],
        tabela: {
          titulo: "HSMR agregado nacional, por ano (verificação de calibração)",
          colunas: ["Ano", "Hospitais (≥12 intern.)", "Óbitos observados", "Óbitos esperados", "HSMR agregado", "Instáveis (esp. < 5)"],
          linhas: [
            ["2022", "4.757", "605.517", "605.514,6", "1,0000", "412 (8,7%)"],
            ["2023", "4.701", "588.626", "588.617,9", "1,0000", "439 (9,3%)"],
            ["2024", "4.739", "622.222", "622.215,2", "1,0000", "457 (9,6%)"],
          ],
          nota: "Fonte: mart_hsmr_hospital. 'Instáveis' são hospitais com óbitos esperados < 5 — sinalizados com ⚠ na tabela pública, nunca ocultados. Elaboração: Saúde em Dado.",
        },
      },
      {
        titulo: "O limiar de instabilidade: por que 5, não 20",
        paragrafos: [
          "Quando o número esperado de óbitos é pequeno, a razão observado/esperado fica hipersensível a um único caso a mais — um hospital com 0,2 óbitos esperados e 1 óbito observado produz HSMR de 5, um número tecnicamente correto e estatisticamente inútil. A regra geral de epidemiologia para razões padronizadas marca essa fronteira em esperado < 5, ponto em que o intervalo de confiança exato de Poisson deixa de ser confiável.",
          "Estudos específicos de HSMR por vezes usam um corte mais conservador — 20 óbitos esperados — mas nesses estudos o hospital é excluído do relatório. Optamos por não excluir: hospitais pequenos continuam na tabela pública, apenas marcados como instáveis (entre 8,7% e 9,6% do total, conforme o ano). É a mesma lógica já aplicada aos municípios pequenos nas taxas de mortalidade da plataforma — sinalizar a incerteza, não apagar o dado.",
          "Um exemplo real ilustra o mecanismo: em 2024, um hospital de Castanhal (PA) registrou HSMR de 22,38 com apenas 0,04 óbitos esperados e 1 óbito observado — marcado ⚠ corretamente. No mesmo ano, um hospital do Rio de Janeiro com 132,7 óbitos esperados (base grande, estável) registrou HSMR de 7,45 — um sinal que já merece investigação por não depender de um único caso.",
        ],
      },
      {
        titulo: "Permanência esperada (LOS): mediana do hospital vs. mediana nacional",
        paragrafos: [
          "Para cada diagnóstico (CID-10, 3 caracteres), calculamos a mediana nacional de dias de internação e comparamos à mediana do próprio hospital para o mesmo diagnóstico. Por volume — mais de 248 mil combinações hospital×diagnóstico nos três anos —, não guardamos a duração individual de cada internação: a mediana é aproximada por um histograma de oito faixas de dias (0–1, 2–3, 4–7, 8–14, 15–21, 22–30, 31–60, 61+), tomando o ponto médio da faixa onde a frequência acumulada cruza 50%. É uma aproximação declarada, não a mediana exata.",
          "O desvio (hospital − nacional) revela padrões clinicamente interpretáveis, não ruído: em 2024, hospitais com maior desvio positivo concentraram-se em condições que legitimamente exigem internação prolongada — epilepsia (G40) e transtornos psiquiátricos (F09, F23, F32) em unidades especializadas, com desvios de +40 a +70 dias sobre a mediana nacional. O indicador não classifica hospitais como 'bons' ou 'ruins'; localiza onde a permanência foge do padrão para investigação qualificada.",
        ],
      },
      {
        titulo: "Previsão de demanda: por que 36 meses mudam tudo",
        paragrafos: [
          "O terceiro indicador projeta a demanda mensal de cada hospital por tendência linear sobre a série observada — o mesmo método já usado no excesso de mortalidade da plataforma (regressão sobre a série histórica, projetada adiante), aqui aplicado por estabelecimento em vez de por UF. A faixa de incerteza é a previsão ± 1,96 desvio-padrão dos resíduos do ajuste — uma faixa indicativa, não um intervalo de predição formal.",
          "O SIH hospitalar (nível CNES) originalmente só cobria 2024. Um forecast sobre 12 pontos mensais é estatisticamente frágil, e declaramos isso: toda previsão nascia marcada confiança 'baixa'. Estendemos o reprocessamento para 2022 e 2023 — com verificação de calibração do HSMR (tabela acima) confirmando a correção de cada ano antes do envio — e a série de demanda passou de 12 para 36 meses por hospital. O efeito na confiança do forecast foi imediato:",
        ],
        tabela: {
          titulo: "Confiança do forecast de demanda, antes e depois da extensão a 3 anos",
          colunas: ["Situação", "Meses de histórico", "Previsões 'adequada'", "Previsões 'baixa'"],
          linhas: [
            ["Antes (só 2024)", "até 12", "0 (0%)", "13.902 (100%)"],
            ["Depois (2022–2024)", "até 36", "13.419 (92,3%)", "1.125 (7,7%)"],
          ],
          nota: "Limiar: confiança 'adequada' a partir de 24 meses de histórico contínuo. Fonte: mart_forecast_demanda_hospital, 14.544 previsões / 4.848 hospitais. Elaboração: Saúde em Dado.",
        },
      },
      {
        titulo: "O que esta página deliberadamente não faz",
        paragrafos: [
          "Não estimamos risco de readmissão ou reinternação por paciente. A AIH pública não tem identificador estável de indivíduo — o CNS é removido dos microdados por exigência da LGPD —, o que significa que ligar duas internações à mesma pessoa exigiria um dado que simplesmente não é público. Ferramentas que oferecem esse indicador a partir de dado aberto do DataSUS, ou têm acesso a dado institucional privado (prontuário, com identificador de paciente) que o Saúde em Dado nunca terá por desenho, ou estão publicando uma aproximação sem essa base.",
          "Preferimos declarar a limitação, com o mesmo destaque dado aos resultados, a produzir uma métrica que pareça precisa sem sustentação nos dados abertos. É o mesmo princípio já aplicado ao excesso de mortalidade (ver 'Por que isso importa além do número' em outro artigo desta seção) e à taxa padronizada em municípios pequenos: honestidade metodológica não é um adendo, é a condição para que o número seja citável.",
        ],
      },
      {
        titulo: "Acesso e reprodutibilidade",
        paragrafos: [
          "Os quatro marts descritos aqui (mart_hsmr_hospital, mart_los_hospital, mart_demanda_mensal_hospital, mart_forecast_demanda_hospital) são públicos via API REST sem cadastro, com download em Parquet e checksum SHA-256, sob CC BY 4.0. O código dos pipelines é aberto (MIT) — scripts/pipeline_sih_hospitalar.py e scripts/forecast_demanda_hospitalar.py — e cada número desta análise pode ser regenerado a partir dos arquivos originais do SIH/DataSUS. Um agente MCP publicado no PyPI (saudeemdado-mcp) permite consultar os mesmos indicadores em linguagem natural, com cada resposta citando a fonte.",
        ],
      },
    ],
    referencias: [
      "Saúde em Dado. mart_hsmr_hospital, mart_los_hospital, mart_demanda_mensal_hospital, mart_forecast_demanda_hospital. saudeemdado.com/hospitalar.",
      "Brasil, Ministério da Saúde / DATASUS. SIH — Sistema de Informações Hospitalares (AIH aprovadas), 2022–2024.",
      "Jarman B. et al. Explaining differences in English hospital death rates using routinely collected data. BMJ, 1999 (método HSMR original).",
      "Canadian Institute for Health Information. Hospital Standardized Mortality Ratio (HSMR): Methodology Notes.",
      "Saúde em Dado. Inteligência epidemiológica a custo zero: a arquitetura por trás da plataforma. saudeemdado.com/artigos.",
    ],
  },
  {
    slug: "o-que-os-indicadores-nao-comparam",
    titulo: "O que os indicadores não comparam: quatro achados, um mesmo erro",
    dek: "Excesso de mortalidade, ICSAP, cobertura da atenção primária e mortalidade hospitalar ajustada. Quatro indicadores, quatro fontes, quatro métodos — e, em todos, o ajuste aparente esconde o mesmo efeito estrutural.",
    data: "2026-07-19",
    leituraMin: 14,
    tags: ["métodos", "denominador", "confundimento", "HSMR", "ICSAP", "atenção primária"],
    resumo:
      "Ao longo da construção desta plataforma, quatro indicadores independentes falharam pela mesma razão. O excesso de mortalidade padronizado por idade subestima o pico pandêmico em ~138 mil óbitos porque o denominador populacional está quebrado. O ICSAP mede apenas a rede SUS, num país onde a cobertura privada varia com a renda. A cobertura potencial da atenção primária satura acima de 100% em 86% dos municípios e correlaciona-se com o porte (ρ = −0,54), não com internações evitáveis (ρ = +0,004). E o HSMR, mesmo calibrado a 1,0000, penaliza hospitais grandes: os classificados acima do esperado são quase 5× maiores que os abaixo. O padrão comum não é o denominador em si — é a ilusão de que um indicador ajustado já é comparável.",
    secoes: [
      {
        paragrafos: [
          "Indicadores de saúde existem para permitir comparação. Sem eles, cada município e cada hospital é um caso isolado; com eles, é possível perguntar quem está melhor, quem piorou, onde intervir. Todo o esforço técnico da epidemiologia descritiva — padronizar por idade, calcular por 100 mil habitantes, ajustar por perfil de casos — serve a esse propósito: tornar comparável o que não é diretamente comparável.",
          "Este artigo é sobre as vezes em que esse esforço falha silenciosamente. Não falha produzindo erro visível: falha produzindo um número plausível, bem-formatado, aparentemente ajustado — que mede outra coisa. Reunimos aqui quatro casos independentes encontrados na construção desta plataforma. Não foram procurados; apareceram quando cada indicador foi testado antes de publicar.",
        ],
      },
      {
        titulo: "Caso 1 — O excesso de mortalidade e a população que não existia",
        paragrafos: [
          "Para medir quantas pessoas morreram a mais na pandemia, a recomendação metodológica corrente é padronizar por idade: aplicar taxas por faixa etária à estrutura populacional de cada ano. É o método mais sofisticado disponível, e deveria ser o melhor.",
          "No Brasil de 2020–2024, ele produz ~505 mil óbitos em excesso no pico pandêmico. O método simples — regressão de tendência sobre os óbitos observados, sem tocar em população — produz 643 mil, valor compatível com as estimativas internacionais independentes (~660–680 mil). O método sofisticado erra para menos em cerca de 138 mil mortes.",
          "A causa não está no método, está no insumo. A projeção populacional do IBGE de 2018 superestimava a população brasileira; o Censo 2022 a revisou para baixo em milhões de pessoas, e a série pós-Censo introduz uma descontinuidade em 2022. Uma população idosa inflada infla o número esperado de óbitos e, portanto, apaga o excesso. Reconciliamos o denominador interpolando os Censos de 2010 e 2022 — o excesso subiu para ~530 mil, mas não convergiu. Parte do problema era o dado; parte era metodológica.",
          "A lição: um método que depende de um denominador herda toda a fragilidade desse denominador — e não avisa quando ela está presente.",
        ],
      },
      {
        titulo: "Caso 2 — O ICSAP e o denominador que só enxerga metade do país",
        paragrafos: [
          "As Internações por Condições Sensíveis à Atenção Primária (ICSAP) medem internações que bom acesso à atenção básica poderia ter evitado. É um dos melhores indicadores-proxy de qualidade da porta de entrada do SUS, usado em pesquisa e em avaliação de política pública.",
          "O problema é que ele é calculado sobre o SIH, que registra apenas internações pagas pelo SUS. Cerca de um quarto da população brasileira tem plano de saúde — e essa fração não é distribuída ao acaso: concentra-se em municípios mais ricos e urbanos. Um município com alta cobertura privada terá ICSAP baixo simplesmente porque parte de seus moradores se interna fora do SUS, sem que sua atenção básica seja melhor.",
          "Aqui o denominador não está errado, está incompleto — e o viés não é aleatório, é correlacionado com renda. Comparar ICSAP entre municípios de perfis socioeconômicos diferentes sem levar isso em conta produz um ranking que mede, em parte, quem tem plano de saúde.",
        ],
      },
      {
        titulo: "Caso 3 — A cobertura da atenção primária que mede tamanho",
        paragrafos: [
          "Este é o caso mais recente e o mais surpreendente. O Ministério da Saúde publica mensalmente a cobertura potencial da Atenção Primária por município: capacidade instalada das equipes credenciadas dividida pela população. É um dado atual (jan/2021 a mai/2026), granular e oficialmente mantido.",
          "A hipótese natural é que mais cobertura signifique menos internações evitáveis. Testamos. A correlação bruta entre cobertura potencial e ICSAP por 100 mil habitantes é ρ = +0,004 — indistinguível de zero, e no sinal contrário ao esperado. Controlando porte populacional e vulnerabilidade social, ρ parcial = +0,018. A associação simplesmente não existe.",
          "O motivo aparece ao estratificar por porte. Como a capacidade de cada equipe é padronizada, um município pequeno satura o indicador com poucas equipes: a cobertura ultrapassa 100% em 86% dos municípios brasileiros e chega a 800%. Nos municípios com menos de 10 mil habitantes, a cobertura mediana é 167% e 97% deles estão saturados. Nos com mais de 200 mil, a cobertura mediana é 78,7% e apenas 13% saturam.",
          "A correlação entre cobertura e população é ρ = −0,54. Ou seja: a maior parte da variação do indicador entre municípios não informa sobre a atenção primária — informa sobre quantos habitantes o município tem. E os municípios de maior cobertura são justamente os de maior ICSAP, o oposto da hipótese de política pública.",
        ],
        tabela: {
          titulo: "Cobertura potencial da APS e ICSAP por porte municipal (2024)",
          colunas: ["Porte", "Municípios", "Cobertura mediana", "Saturados (>100%)", "ICSAP/100 mil (mediana)"],
          linhas: [
            ["< 10 mil hab.", "2.466", "167,1%", "97%", "1.468"],
            ["10–50 mil", "2.429", "142,0%", "88%", "1.546"],
            ["50–200 mil", "517", "97,1%", "46%", "1.220"],
            ["> 200 mil", "158", "78,7%", "13%", "960"],
          ],
          nota: "Se a cobertura potencial medisse força da atenção primária, o gradiente de ICSAP seria inverso ao de cobertura. Ele acompanha, na verdade, o porte. Fontes: e-Gestor AB (cobertura) e SIH/DataSUS (ICSAP). Reprodutível em scripts/analise_cobertura_icsap.py. Elaboração: Saúde em Dado.",
        },
      },
      {
        titulo: "Caso 4 — O HSMR calibrado que ainda penaliza hospital grande",
        paragrafos: [
          "A mortalidade hospitalar bruta é reconhecidamente injusta: um hospital terciário que recebe os casos mais graves morre mais que uma maternidade, sem que isso signifique pior assistência. A solução clássica é o HSMR — razão entre óbitos observados e esperados, ajustada pelo perfil de casos. Implementamos com padronização indireta por faixa etária × capítulo CID-10, e o resultado calibra perfeitamente: a razão agregada nacional é 1,0000 nos três anos publicados, exatamente como a construção do método exige.",
          "Calibração, porém, não é o mesmo que ausência de viés. Classificando os hospitais por significância estatística, os que ficam acima do esperado têm mediana de 5.350 internações; os abaixo, 1.136. Os hospitais “acima” são quase cinco vezes maiores e concentram 58,9% de todos os óbitos hospitalares do país.",
          "A explicação é o que se chama case-mix residual. Um capítulo da CID-10 é uma categoria larga: o capítulo IX abrange desde hipertensão até cirurgia cardíaca complexa. Ajustar por capítulo remove a diferença entre um hospital de partos e um de cardiologia, mas não remove a diferença entre dois hospitais de cardiologia — um que faz consulta e outro que faz transplante. Os grandes centros concentram a gravidade dentro de cada capítulo, e o ajuste não a enxerga.",
          "Há uma segunda armadilha, independente da primeira: testar ~4.600 hospitais por ano é testar ~4.600 hipóteses simultaneamente, e a 5% de significância isso produziria dezenas de falsos positivos só por acaso. Corrigimos com Benjamini-Hochberg (controle da taxa de falsas descobertas) por ano civil — o efeito foi honesto, não dramático: de 10.046 hospitais-ano significativos sem correção, 282 (2,8%) perdem a classificação após o ajuste. A maior parte do sinal bruto é real, mas nem todo.",
          "O indicador continua útil: um HSMR alto que sobrevive à correção por múltiplas comparações é uma hipótese que merece investigação. O que ele não suporta, em nenhum dos dois casos, é ranking. E note que a solução para o case-mix residual — ajustar por procedimento, gravidade ou comorbidade — exigiria dados que a AIH pública não traz.",
        ],
      },
      {
        titulo: "O padrão comum",
        paragrafos: [
          "Os quatro casos não compartilham a mesma fonte, o mesmo método nem o mesmo tipo de erro. O que compartilham é a estrutura da falha: em cada um, uma variável estrutural — tamanho da população, tamanho do município, tamanho do hospital, cobertura privada — atravessa o indicador e sobrevive ao ajuste que deveria neutralizá-la.",
          "Isso importa porque o ajuste produz confiança. Uma taxa padronizada por idade parece mais comparável que uma taxa bruta; um HSMR parece mais justo que a mortalidade bruta; uma cobertura percentual parece independente de escala justamente por ser percentual. Em todos esses casos, a aparência de ajuste é o que torna o erro difícil de detectar: o número passa no teste do olhar.",
          "A implicação prática não é abandonar indicadores ajustados — é testá-los contra o confundidor estrutural óbvio antes de publicá-los. Nos quatro casos aqui, o teste custou poucas linhas de código: correlacionar o indicador com o tamanho. Quando essa correlação é forte, o indicador está medindo escala, não desempenho.",
        ],
        tabela: {
          titulo: "Os quatro casos e a variável estrutural que sobrevive ao ajuste",
          colunas: ["Indicador", "Ajuste aplicado", "Variável que sobrevive", "Efeito medido"],
          linhas: [
            ["Excesso de mortalidade", "Padronização por idade", "Erro do denominador populacional", "−138 mil óbitos no pico pandêmico"],
            ["ICSAP", "Taxa por 100 mil hab.", "Cobertura privada (fora do SIH)", "Viés correlacionado com renda"],
            ["Cobertura da APS", "Percentual da população", "Porte do município", "ρ = −0,54 com população; +0,004 com ICSAP"],
            ["HSMR", "Padronização indireta (idade × capítulo)", "Tamanho e complexidade do hospital", "“Acima do esperado” são ~5× maiores"],
          ],
          nota: "Elaboração: Saúde em Dado, a partir dos marts públicos do projeto.",
        },
      },
      {
        titulo: "O que fizemos com isso",
        paragrafos: [
          "Nenhum dos quatro indicadores foi retirado da plataforma. Todos continuam publicados — com o teste, o número e a limitação no mesmo lugar em que está o resultado. O excesso de mortalidade usa o método de tendência, e a análise de sensibilidade que o justifica está publicada. O ICSAP traz o aviso de cobertura suplementar junto ao ranking. A cobertura da APS ganhou uma página que explica, antes de qualquer tabela, para que ela serve e para que não serve. E o HSMR passou a exibir intervalo de confiança em vez de uma flag binária: um hospital com HSMR 5,94 e intervalo [0,13 – 27,86] deixa de parecer um alarme e passa a ser o que é — um hospital pequeno demais para se afirmar qualquer coisa.",
          "Há um argumento mais amplo aqui, sobre o que significa publicar um indicador. Um número acompanhado da sua limitação é mais útil que o mesmo número sozinho, mesmo quando a limitação enfraquece a conclusão — porque a alternativa não é uma conclusão mais forte, é uma conclusão errada que ninguém detectou.",
        ],
      },
    ],
    referencias: [
      "Saúde em Dado. Análise de sensibilidade do excesso de mortalidade: scripts/sensibilidade_excesso_idade.py e scripts/reconciliacao_denominador.py.",
      "Saúde em Dado. Cobertura da APS × ICSAP: scripts/analise_cobertura_icsap.py; marts mart_cobertura_aps_municipio e mart_cobertura_icsap_municipio.",
      "Saúde em Dado. IC95% do HSMR (gamma/Poisson exato): scripts/hsmr_intervalo_confianca.py.",
      "Brasil, Ministério da Saúde. Relatório público de Cobertura da Atenção Primária (e-Gestor AB). relatorioaps.saude.gov.br.",
      "IBGE. Censo Demográfico 2022; Projeções da População (revisão 2018). SIDRA.",
      "Jarman B. et al. Explaining differences in English hospital death rates using routinely collected data. BMJ, 1999.",
      "Karlinsky A., Kobak D. Excess mortality during the COVID-19 pandemic: World Mortality Dataset. eLife, 2021.",
    ],
  },
];

export function getArtigo(slug: string): Artigo | undefined {
  return ARTIGOS.find((a) => a.slug === slug);
}
