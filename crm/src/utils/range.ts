export const RANGE_OPTIONS = [
  ['1d', 'Last 1 day'],
  ['3d', 'Last 3 days'],
  ['7d', 'Last 7 days'],
  ['15d', 'Last 15 days'],
  ['30d', 'Last 30 days'],
  ['3m', 'Last 3 months'],
  ['6m', 'Last 6 months'],
  ['1y', 'Last 1 year'],
  ['all', 'All time'],
] as const;

export function rangeLabel(range: string) {
  return RANGE_OPTIONS.find(([value]) => value === range)?.[1] || 'Last 7 days';
}
