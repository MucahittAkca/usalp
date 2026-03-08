const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "/api/v1";

interface ApiResponse<T> {
  data: T;
  meta: Record<string, unknown>;
}

export async function fetchApi<T>(
  endpoint: string,
  options?: RequestInit
): Promise<ApiResponse<T>> {
  const res = await fetch(`${API_BASE}${endpoint}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });

  if (!res.ok) {
    throw new Error(`API error: ${res.status} ${res.statusText}`);
  }

  return res.json() as Promise<ApiResponse<T>>;
}
