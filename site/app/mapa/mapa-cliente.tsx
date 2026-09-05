"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { geoMercator, type GeoProjection } from "d3-geo";
import { Kpi, Skeleton } from "@/components/kpi";
import { ANOS, ANO_PADRAO, UFS, ehPreliminar, fmtDec, fmtInt, rest, type CnesMunicipio, type LinhaMunicipio } from "@/lib/api";

function mediana(vs: number[]): number | null {
  if (!vs.length) return null;
  const s = [...vs].sort((a, b) => a - b);
  const mid = Math.floor(s.length / 2);
  return s.length % 2 ? s[mid] : (s[mid - 1] + s[mid]) / 2;
}

// O pipeline de clip/resampling esférico do geoPath produz um retângulo de
// moldura espúrio com esta malha auto-hospedada. Isso quebrava DUAS coisas:
// o path desenhado (a moldura cobria o mapa) e o fitSize (que mede os limites
// por esse mesmo pipeline e acabava ajustando a MOLDURA ao viewBox, deixando o
// estado num aglomerado de ~19x16 unidades num canvas de 800x620).
// Como municípios nunca cruzam o antimeridiano, projetamos ponto a ponto e
// calculamos o enquadramento na mão — equivalente e sem o pipeline defeituoso.

function aneisDe(geom: GeoJSON.Geometry): number[][][] {
  return geom.type === "Polygon" ? (geom.coordinates as number[][][])
    : geom.type === "MultiPolygon" ? (geom.coordinates as number[][][][]).flat()
    : [];
}

function ajustarProjecao(
  proj: GeoProjection,
  geo: { features: { geometry: GeoJSON.Geometry }[] },
  largura: number,
  altura: number,
): GeoProjection {
  proj.scale(1).translate([0, 0]);
  let x0 = Infinity, y0 = Infinity, x1 = -Infinity, y1 = -Infinity;
  for (const f of geo.features) {
    for (const anel of aneisDe(f.geometry)) {
      for (const pt of anel) {
        const p = proj(pt as [number, number]);
        if (!p) continue;
        if (p[0] < x0) x0 = p[0];
        if (p[0] > x1) x1 = p[0];
        if (p[1] < y0) y0 = p[1];
        if (p[1] > y1) y1 = p[1];
      }
    }
  }
  if (!isFinite(x0) || x1 === x0 || y1 === y0) return proj;
  const s = 0.98 / Math.max((x1 - x0) / largura, (y1 - y0) / altura);
  return proj.scale(s).translate([(largura - s * (x1 + x0)) / 2, (altura - s * (y1 + y0)) / 2]);
}

function pathDeGeometria(geom: GeoJSON.Geometry, proj: GeoProjection): string {
  return aneisDe(geom)
    .map((anel) => {
      const pts = anel.map((pt) => proj(pt as [number, number]));
      if (pts.some((p) => !p)) return "";
      return "M" + pts.map((p) => `${p![0].toFixed(3)},${p![1].toFixed(3)}`).join("L") + "Z";
    })
    .join("");
}

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

export function MapaCliente() {
  const [uf, setUf] = useState("MG");
  const [ano, setAno] = useState(ANO_PADRAO);
  const [metrica, setMetrica] = useState<Metrica>("taxa_padronizada_100k");
  const [geo, setGeo] = useState<{ features: Feature[] } | null>(null);
  const [dados, setDados] = useState<Map<string, LinhaMunicipio> | null>(null);
  const [hover, setHover] = useState<{ x: number; y: number; m: LinhaMunicipio | null; nome: string } | null>(null);
  const [erro, setErro] = useState<string | null>(null);
  const [cnes, setCnes] = useState<CnesMunicipio[] | null>(null);
  const geoCache = useRef(new Map<string, { features: Feature[] }>());

  // Estabelecimentos de saúde (CNES) — cadastro corrente, sem dimensão de ano;
  // busca única para o Brasil inteiro (5.571 linhas, poucas centenas de KB).
  useEffect(() => {
    rest<CnesMunicipio>("mart_cnes_municipio", {
      select: "municipio_cod,uf_sigla,estabelecimentos_hospitalares,populacao,estab_hosp_por_10k,pct_publico",
    })
      .then(setCnes)
      .catch(() => setCnes(null));
  }, []);

  const cnesResumo = useMemo(() => {
    if (!cnes) return null;
    const nacional = mediana(cnes.map((m) => m.estab_hosp_por_10k).filter((v): v is number => v != null));
    const doEstado = cnes.filter((m) => m.uf_sigla === uf);
    const hospTotal = doEstado.reduce((s, m) => s + (m.estabelecimentos_hospitalares || 0), 0);
    const popTotal = doEstado.reduce((s, m) => s + (m.populacao || 0), 0);
    const pctPublicoMedio = mediana(doEstado.map((m) => m.pct_publico).filter((v): v is number => v != null));
    return {
      nacionalMediana: nacional,
      estadoPor10k: popTotal > 0 ? (hospTotal / popTotal) * 10_000 : null,
      estadoPctPublico: pctPublicoMedio,
      municipiosNoEstado: doEstado.length,
    };
  }, [cnes, uf]);

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
    const proj = ajustarProjecao(geoMercator(), geo, 800, 620);

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
        d: pathDeGeometria(f.geometry, proj),
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
              <option key={a} value={a}>{a}{ehPreliminar(a) ? " (preliminar)" : ""}</option>
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

      <div className="mt-4 grid gap-4 sm:grid-cols-3">
        <Kpi
          rotulo={`Estab. hospitalares /10 mil hab. em ${uf}`}
          valor={cnesResumo?.estadoPor10k != null ? fmtDec(cnesResumo.estadoPor10k) : "—"}
          detalhe={cnesResumo ? `${cnesResumo.municipiosNoEstado} municípios com dado` : "carregando…"}
        />
        <Kpi
          rotulo="Mediana Brasil /10 mil hab."
          valor={cnesResumo?.nacionalMediana != null ? fmtDec(cnesResumo.nacionalMediana) : "—"}
          detalhe="entre os 5.571 municípios"
        />
        <Kpi
          rotulo={`% de natureza pública em ${uf}`}
          valor={cnesResumo?.estadoPctPublico != null ? `${fmtDec(cnesResumo.estadoPctPublico)}%` : "—"}
          detalhe="mediana municipal, por natureza jurídica"
        />
      </div>
      <p className="mt-2 text-xs text-ink-500">
        {/* O texto dizia "não coberto ainda", e deixou de ser verdade quando
            `pipeline_cnes_leitos` entrou: leitos existem em
            `mart_leitos_municipio` e aparecem na visão hospitalar. A limitação
            é DESTE mapa, cuja camada vem da API de dados abertos, e não do
            projeto — dizer o contrário mandava o visitante procurar fora. */}
        Estabelecimentos de saúde ativos com perfil hospitalar (CNES, cadastro corrente, API de dados
        abertos do Ministério da Saúde) — esta camada não traz leitos, que vêm do FTP do DataSUS e
        estão na <a className="text-accent-700 underline" href="/hospitalar/">visão hospitalar</a>.
        "Público" vem da natureza jurídica do estabelecimento, não da esfera de gestão — ver{" "}
        <a className="text-accent-700 underline" href="/metodologia/">metodologia</a>.
      </p>

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
