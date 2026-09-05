"use client";

import { useEffect, useMemo, useState } from "react";
import { SerieCobertura } from "@/components/charts";
import { Kpi, Skeleton } from "@/components/kpi";
import {
  UFS, fmtDec, fmtInt, rest,
  type CoberturaApsMunicipio, type CoberturaIcsapMunicipio,
} from "@/lib/api";
import { semAcento } from "@/lib/busca";

const FAIXAS: { rotulo: string; min: number; max: number }[] = [
  { rotulo: "< 10 mil hab.", min: 0, max: 10_000 },
  { rotulo: "10–50 mil", min: 10_000, max: 50_000 },
  { rotulo: "50–200 mil", min: 50_000, max: 200_000 },
  { rotulo: "> 200 mil", min: 200_000, max: Infinity },
];

function mediana(v: number[]): number | null {
  if (!v.length) return null;
  const s = [...v].sort((a, b) => a - b);
  const m = Math.floor(s.length / 2);
  return s.length % 2 ? s[m] : (s[m - 1] + s[m]) / 2;
}

export function AtencaoBasicaCliente() {
  // ── Série do município (o uso VÁLIDO do indicador) ───────────────────────
  const [busca, setBusca] = useState("");
  const [municipios, setMunicipios] = useState<CoberturaIcsapMunicipio[]>([]);
  const [sel, setSel] = useState<{ cod: string; nome: string; uf: string } | null>(null);
  const [serie, setSerie] = useState<CoberturaApsMunicipio[] | null>(null);

  // ── Cruzamento com ICSAP (o achado) ──────────────────────────────────────
  const [cruz, setCruz] = useState<CoberturaIcsapMunicipio[] | null>(null);
  const [ufFiltro, setUfFiltro] = useState("Brasil");

  useEffect(() => {
    rest<CoberturaIcsapMunicipio>("mart_cobertura_icsap_municipio", {
      select: "municipio_cod,municipio_nome,uf_sigla,regiao,ano,populacao,cobertura_pct,cobertura_efetiva,qt_esf,internacoes_total,internacoes_icsap,pct_icsap,icsap_100k,ivs_score",
      ano: "eq.2024", order: "municipio_cod",
    }).then((r) => { setCruz(r); setMunicipios(r); }).catch(() => { setCruz([]); setMunicipios([]); });
  }, []);

  const opcoes = useMemo(() => {
    const q = semAcento(busca.trim());
    if (q.length < 3) return [];
    return municipios
      .filter((m) => semAcento(m.municipio_nome ?? "").includes(q))
      .sort((a, b) => (b.populacao ?? 0) - (a.populacao ?? 0))
      .slice(0, 8);
  }, [municipios, busca]);

  useEffect(() => {
    if (!sel) { setSerie(null); return; }
    rest<CoberturaApsMunicipio>("mart_cobertura_aps_municipio", {
      select: "municipio_cod,municipio_nome,uf_sigla,ano,mes,mes_competencia,populacao,qt_esf,qt_eap20,qt_eap30,capacidade_equipe,cobertura_pct",
      municipio_cod: `eq.${sel.cod}`, order: "mes_competencia",
    }).then(setSerie).catch(() => setSerie([]));
  }, [sel]);

  const serieChart = useMemo(
    () => serie?.map((r) => ({ mes: r.mes_competencia, cobertura: r.cobertura_pct ?? 0 })) ?? [],
    [serie],
  );
  const ultimo = serie?.length ? serie[serie.length - 1] : null;
  const primeiro = serie?.length ? serie[0] : null;

  // Estratos: a demonstração de que cobertura é proxy de porte
  const estratos = useMemo(() => {
    if (!cruz?.length) return null;
    const base = ufFiltro === "Brasil" ? cruz : cruz.filter((m) => m.uf_sigla === ufFiltro);
    return FAIXAS.map((f) => {
      const sub = base.filter((m) => (m.populacao ?? 0) >= f.min && (m.populacao ?? 0) < f.max);
      return {
        rotulo: f.rotulo,
        n: sub.length,
        cobertura: mediana(sub.map((m) => m.cobertura_pct ?? 0).filter((v) => v > 0)),
        icsap: mediana(sub.map((m) => m.icsap_100k ?? 0).filter((v) => v > 0)),
        pctIcsap: mediana(sub.map((m) => m.pct_icsap ?? 0).filter((v) => v > 0)),
        saturados: sub.length ? sub.filter((m) => (m.cobertura_pct ?? 0) > 100).length / sub.length * 100 : 0,
      };
    });
  }, [cruz, ufFiltro]);

  const agregado = useMemo(() => {
    if (!cruz?.length) return null;
    const base = ufFiltro === "Brasil" ? cruz : cruz.filter((m) => m.uf_sigla === ufFiltro);
    const acima = base.filter((m) => (m.cobertura_pct ?? 0) > 100).length;
    const equipes = base.reduce((s, m) => s + (m.qt_esf ?? 0), 0);
    return {
      n: base.length,
      acimaPct: base.length ? (acima / base.length) * 100 : 0,
      equipes,
      medianaCob: mediana(base.map((m) => m.cobertura_pct ?? 0).filter((v) => v > 0)),
    };
  }, [cruz, ufFiltro]);

  return (
    <div className="mx-auto max-w-7xl px-4 py-10 sm:px-6">
      <h1 className="font-serif text-3xl font-semibold tracking-tight text-ink-950">Atenção Primária</h1>
      <p className="mt-2 max-w-3xl text-ink-600">
        Cobertura potencial da Atenção Primária à Saúde por município e mês (2021–2026), a partir do
        relatório público do Ministério da Saúde (e-Gestor AB): equipes credenciadas, capacidade
        instalada e evolução no tempo.
      </p>

      <div className="mt-4 max-w-3xl rounded-lg border border-amber-300 bg-amber-50 px-4 py-3.5 text-sm text-amber-900">
        <p className="font-semibold">Leia isto antes de comparar municípios.</p>
        <p className="mt-1.5">
          A cobertura potencial é <strong>capacidade instalada ÷ população</strong>. Como a capacidade
          de cada equipe é padronizada, municípios pequenos saturam o indicador com poucas equipes —
          ele passa de 100% em <strong>86% dos municípios</strong> e chega a 800%. Nossa análise mostra
          que, empiricamente, esse indicador se correlaciona fortemente com o{" "}
          <strong>porte do município</strong> (ρ = −0,54 com a população) e{" "}
          <strong>praticamente nada com internações evitáveis</strong> (ρ = +0,004).
        </p>
        <p className="mt-1.5">
          <strong>Use para:</strong> acompanhar a evolução de <em>um</em> município no tempo, e contar
          equipes. <strong>Não use para:</strong> ranquear municípios ou inferir qualidade da atenção
          básica. O porquê está detalhado abaixo e na{" "}
          <a className="underline" href="/artigos/o-que-os-indicadores-nao-comparam/">análise metodológica</a>.
        </p>
      </div>

      {/* ── Uso válido: um município no tempo ───────────────────────────── */}
      <div className="card mt-6">
        <h2 className="font-serif text-xl font-semibold text-ink-900">Evolução de um município</h2>
        <p className="mt-1 max-w-2xl text-sm text-ink-500">
          O uso metodologicamente válido: a mesma população, o mesmo critério, ao longo de 65
          competências mensais. Variações aqui refletem mudanças reais de credenciamento de equipes.
        </p>
        <div className="mt-4 max-w-md">
          <label className="label" htmlFor="ab-busca">Buscar município</label>
          <input id="ab-busca" className="select" placeholder="ex.: Penápolis" value={busca}
                 onChange={(e) => { setBusca(e.target.value); setSel(null); }} />
          {opcoes.length > 0 && !sel && (
            <div className="mt-1 rounded-lg border border-ink-200 bg-white shadow-sm">
              {opcoes.map((o) => (
                <button key={o.municipio_cod} type="button"
                        onClick={() => { setSel({ cod: o.municipio_cod, nome: o.municipio_nome ?? o.municipio_cod, uf: o.uf_sigla }); setBusca(o.municipio_nome ?? ""); }}
                        className="block w-full px-3 py-2 text-left text-sm hover:bg-ink-50">
                  {o.municipio_nome} <span className="text-ink-500">· {o.uf_sigla} · {fmtInt(o.populacao)} hab.</span>
                </button>
              ))}
            </div>
          )}
        </div>

        {sel && (
          <div className="mt-5">
            {serie ? (
              serie.length === 0 ? (
                <p className="text-sm text-ink-500">Sem série publicada para este município.</p>
              ) : (
                <>
                  <div className="grid gap-4 sm:grid-cols-4">
                    <Kpi rotulo="Cobertura potencial" valor={`${fmtDec(ultimo?.cobertura_pct, 1)}%`}
                         detalhe={`competência ${ultimo?.mes_competencia?.slice(0, 7) ?? "—"}`} />
                    <Kpi rotulo="Equipes de Saúde da Família" valor={fmtInt(ultimo?.qt_esf)}
                         detalhe={primeiro ? `eram ${fmtInt(primeiro.qt_esf)} em ${primeiro.mes_competencia.slice(0, 7)}` : ""} />
                    <Kpi rotulo="Capacidade instalada" valor={fmtInt(ultimo?.capacidade_equipe)}
                         detalhe="pessoas que as equipes podem acompanhar" />
                    <Kpi rotulo="População" valor={fmtInt(ultimo?.populacao)} detalhe="base do cálculo (estimativa oficial)" />
                  </div>
                  <div className="mt-5">
                    <p className="label mb-2">
                      {sel.nome} · {sel.uf} — cobertura potencial mensal (2021–2026)
                    </p>
                    <SerieCobertura data={serieChart} titulo={`${sel.nome} · ${sel.uf} — cobertura potencial mensal`} />
                  </div>
                </>
              )
            ) : <Skeleton altura={320} />}
          </div>
        )}
      </div>

      {/* ── O achado: cobertura é proxy de porte ────────────────────────── */}
      <div className="card mt-6">
        <div className="flex flex-wrap items-end justify-between gap-4">
          <div>
            <h2 className="font-serif text-xl font-semibold text-ink-900">
              Por que não dá para comparar municípios
            </h2>
            <p className="mt-1 max-w-2xl text-sm text-ink-500">
              Agrupando os municípios por porte, a cobertura mediana cai monotonicamente conforme a
              população cresce. O “gradiente de cobertura” é, na prática, um gradiente de tamanho —
              não de força da atenção primária.
            </p>
          </div>
          <div>
            <label className="label" htmlFor="ab-uf">Abrangência</label>
            <select id="ab-uf" className="select" value={ufFiltro} onChange={(e) => setUfFiltro(e.target.value)}>
              <option value="Brasil">Brasil (todas as UFs)</option>
              {UFS.map((u) => <option key={u} value={u}>{u}</option>)}
            </select>
          </div>
        </div>

        {agregado && (
          <div className="mt-4 grid gap-4 sm:grid-cols-4">
            <Kpi rotulo="Municípios" valor={fmtInt(agregado.n)} detalhe="com dado de cobertura e ICSAP em 2024" />
            <Kpi rotulo="Cobertura mediana" valor={`${fmtDec(agregado.medianaCob, 1)}%`} detalhe="mediana do recorte" />
            <Kpi rotulo="Acima de 100%" valor={`${fmtDec(agregado.acimaPct, 1)}%`} detalhe="dos municípios — indicador saturado" />
            <Kpi rotulo="Equipes de Saúde da Família" valor={fmtInt(Math.round(agregado.equipes))} detalhe="média de 2024, soma do recorte" />
          </div>
        )}

        <div className="mt-4 overflow-x-auto">
          {estratos ? (
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b-2 border-ink-200 text-left text-xs uppercase tracking-wide text-ink-500">
                  <th className="px-3 py-2">Porte do município</th>
                  <th className="px-3 py-2 text-right">Municípios</th>
                  <th className="px-3 py-2 text-right">Cobertura mediana</th>
                  <th className="px-3 py-2 text-right">Saturados (&gt;100%)</th>
                  <th className="px-3 py-2 text-right">ICSAP/100k mediano</th>
                  <th className="px-3 py-2 text-right">% ICSAP mediano</th>
                </tr>
              </thead>
              <tbody>
                {estratos.map((e) => (
                  <tr key={e.rotulo} className="border-b border-ink-100 hover:bg-ink-50">
                    <td className="px-3 py-2 font-medium text-ink-900">{e.rotulo}</td>
                    <td className="px-3 py-2 text-right tabular-nums text-ink-600">{fmtInt(e.n)}</td>
                    <td className="px-3 py-2 text-right font-semibold tabular-nums text-accent-800">{fmtDec(e.cobertura, 1)}%</td>
                    <td className="px-3 py-2 text-right tabular-nums text-ink-600">{fmtDec(e.saturados, 0)}%</td>
                    <td className="px-3 py-2 text-right tabular-nums">{fmtDec(e.icsap, 0)}</td>
                    <td className="px-3 py-2 text-right tabular-nums text-ink-600">{fmtDec(e.pctIcsap, 1)}%</td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : <Skeleton altura={200} />}
        </div>
        <p className="mt-3 max-w-3xl text-xs text-ink-500">
          Leia as colunas de cobertura e ICSAP em conjunto: os municípios com <em>maior</em> cobertura
          mediana são os menores — e não são os de menor ICSAP. Se a cobertura potencial medisse força
          da atenção primária, esperaríamos o contrário. Análise completa (correlação bruta, parcial
          controlando porte e vulnerabilidade, e estratificada) em{" "}
          <code>scripts/analise_cobertura_icsap.py</code>.
        </p>
      </div>

      {/* ── Teste de robustez: comparar só pares do mesmo porte ──────────── */}
      <div className="card mt-6">
        <h2 className="font-serif text-xl font-semibold text-ink-900">
          Teste de robustez: e se compararmos só municípios do mesmo tamanho?
        </h2>
        <p className="mt-1 max-w-3xl text-sm text-ink-500">
          A seção anterior mostra que a cobertura (%) não serve para comparar municípios de portes
          diferentes. Mas talvez sirva para comparar municípios <strong>do mesmo porte</strong> entre
          si — a pergunta de equidade legítima. Testamos com o método mais rigoroso possível:
          substituímos a cobertura por <strong>densidade real de equipes</strong> (ESF por 10 mil
          habitantes, sem o teto artificial de capacidade padronizada), comparamos cada município
          apenas aos pares do <strong>mesmo quartil de população</strong>, e usamos{" "}
          <strong>%ICSAP</strong> em vez de ICSAP por 100 mil — porque testamos e o ICSAP por 100 mil
          cai em municípios vulneráveis simplesmente porque o acesso hospitalar geral é menor lá, não
          porque a atenção primária seja melhor.
        </p>

        <div className="mt-4 grid gap-4 sm:grid-cols-3">
          <Kpi rotulo="Densidade de ESF × %ICSAP, no mesmo porte" valor="ρ ≈ 0,00"
               detalhe="entre −0,02 e +0,18 conforme o quartil de porte — sem relação" />
          <Kpi rotulo="Co-ocorrência observada vs. esperada ao acaso" valor="0,94×"
               detalhe="menos equipe + mais ICSAP juntos: não passa do que a coincidência prevê" />
          <Kpi rotulo="%ICSAP por quartil de vulnerabilidade" valor="19–21%"
               detalhe="praticamente constante — sem gradiente por vulnerabilidade" />
        </div>

        <p className="mt-4 max-w-3xl text-sm text-ink-700">
          <strong>Resultado: o achado nulo sobrevive ao teste mais rigoroso.</strong> Mesmo comparando
          apenas municípios do mesmo tamanho, e mesmo trocando a métrica de cobertura pela densidade
          real de equipes, não há associação entre ter mais Estratégia Saúde da Família e internar
          proporcionalmente menos por causas evitáveis. A leve diferença que aparece por
          vulnerabilidade social é explicada pela <em>alocação</em> de equipes — municípios mais
          vulneráveis têm, na mediana, mais ESF por habitante dentro do próprio porte, um sinal
          positivo de direcionamento de recursos — e não por um efeito da atenção primária sobre o
          ICSAP em si, que fica praticamente constante entre os quartis de vulnerabilidade.
        </p>
        <p className="mt-2 max-w-3xl text-xs text-ink-500">
          Não publicamos isto como ranking ou lista de municípios prioritários: a razão
          observado/esperado de 0,94 mostra que qualquer classificação individual de "município em
          atenção" seria estatisticamente indistinguível de ruído. Reprodutível em{" "}
          <code>scripts/analise_equidade_aps.py</code>; discussão completa no artigo{" "}
          <a href="/artigos/o-que-os-indicadores-nao-comparam/" className="text-accent-700 underline">
            "O que os indicadores não comparam"
          </a>.
        </p>
      </div>

      {/* ── Teste longitudinal: e se o efeito só aparecer com o tempo? ────── */}
      <div className="card mt-6">
        <h2 className="font-serif text-xl font-semibold text-ink-900">
          E equipes recém-implantadas? Um teste ao longo de 4 anos
        </h2>
        <p className="mt-1 max-w-3xl text-sm text-ink-500">
          Uma objeção legítima ao teste acima: ele usa um único ano (2024), e o efeito de uma equipe
          nova pode levar tempo para aparecer. Reprocessamos o ICSAP de 2021 a 2023 (2024 já
          disponível) e comparamos cada município consigo mesmo ao longo do tempo — a única forma de
          eliminar qualquer diferença fixa entre municípios (geografia, perfil de doenças, distância
          de referência).
        </p>
        <p className="mt-2 max-w-3xl text-sm text-ink-500">
          O primeiro teste pareceu mostrar um sinal — na direção errada. Descobrimos por quê: ESF e
          %ICSAP subiram juntos no Brasil inteiro nesses 4 anos (provável retomada pós-pandemia),
          então qualquer município "acompanhando a maré" nacional gerava correlação artificial. Ao
          remover também essa tendência de calendário, o sinal desaparece.
        </p>

        <div className="mt-4 grid gap-4 sm:grid-cols-3">
          <Kpi rotulo="Correlação ingênua (só por município)" valor="ρ = +0,13"
               detalhe="parecia sinal — mas era tendência nacional comum, não efeito real" />
          <Kpi rotulo="Correlação correta (município + ano)" valor="ρ = +0,01"
               detalhe="ao remover a tendência de calendário, o sinal desaparece" />
          <Kpi rotulo="Maior |ρ| entre os 3 testes corretos" valor="0,03"
               detalhe="contemporâneo, variação ano a ano, e defasagem de 1 ano" />
        </div>

        <p className="mt-4 max-w-3xl text-sm text-ink-700">
          <strong>O achado nulo se confirma também no tempo.</strong> Nem no mesmo ano, nem olhando a
          variação ano a ano, nem testando um efeito defasado em 1 ano, aparece associação entre
          densidade de ESF e %ICSAP dentro do mesmo município. E o episódio virou, ele mesmo, mais um
          exemplo do problema central deste projeto: uma tendência de calendário compartilhada pode
          simular um "achado" do mesmo jeito que o porte municipal simulava um antes — a correção é
          sempre a mesma, comparar cada unidade a si mesma ou a seus pares reais, nunca ao Brasil
          inteiro de uma vez.
        </p>
        <p className="mt-2 max-w-3xl text-xs text-ink-500">
          Painel balanceado de 5.568 municípios × 4 anos (22.272 observações). Reprodutível em{" "}
          <code>scripts/analise_equidade_aps_longitudinal.py</code>.
        </p>
      </div>

      <p className="mt-4 text-xs text-ink-500">
        Fonte: relatório público de Cobertura da APS (Ministério da Saúde / e-Gestor AB), competências
        de jan/2021 a mai/2026, cruzado com ICSAP (SIH/DataSUS, 2024) e o índice-proxy de
        vulnerabilidade (Censo 2022). A população usada no denominador é a estimativa oficial adotada
        pelo próprio relatório, não a série do projeto. Ver{" "}
        <a className="text-accent-700 underline" href="/metodologia/">metodologia</a>.
      </p>
    </div>
  );
}
