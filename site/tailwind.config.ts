import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        // Escala neutra. Contraste sobre branco (WCAG AA pede 4,5:1 para texto
        // normal e 3:1 para elemento de interface):
        //
        //   50–200  fundo
        //   300     1,96:1  borda e decoração — NUNCA texto
        //   400     3,07:1  ícone e divisor — NUNCA texto
        // Neutro QUENTE — direção "papel científico". O 50 é a superfície do
        // body; os cards ficam brancos sobre ele. Contraste medido sobre o papel
        // (#FAF7F2), não sobre branco puro:
        //
        //   50–200            fundo
        //   300     1,86:1    borda — NUNCA texto, NUNCA elemento de interface
        //   400     3,06:1    ícone e divisor (>=3:1 p/ UI) — NUNCA texto
        //   500     5,36:1    texto secundário (menor tom seguro)
        //   600+    7,2:1+    texto
        //
        // A rampa fria anterior tinha o 500 em 4,54:1, com 0,04 de margem. Esta
        // mantém o mesmo papel por passo, com o viés quente e a folga preservada.
        ink: {
          50: "#faf7f2",
          100: "#f1ede5",
          200: "#e0d9cd",
          300: "#c0b7a8",
          400: "#978d7e",
          500: "#6e6559",
          600: "#5a5248",
          700: "#46403a",
          800: "#35302b",
          900: "#23201c",
          950: "#17150f",
        },
        // Verde-petróleo, mais fundo que o verde médio anterior. O 700 é o tom
        // de link e botão: 7,13:1 sobre o papel.
        accent: {
          50: "#edf6f2",
          100: "#d4eae0",
          200: "#a9d6c3",
          300: "#6fbba0",
          400: "#3d9e7e",
          500: "#1b8163",
          600: "#0f6d53",
          700: "#0b5f4c",
          800: "#094b3d",
          900: "#073b31",
        },
      },
      fontFamily: {
        sans: ["var(--font-inter)", "system-ui", "sans-serif"],
        serif: ["var(--font-serif)", "Georgia", "serif"],
      },
      // Escala tipográfica explícita, com entrelinha por passo.
      //
      // Antes eram os defaults do Tailwind aplicados ad hoc: 108 usos de
      // `text-xs` (12px) e 147 de `text-sm` — /internacoes/ tinha 24 elementos
      // em 12px, tamanho de nota de rodapé carregando informação de leitura.
      // Aqui o menor passo sobe para 13px e a entrelinha cresce nos passos de
      // texto corrido; os passos de título ficam mais fechados. Redefinir o
      // token levanta todos os usos existentes sem renomear classe em 11
      // páginas.
      fontSize: {
        // texto: entrelinha generosa
        xs: ["0.8125rem", { lineHeight: "1.5" }],     // 13px — mínimo legível
        sm: ["0.9063rem", { lineHeight: "1.6" }],     // 14,5px
        base: ["1rem", { lineHeight: "1.65" }],       // 16px
        lg: ["1.125rem", { lineHeight: "1.6" }],      // 18px
        // título: entrelinha fechada
        xl: ["1.25rem", { lineHeight: "1.35" }],
        "2xl": ["1.5rem", { lineHeight: "1.3" }],
        "3xl": ["1.875rem", { lineHeight: "1.22" }],
        "4xl": ["2.25rem", { lineHeight: "1.15" }],
        "5xl": ["3rem", { lineHeight: "1.08" }],
      },
    },
  },
  plugins: [],
};

export default config;
