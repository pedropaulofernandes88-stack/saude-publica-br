/**
 * alertas-envio — entrega o alerta semanal aos assinantes confirmados.
 *
 * Chamado pelo workflow boletim-semanal.yml com o JSON produzido por
 * build-alertas.mjs. Não decide nada sobre epidemiologia: apenas entrega o que
 * o gerador já classificou como novidade.
 *
 * verify_jwt = false, mas a rota exige o header `x-alertas-secret` conferido
 * contra ALERTAS_ENVIO_SECRET — autenticação própria, já que quem chama é um
 * workflow do GitHub, não um usuário com JWT.
 *
 * Cada assinante recebe só o que é dele: quem assinou uma UF vê a sua; quem
 * assinou o Brasil vê tudo. Reexecução na mesma edição não reenvia.
 */
import { createClient } from "jsr:@supabase/supabase-js@2";

const SUPABASE_URL = Deno.env.get("SUPABASE_URL")!;
const SERVICE_KEY = Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!;
const RESEND_API_KEY = Deno.env.get("RESEND_API_KEY");
const ENVIO_SECRET = Deno.env.get("ALERTAS_ENVIO_SECRET");
// Mesmo padrão de alertas-assinatura: remetente de teste do Resend, que
// dispensa domínio verificado. Ver comentário lá.
const REMETENTE = Deno.env.get("ALERTAS_REMETENTE") ?? "Saúde em Dado <onboarding@resend.dev>";
const FUNC_URL = `${SUPABASE_URL}/functions/v1/alertas-assinatura`;

const db = createClient(SUPABASE_URL, SERVICE_KEY, { auth: { persistSession: false } });
const json = (b: unknown, s = 200) =>
  new Response(JSON.stringify(b), { status: s, headers: { "content-type": "application/json; charset=utf-8" } });

interface Ocorrencia {
  doenca: string; municipio: string; geocode: string;
  nivel: number; nivel_label: string; nivel_anterior: number | null;
  rt: number | null; casos_notificados: number; casos_estimados: number;
  variacao_4sem_pct: number | null;
}
interface UfBloco { uf: string; novos: Ocorrencia[]; agravados: Ocorrencia[]; total: number }

const int = (n: number) => Math.round(n).toLocaleString("pt-BR");

function linhaOcorrencia(o: Ocorrencia, tipo: "novo" | "agravado") {
  const rotulo = tipo === "novo"
    ? `entrou em alerta <strong>${o.nivel_label}</strong>`
    : `agravou para <strong>${o.nivel_label}</strong>`;
  const rt = o.rt != null
    ? ` Rt ${o.rt.toFixed(2)}${o.rt > 1 ? " (transmissão crescendo)" : ""}.`
    : "";
  return `<li style="margin-bottom:10px">
<strong>${o.municipio}</strong> — ${o.doenca} ${rotulo}.<br>
<span style="color:#4a5568;font-size:14px">${int(o.casos_notificados)} casos notificados, <strong>${int(o.casos_estimados)} estimados</strong> nesta semana.${rt}</span></li>`;
}

function corpoEmail(blocos: UfBloco[], meta: {
  semana: number; ano: number; permalink: string; cancelar: string; escopo: string;
}) {
  const secoes = blocos.map((b) => `
<h3 style="font-family:Georgia,serif;color:#0d1b2a;margin:22px 0 8px;font-size:18px">${b.uf}</h3>
<ul style="padding-left:18px;margin:0">
${b.novos.map((o) => linhaOcorrencia(o, "novo")).join("")}
${b.agravados.map((o) => linhaOcorrencia(o, "agravado")).join("")}
</ul>`).join("");

  const total = blocos.reduce((s, b) => s + b.total, 0);
  const html = `<div style="font:16px/1.6 system-ui,-apple-system,sans-serif;color:#1a2231;max-width:560px">
<p style="color:#8694ab;font-size:13px;text-transform:uppercase;letter-spacing:.5px;margin:0 0 4px">Alerta epidemiológico · SE ${meta.semana}/${meta.ano}</p>
<h2 style="font-family:Georgia,serif;color:#0d1b2a;margin:0 0 14px">${total} município${total > 1 ? "s" : ""} com mudança ${meta.escopo}</h2>
<p style="color:#4a5568">Detectamos entrada ou agravamento de alerta de arbovirose na rede sentinela nesta semana.</p>
${secoes}
<p style="margin-top:26px"><a href="${meta.permalink}" style="display:inline-block;background:#107752;color:#fff;text-decoration:none;padding:12px 22px;border-radius:9px;font-weight:600">Ver o boletim completo</a></p>
<div style="margin-top:26px;padding-top:16px;border-top:1px solid #eceef2;color:#8694ab;font-size:13px">
<p style="margin:0 0 8px"><strong>Como ler:</strong> “estimados” vem do nowcasting do InfoDengue (Fiocruz/FGV), que corrige o atraso de digitação — a contagem crua da semana corrente sempre subestima. Um município pode alertar com poucos casos digitados: o sinal vem do padrão de crescimento.</p>
<p style="margin:0 0 8px">Você recebe este e-mail apenas quando há mudança. Semana sem novidade, nenhuma mensagem.</p>
<p style="margin:0"><a href="${meta.cancelar}" style="color:#8694ab">Cancelar inscrição</a> · <a href="https://saudeemdado.com/metodologia/" style="color:#8694ab">Metodologia</a></p>
</div></div>`;

  const texto = blocos.map((b) => `${b.uf}\n` + [...b.novos.map((o) => `- ${o.municipio}: ${o.doenca} entrou em alerta ${o.nivel_label} (${int(o.casos_estimados)} casos estimados)`),
    ...b.agravados.map((o) => `- ${o.municipio}: ${o.doenca} agravou para ${o.nivel_label} (${int(o.casos_estimados)} casos estimados)`)].join("\n")).join("\n\n");
  return {
    html,
    texto: `Alerta epidemiológico — SE ${meta.semana}/${meta.ano}\n\n${texto}\n\nBoletim completo: ${meta.permalink}\nCancelar: ${meta.cancelar}`,
  };
}

