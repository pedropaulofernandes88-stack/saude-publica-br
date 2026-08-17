"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useRef, useState } from "react";

type Item = { href: string; label: string; curto: string };
type Grupo = { label: string; curto: string; group: Item[] };
type Entry = Item | Grupo;

const NAV: Entry[] = [
  { href: "/", label: "Início", curto: "Início" },
  { href: "/painel/", label: "Mortalidade", curto: "Mortal." },
  { href: "/dengue/", label: "Dengue", curto: "Dengue" },
  {
    label: "Assistência", curto: "Assist.",
    group: [
      { href: "/internacoes/", label: "Internações por município", curto: "Intern." },
      { href: "/hospitalar/", label: "Visão hospitalar", curto: "Hospital" },
      { href: "/atencao-basica/", label: "Atenção primária", curto: "APS" },
    ],
  },
  {
    label: "Explorar", curto: "Explorar",
    group: [
      { href: "/mapa/", label: "Mapa", curto: "Mapa" },
      { href: "/tendencias/", label: "Tendências", curto: "Tend." },
      { href: "/nascimentos/", label: "Nascimentos", curto: "Nasc." },
    ],
  },
  {
    label: "Análises", curto: "Análises",
    group: [
      { href: "/artigos/", label: "Artigos", curto: "Artigos" },
      { href: "/boletim-semanal/", label: "Boletim semanal", curto: "Boletim" },
    ],
  },
  {
    label: "Dados", curto: "Dados",
    group: [
      { href: "/dados/", label: "Dados & API", curto: "API" },
      { href: "/metodologia/", label: "Metodologia", curto: "Método" },
    ],
  },
  { href: "/sobre/", label: "Sobre", curto: "Sobre" },
];

function isGroup(e: Entry): e is Grupo {
  return "group" in e;
}

/** Fecha ao clicar fora e ao pressionar Escape; devolve o foco a quem abriu. */
function useFecharAoSair(
  aberto: boolean,
  fechar: () => void,
  refs: React.RefObject<HTMLElement | null>[],
) {
  useEffect(() => {
    if (!aberto) return;
    const foraDeTudo = (alvo: Node) => !refs.some((r) => r.current?.contains(alvo));
    const onClique = (e: MouseEvent) => {
      if (e.target instanceof Node && foraDeTudo(e.target)) fechar();
    };
    const onTecla = (e: KeyboardEvent) => {
      if (e.key === "Escape") fechar();
    };
    document.addEventListener("mousedown", onClique);
    document.addEventListener("keydown", onTecla);
    return () => {
      document.removeEventListener("mousedown", onClique);
      document.removeEventListener("keydown", onTecla);
    };
  }, [aberto, fechar, refs]);
}

