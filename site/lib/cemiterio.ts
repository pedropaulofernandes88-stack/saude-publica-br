/**
 * Cemitério Digital — endereço do serviço externo, como parâmetro.
 *
 * O Cemitério Digital NÃO roda neste site. O Saúde em Dado é um export
 * estático publicado no GitHub Pages, que serve arquivo e nada mais; a
 * ferramenta precisa de um processo Python persistente lendo Parquet, com um
 * gateway que injeta a credencial interna do lado do servidor. São hospedagens
 * diferentes, e este módulo é toda a ligação que o site guarda: um endereço.
 *
 * POR QUE VARIÁVEL, E NÃO CONSTANTE
 * ----------------------------------
 * `cemiterio.saudeemdado.com` é uma SUGESTÃO do pacote, não um fato. Em
 * 2026-09-06 o nome não resolvia: o domínio está na HostGator (dns3/dns4) e
 * aponta para os IPs do GitHub Pages (185.199.108–111.153), sem registro para
 * o subdomínio e sem wildcard. Fixar o endereço no código publicaria um link
 * quebrado num site que se apresenta como confiável.
 *
 * FALHA FECHADA, DE PROPÓSITO
 * ----------------------------
 * Sem a variável — ou com valor que não passe na conferência — `enderecoDoCemiterio`
 * devolve `null` e o acesso simplesmente não aparece. Um link ausente é uma
 * lacuna; um link quebrado, ou em `http://`, é uma promessa falsa. Só o segundo
 * custa credibilidade, então o padrão é não mostrar.
 *
 * A variável é lida em tempo de BUILD (`NEXT_PUBLIC_*` é inlinado no bundle):
 * ligar o acesso exige uma nova publicação do site, não uma troca em runtime.
 * Isso é aceitável aqui — o subdomínio muda uma vez.
 */

/** Nome da variável que o titular cadastra no provedor. Sem valor embutido. */
export const VARIAVEL = "NEXT_PUBLIC_CEMITERIO_URL";

/** O que o pacote sugere. Documentação — nunca um padrão silencioso. */
export const SUBDOMINIO_SUGERIDO = "cemiterio.saudeemdado.com";

/**
 * Normaliza o endereço configurado, ou devolve `null` se não der para confiar.
 *
 * Recusa, e o motivo de cada recusa:
 *  - vazio/ausente → o serviço ainda não existe; não anunciar;
 *  - `http:` → a ferramenta serve consultas e exportações, e origem mista
 *    quebraria as chamadas relativas a `/api/` do próprio subdomínio;
 *  - usuário/senha na URL → credencial em link público, jamais;
 *  - caminho, query ou fragmento → é a RAIZ de um serviço, não uma página;
 *    aceitar `?x=1` aqui deixaria alguém fixar um recorte como se fosse o todo.
 */
export function enderecoDoCemiterio(bruto?: string | null): string | null {
  const texto = (bruto ?? "").trim();
  if (!texto) return null;

  let url: URL;
  try {
    url = new URL(texto);
  } catch {
    return null;
  }

  if (url.protocol !== "https:") return null;
  if (url.username || url.password) return null;
  if (url.search || url.hash) return null;
  if (url.pathname !== "/" && url.pathname !== "") return null;
  if (!url.hostname.includes(".")) return null;

  // Sem barra final: quem concatenar caminho depois não gera `//`.
  return `${url.protocol}//${url.host}`;
}

/**
 * O endereço efetivo desta build, ou `null` enquanto o serviço não existir.
 *
 * `process.env.NEXT_PUBLIC_*` é substituído literalmente no bundle, então a
 * leitura precisa ser textual — desmontar em variável apagaria a substituição.
 */
export function cemiterioConfigurado(): string | null {
  return enderecoDoCemiterio(process.env.NEXT_PUBLIC_CEMITERIO_URL);
}
