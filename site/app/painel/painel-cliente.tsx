"use client";

import { Fragment, Suspense, useCallback, useEffect, useMemo, useState } from "react";
import { useSearchParams } from "next/navigation";
import { Barras, SerieLinha } from "@/components/charts";
import { Kpi, Skeleton } from "@/components/kpi";
import { VerMais } from "@/components/ver-mais";
import {
  ANOS,
  ANO_PADRAO,
  PERIODO,
  ANO_DETALHE,
  ehPreliminar,
  FAIXAS_ORDEM,
  UFS,
  fmtDec,
  fmtInt,
  rest,
  sdata,
  type CapituloCid,
  type CausaAgregada,
  type LinhaMunicipio,
  type LinhaUfMes,
  type SerieTotalItem,
} from "@/lib/api";
import { particionarMunicipios } from "@/lib/municipios";
import { BotaoExportarCsv } from "@/components/exportar-csv";
import { ProcedenciaImpressa } from "@/components/procedencia-impressa";
import { FichaIndicador } from "@/components/ficha-indicador";
import { casaMunicipio, semAcento } from "@/lib/busca";
import { incompletosDe, notaCompletude, type ManifestoCompletude } from "@/lib/completude";

type Sexo = "TOTAL" | "M" | "F";

/**
 * O recorte vive na URL, e não só no estado do componente.
 *
 * Sem isto, `/painel/` era o endereço de qualquer análise: escolher UF, ano,
 * capítulo e ordenação não mudava o link, então não havia como mandar a mesma
 * tela para outra pessoa nem voltar a ela depois. Os nomes são curtos e fixos
 * porque viram endereço público — renomear um quebra links já compartilhados.
 *
 * Valor inválido não derruba a página: cai no padrão. Um link colado errado, ou
 * de uma versão anterior do site, abre o painel em vez de uma tela quebrada.
 */
const PARAM = { uf: "uf", ano: "ano", cap: "cap", sexo: "sexo", pop: "pop", ord: "ord", q: "q" } as const;

const POPULACOES_MIN = [0, 10_000, 50_000, 100_000, 500_000] as const;
const ORDENS = ["taxa_pad", "taxa", "obitos"] as const;
type Ordem = (typeof ORDENS)[number];

