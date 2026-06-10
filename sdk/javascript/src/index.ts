/**
 * saude-publica-br — SDK TypeScript/JavaScript oficial
 *
 * Cliente para a API pública do DataSUS (saude-publica.br/api).
 * Suporte a Node.js 18+ (fetch nativo), Bun e ambientes browser-compatíveis.
 *
 * @example
 * ```ts
 * import { SaudePublicaClient } from 'saude-publica-br';
 *
 * const client = new SaudePublicaClient({ apiKey: 'spb_live_...' });
 *
 * const dengue = await client.doencas.listar({ uf: 'AM', agravo: 'A90', ano: 2024 });
 * console.log(`${dengue.meta.total} registros de dengue no AM`);
 * ```
 *
 * @module
 */

// ---------------------------------------------------------------------------
// Tipos base
// ---------------------------------------------------------------------------

export interface MetaPaginacao {
  total: number;
  pagina: number;
  por_pagina: number;
  paginas: number;
}

export interface RateLimitInfo {
  limite_hora: number;
  usadas_hora: number;
  tier: string;
}

// ---------------------------------------------------------------------------
// Produção ambulatorial (SIA)
// ---------------------------------------------------------------------------

export interface ProducaoItem {
  competencia: string;
  uf: string;
  municipio_codigo: string | null;
  procedimento_codigo: string;
  procedimento_descricao: string;
  quantidade_aprovada: number;
  valor_aprovado: number;
  quantidade_apresentada: number | null;
}

export interface ProducaoResponse {
  dados: ProducaoItem[];
  meta: MetaPaginacao;
  rate_limit: RateLimitInfo;
  ultima_atualizacao: string;
}

export interface ResumoProducaoItem {
  uf: string;
  total_procedimentos: number;
  total_valor_aprovado: number;
  competencias_disponiveis: number;
}

export interface ResumoProducaoResponse {
  dados: ResumoProducaoItem[];
  rate_limit: RateLimitInfo;
}

// Parâmetros de filtro

export interface ListarProducaoParams {
  uf?: string;
  municipio?: string;
  procedimento?: string;
  competencia_inicio?: string;
  competencia_fim?: string;
  pagina?: number;
  por_pagina?: number;
}

export interface ResumoProducaoParams {
  competencia_inicio?: string;
  competencia_fim?: string;
}

// ---------------------------------------------------------------------------
// Mortalidade (SIM)
// ---------------------------------------------------------------------------

export interface MortalidadeItem {
  ano: number;
  uf: string;
  municipio_codigo: string | null;
  causa_cid10: string;
  causa_descricao: string;
  capitulo_cid: string | null;
  obitos: number;
  taxa_100k: number | null;
  idade_media: number | null;
  prop_feminino: number | null;
}

export interface MortalidadeResponse {
  dados: MortalidadeItem[];
  meta: MetaPaginacao;
  rate_limit: RateLimitInfo;
  ultima_atualizacao: string;
}

export interface CausaPrincipalItem {
  causa_cid10: string;
  causa_descricao: string;
  capitulo_cid: string | null;
  obitos: number;
  pct_total: number | null;
}

export interface CausasPrincipaisResponse {
  uf: string;
  ano: number;
  dados: CausaPrincipalItem[];
  rate_limit: RateLimitInfo;
  fonte: string;
}

export interface TendenciaMortalidadeItem {
  ano: number;
  obitos: number;
  taxa_100k: number | null;
}

export interface TendenciaMortalidadeResponse {
  uf: string;
  causa_cid10: string;
  serie: TendenciaMortalidadeItem[];
  rate_limit: RateLimitInfo;
  fonte: string;
}

export interface ListarMortalidadeParams {
  uf?: string;
  municipio?: string;
  cid10?: string;
  ano_inicio?: number;
  ano_fim?: number;
  com_taxa?: boolean;
  pagina?: number;
  por_pagina?: number;
}

export interface CausasPrincipaisParams {
  uf: string;
  ano: number;
  top_n?: number;
}

export interface TendenciaParams {
  uf: string;
  cid10: string;
}

// ---------------------------------------------------------------------------
// Capacidade instalada (CNES)
// ---------------------------------------------------------------------------

export interface EstabelecimentoItem {
  cnes: string;
  nome: string;
  uf: string;
  municipio_codigo: string;
  municipio_nome: string;
  tipo_unidade: string;
  gestao: string;
  leitos_sus: number;
  leitos_uti: number;
  equipes_saude_familia: number | null;
  profissionais: number | null;
  competencia: string;
  latitude: number | null;
  longitude: number | null;
}

