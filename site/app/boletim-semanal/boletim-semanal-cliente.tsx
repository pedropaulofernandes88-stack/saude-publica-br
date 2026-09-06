"use client";

import Link from "next/link";
import { Suspense, useEffect, useMemo, useState } from "react";
import { useSearchParams } from "next/navigation";
import {
  Area, CartesianGrid, ComposedChart, Legend, Line, ResponsiveContainer, Tooltip, XAxis, YAxis,
} from "recharts";
import { Kpi, Skeleton } from "@/components/kpi";
import { LinhasExcesso } from "@/components/charts";
import { AssinarAlertas } from "@/components/assinar-alertas";
import { MudouDesde } from "@/components/mudou-desde";
import { fmtDec, fmtInt, sdata } from "@/lib/api";
import { ALERTA, EIXO, GRADE, REFERENCIA } from "@/lib/tokens";

interface CanalSemana {
  semana: number;
  p25: number;
  mediana: number;
  p75: number;
  observado: number;
}

interface MunicipioVigilancia {
  uf: string;
  municipio: string;
  geocode: string;
  populacao: number | null;
  semana_epi: number;
  ano_epi: number;
  casos_notificados: number;
  casos_estimados: number;
  casos_est_min: number | null;
  casos_est_max: number | null;
  incidencia_100k: number | null;
  nivel: number | null;
  nivel_label: string | null;
  rt: number | null;
  variacao_4sem_pct: number | null;
  versao_modelo: string | null;
}

interface ResumoDoenca {
  municipios_monitorados: number;
  resumo_niveis: Record<string, number>;
  em_alerta: MunicipioVigilancia[];
  transmissao_crescente: number;
  maiores_volumes: MunicipioVigilancia[];
  por_uf: {
    uf: string;
    municipios: number;
    em_alerta: number;
    casos_estimados: number;
    casos_notificados: number;
  }[];
  total_estimado: number;
  total_notificado: number;
}

interface Vigilancia {
  fonte: string;
  fonte_url: string;
  semana_epi: number;
  ano_epi: number;
  versao_modelo: string | null;
  rede: {
    total: number;
    consultados: number;
    falhas: number;
    populacao_coberta: number;
    cobertura_pct: number;
    ufs_cobertas: number;
    criterios: {
      populacao_minima: number;
      top_risco_dengue: number;
      ano_populacao: number;
      ano_dengue: number;
    };
  };
  dengue: ResumoDoenca;
  chikungunya: ResumoDoenca;
  capitais_dengue: MunicipioVigilancia[];
  /** Semanas entre a edição e o dado mais recente da fonte. Normal: 1–2. */
  atraso_semanas?: number | null;
}

interface Boletim {
  edicao: string;
  ano: number;
  semana: number;
  gerado_em: string;
  versao_dataset: string | null;
  nota_preliminar: string | null;
  destaques: string[];
  vigilancia_atual: Vigilancia | null;
  verificacoes?: { nome: string; ok: boolean; critico: boolean; detalhe: string }[];
  dengue: {
    ano_ref: number;
    baseline: string;
    casos: number;
    graves: number;
    obitos: number;
    semanas_acima_p75: number;
    canal_br: CanalSemana[];
    ufs: { uf: string; casos: number; graves: number; obitos: number; semanas_acima_p75: number }[];
  };
  mortalidade: {
    ultimo_mes: string;
    obitos_br: number;
    esperado_br: number;
    pct_excesso_br: number;
    meses_descartados: number;
    serie_12m: { mes: string; obitos: number; esperado: number }[];
    ufs_ultimo_mes: { uf: string; obitos: number; esperado: number; excesso: number; pct_excesso: number | null }[];
  };
  internacoes: {
    ano_ref: number;
    internacoes: number;
    obitos: number;
    valor_total: number;
    /** Base: AIH normal (IDENT=1). Null quando o mart ainda não traz a separação. */
    permanencia_media: number | null;
    mortalidade_pct: number;
  };
}

