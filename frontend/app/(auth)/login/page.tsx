/**
 * frontend/app/(auth)/login/page.tsx
 * Página de login com validação client-side e redirecionamento pós-autenticação.
 */

"use client";

import { useState, FormEvent } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { login } from "@/lib/auth";

export default function LoginPage() {
  const router      = useRouter();
  const params      = useSearchParams();
  const redirectTo  = params.get("redirect") ?? "/portal";

  const [email,    setEmail]    = useState("");
  const [senha,    setSenha]    = useState("");
  const [erro,     setErro]     = useState<string | null>(null);
  const [loading,  setLoading]  = useState(false);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setErro(null);
    setLoading(true);

    try {
      await login(email, senha);
      // Setar cookie de sessão simples para o middleware Next.js
      document.cookie = "spbr_session=1; path=/; max-age=2592000; SameSite=Lax";
      router.push(redirectTo);
    } catch (err: unknown) {
      setErro(err instanceof Error ? err.message : "Erro ao fazer login");
    } finally {
      setLoading(false);
    }
  }

  return (
    <>
      <h1 className="text-2xl font-bold text-gray-900 mb-1">Entrar</h1>
      <p className="text-gray-500 text-sm mb-6">
        Acesse o portal de dados epidemiológicos
      </p>

      {erro && (
        <div className="bg-red-50 border border-red-200 text-red-700 rounded-lg px-4 py-3 text-sm mb-4">
          {erro}
        </div>
      )}

      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            E-mail
          </label>
          <input
            type="email"
            required
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            placeholder="seu@email.com"
            autoComplete="email"
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Senha
          </label>
          <input
            type="password"
            required
            value={senha}
            onChange={(e) => setSenha(e.target.value)}
            className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            placeholder="••••••••"
            autoComplete="current-password"
          />
        </div>

        <button
          type="submit"
          disabled={loading}
          className="w-full bg-blue-600 hover:bg-blue-700 disabled:bg-blue-400 text-white font-semibold rounded-lg py-2.5 text-sm transition-colors"
        >
          {loading ? "Entrando…" : "Entrar"}
        </button>
      </form>

      <div className="mt-6 text-center">
        <span className="text-gray-500 text-sm">Não tem conta? </span>
        <Link
          href="/registro"
          className="text-blue-600 hover:text-blue-700 text-sm font-medium"
        >
          Criar conta gratuita
        </Link>
      </div>

      <div className="mt-3 text-center">
        <Link
          href="/portal"
          className="text-gray-400 hover:text-gray-600 text-xs"
        >
          Continuar sem conta →
        </Link>
      </div>
    </>
  );
}