async function enviar(para: string, assunto: string, html: string, texto: string) {
  const r = await fetch("https://api.resend.com/emails", {
    method: "POST",
    headers: { Authorization: `Bearer ${RESEND_API_KEY}`, "content-type": "application/json" },
    body: JSON.stringify({ from: REMETENTE, to: [para], subject: assunto, html, text: texto }),
  });
  if (!r.ok) throw new Error(`resend ${r.status}: ${(await r.text()).slice(0, 160)}`);
}

Deno.serve(async (req) => {
  if (req.method !== "POST") return json({ ok: false, erro: "use POST" }, 405);

  if (!ENVIO_SECRET || req.headers.get("x-alertas-secret") !== ENVIO_SECRET) {
    return json({ ok: false, erro: "não autorizado" }, 401);
  }
  if (!RESEND_API_KEY) return json({ ok: false, erro: "envio de e-mail não configurado" }, 503);

  let payload: {
    edicao: string; semana_epi: number; ano_epi: number; permalink: string;
    deve_enviar: boolean; linha_de_base: boolean; ufs_afetadas: string[]; por_uf: UfBloco[];
    dry_run?: boolean;
  };
  try { payload = await req.json(); } catch { return json({ ok: false, erro: "corpo inválido" }, 400); }

  if (payload.linha_de_base) return json({ ok: true, enviados: 0, motivo: "linha_de_base" });
  if (!payload.deve_enviar || !payload.por_uf?.length) {
    return json({ ok: true, enviados: 0, motivo: "sem_novidade" });
  }

  const { data: destinos, error } = await db.rpc("alerta_destinatarios", {
    p_ufs: payload.ufs_afetadas, p_edicao: payload.edicao,
  });
  if (error) return json({ ok: false, erro: String(error.message) }, 500);
  if (!destinos?.length) return json({ ok: true, enviados: 0, motivo: "sem_destinatarios" });

  const porUf = new Map(payload.por_uf.map((b) => [b.uf, b]));
  const enviados: string[] = [];
  const falhas: string[] = [];

  for (const d of destinos as { email: string; uf: string | null; token_cancelamento: string }[]) {
    // Quem assinou uma UF recebe só a dela; quem assinou o Brasil recebe tudo.
    const blocos = d.uf ? [porUf.get(d.uf)].filter(Boolean) as UfBloco[] : payload.por_uf;
    if (!blocos.length) continue;

    const escopo = d.uf ? `em ${d.uf}` : "no Brasil";
    const total = blocos.reduce((s, b) => s + b.total, 0);
    const { html, texto } = corpoEmail(blocos, {
      semana: payload.semana_epi, ano: payload.ano_epi, permalink: payload.permalink,
      cancelar: `${FUNC_URL}/cancelar?token=${d.token_cancelamento}`, escopo,
    });
    const assunto = `Alerta: ${total} município${total > 1 ? "s" : ""} ${escopo} — SE ${payload.semana_epi}/${payload.ano_epi}`;

    if (payload.dry_run) { enviados.push(d.email); continue; }
    try {
      await enviar(d.email, assunto, html, texto);
      enviados.push(d.email);
    } catch (e) {
      console.error("[alertas-envio]", d.email.replace(/(.).*(@.*)/, "$1***$2"), String((e as Error).message));
      falhas.push(d.email);
    }
  }

  if (enviados.length && !payload.dry_run) {
    await db.rpc("alerta_marcar_envio", { p_emails: enviados, p_edicao: payload.edicao });
  }
  return json({
    ok: true, edicao: payload.edicao, dry_run: !!payload.dry_run,
    destinatarios: destinos.length, enviados: enviados.length, falhas: falhas.length,
  });
});
