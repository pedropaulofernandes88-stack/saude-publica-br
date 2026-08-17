/**
 * Invariantes da contagem de municípios.
 *
 * Executar: cd site && npm test   (usa o runner nativo do Node, sem dependências)
 */
import { test } from "node:test";
import assert from "node:assert/strict";

import {
  TOTAL_MUNICIPIOS_IBGE,
  UF_NAO_IDENTIFICADA,
  ehCodigoAgregado,
  municipioIdentificado,
  particionarMunicipios,
  type LinhaMunicipal,
} from "./municipios.ts";

function linha(over: Partial<LinhaMunicipal> = {}): LinhaMunicipal {
  return { municipio_cod: "355030", municipio_nome: "São Paulo", uf_sigla: "SP", obitos: 10, ...over };
}

/**
 * Os 23 códigos agregados que o mart devolve para o Brasil em 2024, lidos da
 * API pública (uf_sigla=eq.ND) e não inventados.
 */
const CODIGOS_AGREGADOS_2024 = [
  "110000", "130000", "140000", "150000", "170000", "210000", "220000", "230000",
  "240000", "250000", "260000", "270000", "290000", "310000", "320000", "330000",
  "350000", "410000", "420000", "430000", "500000", "510000", "520000",
];

test("codigo agregado: UF + 0000 e reconhecido", () => {
  for (const cod of CODIGOS_AGREGADOS_2024) {
    assert.equal(ehCodigoAgregado(cod), true, `${cod} deveria ser agregado`);
  }
});

test("codigo agregado: municipio real nao e confundido", () => {
  for (const cod of ["355030", "330455", "230440", "500270", "110020"]) {
    assert.equal(ehCodigoAgregado(cod), false, `${cod} nao e agregado`);
  }
});

test("municipio identificado exige codigo, UF e nome", () => {
  assert.equal(municipioIdentificado(linha()), true);
  assert.equal(municipioIdentificado(linha({ municipio_cod: "350000" })), false);
  assert.equal(municipioIdentificado(linha({ uf_sigla: UF_NAO_IDENTIFICADA })), false);
  assert.equal(municipioIdentificado(linha({ municipio_nome: null })), false);
  assert.equal(municipioIdentificado(linha({ municipio_nome: "" })), false);
});

test("particao nao perde linha nem obito", () => {
  const linhas = [
    linha({ municipio_cod: "355030", obitos: 100 }),
    linha({ municipio_cod: "350000", municipio_nome: null, uf_sigla: "ND", obitos: 344 }),
    linha({ municipio_cod: "330455", obitos: 50 }),
  ];
  const p = particionarMunicipios(linhas);
  assert.equal(p.identificados.length + p.naoIdentificados.length, linhas.length);
  const somaTotal = linhas.reduce((s, l) => s + l.obitos, 0);
  const somaParticao =
    p.identificados.reduce((s, l) => s + l.obitos, 0) + p.obitosNaoIdentificados;
  assert.equal(somaParticao, somaTotal, "obitos precisam continuar fechando");
});

test("obitos nao identificados sao somados, nao descartados", () => {
  const p = particionarMunicipios([
    linha({ municipio_cod: "350000", municipio_nome: null, uf_sigla: "ND", obitos: 344 }),
    linha({ municipio_cod: "330000", municipio_nome: null, uf_sigla: "ND", obitos: 666 }),
    linha({ municipio_cod: "355030", obitos: 1 }),
  ]);
  assert.equal(p.obitosNaoIdentificados, 1010);
  assert.equal(p.identificados.length, 1);
});

test("invariante: municipios contados nunca excedem a dimensao IBGE", () => {
  // Reproduz o recorte real Brasil/2024/TOTAL: 5.593 linhas do mart.
  const reais = Array.from({ length: 5570 }, (_, i) => {
    const cod = String(110001 + i);
    return linha({ municipio_cod: cod, municipio_nome: `Municipio ${i}`, uf_sigla: "SP", obitos: 1 });
  });
  const agregados = CODIGOS_AGREGADOS_2024.map((cod) =>
    linha({ municipio_cod: cod, municipio_nome: null, uf_sigla: "ND", obitos: 10 }),
  );

  const p = particionarMunicipios([...reais, ...agregados]);

  assert.equal(p.identificados.length, 5570, "os 5.570 nomeados de 2024");
  assert.equal(p.naoIdentificados.length, 23, "os 23 codigos agregados de 2024");
  assert.equal(p.obitosNaoIdentificados, 230);
  assert.ok(
    p.identificados.length <= TOTAL_MUNICIPIOS_IBGE,
    `contagem (${p.identificados.length}) excedeu o teto IBGE (${TOTAL_MUNICIPIOS_IBGE})`,
  );
});

test("invariante: lista so de agregados conta zero municipio", () => {
  const p = particionarMunicipios(
    CODIGOS_AGREGADOS_2024.map((cod) =>
      linha({ municipio_cod: cod, municipio_nome: null, uf_sigla: "ND", obitos: 5 }),
    ),
  );
  assert.equal(p.identificados.length, 0);
  assert.equal(p.obitosNaoIdentificados, 115);
});
