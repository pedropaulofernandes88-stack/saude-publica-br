"use client";

import { useState } from "react";

/**
 * Recorta verticalmente um bloco alto (tipicamente uma tabela de ranking) e
 * oferece um botão para revelar o resto.
 *
 * Por que existe: /internacoes/ chegava a 19,5 telas de scroll no celular, e
 * 70% dessa altura eram seis tabelas somando 181 linhas — duas delas com 50
 * linhas cada. Quem varre um ranking quer o topo; as outras 40 linhas são
 * consulta, não leitura.
 *
 * A tabela inteira continua no DOM, apenas recortada visualmente. Isso é
 * deliberado: leitor de tela e Ctrl+F seguem alcançando todas as linhas, e
 * nenhuma das tabelas tem link ou botão dentro (conferido), então não há foco
 * de teclado preso na parte oculta.
 */
export function VerMais({
  children,
  alturaFechada = 340,
  total,
  rotulo = "linhas",
}: {
  children: React.ReactNode;
  /** Altura visível quando fechado, em px. ~340 mostra 8–10 linhas de tabela. */
  alturaFechada?: number;
  /** Quantas linhas existem no total — vai no rótulo do botão. */
  total?: number;
  /** Nome do que está sendo listado, no plural: "municípios", "hospitais". */
  rotulo?: string;
}) {
  const [aberto, setAberto] = useState(false);
  const id = `ver-mais-${rotulo.replace(/\s+/g, "-")}`;

  return (
    <div>
      {/*
        `overflow-x-auto` SEMPRE, `overflow-y-hidden` só quando fechado.
        Antes era `overflow-hidden` nos dois eixos, e isso não recortava só a
        altura: numa tela de 375px a tabela do painel mede 852px, e as colunas
        além do corte ficavam INALCANÇÁVEIS — o `overflow-x-auto` do container
        de fora nunca via transbordo nenhum, porque este div já havia cortado.
        Não era tabela apertada, era dado escondido.
        Deixar o eixo X rolável aqui também torna ESTE o container de rolagem
        nos dois estados, aberto e fechado, que é o que a coluna presa
        (`col-id`) precisa para ter contra o que ficar parada.
      */}
      <div
        id={id}
        className={`relative overflow-x-auto${aberto ? "" : " overflow-y-hidden"}`}
        style={aberto ? undefined : { maxHeight: alturaFechada }}
      >
        {children}
        {!aberto && (
          // Sinaliza que há mais conteúdo — sem isso o corte parece defeito.
          <div
            aria-hidden
            className="pointer-events-none absolute inset-x-0 bottom-0 h-14 bg-gradient-to-t from-white to-transparent"
          />
        )}
      </div>
      <button
        type="button"
        aria-expanded={aberto}
        aria-controls={id}
        onClick={() => setAberto((v) => !v)}
        className="mt-2 flex min-h-[44px] w-full items-center justify-center gap-1.5 rounded-lg border border-ink-200 text-sm font-medium text-accent-700 transition hover:bg-ink-50"
      >
        {aberto
          ? "Mostrar menos"
          : total
            ? `Ver todos os ${total} ${rotulo}`
            : `Ver tudo`}
        <span aria-hidden className={`text-[10px] transition ${aberto ? "rotate-180" : ""}`}>
          ▾
        </span>
      </button>
    </div>
  );
}
