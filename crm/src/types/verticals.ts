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

export interface UniversalInstallerResponse {
  script_tag: string;
  script_url: string;
  mode: string;
}
