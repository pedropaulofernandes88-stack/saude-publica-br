"use client";

import Link from "next/link";
import { Suspense, useEffect, useMemo, useState } from "react";
import { useSearchParams } from "next/navigation";
import { Barras } from "@/components/charts";
import { Kpi, Skeleton } from "@/components/kpi";
import {
  Line, LineChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis,
} from "recharts";
import { Bloco, useCarga } from "@/components/bloco";
import { BotaoExportarCsv } from "@/components/exportar-csv";
import { DengueMunicipio } from "@/components/dengue-municipio";
import { ProcedenciaImpressa } from "@/components/procedencia-impressa";
import { type Carga } from "@/lib/carga";
import { FichaIndicador } from "@/components/ficha-indicador";
import { IcsapPares } from "@/components/icsap-pares";
import { Imunopreveniveis as CardImuno } from "@/components/imunopreveniveis";
import { ehPreliminar, fmtDec, fmtInt, rest, sdata, type CapituloCid, type ClusterMunicipio, type IcsapPares as TIcsapPares, type Imunopreveniveis, type Ivs, type LinhaMunicipio } from "@/lib/api";
import { ehCodigoAgregado } from "@/lib/municipios";
import { EIXO, GRADE, REFERENCIA, SERIE } from "@/lib/tokens";

function SerieTaxas({ data }: { data: { ano: number; bruta: number | null; padronizada: number | null }[] }) {
  return (
    <ResponsiveContainer width="100%" height={300}>
      <LineChart data={data} margin={{ top: 8, right: 16, bottom: 0, left: 8 }}>
        <CartesianGrid stroke={GRADE} vertical={false} />
        <XAxis dataKey="ano" tick={{ fontSize: 12, fill: EIXO }} />
        <YAxis tick={{ fontSize: 12, fill: EIXO }} width={48} />
        <Tooltip
          formatter={(v, name) => [fmtDec(v as number), name === "padronizada" ? "Padronizada /100 mil" : "Bruta /100 mil"]}
          contentStyle={{ borderRadius: 8, borderColor: GRADE, fontSize: 13 }}
        />
        <Line type="monotone" dataKey="bruta" stroke={REFERENCIA} strokeWidth={2} strokeDasharray="5 4" dot={{ r: 2.5 }} />
        <Line type="monotone" dataKey="padronizada" stroke={SERIE} strokeWidth={2.5} dot={{ r: 3 }} />
      </LineChart>
    </ResponsiveContainer>
  );
}

