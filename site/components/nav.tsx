"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

type Item = { href: string; label: string; curto: string };
type Entry = Item | { label: string; curto: string; group: Item[] };

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

function isGroup(e: Entry): e is { label: string; curto: string; group: Item[] } {
  return "group" in e;
}

export function Nav() {
  const pathname = usePathname();
  const isActive = (href: string) => (href === "/" ? pathname === "/" : pathname?.startsWith(href));

  const linkClass = (active: boolean) =>
    `whitespace-nowrap rounded-lg px-2 py-2 text-[13px] font-medium transition sm:px-3 sm:text-sm ${
      active ? "text-accent-700" : "text-ink-600 hover:bg-ink-100 hover:text-ink-900"
    }`;

  return (
    <nav className="flex items-center gap-0 overflow-x-auto sm:gap-1 sm:overflow-visible">
      {NAV.map((item) => {
        if (isGroup(item)) {
          const activeInGroup = item.group.some((g) => isActive(g.href));
          return (
            <div key={item.label} className="group/nav relative">
              <button
                type="button"
                className={`${linkClass(activeInGroup)} hidden items-center gap-0.5 sm:inline-flex`}
              >
                {item.label}
                <span aria-hidden className="text-[10px] text-ink-400">▾</span>
              </button>
              {/* mobile: itens do grupo aparecem soltos na lista rolável */}
              {item.group.map((g) => (
                <Link key={g.href} href={g.href} className={`${linkClass(isActive(g.href))} sm:hidden`}>
                  {g.curto}
                </Link>
              ))}
              {/* desktop: dropdown por hover */}
              <div className="invisible absolute left-0 top-full z-50 hidden min-w-[180px] rounded-lg border border-ink-200 bg-white py-1.5 opacity-0 shadow-lg transition group-hover/nav:visible group-hover/nav:opacity-100 sm:block">
                {item.group.map((g) => (
                  <Link
                    key={g.href}
                    href={g.href}
                    className={`block whitespace-nowrap px-3.5 py-2 text-sm ${
                      isActive(g.href) ? "font-medium text-accent-700" : "text-ink-700 hover:bg-ink-50"
                    }`}
                  >
                    {g.label}
                  </Link>
                ))}
              </div>
            </div>
          );
        }
        const active = isActive(item.href);
        return (
          <Link
            key={item.href}
            href={item.href}
            className={`${linkClass(active)} ${item.href === "/" ? "hidden sm:inline-flex" : ""}`}
          >
            <span className="sm:hidden">{item.curto}</span>
            <span className="hidden sm:inline">{item.label}</span>
          </Link>
        );
      })}
    </nav>
  );
}
