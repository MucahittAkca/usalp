"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import useSWR from "swr";
import { AppShell } from "@/components/layout/AppShell";
import { MetricGrid } from "@/components/metrics/MetricGrid";
import { ServiceList } from "@/components/services/ServiceList";
import { LogViewer } from "@/components/logs/LogViewer";
import { AnalysisPanel } from "@/components/ai/AnalysisPanel";
import { ServerStatusBadge } from "@/components/servers/ServerStatusBadge";
import { useServerMetrics, type MetricRange } from "@/hooks/useServerMetrics";
import { api } from "@/lib/api";
import {
  SERVER_ENVIRONMENT_COLORS,
  SERVER_ENVIRONMENT_LABELS,
  cn,
  formatDateTime,
} from "@/lib/utils";
import type { ApiResponse, Server } from "@/types/api";
import { Ban, Boxes, KeyRound, Monitor, Tag } from "lucide-react";

// ---------------------------------------------------------------------------
// Sekme tanımları
// ---------------------------------------------------------------------------

type TabKey = "metrics" | "services" | "logs" | "ai";

const TABS: { key: TabKey; label: string; suffix: string }[] = [
  { key: "metrics",  label: "Metrikler",  suffix: "" },
  { key: "services", label: "Servisler",  suffix: "#services" },
  { key: "logs",     label: "Loglar",     suffix: "#logs" },
  { key: "ai",       label: "AI Analiz",  suffix: "#ai" },
];

function getActiveTab(hash: string): TabKey {
  if (hash === "#services") return "services";
  if (hash === "#logs")     return "logs";
  if (hash === "#ai")       return "ai";
  return "metrics";
}

// ---------------------------------------------------------------------------
// TabNav — hash-based sekme navigasyonu
// ---------------------------------------------------------------------------

function TabNav({ serverId, active }: { serverId: number; active: TabKey }) {
  return (
    <nav
      className="flex border-b border-slate-200"
      aria-label="Sunucu detay sekmeleri"
    >
      {TABS.map((tab) => (
        <Link
          key={tab.key}
          href={`/servers/${serverId}${tab.suffix}`}
          replace
          className={cn(
            "px-5 py-3 text-sm font-medium transition-colors",
            active === tab.key
              ? "border-b-2 border-blue-500 text-blue-600"
              : "text-slate-500 hover:text-slate-800",
          )}
          aria-current={active === tab.key ? "page" : undefined}
        >
          {tab.label}
        </Link>
      ))}
    </nav>
  );
}

// ---------------------------------------------------------------------------
// ServerDetailPage
// ---------------------------------------------------------------------------

interface ServerDetailPageProps {
  params: { id: string };
}

