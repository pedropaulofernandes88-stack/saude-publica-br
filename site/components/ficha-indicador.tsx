"use client";

import { useEffect, useState } from "react";
import { sdata } from "@/lib/api";
import { indicador } from "@/lib/indicadores";
import { tituloDoSlug } from "@/lib/metodologia-secoes";
import { periodoCoberto, tabelaPublicada, type Manifesto } from "@/lib/manifesto";

/**
 * "Como este número foi calculado?" — o contexto ao lado do número.
 *
 * POR QUE `<details>` E NÃO UM MODAL
 * ----------------------------------
 * O elemento nativo já é acessível por teclado, já anuncia estado a leitor de
 * tela, já funciona sem JavaScript e já imprime — um modal reimplementaria as
 * quatro coisas, e as três primeiras costumam sair erradas. O único ajuste é
 * de impressão: no papel a ficha abre sozinha (`globals.css`), porque um
 * "clique para expandir" impresso é instrução que ninguém pode seguir.
 *
 * O QUE ELA MONTA, E DE ONDE
 * --------------------------
 * Definição, numerador, denominador e limitações vêm de `lib/indicadores.ts`,
 * que é texto editorial. Competência, número de linhas, versão da publicação e
 * checksum vêm do manifesto — então mudam sozinhos quando o dado muda, sem que
 * ninguém precise lembrar de reescrever a ficha. É a mesma disciplina de
 * `cobertura()`: o que pode ser derivado é derivado.
 *
 * O manifesto é buscado uma vez e compartilhado entre as fichas da página, por
 * um cache de módulo. Sem ele, uma página com cinco cartões faria cinco
 * requisições ao mesmo JSON.
 */

let cache: Promise<Manifesto> | null = null;
function carregarManifesto(): Promise<Manifesto> {
  cache ??= sdata<Manifesto>("manifesto");
  return cache;
}

/**
 * A citação vem de `meta_dataset`, que a deriva do `CITATION.cff` — não é uma
 * terceira cópia da frase. Marts derivados estão sob CC BY 4.0, em que
 * atribuição é condição da licença: a ficha é onde ela fica ao alcance de quem
 * está olhando o número, e não a três cliques dele.
 */
let cacheMeta: Promise<{ chave: string; valor: string }[]> | null = null;
function carregarMeta(): Promise<{ chave: string; valor: string }[]> {
  cacheMeta ??= sdata<{ chave: string; valor: string }[]>("meta");
  return cacheMeta;
}

function Linha({ termo, children }: { termo: string; children: React.ReactNode }) {
  return (
    <div className="grid gap-0.5 py-1.5 sm:grid-cols-[10rem_1fr] sm:gap-3">
      <dt className="text-xs font-semibold uppercase tracking-wide text-ink-500">{termo}</dt>
      <dd className="text-sm text-ink-700">{children}</dd>
    </div>
  );
}

