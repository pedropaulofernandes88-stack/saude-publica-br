/**
 * build-boletim.mjs — gera a edição semanal do Boletim Epidemiológico.
 *
 * Duas camadas, deliberadamente separadas por fonte e método:
 *
 *  1. VIGILÂNCIA ATUAL (InfoDengue — Fiocruz/FGV): situação da semana corrente
 *     nas 27 capitais, com nowcasting que corrige o atraso de notificação.
 *     É o que muda toda semana e justifica um boletim semanal.
 *  2. ANÁLISE HISTÓRICA (DataSUS consolidado): canal endêmico, excesso de
 *     mortalidade e internações — base fechada, muda quando o MS publica.
 *
 * Grava a edição em /public/sdata/boletins/<ano>-se<NN>.json + index.json.
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
const plural = (n, sing, plur) => `${fmtInt(n)} ${n === 1 ? sing : plur}`;

// ── Guard-rail ─────────────────────────────────────────────────────────────
// Um boletim automático degrada em silêncio: a fonte muda de formato, o modelo
// externo congela, uma mart some — e ele continua publicando algo plausível.
// Estas verificações transformam degradação silenciosa em falha ruidosa. As
// críticas derrubam a execução (exit != 0), o que faz o Actions notificar e
// abrir issue; as não críticas apenas ficam registradas na edição.
const verificacoes = [];
function verificar(nome, ok, detalhe, { critico = false } = {}) {
  verificacoes.push({ nome, ok, critico, detalhe });
  const marca = ok ? "ok  " : critico ? "FALHA" : "aviso";
  console.log(`[verif] ${marca} ${nome}: ${detalhe}`);
  return ok;
}

// ── Data da edição ──────────────────────────────────────────────────────────
const argData = process.argv.indexOf("--data");
const hoje = argData > -1 ? new Date(`${process.argv[argData + 1]}T12:00:00Z`) : new Date();
const { ano: anoEd, semana: semEd } = semanaEpi(hoje);
const edicao = `${anoEd}-se${String(semEd).padStart(2, "0")}`;
console.log(`[boletim] edição ${edicao} (gerada em ${hoje.toISOString().slice(0, 10)})`);

// ── 1. VIGILÂNCIA ATUAL — InfoDengue (Fiocruz/FGV) ─────────────────────────
// Rede sentinela definida em sdata/rede-sentinela.json (ver build-rede-sentinela.mjs):
// capitais + municípios grandes + municípios de alto risco histórico de dengue.
//
// O InfoDengue publica nowcasting semanal por município: `casos` é a notificação
// já digitada (sempre subestimada na semana corrente) e `casos_est` é a estimativa
// corrigida para o atraso — por isso o boletim reporta as duas, nunca só a crua.
// Níveis: 1 verde | 2 amarelo (atenção) | 3 laranja (transmissão sustentada) |
// 4 vermelho (epidemia). Rt > 1 indica transmissão em crescimento.
//
// Detalhe completo é guardado só para municípios em alerta e para os maiores
// volumes; o resto entra como agregado — cada edição é commitada toda semana e
// guardar ~900 registros inteiros incharia o repositório sem ganho de leitura.
const NIVEL_LABEL = { 1: "verde", 2: "amarelo", 3: "laranja", 4: "vermelho" };
const CONCORRENCIA = 6; // medido: sem erros; ~15 req/s. Serviço público — não abusar.

async function infodengue(geocode, doenca, tentativa = 1) {
  // Janela de 8 semanas para calcular tendência; cruza o ano quando necessário.
  const cruzaAno = semEd <= 8;
  const qs = new URLSearchParams({
    geocode, disease: doenca, format: "json",
    ew_start: String(cruzaAno ? 45 : semEd - 8),
    ew_end: String(semEd),
    ey_start: String(cruzaAno ? anoEd - 1 : anoEd),
    ey_end: String(anoEd),
  });
  try {
    const res = await fetch(`https://info.dengue.mat.br/api/alertcity?${qs}`, {
      signal: AbortSignal.timeout(30_000),
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return await res.json();
  } catch (e) {
    if (tentativa >= 3) throw e;
    await new Promise((r) => setTimeout(r, 800 * tentativa));
    return infodengue(geocode, doenca, tentativa + 1);
  }
}

function extrair(serie, mun) {
  if (!serie.length) return null;
  const ordenada = [...serie].sort((a, b) => a.SE - b.SE);
  const atual = ordenada[ordenada.length - 1];
  // Tendência: estimativa desta semana vs. 4 semanas antes (nowcast, não bruto)
  const antes = ordenada[Math.max(0, ordenada.length - 5)];
  const variacao = antes?.casos_est > 0
    ? ((atual.casos_est - antes.casos_est) / antes.casos_est) * 100 : null;
  const min = atual.casos_est_min ?? null;
  const max = atual.casos_est_max ?? null;
  return {
    uf: mun.uf, municipio: mun.municipio, geocode: mun.geocode,
    populacao: mun.populacao ?? null,
    // InfoDengue devolve SE no formato AAAASS (202628 = semana 28 de 2026)
    semana_epi: atual.SE % 100,
    ano_epi: Math.floor(atual.SE / 100),
    casos_notificados: atual.casos ?? 0,
    casos_estimados: Math.round(atual.casos_est ?? 0),
    // min = max significa que o modelo não estimou incerteza — não é intervalo
    casos_est_min: min !== max ? min : null,
    casos_est_max: min !== max ? max : null,
    incidencia_100k: atual.p_inc100k ?? null,
    nivel: atual.nivel ?? null,
    nivel_label: NIVEL_LABEL[atual.nivel] ?? null,
    rt: atual.Rt ?? null,
    variacao_4sem_pct: variacao,
    versao_modelo: atual.versao_modelo ?? null,
  };
}

async function vigilanciaRede(municipios, doenca) {
  const fila = [...municipios];
  const linhas = [];
  const falhas = [];
  await Promise.all(Array.from({ length: CONCORRENCIA }, async () => {
    while (fila.length) {
      const mun = fila.shift();
      try {
        const r = extrair(await infodengue(mun.geocode, doenca), mun);
        if (r) linhas.push(r);
      } catch (e) {
        falhas.push(`${mun.uf}/${mun.municipio}`);
      }
    }
  }));
  return { linhas, falhas };
}

/** Resume uma doença: agregados para toda a rede, detalhe só onde importa. */
function resumirDoenca(linhas) {
  const niveis = { 1: 0, 2: 0, 3: 0, 4: 0 };
  const ufMap = new Map();
  for (const l of linhas) {
    if (l.nivel) niveis[l.nivel] = (niveis[l.nivel] ?? 0) + 1;
    const u = ufMap.get(l.uf) ?? { uf: l.uf, municipios: 0, em_alerta: 0, casos_estimados: 0, casos_notificados: 0 };
    u.municipios++;
    if ((l.nivel ?? 0) >= 3) u.em_alerta++;
    u.casos_estimados += l.casos_estimados;
    u.casos_notificados += l.casos_notificados;
    ufMap.set(l.uf, u);
  }
  const porNivel = (a, b) => (b.nivel - a.nivel) || (b.casos_estimados - a.casos_estimados);
  return {
    municipios_monitorados: linhas.length,
    resumo_niveis: niveis,
    em_alerta: linhas.filter((l) => (l.nivel ?? 0) >= 3).sort(porNivel),
    transmissao_crescente: linhas.filter((l) => (l.rt ?? 0) > 1).length,
    maiores_volumes: [...linhas].sort((a, b) => b.casos_estimados - a.casos_estimados).slice(0, 20),
    por_uf: [...ufMap.values()].sort((a, b) => b.em_alerta - a.em_alerta || b.casos_estimados - a.casos_estimados),
    total_estimado: linhas.reduce((s, l) => s + l.casos_estimados, 0),
    total_notificado: linhas.reduce((s, l) => s + l.casos_notificados, 0),
  };
}

