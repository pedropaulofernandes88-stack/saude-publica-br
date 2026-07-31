"use client";

import { useEffect, useState } from "react";
import { SUPABASE_URL, UFS } from "@/lib/api";

const BASE = `${SUPABASE_URL}/functions/v1/alertas-assinatura`;

type Estado = "ocioso" | "enviando" | "ok" | "erro";

/** Convite ao feed: entrega sem provedor de e-mail, sem cadastro, sem dado pessoal. */
function LinhaFeed() {
  return (
    <p className="mt-3 border-t border-ink-100 pt-3 text-sm text-ink-600">
      Prefere não deixar e-mail? Assine o{" "}
      <a href="/alertas.xml" className="font-medium text-accent-700 underline">feed de alertas</a>{" "}
      em qualquer leitor de RSS — só recebe entrada quando algum município muda de situação.
      Há também o{" "}
      <a href="/boletim.xml" className="font-medium text-accent-700 underline">feed de todas as edições</a>.
    </p>
  );
}

/** Quando o envio por e-mail não está operante, o feed segue disponível. */
function SomenteFeed() {
  return (
    <div className="card mt-6 no-print">
      <h2 className="font-serif text-xl font-semibold text-ink-900">
        Acompanhe os alertas por feed
      </h2>
      <p className="mt-1.5 text-sm leading-relaxed text-ink-600">
        A rede sentinela detecta surtos toda semana. Assine o{" "}
        <a href="/alertas.xml" className="font-medium text-accent-700 underline">feed de alertas</a>{" "}
        em qualquer leitor de RSS e receba uma entrada <strong>só quando houver mudança</strong> —
        um município entrando em alerta ou um alerta se agravando. Sem cadastro e sem e-mail.
      </p>
      <p className="mt-2 text-sm text-ink-600">
        Para acompanhar todas as edições, inclusive as semanas sem novidade, use o{" "}
        <a href="/boletim.xml" className="font-medium text-accent-700 underline">feed do boletim</a>.
      </p>
    </div>
  );
}

/**
 * Assinatura do alerta epidemiológico.
 *
 * Coleta o mínimo necessário (e-mail + UF de interesse) com consentimento
 * explícito. O opt-in é duplo: nada é enviado antes de o assinante confirmar
 * pelo link, e o cancelamento apaga o registro.
 */
