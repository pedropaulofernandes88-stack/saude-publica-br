/**
 * O tamanho e o alcance da base, lidos do dado — não digitados.
 *
 * O site anunciava "14,4 milhões de óbitos (2015–2024)" em oito lugares: a
 * descrição que aparece ao compartilhar o link, o nome no schema.org, o herói
 * da home, o cartão de mortalidade, o rótulo de um KPI, a citação sugerida e o
 * quadro de números do /sobre. Todos digitados, todos defasados no mesmo dia em
 * que 2025 entrou — e o KPI ao lado de um deles já exibia o número certo,
 * porque esse era calculado.
 *
 * A régua deste projeto para número em prosa é a de `test_numeros_do_site`: o
 * que pode ser derivado é derivado. Estes oito não podiam, porque não havia de
 * onde derivar num componente de servidor. Agora há.
 *
 * A fonte é `sdata/serie_total.json`, gravado pelo `build-static-data.mjs` a
 * partir do Postgres no mesmo build — a mesma série que a home já somava no
 * cliente para o KPI "Óbitos registrados". Ler o arquivo em vez de repetir a
 * consulta mantém as duas afirmações presas ao mesmo número por construção.
 */
import { readFileSync } from "node:fs";
import path from "node:path";

export interface Cobertura {
  /** Primeiro e último ano com registro na série. */
  anoInicial: number;
  anoFinal: number;
  /** "2015–2025" */
  periodo: string;
  /** Total de óbitos não fetais no período. */
  obitos: number;
  /** "16,0 milhões" — a forma como o texto corrido cita o total. */
  obitosAprox: string;
}

let cache: Cobertura | null = null;

export function cobertura(): Cobertura {
  if (cache) return cache;

  const arquivo = path.join(process.cwd(), "public", "sdata", "serie_total.json");
  const bruto = JSON.parse(readFileSync(arquivo, "utf8")) as {
    uf_sigla: string;
    ano: number;
    obitos: number;
  }[];

  // O arquivo traz uma linha por UF **e** a linha agregada 'BR'. Somar tudo
  // conta cada óbito duas vezes — na primeira versão deste helper deu 32,0
  // milhões, o dobro do real, e o número passaria por plausível numa página de
  // marketing. A home já filtrava por 'BR' antes de somar; aqui é a mesma
  // regra, não uma segunda.
  const serie = bruto.filter((r) => r.uf_sigla === "BR");
  if (!serie.length) {
    throw new Error("serie_total.json sem linhas 'BR' — a agregação nacional sumiu");
  }

  const anos = serie.map((r) => r.ano);
  const anoInicial = Math.min(...anos);
  const anoFinal = Math.max(...anos);
  const obitos = serie.reduce((s, r) => s + r.obitos, 0);

  cache = {
    anoInicial,
    anoFinal,
    periodo: `${anoInicial}–${anoFinal}`,
    obitos,
    obitosAprox: `${(obitos / 1e6).toFixed(1).replace(".", ",")} milhões`,
  };
  return cache;
}
