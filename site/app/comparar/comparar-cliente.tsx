"use client";

import { Suspense, useCallback, useEffect, useMemo, useState } from "react";
import { useSearchParams } from "next/navigation";
import {
  CartesianGrid, Legend, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis,
} from "recharts";
import { Skeleton } from "@/components/kpi";
import { FichaIndicador } from "@/components/ficha-indicador";
import { ehPreliminar, fmtDec, fmtInt, rest, sdata, type ClusterMunicipio, type Ivs, type LinhaMunicipio } from "@/lib/api";
import { casaMunicipio } from "@/lib/busca";
import { EIXO, GRADE } from "@/lib/tokens";

/**
 * Comparador de municípios — e a comparabilidade dita antes do gráfico.
 *
 * POR QUE ELE EXISTE
 * ------------------
 * Comparar dois municípios era possível e trabalhoso: abrir o painel, filtrar,
 * anotar, trocar o filtro, anotar de novo. E era possível fazer errado sem
 * perceber, porque o painel não impede comparar a taxa BRUTA de uma cidade
 * envelhecida com a de uma cidade jovem.
 *
 * A PÁGINA COMEÇA PELA RESSALVA, NÃO TERMINA NELA
 * ------------------------------------------------
 * A regra deste projeto é que a cautela acompanhe o número. Aqui ela vem antes:
 * a série exibida por padrão é a PADRONIZADA por idade, e o quadro de
 * comparabilidade — porte, estrato de saúde e vulnerabilidade — fica acima do
 * gráfico, com aviso explícito quando os municípios escolhidos têm portes muito
 * diferentes. Um comparador que deixa o usuário montar a comparação errada em
 * silêncio é pior que nenhum.
 *
 * Limite de cinco: acima disso o gráfico vira emaranhado e a comparação deixa
 * de ser leitura para virar decoração.
 */

const MAX = 5;
const CORES = ["#0b5f4c", "#b45309", "#1d4ed8", "#9d174d", "#3f6212"];

type Linha = [cod: string, nome: string, uf: string];

