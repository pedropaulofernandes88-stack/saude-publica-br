"use client";

import { useState } from "react";
import { Bloco, useCarga } from "@/components/bloco";
import { fmtDec, fmtInt, rest, type IcsapPares } from "@/lib/api";

const fmtReais = (v: number | null | undefined) =>
  v == null ? "—"
  : v >= 1e6 ? `R$ ${fmtDec(v / 1e6, 1)} mi`
  : v >= 1e3 ? `R$ ${fmtDec(v / 1e3, 0)} mil`
  : `R$ ${fmtInt(v)}`;

/**
 * Traduz o indicador ICSAP na pergunta que um gestor faz: "quanto estou acima de
 * municípios comparáveis, e o que isso representa em internações, leitos e custo?".
 *
 * O enquadramento é deliberado: DISTÂNCIA até os pares, nunca "economia". Ver as
 * ressalvas no rodapé do card — elas não são disclaimer decorativo, são o que
 * separa um número útil de um número enganoso.
 */
/**
 * Quem são os pares — a lista, não só a contagem.
 *
 * O cartão dizia "comparado com 272 municípios do mesmo grupo" e nunca dizia
 * QUAIS. Uma comparação cujo grupo de referência é invisível não é conferível:
 * quem discorda do resultado não tem o que examinar, e quem concorda também
 * não. O grupo é definido pelo arquétipo (estrato de saúde), então ele é
 * exatamente reprodutível por uma consulta.
 *
 * A consulta só sai quando alguém abre a lista — 272 linhas que não servem a
 * quem veio ler o número.
 */
