import { buildUrl } from "./utils";
import type {
  InternacoesParams,
  InternacoesResponse,
  InternacoesSerieResponse,
  RankingItem,
  RankingParams,
  MortalidadeParams,
  MortalidadeResponse,
  MortalidadeSerieResponse,
  AnomaliaResponse,
  EpidemiologiaResponse,
  ProducaoResponse,
} from "./types";

const BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

// ---------------------------------------------------------------------------
// Fetch helper
// ---------------------------------------------------------------------------
async function apiFetch<T>(path: string): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    next: { revalidate: 600 }, // Next.js ISR — 10 min
  });

  if (!res.ok) {
    const body = await res.text().catch(() => "");
    throw new Error(`API ${res.status}: ${body}`);
  }

  return res.json() as Promise<T>;
}

// ---------------------------------------------------------------------------
// Internações
// ---------------------------------------------------------------------------

/** Lista paginada de internações com filtros opcionais */
export function getInternacoes(params: InternacoesParams = {}): Promise<InternacoesResponse> {
  const path = buildUrl("/internacoes", params as Record<string, string | number | boolean | undefined | null>);
  return apiFetch<InternacoesResponse>(path);
}

/** Série temporal de internações para um município */
export function getInternacoesMunicipio(cod: string): Promise<InternacoesSerieResponse> {
  return apiFetch<InternacoesSerieResponse>(`/internacoes/municipio/${encodeURIComponent(cod)}`);
}

/** Série temporal de internações para uma UF */
export function getInternacoesUF(uf: string): Promise<InternacoesSerieResponse> {
  return apiFetch<InternacoesSerieResponse>(`/internacoes/uf/${encodeURIComponent(uf)}`);
}

/** Ranking de municípios por métrica */
export function getInternacoesRanking(params: RankingParams = {}): Promise<RankingItem[]> {
  const path = buildUrl("/internacoes/ranking", params as Record<string, string | number | boolean | undefined | null>);
  return apiFetch<RankingItem[]>(path);
}

// ---------------------------------------------------------------------------
// Mortalidade
// ---------------------------------------------------------------------------

/** Lista paginada de óbitos com filtros opcionais */
export function getMortalidade(params: MortalidadeParams = {}): Promise<MortalidadeResponse> {
  const path = buildUrl("/mortalidade", params as Record<string, string | number | boolean | undefined | null>);
  return apiFetch<MortalidadeResponse>(path);
}

/** Série temporal de mortalidade para um município */
export function getMortalidadeMunicipio(cod: string): Promise<MortalidadeSerieResponse> {
  return apiFetch<MortalidadeSerieResponse>(`/mortalidade/municipio/${encodeURIComponent(cod)}`);
}

/** Série temporal de mortalidade para uma UF */
export function getMortalidadeUF(uf: string): Promise<MortalidadeSerieResponse> {
  return apiFetch<MortalidadeSerieResponse>(`/mortalidade/uf/${encodeURIComponent(uf)}`);
}

// ---------------------------------------------------------------------------
// Epidemiologia / CID-10
// ---------------------------------------------------------------------------

export function getEpidemiologia(params: Record<string, string | number | undefined> = {}): Promise<EpidemiologiaResponse> {
  const path = buildUrl("/epidemiologia", params as Record<string, string | number | boolean | undefined | null>);
  return apiFetch<EpidemiologiaResponse>(path);
}

// ---------------------------------------------------------------------------
// Produção ambulatorial
// ---------------------------------------------------------------------------

export function getProducao(params: Record<string, string | number | undefined> = {}): Promise<ProducaoResponse> {
  const path = buildUrl("/producao", params as Record<string, string | number | boolean | undefined | null>);
  return apiFetch<ProducaoResponse>(path);
}

// ---------------------------------------------------------------------------
// Anomalias
// ---------------------------------------------------------------------------

export function getAnomalias(params: Record<string, string | number | undefined> = {}): Promise<AnomaliaResponse> {
  const path = buildUrl("/anomalias", params as Record<string, string | number | boolean | undefined | null>);
  return apiFetch<AnomaliaResponse>(path);
}

// ---------------------------------------------------------------------------
// GeoJSON dos municípios (IBGE)
// ---------------------------------------------------------------------------

/** GeoJSON simplificado dos municípios brasileiros (servido pelo próprio backend) */
export function getGeoJsonMunicipios(): Promise<GeoJSON.FeatureCollection> {
  return apiFetch<GeoJSON.FeatureCollection>("/geo/municipios");
}

/** GeoJSON simplificado das UFs */
export function getGeoJsonUFs(): Promise<GeoJSON.FeatureCollection> {
  return apiFetch<GeoJSON.FeatureCollection>("/geo/ufs");
}

// ---------------------------------------------------------------------------
// React Query keys
// ---------------------------------------------------------------------------
export const queryKeys = {
  internacoes: (params: InternacoesParams) => ["internacoes", params] as const,
  internacoesMunicipio: (cod: string) => ["internacoes", "municipio", cod] as const,
  internacoesUF: (uf: string) => ["internacoes", "uf", uf] as const,
  internacoesRanking: (params: RankingParams) => ["internacoes", "ranking", params] as const,
  mortalidade: (params: MortalidadeParams) => ["mortalidade", params] as const,
  mortalidadeMunicipio: (cod: string) => ["mortalidade", "municipio", cod] as const,
  mortalidadeUF: (uf: string) => ["mortalidade", "uf", uf] as const,
  epidemiologia: (params: object) => ["epidemiologia", params] as const,
  producao: (params: object) => ["producao", params] as const,
  anomalias: (params: object) => ["anomalias", params] as const,
  geoMunicipios: () => ["geo", "municipios"] as const,
  geoUFs: () => ["geo", "ufs"] as const,
} as const;
