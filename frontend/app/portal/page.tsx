/**
 * frontend/app/portal/page.tsx
 * Landing page do portal público — lista dashboards públicos + CTA de criação.
 */

"use client";

import { useEffect, useState } from "react";
import Link from "next/link";

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

interface DashboardListItem {
  id: string;
  slug: string;
  titulo: string;
  descricao: string | null;
  autor_nome: string;
  publico: boolean;
  total_widgets: number;
  total_favoritos: number;
  atualizado_em: string;
}

function DashboardCard({ d }: { d: DashboardListItem }) {
  const updatedAt = new Date(d.atualizado_em).toLocaleDateString("pt-BR", {
    day: "2-digit", month: "short", year: "numeric",
  });

  return (
    <Link href={`/portal/d/${d.slug}`} className="block group">
      <div className="bg-white border border-gray-200 rounded-xl p-5 hover:shadow-md hover:border-blue-300 transition-all">
        <div className="flex items-start justify-between gap-3 mb-2">
          <h3 className="font-semibold text-gray-900 group-hover:text-blue-700 text-sm leading-snug">
            {d.titulo}
          </h3>
          {d.publico && (
            <span className="shrink-0 text-xs bg-green-100 text-green-700 px-2 py-0.5 rounded-full font-medium">
              Público
            </span>
          )}
        </div>
        {d.descricao && (
          <p className="text-gray-500 text-xs line-clamp-2 mb-3">{d.descricao}</p>
        )}
        <div className="flex items-center justify-between text-xs text-gray-400">
          <span>por {d.autor_nome}</span>
          <span className="flex items-center gap-3">
            <span title="Widgets">⬛ {d.total_widgets}</span>
            <span title="Favoritos">⭐ {d.total_favoritos}</span>
            <span>{updatedAt}</span>
          </span>
        </div>
      </div>
    </Link>
  );
}

export default function PortalPage() {
  const [dashboards, setDashboards] = useState<DashboardListItem[]>([]);
  const [loading,    setLoading]    = useState(true);
  const [erro,       setErro]       = useState<string | null>(null);
  const [busca,      setBusca]      = useState("");

  useEffect(() => {
    async function fetch_data() {
      try {
        const params = new URLSearchParams({ publico: "true", limite: "50" });
        if (busca) params.set("busca", busca);
        const res = await fetch(`${API_BASE}/dashboards?${params}`);
        if (!res.ok) throw new Error("Erro ao carregar dashboards");
        setDashboards(await res.json());
      } catch (e: unknown) {
        setErro(e instanceof Error ? e.message : "Erro");
      } finally {
        setLoading(false);
      }
    }
    fetch_data();
  }, [busca]);

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Hero */}
      <div className="bg-gradient-to-br from-blue-900 to-teal-700 text-white py-16 px-4">
        <div className="max-w-4xl mx-auto text-center">
          <div className="inline-flex items-center gap-2 bg-white/10 rounded-full px-4 py-1.5 text-sm mb-4">
            <span>🩺</span>
            <span>Saúde Pública BR</span>
          </div>
          <h1 className="text-4xl font-bold mb-3">
            O Our World in Data do SUS
          </h1>
          <p className="text-blue-200 text-lg mb-6 max-w-2xl mx-auto">
            27 estados · 480M registros · 2019–2024 · Dados abertos do DataSUS
          </p>
          <div className="flex flex-wrap gap-3 justify-center">
            <Link
              href="/registro"
              className="bg-white text-blue-900 font-semibold px-6 py-2.5 rounded-lg hover:bg-blue-50 transition-colors text-sm"
            >
              Criar conta gratuita
            </Link>
            <Link
              href="/docs"
              className="border border-white/40 text-white px-6 py-2.5 rounded-lg hover:bg-white/10 transition-colors text-sm"
            >
              Ver documentação API →
            </Link>
          </div>
        </div>
      </div>

      {/* Stats bar */}
      <div className="bg-white border-b">
        <div className="max-w-4xl mx-auto px-4 py-4 grid grid-cols-2 md:grid-cols-4 gap-4">
          {[
            { valor: "27", label: "Estados" },
            { valor: "5", label: "Sistemas DataSUS" },
            { valor: "480M", label: "Registros" },
            { valor: "2019–2024", label: "Período" },
          ].map((s) => (
            <div key={s.label} className="text-center">
              <div className="text-2xl font-bold text-blue-700">{s.valor}</div>
              <div className="text-xs text-gray-500">{s.label}</div>
            </div>
          ))}
        </div>
      </div>

      {/* Dashboards */}
      <div className="max-w-4xl mx-auto px-4 py-10">
        <div className="flex items-center justify-between mb-6 gap-4 flex-wrap">
          <h2 className="text-xl font-bold text-gray-900">Dashboards Públicos</h2>
          <div className="flex items-center gap-3">
            <input
              type="search"
              value={busca}
              onChange={(e) => setBusca(e.target.value)}
              placeholder="Buscar dashboard…"
              className="border border-gray-300 rounded-lg px-3 py-1.5 text-sm w-48 focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
            <Link
              href="/login?redirect=/portal/dashboards/new"
              className="bg-blue-600 text-white text-sm font-semibold px-4 py-1.5 rounded-lg hover:bg-blue-700 transition-colors whitespace-nowrap"
            >
              + Novo dashboard
            </Link>
          </div>
        </div>

        {loading && (
          <div className="text-center text-gray-400 py-16">Carregando…</div>
        )}
        {erro && (
          <div className="text-center text-red-500 py-8">{erro}</div>
        )}
        {!loading && !erro && dashboards.length === 0 && (
          <div className="text-center text-gray-400 py-16">
            Nenhum dashboard público encontrado.
          </div>
        )}

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {dashboards.map((d) => (
            <DashboardCard key={d.id} d={d} />
          ))}
        </div>
      </div>
    </div>
  );
}
