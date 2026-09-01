import { fmtDec, fmtInt, type Imunopreveniveis as Dados } from "@/lib/api";

/**
 * Grupo 1 da Lista Brasileira de ICSAP: internações por doença prevenível por
 * imunização.
 *
 * Mostra o município contra a mediana da própria UF, e não sozinho. Uma taxa
 * municipal isolada não diz se é alta — e o próprio projeto já mediu que ICSAP
 * responde a porte e oferta hospitalar, não só a qualidade da atenção básica.
 *
 * O que este card deliberadamente NÃO faz: sugerir que o número mede cobertura
 * vacinal do município. As doses aplicadas existem na base (PNI/RNDS), mas o
 * recorte municipal delas é publicado só por download — e cobertura vacinal
 * municipal foi testada e reprovada por viés de denominador. Cruzar aqui daria
 * ao leitor uma leitura causal que o dado não sustenta.
 */
export function Imunopreveniveis({ mun, uf }: { mun: Dados; uf: Dados[] }) {
  const taxas = uf
    .map((m) => m.g1_100k)
    .filter((v): v is number => v != null && v > 0)
    .sort((a, b) => a - b);
  const mediana = taxas.length ? taxas[Math.floor(taxas.length / 2)] : null;
  const taxa = mun.g1_100k;
  const n = mun.internacoes_g1;

  // Sem internação do grupo 1 é resultado, não ausência de dado — e no
  // município pequeno é o caso comum. Dizer isso é melhor que esconder o card.
  const semCaso = n === 0;
  const acima = taxa != null && mediana != null && taxa > mediana;
  const razao = taxa != null && mediana != null && mediana > 0 ? taxa / mediana : null;

  const pctDoIcsap =
    n != null && mun.internacoes_icsap ? (100 * n) / mun.internacoes_icsap : null;

  return (
    <div className="card mt-6">
      <h2 className="font-serif text-xl font-semibold text-ink-900">
        Internações por doença prevenível por vacina ({mun.ano})
      </h2>
      <p className="mt-1 text-sm text-ink-500">
        Grupo 1 da Lista Brasileira de ICSAP: tuberculoses, tétano, difteria, coqueluche,
        sífilis, febre amarela, sarampo, rubéola, hepatite B, caxumba, malária, meningite e
        febre reumática.
      </p>

      {semCaso ? (
        <p className="mt-4 text-sm text-ink-700">
          Nenhuma internação do grupo 1 registrada neste município em {mun.ano}. Em municípios
          pequenos isso é o resultado esperado — o grupo responde por cerca de 1,4% das
          internações evitáveis no país.
        </p>
      ) : (
        <>
          <div className="mt-4 grid gap-4 sm:grid-cols-3">
            <div>
              <p className="font-mono text-2xl font-semibold text-ink-900">{fmtInt(n ?? 0)}</p>
              <p className="mt-1 text-sm text-ink-600">internações no ano</p>
            </div>
            <div>
              <p className="font-mono text-2xl font-semibold text-ink-900">
                {taxa != null ? fmtDec(taxa, 1) : "—"}
              </p>
              <p className="mt-1 text-sm text-ink-600">por 100 mil habitantes</p>
            </div>
            <div>
              <p className="font-mono text-2xl font-semibold text-ink-900">
                {mediana != null ? fmtDec(mediana, 1) : "—"}
              </p>
              <p className="mt-1 text-sm text-ink-600">
                mediana dos municípios de {mun.uf_sigla}
              </p>
            </div>
          </div>

          {razao != null && (
            <p className="mt-4 text-sm text-ink-700">
              A taxa deste município é{" "}
              <strong>
                {razao >= 1 ? `${fmtDec(razao, 1)}× a mediana` : `${fmtDec(1 / razao, 1)}× menor que a mediana`}
              </strong>{" "}
              da unidade da federação{acima ? "" : ""}.
              {pctDoIcsap != null && (
                <>
                  {" "}O grupo 1 representa {fmtDec(pctDoIcsap, 1)}% de todas as internações
                  evitáveis registradas aqui.
                </>
              )}
            </p>
          )}
        </>
      )}

      <p className="mt-4 border-t border-ink-200 pt-3 text-xs leading-relaxed text-ink-500">
        Contagem por município de <strong>residência</strong>, diagnóstico principal da AIH.
        Número alto não significa, por si, falha de vacinação: internação depende também de
        oferta hospitalar local — este projeto mediu correlação positiva entre leitos e
        internações evitáveis. A associação é municipal (agregada) e não sustenta inferência
        sobre pessoas.
      </p>
    </div>
  );
}
