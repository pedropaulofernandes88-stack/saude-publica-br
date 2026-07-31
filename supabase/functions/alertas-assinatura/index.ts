/**
 * alertas-assinatura — inscrição, confirmação e cancelamento do alerta
 * epidemiológico do saudeemdado.com.
 *
 * verify_jwt = false por necessidade: o assinante é um visitante anônimo, não
 * tem JWT. A fronteira de segurança é esta função — ela usa service_role
 * server-side e só chama RPCs específicas (uma operação cada). O schema com os
 * dados pessoais não é alcançável pelo PostgREST público.
 *
 * LGPD: opt-in duplo (nada é enviado antes de confirmar), finalidade única
 * declarada no e-mail, cancelamento por link sem login e exclusão efetiva.
 *
 * Rotas:
 *   GET  /alertas-assinatura/status                  {email_configurado}
 *   POST /alertas-assinatura/assinar   {email, uf?, consentimento}
 *   GET  /alertas-assinatura/confirmar?token=<uuid>
 *   GET  /alertas-assinatura/cancelar?token=<uuid>
 */
import { createClient } from "jsr:@supabase/supabase-js@2";

const SUPABASE_URL = Deno.env.get("SUPABASE_URL")!;
const SERVICE_KEY = Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!;
const RESEND_API_KEY = Deno.env.get("RESEND_API_KEY");
// Padrão é o remetente de teste do Resend, que funciona SEM domínio verificado
// (só entrega ao e-mail da conta). Assim o sistema sai da caixa em vez de falhar
// esperando propagação de DNS. Para usar o domínio próprio, defina o segredo
// ALERTAS_REMETENTE como "Saúde em Dado <alertas@saudeemdado.com>" DEPOIS de
// verificar saudeemdado.com em resend.com/domains.
const REMETENTE = Deno.env.get("ALERTAS_REMETENTE") ?? "Saúde em Dado <onboarding@resend.dev>";
const SITE = "https://saudeemdado.com";
const FUNC_URL = `${SUPABASE_URL}/functions/v1/alertas-assinatura`;

const UFS = new Set(["AC","AL","AP","AM","BA","CE","DF","ES","GO","MA","MT","MS","MG","PA","PB",
  "PR","PE","PI","RJ","RN","RS","RO","RR","SC","SP","SE","TO"]);

const db = createClient(SUPABASE_URL, SERVICE_KEY, { auth: { persistSession: false } });

const CORS = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Headers": "content-type, apikey, authorization",
  "Access-Control-Allow-Methods": "POST, GET, OPTIONS",
};

const json = (body: unknown, status = 200, extra: Record<string, string> = {}) =>
  new Response(JSON.stringify(body), {
    status,
    headers: { ...CORS, "content-type": "application/json; charset=utf-8", ...extra },
  });

/** Página transacional simples — vista uma vez, autocontida. */
function pagina(titulo: string, corpo: string, status = 200) {
  const html = `<!doctype html><html lang="pt-BR"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="robots" content="noindex">
<title>${titulo} · Saúde em Dado</title>
<style>
:root{color-scheme:light}
body{margin:0;min-height:100vh;display:flex;align-items:center;justify-content:center;
  background:#f7f8fa;color:#1a2231;font:16px/1.6 system-ui,-apple-system,"Segoe UI",sans-serif;padding:24px}
.c{max-width:520px;background:#fff;border:1px solid #e4e8ee;border-radius:14px;padding:36px 32px;
  box-shadow:0 1px 3px rgba(16,24,40,.05)}
h1{font-family:Georgia,"Times New Roman",serif;font-size:26px;margin:0 0 12px;color:#0d1b2a}
p{margin:0 0 12px;color:#4a5568}
a.btn{display:inline-block;margin-top:18px;background:#107752;color:#fff;text-decoration:none;
  padding:11px 20px;border-radius:9px;font-weight:600;font-size:15px}
.s{margin-top:22px;padding-top:16px;border-top:1px solid #eceef2;font-size:13px;color:#8694ab}
</style></head><body><div class="c">${corpo}
<p class="s">Saúde em Dado — vigilância epidemiológica aberta.<br>Dados de arboviroses via InfoDengue (Fiocruz/FGV).</p>
</div></body></html>`;
  return new Response(html, { status, headers: { ...CORS, "content-type": "text/html; charset=utf-8" } });
}

class ErroProvedor extends Error {
  constructor(public status: number, public detalhe: string) {
    super(`provedor ${status}: ${detalhe}`);
  }
}