function CardComparabilidade({
  escolhidos, ivs, clusters, ultimo,
}: {
  escolhidos: Linha[];
  ivs: Record<string, Ivs>;
  clusters: Record<string, ClusterMunicipio>;
  ultimo: Record<string, LinhaMunicipio>;
}) {
  const pops = escolhidos.map((m) => ultimo[m[0]]?.populacao ?? 0).filter((p) => p > 0);
  const razaoPorte = pops.length > 1 ? Math.max(...pops) / Math.min(...pops) : 1;

  return (
    <div className="card mt-6">
      <h2 className="font-serif text-xl font-semibold text-ink-900">Estes municípios são comparáveis?</h2>
      <p className="mt-1 text-sm text-ink-500">
        A taxa padronizada por idade corrige a estrutura etária, que é a diferença que mais
        distorce comparação entre municípios. Ela <strong>não</strong> corrige porte, oferta
        hospitalar nem qualidade do registro — por isso eles ficam à vista.
      </p>

      <div className="mt-4 overflow-x-auto">
        <table className="w-full min-w-[560px] text-sm">
          <thead>
            <tr className="border-b-2 border-ink-200 text-left text-xs uppercase tracking-wide text-ink-500">
              <th className="px-2 py-2">Município</th>
              <th className="px-2 py-2 text-right">População</th>
              <th className="px-2 py-2">Vulnerabilidade</th>
              <th className="px-2 py-2">Estrato de saúde</th>
            </tr>
          </thead>
          <tbody>
            {escolhidos.map((m, i) => (
              <tr key={m[0]} className="border-b border-ink-100">
                <td className="px-2 py-2 font-medium text-ink-900">
                  <span className="mr-2 inline-block h-2.5 w-2.5 rounded-full" style={{ background: CORES[i] }} />
                  {m[1]} <span className="text-ink-500">· {m[2]}</span>
                </td>
                <td className="px-2 py-2 text-right tabular-nums">
                  {ultimo[m[0]]?.populacao ? fmtInt(ultimo[m[0]].populacao!) : "—"}
                </td>
                <td className="px-2 py-2 text-ink-700">
                  {ivs[m[0]] ? `${fmtDec(ivs[m[0]].ivs_score, 0)}/100 · ${ivs[m[0]].ivs_quartil}` : "—"}
                </td>
                <td className="px-2 py-2 text-ink-700">{clusters[m[0]]?.perfil ?? "—"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {razaoPorte >= 5 && (
        <p className="mt-3 rounded-lg border border-amber-200 bg-amber-50 px-4 py-2 text-sm text-amber-800">
          ⚠ O maior destes municípios tem <strong>{fmtDec(razaoPorte, 1)}×</strong> a população do
          menor. A taxa padronizada continua válida, mas a do município pequeno oscila muito de um
          ano para o outro por acaso — leia a série dele pela tendência, não pelo ponto, e confira o
          IC95% no boletim.
        </p>
      )}
    </div>
  );
}

function CompararInner() {
  const params = useSearchParams();
  const [lista, setLista] = useState<Linha[] | null>(null);
  const [codigos, setCodigos] = useState<string[]>(
    () => (params.get("m") ?? "").split(",").map((c) => c.trim()).filter(Boolean).slice(0, MAX),
  );
  const [termo, setTermo] = useState("");
  const [series, setSeries] = useState<LinhaMunicipio[] | null>(null);
  const [ivs, setIvs] = useState<Record<string, Ivs>>({});
  const [clusters, setClusters] = useState<Record<string, ClusterMunicipio>>({});
  const [metrica, setMetrica] = useState<"taxa_padronizada_100k" | "taxa_obitos_100k" | "obitos">("taxa_padronizada_100k");
  const [copiado, setCopiado] = useState(false);

  useEffect(() => { sdata<Linha[]>("municipios").then(setLista).catch(() => setLista([])); }, []);

  useEffect(() => {
    if (typeof window === "undefined") return;
    window.history.replaceState(null, "", codigos.length ? `?m=${codigos.join(",")}` : window.location.pathname);
    setCopiado(false);
  }, [codigos]);

  useEffect(() => {
    if (!codigos.length) { setSeries([]); return; }
    setSeries(null);
    const filtro = `in.(${codigos.join(",")})`;
    rest<LinhaMunicipio>("mart_mortalidade_municipio", {
      select: "municipio_cod,municipio_nome,uf_sigla,ano,obitos,populacao,taxa_obitos_100k,taxa_padronizada_100k,ic95_inf,ic95_sup",
      municipio_cod: filtro, capitulo_cid: "eq.TOTAL", sexo: "eq.TOTAL", order: "ano",
    }).then(setSeries).catch(() => setSeries([]));
    rest<Ivs>("dim_ivs", {
      select: "municipio_cod,taxa_analfabetismo,pct_sem_agua,ivs_score,ivs_quartil",
      municipio_cod: filtro,
    }).then((r) => setIvs(Object.fromEntries(r.map((x) => [x.municipio_cod, x])))).catch(() => {});
    rest<ClusterMunicipio>("dim_cluster_municipio", {
      select: "municipio_cod,cluster,estrato_cod,perfil", municipio_cod: filtro,
    }).then((r) => setClusters(Object.fromEntries(r.map((x) => [x.municipio_cod, x])))).catch(() => {});
  }, [codigos]);

  const escolhidos: Linha[] = useMemo(
    () => codigos.map((c) => lista?.find((l) => l[0] === c) ?? [c, c, ""] as Linha),
    [codigos, lista],
  );

  const sugestoes = useMemo(() => {
    const q = termo.trim();
    if (!q || !lista) return [];
    return lista
      .filter(([cod, nome]) => casaMunicipio(q, nome, cod))
      .filter(([cod]) => !codigos.includes(cod))
      .slice(0, 6);
  }, [termo, lista, codigos]);

  /** Uma linha por ano, uma coluna por município — o formato que o gráfico lê. */
  const dados = useMemo(() => {
    if (!series?.length) return [];
    const anos = [...new Set(series.map((r) => r.ano))].sort((a, b) => a - b);
    return anos.map((ano) => {
      const linha: Record<string, number | string | null> = { ano };
      for (const c of codigos) {
        const r = series.find((x) => x.municipio_cod === c && x.ano === ano);
        linha[c] = r ? (r[metrica] as number | null) : null;
      }
      return linha;
    });
  }, [series, codigos, metrica]);

  const ultimo = useMemo(() => {
    const fora: Record<string, LinhaMunicipio> = {};
    for (const r of series ?? []) {
      const atual = fora[r.municipio_cod];
      if (!atual || r.ano > atual.ano) fora[r.municipio_cod] = r;
    }
    return fora;
  }, [series]);

  const copiarLink = useCallback(async () => {
    try {
      await navigator.clipboard.writeText(window.location.href);
      setCopiado(true);
    } catch { setCopiado(false); }
  }, []);

  const rotuloMetrica = metrica === "obitos"
    ? "Óbitos registrados"
    : metrica === "taxa_obitos_100k" ? "Taxa bruta /100 mil" : "Taxa padronizada /100 mil";

  return (
    <div className="mx-auto max-w-6xl px-4 py-10 sm:px-6">
      <h1 className="font-serif text-3xl font-semibold tracking-tight text-ink-950">Comparar municípios</h1>
      <p className="mt-2 max-w-3xl text-ink-600">
        Até {MAX} municípios lado a lado, na série {series?.length ? `${dados[0]?.ano}–${dados[dados.length - 1]?.ano}` : "completa"} do
        SIM. A métrica padrão é a <strong>taxa padronizada por idade</strong>, que é a única que
        permite comparar municípios com estruturas etárias diferentes.
      </p>

      <div className="card mt-6">
        <label className="label" htmlFor="cmp-busca">Adicionar município</label>
        <input
          id="cmp-busca" className="select" autoComplete="off"
          placeholder={codigos.length >= MAX ? `Limite de ${MAX} municípios atingido` : "nome ou código IBGE"}
          disabled={codigos.length >= MAX}
          value={termo} onChange={(e) => setTermo(e.target.value)}
        />
        {sugestoes.length > 0 && (
          <ul className="mt-1 divide-y divide-ink-100 rounded-lg border border-ink-200">
            {sugestoes.map(([cod, nome, uf]) => (
              <li key={cod}>
                <button
                  className="w-full px-3 py-2 text-left text-sm hover:bg-ink-50"
                  onClick={() => { setCodigos((c) => [...c, cod].slice(0, MAX)); setTermo(""); }}
                >
                  {nome} <span className="text-ink-500">· {uf}</span>
                </button>
              </li>
            ))}
          </ul>
        )}

        {escolhidos.length > 0 && (
          <div className="mt-3 flex flex-wrap items-center gap-2">
            {escolhidos.map((m, i) => (
              <button
                key={m[0]}
                onClick={() => setCodigos((c) => c.filter((x) => x !== m[0]))}
                className="inline-flex items-center gap-2 rounded-full border border-ink-300 bg-white px-3 py-1 text-sm text-ink-700 hover:bg-ink-50"
                title="Remover da comparação"
              >
                <span className="inline-block h-2.5 w-2.5 rounded-full" style={{ background: CORES[i] }} />
                {m[1]} <span aria-hidden className="text-ink-400">×</span>
              </button>
            ))}
            <button onClick={copiarLink} className="text-xs font-medium text-accent-700 underline">
              {copiado ? "✓ Link copiado" : "Copiar link desta comparação"}
            </button>
          </div>
        )}
      </div>

      {codigos.length === 0 && (
        <p className="card mt-6 text-sm text-ink-600">
          Escolha ao menos dois municípios. Sugestão para começar: <strong>Penápolis</strong> e{" "}
          <strong>Araçatuba</strong> — vizinhas, mesmo perfil de mortalidade e vulnerabilidade, e
          resultados assistenciais opostos.
        </p>
      )}

      {codigos.length > 0 && series === null && <Skeleton altura={360} />}

      {codigos.length > 0 && series !== null && (
        <>
          <CardComparabilidade escolhidos={escolhidos} ivs={ivs} clusters={clusters} ultimo={ultimo} />

          <div className="card mt-6">
            <div className="flex flex-wrap items-end justify-between gap-4">
              <h2 className="font-serif text-xl font-semibold text-ink-900">{rotuloMetrica}</h2>
              <div>
                <label className="label" htmlFor="cmp-metrica">Métrica</label>
                <select id="cmp-metrica" className="select" value={metrica}
                        onChange={(e) => setMetrica(e.target.value as typeof metrica)}>
                  <option value="taxa_padronizada_100k">Taxa padronizada por idade (comparável)</option>
                  <option value="taxa_obitos_100k">Taxa bruta /100 mil</option>
                  <option value="obitos">Óbitos absolutos</option>
                </select>
              </div>
            </div>

            {metrica !== "taxa_padronizada_100k" && (
              <p className="mt-2 rounded-lg border border-amber-200 bg-amber-50 px-4 py-2 text-sm text-amber-800">
                ⚠ {metrica === "obitos"
                  ? "Óbitos absolutos acompanham o tamanho do município: a linha mais alta é quase sempre a cidade maior."
                  : "A taxa bruta não corrige a estrutura etária: um município envelhecido aparece pior sem que ninguém adoeça mais."}
                {" "}Para comparar, volte à padronizada.
              </p>
            )}

            <div className="mt-4">
              <ResponsiveContainer width="100%" height={340}>
                <LineChart data={dados} margin={{ top: 8, right: 16, bottom: 0, left: 8 }}>
                  <CartesianGrid stroke={GRADE} vertical={false} />
                  <XAxis dataKey="ano" tick={{ fontSize: 12, fill: EIXO }} />
                  <YAxis tick={{ fontSize: 12, fill: EIXO }} width={56} />
                  <Tooltip
                    contentStyle={{ borderRadius: 8, borderColor: GRADE, fontSize: 13 }}
                    formatter={(v, nome) => [
                      metrica === "obitos" ? fmtInt(v as number) : fmtDec(v as number),
                      escolhidos.find((m) => m[0] === nome)?.[1] ?? nome,
                    ]}
                  />
                  <Legend formatter={(nome) => escolhidos.find((m) => m[0] === nome)?.[1] ?? nome} />
                  {codigos.map((c, i) => (
                    <Line key={c} type="monotone" dataKey={c} stroke={CORES[i]} strokeWidth={2.5}
                          dot={{ r: 2.5 }} connectNulls />
                  ))}
                </LineChart>
              </ResponsiveContainer>
            </div>

            <p className="mt-2 text-xs text-ink-500">
              O último ano da série é preliminar quando marcado como tal no boletim — os valores só
              crescem. Anos preliminares desta série: {[...new Set((series ?? []).map((r) => r.ano))]
                .filter(ehPreliminar).join(", ") || "nenhum"}.
            </p>

            <FichaIndicador
              id={metrica === "obitos" ? "obitos" : metrica === "taxa_obitos_100k" ? "taxa-bruta" : "taxa-padronizada"}
              contexto={`${escolhidos.map((m) => m[1]).join(", ")} — série completa`}
            />
          </div>

          <div className="card mt-6 overflow-x-auto">
            <h2 className="font-serif text-xl font-semibold text-ink-900">Tabela</h2>
            <table className="mt-3 w-full min-w-[520px] text-sm">
              <thead>
                <tr className="border-b-2 border-ink-200 text-left text-xs uppercase tracking-wide text-ink-500">
                  <th className="px-2 py-2">Ano</th>
                  {escolhidos.map((m) => <th key={m[0]} className="px-2 py-2 text-right">{m[1]}</th>)}
                </tr>
              </thead>
              <tbody>
                {dados.map((linha) => (
                  <tr key={String(linha.ano)} className="border-b border-ink-100">
                    <td className="px-2 py-2 tabular-nums text-ink-600">{String(linha.ano)}</td>
                    {codigos.map((c) => (
                      <td key={c} className="px-2 py-2 text-right tabular-nums">
                        {linha[c] == null ? "—"
                          : metrica === "obitos" ? fmtInt(linha[c] as number) : fmtDec(linha[c] as number)}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}
    </div>
  );
}

export function CompararCliente() {
  return (
    <Suspense fallback={<div className="mx-auto max-w-6xl px-4 py-10 sm:px-6"><Skeleton altura={400} /></div>}>
      <CompararInner />
    </Suspense>
  );
}
