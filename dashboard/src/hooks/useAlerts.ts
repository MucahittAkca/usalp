import useSWR from "swr";
import { api } from "@/lib/api";
import type { Alert } from "@/types/api";

/** Alertleri düşük frekanslı polling ile döndürür. */
export function useAlerts(serverId?: number) {
  const { data, error, isLoading, mutate } = useSWR(
    serverId ? `alerts-server-${serverId}` : "alerts-all",
    () => api.alerts.list({ server_id: serverId, resolved: false }),
    {
      refreshInterval: 60_000,
      dedupingInterval: 10_000,
      revalidateOnFocus: false,
    },
  );

  const alerts: Alert[] = data?.data ?? [];

  return {
    alerts,
    activeCount: alerts.filter((a) => !a.resolved_at).length,
    criticalCount: alerts.filter(
      (a) => a.severity === "critical" && !a.resolved_at,
    ).length,
    error,
    isLoading,
    mutate,
  };
}
