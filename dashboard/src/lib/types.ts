export interface Server {
  id: number;
  name: string;
  hostname: string;
  ip_address: string;
  status: string;
  created_at: string;
}

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

export interface Alert {
  id: number;
  server_id: number;
  type: string;
  severity: string;
  message: string;
  resolved_at: string | null;
  created_at: string;
}

export interface AIAnalysis {
  id: number;
  alert_id: number | null;
  server_id: number;
  category: string;
  severity: string;
  summary: string;
  causes: string;
  commands: string;
  confidence: number;
  created_at: string;
}
