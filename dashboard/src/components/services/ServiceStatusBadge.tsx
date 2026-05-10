import { cn, SERVICE_STATUS_COLORS } from "@/lib/utils";
import type { ServiceStatus } from "@/types/api";

const LABELS: Record<ServiceStatus, string> = {
  active:       "Aktif",
  inactive:     "Pasif",
  failed:       "Başarısız",
  activating:   "Başlatılıyor",
  deactivating: "Durduruluyor",
  reloading:    "Yenileniyor",
  unknown:      "Bilinmiyor",
};

interface ServiceStatusBadgeProps {
  status: ServiceStatus;
  className?: string;
}

export function ServiceStatusBadge({ status, className }: ServiceStatusBadgeProps) {
  const color = SERVICE_STATUS_COLORS[status] ?? SERVICE_STATUS_COLORS.unknown;
  const label = LABELS[status] ?? status;

  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium",
        color,
        className,
      )}
    >
      {label}
    </span>
  );
}
