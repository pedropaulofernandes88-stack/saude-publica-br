/**
 * build-rede-sentinela.mjs — define a rede sentinela de vigilância de arboviroses.
 *
 * NÃO roda toda semana. A composição da rede depende de população (anual) e de
 * carga histórica de dengue (anual), então é gerada sob demanda e COMMITADA —
 * assim a rede fica auditável e o boletim semanal não precisa recalculá-la.
 *
 * Critérios de inclusão (um município entra se satisfizer qualquer um):
 *   1. capital        — as 27 capitais, garantindo cobertura geográfica de todas as UFs
 *   2. populacao      — população ≥ 100 mil (cobertura populacional)
 *   3. risco_dengue   — entre os de maior incidência de dengue no último ano fechado,
 *                       com população ≥ 20 mil (evita taxa instável de denominador pequeno)
 *
 * O critério 3 existe porque ranking puro por população perde a cidade média com
 * surto explosivo — que é exatamente onde a dengue costuma estourar no Brasil.
 *
 * O InfoDengue usa o código IBGE de 7 dígitos; os marts do projeto usam 6. O de
 * 7 vem da API de localidades do IBGE e o casamento é feito pelo prefixo de 6.
 *
 * Uso:  node site/scripts/build-rede-sentinela.mjs [--pop-min 100000] [--risco 150]
 */
import { mkdir, writeFile } from "node:fs/promises";
import path from "node:path";

const BASE =
  process.env.NEXT_PUBLIC_SUPABASE_URL ?? "https://zekjhmxjamatlxpkykde.supabase.co";
const KEY =
  process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY ??
  "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Inpla2pobXhqYW1hdGx4cGt5a2RlIiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODEwNzY4MzIsImV4cCI6MjA5NjY1MjgzMn0.px8FcU0QK8w9v95kwGlGzASKpY3drsxAvFe0e6wUoCU";

const HEADERS = { apikey: KEY, Authorization: `Bearer ${KEY}` };
const PAGE = 1000;

async function rest(table, params) {
  const rows = [];
  let offset = 0;
  for (;;) {
    const qs = new URLSearchParams(params).toString();
    const res = await fetch(`${BASE}/rest/v1/${table}?${qs}`, {
      headers: { ...HEADERS, "Range-Unit": "items", Range: `${offset}-${offset + PAGE - 1}` },
    });
    if (!res.ok) throw new Error(`${table}: HTTP ${res.status} ${await res.text()}`);
    const chunk = await res.json();
    rows.push(...chunk);
    if (chunk.length < PAGE) break;
    offset += PAGE;
  }
  return rows;
}

const arg = (nome, padrao) => {
  const i = process.argv.indexOf(`--${nome}`);
  return i > -1 ? Number(process.argv[i + 1]) : padrao;
};
const POP_MIN = arg("pop-min", 100_000);
const TOP_RISCO = arg("risco", 150);
const POP_MIN_RISCO = 20_000;

// Códigos IBGE de 6 dígitos das 27 capitais (o de 7 vem do IBGE adiante).
const CAPITAIS_6 = new Set([
  "120040", "270430", "160030", "130260", "292740", "230440", "530010", "320530",
  "520870", "211130", "510340", "500270", "310620", "150140", "250750", "410690",
  "261160", "221100", "330455", "240810", "431490", "110020", "140010", "420540",
  "355030", "280030", "172100",
]);

console.log("[rede] baixando lista de municípios do IBGE (códigos de 7 dígitos)…");
const ibgeRes = await fetch("https://servicodados.ibge.gov.br/api/v1/localidades/municipios", {
  signal: AbortSignal.timeout(120_000),
});
if (!ibgeRes.ok) throw new Error(`IBGE: HTTP ${ibgeRes.status}`);
const ibge = await ibgeRes.json();
// prefixo de 6 dígitos -> { geocode7, nome, uf }
const porCod6 = new Map(
  ibge.map((m) => [
    String(m.id).slice(0, 6),
    { geocode: String(m.id), nome: m.nome, uf: m.microrregiao?.mesorregiao?.UF?.sigla ?? null },
  ]),
);
console.log(`[rede]   ${ibge.length} municípios`);

