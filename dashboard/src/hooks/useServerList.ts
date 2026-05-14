import useSWR from "swr";
import { api } from "@/lib/api";
import type { Server } from "@/types/api";

export interface ServerListFilters {
  environment?: string;
  group_name?: string;
  tag?: string;
}

export function useServerList(filters?: ServerListFilters) {
  const { data, error, isLoading, mutate } = useSWR<{ data: Server[] }>(
    ["server-list", filters?.environment ?? "", filters?.group_name ?? "", filters?.tag ?? ""],
    () => api.servers.list(filters),
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
