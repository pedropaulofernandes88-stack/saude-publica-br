/**
 * Cliente PostgREST (Supabase) — somente leitura, chave pública.
 *
 * A anon key é pública por design: o banco aceita apenas SELECT (RLS).
 * Paginação por offset exige ordenação determinística (Supabase limita
 * cada resposta a 1000 linhas).
 */

export const SUPABASE_URL =
  process.env.NEXT_PUBLIC_SUPABASE_URL ??
  "https://zekjhmxjamatlxpkykde.supabase.co";

export const SUPABASE_ANON_KEY =
  process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY ??
  "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Inpla2pobXhqYW1hdGx4cGt5a2RlIiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODEwNzY4MzIsImV4cCI6MjA5NjY1MjgzMn0.px8FcU0QK8w9v95kwGlGzASKpY3drsxAvFe0e6wUoCU";

const PAGE = 1000;

export async function rest<T = Record<string, unknown>>(
  table: string,
  params: Record<string, string>,
  maxRows = 100_000,
): Promise<T[]> {
  const rows: T[] = [];
  let offset = 0;
  while (rows.length < maxRows) {
    const qs = new URLSearchParams(params).toString();
    const res = await fetch(`${SUPABASE_URL}/rest/v1/${table}?${qs}`, {
      headers: {
        apikey: SUPABASE_ANON_KEY,
        Authorization: `Bearer ${SUPABASE_ANON_KEY}`,
        "Range-Unit": "items",
        Range: `${offset}-${offset + PAGE - 1}`,
      },
    });
    if (!res.ok) {
      throw new Error(`API ${table}: HTTP ${res.status} — ${await res.text()}`);
    }
    const chunk = (await res.json()) as T[];
    rows.push(...chunk);
    if (chunk.length < PAGE) break;
    offset += PAGE;
  }
  return rows;
}

// ── Tipos das tabelas publicadas ─────────────────────────────────────────────

export interface SerieMensal {
  mes_competencia: string;
  uf_sigla: string;
  obitos: number;
}

export interface LinhaUfMes {
  uf_sigla: string;
  ano: number;
  mes: number;
  mes_competencia: string;
  capitulo_cid: string;
  sexo: string;
  faixa_etaria: string;
  obitos: number;
}

export interface LinhaMunicipio {
  municipio_cod: string;
  municipio_nome: string | null;
  uf_sigla: string;
  regiao: string | null;
  ano: number;
  capitulo_cid: string;
  sexo: string;
  obitos: number;
  obitos_hospital: number | null;
  obitos_domicilio: number | null;
  populacao: number | null;
  taxa_obitos_100k: number | null;
  taxa_padronizada_100k: number | null;
  ic95_inf: number | null;
  ic95_sup: number | null;
}

export interface LinhaExcesso {
  uf_sigla: string;
  ano: number;
  mes_competencia: string;
  obitos: number;
  esperado: number;
  excesso: number;
  pct_excesso: number | null;
}

export interface SerieTotalItem {
  uf_sigla: string;
  ano: number;
  mes_competencia: string;
  obitos: number;
}

export interface DengueSemana {
  municipio_cod: string;
  municipio_nome: string | null;
  uf_sigla: string;
  ano_epi: number;
  semana_epi: number;
  casos_provaveis: number;
  casos_graves: number;
  obitos: number;
}

export interface DengueAno {
  municipio_cod: string;
  municipio_nome: string | null;
  uf_sigla: string;
  regiao: string | null;
  ano_epi: number;
  casos_provaveis: number;
  casos_graves: number;
  obitos: number;
  populacao: number | null;
  incidencia_100k: number | null;
  letalidade_pct: number | null;
}

export interface Internacao {
  municipio_cod: string;
  municipio_nome: string | null;
  uf_sigla: string;
  regiao: string | null;
  ano: number;
  capitulo_cid: string;
  internacoes: number;
  obitos: number;
  dias_permanencia: number;
  valor_total: number;
  aih_continuacao: number | null;
  aih_normal: number | null;
  dias_permanencia_normal: number | null;
  valor_normal: number | null;
  permanencia_media: number | null;
  mortalidade_pct: number | null;
  custo_medio: number | null;
  internacoes_100k: number | null;
  populacao: number | null;
}

export interface InternacaoAgravo {
  municipio_cod: string;
  municipio_nome: string | null;
  uf_sigla: string;
  regiao: string | null;
  ano: number;
  agravo: string;
  agravo_label: string | null;
  grupo: string | null;
  internacoes: number;
  obitos: number;
  dias_permanencia: number;
  valor_total: number;
  aih_continuacao: number | null;
  aih_normal: number | null;
  dias_permanencia_normal: number | null;
  valor_normal: number | null;
  permanencia_media: number | null;
  mortalidade_pct: number | null;
  custo_medio: number | null;
  populacao: number | null;
  internacoes_100k: number | null;
}

