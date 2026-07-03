/* eslint-disable react-hooks/purity */
/* eslint-disable react-refresh/only-export-components */
import { Gauge, Square } from 'lucide-react';
import type { Client, OperationStatus, OperationStatusResponse } from '../../types';
import { Button } from '../../components/ui/Button';
import { number } from '../../utils/format';
import type { ClientWorkspaceTabId } from '../../verticals/types';

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

export function OperatorRunSummary({
  feedback,
  backendOperation,
}: {
  feedback: OperationFeedbackState | null;
  backendOperation: OperationStatus | null;
}) {
  if (!feedback && !backendOperation) return null;
  const kind = feedback?.kind ?? (backendOperation?.kind as OperationFeedbackKind | undefined);
  if (!kind) return null;
  const status = feedback?.status || normalizeTimelineStatus(backendOperation?.status);
  if (status === 'pending') return null;
  const useBackend = shouldUseBackendOperation(backendOperation, feedback);
  const stages = useBackend
    ? backendOperation.stages.map((stage) => ({
        label: stage.label || stage.name,
        status: normalizeTimelineStatus(stage.status),
        message: stage.message || stage.status,
      }))
    : operationStages(kind).map((stage, index) => ({
        label: stage,
        status: feedback ? localStageStatus(index, feedback) : 'pending',
        message: feedback && index === feedback.stageIndex ? feedback.message : stage,
      }));
  const progress = useBackend
    ? Math.max(0, Math.min(100, Number(backendOperation.progress || 0)))
    : feedback?.status === 'complete'
    ? 100
    : feedback
    ? Math.min(94, Math.round(((feedback.stageIndex + 1) / stages.length) * 100))
    : 0;
  const elapsedSeconds = feedback
    ? Math.max(0, Math.round((Date.now() - feedback.startedAt) / 1000))
    : Math.max(0, Math.round(Number(backendOperation?.duration_ms ?? 0) / 1000));
  const remainingSeconds = feedback ? estimatedRemainingSeconds(kind, elapsedSeconds, progress, status) : 0;
  const activeStage = stages.find((stage) => stage.status === 'running') ?? stages.find((stage) => stage.status !== 'complete');
  const completedStages = stages.filter((stage) => stage.status === 'complete').length;
  return (
    <div className={`operator-run-summary ${status}`} aria-live={status === 'running' ? 'polite' : undefined}>
      <div className="operator-run-summary-head">
        <span>{status === 'running' ? 'Live progress' : status}</span>
        <strong>{number(progress)}%</strong>
      </div>
      <div className="operator-run-progress" aria-label={`${progress}% complete`}>
        <span style={{ width: `${progress}%` }} />
      </div>
      <p>{activeStage?.message || activeStage?.label || backendOperation?.message || feedback?.message}</p>
      <div className="operator-run-meta">
        <span>{number(completedStages)}/{number(stages.length)} stages</span>
        {elapsedSeconds ? <span>{number(elapsedSeconds)}s elapsed</span> : null}
        {remainingSeconds ? <span>~{number(remainingSeconds)}s left</span> : null}
      </div>
    </div>
  );
}

