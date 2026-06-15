import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import { ARTIGOS, AUTHOR, getArtigo } from "@/content/artigos";
import { AuthorCard, Byline } from "@/components/byline";

export const dynamicParams = false;

export function generateStaticParams() {
  return ARTIGOS.map((a) => ({ slug: a.slug }));
}

export function generateMetadata({ params }: { params: { slug: string } }): Metadata {
  const a = getArtigo(params.slug);
  if (!a) return {};
  return {
    title: a.titulo,
    description: a.dek,
    alternates: { canonical: `/artigos/${a.slug}/` },
    openGraph: {
      type: "article",
      title: a.titulo,
      description: a.dek,
      url: `https://saudeemdado.com/artigos/${a.slug}/`,
      publishedTime: a.data,
      authors: [AUTHOR.nome],
    },
  };
}

export default function ArtigoPage({ params }: { params: { slug: string } }) {
  const a = getArtigo(params.slug);
  if (!a) notFound();

  const jsonld = {
    "@context": "https://schema.org",
    "@type": "ScholarlyArticle",
    headline: a.titulo,
    description: a.dek,
    datePublished: a.data,
    inLanguage: "pt-BR",
    keywords: a.tags.join(", "),
    author: {
      "@type": "Person",
      name: AUTHOR.nome,
      ...(AUTHOR.linkedin || AUTHOR.lattes ? { sameAs: [AUTHOR.lattes, AUTHOR.linkedin].filter(Boolean) } : {}),
      jobTitle: "Diretor de TI — Prefeitura de Penápolis; Mestrando em Saúde Coletiva (IAMSPE)",
    },
    publisher: { "@type": "Organization", name: "Saúde em Dado", url: "https://saudeemdado.com" },
    isAccessibleForFree: true,
    mainEntityOfPage: `https://saudeemdado.com/artigos/${a.slug}/`,
  };

  const relacionados = ARTIGOS.filter((x) => x.slug !== a.slug)
    .filter((x) => x.tags.some((t) => a.tags.includes(t)))
    .slice(0, 3);

  return (
    <article className="prose-doc mx-auto max-w-3xl px-4 py-12 sm:px-6">
      <script type="application/ld+json" dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonld) }} />

      <Link href="/artigos/" className="text-sm font-medium text-accent-700 hover:underline">← Análises</Link>

      <div className="mt-3 flex flex-wrap gap-1">
        {a.tags.map((t) => (
          <span key={t} className="rounded bg-ink-100 px-2 py-0.5 text-[11px] text-ink-600">{t}</span>
        ))}
      </div>

      <h1 className="mt-3 font-serif text-3xl font-semibold leading-tight tracking-tight text-ink-950 sm:text-4xl">
        {a.titulo}
      </h1>
      <p className="mt-3 text-lg leading-relaxed text-ink-600">{a.dek}</p>

      <Byline data={a.data} leituraMin={a.leituraMin} />

      <div className="mt-6 rounded-lg border-l-4 border-accent-600 bg-ink-50 p-4">
        <p className="text-xs font-semibold uppercase tracking-wide text-ink-500">Resumo</p>
        <p className="mt-1 text-sm leading-relaxed text-ink-700">{a.resumo}</p>
      </div>

      {a.secoes.map((s, i) => (
        <section key={i}>
          {s.titulo && <h2>{s.titulo}</h2>}
          {s.paragrafos.map((p, j) => <p key={j}>{p}</p>)}
          {s.lista && <ul>{s.lista.map((li, k) => <li key={k}>{li}</li>)}</ul>}
        </section>
      ))}

      <h2>Referências e fontes</h2>
      <ol className="mt-2 list-decimal pl-6 text-sm text-ink-600">
        {a.referencias.map((r, i) => <li key={i} className="mt-1">{r}</li>)}
      </ol>

      <div className="mt-6 rounded-lg bg-ink-50 p-4 text-xs leading-relaxed text-ink-500">
        <strong>Como citar:</strong> {AUTHOR.nome}. {a.titulo}. Saúde em Dado, {new Date(`${a.data}T00:00:00`).toLocaleDateString("pt-BR", { month: "long", year: "numeric" })}.
        Disponível em: https://saudeemdado.com/artigos/{a.slug}/. Dados: DataSUS e IBGE (domínio público).
      </div>

      <AuthorCard />

      {relacionados.length > 0 && (
        <div className="mt-10 not-prose">
          <h2 className="font-serif text-xl font-semibold text-ink-900">Leia também</h2>
          <div className="mt-3 space-y-2">
            {relacionados.map((r) => (
              <Link key={r.slug} href={`/artigos/${r.slug}/`} className="block text-accent-700 hover:underline">
                {r.titulo}
              </Link>
            ))}
          </div>
        </div>
      )}
    </article>
  );
}
