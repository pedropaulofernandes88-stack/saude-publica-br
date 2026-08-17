"use client";

import {
  ResponsiveContainer,
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
} from "recharts";
import { formatMesCompetencia } from "@/lib/utils";

export interface TimeSeriesDataPoint {
  mes_competencia: string;
  [key: string]: string | number | null | undefined;
}

export interface TimeSeriesSeries {
  dataKey: string;
  label: string;
  color: string;
  unit?: string;
}

interface TimeSeriesProps {
  data: TimeSeriesDataPoint[];
  series: TimeSeriesSeries[];
  height?: number;
  xKey?: string;
}

export function TimeSeries({
  data,
  series,
  height = 300,
  xKey = "mes_competencia",
}: TimeSeriesProps) {
  if (!data || data.length === 0) {
    return (
      <div
        className="flex items-center justify-center text-muted-foreground text-sm"
        style={{ height }}
      >
        Sem dados disponíveis
      </div>
    );
  }

  return (
    <ResponsiveContainer width="100%" height={height}>
      <AreaChart data={data} margin={{ top: 4, right: 16, left: 0, bottom: 0 }}>
        <defs>
          {series.map((s) => (
            <linearGradient
              key={s.dataKey}
              id={`grad-${s.dataKey}`}
              x1="0"
              y1="0"
              x2="0"
              y2="1"
            >
              <stop offset="5%" stopColor={s.color} stopOpacity={0.15} />
              <stop offset="95%" stopColor={s.color} stopOpacity={0} />
            </linearGradient>
          ))}
        </defs>

        <CartesianGrid strokeDasharray="3 3" className="stroke-border" />

        <XAxis
          dataKey={xKey}
          tickFormatter={formatMesCompetencia}
          tick={{ fontSize: 11 }}
          tickLine={false}
          axisLine={false}
          interval="preserveStartEnd"
        />

        <YAxis
          tick={{ fontSize: 11 }}
          tickLine={false}
          axisLine={false}
          width={48}
        />

        <Tooltip
          labelFormatter={(v) => formatMesCompetencia(String(v))}
          formatter={(value: number, name: string) => {
            const s = series.find((s) => s.dataKey === name);
            return [
              value != null
                ? `${value.toLocaleString("pt-BR", { maximumFractionDigits: 2 })}${s?.unit ? ` ${s.unit}` : ""}`
                : "—",
              s?.label ?? name,
            ];
          }}
          contentStyle={{
            fontSize: 12,
            borderRadius: 6,
            border: "1px solid hsl(var(--border))",
            background: "hsl(var(--popover))",
            color: "hsl(var(--popover-foreground))",
          }}
        />

        <Legend
          formatter={(value) =>
            series.find((s) => s.dataKey === value)?.label ?? value
          }
          wrapperStyle={{ fontSize: 12 }}
        />

        {series.map((s) => (
          <Area
            key={s.dataKey}
            type="monotone"
            dataKey={s.dataKey}
            stroke={s.color}
            strokeWidth={2}
            fill={`url(#grad-${s.dataKey})`}
            dot={false}
            activeDot={{ r: 4 }}
            connectNulls
          />
        ))}
      </AreaChart>
    </ResponsiveContainer>
  );
}
