/**
 * Invariantes do índice da metodologia.
 *
 * O risco aqui é o sumário mentir: prometer uma seção que a página não tem, ou
 * a página ganhar seção que o sumário esconde. Por isso o teste lê o próprio
 * page.tsx e confere a correspondência.
 */
import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import path from "node:path";

import { SECOES, gruposOrdenados, secao, slugify } from "./metodologia-secoes.ts";

const PAGINA = readFileSync(
  path.join(import.meta.dirname, "..", "app", "metodologia", "page.tsx"),
  "utf8",
);

test("slugify remove acento, pontuacao e simbolo", () => {
  assert.equal(slugify("Fontes de dados"), "fontes-de-dados");
  assert.equal(slugify("Intervalos de confiança (IC95%)"), "intervalos-de-confianca-ic95");
  assert.equal(slugify("Leitos × ICSAP: o indicador"), "leitos-icsap-o-indicador");
  assert.equal(slugify("  espaços  nas  bordas  "), "espacos-nas-bordas");
});

test("numeracao e contigua a partir de 1", () => {
  SECOES.forEach((s, i) => assert.equal(s.n, i + 1, `secao na posicao ${i} tem n=${s.n}`));
});

test("slugs sao unicos", () => {
  const vistos = new Set<string>();
  for (const s of SECOES) {
    assert.ok(!vistos.has(s.slug), `slug duplicado: ${s.slug}`);
    assert.ok(s.slug.length > 0, `slug vazio na secao ${s.n}`);
    vistos.add(s.slug);
  }
});

test("todo grupo do sumario e contiguo e cobre todas as secoes", () => {
  const grupos = gruposOrdenados();
  const achatado = grupos.flatMap((g) => g.secoes);
  assert.deepEqual(
    achatado.map((s) => s.n),
    SECOES.map((s) => s.n),
    "o sumario nao pode reordenar nem omitir secao",
  );
  const nomes = grupos.map((g) => g.grupo);
  assert.equal(new Set(nomes).size, nomes.length, "grupo repetido = grupo nao contiguo");
});

test("a pagina renderiza exatamente as secoes declaradas", () => {
  const usados = [...PAGINA.matchAll(/<H2 n=\{(\d+)\} \/>/g)].map((m) => Number(m[1]));
  assert.deepEqual(
    usados,
    SECOES.map((s) => s.n),
    "os <H2 n={…}> da pagina precisam bater com SECOES, na mesma ordem",
  );
});

test("nao sobrou <h2> solto sem ancora na pagina", () => {
  // O sumario tem um h2 proprio (id="sumario-titulo"); qualquer outro <h2>
  // literal seria uma secao sem ancora, que e exatamente o defeito corrigido.
  const soltos = [...PAGINA.matchAll(/<h2(?![^>]*id=)/g)];
  assert.equal(soltos.length, 0, "todo titulo de secao deve passar por <H2 n={…}>");
});

test("secao() falha alto em numero inexistente", () => {
  assert.throws(() => secao(0), /não existe/);
  assert.throws(() => secao(SECOES.length + 1), /não existe/);
  assert.equal(secao(1).n, 1);
  assert.equal(secao(SECOES.length).n, SECOES.length);
});
