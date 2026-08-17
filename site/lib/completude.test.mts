/**
 * Invariantes da detecção de meses incompletos.
 *
 * Executar: cd site && npm test
 */
import { test } from "node:test";
import assert from "node:assert/strict";

import {
  LIMIAR_COMPLETUDE,
  construirManifesto,
  incompletosDe,
  mesesIncompletosDaSerie,
  notaCompletude,
} from "./completude.ts";

function p(mes: string, obitos: number, esperado = 100) {
  return { mes_competencia: mes, obitos, esperado };
}

test("serie inteira consolidada nao marca nada", () => {
  const r = mesesIncompletosDaSerie([p("2024-01-01", 100), p("2024-02-01", 98), p("2024-03-01", 105)]);
  assert.deepEqual(r, []);
});

test("cauda parcial e marcada, do mais antigo ao mais recente", () => {
  const r = mesesIncompletosDaSerie([
    p("2024-09-01", 99),
    p("2024-10-01", 80),
    p("2024-11-01", 60),
    p("2024-12-01", 34),
  ]);
  assert.deepEqual(r, ["2024-10-01", "2024-11-01", "2024-12-01"]);
});

test("queda no meio da serie NAO e silenciada", () => {
  // Um mes baixo cercado de meses cheios e sinal epidemiologico, nao atraso.
  const r = mesesIncompletosDaSerie([
    p("2024-01-01", 100),
    p("2024-02-01", 20), // colapso real
    p("2024-03-01", 100),
  ]);
  assert.deepEqual(r, [], "a varredura so pode consumir a cauda");
});

test("o limiar e exatamente LIMIAR_COMPLETUDE (inclusive)", () => {
  const noLimiar = mesesIncompletosDaSerie([p("2024-01-01", 100), p("2024-02-01", LIMIAR_COMPLETUDE * 100)]);
  assert.deepEqual(noLimiar, [], "razao igual ao limiar conta como completo");

  const abaixo = mesesIncompletosDaSerie([p("2024-01-01", 100), p("2024-02-01", LIMIAR_COMPLETUDE * 100 - 1)]);
  assert.deepEqual(abaixo, ["2024-02-01"]);
});

test("esperado zero nao divide por zero nem marca o mes", () => {
  const r = mesesIncompletosDaSerie([p("2024-01-01", 100), { mes_competencia: "2024-02-01", obitos: 0, esperado: 0 }]);
  assert.deepEqual(r, []);
});

test("ordem de entrada nao importa", () => {
  const r = mesesIncompletosDaSerie([p("2024-12-01", 30), p("2024-01-01", 100), p("2024-11-01", 60)]);
  assert.deepEqual(r, ["2024-11-01", "2024-12-01"]);
});

test("manifesto agrega BR a partir das UFs e ignora BR de entrada", () => {
  const m = construirManifesto([
    { uf_sigla: "SP", mes_competencia: "2024-01-01", obitos: 100, esperado: 100 },
    { uf_sigla: "SP", mes_competencia: "2024-02-01", obitos: 40, esperado: 100 },
    { uf_sigla: "RJ", mes_competencia: "2024-01-01", obitos: 100, esperado: 100 },
    { uf_sigla: "RJ", mes_competencia: "2024-02-01", obitos: 95, esperado: 100 },
    // Uma linha "BR" ja agregada na origem nao pode ser contada duas vezes.
    { uf_sigla: "BR", mes_competencia: "2024-02-01", obitos: 1, esperado: 100 },
  ]);
  assert.deepEqual(m.SP, ["2024-02-01"], "SP em 40% esta incompleto");
  assert.deepEqual(m.RJ, [], "RJ em 95% esta completo");
  // BR = (40+95)/(100+100) = 0,675 -> incompleto
  assert.deepEqual(m.BR, ["2024-02-01"]);
});

test("incompletosDe traduz 'Brasil' para a chave BR", () => {
  const m = { BR: ["2024-12-01"], SP: [] };
  assert.equal(incompletosDe(m, "Brasil").has("2024-12-01"), true);
  assert.equal(incompletosDe(m, "BR").has("2024-12-01"), true);
  assert.equal(incompletosDe(m, "SP").size, 0);
  assert.equal(incompletosDe(m, "UF-inexistente").size, 0);
  assert.equal(incompletosDe(null, "Brasil").size, 0, "sem manifesto, nao inventa marcacao");
});

test("nota so aparece quando ha mes incompleto, e concorda em numero", () => {
  assert.equal(notaCompletude(new Set()), "");
  assert.match(notaCompletude(new Set(["2024-12-01"])), /^O último mês está/);
  assert.match(notaCompletude(new Set(["2024-11-01", "2024-12-01"])), /^Os 2 últimos meses estão/);
});
