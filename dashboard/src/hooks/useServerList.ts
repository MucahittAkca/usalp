import useSWR from "swr";
import { api } from "@/lib/api";
import type { Server } from "@/types/api";

export function useServerList() {
  const { data, error, isLoading, mutate } = useSWR<{ data: Server[] }>(
    "server-list",
    () => api.servers.list(),
    {
      refreshInterval: 30_000,
      revalidateOnFocus: true,
      dedupingInterval: 5_000,
    },
  );

  return {
    servers: data?.data ?? [],
    total: (data as { meta?: { total?: number } } | undefined)?.meta?.total ?? 0,
    error,
    isLoading,
    mutate,
  };
}
