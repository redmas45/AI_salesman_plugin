import { tab } from '../shared';
import type { CrmVerticalDefinition } from '../types';

export const financeBrokerVertical: CrmVerticalDefinition = {
  key: 'finance_broker',
  label: 'Finance Broker',
  riskLevel: 'high',
  entityLabelSingular: 'financial product',
  entityLabelPlural: 'financial products',
  defaultPlanLabel: 'Finance broker plan',
  clientTabs: [
    tab('overview', 'Overview'),
    tab('readiness', 'Readiness'),
    tab('catalog', 'Products'),
    tab('calculators', 'Calculators'),
    tab('leads', 'Leads'),
    tab('compliance', 'Compliance'),
    tab('activity', 'Conversations'),
    tab('prompt', 'Prompt'),
    tab('controls', 'Controls'),
  ],
  entityTypes: ['financial_product', 'loan_product', 'rate_table', 'calculator', 'disclosure', 'advisor'],
  readinessChecks: ['products', 'rates', 'calculators', 'disclosures', 'application_flow', 'lead_capture'],
};
