/**
 * frontend/middleware.ts
 * Next.js Edge Middleware: proteção de rotas /portal/*.
 * Redireciona para /login se não houver access token.
 */

import { NextRequest, NextResponse } from "next/server";

const PROTECTED_PREFIXES = ["/portal/dashboards/new", "/portal/perfil"];
const PUBLIC_AUTH_PATHS  = ["/login", "/registro", "/auth/verificar-email"];

export function middleware(request: NextRequest): NextResponse {
  const { pathname } = request.nextUrl;

  // Verificar se a rota requer autenticação
  const isProtected = PROTECTED_PREFIXES.some((prefix) =>
    pathname.startsWith(prefix)
  );

  if (!isProtected) return NextResponse.next();

  // O token fica no localStorage (client-side), não em cookies HttpOnly aqui.
  // O middleware valida apenas presença de um cookie de sessão simples.
  // A validação real de JWT acontece no lado cliente e na API.
  const sessionCookie = request.cookies.get("spbr_session");

  if (!sessionCookie) {
    const loginUrl = new URL("/login", request.url);
    loginUrl.searchParams.set("redirect", pathname);
    return NextResponse.redirect(loginUrl);
  }

  return NextResponse.next();
}

export const config = {
  matcher: ["/portal/:path*"],
};
