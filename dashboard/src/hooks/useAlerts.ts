import useSWR from "swr";
import { api } from "@/lib/api";
import type { Alert } from "@/types/api";

/** Tüm alertleri 15 sn polling ile döndürür. Sidebar badge ve alarm merkezi için. */
export function useAlerts(serverId?: number) {
  const { data, error, isLoading, mutate } = useSWR(
    serverId ? `alerts-server-${serverId}` : "alerts-all",
    () => api.alerts.list({ server_id: serverId, resolved: false }),
    { refreshInterval: 15_000 },
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
