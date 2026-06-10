/**
 * frontend/app/(auth)/registro/page.tsx
 * Cadastro de novo usuário com validação de senha em tempo real.
 */

"use client";

import { useState, FormEvent } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { registro } from "@/lib/auth";

const SENHA_REQUISITOS = [
  { re: /.{8,}/,          texto: "Mínimo 8 caracteres" },
  { re: /[A-Z]/,          texto: "Uma letra maiúscula" },
  { re: /[a-z]/,          texto: "Uma letra minúscula" },
  { re: /\d/,             texto: "Um número" },
  { re: /[@$!%*#?&]/,     texto: "Um caractere especial (@$!%*#?&)" },
];

function CheckItem({ ok, texto }: { ok: boolean; texto: string }) {
  return (
    <li className={`flex items-center gap-1.5 text-xs ${ok ? "text-green-600" : "text-gray-400"}`}>
      <span>{ok ? "✓" : "○"}</span>
      {texto}
    </li>
  );
}

export default function RegistroPage() {
  const router = useRouter();

  const [form, setForm] = useState({
    email: "", nome: "", senha: "", confirmar_senha: "",
  });
  const [erro,    setErro]    = useState<string | null>(null);
  const [sucesso, setSucesso] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [mostrarReq, setMostrarReq] = useState(false);

  const senhaOk = SENHA_REQUISITOS.every(({ re }) => re.test(form.senha));
  const senhasIguais = form.senha === form.confirmar_senha && form.confirmar_senha.length > 0;

  function handleChange(field: keyof typeof form) {
    return (e: React.ChangeEvent<HTMLInputElement>) =>
      setForm((prev) => ({ ...prev, [field]: e.target.value }));
  }

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setErro(null);

    if (!senhaOk) {
      setErro("A senha não atende aos requisitos de segurança");
      return;
    }
    if (!senhasIguais) {
      setErro("As senhas não coincidem");
      return;
    }

    setLoading(true);
    try {
      const resp = await registro(form.email, form.nome, form.senha, form.confirmar_senha);
      setSucesso(resp.mensagem);
    } catch (err: unknown) {
      setErro(err instanceof Error ? err.message : "Erro ao criar conta");
    } finally {
      setLoading(false);
    }
  }

  if (sucesso) {
    return (
      <div className="text-center">
        <div className="text-5xl mb-4">✉️</div>
        <h2 className="text-xl font-bold text-gray-900 mb-2">Conta criada!</h2>
        <p className="text-gray-600 text-sm mb-6">{sucesso}</p>
        <Link
          href="/login"
          className="inline-block bg-blue-600 text-white rounded-lg px-6 py-2.5 text-sm font-semibold hover:bg-blue-700"
        >
          Ir para o login
        </Link>
      </div>
    );
  }

  return (
    <>
      <h1 className="text-2xl font-bold text-gray-900 mb-1">Criar conta</h1>
      <p className="text-gray-500 text-sm mb-6">
        Acesso gratuito a todos os dados e dashboards públicos
      </p>

      {erro && (
        <div className="bg-red-50 border border-red-200 text-red-700 rounded-lg px-4 py-3 text-sm mb-4">
          {erro}
        </div>
      )}

      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Nome completo</label>
          <input
            type="text"
            required
            minLength={2}
            value={form.nome}
            onChange={handleChange("nome")}
            className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            placeholder="Seu nome"
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">E-mail</label>
          <input
            type="email"
            required
            value={form.email}
            onChange={handleChange("email")}
            className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            placeholder="seu@email.com"
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Senha</label>
          <input
            type="password"
            required
            value={form.senha}
            onChange={handleChange("senha")}
            onFocus={() => setMostrarReq(true)}
            className={`w-full border rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 ${
              form.senha.length > 0
                ? senhaOk ? "border-green-400" : "border-orange-400"
                : "border-gray-300"
            }`}
            placeholder="••••••••"
          />
          {mostrarReq && form.senha.length > 0 && (
            <ul className="mt-2 space-y-1 pl-1">
              {SENHA_REQUISITOS.map(({ re, texto }) => (
                <CheckItem key={texto} ok={re.test(form.senha)} texto={texto} />
              ))}
            </ul>
          )}
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Confirmar senha</label>
          <input
            type="password"
            required
            value={form.confirmar_senha}
            onChange={handleChange("confirmar_senha")}
            className={`w-full border rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 ${
              form.confirmar_senha.length > 0
                ? senhasIguais ? "border-green-400" : "border-red-400"
                : "border-gray-300"
            }`}
            placeholder="••••••••"
          />
          {form.confirmar_senha.length > 0 && !senhasIguais && (
            <p className="text-red-500 text-xs mt-1">As senhas não coincidem</p>
          )}
        </div>

        <button
          type="submit"
          disabled={loading}
          className="w-full bg-blue-600 hover:bg-blue-700 disabled:bg-blue-400 text-white font-semibold rounded-lg py-2.5 text-sm transition-colors"
        >
          {loading ? "Criando conta…" : "Criar conta gratuita"}
        </button>
      </form>

      <div className="mt-6 text-center">
        <span className="text-gray-500 text-sm">Já tem conta? </span>
        <Link href="/login" className="text-blue-600 hover:text-blue-700 text-sm font-medium">
          Entrar
        </Link>
      </div>
    </>
  );
}