interface EdicaoIndex {
  edicao: string;
  ano: number;
  semana: number;
  gerado_em: string;
  destaques: string[];
}

const fmtPct = (n: number) => `${n >= 0 ? "+" : ""}${fmtDec(n, 1)}%`;

function mesPt(m: string) {
  return new Date(`${m}-01T12:00:00Z`).toLocaleDateString("pt-BR", {
    month: "long",
    year: "numeric",
    timeZone: "UTC",
  });
}

function CanalEndemico({ data, ano }: { data: CanalSemana[]; ano: number }) {
  return (
    <ResponsiveContainer width="100%" height={340}>
      <ComposedChart data={data} margin={{ top: 8, right: 16, bottom: 0, left: 8 }}>
        <CartesianGrid stroke={GRADE} vertical={false} />
        <XAxis dataKey="semana" tick={{ fontSize: 12, fill: EIXO }}
               label={{ value: "semana epidemiológica", position: "insideBottom", offset: -2, fontSize: 11, fill: REFERENCIA }} />
        <YAxis tick={{ fontSize: 12, fill: EIXO }} width={52}
               tickFormatter={(v) => (v as number).toLocaleString("pt-BR", { notation: "compact" })} />
        <Tooltip
          formatter={(v, n) => [fmtInt(v as number),
            n === "observado" ? `Observado ${ano}` : n === "mediana" ? "Mediana histórica" : "Faixa esperada (P75)"]}
          labelFormatter={(l) => `Semana ${l}`}
          contentStyle={{ borderRadius: 8, borderColor: GRADE, fontSize: 13 }} />
        <Area type="monotone" dataKey="p75" stroke="none" fill="#cdd5e0" fillOpacity={0.6} name="p75" />
        <Area type="monotone" dataKey="p25" stroke="none" fill="#ffffff" fillOpacity={1} name="p25" />
        <Line type="monotone" dataKey="mediana" stroke={REFERENCIA} strokeWidth={1.6} strokeDasharray="5 4" dot={false} name="mediana" />
        <Line type="monotone" dataKey="observado" stroke={ALERTA} strokeWidth={2.8} dot={false} name="observado" />
        <Legend />
      </ComposedChart>
    </ResponsiveContainer>
  );
}

const NIVEL_ESTILO: Record<number, { cor: string; texto: string }> = {
  1: { cor: "bg-emerald-100 text-emerald-800 border-emerald-200", texto: "verde" },
  2: { cor: "bg-amber-100 text-amber-800 border-amber-200", texto: "amarelo" },
  3: { cor: "bg-orange-100 text-orange-800 border-orange-300", texto: "laranja" },
  4: { cor: "bg-red-100 text-red-800 border-red-300", texto: "vermelho" },
};

function NivelBadge({ nivel }: { nivel: number | null }) {
  const e = nivel ? NIVEL_ESTILO[nivel] : null;
  if (!e) return <span className="text-ink-500">—</span>;
  return (
    <span className={`inline-block rounded border px-1.5 py-0.5 text-xs font-medium ${e.cor}`}>
      {e.texto}
    </span>
  );
}

