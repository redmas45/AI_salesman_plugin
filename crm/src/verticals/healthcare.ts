import { tab } from './shared';
import type { CrmVerticalDefinition } from './types';

export const healthcareVertical: CrmVerticalDefinition = {
  key: 'healthcare',
  label: 'Healthcare',
  riskLevel: 'high',
  entityLabelSingular: 'provider',
  entityLabelPlural: 'providers',
  defaultPlanLabel: 'Healthcare plan',
  clientTabs: [
    tab('overview', 'Overview'),
    tab('readiness', 'Readiness'),
    tab('catalog', 'Providers'),
    tab('appointments', 'Appointments'),
    tab('leads', 'Leads'),
    tab('compliance', 'Compliance'),
    tab('activity', 'Conversations'),
    tab('prompt', 'Prompt'),
    tab('controls', 'Controls'),
  ],
  entityTypes: ['doctor', 'clinic', 'specialty', 'service_line', 'lab_test', 'health_article'],
  readinessChecks: ['providers', 'specialties', 'appointments', 'locations', 'privacy', 'emergency_notice'],
};
