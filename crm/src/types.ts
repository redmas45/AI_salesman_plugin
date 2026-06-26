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
  script_tag: string;
  catalog: CatalogSummary;
  usage: UsageSummary;
  quota: QuotaStatus;
  catalog_preview?: ProductPreview[];
  sync_runs?: SyncRun[];
}

export interface ProductPreview {
  id?: string | number;
  product_id?: string | number;
  name?: string;
  brand?: string;
  category?: string;
  category_name?: string;
  price?: number;
  stock?: number;
  image_url?: string | null;
  is_active?: boolean | number;
  has_embedding?: boolean | number;
}

export interface CatalogProduct {
  id: string;
  name: string;
  brand?: string;
  category_name?: string;
  category?: string;
  description?: string;
  price: number;
  original_price?: number | null;
  rating?: number;
  review_count?: number;
  stock?: number;
  image_url?: string | null;
  has_embedding?: boolean | number;
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
  generated_at?: string;
  metrics: {
    turns: number;
    tokens: number;
    sessions: number;
    avg_latency_ms: number;
    actions?: number;
    action_rate?: number;
    error_rate?: number;
    tokens_per_turn?: number;
  };
  top_intents: RankRow[];
  top_products: RankRow[];
  top_terms: RankRow[];
  status_mix?: RankRow[];
  transport_mix?: RankRow[];
  site_mix?: RankRow[];
  latency_buckets?: RankRow[];
  peak_day?: SeriesRow | null;
  recent_events?: UsageEvent[];
  series: SeriesRow[];
  summary: string;
  summary_source?: string;
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

export interface VerticalDefinition {
  key: string;
  label: string;
  risk_level: 'low' | 'medium' | 'high';
  entity_label_singular: string;
  entity_label_plural: string;
  default_plan_label: string;
  crm_tabs: Array<{ id: string; label: string }>;
  entity_types: string[];
  readiness_checks: string[];
  action_types: string[];
}

export interface VerticalsResponse {
  default_vertical_key: string;
  verticals: VerticalDefinition[];
}

export interface TokenLimitsPayload {
  token_limit: number;
  session_token_limit: number;
}

export interface ClientPanelPasswordPayload {
  password?: string;
  auto_generate?: boolean;
}

export interface CapabilityItem {
  name: string;
  supported: boolean;
  confidence: number;
  evidence: string;
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

export interface KnowledgeStats {
  total_items: number;
  active_items: number;
  missing_embeddings: number;
  entity_types: number;
}

export interface KnowledgeItem {
  id: string;
  external_id?: string;
  entity_type: string;
  title: string;
  subtitle?: string;
  summary?: string;
  body?: string;
  url?: string;
  image_url?: string;
  source_id?: string;
  attributes?: Record<string, unknown>;
  pricing?: Record<string, unknown>;
  availability?: Record<string, unknown>;
  has_embedding?: boolean | number;
  updated_at?: string;
}

export interface KnowledgeResponse {
  stats: KnowledgeStats;
  items: KnowledgeItem[];
}

export interface AdapterRuntimeConfig {
  version: number;
  site_id: string;
  enabled: boolean;
  api_base_url: string;
  install: Record<string, string>;
  vertical: Record<string, unknown>;
  adapter: {
    name?: string;
    mode?: string;
    platform?: string;
    routes?: Record<string, unknown>;
    actions?: Record<string, unknown>;
    selectors?: Record<string, unknown>;
    selector_confidence?: number;
    selector_validated?: boolean;
  };
}

export interface AdapterConfigResponse {
  runtime_config: AdapterRuntimeConfig;
  adapter_code: string;
}

export interface PromptVersion {
  id: string;
  profile_id: string;
  version: number;
  status: 'draft' | 'published' | 'archived' | string;
  system_prompt: string;
  developer_rules: string;
  response_schema?: Record<string, unknown>;
  variables?: Record<string, unknown>;
  allowed_actions?: string[];
  changelog?: string;
  created_by?: string;
  created_at?: string;
  published_at?: string | null;
}

export interface PromptProfile {
  id: string;
  site_id: string;
  name: string;
  vertical_key: string;
  status: string;
  created_by?: string;
  created_at?: string;
  updated_at?: string;
}

export interface PromptProfileResponse {
  profile: PromptProfile;
  versions: PromptVersion[];
  draft_version: PromptVersion | null;
  published_version: PromptVersion | null;
  active_version: PromptVersion | null;
}

export interface PromptProfileSavePayload {
  name: string;
  system_prompt: string;
  developer_rules: string;
  publish: boolean;
  changelog?: string;
}