function TabelaVigilancia({
  capitais,
  rotulo = "Município",
}: {
  capitais: MunicipioVigilancia[];
  rotulo?: string;
}) {
  return (
    <div className="mt-4 overflow-x-auto tabela-rolavel">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-ink-200 text-left text-xs uppercase tracking-wide text-ink-500">
            <th className="col-id py-2 pr-3">{rotulo}</th>
            <th className="py-2 pr-3">Alerta</th>
            <th className="py-2 pr-3 text-right">Notificados</th>
            <th className="py-2 pr-3 text-right">Estimados</th>
            <th className="py-2 pr-3 text-right">Rt</th>
            <th className="py-2 text-right">4 semanas</th>
          </tr>
        </thead>
        <tbody>
          {capitais.map((c) => (
            <tr key={c.geocode} className="border-b border-ink-100">
              <td className="col-id py-2 pr-3 font-medium text-ink-900">
                {c.municipio} <span className="text-ink-500">{c.uf}</span>
              </td>
              <td className="py-2 pr-3"><NivelBadge nivel={c.nivel} /></td>
              <td className="py-2 pr-3 text-right tabular-nums text-ink-600">{fmtInt(c.casos_notificados)}</td>
              <td className="py-2 pr-3 text-right tabular-nums font-medium text-ink-900">
                {fmtInt(c.casos_estimados)}
                {/* Intervalo degenerado (min = max) significa que o nowcast não
                    produziu estimativa própria — exibi-lo sugeriria certeza que não existe. */}
                {c.casos_est_min != null && c.casos_est_max != null
                  && c.casos_est_min !== c.casos_est_max && (
                  <span className="ml-1 text-xs font-normal text-ink-500">
                    ({fmtInt(c.casos_est_min)}–{fmtInt(c.casos_est_max)})
                  </span>
                )}
              </td>
              <td className={`py-2 pr-3 text-right tabular-nums ${(c.rt ?? 0) > 1 ? "font-medium text-red-700" : "text-ink-600"}`}>
                {c.rt != null ? fmtDec(c.rt, 2) : "—"}
              </td>
              <td className={`py-2 text-right tabular-nums ${(c.variacao_4sem_pct ?? 0) > 0 ? "text-red-700" : "text-ink-600"}`}>
                {c.variacao_4sem_pct != null ? fmtPct(c.variacao_4sem_pct) : "—"}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function BoletimInner() {
  const params = useSearchParams();
  const edParam = params.get("e");
  const [index, setIndex] = useState<EdicaoIndex[] | null>(null);
  const [boletim, setBoletim] = useState<Boletim | null>(null);
  const [erro, setErro] = useState<string | null>(null);

  useEffect(() => {
    sdata<EdicaoIndex[]>("boletins/index").then(setIndex).catch((e) => setErro(String(e)));
  }, []);

  const edicao = edParam ?? index?.[0]?.edicao ?? null;

  useEffect(() => {
    if (!edicao) return;
    setBoletim(null);
    sdata<Boletim>(`boletins/${edicao}`).then(setBoletim).catch((e) => setErro(String(e)));
  }, [edicao]);

  const ufsAlertaDengue = useMemo(
    () => boletim?.dengue.ufs.filter((u) => u.semanas_acima_p75 >= 13).slice(0, 10) ?? [],
    [boletim],
  );

  const ufsExcesso = useMemo(
    () => boletim?.mortalidade.ufs_ultimo_mes.filter((u) => (u.pct_excesso ?? 0) > 0).slice(0, 8) ?? [],
    [boletim],
  );

  if (erro) return <div className="card mt-6 border-red-200 bg-red-50 text-sm text-red-800">Falha: {erro}</div>;
  if (!boletim) return <Skeleton altura={480} />;

  const { dengue, mortalidade, internacoes, vigilancia_atual: vig } = boletim;
  const geradoEm = new Date(boletim.gerado_em).toLocaleDateString("pt-BR", { dateStyle: "long" });

  return (
    <>
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <p className="text-xs font-semibold uppercase tracking-wide text-accent-700">
            Boletim epidemiológico semanal
          </p>
          <h1 className="mt-1 font-serif text-3xl font-semibold tracking-tight text-ink-950">
            Semana epidemiológica {boletim.semana} · {boletim.ano}
          </h1>
          <p className="mt-1 text-ink-600">
            Gerado automaticamente em {geradoEm} a partir dos microdados do DataSUS
            {boletim.versao_dataset && <span className="ml-2 rounded bg-ink-100 px-2 py-0.5 text-xs text-ink-600">dataset v{boletim.versao_dataset}</span>}
          </p>
        </div>
        <button onClick={() => window.print()} className="btn-primary no-print">🖨 Imprimir / PDF</button>
      </div>

      <div className="card mt-6 border-accent-700/20 bg-accent-700/[0.03]">
        <h2 className="font-serif text-lg font-semibold text-ink-900">Destaques da edição</h2>
        <ul className="mt-3 space-y-2 text-[15px] leading-relaxed text-ink-800">
          {boletim.destaques.map((d, i) => (
            <li key={i} className="flex gap-2.5"><span className="mt-[7px] h-1.5 w-1.5 shrink-0 rounded-full bg-accent-700" />{d}</li>
          ))}
        </ul>
      </div>

      {/* Degradação nunca é omitida em silêncio: se a vigilância faltou ou veio
          defasada, o leitor precisa saber antes de confiar no que está lendo. */}
      {!vig && (
        <div className="card mt-6 border-amber-300 bg-amber-50">
          <h2 className="font-serif text-lg font-semibold text-amber-900">
            ⚠ Vigilância indisponível nesta edição
          </h2>
          <p className="mt-2 text-sm leading-relaxed text-amber-900">
            Não foi possível obter os dados de vigilância corrente do InfoDengue quando esta
            edição foi gerada. As seções históricas abaixo (DataSUS consolidado) seguem
            íntegras — <strong>mas esta edição não informa a situação da semana atual</strong>.
            Consulte diretamente o{" "}
            <a href="https://info.dengue.mat.br" target="_blank" rel="noreferrer"
               className="font-medium underline">InfoDengue</a>.
          </p>
        </div>
      )}
      {vig && vig.atraso_semanas != null && vig.atraso_semanas >= 3 && (
        <div className="card mt-6 border-red-300 bg-red-50">
          <h2 className="font-serif text-lg font-semibold text-red-900">
            ⚠ Boletim degradado — vigilância defasada
          </h2>
          <p className="mt-2 text-sm leading-relaxed text-red-900">
            Os dados de vigilância mais recentes são da SE {vig.semana_epi}/{vig.ano_epi} —{" "}
            <strong>{vig.atraso_semanas} semanas atrás</strong> desta edição (SE {boletim.semana}).
            O atraso normal é de 1 a 2 semanas, então a fonte externa pode estar desatualizada.
            Trate a seção abaixo como retrato antigo, não como situação de hoje.
          </p>
        </div>
      )}

      {/* ── Vigilância atual (InfoDengue) ── */}
      {vig && (
        <>
          {/* Nunca "desta semana": a semana da EDIÇÃO e a semana do DADO são coisas
              diferentes, e em saúde pública confundi-las é erro de conteúdo, não de
              layout. O título passa a nomear a semana de referência, e a defasagem
              aparece sempre — não só quando fica grave. */}
          <h2 className="mt-10 font-serif text-2xl font-semibold text-ink-950">
            🚨 Vigilância corrente — SE {vig.semana_epi}/{vig.ano_epi}
          </h2>
          <p className={`mt-2 inline-block rounded-lg border px-3 py-1.5 text-sm ${
            vig.atraso_semanas == null ? "border-ink-200 bg-ink-50 text-ink-700"
            : vig.atraso_semanas >= 3 ? "border-red-300 bg-red-50 text-red-900"
            : vig.atraso_semanas === 2 ? "border-amber-300 bg-amber-50 text-amber-900"
            : "border-ink-200 bg-ink-50 text-ink-700"}`}>
            Publicado na SE {boletim.semana}/{boletim.ano}. Última semana disponível no
            InfoDengue: <strong>SE {vig.semana_epi}/{vig.ano_epi}</strong>
            {vig.atraso_semanas != null && (
              <> — defasagem de <strong>{vig.atraso_semanas}{" "}
              {vig.atraso_semanas === 1 ? "semana" : "semanas"}</strong>
              {vig.atraso_semanas >= 3 ? " (acima do normal — veja o aviso acima)"
                : vig.atraso_semanas === 2 ? " (no limite do normal, que é 1 a 2 semanas)"
                : ""}</>
            )}.
          </p>
          <p className="mt-2 text-sm text-ink-600">
            Rede sentinela de <strong>{fmtInt(vig.rede.total)} municípios</strong> (as 27 capitais, municípios
            com mais de {fmtInt(vig.rede.criterios.populacao_minima)} habitantes e os de maior carga histórica
            de dengue) — <strong>{fmtDec(vig.rede.cobertura_pct, 0)}% da população do país</strong>, todas as
            UFs. Dados do{" "}
            <a href={vig.fonte_url} target="_blank" rel="noreferrer" className="font-medium text-accent-700 underline">
              InfoDengue
            </a>{" "}
            (Fiocruz/FGV) — fonte e metodologia independentes do DataSUS consolidado usado no resto do boletim.
          </p>

          <div className="mt-4 grid gap-4 sm:grid-cols-3">
            <Kpi rotulo="Municípios em alerta" valor={String(vig.dengue.em_alerta.length)}
                 detalhe={`nível laranja ou vermelho, de ${fmtInt(vig.dengue.municipios_monitorados)} monitorados`} />
            <Kpi rotulo="Transmissão em crescimento" valor={String(vig.dengue.transmissao_crescente)}
                 detalhe="municípios com Rt > 1" />
            <Kpi rotulo={`Casos estimados na SE ${vig.semana_epi}`} valor={fmtInt(vig.dengue.total_estimado)}
                 detalhe={`${fmtInt(vig.dengue.total_notificado)} já notificados — o restante é atraso de digitação`} />
          </div>

          <p className="mt-3 rounded-lg border border-sky-200 bg-sky-50 px-4 py-2 text-sm text-sky-900">
            💡 <strong>Por que estimado &gt; notificado:</strong> a notificação da semana corrente ainda está sendo
            digitada. O InfoDengue aplica <em>nowcasting</em> para estimar o total real; usar a contagem crua
            subestima sistematicamente a situação atual. Um município pode aparecer em alerta com poucos casos
            já digitados — o alerta vem do padrão de crescimento, não só do número bruto.
          </p>

          {vig.dengue.em_alerta.length > 0 && (
            <div className="card mt-6 border-orange-200">
              <h3 className="font-serif text-xl font-semibold text-ink-900">
                Municípios em alerta — dengue
              </h3>
              <p className="mt-1 text-sm text-ink-500">
                Nível laranja (transmissão sustentada) ou vermelho (epidemia), ordenados por gravidade.
              </p>
              <TabelaVigilancia capitais={vig.dengue.em_alerta} />
            </div>
          )}

          {vig.chikungunya.em_alerta.length > 0 && (
            <div className="card mt-6 border-orange-200">
              <h3 className="font-serif text-xl font-semibold text-ink-900">
                Municípios em alerta — chikungunya
              </h3>
              <TabelaVigilancia capitais={vig.chikungunya.em_alerta} />
            </div>
          )}

          <div className="card mt-6">
            <h3 className="font-serif text-xl font-semibold text-ink-900">Panorama por UF — dengue</h3>
            <p className="mt-1 text-sm text-ink-500">
              Municípios da rede sentinela em cada UF e quantos estão em alerta na SE {vig.semana_epi}/{vig.ano_epi}.
            </p>
            <div className="mt-4 overflow-x-auto tabela-rolavel">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-ink-200 text-left text-xs uppercase tracking-wide text-ink-500">
                    <th className="col-id py-2 pr-3">UF</th>
                    <th className="py-2 pr-3 text-right">Monitorados</th>
                    <th className="py-2 pr-3 text-right">Em alerta</th>
                    <th className="py-2 pr-3 text-right">Notificados</th>
                    <th className="py-2 text-right">Estimados</th>
                  </tr>
                </thead>
                <tbody>
                  {vig.dengue.por_uf.map((u) => (
                    <tr key={u.uf} className="border-b border-ink-100">
                      <td className="col-id py-2 pr-3 font-medium text-ink-900">{u.uf}</td>
                      <td className="py-2 pr-3 text-right tabular-nums text-ink-600">{u.municipios}</td>
                      <td className={`py-2 pr-3 text-right tabular-nums ${u.em_alerta > 0 ? "font-medium text-orange-700" : "text-ink-500"}`}>
                        {u.em_alerta || "—"}
                      </td>
                      <td className="py-2 pr-3 text-right tabular-nums text-ink-600">{fmtInt(u.casos_notificados)}</td>
                      <td className="py-2 text-right tabular-nums font-medium text-ink-900">{fmtInt(u.casos_estimados)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          <div className="card mt-6">
            <h3 className="font-serif text-xl font-semibold text-ink-900">Capitais — dengue</h3>
            <p className="mt-1 text-sm text-ink-500">
              Referência das 27 capitais, ordenadas por casos estimados. A coluna &quot;4 semanas&quot; compara
              a estimativa da SE {vig.semana_epi} com a de quatro semanas antes.
            </p>
            <TabelaVigilancia capitais={vig.capitais_dengue} rotulo="Capital" />
            <p className="mt-3 text-xs text-ink-500">
              Níveis do InfoDengue: verde (1) · amarelo (2, atenção) · laranja (3, transmissão sustentada) ·
              vermelho (4, epidemia). Modelo {vig.versao_modelo}. Intervalo entre parênteses = faixa da
              estimativa; quando ausente, o modelo não estimou incerteza para aquele município.
              {vig.rede.falhas > 0 && ` ${vig.rede.falhas} municípios da rede não responderam nesta execução.`}
            </p>
          </div>
        </>
      )}

      {/* Momento de maior relevância do convite: logo depois de ver os alertas. */}
      <AssinarAlertas />

      {/* ── Dengue histórica ── */}
      <h2 className="mt-10 font-serif text-2xl font-semibold text-ink-950">🦟 Dengue — retrospectiva {dengue.ano_ref}</h2>
      <p className="mt-1 text-sm text-ink-600">
        Base consolidada do SINAN/DataSUS — muda quando o Ministério da Saúde publica, não toda semana.
      </p>
      <div className="mt-4 grid gap-4 sm:grid-cols-3">
        <Kpi rotulo="Casos prováveis" valor={fmtInt(dengue.casos)} detalhe={`${fmtInt(dengue.graves)} graves/com alarme`} />
        <Kpi rotulo="Óbitos" valor={fmtInt(dengue.obitos)}
             detalhe={`letalidade ${fmtDec((dengue.obitos / dengue.casos) * 100, 3)}% dos casos prováveis`} />
        <Kpi rotulo="Semanas acima do canal" valor={`${dengue.semanas_acima_p75}/52`}
             detalhe={`observado > P75 da faixa esperada (${dengue.baseline})`} />
      </div>

      <div className="card mt-6">
        <h3 className="font-serif text-xl font-semibold text-ink-900">Canal endêmico — Brasil</h3>
        <p className="mt-1 text-sm text-ink-500">
          Faixa cinza: intervalo esperado (P25–P75 das semanas de {dengue.baseline}). Linha vermelha:
          casos observados em {dengue.ano_ref}. Acima da faixa = sinal de surto epidêmico.
        </p>
        <div className="mt-4"><CanalEndemico data={dengue.canal_br} ano={dengue.ano_ref} /></div>
      </div>

      {ufsAlertaDengue.length > 0 && (
        <div className="card mt-6">
          <h3 className="font-serif text-xl font-semibold text-ink-900">UFs em alerta prolongado</h3>
          <p className="mt-1 text-sm text-ink-500">
            Estados que passaram 13+ semanas (≥ 1 trimestre) acima do próprio canal endêmico em {dengue.ano_ref}, ordenados por volume de casos.
          </p>
          <div className="mt-4 overflow-x-auto tabela-rolavel">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-ink-200 text-left text-xs uppercase tracking-wide text-ink-500">
                  <th className="col-id py-2 pr-4">UF</th>
                  <th className="py-2 pr-4 text-right">Casos prováveis</th>
                  <th className="py-2 pr-4 text-right">Óbitos</th>
                  <th className="py-2 text-right">Semanas acima do P75</th>
                </tr>
              </thead>
              <tbody>
                {ufsAlertaDengue.map((u) => (
                  <tr key={u.uf} className="border-b border-ink-100">
                    <td className="col-id py-2 pr-4 font-medium text-ink-900">{u.uf}</td>
                    <td className="py-2 pr-4 text-right tabular-nums">{fmtInt(u.casos)}</td>
                    <td className="py-2 pr-4 text-right tabular-nums">{fmtInt(u.obitos)}</td>
                    <td className="py-2 text-right tabular-nums font-medium text-red-700">{u.semanas_acima_p75}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* ── Mortalidade ── */}
      <h2 className="mt-10 font-serif text-2xl font-semibold text-ink-950">📈 Mortalidade geral — excesso vs. esperado</h2>
      <div className="mt-4 grid gap-4 sm:grid-cols-3">
        <Kpi rotulo={`Óbitos em ${mesPt(mortalidade.ultimo_mes)}`} valor={fmtInt(mortalidade.obitos_br)}
             detalhe={`esperado: ${fmtInt(mortalidade.esperado_br)} (baseline 2015–2019)`} />
        <Kpi rotulo="Excesso no mês" valor={fmtPct(mortalidade.pct_excesso_br)}
             detalhe={mortalidade.pct_excesso_br > 5 ? "acima do esperado" : mortalidade.pct_excesso_br < -5 ? "abaixo do esperado" : "dentro da variação usual"} />
        <Kpi rotulo="UFs com excesso positivo" valor={String(ufsExcesso.length ? mortalidade.ufs_ultimo_mes.filter((u) => (u.pct_excesso ?? 0) > 0).length : 0)}
             detalhe="no último mês consolidado" />
      </div>
      {mortalidade.meses_descartados > 0 && (
        <p className="mt-3 rounded-lg border border-amber-200 bg-amber-50 px-4 py-2 text-sm text-amber-800">
          ⚠ {mortalidade.meses_descartados === 1 ? "O mês mais recente foi excluído" : `Os ${mortalidade.meses_descartados} meses mais recentes foram excluídos`} desta
          análise por registro ainda incompleto no SIM (observado &lt; 90% do esperado). O dado será incorporado quando consolidar.
        </p>
      )}

      <div className="card mt-6">
        <h3 className="font-serif text-xl font-semibold text-ink-900">Observado vs. esperado — últimos 12 meses consolidados</h3>
        <div className="mt-4">
          <LinhasExcesso data={mortalidade.serie_12m.map((s) => ({ ...s, mes: `${s.mes}-01` }))} />
        </div>
      </div>

      {ufsExcesso.length > 0 && (
        <div className="card mt-6">
          <h3 className="font-serif text-xl font-semibold text-ink-900">
            Maiores excessos em {mesPt(mortalidade.ultimo_mes)}
          </h3>
          <div className="mt-4 overflow-x-auto tabela-rolavel">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-ink-200 text-left text-xs uppercase tracking-wide text-ink-500">
                  <th className="col-id py-2 pr-4">UF</th>
                  <th className="py-2 pr-4 text-right">Óbitos</th>
                  <th className="py-2 pr-4 text-right">Esperado</th>
                  <th className="py-2 text-right">Excesso</th>
                </tr>
              </thead>
              <tbody>
                {ufsExcesso.map((u) => (
                  <tr key={u.uf} className="border-b border-ink-100">
                    <td className="col-id py-2 pr-4 font-medium text-ink-900">{u.uf}</td>
                    <td className="py-2 pr-4 text-right tabular-nums">{fmtInt(u.obitos)}</td>
                    <td className="py-2 pr-4 text-right tabular-nums">{fmtInt(u.esperado)}</td>
                    <td className="py-2 text-right tabular-nums font-medium text-red-700">{fmtPct(u.pct_excesso ?? 0)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <p className="mt-2 text-xs text-ink-500">
            Excesso mensal por UF oscila; valores isolados não indicam necessariamente evento sanitário.
          </p>
        </div>
      )}

      {/* ── Internações ── */}
      <h2 className="mt-10 font-serif text-2xl font-semibold text-ink-950">🏥 Internações SUS — {internacoes.ano_ref}</h2>
      <div className="mt-4 grid gap-4 sm:grid-cols-4">
        <Kpi rotulo="Internações (AIH)" valor={fmtInt(internacoes.internacoes)} />
        <Kpi rotulo="Mortalidade intra-hospitalar" valor={`${fmtDec(internacoes.mortalidade_pct, 1)}%`}
             detalhe={`${fmtInt(internacoes.obitos)} óbitos`} />
        <Kpi rotulo="Permanência média" valor={`${fmtDec(internacoes.permanencia_media, 1)} dias`} />
        <Kpi rotulo="Valor aprovado" valor={`R$ ${fmtDec(internacoes.valor_total / 1e9, 1)} bi`} />
      </div>

      <MudouDesde edicao={boletim.edicao}
                  ehMaisAntiga={!!index && index[index.length - 1]?.edicao === boletim.edicao} />

      {/* ── Arquivo + rodapé ── */}
      {index && index.length > 1 && (
        <div className="card mt-10 no-print">
          <h2 className="font-serif text-lg font-semibold text-ink-900">Edições anteriores</h2>
          <ul className="mt-3 grid gap-1.5 text-sm sm:grid-cols-2">
            {index.map((e) => (
              <li key={e.edicao}>
                <Link href={`/boletim-semanal/?e=${e.edicao}`}
                      className={`hover:text-accent-700 ${e.edicao === boletim.edicao ? "font-semibold text-accent-700" : "text-ink-700"}`}>
                  SE {e.semana} · {e.ano}
                </Link>
                <span className="ml-2 text-xs text-ink-500">
                  {new Date(e.gerado_em).toLocaleDateString("pt-BR")}
                </span>
              </li>
            ))}
          </ul>
        </div>
      )}

      <div className="card mt-6 text-sm leading-relaxed text-ink-600">
        <p>
          <b>Fontes e método:</b> a vigilância desta semana vem do{" "}
          <a href="https://info.dengue.mat.br" target="_blank" rel="noreferrer" className="font-medium text-accent-700 underline">
            InfoDengue
          </a>{" "}
          (Fiocruz/FGV), que aplica <em>nowcasting</em> para corrigir o atraso de notificação —
          fonte e metodologia independentes do restante do boletim. As seções históricas usam
          SIM, SINAN e SIH/DataSUS (Ministério da Saúde) e população IBGE.
          Canal endêmico: quartis P25–P75 das semanas epidemiológicas de {dengue.baseline} (diagrama de
          controle). Excesso de mortalidade: observado vs. tendência 2015–2019 projetada.
          {boletim.nota_preliminar && <> {boletim.nota_preliminar}.</>} Metodologia completa em{" "}
          <Link href="/metodologia/" className="font-medium text-accent-700 underline">saudeemdado.com/metodologia</Link>.
        </p>
        <p className="mt-2">
          Boletim gerado automaticamente toda segunda-feira pelo pipeline aberto do{" "}
          <b>saudeemdado.com</b> — edição permanente:{" "}
          <span className="font-mono text-xs">saudeemdado.com/boletim-semanal/?e={boletim.edicao}</span>
        </p>
      </div>
    </>
  );
}

export function BoletimSemanalCliente() {
  return (
    <div className="mx-auto max-w-5xl px-4 py-10 sm:px-6">
      <Suspense fallback={<Skeleton altura={480} />}>
        <BoletimInner />
      </Suspense>
    </div>
  );
}
