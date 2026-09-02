/**
 * build-feed.mjs — publica o boletim como feed Atom.
 *
 * Por que existe: o e-mail é o elo mais frágil da entrega. Depende de conta em
 * provedor, verificação de domínio, SPF/DKIM, reputação de IP e caixa de spam —
 * qualquer um desses quebra e o alerta não chega. O feed não depende de nada
 * disso: é um arquivo estático no mesmo GitHub Pages do site, sem credencial,
 * sem cadastro, sem base de dados pessoais.
 *
 * Também serve de matéria-prima para automação: qualquer leitor, IFTTT, Zapier,
 * n8n ou bot de Telegram consome Atom nativamente, então quem quiser receber por
 * outro canal monta o próprio caminho sem depender do projeto.
 *
 * Gera dois feeds:
 *   /boletim.xml  — uma entrada por edição publicada
 *   /alertas.xml  — só as edições que trouxeram entrada ou agravamento de alerta
 *
 * Uso:  node site/scripts/build-feed.mjs
 */
import { readFile, readdir, writeFile } from "node:fs/promises";
import path from "node:path";

import { exigirEdicoes } from "../lib/edicoes.ts";

const DIR = path.join(import.meta.dirname, "..", "public", "sdata", "boletins");
const OUT = path.join(import.meta.dirname, "..", "public");
const SITE = "https://saudeemdado.com";
const MAX_ENTRADAS = 30;

