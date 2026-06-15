/**
 * build-static-data.mjs — gera JSONs estáticos no build (prebuild).
 *
 * As consultas mais comuns do site (séries TOTAL por UF/Brasil, excesso de
 * mortalidade, capítulos, metadados) são congeladas em /public/sdata/*.json
 * e servidas pelo próprio GitHub Pages — egress zero no Supabase para a
 * navegação típica. Consultas finas (municípios, capítulos específicos)
 * continuam indo à API ao vivo.
 */
import { mkdir, writeFile } from "node:fs/promises";
import path from "node:path";

const URL =
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
    const res = await fetch(`${URL}/rest/v1/${table}?${qs}`, {
      headers: {
        ...HEADERS,
        "Range-Unit": "items",
        Range: `${offset}-${offset + PAGE - 1}`,
      },
    });
    if (!res.ok) throw new Error(`${table}: HTTP ${res.status} ${await res.text()}`);
    const chunk = await res.json();
    rows.push(...chunk);
    if (chunk.length < PAGE) break;
    offset += PAGE;
  }
  return rows;
}

const OUT = path.join(import.meta.dirname, "..", "public", "sdata");
await mkdir(OUT, { recursive: true });

console.log("[sdata] série mensal TOTAL por UF…");
const serie = await rest("mart_mortalidade_uf_mes", {
  select: "uf_sigla,ano,mes_competencia,obitos",
  capitulo_cid: "eq.TOTAL",
  sexo: "eq.TOTAL",
  faixa_etaria: "eq.TOTAL",
  order: "mes_competencia,uf_sigla",
});
// Acrescenta Brasil agregado
const porMes = new Map();
for (const r of serie) {
  porMes.set(r.mes_competencia, (porMes.get(r.mes_competencia) ?? 0) + r.obitos);
}
const br = [...porMes.entries()]
  .sort(([a], [b]) => a.localeCompare(b))
  .map(([mes_competencia, obitos]) => ({
    uf_sigla: "BR",
    ano: Number(mes_competencia.slice(0, 4)),
    mes_competencia,
    obitos,
  }));
await writeFile(path.join(OUT, "serie_total.json"), JSON.stringify([...serie, ...br]));
console.log(`[sdata]   ${serie.length + br.length} linhas`);

console.log("[sdata] excesso de mortalidade…");
const excesso = await rest("mart_excesso_uf_mes", {
  select: "uf_sigla,ano,mes_competencia,obitos,esperado,excesso,pct_excesso",
  order: "mes_competencia,uf_sigla",
});
await writeFile(path.join(OUT, "excesso.json"), JSON.stringify(excesso));
console.log(`[sdata]   ${excesso.length} linhas`);

console.log("[sdata] dengue — agregado por UF × ano × semana (server-side)…");
try {
  const dengue = await rest("mart_dengue_semana", {
    select: "uf_sigla,ano_epi,semana_epi,casos_provaveis:casos_provaveis.sum(),casos_graves:casos_graves.sum(),obitos:obitos.sum()",
    semana_epi: "gte.1",
    order: "uf_sigla,ano_epi,semana_epi",
  });
  await writeFile(path.join(OUT, "dengue_uf_semana.json"), JSON.stringify(dengue));
  console.log(`[sdata]   ${dengue.length} linhas`);
} catch (e) {
  console.warn("[sdata]   dengue indisponível (ainda não carregado?):", String(e).slice(0, 120));
  await writeFile(path.join(OUT, "dengue_uf_semana.json"), "[]");
}

console.log("[sdata] vulnerabilidade × mortalidade (IVS proxy × taxa padronizada, 2023)…");
try {
  const [ivs, mort] = await Promise.all([
    rest("dim_ivs", { select: "municipio_cod,municipio_nome,uf_sigla,regiao,ivs_score,ivs_quartil" }),
    rest("mart_mortalidade_municipio", {
      select: "municipio_cod,taxa_padronizada_100k,populacao",
      ano: "eq.2023", capitulo_cid: "eq.TOTAL", sexo: "eq.TOTAL", order: "municipio_cod",
    }),
  ]);
  const mortByCod = new Map(mort.map((m) => [m.municipio_cod, m]));
  const cruz = [];
  for (const i of ivs) {
    const m = mortByCod.get(i.municipio_cod);
    if (!m || m.taxa_padronizada_100k == null || i.ivs_score == null) continue;
    if ((m.populacao ?? 0) < 10000) continue; // taxas instáveis em municípios pequenos
    cruz.push({
      cod: i.municipio_cod, nome: i.municipio_nome, uf: i.uf_sigla, regiao: i.regiao,
      ivs: i.ivs_score, taxa_pad: m.taxa_padronizada_100k, pop: m.populacao,
    });
  }
  await writeFile(path.join(OUT, "vulnerab_mortalidade.json"), JSON.stringify(cruz));
  console.log(`[sdata]   ${cruz.length} municípios`);
} catch (e) {
  console.warn("[sdata]   cruzamento indisponível:", String(e).slice(0, 120));
  await writeFile(path.join(OUT, "vulnerab_mortalidade.json"), "[]");
}

console.log("[sdata] capítulos, padrão etário e metadados…");
const caps = await rest("dim_cid10_capitulo", {
  select: "capitulo,capitulo_num,faixa,descricao",
  order: "capitulo_num",
});
await writeFile(path.join(OUT, "capitulos.json"), JSON.stringify(caps));
const meta = await rest("meta_dataset", { select: "chave,valor" });
await writeFile(path.join(OUT, "meta.json"), JSON.stringify(meta));

console.log("[sdata] concluído.");
