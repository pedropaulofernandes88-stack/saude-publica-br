import type { Metadata } from "next";
import { HospitalarCliente } from "./hospitalar-cliente";

/**
 * Wrapper de servidor: um componente "use client" não pode exportar `metadata`,
 * e sem isso a rota herdava o title da home e um canonical apontando para "/" —
 * declarando-se duplicata dela para os buscadores.
 */
export const metadata: Metadata = {
  title: "Visão hospitalar: HSMR, permanência e projeção de demanda",
  description:
    "Inteligência por estabelecimento (CNES) a partir do SIH/AIH: mortalidade hospitalar ajustada por case-mix (HSMR), tempo de permanência esperado por diagnóstico e projeção de demanda mensal.",
  alternates: { canonical: "/hospitalar/" },
  openGraph: {
    title: "Visão hospitalar: HSMR, permanência e projeção de demanda — Saúde em Dado",
    description: "Inteligência por estabelecimento (CNES) a partir do SIH/AIH: mortalidade hospitalar ajustada por case-mix (HSMR), tempo de permanência esperado por diagnóstico e projeção de demanda mensal.",
    url: "https://saudeemdado.com/hospitalar/",
    type: "website",
  },
};

export default function Hospitalar() {
  return <HospitalarCliente />;
}
