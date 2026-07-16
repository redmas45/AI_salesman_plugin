import { FileText, ShieldCheck } from 'lucide-react';
import type { AdapterConfigResponse, PromptProfileResponse } from '../../../types';
import { Button } from '../../../components/ui/Button';
import { EmptyState } from '../../../components/ui/EmptyState';
import { Panel } from '../../../components/ui/Panel';
import { TechnicalDetails } from '../../../components/shared/TechnicalDetails';
import { KeyValue } from './AdapterDiagnosticRows';
import { AdapterActionDiagnosticsPanels, type AdapterActionRow } from './AdapterActionDiagnosticsPanels';
import {
  AutomationBarriersPanel,
  FlowDiscoveryPanel,
  FlowRehearsalPanel,
  GeneratedPromptPreviewPanel,
  SiteChangesPanel,
} from './AdapterFlowDiagnostics';

type RuntimeCapabilityRow = {
  label: string;
  value: string | number;
};

interface AdapterDiagnosticsProps {
  adapter: AdapterConfigResponse | null;
  activePrompt: NonNullable<PromptProfileResponse['active_version']> | null;
  showAdvanced: boolean;
  onToggleAdvanced: () => void;
  runtimeCapabilityRows: RuntimeCapabilityRow[];
  adapterPrompts: string[];
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
  flow: Record<string, unknown>;
  flowSummary: Record<string, unknown>;
  flowPrompts: string[];
  rehearsal: Record<string, unknown>;
  rehearsalSummary: Record<string, unknown>;
  rehearsalSteps: Record<string, unknown>[];
  barriers: Record<string, unknown>;
  barrierSummary: Record<string, unknown>;
  barrierFindings: Record<string, unknown>[];
  regression: Record<string, unknown>;
  regressionSummary: Record<string, unknown>;
  regressionChanges: Record<string, unknown>[];
  flowRepairProposals: Record<string, unknown>[];
  flowRepairReviews: Record<string, unknown>[];
  refreshingProposals: boolean;
  reviewingProposal: string;
  reviewingFlowProposal: string;
  refreshActionProposals: () => void;
  reviewActionProposal: (proposal: Record<string, unknown>, decision: 'approve' | 'reject') => void;
  reviewFlowRepairProposal: (proposal: Record<string, unknown>, decision: 'approve' | 'reject') => void;
}

export function AdapterDiagnostics({
  adapter,
  activePrompt,
  showAdvanced,
  onToggleAdvanced,
  runtimeCapabilityRows,
  adapterPrompts,
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
  flow,
  flowSummary,
  flowPrompts,
  rehearsal,
  rehearsalSummary,
  rehearsalSteps,
  barriers,
  barrierSummary,
  barrierFindings,
  regression,
  regressionSummary,
  regressionChanges,
  flowRepairProposals,
  flowRepairReviews,
  refreshingProposals,
  reviewingProposal,
  reviewingFlowProposal,
  refreshActionProposals,
  reviewActionProposal,
  reviewFlowRepairProposal,
}: AdapterDiagnosticsProps) {
  return (
    <>
      <div className="mt-6 flex flex-col items-center justify-center p-6 border border-line rounded-lg bg-soft">
        <h3 className="text-sm font-semibold text-muted">Troubleshooting & Diagnostics</h3>
        <p className="mt-1 text-xs text-muted mb-4">Access prompt generation, action policies, site changes, and logs.</p>
        <Button variant="secondary" onClick={onToggleAdvanced}>
          {showAdvanced ? 'Hide Advanced Diagnostics & Tools' : 'Show Advanced Diagnostics & Tools'}
        </Button>
      </div>

      {showAdvanced ? (
        <div className="grid gap-4 xl:grid-cols-2 mt-4 fade-in">
          <ScriptCapabilitiesPanel runtimeCapabilityRows={runtimeCapabilityRows} />
          <PromptIdeasPanel adapterPrompts={adapterPrompts} />
          <AdapterActionDiagnosticsPanels
            actionReadiness={actionReadiness}
            interactionEvents={interactionEvents}
            actionHealthRows={actionHealthRows}
            actionProposals={actionProposals}
            actionProposalReviews={actionProposalReviews}
            actionRepairs={actionRepairs}
            actionEvents={actionEvents}
            actionRows={actionRows}
            validationActions={validationActions}
            actionReviews={actionReviews}
            blockedActions={blockedActions}
            runtimeBlockedActions={runtimeBlockedActions}
            handoffActions={handoffActions}
            handoffFlows={handoffFlows}
            policyNotes={policyNotes}
            policyEvents={policyEvents}
            refreshingProposals={refreshingProposals}
            reviewingProposal={reviewingProposal}
            refreshActionProposals={refreshActionProposals}
            reviewActionProposal={reviewActionProposal}
          />
          <FlowDiscoveryPanel flow={flow} flowSummary={flowSummary} flowPrompts={flowPrompts} />
          <FlowRehearsalPanel rehearsal={rehearsal} rehearsalSummary={rehearsalSummary} rehearsalSteps={rehearsalSteps} />
          <AutomationBarriersPanel barriers={barriers} barrierSummary={barrierSummary} barrierFindings={barrierFindings} />
          <SiteChangesPanel
            regression={regression}
            regressionSummary={regressionSummary}
            regressionChanges={regressionChanges}
            flowRepairProposals={flowRepairProposals}
            flowRepairReviews={flowRepairReviews}
            reviewingFlowProposal={reviewingFlowProposal}
            reviewFlowRepairProposal={reviewFlowRepairProposal}
          />
          <Panel title="Generated adapter code">
            <pre className="code-block install-script">{adapter?.adapter_code || '// Adapter code is not generated yet.'}</pre>
          </Panel>
          <GeneratedPromptPreviewPanel activePrompt={activePrompt} />
        </div>
      ) : null}

      <TechnicalDetails title="Generated runtime config JSON" data={adapter?.runtime_config ?? null} />
    </>
  );
}

function ScriptCapabilitiesPanel({ runtimeCapabilityRows }: { runtimeCapabilityRows: RuntimeCapabilityRow[] }) {
  return (
    <Panel title="Script capabilities" action={<ShieldCheck size={16} aria-hidden="true" />}>
      {runtimeCapabilityRows.length ? (
        <div className="grid gap-2 text-sm">
          {runtimeCapabilityRows.map((row) => (
            <KeyValue key={row.label} label={row.label} value={row.value} />
          ))}
        </div>
      ) : (
        <EmptyState text="Open the client site with the install script to report runtime capabilities." />
      )}
    </Panel>
  );
}

function PromptIdeasPanel({ adapterPrompts }: { adapterPrompts: string[] }) {
  return (
    <Panel title="Prompt ideas from discovery" action={<FileText size={16} aria-hidden="true" />}>
      {adapterPrompts.length ? (
        <div className="grid gap-2">
          {adapterPrompts.map((prompt) => (
            <span key={prompt} className="rounded-md border border-line bg-soft p-2 text-sm">
              {prompt}
            </span>
          ))}
        </div>
      ) : (
        <EmptyState text="Prompt ideas appear after the first browser registration or flow discovery." />
      )}
    </Panel>
  );
}

