"use client";

import { CheckCircle2, RefreshCw, XCircle } from "lucide-react";
import { useServerServices } from "@/hooks/useServerServices";
import { ServiceStatusBadge } from "@/components/services/ServiceStatusBadge";
import { formatDuration, formatDateTime } from "@/lib/utils";
import type { ServiceStatusEntry } from "@/types/api";

// ---------------------------------------------------------------------------
// Tek servis satırı
// ---------------------------------------------------------------------------

interface ServiceRowProps {
  service: ServiceStatusEntry;
}

function ServiceRow({ service }: ServiceRowProps) {
  const isFailed = service.status === "failed";

  return (
    <li className="flex items-center gap-3 px-4 py-3">
      {/* Durum ikonu */}
      <div className="shrink-0">
        {isFailed ? (
          <XCircle size={16} className="text-red-500" aria-hidden="true" />
        ) : service.status === "active" ? (
          <CheckCircle2 size={16} className="text-green-500" aria-hidden="true" />
        ) : (
          <RefreshCw size={16} className="text-slate-400" aria-hidden="true" />
        )}
      </div>

      {/* İsim + sub_state */}
      <div className="min-w-0 flex-1">
        <p className="truncate text-sm font-medium text-slate-800">
          {service.service_name}
        </p>
        {service.status !== "active" && (
          <p className="truncate text-xs text-slate-400">
            {service.status === "failed"
              ? `Kontrol: ${formatDateTime(service.checked_at)}`
              : service.status}
          </p>
        )}
      </div>

      {/* Badge */}
      <ServiceStatusBadge status={service.status} className="shrink-0" />
    </li>
  );
}

// ---------------------------------------------------------------------------
// Loading iskeleti
// ---------------------------------------------------------------------------

function SkeletonRow() {
  return (
    <li className="flex items-center gap-3 px-4 py-3 animate-pulse">
      <div className="h-4 w-4 rounded-full bg-slate-200 shrink-0" />
      <div className="flex-1 space-y-1.5">
        <div className="h-3.5 w-32 rounded bg-slate-200" />
        <div className="h-2.5 w-20 rounded bg-slate-100" />
      </div>
      <div className="h-5 w-16 rounded-full bg-slate-200 shrink-0" />
    </li>
  );
}

// ---------------------------------------------------------------------------
// Ana bileşen
// ---------------------------------------------------------------------------

interface ServiceListProps {
  serverId: number;
}

export function ServiceList({ serverId }: ServiceListProps) {
  const { services, failedCount, isLoading, error, mutate } = useServerServices(serverId);

  if (isLoading) {
    return (
      <div className="rounded-xl border border-slate-200 bg-white shadow-sm">
        <ul className="divide-y divide-slate-100">
          {Array.from({ length: 6 }).map((_, i) => <SkeletonRow key={i} />)}
        </ul>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex flex-col items-center gap-3 rounded-xl border border-red-200 bg-red-50 py-10 text-center">
        <p className="text-sm font-medium text-red-700">Servis listesi alınamadı</p>
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

  if (services.length === 0) {
    return (
      <div className="rounded-xl border border-dashed border-slate-300 bg-white py-12 text-center">
        <p className="text-sm text-slate-400">Servis verisi bulunamadı</p>
      </div>
    );
  }

  // Failed servisler önce
  const failed  = services.filter((s) => s.status === "failed");
  const others  = services.filter((s) => s.status !== "failed");
  const sorted  = [...failed, ...others];

  return (
    <div className="rounded-xl border border-slate-200 bg-white shadow-sm">
      {/* Başlık */}
      <div className="flex items-center justify-between border-b border-slate-100 px-4 py-3">
        <h3 className="text-sm font-semibold text-slate-700">
          Servis Durumları
          <span className="ml-2 text-xs font-normal text-slate-400">
            ({services.length} servis)
          </span>
        </h3>
        {failedCount > 0 && (
          <span className="inline-flex items-center gap-1 rounded-full bg-red-100 px-2.5 py-0.5 text-xs font-medium text-red-700">
            <XCircle size={11} aria-hidden="true" />
            {failedCount} başarısız
          </span>
        )}
      </div>

      <ul className="divide-y divide-slate-50" role="list" aria-label="Servis listesi">
        {sorted.map((service) => (
          <ServiceRow key={`${service.id}-${service.service_name}`} service={service} />
        ))}
      </ul>
    </div>
  );
}
