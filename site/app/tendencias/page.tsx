"use client";

import { useEffect, useMemo, useState } from "react";
import { DispersaoVulnMort, LinhasExcesso, SerieLinha } from "@/components/charts";
import { Kpi, Skeleton } from "@/components/kpi";
import { UFS, fmtDec, fmtInt, sdata, type CruzVulnMort, type LinhaExcesso, type SerieTotalItem } from "@/lib/api";

const REGIOES = ["Norte", "Nordeste", "Centro-Oeste", "Sudeste", "Sul"];
const COR_REG: Record<string, string> = {
  Norte: "#1f9e8a", Nordeste: "#e07a1f", "Centro-Oeste": "#a05fb4", Sudeste: "#2f6fb0", Sul: "#107752",
};

export default function Tendencias() {
  const [uf, setUf] = useState("BR");
  const [excesso, setExcesso] = useState<LinhaExcesso[] | null>(null);
  const [serie, setSerie] = useState<SerieTotalItem[] | null>(null);
  const [cruz, setCruz] = useState<CruzVulnMort[] | null>(null);
  const [ufScatter, setUfScatter] = useState("Brasil");
  const [erro, setErro] = useState<string | null>(null);

  useEffect(() => {
    Promise.all([sdata<LinhaExcesso[]>("excesso"), sdata<SerieTotalItem[]>("serie_total")])
      .then(([e, s]) => { setExcesso(e); setSerie(s); })
      .catch((e) => setErro(String(e)));
    sdata<CruzVulnMort[]>("vulnerab_mortalidade").then(setCruz).catch(() => {});
  }, []);

  const cruzFiltrado = useMemo(
    () => cruz?.filter((d) => ufScatter === "Brasil" || d.uf === ufScatter) ?? null,
    [cruz, ufScatter],
  );

  // correlação de Pearson entre vulnerabilidade e taxa padronizada
  const pearson = useMemo(() => {
    if (!cruzFiltrado || cruzFiltrado.length < 10) return null;
    const xs = cruzFiltrado.map((d) => d.ivs), ys = cruzFiltrado.map((d) => d.taxa_pad);
    const n = xs.length, mx = xs.reduce((a, b) => a + b, 0) / n, my = ys.reduce((a, b) => a + b, 0) / n;
    let sxy = 0, sx = 0, sy = 0;
    for (let i = 0; i < n; i++) { const dx = xs[i] - mx, dy = ys[i] - my; sxy += dx * dy; sx += dx * dx; sy += dy * dy; }
    return sxy / Math.sqrt(sx * sy);
  }, [cruzFiltrado]);

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

      {/* Vulnerabilidade × mortalidade */}
      <div className="card mt-10">
        <div className="flex flex-wrap items-end justify-between gap-4">
          <div>
            <h2 className="font-serif text-xl font-semibold text-ink-900">
              Vulnerabilidade social × mortalidade (2023)
            </h2>
            <p className="mt-1 max-w-2xl text-sm text-ink-500">
              Cada ponto é um município (≥ 10 mil hab.): vulnerabilidade social
              (proxy Censo 2022) no eixo X, taxa de mortalidade padronizada por
              idade no eixo Y. Tamanho ∝ população; cor por região.
            </p>
          </div>
          <div>
            <label className="label" htmlFor="s-uf">Recorte</label>
            <select id="s-uf" className="select" value={ufScatter} onChange={(e) => setUfScatter(e.target.value)}>
              <option value="Brasil">Brasil</option>
              {UFS.map((u) => <option key={u} value={u}>{u}</option>)}
            </select>
          </div>
        </div>

        {pearson != null && (
          <div className="mt-4 grid gap-4 sm:grid-cols-3">
            <Kpi rotulo="Correlação (Pearson)" valor={fmtDec(pearson, 2)}
                 detalhe={Math.abs(pearson) < 0.2 ? "fraca" : Math.abs(pearson) < 0.5 ? "moderada" : "forte"} />
            <Kpi rotulo="Municípios no gráfico" valor={cruzFiltrado ? fmtInt(cruzFiltrado.length) : "…"} detalhe="≥ 10 mil hab." />
            <div className="card flex flex-col justify-center">
              <p className="text-xs leading-relaxed text-ink-600">
                {pearson > 0.2
                  ? "Municípios mais vulneráveis tendem a ter maior mortalidade padronizada — coerente com a literatura de determinantes sociais."
                  : pearson < -0.05
                    ? "Associação fraca/negativa: a taxa é padronizada por idade e há sub-registro de óbitos em áreas mais vulneráveis, o que atenua a relação esperada. Um sinal a investigar, não uma conclusão."
                    : "No recorte atual a associação é fraca; a relação varia por região, causa e qualidade do registro."}
              </p>
            </div>
          </div>
        )}

        <div className="mt-4">
          {cruzFiltrado ? <DispersaoVulnMort data={cruzFiltrado} /> : <Skeleton altura={420} />}
        </div>

        <div className="mt-3 flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-ink-600">
          {REGIOES.map((r) => (
            <span key={r} className="flex items-center gap-1">
              <span className="inline-block h-3 w-3 rounded-full" style={{ background: COR_REG[r] }} /> {r}
            </span>
          ))}
        </div>
        <p className="mt-3 text-xs text-ink-500">
          Vulnerabilidade = proxy do Censo 2022 (analfabetismo + falta de água, z-score), não o IVS
          oficial do IPEA. Taxa padronizada por idade (padrão Brasil 2022). Correlação não implica
          causalidade. Ver <a className="text-accent-700 underline" href="/metodologia/">metodologia</a>.
        </p>
      </div>
    </div>
  );
}
