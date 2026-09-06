"use client";

import { useEffect, useState } from "react";
import { linhaDaTabela, type Recorte } from "@/lib/exportar";
import { type Manifesto } from "@/lib/manifesto";
import { CITACAO_MINIMA, carregarManifesto, carregarMeta, valorMeta } from "@/lib/procedencia";

/**
 * No papel, o que o cabeçalho e o rodapé da tela levavam embora.
 *
 * `@media print` esconde `header` e `footer` — decisão certa para a tela, com
 * um efeito que ninguém tinha medido: o PDF saía sem endereço, sem fonte, sem
 * versão da publicação e sem citação. Um boletim impresso circula por e-mail,
 * é anexado a processo e é lido meses depois por quem não fez a consulta;
 * daquele jeito, era uma folha de números sem procedência.
 *
 * É o mesmo conteúdo que o CSV carrega, montado a partir do mesmo `Recorte` e
 * das mesmas funções — para que a folha e o arquivo não possam divergir.
 *
 * POR QUE BUSCA NO MOUNT, E NÃO NO `beforeprint`
 * ----------------------------------------------
 * `beforeprint` é síncrono: uma requisição disparada ali não termina antes de o
 * navegador montar as páginas, e o bloco sairia vazio justamente na hora em que
 * é a única coisa que importa. Os dois JSON são estáticos, pequenos e
 * compartilhados com a ficha de indicador pelo cache de módulo — na prática,
 * zero requisição adicional numa página que já tem ficha.
 */
export function ProcedenciaImpressa({ recorte }: { recorte: Recorte }) {
  const [manifesto, setManifesto] = useState<Manifesto | null>(null);
  const [citacao, setCitacao] = useState<string>(CITACAO_MINIMA);
  const [url, setUrl] = useState("");
  // A data de acesso NÃO pode ser calculada durante o render: a página é
  // exportada estaticamente, então o HTML no disco carrega a data do BUILD e o
  // cliente renderizaria a de hoje — "Text content does not match
  // server-rendered HTML", e o React derruba a hidratação do limite de
  // Suspense inteiro. Foi o que aconteceu: a página de comparação parou de
  // montar. Valor que depende do relógio nasce no efeito, nunca no render.
  const [dia, setDia] = useState("");

  useEffect(() => {
    setDia(new Date().toISOString().slice(0, 10));
    carregarManifesto().then(setManifesto).catch(() => setManifesto(null));
    carregarMeta()
      .then((m) => setCitacao(valorMeta(m, "como_citar") ?? CITACAO_MINIMA))
      .catch(() => {});
    setUrl(window.location.href);
  }, []);

  const filtros = recorte.filtros.filter(([, v]) => v != null && String(v).trim() !== "");

  return (
    <section className="print-only mt-6 border-t border-ink-300 pt-3 text-[10px] leading-snug text-ink-700">
      <p className="font-semibold">Saúde em Dado — {recorte.titulo}</p>

      <p className="mt-1">
        <strong>Recorte:</strong>{" "}
        {filtros.length
          ? filtros.map(([r, v]) => `${r}: ${v}`).join(" · ")
          : "sem filtros — conjunto completo desta consulta"}
      </p>

      <p className="mt-1">
        <strong>Fonte:</strong>{" "}
        {recorte.tabelas.map((t) => linhaDaTabela(t, manifesto)).join(" | ")}
      </p>

      {recorte.ressalvas?.length ? (
        <p className="mt-1"><strong>Ressalvas:</strong> {recorte.ressalvas.join(" ")}</p>
      ) : null}

      {/* A distinção vazio/zero também vale no papel: numa tabela impressa a
          célula em branco é ainda mais fácil de ler como zero. */}
      <p className="mt-1">
        <strong>Ausência:</strong> célula vazia significa sem dado publicado para o recorte;
        zero medido é escrito 0.
      </p>

      <p className="mt-1">
        <strong>Licença:</strong> CC BY 4.0 — atribuição é condição da licença. Dados originais
        em domínio público (DATASUS/MS e IBGE).
      </p>

      <p className="mt-1">
        <strong>Como citar:</strong> {citacao} Consulta: {url} Acesso em: {dia}.
      </p>
    </section>
  );
}