const escapar = (s) => String(s ?? "")
  .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
  .replace(/"/g, "&quot;").replace(/'/g, "&apos;");

const index = JSON.parse(await readFile(path.join(DIR, "index.json"), "utf8"));
const naoVazio = exigirEdicoes(index);
if (!naoVazio.ok) {
  console.error(`[feed] ${naoVazio.erro}`);
  process.exit(1);
}

const arquivos = new Set(await readdir(DIR));

/** Carrega edição + o arquivo de alertas correspondente, se existir. */
async function carregar(entrada) {
  const boletim = JSON.parse(await readFile(path.join(DIR, `${entrada.edicao}.json`), "utf8"));
  let alertas = null;
  if (arquivos.has(`alertas-${entrada.edicao}.json`)) {
    try {
      alertas = JSON.parse(await readFile(path.join(DIR, `alertas-${entrada.edicao}.json`), "utf8"));
    } catch { /* edição antiga sem arquivo de alertas */ }
  }
  return { entrada, boletim, alertas };
}

const edicoes = [];
for (const e of index.slice(0, MAX_ENTRADAS)) {
  try { edicoes.push(await carregar(e)); }
  catch (err) { console.warn(`[feed] ${e.edicao} ilegível: ${String(err).slice(0, 80)}`); }
}

function titulo({ boletim, alertas }) {
  const se = `SE ${boletim.semana}/${boletim.ano}`;
  const novos = alertas?.total_novos ?? 0;
  const agrav = alertas?.total_agravados ?? 0;
  if (novos + agrav > 0) {
    const partes = [];
    if (novos) partes.push(`${novos} município${novos > 1 ? "s" : ""} em novo alerta`);
    if (agrav) partes.push(`${agrav} agravamento${agrav > 1 ? "s" : ""}`);
    return `${se} — ${partes.join(" e ")}`;
  }
  const emAlerta = boletim.vigilancia_atual?.dengue?.em_alerta?.length;
  if (emAlerta != null) return `${se} — ${emAlerta} município(s) em alerta, sem mudança na semana`;
  return `${se} — boletim epidemiológico`;
}

function conteudo({ boletim, alertas }) {
  const itens = (boletim.destaques ?? []).map((d) => `<li>${escapar(d)}</li>`).join("");
  let detalhe = "";
  if (alertas?.por_uf?.length) {
    const linhas = alertas.por_uf.flatMap((u) => [
      ...u.novos.map((m) => `<li><strong>${escapar(m.municipio)}/${escapar(u.uf)}</strong> — ${escapar(m.doenca)} entrou em alerta ${escapar(m.nivel_label)}</li>`),
      ...u.agravados.map((m) => `<li><strong>${escapar(m.municipio)}/${escapar(u.uf)}</strong> — ${escapar(m.doenca)} agravou para ${escapar(m.nivel_label)}</li>`),
    ]).join("");
    if (linhas) detalhe = `&lt;h3&gt;Mudanças desta semana&lt;/h3&gt;&lt;ul&gt;${linhas.replace(/</g, "&lt;").replace(/>/g, "&gt;")}&lt;/ul&gt;`;
  }
  const vig = boletim.vigilancia_atual;
  const nota = vig
    ? `&lt;p&gt;&lt;small&gt;Vigilância: SE ${vig.semana_epi}/${vig.ano_epi}, rede de ${vig.rede?.total ?? "?"} municípios. Fonte: InfoDengue (Fiocruz/FGV).&lt;/small&gt;&lt;/p&gt;`
    : `&lt;p&gt;&lt;small&gt;Esta edição saiu sem dados de vigilância corrente.&lt;/small&gt;&lt;/p&gt;`;
  return `&lt;ul&gt;${itens.replace(/</g, "&lt;").replace(/>/g, "&gt;")}&lt;/ul&gt;${detalhe}${nota}`;
}

function montarFeed({ id, titulo: tituloFeed, subtitulo, caminho, lista }) {
  const atualizado = lista[0]?.boletim?.gerado_em ?? new Date().toISOString();
  const entradas = lista.map((ed) => {
    const url = `${SITE}/boletim-semanal/?e=${ed.entrada.edicao}`;
    return `  <entry>
    <title>${escapar(titulo(ed))}</title>
    <link href="${escapar(url)}"/>
    <id>tag:saudeemdado.com,${ed.boletim.ano}:${escapar(ed.entrada.edicao)}</id>
    <updated>${escapar(ed.boletim.gerado_em)}</updated>
    <content type="html">${conteudo(ed)}</content>
  </entry>`;
  }).join("\n");

  return `<?xml version="1.0" encoding="utf-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <title>${escapar(tituloFeed)}</title>
  <subtitle>${escapar(subtitulo)}</subtitle>
  <link href="${SITE}${caminho}" rel="self"/>
  <link href="${SITE}/boletim-semanal/"/>
  <id>tag:saudeemdado.com,2026:${id}</id>
  <updated>${escapar(atualizado)}</updated>
  <author><name>Saúde em Dado</name><uri>${SITE}</uri></author>
  <rights>Dados públicos (DataSUS/MS, IBGE) e InfoDengue (Fiocruz/FGV). Agregados sob CC BY 4.0.</rights>
${entradas}
</feed>
`;
}

await writeFile(path.join(OUT, "boletim.xml"), montarFeed({
  id: "boletim",
  titulo: "Saúde em Dado — Boletim epidemiológico semanal",
  subtitulo: "Vigilância de arboviroses e indicadores do SUS. Uma entrada por edição.",
  caminho: "/boletim.xml",
  lista: edicoes,
}));

// Feed enxuto: só semanas em que algo mudou. É o equivalente do e-mail —
// quem assina isto não é incomodado quando não há novidade.
const comMudanca = edicoes.filter((e) => (e.alertas?.total_novos ?? 0) + (e.alertas?.total_agravados ?? 0) > 0);
await writeFile(path.join(OUT, "alertas.xml"), montarFeed({
  id: "alertas",
  titulo: "Saúde em Dado — Alertas epidemiológicos",
  subtitulo: "Só quando um município entra em alerta ou um alerta se agrava. Semana sem mudança não gera entrada.",
  caminho: "/alertas.xml",
  lista: comMudanca,
}));

console.log(`[feed] boletim.xml: ${edicoes.length} entrada(s)`);
console.log(`[feed] alertas.xml: ${comMudanca.length} entrada(s) (só semanas com mudança)`);