export function FichaIndicador({ id, contexto }: { id: string; contexto?: string }) {
  const ind = indicador(id);
  const [manifesto, setManifesto] = useState<Manifesto | null>(null);
  const [citacao, setCitacao] = useState<string | null>(null);
  const [aberta, setAberta] = useState(false);
  const [copiado, setCopiado] = useState(false);

  // Só busca o manifesto quando alguém abre a primeira ficha da página: o
  // arquivo não serve para nada enquanto todas estão fechadas, e a home não
  // deve pagar por um contexto que ninguém pediu.
  useEffect(() => {
    if (!aberta || manifesto) return;
    carregarManifesto().then(setManifesto).catch(() => setManifesto(null));
    carregarMeta()
      .then((m) => setCitacao(m.find((r) => r.chave === "como_citar")?.valor ?? null))
      .catch(() => setCitacao(null));
  }, [aberta, manifesto]);

  /** A citação com o endereço EXATO que está na barra — o recorte é a análise. */
  const textoCitacao = () => {
    const hoje = new Date().toISOString().slice(0, 10);
    const url = typeof window === "undefined" ? "" : window.location.href;
    return `${citacao ?? "Fernandes, P. P. Saúde em Dado. https://saudeemdado.com"}`
      + ` Indicador: ${ind.rotulo}${contexto ? ` (${contexto})` : ""}.`
      + ` Consulta: ${url} Acesso em: ${hoje}.`;
  };

  const tab = tabelaPublicada(manifesto, ind.tabela);
  const periodo = periodoCoberto(tab);
  const titulo = tituloDoSlug(ind.secao);

  return (
    <details
      className="ficha mt-2 rounded-lg border border-ink-200 bg-ink-50 px-3 py-2 text-sm"
      onToggle={(e) => setAberta((e.currentTarget as HTMLDetailsElement).open)}
    >
      {/* O resumo NOMEIA o indicador. Ele nem sempre fica colado a um cartão
          só — no boletim as três fichas de mortalidade ficam juntas abaixo dos
          KPIs, porque dentro da coluna do cartão a lista de definições era
          espremida a um terço da largura e ficava ilegível. "Este número" só
          funciona quando há um número e ele está ao lado. */}
      <summary className="cursor-pointer list-none text-xs font-medium text-accent-700 marker:content-none">
        Como calculamos: {ind.rotulo}
      </summary>

      <dl className="mt-2 divide-y divide-ink-200 border-t border-ink-200 pt-1">
        <Linha termo="Indicador">
          {ind.rotulo} <span className="text-ink-500">({ind.unidade})</span>
        </Linha>
        <Linha termo="Definição">{ind.definicao}</Linha>
        <Linha termo="Numerador">{ind.numerador}</Linha>
        {ind.denominador && <Linha termo="Denominador">{ind.denominador}</Linha>}
        {contexto && <Linha termo="Recorte exibido">{contexto}</Linha>}
        <Linha termo="Fonte">
          <code className="break-all rounded bg-white px-1 py-0.5 text-xs">{ind.tabela}</code>
          {tab ? (
            <>
              {" · "}
              {tab.linhas.toLocaleString("pt-BR")} linhas
              {periodo && ` · cobre ${periodo}`}
              {!tab.servida && (
                <span className="ml-1 rounded bg-amber-100 px-1.5 py-0.5 text-[11px] text-amber-800">
                  só download
                </span>
              )}
            </>
          ) : (
            <span className="text-ink-500"> · carregando…</span>
          )}
        </Linha>
        {tab?.publicada_em && (
          <Linha termo="Versão do dado">
            publicação <span className="font-mono">{tab.publicada_em}</span>
            {tab.sha256 && (
              <>
                {" · "}
                <span className="font-mono text-xs text-ink-500" title={tab.sha256}>
                  sha256 {tab.sha256.slice(0, 12)}…
                </span>
              </>
            )}
          </Linha>
        )}
        <Linha termo="O que não afirma">
          <ul className="list-disc space-y-1 pl-4">
            {ind.limitacoes.map((l) => <li key={l}>{l}</li>)}
          </ul>
        </Linha>
        <Linha termo="Como citar">
          <p className="text-xs leading-relaxed text-ink-600">{textoCitacao()}</p>
          <button
            type="button"
            className="mt-1 rounded border border-ink-300 bg-white px-2 py-1 text-xs font-medium text-ink-700 no-print"
            onClick={async () => {
              try {
                await navigator.clipboard.writeText(textoCitacao());
                setCopiado(true);
              } catch {
                setCopiado(false);
              }
            }}
          >
            {copiado ? "✓ Citação copiada" : "Copiar citação"}
          </button>
        </Linha>
        <Linha termo="Método">
          {/* Sem repetir a publicação: ela já está em "versão do dado", e o
              mesmo identificador duas vezes na mesma ficha faz o leitor
              procurar a diferença entre eles. */}
          <a className="text-accent-700 underline" href={`/metodologia/#${ind.secao}`}>
            {titulo ?? "Metodologia"}
          </a>
        </Linha>
      </dl>
    </details>
  );
}
