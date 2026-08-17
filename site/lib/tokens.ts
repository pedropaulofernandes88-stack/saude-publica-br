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

/** Escala neutra — ver o comentário de contraste no tailwind.config. */
export const INK = {
  100: "#eceef2",
  200: "#d5dae2",
  300: "#b1bac9",
  400: "#8694ab",
  500: "#5e6c84",
  600: "#525f78",
  800: "#3a4253",
} as const;

export const ACCENT = {
  400: "#46d295",
  700: "#107752",
} as const;

/** Vermelho de série observada / alerta. Não está na escala da marca. */
export const ALERTA = "#b4232a";

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

/** Cor por região do país — categórica, não sequencial. */
export const CORES_REGIAO: Record<string, string> = {
  Norte: "#1f9e8a",
  Nordeste: "#e07a1f",
  "Centro-Oeste": "#a05fb4",
  Sudeste: "#2f6fb0",
  Sul: "#107752",
};
