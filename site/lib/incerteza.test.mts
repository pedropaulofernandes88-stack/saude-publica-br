/**
 * A tela só pode afirmar o que o intervalo autoriza.
 *
 * O comparador desenha duas linhas separadas e, ao lado, escreve se a
 * diferença se sustenta. Essa frase é uma afirmação estatística: se ela errar
 * a direção, o site passa a dizer "iguais" onde o dado só permite dizer "não
 * dá para distinguir" — que é o erro clássico de leitura de IC.
 *
 * Executar: cd site && npm test
 */
import { test } from "node:test";
import assert from "node:assert/strict";

import { intervaloValido, sobrepoe, veredito } from "./incerteza.ts";

test("intervalos separados são distinguíveis", () => {
  assert.equal(veredito({ inf: 100, sup: 200 }, { inf: 300, sup: 400 }), "distinguivel");
  assert.equal(sobrepoe({ inf: 100, sup: 200 }, { inf: 300, sup: 400 }), false);
});

test("intervalos que se cruzam NÃO são distinguíveis", () => {
  assert.equal(veredito({ inf: 100, sup: 300 }, { inf: 200, sup: 400 }), "indistinguivel");
});

test("tocar exatamente na ponta já conta como sobreposição", () => {
  // O caso de borda que decide a frase na tela. `<` no lugar de `<=` faria
  // dois intervalos que encostam serem anunciados como diferença real.
  assert.equal(sobrepoe({ inf: 100, sup: 200 }, { inf: 200, sup: 300 }), true);
  assert.equal(veredito({ inf: 100, sup: 200 }, { inf: 200, sup: 300 }), "indistinguivel");
});

test("um intervalo contido no outro se sobrepõe", () => {
  assert.equal(sobrepoe({ inf: 150, sup: 160 }, { inf: 100, sup: 400 }), true);
});

test("a relação é simétrica — a ordem do par não muda o veredito", () => {
  const a = { inf: 100, sup: 250 };
  const b = { inf: 200, sup: 400 };
  assert.equal(sobrepoe(a, b), sobrepoe(b, a));
  assert.equal(veredito(a, b), veredito(b, a));
});

test("NÃO existe veredito de igualdade — só as duas direções que o IC autoriza", async () => {
  // Se algum dia alguém acrescentar "iguais" ao tipo, este teste cai. É o
  // ponto: sobreposição nunca prova ausência de diferença.
  const mod = await import("./incerteza.ts");
  const nomes = Object.keys(mod);
  assert.ok(!nomes.some((n) => /igual|identic|mesmo/i.test(n)),
            `função que sugere igualdade: ${nomes}`);
  const vs = new Set([
    veredito({ inf: 1, sup: 2 }, { inf: 3, sup: 4 }),
    veredito({ inf: 1, sup: 3 }, { inf: 2, sup: 4 }),
  ]);
  assert.deepEqual([...vs].sort(), ["distinguivel", "indistinguivel"]);
});

test("intervalo invertido é recusado — faixa negativa desenha de cabeça para baixo", () => {
  assert.equal(intervaloValido(200, 100), false);
  assert.equal(intervaloValido(100, 200), true);
  assert.equal(intervaloValido(100, 100), true, "intervalo de largura zero é válido");
});

test("ausente e não numérico são recusados, e não viram zero", () => {
  assert.equal(intervaloValido(null, 200), false);
  assert.equal(intervaloValido(undefined, undefined), false);
  assert.equal(intervaloValido(NaN, 200), false);
  assert.equal(intervaloValido(Infinity, 200), false);
  assert.equal(intervaloValido("100", 200), false, "string não é intervalo");
});