export interface CapacidadeResponse {
  dados: EstabelecimentoItem[];
  meta: MetaPaginacao;
  rate_limit: RateLimitInfo;
  ultima_atualizacao: string;
}

export interface ResumoCapacidadeItem {
  uf: string;
  municipio_codigo: string | null;
  municipio_nome: string | null;
  total_estabelecimentos: number;
  total_leitos_sus: number;
  total_leitos_uti: number;
  leitos_uti_por_100k: number | null;
  equipes_esf: number | null;
  cobertura_esf_pct: number | null;
  competencia: string;
}

export interface ResumoCapacidadeResponse {
  dados: ResumoCapacidadeItem[];
  rate_limit: RateLimitInfo;
  ultima_atualizacao: string;
}

export interface LeitosUtiItem {
  uf: string;
  total_leitos_uti: number;
  leitos_uti_por_100k: number | null;
  total_estabelecimentos: number;
}

export interface LeitosUtiResponse {
  competencia: string;
  granularidade: string;
  referencia_oms: number;
  dados: LeitosUtiItem[];
  rate_limit: RateLimitInfo;
  fonte: string;
}

export interface ListarEstabelecimentosParams {
  uf?: string;
  municipio?: string;
  tipo?: string;
  gestao?: string;
  apenas_sus?: boolean;
  competencia?: string;
  com_coords?: boolean;
  pagina?: number;
  por_pagina?: number;
}

export interface ResumoCapacidadeParams {
  competencia?: string;
}

export interface LeitosUtiParams {
  granularidade?: 'uf' | 'municipio';
  competencia?: string;
  top_n?: number;
}

// ---------------------------------------------------------------------------
// Doenças e agravos (SINAN)
// ---------------------------------------------------------------------------

export interface DoencaItem {
  ano: number;
  semana_epidemiologica: number;
  uf: string;
  municipio_codigo: string | null;
  agravo_cid10: string;
  agravo_nome: string;
  casos: number;
  casos_graves: number | null;
  obitos: number | null;
  incidencia_100k: number | null;
  alertas: string[] | null;
}

export interface DoencaResponse {
  dados: DoencaItem[];
  meta: MetaPaginacao;
  rate_limit: RateLimitInfo;
  ultima_atualizacao: string;
}

export interface SurtoItem {
  agravo_nome: string;
  uf: string;
  semana_inicio: number;
  semana_fim: number;
  casos_observados: number;
  casos_esperados: number;
  razao_observado_esperado: number;
  nivel_alerta: 'VERDE' | 'AMARELO' | 'LARANJA' | 'VERMELHO';
}

export interface SurtosResponse {
  dados: SurtoItem[];
  rate_limit: RateLimitInfo;
  gerado_em: string;
}

export interface AgravoItem {
  cid10: string;
  nome: string;
}

export interface AgravosResponse {
  dados: AgravoItem[];
  total: number;
  rate_limit: RateLimitInfo;
}

export interface SerieDoencaItem {
  semana_epidemiologica: number;
  casos: number;
  incidencia_100k: number | null;
  prophet_yhat: number | null;
  prophet_yhat_lower: number | null;
  prophet_yhat_upper: number | null;
  alertas: string[] | null;
}

export interface SerieDoencaResponse {
  uf: string;
  agravo_cid10: string;
  agravo_nome: string;
  ano: number;
  serie: SerieDoencaItem[];
  rate_limit: RateLimitInfo;
  fonte: string;
}

export interface ListarDoencasParams {
  uf?: string;
  agravo?: string;
  ano?: number;
  semana_inicio?: number;
  semana_fim?: number;
  apenas_alertas?: boolean;
  pagina?: number;
  por_pagina?: number;
}

export interface ListarSurtosParams {
  uf?: string;
  agravo?: string;
  nivel_minimo?: 'AMARELO' | 'LARANJA' | 'VERMELHO';
}

export interface SerieDoencaParams {
  uf: string;
  agravo: string;
  ano: number;
}

// ---------------------------------------------------------------------------
// Utilitários (/v1/status, /v1/me, /v1/sistemas)
// ---------------------------------------------------------------------------

export interface SistemaStatus {
  status: 'ok' | 'degradado';
  ultima_carga: string | null;
}