export interface InternacaoHospital {
  cnes: string;
  municipio_cod: string;
  municipio_nome: string | null;
  uf_sigla: string;
  regiao: string | null;
  ano: number;
  capitulo_principal: string | null;
  internacoes: number;
  obitos: number;
  dias_permanencia: number;
  valor_total: number;
  aih_continuacao: number | null;
  aih_normal: number | null;
  dias_permanencia_normal: number | null;
  valor_normal: number | null;
  permanencia_media: number | null;
  mortalidade_pct: number | null;
  custo_medio: number | null;
}

export interface CoberturaApsMunicipio {
  municipio_cod: string;
  municipio_nome: string | null;
  uf_sigla: string;
  regiao: string | null;
  ano: number;
  mes: number;
  mes_competencia: string;
  populacao: number | null;
  qt_esf: number | null;
  qt_eap20: number | null;
  qt_eap30: number | null;
  qt_esfr: number | null;
  qt_ecr: number | null;
  qt_eapp20: number | null;
  qt_eapp30: number | null;
  capacidade_equipe: number | null;
  cobertura_pct: number | null;
}

export interface EquidadeApsMunicipio {
  municipio_cod: string;
  municipio_nome: string | null;
  uf_sigla: string;
  regiao: string | null;
  ano: number;
  populacao: number | null;
  porte_quartil: string | null;
  esf_por_10k: number | null;
  pct_esf_no_porte: number | null;
  pct_icsap: number | null;
  icsap_100k: number | null;
  pct_icsap_no_porte: number | null;
  ivs_score: number | null;
  ivs_quartil: string | null;
  atencao: boolean | null;
}

export interface CnesMunicipio {
  municipio_cod: string;
  municipio_nome: string | null;
  uf_sigla: string;
  regiao: string | null;
  estabelecimentos_total: number;
  estabelecimentos_hospitalares: number;
  publico: number;
  privado_lucrativo: number;
  sem_fins_lucrativos: number;
  pessoa_fisica: number;
  internacional: number;
  populacao: number | null;
  estab_por_10k: number | null;
  estab_hosp_por_10k: number | null;
  pct_publico: number | null;
  ano_referencia: number;
}

export interface LeitosMunicipio {
  municipio_cod: string;
  municipio_nome: string | null;
  uf_sigla: string;
  regiao: string | null;
  ano: number;
  leitos_total: number;
  leitos_sus: number;
  leitos_nao_sus: number;
  leitos_uti: number;
  leitos_uti_sus: number;
  leitos_cirurgico: number;
  leitos_clinico: number;
  leitos_obstetrico: number;
  leitos_pediatrico: number;
  leitos_complementar: number;
  leitos_outras_especialidades: number;
  leitos_hospital_dia: number;
  populacao: number | null;
  leitos_por_mil: number | null;
  leitos_sus_por_mil: number | null;
  leitos_uti_por_100k: number | null;
  pct_leitos_sus: number | null;
}

export interface HsmrHospital {
  cnes: string;
  municipio_cod: string;
  municipio_nome: string | null;
  uf_sigla: string;
  ano: number;
  internacoes: number;
  obitos_observados: number;
  obitos_esperados: number;
  hsmr: number | null;
  estavel: boolean;
  hsmr_ic95_inf: number | null;
  hsmr_ic95_sup: number | null;
  hsmr_pvalor: number | null;
  hsmr_q_valor: number | null;
  significancia: "acima" | "abaixo" | "esperado" | "indeterminado" | null;
  /** HSMR recalibrado dentro do estrato de complexidade (com/sem UTI) —
   *  é a régua usada pela classificação. Ver metodologia §14. */
  hsmr_estrato: number | null;
  estrato: "com_uti" | "sem_uti" | "indefinido" | null;
  tem_uti: boolean | null;
  leitos_total: number | null;
  leitos_uti: number | null;
}

export interface CoberturaIcsapMunicipio {
  municipio_cod: string;
  municipio_nome: string | null;
  uf_sigla: string;
  regiao: string | null;
  ano: number;
  populacao: number | null;
  cobertura_pct: number | null;
  cobertura_efetiva: number | null;
  qt_esf: number | null;
  internacoes_total: number;
  internacoes_icsap: number;
  pct_icsap: number | null;
  icsap_100k: number | null;
  ivs_score: number | null;
}

export interface LosHospital {
  cnes: string;
  municipio_cod: string;
  municipio_nome: string | null;
  uf_sigla: string;
  ano: number;
  cid3: string;
  capitulo_cid: string;
  internacoes: number;
  mediana_hospital_dias: number | null;
  mediana_nacional_dias: number | null;
  desvio_dias: number | null;
}

