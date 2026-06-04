"use client";

import {
  Area,
  AreaChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
  type TooltipContentProps,
} from "recharts";
import { formatTime } from "@/lib/utils";
import type { Metric } from "@/types/api";

// ---------------------------------------------------------------------------
// Sabitler
// ---------------------------------------------------------------------------

type MetricKey = "cpu_percent" | "ram_percent" | "disk_percent";

const CHART_CONFIG: Record<
  MetricKey,
  { label: string; color: string; gradientId: string; warn: number; crit: number }
> = {
  cpu_percent: {
    label: "CPU",
    color: "#3b82f6",   // blue-500
    gradientId: "colorCpu",
    warn: 80,
    crit: 90,
  },
  ram_percent: {
    label: "RAM",
    color: "#a855f7",   // purple-500
    gradientId: "colorRam",
    warn: 85,
    crit: 95,
  },
  disk_percent: {
    label: "Disk",
    color: "#f97316",   // orange-500
    gradientId: "colorDisk",
    warn: 85,
    crit: 95,
  },
};

// ---------------------------------------------------------------------------
// Özel tooltip
// ---------------------------------------------------------------------------

function CustomTooltip({ active, payload, label }: TooltipContentProps) {
  if (!active || !payload?.length) return null;

  return (
    <div className="rounded-lg border border-slate-200 bg-white px-3 py-2 shadow-md">
      <p className="mb-1 text-xs text-slate-400">{formatTime(label as string)}</p>
      {payload.map((entry) => (
        <p key={String(entry.name)} className="text-xs font-medium" style={{ color: entry.color }}>
          {entry.name}: %{Number(entry.value).toFixed(1)}
        </p>
      ))}
    </div>
  );
}

// ---------------------------------------------------------------------------
// MetricChart
// ---------------------------------------------------------------------------

interface MetricChartProps {
  /** Metrik dizisi — recorded_at'e göre sıralı (asc) olmalı */
  data: Metric[];
  /** Hangi metrik gösterilecek */
  metricKey: MetricKey;
  /** Grafik yüksekliği (px) */
  height?: number;
}

export function MetricChart({ data, metricKey, height = 200 }: MetricChartProps) {
  const cfg = CHART_CONFIG[metricKey];

  // API desc döndürür, grafik için asc sıraya çevir
  const sorted = [...data].reverse();

  return (
    <div aria-label={`${cfg.label} kullanım grafiği`}>
      <ResponsiveContainer width="100%" height={height}>
        <AreaChart
          data={sorted}
          margin={{ top: 4, right: 4, left: -20, bottom: 0 }}
        >
          <defs>
            <linearGradient id={cfg.gradientId} x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%"  stopColor={cfg.color} stopOpacity={0.25} />
              <stop offset="95%" stopColor={cfg.color} stopOpacity={0} />
            </linearGradient>
          </defs>

          <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" vertical={false} />

          <XAxis
            dataKey="recorded_at"
            tickFormatter={(v) => formatTime(v as string)}
            tick={{ fontSize: 11, fill: "#94a3b8" }}
            tickLine={false}
            axisLine={false}
            minTickGap={40}
          />

          <YAxis
            domain={[0, 100]}
            unit="%"
            tick={{ fontSize: 11, fill: "#94a3b8" }}
            tickLine={false}
            axisLine={false}
            width={38}
          />

          <Tooltip content={CustomTooltip} />

          {/* Uyarı eşiği referans çizgisi */}
          <Area
            type="monotone"
            dataKey={metricKey}
            name={cfg.label}
            stroke={cfg.color}
            strokeWidth={2}
            fill={`url(#${cfg.gradientId})`}
            dot={false}
            activeDot={{ r: 4, strokeWidth: 0 }}
            isAnimationActive={false}
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}
