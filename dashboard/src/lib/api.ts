/**
 * Backend API istemcisi.
 *
 * Tüm endpoint çağrıları buradan yapılır. SWR hook'ları ve bileşenler
 * doğrudan fetch kullanmak yerine bu modülü kullanmalıdır.
 */

import { clearToken, getToken } from "@/lib/auth";
import type {
  AiAnalysis,
  Alert,
  AlertStats,
  ApiResponse,
  LogEntry,
  MetricListResponse,
  PaginatedResponse,
  Server,
  ServerApiKey,
  ServerCreated,
  ServerCreateRequest,
  ServiceStatusEntry,
  TokenRequest,
  TokenResponse,
} from "@/types/api";

// ---------------------------------------------------------------------------
// Konfigürasyon
// ---------------------------------------------------------------------------

const API_BASE =
  process.env.NEXT_PUBLIC_API_URL ?? "/api/v1";

function apiUrl(path: string): string {
  return `${API_BASE}${path}`;
}

// ---------------------------------------------------------------------------
// Yardımcı: genel fetch wrapper
// ---------------------------------------------------------------------------

export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
    public details?: Record<string, unknown>,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

async function apiFetch<T>(path: string, options?: RequestInit): Promise<T> {
  const token = getToken();

  const res = await fetch(apiUrl(path), {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...options?.headers,
    },
  });

  if (res.status === 401) {
    clearToken();
    if (typeof window !== "undefined" && !window.location.pathname.startsWith("/login")) {
      window.location.href = "/login";
    }
    throw new ApiError(401, "Unauthorized");
  }

  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new ApiError(
      res.status,
      body?.error?.message ?? body?.detail ?? `HTTP ${res.status}`,
      body?.error?.details,
    );
  }

  return res.json() as Promise<T>;
}

// ---------------------------------------------------------------------------
// Query string oluşturucu
// ---------------------------------------------------------------------------

function qs(params: Record<string, string | number | boolean | undefined | null>): string {
  const entries = Object.entries(params).filter(
    (entry): entry is [string, string | number | boolean] =>
      entry[1] != null && entry[1] !== "",
  );
  if (entries.length === 0) return "";
  return "?" + new URLSearchParams(entries.map(([k, v]) => [k, String(v)])).toString();
}

// ---------------------------------------------------------------------------
// Auth
// ---------------------------------------------------------------------------

const auth = {
  login: (credentials: TokenRequest) =>
    apiFetch<TokenResponse>("/auth/token", {
      method: "POST",
      body: JSON.stringify(credentials),
    }),
};

// ---------------------------------------------------------------------------
// Servers
// ---------------------------------------------------------------------------

interface ServerListParams {
  page?: number;
  per_page?: number;
  environment?: string;
  group_name?: string;
  tag?: string;
}

interface MetricListParams {
  from_dt?: string;
  to_dt?: string;
  limit?: number;
}

interface LogListParams {
  level?: string;
  q?: string;
  from_dt?: string;
  to_dt?: string;
  page?: number;
  per_page?: number;
}

const servers = {
  list: (params?: ServerListParams) =>
    apiFetch<PaginatedResponse<Server>>(`/servers${qs({ ...params })}`),

  create: (body: ServerCreateRequest) =>
    apiFetch<ApiResponse<ServerCreated>>("/servers", {
      method: "POST",
      body: JSON.stringify(body),
    }),

  get: (id: number) =>
    apiFetch<ApiResponse<Server>>(`/servers/${id}`),

  rotateKey: (id: number) =>
    apiFetch<ApiResponse<ServerApiKey>>(`/servers/${id}/rotate-key`, {
      method: "POST",
    }),

  revokeKey: (id: number) =>
    apiFetch<ApiResponse<Server>>(`/servers/${id}/revoke-key`, {
      method: "PATCH",
    }),

  metrics: (id: number, params?: MetricListParams) =>
    apiFetch<MetricListResponse>(`/servers/${id}/metrics${qs({ ...params })}`),

  metricsStreamUrl: (id: number) =>
    apiUrl(`/servers/${id}/metrics/stream`),

  services: (id: number) =>
    apiFetch<ApiResponse<ServiceStatusEntry[]>>(`/servers/${id}/services`),

  logs: (id: number, params?: LogListParams) =>
    apiFetch<PaginatedResponse<LogEntry>>(`/servers/${id}/logs${qs({ ...params })}`),
};

// ---------------------------------------------------------------------------
// Alerts
// ---------------------------------------------------------------------------

interface AlertListParams {
  server_id?: number;
  severity?: string;
  alert_type?: string;
  resolved?: boolean;
  page?: number;
  per_page?: number;
}

const alerts = {
  list: (params?: AlertListParams) =>
    apiFetch<PaginatedResponse<Alert>>(`/alerts${qs({ ...params })}`),

  resolve: (id: number) =>
    apiFetch<ApiResponse<Alert>>(`/alerts/${id}/resolve`, { method: "PATCH" }),

  stats: (serverId?: number) =>
    apiFetch<ApiResponse<AlertStats>>(
      `/alerts/stats${qs({ server_id: serverId })}`,
    ),
};

// ---------------------------------------------------------------------------
// AI
// ---------------------------------------------------------------------------

interface AnalysisListParams {
  page?: number;
  per_page?: number;
}

const ai = {
  analyze: (serverId: number) =>
    apiFetch<ApiResponse<AiAnalysis | null>>("/ai/analyze", {
      method: "POST",
      body: JSON.stringify({ server_id: serverId }),
    }),

  analyses: (serverId: number, params?: AnalysisListParams) =>
    apiFetch<PaginatedResponse<AiAnalysis>>(
      `/ai/analyses/${serverId}${qs({ ...params })}`,
    ),
};

// ---------------------------------------------------------------------------
// Public API nesnesi
// ---------------------------------------------------------------------------

export const api = { auth, servers, alerts, ai } as const;