export interface StatusResponse {
  status: 'ok' | 'degradado' | 'indisponível';
  versao: string;
  sistemas: Record<string, SistemaStatus>;
  documentacao: string;
  repositorio: string;
}

export interface ApiKeyMeResponse {
  key_prefix: string;
  nome: string;
  tier: string;
  scopes: string[];
  rate_limit_hora: number;
  rate_limit_dia: number;
  total_requests: number;
  criado_em: string;
  ultimo_uso: string | null;
  rate_limit: RateLimitInfo;
}

export interface SistemaInfo {
  sigla: string;
  nome: string;
  descricao: string;
  granularidade: string;
  endpoints: string[];
  anos_disponiveis?: { inicio: number; fim: number };
  ufs?: number;
  status?: string;
  agravos_disponiveis?: number;
}

export interface SistemasResponse {
  sistemas: SistemaInfo[];
  total: number;
  rate_limit: RateLimitInfo;
}

// ---------------------------------------------------------------------------
// Erros
// ---------------------------------------------------------------------------

/** Erro base do SDK. */
export class SaudePublicaError extends Error {
  public readonly statusCode: number;
  public readonly detail: string;

  constructor(statusCode: number, detail: string) {
    super(`[${statusCode}] ${detail}`);
    this.name = 'SaudePublicaError';
    this.statusCode = statusCode;
    this.detail = detail;
  }
}

/** Rate limit atingido — aguarde `retryAfterSeconds` antes de tentar novamente. */
export class RateLimitError extends SaudePublicaError {
  public readonly retryAfterSeconds: number;

  constructor(detail: string, retryAfterSeconds = 3600) {
    super(429, detail);
    this.name = 'RateLimitError';
    this.retryAfterSeconds = retryAfterSeconds;
  }
}

/** API key ausente, inválida ou expirada. */
export class AuthError extends SaudePublicaError {
  constructor(detail: string) {
    super(401, detail);
    this.name = 'AuthError';
  }
}

/** Scope insuficiente ou tier insuficiente para o recurso. */
export class ForbiddenError extends SaudePublicaError {
  constructor(detail: string) {
    super(403, detail);
    this.name = 'ForbiddenError';
  }
}

// ---------------------------------------------------------------------------
// Transporte HTTP com retry
// ---------------------------------------------------------------------------

const DEFAULT_BASE_URL = 'https://api.saudepublica.br';
const MAX_RETRIES = 3;
const RETRY_STATUSES = new Set([429, 500, 502, 503, 504]);

export interface ClientOptions {
  /** API key no formato `spb_live_...` */
  apiKey: string;
  /** URL base da API. Padrão: `https://api.saudepublica.br` */
  baseUrl?: string;
  /** Timeout em milissegundos. Padrão: 30000 (30s) */
  timeoutMs?: number;
}

async function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

/**
 * Transporte HTTP interno. Não use diretamente — utilize `SaudePublicaClient`.
 */
class Transport {
  private readonly apiKey: string;
  private readonly baseUrl: string;
  private readonly timeoutMs: number;

  constructor(options: ClientOptions) {
    this.apiKey = options.apiKey;
    this.baseUrl = (options.baseUrl ?? DEFAULT_BASE_URL).replace(/\/$/, '');
    this.timeoutMs = options.timeoutMs ?? 30_000;
  }

  /**
   * Serializa um objeto de parâmetros em query string,
   * omitindo valores `undefined` e `null`.
   */
  private buildQuery(params: Record<string, unknown>): string {
    const entries = Object.entries(params).filter(
      ([, v]) => v !== undefined && v !== null,
    );
    if (entries.length === 0) return '';
    const qs = entries.map(([k, v]) => `${encodeURIComponent(k)}=${encodeURIComponent(String(v))}`).join('&');
    return `?${qs}`;
  }