async function enviarEmail(para: string, assunto: string, html: string, texto: string) {
  if (!RESEND_API_KEY) throw new Error("email_nao_configurado");
  const r = await fetch("https://api.resend.com/emails", {
    method: "POST",
    headers: { Authorization: `Bearer ${RESEND_API_KEY}`, "content-type": "application/json" },
    body: JSON.stringify({ from: REMETENTE, to: [para], subject: assunto, html, text: texto }),
  });
  if (!r.ok) throw new ErroProvedor(r.status, (await r.text()).slice(0, 300));
  return r.json();
}

function emailConfirmacao(link: string, uf: string | null) {
  const escopo = uf ? `do estado <strong>${uf}</strong>` : "de <strong>todo o Brasil</strong>";
  const escopoTxt = uf ? `do estado ${uf}` : "de todo o Brasil";
  const html = `<div style="font:16px/1.6 system-ui,sans-serif;color:#1a2231;max-width:520px">
<h2 style="font-family:Georgia,serif;color:#0d1b2a">Confirme sua inscrição</h2>
<p>Você pediu para receber alertas quando um município ${escopo} <strong>entrar em alerta epidemiológico</strong> de dengue ou chikungunya.</p>
<p>Para começar a receber, confirme:</p>
<p><a href="${link}" style="display:inline-block;background:#107752;color:#fff;text-decoration:none;padding:12px 22px;border-radius:9px;font-weight:600">Confirmar inscrição</a></p>
<p style="color:#4a5568;font-size:14px">Você só receberá e-mail nas semanas em que houver <em>mudança</em>: um município entrando em alerta ou agravando. Semana sem novidade, nenhuma mensagem.</p>
<p style="color:#8694ab;font-size:13px;border-top:1px solid #eceef2;padding-top:14px">Se não foi você, ignore este e-mail — nada será enviado sem esta confirmação. O link expira em 7 dias.</p></div>`;
  const texto = `Confirme sua inscrição nos alertas ${escopoTxt}.\n\n${link}\n\nVocê só receberá e-mail quando houver mudança (município entrando em alerta ou agravando). Se não foi você, ignore — nada será enviado sem confirmação.`;
  return { html, texto };
}

