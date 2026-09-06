/**
 * O arquivo que sai daqui tem que se explicar sozinho.
 *
 * Um CSV baixado vira anexo de e-mail, entra numa pasta compartilhada e é
 * aberto meses depois por quem não fez a consulta. Estes testes fixam o que
 * precisa estar dentro dele: o recorte, a fonte com versão, a licença, a
 * citação, e a diferença entre ausência e zero.
 *
 * Executar: cd site && npm test
 */
import { test } from "node:test";
import assert from "node:assert/strict";

import { cabecalho, celula, linhaDaTabela, nomeDeArquivo, paraCsv, SEP } from "./exportar.ts";
import { type Manifesto } from "./manifesto.ts";

const AGORA = new Date("2026-09-06T11:00:00Z");

const MANIFESTO: Manifesto = {
  id: "2026-09-06",
  gerado_em: "2026-09-06 11:16 UTC",
  commit: "c430183",
  tabelas: {
    mart_icsap_pares: {
      linhas: 22280,
      competencia_min: "2021",
      competencia_max: "2024",
      publicada_em: "2026-09-06",
      servida: true,
      sha256: "42fef0b836b4dab50652c6ed95d5b8b2f08e7968e4375da1df2fe134878ed073",
    },
  },
};

const RECORTE = {
  titulo: "Internações evitáveis — pares do estrato",
  filtros: [["UF", "SP"], ["Ano", "2024"]] as [string, string][],
  tabelas: ["mart_icsap_pares"],
  url: "https://saudeemdado.com/boletim/?m=353730",
};

test("o cabeçalho carrega recorte, fonte, licença e citação", () => {
  const h = cabecalho(RECORTE, MANIFESTO, "Fernandes, P. P. Saúde em Dado.", AGORA).join("\n");
  assert.match(h, /RECORTE/);
  assert.match(h, /UF: SP/);
  assert.match(h, /Ano: 2024/);
  assert.match(h, /FONTE/);
  assert.match(h, /LICENÇA/);
  assert.match(h, /CC BY 4\.0/);
  assert.match(h, /COMO CITAR/);
  assert.match(h, /Fernandes, P\. P\./);
  assert.match(h, /saudeemdado\.com\/boletim/);
  assert.match(h, /Acesso em: 2026-09-06/);
});

test("toda linha do cabeçalho é comentário — nenhuma vaza para a tabela", () => {
  for (const l of cabecalho(RECORTE, MANIFESTO, "cit", AGORA)) {
    assert.ok(l.startsWith("#"), `linha sem # vazaria como dado: ${JSON.stringify(l)}`);
  }
});

test("a linha da fonte é DERIVADA: sistema, período e versão da publicação", () => {
  const l = linhaDaTabela("mart_icsap_pares", MANIFESTO);
  assert.match(l, /mart_icsap_pares/);
  assert.match(l, /SIH/, "o sistema de origem sai de lib/fontes.ts");
  assert.match(l, /2021–2024/, "o período sai do manifesto");
  assert.match(l, /publicação 2026-09-06/);
  assert.match(l, /sha256 42fef0b836b4…/);
});

test("tabela ausente do manifesto não derruba a exportação, só informa menos", () => {
  const l = linhaDaTabela("mart_icsap_pares", null);
  assert.match(l, /mart_icsap_pares/);
  assert.ok(!l.includes("publicação"), "sem manifesto não há versão a afirmar");
});

test("recorte sem filtro DIZ que não há filtro, em vez de omitir a seção", () => {
  const h = cabecalho({ ...RECORTE, filtros: [] }, MANIFESTO, "cit", AGORA).join("\n");
  assert.match(h, /RECORTE/);
  assert.match(h, /sem filtros/);
});

test("filtro vazio não vira linha — 'Sexo: ' sugeriria um filtro que não houve", () => {
  const h = cabecalho(
    { ...RECORTE, filtros: [["UF", "SP"], ["Sexo", ""], ["Capítulo", null]] },
    MANIFESTO, "cit", AGORA,
  ).join("\n");
  assert.match(h, /UF: SP/);
  assert.ok(!h.includes("Sexo:"), "filtro vazio não pode aparecer");
  assert.ok(!h.includes("Capítulo:"), "filtro nulo não pode aparecer");
});

test("ausência e zero são distinguidos no arquivo, e a regra está escrita nele", () => {
  const csv = paraCsv(
    RECORTE, ["municipio", "obitos"],
    [["Sem dado", null], ["Zero medido", 0]],
    MANIFESTO, "cit", AGORA,
  );
  assert.match(csv, /célula vazia = sem dado publicado/);
  assert.match(csv, /0 = medido e igual a zero/);
  const linhas = csv.split("\r\n");
  assert.ok(linhas.includes(`Sem dado${SEP}`), "null tem que sair vazio");
  assert.ok(linhas.includes(`Zero medido${SEP}0`), "zero tem que sair 0");
});

test("célula com o separador dentro é escapada — senão desloca a linha inteira", () => {
  assert.equal(celula("Santana do Livramento; RS"), '"Santana do Livramento; RS"');
  assert.equal(celula('aspas " dentro'), '"aspas "" dentro"');
  assert.equal(celula("quebra\nlinha"), '"quebra\nlinha"');
  assert.equal(celula("simples"), "simples");
});

test("null vira vazio e zero vira 0 — a distinção é do tipo, não do formato", () => {
  assert.equal(celula(null), "");
  assert.equal(celula(undefined), "");
  assert.equal(celula(0), "0");
  assert.equal(celula(false), "false");
});

test("o cabeçalho ensina a ler o próprio arquivo", () => {
  const h = cabecalho(RECORTE, MANIFESTO, "cit", AGORA).join("\n");
  assert.match(h, /comment="#"/, "quem carregar em pandas precisa da dica");
  assert.match(h, /comment\.char="#"/);
});

test("a tabela começa depois do cabeçalho, e o cabeçalho vem antes das colunas", () => {
  const csv = paraCsv(RECORTE, ["a", "b"], [[1, 2]], MANIFESTO, "cit", AGORA);
  const linhas = csv.split("\r\n");
  const iCol = linhas.indexOf(`a${SEP}b`);
  assert.ok(iCol > 0, "a linha de colunas tem que existir");
  assert.ok(linhas.slice(0, iCol).every((l) => l === "" || l.startsWith("#")),
            "nada além de comentário pode preceder as colunas");
  assert.equal(linhas[iCol + 1], `1${SEP}2`);
});

test("o nome do arquivo carrega o recorte e a data, sem acento nem espaço", () => {
  const n = nomeDeArquivo("mortalidade", [["UF", "SP"], ["Capítulo", "Doenças do aparelho"]], AGORA);
  assert.equal(n, "mortalidade_sp_doencas-do-aparelho_2026-09-06.csv");
  assert.ok(!/[^\x20-\x7e]/.test(n), "nome com caractere não-ASCII quebra em algum sistema");
});

test("nome de arquivo ignora filtro vazio em vez de deixar '__'", () => {
  assert.equal(nomeDeArquivo("painel", [["UF", ""], ["Ano", "2024"]], AGORA),
               "painel_2024_2026-09-06.csv");
});

test("sistema igual ao órgão não vira 'IBGE (IBGE)'", () => {
  // `dim_ivs` vem do IBGE, que é sistema e órgão ao mesmo tempo. Apareceu no
  // rodapé impresso do boletim, não em teste — daí este.
  const l = linhaDaTabela("dim_ivs", null);
  assert.ok(!/IBGE \(IBGE\)/.test(l), `parêntese redundante: ${l}`);
  assert.match(l, /IBGE/);
});
