import type { Metadata } from "next";
import Link from "next/link";
import { ARTIGOS, AUTHOR } from "@/content/artigos";

export const metadata: Metadata = {
  title: "Análises",
  description:
    "Artigos analíticos sobre mortalidade, dengue, internações, natalidade e desigualdade no Brasil, a partir dos microdados do DataSUS. Por Pedro Fernandes.",
  alternates: { canonical: "/artigos/" },
};

const CAPA: Record<string, { bg: string; icone: string }> = {
  dengue: { bg: "linear-gradient(135deg,#b4232a,#e07a1f)", icone: "🦟" },
  mortalidade: { bg: "linear-gradient(135deg,#3a4253,#677791)", icone: "💀" },
  "mortalidade infantil": { bg: "linear-gradient(135deg,#107752,#46b785)", icone: "👶" },
  SIH: { bg: "linear-gradient(135deg,#2f6fb0,#1f9e8a)", icone: "🏥" },
  metodologia: { bg: "linear-gradient(135deg,#5b4b8a,#a05fb4)", icone: "📐" },
  desigualdade: { bg: "linear-gradient(135deg,#8a5a1f,#e07a1f)", icone: "⚖️" },
  "ciência de dados": { bg: "linear-gradient(135deg,#0c5c41,#107752)", icone: "🧬" },
  _default: { bg: "linear-gradient(135deg,#15875e,#0c5c41)", icone: "📊" },
};

export default function Artigos() {
  const ordenados = [...ARTIGOS].sort((a, b) => b.data.localeCompare(a.data));
  return (
    <div className="mx-auto max-w-4xl px-4 py-12 sm:px-6">
      <h1 className="font-serif text-3xl font-semibold tracking-tight text-ink-950">Análises</h1>
      <p className="mt-3 max-w-2xl text-lg leading-relaxed text-ink-600">
        Artigos que cruzam os dados desta plataforma com análise estatística e
        leitura epidemiológica — escala da dengue, excesso de mortalidade,
        desigualdade, custos hospitalares e método.
      </p>
      <p className="mt-2 text-sm text-ink-500">
        Por <span className="font-medium text-ink-700">{AUTHOR.nome}</span> — {AUTHOR.credenciais[0]};
        {" "}{AUTHOR.credenciais[1]}.
      </p>

      <div className="mt-10 grid gap-6 sm:grid-cols-2">
        {ordenados.map((a) => {
          const cor = CAPA[a.tags[0]] ?? CAPA._default;
          return (
            <Link key={a.slug} href={`/artigos/${a.slug}/`}
                  className="group flex flex-col overflow-hidden rounded-xl border border-ink-200 bg-white shadow-sm transition hover:-translate-y-0.5 hover:border-accent-400 hover:shadow-md">
              <div className="relative h-28 overflow-hidden" style={{ background: cor.bg }}>
                <span className="absolute right-3 top-3 text-3xl opacity-90">{cor.icone}</span>
                <span className="absolute bottom-3 left-4 text-[11px] font-semibold uppercase tracking-widest text-white/90">
                  {a.tags[0]}
                </span>
              </div>
              <div className="flex flex-1 flex-col p-5">
                <div className="flex items-center gap-2 text-xs text-ink-500">
                  <time>{new Date(`${a.data}T00:00:00`).toLocaleDateString("pt-BR", { month: "short", year: "numeric" })}</time>
                  <span>·</span><span>{a.leituraMin} min</span>
                </div>
                <h2 className="mt-2 font-serif text-lg font-semibold leading-snug text-ink-900 group-hover:text-accent-800">
                  {a.titulo}
                </h2>
                <p className="mt-1.5 flex-1 text-sm leading-relaxed text-ink-600">{a.dek}</p>
                <span className="mt-3 text-sm font-medium text-accent-700 group-hover:underline">Ler análise →</span>
              </div>
            </Link>
          );
        })}
      </div>
    </div>
  );
}
