import useSWR from "swr";
import { api } from "@/lib/api";
import type { Metric } from "@/types/api";

/** Bir sunucunun en güncel metriğini döndürür (CardView için). */
export function useLatestMetric(serverId: number): {
  metric: Metric | null;
  isLoading: boolean;
  error: Error | undefined;
} {
  const { data, error, isLoading } = useSWR(
    `metric-latest-${serverId}`,
    () => api.servers.metrics(serverId, { limit: 1 }),
    {
      refreshInterval: 30_000,
      dedupingInterval: 10_000,
    },
  );

  return {
    metric: data?.data[0] ?? null,
    isLoading,
    error,
  };
}

/** Bir sunucunun son 1 saatlik metrik serisini döndürür (Chart için). */
export function useServerMetrics(serverId: number) {
  const { data, error, isLoading, mutate } = useSWR(
    `metrics-${serverId}`,
    () => api.servers.metrics(serverId),
    {
      refreshInterval: 30_000,
      revalidateOnFocus: true,
      dedupingInterval: 5_000,
    },
  );

  return {
    metrics: data?.data ?? [],
    error,
    isLoading,
    mutate,
  };
}
