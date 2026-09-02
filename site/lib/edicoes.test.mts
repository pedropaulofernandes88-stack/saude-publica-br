/**
 * Seleção de edição do boletim, exercitada nos dois sentidos.
 *
 * As três guardas cobertas aqui — índice vazio no build-alertas, índice vazio no
 * build-feed, e edição inexistente — derrubam jobs que rodam sozinhos, e nenhuma
 * tinha sido vista derrubando nada. Não por descuido: `npm test` roda
 * `node --test "lib/**\/*.test.mts"` e nada em `scripts/` é alcançável pela
 * suíte, então a única forma de testá-las era tirar a decisão de dentro do
 * script.
 *
 * O caso que mais importa aqui não é o erro, é o ACERTO silencioso: qual edição
 * é a anterior. Errar isso não quebra nada visível — o build roda, compara duas
 * edições reais e publica alertas invertidos.
 */
import { test } from "node:test";
import assert from "node:assert/strict";

import { exigirEdicoes, selecionarEdicao } from "./edicoes.ts";

/** Índice como o `index.json` real: do mais NOVO para o mais antigo. */
const INDICE = [
  { edicao: "2026-se30" },
  { edicao: "2026-se29" },
  { edicao: "2026-se28" },
];

// ---------------------------------------------------------------------------
// 1. as guardas que derrubam
// ---------------------------------------------------------------------------

test("índice vazio é erro, não edição zero", () => {
  const r = exigirEdicoes([]);
  assert.equal(r.ok, false);
  assert.match(r.ok === false ? r.erro : "", /nenhuma edição publicada/);
});

test("índice vazio também derruba a seleção", () => {
  const r = selecionarEdicao([]);
  assert.equal(r.ok, false);
});

test("edição pedida que não existe é erro, não volta ao padrão", () => {
  // Cair no padrão em silêncio seria o pior desfecho: o job geraria alertas da
  // semana errada e reportaria sucesso.
  const r = selecionarEdicao(INDICE, "2026-se99");
  assert.equal(r.ok, false);
  assert.match(r.ok === false ? r.erro : "", /2026-se99 não encontrada/);
});

test("índice com edições passa", () => {
  assert.equal(exigirEdicoes(INDICE).ok, true);
});

// ---------------------------------------------------------------------------
// 2. o acerto silencioso: qual é a anterior
// ---------------------------------------------------------------------------

test("sem alvo, usa a mais recente e compara com a de antes", () => {
  const r = selecionarEdicao(INDICE);
  assert.equal(r.ok, true);
  if (r.ok) {
    assert.equal(r.atual, "2026-se30");
    assert.equal(r.anterior, "2026-se29");
  }
});

test("a anterior é i+1 porque o índice desce do mais novo", () => {
  // Inverter para i-1 não quebraria nada de forma visível: o build compararia
  // duas edições reais, só que na ordem errada, e todo "novo" ou "agravado" da
  // semana sairia invertido.
  const r = selecionarEdicao(INDICE, "2026-se29");
  assert.equal(r.ok, true);
  if (r.ok) {
    assert.equal(r.atual, "2026-se29");
    assert.equal(r.anterior, "2026-se28");
    assert.equal(r.indice, 1);
  }
});

test("a edição mais antiga não tem anterior", () => {
  // Sem o `?? null`, `index[i + 1].edicao` estouraria. Com um `?? index[0]` no
  // lugar, a mais antiga se compararia com a mais NOVA e reportaria mudança em
  // quase tudo.
  const r = selecionarEdicao(INDICE, "2026-se28");
  assert.equal(r.ok, true);
  if (r.ok) assert.equal(r.anterior, null);
});

test("índice com uma edição só seleciona sem anterior", () => {
  // A primeira edição publicada na história do boletim. Todo município em alerta
  // é legitimamente "novo" — mas isso tem de vir de `anterior: null`, não de uma
  // comparação com lixo.
  const r = selecionarEdicao([{ edicao: "2026-se30" }]);
  assert.equal(r.ok, true);
  if (r.ok) {
    assert.equal(r.atual, "2026-se30");
    assert.equal(r.anterior, null);
  }
});
