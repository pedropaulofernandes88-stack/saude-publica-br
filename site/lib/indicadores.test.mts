/**
 * O catálogo de indicadores continua descrevendo o que existe.
 *
 * POR QUE ESTE TESTE EXISTE
 * -------------------------
 * A ficha de indicador junta três fontes: texto editorial daqui, fatos do
 * manifesto de publicação e a seção correspondente da metodologia. Duas dessas
 * ligações são por NOME — o nome da tabela e o slug da seção — e nome quebra em
 * silêncio: a ficha mostraria "—" no lugar da competência, ou um link para uma
 * âncora que não existe mais, e ninguém veria até alguém reclamar.
 *
 * É o mesmo motivo de `test_manuscrito.py` conferir tabela contra CSV. Ligação
 * por nome sem regressão é ligação que já quebrou e ninguém sabe.
 *
 * Executar: cd site && npm test
 */
import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync, existsSync } from "node:fs";
import path from "node:path";

import { INDICADORES, indicador } from "./indicadores.ts";
import { SECOES, tituloDoSlug } from "./metodologia-secoes.ts";
import { periodoCoberto, type Manifesto } from "./manifesto.ts";

/**
 * O manifesto vem de `data/publicacoes/`, e não de `public/sdata/manifesto.json`.
 *
 * O JSON servido é DERIVADO — o prebuild o reescreve — e no CI os testes rodam
 * ANTES do build. Conferir contra o derivado validaria a cópia da última vez
 * que alguém rodou o prebuild, não a publicação corrente: bastaria publicar uma
 * tabela nova e esquecer o prebuild para o teste aprovar um catálogo que aponta
 * para o passado. A camada canônica não tem esse intervalo.
 */
const CAMINHO = path.join(process.cwd(), "..", "data", "publicacoes");

function manifesto(): Manifesto | null {
  const ponteiro = path.join(CAMINHO, "atual.json");
  if (!existsSync(ponteiro)) return null;
  const { arquivo } = JSON.parse(readFileSync(ponteiro, "utf8")) as { arquivo: string };
  return JSON.parse(readFileSync(path.join(CAMINHO, arquivo), "utf8")) as Manifesto;
}

test("ids são únicos — o id entra em âncora e citação", () => {
  const ids = INDICADORES.map((i) => i.id);
  assert.equal(new Set(ids).size, ids.length, `ids repetidos em: ${ids.join(", ")}`);
});

test("todo indicador aponta para uma seção que existe na metodologia", () => {
  const slugs = new Set(SECOES.map((s) => s.slug));
  const orfas = INDICADORES.filter((i) => !slugs.has(i.secao));
  assert.deepEqual(
    orfas.map((i) => `${i.id} → ${i.secao}`),
    [],
    "seção renomeada ou removida: o link da ficha levaria a uma âncora inexistente",
  );
});

test("cada seção citada tem título — é o texto do link da ficha", () => {
  for (const i of INDICADORES) {
    assert.ok(tituloDoSlug(i.secao), `sem título para ${i.secao}`);
  }
});

test("todo indicador declara ao menos uma limitação", () => {
  // O campo mais importante da ficha. Um indicador sem limitação declarada é
  // quase sempre um indicador cujas limitações ninguém escreveu — não um sem
  // limitações.
  const vazios = INDICADORES.filter((i) => i.limitacoes.length === 0).map((i) => i.id);
  assert.deepEqual(vazios, []);
});

test("razão declara denominador; contagem não declara", () => {
  for (const i of INDICADORES) {
    const ehRazao = /por 100 mil|%|razão/.test(i.unidade);
    if (ehRazao) {
      assert.ok(i.denominador, `${i.id}: unidade de razão sem denominador declarado`);
    }
  }
});

test("indicador() lança em id desconhecido, para o erro aparecer no build", () => {
  assert.throws(() => indicador("nao-existe"), /indicador desconhecido/);
});

test("toda tabela citada existe no manifesto publicado", (t) => {
  const m = manifesto();
  if (!m) return t.skip("data/publicacoes/atual.json ausente");
  const ausentes = INDICADORES
    .filter((i) => !m.tabelas[i.tabela])
    .map((i) => `${i.id} → ${i.tabela}`);
  assert.deepEqual(
    ausentes,
    [],
    "tabela citada não está na publicação corrente: a ficha mostraria competência vazia",
  );
});

test("a guarda reprova tabela inexistente — vista reprovando, não suposta", () => {
  const m = manifesto();
  assert.ok(m, "sem manifesto não há o que conferir");
  assert.ok(!m!.tabelas["mart_que_nao_existe"], "o nome de controle não pode existir de verdade");
  const ausentes = [{ id: "controle", tabela: "mart_que_nao_existe" }]
    .filter((i) => !m!.tabelas[i.tabela]);
  assert.equal(ausentes.length, 1, "a mesma checagem do teste acima aprovaria um catálogo quebrado");
});

test("periodoCoberto resume a competência sem inventar", () => {
  assert.equal(periodoCoberto(null), null);
  const base = { linhas: 1, publicada_em: null, servida: true, sha256: null };
  assert.equal(periodoCoberto({ ...base, competencia_min: null, competencia_max: null }), null);
  assert.equal(periodoCoberto({ ...base, competencia_min: "2015", competencia_max: "2025" }), "2015–2025");
  assert.equal(periodoCoberto({ ...base, competencia_min: "2024-01", competencia_max: "2024-12" }), "2024");
});
