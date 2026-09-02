/**
 * build-alertas.mjs — decide o que, nesta semana, merece interromper alguém.
 *
 * Um boletim que chega toda semana dizendo a mesma coisa é ignorado em um mês.
 * Por isso este script NÃO reporta a situação: ele reporta a MUDANÇA. Compara a
 * edição atual com a anterior e classifica cada município da rede sentinela:
 *
 *   novo      — não estava em alerta (nível <3) e entrou
 *   agravado  — já estava, mas piorou (laranja → vermelho)
 *   resolvido — estava em alerta e saiu (informativo; sozinho não gera envio)
 *
 * Só `novo` e `agravado` justificam e-mail. Se a semana não trouxe nenhum dos
 * dois para a UF do assinante, ele não recebe nada — silêncio é a resposta certa.
 *
 * Saída: site/public/sdata/boletins/alertas-<edicao>.json, consumido pelo
 * enviar-alertas (Edge Function) via workflow.
 *
 * Uso:  node site/scripts/build-alertas.mjs [--edicao 2026-se30]
 */
import { readFile, readdir, writeFile } from "node:fs/promises";
import path from "node:path";

import { selecionarEdicao } from "../lib/edicoes.ts";

const DIR = path.join(import.meta.dirname, "..", "public", "sdata", "boletins");
const NIVEL_MIN_ALERTA = 3; // laranja

const argEd = process.argv.indexOf("--edicao");
const edicaoAlvo = argEd > -1 ? process.argv[argEd + 1] : null;

const index = JSON.parse(await readFile(path.join(DIR, "index.json"), "utf8"));

// A seleção mora em lib/edicoes.ts para ser testável: `npm test` não alcança
// scripts/, e as duas guardas abaixo nunca tinham sido vistas reprovando.
const selecao = selecionarEdicao(index, edicaoAlvo);
if (!selecao.ok) {
  console.error(`[alertas] ${selecao.erro}`);
  process.exit(1);
}
const { atual: edAtual, anterior: edAnterior } = selecao;

const ler = async (ed) => JSON.parse(await readFile(path.join(DIR, `${ed}.json`), "utf8"));
const atual = await ler(edAtual);
const anterior = edAnterior ? await ler(edAnterior) : null;

console.log(`[alertas] ${edAtual}${edAnterior ? ` vs ${edAnterior}` : " (sem edição anterior)"}`);

/** Mapa geocode -> nível, considerando TODOS os monitorados, não só os em alerta. */
function niveisDe(boletim, doenca) {
  const v = boletim?.vigilancia_atual?.[doenca];
  if (!v) return null; // sem vigilância nessa edição: não dá para comparar
  const m = new Map();
  // `em_alerta` e `maiores_volumes` trazem detalhe; o resto da rede não é
  // guardado por município. Quem não aparece aqui não estava em alerta —
  // é exatamente o que precisamos para detectar entrada.
  for (const lista of [v.em_alerta ?? [], v.maiores_volumes ?? []]) {
    for (const mun of lista) {
      if (!m.has(mun.geocode)) m.set(mun.geocode, mun);
    }
  }
  return m;
}

function diff(doenca) {
  const agora = niveisDe(atual, doenca);
  const antes = niveisDe(anterior, doenca);
  if (!agora) return null;

  // Sem vigilância na edição anterior não existe "novo": tudo pareceria novo e
  // o assinante levaria uma enxurrada. Marcamos como linha de base.
  const linhaDeBase = antes === null;

  const emAlertaAgora = [...agora.values()].filter((m) => (m.nivel ?? 0) >= NIVEL_MIN_ALERTA);
  const novos = [];
  const agravados = [];

  for (const mun of emAlertaAgora) {
    const antesM = antes?.get(mun.geocode);
    const nivelAntes = antesM?.nivel ?? 0;
    if (nivelAntes < NIVEL_MIN_ALERTA) {
      novos.push({ ...mun, nivel_anterior: antesM ? nivelAntes : null });
    } else if ((mun.nivel ?? 0) > nivelAntes) {
      agravados.push({ ...mun, nivel_anterior: nivelAntes });
    }
  }

  const resolvidos = [];
  if (antes) {
    for (const mun of antes.values()) {
      if ((mun.nivel ?? 0) < NIVEL_MIN_ALERTA) continue;
      const agoraM = agora.get(mun.geocode);
      if (!agoraM || (agoraM.nivel ?? 0) < NIVEL_MIN_ALERTA) {
        resolvidos.push({
          uf: mun.uf, municipio: mun.municipio, geocode: mun.geocode,
          nivel_anterior: mun.nivel, nivel: agoraM?.nivel ?? null,
        });
      }
    }
  }

  return {
    linha_de_base: linhaDeBase,
    em_alerta_total: emAlertaAgora.length,
    novos: novos.sort((a, b) => (b.nivel - a.nivel) || (b.casos_estimados - a.casos_estimados)),
    agravados: agravados.sort((a, b) => b.nivel - a.nivel),
    resolvidos,
  };
}