export default function ServerDetailPage({ params }: ServerDetailPageProps) {
  const serverId = Number(params.id);
  const [activeTab, setActiveTab] = useState<TabKey>("metrics");
  const [newApiKey, setNewApiKey] = useState<string | null>(null);
  const [keyActionError, setKeyActionError] = useState<string | null>(null);
  const [keyActionLoading, setKeyActionLoading] = useState<"rotate" | "revoke" | null>(null);
  const [metricRange, setMetricRange] = useState<MetricRange>("1h");

  useEffect(() => {
    const updateActiveTab = () => setActiveTab(getActiveTab(window.location.hash));
    updateActiveTab();
    window.addEventListener("hashchange", updateActiveTab);
    return () => window.removeEventListener("hashchange", updateActiveTab);
  }, []);

  const {
    data: serverData,
    error: serverError,
    isLoading: serverLoading,
    mutate: mutateServer,
  } = useSWR<ApiResponse<Server>>(
    `server-${serverId}`,
    () => api.servers.get(serverId),
    { refreshInterval: 30_000 },
  );

  const { metrics, isLoading: metricsLoading } = useServerMetrics(serverId, metricRange);

  const server = serverData?.data;
  const envLabel = server
    ? SERVER_ENVIRONMENT_LABELS[server.environment] ?? server.environment
    : "";
  const envClass = server
    ? SERVER_ENVIRONMENT_COLORS[server.environment] ??
      "border-slate-200 bg-slate-50 text-slate-600"
    : "";

  async function rotateKey() {
    setKeyActionLoading("rotate");
    setKeyActionError(null);
    try {
      const res = await api.servers.rotateKey(serverId);
      setNewApiKey(res.data.api_key);
      await mutateServer();
    } catch (err) {
      setKeyActionError(err instanceof Error ? err.message : "API anahtarı yenilenemedi");
    } finally {
      setKeyActionLoading(null);
    }
  }

  async function revokeKey() {
    setKeyActionLoading("revoke");
    setKeyActionError(null);
    setNewApiKey(null);
    try {
      await api.servers.revokeKey(serverId);
      await mutateServer();
    } catch (err) {
      setKeyActionError(err instanceof Error ? err.message : "API anahtarı iptal edilemedi");
    } finally {
      setKeyActionLoading(null);
    }
  }

  return (
    <AppShell>
      <div className="flex flex-col min-h-screen">
        {/* Üst başlık */}
        <div className="border-b border-slate-200 bg-white px-6 py-5">
          {serverLoading && (
            <div className="space-y-2">
              <div className="h-5 w-48 animate-pulse rounded bg-slate-100" />
              <div className="h-4 w-64 animate-pulse rounded bg-slate-100" />
            </div>
          )}

          {serverError && !serverLoading && (
            <p className="text-sm text-red-500">Sunucu bilgisi yüklenemedi.</p>
          )}

          {server && (
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div className="flex items-center gap-3">
                <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-slate-100">
                  <Monitor size={18} className="text-slate-500" />
                </div>
                <div>
                  <div className="flex items-center gap-2">
                    <h1 className="text-lg font-bold text-slate-900">{server.name}</h1>
                    <ServerStatusBadge status={server.status} />
                  </div>
                  <p className="text-sm text-slate-400">
                    {server.hostname} · {server.ip_address}
                  </p>
                  <div className="mt-2 flex flex-wrap items-center gap-1.5">
                    <span
                      className={cn(
                        "inline-flex items-center rounded-full border px-2 py-0.5 text-[11px] font-medium",
                        envClass,
                      )}
                    >
                      {envLabel}
                    </span>
                    {server.group_name && (
                      <span className="inline-flex items-center gap-1 rounded-full border border-slate-200 bg-slate-50 px-2 py-0.5 text-[11px] font-medium text-slate-600">
                        <Boxes size={10} />
                        {server.group_name}
                      </span>
                    )}
                    {server.tags.map((tag) => (
                      <span
                        key={tag}
                        className="inline-flex items-center gap-1 rounded-full bg-slate-100 px-2 py-0.5 text-[11px] text-slate-500"
                      >
                        <Tag size={10} />
                        {tag}
                      </span>
                    ))}
                  </div>
                </div>
              </div>
              <div className="flex flex-col items-end gap-2">
                <p className="text-xs text-slate-400">
                  Eklendi: {formatDateTime(server.created_at)}
                  {server.last_seen && (
                    <span className="ml-2">
                      Son görülme: {formatDateTime(server.last_seen)}
                    </span>
                  )}
                </p>
                <div className="flex flex-wrap justify-end gap-2">
                  <button
                    onClick={rotateKey}
                    disabled={keyActionLoading !== null}
                    className="inline-flex items-center gap-1.5 rounded-md bg-slate-100 px-3 py-1.5 text-xs font-medium text-slate-700 hover:bg-slate-200 disabled:opacity-50"
                  >
                    <KeyRound size={12} />
                    {keyActionLoading === "rotate" ? "Yenileniyor" : "Anahtarı Yenile"}
                  </button>
                  <button
                    onClick={revokeKey}
                    disabled={keyActionLoading !== null}
                    className="inline-flex items-center gap-1.5 rounded-md bg-red-50 px-3 py-1.5 text-xs font-medium text-red-700 hover:bg-red-100 disabled:opacity-50"
                  >
                    <Ban size={12} />
                    {keyActionLoading === "revoke" ? "İptal ediliyor" : "Anahtarı İptal Et"}
                  </button>
                </div>
              </div>
            </div>
          )}
        </div>

        {(newApiKey || keyActionError) && (
          <div className="border-b border-slate-200 bg-white px-6 py-3">
            {newApiKey && (
              <div className="rounded-lg bg-slate-900 px-4 py-3">
                <p className="mb-1 text-xs font-medium text-slate-400">
                  Yeni API anahtarı yalnızca bir kez gösterilir
                </p>
                <code className="break-all font-mono text-xs text-green-400">{newApiKey}</code>
              </div>
            )}
            {keyActionError && (
              <p className="rounded-lg bg-red-50 px-3 py-2 text-sm text-red-600">
                {keyActionError}
              </p>
            )}
          </div>
        )}

        {/* Sekme navigasyonu */}
        <div className="bg-white px-6">
          <TabNav serverId={serverId} active={activeTab} />
        </div>

        {/* İçerik */}
        <div className="flex-1 px-6 py-6">
          {activeTab === "metrics" && (
            <MetricGrid
              metrics={metrics}
              isLoading={metricsLoading}
              range={metricRange}
              onRangeChange={setMetricRange}
            />
          )}
          {activeTab === "services" && (
            <ServiceList serverId={serverId} />
          )}
          {activeTab === "logs" && (
            <LogViewer serverId={serverId} />
          )}
          {activeTab === "ai" && (
            <div className="max-w-3xl">
              <AnalysisPanel serverId={serverId} />
            </div>
          )}
        </div>
      </div>
    </AppShell>
  );
}
