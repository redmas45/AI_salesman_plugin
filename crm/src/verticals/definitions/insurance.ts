import { tab } from '../shared';
import type { CrmVerticalDefinition } from '../types';

export const insuranceVertical: CrmVerticalDefinition = {
  key: 'insurance',
  label: 'Insurance',
  riskLevel: 'high',
  entityLabelSingular: 'plan',
  entityLabelPlural: 'plans',
  defaultPlanLabel: 'Insurance plan',
  clientTabs: [
    tab('overview', 'Overview'),
    tab('readiness', 'Readiness'),
    tab('catalog', 'Plans'),
    tab('quote_flows', 'Quotes'),
    tab('leads', 'Leads'),
    tab('compliance', 'Compliance'),
    tab('activity', 'Conversations'),
    tab('prompt', 'Prompt'),
    tab('controls', 'Controls'),
  ],
  entityTypes: ['insurance_plan', 'insurer', 'coverage_feature', 'claim_flow', 'document_requirement'],
  readinessChecks: ['plans', 'quote_flow', 'claims', 'renewals', 'disclosures', 'lead_capture'],
  actionTypes: ['SHOW_ENTITIES', 'COMPARE_ENTITIES', 'SORT_ENTITIES', 'START_QUOTE', 'CAPTURE_LEAD', 'HANDOFF_TO_AGENT'],
};
