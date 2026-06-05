"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Activity, Loader2 } from "lucide-react";
import { ApiError, api } from "@/lib/api";
import { setToken } from "@/lib/auth";

export default function LoginPage() {
  const router = useRouter();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const normalizedUsername = username.trim();

    if (!normalizedUsername) {
      setError("Kullanıcı adı boş olamaz.");
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const res = await api.auth.login({ username: normalizedUsername, password });
      setToken(res.access_token);
      router.push("/");
    } catch (err) {
      if (err instanceof ApiError && err.status === 401) {
        setError(
          "Kullanıcı adı veya şifre hatalı. Kurulumda girilen değerler birebir eşleşmeli. Emin değilseniz sunucuda ./scripts/setup-prod.sh --reset-dashboard-password çalıştırın.",
        );
      } else if (err instanceof ApiError && err.status === 429) {
        setError("Çok fazla başarısız giriş denemesi. Birkaç dakika sonra tekrar deneyin.");
      } else {
        setError("Backend'e bağlanılamıyor. Servisin çalıştığından emin olun.");
      }
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-slate-50">
      <div className="w-full max-w-sm">
        {/* Logo */}
        <div className="mb-8 flex flex-col items-center gap-3">
          <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-brand-600 shadow-lg">
            <Activity size={24} className="text-white" />
          </div>
          <div className="text-center">
            <h1 className="text-2xl font-bold text-slate-900">Usalp</h1>
            <p className="mt-1 text-sm text-slate-500">
              AI destekli sunucu izleme platformu
            </p>
          </div>
        </div>

        {/* Kart */}
        <div className="rounded-2xl border border-slate-200 bg-white p-8 shadow-sm">
          <h2 className="mb-6 text-base font-semibold text-slate-900">
            Giriş Yap
          </h2>

          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="mb-1.5 block text-sm font-medium text-slate-700">
                Kullanıcı Adı
              </label>
              <input
                type="text"
                required
                autoComplete="username"
                autoCapitalize="none"
                autoCorrect="off"
                spellCheck={false}
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                className="w-full rounded-lg border border-slate-200 px-3 py-2.5 text-sm text-slate-900 placeholder:text-slate-400 focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
                placeholder="admin"
              />
            </div>

            <div>
              <label className="mb-1.5 block text-sm font-medium text-slate-700">
                Şifre
              </label>
              <input
                type="password"
                required
                autoComplete="current-password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="w-full rounded-lg border border-slate-200 px-3 py-2.5 text-sm text-slate-900 placeholder:text-slate-400 focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
                placeholder="••••••••"
              />
            </div>

            {error && (
              <p className="rounded-lg bg-red-50 px-3 py-2 text-sm text-red-600">
                {error}
              </p>
            )}

            <button
              type="submit"
              disabled={loading}
              className="mt-2 inline-flex w-full items-center justify-center gap-2 rounded-lg bg-brand-600 py-2.5 text-sm font-medium text-white hover:bg-brand-700 disabled:opacity-60 transition-colors"
            >
              {loading && <Loader2 size={15} className="animate-spin" />}
              Giriş Yap
            </button>
          </form>
        </div>
      </div>
    </div>
  );
}
