"use client";

import { useEffect, useMemo, useState } from "react";
import { Barras, SerieLinha } from "@/components/charts";
import { Kpi, Skeleton } from "@/components/kpi";
import {
  ANOS,
  ANO_DETALHE,
  FAIXAS_ORDEM,
  UFS,
  fmtDec,
  fmtInt,
  rest,
  sdata,
  type CapituloCid,
  type CausaAgregada,
  type LinhaMunicipio,
  type LinhaUfMes,
  type SerieTotalItem,
} from "@/lib/api";

type Sexo = "TOTAL" | "M" | "F";

export default function Painel() {
  const [uf, setUf] = useState<string>("Brasil");
  const [ano, setAno] = useState<number>(2024);
  const [capitulo, setCapitulo] = useState<string>("TOTAL");
  const [sexo, setSexo] = useState<Sexo>("TOTAL");
  const [capitulos, setCapitulos] = useState<CapituloCid[]>([]);

  const [serie, setSerie] = useState<{ mes: string; obitos: number }[] | null>(null);
  const [faixas, setFaixas] = useState<LinhaUfMes[] | null>(null);
  const [municipios, setMunicipios] = useState<LinhaMunicipio[] | null>(null);
  const [causas, setCausas] = useState<CausaAgregada[] | null>(null);
  const [erro, setErro] = useState<string | null>(null);

  const [busca, setBusca] = useState("");
  const [popMin, setPopMin] = useState(50_000);
  const [ordenarPor, setOrdenarPor] = useState<"taxa_pad" | "taxa" | "obitos">("taxa_pad");

  const historico = ano < ANO_DETALHE; // grão reduzido: sexo/faixa só TOTAL

  useEffect(() => {
    sdata<CapituloCid[]>("capitulos")
      .catch(() =>
        rest<CapituloCid>("dim_cid10_capitulo", {
          select: "capitulo,capitulo_num,faixa,descricao",
          order: "capitulo_num",
        }),
      )
      .then(setCapitulos)
      .catch((e) => setErro(String(e)));
  }, []);

  // séries históricas em grão reduzido não têm sexo ≠ TOTAL
  useEffect(() => {
    if (historico && sexo !== "TOTAL") setSexo("TOTAL");
  }, [historico, sexo]);

  useEffect(() => {
    setSerie(null); setFaixas(null); setMunicipios(null); setCausas(null); setErro(null);
    const ufFiltro: Record<string, string> = uf === "Brasil" ? {} : { uf_sigla: `eq.${uf}` };

    (async () => {
      try {
        // Série mensal: caminho estático (egress zero) p/ TOTAL; REST para recortes
        let seriePromise: Promise<{ mes: string; obitos: number }[]>;
        if (capitulo === "TOTAL" && sexo === "TOTAL") {
          seriePromise = sdata<SerieTotalItem[]>("serie_total").then((all) => {
            const alvo = uf === "Brasil" ? "BR" : uf;
            return all
              .filter((r) => r.uf_sigla === alvo)
              .sort((a, b) => a.mes_competencia.localeCompare(b.mes_competencia))
              .map((r) => ({ mes: r.mes_competencia, obitos: r.obitos }));
          });
        } else {
          seriePromise = rest<LinhaUfMes>("mart_mortalidade_uf_mes", {
            select: "mes_competencia,uf_sigla,obitos",
            capitulo_cid: `eq.${capitulo}`,
            sexo: `eq.${sexo}`,
            faixa_etaria: "eq.TOTAL",
            order: "mes_competencia,uf_sigla",
            ...ufFiltro,
          }).then((rows) => {
            const por = new Map<string, number>();
            for (const r of rows) por.set(r.mes_competencia, (por.get(r.mes_competencia) ?? 0) + r.obitos);
            return [...por.entries()].sort(([a], [b]) => a.localeCompare(b)).map(([mes, obitos]) => ({ mes, obitos }));
          });
        }

        const [serieR, faixasR, muniR, causasR] = await Promise.all([
          seriePromise,
          rest<LinhaUfMes>("mart_mortalidade_uf_mes", {
            select: "faixa_etaria,uf_sigla,obitos",
            capitulo_cid: historico ? "eq.TOTAL" : `eq.${capitulo}`,
            sexo: "eq.TOTAL",
            faixa_etaria: "neq.TOTAL",
            ano: `eq.${ano}`,
            order: "faixa_etaria,uf_sigla,mes_competencia",
            ...ufFiltro,
          }),
          rest<LinhaMunicipio>("mart_mortalidade_municipio", {
            select:
              "municipio_cod,municipio_nome,uf_sigla,regiao,obitos,obitos_hospital,obitos_domicilio,populacao,taxa_obitos_100k,taxa_padronizada_100k,ic95_inf,ic95_sup",
            capitulo_cid: `eq.${capitulo}`,
            sexo: `eq.${sexo}`,
            ano: `eq.${ano}`,
            order: "municipio_cod",
            ...ufFiltro,
          }),
          rest<CausaAgregada>("mart_mortalidade_causa", {
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
  }, [uf, ano, capitulo, sexo, historico]);

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
        ordenarPor === "taxa_pad"
          ? (b.taxa_padronizada_100k ?? -1) - (a.taxa_padronizada_100k ?? -1)
          : ordenarPor === "taxa"
            ? (b.taxa_obitos_100k ?? -1) - (a.taxa_obitos_100k ?? -1)
            : b.obitos - a.obitos,
      )
      .slice(0, 100);
  }, [municipios, busca, popMin, ordenarPor, sexo]);

  const topCausas = useMemo(() => {
    if (!causas) return null;
    return [...causas].sort((a, b) => b.obitos - a.obitos).slice(0, 15)
      .map((c) => ({ nome: c.causabas_3, obitos: c.obitos }));
  }, [causas]);

  const totalPeriodo = serie?.reduce((s, r) => s + r.obitos, 0);
  const totalAno = useMemo(
    () => serie?.filter((r) => r.mes.startsWith(String(ano))).reduce((s, r) => s + r.obitos, 0),
    [serie, ano],
  );

  function exportarCsv() {
    if (!ranking) return;
    const linhas = [
      "municipio;uf;obitos;populacao;taxa_bruta_100k;ic95_inf;ic95_sup;taxa_padronizada_100k",
      ...ranking.map((m) =>
        [m.municipio_nome, m.uf_sigla, m.obitos, m.populacao ?? "", m.taxa_obitos_100k ?? "",
         m.ic95_inf ?? "", m.ic95_sup ?? "", m.taxa_padronizada_100k ?? ""].join(";"),
      ),
    ].join("\n");
    const blob = new Blob(["﻿" + linhas], { type: "text/csv;charset=utf-8" });
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = `mortalidade_${uf}_${ano}_${capitulo}_${sexo}.csv`;
    a.click();
    URL.revokeObjectURL(a.href);
  }

  const capDesc = capitulo === "TOTAL"
    ? "Todas as causas"
    : `Capítulo ${capitulo} — ${capitulos.find((c) => c.capitulo === capitulo)?.descricao ?? ""}`;

  return (
    <div className="mx-auto max-w-7xl px-4 py-10 sm:px-6">
      <h1 className="font-serif text-3xl font-semibold tracking-tight text-ink-950">Painel de mortalidade</h1>
      <p className="mt-2 max-w-3xl text-ink-600">
        Série 2015–2024 (10 anos). Taxas padronizadas por idade e IC95% para
        comparação responsável entre municípios — os mesmos valores da API pública.
      </p>

      <div className="card mt-6 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <div>
          <label className="label" htmlFor="f-uf">Abrangência</label>
          <select id="f-uf" className="select" value={uf} onChange={(e) => setUf(e.target.value)}>
            <option value="Brasil">Brasil (todas as UFs)</option>
            {UFS.map((u) => <option key={u} value={u}>{u}</option>)}
          </select>
        </div>
        <div>
          <label className="label" htmlFor="f-ano">Ano de referência</label>
          <select id="f-ano" className="select" value={ano} onChange={(e) => setAno(Number(e.target.value))}>
            {[...ANOS].reverse().map((a) => (
              <option key={a} value={a}>
                {a}{a === 2024 ? " (preliminar)" : a < ANO_DETALHE ? " (grão reduzido)" : ""}
              </option>
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
          <select id="f-sexo" className="select" value={sexo} disabled={historico}
                  onChange={(e) => setSexo(e.target.value as Sexo)}>
            <option value="TOTAL">Ambos</option>
            <option value="M">Masculino</option>
            <option value="F">Feminino</option>
          </select>
          {historico && (
            <p className="mt-1 text-[11px] text-amber-700">
              Antes de {ANO_DETALHE}: apenas totais (sem recorte por sexo).
            </p>
          )}
        </div>
      </div>

      {erro && <div className="card mt-6 border-red-200 bg-red-50 text-sm text-red-800">Falha ao consultar a base: {erro}</div>}

      <div className="mt-6 grid gap-4 sm:grid-cols-3">
        <Kpi rotulo={`Óbitos em ${ano}`} valor={totalAno != null ? fmtInt(totalAno) : "…"} detalhe={capDesc} />
        <Kpi rotulo="Óbitos na série 2015–2024" valor={totalPeriodo != null ? fmtInt(totalPeriodo) : "…"} detalhe={uf === "Brasil" ? "Brasil" : uf} />
        <Kpi rotulo="Municípios com registro" valor={municipios ? fmtInt(municipios.length) : "…"} detalhe={`no recorte selecionado, ${ano}`} />
      </div>

      <div className="card mt-6">
        <h2 className="font-serif text-xl font-semibold text-ink-900">
          Evolução mensal — {uf === "Brasil" ? "Brasil" : uf}
        </h2>
        <p className="mt-1 text-sm text-ink-500">
          {capDesc}{sexo !== "TOTAL" ? ` · sexo ${sexo === "M" ? "masculino" : "feminino"}` : ""} · 2015–2024
        </p>
        <div className="mt-4">{serie ? <SerieLinha data={serie} /> : <Skeleton />}</div>
      </div>

      <div className="mt-6 grid gap-6 lg:grid-cols-2">
        <div className="card">
          <h2 className="font-serif text-xl font-semibold text-ink-900">Distribuição etária ({ano})</h2>
          {historico && <p className="mt-1 text-xs text-ink-500">No grão histórico, sempre todas as causas.</p>}
          <div className="mt-4">{faixaChart ? <Barras data={faixaChart} /> : <Skeleton altura={300} />}</div>
        </div>
        <div className="card">
          <h2 className="font-serif text-xl font-semibold text-ink-900">15 principais causas básicas ({ano})</h2>
          <p className="mt-1 text-xs text-ink-500">Categorias CID-10 (3 caracteres), independentes do filtro de capítulo/sexo.</p>
          <div className="mt-4">
            {topCausas ? <Barras data={topCausas} horizontal altura={360} /> : <Skeleton altura={360} />}
          </div>
        </div>
      </div>

      <div className="card mt-6">
        <div className="flex flex-wrap items-end justify-between gap-4">
          <div>
            <h2 className="font-serif text-xl font-semibold text-ink-900">Municípios ({ano})</h2>
            <p className="mt-1 text-sm text-ink-500">
              <b>Taxa padronizada</b> (ajustada por idade) é o indicador recomendado para comparar
              municípios; a bruta acompanha IC95%. Disponíveis quando sexo = Ambos.
            </p>
          </div>
          <button onClick={exportarCsv} className="btn-ghost" disabled={!ranking?.length}>⬇ Exportar CSV</button>
        </div>

        <div className="mt-4 grid gap-4 sm:grid-cols-3">
          <div>
            <label className="label" htmlFor="f-busca">Buscar município</label>
            <input id="f-busca" className="select" placeholder="ex.: Campinas" value={busca}
                   onChange={(e) => setBusca(e.target.value)} />
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
            <select id="f-ord" className="select" value={ordenarPor}
                    onChange={(e) => setOrdenarPor(e.target.value as typeof ordenarPor)}>
              <option value="taxa_pad">Taxa padronizada /100 mil</option>
              <option value="taxa">Taxa bruta /100 mil</option>
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
                  <th className="px-3 py-2 text-right">População</th>
                  <th className="px-3 py-2 text-right">Taxa bruta (IC95%)</th>
                  <th className="px-3 py-2 text-right">Taxa padronizada</th>
                </tr>
              </thead>
              <tbody>
                {ranking.map((m, i) => (
                  <tr key={m.municipio_cod} className="border-b border-ink-100 hover:bg-ink-50">
                    <td className="px-3 py-2 tabular-nums text-ink-400">{i + 1}</td>
                    <td className="px-3 py-2 font-medium text-ink-900">
                      {m.municipio_nome ?? m.municipio_cod}
                      {(m.populacao ?? 0) > 0 && (m.populacao ?? 0) < 10_000 && (
                        <span title="População pequena: taxas instáveis — observe o IC95%" className="ml-1 text-amber-600">⚠</span>
                      )}
                    </td>
                    <td className="px-3 py-2 text-ink-600">{m.uf_sigla}</td>
                    <td className="px-3 py-2 text-right tabular-nums">{fmtInt(m.obitos)}</td>
                    <td className="px-3 py-2 text-right tabular-nums text-ink-600">{fmtInt(m.populacao)}</td>
                    <td className="px-3 py-2 text-right tabular-nums text-ink-700">
                      {fmtDec(m.taxa_obitos_100k)}
                      {m.ic95_inf != null && (
                        <span className="text-xs text-ink-400"> ({fmtDec(m.ic95_inf)}–{fmtDec(m.ic95_sup)})</span>
                      )}
                    </td>
                    <td className="px-3 py-2 text-right font-semibold tabular-nums text-accent-800">
                      {fmtDec(m.taxa_padronizada_100k)}
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
        <p className="mt-3 text-xs text-ink-500">
          Taxa padronizada disponível apenas para todas as causas (método direto, padrão Brasil
          Censo 2022). ⚠ indica população &lt; 10 mil hab. Detalhes na{" "}
          <a className="text-accent-700 underline" href="/metodologia/">metodologia</a>.
        </p>
      </div>
    </div>
  );
}
