import { useState } from 'react';
import { AlertTriangle, CheckCircle2, Gauge, XCircle } from 'lucide-react';
import type { CapabilitiesSummary, Client, OperationStatus, OperationStatusResponse, ReadinessReport } from '../../../types';
import type { CrmVerticalDefinition } from '../../../verticals/types';
import { Button } from '../../../components/ui/Button';
import { Panel } from '../../../components/ui/Panel';
import { StatusPill } from '../../../components/ui/Badge';
import { EmptyState } from '../../../components/ui/EmptyState';
import { NoticeBanner } from '../../../components/shared/NoticeBanner';
import { TechnicalDetails } from '../../../components/shared/TechnicalDetails';
import { labelize, number, percent } from '../../../utils/format';
import { ActionChipGrid } from '../components/actionChips';
import { automationHintForCapability, isBlockingCapabilityGap, readinessGapRows } from '../evidence/readinessHelpers';
import { KeyValue } from '../components/workspaceCards';
import {
  OperatorRunSummary,
  READINESS_OPERATION_STAGES,
  minimumOperationDuration,
  normalizeTimelineStatus,
  operationBelongsToFeedback,
  type OperationFeedbackState,
} from '../operations/OperationFeedback';
export function ClientReadinessTab({
  capabilities,
  scanReport,
  scanning,
  operationFeedback,
  operationStatus,
  sourceReachable,
  sourceStatus,
  automationLocked,
  onRunSetup,
  vertical,
}: {
  client: Client;
  capabilities: CapabilitiesSummary | null;
  scanReport: ReadinessReport | null;
  scanning: boolean;
  operationFeedback: OperationFeedbackState | null;
  operationStatus: OperationStatusResponse | null;
  sourceReachable: boolean;
  sourceStatus: string;
  automationLocked: boolean;
  onRunSetup: () => void;
  vertical: CrmVerticalDefinition;
}) {
  const [filter, setFilter] = useState<'needs' | 'supported' | 'all'>('needs');
  const rows = scanReport?.capabilities ?? [];
  const supported = rows.filter((capability) => capability.supported);
  const unsupported = rows.filter(isBlockingCapabilityGap);
  const unsupportedNonDomain = readinessGapRows(scanReport);
  const filteredRows = filter === 'all'
    ? rows
    : filter === 'supported'
    ? supported
    : unsupported;
  const confidence = percent(scanReport?.platform_confidence ?? capabilities?.platform_confidence ?? 0);
  const platform = String(scanReport?.platform || capabilities?.platform || 'unknown');
  const latestScanUnreachable = Boolean(scanReport && platform.toLowerCase() === 'unreachable');
  const readinessFeedback = operationFeedback?.kind === 'readiness' ? operationFeedback : null;
  const readinessOperation = operationStatus?.operations.readiness ?? null;
  return (
    <div className="tab-content fade-in">
      <section className="section-row">
        <div>
          <h2 className="text-base font-semibold">Readiness checks</h2>
          <p className="mt-1 text-sm text-muted">
            Current capability evidence for {vertical.entityLabelPlural}, source coverage, handoff points, and allowed actions.
          </p>
        </div>
        <Button variant="secondary" disabled={scanning || automationLocked || !sourceReachable} icon={Gauge} onClick={onRunSetup}>
          {scanning ? 'Setup running...' : 'Run setup'}
        </Button>
      </section>
      {!automationLocked && !sourceReachable ? (
        <NoticeBanner
          tone="info"
          message={`Setup is locked because the source website is ${sourceStatus}. Start the website and refresh AI Hub first. Owner panel remains available.`}
        />
      ) : null}
      <ReadinessRunConsole
        feedback={readinessFeedback}
        operation={readinessOperation}
        scanReport={scanReport}
        automationLocked={automationLocked}
      />
      <div className="readiness-summary-grid">
        <section className="card readiness-score-card">
          <span className="kpi-label">Readiness picture</span>
          <strong className="kpi-value">{latestScanUnreachable ? 'unreachable' : scanReport ? `${supported.length}/${rows.length}` : '-'}</strong>
          <p className="text-sm text-muted">
            {latestScanUnreachable
              ? 'Latest scan was saved, but the scanner could not reach the source website.'
              : rows.length
              ? `${unsupported.length} check(s) need work. ${confidence}% platform confidence.`
              : scanReport
              ? 'Latest scan saved no capability rows. Run setup if source and adapter evidence changed.'
              : 'Run setup to save the first readiness evidence set.'}
          </p>
        </section>
        <Panel title="Scan summary">
          <KeyValue label="Platform" value={platform} />
          <KeyValue label="Supported" value={supported.length} />
          <KeyValue label="Needs work" value={unsupported.length} />
          <KeyValue label="Domain" value={vertical.label} />
          <KeyValue label="Allowed actions" value={capabilities?.allowed_actions.length ?? 0} />
        </Panel>
        <Panel title="Next operator step">
          <div className="readiness-next-step">
            <StatusPill value={automationLocked ? 'available' : latestScanUnreachable || unsupported.length ? 'needs work' : rows.length ? 'ready' : 'pending'} />
            <strong>{readinessNextStep(rows.length, unsupported.length, automationLocked, latestScanUnreachable, Boolean(scanReport))}</strong>
            <p>
              {automationLocked
                ? 'Move this install to Current before scanning or changing runtime state.'
                : latestScanUnreachable
                ? 'Start the source website, refresh AI Hub, then rerun readiness. In Docker, localhost URLs are probed through the host alias too.'
                : unsupported.length
                ? 'Use the unsupported evidence below to decide whether to run setup from the operator center, repair adapter actions, or inspect source data.'
                : rows.length
                ? 'No readiness blockers are visible in the latest scan. Re-scan after source-site layout or data changes.'
                : scanReport
                ? 'The latest scan completed without capability rows. Use setup to rebuild crawl, discovery, rehearsal, and readiness evidence.'
                : 'Run setup to create the first crawl, discovery, readiness, and prompt evidence set. The staged monitor will keep progress visible.'}
            </p>
          </div>
        </Panel>
      </div>
      {unsupportedNonDomain.length ? (
        <NoticeBanner
          tone="info"
          message={`${unsupportedNonDomain.length} non-domain readiness check(s) need work. The cards below show evidence and the recommended fix path.`}
        />
      ) : null}
      <Panel
        title="Capability report"
        action={
          rows.length ? (
            <div className="readiness-filter" role="group" aria-label="Readiness report filter">
              {(['needs', 'supported', 'all'] as const).map((item) => (
                <button
                  key={item}
                  type="button"
                  className={filter === item ? 'active' : ''}
                  onClick={() => setFilter(item)}
                >
                  {item === 'needs' ? 'Needs work' : item === 'supported' ? 'Supported' : 'All'}
                </button>
              ))}
            </div>
          ) : null
        }
      >
        {filteredRows.length ? (
          <div className="capability-grid">
            {filteredRows.map((capability) => (
              <CapabilityReportCard
                key={capability.name}
                capability={capability}
                canRunSetup={!automationLocked && sourceReachable && !scanning}
                sourceStatus={sourceStatus}
                onRunSetup={onRunSetup}
              />
            ))}
          </div>
        ) : rows.length ? (
          <EmptyState title="No checks in this filter" message="Switch filters to inspect supported checks or the full report." />
        ) : (
          <EmptyState text="Run setup to generate a readable capability report." />
        )}
      </Panel>
      <div className="grid gap-4 xl:grid-cols-[0.8fr_1.2fr] items-start">
        <Panel title="Supported customer actions">
          <ActionChipGrid actions={capabilities?.allowed_actions ?? []} />
        </Panel>
        <TechnicalDetails title="Advanced readiness JSON" data={scanReport} />
      </div>
    </div>
  );
}

