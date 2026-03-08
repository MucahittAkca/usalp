"use client";

import { useCallback, useEffect, useRef, useState } from "react";

/**
 * Belirli aralıklarla veri çeken hook.
 * MVP'de WebSocket yerine polling kullanılır.
 */
export function usePolling<T>(
  fetcher: () => Promise<T>,
  intervalMs: number = 10_000
) {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState<Error | null>(null);
  const [loading, setLoading] = useState(true);
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const poll = useCallback(async () => {
    try {
      const result = await fetcher();
      setData(result);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err : new Error(String(err)));
    } finally {
      setLoading(false);
    }
  }, [fetcher]);

  useEffect(() => {
    poll();
    timerRef.current = setInterval(poll, intervalMs);
    return () => {
      if (timerRef.current) clearInterval(timerRef.current);
    };
  }, [poll, intervalMs]);

  return { data, error, loading };
}
