"use client";

import { useEffect, useMemo, useState } from "react";
import { Barras } from "@/components/charts";
import { Kpi, Skeleton } from "@/components/kpi";
import { UFS, fmtDec, fmtInt, rest, sdata, type CapituloCid, type FluxoIntermunicipal, type Icsap, type Internacao } from "@/lib/api";

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

  // ICSAP (internações evitáveis) — 2024
  const [icsap, setIcsap] = useState<Icsap[] | null>(null);
  // Fluxo de pacientes — 2024
  const [fluxoBusca, setFluxoBusca] = useState("");
  const [fluxoSel, setFluxoSel] = useState<{ cod: string; nome: string } | null>(null);
  const [fluxoSai, setFluxoSai] = useState<FluxoIntermunicipal[] | null>(null);

  useEffect(() => {
    sdata<CapituloCid[]>("capitulos").then(setCapsDim).catch(() => {});
  }, []);

  useEffect(() => {
    const ufF: Record<string, string> = uf === "Brasil" ? {} : { uf_sigla: `eq.${uf}` };
    rest<Icsap>("mart_icsap_municipio", {
      select: "municipio_cod,municipio_nome,uf_sigla,ano,internacoes_total,internacoes_icsap,pct_icsap,icsap_100k,populacao",
      ano: "eq.2024", order: "municipio_cod", ...ufF,
    }).then(setIcsap).catch(() => setIcsap([]));
  }, [uf]);

  useEffect(() => {
    if (!fluxoSel) { setFluxoSai(null); return; }
    rest<FluxoIntermunicipal>("mart_fluxo_intermunicipal", {
      select: "municipio_mov,municipio_mov_nome,uf_mov,internacoes",
      municipio_res: `eq.${fluxoSel.cod}`, ano: "eq.2024",
      order: "internacoes.desc", limit: "15",
    }).then(setFluxoSai).catch(() => setFluxoSai([]));
  }, [fluxoSel]);

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

  const icsapAgg = useMemo(() => {
    if (!icsap) return null;
    const tot = icsap.reduce((s, m) => s + m.internacoes_total, 0);
    const ic = icsap.reduce((s, m) => s + m.internacoes_icsap, 0);
    return { tot, ic, pct: tot ? (ic / tot) * 100 : 0 };
  }, [icsap]);

  const icsapRank = useMemo(() => {
    if (!icsap) return null;
    return [...icsap].filter((m) => m.internacoes_total >= 200)
      .sort((a, b) => (b.pct_icsap ?? -1) - (a.pct_icsap ?? -1)).slice(0, 30);
  }, [icsap]);

  const fluxoOpcoes = useMemo(() => {
    if (!icsap || fluxoBusca.trim().length < 2) return [];
    const q = fluxoBusca.trim().toLowerCase();
    return icsap.filter((m) => (m.municipio_nome ?? "").toLowerCase().includes(q)).slice(0, 8);
  }, [icsap, fluxoBusca]);

  const fluxoTotalSai = useMemo(
    () => fluxoSai?.reduce((s, f) => s + f.internacoes, 0) ?? 0, [fluxoSai]);

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

      {/* ICSAP — internações evitáveis */}
      <div className="card mt-6">
        <h2 className="font-serif text-xl font-semibold text-ink-900">
          Internações evitáveis (ICSAP) — {uf === "Brasil" ? "Brasil" : uf}, 2024
        </h2>
        <p className="mt-1 max-w-3xl text-sm text-ink-500">
          Internações por Condições Sensíveis à Atenção Primária: casos que <strong>bom acesso à atenção
          básica</strong> (vacinação, pré-natal, controle de hipertensão/diabetes) poderia ter evitado.
          Proporção alta sinaliza fragilidade da porta de entrada do SUS.
        </p>
        {icsapAgg && (
          <div className="mt-4 grid gap-4 sm:grid-cols-2">
            <Kpi rotulo="% de internações evitáveis" valor={`${fmtDec(icsapAgg.pct, 1)}%`}
                 detalhe={`${fmtInt(icsapAgg.ic)} de ${fmtInt(icsapAgg.tot)} internações`} />
            <Kpi rotulo="Municípios analisados" valor={icsap ? fmtInt(icsap.length) : "…"} detalhe="com internações em 2024" />
          </div>
        )}
        <div className="mt-4 overflow-x-auto">
          {icsapRank ? (
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b-2 border-ink-200 text-left text-xs uppercase tracking-wide text-ink-500">
                  <th className="px-3 py-2">#</th><th className="px-3 py-2">Município (≥200 intern.)</th><th className="px-3 py-2">UF</th>
                  <th className="px-3 py-2 text-right">% evitáveis</th><th className="px-3 py-2 text-right">ICSAP</th><th className="px-3 py-2 text-right">Total</th>
                </tr>
              </thead>
              <tbody>
                {icsapRank.map((m, i) => (
                  <tr key={m.municipio_cod} className="border-b border-ink-100 hover:bg-ink-50">
                    <td className="px-3 py-2 tabular-nums text-ink-400">{i + 1}</td>
                    <td className="px-3 py-2 font-medium text-ink-900">{m.municipio_nome ?? m.municipio_cod}</td>
                    <td className="px-3 py-2 text-ink-600">{m.uf_sigla}</td>
                    <td className="px-3 py-2 text-right font-semibold tabular-nums text-accent-800">{fmtDec(m.pct_icsap, 1)}%</td>
                    <td className="px-3 py-2 text-right tabular-nums text-ink-600">{fmtInt(m.internacoes_icsap)}</td>
                    <td className="px-3 py-2 text-right tabular-nums text-ink-600">{fmtInt(m.internacoes_total)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : <Skeleton altura={300} />}
        </div>
      </div>

      {/* Fluxo de pacientes */}
      <div className="card mt-6">
        <h2 className="font-serif text-xl font-semibold text-ink-900">Fluxo de pacientes (2024)</h2>
        <p className="mt-1 max-w-3xl text-sm text-ink-500">
          Para onde vão os moradores de um município se internar. Revela dependência de polos
          regionais e evasão da rede local. Inspirado no LabSUS.
        </p>
        <div className="mt-4 max-w-md">
          <label className="label" htmlFor="f-busca">Buscar município de residência</label>
          <input id="f-busca" className="select" placeholder="ex.: Penápolis" value={fluxoBusca}
                 onChange={(e) => { setFluxoBusca(e.target.value); setFluxoSel(null); }} />
          {fluxoOpcoes.length > 0 && !fluxoSel && (
            <div className="mt-1 rounded-lg border border-ink-200 bg-white shadow-sm">
              {fluxoOpcoes.map((o) => (
                <button key={o.municipio_cod} type="button"
                        onClick={() => { setFluxoSel({ cod: o.municipio_cod, nome: o.municipio_nome ?? o.municipio_cod }); setFluxoBusca(o.municipio_nome ?? ""); }}
                        className="block w-full px-3 py-2 text-left text-sm hover:bg-ink-50">
                  {o.municipio_nome} <span className="text-ink-400">· {o.uf_sigla}</span>
                </button>
              ))}
            </div>
          )}
        </div>
        {fluxoSel && (
          <div className="mt-4">
            <p className="text-sm text-ink-600">
              Destinos das internações de moradores de <strong>{fluxoSel.nome}</strong> (fluxos intermunicipais ≥ 5):
            </p>
            {fluxoSai ? (
              fluxoSai.length === 0 ? (
                <p className="mt-2 text-sm text-ink-500">Sem fluxo intermunicipal relevante registrado (pacientes internados no próprio município).</p>
              ) : (
                <table className="mt-2 w-full text-sm">
                  <thead>
                    <tr className="border-b-2 border-ink-200 text-left text-xs uppercase tracking-wide text-ink-500">
                      <th className="px-3 py-2">Destino</th><th className="px-3 py-2">UF</th>
                      <th className="px-3 py-2 text-right">Internações</th><th className="px-3 py-2 text-right">% do fluxo</th>
                    </tr>
                  </thead>
                  <tbody>
                    {fluxoSai.map((f) => (
                      <tr key={f.municipio_mov} className="border-b border-ink-100">
                        <td className="px-3 py-2 font-medium text-ink-900">{f.municipio_mov_nome ?? f.municipio_mov}</td>
                        <td className="px-3 py-2 text-ink-600">{f.uf_mov}</td>
                        <td className="px-3 py-2 text-right tabular-nums">{fmtInt(f.internacoes)}</td>
                        <td className="px-3 py-2 text-right tabular-nums text-ink-600">{fmtDec(f.internacoes / fluxoTotalSai * 100, 1)}%</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )
            ) : <Skeleton altura={160} />}
          </div>
        )}
      </div>

      <p className="mt-4 text-xs text-ink-500">
        Fonte: SIH/DataSUS (AIH aprovadas). Internações por município de residência e capítulo CID-10 do
        diagnóstico principal; valores aprovados (VAL_TOT). ICSAP: aproximação da Lista Brasileira (CID-10
        3 caracteres). Fluxo: município de residência → de atendimento. Cobre apenas a rede SUS. 2024
        preliminar. Ver <a className="text-accent-700 underline" href="/metodologia/">metodologia</a>.
      </p>
    </div>
  );
}
