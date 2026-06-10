"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  getInternacoes,
  getInternacoesRanking,
  getGeoJsonMunicipios,
  queryKeys,
} from "@/lib/api";
import type { InternacoesParams } from "@/lib/types";
import { TimeSeries } from "@/components/TimeSeries";
import { ChoroplethMap } from "@/components/Map";
import type { ChoroplethProperties } from "@/components/Map";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { Badge } from "@/components/ui/badge";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Separator } from "@/components/ui/separator";
import { formatNumero, formatTaxa } from "@/lib/utils";
import type { FeatureCollection, Geometry } from "geojson";

const UFS = [
  "AC","AL","AM","AP","BA","CE","DF","ES","GO","MA",
  "MG","MS","MT","PA","PB","PE","PI","PR","RJ","RN",
  "RO","RR","RS","SC","SE","SP","TO",
];

const ANOS = ["2019","2020","2021","2022","2023","2024"];

export default function InternacoesPage() {
  const [uf, setUf] = useState<string>("all");
  const [ano, setAno] = useState<string>("all");

  const params: InternacoesParams = {
    uf: uf !== "all" ? uf : undefined,
    ano: ano !== "all" ? Number(ano) : undefined,
    tamanho: 200,
  };

  const { data: internacoes, isLoading: loadingInternacoes } = useQuery({
    queryKey: queryKeys.internacoes(params),
    queryFn: () => getInternacoes(params),
  });

  const { data: ranking, isLoading: loadingRanking } = useQuery({
    queryKey: queryKeys.ranking({ metrica: "taxa_internacao", limite: 20 }),
    queryFn: () => getInternacoesRanking({ metrica: "taxa_internacao", limite: 20 }),
  });

  const { data: geojson, isLoading: loadingGeo } = useQuery({
    queryKey: queryKeys.geoMunicipios,
    queryFn: getGeoJsonMunicipios,
    staleTime: Infinity,
  });

  // ── Derived series data for the time-series chart ──────────────────────────
  const seriesData = internacoes?.items ?? [];

  // ── Aggregate KPIs from current page ──────────────────────────────────────
  const totalAih = seriesData.reduce(
    (s, r) => s + (r.total_aih ?? 0),
    0
  );
  const mediaObitos = seriesData.length
    ? seriesData.reduce((s, r) => s + (r.obitos ?? 0), 0) / seriesData.length
    : null;

  // ── Build choropleth geojson ───────────────────────────────────────────────
  // Normalise taxa_internacao across ranking for colour scale
  const maxTaxa =
    ranking?.items.reduce(
      (m, r) => Math.max(m, r.taxa_internacao ?? 0),
      0
    ) ?? 1;

  const choroplethGeo: FeatureCollection<Geometry, ChoroplethProperties> | null =
    geojson
      ? {
          type: "FeatureCollection",
          features: geojson.features.map((f) => {
            const cod = f.properties?.cod_municipio;
            const match = ranking?.items.find(
              (r) => String(r.cod_municipio) === String(cod)
            );
            return {
              ...f,
              properties: {
                id: cod ?? "",
                value: match?.taxa_internacao != null
                  ? match.taxa_internacao / (maxTaxa || 1)
                  : null,
                label: f.properties?.nome_municipio ?? String(cod),
              },
            } as typeof choroplethGeo.features[number];
          }),
        }
      : null;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col gap-1">
        <h1 className="text-2xl font-semibold tracking-tight">
          Internações Hospitalares
        </h1>
        <p className="text-sm text-muted-foreground">
          Autorizações de Internação Hospitalar (AIH) — SIH/DATASUS
        </p>
      </div>

      <Separator />

      {/* Filters */}
      <div className="flex flex-wrap gap-3">
        <Select value={uf} onValueChange={setUf}>
          <SelectTrigger className="w-36">
            <SelectValue placeholder="UF" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">Todos os estados</SelectItem>
            {UFS.map((u) => (
              <SelectItem key={u} value={u}>
                {u}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>

        <Select value={ano} onValueChange={setAno}>
          <SelectTrigger className="w-32">
            <SelectValue placeholder="Ano" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">Todos os anos</SelectItem>
            {ANOS.map((a) => (
              <SelectItem key={a} value={a}>
                {a}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      {/* KPI cards */}
      <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
        {[
          {
            label: "Total de AIH",
            value: loadingInternacoes ? null : formatNumero(totalAih),
          },
          {
            label: "Registros no período",
            value: loadingInternacoes
              ? null
              : formatNumero(internacoes?.meta.total ?? 0),
          },
          {
            label: "Média de óbitos / mês",
            value: loadingInternacoes
              ? null
              : mediaObitos != null
              ? formatNumero(Math.round(mediaObitos))
              : "—",
          },
          {
            label: "Cidades no ranking",
            value: loadingRanking
              ? null
              : formatNumero(ranking?.items.length ?? 0),
          },
        ].map(({ label, value }) => (
          <Card key={label}>
            <CardHeader className="pb-1 pt-4 px-4">
              <CardDescription className="text-xs">{label}</CardDescription>
            </CardHeader>
            <CardContent className="px-4 pb-4">
              {value == null ? (
                <Skeleton className="h-7 w-24" />
              ) : (
                <p className="text-2xl font-semibold tabular-nums">{value}</p>
              )}
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Main content tabs */}
      <Tabs defaultValue="serie">
        <TabsList>
          <TabsTrigger value="serie">Série temporal</TabsTrigger>
          <TabsTrigger value="mapa">Mapa</TabsTrigger>
          <TabsTrigger value="ranking">Ranking</TabsTrigger>
        </TabsList>

        {/* ── Serie temporal ── */}
        <TabsContent value="serie">
          <Card>
            <CardHeader>
              <CardTitle className="text-base">
                Evolução mensal de internações
              </CardTitle>
              <CardDescription>
                Total de AIH e taxa de mortalidade intra-hospitalar
              </CardDescription>
            </CardHeader>
            <CardContent>
              {loadingInternacoes ? (
                <Skeleton className="h-[300px] w-full" />
              ) : (
                <TimeSeries
                  data={seriesData.map((d) => ({
                    mes_competencia: `${d.ano_cmpt}-${String(d.mes_cmpt).padStart(2, "0")}`,
                    total_aih: d.total_aih,
                    taxa_mortalidade: d.taxa_mortalidade_intra,
                  }))}
                  series={[
                    {
                      dataKey: "total_aih",
                      label: "Total AIH",
                      color: "#16a34a",
                    },
                    {
                      dataKey: "taxa_mortalidade",
                      label: "Taxa mortalidade (%)",
                      color: "#dc2626",
                      unit: "%",
                    },
                  ]}
                  height={300}
                />
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* ── Mapa ── */}
        <TabsContent value="mapa">
          <Card>
            <CardHeader>
              <CardTitle className="text-base">
                Taxa de internação por município
              </CardTitle>
              <CardDescription>
                Internações por 1.000 habitantes — top 20 municípios
              </CardDescription>
            </CardHeader>
            <CardContent>
              {loadingGeo || loadingRanking || !choroplethGeo ? (
                <Skeleton className="h-[420px] w-full" />
              ) : (
                <ChoroplethMap
                  geojson={choroplethGeo}
                  height={420}
                  getTooltip={(f) => {
                    const val = f.properties.value;
                    const taxa =
                      val != null
                        ? formatTaxa(val * (maxTaxa || 1))
                        : "sem dados";
                    return `<strong>${f.properties.label}</strong><br/>Taxa: ${taxa} / 1.000 hab.`;
                  }}
                />
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* ── Ranking ── */}
        <TabsContent value="ranking">
          <Card>
            <CardHeader>
              <CardTitle className="text-base">
                Top 20 municípios — taxa de internação
              </CardTitle>
              <CardDescription>
                Internações por 1.000 habitantes
              </CardDescription>
            </CardHeader>
            <CardContent>
              {loadingRanking ? (
                <Skeleton className="h-64 w-full" />
              ) : (
                <div className="space-y-1">
                  {ranking?.items.map((item, i) => (
                    <div
                      key={item.cod_municipio}
                      className="flex items-center gap-3 py-1.5 border-b last:border-0"
                    >
                      <span className="w-6 text-xs text-muted-foreground tabular-nums">
                        {i + 1}.
                      </span>
                      <span className="flex-1 text-sm">
                        {item.nome_municipio ?? item.cod_municipio}
                      </span>
                      <Badge variant="outline" className="tabular-nums text-xs">
                        {formatTaxa(item.taxa_internacao ?? 0)} / 1k
                      </Badge>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}
