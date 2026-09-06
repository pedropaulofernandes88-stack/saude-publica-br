/**
 * O que dois intervalos de confiança permitem afirmar — e o que não permitem.
 *
 * Isto vive fora do componente porque é uma AFIRMAÇÃO ESTATÍSTICA feita ao
 * leitor ("a diferença não se sustenta"), e afirmação estatística dentro de um
 * `useMemo` não tem como ser testada. O resto do comparador desenha; aqui se
 * decide o que a tela tem direito de dizer.
 *
 * A ASSIMETRIA É O PONTO
 * ----------------------
 * Sobreposição de IC95% é um teste **conservador**:
 *
 *   * intervalos que NÃO se tocam ⇒ a diferença se sustenta ao nível de 5%;
 *   * intervalos que se tocam ⇒ **nada** se conclui. Não é "são iguais", e não
 *     é "não há diferença" — é "com este dado não dá para distinguir".
 *
 * Duas médias podem ter intervalos sobrepostos e ainda assim diferir num teste
 * direto da diferença. Por isso `veredito` devolve rótulos assimétricos, e por
 * isso não existe aqui nenhuma função chamada `saoIguais`.
 */

export interface Intervalo {
  inf: number;
  sup: number;
}

/** Os dois intervalos têm algum ponto em comum? Tocar nas pontas conta. */
export function sobrepoe(a: Intervalo, b: Intervalo): boolean {
  return a.inf <= b.sup && b.inf <= a.sup;
}

export type Veredito = "distinguivel" | "indistinguivel";

/**
 * O veredito de um par.
 *
 * `indistinguivel` NÃO afirma igualdade — afirma que este dado não separa os
 * dois. É a única direção em que a sobreposição autoriza conclusão.
 */
export function veredito(a: Intervalo, b: Intervalo): Veredito {
  return sobrepoe(a, b) ? "indistinguivel" : "distinguivel";
}

/**
 * Um intervalo é utilizável? Limite invertido ou não finito não vira faixa.
 *
 * Faixa desenhada a partir de `sup < inf` sai como área negativa e o gráfico a
 * renderiza de cabeça para baixo, sem erro nenhum — parece decoração e é dado
 * corrompido.
 */
export function intervaloValido(inf: unknown, sup: unknown): boolean {
  return typeof inf === "number" && typeof sup === "number"
    && Number.isFinite(inf) && Number.isFinite(sup) && inf <= sup;
}

/**
 * O intervalo, ou `null` se os limites não servem.
 *
 * Existe além de `intervaloValido` porque um predicado de DOIS argumentos não
 * estreita tipo em TypeScript: quem chamasse `intervaloValido(a, b)` e depois
 * usasse `a!`/`b!` estaria afirmando à mão o que o compilador poderia provar.
 * Devolver o objeto move a prova para o tipo.
 */
export function intervaloDe(inf: unknown, sup: unknown): Intervalo | null {
  return intervaloValido(inf, sup) ? { inf: inf as number, sup: sup as number } : null;
}
