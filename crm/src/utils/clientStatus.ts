import type { Client } from '../types';

export function clientRuntimeStatus(client: Client): string {
  return String(client.runtime_status?.status || 'unknown').toLowerCase();
}
