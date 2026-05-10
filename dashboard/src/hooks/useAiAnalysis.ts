import { useState } from "react";
import useSWR from "swr";
import { api, ApiError } from "@/lib/api";
import type { AiAnalysis } from "@/types/api";

export function useAiAnalysis(serverId: number) {
  const [triggering, setTriggering] = useState(false);
  const [cooldownError, setCooldownError] = useState(false);
  const [triggerError, setTriggerError] = useState<string | null>(null);

  const { data, error, isLoading, mutate } = useSWR(
    `ai-analyses-${serverId}`,
    () => api.ai.analyses(serverId, { per_page: 10 }),
    {
      revalidateOnFocus: false,
      dedupingInterval: 30_000,
    },
  );

  const analyses: AiAnalysis[] = data?.data ?? [];

  async function trigger(): Promise<AiAnalysis | null> {
    if (triggering) return null;

    setTriggering(true);
    setCooldownError(false);
    setTriggerError(null);

    try {
      const res = await api.ai.analyze(serverId);
      if (!res.data) {
        setTriggerError(
          typeof res.meta.message === "string"
            ? res.meta.message
            : "Analiz çalıştırılamadı",
        );
        return null;
      }
      // Analiz başarılı — geçmiş listeyi yenile
      await mutate();
      return res.data;
    } catch (err) {
      if (err instanceof ApiError && err.status === 429) {
        setCooldownError(true);
      } else {
        setTriggerError(
          err instanceof Error ? err.message : "Analiz başlatılamadı",
        );
      }
      return null;
    } finally {
      setTriggering(false);
    }
  }

  return {
    analyses,
    latest: analyses[0] ?? null,
    isLoading,
    error,
    mutate,
    trigger,
    triggering,
    cooldownError,
    triggerError,
  };
}