export function Nav() {
  const pathname = usePathname();
  const isActive = (href: string) => (href === "/" ? pathname === "/" : pathname?.startsWith(href));

  // Um grupo aberto por vez, por rótulo. Abre por clique — não por hover: hover
  // não existe em toque, e tablet cai no breakpoint de desktop.
  const [grupoAberto, setGrupoAberto] = useState<string | null>(null);
  const [menuAberto, setMenuAberto] = useState(false);

  const barraRef = useRef<HTMLDivElement | null>(null);
  const painelRef = useRef<HTMLDivElement | null>(null);

  useFecharAoSair(grupoAberto !== null, () => setGrupoAberto(null), [barraRef]);
  useFecharAoSair(menuAberto, () => setMenuAberto(false), [barraRef, painelRef]);

  // Navegar fecha tudo — sem isso o painel fica aberto sobre a página nova.
  useEffect(() => {
    setMenuAberto(false);
    setGrupoAberto(null);
  }, [pathname]);

  const itemDesktop = (active: boolean) =>
    `whitespace-nowrap rounded-lg px-3 py-2 text-sm font-medium transition ${
      active ? "text-accent-700" : "text-ink-600 hover:bg-ink-100 hover:text-ink-900"
    }`;

  /** Alvo de toque confortável: 44px de altura mínima. */
  const itemMobile = (active: boolean) =>
    `flex min-h-[44px] items-center rounded-lg px-3 text-[15px] transition ${
      active ? "bg-accent-50 font-medium text-accent-800" : "text-ink-700 active:bg-ink-100"
    }`;

  return (
    <div ref={barraRef} className="flex items-center">
      {/* ── Desktop: barra com dropdowns por clique ───────────────────────── */}
      <nav aria-label="Navegação principal" className="hidden items-center gap-1 sm:flex">
        {NAV.map((item) => {
          if (!isGroup(item)) {
            return (
              <Link key={item.href} href={item.href} className={itemDesktop(!!isActive(item.href))}>
                {item.label}
              </Link>
            );
          }
          const aberto = grupoAberto === item.label;
          const painelId = `nav-grupo-${item.label.toLowerCase()}`;
          const ativoNoGrupo = item.group.some((g) => isActive(g.href));
          return (
            <div key={item.label} className="relative">
              <button
                type="button"
                aria-expanded={aberto}
                aria-controls={painelId}
                onClick={() => setGrupoAberto(aberto ? null : item.label)}
                className={`${itemDesktop(ativoNoGrupo)} inline-flex items-center gap-1`}
              >
                {item.label}
                <span aria-hidden className={`text-[10px] text-ink-500 transition ${aberto ? "rotate-180" : ""}`}>
                  ▾
                </span>
              </button>
              <div
                id={painelId}
                hidden={!aberto}
                className="absolute left-0 top-full z-50 mt-1 min-w-[200px] rounded-lg border border-ink-200 bg-white py-1.5 shadow-lg"
              >
                {item.group.map((g) => (
                  <Link
                    key={g.href}
                    href={g.href}
                    className={`block whitespace-nowrap px-3.5 py-2 text-sm ${
                      isActive(g.href) ? "font-medium text-accent-800" : "text-ink-700 hover:bg-ink-50"
                    }`}
                  >
                    {g.label}
                  </Link>
                ))}
              </div>
            </div>
          );
        })}
      </nav>

      {/* ── Mobile: menu de verdade ───────────────────────────────────────── */}
      {/* Antes eram 13 links numa tira de 720px rolando dentro de 190px: ~26%
          visível por vez, sem indicação de que rolava. */}
      <button
        type="button"
        aria-expanded={menuAberto}
        aria-controls="nav-mobile"
        onClick={() => setMenuAberto((v) => !v)}
        className="-mr-1 flex h-11 w-11 items-center justify-center rounded-lg text-ink-700 active:bg-ink-100 sm:hidden"
      >
        <span className="sr-only">{menuAberto ? "Fechar menu" : "Abrir menu"}</span>
        <svg aria-hidden viewBox="0 0 20 20" className="h-6 w-6" fill="none" stroke="currentColor" strokeWidth="1.75">
          {menuAberto ? (
            <path d="M5 5l10 10M15 5L5 15" strokeLinecap="round" />
          ) : (
            <path d="M3 6h14M3 10h14M3 14h14" strokeLinecap="round" />
          )}
        </svg>
      </button>

      {menuAberto && (
        <div
          ref={painelRef}
          id="nav-mobile"
          className="absolute inset-x-0 top-full max-h-[calc(100dvh-3.5rem)] overflow-y-auto border-b border-ink-200 bg-white px-3 pb-4 pt-2 shadow-lg sm:hidden"
        >
          <nav aria-label="Navegação principal" className="flex flex-col gap-0.5">
            {NAV.map((item) =>
              isGroup(item) ? (
                <div key={item.label} className="mt-2 first:mt-0">
                  <p className="px-3 pb-1 pt-2 text-[11px] font-semibold uppercase tracking-wider text-ink-500">
                    {item.label}
                  </p>
                  {item.group.map((g) => (
                    <Link key={g.href} href={g.href} className={itemMobile(!!isActive(g.href))}>
                      {g.label}
                    </Link>
                  ))}
                </div>
              ) : (
                <Link key={item.href} href={item.href} className={itemMobile(!!isActive(item.href))}>
                  {item.label}
                </Link>
              ),
            )}
          </nav>
        </div>
      )}
    </div>
  );
}
