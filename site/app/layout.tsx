import type { Metadata } from "next";
import { Inter, Source_Serif_4 } from "next/font/google";
import Link from "next/link";
import "./globals.css";

const inter = Inter({ subsets: ["latin"], variable: "--font-inter" });
const serif = Source_Serif_4({ subsets: ["latin"], variable: "--font-serif" });

export const metadata: Metadata = {
  title: {
    default: "Saúde Pública BR — Mortalidade no Brasil (SIM/DataSUS)",
    template: "%s · Saúde Pública BR",
  },
  description:
    "Plataforma aberta de inteligência epidemiológica: 4,4 milhões de óbitos do SIM/DataSUS (2022–2024) em painéis navegáveis e API pública gratuita, para pesquisa acadêmica.",
  keywords: [
    "DataSUS", "SIM", "mortalidade", "epidemiologia", "dados abertos",
    "saúde pública", "CID-10", "Brasil",
  ],
};

const NAV = [
  { href: "/", label: "Início" },
  { href: "/painel/", label: "Painel" },
  { href: "/dados/", label: "Dados & API" },
  { href: "/metodologia/", label: "Metodologia" },
];

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="pt-BR" className={`${inter.variable} ${serif.variable}`}>
      <body className="flex min-h-screen flex-col font-sans">
        <header className="sticky top-0 z-40 border-b border-ink-200 bg-white/90 backdrop-blur">
          <div className="mx-auto flex h-16 max-w-7xl items-center justify-between px-4 sm:px-6">
            <Link href="/" className="flex items-center gap-2.5">
              <span className="flex h-9 w-9 items-center justify-center rounded-lg bg-accent-700 font-serif text-lg font-bold text-white">
                S
              </span>
              <span className="font-serif text-lg font-semibold tracking-tight text-ink-900">
                Saúde Pública <span className="text-accent-700">BR</span>
              </span>
            </Link>
            <nav className="flex items-center gap-1 sm:gap-2">
              {NAV.map((item) => (
                <Link
                  key={item.href}
                  href={item.href}
                  className="rounded-lg px-3 py-2 text-sm font-medium text-ink-600 transition hover:bg-ink-100 hover:text-ink-900"
                >
                  {item.label}
                </Link>
              ))}
            </nav>
          </div>
        </header>

        <main className="flex-1">{children}</main>

        <footer className="mt-16 border-t border-ink-200 bg-white">
          <div className="mx-auto grid max-w-7xl gap-8 px-4 py-10 sm:grid-cols-3 sm:px-6">
            <div>
              <p className="font-serif text-base font-semibold text-ink-900">Saúde Pública BR</p>
              <p className="mt-2 text-sm leading-relaxed text-ink-600">
                Plataforma aberta e sem fins lucrativos que transforma microdados
                públicos do SUS em indicadores acessíveis para pesquisa.
              </p>
            </div>
            <div>
              <p className="text-sm font-semibold text-ink-900">Fontes oficiais</p>
              <ul className="mt-2 space-y-1.5 text-sm text-ink-600">
                <li>
                  <a className="hover:text-accent-700" href="https://opendatasus.saude.gov.br/dataset/sim" target="_blank" rel="noreferrer">
                    SIM — Ministério da Saúde / OpenDataSUS
                  </a>
                </li>
                <li>
                  <a className="hover:text-accent-700" href="https://sidra.ibge.gov.br" target="_blank" rel="noreferrer">
                    População — IBGE (Censo 2022 e Estimativas)
                  </a>
                </li>
              </ul>
            </div>
            <div>
              <p className="text-sm font-semibold text-ink-900">Transparência</p>
              <ul className="mt-2 space-y-1.5 text-sm text-ink-600">
                <li><Link className="hover:text-accent-700" href="/metodologia/">Metodologia completa</Link></li>
                <li><Link className="hover:text-accent-700" href="/dados/">API pública e downloads</Link></li>
                <li>Código aberto (MIT) — pipeline 100% reproduzível</li>
              </ul>
            </div>
          </div>
          <div className="border-t border-ink-100 py-4 text-center text-xs text-ink-500">
            Dados originais em domínio público (DATASUS/MS e IBGE). Óbitos não fetais;
            o ano mais recente pode ser preliminar. Cite as fontes originais.
          </div>
        </footer>
      </body>
    </html>
  );
}
