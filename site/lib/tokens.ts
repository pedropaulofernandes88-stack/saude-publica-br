/**
 * Tokens de design consumidos por JavaScript.
 *
 * O Recharts recebe cor por prop, não por classe CSS, então os gráficos vinham
 * com hex cravado em seis arquivos — e quando a escala `ink` mudou no
 * tailwind.config, os eixos ficaram com o valor antigo. Estes constantes são a
 * ponte: quem desenha gráfico importa daqui, e a paleta passa a ter um lugar
 * só para mudar.
 *
 * Mantenha em sincronia com `tailwind.config.ts`.
 */

/** Escala neutra quente — ver o comentário de contraste no tailwind.config. */
export const INK = {
  100: "#f1ede5",
  200: "#e0d9cd",
  300: "#c0b7a8",
  400: "#978d7e",
  500: "#6e6559",
  600: "#5a5248",
  800: "#35302b",
} as const;

export const ACCENT = {
  400: "#3d9e7e",
  700: "#0b5f4c",
} as const;

/** Superfície do body. Os cards ficam brancos sobre ela. */
export const PAPEL = "#faf7f2";

/** Vermelho de série observada / alerta. Não está na escala da marca. */
export const ALERTA = "#a32a22";

// ── Papéis dentro de um gráfico ───────────────────────────────────────────────

/** Cor do texto dos eixos: é texto pequeno sobre branco, precisa ser legível. */
export const EIXO = INK[500];

/** Linhas de grade — elemento decorativo, fica no tom mais claro. */
export const GRADE = INK[100];

/** Rótulo de categoria dentro do gráfico (mais forte que o eixo). */
export const CATEGORIA = INK[800];

/** Linha de referência (esperado, mediana, baseline): presente mas discreta. */
export const REFERENCIA = INK[400];

/** Série principal. */
export const SERIE = ACCENT[700];

/** Estilo padrão do tick de eixo, usado por todos os gráficos. */
export const TICK = { fontSize: 12, fill: EIXO } as const;

/** Estilo padrão do tooltip. */
export const TOOLTIP = { borderRadius: 8, borderColor: INK[100], fontSize: 13 } as const;

/**
 * Cor por região — categórica, não sequencial: a ordem é identidade, nunca
 * posto. A sequência abaixo foi validada com o validador de paleta contra a
 * superfície de papel e passa nos cinco testes:
 *
 *   separação mínima entre vizinhos — ΔE 17,8 (protanopia), 16,3 (tritanopia),
 *   25,6 (visão normal); croma acima do piso; contraste >= 3:1
 *
 * As posições importam: hues próximos NÃO podem ficar adjacentes. Uma versão
 * anterior tinha azul-aço ao lado de ameixa e dava ΔE 1,5 em protanopia —
 * indistinguíveis. Não reordene sem rodar o validador.
 */
export const CORES_REGIAO: Record<string, string> = {
  Norte: "#0090a6",
  Nordeste: "#c9601f",
  Sudeste: "#2158a8",
  Sul: "#6e9b12",
  "Centro-Oeste": "#9b3d93",
};
