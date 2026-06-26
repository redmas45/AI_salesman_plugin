import { tab } from './shared';
import type { CrmVerticalDefinition } from './types';

export const foodVertical: CrmVerticalDefinition = {
  key: 'food',
  label: 'Food',
  riskLevel: 'low',
  entityLabelSingular: 'menu item',
  entityLabelPlural: 'menu items',
  defaultPlanLabel: 'Food ordering plan',
  clientTabs: [
    tab('overview', 'Overview'),
    tab('readiness', 'Readiness'),
    tab('catalog', 'Menu'),
    tab('crawl', 'Sources'),
    tab('leads', 'Orders/Leads'),
    tab('activity', 'Conversations'),
    tab('prompt', 'Prompt'),
    tab('controls', 'Controls'),
  ],
  entityTypes: ['restaurant', 'menu_item', 'grocery_item', 'cuisine', 'offer', 'delivery_zone'],
  readinessChecks: ['menu', 'location', 'delivery_zone', 'cart', 'checkout', 'dietary_data'],
};
