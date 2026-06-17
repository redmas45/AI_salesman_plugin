export type View =
  | 'dashboard'
  | 'clients'
  | 'client-detail'
  | 'catalogs'
  | 'usage'
  | 'conversations'
  | 'analytics'
  | 'adapters'
  | 'settings'
  | 'health';

export type Theme = 'light' | 'dark';

export interface HealthSnapshot {
  fastapi?: string;
  postgres?: string;
  pgvector?: string;
  crawler?: string;
  [key: string]: string | undefined;
}

export interface CatalogSource {
  source_name?: string;
  active_products?: number;
  total_products?: number;
  last_seen_at?: string;
}

export interface SyncRun {
  id?: number;
  source_name?: string;
  source_count?: number;
  changed_count?: number;
  deactivated_count?: number;
  vectorized_count?: number;
  created_at?: string;
}

export interface CatalogSummary {
  total_products: number;
  active_products: number;
  missing_embeddings: number;
  categories?: number;
  sources?: CatalogSource[];
  last_sync?: SyncRun | null;
  error?: string;
}

export interface UsageSummary {
  total_turns: number;
  turns_today: number;
  tokens_estimated: number;
  avg_latency_ms: number;
}

export interface QuotaPart {
  used: number;
  limit: number;
  remaining: number;
}

export interface QuotaStatus {
  client: QuotaPart;
  session: QuotaPart;
}

export interface Client {
  site_id: string;
  name: string;
  store_url: string;
  allowed_origin: string;
  deploy_mode: string;
  plan: string;
  adapter_name: string;
  status: string;
  token_limit?: number;
  session_token_limit?: number;
  last_crawl_status?: string;
  last_crawl_message?: string;
  last_crawl_at?: string | null;
  script_tag: string;
  catalog: CatalogSummary;
  usage: UsageSummary;
  quota: QuotaStatus;
  catalog_preview?: ProductPreview[];
  sync_runs?: SyncRun[];
}

export interface ProductPreview {
  id?: string | number;
  name?: string;
  category?: string;
  price?: number;
  has_embedding?: boolean;
}

export interface OverviewMetrics {
  active_clients: number;
  voice_turns_today: number;
  total_voice_turns: number;
  products_indexed: number;
  avg_latency_ms: number;
  tokens_estimated: number;
}

export interface UsageEvent {
  site_id: string;
  session_id: string;
  transport: string;
  status: string;
  intent: string;
  action_count: number;
  latency_ms: number;
  input_tokens: number;
  output_tokens: number;
  transcript: string;
  response_text: string;
  created_at: string;
}

export interface Overview {
  health: HealthSnapshot;
  metrics: OverviewMetrics;
  clients: Client[];
  recent_activity: UsageEvent[];
}

export interface ConversationTurn {
  created_at: string;
  transport: string;
  status: string;
  intent: string;
  tokens: number;
  latency_ms: number;
  transcript: string;
  response_text: string;
  action_count: number;
}

export interface ConversationSession {
  site_id: string;
  session_id: string;
  started_at: string;
  last_seen_at: string;
  turn_count: number;
  tokens_used: number;
  turns: ConversationTurn[];
}

export interface ConversationGroup {
  date: string;
  sessions: ConversationSession[];
}

export interface ConversationsResponse {
  range: string;
  site_id: string;
  groups: ConversationGroup[];
}

export interface RankRow {
  label: string;
  count: number;
}

export interface SeriesRow {
  date: string;
  turns: number;
  tokens: number;
}

export interface AnalyticsResponse {
  range: string;
  site_id: string;
  metrics: {
    turns: number;
    tokens: number;
    sessions: number;
    avg_latency_ms: number;
  };
  top_intents: RankRow[];
  top_products: RankRow[];
  top_terms: RankRow[];
  series: SeriesRow[];
  summary: string;
  summary_source?: string;
}

export interface Setting {
  key: string;
  value: string;
  is_secret: boolean;
  configured?: boolean;
}

export interface SettingsResponse {
  settings: Setting[];
}

export interface CreateClientPayload {
  name: string;
  store_url: string;
  site_id?: string;
  deploy_mode: string;
  plan: string;
  adapter_name: string;
}
