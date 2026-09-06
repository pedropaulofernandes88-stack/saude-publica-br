/**
 * Exportação: o arquivo sai sabendo o que é, de onde veio e como ser citado.
 *
 * O QUE ESTAVA ERRADO
 * -------------------
 * Havia UMA exportação no site inteiro, no painel, e ela produzia um CSV com
 * oito colunas e nada mais. O recorte estava só no nome do arquivo
 * (`mortalidade_SP_2024_TOTAL_M.csv`) — que é a primeira coisa que alguém
 * renomeia — e a fonte, a licença, a versão da publicação e a citação não
 * estavam em lugar nenhum. Um arquivo assim, dois meses depois, é uma planilha
 * órfã: ninguém sabe de que ano é a base, se o município estava filtrado por
 * população, nem que a licença exige atribuição.
 *
 * Os marts derivados são CC BY 4.0. Atribuição é CONDIÇÃO da licença. Deixá-la
 * fora do arquivo transfere para quem baixa a obrigação de voltar ao site para
 * descobrir uma exigência que ele nem sabe que existe.
 *
 * POR QUE CABEÇALHO COMENTADO, E NÃO ARQUIVO SEPARADO
 * ---------------------------------------------------
 * Um README ao lado se perde no primeiro e-mail encaminhado. `#` no início da
 * linha é a convenção que `pandas.read_csv(comment="#")` e
 * `read.csv2(comment.char="#")` já entendem, e o próprio cabeçalho ensina as
 * duas chamadas — para que a procedência não custe um obstáculo a quem for
 * carregar o arquivo. No Excel as linhas aparecem como texto acima da tabela,
 * que é onde uma citação deve mesmo estar.
 *
 * AUSÊNCIA E ZERO
 * ---------------
 * Célula vazia e `0` significam coisas diferentes e o arquivo diz isso em
 * palavras. É a mesma regra que `lib/carga.ts` aplica na tela: falha e ausência
 * não podem produzir a mesma saída, e ausência não pode virar zero.
 *
 * Este módulo é PURO de propósito — nada de `fetch`, nada de `window`. Quem
 * chama já tem o manifesto e a citação em mãos (`lib/procedencia.ts`), e
 * função pura é o que permite `exportar.test.mts` conferir o arquivo inteiro
 * sem navegador.
 */
import { FONTE_DA_TABELA, fonte } from "./fontes.ts";
import { periodoCoberto, tabelaPublicada, type Manifesto } from "./manifesto.ts";

/** Separador do projeto: ponto-e-vírgula, porque o decimal brasileiro é vírgula. */
export const SEP = ";";

export interface Recorte {
  /** O que este arquivo é, em uma linha. Vira a primeira linha do cabeçalho. */
  titulo: string;
  /**
   * Os filtros aplicados, na ordem em que o leitor os reconheceria.
   * Pares vazios são omitidos: "Sexo: " não informa nada e sugere filtro.
   */
  filtros: [rotulo: string, valor: string | null | undefined][];
  /** Tabelas publicadas de onde os números saíram. */
  tabelas: string[];
  /** A URL exata da consulta — o recorte É a análise. */
  url?: string;
  /** Observação editorial que precisa viajar com estes números. */
  ressalvas?: string[];
}

const PREFIXO = "# ";

function comentar(linhas: string[]): string[] {
  return linhas.map((l) => (l ? PREFIXO + l : "#"));
}

/**
 * A linha de uma tabela no cabeçalho: sistema de origem, período e versão.
 *
 * Nada aqui é digitado. Sistema e órgão vêm de `lib/fontes.ts` (conhecimento
 * editorial, com guarda que exige toda tabela classificada); período, publicação
 * e checksum vêm do manifesto. Uma tabela nova aparece sozinha; uma tabela que
 * mudou de competência muda aqui sem que ninguém lembre de reescrever.
 */
export function linhaDaTabela(nome: string, m: Manifesto | null): string {
  const f = fonte(FONTE_DA_TABELA[nome] ?? "");
  const t = tabelaPublicada(m, nome);
  const partes = [nome];
  // `IBGE (IBGE)` — quando o sistema e o órgão são o mesmo nome, repetir os
  // dois entre parênteses só faz ruído. Acontece com as fontes que não têm um
  // sistema nomeado separadamente do órgão.
  if (f) partes.push(f.sistema === f.orgao ? f.sistema : `${f.sistema} (${f.orgao})`);
  const periodo = periodoCoberto(t);
  if (periodo) partes.push(periodo);
  if (t?.publicada_em) partes.push(`publicação ${t.publicada_em}`);
  if (t?.sha256) partes.push(`sha256 ${t.sha256.slice(0, 12)}…`);
  return partes.join(" · ");
}