function PainelInner() {
  const params = useSearchParams();
  const [uf, setUf] = useState<string>(
    () => { const v = params.get(PARAM.uf); return v && (v === "Brasil" || (UFS as readonly string[]).includes(v)) ? v : "Brasil"; },
  );
  const periodo = PERIODO;
  const [ano, setAno] = useState<number>(
    () => { const v = Number(params.get(PARAM.ano)); return (ANOS as readonly number[]).includes(v) ? v : ANO_PADRAO; },
  );
  const [capitulo, setCapitulo] = useState<string>(() => params.get(PARAM.cap) ?? "TOTAL");
  const [sexo, setSexo] = useState<Sexo>(
    () => { const v = params.get(PARAM.sexo); return v === "M" || v === "F" ? v : "TOTAL"; },
  );
  const [capitulos, setCapitulos] = useState<CapituloCid[]>([]);
  const [descricoesCid, setDescricoesCid] = useState<Record<string, string>>({});

  const [serie, setSerie] = useState<{ mes: string; obitos: number }[] | null>(null);
  const [completude, setCompletude] = useState<ManifestoCompletude | null>(null);
  const [faixas, setFaixas] = useState<LinhaUfMes[] | null>(null);
  const [municipios, setMunicipios] = useState<LinhaMunicipio[] | null>(null);
  const [causas, setCausas] = useState<CausaAgregada[] | null>(null);
  const [erro, setErro] = useState<string | null>(null);

  const [busca, setBusca] = useState(() => params.get(PARAM.q) ?? "");
  // `Number(null)` é 0, e 0 ("sem mínimo") é uma opção VÁLIDA — validar só o
  // valor fazia todo painel recém-aberto nascer sem filtro de população e com
  // `?pop=0` na barra. Ausência do parâmetro tem de ser testada antes da
  // conversão. Pego na verificação em navegador, não no type-check.
  const [popMin, setPopMin] = useState(() => {
    const bruto = params.get(PARAM.pop);
    if (bruto == null) return 50_000;
    const v = Number(bruto);
    return (POPULACOES_MIN as readonly number[]).includes(v) ? v : 50_000;
  });
  const [ordenarPor, setOrdenarPor] = useState<Ordem>(
    () => { const v = params.get(PARAM.ord); return (ORDENS as readonly string[]).includes(v ?? "") ? (v as Ordem) : "taxa_pad"; },
  );
  const [linkCopiado, setLinkCopiado] = useState(false);

  /**
   * Quais colunas a tabela mostra.
   *
   * Sete colunas em 375px viram rolagem horizontal longa. Esconder por padrão
   * seria decidir pelo leitor o que importa; o que a tela faz é OFERECER a
   * escolha, com todas ligadas de saída — e a linha de detalhe garante que
   * nada fica inacessível por ter sido desmarcado.
   *
   * O estado não vai para a URL: é preferência de leitura desta sessão, não
   * recorte de dado. Link compartilhado tem que abrir no mesmo RECORTE, e a
   * escolha de colunas não muda um número sequer.
   */
  const [colunas, setColunas] = useState<Record<string, boolean>>({
    uf: true, obitos: true, populacao: true, bruta: true, padronizada: true,
  });
  const alternar = (k: string) => setColunas((c) => ({ ...c, [k]: !c[k] }));
  const [detalhe, setDetalhe] = useState<string | null>(null);
  const [buscaCid, setBuscaCid] = useState("");

  const historico = ano < ANO_DETALHE; // grão reduzido: sexo/faixa só TOTAL

  /**
   * O endereço acompanha o recorte, e só o que difere do padrão entra nele —
   * um painel recém-aberto continua sendo `/painel/`, sem sujeira.
   *
   * `replaceState` e não `pushState`: cada tecla digitada na busca criaria uma
   * entrada no histórico, e o botão "voltar" passaria a desfazer letra por
   * letra em vez de sair da página.
   */
  const consulta = useMemo(() => {
    const p = new URLSearchParams();
    if (uf !== "Brasil") p.set(PARAM.uf, uf);
    if (ano !== ANO_PADRAO) p.set(PARAM.ano, String(ano));
    if (capitulo !== "TOTAL") p.set(PARAM.cap, capitulo);
    if (sexo !== "TOTAL") p.set(PARAM.sexo, sexo);
    if (popMin !== 50_000) p.set(PARAM.pop, String(popMin));
    if (ordenarPor !== "taxa_pad") p.set(PARAM.ord, ordenarPor);
    if (busca.trim()) p.set(PARAM.q, busca.trim());
    return p.toString();
  }, [uf, ano, capitulo, sexo, popMin, ordenarPor, busca]);

  useEffect(() => {
    if (typeof window === "undefined") return;
    window.history.replaceState(null, "", consulta ? `?${consulta}` : window.location.pathname);
    setLinkCopiado(false);
  }, [consulta]);

  const copiarLink = useCallback(async () => {
    if (typeof window === "undefined") return;
    const url = `${window.location.origin}${window.location.pathname}${consulta ? `?${consulta}` : ""}`;
    try {
      await navigator.clipboard.writeText(url);
      setLinkCopiado(true);
    } catch {
      // Clipboard bloqueado (contexto não seguro, permissão negada): a URL da
      // barra de endereço já é a análise, então o usuário copia dali. Silenciar
      // é melhor que um erro que não tem conserto do lado dele.
      setLinkCopiado(false);
    }
  }, [consulta]);

  useEffect(() => {
    // As descrições da CID-10, uma vez por sessão: 2.046 linhas que só o
    // gráfico de causas usa, e sem as quais ele fala em código.
    rest<{ causabas_3: string; descricao: string }>("dim_cid10_categoria", {
      select: "causabas_3,descricao",
    })
      .then((r) => setDescricoesCid(Object.fromEntries(r.map((x) => [x.causabas_3, x.descricao]))))
      .catch(() => {});
    sdata<ManifestoCompletude>("completude").then(setCompletude).catch(() => {});
    sdata<CapituloCid[]>("capitulos")
      .catch(() =>
        rest<CapituloCid>("dim_cid10_capitulo", {
          select: "capitulo,capitulo_num,faixa,descricao",
          order: "capitulo_num",
        }),
      )
      .then(setCapitulos)
      .catch((e) => setErro(String(e)));
  }, []);

  // séries históricas em grão reduzido não têm sexo ≠ TOTAL
  useEffect(() => {
    if (historico && sexo !== "TOTAL") setSexo("TOTAL");
  }, [historico, sexo]);

  useEffect(() => {
    setSerie(null); setFaixas(null); setMunicipios(null); setCausas(null); setErro(null);
    const ufFiltro: Record<string, string> = uf === "Brasil" ? {} : { uf_sigla: `eq.${uf}` };

    (async () => {
      try {
        // Série mensal: caminho estático (egress zero) p/ TOTAL; REST para recortes
        let seriePromise: Promise<{ mes: string; obitos: number }[]>;
        if (capitulo === "TOTAL" && sexo === "TOTAL") {
          seriePromise = sdata<SerieTotalItem[]>("serie_total").then((all) => {
            const alvo = uf === "Brasil" ? "BR" : uf;
            return all
              .filter((r) => r.uf_sigla === alvo)
              .sort((a, b) => a.mes_competencia.localeCompare(b.mes_competencia))
              .map((r) => ({ mes: r.mes_competencia, obitos: r.obitos }));
          });
        } else {
          seriePromise = rest<LinhaUfMes>("mart_mortalidade_uf_mes", {
            select: "mes_competencia,uf_sigla,obitos",
            capitulo_cid: `eq.${capitulo}`,
            sexo: `eq.${sexo}`,
            faixa_etaria: "eq.TOTAL",
            order: "mes_competencia,uf_sigla",
            ...ufFiltro,
          }).then((rows) => {
            const por = new Map<string, number>();
            for (const r of rows) por.set(r.mes_competencia, (por.get(r.mes_competencia) ?? 0) + r.obitos);
            return [...por.entries()].sort(([a], [b]) => a.localeCompare(b)).map(([mes, obitos]) => ({ mes, obitos }));
          });
        }

        const [serieR, faixasR, muniR, causasR] = await Promise.all([
          seriePromise,
          rest<LinhaUfMes>("mart_mortalidade_uf_mes", {
            select: "faixa_etaria,uf_sigla,obitos",
            capitulo_cid: historico ? "eq.TOTAL" : `eq.${capitulo}`,
            sexo: "eq.TOTAL",
            faixa_etaria: "neq.TOTAL",
            ano: `eq.${ano}`,
            order: "faixa_etaria,uf_sigla,mes_competencia",
            ...ufFiltro,
          }),
          rest<LinhaMunicipio>("mart_mortalidade_municipio", {
            select:
              "municipio_cod,municipio_nome,uf_sigla,regiao,obitos,obitos_hospital,obitos_domicilio,populacao,taxa_obitos_100k,taxa_padronizada_100k,ic95_inf,ic95_sup",
            capitulo_cid: `eq.${capitulo}`,
            sexo: `eq.${sexo}`,
            ano: `eq.${ano}`,
            order: "municipio_cod",
            ...ufFiltro,
          }),
          rest<CausaAgregada>("mart_mortalidade_causa", {
            select: "causabas_3,obitos:obitos.sum()",
            ano: `eq.${ano}`,
            order: "causabas_3",
            ...ufFiltro,
          }),
        ]);
        setSerie(serieR);
        setFaixas(faixasR);
        setMunicipios(muniR);
        setCausas(causasR);
      } catch (e) {
        setErro(String(e));
      }
    })();
  }, [uf, ano, capitulo, sexo, historico]);

  const faixaChart = useMemo(() => {
    if (!faixas) return null;
    const por = new Map<string, number>();
    for (const r of faixas) por.set(r.faixa_etaria, (por.get(r.faixa_etaria) ?? 0) + r.obitos);
    return FAIXAS_ORDEM.filter((f) => por.has(f)).map((f) => ({ nome: f, obitos: por.get(f)! }));
  }, [faixas]);

  // Códigos agregados "UF0000" (óbito sem município identificado) não são
  // municípios: ficam fora da contagem, do ranking e do CSV, mas seus óbitos
  // continuam visíveis para o total não se perder.
  const particao = useMemo(
    () => (municipios ? particionarMunicipios(municipios) : null),
    [municipios],
  );

  /**
   * O recorte inteiro, filtrado e ordenado — sem o corte de 100.
   *
   * A tabela mostra 100; a EXPORTAÇÃO leva tudo. Antes ela levava os mesmos
   * 100 e não dizia: quem filtrava São Paulo e exportava recebia um arquivo
   * com 100 dos 645 municípios, sem nada no arquivo indicando o corte. Limite
   * visual é decisão de tela, não recorte de dado.
   *
   * O filtro também morava em dois memos idênticos (aqui e na contagem), o que
   * é a forma clássica de os dois divergirem numa edição futura.
   */
  const recorteCompleto = useMemo(() => {
    if (!particao) return null;
    return particao.identificados
      .filter((m) => (m.populacao ?? 0) >= popMin || sexo !== "TOTAL")
      // `casaMunicipio` e não `includes` minúsculo: "Penapolis" precisa
      // encontrar Penápolis, e o código do IBGE também. Ver `lib/busca.ts`.
      .filter((m) => casaMunicipio(busca, m.municipio_nome, m.municipio_cod))
      .sort((a, b) =>
        ordenarPor === "taxa_pad"
          ? (b.taxa_padronizada_100k ?? -1) - (a.taxa_padronizada_100k ?? -1)
          : ordenarPor === "taxa"
            ? (b.taxa_obitos_100k ?? -1) - (a.taxa_obitos_100k ?? -1)
            : b.obitos - a.obitos,
      );
  }, [particao, busca, popMin, ordenarPor, sexo]);

  const ranking = useMemo(() => recorteCompleto?.slice(0, 100) ?? null, [recorteCompleto]);

  /**
   * Quantos o recorte tem, contra quantos a tabela mostra.
   *
   * A tabela corta em 100 e não dizia. Quem filtrava uma UF grande via uma
   * lista terminar no centésimo município e não tinha como saber se aquele era
   * o fim do recorte ou o fim da página — limite visual e ausência de registro
   * têm a mesma aparência quando ninguém conta.
   */
  const totalNoRecorte = recorteCompleto?.length ?? null;

  /**
   * As quinze principais causas, com DESCRIÇÃO e não só o código.
   *
   * O gráfico rotulava as barras com `I21`, `J18`, `B34` — legível para quem
   * sabe CID-10 de cor, opaco para todo o resto, que é a maioria de quem chega
   * a um painel público. `dim_cid10_categoria` já está publicada e tem as 2.046
   * descrições; faltava buscá-la.
   *
   * O código continua no rótulo, na frente: quem sabe procura por ele, quem não
   * sabe lê o que vem depois.
   */
  const topCausas = useMemo(() => {
    if (!causas) return null;
    return [...causas].sort((a, b) => b.obitos - a.obitos).slice(0, 15)
      .map((c) => {
        // `descricao` já vem com o código na frente ("I21   Infarto agudo do
        // miocardio"), e concatenar produzia "I21 — I21   Infarto…", com o
        // corte comendo o texto. O prefixo sai antes.
        const desc = (descricoesCid[c.causabas_3] ?? "").replace(/^[A-Z]\d{2}\s+/, "").trim();
        return {
          nome: desc ? `${c.causabas_3} — ${desc.slice(0, 40)}` : c.causabas_3,
          obitos: c.obitos,
        };
      });
  }, [causas, descricoesCid]);

  const totalPeriodo = serie?.reduce((s, r) => s + r.obitos, 0);
  const totalAno = useMemo(
    () => serie?.filter((r) => r.mes.startsWith(String(ano))).reduce((s, r) => s + r.obitos, 0),
    [serie, ano],
  );

  const capDesc = capitulo === "TOTAL"
    ? "Todas as causas"
    : `Capítulo ${capitulo} — ${capitulos.find((c) => c.capitulo === capitulo)?.descricao ?? ""}`;

  /**
   * Capítulos que casam com a busca — por NOME ou por CÓDIGO.
   *
   * A lista tinha 22 opções com a descrição cortada em 48 caracteres, e
   * "Doenças endócrinas, nutricionais e metabólic…" não é um rótulo, é um
   * enigma. Quem sabe CID procura por `I00-I99` ou por `IX`; quem não sabe
   * procura por "circulatório". Os dois passam a funcionar, e a descrição
   * deixa de ser cortada.
   *
   * O capítulo SELECIONADO nunca é filtrado para fora: um `<select>` cujo
   * `value` não está entre as opções mostra a primeira, e o filtro trocaria o
   * recorte do visitante sem que ele pedisse.
   */
  const capitulosFiltrados = useMemo(() => {
    const q = semAcento(buscaCid);
    if (!q) return capitulos;
    return capitulos.filter((c) =>
      c.capitulo === capitulo
      || semAcento(c.descricao).includes(q)
      || semAcento(c.faixa).includes(q)
      || semAcento(c.capitulo).includes(q));
  }, [capitulos, buscaCid, capitulo]);

  /**
   * Os filtros que DIFEREM do padrão, cada um com como desfazê-lo.
   *
   * O painel tem sete controles espalhados por dois blocos, e um recorte
   * herdado de um link compartilhado chegava sem nada dizendo o que já estava
   * aplicado — o visitante via uma tabela curta e não sabia por quê. Só o que
   * difere do padrão entra: um painel recém-aberto não tem nada a listar, e uma
   * lista que sempre aparece deixa de ser lida.
   */
  const filtrosAtivos: { rotulo: string; limpar: () => void }[] = [
    ...(uf !== "Brasil" ? [{ rotulo: `UF: ${uf}`, limpar: () => setUf("Brasil") }] : []),
    ...(ano !== ANO_PADRAO ? [{ rotulo: `Ano: ${ano}`, limpar: () => setAno(ANO_PADRAO) }] : []),
    ...(capitulo !== "TOTAL" ? [{ rotulo: `Causa: ${capitulo}`, limpar: () => setCapitulo("TOTAL") }] : []),
    ...(sexo !== "TOTAL" ? [{ rotulo: `Sexo: ${sexo === "M" ? "masculino" : "feminino"}`, limpar: () => setSexo("TOTAL") }] : []),
    ...(popMin !== 50_000 ? [{ rotulo: `População ≥ ${fmtInt(popMin)}`, limpar: () => setPopMin(50_000) }] : []),
    ...(ordenarPor !== "taxa_pad" ? [{ rotulo: `Ordem: ${ordenarPor === "taxa" ? "taxa bruta" : "óbitos"}`, limpar: () => setOrdenarPor("taxa_pad") }] : []),
    ...(busca.trim() ? [{ rotulo: `Busca: "${busca.trim()}"`, limpar: () => setBusca("") }] : []),
  ];

  function limparTudo() {
    setUf("Brasil"); setAno(ANO_PADRAO); setCapitulo("TOTAL"); setSexo("TOTAL");
    setPopMin(50_000); setOrdenarPor("taxa_pad"); setBusca("");
  }

  /**
   * Por que a busca não achou nada — a diferença entre "não existe" e "o filtro
   * escondeu".
   *
   * Buscar "Penápolis" com o mínimo de 50 mil habitantes devolvia lista vazia
   * sem dizer que o município EXISTE e tem 63 mil; buscar um de 8 mil devolvia
   * a mesma tela. Duas situações opostas com a mesma resposta.
   */
  const escondidosPeloPorte = useMemo(() => {
    if (!particao || !busca.trim() || sexo !== "TOTAL") return [];
    return particao.identificados
      .filter((m) => casaMunicipio(busca, m.municipio_nome, m.municipio_cod))
      .filter((m) => (m.populacao ?? 0) < popMin);
  }, [particao, busca, popMin, sexo]);

  return (
    <div className="mx-auto max-w-7xl px-4 py-10 sm:px-6">
      <h1 className="font-serif text-3xl font-semibold tracking-tight text-ink-950">Painel de mortalidade</h1>
      <p className="mt-2 max-w-3xl text-ink-600">
        Série {periodo} ({ANOS.length} anos). Taxas padronizadas por idade e IC95% para
        comparação responsável entre municípios — os mesmos valores da API pública.
      </p>

      <div className="card mt-6 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <div>
          <label className="label" htmlFor="f-uf">Abrangência</label>
          <select id="f-uf" className="select" value={uf} onChange={(e) => setUf(e.target.value)}>
            <option value="Brasil">Brasil (todas as UFs)</option>
            {UFS.map((u) => <option key={u} value={u}>{u}</option>)}
          </select>
        </div>
        <div>
          <label className="label" htmlFor="f-ano">Ano de referência</label>
          <select id="f-ano" className="select" value={ano} onChange={(e) => setAno(Number(e.target.value))}>
            {[...ANOS].reverse().map((a) => (
              <option key={a} value={a}>
                {a}{ehPreliminar(a) ? " (preliminar)" : a < ANO_DETALHE ? " (grão reduzido)" : ""}
              </option>
            ))}
          </select>
        </div>
        <div>
          <label className="label" htmlFor="f-cap">Causa (capítulo CID-10)</label>
          <input
            id="f-cap-busca"
            className="select mb-1"
            placeholder="filtrar por nome ou código — ex.: circulatório, I00-I99, IX"
            value={buscaCid}
            onChange={(e) => setBuscaCid(e.target.value)}
            aria-label="Filtrar capítulos CID-10 por nome ou código"
          />
          <select id="f-cap" className="select" value={capitulo} onChange={(e) => setCapitulo(e.target.value)}>
            <option value="TOTAL">Todas as causas</option>
            {capitulosFiltrados.map((c) => (
              <option key={c.capitulo} value={c.capitulo}>
                {c.capitulo} ({c.faixa}) — {c.descricao}
              </option>
            ))}
          </select>
          {/* Total encontrado contra total exibido: sem isto, uma busca que
              não casa com nada e uma busca que casa com tudo têm a mesma
              aparência — a lista simplesmente muda de tamanho em silêncio. */}
          {buscaCid.trim() !== "" && (
            <p className="mt-1 text-[11px] text-ink-500">
              {capitulosFiltrados.length === 0
                ? "Nenhum capítulo casa com a busca — o filtro segue em " + capDesc + "."
                : `${capitulosFiltrados.length} de ${capitulos.length} capítulos`}
            </p>
          )}
        </div>
        <div>
          <label className="label" htmlFor="f-sexo">Sexo</label>
          <select id="f-sexo" className="select" value={sexo} disabled={historico}
                  onChange={(e) => setSexo(e.target.value as Sexo)}>
            <option value="TOTAL">Ambos</option>
            <option value="M">Masculino</option>
            <option value="F">Feminino</option>
          </select>
          {historico && (
            <p className="mt-1 text-[11px] text-amber-700">
              Antes de {ANO_DETALHE}: apenas totais (sem recorte por sexo).
            </p>
          )}
        </div>
      </div>

      {filtrosAtivos.length > 0 && (
        <div className="mt-3 flex flex-wrap items-center gap-2 text-sm">
          <span className="text-xs font-semibold uppercase tracking-wide text-ink-500">Filtros ativos</span>
          {filtrosAtivos.map((f) => (
            <button
              key={f.rotulo}
              onClick={f.limpar}
              className="inline-flex items-center gap-1 rounded-full border border-ink-300 bg-white px-3 py-1 text-xs text-ink-700 hover:border-ink-400 hover:bg-ink-50"
              title={`Remover: ${f.rotulo}`}
            >
              {f.rotulo} <span aria-hidden className="text-ink-400">×</span>
              <span className="sr-only">remover filtro</span>
            </button>
          ))}
          <button onClick={limparTudo} className="text-xs font-medium text-accent-700 underline">
            Limpar tudo
          </button>
        </div>
      )}

      {erro && <div className="card mt-6 border-red-200 bg-red-50 text-sm text-red-800">Falha ao consultar a base: {erro}</div>}

      <div className="mt-6 grid gap-4 sm:grid-cols-3">
        <Kpi rotulo={`Óbitos em ${ano}`} valor={totalAno != null ? fmtInt(totalAno) : "…"} detalhe={capDesc} />
        <Kpi rotulo={`Óbitos na série ${periodo}`} valor={totalPeriodo != null ? fmtInt(totalPeriodo) : "…"} detalhe={uf === "Brasil" ? "Brasil" : uf} />
        <Kpi
          rotulo="Municípios com registro"
          valor={particao ? fmtInt(particao.identificados.length) : "…"}
          detalhe={
            particao && particao.obitosNaoIdentificados > 0
              ? `no recorte selecionado, ${ano} · ${fmtInt(particao.obitosNaoIdentificados)} óbitos sem município identificado`
              : `no recorte selecionado, ${ano}`
          }
        />
      </div>
      {/* A ficha vale para os dois primeiros cartões e para a coluna de taxa
          padronizada da tabela — é o mesmo indicador, do mesmo mart. Fica
          abaixo do bloco e em largura cheia, pela mesma razão do boletim. */}
      <div className="mt-2 space-y-2">
        <FichaIndicador
          id="obitos"
          contexto={`${uf === "Brasil" ? "Brasil" : uf}, ${ano}${ehPreliminar(ano) ? " · dado preliminar" : " · dado consolidado"} · ${capDesc}`}
        />
        <FichaIndicador
          id="taxa-padronizada"
          contexto={`${uf === "Brasil" ? "Brasil" : uf}, ${ano} · coluna "Taxa padronizada" da tabela`}
        />
      </div>

      <div className="card mt-6">
        <h2 className="font-serif text-xl font-semibold text-ink-900">
          Evolução mensal — {uf === "Brasil" ? "Brasil" : uf}
        </h2>
        <p className="mt-1 text-sm text-ink-500">
          {capDesc}{sexo !== "TOTAL" ? ` · sexo ${sexo === "M" ? "masculino" : "feminino"}` : ""} · {periodo}
        </p>
        <div className="mt-4">
          {serie ? <SerieLinha data={serie} incompletos={incompletosDe(completude, uf)} titulo={`Evolução mensal — ${uf === "Brasil" ? "Brasil" : uf}`} /> : <Skeleton />}
        </div>
        {serie && notaCompletude(incompletosDe(completude, uf)) && (
          <p className="mt-3 border-t border-ink-200 pt-3 text-xs text-ink-600">
            <span className="font-medium text-ink-700">Trecho tracejado:</span>{" "}
            {notaCompletude(incompletosDe(completude, uf))}
          </p>
        )}
      </div>

      <div className="mt-6 grid gap-6 lg:grid-cols-2">
        <div className="card">
          <h2 className="font-serif text-xl font-semibold text-ink-900">Distribuição etária ({ano})</h2>
          {historico && <p className="mt-1 text-xs text-ink-500">No grão histórico, sempre todas as causas.</p>}
          <div className="mt-4">{faixaChart ? <Barras data={faixaChart} titulo={`Distribuição etária (${ano})`} /> : <Skeleton altura={300} />}</div>
        </div>
        <div className="card">
          <h2 className="font-serif text-xl font-semibold text-ink-900">15 principais causas básicas ({ano})</h2>
          <p className="mt-1 text-xs text-ink-500">Categorias CID-10 (3 caracteres), independentes do filtro de capítulo/sexo.</p>
          <div className="mt-4">
            {topCausas ? <Barras data={topCausas} horizontal altura={360} titulo={`15 principais causas básicas (${ano})`} /> : <Skeleton altura={360} />}
          </div>
        </div>
      </div>

      <div className="card mt-6">
        <div className="flex flex-wrap items-end justify-between gap-4">
          <div>
            <h2 className="font-serif text-xl font-semibold text-ink-900">
              Municípios ({ano})
              {totalNoRecorte != null && (
                <span className="ml-2 align-middle text-sm font-normal text-ink-500">
                  {totalNoRecorte > 100
                    ? `mostrando 100 de ${fmtInt(totalNoRecorte)} no recorte`
                    : `${fmtInt(totalNoRecorte)} no recorte`}
                </span>
              )}
            </h2>
            <p className="mt-1 text-sm text-ink-500">
              <b>Taxa padronizada</b> (ajustada por idade) é o indicador recomendado para comparar
              municípios; a bruta acompanha IC95%. Disponíveis quando sexo = Ambos.
            </p>
          </div>
          <div className="flex flex-wrap gap-2 no-print">
            <button onClick={copiarLink} className="btn-ghost" title="Copia o endereço com o recorte atual">
              {linkCopiado ? "✓ Link copiado" : "🔗 Copiar link desta análise"}
            </button>
            <BotaoExportarCsv
              base="mortalidade"
              desabilitado={!recorteCompleto?.length}
              recorte={{
                titulo: "Mortalidade por município",
                filtros: [
                  ["UF", uf],
                  ["Ano", String(ano)],
                  ["Capítulo CID-10", capDesc],
                  ["Sexo", sexo === "TOTAL" ? "ambos" : sexo === "M" ? "masculino" : "feminino"],
                  ["População mínima", popMin ? fmtInt(popMin) + " habitantes" : ""],
                  ["Busca", busca],
                ],
                tabelas: ["mart_mortalidade_municipio"],
                ressalvas: [
                  ehPreliminar(ano)
                    ? `${ano} é PRELIMINAR: vem do diretório que o DataSUS ainda não fechou e será revisado — os valores só crescem, e a codificação também muda.`
                    : `${ano} é consolidado.`,
                  "Taxa padronizada por idade é o indicador comparável entre municípios; a bruta não é. Ambas só existem quando sexo = ambos.",
                  "Códigos agregados UF0000 (óbito sem município identificado) ficam FORA deste arquivo; seus óbitos entram no total da tela.",
                  "Célula vazia em taxa = município sem população publicada para o ano, não taxa zero.",
                ],
              }}
              colunas={["municipio_cod", "municipio", "uf", "obitos", "populacao",
                        "taxa_bruta_100k", "ic95_inf", "ic95_sup", "taxa_padronizada_100k"]}
              linhas={() => (recorteCompleto ?? []).map((m) => [
                m.municipio_cod, m.municipio_nome, m.uf_sigla, m.obitos, m.populacao,
                m.taxa_obitos_100k, m.ic95_inf, m.ic95_sup, m.taxa_padronizada_100k,
              ])}
            />
          </div>
        </div>

        <div className="mt-4 grid gap-4 sm:grid-cols-3">
          <div>
            <label className="label" htmlFor="f-busca">Buscar município</label>
            <input id="f-busca" className="select" placeholder="nome ou código IBGE — ex.: Campinas, 350950"
                   value={busca} onChange={(e) => setBusca(e.target.value)} />
            <p className="mt-1 text-[11px] text-ink-500">Acento e maiúscula são opcionais.</p>
          </div>
          <div>
            <label className="label" htmlFor="f-pop">População mínima</label>
            <select id="f-pop" className="select" value={popMin} onChange={(e) => setPopMin(Number(e.target.value))}>
              {[0, 10_000, 50_000, 100_000, 500_000].map((p) => (
                <option key={p} value={p}>{p === 0 ? "Sem mínimo" : `≥ ${fmtInt(p)} hab.`}</option>
              ))}
            </select>
          </div>
          <div>
            <label className="label" htmlFor="f-ord">Ordenar por</label>
            <select id="f-ord" className="select" value={ordenarPor}
                    onChange={(e) => setOrdenarPor(e.target.value as typeof ordenarPor)}>
              <option value="taxa_pad">Taxa padronizada /100 mil</option>
              <option value="taxa">Taxa bruta /100 mil</option>
              <option value="obitos">Óbitos absolutos</option>
            </select>
          </div>
        </div>

        {/* Escolha de colunas: a tabela tem sete e o celular tem 375px. */}
        <fieldset className="mt-4 flex flex-wrap items-center gap-x-4 gap-y-1 no-print">
          <legend className="sr-only">Colunas visíveis</legend>
          <span className="text-xs font-semibold uppercase tracking-wide text-ink-500">Colunas</span>
          {COLUNAS_OPCIONAIS.map(([chave, rotulo]) => (
            <label key={chave} className="flex items-center gap-1.5 text-xs text-ink-600">
              <input type="checkbox" checked={colunas[chave]} onChange={() => alternar(chave)} />
              {rotulo}
            </label>
          ))}
          <span className="text-xs text-ink-400">
            Município fica sempre visível. A exportação leva todas as colunas.
          </span>
        </fieldset>

        <p className="dica-rolagem mt-2 text-xs text-ink-500 no-print">
          Tabela rolável na horizontal — o município fica parado à esquerda. Toque em
          <strong> ⋯ </strong> para ver todos os campos de uma linha.
        </p>

        <div className="mt-2 overflow-x-auto tabela-rolavel">
          {ranking ? (
            <VerMais total={ranking.length} rotulo="municípios">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b-2 border-ink-200 text-left text-xs uppercase tracking-wide text-ink-500">
                  <th className="px-3 py-2">#</th>
                  <th className="col-id px-3 py-2">Município</th>
                  {colunas.uf && <th className="px-3 py-2">UF</th>}
                  {colunas.obitos && <th className="px-3 py-2 text-right">Óbitos</th>}
                  {colunas.populacao && <th className="px-3 py-2 text-right">População</th>}
                  {colunas.bruta && <th className="px-3 py-2 text-right">Taxa bruta (IC95%)</th>}
                  {colunas.padronizada && <th className="px-3 py-2 text-right">Taxa padronizada</th>}
                  <th className="px-3 py-2 text-right no-print"><span className="sr-only">Detalhes</span></th>
                </tr>
              </thead>
              <tbody>
                {ranking.map((m, i) => (
                  <Fragment key={m.municipio_cod}>
                  <tr className="border-b border-ink-100 hover:bg-ink-50">
                    <td className="px-3 py-2 tabular-nums text-ink-500">{i + 1}</td>
                    <td className="col-id px-3 py-2 font-medium text-ink-900">
                      {/* O ano viaja junto. Sem ele o boletim abria no mais
                          recente da série — em 2025, preliminar — enquanto o
                          painel de origem estava em 2024: o visitante trocava
                          de ano sem pedir e sem ser avisado. */}
                      <a href={`/boletim/?m=${m.municipio_cod}&ano=${ano}`}
                         className="hover:text-accent-700 hover:underline"
                         title={`Abrir boletim do município em ${ano}`}>
                        {m.municipio_nome ?? m.municipio_cod}
                      </a>
                      {(m.populacao ?? 0) > 0 && (m.populacao ?? 0) < 10_000 && (
                        <span title="População pequena: taxas instáveis — observe o IC95%" className="ml-1 text-amber-600">⚠</span>
                      )}
                    </td>
                    {colunas.uf && <td className="px-3 py-2 text-ink-600">{m.uf_sigla}</td>}
                    {colunas.obitos && <td className="px-3 py-2 text-right tabular-nums">{fmtInt(m.obitos)}</td>}
                    {colunas.populacao && <td className="px-3 py-2 text-right tabular-nums text-ink-600">{fmtInt(m.populacao)}</td>}
                    {colunas.bruta && (
                      <td className="px-3 py-2 text-right tabular-nums text-ink-700">
                        {fmtDec(m.taxa_obitos_100k)}
                        {m.ic95_inf != null && (
                          <span className="text-xs text-ink-500"> ({fmtDec(m.ic95_inf)}–{fmtDec(m.ic95_sup)})</span>
                        )}
                      </td>
                    )}
                    {colunas.padronizada && (
                      <td className="px-3 py-2 text-right font-semibold tabular-nums text-accent-800">
                        {fmtDec(m.taxa_padronizada_100k)}
                      </td>
                    )}
                    <td className="px-1 py-2 text-right no-print">
                      <button
                        onClick={() => setDetalhe((d) => (d === m.municipio_cod ? null : m.municipio_cod))}
                        aria-expanded={detalhe === m.municipio_cod}
                        aria-label={`Todos os campos de ${m.municipio_nome ?? m.municipio_cod}`}
                        className="rounded px-2 py-0.5 text-ink-400 hover:bg-ink-100 hover:text-ink-700"
                      >⋯</button>
                    </td>
                  </tr>
                  {/* Detalhe da linha: TODOS os campos, inclusive os que a
                      escolha de colunas escondeu. Sem isto, desmarcar uma
                      coluna tornaria o dado inalcançável na tela — que é
                      esconder, não escolher. */}
                  {detalhe === m.municipio_cod && (
                    <tr className="border-b border-ink-100 bg-ink-50/60">
                      <td colSpan={9} className="px-3 py-2">
                        <dl className="grid gap-x-4 gap-y-1 text-xs sm:grid-cols-3">
                          <Campo termo="Código IBGE" valor={m.municipio_cod} />
                          <Campo termo="UF" valor={m.uf_sigla} />
                          <Campo termo="Óbitos" valor={fmtInt(m.obitos)} />
                          <Campo termo="População" valor={m.populacao == null ? null : fmtInt(m.populacao)} />
                          <Campo termo="Taxa bruta /100 mil" valor={m.taxa_obitos_100k == null ? null : fmtDec(m.taxa_obitos_100k)} />
                          <Campo termo="IC95%" valor={m.ic95_inf == null ? null : `${fmtDec(m.ic95_inf)}–${fmtDec(m.ic95_sup)}`} />
                          <Campo termo="Taxa padronizada /100 mil" valor={m.taxa_padronizada_100k == null ? null : fmtDec(m.taxa_padronizada_100k)} />
                        </dl>
                      </td>
                    </tr>
                  )}
                  </Fragment>
                ))}
              </tbody>
            </table>
            </VerMais>
          ) : (
            <Skeleton altura={300} />
          )}
          {ranking && ranking.length === 0 && (
            <div className="py-6 text-center text-sm text-ink-500">
              {escondidosPeloPorte.length > 0 ? (
                <>
                  <p className="text-ink-700">
                    {escondidosPeloPorte.length === 1
                      ? `${escondidosPeloPorte[0].municipio_nome} existe na base`
                      : `${escondidosPeloPorte.length} municípios existem na base`}
                    , mas {escondidosPeloPorte.length === 1 ? "está" : "estão"} abaixo do filtro de
                    população mínima ({fmtInt(popMin)} hab.).
                  </p>
                  <button onClick={() => setPopMin(0)} className="mt-2 text-accent-700 underline">
                    Mostrar sem mínimo de população
                  </button>
                </>
              ) : (
                <p>Nenhum município no recorte — reduza a população mínima ou ajuste a busca.</p>
              )}
            </div>
          )}
        </div>
        <p className="mt-3 text-xs text-ink-500">
          Taxa padronizada disponível apenas para todas as causas (método direto, padrão Brasil
          Censo 2022). ⚠ indica população &lt; 10 mil hab. Detalhes na{" "}
          <a className="text-accent-700 underline" href="/metodologia/">metodologia</a>.
        </p>
      </div>

      <ProcedenciaImpressa
        recorte={{
          titulo: "Painel de mortalidade por município",
          filtros: [
            ["UF", uf],
            ["Ano", String(ano)],
            ["Capítulo CID-10", capDesc],
            ["Sexo", sexo === "TOTAL" ? "ambos" : sexo === "M" ? "masculino" : "feminino"],
            ["População mínima", popMin ? `${fmtInt(popMin)} habitantes` : ""],
            ["Busca", busca],
            ["Exibidos", totalNoRecorte != null
              ? `${Math.min(100, totalNoRecorte)} de ${fmtInt(totalNoRecorte)} no recorte`
              : ""],
          ],
          tabelas: ["mart_mortalidade_municipio"],
          ressalvas: [
            "A tabela impressa mostra no máximo 100 municípios; o recorte pode ser maior — o campo 'Exibidos' diz quantos.",
            "Taxa padronizada por idade é a comparável entre municípios; a bruta não é.",
            "Códigos agregados UF0000 (óbito sem município identificado) não entram na tabela.",
          ],
        }}
      />
    </div>
  );
}

