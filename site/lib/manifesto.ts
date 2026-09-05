/**
 * O manifesto de publicação, do lado do site.
 *
 * `data/publicacoes/<id>.json` é a camada canônica do projeto: o Parquet datado
 * é a verdade e o Postgres é cache reconstruível. O `build-static-data.mjs`
 * recorta esse manifesto para `sdata/manifesto.json` no build — do DISCO, não
 * da API, porque perguntar ao cache o que o original responde devolveria os
 * mesmos números sem o checksum e sem a versão da publicação.
 *
 * Aqui ficam só o tipo e as leituras. Quem monta o texto é a ficha.
 */

export interface TabelaPublicada {
  linhas: number;
  /** Primeira e última competência cobertas, quando a tabela é temporal. */
  competencia_min: string | null;
  competencia_max: string | null;
  /** Publicação em que esta tabela foi gravada pela última vez ("2026-09-03.2"). */
  publicada_em: string | null;
  /** `false` = existe como download em Parquet e NÃO é servida pela API. */
  servida: boolean;
  sha256: string | null;
}

export interface Manifesto {
  /** Identificador da publicação corrente ("2026-09-03.2"). */
  id: string;
  gerado_em: string;
  commit: string | null;
  tabelas: Record<string, TabelaPublicada>;
}

/**
 * Os fatos de uma tabela, ou `null` se ela não está no manifesto.
 *
 * Devolver `null` em vez de lançar é deliberado: a ficha aparece ao lado de um
 * número que já está na tela, e uma tabela ausente do manifesto não pode
 * derrubar a página inteira. Quem garante que isso não acontece em silêncio é
 * `indicadores.test.mts`, que reprova no CI antes de chegar ao navegador.
 */
export function tabelaPublicada(m: Manifesto | null, nome: string): TabelaPublicada | null {
  return m?.tabelas?.[nome] ?? null;
}

/**
 * "2015 a 2025" a partir das competências, que vêm em formatos diferentes
 * conforme a tabela: ano (`2024`), competência (`2024-07`) ou data completa.
 * Só o ano interessa ao leitor da ficha.
 */
export function periodoCoberto(t: TabelaPublicada | null): string | null {
  if (!t) return null;
  const ano = (v: string | null) => (v ? String(v).slice(0, 4) : null);
  const ini = ano(t.competencia_min);
  const fim = ano(t.competencia_max);
  if (!ini || !fim) return null;
  return ini === fim ? ini : `${ini}–${fim}`;
}
