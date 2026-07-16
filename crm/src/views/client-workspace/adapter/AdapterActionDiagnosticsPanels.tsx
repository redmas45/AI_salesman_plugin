import { CheckCircle2, RotateCcw, ShieldCheck, XCircle } from 'lucide-react';
import { Button } from '../../../components/ui/Button';
import { EmptyState } from '../../../components/ui/EmptyState';
import { Panel } from '../../../components/ui/Panel';
import { StatusPill } from '../../../components/ui/Badge';
import { KeyValue } from './AdapterDiagnosticRows';
import { ActionPolicyRecordLists } from './AdapterFlowDiagnostics';
import {
  actionConfig,
  actionTarget,
  candidateTarget,
  formatConfidence,
  interactionTarget,
  proposalReviewKey,
  proposalReviewLabel,
  proposalTarget,
  readinessParamText,
  repairTargetLabel,
  validationLabel,
} from './adapterFormatters';

export type AdapterActionRow = {
  name: string;
  config: Record<string, unknown>;
};

interface AdapterActionDiagnosticsPanelsProps {
  actionReadiness: Record<string, unknown>[];
  interactionEvents: Record<string, unknown>[];
  actionHealthRows: Record<string, unknown>[];
  actionProposals: Record<string, unknown>[];
  actionProposalReviews: Record<string, unknown>[];
  actionRepairs: Record<string, unknown>[];
  actionEvents: Record<string, unknown>[];
  actionRows: AdapterActionRow[];
  validationActions: Record<string, unknown>;
  actionReviews: Record<string, unknown>[];
  blockedActions: string[];
  runtimeBlockedActions: string[];
  handoffActions: string[];
  handoffFlows: Record<string, unknown>[];
  policyNotes: Record<string, unknown>[];
  policyEvents: Record<string, unknown>[];
  refreshingProposals: boolean;
  reviewingProposal: string;
  refreshActionProposals: () => void;
  reviewActionProposal: (proposal: Record<string, unknown>, decision: 'approve' | 'reject') => void;
}

export function AdapterActionDiagnosticsPanels({
  actionReadiness,
  interactionEvents,
  actionHealthRows,
  actionProposals,
  actionProposalReviews,
  actionRepairs,
  actionEvents,
  actionRows,
  validationActions,
  actionReviews,
  blockedActions,
  runtimeBlockedActions,
  handoffActions,
  handoffFlows,
  policyNotes,
  policyEvents,
  refreshingProposals,
  reviewingProposal,
  refreshActionProposals,
  reviewActionProposal,
}: AdapterActionDiagnosticsPanelsProps) {
  return (
    <>
      <ActionReadinessPanel actionReadiness={actionReadiness} />
      <LearnedInteractionsPanel interactionEvents={interactionEvents} />
      <ActionHealthPanel actionHealthRows={actionHealthRows} />
      <ActionRepairProposalsPanel
        actionProposals={actionProposals}
        actionProposalReviews={actionProposalReviews}
        refreshingProposals={refreshingProposals}
        reviewingProposal={reviewingProposal}
        refreshActionProposals={refreshActionProposals}
        reviewActionProposal={reviewActionProposal}
      />
      <RuntimeRepairsPanel actionRepairs={actionRepairs} />
      <ActionExecutionPanel actionEvents={actionEvents} />
      <ActionMapPanel actionRows={actionRows} validationActions={validationActions} />
      <ActionReviewHistoryPanel actionReviews={actionReviews} />
      <ActionPolicyPanel
        blockedActions={blockedActions}
        runtimeBlockedActions={runtimeBlockedActions}
        handoffActions={handoffActions}
        handoffFlows={handoffFlows}
        policyNotes={policyNotes}
        policyEvents={policyEvents}
      />
    </>
  );
}

function ActionReadinessPanel({ actionReadiness }: { actionReadiness: Record<string, unknown>[] }) {
  return (
    <Panel title="Action readiness">
      {actionReadiness.length ? (
        <div className="grid gap-3">
          {actionReadiness.slice(0, 10).map((row) => (
            <div key={`${String(row.action)}-${String(row.status)}`} className="rounded-md border border-line p-3">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <strong className="text-sm">{String(row.action || '-')}</strong>
                <StatusPill value={String(row.status || 'unknown')} />
              </div>
              <div className="mt-2 grid gap-1 text-sm text-muted">
                <span>Required: {readinessParamText(row.required_params)}</span>
                <span>Optional: {readinessParamText(row.optional_params)}</span>
                <span>Ask: {String(row.question || '-')}</span>
                <span>Reason: {String(row.reason || '-')}</span>
              </div>
            </div>
          ))}
        </div>
      ) : (
        <EmptyState text="Field readiness appears after generated form or sequence actions are discovered." />
      )}
    </Panel>
  );
}