export function AssinarAlertas() {
  const [email, setEmail] = useState("");
  const [uf, setUf] = useState("");
  const [consentimento, setConsentimento] = useState(false);
  const [estado, setEstado] = useState<Estado>("ocioso");
  const [mensagem, setMensagem] = useState("");
  // null = ainda verificando. Não se oferece à pessoa um campo que não pode
  // funcionar: o formulário só aparece quando o envio está operante, e passa a
  // aparecer sozinho quando a chave for configurada (sem redeploy do site).
  const [disponivel, setDisponivel] = useState<boolean | null>(null);

  useEffect(() => {
    let vivo = true;
    fetch(`${BASE}/status`)
      .then((r) => r.json())
      .then((d) => { if (vivo) setDisponivel(!!d.email_configurado); })
      .catch(() => { if (vivo) setDisponivel(false); });
    return () => { vivo = false; };
  }, []);

  async function enviar(e: React.FormEvent) {
    e.preventDefault();
    setEstado("enviando");
    setMensagem("");
    try {
      const res = await fetch(`${BASE}/assinar`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, uf: uf || null, consentimento }),
      });
      const dados = await res.json().catch(() => ({}));
      if (res.ok && dados.ok) {
        setEstado("ok");
        setMensagem(dados.mensagem ?? "Verifique sua caixa de entrada para confirmar.");
      } else if (dados.email_configurado === false) {
        // O serviço caiu entre a checagem e o envio: recolhe o formulário em
        // vez de deixar a pessoa tentando de novo em vão.
        setDisponivel(false);
      } else {
        setEstado("erro");
        setMensagem(dados.erro ?? "Não foi possível concluir a inscrição agora.");
      }
    } catch {
      setEstado("erro");
      setMensagem("Falha de conexão. Tente novamente em instantes.");
    }
  }

  // Enquanto verifica, não renderiza nada. Se o envio não está operante, ainda
  // assim oferece o feed — que não depende de provedor de e-mail nem cadastro.
  if (disponivel === null) return null;
  if (disponivel === false) return <SomenteFeed />;

  if (estado === "ok") {
    return (
      <div className="card mt-6 border-accent-700/30 bg-accent-700/[0.04]">
        <h2 className="font-serif text-xl font-semibold text-ink-900">Quase lá ✉</h2>
        <p className="mt-2 text-ink-700">{mensagem}</p>
        <p className="mt-2 text-sm text-ink-500">
          O link de confirmação vale por 7 dias. Sem essa confirmação, seu endereço é
          apagado automaticamente e nada é enviado.
        </p>
      </div>
    );
  }

  return (
    <div className="card mt-6 no-print">
      <h2 className="font-serif text-xl font-semibold text-ink-900">
        Receba um aviso quando sua região entrar em alerta
      </h2>
      <p className="mt-1.5 text-sm leading-relaxed text-ink-600">
        A rede sentinela detecta surtos toda semana — mas ninguém em Sobral descobre isso
        visitando um site. Deixe seu e-mail e avisamos <strong>quando houver mudança</strong>:
        um município entrando em alerta ou um alerta se agravando. Semana sem novidade,
        nenhuma mensagem.
      </p>

      <form onSubmit={enviar} className="mt-4 space-y-3">
        <div className="grid gap-3 sm:grid-cols-[1fr_auto]">
          <div>
            <label htmlFor="alerta-email" className="block text-xs font-semibold uppercase tracking-wide text-ink-500">
              Seu e-mail
            </label>
            <input
              id="alerta-email"
              type="email"
              required
              value={email}
              onChange={(ev) => setEmail(ev.target.value)}
              placeholder="voce@exemplo.gov.br"
              className="mt-1 w-full rounded-lg border border-ink-200 px-3 py-2 text-sm text-ink-900 outline-none focus:border-accent-700 focus:ring-1 focus:ring-accent-700"
            />
          </div>
          <div>
            <label htmlFor="alerta-uf" className="block text-xs font-semibold uppercase tracking-wide text-ink-500">
              Acompanhar
            </label>
            <select
              id="alerta-uf"
              value={uf}
              onChange={(ev) => setUf(ev.target.value)}
              className="mt-1 w-full rounded-lg border border-ink-200 bg-white px-3 py-2 text-sm text-ink-900 outline-none focus:border-accent-700 focus:ring-1 focus:ring-accent-700 sm:w-40"
            >
              <option value="">Brasil inteiro</option>
              {UFS.map((u) => <option key={u} value={u}>{u}</option>)}
            </select>
          </div>
        </div>

        <label className="flex items-start gap-2.5 text-sm text-ink-600">
          <input
            type="checkbox"
            required
            checked={consentimento}
            onChange={(ev) => setConsentimento(ev.target.checked)}
            className="mt-1 h-4 w-4 shrink-0 rounded border-ink-300 text-accent-700 focus:ring-accent-700"
          />
          <span>
            Concordo que meu e-mail seja usado <strong>somente</strong> para enviar estes
            alertas. Não compartilhamos com ninguém, não enviamos publicidade, e o
            cancelamento (em um clique, no rodapé de cada mensagem) <strong>apaga</strong> meu
            endereço da base.
          </span>
        </label>

        {estado === "erro" && (
          <p className="rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-800">
            {mensagem}
          </p>
        )}

        <button type="submit" disabled={estado === "enviando"} className="btn-primary disabled:opacity-60">
          {estado === "enviando" ? "Enviando…" : "Quero ser avisado"}
        </button>
      </form>

      <p className="mt-3 border-t border-ink-100 pt-3 text-xs leading-relaxed text-ink-500">
        Guardamos apenas o e-mail e a UF escolhida — sem nome, sem telefone, sem rastreio.
        A inscrição só vale após você confirmar por link (opt-in duplo). Base de dados
        isolada da API pública do projeto. Dúvidas sobre tratamento de dados:{" "}
        <a href="mailto:pedropaulofernandes88@gmail.com" className="text-accent-700 underline">
          fale com o mantenedor
        </a>.
      </p>
      <LinhaFeed />
    </div>
  );
}
