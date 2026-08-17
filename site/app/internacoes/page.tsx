import type { Metadata } from "next";
import { InternacoesCliente } from "./internacoes-cliente";

/**
 * Wrapper de servidor. Existe para esta rota poder ter metadata própria: um
 * componente "use client" não pode exportar `metadata`, e por isso a página
 * herdava o título e — pior — o canônico da home, declarando-se duplicata dela
 * para os buscadores.
 */
export const metadata: Metadata = {
  title: "Internações hospitalares no SUS por município",
  description:
    "Internações pagas pelo SUS (SIH/DataSUS, 2022–2024) por município e capítulo CID-10: "
    + "permanência média, mortalidade hospitalar, custo médio, internações evitáveis (ICSAP), "
    + "fluxo intermunicipal de pacientes e visão por hospital (CNES).",
  alternates: { canonical: "/internacoes/" },
  openGraph: {
    title: "Internações hospitalares no SUS por município — Saúde em Dado",
    description:
      "SIH/DataSUS 2022–2024 por município e causa: permanência, mortalidade hospitalar, custo, "
      + "ICSAP e visão por hospital.",
    url: "https://saudeemdado.com/internacoes/",
    type: "website",
  },
};

export default function Internacoes() {
  return <InternacoesCliente />;
}
