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
        //   500     5,31:1  texto secundário (menor tom seguro)
        //   600+    6,43:1+ texto
        //
        // O 500 estava em #677791 = 4,54:1, passando por 0,04 de margem: qualquer
        // ajuste de cor o derrubava. Só ele foi escurecido — de 600 para cima a
        // rampa já tinha espaçamento bom (6,4 / 8,5 / 10,1 / 15,5).
        ink: {
          50: "#f6f7f9",
          100: "#eceef2",
          200: "#d5dae2",
          300: "#b1bac9",
          400: "#8694ab",
          500: "#5e6c84",
          600: "#525f78",
          700: "#434d62",
          800: "#3a4253",
          900: "#1e2433",
          950: "#14181f",
        },
        accent: {
          50: "#eefdf5",
          100: "#d6fae6",
          200: "#b0f3d1",
          300: "#7ce7b6",
          400: "#46d295",
          500: "#1fb87b",
          600: "#129563",
          700: "#107752",
          800: "#115e43",
          900: "#0f4d38",
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
