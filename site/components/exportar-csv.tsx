"use client";

import { useState } from "react";
import { nomeDeArquivo, paraCsv, type Recorte } from "@/lib/exportar";
import { CITACAO_MINIMA, carregarManifesto, carregarMeta, valorMeta } from "@/lib/procedencia";

/**
 * Um botão de exportar para o site inteiro.
 *
 * Antes havia um só, no painel, montando o CSV à mão dentro do componente da
 * página. Cada tela nova que quisesse exportar copiaria aquele bloco — e a
 * cópia seguinte esqueceria a licença, como a primeira já esquecia.
 *
 * O TRABALHO SÓ ACONTECE NO CLIQUE
 * --------------------------------
 * `linhas` é uma função, não um array: montar a matriz de exportação a cada
 * render custaria em toda página que tem tabela grande, para servir a quem
 * talvez nunca clique. O manifesto e a citação também só são buscados aqui — e
 * pelo cache de módulo de `lib/procedencia.ts`, se a ficha de indicador já os
 * pediu, não há segunda requisição.
 *
 * FALHA NÃO PODE VIRAR ARQUIVO SEM PROCEDÊNCIA
 * --------------------------------------------
 * Se o manifesto não responder, o arquivo sai mesmo assim — com a citação
 * mínima e sem as linhas de versão, e a tela DIZ que saiu incompleto. O que não
 * pode acontecer é o botão fingir sucesso: quem baixou precisa saber que aquele
 * arquivo não carrega o checksum da publicação. É a mesma regra de
 * `lib/carga.ts`, do outro lado do fluxo.
 */
export function BotaoExportarCsv({
  recorte, colunas, linhas, base, rotulo = "⬇ Exportar CSV", desabilitado,
}: {
  recorte: Recorte;
  colunas: string[];
  /** Só é chamada no clique. */
  linhas: () => unknown[][];
  /** Começo do nome do arquivo, antes dos filtros e da data. */
  base: string;
  rotulo?: string;
  desabilitado?: boolean;
}) {
  const [estado, setEstado] = useState<"pronto" | "gerando" | "parcial" | "erro">("pronto");

  async function exportar() {
    setEstado("gerando");
    // `allSettled`: a ausência do manifesto degrada o cabeçalho, não impede o
    // download. Quem está com a rede instável precisa mais do dado do que da
    // linha de checksum — mas precisa SABER que ela não veio.
    const [m, meta] = await Promise.allSettled([carregarManifesto(), carregarMeta()]);
    const manifesto = m.status === "fulfilled" ? m.value : null;
    const citacao = meta.status === "fulfilled"
      ? valorMeta(meta.value, "como_citar") ?? CITACAO_MINIMA
      : CITACAO_MINIMA;

    try {
      const agora = new Date();
      const url = typeof window === "undefined" ? recorte.url : window.location.href;
      const texto = paraCsv({ ...recorte, url }, colunas, linhas(), manifesto, citacao, agora);
      // BOM: sem ele o Excel em português abre "óbitos" como "Ã³bitos".
      const blob = new Blob(["﻿" + texto], { type: "text/csv;charset=utf-8" });
      const a = document.createElement("a");
      a.href = URL.createObjectURL(blob);
      a.download = nomeDeArquivo(base, recorte.filtros, agora);
      a.click();
      URL.revokeObjectURL(a.href);
      setEstado(manifesto ? "pronto" : "parcial");
    } catch {
      setEstado("erro");
    }
  }

  return (
    <span className="inline-flex flex-col items-start gap-1">
      <button onClick={exportar} className="btn-ghost no-print"
              disabled={desabilitado || estado === "gerando"}>
        {estado === "gerando" ? "Gerando…" : rotulo}
      </button>
      {estado === "parcial" && (
        <span className="text-xs text-amber-800">
          Baixado sem a versão da publicação — o manifesto não respondeu. Os números são os
          da tela; o cabeçalho não traz competência nem checksum.
        </span>
      )}
      {estado === "erro" && (
        <span className="text-xs text-red-800">Não foi possível gerar o arquivo.</span>
      )}
    </span>
  );
}
