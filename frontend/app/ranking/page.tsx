"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { getInternacoesRanking, queryKeys } from "@/lib/api";
import type { RankingMetrica } from "@/lib/types";
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
import { Separator } from "@/components/ui/separator";
import { formatNumero, formatTaxa, formatReais } from "@/lib/utils";

const METRICAS: { value: RankingMetrica; label: string; unit: string }[] = [
  { value: "taxa_internacao", label: "Taxa de internação", unit: "/ 1k hab." },
  {
    value: "taxa_mortalidade_intra",
    label: "Taxa de mortalidade intra-hospitalar",
    unit: "%",
  },
];

const LIMITES = ["10", "20", "50"];

const ANOS = ["2019", "2020", "2021", "2022", "2023", "2024"];

export default function RankingPage() {
  const [metrica, setMetrica] = useState<RankingMetrica>("taxa_internacao");
  const [limite, setLimite] = useState<string>("20");
  const [ano, setAno] = useState<string>("all");

  const { data: ranking, isLoading } = useQuery({
    queryKey: queryKeys.ranking({
      metrica,
      limite: Number(limite),
      ano: ano !== "all" ? Number(ano) : undefined,
    }),
    queryFn: () =>
      getInternacoesRanking({
        metrica,
        limite: Number(limite),
        ano: ano !== "all" ? Number(ano) : undefined,
      }),
  });

  const metricaMeta = METRICAS.find((m) => m.value === metrica)!;

  const formatValor = (item: (typeof ranking)["items"][number]) => {
    if (metrica === "taxa_internacao")
      return `${formatTaxa(item.taxa_internacao ?? 0)} ${metricaMeta.unit}`;
    return `${formatTaxa(item.taxa_mortalidade_intra ?? 0)} ${metricaMeta.unit}`;
  };

  // Determine bar width relative to max value
  const maxVal = ranking?.items.reduce<number>((m, r) => {
    const v =
      metrica === "taxa_internacao"
        ? (r.taxa_internacao ?? 0)
        : (r.taxa_mortalidade_intra ?? 0);
    return Math.max(m, v);
  }, 0) ?? 1;

  const getBarPct = (item: (typeof ranking)["items"][number]) => {
    const v =
      metrica === "taxa_internacao"
        ? (item.taxa_internacao ?? 0)
        : (item.taxa_mortalidade_intra ?? 0);
    return ((v / (maxVal || 1)) * 100).toFixed(1);
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-1">
        <h1 className="text-2xl font-semibold tracking-tight">
          Ranking de Municípios
        </h1>
        <p className="text-sm text-muted-foreground">
          Classificação por indicador de saúde hospitalar — SIH/DATASUS
        </p>
      </div>

      <Separator />

      {/* Filters */}
      <div className="flex flex-wrap gap-3">
        <Select
          value={metrica}
          onValueChange={(v) => setMetrica(v as RankingMetrica)}
        >
          <SelectTrigger className="w-72">
            <SelectValue placeholder="Métrica" />
          </SelectTrigger>
          <SelectContent>
            {METRICAS.map((m) => (
              <SelectItem key={m.value} value={m.value}>
                {m.label}
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

        <Select value={limite} onValueChange={setLimite}>
          <SelectTrigger className="w-28">
            <SelectValue placeholder="Top N" />
          </SelectTrigger>
          <SelectContent>
            {LIMITES.map((l) => (
              <SelectItem key={l} value={l}>
                Top {l}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      {/* Chart card */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">{metricaMeta.label}</CardTitle>
          <CardDescription>
            Top {limite} municípios · {ano !== "all" ? `${ano}` : "período completo"}
          </CardDescription>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <div className="space-y-2">
              {Array.from({ length: 10 }).map((_, i) => (
                <Skeleton key={i} className="h-8 w-full" />
              ))}
            </div>
          ) : !ranking?.items.length ? (
            <p className="text-sm text-muted-foreground py-8 text-center">
              Nenhum dado encontrado para os filtros selecionados.
            </p>
          ) : (
            <div className="space-y-2">
              {ranking.items.map((item, i) => (
                <div key={item.cod_municipio} className="flex items-center gap-3">
                  {/* Rank */}
                  <span className="w-6 shrink-0 text-xs text-muted-foreground tabular-nums text-right">
                    {i + 1}
                  </span>

                  {/* Name + bar */}
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center justify-between mb-0.5">
                      <span className="text-sm truncate">
                        {item.nome_municipio ?? item.cod_municipio}
                      </span>
                      <Badge
                        variant={i < 3 ? "default" : "outline"}
                        className="ml-2 shrink-0 tabular-nums text-xs"
                      >
                        {formatValor(item)}
                      </Badge>
                    </div>
                    {/* Horizontal bar */}
                    <div className="h-1.5 w-full rounded-full bg-muted overflow-hidden">
                      <div
                        className="h-full rounded-full bg-primary transition-all duration-500"
                        style={{ width: `${getBarPct(item)}%` }}
                      />
                    </div>
                  </div>

                  {/* State badge */}
                  <span className="w-8 shrink-0 text-xs text-center text-muted-foreground">
                    {item.uf ?? "—"}
                  </span>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Secondary stats */}
      {!isLoading && ranking?.items.length ? (
        <div className="grid grid-cols-2 gap-4 sm:grid-cols-3">
          <Card>
            <CardHeader className="pb-1 pt-4 px-4">
              <CardDescription className="text-xs">
                1º lugar — {metricaMeta.label}
              </CardDescription>
            </CardHeader>
            <CardContent className="px-4 pb-4">
              <p className="text-base font-semibold leading-tight">
                {ranking.items[0].nome_municipio ?? ranking.items[0].cod_municipio}
              </p>
              <p className="text-2xl font-bold tabular-nums text-primary mt-1">
                {formatValor(ranking.items[0])}
              </p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="pb-1 pt-4 px-4">
              <CardDescription className="text-xs">
                Média do top {limite}
              </CardDescription>
            </CardHeader>
            <CardContent className="px-4 pb-4">
              <p className="text-2xl font-semibold tabular-nums">
                {(() => {
                  const vals = ranking.items.map((r) =>
                    metrica === "taxa_internacao"
                      ? (r.taxa_internacao ?? 0)
                      : (r.taxa_mortalidade_intra ?? 0)
                  );
                  const avg = vals.reduce((a, b) => a + b, 0) / vals.length;
                  return `${formatTaxa(avg)} ${metricaMeta.unit}`;
                })()}
              </p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="pb-1 pt-4 px-4">
              <CardDescription className="text-xs">
                Municípios no ranking
              </CardDescription>
            </CardHeader>
            <CardContent className="px-4 pb-4">
              <p className="text-2xl font-semibold tabular-nums">
                {formatNumero(ranking.items.length)}
              </p>
            </CardContent>
          </Card>
        </div>
      ) : null}
    </div>
  );
}
