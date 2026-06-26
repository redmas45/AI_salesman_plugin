import { tab } from './shared';
import type { CrmVerticalDefinition } from './types';

export const legalServicesVertical: CrmVerticalDefinition = {
  key: 'legal_services',
  label: 'Legal Services',
  riskLevel: 'high',
  entityLabelSingular: 'service',
  entityLabelPlural: 'services',
  defaultPlanLabel: 'Legal services plan',
  clientTabs: [
    tab('overview', 'Overview'),
    tab('readiness', 'Readiness'),
    tab('catalog', 'Services'),
    tab('documents', 'Documents'),
    tab('leads', 'Intake/Leads'),
    tab('compliance', 'Compliance'),
    tab('activity', 'Conversations'),
    tab('prompt', 'Prompt'),
    tab('controls', 'Controls'),
  ],
  entityTypes: ['legal_service', 'lawyer', 'practice_area', 'document_template', 'jurisdiction'],
  readinessChecks: ['services', 'attorneys', 'jurisdictions', 'consultation', 'disclaimers', 'pricing'],
};
