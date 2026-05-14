"use client";

import { useState } from "react";
import { Filter, RefreshCw, RotateCcw, ServerOff } from "lucide-react";
import { useServerList, type ServerListFilters } from "@/hooks/useServerList";
import { ServerCard } from "@/components/servers/ServerCard";

// ---------------------------------------------------------------------------
// Loading skeleton
// ---------------------------------------------------------------------------

function SkeletonCard() {
  return (
    <div className="flex flex-col gap-4 rounded-xl border bg-white p-5 shadow-sm animate-pulse">
      <div className="flex items-start justify-between">
        <div className="flex items-center gap-3">
          <div className="h-9 w-9 rounded-lg bg-slate-200" />
          <div className="space-y-1.5">
            <div className="h-3.5 w-28 rounded bg-slate-200" />
            <div className="h-2.5 w-20 rounded bg-slate-100" />
          </div>
        </div>
        <div className="h-5 w-20 rounded-full bg-slate-200" />
      </div>
      <div className="h-2.5 w-24 rounded bg-slate-100" />
      <div className="space-y-2">
        {[1, 2, 3].map((i) => (
          <div key={i} className="flex items-center gap-2">
            <div className="h-2.5 w-10 rounded bg-slate-100" />
            <div className="h-1.5 flex-1 rounded-full bg-slate-100" />
            <div className="h-2.5 w-10 rounded bg-slate-100" />
          </div>
        ))}
      </div>
      <div className="flex items-center justify-between pt-1">
        <div className="h-5 w-20 rounded-full bg-slate-100" />
        <div className="h-4 w-4 rounded bg-slate-100" />
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Boş durum
// ---------------------------------------------------------------------------

function EmptyState() {
  return (
    <div className="col-span-full flex flex-col items-center justify-center rounded-xl border border-dashed border-slate-300 bg-white py-16 text-center">
      <ServerOff size={36} className="mb-3 text-slate-300" />
      <p className="text-sm font-medium text-slate-600">Kayıtlı sunucu bulunamadı</p>
      <p className="mt-1 text-xs text-slate-400">
        Agent çalıştırın ve sunucunuzu sisteme ekleyin.
      </p>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Hata durumu
// ---------------------------------------------------------------------------

function ErrorState({ onRetry }: { onRetry: () => void }) {
  return (
    <div className="col-span-full flex flex-col items-center justify-center rounded-xl border border-red-200 bg-red-50 py-12 text-center">
      <p className="text-sm font-medium text-red-700">Sunucu listesi alınamadı</p>
      <p className="mt-1 text-xs text-red-500">
          Backend&apos;e bağlanılamıyor. Bağlantıyı kontrol edin.
      </p>
      <button
        onClick={onRetry}
        className="mt-4 inline-flex items-center gap-1.5 rounded-md bg-red-100 px-3 py-1.5 text-xs font-medium text-red-700 hover:bg-red-200 transition-colors"
      >
        <RefreshCw size={12} />
        Tekrar dene
      </button>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Ana bileşen
// ---------------------------------------------------------------------------

interface ServerListProps {
  showFilters?: boolean;
}

function hasFilters(filters: ServerListFilters): boolean {
  return Boolean(filters.environment || filters.group_name || filters.tag);
}

function ServerFilters({
  filters,
  setFilters,
}: {
  filters: ServerListFilters;
  setFilters: React.Dispatch<React.SetStateAction<ServerListFilters>>;
}) {
  const active = hasFilters(filters);

  return (
    <div className="flex flex-wrap items-end gap-3 rounded-lg border border-slate-200 bg-white px-4 py-3">
      <div className="flex items-center gap-2 text-sm font-medium text-slate-700">
        <Filter size={15} className="text-slate-400" />
        Filtreler
      </div>

      <label className="flex flex-col gap-1">
        <span className="text-xs font-medium text-slate-500">Ortam</span>
        <select
          value={filters.environment ?? ""}
          onChange={(e) =>
            setFilters((current) => ({
              ...current,
              environment: e.target.value || undefined,
            }))
          }
          className="h-9 min-w-36 rounded-md border border-slate-200 px-2 text-sm text-slate-700 focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
        >
          <option value="">Tümü</option>
          <option value="production">Production</option>
          <option value="staging">Staging</option>
          <option value="development">Development</option>
          <option value="test">Test</option>
        </select>
      </label>

      <label className="flex flex-col gap-1">
        <span className="text-xs font-medium text-slate-500">Grup</span>
        <input
          value={filters.group_name ?? ""}
          onChange={(e) =>
            setFilters((current) => ({
              ...current,
              group_name: e.target.value.trim() || undefined,
            }))
          }
          placeholder="edge"
          className="h-9 w-36 rounded-md border border-slate-200 px-2 text-sm text-slate-700 placeholder:text-slate-400 focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
        />
      </label>

      <label className="flex flex-col gap-1">
        <span className="text-xs font-medium text-slate-500">Etiket</span>
        <input
          value={filters.tag ?? ""}
          onChange={(e) =>
            setFilters((current) => ({
              ...current,
              tag: e.target.value.trim() || undefined,
            }))
          }
          placeholder="nginx"
          className="h-9 w-36 rounded-md border border-slate-200 px-2 text-sm text-slate-700 placeholder:text-slate-400 focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
        />
      </label>

      <button
        type="button"
        onClick={() => setFilters({})}
        disabled={!active}
        className="inline-flex h-9 items-center gap-1.5 rounded-md bg-slate-100 px-3 text-xs font-medium text-slate-600 hover:bg-slate-200 disabled:opacity-40"
      >
        <RotateCcw size={13} />
        Sıfırla
      </button>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Ana bileşen
// ---------------------------------------------------------------------------

export function ServerList({ showFilters = false }: ServerListProps) {
  const [filters, setFilters] = useState<ServerListFilters>({});
  const { servers, isLoading, error, mutate } = useServerList(showFilters ? filters : undefined);

  return (
    <div className="flex flex-col gap-4">
      {showFilters && <ServerFilters filters={filters} setFilters={setFilters} />}

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {isLoading &&
          Array.from({ length: 6 }).map((_, i) => <SkeletonCard key={i} />)}

        {error && !isLoading && <ErrorState onRetry={() => mutate()} />}

        {!isLoading && !error && servers.length === 0 && <EmptyState />}

        {!isLoading &&
          !error &&
          servers.map((server) => (
            <ServerCard key={server.id} server={server} />
          ))}
      </div>
    </div>
  );
}
