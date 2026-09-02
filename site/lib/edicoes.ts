/**
 * Seleção de edição do boletim, compartilhada por build-alertas e build-feed.
 *
 * POR QUE ISTO EXISTE COMO MÓDULO
 * -------------------------------
 * Os dois scripts abriam `index.json` e exigiam índice não vazio, cada um com
 * sua cópia da checagem e seu `process.exit(1)`. Nenhuma das três guardas tinha
 * teste, pelo mesmo motivo estrutural do guard-rail do boletim: `npm test` roda
 * `node --test "lib/**\/*.test.mts"`, e nada em `scripts/` é alcançável pela
 * suíte.
 *
 * Aqui a decisão fica pura — devolve seleção ou erro — e o `process.exit` fica
 * no script, que é onde ele pertence.
 *
 * A ORDEM DO ÍNDICE É O CONTRATO
 * ------------------------------
 * `index.json` vem do mais NOVO para o mais antigo. É por isso que a edição
 * anterior é `i + 1` e não `i - 1`. Inverter isso não quebraria nada de forma
 * visível: o build continuaria rodando e comparando duas edições reais — só que
 * as erradas, e todo alerta "novo" ou "agravado" da semana sairia invertido.
 *
 * O caso de borda que importa é a edição mais ANTIGA: ela não tem predecessora,
 * e `anterior` é `null`. Sem isso, `index[i + 1].edicao` estouraria; com um
 * `?? index[0]` no lugar do `null`, a edição mais antiga se compararia com a
 * mais nova e reportaria mudança em quase tudo.
 */

export type Edicao = { edicao: string };

export type SelecaoEdicao =
  | { ok: true; atual: string; anterior: string | null; indice: number }
  | { ok: false; erro: string };

/** O índice tem ao menos uma edição? */
export function exigirEdicoes(index: readonly Edicao[]): { ok: true } | { ok: false; erro: string } {
  if (!index.length) return { ok: false, erro: "nenhuma edição publicada" };
  return { ok: true };
}

/**
 * Escolhe a edição a processar e a sua predecessora.
 *
 * Sem `alvo`, usa a mais recente. Com `alvo`, exige que ela exista — pedir uma
 * edição inexistente é erro de quem chamou, não motivo para cair no padrão em
 * silêncio e gerar alertas da semana errada.
 */
export function selecionarEdicao(
  index: readonly Edicao[],
  alvo: string | null = null,
): SelecaoEdicao {
  const naoVazio = exigirEdicoes(index);
  if (!naoVazio.ok) return naoVazio;

  const i = alvo ? index.findIndex((e) => e.edicao === alvo) : 0;
  if (i < 0) return { ok: false, erro: `edição ${alvo} não encontrada` };

  return {
    ok: true,
    indice: i,
    atual: index[i].edicao,
    anterior: index[i + 1]?.edicao ?? null,
  };
}
