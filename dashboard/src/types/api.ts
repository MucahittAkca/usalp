/**
 * Backend Pydantic şemalarıyla 1:1 eşleşen TypeScript tipleri.
 *
 * Her tip, karşılık gelen backend schema dosyasından türetilmiştir:
 *   - ServerOut        → backend/app/schemas/server.py
 *   - MetricOut        → backend/app/schemas/metric.py
 *   - AlertOut         → backend/app/schemas/alert.py
 *   - AIAnalysisOut    → backend/app/schemas/ai_analysis.py
 *   - TokenResponse    → backend/app/schemas/auth.py
 */

// ---------------------------------------------------------------------------
// Enum-like union tipler
// ---------------------------------------------------------------------------

export type ServerStatus = "online" | "offline" | "warning";

export type ServerEnvironment = "production" | "staging" | "development" | "test" | string;

export type ServiceStatus =
  | "active"
  | "inactive"
  | "failed"
  | "activating"
  | "deactivating"
  | "reloading"
  | "unknown";

export type AlertSeverity = "warning" | "critical";

export type AlertType =
  | "cpu_threshold"
  | "ram_threshold"
  | "disk_threshold"
  | "service_failed"
  | "critical_log_burst";

export type AiSeverity = "low" | "medium" | "high" | "critical";

export type CommandRisk = "low" | "medium" | "high";

export type AiCategory =
  | "network_error"
  | "disk_issue"
  | "permission_issue"
  | "config_error"
  | "dependency_failure"
  | "resource_exhaustion"
  | "unknown";

// ---------------------------------------------------------------------------
// Kaynak (resource) tipleri — backend *Out şemalarıyla eşleşir
// ---------------------------------------------------------------------------

/** backend/app/schemas/server.py → ServerOut */
export interface Server {
  id: number;
  name: string;
  hostname: string;
  ip_address: string;
  environment: ServerEnvironment;
  group_name: string;
  tags: string[];
  status: ServerStatus;
  last_seen: string | null;
  created_at: string;
  latest_metric: Metric | null;
  active_alert_count: number;
  critical_alert_count: number;
}

/** POST /servers request body */
export interface ServerCreateRequest {
  name: string;
  hostname: string;
  ip_address: string;
  environment?: ServerEnvironment;
  group_name?: string;
  tags?: string[];
}

/** backend/app/schemas/server.py → ServerCreatedOut (api_key yalnızca burada) */
export interface ServerCreated {
  id: number;
  name: string;
  hostname: string;
  ip_address: string;
  environment: ServerEnvironment;
  group_name: string;
  tags: string[];
  status: string;
  api_key: string;
  last_seen: string | null;
  created_at: string;
}

/** POST /servers/{id}/rotate-key response */
export interface ServerApiKey {
  id: number;
  api_key: string;
}

/** backend/app/schemas/metric.py → MetricOut */
export interface Metric {
  id: number;
  server_id: number;
  cpu_percent: number;
  ram_percent: number;
  disk_percent: number;
  network_in_bytes: number;
  network_out_bytes: number;
  load_avg_1: number;
  load_avg_5: number;
  load_avg_15: number;
  recorded_at: string;
}

/** backend/app/schemas/server.py → ServiceStatusOut */
export interface ServiceStatusEntry {
  id: number;
  server_id: number;
  service_name: string;
  status: ServiceStatus;
  checked_at: string;
}

/** backend/app/schemas/server.py → LogEntryOut */
export interface LogEntry {
  id: number;
  server_id: number;
  source_file: string;
  level: string;
  message: string;
  logged_at: string;
}

/** backend/app/schemas/alert.py → AlertOut */
export interface Alert {
  id: number;
  server_id: number;
  type: AlertType;
  dedupe_key: string;
  severity: AlertSeverity;
  message: string;
  resolved_at: string | null;
  created_at: string;
}

/** backend/app/schemas/ai_analysis.py → CommandSuggestion */
export interface CommandSuggestion {
  command: string;
  description: string;
  risk_level: CommandRisk;
}

/** backend/app/schemas/ai_analysis.py → AIAnalysisOut */
export interface AiAnalysis {
  id: number;
  alert_id: number | null;
  server_id: number;
  category: AiCategory;
  severity: AiSeverity;
  summary: string;
  causes: string[];
  evidence_lines: string[];
  commands: CommandSuggestion[];
  confidence: number;
  created_at: string;
}

/** GET /alerts/stats yanıtı */
export interface AlertStats {
  total_active: number;
  critical: number;
  warning: number;
}

// ---------------------------------------------------------------------------
// Auth
// ---------------------------------------------------------------------------

/** POST /auth/token request body */
export interface TokenRequest {
  username: string;
  password: string;
}

/** POST /auth/token → TokenResponse */
export interface TokenResponse {
  access_token: string;
  token_type: string;
}

// ---------------------------------------------------------------------------
// API yanıt zarfları (response wrappers)
// ---------------------------------------------------------------------------

export interface ApiResponse<T> {
  data: T;
  meta: Record<string, unknown>;
}

export interface PaginatedResponse<T> {
  data: T[];
  meta: {
    total: number;
    page: number;
    per_page: number;
  };
}

/** GET /servers/{id}/metrics özel meta yapısı */
export interface MetricListResponse {
  data: Metric[];
  meta: {
    total: number;
    limit: number;
    from: string;
    to: string;
  };
}