export interface ForecastDemandaHospital {
  cnes: string;
  municipio_cod: string;
  municipio_nome: string | null;
  uf_sigla: string;
  ano_mes_previsto: string;
  internacoes_previstas: number;
  ic_inferior: number;
  ic_superior: number;
  n_meses_historico: number;
  confianca: "adequada" | "baixa";
}

export interface Natalidade {
  municipio_cod: string;
  municipio_nome: string | null;
  uf_sigla: string;
  regiao: string | null;
  ano: number;
  nascidos: number;
  pct_baixo_peso: number | null;
  pct_prematuro: number | null;
  pct_prenatal_7mais: number | null;
  idade_media_mae: number | null;
}

export interface MortalidadeInfantil {
  uf_sigla: string;
  ano: number;
  nascidos: number;
  obitos_menor1: number | null;
  tmi_por_mil: number | null;
}

export interface Ivs {
  municipio_cod: string;
  municipio_nome: string | null;
  uf_sigla: string;
  regiao: string | null;
  taxa_analfabetismo: number | null;
  pct_sem_agua: number | null;
  ivs_score: number | null;
  ivs_quartil: string | null;
}

export interface CruzVulnMort {
  cod: string;
  nome: string | null;
  uf: string;
  regiao: string | null;
  ivs: number;
  taxa_pad: number;
  pop: number;
}

/** Distância até a mediana dos pares em internações evitáveis (ICSAP). */
export interface IcsapPares {
  municipio_cod: string;
  municipio_nome: string | null;
  uf_sigla: string;
  ano: number;
  populacao: number | null;
  internacoes_total: number;
  internacoes_icsap: number;
  pct_icsap: number;
  arquetipo: string | null;
  criterio_pares: string;
  n_pares: number;
  mediana_pares_pct: number;
  p25_pares_pct: number;
  diferenca_pp: number;
  internacoes_acima_pares: number;
  internacoes_acima_p25: number;
  // Derivados do custo/permanência por internação: nulos enquanto o SIH não estiver
  // reprocessado com separação por tipo de AIH (ver §10 da metodologia).
  custo_associado_reais: number | null;
  leitos_dia_associados: number | null;
  leitos_equivalentes_ano: number | null;
  custo_medio_icsap_ref: number | null;
  permanencia_media_icsap_ref: number | null;
  amostra_pequena: boolean;
}

export interface ClusterMunicipio {
  municipio_cod: string;
  uf_sigla: string;
  cluster: number;
  perfil: string;
  taxa_padronizada_100k: number | null;
  ivs_score: number | null;
  internacoes_100k: number | null;
}

export interface FluxoIntermunicipal {
  ano: number;
  municipio_res: string;
  municipio_res_nome: string | null;
  uf_res: string | null;
  municipio_mov: string;
  municipio_mov_nome: string | null;
  uf_mov: string | null;
  internacoes: number;
}

export interface Icsap {
  municipio_cod: string;
  municipio_nome: string | null;
  uf_sigla: string;
  regiao: string | null;
  ano: number;
  internacoes_total: number;
  internacoes_icsap: number;
  pct_icsap: number | null;
  populacao: number | null;
  icsap_100k: number | null;
}

/** Dados estáticos gerados no build (servidos pelo próprio site — egress zero). */
export async function sdata<T>(name: string): Promise<T> {
  const res = await fetch(`/sdata/${name}.json`);
  if (!res.ok) throw new Error(`sdata/${name}: HTTP ${res.status}`);
  return (await res.json()) as T;
}

export interface CapituloCid {
  capitulo: string;
  capitulo_num: number;
  faixa: string;
  descricao: string;
}

export interface CausaAgregada {
  causabas_3: string;
  obitos: number;
}

export interface MetaItem {
  chave: string;
  valor: string;
}

// ── Constantes de domínio ────────────────────────────────────────────────────

export const UFS = [
  "AC", "AL", "AM", "AP", "BA", "CE", "DF", "ES", "GO", "MA", "MG", "MS",
  "MT", "PA", "PB", "PE", "PI", "PR", "RJ", "RN", "RO", "RR", "RS", "SC",
  "SE", "SP", "TO",
] as const;

export const ANOS = [2015, 2016, 2017, 2018, 2019, 2020, 2021, 2022, 2023, 2024] as const;

/** A partir deste ano há detalhe demográfico completo (sexo × faixa × capítulo). */
export const ANO_DETALHE = 2022;

export const FAIXAS_ORDEM = [
  "<1", "1-4", "5-14", "15-29", "30-44", "45-59", "60-74", "75+", "IGN",
] as const;

export const fmtInt = (n: number | null | undefined) =>
  n == null ? "—" : n.toLocaleString("pt-BR");

export const fmtDec = (n: number | null | undefined, d = 1) =>
  n == null ? "—" : n.toLocaleString("pt-BR", { maximumFractionDigits: d, minimumFractionDigits: d });
