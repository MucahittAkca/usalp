"use client";

import Link from "next/link";
import { AlertTriangle, ArrowRight, Boxes, Globe, Server, Tag } from "lucide-react";
import {
  SERVER_ENVIRONMENT_COLORS,
  SERVER_ENVIRONMENT_LABELS,
  cn,
  metricBarColor,
  metricColor,
} from "@/lib/utils";
import { useLatestMetric } from "@/hooks/useServerMetrics";
import { useAlerts } from "@/hooks/useAlerts";
import { ServerStatusBadge } from "@/components/servers/ServerStatusBadge";
import type { Server as ServerType } from "@/types/api";

interface ServerCardProps {
  server: ServerType;
}

// ---------------------------------------------------------------------------
// Mini metric row — yüzde çubuğu + değer
// ---------------------------------------------------------------------------

interface MetricRowProps {
  label: string;
  value: number;
  warn?: number;
  crit?: number;
}

function MetricRow({ label, value, warn = 80, crit = 90 }: MetricRowProps) {
  const bar = metricBarColor(value, warn, crit);
  const text = metricColor(value, warn, crit);

  return (
    <div className="flex items-center gap-2">
      <span className="w-10 shrink-0 text-xs text-slate-500">{label}</span>
      <div className="flex-1 overflow-hidden rounded-full bg-slate-100 h-1.5">
        <div
          className={cn("h-full rounded-full transition-all", bar)}
          style={{ width: `${Math.min(value, 100)}%` }}
          role="progressbar"
          aria-valuenow={value}
          aria-valuemin={0}
          aria-valuemax={100}
          aria-label={`${label} %${value.toFixed(0)}`}
        />
      </div>
      <span className={cn("w-10 text-right text-xs font-medium tabular-nums", text)}>
        %{value.toFixed(0)}
      </span>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Metrik bölümü — yükleniyor / hata / veriler
// ---------------------------------------------------------------------------

function MetricsSection({ serverId, offline }: { serverId: number; offline: boolean }) {
  const { metric, isLoading } = useLatestMetric(serverId);

  if (offline) {
    return (
      <p className="text-xs text-slate-400 italic">Sunucu çevrimdışı — metrik alınamıyor</p>
    );
  }

  if (isLoading) {
    return (
      <div className="space-y-2">
        {["CPU", "RAM", "Disk"].map((l) => (
          <div key={l} className="flex items-center gap-2">
            <span className="w-10 text-xs text-slate-400">{l}</span>
            <div className="h-1.5 flex-1 animate-pulse rounded-full bg-slate-200" />
            <span className="w-10" />
          </div>
        ))}
      </div>
    );
  }

  if (!metric) {
    return <p className="text-xs text-slate-400 italic">Henüz metrik verisi yok</p>;
  }

  return (
    <div className="space-y-2">
      <MetricRow label="CPU" value={metric.cpu_percent} />
      <MetricRow label="RAM" value={metric.ram_percent} warn={85} crit={95} />
      <MetricRow label="Disk" value={metric.disk_percent} warn={85} crit={95} />
    </div>
  );
}

// ---------------------------------------------------------------------------
// Ana kart
// ---------------------------------------------------------------------------

export function ServerCard({ server }: ServerCardProps) {
  const offline = server.status === "offline";
  const { activeCount, criticalCount } = useAlerts(server.id);
  const envLabel = SERVER_ENVIRONMENT_LABELS[server.environment] ?? server.environment;
  const envClass =
    SERVER_ENVIRONMENT_COLORS[server.environment] ??
    "border-slate-200 bg-slate-50 text-slate-600";

  return (
    <Link
      href={`/servers/${server.id}`}
      className={cn(
        "group flex flex-col gap-4 rounded-xl border bg-white p-5 shadow-sm",
        "transition-shadow hover:shadow-md focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-500",
        offline && "opacity-60",
      )}
      aria-label={`${server.name} sunucu detayına git`}
    >
      {/* Başlık satırı */}
      <div className="flex items-start justify-between gap-2">
        <div className="flex items-center gap-3 min-w-0">
          <div
            className={cn(
              "flex h-9 w-9 shrink-0 items-center justify-center rounded-lg",
              offline ? "bg-slate-100" : "bg-brand-50",
            )}
          >
            <Server
              size={18}
              className={offline ? "text-slate-400" : "text-brand-600"}
              aria-hidden="true"
            />
          </div>
          <div className="min-w-0">
            <p className="truncate text-sm font-semibold text-slate-900">
              {server.name}
            </p>
            <p className="truncate text-xs text-slate-500">{server.hostname}</p>
          </div>
        </div>
        <ServerStatusBadge status={server.status} className="shrink-0" />
      </div>

      {/* IP adresi */}
      <div className="flex items-center gap-1.5 text-xs text-slate-500">
        <Globe size={12} aria-hidden="true" />
        <span className="font-mono">{server.ip_address}</span>
      </div>

      <div className="flex min-h-6 flex-wrap items-center gap-1.5">
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
            <Boxes size={10} aria-hidden="true" />
            {server.group_name}
          </span>
        )}
        {server.tags.slice(0, 2).map((tag) => (
          <span
            key={tag}
            className="inline-flex items-center gap-1 rounded-full bg-slate-100 px-2 py-0.5 text-[11px] text-slate-500"
          >
            <Tag size={10} aria-hidden="true" />
            {tag}
          </span>
        ))}
        {server.tags.length > 2 && (
          <span className="rounded-full bg-slate-100 px-2 py-0.5 text-[11px] text-slate-400">
            +{server.tags.length - 2}
          </span>
        )}
      </div>

      {/* Metrikler */}
      <MetricsSection serverId={server.id} offline={offline} />

      {/* Alt satır: alarm sayısı + ok */}
      <div className="flex items-center justify-between pt-1">
        {activeCount > 0 ? (
          <span
            className={cn(
              "inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-medium",
              criticalCount > 0
                ? "bg-red-100 text-red-700"
                : "bg-yellow-100 text-yellow-700",
            )}
          >
            <AlertTriangle size={11} aria-hidden="true" />
            {activeCount} aktif alarm
          </span>
        ) : (
          <span className="text-xs text-slate-400">Alarm yok</span>
        )}

        <ArrowRight
          size={15}
          className="text-slate-300 transition-transform group-hover:translate-x-0.5 group-hover:text-brand-500"
          aria-hidden="true"
        />
      </div>
    </Link>
  );
}
