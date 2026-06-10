import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: {
          50: "#f6f7f9",
          100: "#eceef2",
          200: "#d5dae2",
          300: "#b1bac9",
          400: "#8694ab",
          500: "#677791",
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
    },
  },
  plugins: [],
};

export default config;
