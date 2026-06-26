import { tab } from './shared';
import type { CrmVerticalDefinition } from './types';

export const eventsTicketingVertical: CrmVerticalDefinition = {
  key: 'events_ticketing',
  label: 'Events & Ticketing',
  riskLevel: 'low',
  entityLabelSingular: 'event',
  entityLabelPlural: 'events',
  defaultPlanLabel: 'Events plan',
  clientTabs: [
    tab('overview', 'Overview'),
    tab('readiness', 'Readiness'),
    tab('catalog', 'Events'),
    tab('bookings', 'Ticketing'),
    tab('leads', 'Waitlists/Leads'),
    tab('activity', 'Conversations'),
    tab('prompt', 'Prompt'),
    tab('controls', 'Controls'),
  ],
  entityTypes: ['event', 'venue', 'performer', 'ticket_type', 'showtime', 'organizer'],
  readinessChecks: ['events', 'date_location', 'ticket_handoff', 'venue_maps', 'policies', 'organizer_contact'],
};
