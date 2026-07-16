import { tab } from '../shared';
import type { CrmVerticalDefinition } from '../types';

export const automotiveVertical: CrmVerticalDefinition = {
  key: 'automotive',
  label: 'Automotive',
  riskLevel: 'medium',
  entityLabelSingular: 'vehicle',
  entityLabelPlural: 'vehicles',
  defaultPlanLabel: 'Automotive plan',
  clientTabs: [
    tab('overview', 'Overview'),
    tab('readiness', 'Readiness'),
    tab('catalog', 'Vehicles'),
    tab('calculators', 'Finance'),
    tab('leads', 'Test Drives'),
    tab('activity', 'Conversations'),
    tab('prompt', 'Prompt'),
    tab('controls', 'Controls'),
  ],
  entityTypes: ['vehicle_listing', 'vehicle_model', 'trim', 'dealer', 'finance_offer', 'test_drive_slot'],
  readinessChecks: ['vehicles', 'specs', 'dealer_contact', 'test_drive', 'finance', 'freshness'],
};