  /**
   * Realiza uma requisição GET com retry automático e backoff exponencial.
   */
  async get<T>(path: string, params: Record<string, unknown> = {}): Promise<T> {
    const url = `${this.baseUrl}${path}${this.buildQuery(params)}`;

    for (let attempt = 0; attempt <= MAX_RETRIES; attempt++) {
      const controller = new AbortController();
      const timerId = setTimeout(() => controller.abort(), this.timeoutMs);

      let response: Response;
      try {
        response = await fetch(url, {
          method: 'GET',
          headers: {
            'X-API-Key': this.apiKey,
            Accept: 'application/json',
            'User-Agent': 'saude-publica-br-sdk-ts/1.0.0',
          },
          signal: controller.signal,
        });
      } catch (err) {
        clearTimeout(timerId);
        if (attempt < MAX_RETRIES) {
          await sleep(2 ** attempt * 1000);
          continue;
        }
        throw new SaudePublicaError(0, `Erro de rede: ${String(err)}`);
      }
      clearTimeout(timerId);

      // Sucesso
      if (response.ok) {
        return response.json() as Promise<T>;
      }

      // Erros que devemos fazer retry
      if (RETRY_STATUSES.has(response.status) && attempt < MAX_RETRIES) {
        if (response.status === 429) {
          const retryAfter = parseInt(response.headers.get('Retry-After') ?? '60', 10);
          await sleep(retryAfter * 1000);
        } else {
          await sleep(2 ** attempt * 1000);
        }
        continue;
      }

      // Extrair detalhes do erro
      let detail = `HTTP ${response.status}`;
      try {
        const body = (await response.json()) as { detail?: string };
        if (body.detail) detail = body.detail;
      } catch {
        // não conseguiu parsear JSON — usa mensagem genérica
      }

      if (response.status === 401) throw new AuthError(detail);
      if (response.status === 403) throw new ForbiddenError(detail);
      if (response.status === 429) {
        const retryAfter = parseInt(response.headers.get('Retry-After') ?? '3600', 10);
        throw new RateLimitError(detail, retryAfter);
      }
      throw new SaudePublicaError(response.status, detail);
    }

    // Nunca deveria chegar aqui
    throw new SaudePublicaError(0, 'Máximo de tentativas atingido.');
  }
}

// ---------------------------------------------------------------------------
// Sub-clientes por domínio
// ---------------------------------------------------------------------------

/** Endpoints de produção ambulatorial (SIA). */
export class ProducaoClient {
  constructor(private readonly transport: Transport) {}

  /**
   * Lista registros de produção ambulatorial com filtros e paginação.
   * Usuários `free` têm acesso apenas aos últimos 12 meses.
   */
  async listar(params: ListarProducaoParams = {}): Promise<ProducaoResponse> {
    return this.transport.get<ProducaoResponse>('/v1/producao', params as Record<string, unknown>);
  }

  /**
   * Resumo agregado de produção por UF para um período.
   */
  async resumo(params: ResumoProducaoParams = {}): Promise<ResumoProducaoResponse> {
    return this.transport.get<ResumoProducaoResponse>('/v1/producao/resumo', params as Record<string, unknown>);
  }
}

/** Endpoints de mortalidade (SIM). */
export class MortalidadeClient {
  constructor(private readonly transport: Transport) {}

  /**
   * Lista dados anuais de mortalidade por causa (CID-10).
   * Usuários `free`: últimos 5 anos.
   */
  async listar(params: ListarMortalidadeParams = {}): Promise<MortalidadeResponse> {
    return this.transport.get<MortalidadeResponse>('/v1/mortalidade', params as Record<string, unknown>);
  }

  /**
   * Top-N causas de morte para uma UF e ano.
   */
  async causasPrincipais(params: CausasPrincipaisParams): Promise<CausasPrincipaisResponse> {
    return this.transport.get<CausasPrincipaisResponse>('/v1/mortalidade/causas-principais', params as Record<string, unknown>);
  }

  /**
   * Série histórica anual para uma causa e UF.
   */
  async tendencia(params: TendenciaParams): Promise<TendenciaMortalidadeResponse> {
    return this.transport.get<TendenciaMortalidadeResponse>('/v1/mortalidade/tendencia', params as Record<string, unknown>);
  }
}

/** Endpoints de capacidade instalada (CNES). */
export class CapacidadeClient {
  constructor(private readonly transport: Transport) {}

  /**
   * Lista estabelecimentos de saúde com filtros por UF, município, tipo e gestão.
   */
  async estabelecimentos(params: ListarEstabelecimentosParams = {}): Promise<CapacidadeResponse> {
    return this.transport.get<CapacidadeResponse>('/v1/capacidade/estabelecimentos', params as Record<string, unknown>);
  }

  /**
   * Resumo de capacidade instalada por UF — todos os 27 estados em uma chamada.
   */
  async resumo(params: ResumoCapacidadeParams = {}): Promise<ResumoCapacidadeResponse> {
    return this.transport.get<ResumoCapacidadeResponse>('/v1/capacidade/resumo', params as Record<string, unknown>);
  }

