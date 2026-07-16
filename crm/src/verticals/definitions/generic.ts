import { tab } from '../shared';
import type { CrmVerticalDefinition } from '../types';

export const genericVertical: CrmVerticalDefinition = {
  key: 'generic',
  label: 'Generic',
  riskLevel: 'medium',
  entityLabelSingular: 'item',
  entityLabelPlural: 'items',
  defaultPlanLabel: 'Generic AI plan',
  clientTabs: [
    tab('overview', 'Overview'),
    tab('readiness', 'Readiness'),
    tab('catalog', 'Knowledge'),
    tab('crawl', 'Sources'),
    tab('leads', 'Leads'),
    tab('activity', 'Conversations'),
    tab('prompt', 'Prompt'),
    tab('controls', 'Controls'),
  ],
  entityTypes: ['knowledge_item', 'service', 'article', 'faq', 'policy_page', 'contact'],
  readinessChecks: ['knowledge', 'sources', 'contact', 'policies', 'lead_capture'],
  actionTypes: ['SHOW_ENTITIES', 'SORT_ENTITIES', 'NAVIGATE_TO', 'CAPTURE_LEAD', 'HANDOFF_TO_HUMAN'],
};
