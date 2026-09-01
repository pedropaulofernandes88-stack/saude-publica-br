"use client";

import Link from "next/link";
import { Suspense, useEffect, useMemo, useState } from "react";
import { useSearchParams } from "next/navigation";
import { Barras } from "@/components/charts";
import { Kpi, Skeleton } from "@/components/kpi";
import {
  Line, LineChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis,
} from "recharts";
import { IcsapPares } from "@/components/icsap-pares";
import { Imunopreveniveis as CardImuno } from "@/components/imunopreveniveis";
import { fmtDec, fmtInt, rest, sdata, type CapituloCid, type ClusterMunicipio, type IcsapPares as TIcsapPares, type Imunopreveniveis, type Ivs, type LinhaMunicipio } from "@/lib/api";
import { ehCodigoAgregado } from "@/lib/municipios";
import { EIXO, GRADE, REFERENCIA, SERIE } from "@/lib/tokens";

function SerieTaxas({ data }: { data: { ano: number; bruta: number | null; padronizada: number | null }[] }) {
  return (
    <ResponsiveContainer width="100%" height={300}>
      <LineChart data={data} margin={{ top: 8, right: 16, bottom: 0, left: 8 }}>
        <CartesianGrid stroke={GRADE} vertical={false} />
        <XAxis dataKey="ano" tick={{ fontSize: 12, fill: EIXO }} />
        <YAxis tick={{ fontSize: 12, fill: EIXO }} width={48} />
        <Tooltip
          formatter={(v, name) => [fmtDec(v as number), name === "padronizada" ? "Padronizada /100 mil" : "Bruta /100 mil"]}
          contentStyle={{ borderRadius: 8, borderColor: GRADE, fontSize: 13 }}
        />
        <Line type="monotone" dataKey="bruta" stroke={REFERENCIA} strokeWidth={2} strokeDasharray="5 4" dot={{ r: 2.5 }} />
        <Line type="monotone" dataKey="padronizada" stroke={SERIE} strokeWidth={2.5} dot={{ r: 3 }} />
      </LineChart>
    </ResponsiveContainer>
  );
}

