import { AlertTriangle, Cpu, HardDrive, MemoryStick, ScrollText, Server, type LucideIcon } from "lucide-react";
import { cn } from "@/lib/utils";
import type { AlertSeverity, AlertType } from "@/types/api";

// ---------------------------------------------------------------------------
// Severity badge
// ---------------------------------------------------------------------------

const SEVERITY_STYLES: Record<AlertSeverity, string> = {
  warning:  "text-yellow-700 bg-yellow-100 border-yellow-200",
  critical: "text-red-700 bg-red-100 border-red-200",
};

const SEVERITY_LABELS: Record<AlertSeverity, string> = {
  warning:  "Uyarı",
  critical: "Kritik",
};

interface AlertSeverityBadgeProps {
  severity: AlertSeverity;
  className?: string;
}

export function AlertSeverityBadge({ severity, className }: AlertSeverityBadgeProps) {
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1 rounded-full border px-2.5 py-0.5 text-xs font-semibold",
        SEVERITY_STYLES[severity],
        className,
      )}
    >
      <AlertTriangle size={11} aria-hidden="true" />
      {SEVERITY_LABELS[severity]}
    </span>
  );
}

// ---------------------------------------------------------------------------
// Type badge — alarm türünü ikonla gösterir
// ---------------------------------------------------------------------------

const TYPE_META: Record<AlertType, { label: string; Icon: LucideIcon }> = {
  cpu_threshold:  { label: "CPU",       Icon: Cpu },
  ram_threshold:  { label: "RAM",       Icon: MemoryStick },
  disk_threshold: { label: "Disk",      Icon: HardDrive },
  service_failed:      { label: "Servis",     Icon: Server },
  critical_log_burst:  { label: "Kritik Log", Icon: ScrollText },
};

interface AlertTypeBadgeProps {
  type: AlertType;
  className?: string;
}

export function AlertTypeBadge({ type, className }: AlertTypeBadgeProps) {
  const meta = TYPE_META[type] ?? { label: type, Icon: ScrollText };
  const { Icon } = meta;

  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 rounded-md bg-slate-100 px-2 py-0.5 text-xs font-medium text-slate-600",
        className,
      )}
    >
      <Icon size={11} aria-hidden="true" />
      {meta.label}
    </span>
  );
}
