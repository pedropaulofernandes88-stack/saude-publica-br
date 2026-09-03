import type { Metadata } from "next";

import { ANOS_SINASC } from "@/lib/api";
import { NascimentosCliente } from "./nascimentos-cliente";

/**
 * Wrapper de servidor: um componente "use client" não pode exportar `metadata`,
 * e sem isso a rota herdava o title da home e um canonical apontando para "/" —
 * declarando-se duplicata dela para os buscadores.
 */
export const metadata: Metadata = {
  title: "Nascimentos e mortalidade infantil por município",
  description:
    `Nascidos vivos (SINASC/DataSUS, ${ANOS_SINASC[0]}–${ANOS_SINASC[ANOS_SINASC.length - 1]}) por município — peso ao nascer, prematuridade e pré-natal — e a Taxa de Mortalidade Infantil por UF.`,
  alternates: { canonical: "/nascimentos/" },
  openGraph: {
    title: "Nascimentos e mortalidade infantil por município — Saúde em Dado",
    description: `Nascidos vivos (SINASC/DataSUS, ${ANOS_SINASC[0]}–${ANOS_SINASC[ANOS_SINASC.length - 1]}) por município — peso ao nascer, prematuridade e pré-natal — e a Taxa de Mortalidade Infantil por UF.`,
    url: "https://saudeemdado.com/nascimentos/",
    type: "website",
  },
};

export default function Nascimentos() {
  return <NascimentosCliente />;
}
