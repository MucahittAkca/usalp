import { Circle } from "lucide-react";
import { cn, SERVER_STATUS_COLORS, SERVER_STATUS_LABELS } from "@/lib/utils";
import type { ServerStatus } from "@/types/api";

interface ServerStatusBadgeProps {
  status: ServerStatus;
  className?: string;
}

export function ServerStatusBadge({ status, className }: ServerStatusBadgeProps) {
  const color =
    SERVER_STATUS_COLORS[status] ?? "text-slate-600 bg-slate-100 border-slate-200";
  const label = SERVER_STATUS_LABELS[status] ?? status;

  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 rounded-full border px-2.5 py-0.5 text-xs font-medium",
        color,
        className,
      )}
    >
      <Circle
        size={6}
        className="fill-current"
        aria-hidden="true"
      />
      {label}
    </span>
  );
}
