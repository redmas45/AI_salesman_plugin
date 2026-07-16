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
    action_policy?: Record<string, unknown>;
    action_events?: Array<Record<string, unknown>>;
    action_health?: Record<string, unknown>;
    action_proposals?: Array<Record<string, unknown>>;
    action_proposal_reviews?: Array<Record<string, unknown>>;
    action_repairs?: Array<Record<string, unknown>>;
    action_reviews?: Array<Record<string, unknown>>;
    flow_repair_proposals?: Array<Record<string, unknown>>;
    flow_repair_reviews?: Array<Record<string, unknown>>;
    policy_events?: Array<Record<string, unknown>>;
    interaction_events?: Array<Record<string, unknown>>;
    action_candidates?: Array<Record<string, unknown>>;
    prompt_suggestions?: string[];
    intake_questions?: Array<Record<string, unknown>>;
    action_readiness?: Array<Record<string, unknown>>;
    discovery?: Record<string, unknown>;
    validation?: Record<string, unknown>;
    initialization?: Record<string, unknown>;
    flow?: Record<string, unknown>;
    barriers?: Record<string, unknown>;
    rehearsal?: Record<string, unknown>;
    regression?: Record<string, unknown>;
    runtime_capabilities?: Record<string, unknown>;
    selectors?: Record<string, unknown>;
    selector_confidence?: number;
    selector_validated?: boolean;
  };
}

export interface AdapterConfigResponse {
  runtime_config: AdapterRuntimeConfig;
  adapter_code: string;
}

export interface FlowReport {
  site_id: string;
  site_url: string;
  vertical_key: string;
  detected_vertical_key: string;
  confidence: number;
  engine: string;
  pages: Array<Record<string, unknown>>;
  actions: Array<Record<string, unknown>>;
  routes: Record<string, string>;
  adapter_actions: Record<string, unknown>;
  prompt_suggestions: string[];
  barriers: Record<string, unknown>;
  summary: Record<string, unknown>;
  discovered_at: string;
  duration_ms: number;
}

export interface FlowDiscoveryResponse {
  flow: FlowReport;
  runtime_config: AdapterRuntimeConfig;
  adapter_code: string;
}

export interface FlowRehearsalReport {
  site_id: string;
  site_url: string;
  engine: string;
  steps: Array<Record<string, unknown>>;
  summary: Record<string, unknown>;
  rehearsed_at: string;
  duration_ms: number;
}

export interface FlowRehearsalResponse {
  rehearsal: FlowRehearsalReport;
  runtime_config: AdapterRuntimeConfig;
  adapter_code: string;
}

export interface FlowRegressionReport {
  site_id: string;
  site_url: string;
  status: string;
  summary: Record<string, unknown>;
  changes: Array<Record<string, unknown>>;
  compared_at: string;
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
