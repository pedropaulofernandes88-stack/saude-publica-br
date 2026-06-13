"use client";

import { useEffect, useMemo, useState } from "react";
import {
  Area, AreaChart, CartesianGrid, Legend, Line, LineChart, ResponsiveContainer,
  Tooltip, XAxis, YAxis,
} from "recharts";
import { Kpi, Skeleton } from "@/components/kpi";
import { UFS, fmtDec, fmtInt, rest, sdata, type DengueAno, type DengueSemana } from "@/lib/api";

const ANOS_DENGUE = [2024, 2023, 2022, 2021, 2020, 2019, 2018, 2017, 2016, 2015];
const CORES_ANO: Record<number, string> = {
  2024: "#b4232a", 2023: "#e07a1f", 2022: "#1fb87b", 2021: "#677791", 2019: "#8694ab",
};

export default function Dengue() {
  const [uf, setUf] = useState("Brasil");
  const [ano, setAno] = useState(2024);
  const [semana, setSemana] = useState<DengueSemana[] | null>(null);
  const [anual, setAnual] = useState<DengueAno[] | null>(null);
  const [erro, setErro] = useState<string | null>(null);

  const [semanaBruta, setSemanaBruta] = useState<DengueSemana[] | null>(null);
  // curvas: dados estáticos agregados por UF × ano × semana (egress zero)
  useEffect(() => {
    sdata<DengueSemana[]>("dengue_uf_semana")
      .then(setSemanaBruta)
      .catch((e) => setErro(String(e)));
  }, []);
  useEffect(() => {
    if (!semanaBruta) { setSemana(null); return; }
    setSemana(uf === "Brasil" ? semanaBruta : semanaBruta.filter((r) => r.uf_sigla === uf));
  }, [semanaBruta, uf]);

  // ranking municipal: REST filtrado por ano (≤ ~5,5k linhas)
  useEffect(() => {
    setAnual(null);
    const ufF: Record<string, string> = uf === "Brasil" ? {} : { uf_sigla: `eq.${uf}` };
    rest<DengueAno>("mart_dengue_municipio_ano", {
      select: "municipio_cod,municipio_nome,uf_sigla,regiao,ano_epi,casos_provaveis,casos_graves,obitos,populacao,incidencia_100k,letalidade_pct",
      ano_epi: `eq.${ano}`,
      order: "municipio_cod",
      ...ufF,
    })
      .then(setAnual)
      .catch((e) => setErro(String(e)));
  }, [uf, ano]);

  // curva sazonal: casos por semana, uma linha por ano (sobreposição)
  const sazonal = useMemo(() => {
    if (!semana) return null;
    const porSemana: Record<number, Record<string, number>> = {};
    for (const r of semana) {
      const w = r.semana_epi;
      if (w < 1 || w > 53) continue;
      porSemana[w] ??= { semana: w };
      porSemana[w][`a${r.ano_epi}`] = (porSemana[w][`a${r.ano_epi}`] ?? 0) + r.casos_provaveis;
    }
    return Object.values(porSemana).sort((a, b) => a.semana - b.semana);
  }, [semana]);

  const totaisAno = useMemo(() => {
    if (!semana) return null;
    const m = new Map<number, { casos: number; graves: number; obitos: number }>();
    for (const r of semana) {
      const cur = m.get(r.ano_epi) ?? { casos: 0, graves: 0, obitos: 0 };
      cur.casos += r.casos_provaveis; cur.graves += r.casos_graves; cur.obitos += r.obitos;
      m.set(r.ano_epi, cur);
    }
    return [...m.entries()].sort(([a], [b]) => a - b).map(([ano, v]) => ({ ano, ...v }));
  }, [semana]);

  const doAno = totaisAno?.find((t) => t.ano === ano);

  const rankingInc = useMemo(() => {
    if (!anual) return null;
    return [...anual]
      .filter((m) => (m.populacao ?? 0) >= 50_000)
      .sort((a, b) => (b.incidencia_100k ?? -1) - (a.incidencia_100k ?? -1))
      .slice(0, 50);
  }, [anual]);

  return (
    <div className="mx-auto max-w-7xl px-4 py-10 sm:px-6">
      <h1 className="font-serif text-3xl font-semibold tracking-tight text-ink-950">Dengue no Brasil</h1>
      <p className="mt-2 max-w-3xl text-ink-600">
        Casos prováveis, gravidade, óbitos e incidência da dengue (SINAN/DataSUS,
        2015–2024) por município e semana epidemiológica. Inclui a epidemia
        recorde de 2024.
      </p>

      <div className="card mt-6 grid gap-4 sm:grid-cols-2">
        <div>
          <label className="label" htmlFor="d-uf">Abrangência</label>
          <select id="d-uf" className="select" value={uf} onChange={(e) => setUf(e.target.value)}>
            <option value="Brasil">Brasil (todas as UFs)</option>
            {UFS.map((u) => <option key={u} value={u}>{u}</option>)}
          </select>
        </div>
        <div>
          <label className="label" htmlFor="d-ano">Ano (ranking municipal)</label>
          <select id="d-ano" className="select" value={ano} onChange={(e) => setAno(Number(e.target.value))}>
            {ANOS_DENGUE.map((a) => <option key={a} value={a}>{a}{a === 2024 ? " (epidemia recorde)" : ""}</option>)}
          </select>
        </div>
      </div>

      {erro && <div className="card mt-6 border-red-200 bg-red-50 text-sm text-red-800">Falha: {erro}</div>}

      {doAno && (
        <div className="mt-6 grid gap-4 sm:grid-cols-4">
          <Kpi rotulo={`Casos prováveis ${ano}`} valor={fmtInt(doAno.casos)} detalhe={uf === "Brasil" ? "Brasil" : uf} />
          <Kpi rotulo="Casos graves" valor={fmtInt(doAno.graves)} detalhe="alarme + grave" />
          <Kpi rotulo="Óbitos por dengue" valor={fmtInt(doAno.obitos)}
               detalhe={`letalidade ${fmtDec((doAno.obitos / doAno.casos) * 100, 2)}%`} />
          <Kpi rotulo="Municípios afetados" valor={anual ? fmtInt(anual.length) : "…"} detalhe={`com casos em ${ano}`} />
        </div>
      )}

      <div className="card mt-6">
        <h2 className="font-serif text-xl font-semibold text-ink-900">
          Curva sazonal — casos por semana epidemiológica
        </h2>
        <p className="mt-1 text-sm text-ink-500">
          Sobreposição de anos: o pico do verão (semanas 1–20) e a magnitude de 2024 vs. anos anteriores.
        </p>
        <div className="mt-4">
          {sazonal ? (
            <ResponsiveContainer width="100%" height={340}>
              <LineChart data={sazonal} margin={{ top: 8, right: 16, bottom: 0, left: 8 }}>
                <CartesianGrid stroke="#eceef2" vertical={false} />
                <XAxis dataKey="semana" tick={{ fontSize: 12, fill: "#677791" }}
                       label={{ value: "semana epidemiológica", position: "insideBottom", offset: -2, fontSize: 11, fill: "#8694ab" }} />
                <YAxis tick={{ fontSize: 12, fill: "#677791" }} width={52}
                       tickFormatter={(v) => (v as number).toLocaleString("pt-BR", { notation: "compact" })} />
                <Tooltip formatter={(v, n) => [fmtInt(v as number), String(n).replace("a", "")]}
                         contentStyle={{ borderRadius: 8, borderColor: "#eceef2", fontSize: 13 }} />
                {[2024, 2023, 2022, 2019].map((a) => (
                  <Line key={a} type="monotone" dataKey={`a${a}`} name={`a${a}`}
                        stroke={CORES_ANO[a] ?? "#b1bac9"} strokeWidth={a === 2024 ? 2.8 : 1.8} dot={false} />
                ))}
                <Legend formatter={(v) => String(v).replace("a", "")} />
              </LineChart>
            </ResponsiveContainer>
          ) : <Skeleton altura={340} />}
        </div>
      </div>

      <div className="card mt-6">
        <h2 className="font-serif text-xl font-semibold text-ink-900">Casos prováveis por ano — {uf === "Brasil" ? "Brasil" : uf}</h2>
        <div className="mt-4">
          {totaisAno ? (
            <ResponsiveContainer width="100%" height={280}>
              <AreaChart data={totaisAno} margin={{ top: 8, right: 16, bottom: 0, left: 8 }}>
                <defs>
                  <linearGradient id="gd" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor="#b4232a" stopOpacity={0.5} />
                    <stop offset="100%" stopColor="#b4232a" stopOpacity={0.05} />
                  </linearGradient>
                </defs>
                <CartesianGrid stroke="#eceef2" vertical={false} />
                <XAxis dataKey="ano" tick={{ fontSize: 12, fill: "#677791" }} />
                <YAxis tick={{ fontSize: 12, fill: "#677791" }} width={52}
                       tickFormatter={(v) => (v as number).toLocaleString("pt-BR", { notation: "compact" })} />
                <Tooltip formatter={(v) => [fmtInt(v as number), "Casos prováveis"]}
                         contentStyle={{ borderRadius: 8, borderColor: "#eceef2", fontSize: 13 }} />
                <Area type="monotone" dataKey="casos" stroke="#b4232a" strokeWidth={2.5} fill="url(#gd)" />
              </AreaChart>
            </ResponsiveContainer>
          ) : <Skeleton altura={280} />}
        </div>
      </div>

      <div className="card mt-6 overflow-x-auto">
        <h2 className="font-serif text-xl font-semibold text-ink-900">
          Municípios por incidência ({ano}, pop. ≥ 50 mil)
        </h2>
        <p className="mt-1 text-sm text-ink-500">Incidência = casos prováveis por 100 mil habitantes.</p>
        <div className="mt-4">
          {rankingInc ? (
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b-2 border-ink-200 text-left text-xs uppercase tracking-wide text-ink-500">
                  <th className="px-3 py-2">#</th><th className="px-3 py-2">Município</th><th className="px-3 py-2">UF</th>
                  <th className="px-3 py-2 text-right">Casos</th><th className="px-3 py-2 text-right">Incidência /100k</th>
                  <th className="px-3 py-2 text-right">Óbitos</th><th className="px-3 py-2 text-right">Letalidade</th>
                </tr>
              </thead>
              <tbody>
                {rankingInc.map((m, i) => (
                  <tr key={m.municipio_cod} className="border-b border-ink-100 hover:bg-ink-50">
                    <td className="px-3 py-2 tabular-nums text-ink-400">{i + 1}</td>
                    <td className="px-3 py-2 font-medium text-ink-900">{m.municipio_nome ?? m.municipio_cod}</td>
                    <td className="px-3 py-2 text-ink-600">{m.uf_sigla}</td>
                    <td className="px-3 py-2 text-right tabular-nums">{fmtInt(m.casos_provaveis)}</td>
                    <td className="px-3 py-2 text-right font-semibold tabular-nums text-red-700">{fmtDec(m.incidencia_100k)}</td>
                    <td className="px-3 py-2 text-right tabular-nums text-ink-600">{fmtInt(m.obitos)}</td>
                    <td className="px-3 py-2 text-right tabular-nums text-ink-600">{fmtDec(m.letalidade_pct, 2)}%</td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : <Skeleton altura={300} />}
        </div>
      </div>

      <p className="mt-4 text-xs text-ink-500">
        Fonte: SINAN/DataSUS. Caso provável = notificação não descartada; semana pela data dos primeiros
        sintomas e município de residência. Anos recentes podem ter classificação em andamento. Ver{" "}
        <a className="text-accent-700 underline" href="/metodologia/">metodologia</a>.
      </p>
    </div>
  );
}