let vigilancia = null;
try {
  const rede = JSON.parse(
    await readFile(path.join(import.meta.dirname, "..", "public", "sdata", "rede-sentinela.json"), "utf8"),
  );
  console.log(`[boletim] vigilância atual — InfoDengue (${rede.total} municípios sentinela)…`);
  const t0 = Date.now();
  const dg = await vigilanciaRede(rede.municipios, "dengue");
  const ch = await vigilanciaRede(rede.municipios, "chikungunya");
  if (!dg.linhas.length) throw new Error("nenhum município retornou dados");

  const maisRecente = dg.linhas.reduce((a, b) =>
    (b.ano_epi * 100 + b.semana_epi) > (a.ano_epi * 100 + a.semana_epi) ? b : a);
  const codCapitais = new Set(rede.municipios.filter((m) => m.motivos.includes("capital")).map((m) => m.geocode));

  vigilancia = {
    fonte: "InfoDengue — Fiocruz/FGV (nowcasting; corrige atraso de notificação)",
    fonte_url: "https://info.dengue.mat.br",
    semana_epi: maisRecente.semana_epi,
    ano_epi: maisRecente.ano_epi,
    versao_modelo: maisRecente.versao_modelo ?? null,
    rede: {
      total: rede.total,
      consultados: dg.linhas.length,
      falhas: dg.falhas.length,
      populacao_coberta: rede.populacao_coberta,
      cobertura_pct: rede.cobertura_pct,
      ufs_cobertas: rede.ufs_cobertas,
      criterios: rede.criterios,
    },
    dengue: resumirDoenca(dg.linhas),
    chikungunya: resumirDoenca(ch.linhas),
    capitais_dengue: dg.linhas.filter((l) => codCapitais.has(l.geocode))
      .sort((a, b) => b.casos_estimados - a.casos_estimados),
  };
  console.log(`[boletim]   SE ${vigilancia.semana_epi}/${vigilancia.ano_epi} em ${((Date.now() - t0) / 1000).toFixed(0)}s · `
    + `dengue: ${vigilancia.dengue.em_alerta.length} em alerta de ${dg.linhas.length} · `
    + `chik: ${vigilancia.chikungunya.em_alerta.length} · modelo ${vigilancia.versao_modelo}`
    + (dg.falhas.length ? ` · ${dg.falhas.length} falhas` : ""));

  // Cobertura: perder alguns municípios é tolerável; perder metade da rede
  // significa que o boletim está cego para grande parte do país.
  const pctResp = (100 * dg.linhas.length) / rede.total;
  verificar(
    "rede_sentinela_respondeu",
    pctResp >= 50,
    `${dg.linhas.length}/${rede.total} municípios (${pctResp.toFixed(0)}%)`
      + (pctResp < 80 ? " — abaixo do esperado (80%)" : ""),
    { critico: true },
  );
  if (pctResp >= 50 && pctResp < 80) {
    verificar("rede_sentinela_cobertura_parcial", false,
      `só ${pctResp.toFixed(0)}% da rede respondeu; alertas podem estar incompletos`);
  }

  // A falha MAIS PERIGOSA e mais difícil de notar: se o InfoDengue parar de
  // atualizar, continuaríamos publicando a mesma semana como se fosse atual.
  // Atraso normal é de 1 a 2 semanas.
  const idx = (a, s) => a * 53 + s;
  const atraso = idx(anoEd, semEd) - idx(vigilancia.ano_epi, vigilancia.semana_epi);
  verificar(
    "vigilancia_atualizada",
    atraso <= 3,
    `SE ${vigilancia.semana_epi}/${vigilancia.ano_epi} está ${atraso} semana(s) atrás da edição`
      + (atraso > 3 ? " — fonte externa parece congelada" : ""),
    { critico: true },
  );
  vigilancia.atraso_semanas = atraso;
} catch (e) {
  vigilancia = null; // não publicar vigilância parcial/inconsistente
  verificar("vigilancia_disponivel", false,
    `InfoDengue indisponível: ${String(e).slice(0, 120)}`, { critico: true });
}

