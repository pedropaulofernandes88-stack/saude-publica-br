"use client";

import { useEffect, useMemo, useState } from "react";
import { LinhasExcesso, SerieLinha } from "@/components/charts";
import { Kpi, Skeleton } from "@/components/kpi";
import { UFS, fmtDec, fmtInt, sdata, type LinhaExcesso, type SerieTotalItem } from "@/lib/api";

export default function Tendencias() {
  const [uf, setUf] = useState("BR");
  const [excesso, setExcesso] = useState<LinhaExcesso[] | null>(null);
  const [serie, setSerie] = useState<SerieTotalItem[] | null>(null);
  const [erro, setErro] = useState<string | null>(null);

  useEffect(() => {
    Promise.all([sdata<LinhaExcesso[]>("excesso"), sdata<SerieTotalItem[]>("serie_total")])
      .then(([e, s]) => { setExcesso(e); setSerie(s); })
      .catch((e) => setErro(String(e)));
  }, []);

  const serieUf = useMemo(
    () => serie?.filter((r) => r.uf_sigla === uf)
      .sort((a, b) => a.mes_competencia.localeCompare(b.mes_competencia))
      .map((r) => ({ mes: r.mes_competencia, obitos: r.obitos })) ?? null,
    [serie, uf],
  );

  const excUf = useMemo(
    () => excesso?.filter((r) => r.uf_sigla === uf)
      .sort((a, b) => a.mes_competencia.localeCompare(b.mes_competencia))
      .map((r) => ({ mes: r.mes_competencia, obitos: r.obitos, esperado: r.esperado, excesso: r.excesso })) ?? null,
    [excesso, uf],
  );

  const resumo = useMemo(() => {
    if (!excUf) return null;
    const porAno = new Map<number, { exc: number; obs: number; esp: number }>();
    for (const r of excUf) {
      const a = Number(r.mes.slice(0, 4));
      const cur = porAno.get(a) ?? { exc: 0, obs: 0, esp: 0 };
      cur.exc += r.excesso; cur.obs += r.obitos; cur.esp += r.esperado;
      porAno.set(a, cur);
    }
    return [...porAno.entries()].sort(([a], [b]) => a - b)
      .map(([ano, v]) => ({ ano, ...v, pct: (v.obs / v.esp - 1) * 100 }));
  }, [excUf]);

  const totalPandemia = resumo
    ?.filter((r) => r.ano === 2020 || r.ano === 2021)
    .reduce((s, r) => s + r.exc, 0);

  return (
    <div className="mx-auto max-w-7xl px-4 py-10 sm:px-6">
      <h1 className="font-serif text-3xl font-semibold tracking-tight text-ink-950">
        Tendências e excesso de mortalidade
      </h1>
      <p className="mt-2 max-w-3xl text-ink-600">
        Dez anos de série mensal (2015–2024) e excesso de mortalidade: óbitos
        observados versus esperados pela média 2015–2019 do mesmo mês, ajustada
        pela população do ano.
      </p>

      <div className="card mt-6 max-w-xs">
        <label className="label" htmlFor="t-uf">Abrangência</label>
        <select id="t-uf" className="select" value={uf} onChange={(e) => setUf(e.target.value)}>
          <option value="BR">Brasil</option>
          {UFS.map((u) => <option key={u} value={u}>{u}</option>)}
        </select>
      </div>

      {erro && <div className="card mt-6 border-red-200 bg-red-50 text-sm text-red-800">Falha: {erro}</div>}

      {totalPandemia != null && (
        <div className="mt-6 grid gap-4 sm:grid-cols-3">
          <Kpi rotulo="Excesso 2020–2021 (pandemia)" valor={fmtInt(Math.round(totalPandemia))}
               detalhe="óbitos acima do esperado" />
          {resumo?.filter((r) => r.ano >= 2023).map((r) => (
            <Kpi key={r.ano} rotulo={`Excesso em ${r.ano}`} valor={fmtInt(Math.round(r.exc))}
                 detalhe={`${fmtDec(r.pct, 1)}% vs esperado`} />
          ))}
        </div>
      )}

      <div className="card mt-6">
        <h2 className="font-serif text-xl font-semibold text-ink-900">
          Observado × esperado — {uf === "BR" ? "Brasil" : uf} (2020–2024)
        </h2>
        <p className="mt-1 text-sm text-ink-500">
          Linha tracejada: esperado (baseline 2015–2019 com ajuste populacional). Vermelha: observado.
        </p>
        <div className="mt-4">{excUf ? <LinhasExcesso data={excUf} /> : <Skeleton altura={340} />}</div>
      </div>

      <div className="card mt-6">
        <h2 className="font-serif text-xl font-semibold text-ink-900">
          Série completa 2015–2024 — {uf === "BR" ? "Brasil" : uf}
        </h2>
        <div className="mt-4">{serieUf ? <SerieLinha data={serieUf} /> : <Skeleton />}</div>
      </div>

      {resumo && (
        <div className="card mt-6 overflow-x-auto">
          <h2 className="font-serif text-xl font-semibold text-ink-900">Resumo anual do excesso</h2>
          <table className="mt-3 w-full text-sm">
            <thead>
              <tr className="border-b-2 border-ink-200 text-left text-xs uppercase tracking-wide text-ink-500">
                <th className="px-3 py-2">Ano</th>
                <th className="px-3 py-2 text-right">Observado</th>
                <th className="px-3 py-2 text-right">Esperado</th>
                <th className="px-3 py-2 text-right">Excesso</th>
                <th className="px-3 py-2 text-right">% vs esperado</th>
              </tr>
            </thead>
            <tbody>
              {resumo.map((r) => (
                <tr key={r.ano} className="border-b border-ink-100">
                  <td className="px-3 py-2 font-medium">{r.ano}{r.ano === 2024 ? " *" : ""}</td>
                  <td className="px-3 py-2 text-right tabular-nums">{fmtInt(Math.round(r.obs))}</td>
                  <td className="px-3 py-2 text-right tabular-nums text-ink-600">{fmtInt(Math.round(r.esp))}</td>
                  <td className={`px-3 py-2 text-right font-semibold tabular-nums ${r.exc > 0 ? "text-red-700" : "text-accent-800"}`}>
                    {r.exc > 0 ? "+" : ""}{fmtInt(Math.round(r.exc))}
                  </td>
                  <td className="px-3 py-2 text-right tabular-nums">{fmtDec(r.pct, 1)}%</td>
                </tr>
              ))}
            </tbody>
          </table>
          <p className="mt-2 text-xs text-ink-500">* dados preliminares, sujeitos a revisão pelo MS.</p>
        </div>
      )}
    </div>
  );
}