function BoletimInner() {
  const params = useSearchParams();
  const cod = params.get("m") ?? "";
  const [linhas, setLinhas] = useState<LinhaMunicipio[] | null>(null);
  const [capitulos, setCapitulos] = useState<(LinhaMunicipio & { capitulo_cid: string })[] | null>(null);
  const [capsDim, setCapsDim] = useState<CapituloCid[]>([]);
  const [icsap, setIcsap] = useState<TIcsapPares | null>(null);
  const [erro, setErro] = useState<string | null>(null);

  /**
   * Contexto social, estrato e imunopreveníveis passam por `useCarga`.
   *
   * Antes eram `catch(() => {})`: a consulta falhava, o cartão virava `null` e
   * a página passava a AFIRMAR, pela ausência, que este município não tem
   * contexto social nem internações evitáveis. Falha de rede não pode produzir
   * uma afirmação sobre o dado. Ver `lib/carga.ts`.
   */
  const [cargaIvs, recarregarIvs] = useCarga<{ ivs: Ivs; cluster: ClusterMunicipio | null }>(
    async () => {
      if (!cod) throw new Error("sem município");
      const [i, c] = await Promise.all([
        rest<Ivs>("dim_ivs", {
          select: "municipio_cod,taxa_analfabetismo,pct_sem_agua,ivs_score,ivs_quartil",
          municipio_cod: `eq.${cod}`,
        }),
        rest<ClusterMunicipio>("dim_cluster_municipio", {
          select: "municipio_cod,cluster,estrato_cod,perfil", municipio_cod: `eq.${cod}`,
        }),
      ]);
      return i[0] ? { ivs: i[0], cluster: c[0] ?? null } : null as never;
    },
    [cod],
    (d) => !d?.ivs,
  );

  const [cargaImuno, recarregarImuno] = useCarga<{ mun: Imunopreveniveis; uf: Imunopreveniveis[] }>(
    async () => {
      if (!cod) throw new Error("sem município");
      const r = await rest<Imunopreveniveis>("mart_icsap_municipio", {
        select: "municipio_cod,uf_sigla,ano,internacoes_g1,g1_100k,internacoes_icsap",
        municipio_cod: `eq.${cod}`, order: "ano.desc", limit: "1",
      });
      const mun = r[0];
      if (!mun) return null as never;
      // O município contra os demais da mesma UF: taxa isolada não diz se é alta.
      const uf = await rest<Imunopreveniveis>("mart_icsap_municipio", {
        select: "municipio_cod,uf_sigla,ano,internacoes_g1,g1_100k,internacoes_icsap",
        uf_sigla: `eq.${mun.uf_sigla}`, ano: `eq.${mun.ano}`,
      });
      return { mun, uf };
    },
    [cod],
    (d) => !d?.mun,
  );

  useEffect(() => {
    if (!cod) return;
    setLinhas(null); setCapitulos(null); setErro(null);
    Promise.all([
      rest<LinhaMunicipio>("mart_mortalidade_municipio", {
        select: "municipio_cod,municipio_nome,uf_sigla,regiao,ano,obitos,obitos_hospital,obitos_domicilio,populacao,taxa_obitos_100k,ic95_inf,ic95_sup,taxa_padronizada_100k",
        municipio_cod: `eq.${cod}`,
        capitulo_cid: "eq.TOTAL",
        sexo: "eq.TOTAL",
        order: "ano",
      }),
      rest<LinhaMunicipio & { capitulo_cid: string }>("mart_mortalidade_municipio", {
        select: "capitulo_cid,obitos,ano",
        municipio_cod: `eq.${cod}`,
        sexo: "eq.TOTAL",
        capitulo_cid: "neq.TOTAL",
        order: "ano,capitulo_cid",
      }),
      sdata<CapituloCid[]>("capitulos"),
    ])
      .then(([l, c, dim]) => { setLinhas(l); setCapitulos(c); setCapsDim(dim); })
      .catch((e) => setErro(String(e)));
    setIcsap(null);
    rest<TIcsapPares>("mart_icsap_pares", {
      select: "municipio_cod,municipio_nome,uf_sigla,ano,populacao,internacoes_total,internacoes_icsap,"
        + "pct_icsap,arquetipo,criterio_pares,n_pares,mediana_pares_pct,p25_pares_pct,diferenca_pp,"
        + "internacoes_acima_pares,internacoes_acima_p25,custo_associado_reais,leitos_dia_associados,"
        + "leitos_equivalentes_ano,custo_medio_icsap_ref,permanencia_media_icsap_ref,amostra_pequena",
      municipio_cod: `eq.${cod}`,
      // Sem ORDER BY o PostgREST devolve as linhas em ordem indefinida, e o
      // cartão mostrava um ano ARBITRÁRIO — Penápolis exibia 2022 enquanto
      // 2024 existia. Ficou invisível enquanto a view tinha um ano só; a
      // extensão do ICSAP para 2021–2024 expôs.
      order: "ano.desc",
      limit: "1",
    }).then((r) => setIcsap(r[0] ?? null)).catch(() => {});
  }, [cod]);

  /**
   * O ano exibido, e por que ele não é simplesmente o último da série.
   *
   * Era: `linhas[linhas.length - 1]`, o mais recente que existisse. Sair do
   * painel em 2024 e cair num boletim de 2025 preliminar trocava o ano do
   * visitante sem aviso, e o próprio aviso de preliminar mandava "use 2024"
   * sem oferecer como. Agora o painel manda o ano na URL, existe seletor, e o
   * fallback continua sendo o mais recente para quem chega sem `?ano=`.
   *
   * Ano pedido que não existe para este município cai no mais recente em vez
   * de mostrar página vazia — município pequeno pode não ter linha em todo ano.
   */
  const anosDisponiveis = useMemo(
    () => (linhas ?? []).map((l) => l.ano).sort((a, b) => b - a),
    [linhas],
  );
  const anoPedido = Number(params.get("ano")) || null;
  const [anoEscolhido, setAnoEscolhido] = useState<number | null>(null);
  const anoAlvo = anoEscolhido ?? anoPedido;

  const atual = useMemo(() => {
    if (!linhas?.length) return null;
    return (anoAlvo && linhas.find((l) => l.ano === anoAlvo)) || linhas[linhas.length - 1];
  }, [linhas, anoAlvo]);

  const ultimoConsolidado = useMemo(
    () => anosDisponiveis.find((a) => !ehPreliminar(a)) ?? null,
    [anosDisponiveis],
  );

  /** A janela que o gráfico desenha, para o título não prometer outra. */
  const janelaSerie = useMemo(() => {
    if (!linhas?.length) return "";
    return `${linhas[0].ano}–${linhas[linhas.length - 1].ano}`;
  }, [linhas]);

  /**
   * O recorte efetivo, para a ficha dizer de QUE número ela fala.
   *
   * Sem isto a ficha explicaria o indicador em abstrato — e o que o visitante
   * tem na tela é um município e um ano específicos. "Território e período
   * efetivos" é um campo da ficha, não um detalhe.
   */
  const contextoFicha = useMemo(() => {
    if (!atual) return undefined;
    const preliminar = ehPreliminar(atual.ano) ? " · dado preliminar" : " · dado consolidado";
    return `${atual.municipio_nome ?? cod} (${atual.uf_sigla}), ${atual.ano}${preliminar}`;
  }, [atual, cod]);

  /** O endereço acompanha o ano, para o link compartilhado abrir no mesmo. */
  useEffect(() => {
    if (typeof window === "undefined" || !atual || !cod) return;
    window.history.replaceState(null, "", `?m=${cod}&ano=${atual.ano}`);
  }, [cod, atual]);

  const serieTaxas = useMemo(
    () => linhas?.map((l) => ({ ano: l.ano, bruta: l.taxa_obitos_100k, padronizada: l.taxa_padronizada_100k })) ?? null,
    [linhas],
  );

  const capChart = useMemo(() => {
    if (!capitulos || !atual) return null;
    const doAno = capitulos.filter((c) => c.ano === atual.ano);
    return doAno
      .sort((a, b) => b.obitos - a.obitos)
      .slice(0, 8)
      .map((c) => ({ nome: c.capitulo_cid, obitos: c.obitos }));
  }, [capitulos, atual]);

  if (!cod) {
    return (
      <div className="card mx-auto mt-10 max-w-xl text-center">
        <p className="text-ink-700">
          Selecione um município no <Link href="/painel/" className="font-medium text-accent-700 underline">painel</Link>{" "}
          (clique no nome na tabela) para gerar o boletim.
        </p>
      </div>
    );
  }

  // "UF0000" é o código que o SIM usa para óbito sem município identificado —
  // existe no mart, mas não é um município e não rende boletim.
  if (ehCodigoAgregado(cod)) {
    return (
      <div className="card mx-auto mt-10 max-w-xl text-center">
        <p className="text-ink-700">
          O código <span className="font-mono">{cod}</span> não é um município: o SIM o usa para
          agrupar óbitos cujo município de residência não foi identificado. Escolha um município no{" "}
          <Link href="/painel/" className="font-medium text-accent-700 underline">painel</Link>.
        </p>
      </div>
    );
  }

  return (
    <>
      {erro && <div className="card mt-6 border-red-200 bg-red-50 text-sm text-red-800">Falha: {erro}</div>}
      {/* Consulta que VOLTOU VAZIA não é consulta em andamento. Um `?m=` que
          não existe deixava o esqueleto girando para sempre, e a página não
          dizia nem "carregando" nem "não achei" — o visitante ficava olhando
          um retângulo cinza. É a mesma confusão que `lib/carga.ts` resolve nos
          cartões, aqui no nível da página. */}
      {!atual && !erro && linhas === null && <Skeleton altura={400} />}
      {!atual && !erro && linhas !== null && (
        <div className="card mx-auto mt-10 max-w-xl text-center">
          <p className="text-ink-700">
            Não há boletim publicado para o código <span className="font-mono">{cod}</span>.
            A consulta respondeu — o código é que não existe na base de mortalidade.
          </p>
          <p className="mt-2 text-sm text-ink-500">
            O código do município aqui tem <strong>6 dígitos</strong> (o do IBGE sem o dígito
            verificador): Penápolis é <span className="font-mono">353730</span>, não 3536505.
          </p>
          <p className="mt-3">
            <Link href="/painel/" className="font-medium text-accent-700 underline">
              Escolher um município no painel
            </Link>
          </p>
        </div>
      )}
      {atual && (
        <>
          <div className="flex flex-wrap items-start justify-between gap-4">
            <div>
              <h1 className="font-serif text-3xl font-semibold tracking-tight text-ink-950">
                {atual.municipio_nome ?? cod} <span className="text-ink-500">· {atual.uf_sigla}</span>
              </h1>
              <p className="mt-1 text-ink-600">
                Boletim de mortalidade · {atual.regiao} · População {fmtInt(atual.populacao)} ({atual.ano})
              </p>
            </div>
            <div className="flex flex-wrap items-end gap-3 no-print">
              {anosDisponiveis.length > 1 && (
                <div>
                  <label className="label" htmlFor="b-ano">Ano de referência</label>
                  <select id="b-ano" className="select" value={atual.ano}
                          onChange={(e) => setAnoEscolhido(Number(e.target.value))}>
                    {anosDisponiveis.map((a) => (
                      <option key={a} value={a}>{a}{ehPreliminar(a) ? " (preliminar)" : ""}</option>
                    ))}
                  </select>
                </div>
              )}
              <button onClick={() => window.print()} className="btn-primary">🖨 Imprimir / PDF</button>
            </div>
          </div>

          <ResumoExecutivo atual={atual} icsap={icsap} cargaIvs={cargaIvs} janela={janelaSerie}
                           primeiro={linhas?.[0] ?? null} />

          <div className="mt-6 grid gap-4 sm:grid-cols-3">
            <Kpi rotulo={`Óbitos em ${atual.ano}${ehPreliminar(atual.ano) ? " (preliminar)" : ""}`} valor={fmtInt(atual.obitos)}
                 detalhe={`${fmtInt(atual.obitos_hospital)} em hospital · ${fmtInt(atual.obitos_domicilio)} em domicílio`} />
            <Kpi rotulo="Taxa bruta /100 mil" valor={fmtDec(atual.taxa_obitos_100k)}
                 detalhe={atual.ic95_inf != null ? `IC95%: ${fmtDec(atual.ic95_inf)}–${fmtDec(atual.ic95_sup)}` : undefined} />
            <Kpi rotulo="Taxa padronizada /100 mil" valor={fmtDec(atual.taxa_padronizada_100k)}
                 detalhe="ajustada por idade — comparável entre municípios" />
          </div>
          {/* As fichas ficam ABAIXO dos três cartões, não dentro deles: numa
              coluna de um terço da largura a lista de definições quebrava
              palavra a palavra e o nome da tabela estourava o cartão. */}
          <div className="mt-2 space-y-2">
            <FichaIndicador id="obitos" contexto={contextoFicha} />
            <FichaIndicador id="taxa-bruta" contexto={contextoFicha} />
            <FichaIndicador id="taxa-padronizada" contexto={contextoFicha} />
          </div>
          {ehPreliminar(atual.ano) && (
            <p className="mt-3 rounded-lg border border-amber-200 bg-amber-50 px-4 py-2 text-sm text-amber-800">
              ⚠ {atual.ano} é <strong>preliminar</strong>: vem do diretório que o DataSUS
              ainda não fechou (<code>SIM/PRELIM/DORES</code>) e será revisado. O que muda
              ao consolidar não é só o total — a codificação também: entre as duas versões
              de 2024, milhares de óbitos migraram de &quot;causa mal definida&quot; para
              causas específicas.
              {ultimoConsolidado != null && (
                <>
                  {" "}Para comparar com anos anteriores,{" "}
                  <button type="button" onClick={() => setAnoEscolhido(ultimoConsolidado)}
                          className="font-semibold underline underline-offset-2 no-print">
                    ver {ultimoConsolidado}, o último consolidado
                  </button>
                  <span className="print-only">use {ultimoConsolidado}, o último consolidado.</span>
                </>
              )}
            </p>
          )}
          {(atual.populacao ?? 0) < 10_000 && (
            <p className="mt-3 rounded-lg border border-amber-200 bg-amber-50 px-4 py-2 text-sm text-amber-800">
              ⚠ Município com população pequena: taxas anuais são instáveis. Interprete com o IC95%.
            </p>
          )}

          <Bloco carga={cargaIvs} recarregar={recarregarIvs} titulo="Contexto social"
                 vazio="Este município não tem linha no proxy de vulnerabilidade do Censo 2022."
                 altura={220}>
            {({ ivs, cluster }) => (
            <div className="card mt-6">
              <h2 className="font-serif text-xl font-semibold text-ink-900">Contexto social (Censo 2022)</h2>
              <div className="mt-3 grid gap-4 sm:grid-cols-3">
                <div>
                  <p className="text-xs font-semibold uppercase tracking-wide text-ink-500">Vulnerabilidade (proxy)</p>
                  <p className="mt-1 font-serif text-2xl font-semibold text-ink-900">
                    {fmtDec(ivs.ivs_score, 0)}<span className="text-base text-ink-500">/100</span>
                    <span className="ml-2 rounded bg-ink-100 px-2 py-0.5 text-xs font-medium text-ink-600">{ivs.ivs_quartil}</span>
                  </p>
                </div>
                <div>
                  <p className="text-xs font-semibold uppercase tracking-wide text-ink-500">Analfabetismo (15+)</p>
                  <p className="mt-1 font-serif text-2xl font-semibold text-ink-900">{fmtDec(ivs.taxa_analfabetismo, 1)}%</p>
                </div>
                <div>
                  <p className="text-xs font-semibold uppercase tracking-wide text-ink-500">Sem água encanada</p>
                  <p className="mt-1 font-serif text-2xl font-semibold text-ink-900">{fmtDec(ivs.pct_sem_agua, 1)}%</p>
                </div>
              </div>
              <p className="mt-2 text-xs text-ink-500">
                Proxy de vulnerabilidade (z-score de analfabetismo e falta de água, Censo 2022) — quartil entre
                os 5.570 municípios; Q4 = mais vulnerável. Não é o IVS oficial do IPEA. Associações entre
                vulnerabilidade e saúde aqui são <strong>municipais</strong> (agregadas): descrevem padrões,
                não implicam risco individual nem causalidade (falácia ecológica).
              </p>
              {cluster && (
                <p className="mt-3 border-t border-ink-200 pt-3 text-sm text-ink-700">
                  <span className="font-semibold">Estrato de saúde:</span> {cluster.perfil}
                  <span className="ml-2 rounded bg-ink-100 px-2 py-0.5 text-xs text-ink-600">
                    {cluster.estrato_cod ? `${cluster.estrato_cod} · ` : ""}estrato {cluster.cluster}/27
                  </span>
                  <span className="mt-1 block text-xs text-ink-500">
                    Cruzamento dos tercis de mortalidade × vulnerabilidade × internações (2023), com cortes
                    fixos. O estrato depende só dos valores deste município — não muda entre consultas.
                  </span>
                </p>
              )}
              <FichaIndicador id="ivs-proxy" contexto={`${atual.municipio_nome ?? cod} (${atual.uf_sigla}), Censo 2022`} />
            </div>
            )}
          </Bloco>

          {icsap && (
            <>
              <IcsapPares dados={icsap} />
              <FichaIndicador id="icsap-pct" contexto={`${icsap.municipio_nome ?? cod} (${icsap.uf_sigla}), ${icsap.ano}`} />
            </>
          )}

          <DengueMunicipio cod={cod} nome={atual.municipio_nome ?? cod} />

          <Bloco carga={cargaImuno} recarregar={recarregarImuno} titulo="Internações evitáveis por vacina"
                 vazio="Sem internações do grupo 1 da ICSAP publicadas para este município."
                 altura={180}>
            {(imuno) => (
              <>
                <CardImuno mun={imuno.mun} uf={imuno.uf} />
                <FichaIndicador id="imunopreveniveis-g1" contexto={`${atual.municipio_nome ?? cod} (${imuno.mun.uf_sigla}), ${imuno.mun.ano}`} />
              </>
            )}
          </Bloco>

          <div className="card mt-6">
            {/* O gráfico traz a série INTEIRA, então o título segue a janela
                dela — e não o ano selecionado no seletor. Com `atual.ano`,
                escolher um ano do meio rotulava o gráfico com um intervalo
                menor do que o que ele desenha. */}
            <h2 className="font-serif text-xl font-semibold text-ink-900">
              Taxas de mortalidade, {janelaSerie}
            </h2>
            <p className="mt-1 text-sm text-ink-500">Verde: padronizada por idade. Cinza tracejada: bruta.</p>
            <div className="mt-4">{serieTaxas ? <SerieTaxas data={serieTaxas} /> : <Skeleton altura={300} />}</div>
          </div>

          <div className="card mt-6">
            <h2 className="font-serif text-xl font-semibold text-ink-900">
              Principais grupos de causas ({atual.ano})
            </h2>
            <div className="mt-4">{capChart ? <Barras data={capChart} horizontal altura={300} titulo={`Principais grupos de causas (${atual.ano})`} /> : <Skeleton altura={300} />}</div>
            <div className="mt-3 grid gap-1 text-xs text-ink-500 sm:grid-cols-2">
              {capChart?.map((c) => {
                const d = capsDim.find((x) => x.capitulo === c.nome);
                return d ? <p key={c.nome}><b>{c.nome}</b>: {d.descricao}</p> : null;
              })}
            </div>
          </div>

          <div className="card mt-6 text-sm leading-relaxed text-ink-600">
            <p>
              <b>Fontes:</b> SIM/DataSUS (Ministério da Saúde) e IBGE (Censo 2022 e
              Estimativas). Óbitos não fetais, por município de residência. Padronização
              direta com padrão Brasil/Censo 2022; IC95% por método gamma. Ano mais
              recente pode ser preliminar. Metodologia completa:{" "}
              <span className="font-medium">saudeemdado.com/metodologia</span>.
            </p>
            <p className="mt-2">
              Gerado por <b>saudeemdado.com</b> — plataforma aberta e sem fins lucrativos.
            </p>
            <div className="mt-3 no-print">
              <BotaoExportarCsv
                base="boletim"
                rotulo="⬇ Exportar a série em CSV"
                recorte={{
                  titulo: `Boletim municipal — ${atual.municipio_nome ?? cod} (${atual.uf_sigla})`,
                  filtros: [
                    ["Município", `${atual.municipio_nome ?? cod} (${cod})`],
                    ["UF", atual.uf_sigla],
                    ["Série", janelaSerie],
                  ],
                  tabelas: ["mart_mortalidade_municipio"],
                  ressalvas: [
                    "Óbitos não fetais, por município de RESIDÊNCIA.",
                    "Padronização direta pelo padrão Brasil/Censo 2022; IC95% por método gamma.",
                    "O ano mais recente pode ser preliminar (SIM/PRELIM/DORES) e será revisado — os valores só crescem, e a codificação também muda.",
                    "Taxa padronizada é a comparável entre municípios; a bruta não é.",
                  ],
                }}
                colunas={["ano", "municipio_cod", "municipio", "uf", "populacao", "obitos",
                          "obitos_hospital", "obitos_domicilio", "taxa_bruta_100k",
                          "ic95_inf", "ic95_sup", "taxa_padronizada_100k"]}
                linhas={() => (linhas ?? []).map((l) => [
                  l.ano, l.municipio_cod, l.municipio_nome, l.uf_sigla, l.populacao, l.obitos,
                  l.obitos_hospital, l.obitos_domicilio, l.taxa_obitos_100k,
                  l.ic95_inf, l.ic95_sup, l.taxa_padronizada_100k,
                ])}
              />
            </div>
          </div>

          {/* No papel, o que `@media print` tira do cabeçalho e do rodapé:
              endereço, versão da publicação, checksum e citação. */}
          <ProcedenciaImpressa
            recorte={{
              titulo: `Boletim municipal — ${atual.municipio_nome ?? cod} (${atual.uf_sigla}), ${atual.ano}`,
              filtros: [
                ["Município", `${atual.municipio_nome ?? cod} (${cod})`],
                ["Ano de referência", `${atual.ano}${ehPreliminar(atual.ano) ? " — PRELIMINAR" : " — consolidado"}`],
                ["Série exibida", janelaSerie],
              ],
              tabelas: ["mart_mortalidade_municipio", "mart_icsap_pares", "dim_ivs"],
              ressalvas: [
                "Óbitos não fetais, por município de residência.",
                "Taxa padronizada pelo padrão Brasil/Censo 2022 é a comparável entre municípios.",
              ],
            }}
          />
        </>
      )}
    </>
  );
}

