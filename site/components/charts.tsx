"use client";

import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Line,
  LineChart,
  ReferenceArea,
  ReferenceLine,
  ResponsiveContainer,
  Scatter,
  ScatterChart,
  Tooltip,
  XAxis,
  YAxis,
  ZAxis,
} from "recharts";
import { fmtDec, fmtInt } from "@/lib/api";
import { ALERTA, CATEGORIA, CORES_REGIAO, EIXO, GRADE, REFERENCIA, SERIE } from "@/lib/tokens";

/**
 * Envelope de acessibilidade dos gráficos.
 *
 * Um SVG do Recharts é inerte para tecnologia assistiva: sem role, sem nome e
 * sem alternativa. Aqui o gráfico vira uma imagem com nome e resumo, e os
 * números que ele desenha ficam disponíveis numa tabela — que serve tanto ao
 * leitor de tela quanto a quem só quer o valor exato sem passar o mouse.
 */
function Grafico({
  titulo,
  resumo,
  colunas,
  linhas,
  children,
}: {
  titulo: string;
  resumo: string;
  colunas: string[];
  linhas: (string | number)[][];
  children: React.ReactNode;
}) {
  return (
    <figure className="m-0">
      <div role="img" aria-label={`${titulo}. ${resumo}`}>
        {children}
      </div>
      <details className="grafico-dados mt-2 text-xs">
        <summary className="cursor-pointer text-ink-500 hover:text-accent-700">
          Ver os dados em tabela ({linhas.length} {linhas.length === 1 ? "linha" : "linhas"})
        </summary>
        <div className="mt-2 max-h-72 overflow-auto rounded border border-ink-200">
          <table className="w-full border-collapse text-left">
            <caption className="sr-only">{titulo} — dados do gráfico</caption>
            <thead className="sticky top-0 bg-ink-50">
              <tr>
                {colunas.map((c) => (
                  <th key={c} scope="col" className="border-b border-ink-200 px-3 py-1.5 font-semibold text-ink-800">
                    {c}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {linhas.map((l, i) => (
                <tr key={i}>
                  {l.map((v, j) => (
                    <td key={j} className="border-b border-ink-100 px-3 py-1 tabular-nums text-ink-700">
                      {v}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </details>
    </figure>
  );
}

/** Extremos de uma série, para o resumo textual. */
function extremos(vals: number[]): { min: number; max: number } {
  return { min: Math.min(...vals), max: Math.max(...vals) };
}


export function DispersaoVulnMort({
  data,
  titulo = "Vulnerabilidade social × mortalidade padronizada",
}: {
  data: { ivs: number; taxa_pad: number; pop: number; nome: string | null; uf: string; regiao: string | null }[];
  titulo?: string;
}) {
  const resumo = data.length
    ? `Gráfico de dispersão com ${fmtInt(data.length)} municípios. Eixo horizontal: vulnerabilidade social`
      + ` (proxy de 0 a 100); eixo vertical: taxa de mortalidade padronizada por 100 mil; o tamanho do ponto`
      + ` é a população e a cor, a região.`
    : "Sem dados no recorte selecionado.";

  return (
    <Grafico
      titulo={titulo}
      resumo={resumo}
      colunas={["Município", "UF", "Região", "Vulnerabilidade", "Taxa padroniz. /100 mil", "População"]}
      linhas={data.map((d) => [
        d.nome ?? "—",
        d.uf,
        d.regiao ?? "—",
        fmtDec(d.ivs, 0),
        fmtDec(d.taxa_pad, 0),
        fmtInt(d.pop),
      ])}
    >
    <ResponsiveContainer width="100%" height={420}>
      <ScatterChart margin={{ top: 8, right: 16, bottom: 18, left: 8 }}>
        <CartesianGrid stroke={GRADE} />
        <XAxis
          type="number" dataKey="ivs" name="Vulnerabilidade" domain={[0, 100]}
          tick={{ fontSize: 12, fill: EIXO }}
          label={{ value: "vulnerabilidade social (proxy 0–100)", position: "insideBottom", offset: -8, fontSize: 11, fill: REFERENCIA }}
        />
        <YAxis
          type="number" dataKey="taxa_pad" name="Taxa padronizada"
          tick={{ fontSize: 12, fill: EIXO }} width={52}
          label={{ value: "óbitos /100 mil (padroniz.)", angle: -90, position: "insideLeft", fontSize: 11, fill: REFERENCIA }}
        />
        <ZAxis type="number" dataKey="pop" range={[12, 240]} name="População" />
        <Tooltip
          cursor={{ strokeDasharray: "3 3" }}
          contentStyle={{ borderRadius: 8, borderColor: GRADE, fontSize: 13 }}
          formatter={(v, n) => [
            n === "Vulnerabilidade" ? fmtDec(v as number, 0)
              : n === "Taxa padronizada" ? fmtDec(v as number, 0)
              : fmtInt(v as number),
            n,
          ]}
          labelFormatter={() => ""}
          content={({ payload }) => {
            if (!payload || !payload.length) return null;
            const p = payload[0].payload as { nome: string; uf: string; ivs: number; taxa_pad: number; pop: number };
            return (
              <div style={{ background: "#fff", border: "1px solid #eceef2", borderRadius: 8, padding: "8px 10px", fontSize: 13 }}>
                <div style={{ fontWeight: 600 }}>{p.nome} · {p.uf}</div>
                <div>Vulnerabilidade: <b>{fmtDec(p.ivs, 0)}</b>/100</div>
                <div>Taxa padronizada: <b>{fmtDec(p.taxa_pad, 0)}</b> /100 mil</div>
                <div style={{ color: EIXO }}>População: {fmtInt(p.pop)}</div>
              </div>
            );
          }}
        />
        <Scatter data={data} fillOpacity={0.6}>
          {data.map((d, i) => (
            <Cell key={i} fill={CORES_REGIAO[d.regiao ?? ""] ?? "#94a3b8"} />
          ))}
        </Scatter>
      </ScatterChart>
    </ResponsiveContainer>
    </Grafico>
  );
}

// Apelidos locais herdados: os nomes de verdade vivem em @/lib/tokens.
const AXIS = { fontSize: 12, fill: EIXO };
const GRID = GRADE;
const ACCENT = SERIE;
const INK = CATEGORIA;

function compactPt(n: number): string {
  return n.toLocaleString("pt-BR", { notation: "compact", maximumFractionDigits: 1 });
}

function mesPt(iso: string): string {
  const d = new Date(`${iso}T00:00:00`);
  return d.toLocaleDateString("pt-BR", { month: "short", year: "2-digit" });
}

/**
 * Série mensal de óbitos. `incompletos` marca os meses da cauda que ainda estão
 * com registro parcial (atraso do SIM): eles são desenhados tracejados, sobre
 * faixa sombreada, para não serem lidos como queda de mortalidade.
 */
export function SerieLinha({
  data,
  incompletos,
  titulo = "Série mensal de óbitos",
}: {
  data: { mes: string; obitos: number }[];
  incompletos?: ReadonlySet<string>;
  titulo?: string;
}) {
  const temIncompletos = !!incompletos?.size;

  // Duas séries sobrepostas: a cheia vai até o último mês consolidado, a
  // tracejada cobre a cauda parcial. As duas compartilham o mês de junção
  // (o último completo) — sem isso a sólida atravessaria o trecho incompleto,
  // que é justamente o que se quer evitar, e a tracejada ficaria com um ponto
  // só, invisível.
  const primeiroIncompleto = temIncompletos
    ? data.findIndex((d) => incompletos!.has(d.mes))
    : -1;
  const juncao = primeiroIncompleto > 0 ? primeiroIncompleto - 1 : primeiroIncompleto;
  const dados = data.map((d, i) => ({
    ...d,
    consolidado: primeiroIncompleto < 0 || i <= juncao ? d.obitos : null,
    parcial: primeiroIncompleto >= 0 && i >= juncao ? d.obitos : null,
  }));

  const { min, max } = extremos(data.map((d) => d.obitos));
  const resumo = data.length
    ? `Série mensal com ${data.length} pontos, de ${mesPt(data[0].mes)} a ${mesPt(data[data.length - 1].mes)}.`
      + ` Mínimo ${fmtInt(min)}, máximo ${fmtInt(max)} óbitos.`
      + (temIncompletos
        ? ` Os ${incompletos!.size} últimos meses têm registro incompleto e aparecem tracejados.`
        : "")
    : "Sem dados no recorte selecionado.";

  return (
    <Grafico
      titulo={titulo}
      resumo={resumo}
      colunas={["Mês", "Óbitos", "Situação"]}
      linhas={data.map((d) => [
        mesPt(d.mes),
        fmtInt(d.obitos),
        incompletos?.has(d.mes) ? "parcial" : "consolidado",
      ])}
    >
    <ResponsiveContainer width="100%" height={320}>
      <LineChart data={dados} margin={{ top: 8, right: 16, bottom: 0, left: 8 }}>
        <CartesianGrid stroke={GRID} vertical={false} />
        <XAxis dataKey="mes" tick={AXIS} tickFormatter={mesPt} tickMargin={8} minTickGap={28} />
        <YAxis tick={AXIS} tickFormatter={compactPt} width={52} />
        <Tooltip
          formatter={(v, _n, item) => [
            `${fmtInt(v as number)}${incompletos?.has(String(item?.payload?.mes)) ? " (parcial)" : ""}`,
            "Óbitos",
          ]}
          labelFormatter={(l) =>
            new Date(`${l}T00:00:00`).toLocaleDateString("pt-BR", { month: "long", year: "numeric" })
          }
          contentStyle={{ borderRadius: 8, borderColor: GRID, fontSize: 13 }}
        />
        {primeiroIncompleto >= 0 && (
          <ReferenceArea
            x1={dados[juncao].mes}
            x2={dados[dados.length - 1].mes}
            fill={REFERENCIA}
            fillOpacity={0.1}
          />
        )}
        <Line type="monotone" dataKey="consolidado" stroke={ACCENT} strokeWidth={2.5} dot={false} activeDot={{ r: 4 }} />
        {temIncompletos && (
          <Line type="monotone" dataKey="parcial" stroke={ACCENT} strokeWidth={2} strokeDasharray="5 4"
                strokeOpacity={0.65} dot={false} activeDot={{ r: 4 }} />
        )}
      </LineChart>
    </ResponsiveContainer>
    </Grafico>
  );
}

/** Série mensal de cobertura da APS (%), com linha de referência em 100%. */
export function SerieCobertura({
  data,
  titulo = "Cobertura potencial da Atenção Primária",
}: {
  data: { mes: string; cobertura: number }[];
  titulo?: string;
}) {
  const { min, max } = data.length ? extremos(data.map((d) => d.cobertura)) : { min: 0, max: 0 };
  const resumo = data.length
    ? `Série mensal com ${data.length} pontos, de ${mesPt(data[0].mes)} a ${mesPt(data[data.length - 1].mes)}.`
      + ` Cobertura entre ${fmtDec(min, 1)}% e ${fmtDec(max, 1)}%, com linha de referência em 100%.`
    : "Sem dados no recorte selecionado.";

  return (
    <Grafico
      titulo={titulo}
      resumo={resumo}
      colunas={["Mês", "Cobertura (%)"]}
      linhas={data.map((d) => [mesPt(d.mes), `${fmtDec(d.cobertura, 1)}%`])}
    >
    <ResponsiveContainer width="100%" height={300}>
      <LineChart data={data} margin={{ top: 8, right: 16, bottom: 0, left: 8 }}>
        <CartesianGrid stroke={GRID} vertical={false} />
        <XAxis dataKey="mes" tick={AXIS} tickFormatter={mesPt} tickMargin={8} minTickGap={28} />
        <YAxis tick={AXIS} width={52} tickFormatter={(v) => `${v}%`} />
        <Tooltip
          formatter={(v) => [`${fmtDec(v as number, 1)}%`, "Cobertura potencial"]}
          labelFormatter={(l) =>
            new Date(`${l}T00:00:00`).toLocaleDateString("pt-BR", { month: "long", year: "numeric" })
          }
          contentStyle={{ borderRadius: 8, borderColor: GRID, fontSize: 13 }}
        />
        <ReferenceLine y={100} stroke={REFERENCIA} strokeDasharray="5 4"
                      label={{ value: "100%", position: "right", fontSize: 11, fill: REFERENCIA }} />
        <Line type="monotone" dataKey="cobertura" stroke={ACCENT} strokeWidth={2.5} dot={false} activeDot={{ r: 4 }} />
      </LineChart>
    </ResponsiveContainer>
    </Grafico>
  );
}

export function LinhasExcesso({
  data,
  titulo = "Óbitos observados vs. esperados",
}: {
  data: { mes: string; obitos: number; esperado: number }[];
  titulo?: string;
}) {
  const acima = data.filter((d) => d.obitos > d.esperado).length;
  const resumo = data.length
    ? `Duas séries mensais com ${data.length} pontos, de ${mesPt(data[0].mes)} a ${mesPt(data[data.length - 1].mes)}:`
      + ` óbitos observados e o esperado pelo baseline 2015–2019.`
      + ` O observado supera o esperado em ${acima} dos ${data.length} meses.`
    : "Sem dados no recorte selecionado.";

  return (
    <Grafico
      titulo={titulo}
      resumo={resumo}
      colunas={["Mês", "Observado", "Esperado", "Diferença"]}
      linhas={data.map((d) => [
        mesPt(d.mes),
        fmtInt(d.obitos),
        fmtInt(Math.round(d.esperado)),
        `${d.obitos >= d.esperado ? "+" : ""}${fmtInt(Math.round(d.obitos - d.esperado))}`,
      ])}
    >
    <ResponsiveContainer width="100%" height={340}>
      <LineChart data={data} margin={{ top: 8, right: 16, bottom: 0, left: 8 }}>
        <CartesianGrid stroke={GRID} vertical={false} />
        <XAxis dataKey="mes" tick={AXIS} tickFormatter={mesPt} tickMargin={8} minTickGap={28} />
        <YAxis tick={AXIS} tickFormatter={compactPt} width={56} />
        <Tooltip
          formatter={(v, name) => [fmtInt(Math.round(v as number)), name === "obitos" ? "Observado" : "Esperado (2015–2019)"]}
          labelFormatter={(l) =>
            new Date(`${l}T00:00:00`).toLocaleDateString("pt-BR", { month: "long", year: "numeric" })
          }
          contentStyle={{ borderRadius: 8, borderColor: GRID, fontSize: 13 }}
        />
        <Line type="monotone" dataKey="esperado" stroke={REFERENCIA} strokeWidth={2} strokeDasharray="6 4" dot={false} />
        <Line type="monotone" dataKey="obitos" stroke={ALERTA} strokeWidth={2.5} dot={false} activeDot={{ r: 4 }} />
      </LineChart>
    </ResponsiveContainer>
    </Grafico>
  );
}

export function Barras({
  data,
  cor = ACCENT,
  altura = 300,
  horizontal = false,
  titulo = "Distribuição por categoria",
  unidade = "Óbitos",
}: {
  data: { nome: string; obitos: number }[];
  cor?: string;
  altura?: number;
  horizontal?: boolean;
  titulo?: string;
  /** Rótulo da grandeza medida — nem todo uso deste gráfico é de óbitos. */
  unidade?: string;
}) {
  const { min, max } = data.length ? extremos(data.map((d) => d.obitos)) : { min: 0, max: 0 };
  const maior = data.length ? data.reduce((a, b) => (b.obitos > a.obitos ? b : a)) : null;
  const resumo = data.length
    ? `Gráfico de barras com ${data.length} categorias. Maior: ${maior!.nome}, ${fmtInt(max)}.`
      + ` Menor valor ${fmtInt(min)}. Unidade: ${unidade.toLowerCase()}.`
    : "Sem dados no recorte selecionado.";

  const grafico = horizontal ? (
      <ResponsiveContainer width="100%" height={altura}>
        <BarChart data={data} layout="vertical" margin={{ top: 4, right: 24, bottom: 0, left: 8 }}>
          <CartesianGrid stroke={GRID} horizontal={false} />
          <XAxis type="number" tick={AXIS} tickFormatter={compactPt} />
          <YAxis type="category" dataKey="nome" tick={{ ...AXIS, fill: INK }} width={88} />
          <Tooltip
            formatter={(v) => [fmtInt(v as number), unidade]}
            contentStyle={{ borderRadius: 8, borderColor: GRID, fontSize: 13 }}
          />
          <Bar dataKey="obitos" fill={cor} radius={[0, 4, 4, 0]} barSize={18} />
        </BarChart>
      </ResponsiveContainer>
  ) : (
    <ResponsiveContainer width="100%" height={altura}>
      <BarChart data={data} margin={{ top: 8, right: 16, bottom: 0, left: 8 }}>
        <CartesianGrid stroke={GRID} vertical={false} />
        <XAxis dataKey="nome" tick={AXIS} tickMargin={6} interval={0} angle={data.length > 10 ? -35 : 0} textAnchor={data.length > 10 ? "end" : "middle"} height={data.length > 10 ? 56 : 30} />
        <YAxis tick={AXIS} tickFormatter={compactPt} width={52} />
        <Tooltip
          formatter={(v) => [fmtInt(v as number), unidade]}
          contentStyle={{ borderRadius: 8, borderColor: GRID, fontSize: 13 }}
        />
        <Bar dataKey="obitos" fill={cor} radius={[4, 4, 0, 0]} />
      </BarChart>
    </ResponsiveContainer>
  );

  return (
    <Grafico
      titulo={titulo}
      resumo={resumo}
      colunas={["Categoria", unidade]}
      linhas={data.map((d) => [d.nome, fmtInt(d.obitos)])}
    >
      {grafico}
    </Grafico>
  );
}
