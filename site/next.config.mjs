/** @type {import('next').NextConfig} */
const nextConfig = {
  // Export 100% estático: hospedagem gratuita (Vercel, Cloudflare Pages, GitHub Pages)
  output: "export",
  trailingSlash: true,
  images: { unoptimized: true },
};

export default nextConfig;
