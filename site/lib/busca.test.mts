/**
 * Invariantes da busca municipal.
 *
 * O caso que motivou o módulo é o primeiro teste: `"Penapolis"` sem acento
 * precisa encontrar Penápolis. Ele falhava no painel enquanto o mesmo conserto
 * existia, copiado, em duas outras páginas.
 *
 * Executar: cd site && npm test   (runner nativo do Node, sem dependências)
 */
import { test } from "node:test";
import assert from "node:assert/strict";

import { casaMunicipio, semAcento } from "./busca.ts";

const PENAPOLIS = { nome: "Penápolis", cod: "353730" };

test("acento não é obrigatório na busca — o defeito que originou o módulo", () => {
  assert.ok(casaMunicipio("Penapolis", PENAPOLIS.nome, PENAPOLIS.cod));
  assert.ok(casaMunicipio("penapolis", PENAPOLIS.nome, PENAPOLIS.cod));
  assert.ok(casaMunicipio("PENÁPOLIS", PENAPOLIS.nome, PENAPOLIS.cod));
  assert.ok(casaMunicipio("  penápolis  ", PENAPOLIS.nome, PENAPOLIS.cod));
});

test("acento também não atrapalha quando o usuário o digita", () => {
  assert.ok(casaMunicipio("São Paulo", "São Paulo", "355030"));
  assert.ok(casaMunicipio("sao paulo", "São Paulo", "355030"));
  assert.ok(casaMunicipio("Sao Goncalo", "São Gonçalo", "330490"));
});

test("busca parcial continua funcionando", () => {
  assert.ok(casaMunicipio("pena", PENAPOLIS.nome, PENAPOLIS.cod));
  assert.ok(casaMunicipio("polis", PENAPOLIS.nome, PENAPOLIS.cod));
});

test("termo vazio casa com tudo, para o filtro não ter de testar antes", () => {
  assert.ok(casaMunicipio("", PENAPOLIS.nome, PENAPOLIS.cod));
  assert.ok(casaMunicipio("   ", PENAPOLIS.nome, PENAPOLIS.cod));
});

test("código IBGE de 6 e de 7 dígitos encontram o mesmo município", () => {
  assert.ok(casaMunicipio("353730", PENAPOLIS.nome, PENAPOLIS.cod), "código de 6 dígitos");
  assert.ok(casaMunicipio("3537305", PENAPOLIS.nome, PENAPOLIS.cod), "código de 7 dígitos do IBGE");
  assert.ok(casaMunicipio("3537", PENAPOLIS.nome, PENAPOLIS.cod), "prefixo do código");
});

test("código de outro município não casa", () => {
  assert.ok(!casaMunicipio("355030", PENAPOLIS.nome, PENAPOLIS.cod));
  assert.ok(!casaMunicipio("3550308", PENAPOLIS.nome, PENAPOLIS.cod));
});

test("nome sem correspondência não casa", () => {
  assert.ok(!casaMunicipio("Campinas", PENAPOLIS.nome, PENAPOLIS.cod));
});

test("município sem nome não quebra a busca por texto", () => {
  assert.ok(!casaMunicipio("qualquer", null, "353730"));
  assert.ok(casaMunicipio("353730", null, "353730"), "e o código ainda encontra");
});

test("semAcento é minúscula, sem acento e sem espaço nas pontas", () => {
  assert.equal(semAcento("  Penápolis "), "penapolis");
  assert.equal(semAcento("ÁÉÍÓÚÃÕÇ"), "aeiouaoc");
});
