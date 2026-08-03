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
  // Ordena pela mesma régua que é exibida (hsmr_estrato), não pelo HSMR bruto:
  // ordenar por uma coluna e mostrar outra colocaria no topo hospitais que não
  // são os maiores da lista exibida.
  const [hsmrOrd, setHsmrOrd] = useState<"hsmr_estrato" | "internacoes" | "obitos_observados">("hsmr_estrato");
  useEffect(() => {
    setHsmr(null);
    rest<HsmrHospital>("mart_hsmr_hospital", {
      select: "cnes,municipio_cod,municipio_nome,uf_sigla,ano,internacoes,obitos_observados,obitos_esperados,hsmr,estavel,hsmr_ic95_inf,hsmr_ic95_sup,hsmr_pvalor,hsmr_q_valor,significancia,hsmr_estrato,estrato,tem_uti,leitos_total,leitos_uti",
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
      select: "municipio_cod,municipio_nome,uf_sigla,ano,leitos_total,leitos_sus,leitos_uti,leitos_uti_sus,leitos_cirurgico,leitos_clinico,leitos_obstetrico,leitos_pediatrico,leitos_complementar,leitos_outras_especialidades,leitos_hospital_dia,populacao,leitos_sus_por_mil,pct_leitos_sus",
      ...ufF,
    }).then(setLeitos).catch(() => setLeitos([]));
  }, [ufF]);

  const serieLeitos = useMemo(() => {
    if (!leitos?.length) return null;
    const porAno = new Map<number, {
      leitos: number; sus: number; uti: number; pop: number; semLeito: number; n: number;
      cirurgico: number; clinico: number; obstetrico: number; pediatrico: number;
      complementar: number; outras: number; hospitalDia: number;
    }>();
    for (const l of leitos) {
      const a = porAno.get(l.ano) ?? {
        leitos: 0, sus: 0, uti: 0, pop: 0, semLeito: 0, n: 0,
        cirurgico: 0, clinico: 0, obstetrico: 0, pediatrico: 0,
        complementar: 0, outras: 0, hospitalDia: 0,
      };
      a.leitos += l.leitos_total; a.sus += l.leitos_sus; a.uti += l.leitos_uti;
      a.pop += l.populacao ?? 0; a.n += 1;
      a.cirurgico += l.leitos_cirurgico ?? 0; a.clinico += l.leitos_clinico ?? 0;
      a.obstetrico += l.leitos_obstetrico ?? 0; a.pediatrico += l.leitos_pediatrico ?? 0;
      a.complementar += l.leitos_complementar ?? 0; a.outras += l.leitos_outras_especialidades ?? 0;
      a.hospitalDia += l.leitos_hospital_dia ?? 0;
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

  const tiposLeito = ultimoLeitos ? [
    { rotulo: "Clínico", qt: ultimoLeitos.clinico },
    { rotulo: "Cirúrgico", qt: ultimoLeitos.cirurgico },
    { rotulo: "Complementar (inclui UTI)", qt: ultimoLeitos.complementar },
    { rotulo: "Obstétrico", qt: ultimoLeitos.obstetrico },
    { rotulo: "Pediátrico", qt: ultimoLeitos.pediatrico },
    { rotulo: "Outras especialidades", qt: ultimoLeitos.outras },
    { rotulo: "Hospital-dia", qt: ultimoLeitos.hospitalDia },
  ].filter((t) => t.qt > 0).sort((a, b) => b.qt - a.qt) : [];

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

            {tiposLeito.length > 0 && (
              <div className="mt-5">
                <h3 className="text-sm font-semibold text-ink-700">
                  Leitos por tipo — {uf === "Brasil" ? "Brasil" : uf}, {ultimoLeitos!.ano}
                </h3>
                <div className="mt-2 space-y-1.5">
                  {tiposLeito.map((t) => {
                    const pct = ultimoLeitos!.leitos ? (t.qt / ultimoLeitos!.leitos) * 100 : 0;
                    return (
                      <div key={t.rotulo} className="flex items-center gap-3 text-sm">
                        <span className="w-48 shrink-0 text-ink-600">{t.rotulo}</span>
                        <div className="h-2 flex-1 overflow-hidden rounded-full bg-ink-100">
                          <div className="h-full rounded-full bg-accent-600" style={{ width: `${pct}%` }} />
                        </div>
                        <span className="w-28 shrink-0 text-right tabular-nums text-ink-500">
                          {fmtInt(t.qt)} ({fmtDec(pct, 1)}%)
                        </span>
                      </div>
                    );
                  })}
                </div>
                <p className="mt-2 text-xs text-ink-500">
                  "Complementar" é a categoria que inclui UTI (ver detalhamento de UTI acima) — não é
                  um tipo residual, é uma classificação própria da tabela de domínios do CNES.
                </p>
              </div>
            )}

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

      {/* Vazio assistencial x mortalidade */}
      <div className="card mt-6">
        <h2 className="font-serif text-xl font-semibold text-ink-900">
          Vazio assistencial e mortalidade: não achamos efeito
        </h2>
        <p className="mt-1 max-w-3xl text-sm text-ink-500">
          1.994 municípios (35,8% em 2023) não têm nenhum leito hospitalar. A pergunta óbvia é se isso
          mata mais gente. Duas hipóteses distintas, com implicações opostas: (a) <strong>sobrevida</strong> —
          sem leito perto, o caso grave morre; a assinatura seria taxa <em>padronizada</em> por idade
          maior; ou (b) <strong>local da morte</strong> — a mesma morte ocorre em casa em vez do
          hospital, sem mudar a taxa total.
        </p>

        <div className="mt-4 grid gap-4 sm:grid-cols-3">
          <Kpi rotulo="Municípios sem nenhum leito (2023)" valor="35,8%"
               detalhe="1.994 de 5.570 — grupo comparado ao resto, dentro do mesmo porte" />
          <Kpi rotulo="Diferença de taxa padronizada, dentro do porte" valor="≤ 8,6 /100 mil"
               detalhe="sem leito vs. com leito, em todos os quartis — favorável ao grupo sem leito" />
          <Kpi rotulo="Diferença de óbito domiciliar, dentro do porte" valor="≤ 0,9 p.p."
               detalhe="o efeito bruto (+1,9 p.p.) era quase todo porte" />
        </div>

        <div className="mt-5 overflow-x-auto">
          <table className="w-full min-w-[560px] text-sm">
            <thead>
              <tr className="border-b border-ink-200 text-left text-xs uppercase tracking-wide text-ink-500">
                <th className="py-2 pr-3">Porte</th>
                <th className="py-2 pr-3 text-right">Taxa padr. — sem leito</th>
                <th className="py-2 pr-3 text-right">Taxa padr. — com leito</th>
                <th className="py-2 pr-3 text-right">Diferença</th>
                <th className="py-2 text-right">% óbito domiciliar (sem × com)</th>
              </tr>
            </thead>
            <tbody>
              {[
                { p: "Q1 (menores)", ts: 667.9, tc: 676.5, ds: 23.8, dc: 23.1 },
                { p: "Q2", ts: 683.7, tc: 688.4, ds: 25.4, dc: 24.5 },
                { p: "Q3", ts: 696.6, tc: 701.3, ds: 24.6, dc: 24.5 },
                { p: "Q4 (maiores)", ts: 709.9, tc: 716.1, ds: 20.3, dc: 20.6 },
              ].map((r) => (
                <tr key={r.p} className="border-b border-ink-100 tabular-nums">
                  <td className="py-1.5 pr-3 font-medium text-ink-900">{r.p}</td>
                  <td className="py-1.5 pr-3 text-right">{fmtDec(r.ts, 1)}</td>
                  <td className="py-1.5 pr-3 text-right">{fmtDec(r.tc, 1)}</td>
                  <td className="py-1.5 pr-3 text-right">{fmtDec(r.ts - r.tc, 1)}</td>
                  <td className="py-1.5 text-right">{fmtDec(r.ds, 1)}% × {fmtDec(r.dc, 1)}%</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <p className="mt-4 max-w-3xl text-sm text-ink-700">
          <strong>Nenhuma das duas hipóteses se confirma.</strong> A taxa padronizada por idade é
          praticamente igual entre municípios com e sem leito local, dentro de cada quartil de
          porte — e a diferença que existe favorece levemente o grupo <em>sem</em> leito. O teste mais
          exigente — comparar só na região Norte, onde as distâncias até um hospital de referência são
          maiores — não muda o quadro (taxa padronizada 627,3 sem leito vs. 662,5 com leito). Se faltar
          leito matasse, seria ali que apareceria.
        </p>
        <p className="mt-2 max-w-3xl text-sm text-ink-700">
          Isso conversa com o achado da seção de ICSAP: leito local quase <strong>dobra</strong> a
          internação por causas sensíveis à atenção primária, mas <strong>não muda</strong> a
          mortalidade padronizada. Hospital pequeno parece internar muito caso de baixa complexidade
          que não altera desfecho de sobrevida — dois achados independentes contando a mesma história.
        </p>
        <p className="mt-2 max-w-3xl text-xs text-ink-500">
          <strong>Limitação declarada:</strong> "sem leito local" não mede distância até o leito mais
          próximo — um município a 20 km de um hospital regional e outro a 300 km entram no mesmo
          grupo. O teste regional atenua essa preocupação, mas não substitui medida de distância, que
          exigiria geocodificação não realizada. Reprodutível em{" "}
          <code>scripts/analise_vazio_assistencial.py</code>; mart público{" "}
          <code>mart_vazio_assistencial_municipio</code>.
        </p>
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
              <option value="hsmr_estrato">HSMR no estrato (maior primeiro)</option>
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
                    <th className="px-3 py-2 text-right">Leitos</th><th className="px-3 py-2 text-center">UTI</th>
                    <th className="px-3 py-2 text-right">HSMR no estrato (IC95%)</th>
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
                      <td className="px-3 py-2 text-right tabular-nums text-ink-600">
                        {h.leitos_total != null ? fmtInt(h.leitos_total) : "—"}
                      </td>
                      <td className="px-3 py-2 text-center text-ink-600">
                        {h.estrato === "com_uti" ? (
                          <span title={`${fmtInt(h.leitos_uti)} leitos de UTI — comparado apenas a hospitais com UTI`}
                                className="cursor-help">sim</span>
                        ) : h.estrato === "sem_uti" ? (
                          <span title="Sem UTI — comparado apenas a hospitais sem UTI" className="cursor-help text-ink-400">não</span>
                        ) : <span className="text-ink-300">—</span>}
                      </td>
                      <td className="px-3 py-2 text-right tabular-nums">
                        <span className={
                          h.significancia === "acima" ? "font-semibold text-red-700"
                          : h.significancia === "abaixo" ? "font-semibold text-accent-800"
                          : "font-semibold text-ink-500"
                        }>
                          {/* sem fallback para h.hsmr: aquele valor está em outra
                              régua (nacional) e misturá-lo aqui seria comparar
                              coisas diferentes na mesma coluna. */}
                          {h.hsmr_estrato != null ? fmtDec(h.hsmr_estrato, 2) : "—"}
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
            <strong>Cada hospital é comparado ao seu estrato, não ao Brasil inteiro.</strong> O
            ajuste por capítulo CID-10 enxerga diagnóstico, não gravidade — e hospital com UTI
            recebe o caso crítico do mesmo capítulo. Medimos: em 2024 o O/E agregado era{" "}
            <strong>1,163</strong> nos hospitais com UTI e <strong>0,542</strong> nos sem UTI (o
            nacional é 1,000 por construção, mas nenhum dos dois grupos estava em 1). Por isso o
            HSMR exibido é recalibrado <em>dentro</em> do estrato: responde “este hospital difere
            dos hospitais como ele?”. Entre colchetes, o <strong>IC95% (gamma/Poisson exato)</strong>,
            calculado sobre a mesma régua.
          </p>
          <p>
            A classificação (cor e <span className="text-ink-400">≈</span>) usa o{" "}
            <strong>q-valor</strong>, não o IC bruto: com milhares de hospitais testados por ano,
            testar cada um a 5% sem correção geraria falsos positivos só por acaso. Corrigimos com{" "}
            <strong>Benjamini-Hochberg</strong> aplicado dentro de cada estrato-ano; passe o mouse
            no <span className="text-ink-300">*</span> para ver o q-valor.{" "}
            <span className="text-amber-600">?</span> indica óbitos esperados = 0, onde não há teste
            possível. Mínimo de 12 internações/ano.
          </p>
          <p className="rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-amber-900">
            <strong>Viés residual declarado — a estratificação melhora, mas não elimina.</strong>{" "}
            Antes da correção, 86,1% dos hospitais marcados “acima do esperado” tinham UTI, e a
            marcação ia de 1,7% (menores) a 43,4% (maiores): a flag sinalizava sobretudo{" "}
            <em>“este hospital é grande e tem UTI”</em>. Com a estratificação isso cai para{" "}
            <strong>48,2%</strong> com UTI e o gradiente por porte achata para 5,6%→32,1%. Mas o
            viés não some: mesmo dentro do estrato, o HSMR mediano ainda cresce com o tamanho
            (0,39 nos menores a 0,93 nos maiores). Recalibração posterior não recupera a
            informação de gravidade que o ajuste por capítulo nunca capturou. Conclusão prática:
            compare apenas hospitais de porte e complexidade semelhantes, e use o HSMR para
            levantar hipóteses — <strong>nunca para ranquear</strong>. Detalhes na{" "}
            <a className="underline" href="/metodologia/">metodologia §14</a>.
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
