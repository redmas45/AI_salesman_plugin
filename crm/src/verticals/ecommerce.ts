import { tab } from './shared';
import type { CrmVerticalDefinition } from './types';

export const ecommerceVertical: CrmVerticalDefinition = {
  key: 'ecommerce',
  label: 'E-commerce',
  riskLevel: 'low',
  entityLabelSingular: 'product',
  entityLabelPlural: 'products',
  defaultPlanLabel: 'Commerce plan',
  clientTabs: [
    tab('overview', 'Overview'),
    tab('readiness', 'Readiness'),
    tab('catalog', 'Catalog'),
    tab('crawl', 'Crawl'),
    tab('activity', 'Activity'),
    tab('prompt', 'Prompt'),
    tab('controls', 'Controls'),
  ],
  entityTypes: ['product', 'category', 'brand', 'variant', 'offer', 'policy_page'],
  readinessChecks: ['catalog', 'variants', 'cart', 'checkout'],
};
