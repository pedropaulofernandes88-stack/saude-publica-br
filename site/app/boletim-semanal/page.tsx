import type { Metadata } from "next";
import { BoletimSemanalCliente } from "./boletim-semanal-cliente";

/**
 * Wrapper de servidor: um componente "use client" não pode exportar `metadata`,
 * e sem isso a rota herdava o title da home e um canonical apontando para "/" —
 * declarando-se duplicata dela para os buscadores.
 */
export const metadata: Metadata = {
  title: "Boletim epidemiológico semanal",
  description:
    "Vigilância semanal de dengue (InfoDengue/Fiocruz) com nowcasting e rede sentinela, mais retrospectiva de mortalidade, internações e excesso de mortalidade do DataSUS.",
  alternates: { canonical: "/boletim-semanal/" },
  openGraph: {
    title: "Boletim epidemiológico semanal — Saúde em Dado",
    description: "Vigilância semanal de dengue (InfoDengue/Fiocruz) com nowcasting e rede sentinela, mais retrospectiva de mortalidade, internações e excesso de mortalidade do DataSUS.",
    url: "https://saudeemdado.com/boletim-semanal/",
    type: "website",
  },
};

export default function BoletimSemanal() {
  return <BoletimSemanalCliente />;
}
