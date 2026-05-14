import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

/** Tailwind sınıflarını clsx + twMerge ile birleştirir. */
export function cn(...inputs: ClassValue[]): string {
  return twMerge(clsx(inputs));
}

/**
 * Byte değerini okunabilir formata çevirir.
 * @example formatBytes(1536) → "1.5 KB"
 */
export function formatBytes(bytes: number): string {
  if (bytes === 0) return "0 B";
  const units = ["B", "KB", "MB", "GB", "TB"];
  const i = Math.floor(Math.log(bytes) / Math.log(1024));
  const value = bytes / Math.pow(1024, i);
  return `${value % 1 === 0 ? value : value.toFixed(1)} ${units[i]}`;
}

/**
 * Saniye cinsinden süreyi okunabilir formata çevirir.
 * @example formatDuration(3661) → "1s 1d"  →  "1g 1sa"
 */
export function formatDuration(seconds: number): string {
  if (seconds < 60) return `${seconds}sn`;
  if (seconds < 3600) return `${Math.floor(seconds / 60)}dk`;
  if (seconds < 86400) return `${Math.floor(seconds / 3600)}sa`;
  return `${Math.floor(seconds / 86400)}g`;
}

/**
 * ISO tarih stringini TR locale'de kısa tarih+saat formatına çevirir.
 * @example formatDateTime("2026-04-28T10:30:00Z") → "28 Nis 10:30"
 */
export function formatDateTime(iso: string): string {
  return new Date(iso).toLocaleString("tr-TR", {
    day: "numeric",
    month: "short",
    hour: "2-digit",
    minute: "2-digit",
    timeZone: "Europe/Istanbul",
  });
}

/**
 * ISO tarih stringini TR locale'de saat formatına çevirir.
 * @example formatTime("2026-04-28T10:30:00Z") → "13:30"
 */
export function formatTime(iso: string): string {
  return new Date(iso).toLocaleTimeString("tr-TR", {
    hour: "2-digit",
    minute: "2-digit",
    timeZone: "Europe/Istanbul",
  });
}

// ---------------------------------------------------------------------------
// Renk & durum sabitleri
// ---------------------------------------------------------------------------

export const SERVER_STATUS_COLORS = {
  online:  "text-green-700 bg-green-100 border-green-200",
  offline: "text-slate-600 bg-slate-100 border-slate-200",
  warning: "text-yellow-700 bg-yellow-100 border-yellow-200",
} as const;

export const SERVER_STATUS_LABELS = {
  online:  "Çevrimiçi",
  offline: "Çevrimdışı",
  warning: "Uyarı",
} as const;

export const SERVER_ENVIRONMENT_LABELS: Record<string, string> = {
  production: "Prod",
  staging: "Stage",
  development: "Dev",
  test: "Test",
};

export const SERVER_ENVIRONMENT_COLORS: Record<string, string> = {
  production: "border-red-200 bg-red-50 text-red-700",
  staging: "border-amber-200 bg-amber-50 text-amber-700",
  development: "border-blue-200 bg-blue-50 text-blue-700",
  test: "border-slate-200 bg-slate-50 text-slate-600",
};

export const SEVERITY_COLORS = {
  low:      "text-blue-600 bg-blue-50 border-blue-200",
  medium:   "text-yellow-600 bg-yellow-50 border-yellow-200",
  high:     "text-orange-600 bg-orange-50 border-orange-200",
  critical: "text-red-600 bg-red-50 border-red-200",
} as const;

export const SEVERITY_LABELS = {
  low:      "Düşük",
  medium:   "Orta",
  high:     "Yüksek",
  critical: "Kritik",
} as const;

export const COMMAND_RISK_COLORS = {
  low:    "border-green-200 bg-green-50 text-green-700",
  medium: "border-yellow-200 bg-yellow-50 text-yellow-700",
  high:   "border-red-200 bg-red-50 text-red-700",
} as const;

export const COMMAND_RISK_LABELS = {
  low:    "Düşük Risk",
  medium: "Orta Risk",
  high:   "Yüksek Risk",
} as const;

export const SERVICE_STATUS_COLORS = {
  active:       "text-green-700 bg-green-100",
  inactive:     "text-yellow-700 bg-yellow-100",
  failed:       "text-red-700 bg-red-100",
  activating:   "text-blue-700 bg-blue-100",
  deactivating: "text-slate-600 bg-slate-100",
  reloading:    "text-blue-700 bg-blue-100",
  unknown:      "text-slate-600 bg-slate-100",
} as const;

export const LOG_LEVEL_COLORS = {
  ERROR:    "text-red-600",
  CRITICAL: "text-red-800 font-bold",
  WARNING:  "text-yellow-600",
  INFO:     "text-slate-600",
  DEBUG:    "text-slate-400",
} as const;

/** Metrik yüzdesine göre renk döndürür (warning / critical eşiklerine göre). */
export function metricColor(
  value: number,
  warn = 80,
  crit = 90,
): "text-green-600" | "text-yellow-600" | "text-red-600" {
  if (value >= crit) return "text-red-600";
  if (value >= warn) return "text-yellow-600";
  return "text-green-600";
}

/** Metrik yüzdesine göre progress bar rengi. */
export function metricBarColor(
  value: number,
  warn = 80,
  crit = 90,
): "bg-green-500" | "bg-yellow-500" | "bg-red-500" {
  if (value >= crit) return "bg-red-500";
  if (value >= warn) return "bg-yellow-500";
  return "bg-green-500";
}
