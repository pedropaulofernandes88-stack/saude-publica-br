/**
 * build-boletim.mjs — gera a edição semanal do Boletim Epidemiológico.
 *
 * Consulta os marts públicos (Supabase/PostgREST, anon key somente-leitura),
 * calcula canal endêmico de dengue, excesso de mortalidade e destaques, e
 * grava a edição em /public/sdata/boletins/<ano>-se<NN>.json + index.json.
 *
 * Rodado pelo workflow boletim-semanal.yml (toda segunda-feira) e commitado —
 * cada edição fica arquivada no repositório com permalink próprio.
 *
 * Uso:  node site/scripts/build-boletim.mjs [--data 2026-07-20]
 */
import { mkdir, readFile, writeFile } from "node:fs/promises";
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

// ── Semana epidemiológica (padrão MS/CDC: domingo–sábado; SE1 começa no
//    domingo entre 29/dez e 04/jan) ─────────────────────────────────────────
function inicioAnoEpi(ano) {
  const jan4 = new Date(Date.UTC(ano, 0, 4));
  const d = new Date(jan4);
  d.setUTCDate(jan4.getUTCDate() - jan4.getUTCDay()); // domingo da semana do dia 04/jan
  return d;
}

function semanaEpi(data) {
  const d = new Date(Date.UTC(data.getUTCFullYear(), data.getUTCMonth(), data.getUTCDate()));
  let ano = d.getUTCFullYear();
  if (d >= inicioAnoEpi(ano + 1)) ano += 1;
  else if (d < inicioAnoEpi(ano)) ano -= 1;
  const semana = Math.floor((d - inicioAnoEpi(ano)) / (7 * 86_400_000)) + 1;
  return { ano, semana };
}

function quantil(arr, p) {
  if (!arr.length) return 0;
  const s = [...arr].sort((a, b) => a - b);
  const i = (s.length - 1) * p;
  const lo = Math.floor(i), hi = Math.ceil(i);
  return s[lo] + (s[hi] - s[lo]) * (i - lo);
}

const fmtInt = (n) => Math.round(n).toLocaleString("pt-BR");
const fmtPct = (n) => `${n >= 0 ? "+" : ""}${n.toFixed(1).replace(".", ",")}%`;

// ── Data da edição ──────────────────────────────────────────────────────────
const argData = process.argv.indexOf("--data");
const hoje = argData > -1 ? new Date(`${process.argv[argData + 1]}T12:00:00Z`) : new Date();
const { ano: anoEd, semana: semEd } = semanaEpi(hoje);
const edicao = `${anoEd}-se${String(semEd).padStart(2, "0")}`;
console.log(`[boletim] edição ${edicao} (gerada em ${hoje.toISOString().slice(0, 10)})`);

// ── 1. Dengue: canal endêmico + alertas por UF ─────────────────────────────
console.log("[boletim] dengue — série semanal por UF…");
const dengueRaw = await rest("mart_dengue_semana", {
  select:
    "uf_sigla,ano_epi,semana_epi,casos:casos_provaveis.sum(),graves:casos_graves.sum(),obitos:obitos.sum()",
  semana_epi: "gte.1",
  order: "uf_sigla,ano_epi,semana_epi",
});

const anosDengue = [...new Set(dengueRaw.map((r) => r.ano_epi))].sort((a, b) => a - b);
const anoRefDengue = anosDengue[anosDengue.length - 1];
const baseIni = anosDengue[0];
const baseFim = anoRefDengue - 1;

// Canal endêmico Brasil: baseline = quartis semanais dos anos anteriores ao ano
// de referência; observado = ano de referência (mesma lógica da página /dengue).
const brPorSemanaAno = {}; // semana -> ano -> casos
for (const r of dengueRaw) {
  const w = r.semana_epi;
  if (w < 1 || w > 52) continue;
  (brPorSemanaAno[w] ??= {});
  brPorSemanaAno[w][r.ano_epi] = (brPorSemanaAno[w][r.ano_epi] ?? 0) + r.casos;
}
const canalBr = Array.from({ length: 52 }, (_, k) => {
  const w = k + 1;
  const porAno = brPorSemanaAno[w] ?? {};
  const vals = Object.entries(porAno)
    .filter(([a]) => Number(a) >= baseIni && Number(a) <= baseFim)
    .map(([, v]) => v);
  return {
    semana: w,
    p25: Math.round(quantil(vals, 0.25)),
    mediana: Math.round(quantil(vals, 0.5)),
    p75: Math.round(quantil(vals, 0.75)),
    observado: porAno[anoRefDengue] ?? 0,
  };
});
const semanasAcimaBr = canalBr.filter((c) => c.observado > c.p75).length;

