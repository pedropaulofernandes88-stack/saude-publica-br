import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

/** shadcn/ui className helper */
export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

/** Formata mês competência "YYYY-MM" → "Jan 2024" */
export function formatMesCompetencia(mes: string): string {
  const [ano, m] = mes.split("-");
  const meses = [
    "Jan", "Fev", "Mar", "Abr", "Mai", "Jun",
    "Jul", "Ago", "Set", "Out", "Nov", "Dez",
  ];
  const idx = parseInt(m, 10) - 1;
  return `${meses[idx] ?? m} ${ano}`;
}

/** Formata número com separador de milhar (pt-BR) */
export function formatNumero(n: number | null | undefined, decimais = 0): string {
  if (n == null) return "—";
  return n.toLocaleString("pt-BR", {
    minimumFractionDigits: decimais,
    maximumFractionDigits: decimais,
  });
}

/** Formata taxa por 100k (2 casas decimais) */
export function formatTaxa(n: number | null | undefined): string {
  if (n == null) return "—";
  return n.toLocaleString("pt-BR", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
}

/** Formata valor monetário em R$ */
export function formatReais(n: number | null | undefined): string {
  if (n == null) return "—";
  return n.toLocaleString("pt-BR", {
    style: "currency",
    currency: "BRL",
    maximumFractionDigits: 0,
  });
}

/** Constrói URL de query com parâmetros opcionais */
export function buildUrl(
  base: string,
  params: Record<string, string | number | boolean | undefined | null>,
): string {
  const url = new URL(base, "http://placeholder");
  for (const [key, value] of Object.entries(params)) {
    if (value != null && value !== "") {
      url.searchParams.set(key, String(value));
    }
  }
  return url.pathname + (url.search || "");
}

/** Cor semafórica para severidade de anomalia */
export function corSeveridade(s: string): string {
  switch (s) {
    case "critica": return "destructive";
    case "alta":    return "orange";
    case "media":   return "yellow";
    default:        return "muted";
  }
}
