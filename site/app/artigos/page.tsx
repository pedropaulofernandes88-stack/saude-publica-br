import type { Metadata } from "next";
import Link from "next/link";
import { ARTIGOS, AUTHOR } from "@/content/artigos";

export const metadata: Metadata = {
  title: "Análises",
  description:
    "Artigos analíticos sobre mortalidade, dengue, internações, natalidade e desigualdade no Brasil, a partir dos microdados do DataSUS. Por Pedro Fernandes.",
  alternates: { canonical: "/artigos/" },
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

      <div className="mt-10 space-y-5">
        {ordenados.map((a) => (
          <Link key={a.slug} href={`/artigos/${a.slug}/`}
                className="card group block transition hover:border-accent-400 hover:shadow-md">
            <div className="flex flex-wrap items-center gap-2 text-xs text-ink-500">
              <time>{new Date(`${a.data}T00:00:00`).toLocaleDateString("pt-BR", { month: "short", year: "numeric" })}</time>
              <span>·</span><span>{a.leituraMin} min</span>
              <span className="ml-auto flex gap-1">
                {a.tags.slice(0, 3).map((t) => (
                  <span key={t} className="rounded bg-ink-100 px-2 py-0.5 text-[11px] text-ink-600">{t}</span>
                ))}
              </span>
            </div>
            <h2 className="mt-2 font-serif text-xl font-semibold text-ink-900 group-hover:text-accent-800">
              {a.titulo}
            </h2>
            <p className="mt-1.5 text-sm leading-relaxed text-ink-600">{a.dek}</p>
            <span className="mt-3 inline-block text-sm font-medium text-accent-700 group-hover:underline">Ler análise →</span>
          </Link>
        ))}
      </div>
    </div>
  );
}
