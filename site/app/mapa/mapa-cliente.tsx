"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { geoMercator, type GeoProjection } from "d3-geo";
import { BotaoExportarCsv } from "@/components/exportar-csv";
import { VerMais } from "@/components/ver-mais";
import { semAcento } from "@/lib/busca";
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

type Metrica =
  | "taxa_padronizada_100k" | "taxa_obitos_100k" | "obitos"
  | "pct_domicilio" | "pct_hospital" | "populacao";

/**
 * A ressalva que TODA proporção sobre óbitos carrega neste mapa.
 *
 * Ordenar municípios por percentual põe no topo os de denominador minúsculo:
 * Serra da Saudade lidera com 50,0% de óbitos em domicílio, e são DOIS óbitos
 * em quatro. O mapa não pode esconder isso atrás de um tom de verde — quem lê
 * um ranking de proporções sem o denominador está lendo ruído ordenado.
 */
const INSTAVEL =
  "Em município pequeno a proporção é instável: metade de quatro óbitos são dois. "
  + "A coluna 'Óbitos' da tabela ao lado é o denominador — leia os dois juntos.";

/**
 * Os indicadores do mapa.
 *
 * `valor` existe porque nem todo indicador é uma coluna: a proporção de óbitos
 * em domicílio é derivada de duas, e derivá-la AQUI — num lugar só — é o que
 * impede que a legenda, o mapa, a tabela e a exportação calculem cada um a
 * sua. `unidade` e `casas` idem: quem formata é a definição, não cada tela.
 *
 * `nota` não é decoração. Três destes indicadores não são comparáveis entre
 * municípios pelo mesmo motivo (estrutura etária, porte), e o mapa colore os
 * seis do mesmo jeito — a ressalva é o que separa o número útil do enganoso.
 */
