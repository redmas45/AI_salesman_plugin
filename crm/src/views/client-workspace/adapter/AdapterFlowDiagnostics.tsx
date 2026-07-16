import { AlertTriangle, CheckCircle2, FileText, Network, ShieldCheck, XCircle } from 'lucide-react';
import type { PromptProfileResponse } from '../../../types';
import { Button } from '../../../components/ui/Button';
import { EmptyState } from '../../../components/ui/EmptyState';
import { Panel } from '../../../components/ui/Panel';
import { StatusPill } from '../../../components/ui/Badge';
import { KeyValue, RecordList } from './AdapterDiagnosticRows';
import {
  barrierFindingLabel,
  barrierSummaryText,
  flowRepairHasPatch,
  flowRepairPatchLabel,
  flowRepairProposalKey,
  flowRepairProposalLabel,
  flowRepairReviewLabel,
  handoffFlowLabel,
  policyEventLabel,
  regressionChangeLabel,
  regressionSummaryText,
  rehearsalStepLabel,
  rehearsalSummaryText,
} from './adapterFormatters';

export function FlowDiscoveryPanel({
  flow,
  flowSummary,
  flowPrompts,
}: {
  flow: Record<string, unknown>;
  flowSummary: Record<string, unknown>;
  flowPrompts: string[];
}) {
  return (
    <Panel title="Flow discovery" action={<Network size={16} aria-hidden="true" />}>
      {Object.keys(flowSummary).length ? (
        <div className="grid gap-3">
          <div className="grid gap-2 text-sm">
            <KeyValue label="Engine" value={String(flow.engine || '-')} />
            <KeyValue label="Pages" value={Number(flowSummary.pages ?? 0)} />
            <KeyValue label="Actions" value={Number(flowSummary.actions ?? 0)} />
            <KeyValue label="Forms" value={Number(flowSummary.forms ?? 0)} />
          </div>
          {flowPrompts.length ? (
            <div className="grid gap-2">
              <strong className="text-sm">Prompt suggestions</strong>
              <div className="grid gap-2">
                {flowPrompts.map((prompt) => (
                  <span key={prompt} className="rounded-md border border-line bg-soft p-2 text-sm">
                    {prompt}
                  </span>
                ))}
              </div>
            </div>
          ) : null}
        </div>
      ) : (
        <EmptyState text="Run flow discovery to map pages, forms, actions, and customer prompt ideas." />
      )}
    </Panel>
  );
}

export function FlowRehearsalPanel({
  rehearsal,
  rehearsalSummary,
  rehearsalSteps,
}: {
  rehearsal: Record<string, unknown>;
  rehearsalSummary: Record<string, unknown>;
  rehearsalSteps: Record<string, unknown>[];
}) {
  return (
    <Panel title="Flow rehearsal" action={<ShieldCheck size={16} aria-hidden="true" />}>
      {Object.keys(rehearsalSummary).length ? (
        <div className="grid gap-3">
          <div className="grid gap-2 text-sm">
            <KeyValue label="Engine" value={String(rehearsal.engine || '-')} />
            <KeyValue label="Supported" value={rehearsalSummaryText(rehearsalSummary)} />
            <KeyValue label="Confirmations" value={Number(rehearsalSummary.needs_confirmation ?? 0)} />
          </div>
          <RecordList title="Checked targets" rows={rehearsalSteps} render={rehearsalStepRow} />
        </div>
      ) : (
        <EmptyState text="Run rehearsal after flow discovery to safely verify generated routes, selectors, and form targets." />
      )}
    </Panel>
  );
}

export function AutomationBarriersPanel({
  barriers,
  barrierSummary,
  barrierFindings,
}: {
  barriers: Record<string, unknown>;
  barrierSummary: Record<string, unknown>;
  barrierFindings: Record<string, unknown>[];
}) {
  return (
    <Panel title="Automation barriers" action={<AlertTriangle size={16} aria-hidden="true" />}>
      {Object.keys(barrierSummary).length ? (
        <div className="grid gap-3">
          <div className="grid gap-2 text-sm">
            <KeyValue label="Detected" value={barrierSummaryText(barrierSummary)} />
            <KeyValue label="Last scan" value={String(barriers.detected_at || '-')} />
          </div>
          {barrierFindings.length ? (
            <RecordList title="Hard cases" rows={barrierFindings} render={barrierFindingRow} />
          ) : (
            <EmptyState text="No hard automation barriers detected in the latest flow discovery." />
          )}
        </div>
      ) : (
        <EmptyState text="Run flow discovery to detect CAPTCHA, auth, iframe, payment, calendar, map, and upload barriers." />
      )}
    </Panel>
  );
}

