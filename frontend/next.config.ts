import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Required for Docker multi-stage build (copies only what's needed to run)
  output: "standalone",

  // Transpile deck.gl ESM packages
  transpilePackages: [
    "@deck.gl/core",
    "@deck.gl/layers",
    "@deck.gl/react",
    "@luma.gl/core",
    "@luma.gl/webgl",
  ],

  env: {
    NEXT_PUBLIC_API_BASE_URL:
      process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000",
    NEXT_PUBLIC_MAPTILER_KEY:
      process.env.NEXT_PUBLIC_MAPTILER_KEY ?? "",
  },

  // Configurações de imagem se precisarmos de mapas estáticos
  images: {
    remotePatterns: [
      {
        protocol: "https",
        hostname: "api.maptiler.com",
      },
    ],
  },
};

export default nextConfig;