function ReadinessRunConsole({
  feedback,
  operation,
  scanReport,
  automationLocked,
}: {
  feedback: OperationFeedbackState | null;
  operation: OperationStatus | null;
  scanReport: ReadinessReport | null;
  automationLocked: boolean;
}) {
  const visibleOperation = visibleReadinessOperation(operation, feedback);
  const status = feedback?.status || normalizeTimelineStatus(visibleOperation?.status);
  const etaSeconds = Math.ceil(minimumOperationDuration('readiness') / 1000);
  const heading = automationLocked
    ? 'Activate before scanning'
    : status === 'running'
    ? 'Readiness scan running'
    : status === 'complete'
    ? 'Latest readiness evidence saved'
    : status === 'failed'
    ? 'Readiness scan needs retry'
    : scanReport
    ? 'Readiness evidence is available'
    : 'Ready to scan';
  const copy = automationLocked
    ? 'Move this install to Current before AI Hub scans or changes runtime state.'
    : status === 'running'
    ? 'The scanner is moving through stages now. This page stays live and the saved report appears here when the run finishes.'
    : status === 'complete'
    ? 'The latest scan output is saved below. Re-run after website, adapter, or source-data changes.'
    : status === 'failed'
    ? 'The last scan failed. Use retry from the operation monitor or run the scan again from this page.'
    : `A scan takes at least about ${number(etaSeconds)} seconds in the UI so progress, ETA, stages, and logs are visible instead of flashing.`;
  return (
    <section className={`readiness-run-console ${status}`}>
      <div className="readiness-run-console-head">
        <div>
          <span>Scanner console</span>
          <strong>{heading}</strong>
          <p>{copy}</p>
        </div>
        <StatusPill value={automationLocked ? 'available' : status === 'pending' ? 'ready' : status} />
      </div>
      <OperatorRunSummary feedback={feedback} backendOperation={visibleOperation} />
      <ol className="readiness-run-stage-preview" aria-label="Readiness scan stages">
        {READINESS_OPERATION_STAGES.map((stage, index) => {
          const stageStatus = readinessStageStatus(index, feedback, visibleOperation);
          return (
            <li key={stage} className={stageStatus}>
              <span aria-hidden="true" />
              <strong>{stage}</strong>
            </li>
          );
        })}
      </ol>
    </section>
  );
}

