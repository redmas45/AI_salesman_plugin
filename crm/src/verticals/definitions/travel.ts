import { tab } from '../shared';
import type { CrmVerticalDefinition } from '../types';

export const travelVertical: CrmVerticalDefinition = {
  key: 'travel',
  label: 'Travel',
  riskLevel: 'medium',
  entityLabelSingular: 'travel item',
  entityLabelPlural: 'travel items',
  defaultPlanLabel: 'Travel plan',
  clientTabs: [
    tab('overview', 'Overview'),
    tab('readiness', 'Readiness'),
    tab('catalog', 'Inventory'),
    tab('bookings', 'Bookings'),
    tab('leads', 'Leads'),
    tab('activity', 'Conversations'),
    tab('prompt', 'Prompt'),
    tab('controls', 'Controls'),
  ],
  entityTypes: ['destination', 'hotel', 'room', 'flight', 'package', 'activity', 'itinerary'],
  readinessChecks: ['inventory', 'availability', 'booking_handoff', 'policies', 'lead_capture'],
};
