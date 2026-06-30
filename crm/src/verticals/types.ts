import type { LucideIcon } from 'lucide-react';

export type ClientWorkspaceTabId =
  | 'overview'
  | 'integration'
  | 'readiness'
  | 'catalog'
  | 'crawl'
  | 'activity'
  | 'adapter'
  | 'controls'
  | 'quote_flows'
  | 'bookings'
  | 'appointments'
  | 'calculators'
  | 'documents'
  | 'leads'
  | 'compliance'
  | 'prompt';

export type VerticalRiskLevel = 'low' | 'medium' | 'high';

export interface ClientWorkspaceTabDefinition {
  id: ClientWorkspaceTabId;
  label: string;
  icon: LucideIcon;
}

export interface CrmVerticalDefinition {
  key: string;
  label: string;
  riskLevel: VerticalRiskLevel;
  entityLabelSingular: string;
  entityLabelPlural: string;
  defaultPlanLabel: string;
  clientTabs: ClientWorkspaceTabDefinition[];
  entityTypes: string[];
  readinessChecks: string[];
  actionTypes?: string[];
}
