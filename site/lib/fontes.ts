/**
 * De que sistema vem cada tabela publicada.
 *
 * POR QUE ISTO EXISTE
 * -------------------
 * A página `/dados/` tinha uma tabela "Vigência por base" escrita à mão, com
 * cinco linhas e intervalos digitados. Ela envelheceu como toda coluna copiada
 * neste projeto envelhece — em silêncio, e para pior:
 *
 *   * dizia que o SINASC ia até **2023** e que 2024 não fora liberado pelo MS.
 *     `mart_natalidade_municipio` cobre **2021–2024** desde a publicação de
 *     agosto;
 *   * mostrava **cinco** das dez fontes, e as duas ausências mais graves eram
 *     justamente as MAIS ATUAIS: vacinação (PNI/RNDS, até 2026-08) e atenção
 *     primária (até 2026). Quem procurasse "até onde vai cada série" concluía
 *     que a base para em 2025.
 *
 * O manifesto de publicação já sabe a competência de cada tabela. O que faltava
 * era o elo entre tabela e SISTEMA, que é conhecimento editorial e vive aqui —
 * junto com a observação de cada fonte, que também não se deriva.
 *
 * A GUARDA
 * --------
 * `fontes.test.mts` exige que **toda** tabela do manifesto esteja classificada.
 * Sem isso, publicar uma tabela nova a deixaria fora do painel sem que nada
 * avisasse — que é exatamente como a tabela manual perdeu metade das fontes.
 */

export interface Fonte {
  id: string;
  /** Como o painel chama a fonte. */
  nome: string;
  /** O sistema de origem, como o Ministério o nomeia. */
  sistema: string;
  orgao: string;
  /** O que ela acrescenta, em meia linha. */
  traz: string;
  /**
   * O que o leitor precisa saber antes de comparar períodos entre fontes.
   * Editorial: não se deriva de competência nenhuma.
   */
  observacao: string;
}