  /**
   * Ranking de leitos UTI por 100k habitantes.
   * Granularidade municipal requer tier `pro` ou `enterprise`.
   */
  async leitosUti(params: LeitosUtiParams = {}): Promise<LeitosUtiResponse> {
    return this.transport.get<LeitosUtiResponse>('/v1/capacidade/leitos-uti', params as Record<string, unknown>);
  }
}

/** Endpoints de doenças e agravos notificáveis (SINAN). */
export class DoencasClient {
  constructor(private readonly transport: Transport) {}

  /**
   * Lista notificações semanais com alertas epidemiológicos Prophet.
   * Usuários `free`: últimos 2 anos.
   */
  async listar(params: ListarDoencasParams = {}): Promise<DoencaResponse> {
    return this.transport.get<DoencaResponse>('/v1/doencas', params as Record<string, unknown>);
  }

  /**
   * Surtos e alertas epidemiológicos ativos nas últimas 4 semanas.
   */
  async surtos(params: ListarSurtosParams = {}): Promise<SurtosResponse> {
    return this.transport.get<SurtosResponse>('/v1/doencas/surtos', params as Record<string, unknown>);
  }

  /**
   * Lista todos os agravos disponíveis no SINAN com seus códigos CID-10.
   */
  async agravos(): Promise<AgravosResponse> {
    return this.transport.get<AgravosResponse>('/v1/doencas/agravos');
  }

  /**
   * Série temporal semanal de um agravo em uma UF, com bandas de confiança Prophet.
   */
  async serie(params: SerieDoencaParams): Promise<SerieDoencaResponse> {
    return this.transport.get<SerieDoencaResponse>('/v1/doencas/serie', params as Record<string, unknown>);
  }
}

// ---------------------------------------------------------------------------
// Cliente principal
// ---------------------------------------------------------------------------

/**
 * Cliente da API pública de saúde pública brasileira (DataSUS).
 *
 * @example
 * ```ts
 * import { SaudePublicaClient } from 'saude-publica-br';
 *
 * const client = new SaudePublicaClient({ apiKey: 'spb_live_...' });
 *
 * // Produção ambulatorial
 * const producao = await client.producao.listar({ uf: 'SP', pagina: 1 });
 *
 * // Top causas de mortalidade
 * const causas = await client.mortalidade.causasPrincipais({ uf: 'RJ', ano: 2023 });
 *
 * // Surtos ativos
 * const surtos = await client.doencas.surtos({ nivel_minimo: 'LARANJA' });
 *
 * // Leitos UTI por estado
 * const leitos = await client.capacidade.leitosUti();
 * ```
 */
export class SaudePublicaClient {
  /** Acesso aos endpoints de produção ambulatorial (SIA). */
  public readonly producao: ProducaoClient;
  /** Acesso aos endpoints de mortalidade (SIM). */
  public readonly mortalidade: MortalidadeClient;
  /** Acesso aos endpoints de capacidade instalada (CNES). */
  public readonly capacidade: CapacidadeClient;
  /** Acesso aos endpoints de doenças e agravos notificáveis (SINAN). */
  public readonly doencas: DoencasClient;

  private readonly transport: Transport;

  constructor(options: ClientOptions) {
    if (!options.apiKey) {
      throw new Error('SaudePublicaClient: apiKey é obrigatória.');
    }
    this.transport = new Transport(options);
    this.producao = new ProducaoClient(this.transport);
    this.mortalidade = new MortalidadeClient(this.transport);
    this.capacidade = new CapacidadeClient(this.transport);
    this.doencas = new DoencasClient(this.transport);
  }

  /**
   * Verifica o status operacional da API e dos sistemas de dados.
   * **Não requer autenticação no lado do servidor**, mas o SDK ainda envia a
   * chave (evita erro no gateway de borda).
   */
  async status(): Promise<StatusResponse> {
    return this.transport.get<StatusResponse>('/v1/status');
  }

  /**
   * Retorna informações detalhadas sobre a API key autenticada:
   * tier, scopes, limites e total de requisições.
   */
  async me(): Promise<ApiKeyMeResponse> {
    return this.transport.get<ApiKeyMeResponse>('/v1/me');
  }

  /**
   * Catálogo completo dos sistemas de informação disponíveis na API.
   */
  async sistemas(): Promise<SistemasResponse> {
    return this.transport.get<SistemasResponse>('/v1/sistemas');
  }
}

// ---------------------------------------------------------------------------
// Exportação padrão (conveniência)
// ---------------------------------------------------------------------------

export default SaudePublicaClient;
