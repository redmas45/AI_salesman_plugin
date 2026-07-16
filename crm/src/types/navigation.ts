export type View =
  | 'dashboard'
  | 'clients'
  | 'client-detail'
  | 'catalogs'
  | 'usage'
  | 'conversations'
  | 'analytics'
  | 'adapters'
  | 'settings'
  | 'health';

export type Theme = 'light' | 'dark';

export type ClientBoardSection = 'all' | 'current' | 'available' | 'online' | 'offline';

export type AnalyticsSectionId = 'overview' | 'quality' | 'details';
