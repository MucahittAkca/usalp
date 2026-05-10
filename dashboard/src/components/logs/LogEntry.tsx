import { cn, formatTime, LOG_LEVEL_COLORS } from "@/lib/utils";
import type { LogEntry as LogEntryType } from "@/types/api";

interface LogEntryProps {
  log: LogEntryType;
  /** Satır yüksekliği ve konumunu belirleyen sanal scroll stili */
  style?: React.CSSProperties;
}

/**
 * Tek bir log satırı.
 * Sanal scroll içinde kullanılmak üzere `style` prop'unu doğrudan kök elemana uygular.
 */
export function LogEntry({ log, style }: LogEntryProps) {
  const levelColor =
    LOG_LEVEL_COLORS[log.level as keyof typeof LOG_LEVEL_COLORS] ?? "text-slate-500";

  return (
    <div
      style={style}
      className="flex items-baseline gap-3 border-b border-slate-50 px-4 py-1.5 font-mono text-xs hover:bg-slate-50"
      role="row"
    >
      {/* Zaman damgası */}
      <span className="w-14 shrink-0 text-slate-400" aria-label="Zaman">
        {formatTime(log.logged_at)}
      </span>

      {/* Seviye etiketi */}
      <span
        className={cn("w-16 shrink-0 font-semibold uppercase", levelColor)}
        aria-label={`Seviye: ${log.level}`}
      >
        {log.level}
      </span>

      {/* Kaynak dosya */}
      <span
        className="w-32 shrink-0 truncate text-slate-400"
        title={log.source_file}
        aria-label={`Kaynak: ${log.source_file}`}
      >
        {log.source_file.split("/").pop()}
      </span>

      {/* Mesaj */}
      <span className="min-w-0 flex-1 break-words text-slate-700">{log.message}</span>
    </div>
  );
}
