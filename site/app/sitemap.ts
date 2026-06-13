import type { MetadataRoute } from "next";

export const dynamic = "force-static";

export default function sitemap(): MetadataRoute.Sitemap {
  const base = "https://saudeemdado.com";
  const agora = new Date();
  return ["", "/painel/", "/dengue/", "/internacoes/", "/mapa/", "/tendencias/", "/dados/", "/metodologia/", "/sobre/"].map(
    (p) => ({
      url: `${base}${p}`,
      lastModified: agora,
      changeFrequency: p === "" || p === "/painel/" ? "weekly" : "monthly",
      priority: p === "" ? 1 : p === "/painel/" ? 0.9 : 0.7,
    }),
  );
}
