export const DEFAULT_RANGE = '7d';
export const RECENT_SESSION_LIMIT = 20;
export const TREND_BAR_LIMIT = 14;

export const RANGE_OPTIONS = [
  ['1d', '1 day'],
  ['7d', '7 days'],
  ['30d', '30 days'],
  ['3m', '3 months'],
  ['all', 'All time'],
] as const;

export const DASHBOARD_TABS = [
  ['overview', 'Overview'],
  ['demand', 'Demand'],
  ['conversations', 'Conversations'],
  ['catalog', 'Catalog'],
  ['policy', 'Token policy'],
] as const;

export type DashboardTab = (typeof DASHBOARD_TABS)[number][0];
