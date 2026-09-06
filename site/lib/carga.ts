/**
 * Três estados que não podem ter a mesma aparência.
 *
 * POR QUE ISTO EXISTE
 * -------------------
 * O site tinha 60 pontos de `catch`, e boa parte deles era `catch(() => {})` ou
 * `catch(() => [])`. O efeito: quando a consulta FALHAVA, o componente ficava
 * `null` e simplesmente não aparecia — exatamente como quando o município não
 * tem aquele dado.
 *
 * No boletim, quatro cartões se comportavam assim (vulnerabilidade, estrato,
 * ICSAP e imunopreveníveis). Uma falha de rede produzia uma página que AFIRMA,
 * pela ausência, que aquele município não tem contexto social nem internações
 * evitáveis. É uma afirmação sobre o dado feita por um caminho de erro, e é o
 * tipo de defeito que este projeto persegue em toda parte — ausência não é
 * falha, e falha não é ausência. Ver `coleta-ausencia-vs-falha` na origem da
 * mesma regra do lado dos coletores.
 *
 * O QUE MUDA
 * ----------
 * `Carga<T>` obriga quem consome a decidir o que fazer em cada estado, porque
 * eles são variantes distintas e o TypeScript não deixa esquecer nenhuma:
 *
 *   carregando   a consulta está em curso
 *   ok           veio dado
 *   vazio        a consulta RESPONDEU e não há linha para este recorte
 *   erro         a consulta não respondeu — e isso é recuperável, com um botão
 *
 * "vazio" e "erro" existem separados de propósito: o primeiro é informação
 * sobre o município, o segundo é informação sobre a rede.
 */

export type Carga<T> =
  | { estado: "carregando" }
  | { estado: "ok"; dados: T }
  | { estado: "vazio" }
  | { estado: "erro"; mensagem: string };

/** Mensagem curta e acionável a partir do que a promessa rejeitou. */
export function mensagemDeErro(e: unknown): string {
  const texto = e instanceof Error ? e.message : String(e);
  if (/Failed to fetch|NetworkError|ERR_INTERNET/i.test(texto)) {
    return "sem conexão com a API";
  }
  const http = texto.match(/HTTP (\d{3})/);
  if (http) return `a API respondeu HTTP ${http[1]}`;
  return texto.slice(0, 120);
}
