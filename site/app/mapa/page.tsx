import type { Metadata } from "next";
import { MapaCliente } from "./mapa-cliente";

/**
 * Wrapper de servidor: um componente "use client" não pode exportar `metadata`,
 * e sem isso a rota herdava o title da home e um canonical apontando para "/" —
 * declarando-se duplicata dela para os buscadores.
 */
export const metadata: Metadata = {
  title: "Mapa municipal da mortalidade no Brasil",
  description:
    "Distribuição municipal dos óbitos (SIM/DataSUS) em mapa coroplético por quantis, com a oferta de serviços de saúde do CNES.",
  alternates: { canonical: "/mapa/" },
  openGraph: {
    title: "Mapa municipal da mortalidade no Brasil — Saúde em Dado",
    description: "Distribuição municipal dos óbitos (SIM/DataSUS) em mapa coroplético por quantis, com a oferta de serviços de saúde do CNES.",
    url: "https://saudeemdado.com/mapa/",
    type: "website",
  },
};

export default function Mapa() {
  return <MapaCliente />;
}
