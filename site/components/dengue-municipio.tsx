"use client";

import { Bloco, useCarga } from "@/components/bloco";
import { fmtDec, fmtInt, rest, sdata, type DengueAno } from "@/lib/api";

/**
 * Dengue no boletim municipal: a série histórica e o alerta desta semana.
 *
 * O QUE ESTAVA DESCONECTADO
 * -------------------------
 * O projeto tinha as três peças e nenhuma ligação entre elas: o boletim
 * semanal trazia a vigilância CORRENTE (InfoDengue, com nowcasting), a página
 * `/dengue/` trazia a série HISTÓRICA, e o boletim MUNICIPAL — a página que
 * responde "como está a minha cidade" — não mencionava dengue em lugar nenhum,
 * embora `mart_dengue_municipio_ano` esteja publicada para todos os municípios.
 * Quem queria as duas leituras da própria cidade tinha de visitar três telas e
 * fazer a junção de cabeça.
 *
 * O QUE A AUSÊNCIA NO ALERTA SIGNIFICA — E O QUE NÃO SIGNIFICA
 * ------------------------------------------------------------
 * A edição semanal NOMEIA cerca de 24 municípios (os em alerta e os de maior
 * volume) de uma rede de 451 monitorados, que por sua vez é um recorte dos
 * 5.570. Então não encontrar a cidade nessa lista NÃO quer dizer "sem dengue",
 * nem "fora de alerta", nem "não monitorada" — quer dizer apenas que ela não
 * está entre as nomeadas nesta edição. O texto diz isso com essas palavras, em
 * vez de deixar o silêncio sugerir tranquilidade.
 *
 * CUSTO
 * -----
 * A edição pesa ~43 kB e só serve para descobrir se esta cidade é uma das 24.
 * É uma requisição paga por todos para servir a poucos — aceita porque a
 * ligação entre vigilância corrente e perfil municipal é justamente o que
 * faltava, e porque ela degrada sozinha: se falhar, a série histórica
 * continua, e o cartão diz que a parte corrente não carregou.
 */

interface Vigiado {
  uf: string;
  municipio: string;
  geocode: string;
  nivel: number;
  nivel_label: string;
  casos_notificados: number;
  casos_estimados: number;
  incidencia_100k: number;
  rt: number;
}

interface Edicao {
  edicao: string;
  semana: number;
  ano: number;
  vigilancia_atual: {
    semana_epi: number;
    ano_epi: number;
    dengue: { em_alerta: Vigiado[]; maiores_volumes: Vigiado[] };
    chikungunya: { em_alerta: Vigiado[]; maiores_volumes: Vigiado[] };
  };
}

const COR: Record<string, string> = {
  verde: "text-accent-800",
  amarelo: "text-amber-700",
  laranja: "text-amber-800",
  vermelho: "text-red-800",
};

