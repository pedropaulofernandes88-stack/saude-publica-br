"use client";

import { useCallback, useEffect, useState } from "react";
import { Skeleton } from "@/components/kpi";
import { mensagemDeErro, type Carga } from "@/lib/carga";

/**
 * O invólucro que dá cara própria a cada estado de uma consulta.
 *
 * Ver `lib/carga.ts` para o motivo de os quatro estados existirem separados. A
 * regra desta camada é curta: **falha nunca desaparece**. Um cartão que some
 * quando a rede cai faz a página afirmar, pela ausência, que o município não
 * tem aquele dado.
 */

/**
 * Executa a consulta e devolve o estado, com recarga sob demanda.
 *
 * `vazio` é decidido por quem chama, com `ehVazio`, porque só quem conhece a
 * consulta sabe o que é resposta vazia: `[]` para uma lista, `null` para uma
 * linha única, `0` para uma contagem.
 */
export function useCarga<T>(
  consulta: () => Promise<T>,
  deps: unknown[],
  ehVazio: (d: T) => boolean = (d) => d == null || (Array.isArray(d) && d.length === 0),
): [Carga<T>, () => void] {
  const [carga, setCarga] = useState<Carga<T>>({ estado: "carregando" });
  const [tentativa, setTentativa] = useState(0);

  useEffect(() => {
    let vivo = true;
    setCarga({ estado: "carregando" });
    consulta()
      .then((d) => {
        if (!vivo) return;
        setCarga(ehVazio(d) ? { estado: "vazio" } : { estado: "ok", dados: d });
      })
      .catch((e) => {
        if (vivo) setCarga({ estado: "erro", mensagem: mensagemDeErro(e) });
      });
    return () => { vivo = false; };
    // `consulta` e `ehVazio` são recriadas a cada render por quem chama; as
    // dependências reais são as que o chamador declara.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [...deps, tentativa]);

  const recarregar = useCallback(() => setTentativa((n) => n + 1), []);
  return [carga, recarregar];
}

export function Bloco<T>({
  carga, recarregar, titulo, vazio, altura = 200, children,
}: {
  carga: Carga<T>;
  recarregar?: () => void;
  /** Nome do que falhou, para a mensagem dizer o que não carregou. */
  titulo: string;
  /** Texto quando a consulta respondeu e não há dado para o recorte. */
  vazio?: string;
  altura?: number;
  children: (dados: T) => React.ReactNode;
}) {
  if (carga.estado === "carregando") return <Skeleton altura={altura} />;

  if (carga.estado === "erro") {
    return (
      <div className="card mt-6 border-red-200 bg-red-50">
        <p className="text-sm text-red-900">
          <strong>{titulo}</strong> não carregou — {carga.mensagem}.
        </p>
        <p className="mt-1 text-xs text-red-800">
          Isto é falha de consulta, <strong>não</strong> ausência de dado: não conclua que este
          recorte não tem informação.
        </p>
        {recarregar && (
          <button onClick={recarregar} className="btn-ghost mt-3 no-print">↻ Tentar de novo</button>
        )}
      </div>
    );
  }

  if (carga.estado === "vazio") {
    return (
      <p className="mt-6 rounded-lg border border-ink-200 bg-ink-50 px-4 py-3 text-sm text-ink-600">
        {vazio ?? `Sem dado publicado de ${titulo.toLowerCase()} para este recorte.`}
      </p>
    );
  }

  return <>{children(carga.dados)}</>;
}
