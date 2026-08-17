import type { Metadata } from "next";
import { BoletimCliente } from "./boletim-cliente";

/**
 * Wrapper de servidor: um componente "use client" não pode exportar `metadata`,
 * e sem isso a rota herdava o title da home e um canonical apontando para "/" —
 * declarando-se duplicata dela para os buscadores.
 */
export const metadata: Metadata = {
  title: "Boletim municipal de mortalidade",
  description:
    "Boletim por município: óbitos, taxa bruta e padronizada com IC95%, contexto social do Censo 2022, internações evitáveis e comparação com municípios pares.",
  alternates: { canonical: "/boletim/" },
  openGraph: {
    title: "Boletim municipal de mortalidade — Saúde em Dado",
    description: "Boletim por município: óbitos, taxa bruta e padronizada com IC95%, contexto social do Censo 2022, internações evitáveis e comparação com municípios pares.",
    url: "https://saudeemdado.com/boletim/",
    type: "website",
  },
};

export default function Boletim() {
  return <BoletimCliente />;
}
