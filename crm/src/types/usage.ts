import type { ActionEventStatus, UiActionName } from '@ai-hub/contracts';

export interface HealthSnapshot {
  fastapi?: string;
  postgres?: string;
  pgvector?: string;
  crawler?: string;
  [key: string]: string | undefined;
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

export interface ProviderUsageEvent {
  provider: string;
  category: string;
  message: string;
  occurred_at: string;
}

export interface ProviderUsageStatus {
  status: string;
  provider: string;
  llm_model: string;
  stt_model: string;
  tts_model: string;
  azure_openai_api_key_configured: boolean;
  local_tokens: {
    estimated_total: number;
    turns_total: number;
    turns_today: number;
    avg_latency_ms: number;
  };
  billing: {
    status: string;
    message: string;
  };
  recent_events: ProviderUsageEvent[];
  checked_at: string;
}

export interface ActionExecutionEvent {
  occurred_at: string;
  request_id: string;
  turn_id: string;
  sequence: number;
  action: UiActionName | string;
  status: ActionEventStatus | string;
  stage: string;
  reason: string;
  duration_ms: number;
  requested_url: string;
  final_url: string;
  url_changed?: boolean;
  evidence?: Record<string, unknown>;
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
  action_events?: ActionExecutionEvent[];
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
  action_events?: ActionExecutionEvent[];
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
