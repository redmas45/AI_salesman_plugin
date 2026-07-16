export interface CapabilityItem {
  name: string;
  supported: boolean;
  confidence: number;
  evidence: string;
  blocking?: boolean;
}

export interface ReadinessReport {
  site_id: string;
  scanned_at: string;
  platform: string;
  platform_confidence: number;
  capabilities: CapabilityItem[];
}

export interface CapabilitiesSummary {
  site_id: string;
  scanned: boolean;
  platform: string;
  platform_confidence: number;
  supported: string[];
  unsupported: string[];
  allowed_actions: string[];
  action_policy?: Record<string, unknown>;
  scanned_at?: string;
}

export interface CrawlReport {
  site_id: string;
  site_url: string;
  source_type: string;
  pages_visited: number;
  pages_failed: number;
  pages_blocked: number;
  product_count: number;
  variant_count: number;
  category_count: number;
  failed_urls: string[];
  blocked_urls: string[];
  coverage_score: number;
  duration_ms: number;
  stopped_by_limit: boolean;
  created_at: string;
}

export type OperationKind = 'crawl' | 'readiness' | 'integration';
export type OperationStatusValue = 'pending' | 'running' | 'complete' | 'failed' | 'skipped' | string;

export interface OperationStageStatus {
  name: string;
  label: string;
  status: OperationStatusValue;
  message: string;
  started_at?: string;
  completed_at?: string;
  duration_ms?: number;
  detail?: Record<string, unknown>;
}

export interface OperationStatus {
  kind: OperationKind;
  label: string;
  status: OperationStatusValue;
  message: string;
  progress: number;
  started_at?: string;
  completed_at?: string;
  duration_ms?: number;
  result_tab: string;
  stages: OperationStageStatus[];
  logs: string[];
}

export interface OperationStatusResponse {
  site_id: string;
  generated_at: string;
  operations: Record<OperationKind, OperationStatus>;
}