function LearnedInteractionsPanel({ interactionEvents }: { interactionEvents: Record<string, unknown>[] }) {
  return (
    <Panel title="Learned interactions">
      {interactionEvents.length ? (
        <div className="grid gap-3">
          {interactionEvents.slice(0, 10).map((event) => (
            <div
              key={`${String(event.event_type)}-${String(event.selector)}-${String(event.occurred_at)}`}
              className="rounded-md border border-line p-3"
            >
              <div className="flex flex-wrap items-center justify-between gap-2">
                <strong className="text-sm">{String(event.label || event.selector || event.event_type || '-')}</strong>
                <StatusPill value={String(event.event_type || 'event')} />
              </div>
              <div className="mt-2 grid gap-1 text-sm text-muted">
                <span>
                  Inferred: {String(event.inferred_action || 'unmapped')} ({formatConfidence(event.inference_confidence)})
                </span>
                <span>Target: {interactionTarget(event)}</span>
                <span>Page: {String(event.url || '-')}</span>
              </div>
            </div>
          ))}
        </div>
      ) : (
        <EmptyState text="Observed clicks and form submits appear here after visitors use pages with the install script." />
      )}
    </Panel>
  );
}

function ActionHealthPanel({ actionHealthRows }: { actionHealthRows: Record<string, unknown>[] }) {
  return (
    <Panel title="Action health">
      {actionHealthRows.length ? (
        <div className="grid gap-3">
          {actionHealthRows.slice(0, 10).map((row) => (
            <div
              key={`${String(row.action)}-${String(row.status)}-${String(row.last_seen_at)}`}
              className="rounded-md border border-line p-3"
            >
              <div className="flex flex-wrap items-center justify-between gap-2">
                <strong className="text-sm">{String(row.action || '-')}</strong>
                <StatusPill value={String(row.status || 'unknown')} />
              </div>
              <div className="mt-2 grid gap-1 text-sm text-muted">
                <span>Failures: {String(row.failure_count || 0)}</span>
                <span>Last stage: {String(row.last_stage || '-')}</span>
                <span>Reason: {String(row.last_reason || '-')}</span>
                {Object.keys(actionConfig(row.repair_candidate)).length ? (
                  <span>Suggested repair: {repairTargetLabel(row.repair_candidate)}</span>
                ) : null}
              </div>
            </div>
          ))}
        </div>
      ) : (
        <EmptyState text="Runtime action repair warnings appear after repeated browser execution failures." />
      )}
    </Panel>
  );
}

function ActionRepairProposalsPanel({
  actionProposals,
  actionProposalReviews,
  refreshingProposals,
  reviewingProposal,
  refreshActionProposals,
  reviewActionProposal,
}: Pick<
  AdapterActionDiagnosticsPanelsProps,
  | 'actionProposals'
  | 'actionProposalReviews'
  | 'refreshingProposals'
  | 'reviewingProposal'
  | 'refreshActionProposals'
  | 'reviewActionProposal'
>) {
  return (
    <Panel
      title="Action repair proposals"
      action={
        <Button size="sm" variant="secondary" icon={RotateCcw} disabled={refreshingProposals} onClick={refreshActionProposals}>
          {refreshingProposals ? 'Refreshing...' : 'Refresh'}
        </Button>
      }
    >
      {actionProposals.length ? (
        <div className="grid gap-3">
          {actionProposals.slice(0, 10).map((proposal) => (
            <div key={`${String(proposal.action)}-${proposalReviewKey(proposal)}`} className="rounded-md border border-line p-3">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <strong className="text-sm">{String(proposal.action || '-')}</strong>
                <StatusPill value={String(proposal.kind || 'proposal')} />
              </div>
              <div className="mt-2 grid gap-1 text-sm text-muted">
                <span>Target: {proposalTarget(proposal)}</span>
                <span>Confidence: {formatConfidence(proposal.confidence)}</span>
                <span>Review: {proposalReviewLabel(proposal, actionProposalReviews)}</span>
                <span>Reason: {String(proposal.reason || '-')}</span>
              </div>
              <div className="mt-3 flex flex-wrap items-center gap-2">
                <Button size="sm" icon={CheckCircle2} disabled={Boolean(reviewingProposal)} onClick={() => reviewActionProposal(proposal, 'approve')}>
                  {reviewingProposal === `approve:${proposalReviewKey(proposal)}` ? 'Approving...' : 'Approve'}
                </Button>
                <Button
                  size="sm"
                  variant="secondary"
                  icon={XCircle}
                  disabled={Boolean(reviewingProposal)}
                  onClick={() => reviewActionProposal(proposal, 'reject')}
                >
                  {reviewingProposal === `reject:${proposalReviewKey(proposal)}` ? 'Rejecting...' : 'Reject'}
                </Button>
              </div>
            </div>
          ))}
        </div>
      ) : (
        <EmptyState text="Refresh proposals after browser validation or action failures to review suggested adapter repairs." />
      )}
    </Panel>
  );
}

