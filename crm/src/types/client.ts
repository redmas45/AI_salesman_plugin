import type { CatalogSummary, ProductPreview, SyncRun } from './catalog';
import type { HealthSnapshot, ProviderUsageStatus, QuotaStatus, UsageEvent, UsageSummary } from './usage';

export interface AnswerCacheItem {
  id?: number | string;
  question: string;
  answer_scope?: string;
  cache_type?: string;
  data_version?: number;
  is_stale?: boolean;
  hit_count?: number;
  updated_at?: string;
}

export interface AnswerCacheSummary {
  site_id: string;
  data_version: number;
  total: number;
  fresh: number;
  stale: number;
  hits: number;
  estimated_tokens_saved: number;
  items: AnswerCacheItem[];
  error?: string;
}

export interface Client {
  site_id: string;
  name: string;
  store_url: string;
  allowed_origin: string;
  deploy_mode: string;
  plan: string;
  vertical_key?: string;
  vertical_label?: string;
  vertical_config?: Record<string, unknown>;
  risk_level?: 'low' | 'medium' | 'high' | string;
  locale?: string;
  prompt_profile_id?: string;
  compliance_mode?: string;
  adapter_name: string;
  status: string;
  token_limit?: number;
  session_token_limit?: number;
  last_crawl_status?: string;
  last_crawl_message?: string;
  last_crawl_at?: string | null;
  panel_password_configured?: boolean;
  panel_password_status?: 'configured' | 'revoked' | 'not_configured' | string;
  runtime_status?: {
    status?: 'online' | 'offline' | 'unknown' | string;
    label?: string;
    checked_url?: string;
    status_code?: number;
    message?: string;
  };
  script_tag: string;
  catalog: CatalogSummary;
  answer_cache?: AnswerCacheSummary;
  usage: UsageSummary;
  quota: QuotaStatus;
  catalog_preview?: ProductPreview[];
  sync_runs?: SyncRun[];
}

export interface OverviewMetrics {
  active_clients: number;
  voice_turns_today: number;
  total_voice_turns: number;
  products_indexed: number;
  avg_latency_ms: number;
  tokens_estimated: number;
  answer_cache_hits?: number;
  answer_cache_fresh?: number;
  answer_cache_tokens_saved?: number;
}

export interface Overview {
  health: HealthSnapshot;
  provider_usage?: ProviderUsageStatus;
  metrics: OverviewMetrics;
  clients: Client[];
  recent_activity: UsageEvent[];
}

export interface Setting {
  key: string;
  value: string;
  is_secret: boolean;
  configured?: boolean;
  source?: string;
}

export interface SettingsResponse {
  restart_required?: boolean;
  settings: Setting[];
}

export interface CreateClientPayload {
  name: string;
  store_url: string;
  site_id?: string;
  deploy_mode: string;
  plan: string;
  vertical_key: string;
  adapter_name: string;
}

export interface TokenLimitsPayload {
  token_limit: number;
  session_token_limit: number;
}

export interface ClientPanelPasswordPayload {
  password?: string;
  auto_generate?: boolean;
}

export interface AnswerCacheResponse {
  answer_cache: AnswerCacheSummary;
}