export function OperationFeedbackPanel({
  feedback,
  backendOperation,
  onViewResult,
  onRetry,
  onCancel,
  onDismiss,
}: {
  feedback: OperationFeedbackState | null;
  backendOperation: OperationStatus | null;
  onViewResult: (tabId: ClientWorkspaceTabId) => void;
  onRetry: (kind: OperationFeedbackKind) => void;
  onCancel?: (kind: OperationFeedbackKind) => void;
  onDismiss: () => void;
}) {
  if (!feedback) return null;
  const useBackend = shouldUseBackendOperation(backendOperation, feedback);
  const stageViews = useBackend
    ? backendOperation.stages.map((stage) => ({
        label: stage.label || stage.name,
        status: normalizeTimelineStatus(stage.status),
        message: stage.message || stage.status,
      }))
    : operationStages(feedback.kind).map((stage, index) => ({
        label: stage,
        status: localStageStatus(index, feedback),
        message: localStageStatus(index, feedback) === 'running' ? 'Running now' : localStageStatus(index, feedback),
      }));
  const elapsedSeconds = Math.max(0, Math.round((Date.now() - feedback.startedAt) / 1000));
  const status = useBackend ? normalizeTimelineStatus(backendOperation.status) : feedback.status;
  const message = useBackend ? backendOperation.message || feedback.message : feedback.message;
  const progress = useBackend
    ? Math.max(0, Math.min(100, Number(backendOperation.progress || 0)))
    : feedback.status === 'complete'
    ? 100
    : Math.min(94, Math.round(((feedback.stageIndex + 1) / stageViews.length) * 100));
  const resultTab = (useBackend ? backendOperation.result_tab : operationResultTab(feedback.kind)) as ClientWorkspaceTabId;
  const startedAtLabel = useBackend && backendOperation.started_at
    ? new Date(backendOperation.started_at).toLocaleTimeString()
    : new Date(feedback.startedAt).toLocaleTimeString();
  const remainingSeconds = estimatedRemainingSeconds(feedback.kind, elapsedSeconds, progress, status);
  const nextStage = stageViews.find((stage) => stage.status === 'pending')?.label ?? stageViews[Math.min(feedback.stageIndex + 1, stageViews.length - 1)]?.label;
  const logs = useBackend && backendOperation.logs.length
    ? backendOperation.logs
    : [
        `Started at ${startedAtLabel}.`,
        `Current task: ${message}.`,
        ...(status === 'running' && nextStage ? [`Next task: ${nextStage}.`] : []),
        ...(status === 'complete' ? [`Result is ready in the ${operationResultLabel(feedback.kind)} workspace.`] : []),
        ...(status === 'failed' ? ['Retry is available from this monitor.'] : []),
      ];
  return (
    <section className={`client-run-monitor ${status}`} aria-live="polite">
      <div className="operation-monitor-head">
        <div className="operation-monitor-title">
          <Gauge className={status === 'running' ? 'spin' : ''} size={18} aria-hidden="true" />
          <div>
            <strong>{useBackend ? backendOperation.label : operationLabel(feedback.kind)}</strong>
            <span>{status === 'running' ? message : status === 'complete' ? 'Output saved and ready to review.' : message}</span>
          </div>
        </div>
        <div className="operation-monitor-meta">
          <span>{status}</span>
          <span>{elapsedSeconds}s elapsed</span>
          {remainingSeconds ? <span>~{remainingSeconds}s left</span> : null}
          <span>Started {startedAtLabel}</span>
        </div>
      </div>
      <div className="operation-monitor-body">
        <div className="operation-progress" aria-label={`${progress}% complete`}>
          <span style={{ width: `${progress}%` }} />
        </div>
        <ol className="operation-timeline">
          {stageViews.map((stage, index) => (
            <li key={`${stage.label}-${index}`} className={operationStageClass(stage.status)}>
              <span className="operation-stage-marker" aria-hidden="true" />
              <div>
                <strong>{stage.label}</strong>
                <span>
                  {stage.status === 'complete' ? 'Done' : stage.status === 'pending' ? 'Waiting' : stage.message}
                </span>
              </div>
            </li>
          ))}
        </ol>
        <details className="operation-log">
          <summary>Operation log</summary>
          <ul>
            {logs.map((log) => <li key={log}>{log}</li>)}
          </ul>
        </details>
        <div className="operation-monitor-actions">
          {status === 'running' || status === 'complete' ? (
            <Button variant="secondary" size="sm" onClick={() => onViewResult(resultTab)}>
              {status === 'running' ? 'Open live output' : 'View result'}
            </Button>
          ) : null}
          {status === 'running' && feedback.kind === 'integration' && onCancel ? (
            <Button icon={Square} variant="danger" size="sm" onClick={() => onCancel(feedback.kind)}>
              Stop setup
            </Button>
          ) : null}
          {status === 'failed' ? (
            <Button variant="secondary" size="sm" onClick={() => onRetry(feedback.kind)}>
              Retry
            </Button>
          ) : null}
          {status !== 'running' ? (
            <Button variant="ghost" size="sm" onClick={onDismiss}>
              Dismiss
            </Button>
          ) : null}
        </div>
      </div>
    </section>
  );
}

export function firstRunningOperation(status: OperationStatusResponse | null) {
  if (!status) return null;
  return (['integration', 'crawl', 'readiness'] as const)
    .map((kind) => status.operations[kind])
    .find((operation) => normalizeTimelineStatus(operation?.status) === 'running') ?? null;
}

export function operationOutputValue(operation: OperationStatus | null, fallback: string) {
  if (!operation) return fallback;
  const status = normalizeTimelineStatus(operation.status);
  if (status === 'running') return `${number(operation.progress)}% running`;
  if (status === 'complete') return 'saved';
  if (status === 'failed') return 'failed';
  if (status === 'skipped') return 'skipped';
  return fallback;
}

export function outputTone(operation: OperationStatus | null) {
  const status = normalizeTimelineStatus(operation?.status);
  if (status === 'complete') return 'ok';
  if (status === 'running') return 'live';
  if (status === 'failed') return 'bad';
  if (status === 'skipped') return 'warn';
  return 'idle';
}

