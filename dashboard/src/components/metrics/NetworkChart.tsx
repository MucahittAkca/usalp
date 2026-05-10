"use client";

import {
  Area,
  AreaChart,
  CartesianGrid,
  Legend,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
  type TooltipProps,
} from "recharts";
import { formatBytes, formatTime } from "@/lib/utils";
import type { Metric } from "@/types/api";

// ---------------------------------------------------------------------------
// Özel tooltip
// ---------------------------------------------------------------------------

function NetworkTooltip({ active, payload, label }: TooltipProps<number, string>) {
  if (!active || !payload?.length) return null;

  return (
    <div className="rounded-lg border border-slate-200 bg-white px-3 py-2 shadow-md">
      <p className="mb-1 text-xs text-slate-400">{formatTime(label as string)}</p>
      {payload.map((entry) => (
        <p key={entry.name} className="text-xs font-medium" style={{ color: entry.color }}>
          {entry.name}: {formatBytes(Number(entry.value))}/s
        </p>
      ))}
    </div>
  );
}

// ---------------------------------------------------------------------------
// NetworkChart
// ---------------------------------------------------------------------------

interface NetworkChartProps {
  data: Metric[];
  height?: number;
}

export function NetworkChart({ data, height = 200 }: NetworkChartProps) {
  const sorted = [...data].reverse();

  return (
    <div aria-label="Ağ trafiği grafiği">
      <ResponsiveContainer width="100%" height={height}>
        <AreaChart
          data={sorted}
          margin={{ top: 4, right: 4, left: -8, bottom: 0 }}
        >
          <defs>
            <linearGradient id="colorNetIn" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%"  stopColor="#22c55e" stopOpacity={0.25} />
              <stop offset="95%" stopColor="#22c55e" stopOpacity={0} />
            </linearGradient>
            <linearGradient id="colorNetOut" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%"  stopColor="#64748b" stopOpacity={0.2} />
              <stop offset="95%" stopColor="#64748b" stopOpacity={0} />
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
            tickFormatter={(v) => formatBytes(v as number)}
            tick={{ fontSize: 10, fill: "#94a3b8" }}
            tickLine={false}
            axisLine={false}
            width={52}
          />

          <Tooltip content={<NetworkTooltip />} />

          <Legend
            iconType="circle"
            iconSize={8}
            wrapperStyle={{ fontSize: 11, paddingTop: 8 }}
          />

          <Area
            type="monotone"
            dataKey="network_in_bytes"
            name="Gelen"
            stroke="#22c55e"
            strokeWidth={2}
            fill="url(#colorNetIn)"
            dot={false}
            activeDot={{ r: 4, strokeWidth: 0 }}
            isAnimationActive={false}
          />

          <Area
            type="monotone"
            dataKey="network_out_bytes"
            name="Giden"
            stroke="#64748b"
            strokeWidth={2}
            fill="url(#colorNetOut)"
            dot={false}
            activeDot={{ r: 4, strokeWidth: 0 }}
            isAnimationActive={false}
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}
