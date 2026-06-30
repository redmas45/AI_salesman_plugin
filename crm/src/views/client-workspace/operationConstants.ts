import type { ClientWorkspaceTabId } from '../../verticals/types';
import type { OperationStatus } from '../../types';

export type OperationFeedbackKind = 'readiness' | 'integration' | 'crawl';

export interface OperationFeedbackState {
  kind: OperationFeedbackKind;
  status: 'running' | 'complete' | 'failed';
  stageIndex: number;
  startedAt: number;
  message: string;
}

export const READINESS_OPERATION_STAGES = [
  'Preparing client context',
  'Loading latest adapter evidence',
  'Scanning website capabilities',
  'Comparing domain action contract',
  'Saving readiness report',
];

export const INTEGRATION_OPERATION_STAGES = [
  'Queueing setup run',
  'Crawling source website',
  'Discovering routes and actions',
  'Validating adapter behavior',
  'Running prompt checks',
  'Saving evidence',
];

export const CRAWL_OPERATION_STAGES = [
  'Queueing crawl job',
  'Connecting to website',
  'Reading pages and routes',
  'Extracting records and metadata',
  'Updating knowledge store',
  'Refreshing crawl report',
];

export function normalizeTimelineStatus(status: unknown) {
  const s = String(status || 'pending').toLowerCase();
  if (s === 'in_progress' || s === 'running') return 'running';
  if (s === 'completed' || s === 'complete' || s === 'done' || s === 'success') return 'complete';
  if (s === 'failed' || s === 'error') return 'failed';
  return 'pending';
}

export function operationStages(kind: OperationFeedbackKind) {
  switch (kind) {
    case 'readiness':
      return READINESS_OPERATION_STAGES;
    case 'integration':
      return INTEGRATION_OPERATION_STAGES;
    case 'crawl':
      return CRAWL_OPERATION_STAGES;
  }
}

export function operationLabel(kind: OperationFeedbackKind) {
  switch (kind) {
    case 'readiness':
      return 'Adapter Scan';
    case 'integration':
      return 'Setup & Validation';
    case 'crawl':
      return 'Site Crawl';
  }
}

export function operationResultTab(kind: OperationFeedbackKind): ClientWorkspaceTabId {
  switch (kind) {
    case 'readiness':
      return 'readiness';
    case 'integration':
      return 'integration';
    case 'crawl':
      return 'crawl';
  }
}

export function operationStepInterval(kind: OperationFeedbackKind) {
  switch (kind) {
    case 'readiness':
      return 1200;
    case 'integration':
      return 1800;
    case 'crawl':
      return 1500;
  }
}

export function minimumOperationDuration(kind: OperationFeedbackKind) {
  switch (kind) {
    case 'readiness':
      return 3000;
    case 'integration':
      return 8000;
    case 'crawl':
      return 5000;
  }
}

export function timestampMs(value: unknown) {
  if (!value) return 0;
  if (typeof value === 'number') return value > 9999999999 ? value : value * 1000;
  const parsed = Date.parse(String(value));
  return isNaN(parsed) ? 0 : parsed;
}

export function operationBelongsToFeedback(
  operation: OperationStatus | null | undefined,
  feedback: OperationFeedbackState | null | undefined
) {
  if (!operation || !feedback) return false;
  if (operation.kind !== feedback.kind) return false;
  const startedMs = timestampMs(operation.started_at);
  if (!startedMs) return true;
  return Math.abs(startedMs - feedback.startedAt) < 15000;
}

export function operationMinimumRemainingMs(feedback: OperationFeedbackState) {
  const minDuration = minimumOperationDuration(feedback.kind);
  const elapsed = Date.now() - feedback.startedAt;
  return Math.max(0, minDuration - elapsed);
}
