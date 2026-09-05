import type { Metadata } from "next";

import { cobertura } from "@/lib/cobertura";
import { CompararCliente } from "./comparar-cliente";

/**
 * Wrapper de servidor: um componente "use client" não pode exportar `metadata`,
 * e sem isso a rota herdava o title da home e um canonical apontando para "/" —
 * declarando-se duplicata dela para os buscadores.
 */
export const metadata: Metadata = {
  title: "Comparar municípios",
  description:
    `Compare até cinco municípios lado a lado na mortalidade do SIM/DataSUS (${cobertura().periodo}): taxa padronizada por idade, taxa bruta e óbitos, com porte, vulnerabilidade e estrato de saúde à vista para julgar a comparabilidade.`,
  alternates: { canonical: "/comparar/" },
  openGraph: {
    title: "Comparar municípios — Saúde em Dado",
    description: `Até cinco municípios lado a lado na mortalidade (${cobertura().periodo}), com taxa padronizada por idade e o quadro de comparabilidade.`,
    url: "https://saudeemdado.com/comparar/",
    type: "website",
  },
};

export default function Comparar() {
  return <CompararCliente />;
}
