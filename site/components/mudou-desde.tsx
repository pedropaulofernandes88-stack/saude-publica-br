"use client";

import { Bloco, useCarga } from "@/components/bloco";
import { fmtInt, sdata } from "@/lib/api";

/**
 * O que mudou desde a edição anterior do boletim semanal.
 *
 * O DADO JÁ EXISTIA E NINGUÉM VIA
 * -------------------------------
 * `build-alertas.mjs` já compara cada edição com a anterior e grava
 * `alertas-<edicao>.json` com os municípios que ENTRARAM em alerta, os que
 * AGRAVARAM e os que SAÍRAM — por doença e por UF. Esse arquivo existia só
 * para disparar e-mail. Quem abria o boletim no site via um retrato da semana
 * sem nenhuma noção de movimento: sete edições arquivadas e nada dizendo o que
 * é novo em cada uma.
 *
 * OS QUE SAÍRAM ENTRAM JUNTO, E NÃO É DETALHE
 * -------------------------------------------
 * Mostrar só quem piorou faria toda semana parecer uma semana de piora, que é
 * o viés de um painel de vigilância que só conta alarme. `resolvidos` vem do
 * mesmo arquivo e custa a mesma linha de código.
 *
 * ZERO MUDANÇA NÃO PODE PARECER FALHA
 * -----------------------------------
 * Uma semana calma e uma requisição que falhou produziriam a mesma tela vazia.
 * Por isso passa por `useCarga`/`Bloco`: "nenhum município entrou em alerta" é
 * uma AFIRMAÇÃO sobre a semana, e só pode ser feita quando a consulta
 * respondeu. Ver `lib/carga.ts`.
 */

interface Municipio {
  doenca: string;
  municipio: string;
  geocode: string;
  nivel: number | null;
  nivel_label?: string;
  nivel_anterior: number | null;
}

interface PorUf {
  uf: string;
  novos: Municipio[];
  agravados: Municipio[];
  total: number;
}

interface Alertas {
  edicao: string;
  edicao_anterior: string | null;
  linha_de_base: boolean;
  total_novos: number;
  total_agravados: number;
  por_uf: PorUf[];
  dengue?: { resolvidos: (Municipio & { uf: string })[] };
  chikungunya?: { resolvidos: (Municipio & { uf: string })[] };
}

const NIVEL = ["", "verde", "amarelo", "laranja", "vermelho"];
const nomeDoNivel = (n: number | null) => (n == null ? "sem alerta" : NIVEL[n] ?? `nível ${n}`);

function Linha({ m, uf }: { m: Municipio; uf: string }) {
  return (
    <li className="py-0.5">
      <a href={`/boletim/?m=${m.geocode.slice(0, 6)}`} className="font-medium hover:underline">
        {m.municipio}
      </a>{" "}
      <span className="text-ink-500">· {uf} · {m.doenca}</span>{" "}
      <span className="text-ink-600">
        ({nomeDoNivel(m.nivel_anterior)} → {nomeDoNivel(m.nivel)})
      </span>
    </li>
  );
}

export function MudouDesde({ edicao, ehMaisAntiga }: { edicao: string; ehMaisAntiga: boolean }) {
  const [carga, recarregar] = useCarga<Alertas | null>(
    async () => {
      try {
        return await sdata<Alertas>(`boletins/alertas-${edicao}`);
      } catch {
        // A edição mais antiga do arquivo não tem predecessora, então não tem
        // arquivo de comparação — e isso é NORMAL, não falha. Em qualquer outra
        // edição, arquivo faltando é problema e precisa aparecer como tal.
        if (ehMaisAntiga) return null;
        throw new Error("comparação com a edição anterior não foi publicada");
      }
    },
    [edicao, ehMaisAntiga],
    () => false,
  );

  return (
    <Bloco carga={carga} recarregar={recarregar} titulo="O que mudou desde a edição anterior"
           altura={140}>
      {(a) => {
        if (!a || a.linha_de_base || !a.edicao_anterior) {
          return (
            <div className="card mt-6">
              <h2 className="font-serif text-lg font-semibold text-ink-900">
                O que mudou desde a edição anterior
              </h2>
              <p className="mt-2 text-sm text-ink-600">
                Esta é a primeira edição do arquivo — não há edição anterior com que comparar.
                Não significa que nada mudou na vigilância; significa que o arquivo começa aqui.
              </p>
            </div>
          );
        }

        const resolvidos = [
          ...(a.dengue?.resolvidos ?? []).map((m) => ({ ...m, doenca: "dengue" })),
          ...(a.chikungunya?.resolvidos ?? []).map((m) => ({ ...m, doenca: "chikungunya" })),
        ];
        const nada = a.total_novos === 0 && a.total_agravados === 0 && resolvidos.length === 0;

        return (
          <div className="card mt-6">
            <h2 className="font-serif text-lg font-semibold text-ink-900">
              O que mudou desde a {a.edicao_anterior.replace(/^(\d{4})-se(\d+)$/, "SE $2/$1")}
            </h2>

            <div className="mt-3 flex flex-wrap gap-x-6 gap-y-1 text-sm">
              <span><strong className="text-amber-800">{fmtInt(a.total_novos)}</strong> entraram em alerta</span>
              <span><strong className="text-red-800">{fmtInt(a.total_agravados)}</strong> agravaram</span>
              <span><strong className="text-accent-800">{fmtInt(resolvidos.length)}</strong> saíram do alerta</span>
            </div>

            {nada ? (
              <p className="mt-3 text-sm text-ink-600">
                Nenhum município mudou de nível entre as duas edições. A comparação foi feita e
                não encontrou movimento — é resultado, não ausência de dado.
              </p>
            ) : (
              <div className="mt-3 grid gap-4 text-sm sm:grid-cols-2">
                {(a.total_novos > 0 || a.total_agravados > 0) && (
                  <div>
                    <p className="text-xs font-semibold uppercase tracking-wide text-ink-500">
                      Entraram ou agravaram
                    </p>
                    <ul className="mt-1">
                      {a.por_uf.flatMap((u) =>
                        [...u.novos, ...u.agravados].map((m) => (
                          <Linha key={`${u.uf}-${m.geocode}-${m.doenca}`} m={m} uf={u.uf} />
                        )),
                      )}
                    </ul>
                  </div>
                )}
                {resolvidos.length > 0 && (
                  <div>
                    <p className="text-xs font-semibold uppercase tracking-wide text-ink-500">
                      Saíram do alerta
                    </p>
                    <ul className="mt-1">
                      {resolvidos.map((m) => (
                        <li key={`${m.geocode}-${m.doenca}`} className="py-0.5">
                          <a href={`/boletim/?m=${m.geocode.slice(0, 6)}`}
                             className="font-medium hover:underline">{m.municipio}</a>{" "}
                          <span className="text-ink-500">· {m.uf} · {m.doenca}</span>{" "}
                          <span className="text-ink-600">
                            ({nomeDoNivel(m.nivel_anterior)} → {nomeDoNivel(m.nivel)})
                          </span>
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            )}

            <p className="mt-3 text-xs text-ink-500">
              Nível de alerta do InfoDengue (Fiocruz/FGV): verde, amarelo, laranja, vermelho.
              Mudança de nível reflete o modelo de alerta da semana, que usa casos estimados por
              nowcasting — a contagem crua da semana corrente subestima.
            </p>
          </div>
        );
      }}
    </Bloco>
  );
}
