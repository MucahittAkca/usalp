"use client";

import { MetricChart } from "@/components/metrics/MetricChart";
import { MetricGauge } from "@/components/metrics/MetricGauge";
import { NetworkChart } from "@/components/metrics/NetworkChart";
import { formatBytes } from "@/lib/utils";
import type { Metric } from "@/types/api";

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
}

export function MetricGrid({ metrics, isLoading }: MetricGridProps) {
  if (isLoading) {
    return (
      <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
        {Array.from({ length: 4 }).map((_, i) => (
          <ChartSkeleton key={i} />
        ))}
      </div>
    );
  }

  if (metrics.length === 0) {
    return (
      <div className="flex items-center justify-center rounded-xl border border-dashed border-slate-300 bg-white py-16">
        <p className="text-sm text-slate-400">Henüz metrik verisi bulunmuyor</p>
      </div>
    );
  }

  const latest = metrics[0]; // API desc sıralar, ilk öğe en yeni

  return (
    <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
      {/* Sol üst: Anlık özet + Gauge'lar */}
      <GaugeRow latest={latest} />

      {/* Sağ üst: CPU zaman serisi */}
      <ChartCard
        title="CPU Kullanımı"
        subtitle="Son 1 saat"
      >
        <MetricChart data={metrics} metricKey="cpu_percent" />
      </ChartCard>

      {/* Sol alt: RAM zaman serisi */}
      <ChartCard
        title="RAM Kullanımı"
        subtitle="Son 1 saat"
      >
        <MetricChart data={metrics} metricKey="ram_percent" />
      </ChartCard>

      {/* Sağ alt: Ağ trafiği */}
      <ChartCard
        title="Ağ Trafiği"
        subtitle="Gelen / Giden"
      >
        <NetworkChart data={metrics} />
      </ChartCard>
    </div>
  );
}
