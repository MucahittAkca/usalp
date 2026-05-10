import useSWR from "swr";
import { api } from "@/lib/api";
import type { ServiceStatusEntry } from "@/types/api";

export function useServerServices(serverId: number) {
  const { data, error, isLoading, mutate } = useSWR(
    `services-${serverId}`,
    () => api.servers.services(serverId),
    {
      refreshInterval: 30_000,
      revalidateOnFocus: true,
      dedupingInterval: 10_000,
    },
  );

  const services: ServiceStatusEntry[] = (data?.data as ServiceStatusEntry[] | undefined) ?? [];

  return {
    services,
    failedCount: services.filter((s) => s.status === "failed").length,
    error,
    isLoading,
    mutate,
  };
}
