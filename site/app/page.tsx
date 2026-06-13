"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { SerieLinha } from "@/components/charts";
import { Kpi, Skeleton } from "@/components/kpi";
import { fmtInt, sdata, type MetaItem, type SerieTotalItem } from "@/lib/api";

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
        // dados estáticos gerados no build — nenhuma chamada ao banco
        const [serieRaw, meta] = await Promise.all([
          sdata<SerieTotalItem[]>("serie_total"),
          sdata<MetaItem[]>("meta"),
        ]);
        const serie = serieRaw
          .filter((r) => r.uf_sigla === "BR")
          .sort((a, b) => a.mes_competencia.localeCompare(b.mes_competencia))
          .map((r) => ({ mes: r.mes_competencia, obitos: r.obitos }));
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
            Dados abertos · SIM · SINAN · SIH · DataSUS · IBGE
          </p>
          <h1 className="mt-3 max-w-3xl font-serif text-4xl font-semibold leading-tight tracking-tight text-ink-950 sm:text-5xl">
            A saúde do Brasil em dados, acessível para a pesquisa.
          </h1>
          <p className="mt-5 max-w-2xl text-lg leading-relaxed text-ink-600">
            Mortalidade, dengue e internações hospitalares do SUS — dezenas de
            milhões de registros oficiais (2015–2024) em painéis navegáveis, com
            taxas padronizadas, incidência epidemiológica, excesso de
            mortalidade, mapa municipal e API pública gratuita.
          </p>
          <div className="mt-8 flex flex-wrap gap-3">
            <Link href="/painel/" className="btn-primary">
              Explorar o painel →
            </Link>
            <Link href="/mapa/" className="btn-ghost">
              Mapa municipal
            </Link>
            <Link href="/tendencias/" className="btn-ghost">
              Excesso de mortalidade
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
            detalhe="2015–2024, não fetais"
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

        {/* Três domínios */}
        <div className="mt-12 grid gap-4 sm:grid-cols-3">
          <Link href="/painel/" className="card group transition hover:border-accent-400 hover:shadow-md">
            <h3 className="font-serif text-lg font-semibold text-ink-900">💀 Mortalidade <span className="text-ink-400">· SIM</span></h3>
            <p className="mt-2 text-sm leading-relaxed text-ink-600">
              14,4 milhões de óbitos (2015–2024) por causa, sexo e idade. Taxas
              padronizadas, IC95% e excesso de mortalidade.
            </p>
            <span className="mt-3 inline-block text-sm font-medium text-accent-700 group-hover:underline">Abrir painel →</span>
          </Link>
          <Link href="/dengue/" className="card group transition hover:border-accent-400 hover:shadow-md">
            <h3 className="font-serif text-lg font-semibold text-ink-900">🦟 Dengue <span className="text-ink-400">· SINAN</span></h3>
            <p className="mt-2 text-sm leading-relaxed text-ink-600">
              Casos prováveis, incidência e óbitos por semana epidemiológica,
              incluindo a epidemia recorde de 2024 (6,6 milhões de casos).
            </p>
            <span className="mt-3 inline-block text-sm font-medium text-accent-700 group-hover:underline">Ver dengue →</span>
          </Link>
          <Link href="/internacoes/" className="card group transition hover:border-accent-400 hover:shadow-md">
            <h3 className="font-serif text-lg font-semibold text-ink-900">🏥 Internações <span className="text-ink-400">· SIH</span></h3>
            <p className="mt-2 text-sm leading-relaxed text-ink-600">
              Internações pagas pelo SUS por município e causa: permanência
              média, mortalidade hospitalar e custo.
            </p>
            <span className="mt-3 inline-block text-sm font-medium text-accent-700 group-hover:underline">Ver internações →</span>
          </Link>
        </div>

        {/* Pilares de credibilidade */}
        <div className="mt-8 grid gap-4 sm:grid-cols-3">
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
              Microdados do DataSUS (SIM, SINAN, SIH) e população do IBGE
              (Censo 2022 e Estimativas) — todos em domínio público.
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
