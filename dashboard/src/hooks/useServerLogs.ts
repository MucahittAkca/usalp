import useSWR from "swr";
import { api } from "@/lib/api";
import type { LogEntry } from "@/types/api";

interface UseServerLogsParams {
  level?: string;
  perPage?: number;
}

export function useServerLogs(serverId: number, params?: UseServerLogsParams) {
  const { level, perPage = 200 } = params ?? {};

  const { data, error, isLoading, mutate } = useSWR(
    `logs-${serverId}-${level ?? "all"}-${perPage}`,
    () =>
      api.servers.logs(serverId, {
        level,
        per_page: perPage,
      }),
    {
      refreshInterval: 30_000,
      revalidateOnFocus: true,
      dedupingInterval: 10_000,
    },
  );

  const logs: LogEntry[] = data?.data ?? [];

  return {
    logs,
    total: data?.meta.total ?? 0,
    error,
    isLoading,
    mutate,
  };
}
