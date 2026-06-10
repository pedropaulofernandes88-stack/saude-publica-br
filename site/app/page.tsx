"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { SerieLinha } from "@/components/charts";
import { Kpi, Skeleton } from "@/components/kpi";
import { fmtInt, rest, type MetaItem, type SerieMensal } from "@/lib/api";

interface HomeData {
  serie: { mes: string; obitos: number }[];
  total: number;
  municipios: number;
  geradoEm: string;
}

export default function Home() {
  const [data, setData] = useState<HomeData | null>(null);
  const [erro, setErro] = useState<string | null>(null);

  useEffect(() => {
    (async () => {
      try {
        const [serieRaw, meta] = await Promise.all([
          rest<SerieMensal>("mart_mortalidade_uf_mes", {
            select: "mes_competencia,uf_sigla,obitos",
            capitulo_cid: "eq.TOTAL",
            sexo: "eq.TOTAL",
            faixa_etaria: "eq.TOTAL",
            order: "mes_competencia,uf_sigla",
          }),
          rest<MetaItem>("meta_dataset", { select: "chave,valor" }),
        ]);
        const porMes = new Map<string, number>();
        for (const r of serieRaw) {
          porMes.set(r.mes_competencia, (porMes.get(r.mes_competencia) ?? 0) + r.obitos);
        }
        const serie = [...porMes.entries()]
          .sort(([a], [b]) => a.localeCompare(b))
          .map(([mes, obitos]) => ({ mes, obitos }));
        const geradoEm =
          meta.find((m) => m.chave === "gerado_em")?.valor.slice(0, 10) ?? "";
        setData({
          serie,
          total: serie.reduce((s, r) => s + r.obitos, 0),
          municipios: 5571,
          geradoEm,
        });
      } catch (e) {
        setErro(String(e));
      }
    })();
  }, []);

  return (
    <>
      {/* Hero */}
      <section className="border-b border-ink-200 bg-white">
        <div className="mx-auto max-w-7xl px-4 py-16 sm:px-6 sm:py-20">
          <p className="text-sm font-semibold uppercase tracking-widest text-accent-700">
            Dados abertos · SIM/DataSUS · IBGE
          </p>
          <h1 className="mt-3 max-w-3xl font-serif text-4xl font-semibold leading-tight tracking-tight text-ink-950 sm:text-5xl">
            A mortalidade no Brasil, acessível para a pesquisa.
          </h1>
          <p className="mt-5 max-w-2xl text-lg leading-relaxed text-ink-600">
            4,4 milhões de declarações de óbito (2022–2024) processadas a partir
            dos microdados oficiais do Ministério da Saúde — em painéis
            navegáveis, API pública gratuita e pipeline 100% reproduzível.
          </p>
          <div className="mt-8 flex flex-wrap gap-3">
            <Link href="/painel/" className="btn-primary">
              Explorar o painel →
            </Link>
            <Link href="/dados/" className="btn-ghost">
              Acessar via API
            </Link>
          </div>
        </div>
      </section>

      <section className="mx-auto max-w-7xl px-4 py-12 sm:px-6">
        {erro && (
          <div className="card border-red-200 bg-red-50 text-sm text-red-800">
            Falha ao carregar dados: {erro}
          </div>
        )}

        {/* KPIs */}
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <Kpi
            rotulo="Óbitos registrados"
            valor={data ? fmtInt(data.total) : "…"}
            detalhe="2022–2024, não fetais"
          />
          <Kpi rotulo="Municípios cobertos" valor={data ? fmtInt(data.municipios) : "…"} detalhe="Todos — base IBGE" />
          <Kpi rotulo="Causas (CID-10)" valor="22 capítulos" detalhe="+ categorias de 3 caracteres" />
          <Kpi
            rotulo="Última atualização"
            valor={data?.geradoEm ?? "…"}
            detalhe="Pipeline aberto e auditável"
          />
        </div>

        {/* Série nacional */}
        <div className="card mt-8">
          <div className="flex items-baseline justify-between">
            <h2 className="font-serif text-xl font-semibold text-ink-900">
              Óbitos mensais no Brasil — todas as causas
            </h2>
            <span className="text-xs text-ink-500">Fonte: SIM/DataSUS</span>
          </div>
          <div className="mt-4">
            {data ? <SerieLinha data={data.serie} /> : <Skeleton />}
          </div>
        </div>

        {/* Pilares de credibilidade */}
        <div className="mt-12 grid gap-4 sm:grid-cols-3">
          <div className="card">
            <h3 className="font-semibold text-ink-900">🔬 Reprodutível</h3>
            <p className="mt-2 text-sm leading-relaxed text-ink-600">
              Cada número pode ser regenerado a partir dos microdados oficiais com
              um único script aberto. Sem caixa-preta: a{" "}
              <Link href="/metodologia/" className="font-medium text-accent-700 hover:underline">
                metodologia
              </Link>{" "}
              documenta todas as decisões.
            </p>
          </div>
          <div className="card">
            <h3 className="font-semibold text-ink-900">🏛️ Fontes oficiais</h3>
            <p className="mt-2 text-sm leading-relaxed text-ink-600">
              Microdados do Sistema de Informações sobre Mortalidade
              (SIM/DataSUS) e população do IBGE (Censo 2022 e Estimativas) —
              ambos em domínio público.
            </p>
          </div>
          <div className="card">
            <h3 className="font-semibold text-ink-900">🔓 Acesso irrestrito</h3>
            <p className="mt-2 text-sm leading-relaxed text-ink-600">
              API REST gratuita, sem cadastro, com filtros por município, causa,
              sexo, faixa etária e período. Dados também disponíveis em Parquet
              para análise direta em R ou Python.
            </p>
          </div>
        </div>

        {/* Como citar */}
        <div className="card mt-12 bg-ink-950 text-ink-100">
          <h2 className="font-serif text-xl font-semibold text-white">Como citar</h2>
          <p className="mt-2 text-sm text-ink-300">
            Em trabalhos acadêmicos, cite as fontes primárias e a plataforma:
          </p>
          <pre className="mt-4 overflow-x-auto rounded-lg bg-black/40 p-4 text-xs leading-relaxed">
{`BRASIL. Ministério da Saúde. Sistema de Informações sobre Mortalidade (SIM).
Microdados abertos, OpenDataSUS, 2022–2024.

IBGE. Censo Demográfico 2022 e Estimativas de População. SIDRA.

Saúde Pública BR: plataforma aberta de indicadores de mortalidade.
Pipeline e agregações disponíveis em código aberto (MIT).`}
          </pre>
        </div>
      </section>
    </>
  );
}