// Por UF: total do ano de referência + semanas acima do P75 do canal da própria UF
const ufDengue = new Map(); // uf -> { casos, graves, obitos, porSemanaAno }
for (const r of dengueRaw) {
  const e = ufDengue.get(r.uf_sigla) ?? { casos: 0, graves: 0, obitos: 0, semanas: {} };
  if (r.ano_epi === anoRefDengue) {
    e.casos += r.casos;
    e.graves += r.graves;
    e.obitos += r.obitos;
  }
  if (r.semana_epi >= 1 && r.semana_epi <= 52) {
    (e.semanas[r.semana_epi] ??= {});
    e.semanas[r.semana_epi][r.ano_epi] = (e.semanas[r.semana_epi][r.ano_epi] ?? 0) + r.casos;
  }
  ufDengue.set(r.uf_sigla, e);
}
const dengueUfs = [...ufDengue.entries()]
  .map(([uf, e]) => {
    let acima = 0;
    for (let w = 1; w <= 52; w++) {
      const porAno = e.semanas[w] ?? {};
      const vals = Object.entries(porAno)
        .filter(([a]) => Number(a) >= baseIni && Number(a) <= baseFim)
        .map(([, v]) => v);
      if ((porAno[anoRefDengue] ?? 0) > quantil(vals, 0.75)) acima++;
    }
    return { uf, casos: e.casos, graves: e.graves, obitos: e.obitos, semanas_acima_p75: acima };
  })
  .sort((a, b) => b.casos - a.casos);

const totalDengue = dengueUfs.reduce(
  (acc, u) => ({ casos: acc.casos + u.casos, graves: acc.graves + u.graves, obitos: acc.obitos + u.obitos }),
  { casos: 0, graves: 0, obitos: 0 },
);
const ufsEmAlerta = dengueUfs.filter((u) => u.semanas_acima_p75 >= 13); // ≥1 trimestre acima da faixa

// ── 2. Excesso de mortalidade ──────────────────────────────────────────────
console.log("[boletim] excesso de mortalidade…");
const excesso = await rest("mart_excesso_uf_mes", {
  select: "uf_sigla,mes_competencia,obitos,esperado,excesso,pct_excesso",
  order: "mes_competencia,uf_sigla",
});
const soUfs = excesso.filter((r) => r.uf_sigla !== "BR");

// Série Brasil: soma das UFs por mês
const brPorMes = new Map();
for (const r of soUfs) {
  const cur = brPorMes.get(r.mes_competencia) ?? { obitos: 0, esperado: 0 };
  cur.obitos += r.obitos;
  cur.esperado += r.esperado;
  brPorMes.set(r.mes_competencia, cur);
}

// Completude: o SIM tem atraso de registro — meses finais com razão
// observado/esperado < 90% são descartados como incompletos, senão o boletim
// publicaria um "déficit" de mortalidade que é só dado ainda não digitado.
const mesesOrdenados = [...brPorMes.keys()].sort();
let descartados = 0;
while (mesesOrdenados.length) {
  const m = mesesOrdenados[mesesOrdenados.length - 1];
  const v = brPorMes.get(m);
  if (v.obitos / v.esperado >= 0.9) break;
  mesesOrdenados.pop();
  descartados++;
}
const ultimoMes = mesesOrdenados[mesesOrdenados.length - 1];

const serie12m = mesesOrdenados
  .slice(-12)
  .map((mes) => [mes, brPorMes.get(mes)])
  .map(([mes, v]) => ({
    mes: mes.slice(0, 7),
    obitos: Math.round(v.obitos),
    esperado: Math.round(v.esperado),
  }));

const brUltimo = brPorMes.get(ultimoMes);
const pctExcessoBr = brUltimo ? ((brUltimo.obitos - brUltimo.esperado) / brUltimo.esperado) * 100 : 0;

const ufsUltimoMes = soUfs
  .filter((r) => r.mes_competencia === ultimoMes)
  .map((r) => ({
    uf: r.uf_sigla,
    obitos: r.obitos,
    esperado: Math.round(r.esperado),
    excesso: Math.round(r.excesso),
    pct_excesso: r.pct_excesso,
  }))
  .sort((a, b) => (b.pct_excesso ?? 0) - (a.pct_excesso ?? 0));

