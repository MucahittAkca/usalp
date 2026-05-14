"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { useVirtualizer } from "@tanstack/react-virtual";
import { RefreshCw, ScrollText } from "lucide-react";
import { useServerLogs } from "@/hooks/useServerLogs";
import { LogEntry } from "@/components/logs/LogEntry";
import {
  LogFilter,
  ALL_LOG_LEVELS,
  type LogLevel,
} from "@/components/logs/LogFilter";

// ---------------------------------------------------------------------------
// Sabitler
// ---------------------------------------------------------------------------

/** Her log satırının tahmini piksel yüksekliği (virtual scroll için) */
const ROW_HEIGHT = 32;

/** Ekranda gösterilecek maksimum yükseklik */
const VIEWER_HEIGHT = 480;

function useDebouncedValue(value: string, delayMs: number): string {
  const [debounced, setDebounced] = useState(value);

  useEffect(() => {
    const timer = setTimeout(() => setDebounced(value), delayMs);
    return () => clearTimeout(timer);
  }, [value, delayMs]);

  return debounced;
}

// ---------------------------------------------------------------------------
// Loading iskeleti
// ---------------------------------------------------------------------------

function LogSkeleton() {
  return (
    <div className="flex flex-col gap-2 p-4 animate-pulse">
      {Array.from({ length: 10 }).map((_, i) => (
        <div key={i} className="flex gap-3">
          <div className="h-3 w-14 rounded bg-slate-200" />
          <div className="h-3 w-14 rounded bg-slate-200" />
          <div className="h-3 w-24 rounded bg-slate-100" />
          <div className="h-3 flex-1 rounded bg-slate-100" style={{ maxWidth: `${50 + (i % 5) * 10}%` }} />
        </div>
      ))}
    </div>
  );
}

// ---------------------------------------------------------------------------
// LogViewer
// ---------------------------------------------------------------------------

interface LogViewerProps {
  serverId: number;
}

export function LogViewer({ serverId }: LogViewerProps) {
  const [selectedLevels, setSelectedLevels] = useState<LogLevel[]>([
    ...ALL_LOG_LEVELS,
  ]);
  const [searchTerm, setSearchTerm] = useState("");
  const debouncedSearch = useDebouncedValue(searchTerm.trim(), 300);
  const backendLevel = selectedLevels.length === 1 ? selectedLevels[0] : undefined;

  const { logs, total, isLoading, error, mutate } = useServerLogs(serverId, {
    level: backendLevel,
    q: debouncedSearch || undefined,
    perPage: 200,
  });

  // ---------------------------------------------------------------------------
  // Çoklu seviye filtresi UI tarafında uygulanır; metin araması backend'dedir.
  // ---------------------------------------------------------------------------
  const filtered = useMemo(() => {
    return logs.filter((log) => {
      const levelMatch = selectedLevels.includes(log.level as LogLevel);
      return levelMatch;
    });
  }, [logs, selectedLevels]);

  // ---------------------------------------------------------------------------
  // Level toggle
  // ---------------------------------------------------------------------------
  function handleToggleLevel(level: LogLevel) {
    setSelectedLevels((prev) =>
      prev.includes(level) ? prev.filter((l) => l !== level) : [...prev, level],
    );
  }

  // ---------------------------------------------------------------------------
  // Sanal scroll
  // ---------------------------------------------------------------------------
  const parentRef = useRef<HTMLDivElement>(null);

  const virtualizer = useVirtualizer({
    count: filtered.length,
    getScrollElement: () => parentRef.current,
    estimateSize: () => ROW_HEIGHT,
    overscan: 10,
  });

  const virtualItems = virtualizer.getVirtualItems();

  // ---------------------------------------------------------------------------
  // Render
  // ---------------------------------------------------------------------------
  return (
    <div className="flex flex-col gap-3">
      {/* Filtre çubuğu */}
      <LogFilter
        selectedLevels={selectedLevels}
        onToggleLevel={handleToggleLevel}
        searchTerm={searchTerm}
        onSearchChange={setSearchTerm}
        totalCount={total}
        filteredCount={filtered.length}
      />

      {/* Log listesi */}
      <div className="overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm">
        {/* Kolon başlıkları */}
        <div className="flex items-center gap-3 border-b border-slate-200 bg-slate-50 px-4 py-2 font-mono text-[10px] font-semibold uppercase tracking-wide text-slate-400">
          <span className="w-14 shrink-0">Saat</span>
          <span className="w-16 shrink-0">Seviye</span>
          <span className="w-32 shrink-0">Dosya</span>
          <span className="flex-1">Mesaj</span>
        </div>

        {/* İçerik alanı */}
        {isLoading ? (
          <LogSkeleton />
        ) : error ? (
          <div className="flex flex-col items-center gap-3 py-10 text-center">
            <p className="text-sm font-medium text-red-700">Log verileri alınamadı</p>
            <button
              onClick={() => mutate()}
              className="inline-flex items-center gap-1.5 rounded-md bg-red-50 px-3 py-1.5 text-xs font-medium text-red-700 hover:bg-red-100 transition-colors"
            >
              <RefreshCw size={12} />
              Tekrar dene
            </button>
          </div>
        ) : filtered.length === 0 ? (
          <div className="flex flex-col items-center gap-2 py-12 text-center">
            <ScrollText size={28} className="text-slate-300" />
            <p className="text-sm text-slate-400">
              {logs.length === 0
                ? "Henüz log kaydı bulunmuyor"
                : "Seçili filtrelere uygun log yok"}
            </p>
          </div>
        ) : (
          /* Sanal scroll kapsayıcı */
          <div
            ref={parentRef}
            style={{ height: VIEWER_HEIGHT, overflowY: "auto" }}
            role="log"
            aria-label="Log kayıtları"
            aria-live="polite"
          >
            <div
              style={{ height: virtualizer.getTotalSize(), position: "relative" }}
            >
              {virtualItems.map((vItem) => (
                <LogEntry
                  key={filtered[vItem.index].id}
                  log={filtered[vItem.index]}
                  style={{
                    position: "absolute",
                    top: 0,
                    left: 0,
                    width: "100%",
                    transform: `translateY(${vItem.start}px)`,
                  }}
                />
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
