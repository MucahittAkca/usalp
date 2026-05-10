import { cn } from "@/lib/utils";

interface ConfidenceBarProps {
  /** 0.0 – 1.0 arası güven skoru */
  value: number;
  className?: string;
}

function barColor(v: number): string {
  if (v >= 0.8) return "bg-green-500";
  if (v >= 0.5) return "bg-yellow-500";
  return "bg-red-400";
}

function labelColor(v: number): string {
  if (v >= 0.8) return "text-green-700";
  if (v >= 0.5) return "text-yellow-700";
  return "text-red-600";
}

function confidenceLabel(v: number): string {
  if (v >= 0.8) return "Yüksek güven";
  if (v >= 0.5) return "Orta güven";
  return "Düşük güven";
}

export function ConfidenceBar({ value, className }: ConfidenceBarProps) {
  const pct = Math.round(value * 100);

  return (
    <div className={cn("flex flex-col gap-1.5", className)}>
      <div className="flex items-center justify-between text-xs">
        <span className="font-medium text-slate-500">Güven Skoru</span>
        <span className={cn("font-semibold tabular-nums", labelColor(value))}>
          %{pct} — {confidenceLabel(value)}
        </span>
      </div>

      <div
        className="h-2 w-full overflow-hidden rounded-full bg-slate-100"
        role="progressbar"
        aria-valuenow={pct}
        aria-valuemin={0}
        aria-valuemax={100}
        aria-label={`Güven skoru %${pct}`}
      >
        <div
          className={cn("h-full rounded-full transition-all duration-500", barColor(value))}
          style={{ width: `${pct}%` }}
        />
      </div>
    </div>
  );
}
