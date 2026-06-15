import type { MetadataRoute } from "next";
import { ARTIGOS } from "@/content/artigos";

export const dynamic = "force-static";

export default function sitemap(): MetadataRoute.Sitemap {
  const base = "https://saudeemdado.com";
  const agora = new Date();
  const fixas = ["", "/painel/", "/dengue/", "/internacoes/", "/nascimentos/", "/mapa/", "/tendencias/", "/artigos/", "/dados/", "/metodologia/", "/sobre/"].map(
    (p) => ({
      url: `${base}${p}`,
      lastModified: agora,
      changeFrequency: (p === "" || p === "/painel/" ? "weekly" : "monthly") as "weekly" | "monthly",
      priority: p === "" ? 1 : p === "/painel/" ? 0.9 : 0.7,
    }),
  );
  const artigos = ARTIGOS.map((a) => ({
    url: `${base}/artigos/${a.slug}/`,
    lastModified: new Date(`${a.data}T00:00:00`),
    changeFrequency: "yearly" as const,
    priority: 0.6,
  }));
  return [...fixas, ...artigos];
}