function BoletimInner() {
  const params = useSearchParams();
  const cod = params.get("m") ?? "";
  const [linhas, setLinhas] = useState<LinhaMunicipio[] | null>(null);
  const [capitulos, setCapitulos] = useState<(LinhaMunicipio & { capitulo_cid: string })[] | null>(null);
  const [capsDim, setCapsDim] = useState<CapituloCid[]>([]);
  const [ivs, setIvs] = useState<Ivs | null>(null);
  const [cluster, setCluster] = useState<ClusterMunicipio | null>(null);
  const [icsap, setIcsap] = useState<TIcsapPares | null>(null);
  const [imuno, setImuno] = useState<{ mun: Imunopreveniveis; uf: Imunopreveniveis[] } | null>(null);
  const [erro, setErro] = useState<string | null>(null);

  useEffect(() => {
    if (!cod) return;
    setLinhas(null); setCapitulos(null); setErro(null);
    Promise.all([
      rest<LinhaMunicipio>("mart_mortalidade_municipio", {
        select: "municipio_cod,municipio_nome,uf_sigla,regiao,ano,obitos,obitos_hospital,obitos_domicilio,populacao,taxa_obitos_100k,ic95_inf,ic95_sup,taxa_padronizada_100k",
        municipio_cod: `eq.${cod}`,
        capitulo_cid: "eq.TOTAL",
        sexo: "eq.TOTAL",
        order: "ano",
      }),
      rest<LinhaMunicipio & { capitulo_cid: string }>("mart_mortalidade_municipio", {
        select: "capitulo_cid,obitos,ano",
        municipio_cod: `eq.${cod}`,
        sexo: "eq.TOTAL",
        capitulo_cid: "neq.TOTAL",
        order: "ano,capitulo_cid",
      }),
      sdata<CapituloCid[]>("capitulos"),
    ])
      .then(([l, c, dim]) => { setLinhas(l); setCapitulos(c); setCapsDim(dim); })
      .catch((e) => setErro(String(e)));
    rest<Ivs>("dim_ivs", {
      select: "municipio_cod,taxa_analfabetismo,pct_sem_agua,ivs_score,ivs_quartil",
      municipio_cod: `eq.${cod}`,
    }).then((r) => setIvs(r[0] ?? null)).catch(() => {});
    rest<ClusterMunicipio>("dim_cluster_municipio", {
      select: "municipio_cod,cluster,estrato_cod,perfil",
      municipio_cod: `eq.${cod}`,
    }).then((r) => setCluster(r[0] ?? null)).catch(() => {});
    // Grupo 1 do ICSAP: o município e os demais da mesma UF, para o número
    // ter contra o que ser lido. Taxa municipal isolada não diz se é alta.
    setImuno(null);
    rest<Imunopreveniveis>("mart_icsap_municipio", {
      select: "municipio_cod,uf_sigla,ano,internacoes_g1,g1_100k,internacoes_icsap",
      municipio_cod: `eq.${cod}`,
      order: "ano.desc",
      limit: "1",
    }).then(async (r) => {
      const mun = r[0];
      if (!mun) return;
      const uf = await rest<Imunopreveniveis>("mart_icsap_municipio", {
        select: "municipio_cod,uf_sigla,ano,internacoes_g1,g1_100k,internacoes_icsap",
        uf_sigla: `eq.${mun.uf_sigla}`,
        ano: `eq.${mun.ano}`,
      });
      setImuno({ mun, uf });
    }).catch(() => {});
    setIcsap(null);
    rest<TIcsapPares>("mart_icsap_pares", {
      select: "municipio_cod,municipio_nome,uf_sigla,ano,populacao,internacoes_total,internacoes_icsap,"
        + "pct_icsap,arquetipo,criterio_pares,n_pares,mediana_pares_pct,p25_pares_pct,diferenca_pp,"
        + "internacoes_acima_pares,internacoes_acima_p25,custo_associado_reais,leitos_dia_associados,"
        + "leitos_equivalentes_ano,custo_medio_icsap_ref,permanencia_media_icsap_ref,amostra_pequena",
      municipio_cod: `eq.${cod}`,
      // Sem ORDER BY o PostgREST devolve as linhas em ordem indefinida, e o
      // cartão mostrava um ano ARBITRÁRIO — Penápolis exibia 2022 enquanto
      // 2024 existia. Ficou invisível enquanto a view tinha um ano só; a
      // extensão do ICSAP para 2021–2024 expôs.
      order: "ano.desc",
      limit: "1",
    }).then((r) => setIcsap(r[0] ?? null)).catch(() => {});
  }, [cod]);

  const atual = useMemo(() => linhas?.length ? linhas[linhas.length - 1] : null, [linhas]);

  const serieTaxas = useMemo(
    () => linhas?.map((l) => ({ ano: l.ano, bruta: l.taxa_obitos_100k, padronizada: l.taxa_padronizada_100k })) ?? null,
    [linhas],
  );

  const capChart = useMemo(() => {
    if (!capitulos || !atual) return null;
    const doAno = capitulos.filter((c) => c.ano === atual.ano);
    return doAno
      .sort((a, b) => b.obitos - a.obitos)
      .slice(0, 8)
      .map((c) => ({ nome: c.capitulo_cid, obitos: c.obitos }));
  }, [capitulos, atual]);

  if (!cod) {
    return (
      <div className="card mx-auto mt-10 max-w-xl text-center">
        <p className="text-ink-700">
          Selecione um município no <Link href="/painel/" className="font-medium text-accent-700 underline">painel</Link>{" "}
          (clique no nome na tabela) para gerar o boletim.
        </p>
      </div>
    );
  }

  // "UF0000" é o código que o SIM usa para óbito sem município identificado —
  // existe no mart, mas não é um município e não rende boletim.
  if (ehCodigoAgregado(cod)) {
    return (
      <div className="card mx-auto mt-10 max-w-xl text-center">
        <p className="text-ink-700">
          O código <span className="font-mono">{cod}</span> não é um município: o SIM o usa para
          agrupar óbitos cujo município de residência não foi identificado. Escolha um município no{" "}
          <Link href="/painel/" className="font-medium text-accent-700 underline">painel</Link>.
        </p>
      </div>
    );
  }

  return (
    <>
      {erro && <div className="card mt-6 border-red-200 bg-red-50 text-sm text-red-800">Falha: {erro}</div>}
      {!atual && !erro && <Skeleton altura={400} />}
      {atual && (
        <>
          <div className="flex flex-wrap items-start justify-between gap-4">
            <div>
              <h1 className="font-serif text-3xl font-semibold tracking-tight text-ink-950">
                {atual.municipio_nome ?? cod} <span className="text-ink-500">· {atual.uf_sigla}</span>
              </h1>
              <p className="mt-1 text-ink-600">
                Boletim de mortalidade · {atual.regiao} · População {fmtInt(atual.populacao)} ({atual.ano})
              </p>
            </div>
            <button onClick={() => window.print()} className="btn-primary no-print">🖨 Imprimir / PDF</button>
          </div>

          <div className="mt-6 grid gap-4 sm:grid-cols-3">
            <Kpi rotulo={`Óbitos em ${atual.ano}`} valor={fmtInt(atual.obitos)}
                 detalhe={`${fmtInt(atual.obitos_hospital)} em hospital · ${fmtInt(atual.obitos_domicilio)} em domicílio`} />
            <Kpi rotulo="Taxa bruta /100 mil" valor={fmtDec(atual.taxa_obitos_100k)}
                 detalhe={atual.ic95_inf != null ? `IC95%: ${fmtDec(atual.ic95_inf)}–${fmtDec(atual.ic95_sup)}` : undefined} />
            <Kpi rotulo="Taxa padronizada /100 mil" valor={fmtDec(atual.taxa_padronizada_100k)}
                 detalhe="ajustada por idade — comparável entre municípios" />
          </div>
          {(atual.populacao ?? 0) < 10_000 && (
            <p className="mt-3 rounded-lg border border-amber-200 bg-amber-50 px-4 py-2 text-sm text-amber-800">
              ⚠ Município com população pequena: taxas anuais são instáveis. Interprete com o IC95%.
            </p>
          )}

          {ivs && (
            <div className="card mt-6">
              <h2 className="font-serif text-xl font-semibold text-ink-900">Contexto social (Censo 2022)</h2>
              <div className="mt-3 grid gap-4 sm:grid-cols-3">
                <div>
                  <p className="text-xs font-semibold uppercase tracking-wide text-ink-500">Vulnerabilidade (proxy)</p>
                  <p className="mt-1 font-serif text-2xl font-semibold text-ink-900">
                    {fmtDec(ivs.ivs_score, 0)}<span className="text-base text-ink-500">/100</span>
                    <span className="ml-2 rounded bg-ink-100 px-2 py-0.5 text-xs font-medium text-ink-600">{ivs.ivs_quartil}</span>
                  </p>
                </div>
                <div>
                  <p className="text-xs font-semibold uppercase tracking-wide text-ink-500">Analfabetismo (15+)</p>
                  <p className="mt-1 font-serif text-2xl font-semibold text-ink-900">{fmtDec(ivs.taxa_analfabetismo, 1)}%</p>
                </div>
                <div>
                  <p className="text-xs font-semibold uppercase tracking-wide text-ink-500">Sem água encanada</p>
                  <p className="mt-1 font-serif text-2xl font-semibold text-ink-900">{fmtDec(ivs.pct_sem_agua, 1)}%</p>
                </div>
              </div>
              <p className="mt-2 text-xs text-ink-500">
                Proxy de vulnerabilidade (z-score de analfabetismo e falta de água, Censo 2022) — quartil entre
                os 5.570 municípios; Q4 = mais vulnerável. Não é o IVS oficial do IPEA. Associações entre
                vulnerabilidade e saúde aqui são <strong>municipais</strong> (agregadas): descrevem padrões,
                não implicam risco individual nem causalidade (falácia ecológica).
              </p>
              {cluster && (
                <p className="mt-3 border-t border-ink-200 pt-3 text-sm text-ink-700">
                  <span className="font-semibold">Estrato de saúde:</span> {cluster.perfil}
                  <span className="ml-2 rounded bg-ink-100 px-2 py-0.5 text-xs text-ink-600">
                    {cluster.estrato_cod ? `${cluster.estrato_cod} · ` : ""}estrato {cluster.cluster}/27
                  </span>
                  <span className="mt-1 block text-xs text-ink-500">
                    Cruzamento dos tercis de mortalidade × vulnerabilidade × internações (2023), com cortes
                    fixos. O estrato depende só dos valores deste município — não muda entre consultas.
                  </span>
                </p>
              )}
            </div>
          )}

          {icsap && <IcsapPares dados={icsap} />}

          {imuno && <CardImuno mun={imuno.mun} uf={imuno.uf} />}

          <div className="card mt-6">
            <h2 className="font-serif text-xl font-semibold text-ink-900">Taxas de mortalidade, 2015–{atual.ano}</h2>
            <p className="mt-1 text-sm text-ink-500">Verde: padronizada por idade. Cinza tracejada: bruta.</p>
            <div className="mt-4">{serieTaxas ? <SerieTaxas data={serieTaxas} /> : <Skeleton altura={300} />}</div>
          </div>

          <div className="card mt-6">
            <h2 className="font-serif text-xl font-semibold text-ink-900">
              Principais grupos de causas ({atual.ano})
            </h2>
            <div className="mt-4">{capChart ? <Barras data={capChart} horizontal altura={300} titulo={`Principais grupos de causas (${atual.ano})`} /> : <Skeleton altura={300} />}</div>
            <div className="mt-3 grid gap-1 text-xs text-ink-500 sm:grid-cols-2">
              {capChart?.map((c) => {
                const d = capsDim.find((x) => x.capitulo === c.nome);
                return d ? <p key={c.nome}><b>{c.nome}</b>: {d.descricao}</p> : null;
              })}
            </div>
          </div>

          <div className="card mt-6 text-sm leading-relaxed text-ink-600">
            <p>
              <b>Fontes:</b> SIM/DataSUS (Ministério da Saúde) e IBGE (Censo 2022 e
              Estimativas). Óbitos não fetais, por município de residência. Padronização
              direta com padrão Brasil/Censo 2022; IC95% por método gamma. Ano mais
              recente pode ser preliminar. Metodologia completa:{" "}
              <span className="font-medium">saudeemdado.com/metodologia</span>.
            </p>
            <p className="mt-2">
              Gerado por <b>saudeemdado.com</b> — plataforma aberta e sem fins lucrativos.
              Boletim: <span className="font-mono">saudeemdado.com/boletim/?m={cod}</span>
            </p>
          </div>
        </>
      )}
    </>
  );
}

export function BoletimCliente() {
  return (
    <div className="mx-auto max-w-5xl px-4 py-10 sm:px-6">
      <Suspense fallback={<Skeleton altura={400} />}>
        <BoletimInner />
      </Suspense>
    </div>
  );
}
