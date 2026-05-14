"use client";

import { Download } from "lucide-react";
import { MetricChart } from "@/components/metrics/MetricChart";
import { MetricGauge } from "@/components/metrics/MetricGauge";
import { NetworkChart } from "@/components/metrics/NetworkChart";
import { formatBytes } from "@/lib/utils";
import {
  METRIC_RANGE_LABELS,
  type MetricRange,
} from "@/hooks/useServerMetrics";
import type { Metric } from "@/types/api";

const METRIC_RANGES: MetricRange[] = ["15m", "1h", "6h", "24h", "7d"];

// ---------------------------------------------------------------------------
// Kart sarmalayıcı
// ---------------------------------------------------------------------------

interface ChartCardProps {
  title: string;
  subtitle?: string;
  children: React.ReactNode;
}

function ChartCard({ title, subtitle, children }: ChartCardProps) {
  return (
    <div className="flex flex-col gap-3 rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
      <div>
        <h3 className="text-sm font-semibold text-slate-700">{title}</h3>
        {subtitle && <p className="text-xs text-slate-400">{subtitle}</p>}
      </div>
      {children}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Yükleniyor iskeleti
// ---------------------------------------------------------------------------

function ChartSkeleton() {
  return (
    <div className="flex flex-col gap-3 rounded-xl border border-slate-200 bg-white p-4 shadow-sm animate-pulse">
      <div className="h-4 w-24 rounded bg-slate-200" />
      <div className="h-[200px] w-full rounded-lg bg-slate-100" />
    </div>
  );
}

// ---------------------------------------------------------------------------
// Anlık özet — Gauge'lar yan yana
// ---------------------------------------------------------------------------

interface GaugeRowProps {
  latest: Metric;
}

function GaugeRow({ latest }: GaugeRowProps) {
  return (
    <div className="flex flex-col gap-3 rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
      <div>
        <h3 className="text-sm font-semibold text-slate-700">Anlık Durum</h3>
        <p className="text-xs text-slate-400">
          Load avg: {latest.load_avg_1.toFixed(2)} / {latest.load_avg_5.toFixed(2)} /{" "}
          {latest.load_avg_15.toFixed(2)}
        </p>
      </div>

      <div className="flex items-center justify-around py-2">
        <MetricGauge value={latest.cpu_percent}  label="CPU"  thresholdKey="cpu" />
        <MetricGauge value={latest.ram_percent}  label="RAM"  thresholdKey="ram" />
        <MetricGauge value={latest.disk_percent} label="Disk" thresholdKey="disk" />
      </div>

      {/* Ağ anlık değerleri */}
      <div className="grid grid-cols-2 divide-x divide-slate-100 rounded-lg bg-slate-50 py-2 text-center">
        <div>
          <p className="text-xs text-slate-400">Gelen</p>
          <p className="mt-0.5 text-sm font-semibold text-slate-700">
            {formatBytes(latest.network_in_bytes)}/s
          </p>
        </div>
        <div>
          <p className="text-xs text-slate-400">Giden</p>
          <p className="mt-0.5 text-sm font-semibold text-slate-700">
            {formatBytes(latest.network_out_bytes)}/s
          </p>
        </div>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// MetricGrid — ana bileşen
// ---------------------------------------------------------------------------

interface MetricGridProps {
  metrics: Metric[];
  isLoading: boolean;
  range: MetricRange;
  onRangeChange: (range: MetricRange) => void;
}

function csvEscape(value: string | number): string {
  const raw = String(value);
  return /[",\n]/.test(raw) ? `"${raw.replaceAll("\"", "\"\"")}"` : raw;
}

function exportMetricsCsv(metrics: Metric[], range: MetricRange): void {
  const headers = [
    "recorded_at",
    "cpu_percent",
    "ram_percent",
    "disk_percent",
    "network_in_bytes",
    "network_out_bytes",
    "load_avg_1",
    "load_avg_5",
    "load_avg_15",
  ];
  const rows = [...metrics].reverse().map((metric) =>
    [
      metric.recorded_at,
      metric.cpu_percent,
      metric.ram_percent,
      metric.disk_percent,
      metric.network_in_bytes,
      metric.network_out_bytes,
      metric.load_avg_1,
      metric.load_avg_5,
      metric.load_avg_15,
    ].map(csvEscape).join(","),
  );
  const csv = [headers.join(","), ...rows].join("\n");
  const blob = new Blob([csv], { type: "text/csv;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = `usalp-metrics-${range}-${new Date().toISOString()}.csv`;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}

function MetricToolbar({
  range,
  onRangeChange,
  metrics,
}: {
  range: MetricRange;
  onRangeChange: (range: MetricRange) => void;
  metrics: Metric[];
}) {
  return (
    <div className="flex flex-wrap items-center justify-between gap-3 rounded-lg border border-slate-200 bg-white px-4 py-3 shadow-sm">
      <div className="flex flex-wrap items-center gap-1 rounded-md bg-slate-100 p-1">
        {METRIC_RANGES.map((item) => (
          <button
            key={item}
            type="button"
            onClick={() => onRangeChange(item)}
            className={
              range === item
                ? "rounded bg-white px-3 py-1.5 text-xs font-semibold text-slate-900 shadow-sm"
                : "rounded px-3 py-1.5 text-xs font-medium text-slate-500 hover:text-slate-800"
            }
          >
            {METRIC_RANGE_LABELS[item]}
          </button>
        ))}
      </div>

      <button
        type="button"
        onClick={() => exportMetricsCsv(metrics, range)}
        disabled={metrics.length === 0}
        className="inline-flex items-center gap-1.5 rounded-md bg-slate-900 px-3 py-2 text-xs font-medium text-white hover:bg-slate-800 disabled:opacity-40"
      >
        <Download size={13} />
        CSV
      </button>
    </div>
  );
}

export function MetricGrid({ metrics, isLoading, range, onRangeChange }: MetricGridProps) {
  const rangeLabel = METRIC_RANGE_LABELS[range];

  if (isLoading) {
    return (
      <div className="space-y-4">
        <MetricToolbar range={range} onRangeChange={onRangeChange} metrics={[]} />
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
          {Array.from({ length: 4 }).map((_, i) => (
            <ChartSkeleton key={i} />
          ))}
        </div>
      </div>
    );
  }

  if (metrics.length === 0) {
    return (
      <div className="space-y-4">
        <MetricToolbar range={range} onRangeChange={onRangeChange} metrics={metrics} />
        <div className="flex items-center justify-center rounded-xl border border-dashed border-slate-300 bg-white py-16">
          <p className="text-sm text-slate-400">Seçili aralıkta metrik verisi bulunmuyor</p>
        </div>
      </div>
    );
  }

  const latest = metrics[0]; // API desc sıralar, ilk öğe en yeni

  return (
    <div className="space-y-4">
      <MetricToolbar range={range} onRangeChange={onRangeChange} metrics={metrics} />

      <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
        {/* Sol üst: Anlık özet + Gauge'lar */}
        <GaugeRow latest={latest} />

        {/* Sağ üst: CPU zaman serisi */}
        <ChartCard
          title="CPU Kullanımı"
          subtitle={rangeLabel}
        >
          <MetricChart data={metrics} metricKey="cpu_percent" />
        </ChartCard>

        {/* Sol alt: RAM zaman serisi */}
        <ChartCard
          title="RAM Kullanımı"
          subtitle={rangeLabel}
        >
          <MetricChart data={metrics} metricKey="ram_percent" />
        </ChartCard>

        {/* Sağ alt: Ağ trafiği */}
        <ChartCard
          title="Ağ Trafiği"
          subtitle={`${rangeLabel} · Gelen / Giden`}
        >
          <NetworkChart data={metrics} />
        </ChartCard>
      </div>
    </div>
  );
}
