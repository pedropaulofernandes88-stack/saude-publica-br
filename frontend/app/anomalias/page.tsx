"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { getAnomalias, queryKeys } from "@/lib/api";
import type { AnomaliasSeveridade } from "@/lib/types";
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
import { formatNumero, formatTaxa, corSeveridade, formatMesCompetencia } from "@/lib/utils";
import { AlertTriangle, TrendingUp, TrendingDown, Minus } from "lucide-react";

const SEVERIDADES: { value: AnomaliasSeveridade | "all"; label: string }[] = [
  { value: "all",    label: "Todas as severidades" },
  { value: "critica", label: "Crítica" },
  { value: "alta",    label: "Alta" },
  { value: "media",   label: "Média" },
  { value: "baixa",   label: "Baixa" },
];

const TIPOS = [
  { value: "all",   label: "Todos os tipos" },
  { value: "spike", label: "Pico (spike)" },
  { value: "drop",  label: "Queda (drop)" },
  { value: "trend", label: "Tendência" },
  { value: "zscore", label: "Z-score alto" },
];

const UFS = [
  "AC","AL","AM","AP","BA","CE","DF","ES","GO","MA",
  "MG","MS","MT","PA","PB","PE","PI","PR","RJ","RN",
  "RO","RR","RS","SC","SE","SP","TO",
];

function DirecaoIcon({ tipo }: { tipo?: string | null }) {
  if (!tipo) return <Minus className="h-4 w-4 text-muted-foreground" />;
  if (tipo.toLowerCase().includes("spike") || tipo.toLowerCase().includes("up"))
    return <TrendingUp className="h-4 w-4 text-red-500" />;
  if (tipo.toLowerCase().includes("drop") || tipo.toLowerCase().includes("down"))
    return <TrendingDown className="h-4 w-4 text-blue-500" />;
  return <AlertTriangle className="h-4 w-4 text-yellow-500" />;
}

