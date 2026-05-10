/**
 * JWT token saklama, okuma ve temizleme yardımcıları.
 * Token localStorage'da tutulur (MVP — tek kullanıcı, SSR yok).
 */

const TOKEN_KEY = "usalp_token";

export function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem(TOKEN_KEY);
}

export function setToken(token: string): void {
  localStorage.setItem(TOKEN_KEY, token);
}

export function clearToken(): void {
  localStorage.removeItem(TOKEN_KEY);
}

export function isAuthenticated(): boolean {
  return getToken() !== null;
}
