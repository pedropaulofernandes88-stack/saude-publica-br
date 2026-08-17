import type { Metadata } from "next";
import { DengueCliente } from "./dengue-cliente";

/**
 * Wrapper de servidor: um componente "use client" não pode exportar `metadata`,
 * e sem isso a rota herdava o title da home e um canonical apontando para "/" —
 * declarando-se duplicata dela para os buscadores.
 */
export const metadata: Metadata = {
  title: "Dengue no Brasil por município e semana",
  description:
    "Casos prováveis, gravidade, óbitos e incidência de dengue (SINAN/DataSUS, 2015–2024) por município e semana epidemiológica, com canal endêmico e a epidemia recorde de 2024.",
  alternates: { canonical: "/dengue/" },
  openGraph: {
    title: "Dengue no Brasil por município e semana — Saúde em Dado",
    description: "Casos prováveis, gravidade, óbitos e incidência de dengue (SINAN/DataSUS, 2015–2024) por município e semana epidemiológica, com canal endêmico e a epidemia recorde de 2024.",
    url: "https://saudeemdado.com/dengue/",
    type: "website",
  },
};

export default function Dengue() {
  return <DengueCliente />;
}
