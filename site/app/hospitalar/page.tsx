"use client";

import { useEffect, useMemo, useState } from "react";
import { Kpi, Skeleton } from "@/components/kpi";
import {
  UFS, fmtDec, fmtInt, rest,
  type ForecastDemandaHospital, type HsmrHospital, type InternacaoHospital,
  type LeitosMunicipio, type LosHospital,
} from "@/lib/api";

/** minúsculas + sem acentos, para busca tolerante ("Penapolis" casa com "Penápolis"). */
function normalizar(s: string): string {
  return s.normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase();
}

const ANOS_HOSP = [2024, 2023, 2022] as const;

export default function Hospitalar() {
  const [uf, setUf] = useState("Brasil");
  const [ano, setAno] = useState<number>(2024);
  const ufF = useMemo<Record<string, string>>(
    () => (uf === "Brasil" ? {} as Record<string, string> : { uf_sigla: `eq.${uf}` }),
    [uf],
  );

  // ── HSMR — mortalidade hospitalar ajustada por case-mix ──────────────────
  const [hsmr, setHsmr] = useState<HsmrHospital[] | null>(null);
  const [hsmrOrd, setHsmrOrd] = useState<"hsmr" | "internacoes" | "obitos_observados">("hsmr");
  useEffect(() => {
    setHsmr(null);
    rest<HsmrHospital>("mart_hsmr_hospital", {
      select: "cnes,municipio_cod,municipio_nome,uf_sigla,ano,internacoes,obitos_observados,obitos_esperados,hsmr,estavel,hsmr_ic95_inf,hsmr_ic95_sup,hsmr_pvalor,hsmr_q_valor,significancia",
      ano: `eq.${ano}`, order: `${hsmrOrd}.desc.nullslast`, limit: "60", ...ufF,
    }).then(setHsmr).catch(() => setHsmr([]));
  }, [ufF, hsmrOrd, ano]);

  // Agregados do RECORTE COMPLETO (não da lista top-60 exibida, que é enviesada para
  // os piores hospitais quando ordenada por HSMR) — via agregação no servidor.
  const [hsmrAgg, setHsmrAgg] = useState<{ obs: number; esp: number; n: number } | null>(null);
  const [instaveisTotal, setInstaveisTotal] = useState<number | null>(null);
  useEffect(() => {
    setHsmrAgg(null); setInstaveisTotal(null);
    rest<{ obitos_observados: number; obitos_esperados: number; n: number }>("mart_hsmr_hospital", {
      select: "obitos_observados:obitos_observados.sum(),obitos_esperados:obitos_esperados.sum(),n:cnes.count()",
      ano: `eq.${ano}`, ...ufF,
    }).then((r) => {
      const row = r[0];
      if (row) setHsmrAgg({ obs: row.obitos_observados, esp: row.obitos_esperados, n: row.n });
    }).catch(() => setHsmrAgg(null));
    rest<{ cnes: string }>("mart_hsmr_hospital", {
      select: "cnes", ano: `eq.${ano}`, estavel: "eq.false", ...ufF,
    }).then((r) => setInstaveisTotal(r.length)).catch(() => setInstaveisTotal(null));
  }, [ufF, ano]);
  const hsmrNacional = hsmrAgg && hsmrAgg.esp ? hsmrAgg.obs / hsmrAgg.esp : null;

  // ── Leitos (CNES-LT) — a camada de OFERTA ────────────────────────────────
  // Série anual completa do recorte; agregação é feita no cliente porque o
  // volume é pequeno (5,5 mil municípios × 10 anos) e permite montar a série
  // temporal e o recorte por UF sem ida extra ao servidor.
  const [leitos, setLeitos] = useState<LeitosMunicipio[] | null>(null);
  useEffect(() => {
    setLeitos(null);
    rest<LeitosMunicipio>("mart_leitos_municipio", {
      select: "municipio_cod,municipio_nome,uf_sigla,ano,leitos_total,leitos_sus,leitos_uti,leitos_uti_sus,populacao,leitos_sus_por_mil,pct_leitos_sus",
      ...ufF,
    }).then(setLeitos).catch(() => setLeitos([]));
  }, [ufF]);

  const serieLeitos = useMemo(() => {
    if (!leitos?.length) return null;
    const porAno = new Map<number, { leitos: number; sus: number; uti: number; pop: number; semLeito: number; n: number }>();
    for (const l of leitos) {
      const a = porAno.get(l.ano) ?? { leitos: 0, sus: 0, uti: 0, pop: 0, semLeito: 0, n: 0 };
      a.leitos += l.leitos_total; a.sus += l.leitos_sus; a.uti += l.leitos_uti;
      a.pop += l.populacao ?? 0; a.n += 1;
      if (l.leitos_total === 0) a.semLeito += 1;
      porAno.set(l.ano, a);
    }
    return [...porAno.entries()].sort((x, y) => x[0] - y[0]).map(([ano, v]) => ({
      ano,
      ...v,
      susPorMil: v.pop ? (v.sus / v.pop) * 1000 : null,
      utiPor100k: v.pop ? (v.uti / v.pop) * 100_000 : null,
      pctSemLeito: v.n ? (v.semLeito / v.n) * 100 : null,
    }));
  }, [leitos]);

  const ultimoLeitos = serieLeitos?.[serieLeitos.length - 1] ?? null;
  const primeiroLeitos = serieLeitos?.[0] ?? null;

  // ── LOS esperado — mediana do hospital vs. mediana nacional ──────────────
  const [los, setLos] = useState<LosHospital[] | null>(null);
  useEffect(() => {
    setLos(null);
    rest<LosHospital>("mart_los_hospital", {
      select: "cnes,municipio_cod,municipio_nome,uf_sigla,ano,cid3,capitulo_cid,internacoes,mediana_hospital_dias,mediana_nacional_dias,desvio_dias",
      ano: `eq.${ano}`, internacoes: "gte.30", order: "desvio_dias.desc.nullslast", limit: "40", ...ufF,
    }).then(setLos).catch(() => setLos([]));
  }, [ufF, ano]);

  // ── Forecast de demanda — busca por hospital ──────────────────────────────
  const [hospBusca, setHospBusca] = useState("");
  const [hospitaisTodos, setHospitaisTodos] = useState<InternacaoHospital[]>([]);
  const [hospSel, setHospSel] = useState<{ cnes: string; nome: string } | null>(null);
  const [forecast, setForecast] = useState<ForecastDemandaHospital[] | null>(null);

  // Carrega a lista completa uma vez; filtro é client-side (evita ILIKE sensível a
  // acento no servidor — "Penapolis" não batia com "Penápolis").
  useEffect(() => {
    rest<InternacaoHospital>("mart_internacoes_hospital", {
      select: "cnes,municipio_nome,uf_sigla,internacoes", ano: "eq.2024", order: "internacoes.desc",
    }).then(setHospitaisTodos).catch(() => setHospitaisTodos([]));
  }, []);

  const hospOpcoes = useMemo(() => {
    const q = normalizar(hospBusca.trim());
    if (q.length < 3) return [];
    return hospitaisTodos.filter((h) => normalizar(h.municipio_nome ?? "").includes(q)).slice(0, 8);
  }, [hospitaisTodos, hospBusca]);

  useEffect(() => {
    if (!hospSel) { setForecast(null); return; }
    rest<ForecastDemandaHospital>("mart_forecast_demanda_hospital", {
      select: "cnes,municipio_cod,municipio_nome,uf_sigla,ano_mes_previsto,internacoes_previstas,ic_inferior,ic_superior,n_meses_historico,confianca",
      cnes: `eq.${hospSel.cnes}`, order: "ano_mes_previsto",
    }).then(setForecast).catch(() => setForecast([]));
  }, [hospSel]);

  return (
    <div className="mx-auto max-w-7xl px-4 py-10 sm:px-6">
      <h1 className="font-serif text-3xl font-semibold tracking-tight text-ink-950">Visão hospitalar</h1>
      <p className="mt-2 max-w-3xl text-ink-600">
        Inteligência analítica por estabelecimento (CNES): mortalidade ajustada por case-mix (HSMR),
        tempo de permanência esperado por diagnóstico e projeção de demanda — a partir do SIH/AIH.
      </p>

      <div className="mt-4 max-w-3xl rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900">
        <strong>O que esta página não faz, e por quê:</strong> não estimamos risco de readmissão ou
        reinternação por paciente. A AIH pública não tem identificador estável de paciente (removido por
        LGPD) — ligar duas internações à mesma pessoa exigiria dado que não é público. Preferimos declarar
        essa limitação a fingir uma precisão que os dados abertos não sustentam. Detalhes na{" "}
        <a className="underline" href="/metodologia/">metodologia</a>.
      </div>

      <div className="card mt-6 grid gap-4 sm:max-w-md sm:grid-cols-2">
        <div>
          <label className="label" htmlFor="h-uf">Abrangência</label>
          <select id="h-uf" className="select" value={uf} onChange={(e) => setUf(e.target.value)}>
            <option value="Brasil">Brasil (todas as UFs)</option>
            {UFS.map((u) => <option key={u} value={u}>{u}</option>)}
          </select>
        </div>
        <div>
          <label className="label" htmlFor="h-ano">Ano (HSMR e permanência)</label>
          <select id="h-ano" className="select" value={ano} onChange={(e) => setAno(Number(e.target.value))}>
            {ANOS_HOSP.map((a) => <option key={a} value={a}>{a}{a === 2024 ? " (preliminar)" : ""}</option>)}
          </select>
        </div>
      </div>
      <p className="mt-2 text-xs text-ink-500">
        A projeção de demanda (mais abaixo) sempre usa o histórico mensal completo disponível,
        independente do ano selecionado aqui.
      </p>

      {/* Leitos — camada de oferta */}
      <div className="card mt-6">
        <h2 className="font-serif text-xl font-semibold text-ink-900">
          Leitos hospitalares: a capacidade instalada
        </h2>
        <p className="mt-1 max-w-3xl text-sm text-ink-500">
          Todo o resto desta página mede <strong>uso</strong> (quem internou, quanto tempo ficou, quem
          morreu). Leito é a medida de <strong>oferta</strong> — e sem ela não dá para saber se um
          resultado ruim reflete assistência pior ou simplesmente falta de estrutura. Fonte: CNES grupo
          LT (FTP do DataSUS), competência de dezembro de cada ano.
        </p>

        {serieLeitos && ultimoLeitos ? (
          <>
            <div className="mt-4 grid gap-4 sm:grid-cols-4">
              <Kpi
                rotulo={`Leitos SUS /mil hab. (${ultimoLeitos.ano})`}
                valor={ultimoLeitos.susPorMil != null ? fmtDec(ultimoLeitos.susPorMil) : "—"}
                detalhe={`${fmtInt(ultimoLeitos.sus)} leitos SUS de ${fmtInt(ultimoLeitos.leitos)} totais`}
              />
              <Kpi
                rotulo={`Leitos de UTI /100 mil hab. (${ultimoLeitos.ano})`}
                valor={ultimoLeitos.utiPor100k != null ? fmtDec(ultimoLeitos.utiPor100k) : "—"}
                detalhe={`${fmtInt(ultimoLeitos.uti)} leitos de terapia intensiva`}
              />
              <Kpi
                rotulo="Municípios sem nenhum leito"
                valor={ultimoLeitos.pctSemLeito != null ? `${fmtDec(ultimoLeitos.pctSemLeito, 1)}%` : "—"}
                detalhe={`${fmtInt(ultimoLeitos.semLeito)} de ${fmtInt(ultimoLeitos.n)} no recorte`}
              />
              <Kpi
                rotulo="Parcela SUS do total"
                valor={ultimoLeitos.leitos ? `${fmtDec((ultimoLeitos.sus / ultimoLeitos.leitos) * 100, 1)}%` : "—"}
                detalhe={
                  primeiroLeitos && primeiroLeitos.leitos
                    ? `era ${fmtDec((primeiroLeitos.sus / primeiroLeitos.leitos) * 100, 1)}% em ${primeiroLeitos.ano}`
                    : undefined
                }
              />
            </div>

            <div className="mt-5 overflow-x-auto">
              <table className="w-full min-w-[640px] text-sm">
                <thead>
                  <tr className="border-b border-ink-200 text-left text-xs uppercase tracking-wide text-ink-500">
                    <th className="py-2 pr-3">Ano</th>
                    <th className="py-2 pr-3 text-right">Leitos totais</th>
                    <th className="py-2 pr-3 text-right">Leitos SUS</th>
                    <th className="py-2 pr-3 text-right">% SUS</th>
                    <th className="py-2 pr-3 text-right">UTI</th>
                    <th className="py-2 pr-3 text-right">SUS /mil hab.</th>
                    <th className="py-2 text-right">Municípios sem leito</th>
                  </tr>
                </thead>
                <tbody>
                  {serieLeitos.map((r) => (
                    <tr key={r.ano} className="border-b border-ink-100 tabular-nums">
                      <td className="py-1.5 pr-3 font-medium text-ink-900">{r.ano}</td>
                      <td className="py-1.5 pr-3 text-right">{fmtInt(r.leitos)}</td>
                      <td className="py-1.5 pr-3 text-right">{fmtInt(r.sus)}</td>
                      <td className="py-1.5 pr-3 text-right">{r.leitos ? fmtDec((r.sus / r.leitos) * 100, 1) : "—"}</td>
                      <td className="py-1.5 pr-3 text-right">{fmtInt(r.uti)}</td>
                      <td className="py-1.5 pr-3 text-right">{r.susPorMil != null ? fmtDec(r.susPorMil) : "—"}</td>
                      <td className="py-1.5 text-right">{fmtInt(r.semLeito)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            <div className="mt-4 max-w-3xl rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900">
              <strong>Cuidado ao ler a série de UTI entre 2020 e 2022.</strong> No Brasil, os leitos
              classificados como "complementares" saltam de 59,8 mil (2019) para 99,4 mil (2021) e caem
              para 76,9 mil em 2022 — e a fração deles registrada sob códigos de UTI vai de 77% para 51%
              e volta a 79%. Isso indica que muito leito emergencial da pandemia foi cadastrado fora dos
              códigos de UTI e depois desmobilizado. O salto de UTI em 2022 é, em parte,{" "}
              <em>reclassificação</em>, não só expansão real. A tendência de 10 anos (40,4 mil → 63,8 mil)
              é consistente; a variação ano a ano nessa janela, não.
            </div>

            <p className="mt-3 max-w-3xl text-xs text-ink-500">
              O CNES é um cadastro fotografado mensalmente, não um fluxo de eventos: cada linha é um{" "}
              <strong>snapshot</strong> de dezembro, nunca soma de competências (somar 12 meses
              multiplicaria a capacidade por 12). UTI identificada por lista explícita de códigos da
              tabela oficial de domínios — o código 84, no meio da faixa de UTI, é "acolhimento noturno"
              e fica de fora. Reprodutível em <code>scripts/pipeline_cnes_leitos.py</code>; ver{" "}
              <a className="text-accent-700 underline" href="/metodologia/">metodologia</a>.
            </p>
          </>
        ) : (
          <Skeleton altura={320} />
        )}
      </div>

      {/* HSMR */}
      <div className="card mt-6 overflow-x-auto">
        <div className="flex flex-wrap items-end justify-between gap-4">
          <div>
            <h2 className="font-serif text-xl font-semibold text-ink-900">
              Mortalidade hospitalar ajustada (HSMR) — {uf === "Brasil" ? "Brasil" : uf}, {ano}
            </h2>
            <p className="mt-1 max-w-2xl text-sm text-ink-500">
              Razão entre óbitos observados e óbitos <strong>esperados</strong>, dado o perfil de idade e
              diagnóstico de cada hospital (padronização indireta). HSMR &gt; 1 = mortalidade acima do
              esperado para aquele case-mix; HSMR &lt; 1 = abaixo. Não é um veredito de qualidade —
              é um ponto de partida para investigação.
            </p>
          </div>
          <div>
            <label className="label" htmlFor="h-ord">Ordenar por</label>
            <select id="h-ord" className="select" value={hsmrOrd} onChange={(e) => setHsmrOrd(e.target.value as typeof hsmrOrd)}>
              <option value="hsmr">HSMR (maior primeiro)</option>
              <option value="internacoes">Internações</option>
              <option value="obitos_observados">Óbitos observados</option>
            </select>
          </div>
        </div>

        {hsmrNacional != null && (
          <div className="mt-4 grid gap-4 sm:grid-cols-3">
            <Kpi rotulo="HSMR agregado (todos os hospitais do recorte)" valor={fmtDec(hsmrNacional, 2)}
                 detalhe={`observado / esperado, somado — ${hsmrAgg ? fmtInt(hsmrAgg.n) : "…"} hospitais`} />
            <Kpi rotulo="Instáveis no recorte (óbitos esp. &lt; 5)" valor={instaveisTotal != null ? fmtInt(instaveisTotal) : "…"}
                 detalhe="sinalizados, não ocultados — de todos os hospitais, não só a lista abaixo" />
            <Kpi rotulo="Exibidos na tabela" valor={hsmr ? fmtInt(hsmr.length) : "…"} detalhe="top 60 do critério de ordenação escolhido" />
          </div>
        )}

        <div className="mt-4">
          {hsmr ? (
            hsmr.length === 0 ? (
              <p className="text-sm text-ink-500">
                Sem dados publicados ainda para este recorte — o cálculo de HSMR está em processamento.
              </p>
            ) : (
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b-2 border-ink-200 text-left text-xs uppercase tracking-wide text-ink-500">
                    <th className="px-3 py-2">#</th><th className="px-3 py-2">CNES</th><th className="px-3 py-2">Município</th><th className="px-3 py-2">UF</th>
                    <th className="px-3 py-2 text-right">Internações</th><th className="px-3 py-2 text-right">Óbitos obs.</th>
                    <th className="px-3 py-2 text-right">Óbitos esp.</th><th className="px-3 py-2 text-right">HSMR (IC95%)</th>
                  </tr>
                </thead>
                <tbody>
                  {hsmr.map((h, i) => (
                    <tr key={h.cnes} className="border-b border-ink-100 hover:bg-ink-50">
                      <td className="px-3 py-2 tabular-nums text-ink-400">{i + 1}</td>
                      <td className="px-3 py-2 tabular-nums text-ink-500">{h.cnes}</td>
                      <td className="px-3 py-2 font-medium text-ink-900">{h.municipio_nome ?? h.municipio_cod}</td>
                      <td className="px-3 py-2 text-ink-600">{h.uf_sigla}</td>
                      <td className="px-3 py-2 text-right tabular-nums">{fmtInt(h.internacoes)}</td>
                      <td className="px-3 py-2 text-right tabular-nums text-ink-600">{fmtInt(h.obitos_observados)}</td>
                      <td className="px-3 py-2 text-right tabular-nums text-ink-600">{fmtDec(h.obitos_esperados, 1)}</td>
                      <td className="px-3 py-2 text-right tabular-nums">
                        <span className={
                          h.significancia === "acima" ? "font-semibold text-red-700"
                          : h.significancia === "abaixo" ? "font-semibold text-accent-800"
                          : "font-semibold text-ink-500"
                        }>
                          {fmtDec(h.hsmr, 2)}
                        </span>
                        {h.hsmr_ic95_inf != null && h.hsmr_ic95_sup != null && (
                          <span className="ml-1 whitespace-nowrap text-xs text-ink-400">
                            [{fmtDec(h.hsmr_ic95_inf, 2)}–{fmtDec(h.hsmr_ic95_sup, 2)}]
                          </span>
                        )}
                        {h.significancia === "esperado" && (
                          <span title={`Não difere do esperado após correção para múltiplas comparações (q=${fmtDec(h.hsmr_q_valor, 3)})`}
                                className="ml-1 text-ink-400">≈</span>
                        )}
                        {h.significancia === "indeterminado" && (
                          <span title="Óbitos esperados = 0: não é possível calcular intervalo" className="ml-1 text-amber-600">?</span>
                        )}
                        {(h.significancia === "acima" || h.significancia === "abaixo") && h.hsmr_q_valor != null && (
                          <span title={`q-valor (FDR) = ${fmtDec(h.hsmr_q_valor, 3)}`} className="ml-1 cursor-help text-ink-300">*</span>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )
          ) : <Skeleton altura={320} />}
        </div>
        <div className="mt-3 max-w-3xl space-y-2 text-xs text-ink-500">
          <p>
            Entre colchetes, o <strong>IC95% (gamma/Poisson exato)</strong> — o mesmo método usado nas
            taxas brutas de mortalidade do projeto. A classificação (cor e <span className="text-ink-400">≈</span>)
            usa o <strong>q-valor</strong>, não o IC bruto: com ~4.600 hospitais testados por ano,
            testar cada um a 5% sem correção geraria falsos positivos só por acaso. Corrigimos com{" "}
            <strong>Benjamini-Hochberg</strong> (por ano); passe o mouse no <span className="text-ink-300">*</span>{" "}
            para ver o q-valor. Isso remove 282 de 10.046 hospitais antes classificados como
            significativos (2,8%) — a maior parte do sinal é real, mas nem todo. <span className="text-amber-600">?</span>{" "}
            indica óbitos esperados = 0, onde não há teste possível. Padronização indireta por faixa
            etária × capítulo CID-10, taxas de referência nacionais; mínimo de 12 internações/ano.
          </p>
          <p className="rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-amber-900">
            <strong>Viés conhecido, contra hospitais grandes:</strong> o ajuste por capítulo CID é
            grosseiro — dentro de um mesmo capítulo cabem casos leves e casos graves. Hospitais
            terciários concentram os graves e, por isso, tendem sistematicamente a HSMR maior.
            Nos dados de 2024, os hospitais classificados “acima do esperado” têm mediana de{" "}
            <strong>5.324 internações</strong> contra <strong>1.098</strong> dos “abaixo” — quase 5×
            maiores. Isto é <em>case-mix residual</em>, não necessariamente pior assistência: use o
            HSMR para levantar hipóteses, nunca para ranquear.
          </p>
        </div>
      </div>

      {/* LOS esperado */}
      <div className="card mt-6 overflow-x-auto">
        <h2 className="font-serif text-xl font-semibold text-ink-900">
          Tempo de permanência: hospital vs. esperado — {uf === "Brasil" ? "Brasil" : uf}, {ano}
        </h2>
        <p className="mt-1 max-w-2xl text-sm text-ink-500">
          Mediana de dias de internação do hospital para um diagnóstico (CID-3), comparada à mediana
          nacional do mesmo diagnóstico. Valores positivos = hospital interna por mais tempo que a
          mediana nacional para aquela condição. Mediana aproximada por histograma de faixas de dias.
        </p>
        <div className="mt-4">
          {los ? (
            los.length === 0 ? (
              <p className="text-sm text-ink-500">
                Sem dados publicados ainda para este recorte — o cálculo de LOS está em processamento.
              </p>
            ) : (
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b-2 border-ink-200 text-left text-xs uppercase tracking-wide text-ink-500">
                    <th className="px-3 py-2">Hospital</th><th className="px-3 py-2">UF</th><th className="px-3 py-2">CID-3</th>
                    <th className="px-3 py-2">Cap.</th><th className="px-3 py-2 text-right">Internações</th>
                    <th className="px-3 py-2 text-right">Mediana hospital</th><th className="px-3 py-2 text-right">Mediana nacional</th>
                    <th className="px-3 py-2 text-right">Desvio</th>
                  </tr>
                </thead>
                <tbody>
                  {los.map((l, i) => (
                    <tr key={`${l.cnes}-${l.cid3}-${i}`} className="border-b border-ink-100 hover:bg-ink-50">
                      <td className="px-3 py-2 font-medium text-ink-900">{l.municipio_nome ?? l.municipio_cod}</td>
                      <td className="px-3 py-2 text-ink-600">{l.uf_sigla}</td>
                      <td className="px-3 py-2 tabular-nums text-ink-500">{l.cid3}</td>
                      <td className="px-3 py-2 text-ink-500">{l.capitulo_cid}</td>
                      <td className="px-3 py-2 text-right tabular-nums">{fmtInt(l.internacoes)}</td>
                      <td className="px-3 py-2 text-right tabular-nums">{fmtDec(l.mediana_hospital_dias, 1)}d</td>
                      <td className="px-3 py-2 text-right tabular-nums text-ink-500">{fmtDec(l.mediana_nacional_dias, 1)}d</td>
                      <td className="px-3 py-2 text-right font-semibold tabular-nums text-accent-800">
                        {l.desvio_dias != null && l.desvio_dias > 0 ? "+" : ""}{fmtDec(l.desvio_dias, 1)}d
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )
          ) : <Skeleton altura={300} />}
        </div>
        <p className="mt-2 text-xs text-ink-400">
          Mostrando os maiores desvios positivos (permanência mais longa que o esperado) no recorte, com
          ≥ 30 internações do hospital para o diagnóstico.
        </p>
      </div>

      {/* Forecast de demanda */}
      <div className="card mt-6">
        <h2 className="font-serif text-xl font-semibold text-ink-900">Projeção de demanda por hospital</h2>
        <p className="mt-1 max-w-2xl text-sm text-ink-500">
          Tendência linear sobre a série mensal de internações do hospital — mesmo método usado no excesso
          de mortalidade da plataforma. Com menos de 24 meses de histórico, a confiança é marcada como
          <strong> baixa</strong>: a tendência ainda é instável.
        </p>
        <div className="mt-4 max-w-md">
          <label className="label" htmlFor="h-busca">Buscar hospital por município</label>
          <input id="h-busca" className="select" placeholder="ex.: Penápolis" value={hospBusca}
                 onChange={(e) => { setHospBusca(e.target.value); setHospSel(null); }} />
          {hospOpcoes.length > 0 && !hospSel && (
            <div className="mt-1 rounded-lg border border-ink-200 bg-white shadow-sm">
              {hospOpcoes.map((o) => (
                <button key={o.cnes} type="button"
                        onClick={() => { setHospSel({ cnes: o.cnes, nome: `${o.municipio_nome} · CNES ${o.cnes}` }); setHospBusca(o.municipio_nome ?? ""); }}
                        className="block w-full px-3 py-2 text-left text-sm hover:bg-ink-50">
                  CNES {o.cnes} <span className="text-ink-400">· {o.municipio_nome} · {o.uf_sigla} · {fmtInt(o.internacoes)} internações/2024</span>
                </button>
              ))}
            </div>
          )}
        </div>
        {hospSel && (
          <div className="mt-4">
            <p className="text-sm text-ink-600">Projeção para <strong>{hospSel.nome}</strong>:</p>
            {forecast ? (
              forecast.length === 0 ? (
                <p className="mt-2 text-sm text-ink-500">
                  Sem histórico mensal suficiente para projetar este hospital (mínimo de 6 meses).
                </p>
              ) : (
                <table className="mt-2 w-full text-sm">
                  <thead>
                    <tr className="border-b-2 border-ink-200 text-left text-xs uppercase tracking-wide text-ink-500">
                      <th className="px-3 py-2">Mês previsto</th><th className="px-3 py-2 text-right">Internações previstas</th>
                      <th className="px-3 py-2 text-right">Faixa (IC aprox.)</th><th className="px-3 py-2 text-right">Confiança</th>
                    </tr>
                  </thead>
                  <tbody>
                    {forecast.map((f) => (
                      <tr key={f.ano_mes_previsto} className="border-b border-ink-100">
                        <td className="px-3 py-2 font-medium text-ink-900">{f.ano_mes_previsto}</td>
                        <td className="px-3 py-2 text-right tabular-nums">{fmtDec(f.internacoes_previstas, 0)}</td>
                        <td className="px-3 py-2 text-right tabular-nums text-ink-500">{fmtDec(f.ic_inferior, 0)}–{fmtDec(f.ic_superior, 0)}</td>
                        <td className="px-3 py-2 text-right">
                          <span className={f.confianca === "baixa" ? "text-amber-700" : "text-accent-800"}>
                            {f.confianca} <span className="text-ink-400">({f.n_meses_historico}m)</span>
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )
            ) : <Skeleton altura={140} />}
          </div>
        )}
      </div>

      <p className="mt-4 text-xs text-ink-500">
        Fonte: SIH/DataSUS (AIH aprovadas). HSMR: padronização indireta por faixa etária × capítulo CID-10,
        taxas de referência nacionais. LOS: mediana aproximada por histograma de faixas de dias. Forecast:
        tendência linear sobre a série mensal observada, com faixa de incerteza indicativa (não é IC de
        predição formal). Cobre apenas a rede SUS. Ver <a className="text-accent-700 underline" href="/metodologia/">metodologia</a>.
      </p>
    </div>
  );
}
