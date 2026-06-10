"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { authFetch } from "@/lib/auth";

// ── tipos disponíveis de widget ──────────────────────────────────────────────
const WIDGET_TIPOS = [
  { value: "linha",       label: "📈 Linha",        desc: "Evolução temporal de um indicador" },
  { value: "barra",       label: "📊 Barra",         desc: "Comparação entre categorias"       },
  { value: "mapa",        label: "🗺️ Mapa",          desc: "Distribuição geográfica por UF"    },
  { value: "tabela",      label: "📋 Tabela",        desc: "Dados brutos com filtros"           },
  { value: "metrica",     label: "🔢 Métrica",       desc: "Um número de destaque"              },
  { value: "pizza",       label: "🥧 Pizza",         desc: "Proporção entre categorias"        },
  { value: "dispersao",   label: "🔵 Dispersão",     desc: "Correlação entre dois indicadores" },
  { value: "heatmap",     label: "🌡️ Heatmap",      desc: "Intensidade em matriz temporal"    },
] as const;

// ── fontes de dados disponíveis ──────────────────────────────────────────────
const FONTES = [
  { value: "sia",    label: "SIA/PA — Produção ambulatorial" },
  { value: "sim",    label: "SIM/DO — Mortalidade"           },
  { value: "sih",    label: "SIH/AIH — Internações"         },
  { value: "sinan",  label: "SINAN — Doenças notificáveis"   },
  { value: "cnes",   label: "CNES — Capacidade instalada"    },
] as const;

type WidgetTipo  = typeof WIDGET_TIPOS[number]["value"];
type FonteValor  = typeof FONTES[number]["value"];

interface WidgetDraft {
  id:      number;
  titulo:  string;
  tipo:    WidgetTipo;
  fonte:   FonteValor;
  config:  Record<string, unknown>;
  posicao: { x: number; y: number; w: number; h: number };
}

let _widgetCounter = 0;

function novoWidget(): WidgetDraft {
  return {
    id:      ++_widgetCounter,
    titulo:  "",
    tipo:    "linha",
    fonte:   "sia",
    config:  {},
    posicao: { x: 0, y: 0, w: 6, h: 4 },
  };
}