// ── 3. Internações (SIH, ano mais recente) ─────────────────────────────────
console.log("[boletim] internações SIH…");
const anoSih = (await rest("mart_internacoes_municipio", { select: "ano", order: "ano.desc", limit: "1" }))[0].ano;
const [sih] = await rest("mart_internacoes_municipio", {
  select:
    "internacoes:internacoes.sum(),obitos:obitos.sum(),valor:valor_total.sum(),dias:dias_permanencia.sum()",
  ano: `eq.${anoSih}`,
  capitulo_cid: "eq.TOTAL",
});
const internacoes = {
  ano_ref: anoSih,
  internacoes: sih.internacoes,
  obitos: sih.obitos,
  valor_total: sih.valor,
  permanencia_media: sih.dias / sih.internacoes,
  mortalidade_pct: (sih.obitos / sih.internacoes) * 100,
};

// ── 4. Metadados de frescor ────────────────────────────────────────────────
const meta = await rest("meta_dataset", { select: "chave,valor" });
const metaMap = Object.fromEntries(meta.map((m) => [m.chave, m.valor]));

// ── 5. Destaques (texto automático) ────────────────────────────────────────
const mesLabel = new Date(`${ultimoMes.slice(0, 10)}T12:00:00Z`).toLocaleDateString("pt-BR", {
  month: "long",
  year: "numeric",
  timeZone: "UTC",
});
const destaques = [
  `Dengue ${anoRefDengue}: ${fmtInt(totalDengue.casos)} casos prováveis e ${fmtInt(totalDengue.obitos)} óbitos — casos acima da faixa esperada (P75 do canal endêmico ${baseIni}–${baseFim}) em ${semanasAcimaBr} das 52 semanas.`,
  `${ufsEmAlerta.length} UFs passaram um trimestre ou mais acima do canal endêmico em ${anoRefDengue}${ufsEmAlerta.length ? ` — maiores volumes: ${ufsEmAlerta.slice(0, 3).map((u) => u.uf).join(", ")}` : ""}.`,
  `Mortalidade geral em ${mesLabel}: ${fmtInt(brUltimo.obitos)} óbitos, ${fmtPct(pctExcessoBr)} vs. esperado (baseline 2015–2019)${descartados ? ` — ${descartados} mês(es) mais recente(s) excluído(s) por registro incompleto` : ""}.`,
  `Internações SUS ${anoSih}: ${fmtInt(internacoes.internacoes)} AIH, mortalidade intra-hospitalar de ${internacoes.mortalidade_pct.toFixed(1).replace(".", ",")}% e R$ ${(internacoes.valor_total / 1e9).toFixed(1).replace(".", ",")} bi aprovados.`,
];

// ── 6. Gravar edição + índice ──────────────────────────────────────────────
const OUT = path.join(import.meta.dirname, "..", "public", "sdata", "boletins");
await mkdir(OUT, { recursive: true });

const boletim = {
  edicao,
  ano: anoEd,
  semana: semEd,
  gerado_em: hoje.toISOString(),
  versao_dataset: metaMap.versao_dataset ?? null,
  nota_preliminar: metaMap.nota_preliminar ?? null,
  destaques,
  dengue: {
    ano_ref: anoRefDengue,
    baseline: `${baseIni}–${baseFim}`,
    casos: totalDengue.casos,
    graves: totalDengue.graves,
    obitos: totalDengue.obitos,
    semanas_acima_p75: semanasAcimaBr,
    canal_br: canalBr,
    ufs: dengueUfs,
  },
  mortalidade: {
    ultimo_mes: ultimoMes.slice(0, 7),
    obitos_br: Math.round(brUltimo.obitos),
    esperado_br: Math.round(brUltimo.esperado),
    pct_excesso_br: pctExcessoBr,
    meses_descartados: descartados,
    serie_12m: serie12m,
    ufs_ultimo_mes: ufsUltimoMes,
  },
  internacoes,
};

await writeFile(path.join(OUT, `${edicao}.json`), JSON.stringify(boletim));

let index = [];
try {
  index = JSON.parse(await readFile(path.join(OUT, "index.json"), "utf8"));
} catch {
  /* primeira edição */
}
index = index.filter((e) => e.edicao !== edicao);
index.push({ edicao, ano: anoEd, semana: semEd, gerado_em: boletim.gerado_em, destaques: destaques.slice(0, 2) });
index.sort((a, b) => b.edicao.localeCompare(a.edicao));
await writeFile(path.join(OUT, "index.json"), JSON.stringify(index));

console.log(`[boletim] gravado: sdata/boletins/${edicao}.json (${index.length} edições no índice)`);
destaques.forEach((d) => console.log(`  • ${d}`));
