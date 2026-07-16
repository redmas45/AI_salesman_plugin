import type { AnalyticsResponse } from '../../types';

export type HealthSignalKind = 'transport' | 'status' | 'latency';

export interface HealthSignalSelection {
  kind: HealthSignalKind;
  title: string;
  label: string;
  count: number;
}

export function defaultHealthSignal(analytics: AnalyticsResponse): HealthSignalSelection | null {
  const firstStatus = analytics.status_mix?.[0];
  if (firstStatus) return { kind: 'status', title: 'Status', label: firstStatus.label, count: firstStatus.count };
  const firstTransport = analytics.transport_mix?.[0];
  if (firstTransport) return { kind: 'transport', title: 'Transport', label: firstTransport.label, count: firstTransport.count };
  const firstLatency = analytics.latency_buckets?.[0];
  if (firstLatency) return { kind: 'latency', title: 'Latency', label: firstLatency.label, count: firstLatency.count };
  return null;
}
