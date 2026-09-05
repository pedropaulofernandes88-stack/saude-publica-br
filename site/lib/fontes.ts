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
