/**
 * O catálogo de indicadores — uma definição por número exibido.
 *
 * POR QUE ELE EXISTE
 * ------------------
 * A documentação deste projeto é boa e está no lugar errado para quem consulta:
 * quem vê "920,0" num cartão precisa saber o que é o numerador, qual é o
 * denominador, de que ano é o dado e o que ele não pode afirmar — e para isso
 * tinha de sair da página, abrir a metodologia e achar a seção certa entre
 * vinte e quatro. Contexto que exige navegação é contexto que não é lido.
 *
 * A ficha resolve isso montando o que JÁ EXISTE, não escrevendo de novo:
 *
 *   definição, numerador, denominador   aqui (é editorial, escrito à mão)
 *   competência, linhas, versão, SHA    `sdata/manifesto.json`, do manifesto
 *                                       de publicação em `data/publicacoes/`
 *   seção da metodologia                `lib/metodologia-secoes.ts`
 *   situação preliminar                 `ehPreliminar` de `lib/api.ts`
 *
 * Nenhum campo é digitado duas vezes. O que muda quando o dado muda —
 * competência, contagem, versão — vem do manifesto e se atualiza sozinho no
 * build; o que só muda quando a METODOLOGIA muda fica escrito aqui.
 *
 * A GUARDA QUE IMPEDE ISTO DE ENVELHECER
 * ---------------------------------------
 * `lib/indicadores.test.mts` confere que toda tabela citada existe no manifesto
 * publicado e que todo slug de metodologia existe em `SECOES`. Sem isso, o
 * catálogo apontaria para uma tabela removida ou uma seção renomeada e a ficha
 * mostraria "—" em silêncio — que é pior que não ter ficha, porque parece
 * informação.
 */
export interface Indicador {
  /** Identificador estável — entra na URL da âncora e em citação. */
  id: string;
  /** Como o número aparece na tela. */
  rotulo: string;
  unidade: string;
  /** Uma frase: o que o número mede. */
  definicao: string;
  /** O que é contado em cima. */
  numerador: string;
  /** O que divide. `null` quando o indicador é contagem, não razão. */
  denominador: string | null;
  /**
   * A tabela publicada de onde o número sai. É a chave que liga o catálogo ao
   * manifesto — competência, versão e checksum vêm dela.
   */
  tabela: string;
  /** Slug da seção da metodologia que detalha o método. */
  secao: string;
  /**
   * O que este indicador NÃO permite afirmar. É o campo mais importante da
   * ficha: a página dos limites foi o que mais construiu confiança no material
   * impresso do projeto, e aqui ela fica ao lado do número em vez de a três
   * cliques dele.
   */
  limitacoes: string[];
}

