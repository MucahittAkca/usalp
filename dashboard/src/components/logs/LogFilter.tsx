"use client";

import { Search, X } from "lucide-react";
import { cn } from "@/lib/utils";

// ---------------------------------------------------------------------------
// Sabitler
// ---------------------------------------------------------------------------

export const ALL_LOG_LEVELS = ["CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG"] as const;
export type LogLevel = (typeof ALL_LOG_LEVELS)[number];

const LEVEL_COLORS: Record<LogLevel, string> = {
  CRITICAL: "border-red-400 bg-red-100 text-red-800 data-[active=true]:bg-red-500 data-[active=true]:text-white",
  ERROR:    "border-red-300 bg-red-50 text-red-700 data-[active=true]:bg-red-400 data-[active=true]:text-white",
  WARNING:  "border-yellow-300 bg-yellow-50 text-yellow-700 data-[active=true]:bg-yellow-400 data-[active=true]:text-white",
  INFO:     "border-slate-300 bg-slate-50 text-slate-600 data-[active=true]:bg-slate-500 data-[active=true]:text-white",
  DEBUG:    "border-slate-200 bg-slate-50 text-slate-400 data-[active=true]:bg-slate-400 data-[active=true]:text-white",
};

// ---------------------------------------------------------------------------
// Prop tipleri
// ---------------------------------------------------------------------------

interface LogFilterProps {
  selectedLevels: LogLevel[];
  onToggleLevel: (level: LogLevel) => void;
  searchTerm: string;
  onSearchChange: (value: string) => void;
  totalCount: number;
  filteredCount: number;
}

// ---------------------------------------------------------------------------
// Bileşen
// ---------------------------------------------------------------------------

export function LogFilter({
  selectedLevels,
  onToggleLevel,
  searchTerm,
  onSearchChange,
  totalCount,
  filteredCount,
}: LogFilterProps) {
  return (
    <div className="flex flex-col gap-3 rounded-xl border border-slate-200 bg-white px-4 py-3 shadow-sm">
      {/* Üst satır: Level toggle butonları + sayaç */}
      <div className="flex flex-wrap items-center gap-2">
        <span className="text-xs font-medium text-slate-500">Seviye:</span>

        {ALL_LOG_LEVELS.map((level) => {
          const active = selectedLevels.includes(level);
          return (
            <button
              key={level}
              onClick={() => onToggleLevel(level)}
              data-active={active}
              className={cn(
                "rounded-full border px-2.5 py-0.5 text-xs font-medium transition-colors",
                LEVEL_COLORS[level],
              )}
              aria-pressed={active}
              aria-label={`${level} seviyesini ${active ? "kaldır" : "ekle"}`}
            >
              {level}
            </button>
          );
        })}

        <span className="ml-auto text-xs text-slate-400 tabular-nums">
          {filteredCount} / {totalCount} satır
        </span>
      </div>

      {/* Alt satır: Arama */}
      <div className="relative">
        <Search
          size={14}
          className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-slate-400"
          aria-hidden="true"
        />
        <input
          type="search"
          value={searchTerm}
          onChange={(e) => onSearchChange(e.target.value)}
          placeholder="Log mesajlarında ara…"
          className="w-full rounded-lg border border-slate-200 bg-slate-50 py-2 pl-9 pr-9 text-xs text-slate-800 placeholder-slate-400 outline-none focus:border-brand-500 focus:ring-1 focus:ring-brand-500"
          aria-label="Log mesajı arama"
        />
        {searchTerm && (
          <button
            onClick={() => onSearchChange("")}
            className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600"
            aria-label="Aramayı temizle"
          >
            <X size={14} />
          </button>
        )}
      </div>
    </div>
  );
}
