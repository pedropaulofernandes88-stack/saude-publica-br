/**
 * O guard-rail do boletim semanal, exercitado no sentido em que ele DERRUBA.
 *
 * POR QUE ESTE ARQUIVO EXISTE
 * ---------------------------
 * O boletim é publicado por um job semanal que roda sozinho. As quatro
 * verificações CRÍTICAS de `build-boletim.mjs` — InfoDengue disponível, série
 * histórica de dengue com ao menos 20 UFs, doze meses consolidados de excesso,
 * e mais de um milhão de internações no SIH — existem para transformar
 * degradação silenciosa em falha ruidosa.
 *
 * Nenhuma delas tinha sido vista derrubando nada. A lógica morava dentro de um
 * script linear que termina em `process.exit`, e testá-la exigiria rodar o build
 * inteiro contra três APIs — então ninguém testava.
 *
 * É o mesmo padrão que uma varredura de 2026-09-02 encontrou em 25 guardas do
 * lado Python, e o mais caro dos dois: aqui o consumidor do defeito é o público,
 * não um pipeline interno. Publicar em silêncio um boletim degradado é o único
 * desfecho inaceitável, e é exatamente o que uma guarda quebrada permitiria.
 */
import { test } from "node:test";
import assert from "node:assert/strict";

import { CODIGO_DEGRADADO, avaliar, criarVerificador } from "./verificacao-boletim.ts";

const ok = (nome: string) => ({ nome, ok: true, critico: false, detalhe: "" });
const aviso = (nome: string) => ({ nome, ok: false, critico: false, detalhe: "" });
const critica = (nome: string) => ({ nome, ok: false, critico: true, detalhe: "" });

// ---------------------------------------------------------------------------
// 1. o veredito
// ---------------------------------------------------------------------------

test("falha crítica derruba a execução", () => {
  const v = avaliar([ok("a"), critica("infodengue")]);
  assert.equal(v.codigo, CODIGO_DEGRADADO);
  assert.deepEqual(v.criticas.map((c) => c.nome), ["infodengue"]);
});

test("tudo passando sai com zero", () => {
  assert.equal(avaliar([ok("a"), ok("b")]).codigo, 0);
});

test("aviso não crítico NÃO derruba", () => {
  // A distinção é o que torna o alarme confiável: se aviso derrubasse, o job
  // falharia por cobertura parcial da rede sentinela e alguém aprenderia a
  // ignorar a notificação — e aí a falha crítica também passaria batida.
  const v = avaliar([aviso("rede_sentinela_cobertura_parcial")]);
  assert.equal(v.codigo, 0);
  assert.equal(v.avisos.length, 1);
  assert.equal(v.criticas.length, 0);
});

test("uma crítica no meio de muitos ok basta", () => {
  const v = avaliar([ok("a"), ok("b"), critica("sih"), ok("c"), ok("d")]);
  assert.equal(v.codigo, CODIGO_DEGRADADO);
});

test("críticas e avisos são separados, não somados", () => {
  const v = avaliar([aviso("x"), critica("y"), aviso("z")]);
  assert.equal(v.criticas.length, 1);
  assert.equal(v.avisos.length, 2);
});

test("lista vazia sai com zero", () => {
  // O build pode terminar antes de registrar qualquer verificação. Isso não é
  // degradação, é ausência de sinal — e não deve derrubar.
  assert.equal(avaliar([]).codigo, 0);
});

test("o código de degradação não é 1", () => {
  // 1 é o que o Node devolve para exceção não tratada. Distinguir os dois no log
  // do Actions é o que separa "o boletim degradou" de "o script quebrou" — dois
  // incidentes com respostas diferentes.
  assert.equal(CODIGO_DEGRADADO, 2);
  assert.notEqual(CODIGO_DEGRADADO, 1);
});

// ---------------------------------------------------------------------------
// 2. o acumulador
// ---------------------------------------------------------------------------

test("registrar devolve o próprio ok, para permitir `if (!registrar(...))`", () => {
  const { registrar } = criarVerificador();
  assert.equal(registrar("a", true, "d"), true);
  assert.equal(registrar("b", false, "d", { critico: true }), false);
});

test("registrar acumula na ordem e preserva a forma gravada na edição", () => {
  // A lista vai para dentro do JSON da edição publicada. Mudar a forma quebraria
  // quem lê o boletim, não só o build.
  const { verificacoes, registrar } = criarVerificador();
  registrar("primeira", true, "detalhe 1");
  registrar("segunda", false, "detalhe 2", { critico: true });
  assert.deepEqual(verificacoes, [
    { nome: "primeira", ok: true, critico: false, detalhe: "detalhe 1" },
    { nome: "segunda", ok: false, critico: true, detalhe: "detalhe 2" },
  ]);
});

test("verificação sem opções é NÃO crítica por padrão", () => {
  // O padrão importa: se `critico` viesse true por omissão, qualquer aviso novo
  // passaria a derrubar o job semanal sem que ninguém tivesse pedido.
  const { verificacoes, registrar } = criarVerificador();
  registrar("x", false, "d");
  assert.equal(verificacoes[0].critico, false);
  assert.equal(avaliar(verificacoes).codigo, 0);
});

test("a saída marca FALHA para crítica e aviso para o resto", () => {
  const linhas: string[] = [];
  const { registrar } = criarVerificador((l) => linhas.push(l));
  registrar("a", true, "d");
  registrar("b", false, "d");
  registrar("c", false, "d", { critico: true });
  // A marca de sucesso é "ok  " com dois espaços, para alinhar com "FALHA" e
  // "aviso" na coluna seguinte — somados ao separador do template, são três.
  assert.equal(linhas[0], "[verif] ok   a: d");
  assert.equal(linhas[1], "[verif] aviso b: d");
  assert.equal(linhas[2], "[verif] FALHA c: d");
});