export const FONTES: Fonte[] = [
  {
    id: "sim",
    nome: "Mortalidade",
    sistema: "SIM",
    orgao: "DataSUS/MS",
    traz: "óbitos por município, causa (CID-10), sexo e faixa etária",
    observacao:
      "O ano mais recente é preliminar (SIM/PRELIM/DORES) e será revisado — os valores só crescem, e a codificação também muda.",
  },
  {
    id: "sih",
    nome: "Internações e hospitais",
    sistema: "SIH/AIH",
    orgao: "DataSUS/MS",
    traz: "internações, permanência, custo aprovado, HSMR e fluxo entre municípios",
    observacao:
      "Só a rede SUS. A unidade é a AIH, não a pessoa nem o episódio — internação longa gera mais de uma AIH.",
  },
  {
    id: "sinan",
    nome: "Dengue e arboviroses",
    sistema: "SINAN",
    orgao: "DataSUS/MS",
    traz: "casos notificados por município e semana epidemiológica",
    observacao:
      "Notificação não é incidência. As semanas mais recentes sobem com o atraso de digitação.",
  },
  {
    id: "sifilis",
    nome: "Sífilis",
    sistema: "SINAN",
    orgao: "DataSUS/MS",
    traz:
      "sífilis adquirida, em gestante e congênita por município de residência, com o que houve "
      + "com a mãe do caso congênito: pré-natal, momento do diagnóstico e tratamento",
    observacao:
      "Toda a sífilis do SINAN é PRELIMINAR: não há SIFA/SIFG/SIFC em DADOS/FINAIS, nem para "
      + "2007 — dezenove anos que nunca foram promovidos. O último ano cobre só metade: os "
      + "arquivos de 2025 param em junho, e a coluna meses_cobertos carimba isso linha a "
      + "linha. A defasagem é estrutural — foram reescritos em 30/06/2026 e mesmo assim não "
      + "passam de junho de 2025, enquanto a dengue do mesmo diretório já cobre 2026. A "
      + "sífilis adquirida só passou a ser de notificação compulsória em 2010, e os primeiros "
      + "anos medem a implantação da notificação, não a doença. A taxa por mil nascidos vivos "
      + "existe só em 2021–2024, onde há denominador.",
  },
  {
    id: "sinasc",
    nome: "Nascimentos",
    sistema: "SINASC",
    orgao: "DataSUS/MS",
    traz: "nascidos vivos, peso, prematuridade, pré-natal e mortalidade infantil",
    observacao:
      "Denominador da mortalidade infantil; o ano definitivo sai depois do ano do SIM correspondente.",
  },
  {
    id: "pni",
    nome: "Vacinação",
    sistema: "PNI/RNDS",
    orgao: "OpenDataSUS/MS",
    traz: "doses aplicadas por imunobiológico, e cobertura por UF",
    observacao:
      "É a série mais atual da base. Cobertura vacinal MUNICIPAL foi testada e reprovada por viés de denominador — por isso só existe por UF. As doses de influenza de 2023 estão incompletas no registro nacional.",
  },
  {
    id: "aps",
    nome: "Atenção primária",
    sistema: "e-Gestor AB",
    orgao: "SAPS/MS",
    traz: "cobertura populacional estimada de equipes de saúde da família",
    observacao:
      "Cobertura potencial, calculada por parâmetro de população por equipe — não é atendimento medido.",
  },
  {
    id: "cnes",
    nome: "Estrutura e leitos",
    sistema: "CNES",
    orgao: "DataSUS/MS",
    traz: "estabelecimentos e leitos por tipo, incluindo UTI e leitos SUS",
    observacao:
      "Cadastro, não funcionamento: leito cadastrado não prova leito em operação.",
  },
  {
    id: "siops",
    nome: "Gasto público em saúde",
    sistema: "SIOPS",
    orgao: "MS",
    traz: "despesa municipal em saúde, por habitante e por fonte",
    observacao:
      "Declaratório e sujeito a retificação pelo próprio município.",
  },
  {
    id: "ans",
    nome: "Saúde suplementar",
    sistema: "ANS",
    orgao: "ANS",
    traz: "beneficiários de plano médico-hospitalar por município",
    observacao:
      "Vínculos, não pessoas: quem tem dois planos conta duas vezes.",
  },
  {
    id: "ibge",
    nome: "População e contexto social",
    sistema: "IBGE",
    orgao: "IBGE",
    traz: "denominadores populacionais, Censo 2022 e proxy de vulnerabilidade",
    observacao:
      "O Censo é de 2022 e não se atualiza todo ano; os demais anos são estimativa ou interpolação.",
  },
  {
    id: "oncologia",
    nome: "Oncologia",
    sistema: "Painel Oncologia",
    orgao: "DataSUS/MS",
    traz: "prazo entre diagnóstico e início do tratamento de câncer, por município de residência",
    observacao:
      "A proporção sem tratamento registrado NÃO é comparável entre anos: o ano recente é "
      + "censurado (o tratamento pode ocorrer depois do corte do arquivo) e o Painel mudou de "
      + "escopo em 2018, quando os casos saltaram de 196 mil para 352 mil.",
  },
  {
    id: "siasus",
    nome: "Tratamento oncológico (APAC)",
    sistema: "SIA/SUS",
    orgao: "DataSUS/MS",
    traz:
      "autorizações de quimioterapia e radioterapia por município de residência, "
      + "ano, CID-3 e estadiamento — e o fluxo de quem se trata fora do próprio município",
    observacao:
      "A unidade é a APAC, NÃO a pessoa. Uma autorização é tipicamente mensal, então "
      + "paciente em quimioterapia contínua gera várias por ano, e o identificador de "
      + "pessoa vem criptografado na fonte: qualquer leitura per capita sobre esta tabela "
      + "está errada. Esta fonte também NÃO mede o prazo da Lei dos 60 Dias — a subtração "
      + "entre as datas disponíveis produz uma manchete falsa, e por isso prazo não é "
      + "publicado aqui. Estadiamento ausente tem rótulo próprio (\"ignorado\", ~12% das "
      + "APACs) e nunca é somado ao estádio 0, que é carcinoma in situ — um diagnóstico "
      + "real e precoce. Não compare com o Painel de Oncologia: lá se contam CASOS de "
      + "pessoas, com 51% de estadiamento ausente. 2026 tem SETE meses publicados; a "
      + "coluna meses_cobertos carimba isso em cada linha.",
  },
  {
    id: "rhc",
    nome: "Registro Hospitalar de Câncer",
    sistema: "IntegradorRHC",
    orgao: "INCA/MS",
    traz:
      "casos de câncer com confirmação histopatológica por município de residência, "
      + "ano da primeira consulta, CID-3 e estadiamento — e o tempo até o primeiro "
      + "tratamento de QUALQUER modalidade, que é o que a Lei dos 60 Dias conta",
    observacao:
      "A unidade é a PESSOA, e é a única fonte oncológica do projeto em que isso vale "
      + "na origem — a APAC conta autorização. Três armadilhas viajam com o número. "
      + "Primeira: o ano é o da PRIMEIRA CONSULTA no hospital, não o do diagnóstico, e "
      + "os dois divergem em ~22% dos registros. Segunda: caso analítico e não analítico "
      + "são universos diferentes (o não analítico chegou com diagnóstico E tratamento "
      + "feitos fora), e por isso tipo_caso é coluna de chave, não filtro escondido. "
      + "Terceira: estadiamento ausente é ~53% dos registros, tem rótulo próprio "
      + "(\"ignorado\") e nunca é somado ao estádio 0. O RHC se enche ao longo de anos, "
      + "então os anos mais recentes vêm incompletos — a coluna ano_incompleto carimba "
      + "isso em cada linha, e 2023 traz 15 UFs contra 26.",
  },
  {
    id: "sisagua",
    nome: "Qualidade da água",
    sistema: "SISAGUA",
    orgao: "API de Dados Abertos/MS",
    traz:
      "volume e regularidade das análises de água por município, ano e parâmetro "
      + "(turbidez, coliformes, cor, cloro, E. coli, pH, fluoreto e mais três)",
    observacao:
      "NÃO é potabilidade: é quanto se analisou, e conformidade só onde a própria fonte "
      + "declara o limiar. Município que não analisa aparece na fonte como AUSÊNCIA, e "
      + "ausência de análise é o oposto de água comprovada — é a falta da prova. Por isso "
      + "município-ano sem dado não vira linha zerada, e existe a tabela de cobertura ao "
      + "lado, com uma linha para cada um dos 5.571 municípios: sem ela não há como "
      + "distinguir “não analisou” de “não foi coletado”. São 336 municípios (6,0%) que "
      + "responderam à API sem nenhum registro entre 2014 e 2026 — PI 92, MA 58, PA 52. "
      + "Cuidado ao agrupar cloro por faixa: o rótulo “>= 2,0 mg/L e <= 5,0mg/L” só "
      + "aparece a partir de 2023 ao lado do “> 2,0 mg/L” que cobre a série inteira, e "
      + "somar os dois como rótulos distintos inventa uma quebra de série em 2023.",
  },
  {
    id: "siscan",
    nome: "Rastreamento de câncer",
    sistema: "SISCAN",
    orgao: "DataSUS/MS",
    traz:
      "exames de rastreamento de colo de útero e mama por município e ano de "
      + "competência — histopatológico de colo, histopatológico de mama e citopatológico de mama",
    observacao:
      "São TRÊS das cinco visões do SISCAN, e a que falta é a maior. O citopatológico de "
      + "colo (o exame de Papanicolau, o de maior volume do rastreamento) fica de fora "
      + "porque a fonte só oferece nele o ano de LIBERAÇÃO DO RESULTADO, não o de "
      + "competência: é outro eixo temporal, e somá-lo a estes três produziria uma série "
      + "que mistura quando o exame foi feito com quando o laudo saiu. Não leia estes "
      + "números como cobertura de rastreamento: o denominador é a população-alvo, que "
      + "esta tabela não traz, e exame registrado não é pessoa rastreada — a mesma pessoa "
      + "pode aparecer mais de uma vez no ano. 2013 é o ano de implantação do sistema e "
      + "tem volume baixo por isso, não por queda de rastreamento.",
  },
  {
    id: "convenios",
    nome: "Convênios federais",
    sistema: "Portal da Transparência",
    orgao: "CGU",
    traz:
      "convênios federais da função Saúde por município do convenente, ano e tipo "
      + "de entidade, com valor pactuado, valor liberado e contrapartida",
    observacao:
      "O município é o da SEDE DE QUEM ASSINOU, não o destino do dinheiro — e isso "
      + "domina o ranking, não é caso de borda. Brasília aparece com R$ 32,2 bi, 45% "
      + "de todo o valor do país, porque 90 dos 91 convênios com organizações "
      + "internacionais estão registrados lá e executam programas nacionais; e "
      + "Dourados (MS), com 200 mil habitantes, aparece com R$ 4,5 bi, que são 37 "
      + "convênios da Missão Evangélica Caiuá, operadora de saúde indígena em vários "
      + "estados. Leia a coluna como “valor comprometido com entidades sediadas neste "
      + "município”. Segunda ressalva: valor PACTUADO não é dinheiro entregue — o "
      + "valor liberado viaja ao lado e a execução nacional é de 77,9%. O recorte é a "
      + "função 10 (Saúde) da classificação SIAFI, e o ano é o de início da vigência: "
      + "convênio é plurianual, então somar por ano descreve quando se ASSINOU, não "
      + "quando se gastou.",
  },
  {
    id: "derivado",
    nome: "Análises derivadas",
    sistema: "—",
    orgao: "Saúde em Dado",
    traz: "estratos, perfis, correlações e dimensões de apoio calculadas sobre as fontes acima",
    observacao:
      "Não são coleta: saem dos marts anteriores. A competência é a das fontes que as originam.",
  },
];

