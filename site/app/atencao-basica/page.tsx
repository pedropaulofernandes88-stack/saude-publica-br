import type { Metadata } from "next";
import { AtencaoBasicaCliente } from "./atencao-basica-cliente";

/**
 * Wrapper de servidor: um componente "use client" não pode exportar `metadata`,
 * e sem isso a rota herdava o title da home e um canonical apontando para "/" —
 * declarando-se duplicata dela para os buscadores.
 */
export const metadata: Metadata = {
  title: "Cobertura da Atenção Primária por município",
  description:
    "Cobertura potencial da Atenção Primária à Saúde por município e mês (2021–2026), do e-Gestor AB: equipes credenciadas, capacidade instalada e a crítica metodológica do indicador.",
  alternates: { canonical: "/atencao-basica/" },
  openGraph: {
    title: "Cobertura da Atenção Primária por município — Saúde em Dado",
    description: "Cobertura potencial da Atenção Primária à Saúde por município e mês (2021–2026), do e-Gestor AB: equipes credenciadas, capacidade instalada e a crítica metodológica do indicador.",
    url: "https://saudeemdado.com/atencao-basica/",
    type: "website",
  },
};

export default function AtencaoBasica() {
  return <AtencaoBasicaCliente />;
}