Deno.serve(async (req) => {
  if (req.method === "OPTIONS") return new Response("ok", { headers: CORS });

  const url = new URL(req.url);
  const rota = url.pathname.split("/").filter(Boolean).pop();

  try {
    // ── Status ───────────────────────────────────────────────────────────────
    // O site consulta antes de exibir o formulário: não se oferece a alguém um
    // campo que não pode funcionar. Quando a chave for configurada, o
    // formulário passa a aparecer sozinho — sem redeploy do site.
    if (rota === "status" && req.method === "GET") {
      // Checar só a PRESENÇA da chave dá confiança falsa: uma chave revogada ou
      // copiada pela metade responde "configurado" e o formulário aparece, mas
      // toda inscrição falha. Aqui a chave é de fato validada contra o provedor.
      // Se o provedor estiver inacessível, assume-se configurado (falha
      // transitória não deve esconder o formulário).
      let configurado = !!RESEND_API_KEY;
      let motivo: string | undefined;
      if (RESEND_API_KEY) {
        try {
          const r = await fetch("https://api.resend.com/domains", {
            headers: { Authorization: `Bearer ${RESEND_API_KEY}` },
            signal: AbortSignal.timeout(5000),
          });
          if (r.status === 401 || r.status === 400 || r.status === 403) {
            configurado = false;
            motivo = "chave do provedor recusada";
            console.error("[alertas-assinatura] chave do provedor recusada:", r.status);
          }
        } catch {
          /* provedor inacessível: mantém o formulário no ar */
        }
      } else {
        motivo = "chave do provedor ausente";
      }
      return json(
        { email_configurado: configurado, motivo },
        200,
        { "cache-control": "public, max-age=120" },
      );
    }

    // ── Inscrever ────────────────────────────────────────────────────────────
    if (rota === "assinar" && req.method === "POST") {
      let corpo: { email?: string; uf?: string; consentimento?: boolean };
      try { corpo = await req.json(); } catch { return json({ ok: false, erro: "corpo inválido" }, 400); }

      // Validação SEMPRE antes da checagem de configuração: erro do usuário deve
      // responder 400 mesmo que o serviço de e-mail esteja fora do ar.
      const email = (corpo.email ?? "").trim();
      const uf = ((corpo.uf ?? "").trim().toUpperCase()) || null;
      if (!email || !/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(email)) {
        return json({ ok: false, erro: "Informe um e-mail válido." }, 400);
      }
      if (uf && !UFS.has(uf)) {
        return json({ ok: false, erro: "UF inválida." }, 400);
      }
      if (corpo.consentimento !== true) {
        return json({ ok: false, erro: "É preciso concordar com o uso do e-mail para este fim." }, 400);
      }

      if (!RESEND_API_KEY) {
        return json({ ok: false, email_configurado: false,
          erro: "A inscrição por e-mail ainda não está disponível." }, 503);
      }

      const { data, error } = await db.rpc("alerta_assinar", { p_email: email, p_uf: uf });
      if (error) throw error;
      if (data?.ok === false) return json({ ok: false, erro: "Informe um e-mail válido." }, 400);

      // Só manda e-mail se há token novo. Já confirmado ou throttled: responde
      // igual, sem revelar o estado do cadastro a quem não é dono do e-mail.
      if (data?.token_confirmacao) {
        const link = `${FUNC_URL}/confirmar?token=${data.token_confirmacao}`;
        const { html, texto } = emailConfirmacao(link, data.uf ?? null);
        try {
          await enviarEmail(email, "Confirme sua inscrição — alertas do Saúde em Dado", html, texto);
        } catch (e) {
          // O provedor recusou DEPOIS de gravarmos a inscrição. Se deixássemos a
          // linha pendente, o assinante ficaria num beco sem saída: sem link para
          // confirmar e, ao tentar de novo dentro de uma hora, o anti-abuso
          // responderia "ok" sem reenviar nada. Desfazemos para que a
          // retentativa funcione de imediato.
          await db.rpc("alerta_desfazer_pendente", { p_token: data.token_confirmacao });
          const prov = e instanceof ErroProvedor;
          console.error("[alertas-assinatura] envio recusado pelo provedor:",
            prov ? `${(e as ErroProvedor).status} ${(e as ErroProvedor).detalhe}` : String((e as Error).message));
          return json({
            ok: false,
            erro: "Não conseguimos enviar o e-mail de confirmação agora. "
                + "Sua inscrição não foi registrada — tente novamente em alguns minutos.",
          }, 502);
        }
      }
      return json({ ok: true, mensagem: "Se o endereço estiver correto, você receberá um e-mail para confirmar a inscrição." });
    }

    // ── Confirmar ────────────────────────────────────────────────────────────
    if (rota === "confirmar" && req.method === "GET") {
      const token = url.searchParams.get("token") ?? "";
      const { data, error } = await db.rpc("alerta_confirmar", { p_token: token });
      if (error || data?.ok === false) {
        return pagina("Link inválido", `<h1>Link inválido ou expirado</h1>
<p>Não encontramos essa inscrição. O link pode já ter sido usado ou expirado.</p>
<a class="btn" href="${SITE}/boletim-semanal/">Inscrever novamente</a>`, 404);
      }
      const escopo = data.uf ? `de <strong>${data.uf}</strong>` : "de <strong>todo o Brasil</strong>";
      const cancelar = `${FUNC_URL}/cancelar?token=${data.token_cancelamento}`;
      return pagina("Inscrição confirmada", `<h1>Inscrição confirmada ✓</h1>
<p>Você receberá um e-mail quando um município ${escopo} entrar em alerta de dengue ou chikungunya, ou quando um alerta existente se agravar.</p>
<p>Nas semanas sem mudança, não enviamos nada.</p>
<a class="btn" href="${SITE}/boletim-semanal/">Ver o boletim desta semana</a>
<p class="s">Quer sair? <a href="${cancelar}" style="color:#107752">Cancelar a inscrição</a> — este link também vai no rodapé de cada alerta.</p>`);
    }

    // ── Cancelar ─────────────────────────────────────────────────────────────
    if (rota === "cancelar" && req.method === "GET") {
      const token = url.searchParams.get("token") ?? "";
      const { data, error } = await db.rpc("alerta_cancelar", { p_token: token });
      if (error || data?.ok === false) {
        return pagina("Link inválido", `<h1>Link inválido</h1>
<p>Essa inscrição não foi encontrada — talvez já tenha sido cancelada.</p>
<a class="btn" href="${SITE}/">Ir para o site</a>`, 404);
      }
      return pagina("Inscrição cancelada", `<h1>Inscrição cancelada</h1>
<p>Seu endereço foi <strong>apagado</strong> da nossa base — não guardamos registro de quem cancelou.</p>
<p>Você não receberá mais alertas. O boletim continua aberto no site, sem cadastro.</p>
<a class="btn" href="${SITE}/boletim-semanal/">Ver o boletim</a>`);
    }

    return json({ ok: false, erro: "rota não encontrada" }, 404);
  } catch (e) {
    const msg = String((e as Error)?.message ?? e);
    if (msg.includes("email_nao_configurado")) {
      return json({ ok: false, email_configurado: false, erro: "envio de e-mail não configurado" }, 503);
    }
    console.error("[alertas-assinatura]", msg);
    return json({ ok: false, erro: "falha interna" }, 500);
  }
});
