/**
 * O acesso ao Cemitério Digital falha FECHADO.
 *
 * Em 2026-09-06 `cemiterio.saudeemdado.com` não resolvia. Um link fixo no
 * código teria ido ao ar apontando para o nada — e link quebrado num site que
 * se apresenta como confiável custa mais do que a ausência do link.
 *
 * Executar: cd site && npm test
 */
import { test } from "node:test";
import assert from "node:assert/strict";

import { enderecoDoCemiterio, SUBDOMINIO_SUGERIDO, VARIAVEL } from "./cemiterio.ts";

test("sem variável configurada, não há endereço — e o acesso não aparece", () => {
  assert.equal(enderecoDoCemiterio(undefined), null);
  assert.equal(enderecoDoCemiterio(null), null);
  assert.equal(enderecoDoCemiterio(""), null);
  assert.equal(enderecoDoCemiterio("   "), null);
});

test("endereço https válido é aceito e normalizado sem barra final", () => {
  assert.equal(
    enderecoDoCemiterio("https://cemiterio.saudeemdado.com/"),
    "https://cemiterio.saudeemdado.com",
  );
  assert.equal(
    enderecoDoCemiterio("  https://cemiterio.saudeemdado.com  "),
    "https://cemiterio.saudeemdado.com",
  );
});

test("o subdomínio pode ser outro — o endereço é parâmetro, não constante", () => {
  assert.equal(
    enderecoDoCemiterio("https://obitos.exemplo.org"),
    "https://obitos.exemplo.org",
  );
  assert.equal(
    enderecoDoCemiterio("https://cemiterio.saudeemdado.com:8443"),
    "https://cemiterio.saudeemdado.com:8443",
  );
});

test("http puro é recusado — a ferramenta serve consultas e exportações", () => {
  assert.equal(enderecoDoCemiterio("http://cemiterio.saudeemdado.com"), null);
});

test("credencial embutida na URL é recusada", () => {
  assert.equal(enderecoDoCemiterio("https://user:senha@cemiterio.saudeemdado.com"), null);
  assert.equal(enderecoDoCemiterio("https://chave@cemiterio.saudeemdado.com"), null);
});

test("caminho, query e fragmento são recusados — é a raiz de um serviço", () => {
  assert.equal(enderecoDoCemiterio("https://cemiterio.saudeemdado.com/atlas"), null);
  assert.equal(enderecoDoCemiterio("https://cemiterio.saudeemdado.com/?year=2024"), null);
  assert.equal(enderecoDoCemiterio("https://cemiterio.saudeemdado.com/#mapa"), null);
});

test("lixo não vira link", () => {
  for (const v of ["cemiterio.saudeemdado.com", "javascript:alert(1)", "//exemplo", "https://localhost"]) {
    assert.equal(enderecoDoCemiterio(v), null, `${v} deveria ser recusado`);
  }
});

test("o nome da variável e o subdomínio sugerido estão declarados", () => {
  assert.equal(VARIAVEL, "NEXT_PUBLIC_CEMITERIO_URL");
  assert.equal(SUBDOMINIO_SUGERIDO, "cemiterio.saudeemdado.com");
});

test("nenhum endereço de produção fica embutido no módulo", () => {
  // O sugerido existe como documentação; o que não pode existir é ele virando
  // valor de retorno sem ninguém configurar nada.
  assert.equal(enderecoDoCemiterio(undefined), null);
  assert.notEqual(enderecoDoCemiterio(`https://${SUBDOMINIO_SUGERIDO}`), null);
});
