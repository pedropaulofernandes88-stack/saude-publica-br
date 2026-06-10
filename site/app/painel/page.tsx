"use client";

import { useEffect, useMemo, useState } from "react";
import { Barras, SerieLinha } from "@/components/charts";
import { Kpi, Skeleton } from "@/components/kpi";
import {
  ANOS,
  FAIXAS_ORDEM,
  UFS,
  fmtDec,
  fmtInt,
  rest,
  type CapituloCid,
  type CausaAgregada,
  type LinhaMunicipio,
  type LinhaUfMes,
} from "@/lib/api";

type Sexo = "TOTAL" | "M" | "F";

export default function Painel() {
  // ── Filtros ────────────────────────────────────────────────────────────────
  const [uf, setUf] = useState<string>("Brasil");
  const [ano, setAno] = useState<number>(2024);
  const [capitulo, setCapitulo] = useState<string>("TOTAL");
  const [sexo, setSexo] = useState<Sexo>("TOTAL");
  const [capitulos, setCapitulos] = useState<CapituloCid[]>([]);

  // ── Dados ──────────────────────────────────────────────────────────────────
  const [serie, setSerie] = useState<LinhaUfMes[] | null>(null);
  const [faixas, setFaixas] = useState<LinhaUfMes[] | null>(null);
  const [municipios, setMunicipios] = useState<LinhaMunicipio[] | null>(null);
  const [causas, setCausas] = useState<CausaAgregada[] | null>(null);
  const [erro, setErro] = useState<string | null>(null);

  const [busca, setBusca] = useState("");
  const [popMin, setPopMin] = useState(50_000);
  const [ordenarPor, setOrdenarPor] = useState<"taxa" | "obitos">("taxa");

  useEffect(() => {
    rest<CapituloCid>("dim_cid10_capitulo", {
      select: "capitulo,capitulo_num,faixa,descricao",
      order: "capitulo_num",
    })
      .then(setCapitulos)
      .catch((e) => setErro(String(e)));
  }, []);

  useEffect(() => {
    setSerie(null);
    setFaixas(null);
    setMunicipios(null);
    setCausas(null);
    setErro(null);

    const ufFiltro: Record<string, string> =
      uf === "Brasil" ? {} : { uf_sigla: `eq.${uf}` };

    (async () => {
      try {
        const [serieR, faixasR, muniR, causasR] = await Promise.all([
          rest<LinhaUfMes>("mart_mortalidade_uf_mes", {
            select: "mes_competencia,uf_sigla,obitos",
            capitulo_cid: `eq.${capitulo}`,
            sexo: `eq.${sexo}`,
            faixa_etaria: "eq.TOTAL",
            order: "mes_competencia,uf_sigla",
            ...ufFiltro,
          }),
          rest<LinhaUfMes>("mart_mortalidade_uf_mes", {
            select: "faixa_etaria,uf_sigla,obitos",
            capitulo_cid: `eq.${capitulo}`,
            sexo: `eq.${sexo}`,
            faixa_etaria: "neq.TOTAL",
            ano: `eq.${ano}`,
            order: "faixa_etaria,uf_sigla,mes_competencia",
            ...ufFiltro,
          }),
          rest<LinhaMunicipio>("mart_mortalidade_municipio", {
            select:
              "municipio_cod,municipio_nome,uf_sigla,regiao,obitos,obitos_hospital,obitos_domicilio,populacao,taxa_obitos_100k",
            capitulo_cid: `eq.${capitulo}`,
            sexo: `eq.${sexo}`,
            ano: `eq.${ano}`,
            order: "municipio_cod",
            ...ufFiltro,
          }),
          rest<CausaAgregada>("mart_mortalidade_causa", {
            // agregação server-side: PostgREST agrupa pelas colunas não agregadas
            select: "causabas_3,obitos:obitos.sum()",
            ano: `eq.${ano}`,
            order: "causabas_3",
            ...ufFiltro,
          }),
        ]);
        setSerie(serieR);
        setFaixas(faixasR);
        setMunicipios(muniR);
        setCausas(causasR);
      } catch (e) {
        setErro(String(e));
      }
    })();
  }, [uf, ano, capitulo, sexo]);

  // ── Derivados ──────────────────────────────────────────────────────────────
  const serieMensal = useMemo(() => {
    if (!serie) return null;
    const porMes = new Map<string, number>();
    for (const r of serie) porMes.set(r.mes_competencia, (porMes.get(r.mes_competencia) ?? 0) + r.obitos);
    return [...porMes.entries()].sort(([a], [b]) => a.localeCompare(b)).map(([mes, obitos]) => ({ mes, obitos }));
  }, [serie]);

  const faixaChart = useMemo(() => {
    if (!faixas) return null;
    const por = new Map<string, number>();
    for (const r of faixas) por.set(r.faixa_etaria, (por.get(r.faixa_etaria) ?? 0) + r.obitos);
    return FAIXAS_ORDEM.filter((f) => por.has(f)).map((f) => ({ nome: f, obitos: por.get(f)! }));
  }, [faixas]);

  const ranking = useMemo(() => {
    if (!municipios) return null;
    const q = busca.trim().toLowerCase();
    return municipios
      .filter((m) => (m.populacao ?? 0) >= popMin || sexo !== "TOTAL")
      .filter((m) => !q || (m.municipio_nome ?? "").toLowerCase().includes(q))
      .sort((a, b) =>
        ordenarPor === "taxa"
          ? (b.taxa_obitos_100k ?? -1) - (a.taxa_obitos_100k ?? -1)
          : b.obitos - a.obitos,
      )
      .slice(0, 100);
  }, [municipios, busca, popMin, ordenarPor, sexo]);

  const topCausas = useMemo(() => {
    if (!causas) return null;
    return [...causas]
      .sort((a, b) => b.obitos - a.obitos)
      .slice(0, 15)
      .map((c) => ({ nome: c.causabas_3, obitos: c.obitos }));
  }, [causas]);

  const totalPeriodo = serieMensal?.reduce((s, r) => s + r.obitos, 0);
  const totalAno = useMemo(
    () =>
      serieMensal
        ?.filter((r) => r.mes.startsWith(String(ano)))
        .reduce((s, r) => s + r.obitos, 0),
    [serieMensal, ano],
  );

  function exportarCsv() {
    if (!ranking) return;
    const linhas = [
      "municipio;uf;obitos;obitos_hospital;obitos_domicilio;populacao;taxa_obitos_100k",
      ...ranking.map((m) =>
        [m.municipio_nome, m.uf_sigla, m.obitos, m.obitos_hospital ?? "", m.obitos_domicilio ?? "", m.populacao ?? "", m.taxa_obitos_100k ?? ""].join(";"),
      ),
    ].join("\n");
    const blob = new Blob(["﻿" + linhas], { type: "text/csv;charset=utf-8" });
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = `mortalidade_${uf}_${ano}_${capitulo}_${sexo}.csv`;
    a.click();
    URL.revokeObjectURL(a.href);
  }

  const capDesc =
    capitulo === "TOTAL"
      ? "Todas as causas"
      : `Capítulo ${capitulo} — ${capitulos.find((c) => c.capitulo === capitulo)?.descricao ?? ""}`;

  return (
    <div className="mx-auto max-w-7xl px-4 py-10 sm:px-6">
      <h1 className="font-serif text-3xl font-semibold tracking-tight text-ink-950">
        Painel de mortalidade
      </h1>
      <p className="mt-2 max-w-3xl text-ink-600">
        Filtre por estado, período, causa (CID-10) e sexo. Todos os números vêm
        diretamente da base pública — os mesmos valores acessíveis via API.
      </p>

      {/* Filtros */}
      <div className="card mt-6 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <div>
          <label className="label" htmlFor="f-uf">Abrangência</label>
          <select id="f-uf" className="select" value={uf} onChange={(e) => setUf(e.target.value)}>
            <option value="Brasil">Brasil (todas as UFs)</option>
            {UFS.map((u) => (
              <option key={u} value={u}>{u}</option>
            ))}
          </select>
        </div>
        <div>
          <label className="label" htmlFor="f-ano">Ano de referência</label>
          <select id="f-ano" className="select" value={ano} onChange={(e) => setAno(Number(e.target.value))}>
            {[...ANOS].reverse().map((a) => (
              <option key={a} value={a}>{a}{a === 2024 ? " (preliminar)" : ""}</option>
            ))}
          </select>
        </div>
        <div>
          <label className="label" htmlFor="f-cap">Causa (capítulo CID-10)</label>
          <select id="f-cap" className="select" value={capitulo} onChange={(e) => setCapitulo(e.target.value)}>
            <option value="TOTAL">Todas as causas</option>
            {capitulos.map((c) => (
              <option key={c.capitulo} value={c.capitulo}>
                {c.capitulo} ({c.faixa}) — {c.descricao.slice(0, 48)}
              </option>
            ))}
          </select>
        </div>
        <div>
          <label className="label" htmlFor="f-sexo">Sexo</label>
          <select id="f-sexo" className="select" value={sexo} onChange={(e) => setSexo(e.target.value as Sexo)}>
            <option value="TOTAL">Ambos</option>
            <option value="M">Masculino</option>
            <option value="F">Feminino</option>
          </select>
        </div>
      </div>

      {erro && (
        <div className="card mt-6 border-red-200 bg-red-50 text-sm text-red-800">
          Falha ao consultar a base: {erro}
        </div>
      )}

      {/* KPIs */}
      <div className="mt-6 grid gap-4 sm:grid-cols-3">
        <Kpi rotulo={`Óbitos em ${ano}`} valor={totalAno != null ? fmtInt(totalAno) : "…"} detalhe={capDesc} />
        <Kpi rotulo="Óbitos no triênio 2022–2024" valor={totalPeriodo != null ? fmtInt(totalPeriodo) : "…"} detalhe={uf === "Brasil" ? "Brasil" : uf} />
        <Kpi
          rotulo="Municípios com registro"
          valor={municipios ? fmtInt(municipios.length) : "…"}
          detalhe={`no recorte selecionado, ${ano}`}
        />
      </div>

      {/* Série + composição */}
      <div className="card mt-6">
        <h2 className="font-serif text-xl font-semibold text-ink-900">
          Evolução mensal — {uf === "Brasil" ? "Brasil" : uf}
        </h2>
        <p className="mt-1 text-sm text-ink-500">{capDesc}{sexo !== "TOTAL" ? ` · sexo ${sexo === "M" ? "masculino" : "feminino"}` : ""}</p>
        <div className="mt-4">{serieMensal ? <SerieLinha data={serieMensal} /> : <Skeleton />}</div>
      </div>

      <div className="mt-6 grid gap-6 lg:grid-cols-2">
        <div className="card">
          <h2 className="font-serif text-xl font-semibold text-ink-900">Distribuição etária ({ano})</h2>
          <div className="mt-4">{faixaChart ? <Barras data={faixaChart} /> : <Skeleton altura={300} />}</div>
        </div>
        <div className="card">
          <h2 className="font-serif text-xl font-semibold text-ink-900">
            15 principais causas básicas ({ano})
          </h2>
          <p className="mt-1 text-xs text-ink-500">
            Categorias CID-10 de 3 caracteres, independentes do filtro de capítulo/sexo.
          </p>
          <div className="mt-4">
            {topCausas ? <Barras data={topCausas} horizontal altura={360} /> : <Skeleton altura={360} />}
          </div>
        </div>
      </div>

      {/* Ranking de municípios */}
      <div className="card mt-6">
        <div className="flex flex-wrap items-end justify-between gap-4">
          <div>
            <h2 className="font-serif text-xl font-semibold text-ink-900">Municípios ({ano})</h2>
            <p className="mt-1 text-sm text-ink-500">
              Taxas por 100 mil hab. disponíveis quando sexo = Ambos (população não desagregada).
            </p>
          </div>
          <button onClick={exportarCsv} className="btn-ghost" disabled={!ranking?.length}>
            ⬇ Exportar CSV
          </button>
        </div>

        <div className="mt-4 grid gap-4 sm:grid-cols-3">
          <div>
            <label className="label" htmlFor="f-busca">Buscar município</label>
            <input
              id="f-busca"
              className="select"
              placeholder="ex.: Campinas"
              value={busca}
              onChange={(e) => setBusca(e.target.value)}
            />
          </div>
          <div>
            <label className="label" htmlFor="f-pop">População mínima</label>
            <select id="f-pop" className="select" value={popMin} onChange={(e) => setPopMin(Number(e.target.value))}>
              {[0, 10_000, 50_000, 100_000, 500_000].map((p) => (
                <option key={p} value={p}>{p === 0 ? "Sem mínimo" : `≥ ${fmtInt(p)} hab.`}</option>
              ))}
            </select>
          </div>
          <div>
            <label className="label" htmlFor="f-ord">Ordenar por</label>
            <select id="f-ord" className="select" value={ordenarPor} onChange={(e) => setOrdenarPor(e.target.value as "taxa" | "obitos")}>
              <option value="taxa">Taxa /100 mil hab.</option>
              <option value="obitos">Óbitos absolutos</option>
            </select>
          </div>
        </div>

        <div className="mt-4 overflow-x-auto">
          {ranking ? (
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b-2 border-ink-200 text-left text-xs uppercase tracking-wide text-ink-500">
                  <th className="px-3 py-2">#</th>
                  <th className="px-3 py-2">Município</th>
                  <th className="px-3 py-2">UF</th>
                  <th className="px-3 py-2 text-right">Óbitos</th>
                  <th className="px-3 py-2 text-right">Hospital</th>
                  <th className="px-3 py-2 text-right">Domicílio</th>
                  <th className="px-3 py-2 text-right">População</th>
                  <th className="px-3 py-2 text-right">Taxa /100k</th>
                </tr>
              </thead>
              <tbody>
                {ranking.map((m, i) => (
                  <tr key={`${m.municipio_cod}`} className="border-b border-ink-100 hover:bg-ink-50">
                    <td className="px-3 py-2 tabular-nums text-ink-400">{i + 1}</td>
                    <td className="px-3 py-2 font-medium text-ink-900">{m.municipio_nome ?? m.municipio_cod}</td>
                    <td className="px-3 py-2 text-ink-600">{m.uf_sigla}</td>
                    <td className="px-3 py-2 text-right tabular-nums">{fmtInt(m.obitos)}</td>
                    <td className="px-3 py-2 text-right tabular-nums text-ink-600">{fmtInt(m.obitos_hospital)}</td>
                    <td className="px-3 py-2 text-right tabular-nums text-ink-600">{fmtInt(m.obitos_domicilio)}</td>
                    <td className="px-3 py-2 text-right tabular-nums text-ink-600">{fmtInt(m.populacao)}</td>
                    <td className="px-3 py-2 text-right font-semibold tabular-nums text-accent-800">
                      {fmtDec(m.taxa_obitos_100k)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : (
            <Skeleton altura={300} />
          )}
          {ranking && ranking.length === 0 && (
            <p className="py-6 text-center text-sm text-ink-500">
              Nenhum município no recorte — reduza a população mínima ou ajuste a busca.
            </p>
          )}
        </div>
      </div>
    </div>
  );
}
