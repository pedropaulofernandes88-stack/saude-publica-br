"use client";

import {
  Bar,
  BarChart,
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { fmtInt } from "@/lib/api";

const AXIS = { fontSize: 12, fill: "#677791" };
const GRID = "#eceef2";
const ACCENT = "#107752";
const INK = "#3a4253";

function compactPt(n: number): string {
  return n.toLocaleString("pt-BR", { notation: "compact", maximumFractionDigits: 1 });
}

function mesPt(iso: string): string {
  const d = new Date(`${iso}T00:00:00`);
  return d.toLocaleDateString("pt-BR", { month: "short", year: "2-digit" });
}

export function SerieLinha({ data }: { data: { mes: string; obitos: number }[] }) {
  return (
    <ResponsiveContainer width="100%" height={320}>
      <LineChart data={data} margin={{ top: 8, right: 16, bottom: 0, left: 8 }}>
        <CartesianGrid stroke={GRID} vertical={false} />
        <XAxis dataKey="mes" tick={AXIS} tickFormatter={mesPt} tickMargin={8} minTickGap={28} />
        <YAxis tick={AXIS} tickFormatter={compactPt} width={52} />
        <Tooltip
          formatter={(v) => [fmtInt(v as number), "Óbitos"]}
          labelFormatter={(l) =>
            new Date(`${l}T00:00:00`).toLocaleDateString("pt-BR", { month: "long", year: "numeric" })
          }
          contentStyle={{ borderRadius: 8, borderColor: GRID, fontSize: 13 }}
        />
        <Line type="monotone" dataKey="obitos" stroke={ACCENT} strokeWidth={2.5} dot={false} activeDot={{ r: 4 }} />
      </LineChart>
    </ResponsiveContainer>
  );
}

export function Barras({
  data,
  cor = ACCENT,
  altura = 300,
  horizontal = false,
}: {
  data: { nome: string; obitos: number }[];
  cor?: string;
  altura?: number;
  horizontal?: boolean;
}) {
  if (horizontal) {
    return (
      <ResponsiveContainer width="100%" height={altura}>
        <BarChart data={data} layout="vertical" margin={{ top: 4, right: 24, bottom: 0, left: 8 }}>
          <CartesianGrid stroke={GRID} horizontal={false} />
          <XAxis type="number" tick={AXIS} tickFormatter={compactPt} />
          <YAxis type="category" dataKey="nome" tick={{ ...AXIS, fill: INK }} width={88} />
          <Tooltip
            formatter={(v) => [fmtInt(v as number), "Óbitos"]}
            contentStyle={{ borderRadius: 8, borderColor: GRID, fontSize: 13 }}
          />
          <Bar dataKey="obitos" fill={cor} radius={[0, 4, 4, 0]} barSize={18} />
        </BarChart>
      </ResponsiveContainer>
    );
  }
  return (
    <ResponsiveContainer width="100%" height={altura}>
      <BarChart data={data} margin={{ top: 8, right: 16, bottom: 0, left: 8 }}>
        <CartesianGrid stroke={GRID} vertical={false} />
        <XAxis dataKey="nome" tick={AXIS} tickMargin={6} interval={0} angle={data.length > 10 ? -35 : 0} textAnchor={data.length > 10 ? "end" : "middle"} height={data.length > 10 ? 56 : 30} />
        <YAxis tick={AXIS} tickFormatter={compactPt} width={52} />
        <Tooltip
          formatter={(v) => [fmtInt(v as number), "Óbitos"]}
          contentStyle={{ borderRadius: 8, borderColor: GRID, fontSize: 13 }}
        />
        <Bar dataKey="obitos" fill={cor} radius={[4, 4, 0, 0]} />
      </BarChart>
    </ResponsiveContainer>
  );
}
