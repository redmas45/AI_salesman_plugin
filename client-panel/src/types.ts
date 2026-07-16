export interface QuotaPart {
  used: number;
  limit: number;
  remaining: number;
}

export interface ClientSummary {
  site_id: string;
  name: string;
  store_url: string;
  status: string;
  plan: string;
  vertical_key?: string;
  vertical_label?: string;
  session_token_limit: number;
  usage: {
    total_turns: number;
    turns_today: number;
    tokens_estimated: number;
    avg_latency_ms: number;
  };
  quota: {
    client: QuotaPart;
    session: QuotaPart;
  };
  catalog: {
    active_products: number;
    total_products: number;
    categories: number;
  };
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

export interface Analytics {
  metrics: {
    turns: number;
    tokens: number;
    sessions?: number;
    avg_latency_ms: number;
    actions?: number;
    action_rate?: number;
    error_rate?: number;
    tokens_per_turn?: number;
  };
  summary: string;
  summary_source?: string;
  top_products: RankRow[];
  top_intents: RankRow[];
  status_mix?: RankRow[];
  transport_mix?: RankRow[];
  latency_buckets?: RankRow[];
  peak_day?: SeriesRow | null;
  series: SeriesRow[];
}

export interface IntegrationUnsupportedCheck {
  name: string;
  confidence: number;
  evidence: string;
}

export interface IntegrationSummary {
  status: 'ready' | 'watch' | 'needs_work' | 'pending' | string;
  score: number;
  next_action: string;
  active_records: number;
  missing_vectors: number;
  domain_actions: {
    supported: boolean;
    evidence: string;
    covered: number;
    total: number;
  };
  readiness: {
    supported: number;
    needs_work: number;
    unsupported: IntegrationUnsupportedCheck[];
    informational: IntegrationUnsupportedCheck[];
  };
  prompt_tests: {
    status: string;
    passed: number;
    failed: number;
    total: number;
    message: string;
  };
  automation: {
    flow_graph: boolean;
    flow_rehearsal: boolean;
    runtime_repairs_needed: number;
  };
}

export interface ConversationTurn {
  transcript: string;
  response_text: string;
  intent: string;
  tokens: number;
  latency_ms: number;
  created_at: string;
}

export interface ConversationSession {
  session_id: string;
  turns: ConversationTurn[];
}

export interface ConversationGroup {
  date: string;
  sessions: ConversationSession[];
}

export interface Conversations {
  groups: ConversationGroup[];
}

export interface DashboardResponse {
  client: ClientSummary;
  analytics: Analytics;
  conversations: Conversations;
  integration?: IntegrationSummary;
}