export function operatorNextStep(client: Client, status: OperationStatusResponse | null, automationLocked: boolean) {
  if (automationLocked) return 'Review discovery details, website, and owner panel; activate when this site should become a managed client.';
  const integration = status?.operations.integration;
  if (normalizeTimelineStatus(integration?.status) === 'pending') return 'Run setup to build the first crawl, flow, readiness, and prompt evidence set.';
  if (client.catalog.missing_embeddings > 0) return 'Crawl or run setup to refresh records and repair missing vectors.';
  if (normalizeTimelineStatus(status?.operations.readiness?.status) === 'pending') return 'Run setup before a client demo so readiness gaps are visible.';
  return 'Use the action cards when the source website changes, before demos, or when evidence looks stale.';
}

function isUsefulBackendOperation(operation: OperationStatus | null): operation is OperationStatus {
  if (!operation) return false;
  if (operation.status !== 'pending') return true;
  return operation.stages.some((stage) => normalizeTimelineStatus(stage.status) !== 'pending');
}

function shouldUseBackendOperation(
  operation: OperationStatus | null,
  feedback: OperationFeedbackState | null,
): operation is OperationStatus {
  if (!isUsefulBackendOperation(operation)) return false;
  if (!feedback || feedback.status !== 'running') return true;
  return operationBelongsToFeedback(operation, feedback);
}

export function operationBelongsToFeedback(
  operation: OperationStatus | null | undefined,
  feedback: OperationFeedbackState,
) {
  if (!operation) return false;
  const status = normalizeTimelineStatus(operation.status);
  if (status === 'pending') return false;
  if (status === 'running') return true;
  const startedAt = timestampMs(operation.started_at);
  const completedAt = timestampMs(operation.completed_at);
  const operationTimestamp = completedAt || startedAt;
  if (!operationTimestamp) return false;
  return operationTimestamp >= feedback.startedAt - 1000;
}

function localStageStatus(index: number, feedback: OperationFeedbackState) {
  if (index < feedback.stageIndex) return 'complete';
  if (index === feedback.stageIndex) return feedback.status;
  return 'pending';
}

export function normalizeTimelineStatus(status: unknown) {
  const normalized = String(status || '').toLowerCase();
  if (normalized === 'ok' || normalized === 'completed' || normalized === 'success') return 'complete';
  if (normalized === 'error') return 'failed';
  if (normalized === 'skipped') return 'skipped';
  if (normalized === 'running' || normalized === 'complete' || normalized === 'failed' || normalized === 'pending') return normalized;
  return 'pending';
}

export function timestampMs(value: unknown) {
  const timestamp = Date.parse(String(value || ''));
  return Number.isFinite(timestamp) ? timestamp : 0;
}

export function operationStages(kind: OperationFeedbackKind) {
  if (kind === 'readiness') return READINESS_OPERATION_STAGES;
  if (kind === 'crawl') return CRAWL_OPERATION_STAGES;
  return INTEGRATION_OPERATION_STAGES;
}

export function operationLabel(kind: OperationFeedbackKind) {
  if (kind === 'readiness') return 'Readiness scan';
  if (kind === 'crawl') return 'Crawler run';
  return 'Setup run';
}

export function operationResultTab(kind: OperationFeedbackKind): ClientWorkspaceTabId {
  if (kind === 'readiness') return 'readiness';
  if (kind === 'crawl') return 'crawl';
  return 'integration';
}

function operationResultLabel(kind: OperationFeedbackKind) {
  if (kind === 'readiness') return 'Readiness';
  if (kind === 'crawl') return 'Crawl';
  return 'Setup';
}

export function operationStepInterval(kind: OperationFeedbackKind) {
  if (kind === 'readiness') return 700;
  if (kind === 'crawl') return 900;
  return 1200;
}

export function minimumOperationDuration(kind: OperationFeedbackKind) {
  const animatedMinimumMs = operationStages(kind).length * operationStepInterval(kind) + 350;
  if (kind === 'readiness') return Math.max(animatedMinimumMs, 6500);
  if (kind === 'crawl') return Math.max(animatedMinimumMs, 8500);
  return Math.max(animatedMinimumMs, 11000);
}

export function operationMinimumRemainingMs(feedback: OperationFeedbackState) {
  return Math.max(0, minimumOperationDuration(feedback.kind) - (Date.now() - feedback.startedAt));
}

function estimatedRemainingSeconds(
  kind: OperationFeedbackKind,
  elapsedSeconds: number,
  progress: number,
  status: string,
) {
  if (status !== 'running') return 0;
  const minimumSeconds = Math.ceil(minimumOperationDuration(kind) / 1000);
  const progressRatio = Math.max(0.08, Math.min(0.95, progress / 100));
  const estimatedTotalSeconds = Math.max(minimumSeconds, Math.ceil(elapsedSeconds / progressRatio));
  return Math.max(1, estimatedTotalSeconds - elapsedSeconds);
}

function operationStageClass(status: string) {
  if (status === 'complete') return 'done';
  return status;
}
