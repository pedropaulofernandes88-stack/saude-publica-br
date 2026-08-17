"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  Activity,
  BarChart3,
  Heart,
  Map,
  AlertTriangle,
  Stethoscope,
} from "lucide-react";
import { cn } from "@/lib/utils";

const navItems = [
  {
    href: "/internacoes",
    label: "Internações",
    icon: Activity,
    description: "SIH — internações hospitalares",
  },
  {
    href: "/mortalidade",
    label: "Mortalidade",
    icon: Heart,
    description: "SIM — óbitos registrados",
  },
  {
    href: "/ranking",
    label: "Ranking",
    icon: BarChart3,
    description: "Municípios por taxa",
  },
  {
    href: "/epidemiologia",
    label: "Epidemiologia",
    icon: Stethoscope,
    description: "CID-10 por capítulo",
  },
  {
    href: "/anomalias",
    label: "Anomalias",
    icon: AlertTriangle,
    description: "Alertas estatísticos",
  },
] as const;

export function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="flex flex-col w-[240px] min-h-screen border-r bg-card shrink-0">
      {/* Logo */}
      <div className="flex items-center gap-2 px-4 py-5 border-b">
        <Map className="h-6 w-6 text-primary" />
        <div className="leading-tight">
          <p className="text-sm font-semibold text-foreground">Saúde Pública</p>
          <p className="text-xs text-muted-foreground">Brasil · SUS</p>
        </div>
      </div>

      {/* Nav */}
      <nav className="flex-1 px-2 py-4 space-y-1 overflow-y-auto scrollbar-thin">
        {navItems.map(({ href, label, icon: Icon, description }) => {
          const active = pathname.startsWith(href);
          return (
            <Link
              key={href}
              href={href}
              className={cn(
                "flex items-center gap-3 rounded-md px-3 py-2.5 text-sm transition-colors",
                active
                  ? "bg-primary/10 text-primary font-medium"
                  : "text-muted-foreground hover:bg-accent hover:text-accent-foreground"
              )}
            >
              <Icon className="h-4 w-4 shrink-0" />
              <div className="min-w-0">
                <p className="truncate">{label}</p>
                {active && (
                  <p className="truncate text-xs text-primary/70">
                    {description}
                  </p>
                )}
              </div>
            </Link>
          );
        })}
      </nav>

      {/* Footer */}
      <div className="px-4 py-3 border-t">
        <p className="text-xs text-muted-foreground">
          Dados: DATASUS / MS
        </p>
        <p className="text-xs text-muted-foreground">
          Atualização mensal
        </p>
      </div>
    </aside>
  );
}
