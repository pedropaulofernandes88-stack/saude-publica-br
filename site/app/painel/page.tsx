import type { Metadata } from "next";
import { PainelCliente } from "./painel-cliente";

/**
 * Wrapper de servidor: um componente "use client" não pode exportar `metadata`,
 * e sem isso a rota herdava o title da home e um canonical apontando para "/" —
 * declarando-se duplicata dela para os buscadores.
 */
export const metadata: Metadata = {
  title: "Painel de mortalidade por município",
  description:
    "Mortalidade no Brasil (SIM/DataSUS, 2015–2024) por município, causa (CID-10), sexo e faixa etária: taxas padronizadas por idade com IC95%, série mensal e ranking municipal exportável.",
  alternates: { canonical: "/painel/" },
  openGraph: {
    title: "Painel de mortalidade por município — Saúde em Dado",
    description: "Mortalidade no Brasil (SIM/DataSUS, 2015–2024) por município, causa (CID-10), sexo e faixa etária: taxas padronizadas por idade com IC95%, série mensal e ranking municipal exportável.",
    url: "https://saudeemdado.com/painel/",
    type: "website",
  },
};

export default function Painel() {
  return <PainelCliente />;
}
