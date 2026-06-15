"use client";

import { useEffect, useMemo, useState } from "react";
import { Barras } from "@/components/charts";
import { Kpi, Skeleton } from "@/components/kpi";
import {
  UFS, fmtDec, fmtInt, rest,
  type MortalidadeInfantil, type Natalidade,
} from "@/lib/api";

const ANOS = [2022, 2021];

export default function Nascimentos() {
  const [uf, setUf] = useState("Brasil");
  const [ano, setAno] = useState(2022);
  const [nat, setNat] = useState<Natalidade[] | null>(null);
  const [tmi, setTmi] = useState<MortalidadeInfantil[] | null>(null);
  const [erro, setErro] = useState<string | null>(null);

  useEffect(() => {
    rest<MortalidadeInfantil>("mart_mortalidade_infantil_uf", {
      select: "uf_sigla,ano,nascidos,obitos_menor1,tmi_por_mil",
      order: "ano,uf_sigla",
    }).then(setTmi).catch((e) => setErro(String(e)));
  }, []);

  useEffect(() => {
    setNat(null);
    const ufF: Record<string, string> = uf === "Brasil" ? {} : { uf_sigla: `eq.${uf}` };
    rest<Natalidade>("mart_natalidade_municipio", {
      select: "municipio_cod,municipio_nome,uf_sigla,ano,nascidos,pct_baixo_peso,pct_prematuro,pct_prenatal_7mais,idade_media_mae",
      ano: `eq.${ano}`, order: "municipio_cod", ...ufF,
    }).then(setNat).catch((e) => setErro(String(e)));
  }, [uf, ano]);

  const totalNasc = useMemo(() => nat?.reduce((s, r) => s + r.nascidos, 0), [nat]);

  const tmiUf = useMemo(() => {
    if (!tmi) return null;
    return tmi.filter((r) => r.ano === Math.min(ano, 2022))  // TMI disponível até 2022
      .sort((a, b) => (b.tmi_por_mil ?? -1) - (a.tmi_por_mil ?? -1))
      .map((r) => ({ nome: r.uf_sigla, obitos: r.tmi_por_mil ?? 0 }));
  }, [tmi, ano]);

  const tmiBrasil = useMemo(() => {
    if (!tmi) return null;
    const y = tmi.filter((r) => r.ano === Math.min(ano, 2022));
    const nv = y.reduce((s, r) => s + r.nascidos, 0);
    const ob = y.reduce((s, r) => s + (r.obitos_menor1 ?? 0), 0);
    return nv ? (ob / nv * 1000) : null;
  }, [tmi, ano]);

  const ranking = useMemo(() => {
    if (!nat) return null;
    return [...nat].filter((m) => m.nascidos >= 200)
      .sort((a, b) => (b.pct_baixo_peso ?? -1) - (a.pct_baixo_peso ?? -1)).slice(0, 50);
  }, [nat]);

  return (
    <div className="mx-auto max-w-7xl px-4 py-10 sm:px-6">
      <h1 className="font-serif text-3xl font-semibold tracking-tight text-ink-950">
        Nascimentos e mortalidade infantil
      </h1>
      <p className="mt-2 max-w-3xl text-ink-600">
        Nascidos vivos (SINASC/DataSUS, 2021–2023) por município: peso ao nascer,
        prematuridade e pré-natal; e a Taxa de Mortalidade Infantil por UF
        (óbitos &lt;1 ano do SIM ÷ nascidos vivos).
      </p>

      <div className="card mt-6 grid gap-4 sm:grid-cols-2">
        <div>
          <label className="label" htmlFor="n-uf">Abrangência</label>
          <select id="n-uf" className="select" value={uf} onChange={(e) => setUf(e.target.value)}>
            <option value="Brasil">Brasil (todas as UFs)</option>
            {UFS.map((u) => <option key={u} value={u}>{u}</option>)}
          </select>
        </div>
        <div>
          <label className="label" htmlFor="n-ano">Ano</label>
          <select id="n-ano" className="select" value={ano} onChange={(e) => setAno(Number(e.target.value))}>
            {ANOS.map((a) => <option key={a} value={a}>{a}</option>)}
          </select>
        </div>
      </div>

      {erro && <div className="card mt-6 border-red-200 bg-red-50 text-sm text-red-800">Falha: {erro}</div>}

      <div className="mt-6 grid gap-4 sm:grid-cols-3">
        <Kpi rotulo={`Nascidos vivos ${ano}`} valor={totalNasc != null ? fmtInt(totalNasc) : "…"} detalhe={uf === "Brasil" ? "Brasil" : uf} />
        <Kpi rotulo={`Mortalidade infantil (Brasil, ${Math.min(ano,2022)})`} valor={tmiBrasil != null ? `${fmtDec(tmiBrasil)}‰` : "…"} detalhe="óbitos <1 ano por mil nascidos" />
        <Kpi rotulo="Municípios com nascimentos" valor={nat ? fmtInt(nat.length) : "…"} detalhe={`em ${ano}`} />
      </div>

      <div className="card mt-6">
        <h2 className="font-serif text-xl font-semibold text-ink-900">
          Taxa de Mortalidade Infantil por UF ({Math.min(ano, 2022)})
        </h2>
        <p className="mt-1 text-sm text-ink-500">Óbitos de menores de 1 ano por mil nascidos vivos. Disponível até 2022.</p>
        <div className="mt-4">{tmiUf ? <Barras data={tmiUf} horizontal altura={460} cor="#b4232a" /> : <Skeleton altura={460} />}</div>
      </div>

      <div className="card mt-6 overflow-x-auto">
        <h2 className="font-serif text-xl font-semibold text-ink-900">
          Municípios por % de baixo peso ao nascer ({ano}, ≥200 nascidos)
        </h2>
        <div className="mt-4">
          {ranking ? (
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b-2 border-ink-200 text-left text-xs uppercase tracking-wide text-ink-500">
                  <th className="px-3 py-2">#</th><th className="px-3 py-2">Município</th><th className="px-3 py-2">UF</th>
                  <th className="px-3 py-2 text-right">Nascidos</th><th className="px-3 py-2 text-right">Baixo peso</th>
                  <th className="px-3 py-2 text-right">Prematuro</th><th className="px-3 py-2 text-right">Pré-natal 7+</th>
                  <th className="px-3 py-2 text-right">Idade mãe</th>
                </tr>
              </thead>
              <tbody>
                {ranking.map((m, i) => (
                  <tr key={m.municipio_cod} className="border-b border-ink-100 hover:bg-ink-50">
                    <td className="px-3 py-2 tabular-nums text-ink-400">{i + 1}</td>
                    <td className="px-3 py-2 font-medium text-ink-900">{m.municipio_nome ?? m.municipio_cod}</td>
                    <td className="px-3 py-2 text-ink-600">{m.uf_sigla}</td>
                    <td className="px-3 py-2 text-right tabular-nums">{fmtInt(m.nascidos)}</td>
                    <td className="px-3 py-2 text-right font-semibold tabular-nums text-accent-800">{fmtDec(m.pct_baixo_peso, 1)}%</td>
                    <td className="px-3 py-2 text-right tabular-nums text-ink-600">{fmtDec(m.pct_prematuro, 1)}%</td>
                    <td className="px-3 py-2 text-right tabular-nums text-ink-600">{fmtDec(m.pct_prenatal_7mais, 1)}%</td>
                    <td className="px-3 py-2 text-right tabular-nums text-ink-600">{fmtDec(m.idade_media_mae, 1)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : <Skeleton altura={300} />}
        </div>
      </div>

      <p className="mt-4 text-xs text-ink-500">
        Fonte: SINASC/DataSUS (nascidos por residência) e SIM (óbitos &lt;1 ano). 2023 preliminar;
        TMI calculada até 2022. Ver <a className="text-accent-700 underline" href="/metodologia/">metodologia</a>.
      </p>
    </div>
  );
}
