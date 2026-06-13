import type { Metadata } from "next";
import { Inter, Source_Serif_4 } from "next/font/google";
import Link from "next/link";
import "./globals.css";

const inter = Inter({ subsets: ["latin"], variable: "--font-inter" });
const serif = Source_Serif_4({ subsets: ["latin"], variable: "--font-serif" });

export const metadata: Metadata = {
  metadataBase: new URL("https://saudeemdado.com"),
  title: {
    default: "Saúde em Dado — Mortalidade no Brasil (SIM/DataSUS)",
    template: "%s · Saúde em Dado",
  },
  description:
    "Mortalidade, dengue e internações no Brasil (DataSUS, 2015–2024): painéis navegáveis, mapa municipal, taxas padronizadas, excesso de mortalidade, incidência de dengue e API pública gratuita para pesquisa.",
  keywords: [
    "DataSUS", "SIM", "SINAN", "SIH", "mortalidade", "dengue", "internações",
    "epidemiologia", "dados abertos", "saúde pública", "CID-10", "Brasil",
    "excesso de mortalidade", "taxa padronizada",
  ],
  alternates: { canonical: "/" },
  openGraph: {
    type: "website",
    locale: "pt_BR",
    url: "https://saudeemdado.com",
    siteName: "Saúde em Dado",
    title: "Saúde em Dado — Mortalidade no Brasil (SIM/DataSUS)",
    description:
      "13M+ óbitos (2015–2024) em painéis navegáveis, mapa municipal, taxas padronizadas e API pública gratuita.",
  },
};

// schema.org/Dataset — indexação no Google Dataset Search
const DATASET_JSONLD = {
  "@context": "https://schema.org",
  "@type": "Dataset",
  name: "Saúde em Dado — Mortalidade, dengue e internações no Brasil (DataSUS), 2015–2024",
  description:
    "Indicadores agregados de saúde no Brasil a partir dos microdados do DataSUS: mortalidade (SIM) com taxas padronizadas por idade, IC95% e excesso de mortalidade; dengue (SINAN) com incidência e gravidade; internações SUS (SIH) com permanência, custo e mortalidade hospitalar. Por município, ano e CID-10. População IBGE.",
  url: "https://saudeemdado.com",
  sameAs: "https://github.com/pedropaulofernandes88-stack/saude-publica-br",
  license: "https://creativecommons.org/publicdomain/mark/1.0/",
  isAccessibleForFree: true,
  creator: { "@type": "Person", name: "Pedro Paulo Fernandes" },
  temporalCoverage: "2015-01-01/2024-12-31",
  spatialCoverage: { "@type": "Place", name: "Brasil" },
  keywords: ["mortalidade", "SIM", "DataSUS", "CID-10", "epidemiologia", "dados abertos", "Brasil"],
  distribution: [
    {
      "@type": "DataDownload",
      encodingFormat: "application/json",
      contentUrl: "https://zekjhmxjamatlxpkykde.supabase.co/rest/v1/",
      description: "API REST pública (PostgREST), somente leitura",
    },
    {
      "@type": "DataDownload",
      encodingFormat: "application/x-parquet",
      contentUrl:
        "https://zekjhmxjamatlxpkykde.supabase.co/storage/v1/object/public/dados/mart_mortalidade_municipio.parquet",
      description: "Download em lote (Parquet, com SHA-256 publicado)",
    },
  ],
  citation:
    "BRASIL. Ministério da Saúde. SIM — Sistema de Informações sobre Mortalidade (microdados, OpenDataSUS). IBGE. Censo 2022 e Estimativas de População (SIDRA).",
};

const NAV = [
  { href: "/", label: "Início", curto: "Início" },
  { href: "/painel/", label: "Mortalidade", curto: "Mortal." },
  { href: "/dengue/", label: "Dengue", curto: "Dengue" },
  { href: "/internacoes/", label: "Internações", curto: "Intern." },
  { href: "/mapa/", label: "Mapa", curto: "Mapa" },
  { href: "/tendencias/", label: "Tendências", curto: "Tend." },
  { href: "/dados/", label: "Dados & API", curto: "Dados" },
  { href: "/metodologia/", label: "Metodologia", curto: "Método" },
  { href: "/sobre/", label: "Sobre", curto: "Sobre" },
];

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="pt-BR" className={`${inter.variable} ${serif.variable}`}>
      <body className="flex min-h-screen flex-col font-sans">
        <script
          type="application/ld+json"
          dangerouslySetInnerHTML={{ __html: JSON.stringify(DATASET_JSONLD) }}
        />
        <header className="sticky top-0 z-40 border-b border-ink-200 bg-white/90 backdrop-blur">
          <div className="mx-auto flex h-14 max-w-7xl items-center justify-between gap-2 px-3 sm:h-16 sm:px-6">
            <Link href="/" className="flex shrink-0 items-center gap-2 sm:gap-2.5">
              <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-accent-700 font-serif text-base font-bold text-white sm:h-9 sm:w-9 sm:text-lg">
                S
              </span>
              <span className="whitespace-nowrap font-serif text-base font-semibold tracking-tight text-ink-900 sm:text-lg">
                Saúde Pública <span className="text-accent-700">BR</span>
              </span>
            </Link>
            <nav className="flex items-center gap-0 overflow-x-auto sm:gap-2">
              {NAV.map((item) => (
                <Link
                  key={item.href}
                  href={item.href}
                  className={`whitespace-nowrap rounded-lg px-2 py-2 text-[13px] font-medium text-ink-600 transition hover:bg-ink-100 hover:text-ink-900 sm:px-3 sm:text-sm ${item.href === "/" ? "hidden sm:inline-flex" : ""}`}
                >
                  <span className="sm:hidden">{item.curto}</span>
                  <span className="hidden sm:inline">{item.label}</span>
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
