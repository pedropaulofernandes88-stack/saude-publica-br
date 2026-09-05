/**
 * Busca tolerante de município — acento, caixa, espaço e código IBGE.
 *
 * POR QUE ISTO É UM MÓDULO, E NÃO UMA FUNÇÃO NA PÁGINA
 * -----------------------------------------------------
 * `normalizar` existia DUAS vezes no site, copiada em `hospitalar-cliente.tsx`
 * e em `atencao-basica-cliente.tsx`, com um comentário idêntico dizendo que
 * serve para `"Penapolis"` casar com `"Penápolis"`. E o painel de mortalidade,
 * que é a porta de entrada da busca municipal, filtrava com
 * `nome.toLowerCase().includes(q)` — sem normalização nenhuma.
 *
 * Ou seja: o conserto estava escrito, duas vezes, e não estava onde precisava.
 * É o modo de falha que uma cópia sempre produz — ela não diverge, ela deixa de
 * ser aplicada. Uma definição só, importada pelos três.
 *
 * O CÓDIGO IBGE TEM DUAS FORMAS, E AS DUAS CHEGAM COLADAS
 * -------------------------------------------------------
 * As marts usam o código de **6 dígitos** (`353730`); o IBGE publica o de
 * **7** (`3537305`), com dígito verificador. Quem copia de uma planilha do IBGE
 * cola o de 7 e não encontra nada. Os seis primeiros dígitos do código de 7 são
 * exatamente o de 6, então basta truncar — e a busca aceita as duas formas,
 * além de prefixos parciais.
 */

/** Minúsculas, sem acento e sem espaço nas pontas. */
export function semAcento(s: string): string {
  return s.normalize("NFD").replace(/[̀-ͯ]/g, "").trim().toLowerCase();
}

/** Só os dígitos do termo — `"35 37 30"` e `"3537305"` viram algo comparável. */
function digitos(s: string): string {
  return s.replace(/\D/g, "");
}

/**
 * O termo casa com este município?
 *
 * Termo vazio casa com tudo, para que o filtro não precise testar isso antes.
 * Termo só de dígitos é tratado como código IBGE (6 ou 7 dígitos, ou prefixo);
 * qualquer outro termo é comparado ao nome, sem acento e sem caixa.
 */
export function casaMunicipio(termo: string, nome: string | null, codigo: string): boolean {
  const q = termo.trim();
  if (!q) return true;

  const num = digitos(q);
  if (num && num === q.replace(/\s/g, "")) {
    return codigo.startsWith(num.slice(0, 6));
  }
  return semAcento(nome ?? "").includes(semAcento(q));
}
