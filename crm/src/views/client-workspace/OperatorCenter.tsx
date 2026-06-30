import {
  ArrowLeft,
  ExternalLink,
  Gauge,
  PackageOpen,
  Plus,
  Trash2,
} from 'lucide-react';
import type {
  Client,
  OperationStatusResponse,
} from '../../types';
import { ClientStatusChip } from '../../components/ui/ClientStatusChip';
import { clientPanelHref } from '../../utils/clientLinks';
import { number, shortTime } from '../../utils/format';
import type { ClientWorkspaceTabId, CrmVerticalDefinition } from '../../verticals/types';
import {
  firstRunningOperation,
  normalizeTimelineStatus,
  operationLabel,
  operationResultTab,
  type OperationFeedbackKind,
  type OperationFeedbackState,
} from './OperationFeedback';
import { ActionCard } from './ActionCard';

type PrimaryAction = 'setup' | 'crawl';
type OperatorActionState = 'idle' | 'pending' | 'running' | 'complete' | 'failed' | 'skipped';

export function ClientOperatorCenter({
  client,
  vertical,
  automationLocked,
  sourceReachable,
  sourceStatus,
  scanning,
  crawling,
  autoIntegrating,
  operationFeedback,
  operationStatus,
  onBack,
  onActivate,
  onRunIntegration,
  onRunCrawl,
  onRemoveClient,
  onOpenOutput,
}: {
  client: Client;
  vertical: CrmVerticalDefinition;
  automationLocked: boolean;
  sourceReachable: boolean;
  sourceStatus: string;
  scanning: boolean;
  crawling: boolean;
  autoIntegrating: boolean;
  operationFeedback: OperationFeedbackState | null;
  operationStatus: OperationStatusResponse | null;
  onBack: () => void;
  onActivate: () => void;
  onRunIntegration: () => void;
  onRunCrawl: () => void;
  onRemoveClient: () => void;
  onOpenPasswordDialog: () => void;
  onToggleWidget: () => void;
  onOpenControls: () => void;
  onOpenOutput: (tabId: ClientWorkspaceTabId) => void;
}) {
  const panelUrl = clientPanelHref(client.site_id);
  const runtime = String(sourceStatus || client.runtime_status?.status || 'unknown').toLowerCase();
  const lifecycleStatus = automationLocked ? 'available' : client.status;
  const sourceOffline = !automationLocked && !sourceReachable;
  const setupState = operationActionState('integration', operationFeedback, operationStatus, autoIntegrating);
  const readinessState = operationActionState('readiness', operationFeedback, operationStatus, scanning);
  const crawlState = operationActionState('crawl', operationFeedback, operationStatus, crawling);
  const primaryAction = derivePrimaryAction(setupState, readinessState, crawlState);
  const liveOperation = operationFeedback
    ? operationStatus?.operations?.[operationFeedback.kind] ?? null
    : firstRunningOperation(operationStatus);
  const runningLabel = operationFeedback ? operationLabel(operationFeedback.kind) : liveOperation?.label || '';
  const nextStep = deriveNextStep({
    automationLocked,
    sourceOffline,
    currentStatus: operationFeedback?.status || normalizeTimelineStatus(liveOperation?.status),
    runningLabel,
    setupState,
    readinessState,
    crawlState,
  });
  const anyRunning = autoIntegrating || scanning || crawling || nextStep.running;

  return (
    <section className="overflow-hidden rounded-md border border-[#dce6f5] bg-white text-[#172033]" aria-label="Client operator center">
      <div className="flex items-center justify-between border-b border-[#dce6f5] bg-[#f8fbff] px-4 py-2">
        <button
          type="button"
          onClick={onBack}
          className="flex items-center gap-1.5 text-xs text-[#64748b] transition-colors hover:text-[#172033]"
        >
          <ArrowLeft size={13} aria-hidden="true" />
          All clients
        </button>
        <div className="flex items-center gap-2">
          <RuntimeIndicator online={sourceReachable} />
          {!automationLocked ? (
            <button
              type="button"
              onClick={onRemoveClient}
              className="inline-flex h-8 items-center gap-1.5 rounded-md border border-[#f4b8b8] bg-[#fff5f5] px-3 text-xs font-medium text-[#c43c3c] transition-colors hover:border-[#e24d4d] hover:bg-[#e24d4d] hover:text-white"
            >
              <Trash2 size={12} aria-hidden="true" />
              Move to available
            </button>
          ) : null}
        </div>
      </div>

      <div className="grid min-w-0 grid-cols-[minmax(0,1fr)_360px] max-[980px]:grid-cols-1">
        <div className="flex min-w-0 flex-col gap-5 bg-white p-5">
          <div className="flex min-w-0 flex-col gap-2">
            <div className="flex flex-wrap items-center gap-2">
              <span className="rounded bg-[#eef4ff] px-2 py-0.5 font-mono text-[10px] font-medium uppercase tracking-wider text-[#64748b]">
                {client.vertical_label || vertical.label}
              </span>
              <ClientStatusChip status={lifecycleStatus} />
              <ClientStatusChip status={runtime} />
            </div>

            <button
              type="button"
              onClick={() => onOpenOutput('overview')}
              className="w-fit max-w-full text-left text-lg font-semibold leading-tight text-[#172033] transition-colors hover:text-[#3b6ef8]"
            >
              {client.name}
            </button>

            <div className="flex min-w-0 flex-col gap-1">
              <span className="break-all font-mono text-xs tracking-tight text-[#64748b]">{client.site_id}</span>
              <div className="flex flex-wrap items-center gap-x-4 gap-y-1">
                <a
                  href={client.store_url}
                  target="_blank"
                  rel="noreferrer"
                  className="flex w-fit max-w-full items-center gap-1 truncate text-xs text-[#3b6ef8] transition-colors hover:text-[#93b4fd]"
                >
                  <span className="truncate">{client.store_url}</span>
                  <ExternalLink size={11} className="shrink-0" aria-hidden="true" />
                </a>
                <a
                  href={panelUrl}
                  target="_blank"
                  rel="noreferrer"
                  className="flex w-fit max-w-full items-center gap-1 truncate text-xs text-[#93b4fd] transition-colors hover:text-[#bfdbfe]"
                >
                  <span className="truncate">Owner panel</span>
                  <ExternalLink size={11} className="shrink-0" aria-hidden="true" />
                </a>
              </div>
            </div>
          </div>

          <div className="border-t border-[#dce6f5]" />

          <div className="flex min-w-0 flex-col gap-1.5">
            <span className="text-[10px] font-medium uppercase tracking-wider text-[#64748b]">Next step</span>
            <span className="text-sm font-semibold text-[#172033]">{nextStep.label}</span>
            <span className="max-w-3xl text-xs leading-relaxed text-[#64748b]">{nextStep.description}</span>
          </div>

          <div className="border-t border-[#dce6f5]" />

          <div className="grid min-w-0 grid-cols-3 gap-px overflow-hidden rounded-md bg-[#dce6f5] max-[680px]:grid-cols-1">
            <MetricCell label="Records" value={`${number(client.catalog.active_products)} ${vertical.entityLabelPlural}`} />
            <MetricCell label="Vectors" value={client.catalog.missing_embeddings ? `${number(client.catalog.missing_embeddings)} missing` : 'ready'} />
            <MetricCell label="Last crawl" value={shortTime(client.last_crawl_at)} />
          </div>

          <div className="border-t border-[#dce6f5]" />

          <div className="grid min-w-0 grid-cols-3 gap-2 max-[760px]:grid-cols-1" aria-label="Saved operation evidence">
            <EvidenceTile
              label="Setup evidence"
              detail="Crawl, routes, rehearsal, prompt checks"
              saved={setupState === 'complete'}
              value={setupState === 'running' ? 'Running' : setupState === 'failed' ? 'Needs retry' : setupState === 'complete' ? 'Saved' : 'Not run'}
              onOpen={() => onOpenOutput(operationResultTab('integration'))}
            />
            <EvidenceTile
              label="Readiness output"
              detail="Capability checks and unsupported actions"
              saved={readinessState === 'complete'}
              value={readinessState === 'running' ? 'Running' : readinessState === 'failed' ? 'Needs retry' : readinessState === 'complete' ? 'Saved' : 'Not run'}
              onOpen={() => onOpenOutput(operationResultTab('readiness'))}
            />
            <EvidenceTile
              label="Crawl report"
              detail="Pages, records, source metadata, failures"
              saved={crawlState === 'complete' || Boolean(client.last_crawl_at)}
              value={crawlState === 'running' ? 'Running' : crawlState === 'failed' ? 'Needs retry' : crawlState === 'complete' || client.last_crawl_at ? 'Saved' : 'Not run'}
              onOpen={() => onOpenOutput(operationResultTab('crawl'))}
            />
          </div>
        </div>

        <div className="flex min-w-0 flex-col gap-3 border-l border-[#dce6f5] bg-[#f8fbff] p-4 max-[980px]:border-l-0 max-[980px]:border-t">
          {automationLocked ? (
            <ActionCard
              icon={Plus}
              title="Add to current"
              description="Approve this detected install. This does not start crawling."
              variant="primary"
              disabled={false}
              running={false}
              onClick={onActivate}
              buttonLabel="Add to current"
            />
          ) : (
            <>
              <ActionCard
                icon={Gauge}
                title="Single click setup"
                description="Crawls source data, discovers flows, rehearses actions, scans readiness, and runs prompt checks."
                variant={primaryAction === 'setup' ? 'primary' : 'secondary'}
                disabled={autoIntegrating || sourceOffline || anyRunning}
                running={setupState === 'running'}
                offline={sourceOffline}
                onClick={onRunIntegration}
                buttonLabel={setupState === 'complete' ? 'Run setup again' : 'Run setup'}
              />
              <ActionCard
                icon={PackageOpen}
                title="Crawl source"
                description="Refreshes pages, records, source metadata, and crawl report."
                variant={primaryAction === 'crawl' ? 'primary' : 'secondary'}
                disabled={crawling || sourceOffline || anyRunning}
                running={crawlState === 'running'}
                offline={sourceOffline}
                onClick={onRunCrawl}
                buttonLabel={crawlState === 'complete' ? 'Crawl again' : 'Run crawl'}
              />
            </>
          )}
        </div>
      </div>
    </section>
  );
}

