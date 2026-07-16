import { RANGE_OPTIONS, RECENT_SESSION_LIMIT } from './constants';
import type { ConversationSession, DashboardResponse } from './types';

export interface ConversationPreview extends ConversationSession {
  date: string;
}

export function flattenedSessions(groups: DashboardResponse['conversations']['groups']): ConversationPreview[] {
  return groups
    .flatMap((group) => group.sessions.map((session) => ({ ...session, date: group.date })))
    .slice(0, RECENT_SESSION_LIMIT);
}

export function summaryLines(summary: string): string[] {
  const lines = summary
    .split(/\r?\n/)
    .map((line) => line.replace(/^[-*]\s+/, '').trim())
    .filter(Boolean);
  return lines.length ? lines : ['No customer conversations are logged for this range yet.'];
}

export function clientSlugFromUrl(): string {
  const parts: string[] = window.location.pathname.split('/').filter(Boolean);
  const baseParts: string[] = (import.meta.env.VITE_CLIENT_PANEL_BASE_PATH || '/client_panel/')
    .split('/')
    .filter(Boolean);
  const scopedParts = baseParts.every((part, index) => parts[index] === part)
    ? parts.slice(baseParts.length)
    : parts;
  const slug = scopedParts[0] || import.meta.env.VITE_DEFAULT_CLIENT_ID || 'site_1';
  return slug.replace(/-/g, '_');
}

export function rangeLabel(range: string): string {
  return RANGE_OPTIONS.find(([value]) => value === range)?.[1] || RANGE_OPTIONS[1][1];
}

export function percent(value: number, max: number): number {
  if (!max) return 0;
  return Math.max(0, Math.min(100, Math.round((value / max) * 100)));
}

export function shortSessionId(sessionId: string): string {
  if (sessionId.length <= 18) return sessionId;
  return `${sessionId.slice(0, 8)}...${sessionId.slice(-6)}`;
}

export function fmt(n: number | null | undefined, opts?: Intl.NumberFormatOptions): string {
  if (n == null) return '-';
  return new Intl.NumberFormat('en-US', opts).format(n);
}

export function number(value: unknown): string {
  return fmt(Number(value || 0));
}

export function normalizePositiveInteger(value: string): string {
  const normalized = Math.max(1, Math.round(Number(value)));
  return String(Number.isFinite(normalized) ? normalized : 1);
}