/** As colunas que podem ser escondidas. Município e posição, não. */
const COLUNAS_OPCIONAIS: [string, string][] = [
  ["uf", "UF"],
  ["obitos", "Óbitos"],
  ["populacao", "População"],
  ["bruta", "Taxa bruta"],
  ["padronizada", "Taxa padronizada"],
];

/**
 * Um campo do detalhe da linha.
 *
 * `null` vira "—" com o motivo no `title`, e nunca 0: no painel a taxa ausente
 * significa município sem população publicada para o ano, que é outra coisa
 * que taxa igual a zero.
 */
function Campo({ termo, valor }: { termo: string; valor: string | null }) {
  return (
    <div className="flex justify-between gap-2 border-b border-ink-200/60 py-0.5 sm:block sm:border-0">
      <dt className="font-medium text-ink-500">{termo}</dt>
      <dd className="tabular-nums text-ink-800">
        {valor ?? <span className="text-ink-400" title="Sem dado publicado para este recorte">—</span>}
      </dd>
    </div>
  );
}

export function PainelCliente() {
  // `useSearchParams` exige limite de Suspense na exportação estática — mesmo
  // arranjo já usado pelo boletim.
  return (
    <Suspense fallback={<div className="mx-auto max-w-7xl px-4 py-10 sm:px-6"><Skeleton altura={400} /></div>}>
      <PainelInner />
    </Suspense>
  );
}
