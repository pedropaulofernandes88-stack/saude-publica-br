/**
 * Guard-rail do boletim semanal: acumula verificações e decide se a execução cai.
 *
 * POR QUE ISTO EXISTE COMO MÓDULO
 * -------------------------------
 * A lógica vivia dentro de `scripts/build-boletim.mjs`, um script linear que roda
 * de cima a baixo e termina em `process.exit`. Nada disso é testável: para
 * exercitar a decisão seria preciso rodar o build inteiro, com rede e três APIs.
 *
 * Resultado: quatro verificações CRÍTICAS — as que existem para derrubar o job
 * semanal quando o boletim degrada — nunca tinham sido vistas derrubando nada.
 * Uma varredura em 2026-09-02 encontrou o mesmo padrão em 25 guardas do lado
 * Python; esta é a versão TypeScript dele.
 *
 * A separação que resolve é entre `avaliar` (puro: recebe as verificações,
 * devolve o veredito e o código de saída) e o `encerrar` do script (imprime e
 * chama `process.exit`). O que decide é testável; o que mata o processo fica
 * onde estava.
 *
 * O QUE O GUARD-RAIL PROTEGE
 * --------------------------
 * Um boletim automático degrada em silêncio: a fonte muda de formato, o modelo
 * externo congela, uma mart some — e ele continua publicando algo plausível.
 * Publicar em silêncio um boletim degradado é o único desfecho inaceitável, e é
 * por isso que falha crítica sai com código != 0: o Actions notifica e abre
 * issue.
 */

export type Verificacao = {
  nome: string;
  ok: boolean;
  critico: boolean;
  detalhe: string;
};

export type Veredito = {
  criticas: Verificacao[];
  avisos: Verificacao[];
  /** 2 quando há falha crítica, 0 caso contrário. */
  codigo: 0 | 2;
};

/** Código de saída usado para falha crítica.
 *
 * NÃO é 1 de propósito: 1 é o que o Node devolve para exceção não tratada, e
 * distinguir os dois no log do Actions é o que separa "o boletim degradou" de
 * "o script quebrou". São incidentes diferentes, com respostas diferentes.
 */
export const CODIGO_DEGRADADO = 2;

/**
 * Cria um acumulador de verificações.
 *
 * `registrar` devolve o próprio `ok` para permitir `if (!registrar(...)) return;`
 * sem duplicar a condição — era o contrato da função original e é preservado.
 */
export function criarVerificador(escrever: (linha: string) => void = () => {}) {
  const verificacoes: Verificacao[] = [];

  function registrar(
    nome: string,
    ok: boolean,
    detalhe: string,
    { critico = false }: { critico?: boolean } = {},
  ): boolean {
    verificacoes.push({ nome, ok, critico, detalhe });
    const marca = ok ? "ok  " : critico ? "FALHA" : "aviso";
    escrever(`[verif] ${marca} ${nome}: ${detalhe}`);
    return ok;
  }

  return { verificacoes, registrar };
}

/**
 * Classifica as verificações e devolve o código de saída.
 *
 * Puro: não imprime, não sai, não lê relógio. É a peça que os testes exercitam.
 */
export function avaliar(verificacoes: readonly Verificacao[]): Veredito {
  const criticas = verificacoes.filter((v) => !v.ok && v.critico);
  const avisos = verificacoes.filter((v) => !v.ok && !v.critico);
  return { criticas, avisos, codigo: criticas.length ? CODIGO_DEGRADADO : 0 };
}
