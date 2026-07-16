import { tab } from '../shared';
import type { CrmVerticalDefinition } from '../types';

export const constructionVertical: CrmVerticalDefinition = {
  key: 'construction',
  label: 'Construction',
  riskLevel: 'medium',
  entityLabelSingular: 'service',
  entityLabelPlural: 'services',
  defaultPlanLabel: 'Construction plan',
  clientTabs: [
    tab('overview', 'Overview'),
    tab('readiness', 'Readiness'),
    tab('catalog', 'Services'),
    tab('leads', 'Estimates'),
    tab('activity', 'Conversations'),
    tab('prompt', 'Prompt'),
    tab('controls', 'Controls'),
  ],
  entityTypes: ['construction_service', 'project', 'service_area', 'estimate_flow', 'contractor', 'warranty'],
  readinessChecks: ['services', 'projects', 'estimate_flow', 'contact', 'service_area', 'lead_capture'],
};