console.log("[rede] população (último ano do mart de mortalidade)…");
const anoPop = (await rest("mart_mortalidade_municipio", {
  select: "ano", capitulo_cid: "eq.TOTAL", sexo: "eq.TOTAL", order: "ano.desc", limit: "1",
}))[0].ano;
const pops = await rest("mart_mortalidade_municipio", {
  select: "municipio_cod,municipio_nome,uf_sigla,regiao,populacao",
  ano: `eq.${anoPop}`, capitulo_cid: "eq.TOTAL", sexo: "eq.TOTAL",
  order: "municipio_cod",
});
const popPorCod = new Map(pops.map((p) => [p.municipio_cod, p]));
console.log(`[rede]   ${pops.length} municípios com população (${anoPop})`);

console.log("[rede] incidência de dengue (último ano fechado)…");
const anoDengue = (await rest("mart_dengue_municipio_ano", {
  select: "ano_epi", order: "ano_epi.desc", limit: "1",
}))[0].ano_epi;
const dengue = await rest("mart_dengue_municipio_ano", {
  select: "municipio_cod,incidencia_100k,casos_provaveis,populacao",
  ano_epi: `eq.${anoDengue}`, order: "municipio_cod",
});
console.log(`[rede]   ${dengue.length} municípios com dengue (${anoDengue})`);

// ── Composição ─────────────────────────────────────────────────────────────
const rede = new Map(); // cod6 -> registro

function incluir(cod6, motivo) {
  const geo = porCod6.get(cod6);
  const pop = popPorCod.get(cod6);
  if (!geo || !geo.uf) return false; // sem código de 7 dígitos não dá para consultar
  const existente = rede.get(cod6);
  if (existente) {
    if (!existente.motivos.includes(motivo)) existente.motivos.push(motivo);
    return false;
  }
  rede.set(cod6, {
    municipio_cod: cod6,
    geocode: geo.geocode,
    municipio: pop?.municipio_nome ?? geo.nome,
    uf: pop?.uf_sigla ?? geo.uf,
    regiao: pop?.regiao ?? null,
    populacao: pop?.populacao ?? null,
    motivos: [motivo],
  });
  return true;
}

for (const cod of CAPITAIS_6) incluir(cod, "capital");
const nCapitais = rede.size;

for (const p of pops) {
  if ((p.populacao ?? 0) >= POP_MIN) incluir(p.municipio_cod, "populacao");
}
const nAposPop = rede.size;

const risco = dengue
  .filter((d) => (d.populacao ?? 0) >= POP_MIN_RISCO && d.incidencia_100k != null)
  .sort((a, b) => b.incidencia_100k - a.incidencia_100k)
  .slice(0, TOP_RISCO);
for (const d of risco) incluir(d.municipio_cod, "risco_dengue");

const lista = [...rede.values()].sort((a, b) => (b.populacao ?? 0) - (a.populacao ?? 0));
const popRede = lista.reduce((s, m) => s + (m.populacao ?? 0), 0);
const popBr = pops.reduce((s, p) => s + (p.populacao ?? 0), 0);

const porUf = {};
for (const m of lista) porUf[m.uf] = (porUf[m.uf] ?? 0) + 1;

const saida = {
  gerado_em: new Date().toISOString(),
  criterios: {
    capitais: 27,
    populacao_minima: POP_MIN,
    top_risco_dengue: TOP_RISCO,
    populacao_minima_risco: POP_MIN_RISCO,
    ano_populacao: anoPop,
    ano_dengue: anoDengue,
  },
  total: lista.length,
  populacao_coberta: popRede,
  populacao_brasil: popBr,
  cobertura_pct: (100 * popRede) / popBr,
  ufs_cobertas: Object.keys(porUf).length,
  municipios_por_uf: porUf,
  municipios: lista,
};

const OUT = path.join(import.meta.dirname, "..", "public", "sdata");
await mkdir(OUT, { recursive: true });
await writeFile(path.join(OUT, "rede-sentinela.json"), JSON.stringify(saida));

console.log(`\n[rede] REDE SENTINELA: ${lista.length} municípios`);
console.log(`  capitais              : ${nCapitais}`);
console.log(`  + população ≥ ${POP_MIN.toLocaleString("pt-BR")} : +${nAposPop - nCapitais}`);
console.log(`  + risco dengue (top ${TOP_RISCO}) : +${lista.length - nAposPop}`);
console.log(`  cobertura populacional: ${saida.cobertura_pct.toFixed(1)}% (${popRede.toLocaleString("pt-BR")} hab)`);
console.log(`  UFs cobertas          : ${saida.ufs_cobertas}/27`);
const semPop = lista.filter((m) => m.populacao == null).length;
if (semPop) console.log(`  ⚠ ${semPop} sem população no mart (entraram só por risco/capital)`);