// ── 2. Dengue: canal endêmico + alertas por UF ─────────────────────────────
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

verificar("mart_dengue_historica", dengueUfs.length >= 20,
  `${dengueUfs.length} UFs com série histórica de dengue`, { critico: true });

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

verificar("mart_excesso_mortalidade", mesesOrdenados.length >= 12,
  `${mesesOrdenados.length} meses consolidados de excesso`, { critico: true });
verificar("mart_internacoes_sih", (sih.internacoes ?? 0) > 1_000_000,
  `${fmtInt(sih.internacoes ?? 0)} internações em ${anoSih}`, { critico: true });

// ── 4. Metadados de frescor ────────────────────────────────────────────────
const meta = await rest("meta_dataset", { select: "chave,valor" });
const metaMap = Object.fromEntries(meta.map((m) => [m.chave, m.valor]));

// ── 5. Destaques (texto automático) ────────────────────────────────────────
const mesLabel = new Date(`${ultimoMes.slice(0, 10)}T12:00:00Z`).toLocaleDateString("pt-BR", {
  month: "long",
  year: "numeric",
  timeZone: "UTC",
});
const destaques = [];

// O destaque de abertura é sempre a situação corrente — é o que muda toda semana.
if (vigilancia) {
  const dg = vigilancia.dengue;
  const ch = vigilancia.chikungunya;
  const rede = vigilancia.rede;
  const alerta = dg.em_alerta;
  const ufsComAlerta = new Set(alerta.map((m) => m.uf));

  if (alerta.length) {
    destaques.push(
      `SE ${vigilancia.semana_epi}/${vigilancia.ano_epi} — dengue: `
      + `${plural(alerta.length, "município em alerta", "municípios em alerta")} `
      + `(nível laranja ou vermelho) em ${plural(ufsComAlerta.size, "UF", "UFs")}, `
      + `de ${fmtInt(dg.municipios_monitorados)} monitorados. Maiores: `
      + `${alerta.slice(0, 4).map((m) => `${m.municipio}/${m.uf}`).join(", ")}`
      + `${alerta.length > 4 ? " e outros" : ""}. Fonte: InfoDengue (Fiocruz/FGV).`,
    );
  } else {
    destaques.push(
      `SE ${vigilancia.semana_epi}/${vigilancia.ano_epi} — dengue: nenhum dos `
      + `${fmtInt(dg.municipios_monitorados)} municípios monitorados está em alerta laranja/vermelho; `
      + `${plural(dg.transmissao_crescente, "tem", "têm")} transmissão em crescimento (Rt>1). `
      + `Fonte: InfoDengue (Fiocruz/FGV).`,
    );
  }
  destaques.push(
    `Na rede sentinela (${fmtInt(rede.total)} municípios, ${rede.cobertura_pct.toFixed(0)}% da população), `
    + `${fmtInt(dg.total_notificado)} casos de dengue já notificados na semana, `
    + `mas ${fmtInt(dg.total_estimado)} estimados após correção do atraso de digitação `
    + `(nowcasting) — a contagem crua da semana corrente sempre subestima.`,
  );
  if (ch.em_alerta.length) {
    destaques.push(
      `Chikungunya: ${plural(ch.em_alerta.length, "município em alerta", "municípios em alerta")} — `
      + `${ch.em_alerta.slice(0, 3).map((m) => `${m.municipio}/${m.uf}`).join(", ")}`
      + `${ch.em_alerta.length > 3 ? " e outros" : ""}.`,
    );
  }
}

