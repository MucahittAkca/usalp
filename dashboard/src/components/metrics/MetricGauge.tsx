"use client";

import { PolarAngleAxis, RadialBar, RadialBarChart, ResponsiveContainer } from "recharts";
import { cn } from "@/lib/utils";

// ---------------------------------------------------------------------------
// Sabitler
// ---------------------------------------------------------------------------

/** Metrik türü bazında eşikler */
const THRESHOLDS: Record<string, { warn: number; crit: number }> = {
  cpu:  { warn: 80, crit: 90 },
  ram:  { warn: 85, crit: 95 },
  disk: { warn: 85, crit: 95 },
};

function getColor(value: number, warn: number, crit: number): string {
  if (value >= crit) return "#ef4444"; // red-500
  if (value >= warn) return "#eab308"; // yellow-500
  return "#22c55e";                    // green-500
}

function getTextColor(value: number, warn: number, crit: number): string {
  if (value >= crit) return "text-red-600";
  if (value >= warn) return "text-yellow-600";
  return "text-green-600";
}

// ---------------------------------------------------------------------------
// MetricGauge
// ---------------------------------------------------------------------------

interface MetricGaugeProps {
  /** Gösterilecek yüzde değeri (0–100) */
  value: number;
  /** Kart başlığı (CPU, RAM, Disk vb.) */
  label: string;
  /**
   * Eşik tipi — varsayılan eşikleri seçmek için anahtar.
   * Sağlanmazsa cpu eşikleri kullanılır.
   */
  thresholdKey?: "cpu" | "ram" | "disk";
  /** Gauge yüksekliği/genişliği (px) */
  size?: number;
}

export function MetricGauge({
  value,
  label,
  thresholdKey = "cpu",
  size = 120,
}: MetricGaugeProps) {
  const { warn, crit } = THRESHOLDS[thresholdKey];
  const fill = getColor(value, warn, crit);
  const textColor = getTextColor(value, warn, crit);

  const chartData = [{ value, fill }];

  return (
    <div className="flex flex-col items-center gap-1">
      <div style={{ width: size, height: size }} className="relative">
        <ResponsiveContainer width="100%" height="100%">
          <RadialBarChart
            cx="50%"
            cy="50%"
            innerRadius="72%"
            outerRadius="100%"
            barSize={10}
            data={chartData}
            startAngle={220}
            endAngle={-40}
          >
            {/* Arka plan halkası */}
            <RadialBar
              dataKey="value"
              cornerRadius={6}
              background={{ fill: "#f1f5f9" }}
              isAnimationActive={false}
            />
            <PolarAngleAxis
              type="number"
              domain={[0, 100]}
              angleAxisId={0}
              tick={false}
            />
          </RadialBarChart>
        </ResponsiveContainer>

        {/* Merkez yüzde etiketi */}
        <div className="absolute inset-0 flex flex-col items-center justify-center">
          <span
            className={cn("text-xl font-bold tabular-nums leading-none", textColor)}
            aria-label={`${label} ${value.toFixed(0)} yüzde`}
          >
            {value.toFixed(0)}
            <span className="text-sm font-normal">%</span>
          </span>
        </div>
      </div>

      <span className="text-xs font-medium text-slate-500">{label}</span>
    </div>
  );
}
