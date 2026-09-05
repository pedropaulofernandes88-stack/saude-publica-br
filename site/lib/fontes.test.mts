/**
 * Toda tabela publicada tem fonte declarada.
 *
 * O painel de disponibilidade lista uma linha por SISTEMA, e monta a cobertura
 * somando as competências das tabelas de cada um. Uma tabela sem fonte não
 * aparece em linha nenhuma — some do painel sem erro, sem aviso e sem deixar
 * buraco visível.
 *
 * Foi assim que a versão manual daquele painel perdeu metade das fontes: ela
 * não estava errada, estava incompleta, e incompletude não reprova sozinha.
 *
 * Executar: cd site && npm test
 */
import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync, existsSync } from "node:fs";
import path from "node:path";

import { FONTES, FONTE_DA_TABELA, HORIZONTE_DE_PROJECAO, fonte } from "./fontes.ts";
import type { Manifesto } from "./manifesto.ts";

const DIR = path.join(process.cwd(), "..", "data", "publicacoes");

function manifesto(): Manifesto | null {
  const ponteiro = path.join(DIR, "atual.json");
  if (!existsSync(ponteiro)) return null;
  const { arquivo } = JSON.parse(readFileSync(ponteiro, "utf8")) as { arquivo: string };
  return JSON.parse(readFileSync(path.join(DIR, arquivo), "utf8")) as Manifesto;
}

test("ids de fonte são únicos", () => {
  const ids = FONTES.map((f) => f.id);
  assert.equal(new Set(ids).size, ids.length);
});

test("toda tabela do manifesto tem fonte declarada", (t) => {
  const m = manifesto();
  if (!m) return t.skip("data/publicacoes/atual.json ausente");
  const semFonte = Object.keys(m.tabelas).filter((n) => !FONTE_DA_TABELA[n]).sort();
  assert.deepEqual(
    semFonte,
    [],
    "tabela publicada sem fonte: ela sumiria do painel de disponibilidade sem avisar. "
      + "Classifique em FONTE_DA_TABELA (use 'derivado' para dimensão de apoio).",
  );
});

test("toda fonte citada em FONTE_DA_TABELA existe em FONTES", () => {
  const ids = new Set(FONTES.map((f) => f.id));
  const invalidas = [...new Set(Object.values(FONTE_DA_TABELA))].filter((f) => !ids.has(f)).sort();
  assert.deepEqual(invalidas, []);
});

test("nenhuma fonte declarada fica sem tabela — linha vazia é ruído", (t) => {
  const m = manifesto();
  if (!m) return t.skip("data/publicacoes/atual.json ausente");
  const usadas = new Set(
    Object.keys(m.tabelas).map((n) => FONTE_DA_TABELA[n]).filter(Boolean),
  );
  const ociosas = FONTES.filter((f) => !usadas.has(f.id)).map((f) => f.id);
  assert.deepEqual(ociosas, []);
});

test("toda fonte declara observação — é o que o painel não deriva", () => {
  const mudas = FONTES.filter((f) => !f.observacao.trim()).map((f) => f.id);
  assert.deepEqual(mudas, []);
});

test("a guarda reprova tabela nova sem classificação — vista reprovando", () => {
  const inventada = "mart_tabela_recem_publicada";
  assert.ok(!FONTE_DA_TABELA[inventada], "o nome de controle não pode existir de verdade");
  const semFonte = [inventada].filter((n) => !FONTE_DA_TABELA[n]);
  assert.equal(semFonte.length, 1, "a mesma checagem do teste acima aprovaria o painel incompleto");
});

test("tabela de projeção existe no manifesto — senão a exclusão é letra morta", (t) => {
  const m = manifesto();
  if (!m) return t.skip("data/publicacoes/atual.json ausente");
  const fantasmas = [...HORIZONTE_DE_PROJECAO].filter((n) => !m.tabelas[n]);
  assert.deepEqual(
    fantasmas,
    [],
    "nome em HORIZONTE_DE_PROJECAO que não está publicado: a exclusão não exclui nada "
      + "e a próxima tabela de previsão voltaria a poluir a cobertura em silêncio",
  );
});

test("fonte() devolve null para id desconhecido", () => {
  assert.equal(fonte("nao-existe"), null);
  assert.ok(fonte("sim"));
});
