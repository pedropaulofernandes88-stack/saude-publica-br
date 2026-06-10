"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  getMortalidade,
  getGeoJsonUFs,
  queryKeys,
} from "@/lib/api";
import type { MortalidadeParams } from "@/lib/types";
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

const CAUSAS = [
  { value: "all", label: "Todas as causas" },
  { value: "I", label: "Doenças cardiovasculares (I)" },
  { value: "C", label: "Neoplasias (C)" },
  { value: "J", label: "Respiratório (J)" },
  { value: "K", label: "Digestivo (K)" },
  { value: "A", label: "Infecciosas (A)" },
  { value: "B", label: "Infecciosas (B)" },
];

export default function MortalidadePage() {
  const [uf, setUf] = useState<string>("all");
  const [ano, setAno] = useState<string>("all");
  const [causa, setCausa] = useState<string>("all");

  const params: MortalidadeParams = {
    uf: uf !== "all" ? uf : undefined,
    ano: ano !== "all" ? Number(ano) : undefined,
    causa_basica: causa !== "all" ? causa : undefined,
    tamanho: 200,
  };

  const { data: mortalidade, isLoading: loadingMortalidade } = useQuery({
    queryKey: queryKeys.mortalidade(params),
    queryFn: () => getMortalidade(params),
  });

  const { data: geojson, isLoading: loadingGeo } = useQuery({
    queryKey: queryKeys.geoUFs,
    queryFn: getGeoJsonUFs,
    staleTime: Infinity,
  });

  const items = mortalidade?.items ?? [];

  // KPIs
  const totalObitos = items.reduce((s, r) => s + (r.total_obitos ?? 0), 0);
  const totalRegistros = mortalidade?.meta.total ?? 0;

  // Aggregate per UF for choropleth
  const obitosPerUF = items.reduce<Record<string, number>>((acc, r) => {
    if (r.uf) acc[r.uf] = (acc[r.uf] ?? 0) + (r.total_obitos ?? 0);
    return acc;
  }, {});
  const maxObitos = Math.max(...Object.values(obitosPerUF), 1);

  const choroplethGeo: FeatureCollection<Geometry, ChoroplethProperties> | null =
    geojson
      ? {
          type: "FeatureCollection",
          features: geojson.features.map((f) => {
            const sigla = f.properties?.sigla_uf ?? f.properties?.UF_05;
            const count = obitosPerUF[sigla] ?? null;
            return {
              ...f,
              properties: {
                id: sigla ?? "",
                value: count != null ? count / maxObitos : null,
                label: f.properties?.nome_uf ?? sigla,
              },
            } as typeof choroplethGeo.features[number];
          }),
        }
      : null;

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-1">
        <h1 className="text-2xl font-semibold tracking-tight">
          Mortalidade
        </h1>
        <p className="text-sm text-muted-foreground">
          Sistema de Informações sobre Mortalidade (SIM) — DATASUS
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
              <SelectItem key={u} value={u}>{u}</SelectItem>
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
              <SelectItem key={a} value={a}>{a}</SelectItem>
            ))}
          </SelectContent>
        </Select>

        <Select value={causa} onValueChange={setCausa}>
          <SelectTrigger className="w-56">
            <SelectValue placeholder="Causa básica (CID-10)" />
          </SelectTrigger>
          <SelectContent>
            {CAUSAS.map((c) => (
              <SelectItem key={c.value} value={c.value}>
                {c.label}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      {/* KPI cards */}
      <div className="grid grid-cols-2 gap-4 sm:grid-cols-3">
        {[
          {
            label: "Total de óbitos",
            value: loadingMortalidade ? null : formatNumero(totalObitos),
          },
          {
            label: "Registros no período",
            value: loadingMortalidade ? null : formatNumero(totalRegistros),
          },
          {
            label: "Estados com dados",
            value: loadingMortalidade
              ? null
              : formatNumero(Object.keys(obitosPerUF).length),
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

      <Tabs defaultValue="serie">
        <TabsList>
          <TabsTrigger value="serie">Série temporal</TabsTrigger>
          <TabsTrigger value="mapa">Mapa por UF</TabsTrigger>
        </TabsList>

        {/* ── Serie temporal ── */}
        <TabsContent value="serie">
          <Card>
            <CardHeader>
              <CardTitle className="text-base">
                Óbitos por mês de competência
              </CardTitle>
              <CardDescription>
                Total de óbitos registrados e taxa de mortalidade intra-hospitalar
              </CardDescription>
            </CardHeader>
            <CardContent>
              {loadingMortalidade ? (
                <Skeleton className="h-[300px] w-full" />
              ) : (
                <TimeSeries
                  data={items.map((d) => ({
                    mes_competencia: `${d.ano_obito ?? d.ano}-${String(
                      d.mes_obito ?? d.mes ?? 1
                    ).padStart(2, "0")}`,
                    total_obitos: d.total_obitos,
                    taxa_mortalidade: d.taxa_mortalidade,
                  }))}
                  series={[
                    {
                      dataKey: "total_obitos",
                      label: "Total óbitos",
                      color: "#dc2626",
                    },
                    {
                      dataKey: "taxa_mortalidade",
                      label: "Taxa mortalidade (%)",
                      color: "#f97316",
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
                Distribuição de óbitos por UF
              </CardTitle>
              <CardDescription>
                Volume total de óbitos — escala relativa
              </CardDescription>
            </CardHeader>
            <CardContent>
              {loadingGeo || loadingMortalidade || !choroplethGeo ? (
                <Skeleton className="h-[420px] w-full" />
              ) : (
                <ChoroplethMap
                  geojson={choroplethGeo}
                  highColor={[220, 38, 38]}
                  lowColor={[254, 226, 226]}
                  height={420}
                  getTooltip={(f) => {
                    const v = f.properties.value;
                    const count = v != null ? Math.round(v * maxObitos) : null;
                    return `<strong>${f.properties.label}</strong><br/>Óbitos: ${
                      count != null ? formatNumero(count) : "sem dados"
                    }`;
                  }}
                />
              )}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}
