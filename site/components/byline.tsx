import { AUTHOR } from "@/content/artigos";

export function Byline({ data, leituraMin }: { data?: string; leituraMin?: number }) {
  const dataFmt = data
    ? new Date(`${data}T00:00:00`).toLocaleDateString("pt-BR", { day: "2-digit", month: "long", year: "numeric" })
    : null;
  return (
    <div className="mt-6 flex flex-wrap items-center gap-x-3 gap-y-1 border-y border-ink-200 py-4 text-sm">
      <span className="flex h-9 w-9 items-center justify-center rounded-full bg-accent-700 font-serif font-bold text-white">
        PF
      </span>
      <div>
        <p className="font-semibold text-ink-900">{AUTHOR.nome}</p>
        <p className="text-xs text-ink-500">
          {dataFmt}{dataFmt && leituraMin ? " · " : ""}{leituraMin ? `${leituraMin} min de leitura` : ""}
        </p>
      </div>
      <div className="ml-auto flex flex-wrap gap-2">
        {AUTHOR.orcid && (
          <a href={AUTHOR.orcid} target="_blank" rel="noreferrer"
             className="rounded-lg border border-ink-300 px-3 py-1.5 text-xs font-medium text-ink-700 hover:bg-ink-100">
            ORCID
          </a>
        )}
        {AUTHOR.lattes && (
          <a href={AUTHOR.lattes} target="_blank" rel="noreferrer"
             className="rounded-lg border border-ink-300 px-3 py-1.5 text-xs font-medium text-ink-700 hover:bg-ink-100">
            Lattes
          </a>
        )}
        {AUTHOR.linkedin && (
          <a href={AUTHOR.linkedin} target="_blank" rel="noreferrer"
             className="rounded-lg border border-ink-300 px-3 py-1.5 text-xs font-medium text-ink-700 hover:bg-ink-100">
            LinkedIn
          </a>
        )}
      </div>
    </div>
  );
}

export function AuthorCard() {
  return (
    <div className="card mt-10 bg-ink-50">
      <p className="text-xs font-semibold uppercase tracking-wide text-ink-500">Sobre o autor</p>
      <p className="mt-2 font-serif text-lg font-semibold text-ink-900">{AUTHOR.nome}</p>
      <ul className="mt-2 space-y-1 text-sm text-ink-700">
        {AUTHOR.credenciais.map((c) => <li key={c}>· {c}</li>)}
      </ul>
      <p className="mt-3 text-sm leading-relaxed text-ink-600">{AUTHOR.resumoBio}</p>
      {(AUTHOR.lattes || AUTHOR.linkedin || AUTHOR.orcid) && (
        <div className="mt-3 flex flex-wrap gap-2">
          {AUTHOR.orcid && (
            <a href={AUTHOR.orcid} target="_blank" rel="noreferrer" className="btn-ghost text-xs">ORCID</a>
          )}
          {AUTHOR.lattes && (
            <a href={AUTHOR.lattes} target="_blank" rel="noreferrer" className="btn-ghost text-xs">Currículo Lattes</a>
          )}
          {AUTHOR.linkedin && (
            <a href={AUTHOR.linkedin} target="_blank" rel="noreferrer" className="btn-ghost text-xs">LinkedIn</a>
          )}
        </div>
      )}
    </div>
  );
}