export default function AnomaliasPage() {
  const [severidade, setSeveridade] = useState<string>("all");
  const [tipo,       setTipo      ] = useState<string>("all");
  const [uf,         setUf        ] = useState<string>("all");

  const params = {
    severidade: severidade !== "all" ? (severidade as AnomaliasSeveridade) : undefined,
    tipo:       tipo       !== "all" ? tipo                                 : undefined,
    uf:         uf         !== "all" ? uf                                   : undefined,
    tamanho:    100,
  };

  const { data, isLoading } = useQuery({
    queryKey: queryKeys.anomalias(params),
    queryFn:  () => getAnomalias(params),
    refetchInterval: 60_000, // auto-refresh every minute
  });

  const items = data?.items ?? [];

  // Count by severity
  const countBySev = items.reduce<Record<string, number>>((acc, r) => {
    const s = r.severidade ?? "desconhecida";
    acc[s] = (acc[s] ?? 0) + 1;
    return acc;
  }, {});

  const sevOrder: AnomaliasSeveridade[] = ["critica", "alta", "media", "baixa"];

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-1">
        <h1 className="text-2xl font-semibold tracking-tight">
          Detecção de Anomalias
        </h1>
        <p className="text-sm text-muted-foreground">
          Alertas automáticos sobre padrões atípicos em internações e mortalidade
        </p>
      </div>

      <Separator />

      {/* Severity summary chips */}
      <div className="flex flex-wrap gap-2">
        {sevOrder.map((s) => (
          <div
            key={s}
            className="flex items-center gap-1.5 rounded-full border px-3 py-1 text-xs font-medium cursor-pointer transition-colors hover:bg-muted"
            onClick={() => setSeveridade(severidade === s ? "all" : s)}
            role="button"
          >
            <span
              className={`h-2 w-2 rounded-full ${
                s === "critica"
                  ? "bg-red-600"
                  : s === "alta"
                  ? "bg-orange-500"
                  : s === "media"
                  ? "bg-yellow-500"
                  : "bg-blue-400"
              }`}
            />
            <span className="capitalize">{s}</span>
            <Badge variant="secondary" className="h-4 text-[10px] px-1.5">
              {isLoading ? "…" : formatNumero(countBySev[s] ?? 0)}
            </Badge>
          </div>
        ))}
      </div>

      {/* Filters */}
      <div className="flex flex-wrap gap-3">
        <Select value={severidade} onValueChange={setSeveridade}>
          <SelectTrigger className="w-52">
            <SelectValue placeholder="Severidade" />
          </SelectTrigger>
          <SelectContent>
            {SEVERIDADES.map((s) => (
              <SelectItem key={s.value} value={s.value}>{s.label}</SelectItem>
            ))}
          </SelectContent>
        </Select>

        <Select value={tipo} onValueChange={setTipo}>
          <SelectTrigger className="w-48">
            <SelectValue placeholder="Tipo de anomalia" />
          </SelectTrigger>
          <SelectContent>
            {TIPOS.map((t) => (
              <SelectItem key={t.value} value={t.value}>{t.label}</SelectItem>
            ))}
          </SelectContent>
        </Select>

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
      </div>

      {/* Anomaly list */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base flex items-center gap-2">
            <AlertTriangle className="h-4 w-4 text-yellow-500" />
            Alertas detectados
          </CardTitle>
          <CardDescription>
            {isLoading
              ? "Carregando…"
              : `${formatNumero(data?.meta.total ?? 0)} anomalia(s) · atualização automática a cada minuto`}
          </CardDescription>
        </CardHeader>
        <CardContent className="p-0">
          {isLoading ? (
            <div className="space-y-px px-6 py-4">
              {Array.from({ length: 6 }).map((_, i) => (
                <Skeleton key={i} className="h-16 w-full mb-2" />
              ))}
            </div>
          ) : !items.length ? (
            <div className="flex flex-col items-center justify-center py-16 text-muted-foreground gap-2">
              <AlertTriangle className="h-8 w-8 opacity-30" />
              <p className="text-sm">Nenhuma anomalia nos filtros selecionados.</p>
            </div>
          ) : (
            <div className="divide-y">
              {items.map((item, i) => (
                <div
                  key={`${item.mes_competencia}-${item.indicador}-${i}`}
                  className="flex items-start gap-4 px-6 py-4 hover:bg-muted/40 transition-colors"
                >
                  {/* Direction icon */}
                  <div className="mt-0.5 shrink-0">
                    <DirecaoIcon tipo={item.tipo_anomalia} />
                  </div>

                  {/* Main content */}
                  <div className="flex-1 min-w-0">
                    <div className="flex flex-wrap items-center gap-2 mb-1">
                      <span className="font-medium text-sm">
                        {item.indicador ?? "Indicador desconhecido"}
                      </span>
                      <Badge variant={corSeveridade(item.severidade)} className="text-xs">
                        {item.severidade ?? "—"}
                      </Badge>
                      {item.tipo_anomalia && (
                        <Badge variant="outline" className="text-xs">
                          {item.tipo_anomalia}
                        </Badge>
                      )}
                    </div>

                    <p className="text-xs text-muted-foreground line-clamp-2">
                      {item.descricao ?? item.mensagem ?? "Sem descrição disponível."}
                    </p>

                    <div className="flex flex-wrap gap-3 mt-1.5 text-xs text-muted-foreground">
                      {item.mes_competencia && (
                        <span>
                          📅{" "}
                          {formatMesCompetencia(
                            typeof item.mes_competencia === "string"
                              ? item.mes_competencia
                              : String(item.mes_competencia)
                          )}
                        </span>
                      )}
                      {item.uf && <span>📍 {item.uf}</span>}
                      {item.cod_municipio && (
                        <span>🏙 {item.nome_municipio ?? item.cod_municipio}</span>
                      )}
                      {item.valor_observado != null && (
                        <span>
                          Observado:{" "}
                          <strong className="text-foreground">
                            {formatTaxa(item.valor_observado)}
                          </strong>
                        </span>
                      )}
                      {item.valor_esperado != null && (
                        <span>
                          Esperado:{" "}
                          <strong className="text-foreground">
                            {formatTaxa(item.valor_esperado)}
                          </strong>
                        </span>
                      )}
                      {item.zscore != null && (
                        <span>
                          Z-score:{" "}
                          <strong className="text-foreground">
                            {item.zscore.toFixed(2)}σ
                          </strong>
                        </span>
                      )}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
