"use client";

import { useState } from "react";
import { Check, Copy, Loader2, Plus, Server, X } from "lucide-react";
import { api } from "@/lib/api";
import type { ServerCreated } from "@/types/api";

interface Props {
  onCreated: () => void;
}

type Step = "form" | "success";

export function AddServerModal({ onCreated }: Props) {
  const [open, setOpen] = useState(false);
  const [step, setStep] = useState<Step>("form");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [created, setCreated] = useState<ServerCreated | null>(null);
  const [copied, setCopied] = useState(false);

  const [form, setForm] = useState({ name: "", hostname: "", ip_address: "" });

  function openModal() {
    setStep("form");
    setForm({ name: "", hostname: "", ip_address: "" });
    setError(null);
    setCreated(null);
    setCopied(false);
    setOpen(true);
  }

  function closeModal() {
    setOpen(false);
    if (step === "success") {
      onCreated();
    }
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError(null);

    try {
      const res = await api.servers.create(form);
      setCreated(res.data);
      setStep("success");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Sunucu eklenemedi");
    } finally {
      setLoading(false);
    }
  }

  function copyApiKey() {
    if (!created) return;
    navigator.clipboard.writeText(created.api_key);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  }

  const backendOrigin =
    typeof window !== "undefined" ? window.location.origin : "http://localhost";
  const installCommand = created
    ? `curl -fsSL ${backendOrigin}/install.sh | bash -s -- --api-key ${created.api_key} --backend-url ${backendOrigin}`
    : "";

  function copyInstall() {
    navigator.clipboard.writeText(installCommand);
  }

  return (
    <>
      <button
        onClick={openModal}
        className="inline-flex items-center gap-2 rounded-lg bg-brand-600 px-4 py-2 text-sm font-medium text-white shadow-sm hover:bg-brand-700 transition-colors"
      >
        <Plus size={16} />
        Sunucu Ekle
      </button>

      {open && (
        <div className="fixed inset-0 z-50 flex items-center justify-center">
          {/* Backdrop */}
          <div
            className="absolute inset-0 bg-black/40 backdrop-blur-sm"
            onClick={closeModal}
          />

          {/* Modal */}
          <div className="relative z-10 w-full max-w-lg mx-4 bg-white rounded-2xl shadow-2xl">
            {/* Header */}
            <div className="flex items-center justify-between px-6 py-5 border-b border-slate-100">
              <div className="flex items-center gap-3">
                <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-brand-50">
                  <Server size={18} className="text-brand-600" />
                </div>
                <div>
                  <h2 className="text-base font-semibold text-slate-900">
                    {step === "form" ? "Yeni Sunucu Ekle" : "Sunucu Eklendi"}
                  </h2>
                  <p className="text-xs text-slate-500">
                    {step === "form"
                      ? "Sunucu bilgilerini girin"
                      : "API anahtarını güvenli saklayın"}
                  </p>
                </div>
              </div>
              <button
                onClick={closeModal}
                className="rounded-md p-1.5 text-slate-400 hover:bg-slate-100 hover:text-slate-600 transition-colors"
              >
                <X size={18} />
              </button>
            </div>

            {/* Body */}
            <div className="px-6 py-5">
              {step === "form" ? (
                <form onSubmit={handleSubmit} className="space-y-4">
                  <div>
                    <label className="block text-sm font-medium text-slate-700 mb-1.5">
                      Sunucu Adı
                    </label>
                    <input
                      type="text"
                      required
                      placeholder="Web Sunucusu"
                      value={form.name}
                      onChange={(e) =>
                        setForm((f) => ({ ...f, name: e.target.value }))
                      }
                      className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm text-slate-900 placeholder:text-slate-400 focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-slate-700 mb-1.5">
                      Hostname
                    </label>
                    <input
                      type="text"
                      required
                      placeholder="web-server-01"
                      value={form.hostname}
                      onChange={(e) =>
                        setForm((f) => ({ ...f, hostname: e.target.value }))
                      }
                      className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm text-slate-900 placeholder:text-slate-400 focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-slate-700 mb-1.5">
                      IP Adresi
                    </label>
                    <input
                      type="text"
                      required
                      placeholder="192.168.1.100"
                      value={form.ip_address}
                      onChange={(e) =>
                        setForm((f) => ({ ...f, ip_address: e.target.value }))
                      }
                      className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm text-slate-900 placeholder:text-slate-400 focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
                    />
                  </div>

                  {error && (
                    <p className="rounded-lg bg-red-50 px-3 py-2 text-sm text-red-600">
                      {error}
                    </p>
                  )}

                  <div className="flex justify-end gap-3 pt-1">
                    <button
                      type="button"
                      onClick={closeModal}
                      className="rounded-lg px-4 py-2 text-sm font-medium text-slate-600 hover:bg-slate-100 transition-colors"
                    >
                      İptal
                    </button>
                    <button
                      type="submit"
                      disabled={loading}
                      className="inline-flex items-center gap-2 rounded-lg bg-brand-600 px-4 py-2 text-sm font-medium text-white hover:bg-brand-700 disabled:opacity-60 transition-colors"
                    >
                      {loading && <Loader2 size={14} className="animate-spin" />}
                      Ekle
                    </button>
                  </div>
                </form>
              ) : (
                created && (
                  <div className="space-y-4">
                    {/* Başarı mesajı */}
                    <div className="flex items-center gap-2 rounded-lg bg-green-50 px-4 py-3">
                      <Check size={16} className="text-green-600 shrink-0" />
                      <p className="text-sm text-green-700">
                        <span className="font-semibold">{created.name}</span>{" "}
                        sisteme eklendi.
                      </p>
                    </div>

                    {/* API Key */}
                    <div>
                      <p className="text-sm font-medium text-slate-700 mb-1.5">
                        API Anahtarı{" "}
                        <span className="font-normal text-slate-400">
                          — yalnızca bir kez gösterilir
                        </span>
                      </p>
                      <div className="flex items-center gap-2 rounded-lg bg-slate-900 px-4 py-3">
                        <code className="flex-1 text-xs text-green-400 font-mono break-all">
                          {created.api_key}
                        </code>
                        <button
                          onClick={copyApiKey}
                          className="shrink-0 rounded-md p-1 text-slate-400 hover:text-white transition-colors"
                          title="Kopyala"
                        >
                          {copied ? (
                            <Check size={14} className="text-green-400" />
                          ) : (
                            <Copy size={14} />
                          )}
                        </button>
                      </div>
                    </div>

                    {/* Kurulum komutu */}
                    <div>
                      <p className="text-sm font-medium text-slate-700 mb-1.5">
                        Agent Kurulum Komutu
                      </p>
                      <div className="flex items-start gap-2 rounded-lg bg-slate-900 px-4 py-3">
                        <code className="flex-1 text-xs text-slate-300 font-mono break-all leading-5">
                          {installCommand}
                        </code>
                        <button
                          onClick={copyInstall}
                          className="shrink-0 mt-0.5 rounded-md p-1 text-slate-400 hover:text-white transition-colors"
                          title="Kopyala"
                        >
                          <Copy size={14} />
                        </button>
                      </div>
                      <p className="mt-2 text-xs text-slate-400">
                        Bu komutu izlemek istediğiniz sunucunun terminalinde çalıştırın.
                      </p>
                    </div>

                    <div className="flex justify-end pt-1">
                      <button
                        onClick={closeModal}
                        className="rounded-lg bg-brand-600 px-4 py-2 text-sm font-medium text-white hover:bg-brand-700 transition-colors"
                      >
                        Tamam
                      </button>
                    </div>
                  </div>
                )
              )}
            </div>
          </div>
        </div>
      )}
    </>
  );
}