/**
 * O essencial em prosa, antes de qualquer gráfico.
 *
 * O boletim abria em três KPIs e nove cartões: quem chegava com uma pergunta
 * simples — "como está meu município?" — tinha de montar a resposta sozinho,
 * lendo número por número. Este bloco responde primeiro e deixa o resto como
 * aprofundamento.
 *
 * NENHUM NÚMERO AQUI É DIGITADO. Todos saem de `atual`, de `icsap` e da carga
 * do IVS — inclusive as comparações, que são calculadas na hora. Um resumo com
 * número escrito à mão é a forma mais rápida de a prosa e a tabela discordarem.
 *
 * O que não carregou simplesmente NÃO É AFIRMADO: cada frase depende do seu
 * dado existir. Resumo é onde a tentação de completar a frase com uma suposição
 * é maior, e é onde ela custaria mais caro.
 */
function ResumoExecutivo({
  atual, icsap, cargaIvs, janela, primeiro,
}: {
  atual: LinhaMunicipio;
  icsap: TIcsapPares | null;
  cargaIvs: Carga<{ ivs: Ivs; cluster: ClusterMunicipio | null }>;
  janela: string;
  primeiro: LinhaMunicipio | null;
}) {
  const ivs = cargaIvs.estado === "ok" ? cargaIvs.dados.ivs : null;

  // Variação da taxa padronizada entre a primeira e a última ponta da série.
  // Só existe se as DUAS pontas tiverem taxa: comparar contra `null` produziria
  // uma variação inventada.
  const varPad =
    primeiro && primeiro.ano !== atual.ano
      && primeiro.taxa_padronizada_100k != null && atual.taxa_padronizada_100k != null
      ? ((atual.taxa_padronizada_100k - primeiro.taxa_padronizada_100k)
         / primeiro.taxa_padronizada_100k) * 100
      : null;

  return (
    <div className="card mt-6 border-accent-200 bg-accent-50/40">
      <h2 className="font-serif text-lg font-semibold text-ink-900">Em resumo</h2>
      <ul className="mt-2 space-y-1.5 text-sm leading-relaxed text-ink-700">
        <li>
          <strong>{fmtInt(atual.obitos)} óbitos</strong> em {atual.ano}
          {ehPreliminar(atual.ano) && <> (ano <strong>preliminar</strong>, será revisado)</>}
          {atual.taxa_padronizada_100k != null && (
            <> — taxa padronizada de <strong>{fmtDec(atual.taxa_padronizada_100k)}</strong> por
            100 mil, que é a comparável com outros municípios</>
          )}.
        </li>

        {varPad != null && (
          <li>
            Na série {janela}, a taxa padronizada{" "}
            <strong>{varPad > 0 ? "subiu" : varPad < 0 ? "caiu" : "ficou estável"}</strong>
            {varPad !== 0 && <> {fmtDec(Math.abs(varPad), 1)}%</>} em relação a {primeiro!.ano}.
            {" "}Variação entre duas pontas não é tendência: veja a série completa abaixo.
          </li>
        )}

        {icsap && (
          <li>
            Internações evitáveis: <strong>{fmtDec(icsap.pct_icsap, 1)}%</strong> das internações
            de {icsap.ano} eram sensíveis à atenção primária,{" "}
            {icsap.diferenca_pp > 0 ? (
              <>
                <strong>{fmtDec(icsap.diferenca_pp, 1)} p.p. acima</strong> da mediana dos{" "}
                {fmtInt(icsap.n_pares)} municípios do mesmo estrato de saúde
                {icsap.internacoes_acima_pares > 0 && (
                  <> — {fmtInt(icsap.internacoes_acima_pares)} internações a mais que essa mediana</>
                )}
              </>
            ) : (
              <>
                <strong>na mediana ou abaixo</strong> dos {fmtInt(icsap.n_pares)} municípios do
                mesmo estrato de saúde
              </>
            )}.
          </li>
        )}

        {ivs && (
          <li>
            Contexto social: vulnerabilidade-proxy no <strong>{ivs.ivs_quartil}</strong> de 4
            quartis (Q4 = mais vulnerável), com {fmtDec(ivs.taxa_analfabetismo, 1)}% de analfabetismo
            e {fmtDec(ivs.pct_sem_agua, 1)}% dos domicílios sem água encanada (Censo 2022).
            {" "}A associação é ecológica: descreve o município, não pessoas.
          </li>
        )}

        {cargaIvs.estado === "erro" && (
          <li className="text-red-800">
            O contexto social não carregou — {cargaIvs.mensagem}. Isto é falha de consulta,
            não ausência de dado.
          </li>
        )}
      </ul>
    </div>
  );
}

export function BoletimCliente() {
  return (
    <div className="mx-auto max-w-5xl px-4 py-10 sm:px-6">
      <Suspense fallback={<Skeleton altura={400} />}>
        <BoletimInner />
      </Suspense>
    </div>
  );
}
