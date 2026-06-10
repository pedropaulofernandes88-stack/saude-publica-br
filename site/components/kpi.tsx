export function Kpi({
  rotulo,
  valor,
  detalhe,
}: {
  rotulo: string;
  valor: string;
  detalhe?: string;
}) {
  return (
    <div className="card">
      <p className="text-xs font-semibold uppercase tracking-wide text-ink-500">{rotulo}</p>
      <p className="mt-1.5 font-serif text-3xl font-semibold tabular-nums text-ink-900">{valor}</p>
      {detalhe && <p className="mt-1 text-xs text-ink-500">{detalhe}</p>}
    </div>
  );
}

export function Skeleton({ altura = 320 }: { altura?: number }) {
  return (
    <div
      className="w-full animate-pulse rounded-lg bg-ink-100"
      style={{ height: altura }}
      aria-label="Carregando…"
    />
  );
}
