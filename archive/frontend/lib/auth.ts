/**
 * frontend/lib/auth.ts
 * Cliente de autenticação: login, registro, refresh, logout.
 * Armazena tokens no localStorage (access) e cookie HttpOnly via API (refresh).
 */

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export interface UserPublic {
  id: string;
  email: string;
  nome: string;
  role: "viewer" | "analyst" | "admin";
  status: "pending" | "active" | "suspended";
  email_verificado: boolean;
  ultimo_login: string | null;
  criado_em: string;
}

export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: "Bearer";
  expires_in: number;
  usuario: UserPublic;
}

export interface RegisterResponse {
  mensagem: string;
  usuario_id: string;
  email_verificacao_enviado: boolean;
}

// ─── Storage ─────────────────────────────────────────────────────────────────

const ACCESS_KEY  = "spbr_access_token";
const REFRESH_KEY = "spbr_refresh_token";
const USER_KEY    = "spbr_user";

export function getAccessToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem(ACCESS_KEY);
}

export function getStoredUser(): UserPublic | null {
  if (typeof window === "undefined") return null;
  const raw = localStorage.getItem(USER_KEY);
  if (!raw) return null;
  try {
    return JSON.parse(raw) as UserPublic;
  } catch {
    return null;
  }
}

function _saveSession(resp: TokenResponse): void {
  localStorage.setItem(ACCESS_KEY, resp.access_token);
  localStorage.setItem(REFRESH_KEY, resp.refresh_token);
  localStorage.setItem(USER_KEY, JSON.stringify(resp.usuario));
}

function _clearSession(): void {
  localStorage.removeItem(ACCESS_KEY);
  localStorage.removeItem(REFRESH_KEY);
  localStorage.removeItem(USER_KEY);
}

// ─── API Calls ────────────────────────────────────────────────────────────────

async function _apiFetch<T>(
  path: string,
  options: RequestInit = {},
): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: {
      "Content-Type": "application/json",
      ...options.headers,
    },
    ...options,
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail ?? "Erro desconhecido");
  }

  return res.json() as Promise<T>;
}

// ─── Auth Functions ───────────────────────────────────────────────────────────

export async function login(email: string, senha: string): Promise<UserPublic> {
  const resp = await _apiFetch<TokenResponse>("/auth/login", {
    method: "POST",
    body: JSON.stringify({ email, senha }),
  });
  _saveSession(resp);
  return resp.usuario;
}

export async function registro(
  email: string,
  nome: string,
  senha: string,
  confirmar_senha: string,
): Promise<RegisterResponse> {
  return _apiFetch<RegisterResponse>("/auth/registro", {
    method: "POST",
    body: JSON.stringify({ email, nome, senha, confirmar_senha }),
  });
}

export async function logout(): Promise<void> {
  const refreshToken = localStorage.getItem(REFRESH_KEY);
  const accessToken  = getAccessToken();

  if (refreshToken && accessToken) {
    await _apiFetch("/auth/logout", {
      method: "POST",
      headers: { Authorization: `Bearer ${accessToken}` },
      body: JSON.stringify({ refresh_token: refreshToken }),
    }).catch(() => {/* ignora erros na hora do logout */});
  }

  _clearSession();
}

export async function refreshAccessToken(): Promise<string | null> {
  const refreshToken = localStorage.getItem(REFRESH_KEY);
  if (!refreshToken) return null;

  try {
    const resp = await _apiFetch<TokenResponse>("/auth/refresh", {
      method: "POST",
      body: JSON.stringify({ refresh_token: refreshToken }),
    });
    _saveSession(resp);
    return resp.access_token;
  } catch {
    _clearSession();
    return null;
  }
}

export async function getMe(): Promise<UserPublic> {
  const token = getAccessToken();
  return _apiFetch<UserPublic>("/auth/me", {
    headers: { Authorization: `Bearer ${token}` },
  });
}

// ─── Fetch autenticado (com auto-refresh) ─────────────────────────────────────

export async function authFetch<T>(path: string, options: RequestInit = {}): Promise<T> {
  let token = getAccessToken();

  const doFetch = () =>
    _apiFetch<T>(path, {
      ...options,
      headers: {
        ...options.headers,
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
    });

  try {
    return await doFetch();
  } catch (err: unknown) {
    // Se 401, tenta refresh e refaz
    if (err instanceof Error && err.message.includes("401")) {
      token = await refreshAccessToken();
      if (!token) throw new Error("Sessão expirada. Faça login novamente.");
      return doFetch();
    }
    throw err;
  }
}

export function isAuthenticated(): boolean {
  return !!getAccessToken();
}
