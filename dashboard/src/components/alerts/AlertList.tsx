"use client";

import useSWR from "swr";
import { AlertTriangle, BellOff, ChevronDown, ChevronUp, RefreshCw } from "lucide-react";
import { useState } from "react";
import { api } from "@/lib/api";
import { AlertCard } from "@/components/alerts/AlertCard";
import { cn } from "@/lib/utils";
import type { Alert, AlertSeverity } from "@/types/api";

// ---------------------------------------------------------------------------
// SWR — tüm alarmları çek (resolved dahil, sayfa için)
// ---------------------------------------------------------------------------

function useAllAlerts() {
  const { data, error, isLoading, mutate } = useSWR(
    "alerts-page-all",
    () => api.alerts.list({ per_page: 100 }),
    { refreshInterval: 15_000 },
  );

  const alerts: Alert[] = data?.data ?? [];
  const active   = alerts.filter((a) => a.resolved_at === null);
  const resolved = alerts.filter((a) => a.resolved_at !== null);

  return {
    active,
    resolved,
    criticalCount: active.filter((a) => a.severity === "critical").length,
    warningCount:  active.filter((a) => a.severity === "warning").length,
    error,
    isLoading,
    mutate,
  };
}

// ---------------------------------------------------------------------------
// İstatistik kartı
// ---------------------------------------------------------------------------

interface StatCardProps {
  label: string;
  value: number;
  color: string;
}

function StatCard({ label, value, color }: StatCardProps) {
  return (
    <div className="flex flex-col gap-1 rounded-xl border border-slate-200 bg-white px-5 py-4 shadow-sm">
      <span className="text-xs font-medium text-slate-500">{label}</span>
      <span className={cn("text-2xl font-bold tabular-nums", color)}>{value}</span>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Loading iskeleti
// ---------------------------------------------------------------------------

function AlertSkeleton() {
  return (
    <div className="flex flex-col gap-3 rounded-xl border bg-white p-4 shadow-sm animate-pulse">
      <div className="flex gap-2">
        <div className="h-5 w-16 rounded-full bg-slate-200" />
        <div className="h-5 w-14 rounded-md bg-slate-100" />
        <div className="ml-auto h-4 w-24 rounded bg-slate-100" />
      </div>
      <div className="h-4 w-4/5 rounded bg-slate-200" />
      <div className="h-4 w-2/5 rounded bg-slate-100" />
    </div>
  );
}

// ---------------------------------------------------------------------------
// Ana bileşen
// ---------------------------------------------------------------------------

export function AlertList() {
  const { active, resolved, criticalCount, warningCount, isLoading, error, mutate } =
    useAllAlerts();

  const [showResolved, setShowResolved] = useState(false);

  // ---------------------------------------------------------------------------
  // Loading
  // ---------------------------------------------------------------------------
  if (isLoading) {
    return (
      <div className="flex flex-col gap-4">
        <div className="grid grid-cols-3 gap-4">
          {[1, 2, 3].map((i) => (
            <div key={i} className="h-20 animate-pulse rounded-xl border bg-white shadow-sm" />
          ))}
        </div>
        <div className="flex flex-col gap-3">
          {Array.from({ length: 4 }).map((_, i) => <AlertSkeleton key={i} />)}
        </div>
      </div>
    );
  }

  // ---------------------------------------------------------------------------
  // Hata
  // ---------------------------------------------------------------------------
  if (error) {
    return (
      <div className="flex flex-col items-center gap-3 rounded-xl border border-red-200 bg-red-50 py-12 text-center">
        <AlertTriangle size={28} className="text-red-400" />
        <p className="text-sm font-medium text-red-700">Alarm listesi alınamadı</p>
        <button
          onClick={() => mutate()}
          className="inline-flex items-center gap-1.5 rounded-md bg-red-100 px-3 py-1.5 text-xs font-medium text-red-700 hover:bg-red-200 transition-colors"
        >
          <RefreshCw size={12} />
          Tekrar dene
        </button>
      </div>
    );
  }

  // ---------------------------------------------------------------------------
  // Render
  // ---------------------------------------------------------------------------
  return (
    <div className="flex flex-col gap-6">
      {/* İstatistik şeridi */}
      <div className="grid grid-cols-3 gap-4">
        <StatCard
          label="Aktif Alarm"
          value={active.length}
          color={active.length > 0 ? "text-slate-800" : "text-green-600"}
        />
        <StatCard
          label="Kritik"
          value={criticalCount}
          color={criticalCount > 0 ? "text-red-600" : "text-slate-400"}
        />
        <StatCard
          label="Uyarı"
          value={warningCount}
          color={warningCount > 0 ? "text-yellow-600" : "text-slate-400"}
        />
      </div>

      {/* Aktif alarmlar */}
      <section aria-labelledby="active-heading">
        <h2
          id="active-heading"
          className="mb-3 flex items-center gap-2 text-sm font-semibold text-slate-700"
        >
          <AlertTriangle size={15} className="text-red-500" aria-hidden="true" />
          Aktif Alarmlar
          {active.length > 0 && (
            <span className="rounded-full bg-red-100 px-2 py-0.5 text-xs font-medium text-red-700">
              {active.length}
            </span>
          )}
        </h2>

        {active.length === 0 ? (
          <div className="flex flex-col items-center gap-2 rounded-xl border border-dashed border-slate-300 bg-white py-12 text-center">
            <BellOff size={28} className="text-slate-300" />
            <p className="text-sm font-medium text-slate-500">Aktif alarm yok</p>
            <p className="text-xs text-slate-400">Tüm sistemler normal çalışıyor.</p>
          </div>
        ) : (
          <div className="flex flex-col gap-3">
            {active.map((alert) => (
              <AlertCard key={alert.id} alert={alert} onResolved={() => mutate()} />
            ))}
          </div>
        )}
      </section>

      {/* Çözülen alarmlar — katlanabilir */}
      {resolved.length > 0 && (
        <section aria-labelledby="resolved-heading">
          <button
            onClick={() => setShowResolved((v) => !v)}
            id="resolved-heading"
            className="mb-3 flex w-full items-center gap-2 text-left text-sm font-semibold text-slate-500 hover:text-slate-700 transition-colors"
            aria-expanded={showResolved}
          >
            {showResolved ? (
              <ChevronUp size={15} aria-hidden="true" />
            ) : (
              <ChevronDown size={15} aria-hidden="true" />
            )}
            Çözülmüş Alarmlar
            <span className="rounded-full bg-slate-100 px-2 py-0.5 text-xs font-medium text-slate-500">
              {resolved.length}
            </span>
          </button>

          {showResolved && (
            <div className="flex flex-col gap-3">
              {resolved.map((alert) => (
                <AlertCard key={alert.id} alert={alert} onResolved={() => mutate()} />
              ))}
            </div>
          )}
        </section>
      )}
    </div>
  );
}
