"use client";

import Link from "next/link";
import { Suspense, useEffect, useMemo, useState } from "react";
import { useSearchParams } from "next/navigation";
import {
  Area, CartesianGrid, ComposedChart, Legend, Line, ResponsiveContainer, Tooltip, XAxis, YAxis,
} from "recharts";
import { Kpi, Skeleton } from "@/components/kpi";
import { LinhasExcesso } from "@/components/charts";
import { fmtDec, fmtInt, sdata } from "@/lib/api";

interface CanalSemana {
  semana: number;
  p25: number;
  mediana: number;
  p75: number;
  observado: number;
}

interface Boletim {
  edicao: string;
  ano: number;
  semana: number;
  gerado_em: string;
  versao_dataset: string | null;
  nota_preliminar: string | null;
  destaques: string[];
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
    permanencia_media: number;
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
        <CartesianGrid stroke="#eceef2" vertical={false} />
        <XAxis dataKey="semana" tick={{ fontSize: 12, fill: "#677791" }}
               label={{ value: "semana epidemiológica", position: "insideBottom", offset: -2, fontSize: 11, fill: "#8694ab" }} />
        <YAxis tick={{ fontSize: 12, fill: "#677791" }} width={52}
               tickFormatter={(v) => (v as number).toLocaleString("pt-BR", { notation: "compact" })} />
        <Tooltip
          formatter={(v, n) => [fmtInt(v as number),
            n === "observado" ? `Observado ${ano}` : n === "mediana" ? "Mediana histórica" : "Faixa esperada (P75)"]}
          labelFormatter={(l) => `Semana ${l}`}
          contentStyle={{ borderRadius: 8, borderColor: "#eceef2", fontSize: 13 }} />
        <Area type="monotone" dataKey="p75" stroke="none" fill="#cdd5e0" fillOpacity={0.6} name="p75" />
        <Area type="monotone" dataKey="p25" stroke="none" fill="#ffffff" fillOpacity={1} name="p25" />
        <Line type="monotone" dataKey="mediana" stroke="#8694ab" strokeWidth={1.6} strokeDasharray="5 4" dot={false} name="mediana" />
        <Line type="monotone" dataKey="observado" stroke="#b4232a" strokeWidth={2.8} dot={false} name="observado" />
        <Legend />
      </ComposedChart>
    </ResponsiveContainer>
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

  const { dengue, mortalidade, internacoes } = boletim;
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

      {/* ── Dengue ── */}
      <h2 className="mt-10 font-serif text-2xl font-semibold text-ink-950">🦟 Dengue — situação {dengue.ano_ref}</h2>
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
          <div className="mt-4 overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-ink-200 text-left text-xs uppercase tracking-wide text-ink-500">
                  <th className="py-2 pr-4">UF</th>
                  <th className="py-2 pr-4 text-right">Casos prováveis</th>
                  <th className="py-2 pr-4 text-right">Óbitos</th>
                  <th className="py-2 text-right">Semanas acima do P75</th>
                </tr>
              </thead>
              <tbody>
                {ufsAlertaDengue.map((u) => (
                  <tr key={u.uf} className="border-b border-ink-100">
                    <td className="py-2 pr-4 font-medium text-ink-900">{u.uf}</td>
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
          <div className="mt-4 overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-ink-200 text-left text-xs uppercase tracking-wide text-ink-500">
                  <th className="py-2 pr-4">UF</th>
                  <th className="py-2 pr-4 text-right">Óbitos</th>
                  <th className="py-2 pr-4 text-right">Esperado</th>
                  <th className="py-2 text-right">Excesso</th>
                </tr>
              </thead>
              <tbody>
                {ufsExcesso.map((u) => (
                  <tr key={u.uf} className="border-b border-ink-100">
                    <td className="py-2 pr-4 font-medium text-ink-900">{u.uf}</td>
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
                <span className="ml-2 text-xs text-ink-400">
                  {new Date(e.gerado_em).toLocaleDateString("pt-BR")}
                </span>
              </li>
            ))}
          </ul>
        </div>
      )}

      <div className="card mt-6 text-sm leading-relaxed text-ink-600">
        <p>
          <b>Fontes e método:</b> SIM, SINAN e SIH/DataSUS (Ministério da Saúde); população IBGE.
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

export default function BoletimSemanal() {
  return (
    <div className="mx-auto max-w-5xl px-4 py-10 sm:px-6">
      <Suspense fallback={<Skeleton altura={480} />}>
        <BoletimInner />
      </Suspense>
    </div>
  );
}
