/**
 * Classificação de linhas municipais vindas do SIM/DataSUS.
 *
 * Quando o óbito é registrado sem identificação do município, o DataSUS o
 * atribui a um código agregado "UF + 0000" (110000, 350000, 330000…). Essas
 * linhas chegam do mart com `municipio_nome` nulo e `uf_sigla` igual a "ND".
 * Elas NÃO são municípios: em 2024, `mart_mortalidade_municipio` devolve 5.593
 * linhas para o Brasil, das quais 23 são códigos agregados somando 1.900
 * óbitos — os municípios de fato nomeados são 5.570.
 *
 * Contá-las como município inflava o KPI do painel ("5.593 municípios com
 * registro") e podia empurrá-las para rankings, boletins e CSV exportado.
 * Toda superfície que conta, ordena ou exporta município deve passar por aqui.
 */

/** Sigla que o mart usa quando a UF do município não pôde ser determinada. */
export const UF_NAO_IDENTIFICADA = "ND";

/**
 * Total de municípios brasileiros segundo o IBGE (malha 2022 + Boa Esperança
 * do Norte/MT). Teto absoluto: nenhum recorte pode ter mais municípios
 * nomeados do que isso — se tiver, entrou lixo na contagem.
 */
export const TOTAL_MUNICIPIOS_IBGE = 5571;

/** Código agregado de UF: dois dígitos da UF seguidos de "0000". */
export function ehCodigoAgregado(municipioCod: string): boolean {
  return /^\d{2}0000$/.test(municipioCod);
}

/** Forma mínima que a classificação exige — o mart devolve bem mais colunas. */
export interface LinhaMunicipal {
  municipio_cod: string;
  municipio_nome: string | null;
  uf_sigla: string;
  obitos: number;
}

/**
 * Só é município quem tem código real, UF conhecida e nome. Os três testes são
 * redundantes por segurança: se o mart mudar a convenção de um deles, os outros
 * dois seguram.
 */
export function municipioIdentificado(m: LinhaMunicipal): boolean {
  return (
    !ehCodigoAgregado(m.municipio_cod) &&
    m.uf_sigla !== UF_NAO_IDENTIFICADA &&
    m.municipio_nome != null &&
    m.municipio_nome !== ""
  );
}

export interface ParticaoMunicipios<T> {
  /** Municípios de verdade — o que pode ser contado, ordenado e exportado. */
  identificados: T[];
  /** Códigos agregados: preservados para poder ser reportados, nunca contados. */
  naoIdentificados: T[];
  /** Óbitos que existem mas não têm município — precisam aparecer na tela. */
  obitosNaoIdentificados: number;
}

/**
 * Separa municípios reais de códigos agregados sem perder nenhuma linha: o
 * total de óbitos continua fechando, só deixa de ser atribuído a município.
 */
export function particionarMunicipios<T extends LinhaMunicipal>(
  linhas: readonly T[],
): ParticaoMunicipios<T> {
  const identificados: T[] = [];
  const naoIdentificados: T[] = [];
  for (const l of linhas) {
    if (municipioIdentificado(l)) identificados.push(l);
    else naoIdentificados.push(l);
  }
  return {
    identificados,
    naoIdentificados,
    obitosNaoIdentificados: naoIdentificados.reduce((s, l) => s + (l.obitos ?? 0), 0),
  };
}