export function DengueMunicipio({ cod, nome }: { cod: string; nome: string }) {
  const [carga, recarregar] = useCarga<{ serie: DengueAno[]; atual: Vigiado | null; ed: Edicao | null }>(
    async () => {
      const serie = await rest<DengueAno>("mart_dengue_municipio_ano", {
        select: "municipio_cod,municipio_nome,uf_sigla,ano_epi,casos_provaveis,casos_graves,obitos,populacao,incidencia_100k,letalidade_pct",
        municipio_cod: `eq.${cod}`,
        order: "ano_epi",
      });
      if (!serie.length) return { serie, atual: null, ed: null };

      // A vigilância corrente é OPCIONAL: se ela não vier, a série histórica
      // ainda vale. Falhar o cartão inteiro por causa dela puniria a leitura
      // principal por um enfeite.
      let ed: Edicao | null = null;
      let atual: Vigiado | null = null;
      try {
        const index = await sdata<{ edicao: string }[]>("boletins/index");
        if (index[0]) {
          ed = await sdata<Edicao>(`boletins/${index[0].edicao}`);
          const v = ed.vigilancia_atual;
          // O geocode do InfoDengue tem 7 dígitos; o mart usa 6. Comparar pelos
          // 6 primeiros é o que já liga as duas bases no resto do projeto.
          const casa = (m: Vigiado) => m.geocode.slice(0, 6) === cod;
          atual = [...v.dengue.em_alerta, ...v.dengue.maiores_volumes].find(casa)
            ?? [...v.chikungunya.em_alerta, ...v.chikungunya.maiores_volumes].find(casa)
            ?? null;
        }
      } catch {
        ed = null;
      }
      return { serie, atual, ed };
    },
    [cod],
    (d) => d.serie.length === 0,
  );

  return (
    <Bloco carga={carga} recarregar={recarregar} titulo="Dengue" altura={200}
           vazio={`Sem série de dengue publicada para ${nome}.`}>
      {({ serie, atual, ed }) => {
        const ultimo = serie[serie.length - 1];
        // "Maior incidência", e não "pior ano": a comparação é por incidência, e
        // ano sem população publicada não TEM incidência — logo não pode ganhar,
        // por mais casos que tenha. Penápolis expôs isso: 2025 tem 4.729 casos
        // contra 3.287 de 2022, e 2022 aparecia como "pior ano" só porque 2025
        // não tem denominador. Rótulo que promete um superlativo tem de nomear a
        // métrica, e o cartão diz quantos anos ficaram fora da comparação.
        const comIncidencia = serie.filter((a) => a.incidencia_100k != null);
        const pico = comIncidencia.length
          ? comIncidencia.reduce((a, b) => (b.incidencia_100k! > a.incidencia_100k! ? b : a))
          : null;
        const semDenominador = serie.length - comIncidencia.length;

        return (
          <div className="card mt-6">
            <h2 className="font-serif text-xl font-semibold text-ink-900">
              Dengue — série do município
            </h2>
            <p className="mt-1 text-sm text-ink-500">
              Casos prováveis notificados por ano epidemiológico (SINAN, via série histórica
              publicada). Ano mais recente sujeito a revisão.
            </p>

            <div className="mt-4 grid gap-4 sm:grid-cols-3">
              <div>
                <p className="text-xs font-semibold uppercase tracking-wide text-ink-500">
                  {ultimo.ano_epi} — casos prováveis
                </p>
                <p className="mt-1 font-serif text-2xl font-semibold text-ink-900">
                  {fmtInt(ultimo.casos_provaveis)}
                </p>
                <p className="mt-0.5 text-xs text-ink-500">
                  {ultimo.incidencia_100k != null
                    ? `${fmtDec(ultimo.incidencia_100k)} por 100 mil habitantes`
                    : "incidência não publicada (sem população para o ano)"}
                </p>
              </div>
              <div>
                <p className="text-xs font-semibold uppercase tracking-wide text-ink-500">
                  Maior incidência da série
                </p>
                <p className="mt-1 font-serif text-2xl font-semibold text-ink-600">
                  {pico ? pico.ano_epi : "—"}
                </p>
                <p className="mt-0.5 text-xs text-ink-500">
                  {pico
                    ? `${fmtDec(pico.incidencia_100k)} por 100 mil · ${fmtInt(pico.casos_provaveis)} casos`
                    : "nenhum ano da série tem população publicada"}
                  {semDenominador > 0 && pico && (
                    <> · {semDenominador} ano{semDenominador > 1 ? "s" : ""} fora da comparação
                    por não ter população publicada</>
                  )}
                </p>
              </div>
              <div>
                <p className="text-xs font-semibold uppercase tracking-wide text-ink-500">
                  Óbitos por dengue ({ultimo.ano_epi})
                </p>
                <p className="mt-1 font-serif text-2xl font-semibold text-ink-900">
                  {fmtInt(ultimo.obitos)}
                </p>
                <p className="mt-0.5 text-xs text-ink-500">
                  {ultimo.casos_graves != null
                    ? `${fmtInt(ultimo.casos_graves)} casos graves no ano`
                    : "casos graves não publicados"}
                </p>
              </div>
            </div>

            <div className="mt-4 overflow-x-auto tabela-rolavel">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b-2 border-ink-200 text-left text-xs uppercase tracking-wide text-ink-500">
                    <th className="col-id px-3 py-2">Ano</th>
                    <th className="px-3 py-2 text-right">Casos prováveis</th>
                    <th className="px-3 py-2 text-right">Incidência /100 mil</th>
                    <th className="px-3 py-2 text-right">Graves</th>
                    <th className="px-3 py-2 text-right">Óbitos</th>
                  </tr>
                </thead>
                <tbody>
                  {[...serie].reverse().map((a) => (
                    <tr key={a.ano_epi} className="border-b border-ink-100">
                      <td className="col-id px-3 py-1.5 font-medium">{a.ano_epi}</td>
                      <td className="px-3 py-1.5 text-right tabular-nums">{fmtInt(a.casos_provaveis)}</td>
                      <td className="px-3 py-1.5 text-right tabular-nums">
                        {a.incidencia_100k == null ? "—" : fmtDec(a.incidencia_100k)}
                      </td>
                      <td className="px-3 py-1.5 text-right tabular-nums">{fmtInt(a.casos_graves)}</td>
                      <td className="px-3 py-1.5 text-right tabular-nums">{fmtInt(a.obitos)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {/* ── A ponte com a vigilância corrente ── */}
            {ed == null ? (
              <p className="mt-4 rounded-lg border border-ink-200 bg-ink-50 px-3 py-2 text-xs text-ink-600">
                A vigilância da semana corrente não carregou. A série acima é histórica e não
                diz nada sobre a situação desta semana.
              </p>
            ) : atual ? (
              <p className="mt-4 rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-900">
                <strong>Nesta semana:</strong> {nome} aparece no boletim de{" "}
                SE {ed.vigilancia_atual.semana_epi}/{ed.vigilancia_atual.ano_epi} em nível{" "}
                <strong className={COR[atual.nivel_label] ?? ""}>{atual.nivel_label}</strong>, com{" "}
                {fmtInt(atual.casos_notificados)} casos notificados e{" "}
                <strong>{fmtInt(atual.casos_estimados)} estimados</strong> após correção do atraso
                de digitação (nowcasting), Rt {fmtDec(atual.rt, 2)}.{" "}
                <a href={`/boletim-semanal/?e=${ed.edicao}`}
                   className="font-medium underline underline-offset-2">
                  Ver o boletim da semana
                </a>.
              </p>
            ) : (
              <p className="mt-4 rounded-lg border border-ink-200 bg-ink-50 px-3 py-2 text-xs text-ink-600">
                {nome} <strong>não está entre os municípios nomeados</strong> no boletim de
                SE {ed.vigilancia_atual.semana_epi}/{ed.vigilancia_atual.ano_epi}, que lista os
                que estão em alerta e os de maior volume. Isso <strong>não</strong> significa
                ausência de dengue, nem que o município esteja fora de alerta — a rede monitorada
                cobre 451 municípios e a edição nomeia algumas dezenas.{" "}
                <a href="/boletim-semanal/" className="font-medium text-accent-700 underline underline-offset-2">
                  Ver a vigilância da semana
                </a>.
              </p>
            )}
          </div>
        );
      }}
    </Bloco>
  );
}
