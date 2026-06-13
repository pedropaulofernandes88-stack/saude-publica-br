"use client";

import { useEffect, useMemo, useState } from "react";
import { Barras } from "@/components/charts";
import { Kpi, Skeleton } from "@/components/kpi";
import { UFS, fmtDec, fmtInt, rest, sdata, type CapituloCid, type Internacao } from "@/lib/api";

const ANOS_SIH = [2024, 2023, 2022];

function fmtReais(v: number | null | undefined): string {
  if (v == null) return "—";
  if (v >= 1e9) return `R$ ${(v / 1e9).toLocaleString("pt-BR", { maximumFractionDigits: 1 })} bi`;
  if (v >= 1e6) return `R$ ${(v / 1e6).toLocaleString("pt-BR", { maximumFractionDigits: 1 })} mi`;
  return `R$ ${v.toLocaleString("pt-BR", { maximumFractionDigits: 0 })}`;
}

export default function Internacoes() {
  const [uf, setUf] = useState("Brasil");
  const [ano, setAno] = useState(2024);
  const [capitulo, setCapitulo] = useState("TOTAL");
  const [linhas, setLinhas] = useState<Internacao[] | null>(null);
  const [capsDim, setCapsDim] = useState<CapituloCid[]>([]);
  const [erro, setErro] = useState<string | null>(null);
  const [ordenar, setOrdenar] = useState<"internacoes" | "permanencia_media" | "mortalidade_pct" | "custo_medio">("internacoes");

  useEffect(() => {
    sdata<CapituloCid[]>("capitulos").then(setCapsDim).catch(() => {});
  }, []);

  useEffect(() => {
    setLinhas(null); setErro(null);
    const ufF: Record<string, string> = uf === "Brasil" ? {} : { uf_sigla: `eq.${uf}` };
    rest<Internacao>("mart_internacoes_municipio", {
      select: "municipio_cod,municipio_nome,uf_sigla,regiao,ano,capitulo_cid,internacoes,obitos,dias_permanencia,valor_total,permanencia_media,mortalidade_pct,custo_medio,internacoes_100k,populacao",
      ano: `eq.${ano}`,
      capitulo_cid: `eq.${capitulo}`,
      order: "municipio_cod",
      ...ufF,
    })
      .then(setLinhas)
      .catch((e) => setErro(String(e)));
  }, [uf, ano, capitulo]);

  const agregado = useMemo(() => {
    if (!linhas) return null;
    return linhas.reduce(
      (a, m) => ({
        internacoes: a.internacoes + m.internacoes,
        obitos: a.obitos + m.obitos,
        dias: a.dias + m.dias_permanencia,
        valor: a.valor + m.valor_total,
      }),
      { internacoes: 0, obitos: 0, dias: 0, valor: 0 },
    );
  }, [linhas]);

  const ranking = useMemo(() => {
    if (!linhas) return null;
    return [...linhas]
      .filter((m) => m.internacoes >= 100)
      .sort((a, b) => (b[ordenar] ?? -1) - (a[ordenar] ?? -1))
      .slice(0, 50);
  }, [linhas, ordenar]);

  // Para a visão por capítulo (apenas quando capítulo=TOTAL e Brasil/UF): buscar todos os capítulos
  const [porCap, setPorCap] = useState<{ nome: string; obitos: number }[] | null>(null);
  useEffect(() => {
    setPorCap(null);
    const ufF: Record<string, string> = uf === "Brasil" ? {} : { uf_sigla: `eq.${uf}` };
    rest<Internacao>("mart_internacoes_municipio", {
      select: "capitulo_cid,internacoes:internacoes.sum()",
      ano: `eq.${ano}`,
      capitulo_cid: "neq.TOTAL",
      order: "capitulo_cid",
      ...ufF,
    })
      .then((rows) =>
        setPorCap(
          rows.map((r) => ({ nome: r.capitulo_cid, obitos: r.internacoes }))
            .sort((a, b) => b.obitos - a.obitos).slice(0, 10),
        ),
      )
      .catch(() => {});
  }, [uf, ano]);

  const capDesc = capitulo === "TOTAL" ? "Todas as causas"
    : `Capítulo ${capitulo} — ${capsDim.find((c) => c.capitulo === capitulo)?.descricao ?? ""}`;

  return (
    <div className="mx-auto max-w-7xl px-4 py-10 sm:px-6">
      <h1 className="font-serif text-3xl font-semibold tracking-tight text-ink-950">Internações hospitalares (SUS)</h1>
      <p className="mt-2 max-w-3xl text-ink-600">
        Internações pagas pelo SUS (SIH/AIH, 2022–2024) por município e capítulo
        CID-10: volume, permanência média, mortalidade intra-hospitalar e custo.
      </p>

      <div className="card mt-6 grid gap-4 sm:grid-cols-3">
        <div>
          <label className="label" htmlFor="i-uf">Abrangência</label>
          <select id="i-uf" className="select" value={uf} onChange={(e) => setUf(e.target.value)}>
            <option value="Brasil">Brasil (todas as UFs)</option>
            {UFS.map((u) => <option key={u} value={u}>{u}</option>)}
          </select>
        </div>
        <div>
          <label className="label" htmlFor="i-ano">Ano</label>
          <select id="i-ano" className="select" value={ano} onChange={(e) => setAno(Number(e.target.value))}>
            {ANOS_SIH.map((a) => <option key={a} value={a}>{a}{a === 2024 ? " (preliminar)" : ""}</option>)}
          </select>
        </div>
        <div>
          <label className="label" htmlFor="i-cap">Capítulo CID-10</label>
          <select id="i-cap" className="select" value={capitulo} onChange={(e) => setCapitulo(e.target.value)}>
            <option value="TOTAL">Todas as causas</option>
            {capsDim.map((c) => <option key={c.capitulo} value={c.capitulo}>{c.capitulo} — {c.descricao.slice(0, 44)}</option>)}
          </select>
        </div>
      </div>

      {erro && <div className="card mt-6 border-red-200 bg-red-50 text-sm text-red-800">Falha: {erro}</div>}

      {agregado && (
        <div className="mt-6 grid gap-4 sm:grid-cols-4">
          <Kpi rotulo={`Internações ${ano}`} valor={fmtInt(agregado.internacoes)} detalhe={capDesc} />
          <Kpi rotulo="Permanência média" valor={`${fmtDec(agregado.dias / agregado.internacoes)} dias`} detalhe="dias por internação" />
          <Kpi rotulo="Mortalidade hospitalar" valor={`${fmtDec((agregado.obitos / agregado.internacoes) * 100, 2)}%`}
               detalhe={`${fmtInt(agregado.obitos)} óbitos`} />
          <Kpi rotulo="Valor aprovado" valor={fmtReais(agregado.valor)}
               detalhe={`custo médio ${fmtReais(agregado.valor / agregado.internacoes)}`} />
        </div>
      )}

      <div className="card mt-6">
        <h2 className="font-serif text-xl font-semibold text-ink-900">Internações por capítulo CID-10 ({ano})</h2>
        <div className="mt-4">{porCap ? <Barras data={porCap} horizontal altura={320} /> : <Skeleton altura={320} />}</div>
        <div className="mt-3 grid gap-1 text-xs text-ink-500 sm:grid-cols-2">
          {porCap?.slice(0, 6).map((c) => {
            const d = capsDim.find((x) => x.capitulo === c.nome);
            return d ? <p key={c.nome}><b>{c.nome}</b>: {d.descricao}</p> : null;
          })}
        </div>
      </div>

      <div className="card mt-6 overflow-x-auto">
        <div className="flex flex-wrap items-end justify-between gap-4">
          <h2 className="font-serif text-xl font-semibold text-ink-900">Municípios ({ano})</h2>
          <div>
            <label className="label" htmlFor="i-ord">Ordenar por</label>
            <select id="i-ord" className="select" value={ordenar} onChange={(e) => setOrdenar(e.target.value as typeof ordenar)}>
              <option value="internacoes">Internações</option>
              <option value="permanencia_media">Permanência média</option>
              <option value="mortalidade_pct">Mortalidade hospitalar</option>
              <option value="custo_medio">Custo médio</option>
            </select>
          </div>
        </div>
        <div className="mt-4">
          {ranking ? (
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b-2 border-ink-200 text-left text-xs uppercase tracking-wide text-ink-500">
                  <th className="px-3 py-2">#</th><th className="px-3 py-2">Município</th><th className="px-3 py-2">UF</th>
                  <th className="px-3 py-2 text-right">Internações</th><th className="px-3 py-2 text-right">Perm. média</th>
                  <th className="px-3 py-2 text-right">Mortalidade</th><th className="px-3 py-2 text-right">Custo médio</th>
                </tr>
              </thead>
              <tbody>
                {ranking.map((m, i) => (
                  <tr key={m.municipio_cod} className="border-b border-ink-100 hover:bg-ink-50">
                    <td className="px-3 py-2 tabular-nums text-ink-400">{i + 1}</td>
                    <td className="px-3 py-2 font-medium text-ink-900">{m.municipio_nome ?? m.municipio_cod}</td>
                    <td className="px-3 py-2 text-ink-600">{m.uf_sigla}</td>
                    <td className="px-3 py-2 text-right tabular-nums">{fmtInt(m.internacoes)}</td>
                    <td className="px-3 py-2 text-right tabular-nums text-ink-600">{fmtDec(m.permanencia_media)}</td>
                    <td className="px-3 py-2 text-right tabular-nums text-ink-600">{fmtDec(m.mortalidade_pct, 2)}%</td>
                    <td className="px-3 py-2 text-right tabular-nums text-accent-800">{fmtReais(m.custo_medio)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : <Skeleton altura={300} />}
        </div>
      </div>

      <p className="mt-4 text-xs text-ink-500">
        Fonte: SIH/DataSUS (AIH aprovadas). Internações por município de residência e capítulo CID-10 do
        diagnóstico principal; valores aprovados (VAL_TOT). Cobre apenas a rede SUS. 2024 preliminar. Ver{" "}
        <a className="text-accent-700 underline" href="/metodologia/">metodologia</a>.
      </p>
    </div>
  );
}