function RuntimeRepairsPanel({ actionRepairs }: { actionRepairs: Record<string, unknown>[] }) {
  return (
    <Panel title="Runtime repairs">
      {actionRepairs.length ? (
        <div className="grid gap-3">
          {actionRepairs.slice(0, 10).map((repair) => (
            <div key={`${String(repair.action)}-${String(repair.applied_at)}-${String(repair.last_url)}`} className="rounded-md border border-line p-3">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <strong className="text-sm">{String(repair.action || '-')}</strong>
                <StatusPill value={String(repair.status || 'applied')} />
              </div>
              <div className="mt-2 grid gap-1 text-sm text-muted">
                <span>Target: {repairTargetLabel(repair.repair)}</span>
                <span>Reason: {String(repair.reason || '-')}</span>
                <span>Applied: {String(repair.applied_at || '-')}</span>
              </div>
            </div>
          ))}
        </div>
      ) : (
        <EmptyState text="Automatic runtime repairs appear here when recent browser interactions safely replace broken generated actions." />
      )}
    </Panel>
  );
}

function ActionExecutionPanel({ actionEvents }: { actionEvents: Record<string, unknown>[] }) {
  return (
    <Panel title="Action execution">
      {actionEvents.length ? (
        <div className="grid gap-3">
          {actionEvents.slice(0, 10).map((event) => (
            <div key={`${String(event.action)}-${String(event.stage)}-${String(event.occurred_at)}`} className="rounded-md border border-line p-3">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <strong className="text-sm">{String(event.action || '-')}</strong>
                <StatusPill value={String(event.status || 'unknown')} />
              </div>
              <div className="mt-2 grid gap-1 text-sm text-muted">
                <span>Stage: {String(event.stage || '-')}</span>
                <span>Reason: {String(event.reason || '-')}</span>
                <span>Duration: {String(event.duration_ms || 0)} ms</span>
              </div>
            </div>
          ))}
        </div>
      ) : (
        <EmptyState text="Runtime action success and failure traces appear here after the adapter executes actions." />
      )}
    </Panel>
  );
}

function ActionMapPanel({
  actionRows,
  validationActions,
}: {
  actionRows: AdapterActionRow[];
  validationActions: Record<string, unknown>;
}) {
  return (
    <Panel title="Action map (Read Only)">
      {actionRows.length ? (
        <div className="grid gap-3">
          {actionRows.map(({ name, config }) => (
            <div key={name} className="rounded-md border border-line p-3">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <strong className="text-sm">{name}</strong>
                <StatusPill value={String(config.type || 'generated')} />
              </div>
              <div className="mt-2 grid gap-1 text-sm text-muted">
                <span>Target: {actionTarget(config)}</span>
                <span>Confidence: {formatConfidence(config.confidence)}</span>
                <span>Validation: {validationLabel(validationActions[name])}</span>
              </div>
            </div>
          ))}
        </div>
      ) : (
        <EmptyState text="No generated action map yet." />
      )}
    </Panel>
  );
}

function ActionReviewHistoryPanel({ actionReviews }: { actionReviews: Record<string, unknown>[] }) {
  return (
    <Panel title="Action review history">
      {actionReviews.length ? (
        <div className="grid gap-3">
          {actionReviews.map((review) => (
            <div key={`${String(review.key)}-${String(review.reviewed_at)}`} className="rounded-md border border-line p-3">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <strong className="text-sm">{String(review.action || '-')}</strong>
                <StatusPill value={String(review.decision || 'reviewed')} />
              </div>
              <div className="mt-2 grid gap-1 text-sm text-muted">
                <span>Target: {candidateTarget(review)}</span>
                <span>Source: {String(review.kind || '-')} {String(review.type || '')}</span>
                <span>Reviewed: {String(review.reviewed_at || '-')}</span>
              </div>
            </div>
          ))}
        </div>
      ) : (
        <EmptyState text="Approved and rejected action candidates appear here." />
      )}
    </Panel>
  );
}

function ActionPolicyPanel({
  blockedActions,
  runtimeBlockedActions,
  handoffActions,
  handoffFlows,
  policyNotes,
  policyEvents,
}: Pick<AdapterActionDiagnosticsPanelsProps, 'blockedActions' | 'runtimeBlockedActions' | 'handoffActions' | 'handoffFlows' | 'policyNotes' | 'policyEvents'>) {
  return (
    <Panel title="Action policy" action={<ShieldCheck size={16} aria-hidden="true" />}>
      {blockedActions.length || handoffActions.length || handoffFlows.length || policyNotes.length ? (
        <div className="grid gap-3 text-sm">
          <KeyValue label="Blocked" value={blockedActions.length ? blockedActions.join(', ') : 'none'} />
          <KeyValue label="Runtime repair" value={runtimeBlockedActions.length ? runtimeBlockedActions.join(', ') : 'none'} />
          <KeyValue label="Handoff" value={handoffActions.length ? handoffActions.join(', ') : 'none'} />
          <ActionPolicyRecordLists handoffFlows={handoffFlows} policyNotes={policyNotes} policyEvents={policyEvents} />
        </div>
      ) : (
        <EmptyState text="No action restrictions from barrier policy." />
      )}
    </Panel>
  );
}
