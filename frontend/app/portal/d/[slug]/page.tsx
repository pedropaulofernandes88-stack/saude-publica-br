/**
 * frontend/app/portal/d/[slug]/page.tsx
 * Visualizador de dashboard público ou privado por slug.
 */

"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

interface Widget {
  id: string;
  tipo: string;
  titulo: string;
  posicao: { x: number; y: number; w: number; h: number };
  fonte: string;
  filtros: Record<string, unknown>;
  config: Record<string, unknown>;
  ordem: number;
}

interface Dashboard {
  id: string;
  slug: string;
  titulo: string;
  descricao: string | null;
  autor_nome: string;
  publico: boolean;
  criado_em: string;
  atualizado_em: string;
  widgets: Widget[];
}

function WidgetCard({ widget }: { widget: Widget }) {
  const icons: Record<string, string> = {
    kpi_card: "📊",
    line_chart: "📈",
    bar_chart: "📊",
    area_chart: "📉",
    pie_chart: "🥧",
    map_choropleth: "🗺️",
    data_table: "📋",
    ranking_table: "🏆",
  };
  const icon = icons[widget.tipo] ?? "⬛";

  // Tamanho baseado na grade 12 colunas (w=6 → 50%, w=12 → 100%)
  const widthPct = Math.round((widget.posicao.w / 12) * 100);

  return (
    <div
      className="bg-white border border-gray-200 rounded-xl p-4 shadow-sm"
      style={{ width: `${widthPct}%`, minWidth: "280px" }}
    >
      <div className="flex items-center gap-2 mb-3">
        <span className="text-lg">{icon}</span>
        <h3 className="font-semibold text-gray-800 text-sm">{widget.titulo}</h3>
        <span className="ml-auto text-xs text-gray-400 bg-gray-100 px-2 py-0.5 rounded">
          {widget.tipo.replace("_", " ")}
        </span>
      </div>
      <div className="bg-gray-50 rounded-lg h-32 flex items-center justify-center">
        <p className="text-gray-400 text-xs text-center">
          Fonte: <strong>{widget.fonte}</strong>
          <br />
          {Object.keys(widget.filtros).length > 0 && (
            <span>Filtros: {JSON.stringify(widget.filtros)}</span>
          )}
        </p>
      </div>
    </div>
  );
}

export default function DashboardViewPage() {
  const { slug }                  = useParams<{ slug: string }>();
  const [dashboard, setDashboard] = useState<Dashboard | null>(null);
  const [loading,   setLoading]   = useState(true);
  const [erro,      setErro]      = useState<string | null>(null);

  useEffect(() => {
    async function fetchDash() {
      try {
        const res = await fetch(`${API_BASE}/dashboards/slug/${slug}`);
        if (!res.ok) {
          throw new Error(res.status === 404 ? "Dashboard não encontrado" : "Erro ao carregar");
        }
        setDashboard(await res.json());
      } catch (e: unknown) {
        setErro(e instanceof Error ? e.message : "Erro");
      } finally {
        setLoading(false);
      }
    }
    fetchDash();
  }, [slug]);

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center text-gray-400">
        Carregando dashboard…
      </div>
    );
  }
  if (erro || !dashboard) {
    return (
      <div className="min-h-screen flex flex-col items-center justify-center gap-4">
        <p className="text-red-500">{erro ?? "Dashboard não encontrado"}</p>
        <Link href="/portal" className="text-blue-600 hover:underline text-sm">
          ← Voltar ao portal
        </Link>
      </div>
    );
  }

  const updatedAt = new Date(dashboard.atualizado_em).toLocaleDateString("pt-BR", {
    day: "2-digit", month: "long", year: "numeric",
  });

  // Ordenar widgets pela posição (y ascendente, x ascendente)
  const widgetsSorted = [...dashboard.widgets].sort(
    (a, b) => a.posicao.y - b.posicao.y || a.posicao.x - b.posicao.x
  );

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <div className="bg-white border-b">
        <div className="max-w-6xl mx-auto px-4 py-4">
          <div className="flex items-center gap-2 text-xs text-gray-400 mb-2">
            <Link href="/portal" className="hover:text-blue-600">Portal</Link>
            <span>/</span>
            <span className="text-gray-700 font-medium">{dashboard.titulo}</span>
          </div>
          <div className="flex items-start justify-between gap-4 flex-wrap">
            <div>
              <h1 className="text-xl font-bold text-gray-900">{dashboard.titulo}</h1>
              {dashboard.descricao && (
                <p className="text-gray-500 text-sm mt-0.5">{dashboard.descricao}</p>
              )}
              <p className="text-xs text-gray-400 mt-1">
                por <strong>{dashboard.autor_nome}</strong> · atualizado em {updatedAt}
                {dashboard.publico && (
                  <span className="ml-2 bg-green-100 text-green-700 px-2 py-0.5 rounded-full">
                    Público
                  </span>
                )}
              </p>
            </div>
            <div className="flex items-center gap-2 flex-wrap">
              <ExportButton dashboardId={dashboard.id} slug={slug} />
              <Link
                href="/login"
                className="border border-blue-300 text-blue-700 text-xs font-medium px-3 py-1.5 rounded-lg hover:bg-blue-50"
              >
                ⭐ Favoritar
              </Link>
            </div>
          </div>
        </div>
      </div>

      {/* Widgets */}
      <div className="max-w-6xl mx-auto px-4 py-6">
        {widgetsSorted.length === 0 ? (
          <div className="text-center text-gray-400 py-16">
            Este dashboard ainda não tem widgets.
          </div>
        ) : (
          <div className="flex flex-wrap gap-4">
            {widgetsSorted.map((w) => (
              <WidgetCard key={w.id} widget={w} />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

// ─── Botão de Exportação inline ──────────────────────────────────────────────

function ExportButton({ dashboardId, slug }: { dashboardId: string; slug: string }) {
  const [open,    setOpen]    = useState(false);
  const [loading, setLoading] = useState(false);

  async function exportar(formato: "csv" | "excel" | "json") {
    setLoading(true);
    setOpen(false);
    try {
      // Usa a API de exportação para mortalidade como exemplo
      const r1 = await fetch(`${API_BASE}/exports`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          endpoint: "nacional/mortalidade",
          formato,
          filtros: {},
        }),
      });
      const { export_id } = await r1.json();
      // Redirect para download
      window.location.href = `${API_BASE}/exports/${export_id}/download`;
    } catch {
      alert("Erro ao iniciar exportação");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="relative">
      <button
        onClick={() => setOpen((o) => !o)}
        disabled={loading}
        className="border border-gray-300 text-gray-700 text-xs font-medium px-3 py-1.5 rounded-lg hover:bg-gray-50 flex items-center gap-1"
      >
        {loading ? "⏳" : "⬇️"} Exportar dados
      </button>
      {open && (
        <div className="absolute right-0 top-full mt-1 bg-white border rounded-lg shadow-lg z-10 w-36 overflow-hidden">
          {(["csv", "excel", "json"] as const).map((fmt) => (
            <button
              key={fmt}
              onClick={() => exportar(fmt)}
              className="w-full text-left px-4 py-2 text-xs hover:bg-gray-50 text-gray-700"
            >
              {fmt.toUpperCase()}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
