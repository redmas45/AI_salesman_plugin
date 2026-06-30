import { automotiveVertical } from './automotive';
import { constructionVertical } from './construction';
import { ecommerceVertical } from './ecommerce';
import { educationVertical } from './education';
import { eventsTicketingVertical } from './eventsTicketing';
import { financeBrokerVertical } from './financeBroker';
import { foodVertical } from './food';
import { genericVertical } from './generic';
import { healthcareVertical } from './healthcare';
import { insuranceVertical } from './insurance';
import { jobsRecruitingVertical } from './jobsRecruiting';
import { legalServicesVertical } from './legalServices';
import { realEstateVertical } from './realEstate';
import { travelVertical } from './travel';
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
