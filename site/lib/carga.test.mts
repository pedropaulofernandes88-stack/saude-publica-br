/**
 * Falha e ausência não podem produzir a mesma tela.
 *
 * O site tinha 60 pontos de `catch`, muitos deles `catch(() => {})`: a consulta
 * falhava, o componente virava `null` e sumia — exatamente como quando o
 * município não tem aquele dado. No boletim isso fazia a página afirmar, pela
 * ausência de quatro cartões, que o município não tem contexto social nem
 * internações evitáveis.
 *
 * Executar: cd site && npm test
 */
import { test } from "node:test";
import assert from "node:assert/strict";

import { mensagemDeErro, type Carga } from "./carga.ts";

test("erro de rede vira mensagem que diz o que houve, não a pilha", () => {
  assert.equal(mensagemDeErro(new TypeError("Failed to fetch")), "sem conexão com a API");
  assert.equal(mensagemDeErro(new Error("mart_x: HTTP 503 upstream")), "a API respondeu HTTP 503");
});

test("erro desconhecido é truncado, nunca descartado", () => {
  const longo = "x".repeat(400);
  const m = mensagemDeErro(new Error(longo));
  assert.ok(m.length <= 120 && m.length > 0, "mensagem some ou vaza inteira");
});

test("os quatro estados são mutuamente exclusivos no tipo", () => {
  // Se um estado novo entrar em `Carga` sem tratamento, este switch deixa de
  // ser exaustivo e o TypeScript reprova na compilação — que é o ponto do tipo.
  const rotular = (c: Carga<number[]>): string => {
    switch (c.estado) {
      case "carregando": return "esqueleto";
      case "ok": return `${c.dados.length} linhas`;
      case "vazio": return "sem dado para o recorte";
      case "erro": return `falhou: ${c.mensagem}`;
    }
  };
  assert.equal(rotular({ estado: "carregando" }), "esqueleto");
  assert.equal(rotular({ estado: "ok", dados: [1, 2] }), "2 linhas");
  assert.equal(rotular({ estado: "vazio" }), "sem dado para o recorte");
  assert.equal(rotular({ estado: "erro", mensagem: "sem conexão com a API" }),
               "falhou: sem conexão com a API");
});

test("vazio e erro são estados DIFERENTES — é a razão de o tipo existir", () => {
  const vazio: Carga<number[]> = { estado: "vazio" };
  const erro: Carga<number[]> = { estado: "erro", mensagem: "sem conexão com a API" };
  assert.notEqual(vazio.estado, erro.estado);
});