/**
 * O cabeçalho de procedência, em linhas já comentadas.
 *
 * `agora` entra por parâmetro em vez de sair de `new Date()` aqui dentro para
 * que o teste possa afirmar o arquivo inteiro, byte a byte. Data implícita é o
 * tipo de coisa que torna uma saída impossível de comparar.
 */
export function cabecalho(
  r: Recorte,
  m: Manifesto | null,
  citacao: string,
  agora: Date,
): string[] {
  const dia = agora.toISOString().slice(0, 10);
  const filtros = r.filtros.filter(([, v]) => v != null && String(v).trim() !== "");

  const linhas: string[] = [`Saúde em Dado — ${r.titulo}`, ""];

  linhas.push("RECORTE");
  if (filtros.length) {
    for (const [rotulo, valor] of filtros) linhas.push(`  ${rotulo}: ${valor}`);
  } else {
    // "Sem filtros" precisa ser DITO. Cabeçalho que simplesmente omite a seção
    // deixa o leitor sem saber se o recorte é o total ou se alguém esqueceu de
    // registrá-lo.
    linhas.push("  sem filtros — o arquivo é o conjunto completo desta consulta");
  }
  linhas.push("");

  linhas.push("FONTE");
  for (const t of r.tabelas) linhas.push(`  ${linhaDaTabela(t, m)}`);
  if (m?.id) linhas.push(`  publicação corrente: ${m.id}${m.commit ? ` · commit ${m.commit}` : ""}`);
  linhas.push("");

  if (r.ressalvas?.length) {
    linhas.push("RESSALVAS");
    for (const obs of r.ressalvas) linhas.push(`  ${obs}`);
    linhas.push("");
  }

  linhas.push("AUSÊNCIA E ZERO");
  linhas.push("  célula vazia = sem dado publicado para este recorte.");
  linhas.push("  0 = medido e igual a zero. Os dois NÃO são a mesma coisa.");
  linhas.push("");

  linhas.push("LICENÇA");
  linhas.push("  CC BY 4.0 — atribuição é condição da licença, não cortesia.");
  linhas.push("  Dados originais em domínio público (DATASUS/MS e IBGE).");
  linhas.push("");

  linhas.push("COMO CITAR");
  linhas.push(`  ${citacao}`);
  if (r.url) linhas.push(`  Consulta: ${r.url}`);
  linhas.push(`  Acesso em: ${dia}.`);
  linhas.push("");

  linhas.push("COMO LER ESTE ARQUIVO");
  linhas.push(`  Python: pandas.read_csv(arquivo, sep="${SEP}", comment="#")`);
  linhas.push(`  R:      read.csv2(arquivo, comment.char="#")`);

  return comentar(linhas);
}

/**
 * Escapa uma célula. `null`/`undefined` viram vazio — NUNCA zero.
 *
 * A regra de aspas é a do RFC 4180 com o separador do projeto: só entra entre
 * aspas o que contém separador, aspas ou quebra de linha, e aspas internas
 * dobram. Sem isso um nome de município com ponto-e-vírgula deslocaria a linha
 * inteira em silêncio.
 */
export function celula(v: unknown): string {
  if (v == null) return "";
  const s = String(v);
  return /[";\n\r]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s;
}

/** O CSV completo: cabeçalho de procedência, colunas e linhas. */
export function paraCsv(
  r: Recorte,
  colunas: string[],
  linhas: unknown[][],
  m: Manifesto | null,
  citacao: string,
  agora: Date,
): string {
  return [
    ...cabecalho(r, m, citacao, agora),
    "",
    colunas.join(SEP),
    ...linhas.map((l) => l.map(celula).join(SEP)),
  ].join("\r\n");
}

/**
 * Nome de arquivo estável: sem acento, sem espaço, com o recorte e a data.
 *
 * O recorte continua no nome — é o que ajuda quem tem vinte arquivos na pasta
 * — mas agora ele é redundante com o cabeçalho, e não o único lugar onde
 * existe.
 */
export function nomeDeArquivo(base: string, filtros: Recorte["filtros"], agora: Date): string {
  const limpo = (s: string) =>
    s.normalize("NFD").replace(/[̀-ͯ]/g, "")
      .replace(/[^A-Za-z0-9]+/g, "-").replace(/^-+|-+$/g, "").toLowerCase();
  const partes = [limpo(base)];
  for (const [, v] of filtros) {
    if (v == null || String(v).trim() === "") continue;
    const p = limpo(String(v));
    if (p) partes.push(p.slice(0, 24));
  }
  partes.push(agora.toISOString().slice(0, 10));
  return `${partes.join("_")}.csv`;
}
