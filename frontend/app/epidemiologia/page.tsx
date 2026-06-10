"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { getEpidemiologia, queryKeys } from "@/lib/api";
import { TimeSeries } from "@/components/TimeSeries";
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

const UFS = [
  "AC","AL","AM","AP","BA","CE","DF","ES","GO","MA",
  "MG","MS","MT","PA","PB","PE","PI","PR","RJ","RN",
  "RO","RR","RS","SC","SE","SP","TO",
];

const ANOS = ["2019","2020","2021","2022","2023","2024"];

/** Top CID-10 chapter groups for quick filter */
const CAPITULOS_CID = [
  { value: "all", label: "Todos os capítulos" },
  { value: "I",   label: "I — Infecciosas e parasitárias" },
  { value: "II",  label: "II — Neoplasias" },
  { value: "III", label: "III — Sangue / imune" },
  { value: "IV",  label: "IV — Metabólicas / endócrinas" },
  { value: "V",   label: "V — Transtornos mentais" },
  { value: "VI",  label: "VI-VIII — Sistema nervoso / sentidos" },
  { value: "IX",  label: "IX — Circulatório" },
  { value: "X",   label: "X — Respiratório" },
  { value: "XI",  label: "XI — Digestivo" },
  { value: "XIV", label: "XIV — Geniturinário" },
  { value: "XIX", label: "XIX — Lesões e envenenamentos" },
];

export default function EpidemiologiaPage() {
  const [uf, setUf]           = useState<string>("all");
  const [ano, setAno]         = useState<string>("all");
  const [capitulo, setCapitulo] = useState<string>("all");

  const params = {
    uf:        uf       !== "all" ? uf              : undefined,
    ano:       ano      !== "all" ? Number(ano)     : undefined,
    capitulo:  capitulo !== "all" ? capitulo        : undefined,
    tamanho:   200,
  };

  const { data, isLoading } = useQuery({
    queryKey: queryKeys.epidemiologia(params),
    queryFn:  () => getEpidemiologia(params),
  });

  const items = data?.items ?? [];

  // KPIs
  const totalAih    = items.reduce((s, r) => s + (r.total_aih    ?? 0), 0);
  const totalObitos = items.reduce((s, r) => s + (r.total_obitos ?? 0), 0);

  // Top-10 CID groups by AIH volume for the bar chart
  const byCid = Object.entries(
    items.reduce<Record<string, number>>((acc, r) => {
      const k = r.diag_princ_grupo ?? r.diag_princ ?? "Outros";
      acc[k] = (acc[k] ?? 0) + (r.total_aih ?? 0);
      return acc;
    }, {})
  )
    .sort((a, b) => b[1] - a[1])
    .slice(0, 10);
  const maxCidAih = byCid[0]?.[1] ?? 1;

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-1">
        <h1 className="text-2xl font-semibold tracking-tight">
          Epidemiologia por CID-10
        </h1>
        <p className="text-sm text-muted-foreground">
          Internações por diagnóstico principal — SIH/DATASUS
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

        <Select value={capitulo} onValueChange={setCapitulo}>
          <SelectTrigger className="w-72">
            <SelectValue placeholder="Capítulo CID-10" />
          </SelectTrigger>
          <SelectContent>
            {CAPITULOS_CID.map((c) => (
              <SelectItem key={c.value} value={c.value}>{c.label}</SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      {/* KPI cards */}
      <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
        {[
          {
            label: "Total de AIH",
            value: isLoading ? null : formatNumero(totalAih),
          },
          {
            label: "Total de óbitos",
            value: isLoading ? null : formatNumero(totalObitos),
          },
          {
            label: "Grupos CID distintos",
            value: isLoading ? null : formatNumero(byCid.length),
          },
          {
            label: "Registros",
            value: isLoading ? null : formatNumero(data?.meta.total ?? 0),
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

      <Tabs defaultValue="grupos">
        <TabsList>
          <TabsTrigger value="grupos">Por grupo CID</TabsTrigger>
          <TabsTrigger value="serie">Série temporal</TabsTrigger>
        </TabsList>

        {/* ── Top grupos ── */}
        <TabsContent value="grupos">
          <Card>
            <CardHeader>
              <CardTitle className="text-base">
                Top 10 grupos por volume de AIH
              </CardTitle>
              <CardDescription>
                Internações agrupadas por diagnóstico principal (CID-10)
              </CardDescription>
            </CardHeader>
            <CardContent>
              {isLoading ? (
                <div className="space-y-2">
                  {Array.from({ length: 8 }).map((_, i) => (
                    <Skeleton key={i} className="h-8 w-full" />
                  ))}
                </div>
              ) : !byCid.length ? (
                <p className="text-sm text-muted-foreground py-8 text-center">
                  Nenhum dado para os filtros selecionados.
                </p>
              ) : (
                <div className="space-y-2">
                  {byCid.map(([cid, aih], i) => (
                    <div key={cid} className="flex items-center gap-3">
                      <span className="w-6 shrink-0 text-xs text-muted-foreground tabular-nums text-right">
                        {i + 1}
                      </span>
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center justify-between mb-0.5">
                          <span className="text-sm truncate max-w-[260px]">
                            {cid}
                          </span>
                          <Badge
                            variant={i < 3 ? "default" : "outline"}
                            className="ml-2 shrink-0 tabular-nums text-xs"
                          >
                            {formatNumero(aih)}
                          </Badge>
                        </div>
                        <div className="h-1.5 w-full rounded-full bg-muted overflow-hidden">
                          <div
                            className="h-full rounded-full bg-primary transition-all duration-500"
                            style={{
                              width: `${((aih / maxCidAih) * 100).toFixed(1)}%`,
                            }}
                          />
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* ── Serie temporal ── */}
        <TabsContent value="serie">
          <Card>
            <CardHeader>
              <CardTitle className="text-base">
                Evolução mensal — AIH e óbitos
              </CardTitle>
              <CardDescription>
                Internações e mortalidade por diagnóstico ao longo do tempo
              </CardDescription>
            </CardHeader>
            <CardContent>
              {isLoading ? (
                <Skeleton className="h-[300px] w-full" />
              ) : (
                <TimeSeries
                  data={items.map((d) => ({
                    mes_competencia: `${d.ano_cmpt ?? d.ano}-${String(
                      d.mes_cmpt ?? d.mes ?? 1
                    ).padStart(2, "0")}`,
                    total_aih:    d.total_aih,
                    total_obitos: d.total_obitos,
                  }))}
                  series={[
                    {
                      dataKey: "total_aih",
                      label:   "AIH",
                      color:   "#16a34a",
                    },
                    {
                      dataKey: "total_obitos",
                      label:   "Óbitos",
                      color:   "#dc2626",
                    },
                  ]}
                  height={300}
                />
              )}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}