const dengue = diff("dengue");
const chikungunya = diff("chikungunya");

// Edição sem vigilância é um estado LEGÍTIMO (fonte externa fora do ar), não um
// erro deste script. Sair com código != 0 aqui derrubaria o workflow antes de
// publicar a edição degradada e antes de abrir a issue do guard-rail — ou seja,
// a falha ficaria invisível justamente quando mais importa notificá-la.
if (!dengue) {
  console.warn("[alertas] edição sem vigilância — nada a alertar nesta semana.");
  await writeFile(path.join(DIR, `alertas-${edAtual}.json`), JSON.stringify({
    edicao: edAtual,
    edicao_anterior: edAnterior,
    gerado_em: new Date().toISOString(),
    linha_de_base: false,
    deve_enviar: false,
    motivo: "edição sem dados de vigilância",
    total_novos: 0,
    total_agravados: 0,
    ufs_afetadas: [],
    por_uf: [],
  }));
  process.exit(0);
}

// ── Agrupamento por UF: é assim que o envio é segmentado ───────────────────
const porUf = new Map();
const registrar = (doenca, tipo, mun) => {
  const u = porUf.get(mun.uf) ?? { uf: mun.uf, novos: [], agravados: [] };
  u[tipo].push({
    doenca,
    municipio: mun.municipio,
    geocode: mun.geocode,
    nivel: mun.nivel,
    nivel_label: mun.nivel_label,
    nivel_anterior: mun.nivel_anterior ?? null,
    rt: mun.rt,
    casos_notificados: mun.casos_notificados,
    casos_estimados: mun.casos_estimados,
    variacao_4sem_pct: mun.variacao_4sem_pct,
  });
  porUf.set(mun.uf, u);
};

const linhaDeBase = dengue.linha_de_base;
if (!linhaDeBase) {
  for (const m of dengue.novos) registrar("dengue", "novos", m);
  for (const m of dengue.agravados) registrar("dengue", "agravados", m);
  if (chikungunya && !chikungunya.linha_de_base) {
    for (const m of chikungunya.novos) registrar("chikungunya", "novos", m);
    for (const m of chikungunya.agravados) registrar("chikungunya", "agravados", m);
  }
}

const ufs = [...porUf.values()]
  .map((u) => ({ ...u, total: u.novos.length + u.agravados.length }))
  .sort((a, b) => b.total - a.total);

const totalNovos = ufs.reduce((s, u) => s + u.novos.length, 0);
const totalAgravados = ufs.reduce((s, u) => s + u.agravados.length, 0);

const saida = {
  edicao: edAtual,
  edicao_anterior: edAnterior,
  gerado_em: new Date().toISOString(),
  semana_epi: atual.vigilancia_atual.semana_epi,
  ano_epi: atual.vigilancia_atual.ano_epi,
  // Quando true, NÃO enviar: não há edição anterior comparável e tudo
  // apareceria como novidade.
  linha_de_base: linhaDeBase,
  deve_enviar: !linhaDeBase && (totalNovos + totalAgravados) > 0,
  total_novos: totalNovos,
  total_agravados: totalAgravados,
  ufs_afetadas: ufs.map((u) => u.uf),
  por_uf: ufs,
  dengue: {
    em_alerta_total: dengue.em_alerta_total,
    resolvidos: dengue.resolvidos,
  },
  chikungunya: chikungunya
    ? { em_alerta_total: chikungunya.em_alerta_total, resolvidos: chikungunya.resolvidos }
    : null,
  permalink: `https://saudeemdado.com/boletim-semanal/?e=${edAtual}`,
};

await writeFile(path.join(DIR, `alertas-${edAtual}.json`), JSON.stringify(saida));

if (linhaDeBase) {
  console.log("[alertas] LINHA DE BASE — edição anterior sem vigilância comparável; nada será enviado.");
} else if (!saida.deve_enviar) {
  console.log("[alertas] nenhuma entrada ou agravamento nesta semana — nenhum envio (silêncio é o certo).");
} else {
  console.log(`[alertas] ${totalNovos} novo(s) e ${totalAgravados} agravamento(s) em ${ufs.length} UF(s):`);
  for (const u of ufs) {
    const desc = [...u.novos.map((m) => `${m.municipio} (novo, ${m.nivel_label}, ${m.doenca})`),
                  ...u.agravados.map((m) => `${m.municipio} (agravou p/ ${m.nivel_label}, ${m.doenca})`)];
    console.log(`  ${u.uf}: ${desc.join("; ")}`);
  }
}
console.log(`[alertas] gravado: sdata/boletins/alertas-${edAtual}.json`);
