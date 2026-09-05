"use client";

import { Suspense, useCallback, useEffect, useMemo, useState } from "react";
import { useSearchParams } from "next/navigation";
import { Barras, SerieLinha } from "@/components/charts";
import { Kpi, Skeleton } from "@/components/kpi";
import { VerMais } from "@/components/ver-mais";
import {
  ANOS,
  ANO_PADRAO,
  PERIODO,
  ANO_DETALHE,
  ehPreliminar,
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
import { particionarMunicipios } from "@/lib/municipios";
import { casaMunicipio } from "@/lib/busca";
import { incompletosDe, notaCompletude, type ManifestoCompletude } from "@/lib/completude";

type Sexo = "TOTAL" | "M" | "F";

/**
 * O recorte vive na URL, e não só no estado do componente.
 *
 * Sem isto, `/painel/` era o endereço de qualquer análise: escolher UF, ano,
 * capítulo e ordenação não mudava o link, então não havia como mandar a mesma
 * tela para outra pessoa nem voltar a ela depois. Os nomes são curtos e fixos
 * porque viram endereço público — renomear um quebra links já compartilhados.
 *
 * Valor inválido não derruba a página: cai no padrão. Um link colado errado, ou
 * de uma versão anterior do site, abre o painel em vez de uma tela quebrada.
 */
const PARAM = { uf: "uf", ano: "ano", cap: "cap", sexo: "sexo", pop: "pop", ord: "ord", q: "q" } as const;

const POPULACOES_MIN = [0, 10_000, 50_000, 100_000, 500_000] as const;
const ORDENS = ["taxa_pad", "taxa", "obitos"] as const;
type Ordem = (typeof ORDENS)[number];

function PainelInner() {
  const params = useSearchParams();
  const [uf, setUf] = useState<string>(
    () => { const v = params.get(PARAM.uf); return v && (v === "Brasil" || (UFS as readonly string[]).includes(v)) ? v : "Brasil"; },
  );
  const periodo = PERIODO;
  const [ano, setAno] = useState<number>(
    () => { const v = Number(params.get(PARAM.ano)); return (ANOS as readonly number[]).includes(v) ? v : ANO_PADRAO; },
  );
  const [capitulo, setCapitulo] = useState<string>(() => params.get(PARAM.cap) ?? "TOTAL");
  const [sexo, setSexo] = useState<Sexo>(
    () => { const v = params.get(PARAM.sexo); return v === "M" || v === "F" ? v : "TOTAL"; },
  );
  const [capitulos, setCapitulos] = useState<CapituloCid[]>([]);

  const [serie, setSerie] = useState<{ mes: string; obitos: number }[] | null>(null);
  const [completude, setCompletude] = useState<ManifestoCompletude | null>(null);
  const [faixas, setFaixas] = useState<LinhaUfMes[] | null>(null);
  const [municipios, setMunicipios] = useState<LinhaMunicipio[] | null>(null);
  const [causas, setCausas] = useState<CausaAgregada[] | null>(null);
  const [erro, setErro] = useState<string | null>(null);

  const [busca, setBusca] = useState(() => params.get(PARAM.q) ?? "");
  // `Number(null)` é 0, e 0 ("sem mínimo") é uma opção VÁLIDA — validar só o
  // valor fazia todo painel recém-aberto nascer sem filtro de população e com
  // `?pop=0` na barra. Ausência do parâmetro tem de ser testada antes da
  // conversão. Pego na verificação em navegador, não no type-check.
  const [popMin, setPopMin] = useState(() => {
    const bruto = params.get(PARAM.pop);
    if (bruto == null) return 50_000;
    const v = Number(bruto);
    return (POPULACOES_MIN as readonly number[]).includes(v) ? v : 50_000;
  });
  const [ordenarPor, setOrdenarPor] = useState<Ordem>(
    () => { const v = params.get(PARAM.ord); return (ORDENS as readonly string[]).includes(v ?? "") ? (v as Ordem) : "taxa_pad"; },
  );
  const [linkCopiado, setLinkCopiado] = useState(false);

  const historico = ano < ANO_DETALHE; // grão reduzido: sexo/faixa só TOTAL

  /**
   * O endereço acompanha o recorte, e só o que difere do padrão entra nele —
   * um painel recém-aberto continua sendo `/painel/`, sem sujeira.
   *
   * `replaceState` e não `pushState`: cada tecla digitada na busca criaria uma
   * entrada no histórico, e o botão "voltar" passaria a desfazer letra por
   * letra em vez de sair da página.
   */
  const consulta = useMemo(() => {
    const p = new URLSearchParams();
    if (uf !== "Brasil") p.set(PARAM.uf, uf);
    if (ano !== ANO_PADRAO) p.set(PARAM.ano, String(ano));
    if (capitulo !== "TOTAL") p.set(PARAM.cap, capitulo);
    if (sexo !== "TOTAL") p.set(PARAM.sexo, sexo);
    if (popMin !== 50_000) p.set(PARAM.pop, String(popMin));
    if (ordenarPor !== "taxa_pad") p.set(PARAM.ord, ordenarPor);
    if (busca.trim()) p.set(PARAM.q, busca.trim());
    return p.toString();
  }, [uf, ano, capitulo, sexo, popMin, ordenarPor, busca]);

  useEffect(() => {
    if (typeof window === "undefined") return;
    window.history.replaceState(null, "", consulta ? `?${consulta}` : window.location.pathname);
    setLinkCopiado(false);
  }, [consulta]);

  const copiarLink = useCallback(async () => {
    if (typeof window === "undefined") return;
    const url = `${window.location.origin}${window.location.pathname}${consulta ? `?${consulta}` : ""}`;
    try {
      await navigator.clipboard.writeText(url);
      setLinkCopiado(true);
    } catch {
      // Clipboard bloqueado (contexto não seguro, permissão negada): a URL da
      // barra de endereço já é a análise, então o usuário copia dali. Silenciar
      // é melhor que um erro que não tem conserto do lado dele.
      setLinkCopiado(false);
    }
  }, [consulta]);

  useEffect(() => {
    sdata<ManifestoCompletude>("completude").then(setCompletude).catch(() => {});
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

  // Códigos agregados "UF0000" (óbito sem município identificado) não são
  // municípios: ficam fora da contagem, do ranking e do CSV, mas seus óbitos
  // continuam visíveis para o total não se perder.
  const particao = useMemo(
    () => (municipios ? particionarMunicipios(municipios) : null),
    [municipios],
  );

  const ranking = useMemo(() => {
    if (!particao) return null;
    return particao.identificados
      .filter((m) => (m.populacao ?? 0) >= popMin || sexo !== "TOTAL")
      // `casaMunicipio` e não `includes` minúsculo: "Penapolis" precisa
      // encontrar Penápolis, e o código do IBGE também. Ver `lib/busca.ts`.
      .filter((m) => casaMunicipio(busca, m.municipio_nome, m.municipio_cod))
      .sort((a, b) =>
        ordenarPor === "taxa_pad"
          ? (b.taxa_padronizada_100k ?? -1) - (a.taxa_padronizada_100k ?? -1)
          : ordenarPor === "taxa"
            ? (b.taxa_obitos_100k ?? -1) - (a.taxa_obitos_100k ?? -1)
            : b.obitos - a.obitos,
      )
      .slice(0, 100);
  }, [particao, busca, popMin, ordenarPor, sexo]);

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
        Série {periodo} ({ANOS.length} anos). Taxas padronizadas por idade e IC95% para
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
                {a}{ehPreliminar(a) ? " (preliminar)" : a < ANO_DETALHE ? " (grão reduzido)" : ""}
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
        <Kpi rotulo={`Óbitos na série ${periodo}`} valor={totalPeriodo != null ? fmtInt(totalPeriodo) : "…"} detalhe={uf === "Brasil" ? "Brasil" : uf} />
        <Kpi
          rotulo="Municípios com registro"
          valor={particao ? fmtInt(particao.identificados.length) : "…"}
          detalhe={
            particao && particao.obitosNaoIdentificados > 0
              ? `no recorte selecionado, ${ano} · ${fmtInt(particao.obitosNaoIdentificados)} óbitos sem município identificado`
              : `no recorte selecionado, ${ano}`
          }
        />
      </div>

      <div className="card mt-6">
        <h2 className="font-serif text-xl font-semibold text-ink-900">
          Evolução mensal — {uf === "Brasil" ? "Brasil" : uf}
        </h2>
        <p className="mt-1 text-sm text-ink-500">
          {capDesc}{sexo !== "TOTAL" ? ` · sexo ${sexo === "M" ? "masculino" : "feminino"}` : ""} · {periodo}
        </p>
        <div className="mt-4">
          {serie ? <SerieLinha data={serie} incompletos={incompletosDe(completude, uf)} titulo={`Evolução mensal — ${uf === "Brasil" ? "Brasil" : uf}`} /> : <Skeleton />}
        </div>
        {serie && notaCompletude(incompletosDe(completude, uf)) && (
          <p className="mt-3 border-t border-ink-200 pt-3 text-xs text-ink-600">
            <span className="font-medium text-ink-700">Trecho tracejado:</span>{" "}
            {notaCompletude(incompletosDe(completude, uf))}
          </p>
        )}
      </div>

      <div className="mt-6 grid gap-6 lg:grid-cols-2">
        <div className="card">
          <h2 className="font-serif text-xl font-semibold text-ink-900">Distribuição etária ({ano})</h2>
          {historico && <p className="mt-1 text-xs text-ink-500">No grão histórico, sempre todas as causas.</p>}
          <div className="mt-4">{faixaChart ? <Barras data={faixaChart} titulo={`Distribuição etária (${ano})`} /> : <Skeleton altura={300} />}</div>
        </div>
        <div className="card">
          <h2 className="font-serif text-xl font-semibold text-ink-900">15 principais causas básicas ({ano})</h2>
          <p className="mt-1 text-xs text-ink-500">Categorias CID-10 (3 caracteres), independentes do filtro de capítulo/sexo.</p>
          <div className="mt-4">
            {topCausas ? <Barras data={topCausas} horizontal altura={360} titulo={`15 principais causas básicas (${ano})`} /> : <Skeleton altura={360} />}
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
          <div className="flex flex-wrap gap-2 no-print">
            <button onClick={copiarLink} className="btn-ghost" title="Copia o endereço com o recorte atual">
              {linkCopiado ? "✓ Link copiado" : "🔗 Copiar link desta análise"}
            </button>
            <button onClick={exportarCsv} className="btn-ghost" disabled={!ranking?.length}>⬇ Exportar CSV</button>
          </div>
        </div>

        <div className="mt-4 grid gap-4 sm:grid-cols-3">
          <div>
            <label className="label" htmlFor="f-busca">Buscar município</label>
            <input id="f-busca" className="select" placeholder="nome ou código IBGE — ex.: Campinas, 350950"
                   value={busca} onChange={(e) => setBusca(e.target.value)} />
            <p className="mt-1 text-[11px] text-ink-500">Acento e maiúscula são opcionais.</p>
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
            <VerMais total={ranking.length} rotulo="municípios">
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
                    <td className="px-3 py-2 tabular-nums text-ink-500">{i + 1}</td>
                    <td className="px-3 py-2 font-medium text-ink-900">
                      {/* O ano viaja junto. Sem ele o boletim abria no mais
                          recente da série — em 2025, preliminar — enquanto o
                          painel de origem estava em 2024: o visitante trocava
                          de ano sem pedir e sem ser avisado. */}
                      <a href={`/boletim/?m=${m.municipio_cod}&ano=${ano}`}
                         className="hover:text-accent-700 hover:underline"
                         title={`Abrir boletim do município em ${ano}`}>
                        {m.municipio_nome ?? m.municipio_cod}
                      </a>
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
                        <span className="text-xs text-ink-500"> ({fmtDec(m.ic95_inf)}–{fmtDec(m.ic95_sup)})</span>
                      )}
                    </td>
                    <td className="px-3 py-2 text-right font-semibold tabular-nums text-accent-800">
                      {fmtDec(m.taxa_padronizada_100k)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            </VerMais>
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

export function PainelCliente() {
  // `useSearchParams` exige limite de Suspense na exportação estática — mesmo
  // arranjo já usado pelo boletim.
  return (
    <Suspense fallback={<div className="mx-auto max-w-7xl px-4 py-10 sm:px-6"><Skeleton altura={400} /></div>}>
      <PainelInner />
    </Suspense>
  );
}
