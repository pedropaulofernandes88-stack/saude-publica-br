// ---------------------------------------------------------------------------
// Paginação
// ---------------------------------------------------------------------------
export interface PaginacaoMeta {
  total: number;
  pagina: number;
  tamanho: number;
  paginas: number;
}

// ---------------------------------------------------------------------------
// Internações (SIH)
// ---------------------------------------------------------------------------
export interface InternacoesItem {
  municipio_cod: string;
  municipio_nome: string;
  uf_sigla: string;
  regiao: string;
  mes_competencia: string; // "YYYY-MM"
  ano_cmpt: number;
  mes_cmpt: number;
  diag_cap: string;
  diag_grupo: string;
  sexo: string;
  faixa_etaria: string;
  car_int_grupo: string;
  total_internacoes: number;
  total_obitos_internados: number;
  dias_perm_total: number;
  dias_perm_medio: number;
  val_tot_total: number;
  val_tot_medio: number;
  populacao: number | null;
  taxa_internacao: number | null;
  taxa_mortalidade_intra: number | null;
}

export interface InternacoesResponse {
  data: InternacoesItem[];
  meta: PaginacaoMeta;
}

export interface InternacoesSerieItem {
  mes_competencia: string;
  ano_cmpt: number;
  mes_cmpt: number;
  total_internacoes: number;
  taxa_internacao: number | null;
  taxa_mortalidade_intra: number | null;
  dias_perm_medio: number;
}

export interface InternacoesSerieResponse {
  municipio_cod: string;
  municipio_nome: string;
  uf_sigla: string;
  serie: InternacoesSerieItem[];
}

export type RankingMetrica = "taxa_internacao" | "taxa_mortalidade_intra";
export type RankingOrdem = "desc" | "asc";

export interface RankingItem {
  municipio_cod: string;
  municipio_nome: string;
  uf_sigla: string;
  regiao: string;
  ano_cmpt: number;
  taxa_internacao: number | null;
  taxa_mortalidade_intra: number | null;
  total_internacoes: number;
  populacao: number | null;
}

// ---------------------------------------------------------------------------
// Mortalidade (SIM)
// ---------------------------------------------------------------------------
export interface MortalidadeItem {
  municipio_cod: string;
  municipio_nome: string;
  uf_sigla: string;
  regiao: string;
  ano_obito: number;
  mes_obito: number | null;
  mes_competencia: string | null;
  causa_cap: string;
  causa_grupo: string;
  sexo: string;
  faixa_etaria: string;
  total_obitos: number;
  populacao: number | null;
  taxa_mortalidade: number | null;
}

export interface MortalidadeResponse {
  data: MortalidadeItem[];
  meta: PaginacaoMeta;
}

export interface MortalidadeSerieItem {
  ano_obito: number;
  mes_obito: number | null;
  total_obitos: number;
  taxa_mortalidade: number | null;
}

export interface MortalidadeSerieResponse {
  municipio_cod: string;
  municipio_nome: string;
  uf_sigla: string;
  serie: MortalidadeSerieItem[];
}

// ---------------------------------------------------------------------------
// Produção ambulatorial (SIA)
// ---------------------------------------------------------------------------
export interface ProducaoItem {
  municipio_cod: string;
  municipio_nome: string;
  uf_sigla: string;
  mes_competencia: string;
  ano_cmpt: number;
  mes_cmpt: number;
  grupo_procedimento: string;
  total_procedimentos: number;
  valor_total: number;
}

export interface ProducaoResponse {
  data: ProducaoItem[];
  meta: PaginacaoMeta;
}

// ---------------------------------------------------------------------------
// Epidemiologia / CID-10
// ---------------------------------------------------------------------------
export interface EpidemiologiaItem {
  municipio_cod: string;
  municipio_nome: string;
  uf_sigla: string;
  mes_competencia: string;
  cid10_cap: string;
  cid10_grupo: string;
  total_casos: number;
  taxa_incidencia: number | null;
}

export interface EpidemiologiaResponse {
  data: EpidemiologiaItem[];
  meta: PaginacaoMeta;
}

// ---------------------------------------------------------------------------
// Anomalias
// ---------------------------------------------------------------------------
export type AnomaliasSeveridade = "baixa" | "media" | "alta" | "critica";

export interface AnomaliaItem {
  municipio_cod: string;
  municipio_nome: string;
  uf_sigla: string;
  mes_competencia: string;
  metrica: string;
  valor_observado: number;
  valor_esperado: number;
  desvio_padrao: number;
  z_score: number;
  severidade: AnomaliasSeveridade;
}

export interface AnomaliaResponse {
  data: AnomaliaItem[];
  meta: PaginacaoMeta;
}

// ---------------------------------------------------------------------------
// GeoJSON para Deck.gl
// ---------------------------------------------------------------------------
export interface MunicipioFeatureProperties {
  CD_MUN: string;
  NM_MUN: string;
  SIGLA_UF: string;
  valor?: number | null;
}

// ---------------------------------------------------------------------------
// Helpers de parâmetros de query
// ---------------------------------------------------------------------------
export interface InternacoesParams {
  pagina?: number;
  tamanho?: number;
  uf_sigla?: string;
  municipio_cod?: string;
  ano?: number;
  mes?: number;
  diag_cap?: string;
}

export interface RankingParams {
  uf_sigla?: string;
  ano?: number;
  metrica?: RankingMetrica;
  ordem?: RankingOrdem;
  top?: number;
}

export interface MortalidadeParams {
  pagina?: number;
  tamanho?: number;
  uf_sigla?: string;
  municipio_cod?: string;
  ano?: number;
  causa_cap?: string;
}
