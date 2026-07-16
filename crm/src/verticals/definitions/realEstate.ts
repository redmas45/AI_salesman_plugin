import { tab } from '../shared';
import type { CrmVerticalDefinition } from '../types';

export const realEstateVertical: CrmVerticalDefinition = {
  key: 'real_estate',
  label: 'Real Estate',
  riskLevel: 'medium',
  entityLabelSingular: 'listing',
  entityLabelPlural: 'listings',
  defaultPlanLabel: 'Real estate plan',
  clientTabs: [
    tab('overview', 'Overview'),
    tab('readiness', 'Readiness'),
    tab('catalog', 'Listings'),
    tab('leads', 'Viewings/Leads'),
    tab('compliance', 'Compliance'),
    tab('activity', 'Conversations'),
    tab('prompt', 'Prompt'),
    tab('controls', 'Controls'),
  ],
  entityTypes: ['property_listing', 'development_project', 'agent', 'locality', 'amenity'],
  readinessChecks: ['listings', 'location', 'lead_flow', 'maps', 'freshness', 'compliance'],
};
