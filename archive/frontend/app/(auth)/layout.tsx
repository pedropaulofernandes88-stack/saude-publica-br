/**
 * frontend/app/(auth)/layout.tsx
 * Layout das páginas de autenticação (login / registro).
 * Centralizado, sem navbar, com branding do projeto.
 */

import type { ReactNode } from "react";

export const metadata = {
  title: "Saúde Pública BR — Acesso",
  description: "Portal de dados epidemiológicos do SUS",
};

export default function AuthLayout({ children }: { children: ReactNode }) {
  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-950 via-blue-900 to-teal-800 flex items-center justify-center p-4">
      <div className="w-full max-w-md">
        {/* Branding */}
        <div className="text-center mb-8">
          <div className="inline-flex items-center gap-2 mb-3">
            <span className="text-3xl">🩺</span>
            <span className="text-white font-bold text-2xl">Saúde Pública BR</span>
          </div>
          <p className="text-blue-300 text-sm">
            O Our World in Data do SUS
          </p>
        </div>

        {/* Card */}
        <div className="bg-white rounded-2xl shadow-2xl p-8">
          {children}
        </div>

        {/* Footer */}
        <p className="text-center text-blue-300 text-xs mt-6">
          Dados abertos do DataSUS · Projeto open-source
        </p>
      </div>
    </div>
  );
}