function ListaDePares({ dados }: { dados: IcsapPares }) {
  const [aberta, setAberta] = useState(false);
  const [carga, recarregar] = useCarga<IcsapPares[]>(
    async () => {
      if (!aberta) return [] as IcsapPares[];
      return rest<IcsapPares>("mart_icsap_pares", {
        select: "municipio_cod,municipio_nome,uf_sigla,pct_icsap,populacao,internacoes_total",
        arquetipo: `eq.${dados.arquetipo}`,
        ano: `eq.${dados.ano}`,
        order: "pct_icsap.desc.nullslast",
      });
    },
    [aberta, dados.arquetipo, dados.ano],
    (d) => aberta && d.length === 0,
  );

  return (
    <div className="mt-4 border-t border-ink-100 pt-3">
      <button
        onClick={() => setAberta((v) => !v)}
        className="text-sm font-medium text-accent-700 underline underline-offset-2 no-print"
      >
        {/* Sem contagem no rótulo fechado: antes de abrir, a consulta ainda
            não saiu e o único número disponível é `n_pares` — que conta
            município-ANO, não município (68 municípios x 4 anos = 272). Rótulo
            que promete um número errado é pior que rótulo sem número. */}
        {aberta ? "Ocultar" : "Ver os municípios do grupo"}
      </button>

      {aberta && (
        <div className="mt-3">
          <p className="text-xs text-ink-500">
            Grupo: <strong>{dados.arquetipo}</strong> — {dados.criterio_pares}, {dados.ano}.
            Ordenado pela proporção de ICSAP; este município aparece destacado.
          </p>
          <p className="mt-2 rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-xs text-amber-900">
            <strong>Limitação declarada:</strong> a mediana de referência do grupo é calculada
            sobre 2021–2024 <em>somados</em>, não sobre o ano exibido — e a proporção de ICSAP
            variou bastante nesse intervalo. A lista acima é do ano; a mediana, do período.
            Está registrado na migração que introduziu os estratos e é decisão pendente.
          </p>
          <Bloco carga={carga} recarregar={recarregar} titulo="Lista de pares" altura={160}
                 vazio="Nenhum outro município neste grupo e ano.">
            {(pares) => (
              <div className="mt-2 max-h-80 overflow-y-auto rounded-lg border border-ink-200">
                <table className="w-full text-sm">
                  <thead className="bg-ink-50">
                    <tr className="text-left text-xs uppercase tracking-wide text-ink-500">
                      <th className="px-3 py-2">Município</th>
                      <th className="px-3 py-2 text-right">População</th>
                      <th className="px-3 py-2 text-right">% ICSAP</th>
                    </tr>
                  </thead>
                  <tbody>
                    {pares.map((m) => {
                      const eh = m.municipio_cod === dados.municipio_cod;
                      return (
                        <tr key={m.municipio_cod}
                            className={`border-t border-ink-100 ${eh ? "bg-accent-50 font-semibold text-accent-800" : ""}`}>
                          <td className="px-3 py-1.5">
                            {eh ? "▸ " : ""}
                            <a href={`/boletim/?m=${m.municipio_cod}`} className="hover:underline">
                              {m.municipio_nome} <span className="font-normal text-ink-500">· {m.uf_sigla}</span>
                            </a>
                          </td>
                          <td className="px-3 py-1.5 text-right tabular-nums">
                            {m.populacao ? fmtInt(m.populacao) : "—"}
                          </td>
                          <td className="px-3 py-1.5 text-right tabular-nums">
                            {fmtDec(m.pct_icsap, 1)}%
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            )}
          </Bloco>
        </div>
      )}
    </div>
  );
}

export function IcsapPares({ dados }: { dados: IcsapPares }) {
  const acima = dados.internacoes_acima_pares > 0;

  return (
    <div className="card mt-6">
      <h2 className="font-serif text-xl font-semibold text-ink-900">
        Internações evitáveis — distância até municípios semelhantes
      </h2>
      <p className="mt-1 text-sm text-ink-500">
        Comparado com os municípios do mesmo grupo ({dados.criterio_pares}
        {dados.arquetipo ? `: ${dados.arquetipo}` : ""}). ICSAP = internações por condições
        sensíveis à atenção primária (Lista Brasileira), {dados.ano}.
      </p>

      <ListaDePares dados={dados} />

      <div className="mt-4 grid gap-4 sm:grid-cols-3">
        <div>
          <p className="text-xs font-semibold uppercase tracking-wide text-ink-500">Neste município</p>
          <p className="mt-1 font-serif text-2xl font-semibold text-ink-900">
            {fmtDec(dados.pct_icsap, 1)}<span className="text-base text-ink-500">%</span>
          </p>
          <p className="mt-0.5 text-xs text-ink-500">
            {fmtInt(dados.internacoes_icsap)} de {fmtInt(dados.internacoes_total)} internações
          </p>
        </div>
        <div>
          <p className="text-xs font-semibold uppercase tracking-wide text-ink-500">Mediana dos pares</p>
          <p className="mt-1 font-serif text-2xl font-semibold text-ink-600">
            {fmtDec(dados.mediana_pares_pct, 1)}<span className="text-base text-ink-500">%</span>
          </p>
          <p className="mt-0.5 text-xs text-ink-500">
            os 25% melhores do grupo: {fmtDec(dados.p25_pares_pct, 1)}%
          </p>
        </div>
        <div>
          <p className="text-xs font-semibold uppercase tracking-wide text-ink-500">Diferença</p>
          <p className={`mt-1 font-serif text-2xl font-semibold ${acima ? "text-red-700" : "text-accent-700"}`}>
            {dados.diferenca_pp > 0 ? "+" : ""}{fmtDec(dados.diferenca_pp, 1)}
            <span className="text-base text-ink-500"> p.p.</span>
          </p>
          <p className="mt-0.5 text-xs text-ink-500">
            {acima ? "acima da mediana dos pares" : "na mediana ou abaixo"}
          </p>
        </div>
      </div>

      {acima ? (
        <>
          <div className="mt-5 rounded-lg border border-amber-200 bg-amber-50 p-4">
            <p className="text-sm font-semibold text-amber-900">
              Se este município estivesse na mediana dos seus pares, teria tido
            </p>
            <div className="mt-3 grid gap-4 sm:grid-cols-3">
              <div>
                <p className="font-serif text-3xl font-semibold text-amber-900">
                  {fmtInt(dados.internacoes_acima_pares)}
                </p>
                <p className="text-xs text-amber-800">internações evitáveis a menos, no ano</p>
              </div>
              <div>
                <p className="font-serif text-3xl font-semibold text-amber-900">
                  {fmtDec(dados.leitos_equivalentes_ano, 0)}
                </p>
                <p className="text-xs text-amber-800">
                  leitos livres o ano inteiro ({fmtInt(dados.leitos_dia_associados)} leitos-dia)
                </p>
              </div>
              <div>
                <p className="font-serif text-3xl font-semibold text-amber-900">
                  {fmtReais(dados.custo_associado_reais)}
                </p>
                <p className="text-xs text-amber-800">em internações não realizadas</p>
              </div>
            </div>
            {dados.leitos_equivalentes_ano == null && (
              <p className="mt-3 border-t border-amber-200 pt-3 text-sm text-amber-900">
                A tradução em leitos e em reais está <strong>temporariamente suspensa</strong>: o
                custo e a permanência por internação passaram a ser calculados sobre a AIH normal,
                sem a AIH de continuação, e o SIH está sendo reprocessado. A comparação com os
                pares acima não depende desse ajuste. Ver §10 da metodologia.
              </p>
            )}
            {dados.internacoes_acima_p25 > dados.internacoes_acima_pares && (
              <p className="mt-3 border-t border-amber-200 pt-3 text-sm text-amber-900">
                Contra os <strong>25% melhores</strong> do grupo ({fmtDec(dados.p25_pares_pct, 1)}%), a
                diferença sobe para <strong>{fmtInt(dados.internacoes_acima_p25)}</strong> internações.
              </p>
            )}
          </div>

          <div className="mt-4 rounded-lg border border-ink-200 bg-ink-50 p-4 text-sm leading-relaxed text-ink-700">
            <p className="font-semibold text-ink-900">Como (não) ler estes números</p>
            <ul className="mt-2 space-y-1.5">
              <li>
                <strong>Não é economia disponível.</strong> Chegar à mediana exige{" "}
                <em>investir</em> em atenção primária — mais equipes, mais acompanhamento de
                crônicos —, não cortar. O valor mostra o tamanho do problema, não um caixa a resgatar.
              </li>
              <li>
                <strong>Nem toda ICSAP é evitável.</strong> A Lista Brasileira reúne condições
                <em> sensíveis</em> à atenção primária: boa cobertura reduz, não zera. Por isso a
                referência é a mediana dos pares, não zero.
              </li>
              <li>
                <strong>É uma associação municipal (ecológica).</strong> Descreve um padrão do
                município, não risco individual, e não estabelece causa.
              </li>
              <li>
                <strong>Proporção alta pode ser boa notícia disfarçada.</strong> Onde o acesso
                hospitalar é restrito, internações eletivas somem e a fatia de ICSAP sobe. Cruze
                com a oferta de leitos antes de concluir que a atenção primária falha.
              </li>
            </ul>
          </div>
        </>
      ) : (
        <p className="mt-5 rounded-lg border border-accent-700/20 bg-accent-700/[0.04] px-4 py-3 text-sm text-ink-700">
          A proporção de internações evitáveis está <strong>na mediana ou abaixo</strong> da dos
          municípios comparáveis. Isso não significa ausência de ICSAP — significa que, entre
          pares de perfil semelhante, este município não está acima do padrão.
        </p>
      )}

      {dados.amostra_pequena && (
        <p className="mt-3 rounded-lg border border-amber-200 bg-amber-50 px-4 py-2 text-sm text-amber-800">
          ⚠ Município com menos de 100 internações no ano: a proporção é instável e a comparação,
          frágil. Interprete com cautela.
        </p>
      )}

      <p className="mt-3 border-t border-ink-100 pt-3 text-xs leading-relaxed text-ink-500">
        Custo e permanência por internação ICSAP (R$ {fmtDec(dados.custo_medio_icsap_ref, 0)} e{" "}
        {fmtDec(dados.permanencia_media_icsap_ref, 1)} dias) derivam dos agravos traçadores da
        Lista Brasileira presentes na base (asma, DPOC, pneumonia, diabetes, insuficiência
        cardíaca e doença cerebrovascular). Esses seis pendem para o lado caro da lista, então o
        valor em reais é um <strong>teto</strong>, não uma média fiel. Fonte: SIH/SUS {dados.ano}.
      </p>
    </div>
  );
}