destaques.push(
  `Dengue ${anoRefDengue}: ${fmtInt(totalDengue.casos)} casos prováveis e ${fmtInt(totalDengue.obitos)} óbitos — casos acima da faixa esperada (P75 do canal endêmico ${baseIni}–${baseFim}) em ${semanasAcimaBr} das 52 semanas.`,
  `${ufsEmAlerta.length} UFs passaram um trimestre ou mais acima do canal endêmico em ${anoRefDengue}${ufsEmAlerta.length ? ` — maiores volumes: ${ufsEmAlerta.slice(0, 3).map((u) => u.uf).join(", ")}` : ""}.`,
  `Mortalidade geral em ${mesLabel}: ${fmtInt(brUltimo.obitos)} óbitos, ${fmtPct(pctExcessoBr)} vs. esperado (baseline 2015–2019)${descartados ? ` — ${descartados} mês(es) mais recente(s) excluído(s) por registro incompleto` : ""}.`,
  `Internações SUS ${anoSih}: ${fmtInt(internacoes.internacoes)} AIH, mortalidade intra-hospitalar de ${internacoes.mortalidade_pct.toFixed(1).replace(".", ",")}% e R$ ${(internacoes.valor_total / 1e9).toFixed(1).replace(".", ",")} bi aprovados.`,
);

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
  vigilancia_atual: vigilancia,
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
  verificacoes,
};

/**
 * Encerra sinalizando a saúde da execução.
 *   0 = tudo certo
 *   2 = a edição foi produzida, mas com falha crítica (fonte fora do ar, dado
 *       congelado, mart vazia). O workflow publica assim mesmo — a página mostra
 *       a degradação — e depois derruba o job para notificar e abrir issue.
 * Publicar em silêncio um boletim degradado é o único desfecho inaceitável.
 */
function encerrar() {
  const criticas = verificacoes.filter((v) => !v.ok && v.critico);
  const avisos = verificacoes.filter((v) => !v.ok && !v.critico);
  if (criticas.length) {
    console.error(`\n[verif] ${criticas.length} verificação(ões) CRÍTICA(s) falharam:`);
    for (const c of criticas) console.error(`  ✗ ${c.nome}: ${c.detalhe}`);
    console.error("[verif] a edição foi gravada, mas o boletim está degradado.");
    process.exit(2);
  }
  if (avisos.length) console.warn(`\n[verif] ${avisos.length} aviso(s) não crítico(s).`);
  else console.log("\n[verif] todas as verificações passaram.");
  process.exit(0);
}

// Idempotência: se a edição já existe com o mesmo conteúdo (ignorando o
// timestamp de geração), mantém o arquivo — sem commit novo no workflow.
const outFile = path.join(OUT, `${edicao}.json`);
const semTimestamp = (b) => JSON.stringify({ ...b, gerado_em: undefined });
try {
  const existente = JSON.parse(await readFile(outFile, "utf8"));
  if (semTimestamp(existente) === semTimestamp(boletim)) {
    console.log(`[boletim] ${edicao} já publicada com o mesmo conteúdo — nada a fazer.`);
    encerrar(); // conteúdo igual não silencia falha crítica
  }
} catch {
  /* edição nova */
}

await writeFile(outFile, JSON.stringify(boletim));

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

encerrar();