function RuntimeIndicator({ online }: { online: boolean }) {
  return online ? (
    <span className="flex items-center gap-1.5 text-xs font-medium text-[#22c55e]">
      <span className="h-1.5 w-1.5 rounded-full bg-[#22c55e] motion-safe:animate-pulse" />
      LIVE
    </span>
  ) : (
    <span className="flex items-center gap-1.5 text-xs font-medium text-[#64748b]">
      <span className="h-1.5 w-1.5 rounded-full bg-[#334155]" />
      OFFLINE
    </span>
  );
}

function MetricCell({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex min-w-0 flex-col gap-0.5 bg-[#f8fbff] px-4 py-3">
      <span className="text-[10px] font-medium uppercase tracking-wider text-[#64748b]">{label}</span>
      <span className="truncate font-mono text-sm font-semibold text-[#172033]" title={value}>
        {value}
      </span>
    </div>
  );
}

function EvidenceTile({
  label,
  detail,
  saved,
  value,
  onOpen,
}: {
  label: string;
  detail: string;
  saved: boolean;
  value: string;
  onOpen: () => void;
}) {
  if (!saved) {
    return (
      <div className="flex min-w-0 flex-col gap-0.5 rounded border border-[#dce6f5] bg-[#f8fbff] p-3 opacity-75">
        <span className="text-[10px] font-medium uppercase tracking-wider text-[#64748b]">{label}</span>
        <span className="text-xs font-semibold text-[#172033]">{value}</span>
        <span className="mt-0.5 text-[10px] leading-relaxed text-[#64748b]">{detail}</span>
      </div>
    );
  }
  return (
    <button
      type="button"
      onClick={onOpen}
      className="flex min-w-0 flex-col gap-0.5 rounded border border-[#93b4fd] bg-[#eef4ff] p-3 text-left transition-colors hover:bg-[#e5edff]"
    >
      <span className="text-[10px] font-medium uppercase tracking-wider text-[#64748b]">{label}</span>
      <span className="text-xs font-semibold text-[#93b4fd]">{value}</span>
      <span className="mt-0.5 text-[10px] leading-relaxed text-[#64748b]">{detail}</span>
    </button>
  );
}

function derivePrimaryAction(
  setupState: OperatorActionState,
  readinessState: OperatorActionState,
  crawlState: OperatorActionState,
): PrimaryAction {
  if (setupState !== 'complete') return 'setup';
  if (readinessState !== 'complete') return 'setup';
  if (crawlState !== 'complete') return 'crawl';
  return 'setup';
}

function deriveNextStep({
  automationLocked,
  sourceOffline,
  currentStatus,
  runningLabel,
  setupState,
  readinessState,
  crawlState,
}: {
  automationLocked: boolean;
  sourceOffline: boolean;
  currentStatus: OperatorActionState;
  runningLabel: string;
  setupState: OperatorActionState;
  readinessState: OperatorActionState;
  crawlState: OperatorActionState;
}) {
  if (automationLocked) {
    return {
      label: 'Approve install',
      description: 'Move this detected install to Current before setup, readiness, crawl, or runtime controls.',
      running: false,
    };
  }
  if (currentStatus === 'running') {
    return {
      label: runningLabel || 'Operation running',
      description: 'Progress is saved to the matching evidence output below. Keep this page open for live status.',
      running: true,
    };
  }
  if (sourceOffline) {
    return {
      label: 'Source offline',
      description: 'Start the source website to enable setup, readiness, and crawl. Owner panel remains available from AI Hub.',
      running: false,
    };
  }
  if (setupState !== 'complete') {
    return {
      label: 'Run single click setup',
      description: 'First run indexes the site, discovers routes, rehearses actions, and prepares the agent adapter.',
      running: false,
    };
  }
  if (readinessState !== 'complete') {
    return {
      label: 'Run setup again',
      description: 'Readiness evidence is missing or stale. Setup will rebuild crawl, flows, readiness, and prompt checks in one run.',
      running: false,
    };
  }
  if (crawlState !== 'complete') {
    return {
      label: 'Run crawl',
      description: 'Refresh pages, records, source metadata, and vector-ready catalog content.',
      running: false,
    };
  }
  return {
    label: 'Agent ready',
    description: 'Setup, readiness, and crawl evidence are saved. Monitor live demand from Analytics.',
    running: false,
  };
}

function operationActionState(
  kind: OperationFeedbackKind,
  feedback: OperationFeedbackState | null,
  status: OperationStatusResponse | null,
  localRunning: boolean,
): OperatorActionState {
  if (feedback?.kind === kind) return feedback.status;
  if (localRunning) return 'running';
  const backendStatus = normalizeTimelineStatus(status?.operations[kind]?.status);
  if (
    backendStatus === 'pending'
    || backendStatus === 'running'
    || backendStatus === 'complete'
    || backendStatus === 'failed'
    || backendStatus === 'skipped'
  ) {
    return backendStatus;
  }
  return 'idle';
}