function visibleReadinessOperation(
  operation: OperationStatus | null,
  feedback: OperationFeedbackState | null,
) {
  if (!operation) return null;
  const status = normalizeTimelineStatus(operation.status);
  if (status === 'pending' && !operation.stages.some((stage) => normalizeTimelineStatus(stage.status) !== 'pending')) {
    return null;
  }
  if (!feedback || feedback.status !== 'running') return operation;
  return operationBelongsToFeedback(operation, feedback) ? operation : null;
}

function readinessStageStatus(
  index: number,
  feedback: OperationFeedbackState | null,
  operation: OperationStatus | null,
) {
  const backendStage = !feedback ? operation?.stages[index] : null;
  if (backendStage) return normalizeTimelineStatus(backendStage.status);
  if (!feedback) return 'pending';
  if (feedback.status === 'complete') return 'complete';
  if (index < feedback.stageIndex) return 'complete';
  if (index === feedback.stageIndex) return feedback.status;
  return 'pending';
}

function CapabilityReportCard({
  capability,
  canRunSetup,
  sourceStatus,
  onRunSetup,
}: {
  capability: ReadinessReport['capabilities'][number];
  canRunSetup: boolean;
  sourceStatus: string;
  onRunSetup: () => void;
}) {
  const blockingGap = isBlockingCapabilityGap(capability);
  const Icon = capability.supported || !blockingGap ? CheckCircle2 : capability.confidence >= 0.5 ? AlertTriangle : XCircle;
  const tone = capability.supported || !blockingGap ? 'ok' : capability.confidence >= 0.5 ? 'warn' : 'bad';
  const status = capability.supported ? 'supported' : blockingGap ? 'needs work' : 'informational';
  const hint = automationHintForCapability(capability.name);
  return (
    <article className={`capability-card capability-card-${tone}`}>
      <div className="capability-card-head">
        <Icon size={18} aria-hidden="true" />
        <StatusPill value={status} />
      </div>
      <h3>{labelize(capability.name)}</h3>
      <strong>{percent(capability.confidence)}% confidence</strong>
      <p>{capability.evidence || 'No scanner evidence was saved for this check.'}</p>
      {blockingGap ? (
        <button
          className="capability-card-action capability-card-action-button"
          type="button"
          disabled={!canRunSetup}
          title={canRunSetup ? 'Run setup to rebuild evidence for this gap.' : `Setup is unavailable while source is ${sourceStatus}.`}
          onClick={onRunSetup}
        >
          <small>Suggested fix</small>
          <strong>{canRunSetup ? hint : `Source ${sourceStatus}. Start the website, refresh AI Hub, then run setup.`}</strong>
        </button>
      ) : null}
    </article>
  );
}

function readinessNextStep(
  rowCount: number,
  unsupportedCount: number,
  automationLocked: boolean,
  unreachable = false,
  hasScan = false,
) {
  if (automationLocked) return 'Activate before scanning';
  if (unreachable) return 'Source unreachable in latest scan';
  if (!rowCount && hasScan) return 'Rebuild evidence with setup';
  if (!rowCount) return 'Run setup';
  if (unsupportedCount) return 'Review unsupported evidence';
  return 'Ready, keep monitoring';
}