/**
 * Tabela → fonte. Escrito à mão de propósito: o nome da tabela não determina a
 * fonte com segurança (`mart_leitos_icsap_municipio` cruza CNES e SIH), e uma
 * regra por prefixo classificaria errado em silêncio, que é pior que não
 * classificar.
 */
export const FONTE_DA_TABELA: Record<string, string> = {
  mart_oncologia_municipio: "oncologia",
  // SIM
  mart_mortalidade_municipio: "sim",
  mart_mortalidade_uf_mes: "sim",
  mart_mortalidade_causa: "sim",
  mart_mortalidade_causa_municipio: "sim",
  mart_mortalidade_causa_municipio_faixa: "sim",
  mart_mortalidade_causa_municipio_mes: "sim",
  mart_excesso_uf_mes: "sim",
  mart_qualidade_registro_municipio: "sim",
  mart_anomalia_causa_municipio: "sim",
  // SIH
  mart_internacoes_municipio: "sih",
  mart_internacoes_agravo: "sih",
  mart_internacoes_hospital: "sih",
  mart_icsap_municipio: "sih",
  mart_icsap_pares: "sih",
  mart_fluxo_intermunicipal: "sih",
  mart_hsmr_hospital: "sih",
  mart_los_hospital: "sih",
  mart_demanda_mensal_hospital: "sih",
  mart_forecast_demanda_hospital: "sih",
  // SINAN
  mart_dengue_municipio_ano: "sinan",
  mart_dengue_semana: "sinan",
  mart_dengue_uf_semana: "sinan",
  mart_sinan_agravo_municipio: "sinan",
  mart_sinan_agravo_cobertura: "sinan",
  mart_sifilis_municipio: "sifilis",
  // SINASC
  mart_natalidade_municipio: "sinasc",
  mart_mortalidade_infantil_uf: "sinasc",
  // PNI
  mart_vacinacao_uf_mes: "pni",
  mart_vacinacao_municipio: "pni",
  mart_cobertura_vacinal_uf: "pni",
  // APS
  mart_cobertura_aps_municipio: "aps",
  mart_cobertura_icsap_municipio: "aps",
  mart_equidade_aps_municipio: "aps",
  // CNES
  mart_cnes_municipio: "cnes",
  mart_leitos_municipio: "cnes",
  mart_leitos_icsap_municipio: "cnes",
  mart_vazio_assistencial_municipio: "cnes",
  // SIOPS
  mart_siops_municipio: "siops",
  mart_siops_icsap_municipio: "siops",
  // ANS
  mart_saude_suplementar_municipio: "ans",
  mart_saude_suplementar_icsap_municipio: "ans",
  // Convênios federais
  mart_convenios_municipio: "convenios",
  mart_convenios_cobertura: "convenios",
  // SISCAN
  mart_siscan_municipio: "siscan",
  mart_siscan_cobertura: "siscan",
  // SIA/SUS — APAC oncológica
  mart_apac_oncologia_tratamento: "siasus",
  mart_apac_oncologia_fluxo: "siasus",
  mart_apac_oncologia_cobertura: "siasus",
  // SISAGUA
  mart_sisagua_municipio: "sisagua",
  mart_sisagua_cobertura: "sisagua",
  // IBGE
  dim_populacao: "ibge",
  dim_pop_faixa: "ibge",
  dim_pop_padrao: "ibge",
  dim_ivs: "ibge",
  dim_municipio: "ibge",
  mart_contexto_social_municipio: "ibge",
  // Derivadas e dimensões de apoio
  dim_cid10_capitulo: "derivado",
  dim_cid10_categoria: "derivado",
  dim_cid10_informativo: "derivado",
  dim_cluster_municipio: "derivado",
  mart_perfil_mortalidade_municipio: "derivado",
  mart_correlacao_causas: "derivado",
};

/**
 * Tabelas cuja competência é HORIZONTE DE PROJEÇÃO, não cobertura observada.
 *
 * `mart_forecast_demanda_hospital` vai de 2025-01 a 2025-03 porque é o que ele
 * PREVÊ — o SIH observado para em 2024. Somada à cobertura da fonte, essa
 * competência fazia o painel anunciar que o dado de internações ia até
 * março de 2025, que é o oposto do que o painel existe para dizer.
 *
 * Pego na verificação em navegador, depois de a derivação já estar pronta:
 * derivar do manifesto elimina o número copiado, não a pergunta sobre o que o
 * número significa.
 */
export const HORIZONTE_DE_PROJECAO = new Set(["mart_forecast_demanda_hospital"]);

export function fonte(id: string): Fonte | null {
  return FONTES.find((f) => f.id === id) ?? null;
}