const METRICAS: {
  id: Metrica;
  rotulo: string;
  nota: string;
  unidade: string;
  casas: number;
  valor: (m: LinhaMunicipio) => number | null;
}[] = [
  {
    id: "taxa_padronizada_100k",
    rotulo: "Taxa padronizada /100 mil",
    nota: "Ajustada por idade (padrão: Brasil, Censo 2022) — comparável entre municípios.",
    unidade: "/100 mil", casas: 1,
    valor: (m) => m.taxa_padronizada_100k,
  },
  {
    id: "taxa_obitos_100k",
    rotulo: "Taxa bruta /100 mil",
    nota: "Sem ajuste etário: municípios envelhecidos tendem a taxas maiores.",
    unidade: "/100 mil", casas: 1,
    valor: (m) => m.taxa_obitos_100k,
  },
  {
    id: "obitos",
    rotulo: "Óbitos absolutos",
    nota: "Contagem simples de óbitos no ano. Acompanha o tamanho do município — o mapa "
        + "de óbitos absolutos é, em boa medida, um mapa de população.",
    unidade: "óbitos", casas: 0,
    valor: (m) => m.obitos,
  },
  {
    id: "pct_domicilio",
    rotulo: "% de óbitos em domicílio",
    nota: "Óbitos ocorridos no domicílio sobre o total do município. Lê-se em duas direções "
        + "opostas e o mapa não decide entre elas: pode indicar dificuldade de acesso a "
        + "serviço, ou cuidado paliativo domiciliar por escolha. Municípios sem hospital "
        + "local aparecem altos por falta de onde internar. "
        + INSTAVEL,
    unidade: "%", casas: 1,
    valor: (m) => (m.obitos > 0 && m.obitos_domicilio != null
      ? (m.obitos_domicilio / m.obitos) * 100 : null),
  },
  {
    id: "pct_hospital",
    rotulo: "% de óbitos em hospital",
    nota: "Óbitos ocorridos em estabelecimento hospitalar sobre o total. NÃO é o complemento "
        + "exato do domiciliar: há óbitos em via pública, em outro estabelecimento e sem "
        + "local informado, e os dois somados raramente dão 100%. "
        + INSTAVEL,
    unidade: "%", casas: 1,
    valor: (m) => (m.obitos > 0 && m.obitos_hospital != null
      ? (m.obitos_hospital / m.obitos) * 100 : null),
  },
  {
    id: "populacao",
    rotulo: "População",
    nota: "Estimativa do ano, do IBGE. Está aqui como denominador visível: comparar o mapa de "
        + "óbitos absolutos com este mostra o quanto aquele é explicado por tamanho.",
    unidade: "habitantes", casas: 0,
    valor: (m) => m.populacao,
  },
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
  const [escalaNacional, setEscalaNacional] = useState(false);
  const [busca, setBusca] = useState("");
  const [nacional, setNacional] = useState<LinhaMunicipio[] | null>(null);
  const [erroNacional, setErroNacional] = useState<string | null>(null);

  /**
   * A distribuição do BRASIL para o ano, buscada só quando alguém liga a
   * escala fixa.
   *
   * Sem ela, o mapa recalcula os cortes de quantil sobre a UF exibida: o verde
   * mais escuro de Alagoas e o de São Paulo significam números diferentes, e
   * trocar de estado repinta o mapa sem que nenhum dado tenha mudado. Quem
   * comparar dois estados lado a lado lê uma diferença que a legenda inventou.
   *
   * São ~5.570 linhas por ano — seis requisições ao PostgREST. Caro demais
   * para pagar sempre, barato o suficiente para pagar quando pedido.
   */
  useEffect(() => {
    if (!escalaNacional) return;
    setErroNacional(null);
    setNacional(null);
    rest<LinhaMunicipio>("mart_mortalidade_municipio", {
      select: "municipio_cod,municipio_nome,uf_sigla,ano,obitos,obitos_hospital,obitos_domicilio,"
        + "populacao,taxa_obitos_100k,taxa_padronizada_100k",
      ano: `eq.${ano}`,
      capitulo_cid: "eq.TOTAL",
      sexo: "eq.TOTAL",
      order: "municipio_cod",
    })
      .then(setNacional)
      .catch((e) => setErroNacional(String(e)));
  }, [escalaNacional, ano]);

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
      // `obitos_hospital` e `obitos_domicilio` são as colunas de que os
      // indicadores DERIVADOS precisam. Sem elas o mapa não quebrava — pintava
      // 853 municípios de cinza e enchia a tabela de "—", como se o dado não
      // existisse. Indicador novo que lê coluna nova exige conferir os DOIS
      // `select` desta página: o da UF pinta o mapa, o nacional só dá a escala.
      select:
        "municipio_cod,municipio_nome,uf_sigla,ano,obitos,obitos_hospital,obitos_domicilio,"
        + "populacao,taxa_obitos_100k,taxa_padronizada_100k,ic95_inf,ic95_sup",
      uf_sigla: `eq.${uf}`,
      ano: `eq.${ano}`,
      capitulo_cid: "eq.TOTAL",
      sexo: "eq.TOTAL",
      order: "municipio_cod",
    })
      .then((rows) => setDados(new Map(rows.map((r) => [r.municipio_cod, r]))))
      .catch((e) => setErro(String(e)));
  }, [uf, ano]);

  const metricaInfo = METRICAS.find((m) => m.id === metrica)!;

  const { paths, escala } = useMemo(() => {
    if (!geo || !dados) return { paths: null, escala: null };
    const proj = ajustarProjecao(geoMercator(), geo, 800, 620);

    // De onde saem os CORTES: da UF exibida, ou do Brasil quando a escala fixa
    // está ligada e o nacional já chegou. Enquanto ele não chega, os cortes
    // continuam os da UF — e a legenda diz qual das duas coisas está no ar,
    // porque uma escala que muda sem aviso é pior que uma escala local.
    const usandoNacional = escalaNacional && nacional != null;
    const base = usandoNacional
      ? nacional!.map(metricaInfo.valor)
      : [...dados.values()].map(metricaInfo.valor);

    const valores = base
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
        fill: cor(m ? metricaInfo.valor(m) : null),
      };
    });
    return { paths, escala: { cortes, valores, usandoNacional } };
  }, [geo, dados, metrica, metricaInfo, escalaNacional, nacional]);

  /**
   * A alternativa tabular: o mesmo recorte que o mapa pinta, em texto.
   *
   * Mapa coroplético é ilegível para quem não enxerga cor, e impreciso para
   * todo mundo — ninguém lê 47,3% de um tom de verde. A tabela não é um extra
   * de acessibilidade pendurado ao lado: é a MESMA fonte, ordenada, com o
   * valor escrito. Vale para leitor de tela e vale para quem quer o número.
   */
  const linhasTabela = useMemo(() => {
    if (!dados) return null;
    const q = semAcento(busca);
    return [...dados.values()]
      .map((m) => ({ m, v: metricaInfo.valor(m) }))
      .filter(({ m }) => !q
        || semAcento(m.municipio_nome ?? "").includes(q)
        || m.municipio_cod.startsWith(q))
      .sort((a, b) => (b.v ?? -Infinity) - (a.v ?? -Infinity));
  }, [dados, metricaInfo, busca]);

  /** Os códigos que a busca casa — o mapa contorna esses municípios. */
  const realcados = useMemo(() => {
    const q = semAcento(busca);
    if (!q || !dados) return null;
    return new Set([...dados.values()]
      .filter((m) => semAcento(m.municipio_nome ?? "").includes(q)
        || m.municipio_cod.startsWith(q))
      .map((m) => m.municipio_cod));
  }, [dados, busca]);

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

      <div className="card mt-4 grid gap-4 sm:grid-cols-2">
        <div>
          <label className="label" htmlFor="m-busca">Buscar município</label>
          <input id="m-busca" className="select" value={busca}
                 onChange={(e) => setBusca(e.target.value)}
                 placeholder="nome ou código IBGE — ex.: Uberlândia, 317020" />
          <p className="mt-1 text-[11px] text-ink-500">
            Contorna no mapa e filtra a tabela. Acento e maiúscula são opcionais.
          </p>
        </div>
        <div>
          <span className="label">Escala de cores</span>
          <label className="mt-1 flex items-start gap-2 text-sm text-ink-700">
            <input type="checkbox" className="mt-0.5" checked={escalaNacional}
                   onChange={(e) => setEscalaNacional(e.target.checked)} />
            <span>
              Fixa, calculada sobre o Brasil
              <span className="block text-[11px] text-ink-500">
                Sem isto, os cortes vêm da UF exibida: o tom mais escuro de um estado e o de
                outro significam números diferentes, e trocar de estado repinta o mapa sem que
                nenhum dado mude.
              </span>
            </span>
          </label>
        </div>
      </div>

      <p className="mt-2 text-xs text-ink-500">{metricaInfo.nota}</p>

      {escalaNacional && erroNacional && (
        <p className="mt-2 rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-xs text-red-900">
          A distribuição nacional não carregou — {erroNacional}. O mapa está pintado com a escala
          da UF: <strong>não</strong> compare as cores com as de outro estado.
        </p>
      )}
      {escalaNacional && !erroNacional && !nacional && (
        <p className="mt-2 rounded-lg border border-ink-200 bg-ink-50 px-3 py-2 text-xs text-ink-600">
          Carregando a distribuição nacional… até chegar, as cores ainda são da escala da UF.
        </p>
      )}

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
                  stroke={realcados?.has(p.cod6) ? "#b45309" : "#ffffff"}
                  strokeWidth={realcados?.has(p.cod6) ? 1.6 : 0.3}
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
            {escala && (escala.usandoNacional
              ? <span className="mr-2 text-[11px] font-medium text-accent-800">escala do Brasil</span>
              : <span className="mr-2 text-[11px] font-medium text-ink-500">escala de {uf}</span>)}
            {escala && (
              <div className="mt-2 flex flex-wrap items-center gap-1 px-2 text-[11px] text-ink-600">
                <span className="mr-1">{metricaInfo.rotulo}:</span>
                {CORES.map((c, i) => (
                  <span key={c} className="flex items-center gap-1">
                    <span className="inline-block h-3 w-5 rounded-sm" style={{ background: c }} />
                    {/* `casas` vem da definição do indicador: com 0 fixo, "% de óbitos
                        em domicílio" mostrava faixas 47, 47, 48 — três classes com o
                        mesmo rótulo, porque a diferença estava na casa decimal. */}
                    {i < escala.cortes.length
                      ? `≤${fmtDec(escala.cortes[i], metricaInfo.casas)}`
                      : `>${fmtDec(escala.cortes[escala.cortes.length - 1], metricaInfo.casas)}`}
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

      {/* ── Alternativa tabular ──
          Mapa coroplético não é legível sem cor, e ninguém lê 47,3% de um tom
          de verde. A tabela é a MESMA fonte que o mapa pinta, ordenada e com o
          valor escrito — não é um extra pendurado ao lado. */}
      <div className="card mt-6">
        <div className="flex flex-wrap items-end justify-between gap-4">
          <div>
            <h2 className="font-serif text-xl font-semibold text-ink-900">
              {metricaInfo.rotulo} — {uf}, {ano}
            </h2>
            <p className="mt-1 text-sm text-ink-500">
              Os mesmos municípios que o mapa pinta, do maior para o menor.
              {linhasTabela && (
                <> {" "}{fmtInt(linhasTabela.length)}
                  {busca.trim() ? ` de ${fmtInt(dados?.size ?? 0)} (filtrados pela busca)` : " municípios"}.</>
              )}
            </p>
          </div>
          {linhasTabela && linhasTabela.length > 0 && (
            <BotaoExportarCsv
              base="mapa"
              recorte={{
                titulo: `Mapa — ${metricaInfo.rotulo}`,
                filtros: [
                  ["UF", uf],
                  ["Ano", String(ano)],
                  ["Indicador", metricaInfo.rotulo],
                  ["Busca", busca],
                  ["Escala de cores", escala?.usandoNacional ? "fixa (Brasil)" : `da UF (${uf})`],
                ],
                tabelas: ["mart_mortalidade_municipio"],
                ressalvas: [
                  metricaInfo.nota,
                  "Recorte do mapa: todas as causas, ambos os sexos.",
                  "O ano mais recente pode ser preliminar e será revisado.",
                ],
              }}
              colunas={["municipio_cod", "municipio", "uf", "valor", "unidade",
                        "obitos", "obitos_hospital", "obitos_domicilio", "populacao"]}
              linhas={() => (linhasTabela ?? []).map(({ m, v }) => [
                m.municipio_cod, m.municipio_nome, m.uf_sigla, v, metricaInfo.unidade,
                m.obitos, m.obitos_hospital, m.obitos_domicilio, m.populacao,
              ])}
            />
          )}
        </div>

        {!linhasTabela ? (
          <Skeleton altura={280} />
        ) : linhasTabela.length === 0 ? (
          <p className="mt-4 rounded-lg border border-ink-200 bg-ink-50 px-4 py-3 text-sm text-ink-600">
            Nenhum município de {uf} casa com &quot;{busca}&quot;. A busca compara nome (sem
            exigir acento) e código IBGE.
          </p>
        ) : (
          <div className="mt-4 overflow-x-auto tabela-rolavel">
            <VerMais total={linhasTabela.length} rotulo="municípios">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b-2 border-ink-200 text-left text-xs uppercase tracking-wide text-ink-500">
                    <th className="col-id px-3 py-2">Município</th>
                    <th className="px-3 py-2 text-right">{metricaInfo.rotulo}</th>
                    <th className="px-3 py-2 text-right">Óbitos</th>
                    <th className="px-3 py-2 text-right">População</th>
                  </tr>
                </thead>
                <tbody>
                  {linhasTabela.map(({ m, v }) => (
                    <tr key={m.municipio_cod} className="border-b border-ink-100 hover:bg-ink-50">
                      <td className="col-id px-3 py-1.5 font-medium text-ink-900">
                        <a href={`/boletim/?m=${m.municipio_cod}&ano=${ano}`}
                           className="hover:text-accent-700 hover:underline">
                          {m.municipio_nome ?? m.municipio_cod}
                        </a>
                      </td>
                      <td className="px-3 py-1.5 text-right tabular-nums">
                        {/* Ausente é "—", nunca 0: município sem população publicada
                            não tem taxa, e isso não é taxa igual a zero. */}
                        {v == null
                          ? <span className="text-ink-400" title="Sem dado publicado para este recorte">—</span>
                          : fmtDec(v, metricaInfo.casas)}
                      </td>
                      <td className="px-3 py-1.5 text-right tabular-nums text-ink-600">{fmtInt(m.obitos)}</td>
                      <td className="px-3 py-1.5 text-right tabular-nums text-ink-600">{fmtInt(m.populacao)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </VerMais>
          </div>
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
