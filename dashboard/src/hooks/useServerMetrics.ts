import { useEffect } from "react";
import useSWR, { type KeyedMutator } from "swr";
import { api } from "@/lib/api";
import { clearToken, getToken } from "@/lib/auth";
import type { Metric, MetricListResponse } from "@/types/api";

const MAX_STREAM_METRICS = 1000;
const STREAM_RECONNECT_DELAY_MS = 3_000;

export type MetricRange = "15m" | "1h" | "6h" | "24h" | "7d";

export const METRIC_RANGE_LABELS: Record<MetricRange, string> = {
  "15m": "15 dk",
  "1h": "1 saat",
  "6h": "6 saat",
  "24h": "24 saat",
  "7d": "7 gün",
};

const METRIC_RANGE_MS: Record<MetricRange, number> = {
  "15m": 15 * 60 * 1000,
  "1h": 60 * 60 * 1000,
  "6h": 6 * 60 * 60 * 1000,
  "24h": 24 * 60 * 60 * 1000,
  "7d": 7 * 24 * 60 * 60 * 1000,
};

function metricRangeParams(range: MetricRange) {
  const to = new Date();
  const from = new Date(to.getTime() - METRIC_RANGE_MS[range]);
  return {
    from_dt: from.toISOString(),
    to_dt: to.toISOString(),
    limit: MAX_STREAM_METRICS,
  };
}

function parseMetricEvent(rawEvent: string): Metric | null {
  let eventName = "message";
  const dataLines: string[] = [];

  for (const line of rawEvent.split("\n")) {
    if (line.startsWith("event:")) {
      eventName = line.slice("event:".length).trim();
    } else if (line.startsWith("data:")) {
      dataLines.push(line.slice("data:".length).trimStart());
    }
  }

  if (eventName !== "metric" || dataLines.length === 0) return null;

  try {
    return JSON.parse(dataLines.join("\n")) as Metric;
  } catch {
    return null;
  }
}

function mergeMetric(
  current: MetricListResponse | undefined,
  metric: Metric,
  limit: number,
): MetricListResponse {
  const data = [metric, ...(current?.data ?? []).filter((item) => item.id !== metric.id)]
    .sort(
      (a, b) =>
        new Date(b.recorded_at).getTime() - new Date(a.recorded_at).getTime(),
    )
    .slice(0, limit);

  return {
    data,
    meta: {
      total: Math.max(current?.meta.total ?? 0, data.length),
      limit,
      from: current?.meta.from ?? data[data.length - 1]?.recorded_at ?? metric.recorded_at,
      to: metric.recorded_at,
    },
  };
}

function useMetricStream(
  serverId: number,
  mutate: KeyedMutator<MetricListResponse>,
  limit: number,
): void {
  useEffect(() => {
    if (!Number.isFinite(serverId)) return;

    let stopped = false;
    const controller = new AbortController();

    async function connect() {
      while (!stopped) {
        const token = getToken();
        if (!token) return;

        try {
          const response = await fetch(api.servers.metricsStreamUrl(serverId), {
            headers: {
              Accept: "text/event-stream",
              Authorization: `Bearer ${token}`,
            },
            signal: controller.signal,
          });

          if (response.status === 401) {
            clearToken();
            if (window.location.pathname !== "/login") {
              window.location.href = "/login";
            }
            return;
          }

          if (!response.ok || !response.body) {
            throw new Error(`Metric stream failed: HTTP ${response.status}`);
          }

          const reader = response.body.getReader();
          const decoder = new TextDecoder();
          let buffer = "";

          while (!stopped) {
            const { value, done } = await reader.read();
            if (done) break;

            buffer += decoder.decode(value, { stream: true }).replace(/\r\n/g, "\n");
            const events = buffer.split("\n\n");
            buffer = events.pop() ?? "";

            for (const rawEvent of events) {
              const metric = parseMetricEvent(rawEvent);
              if (!metric) continue;
              await mutate((current) => mergeMetric(current, metric, limit), {
                revalidate: false,
              });
            }
          }
        } catch {
          if (stopped || controller.signal.aborted) return;
          await new Promise((resolve) => setTimeout(resolve, STREAM_RECONNECT_DELAY_MS));
        }
      }
    }

    void connect();

    return () => {
      stopped = true;
      controller.abort();
    };
  }, [serverId, mutate, limit]);
}

/** Bir sunucunun en güncel metriğini döndürür (CardView için). */
export function useLatestMetric(serverId: number): {
  metric: Metric | null;
  isLoading: boolean;
  error: Error | undefined;
} {
  const { data, error, isLoading, mutate } = useSWR(
    `metric-latest-${serverId}`,
    () => api.servers.metrics(serverId, { limit: 1 }),
    {
      refreshInterval: 60_000,
      dedupingInterval: 10_000,
    },
  );
  useMetricStream(serverId, mutate, 1);

  return {
    metric: data?.data[0] ?? null,
    isLoading,
    error,
  };
}

/** Bir sunucunun seçili zaman aralığındaki metrik serisini döndürür (Chart için). */
export function useServerMetrics(serverId: number, range: MetricRange = "1h") {
  const { data, error, isLoading, mutate } = useSWR(
    `metrics-${serverId}-${range}`,
    () => api.servers.metrics(serverId, metricRangeParams(range)),
    {
      refreshInterval: 60_000,
      revalidateOnFocus: true,
      dedupingInterval: 5_000,
    },
  );
  useMetricStream(serverId, mutate, MAX_STREAM_METRICS);

  return {
    metrics: data?.data ?? [],
    error,
    isLoading,
    mutate,
  };
}
