import { automotiveVertical } from './definitions/automotive';
import { constructionVertical } from './definitions/construction';
import { ecommerceVertical } from './definitions/ecommerce';
import { educationVertical } from './definitions/education';
import { eventsTicketingVertical } from './definitions/eventsTicketing';
import { financeBrokerVertical } from './definitions/financeBroker';
import { foodVertical } from './definitions/food';
import { genericVertical } from './definitions/generic';
import { healthcareVertical } from './definitions/healthcare';
import { insuranceVertical } from './definitions/insurance';
import { jobsRecruitingVertical } from './definitions/jobsRecruiting';
import { legalServicesVertical } from './definitions/legalServices';
import { realEstateVertical } from './definitions/realEstate';
import { travelVertical } from './definitions/travel';
import type { CrmVerticalDefinition } from './types';

export const DEFAULT_CRM_VERTICAL_KEY = 'generic';
export const CRM_VERTICALS: CrmVerticalDefinition[] = [
  genericVertical,
  ecommerceVertical,
  insuranceVertical,
  travelVertical,
  financeBrokerVertical,
  healthcareVertical,
  foodVertical,
  realEstateVertical,
  educationVertical,
  automotiveVertical,
  legalServicesVertical,
  jobsRecruitingVertical,
  eventsTicketingVertical,
  constructionVertical,
];

const VERTICALS_BY_KEY = new Map(CRM_VERTICALS.map((vertical) => [vertical.key, vertical]));

export function getCrmVertical(verticalKey?: string): CrmVerticalDefinition {
  const normalizedKey = normalizeVerticalKey(verticalKey) || DEFAULT_CRM_VERTICAL_KEY;
  return VERTICALS_BY_KEY.get(normalizedKey) ?? genericVertical;
}

export function normalizeVerticalKey(value?: string) {
  return String(value ?? '')
    .trim()
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '_')
    .replace(/_+/g, '_')
    .replace(/^_|_$/g, '');
}
