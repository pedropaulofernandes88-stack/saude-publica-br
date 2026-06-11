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
