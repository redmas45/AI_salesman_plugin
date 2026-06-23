import type { Client } from '../types';

const CONFIDENCE_PERCENT = 100;

export function fmt(n: number | null | undefined, opts?: Intl.NumberFormatOptions): string {
  if (n == null) return '-';
  return new Intl.NumberFormat('en-US', opts).format(n);
}

export function number(value: unknown) {
  return fmt(Number(value || 0));
}

export function percent(value: unknown) {
  const numericValue = Number(value || 0);
  const normalizedValue = numericValue <= 1 ? numericValue * CONFIDENCE_PERCENT : numericValue;
  return Math.round(Math.max(0, Math.min(CONFIDENCE_PERCENT, normalizedValue)));
}

export function money(value: unknown) {
  return `$${Number(value || 0).toFixed(2)}`;
}

export function shortTime(value?: string | null) {
  if (!value) return '-';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return String(value).slice(0, 19);
  return date.toLocaleString([], { dateStyle: 'short', timeStyle: 'short' });
}

export function labelize(value: string) {
  return value.replace(/_/g, ' ').replace(/\b\w/g, (letter) => letter.toUpperCase());
}

export function healthState(value?: string) {
  const text = String(value || '').toLowerCase();
  if (text === 'up' || text === 'ready' || text === 'ok') return 'up';
  if (text === 'slow' || text === 'degraded' || text === 'warn' || text === 'warning') return 'warn';
  return 'down';
}

export function statusClass(value: string) {
  const text = String(value || '').toLowerCase();
  if (['live', 'ok', 'up', 'ready', 'vectorized', 'hub running', 'supported'].includes(text)) return 'ok';
  if (['crawling', 'running', 'slow', 'pending vector', 'needs work'].includes(text)) return 'warn';
  if (['disabled', 'offline', 'down', 'error', 'hub degraded', 'failed'].includes(text)) return 'bad';
  return 'neutral';
}

export function panelPasswordLabel(client: Client) {
  const status = String(client.panel_password_status || '').toLowerCase();
  if (status === 'revoked') return 'revoked';
  if (client.panel_password_configured || status === 'configured') return 'configured';
  return 'not configured';
}
