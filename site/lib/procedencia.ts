/**
 * De onde veio o número: manifesto e citação, carregados uma vez por página.
 *
 * POR QUE ESTE MÓDULO EXISTE
 * --------------------------
 * `ficha-indicador.tsx` já sabia buscar o manifesto e a citação, com dois
 * caches de módulo. Quando a exportação passou a precisar dos mesmos dois
 * fatos, a saída óbvia era copiar os loaders — e cópia de definição neste
 * projeto envelhece em silêncio (foi assim que `normalizar` virou duas funções
 * divergentes até `lib/busca.ts` juntá-las). Os loaders vivem aqui; a ficha e a
 * exportação consomem.
 *
 * O cache é de MÓDULO, não de componente: uma página com cinco fichas e um
 * botão de exportar faz uma requisição a cada JSON, não seis.
 */
import { sdata } from "@/lib/api";
import { type Manifesto } from "@/lib/manifesto";

let cacheManifesto: Promise<Manifesto> | null = null;
export function carregarManifesto(): Promise<Manifesto> {
  cacheManifesto ??= sdata<Manifesto>("manifesto");
  return cacheManifesto;
}

export interface LinhaMeta {
  chave: string;
  valor: string;
}

/**
 * A citação vem de `meta_dataset`, que a deriva do `CITATION.cff` — não é uma
 * terceira cópia da frase. Marts derivados estão sob CC BY 4.0, em que
 * atribuição é CONDIÇÃO da licença, não cortesia. Por isso ela acompanha tanto
 * a ficha (ao lado do número na tela) quanto o CSV (dentro do arquivo que sai
 * daqui): quem baixa o dado leva a obrigação junto, sem precisar voltar ao
 * site para descobri-la.
 */
let cacheMeta: Promise<LinhaMeta[]> | null = null;
export function carregarMeta(): Promise<LinhaMeta[]> {
  cacheMeta ??= sdata<LinhaMeta[]>("meta");
  return cacheMeta;
}

/** O valor de uma chave do `meta_dataset`, ou `null` se ela não foi publicada. */
export function valorMeta(meta: LinhaMeta[] | null, chave: string): string | null {
  return meta?.find((r) => r.chave === chave)?.valor ?? null;
}

/**
 * A citação padrão, usada quando `meta_dataset` não respondeu.
 *
 * NÃO é a citação canônica — é o mínimo que impede um arquivo de sair sem
 * atribuição nenhuma quando a rede falha. A canônica sai do `CITATION.cff` via
 * `meta_dataset`; esta existe para que "a rede caiu" não vire "o arquivo saiu
 * sem licença".
 */
export const CITACAO_MINIMA = "Fernandes, P. P. Saúde em Dado. https://saudeemdado.com";
