"use client";

import { useEffect, useMemo, useState } from "react";
import { Barras } from "@/components/charts";
import { Kpi, Skeleton } from "@/components/kpi";
import { UFS, fmtDec, fmtInt, rest, sdata, type CapituloCid, type FluxoIntermunicipal, type Icsap, type Internacao, type InternacaoAgravo, type InternacaoHospital } from "@/lib/api";

const ANOS_SIH = [2024, 2023, 2022];

function fmtReais(v: number | null | undefined): string {
  if (v == null) return "—";
  if (v >= 1e9) return `R$ ${(v / 1e9).toLocaleString("pt-BR", { maximumFractionDigits: 1 })} bi`;
  if (v >= 1e6) return `R$ ${(v / 1e6).toLocaleString("pt-BR", { maximumFractionDigits: 1 })} mi`;
  return `R$ ${v.toLocaleString("pt-BR", { maximumFractionDigits: 0 })}`;
}

/** Limite inferior do IC95% (Wilson) da proporção x/n — evita sinalizar ruído de amostra pequena. */
function wilsonInf(x: number, n: number): number {
  if (!n) return 0;
  const z = 1.96, p = x / n;
  const den = 1 + (z * z) / n;
  const centro = p + (z * z) / (2 * n);
  const margem = z * Math.sqrt((p * (1 - p)) / n + (z * z) / (4 * n * n));
  return (centro - margem) / den;
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

  // ── Item 2: agravos traçadores (CID-3) ────────────────────────────────────
  const AGRAVOS_ORDEM = ["diabetes", "avc", "iam", "icc", "asma", "dpoc", "pneumonia",
    "depressao", "esquizofrenia", "alcool_drogas", "tce"];

  // Custo unitário proxy das condições ICSAP (nacional) → estimativa de gasto evitável.
  const [custoIcsapUnit, setCustoIcsapUnit] = useState<number | null>(null);
  useEffect(() => {
    rest<{ valor_total: number; internacoes: number }>("mart_internacoes_agravo", {
      select: "valor_total:valor_total.sum(),internacoes:internacoes.sum()",
      agravo: "in.(pneumonia,icc,dpoc,asma,diabetes)",
    }).then((r) => {
      if (r[0]?.internacoes) setCustoIcsapUnit(r[0].valor_total / r[0].internacoes);
    }).catch(() => {});
  }, []);
  const [agravoPanorama, setAgravoPanorama] = useState<InternacaoAgravo[] | null>(null);
  const [agravoSel, setAgravoSel] = useState("diabetes");
  const [agravoRank, setAgravoRank] = useState<InternacaoAgravo[] | null>(null);

  useEffect(() => {
    setAgravoPanorama(null);
    const ufF: Record<string, string> = uf === "Brasil" ? {} : { uf_sigla: `eq.${uf}` };
    rest<InternacaoAgravo>("mart_internacoes_agravo", {
      select: "agravo,agravo_label,grupo,internacoes:internacoes.sum(),obitos:obitos.sum(),dias_permanencia:dias_permanencia.sum(),valor_total:valor_total.sum()",
      ano: "eq.2024", order: "agravo", ...ufF,
    }).then(setAgravoPanorama).catch(() => setAgravoPanorama([]));
  }, [uf]);

  useEffect(() => {
    setAgravoRank(null);
    const ufF: Record<string, string> = uf === "Brasil" ? {} : { uf_sigla: `eq.${uf}` };
    rest<InternacaoAgravo>("mart_internacoes_agravo", {
      select: "municipio_cod,municipio_nome,uf_sigla,internacoes,internacoes_100k,permanencia_media,mortalidade_pct,custo_medio",
      ano: "eq.2024", agravo: `eq.${agravoSel}`, internacoes: "gte.20",
      order: "internacoes_100k.desc.nullslast", limit: "30", ...ufF,
    }).then(setAgravoRank).catch(() => setAgravoRank([]));
  }, [uf, agravoSel]);

  const agravoPanoramaCalc = useMemo(() => {
    if (!agravoPanorama) return null;
    return [...agravoPanorama]
      .map((a) => ({
        ...a,
        permanencia_media: a.internacoes ? a.dias_permanencia / a.internacoes : null,
        mortalidade_pct: a.internacoes ? (a.obitos / a.internacoes) * 100 : null,
        custo_medio: a.internacoes ? a.valor_total / a.internacoes : null,
      }))
      .sort((x, y) => y.internacoes - x.internacoes);
  }, [agravoPanorama]);

  // ── Item 3: visão hospitalar (CNES) ───────────────────────────────────────
  const [hospRank, setHospRank] = useState<InternacaoHospital[] | null>(null);
  const [hospOrd, setHospOrd] = useState<"internacoes" | "mortalidade_pct" | "permanencia_media" | "custo_medio">("internacoes");
  useEffect(() => {
    setHospRank(null);
    const ufF: Record<string, string> = uf === "Brasil" ? {} : { uf_sigla: `eq.${uf}` };
    rest<InternacaoHospital>("mart_internacoes_hospital", {
      select: "cnes,municipio_nome,uf_sigla,capitulo_principal,internacoes,permanencia_media,mortalidade_pct,custo_medio",
      ano: "eq.2024", internacoes: "gte.50", order: `${hospOrd}.desc`, limit: "50", ...ufF,
    }).then(setHospRank).catch(() => setHospRank([]));
  }, [uf, hospOrd]);

  const capDesc = capitulo === "TOTAL" ? "Todas as causas"
    : `Capítulo ${capitulo} — ${capsDim.find((c) => c.capitulo === capitulo)?.descricao ?? ""}`;

  return (
    <div className="mx-auto max-w-7xl px-4 py-10 sm:px-6">
      <h1 className="font-serif text-3xl font-semibold tracking-tight text-ink-950">Internações hospitalares (SUS)</h1>
      <p className="mt-2 max-w-3xl text-ink-600">
        Internações pagas pelo SUS (SIH/AIH, 2022–2024) por município e capítulo
        CID-10: volume, permanência média, mortalidade intra-hospitalar e custo.
      </p>
      <div className="mt-4 max-w-3xl rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900">
        <strong>Como ler com cuidado:</strong> esta base cobre <strong>apenas a rede SUS</strong>.
        Como cerca de um quarto da população tem plano de saúde (concentrado em municípios mais
        ricos), internações por 100 mil habitantes <strong>não são comparáveis entre municípios</strong>{" "}
        sem considerar a cobertura privada — um valor baixo pode significar mais plano, não menos
        adoecimento. A mortalidade hospitalar é bruta, <strong>sem ajuste de risco</strong> (case-mix).
        Detalhes na <a className="underline" href="/metodologia/">metodologia</a>.
      </div>

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
          Proporção alta sinaliza fragilidade da porta de entrada do SUS — é um indicador de{" "}
          <strong>sistema</strong>, não de "má gestão" local: costuma refletir subfinanciamento e
          barreiras de acesso à atenção básica, não culpa do município.
        </p>
        {icsapAgg && (
          <div className="mt-4 grid gap-4 sm:grid-cols-3">
            <Kpi rotulo="% de internações evitáveis" valor={`${fmtDec(icsapAgg.pct, 1)}%`}
                 detalhe={`${fmtInt(icsapAgg.ic)} de ${fmtInt(icsapAgg.tot)} internações`} />
            <Kpi rotulo="Gasto potencialmente evitável" valor={custoIcsapUnit ? fmtReais(icsapAgg.ic * custoIcsapUnit) : "…"}
                 detalhe="estimativa (ordem de grandeza)" />
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
                  <th className="px-3 py-2 text-right">R$ evitável (est.)</th>
                </tr>
              </thead>
              <tbody>
                {icsapRank.map((m, i) => {
                  const acima = !!icsapAgg && m.internacoes_total > 0
                    && wilsonInf(m.internacoes_icsap, m.internacoes_total) > icsapAgg.pct / 100;
                  return (
                    <tr key={m.municipio_cod} className="border-b border-ink-100 hover:bg-ink-50">
                      <td className="px-3 py-2 tabular-nums text-ink-400">{i + 1}</td>
                      <td className="px-3 py-2 font-medium text-ink-900">{m.municipio_nome ?? m.municipio_cod}</td>
                      <td className="px-3 py-2 text-ink-600">{m.uf_sigla}</td>
                      <td className="px-3 py-2 text-right font-semibold tabular-nums text-accent-800">
                        {fmtDec(m.pct_icsap, 1)}%
                        {acima && <span title="Acima da média do recorte com 95% de confiança (IC de Wilson)" className="ml-1 text-red-600">▲</span>}
                      </td>
                      <td className="px-3 py-2 text-right tabular-nums text-ink-600">{fmtInt(m.internacoes_icsap)}</td>
                      <td className="px-3 py-2 text-right tabular-nums text-ink-600">{fmtInt(m.internacoes_total)}</td>
                      <td className="px-3 py-2 text-right tabular-nums text-ink-500">{custoIcsapUnit ? fmtReais(m.internacoes_icsap * custoIcsapUnit) : "—"}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          ) : <Skeleton altura={300} />}
        </div>
        <p className="mt-2 text-xs text-ink-400">
          <span className="text-red-600">▲</span> município cujo IC95% (Wilson) do %ICSAP supera a média do
          recorte ({icsapAgg ? fmtDec(icsapAgg.pct, 1) : "…"}%) — sinal robusto, não ruído de amostra pequena.
          Gasto evitável (est.) = internações ICSAP × custo médio das internações por condições sensíveis
          (≈ {custoIcsapUnit ? fmtReais(custoIcsapUnit) : "…"}/internação, nacional); ordem de grandeza, não valor contábil.
        </p>
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

      {/* Item 2 — Internações por agravo (condições traçadoras) */}
      <div className="card mt-6">
        <h2 className="font-serif text-xl font-semibold text-ink-900">
          Internações por agravo — {uf === "Brasil" ? "Brasil" : uf}, 2024
        </h2>
        <p className="mt-1 max-w-3xl text-sm text-ink-500">
          Condições traçadoras isoladas no nível de CID-10 (3 caracteres): permanência média,
          mortalidade hospitalar e custo médio por agravo. Clique numa linha para ver o ranking de municípios.
        </p>
        <div className="mt-4 overflow-x-auto">
          {agravoPanoramaCalc ? (
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b-2 border-ink-200 text-left text-xs uppercase tracking-wide text-ink-500">
                  <th className="px-3 py-2">Agravo</th><th className="px-3 py-2">Grupo</th>
                  <th className="px-3 py-2 text-right">Internações</th><th className="px-3 py-2 text-right">Perm. média</th>
                  <th className="px-3 py-2 text-right">Mortalidade</th><th className="px-3 py-2 text-right">Custo médio</th>
                </tr>
              </thead>
              <tbody>
                {agravoPanoramaCalc.map((a) => (
                  <tr key={a.agravo}
                      className={`cursor-pointer border-b border-ink-100 hover:bg-ink-50 ${a.agravo === agravoSel ? "bg-accent-50" : ""}`}
                      onClick={() => setAgravoSel(a.agravo)}>
                    <td className="px-3 py-2 font-medium text-ink-900">{a.agravo_label}</td>
                    <td className="px-3 py-2 text-ink-500">{a.grupo}</td>
                    <td className="px-3 py-2 text-right tabular-nums">{fmtInt(a.internacoes)}</td>
                    <td className="px-3 py-2 text-right tabular-nums text-ink-600">{fmtDec(a.permanencia_media)}</td>
                    <td className="px-3 py-2 text-right tabular-nums text-ink-600">{fmtDec(a.mortalidade_pct, 2)}%</td>
                    <td className="px-3 py-2 text-right tabular-nums text-accent-800">{fmtReais(a.custo_medio)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : <Skeleton altura={360} />}
        </div>

        <div className="mt-6">
          <p className="label">
            Municípios com maior taxa de{" "}
            <strong className="text-ink-700">{agravoPanorama?.find((p) => p.agravo === agravoSel)?.agravo_label ?? agravoSel}</strong>{" "}
            (≥ 20 internações, por 100k hab.)
          </p>
          <div className="mt-3 overflow-x-auto">
            {agravoRank ? (
              agravoRank.length === 0 ? (
                <p className="text-sm text-ink-500">Sem municípios com ≥ 20 internações para este agravo no recorte.</p>
              ) : (
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b-2 border-ink-200 text-left text-xs uppercase tracking-wide text-ink-500">
                      <th className="px-3 py-2">#</th><th className="px-3 py-2">Município</th><th className="px-3 py-2">UF</th>
                      <th className="px-3 py-2 text-right">Internações</th><th className="px-3 py-2 text-right">por 100k</th>
                      <th className="px-3 py-2 text-right">Mortalidade</th>
                    </tr>
                  </thead>
                  <tbody>
                    {agravoRank.map((m, i) => (
                      <tr key={m.municipio_cod} className="border-b border-ink-100 hover:bg-ink-50">
                        <td className="px-3 py-2 tabular-nums text-ink-400">{i + 1}</td>
                        <td className="px-3 py-2 font-medium text-ink-900">{m.municipio_nome ?? m.municipio_cod}</td>
                        <td className="px-3 py-2 text-ink-600">{m.uf_sigla}</td>
                        <td className="px-3 py-2 text-right tabular-nums">{fmtInt(m.internacoes)}</td>
                        <td className="px-3 py-2 text-right font-semibold tabular-nums text-accent-800">{fmtDec(m.internacoes_100k)}</td>
                        <td className="px-3 py-2 text-right tabular-nums text-ink-600">{fmtDec(m.mortalidade_pct, 2)}%</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )
            ) : <Skeleton altura={300} />}
          </div>
        </div>
      </div>

      {/* Item 3 — Visão hospitalar (CNES) */}
      <div className="card mt-6 overflow-x-auto">
        <div className="flex flex-wrap items-end justify-between gap-4">
          <div>
            <h2 className="font-serif text-xl font-semibold text-ink-900">
              Hospitais — {uf === "Brasil" ? "Brasil" : uf}, 2024
            </h2>
            <p className="mt-1 max-w-2xl text-sm text-ink-500">
              Visão por estabelecimento (CNES), com ≥ 50 internações: volume, permanência média,
              mortalidade hospitalar e custo médio, com o capítulo CID predominante.
            </p>
          </div>
          <div>
            <label className="label" htmlFor="h-ord">Ordenar por</label>
            <select id="h-ord" className="select" value={hospOrd} onChange={(e) => setHospOrd(e.target.value as typeof hospOrd)}>
              <option value="internacoes">Internações</option>
              <option value="mortalidade_pct">Mortalidade</option>
              <option value="permanencia_media">Permanência média</option>
              <option value="custo_medio">Custo médio</option>
            </select>
          </div>
        </div>
        <div className="mt-4">
          {hospRank ? (
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b-2 border-ink-200 text-left text-xs uppercase tracking-wide text-ink-500">
                  <th className="px-3 py-2">#</th><th className="px-3 py-2">CNES</th><th className="px-3 py-2">Município</th><th className="px-3 py-2">UF</th>
                  <th className="px-3 py-2">Cap.</th><th className="px-3 py-2 text-right">Internações</th>
                  <th className="px-3 py-2 text-right">Perm.</th><th className="px-3 py-2 text-right">Mortalidade</th><th className="px-3 py-2 text-right">Custo médio</th>
                </tr>
              </thead>
              <tbody>
                {hospRank.map((hh, i) => (
                  <tr key={hh.cnes} className="border-b border-ink-100 hover:bg-ink-50">
                    <td className="px-3 py-2 tabular-nums text-ink-400">{i + 1}</td>
                    <td className="px-3 py-2 tabular-nums text-ink-500">{hh.cnes}</td>
                    <td className="px-3 py-2 font-medium text-ink-900">{hh.municipio_nome ?? hh.municipio_cod}</td>
                    <td className="px-3 py-2 text-ink-600">{hh.uf_sigla}</td>
                    <td className="px-3 py-2 text-ink-500">{hh.capitulo_principal}</td>
                    <td className="px-3 py-2 text-right tabular-nums">{fmtInt(hh.internacoes)}</td>
                    <td className="px-3 py-2 text-right tabular-nums text-ink-600">{fmtDec(hh.permanencia_media)}</td>
                    <td className="px-3 py-2 text-right tabular-nums text-ink-600">{fmtDec(hh.mortalidade_pct, 2)}%</td>
                    <td className="px-3 py-2 text-right tabular-nums text-accent-800">{fmtReais(hh.custo_medio)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : <Skeleton altura={300} />}
        </div>
        <p className="mt-2 text-xs text-ink-400">
          Hospitais identificados pelo código CNES (o nome do estabelecimento não está incluído nesta versão).
          Ocupação de leitos não é estimada (não deriva de forma confiável da AIH).
        </p>
      </div>

      <p className="mt-4 text-xs text-ink-500">
        Fonte: SIH/DataSUS (AIH aprovadas). Internações por município de residência e capítulo CID-10 do
        diagnóstico principal; valores aprovados (VAL_TOT). ICSAP: aproximação da Lista Brasileira (CID-10
        3 caracteres). Agravos: condições traçadoras pelo diagnóstico principal (CID-10, 3 caracteres) —
        causas externas representadas pelo TCE, pois o mecanismo do acidente (códigos V) não consta no
        diagnóstico principal da AIH. Hospitais: agregados por CNES (município de atendimento). Fluxo:
        município de residência → de atendimento. Cobre apenas a rede SUS. 2024 preliminar.
        Ver <a className="text-accent-700 underline" href="/metodologia/">metodologia</a>.
      </p>
    </div>
  );
}
