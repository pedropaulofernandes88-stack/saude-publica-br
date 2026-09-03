import type { Metadata } from "next";
import { TendenciasCliente } from "./tendencias-cliente";

/**
 * Wrapper de servidor: um componente "use client" não pode exportar `metadata`,
 * e sem isso a rota herdava o title da home e um canonical apontando para "/" —
 * declarando-se duplicata dela para os buscadores.
 */
export const metadata: Metadata = {
  title: "Excesso de mortalidade no Brasil",
  description:
    "Série mensal desde 2015 e excesso de mortalidade por UF: observado versus esperado pela tendência 2015–2019, cruzado com vulnerabilidade social.",
  alternates: { canonical: "/tendencias/" },
  openGraph: {
    title: "Excesso de mortalidade no Brasil — Saúde em Dado",
    description: "Série mensal desde 2015 e excesso de mortalidade por UF: observado versus esperado pela tendência 2015–2019, cruzado com vulnerabilidade social.",
    url: "https://saudeemdado.com/tendencias/",
    type: "website",
  },
};

export default function Tendencias() {
  return <TendenciasCliente />;
}