export function SiteChangesPanel({
  regression,
  regressionSummary,
  regressionChanges,
  flowRepairProposals,
  flowRepairReviews,
  reviewingFlowProposal,
  reviewFlowRepairProposal,
}: {
  regression: Record<string, unknown>;
  regressionSummary: Record<string, unknown>;
  regressionChanges: Record<string, unknown>[];
  flowRepairProposals: Record<string, unknown>[];
  flowRepairReviews: Record<string, unknown>[];
  reviewingFlowProposal: string;
  reviewFlowRepairProposal: (proposal: Record<string, unknown>, decision: 'approve' | 'reject') => void;
}) {
  return (
    <Panel title="Site changes" action={<AlertTriangle size={16} aria-hidden="true" />}>
      {Object.keys(regressionSummary).length ? (
        <div className="grid gap-3">
          <div className="grid gap-2 text-sm">
            <KeyValue label="Status" value={String(regression.status || '-')} />
            <KeyValue label="Changes" value={regressionSummaryText(regression.status, regressionSummary)} />
            <KeyValue label="Compared" value={String(regression.compared_at || '-')} />
          </div>
          {regressionChanges.length ? (
            <RecordList title="Detected drift" rows={regressionChanges} render={regressionChangeRow} />
          ) : (
            <EmptyState text="No route or action drift detected in the latest comparison." />
          )}
          {flowRepairProposals.length ? (
            <div className="grid gap-2">
              <strong className="text-sm">Repair plans</strong>
              <div className="grid gap-2">
                {flowRepairProposals.map((proposal) => (
                  <FlowRepairProposal
                    key={`${String(proposal.key)}-${String(proposal.kind)}`}
                    proposal={proposal}
                    flowRepairReviews={flowRepairReviews}
                    reviewingFlowProposal={reviewingFlowProposal}
                    reviewFlowRepairProposal={reviewFlowRepairProposal}
                  />
                ))}
              </div>
            </div>
          ) : null}
        </div>
      ) : (
        <EmptyState text="Run setup twice to compare current flow evidence against the previous site state." />
      )}
    </Panel>
  );
}

export function GeneratedPromptPreviewPanel({
  activePrompt,
}: {
  activePrompt: NonNullable<PromptProfileResponse['active_version']> | null;
}) {
  return (
    <Panel title="Generated prompt preview" action={<FileText size={16} aria-hidden="true" />}>
      {activePrompt ? (
        <div className="grid gap-3">
          <KeyValue label="Version" value={`v${activePrompt.version} ${activePrompt.status}`} />
          <pre className="code-block install-script">{activePrompt.system_prompt}</pre>
          {activePrompt.developer_rules ? <pre className="code-block install-script">{activePrompt.developer_rules}</pre> : null}
        </div>
      ) : (
        <EmptyState text="No prompt profile exists yet." />
      )}
    </Panel>
  );
}

