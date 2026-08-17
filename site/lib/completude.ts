/**
 * Completude da série mensal do SIM.
 *
 * O SIM tem atraso de registro: os meses mais recentes chegam parciais e vão
 * sendo preenchidos ao longo dos meses seguintes. Plotados sem ressalva, eles
 * desenham uma queda de mortalidade que não aconteceu — em dez/2024 a série
 * nacional marca 45.516 óbitos contra ~134 mil em julho do mesmo ano.
 *
 * A regra de corte é a mesma que `site/scripts/build-boletim.mjs` já aplicava
 * ao excesso de mortalidade: a partir do fim da série, todo mês cuja razão
 * observado/esperado fique abaixo de LIMIAR_COMPLETUDE é considerado
 * incompleto; a varredura para no primeiro mês que passa. O manifesto é
 * calculado no build (build-static-data.mjs) e servido em sdata/completude.json.
 */

/** Abaixo desta razão observado/esperado, o mês está incompleto. */
export const LIMIAR_COMPLETUDE = 0.9;

/** Meses incompletos por UF (chave "BR" para o agregado nacional). */
export type ManifestoCompletude = Record<string, string[]>;

export interface PontoExcesso {
  uf_sigla: string;
  mes_competencia: string;
  obitos: number;
  esperado: number;
}

/**
 * Varre a cauda da série e devolve os meses incompletos, do mais antigo ao mais
 * recente. Só a cauda: um mês baixo no meio da série é sinal epidemiológico,
 * não atraso de digitação, e não pode ser silenciado.
 */
export function mesesIncompletosDaSerie(
  pontos: readonly { mes_competencia: string; obitos: number; esperado: number }[],
): string[] {
  const ordenados = [...pontos].sort((a, b) => a.mes_competencia.localeCompare(b.mes_competencia));
  const incompletos: string[] = [];
  for (let i = ordenados.length - 1; i >= 0; i--) {
    const p = ordenados[i];
    if (!p.esperado || p.obitos / p.esperado >= LIMIAR_COMPLETUDE) break;
    incompletos.push(p.mes_competencia);
  }
  return incompletos.reverse();
}

/** Constrói o manifesto por UF a partir do mart de excesso, incluindo "BR". */
export function construirManifesto(excesso: readonly PontoExcesso[]): ManifestoCompletude {
  const porUf = new Map<string, PontoExcesso[]>();
  const brPorMes = new Map<string, { obitos: number; esperado: number }>();

  for (const r of excesso) {
    if (r.uf_sigla === "BR") continue; // o BR e recalculado a partir das UFs
    const lista = porUf.get(r.uf_sigla) ?? [];
    lista.push(r);
    porUf.set(r.uf_sigla, lista);

    const cur = brPorMes.get(r.mes_competencia) ?? { obitos: 0, esperado: 0 };
    cur.obitos += r.obitos;
    cur.esperado += r.esperado;
    brPorMes.set(r.mes_competencia, cur);
  }

  const manifesto: ManifestoCompletude = {};
  for (const [uf, pontos] of porUf) manifesto[uf] = mesesIncompletosDaSerie(pontos);
  manifesto.BR = mesesIncompletosDaSerie(
    [...brPorMes.entries()].map(([mes_competencia, v]) => ({ mes_competencia, ...v })),
  );
  return manifesto;
}

/** Conjunto de meses incompletos para um recorte; UF desconhecida = nenhum. */
export function incompletosDe(
  manifesto: ManifestoCompletude | null,
  uf: string,
): ReadonlySet<string> {
  return new Set(manifesto?.[uf === "Brasil" ? "BR" : uf] ?? []);
}

/** Rótulo curto para a nota do gráfico; vazio quando não há mês incompleto. */
export function notaCompletude(incompletos: ReadonlySet<string>): string {
  const n = incompletos.size;
  if (n === 0) return "";
  const plural = n > 1 ? `Os ${n} últimos meses estão` : "O último mês está";
  return `${plural} com registro incompleto (atraso do SIM) — a queda no fim da série é de digitação, não de mortalidade.`;
}