// ── componente principal ──────────────────────────────────────────────────────
export default function NovoDashboardPage() {
  const router = useRouter();

  const [titulo,    setTitulo]    = useState("");
  const [descricao, setDescricao] = useState("");
  const [publico,   setPublico]   = useState(false);
  const [widgets,   setWidgets]   = useState<WidgetDraft[]>([novoWidget()]);
  const [loading,   setLoading]   = useState(false);
  const [erro,      setErro]      = useState<string | null>(null);

  // ── helpers de widget ────────────────────────────────────────────────────
  function adicionarWidget() {
    setWidgets(ws => [...ws, novoWidget()]);
  }

  function removerWidget(id: number) {
    setWidgets(ws => ws.filter(w => w.id !== id));
  }

  function atualizarWidget(id: number, patch: Partial<WidgetDraft>) {
    setWidgets(ws => ws.map(w => w.id === id ? { ...w, ...patch } : w));
  }

  function atualizarPosicao(id: number, campo: keyof WidgetDraft["posicao"], valor: number) {
    setWidgets(ws => ws.map(w =>
      w.id === id ? { ...w, posicao: { ...w.posicao, [campo]: valor } } : w
    ));
  }

  // ── submit ───────────────────────────────────────────────────────────────
  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setErro(null);

    if (!titulo.trim()) { setErro("Título é obrigatório"); return; }
    if (widgets.some(w => !w.titulo.trim())) {
      setErro("Todos os widgets precisam de um título"); return;
    }

    setLoading(true);
    try {
      const body = {
        titulo:   titulo.trim(),
        descricao: descricao.trim() || null,
        publico,
        widgets: widgets.map(({ id: _id, ...w }) => w),   // remove draft id
      };

      const data = await authFetch<{ slug: string }>("/dashboards", {
        method: "POST",
        body: JSON.stringify(body),
      });

      router.push(`/portal/d/${data.slug}`);
    } catch (err: unknown) {
      setErro(err instanceof Error ? err.message : "Erro ao criar dashboard");
    } finally {
      setLoading(false);
    }
  }

  // ── render ───────────────────────────────────────────────────────────────
  return (
    <main className="min-h-screen bg-gray-50 py-10 px-4">
      <div className="max-w-4xl mx-auto">

        {/* cabeçalho */}
        <div className="mb-8">
          <button
            onClick={() => router.back()}
            className="text-sm text-blue-600 hover:underline mb-2 flex items-center gap-1"
          >
            ← Voltar
          </button>
          <h1 className="text-3xl font-bold text-gray-900">Novo dashboard</h1>
          <p className="text-gray-500 mt-1">
            Combine indicadores do SUS em um painel personalizado.
          </p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-8">

          {/* ── seção: informações gerais ── */}
          <section className="bg-white rounded-2xl shadow-sm border border-gray-100 p-6 space-y-4">
            <h2 className="text-lg font-semibold text-gray-800">Informações gerais</h2>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Título <span className="text-red-500">*</span>
              </label>
              <input
                type="text"
                value={titulo}
                onChange={e => setTitulo(e.target.value)}
                placeholder="Ex.: Mortalidade infantil por estado 2019-2024"
                className="w-full border border-gray-300 rounded-lg px-4 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                maxLength={120}
                required
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Descrição
              </label>
              <textarea
                value={descricao}
                onChange={e => setDescricao(e.target.value)}
                placeholder="Descreva o objetivo deste dashboard (opcional)"
                rows={3}
                maxLength={500}
                className="w-full border border-gray-300 rounded-lg px-4 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 resize-none"
              />
            </div>

            <div className="flex items-center gap-3">
              <button
                type="button"
                role="switch"
                aria-checked={publico}
                onClick={() => setPublico(p => !p)}
                className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
                  publico ? "bg-blue-600" : "bg-gray-300"
                }`}
              >
                <span className={`inline-block h-4 w-4 transform rounded-full bg-white shadow transition-transform ${
                  publico ? "translate-x-6" : "translate-x-1"
                }`} />
              </button>
              <span className="text-sm text-gray-700">
                {publico
                  ? "🌐 Público — visível para todos"
                  : "🔒 Privado — somente você"}
              </span>
            </div>
          </section>

          {/* ── seção: widgets ── */}
          <section className="space-y-4">
            <div className="flex items-center justify-between">
              <h2 className="text-lg font-semibold text-gray-800">
                Widgets ({widgets.length})
              </h2>
              <button
                type="button"
                onClick={adicionarWidget}
                className="text-sm bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 transition-colors"
              >
                + Adicionar widget
              </button>
            </div>

            {widgets.map((widget, idx) => (
              <WidgetBuilder
                key={widget.id}
                widget={widget}
                index={idx}
                onChange={patch => atualizarWidget(widget.id, patch)}
                onPosicao={(campo, valor) => atualizarPosicao(widget.id, campo, valor)}
                onRemover={() => removerWidget(widget.id)}
                canRemove={widgets.length > 1}
              />
            ))}
          </section>

          {/* ── erro + submit ── */}
          {erro && (
            <div className="bg-red-50 border border-red-200 rounded-lg px-4 py-3 text-sm text-red-700">
              ⚠️ {erro}
            </div>
          )}

          <div className="flex gap-4 justify-end">
            <button
              type="button"
              onClick={() => router.back()}
              className="px-6 py-2.5 rounded-lg border border-gray-300 text-gray-700 hover:bg-gray-50 text-sm font-medium transition-colors"
            >
              Cancelar
            </button>
            <button
              type="submit"
              disabled={loading}
              className="px-6 py-2.5 rounded-lg bg-blue-600 text-white text-sm font-medium hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              {loading ? "Criando…" : "Criar dashboard"}
            </button>
          </div>
        </form>
      </div>
    </main>
  );
}

// ── sub-componente: builder de um widget ─────────────────────────────────────
interface WidgetBuilderProps {
  widget:    WidgetDraft;
  index:     number;
  onChange:  (patch: Partial<WidgetDraft>) => void;
  onPosicao: (campo: keyof WidgetDraft["posicao"], valor: number) => void;
  onRemover: () => void;
  canRemove: boolean;
}

function WidgetBuilder({ widget, index, onChange, onPosicao, onRemover, canRemove }: WidgetBuilderProps) {
  const tipoInfo = WIDGET_TIPOS.find(t => t.value === widget.tipo)!;

  return (
    <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-6 space-y-4">
      {/* header do widget */}
      <div className="flex items-center justify-between">
        <span className="text-xs font-semibold text-blue-600 bg-blue-50 px-2 py-0.5 rounded-full">
          Widget {index + 1}
        </span>
        {canRemove && (
          <button
            type="button"
            onClick={onRemover}
            className="text-xs text-red-500 hover:text-red-700 hover:underline"
          >
            Remover
          </button>
        )}
      </div>

      {/* título do widget */}
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">
          Título do widget <span className="text-red-500">*</span>
        </label>
        <input
          type="text"
          value={widget.titulo}
          onChange={e => onChange({ titulo: e.target.value })}
          placeholder="Ex.: Taxa de mortalidade infantil por UF"
          className="w-full border border-gray-300 rounded-lg px-4 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          maxLength={100}
          required
        />
      </div>

      {/* tipo + fonte */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Tipo de visualização</label>
          <select
            value={widget.tipo}
            onChange={e => onChange({ tipo: e.target.value as WidgetTipo })}
            className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 bg-white"
          >
            {WIDGET_TIPOS.map(t => (
              <option key={t.value} value={t.value}>{t.label}</option>
            ))}
          </select>
          <p className="text-xs text-gray-400 mt-1">{tipoInfo.desc}</p>
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Fonte de dados</label>
          <select
            value={widget.fonte}
            onChange={e => onChange({ fonte: e.target.value as FonteValor })}
            className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 bg-white"
          >
            {FONTES.map(f => (
              <option key={f.value} value={f.value}>{f.label}</option>
            ))}
          </select>
        </div>
      </div>

      {/* posição na grade (12 colunas) */}
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-2">
          Posição na grade <span className="text-gray-400 font-normal">(12 colunas)</span>
        </label>
        <div className="grid grid-cols-4 gap-3">
          {(["x","y","w","h"] as const).map(campo => (
            <div key={campo}>
              <label className="block text-xs text-gray-500 mb-1 uppercase tracking-wide">
                {campo === "x" ? "Col. início" : campo === "y" ? "Linha início" : campo === "w" ? "Largura" : "Altura"}
              </label>
              <input
                type="number"
                min={campo === "w" ? 1 : 0}
                max={campo === "x" ? 11 : campo === "w" ? 12 : campo === "h" ? 12 : 20}
                value={widget.posicao[campo]}
                onChange={e => onPosicao(campo, Number(e.target.value))}
                className="w-full border border-gray-300 rounded-lg px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 text-center"
              />
            </div>
          ))}
        </div>
        <p className="text-xs text-gray-400 mt-1.5">
          Largura 6 = 50% da tela · Largura 12 = 100% · Altura típica = 4
        </p>
      </div>

      {/* preview da largura */}
      <div className="bg-gray-50 rounded-lg p-3">
        <div className="text-xs text-gray-500 mb-1.5">Preview de largura</div>
        <div className="h-6 bg-gray-200 rounded-md w-full relative overflow-hidden">
          <div
            className="h-full bg-blue-400 rounded-md transition-all"
            style={{ width: `${Math.round((widget.posicao.w / 12) * 100)}%` }}
          />
        </div>
        <div className="text-xs text-gray-400 mt-1">
          {widget.posicao.w}/12 colunas = {Math.round((widget.posicao.w / 12) * 100)}% da largura
        </div>
      </div>
    </div>
  );
}
