"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { geoMercator, geoPath } from "d3-geo";
import { Skeleton } from "@/components/kpi";
import { ANOS, UFS, fmtDec, fmtInt, rest, type LinhaMunicipio } from "@/lib/api";

type Metrica = "taxa_padronizada_100k" | "taxa_obitos_100k" | "obitos";

const METRICAS: { id: Metrica; rotulo: string; nota: string }[] = [
  {
    id: "taxa_padronizada_100k",
    rotulo: "Taxa padronizada /100 mil",
    nota: "Ajustada por idade (padrão: Brasil, Censo 2022) — comparável entre municípios.",
  },
  {
    id: "taxa_obitos_100k",
    rotulo: "Taxa bruta /100 mil",
    nota: "Sem ajuste etário: municípios envelhecidos tendem a taxas maiores.",
  },
  { id: "obitos", rotulo: "Óbitos absolutos", nota: "Contagem simples de óbitos no ano." },
];

// Paleta sequencial (claro → escuro)
const CORES = ["#f1f7f4", "#c9e8d8", "#8fd3b0", "#46b785", "#15875e", "#0c5c41", "#07392a"];

interface Feature {
  type: string;
  properties: { codarea: string };
  geometry: GeoJSON.Geometry;
}

export default function Mapa() {
  const [uf, setUf] = useState("MG");
  const [ano, setAno] = useState(2024);
  const [metrica, setMetrica] = useState<Metrica>("taxa_padronizada_100k");
  const [geo, setGeo] = useState<{ features: Feature[] } | null>(null);
  const [dados, setDados] = useState<Map<string, LinhaMunicipio> | null>(null);
  const [hover, setHover] = useState<{ x: number; y: number; m: LinhaMunicipio | null; nome: string } | null>(null);
  const [erro, setErro] = useState<string | null>(null);
  const geoCache = useRef(new Map<string, { features: Feature[] }>());

  useEffect(() => {
    setGeo(null);
    setErro(null);
    (async () => {
      try {
        if (geoCache.current.has(uf)) {
          setGeo(geoCache.current.get(uf)!);
          return;
        }
        // Malha auto-hospedada (rápida e estável); IBGE só como fallback.
        let gj: { features: Feature[] } | null = null;
        try {
          const local = await fetch(`/sdata/malhas/${uf}.json`);
          if (local.ok) gj = await local.json();
        } catch { /* tenta IBGE abaixo */ }
        if (!gj) {
          const r = await fetch(
            `https://servicodados.ibge.gov.br/api/v4/malhas/estados/${uf}?formato=application/vnd.geo+json&intrarregiao=municipio&qualidade=minima`,
          );
          if (!r.ok) throw new Error(`malha indisponível: HTTP ${r.status}`);
          gj = await r.json();
        }
        geoCache.current.set(uf, gj!);
        setGeo(gj);
      } catch (e) {
        setErro(String(e));
      }
    })();
  }, [uf]);

  useEffect(() => {
    setDados(null);
    setErro(null);
    rest<LinhaMunicipio>("mart_mortalidade_municipio", {
      select:
        "municipio_cod,municipio_nome,uf_sigla,ano,obitos,populacao,taxa_obitos_100k,taxa_padronizada_100k,ic95_inf,ic95_sup",
      uf_sigla: `eq.${uf}`,
      ano: `eq.${ano}`,
      capitulo_cid: "eq.TOTAL",
      sexo: "eq.TOTAL",
      order: "municipio_cod",
    })
      .then((rows) => setDados(new Map(rows.map((r) => [r.municipio_cod, r]))))
      .catch((e) => setErro(String(e)));
  }, [uf, ano]);

  const { paths, escala } = useMemo(() => {
    if (!geo || !dados) return { paths: null, escala: null };
    const proj = geoMercator().fitSize([800, 620], geo as never);
    const gen = geoPath(proj);

    const valores = [...dados.values()]
      .map((m) => m[metrica])
      .filter((v): v is number => v != null && isFinite(v))
      .sort((a, b) => a - b);
    const quantil = (q: number) => valores[Math.min(valores.length - 1, Math.floor(q * valores.length))] ?? 0;
    const cortes = [1 / 7, 2 / 7, 3 / 7, 4 / 7, 5 / 7, 6 / 7].map(quantil);
    const cor = (v: number | null | undefined) => {
      if (v == null || !isFinite(v)) return "#e5e9ef";
      let i = 0;
      while (i < cortes.length && v > cortes[i]) i++;
      return CORES[i];
    };

    const paths = geo.features.map((f) => {
      const cod6 = String(f.properties.codarea).slice(0, 6);
      const m = dados.get(cod6) ?? null;
      return {
        d: gen(f as never) ?? "",
        cod6,
        m,
        fill: cor(m?.[metrica] as number | null),
      };
    });
    return { paths, escala: { cortes, valores } };
  }, [geo, dados, metrica]);

  const metricaInfo = METRICAS.find((m) => m.id === metrica)!;

  return (
    <div className="mx-auto max-w-7xl px-4 py-10 sm:px-6">
      <h1 className="font-serif text-3xl font-semibold tracking-tight text-ink-950">Mapa da mortalidade</h1>
      <p className="mt-2 max-w-3xl text-ink-600">
        Distribuição municipal dos óbitos (todas as causas). Classes por quantis;
        municípios sem registro em cinza.
      </p>

      <div className="card mt-6 grid gap-4 sm:grid-cols-3">
        <div>
          <label className="label" htmlFor="m-uf">Estado</label>
          <select id="m-uf" className="select" value={uf} onChange={(e) => setUf(e.target.value)}>
            {UFS.map((u) => <option key={u} value={u}>{u}</option>)}
          </select>
        </div>
        <div>
          <label className="label" htmlFor="m-ano">Ano</label>
          <select id="m-ano" className="select" value={ano} onChange={(e) => setAno(Number(e.target.value))}>
            {[...ANOS].reverse().map((a) => (
              <option key={a} value={a}>{a}{a === 2024 ? " (preliminar)" : ""}</option>
            ))}
          </select>
        </div>
        <div>
          <label className="label" htmlFor="m-met">Indicador</label>
          <select id="m-met" className="select" value={metrica} onChange={(e) => setMetrica(e.target.value as Metrica)}>
            {METRICAS.map((m) => <option key={m.id} value={m.id}>{m.rotulo}</option>)}
          </select>
        </div>
      </div>
      <p className="mt-2 text-xs text-ink-500">{metricaInfo.nota}</p>

      {erro && <div className="card mt-4 border-red-200 bg-red-50 text-sm text-red-800">Falha: {erro}</div>}

      <div className="card relative mt-4 p-2 sm:p-4">
        {paths ? (
          <>
            <svg viewBox="0 0 800 620" className="h-auto w-full" role="img"
                 aria-label={`Mapa de ${uf}: ${metricaInfo.rotulo} por município, ${ano}`}>
              {paths.map((p) => (
                <path
                  key={p.cod6 + p.d.length}
                  d={p.d}
                  fill={p.fill}
                  stroke="#fff"
                  strokeWidth={0.6}
                  onMouseMove={(e) => {
                    const r = (e.currentTarget.ownerSVGElement as SVGSVGElement).getBoundingClientRect();
                    setHover({
                      x: e.clientX - r.left,
                      y: e.clientY - r.top,
                      m: p.m,
                      nome: p.m?.municipio_nome ?? p.cod6,
                    });
                  }}
                  onMouseLeave={() => setHover(null)}
                />
              ))}
            </svg>
            {hover && (
              <div
                className="pointer-events-none absolute z-10 rounded-lg border border-ink-200 bg-white px-3 py-2 text-xs shadow-lg"
                style={{ left: Math.min(hover.x + 12, 560), top: hover.y + 8 }}
              >
                <p className="font-semibold text-ink-900">{hover.nome}</p>
                {hover.m ? (
                  <>
                    <p>Óbitos: <b>{fmtInt(hover.m.obitos)}</b> · Pop.: {fmtInt(hover.m.populacao)}</p>
                    <p>Taxa bruta: <b>{fmtDec(hover.m.taxa_obitos_100k)}</b>
                      {hover.m.ic95_inf != null && ` (IC95% ${fmtDec(hover.m.ic95_inf)}–${fmtDec(hover.m.ic95_sup)})`}
                    </p>
                    <p>Taxa padronizada: <b className="text-accent-800">{fmtDec(hover.m.taxa_padronizada_100k)}</b> /100 mil</p>
                    {(hover.m.populacao ?? 0) < 10_000 && (
                      <p className="mt-1 text-amber-700">⚠ população pequena: taxa instável</p>
                    )}
                  </>
                ) : (
                  <p className="text-ink-500">sem registro no recorte</p>
                )}
              </div>
            )}
            {/* legenda */}
            {escala && (
              <div className="mt-2 flex flex-wrap items-center gap-1 px-2 text-[11px] text-ink-600">
                <span className="mr-1">{metricaInfo.rotulo}:</span>
                {CORES.map((c, i) => (
                  <span key={c} className="flex items-center gap-1">
                    <span className="inline-block h-3 w-5 rounded-sm" style={{ background: c }} />
                    {i < escala.cortes.length ? `≤${fmtDec(escala.cortes[i], 0)}` : `>${fmtDec(escala.cortes[escala.cortes.length - 1], 0)}`}
                  </span>
                ))}
                <span className="ml-2 flex items-center gap-1">
                  <span className="inline-block h-3 w-5 rounded-sm bg-[#e5e9ef]" /> sem dado
                </span>
              </div>
            )}
          </>
        ) : (
          <Skeleton altura={560} />
        )}
      </div>

      <p className="mt-4 text-xs text-ink-500">
        Malha municipal: IBGE (API de malhas, qualidade mínima). Indicadores: SIM/DataSUS e IBGE —
        ver <a className="text-accent-700 underline" href="/metodologia/">metodologia</a>, incl. limitações
        de taxas em municípios pequenos.
      </p>
    </div>
  );
}