export const INDICADORES: Indicador[] = [
  {
    id: "obitos",
    rotulo: "Óbitos registrados",
    unidade: "óbitos",
    definicao:
      "Contagem de óbitos não fetais registrados no SIM, atribuídos ao município de residência declarado na Declaração de Óbito.",
    numerador: "Óbitos com TIPOBITO diferente de fetal, no ano e no município de residência",
    denominador: null,
    tabela: "mart_mortalidade_municipio",
    secao: "criterios-de-inclusao-e-derivacoes",
    limitacoes: [
      "É registro, não ocorrência: óbito não notificado não aparece, e o atraso de registro deixa os meses mais recentes incompletos.",
      "A residência é a declarada no óbito, que pode diferir de onde a pessoa morava de fato.",
      "Óbito fetal não entra — ele vive em outro arquivo do SIM, que este projeto não coleta.",
    ],
  },
  {
    id: "taxa-bruta",
    rotulo: "Taxa bruta de mortalidade",
    unidade: "óbitos por 100 mil habitantes",
    definicao:
      "Óbitos do ano divididos pela população residente, sem qualquer ajuste — é a frequência observada, não o risco comparável.",
    numerador: "Óbitos não fetais do município no ano",
    denominador: "População residente estimada do município no mesmo ano (IBGE)",
    tabela: "mart_mortalidade_municipio",
    secao: "intervalos-de-confianca-ic95",
    limitacoes: [
      "Não é comparável entre municípios: uma cidade envelhecida tem taxa bruta maior sem que ninguém adoeça mais. Para comparar, use a padronizada.",
      "Em município pequeno a taxa oscila muito de um ano para o outro por acaso — leia sempre com o IC95%.",
    ],
  },
  {
    id: "taxa-padronizada",
    rotulo: "Taxa padronizada por idade",
    unidade: "óbitos por 100 mil habitantes",
    definicao:
      "Taxa que o município teria se sua população tivesse a estrutura etária do Brasil no Censo 2022 — é o que torna dois municípios comparáveis.",
    numerador: "Óbitos por faixa etária, reponderados pelo padrão Brasil/Censo 2022 (método direto)",
    denominador: "População do padrão, por faixa etária",
    tabela: "mart_mortalidade_municipio",
    secao: "taxa-padronizada-por-idade",
    limitacoes: [
      "Só existe para o total de causas: a padronização por capítulo da CID-10 exigiria denominador por faixa e capítulo, que a base não serve.",
      "É um número construído, não observado — não diz quantas pessoas morreram, diz quantas morreriam sob uma estrutura etária hipotética.",
      "Faixas etárias largas deixam resíduo de confundimento por idade dentro de cada faixa.",
    ],
  },
  {
    id: "icsap-pct",
    rotulo: "Internações por causas sensíveis à atenção primária (ICSAP)",
    unidade: "% das internações",
    definicao:
      "Participação, no total de internações do município, daquelas por condições que a atenção primária poderia ter evitado, segundo a Lista Brasileira de ICSAP.",
    numerador: "AIHs aprovadas com diagnóstico principal na Lista Brasileira de ICSAP",
    denominador: "AIHs aprovadas do município no mesmo ano",
    tabela: "mart_icsap_municipio",
    secao: "internacoes-evitaveis-icsap-e-fluxo-de-pacientes",
    limitacoes: [
      "O indicador responde à oferta hospitalar: este projeto mediu que leito local quase dobra a ICSAP sem alterar a mortalidade padronizada. Municípios de portes diferentes não se comparam por ele.",
      "A unidade é a AIH, não a pessoa nem o episódio — uma internação longa pode gerar mais de uma AIH.",
      "Serve para acompanhar o mesmo município ao longo do tempo, não para ranquear municípios entre si.",
    ],
  },
  {
    id: "hsmr",
    rotulo: "Mortalidade hospitalar ajustada (HSMR)",
    unidade: "razão observado/esperado",
    definicao:
      "Razão entre os óbitos observados no hospital e os que seriam esperados dado o perfil de idade e diagnóstico dos seus pacientes (padronização indireta).",
    numerador: "Óbitos hospitalares observados no CNES no ano",
    denominador: "Óbitos esperados, somando as taxas nacionais por estrato de idade e diagnóstico",
    tabela: "mart_hsmr_hospital",
    secao: "mortalidade-ajustada-hsmr-permanencia-esperada-e-projecao-de-demanda",
    limitacoes: [
      "Não é um veredito de qualidade assistencial, e a lista não é um ranking: o IC95% de cada hospital diz quantos sequer diferem do esperado.",
      "Depende da codificação do diagnóstico na AIH — hospital que codifica com mais gravidade tem esperado maior e HSMR menor.",
      "Hospital com poucos óbitos esperados tem estimativa instável; esses são sinalizados, não ocultados.",
      "Não inclui óbito ocorrido após a alta.",
    ],
  },
  {
    id: "imunopreveniveis-g1",
    rotulo: "Internações por doença prevenível por vacina (grupo 1 da ICSAP)",
    unidade: "internações por 100 mil habitantes",
    definicao:
      "Internações por doenças imunopreveníveis e condições sensíveis, o primeiro grupo da Lista Brasileira de ICSAP.",
    numerador: "AIHs aprovadas com diagnóstico principal no grupo 1 da Lista Brasileira de ICSAP",
    denominador: "População residente do município no ano",
    tabela: "mart_icsap_municipio",
    secao: "internacoes-evitaveis-icsap-e-fluxo-de-pacientes",
    limitacoes: [
      "O grupo é raro: em município de porte médio, contagens de um dígito são o resultado esperado, e a taxa oscila muito.",
      "Não mede cobertura vacinal do município. Cobertura vacinal municipal foi testada neste projeto e reprovada por viés de denominador.",
      "Internação, não óbito — e o instrumento oficial de mortes evitáveis por vacina cobre outro conjunto de causas.",
    ],
  },
  {
    id: "ivs-proxy",
    rotulo: "Vulnerabilidade social (proxy)",
    unidade: "escore 0–100",
    definicao:
      "Índice construído a partir de duas variáveis do Censo 2022 — analfabetismo em 15 anos ou mais e domicílios sem água encanada — combinadas por z-score.",
    numerador: "z-score de analfabetismo + z-score de falta de água, reescalado para 0–100",
    denominador: null,
    tabela: "dim_ivs",
    secao: "vulnerabilidade-social-proxy-censo-2022",
    limitacoes: [
      "NÃO é o IVS oficial do IPEA, que usa outras dimensões e outro método — os valores não são intercambiáveis.",
      "É de 2022 e não se atualiza anualmente; comparar com um indicador de saúde de outro ano compara períodos diferentes.",
      "Associação entre vulnerabilidade e saúde aqui é municipal e agregada: descreve padrão, não risco individual (falácia ecológica).",
    ],
  },
];

const PORID = new Map(INDICADORES.map((i) => [i.id, i]));

/** O indicador pelo id; lança se o id não existir, para o erro aparecer no build. */
export function indicador(id: string): Indicador {
  const i = PORID.get(id);
  if (!i) throw new Error(`indicador desconhecido: ${id}`);
  return i;
}
