import type { ClientSummary } from './types';

export interface ClientPanelText {
  verticalLabel: string;
  customerSingular: string;
  customerPlural: string;
  entitySingular: string;
  entityPlural: string;
  dataLabel: string;
  dataTabLabel: string;
  dataHealthTitle: string;
  dataSignalsTitle: string;
  totalEntitiesLabel: string;
  activeEntitiesLabel: string;
  demandHeading: string;
  demandRankTitle: string;
  requestedEntitiesTitle: string;
  opportunityTitle: string;
  opportunityEmptyTitle: string;
  opportunityEmptyDetail: string;
  summaryTitle: string;
  simulatorTitle: string;
  simulatorLabel: string;
  simulatorPlaceholder: string;
  sessionLimitTitle: string;
  sessionLimitDetail: string;
}

const GENERIC_TEXT: ClientPanelText = {
  verticalLabel: 'Client',
  customerSingular: 'visitor',
  customerPlural: 'visitors',
  entitySingular: 'record',
  entityPlural: 'records',
  dataLabel: 'Data',
  dataTabLabel: 'Data',
  dataHealthTitle: 'Data health',
  dataSignalsTitle: 'Data signals',
  totalEntitiesLabel: 'Total records',
  activeEntitiesLabel: 'Active records',
  demandHeading: 'What visitors are asking about',
  demandRankTitle: 'Demand signals',
  requestedEntitiesTitle: 'Most requested records',
  opportunityTitle: 'Data opportunity map',
  opportunityEmptyTitle: 'No data opportunities yet',
  opportunityEmptyDetail: 'Demand priorities will appear after more visitor conversations.',
  summaryTitle: 'Client notes',
  simulatorTitle: 'Assistant question simulator',
  simulatorLabel: 'Visitor question',
  simulatorPlaceholder: 'Can you compare the best options for me?',
  sessionLimitTitle: 'Per visitor limit',
  sessionLimitDetail: 'Set the maximum each visitor/session can use.',
};

const TEXT_BY_VERTICAL: Record<string, Partial<ClientPanelText>> = {
  ecommerce: {
    verticalLabel: 'Store',
    customerSingular: 'shopper',
    customerPlural: 'shoppers',
    entitySingular: 'product',
    entityPlural: 'products',
    dataLabel: 'Catalog',
    dataTabLabel: 'Catalog',
    dataHealthTitle: 'Catalog health',
    dataSignalsTitle: 'Catalog signals',
    totalEntitiesLabel: 'Total products',
    activeEntitiesLabel: 'Active products',
    demandHeading: 'What shoppers are asking for',
    demandRankTitle: 'Product demand',
    requestedEntitiesTitle: 'Most requested products',
    opportunityTitle: 'Catalog opportunity map',
    opportunityEmptyTitle: 'No catalog opportunities yet',
    opportunityEmptyDetail: 'Product demand priorities will appear after more shopper conversations.',
    summaryTitle: 'Store notes',
    simulatorTitle: 'Ask my store simulator',
    simulatorLabel: 'Shopper question',
    simulatorPlaceholder: 'Do you have budget sneakers with cash on delivery?',
    sessionLimitTitle: 'Per shopper limit',
    sessionLimitDetail: 'Set the maximum each shopper/session can use.',
  },
  insurance: {
    verticalLabel: 'Insurance client',
    customerSingular: 'customer',
    customerPlural: 'customers',
    entitySingular: 'plan',
    entityPlural: 'plans',
    dataLabel: 'Plan data',
    dataTabLabel: 'Plan data',
    dataHealthTitle: 'Plan data health',
    dataSignalsTitle: 'Plan signals',
    totalEntitiesLabel: 'Total plans',
    activeEntitiesLabel: 'Active plans',
    demandHeading: 'What customers are asking about',
    demandRankTitle: 'Plan demand',
    requestedEntitiesTitle: 'Most requested plans',
    opportunityTitle: 'Plan opportunity map',
    opportunityEmptyTitle: 'No plan opportunities yet',
    opportunityEmptyDetail: 'Plan demand priorities will appear after more customer conversations.',
    summaryTitle: 'Insurance notes',
    simulatorTitle: 'Insurance question simulator',
    simulatorLabel: 'Customer question',
    simulatorPlaceholder: 'Compare health insurance for a 20 year old.',
    sessionLimitTitle: 'Per customer limit',
    sessionLimitDetail: 'Set the maximum each customer/session can use.',
  },
};

export function panelText(client?: Pick<ClientSummary, 'vertical_key' | 'vertical_label'>): ClientPanelText {
  const key = String(client?.vertical_key || '').trim().toLowerCase();
  return {
    ...GENERIC_TEXT,
    ...TEXT_BY_VERTICAL[key],
    verticalLabel: client?.vertical_label || TEXT_BY_VERTICAL[key]?.verticalLabel || GENERIC_TEXT.verticalLabel,
  };
}