function FlowRepairProposal({
  proposal,
  flowRepairReviews,
  reviewingFlowProposal,
  reviewFlowRepairProposal,
}: {
  proposal: Record<string, unknown>;
  flowRepairReviews: Record<string, unknown>[];
  reviewingFlowProposal: string;
  reviewFlowRepairProposal: (proposal: Record<string, unknown>, decision: 'approve' | 'reject') => void;
}) {
  return (
    <div className="rounded-md border border-line p-2 text-sm">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <strong>{String(proposal.item || proposal.key || '-')}</strong>
        <StatusPill value={String(proposal.kind || 'repair')} />
      </div>
      <p className="mt-1 text-muted">{flowRepairProposalLabel(proposal)}</p>
      <div className="mt-2 grid gap-1 text-muted">
        <span>Review: {flowRepairReviewLabel(proposal, flowRepairReviews)}</span>
        <span>Patch: {flowRepairPatchLabel(proposal)}</span>
      </div>
      <div className="mt-3 flex flex-wrap items-center gap-2">
        <Button
          size="sm"
          icon={CheckCircle2}
          disabled={Boolean(reviewingFlowProposal) || !flowRepairHasPatch(proposal)}
          onClick={() => reviewFlowRepairProposal(proposal, 'approve')}
        >
          {reviewingFlowProposal === `approve:${flowRepairProposalKey(proposal)}` ? 'Approving...' : 'Approve'}
        </Button>
        <Button
          size="sm"
          variant="secondary"
          icon={XCircle}
          disabled={Boolean(reviewingFlowProposal)}
          onClick={() => reviewFlowRepairProposal(proposal, 'reject')}
        >
          {reviewingFlowProposal === `reject:${flowRepairProposalKey(proposal)}` ? 'Rejecting...' : 'Reject'}
        </Button>
      </div>
    </div>
  );
}

function handoffFlowRow(flow: Record<string, unknown>) {
  return (
    <div key={`${String(flow.key)}-${String(flow.action)}-${String(flow.page_url)}`} className="rounded-md border border-line p-2">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <strong>{String(flow.title || flow.key || 'Handoff')}</strong>
        <StatusPill value={String(flow.severity || 'unknown')} />
      </div>
      <p className="mt-1 text-muted">{handoffFlowLabel(flow)}</p>
    </div>
  );
}

export function ActionPolicyRecordLists({
  handoffFlows,
  policyNotes,
  policyEvents,
}: {
  handoffFlows: Record<string, unknown>[];
  policyNotes: Record<string, unknown>[];
  policyEvents: Record<string, unknown>[];
}) {
  return (
    <>
      <RecordList title="Handoff flows" rows={handoffFlows} render={handoffFlowRow} />
      <RecordList title="Policy notes" rows={policyNotes} render={policyNoteRow} />
      <RecordList title="Recent blocked attempts" rows={policyEvents} render={policyEventRow} />
    </>
  );
}

function policyNoteRow(note: Record<string, unknown>) {
  return (
    <div key={`${String(note.key)}-${String(note.severity)}`} className="rounded-md border border-line p-2">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <strong>{String(note.key || '-')}</strong>
        <StatusPill value={String(note.severity || 'unknown')} />
      </div>
      <p className="mt-1 text-muted">{String(note.handling || note.evidence || '-')}</p>
    </div>
  );
}

function policyEventRow(event: Record<string, unknown>) {
  return (
    <div key={`${String(event.action)}-${String(event.occurred_at)}-${String(event.reason)}`} className="rounded-md border border-line p-2">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <strong>{String(event.action || '-')}</strong>
        <StatusPill value={String(event.status || 'blocked')} />
      </div>
      <p className="mt-1 text-muted">{policyEventLabel(event)}</p>
    </div>
  );
}

function rehearsalStepRow(step: Record<string, unknown>) {
  return (
    <div key={`${String(step.action_name)}-${String(step.target)}-${String(step.status)}`} className="rounded-md border border-line p-2 text-sm">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <strong>{String(step.action_name || '-')}</strong>
        <StatusPill value={String(step.status || 'unknown')} />
      </div>
      <p className="mt-1 text-muted">{rehearsalStepLabel(step)}</p>
    </div>
  );
}

function barrierFindingRow(finding: Record<string, unknown>) {
  return (
    <div key={`${String(finding.key)}-${String(finding.page_url)}`} className="rounded-md border border-line p-2 text-sm">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <strong>{String(finding.label || finding.key || '-')}</strong>
        <StatusPill value={String(finding.severity || 'unknown')} />
      </div>
      <p className="mt-1 text-muted">{barrierFindingLabel(finding)}</p>
    </div>
  );
}

function regressionChangeRow(change: Record<string, unknown>) {
  return (
    <div key={`${String(change.kind)}-${String(change.item)}-${String(change.current)}`} className="rounded-md border border-line p-2 text-sm">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <strong>{String(change.item || '-')}</strong>
        <StatusPill value={String(change.severity || 'unknown')} />
      </div>
      <p className="mt-1 text-muted">{regressionChangeLabel(change)}</p>
    </div>
  );
}
