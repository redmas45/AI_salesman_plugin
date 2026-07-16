import { useEffect, useMemo, useState } from 'react';
import { Network, ShieldCheck } from 'lucide-react';
import { crmApi } from '../../../api';
import type { AdapterConfigResponse, Client, PromptProfileResponse } from '../../../types';
import type { CrmVerticalDefinition } from '../../../verticals/types';
import { Button } from '../../../components/ui/Button';
import { EmptyState } from '../../../components/ui/EmptyState';
import { StatusPill } from '../../../components/ui/Badge';
import { UniversalInstallerPanel } from '../../../components/shared/UniversalInstallerPanel';
import { AdapterDiagnostics } from './AdapterDiagnostics';
import { AdapterOverviewPanels } from './AdapterOverviewPanels';
import {
  actionConfig,
  capabilityRows,
  flowRepairProposalKey,
  formatActionJson,
  proposalReviewKey,
  recordList,
  stringList,
} from './adapterFormatters';

interface AdapterTabProps {
  client: Client;
  vertical: CrmVerticalDefinition;
}

export function AdapterTab({ client, vertical }: AdapterTabProps) {
  const [adapter, setAdapter] = useState<AdapterConfigResponse | null>(null);
  const [promptProfile, setPromptProfile] = useState<PromptProfileResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [savingActions, setSavingActions] = useState(false);
  const [discoveringFlow, setDiscoveringFlow] = useState(false);
  const [rehearsingFlow, setRehearsingFlow] = useState(false);
  const [refreshingProposals, setRefreshingProposals] = useState(false);
  const [reviewingProposal, setReviewingProposal] = useState('');
  const [reviewingFlowProposal, setReviewingFlowProposal] = useState('');
  const [actionDraft, setActionDraft] = useState('{}');
  const [message, setMessage] = useState('');
  const [showAdvanced, setShowAdvanced] = useState(false);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setMessage('');
    Promise.all([crmApi.getClientAdapter(client.site_id), crmApi.getPromptProfile(client.site_id)])
      .then(([adapterResponse, promptResponse]) => {
        if (cancelled) return;
        setAdapter(adapterResponse);
        setPromptProfile(promptResponse);
        setActionDraft(formatActionJson(adapterResponse));
      })
      .catch((error: unknown) => {
        if (!cancelled) setMessage(error instanceof Error ? error.message : 'Adapter details failed to load.');
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [client.site_id]);

  const actionNames = useMemo(() => {
    const actions = adapter?.runtime_config.adapter.actions ?? {};
    return Object.keys(actions).sort();
  }, [adapter]);
  const actionRows = useMemo(() => {
    const actions = adapter?.runtime_config.adapter.actions ?? {};
    return Object.entries(actions)
      .map(([name, config]) => ({ name, config: actionConfig(config) }))
      .sort((left, right) => left.name.localeCompare(right.name));
  }, [adapter]);

  const activePrompt = promptProfile?.active_version ?? null;
  const actionPolicy = adapter?.runtime_config.adapter.action_policy ?? {};
  const discovery = adapter?.runtime_config.adapter.discovery ?? {};
  const validation = adapter?.runtime_config.adapter.validation ?? {};
  const initialization = adapter?.runtime_config.adapter.initialization ?? {};
  const flow = adapter?.runtime_config.adapter.flow ?? {};
  const barriers = adapter?.runtime_config.adapter.barriers ?? {};
  const rehearsal = adapter?.runtime_config.adapter.rehearsal ?? {};
  const regression = adapter?.runtime_config.adapter.regression ?? {};
  const runtimeCapabilities = actionConfig(adapter?.runtime_config.adapter.runtime_capabilities);
  const actionHealth = actionConfig(adapter?.runtime_config.adapter.action_health);
  const validationActions = actionConfig(validation.actions);
  const blockedActions = stringList(actionPolicy.blocked_actions);
  const runtimeBlockedActions = stringList(actionPolicy.runtime_blocked_actions);
  const handoffActions = stringList(actionPolicy.handoff_actions);
  const handoffFlows = recordList(actionPolicy.handoff_flows);
  const policyNotes = recordList(actionPolicy.notes);
  const actionHealthRows = recordList(actionHealth.needs_repair);
  const actionEvents = recordList(adapter?.runtime_config.adapter.action_events);
  const actionRepairs = recordList(adapter?.runtime_config.adapter.action_repairs);
  const policyEvents = recordList(adapter?.runtime_config.adapter.policy_events);
  const interactionEvents = recordList(adapter?.runtime_config.adapter.interaction_events);
  const actionCandidates = recordList(adapter?.runtime_config.adapter.action_candidates);
  const actionReadiness = recordList(adapter?.runtime_config.adapter.action_readiness);
  const actionProposals = recordList(adapter?.runtime_config.adapter.action_proposals);
  const actionProposalReviews = recordList(adapter?.runtime_config.adapter.action_proposal_reviews);
  const actionReviews = recordList(adapter?.runtime_config.adapter.action_reviews);
  const flowRepairProposals = recordList(adapter?.runtime_config.adapter.flow_repair_proposals);
  const flowRepairReviews = recordList(adapter?.runtime_config.adapter.flow_repair_reviews);
  const adapterPrompts = stringList(adapter?.runtime_config.adapter.prompt_suggestions);
  const flowSummary = actionConfig(flow.summary);
  const flowPrompts = stringList(flow.prompt_suggestions);
  const barrierSummary = actionConfig(barriers.summary);
  const barrierFindings = recordList(barriers.findings);
  const rehearsalSummary = actionConfig(rehearsal.summary);
  const rehearsalSteps = recordList(rehearsal.steps);
  const regressionSummary = actionConfig(regression.summary);
  const regressionChanges = recordList(regression.changes);
  const runtimeCapabilityRows = capabilityRows(runtimeCapabilities);

  async function saveActionMap() {
    setSavingActions(true);
    setMessage('');
    try {
      const parsed = JSON.parse(actionDraft) as Record<string, unknown>;
      const response = await crmApi.saveClientAdapterActions(client.site_id, parsed);
      setAdapter(response);
      setActionDraft(formatActionJson(response));
      setMessage('Adapter action map saved.');
    } catch (error) {
      setMessage(error instanceof Error ? error.message : 'Adapter action save failed.');
    } finally {
      setSavingActions(false);
    }
  }

  function resetActionDraft() {
    setActionDraft(formatActionJson(adapter));
    setMessage('');
  }

  async function discoverFlows() {
    setDiscoveringFlow(true);
    setMessage('');
    try {
      const response = await crmApi.discoverClientFlows(client.site_id, 8);
      const nextAdapter = {
        runtime_config: response.runtime_config,
        adapter_code: response.adapter_code,
      };
      setAdapter(nextAdapter);
      setActionDraft(formatActionJson(nextAdapter));
      setMessage('Flow discovery completed.');
    } catch (error) {
      setMessage(error instanceof Error ? error.message : 'Flow discovery failed.');
    } finally {
      setDiscoveringFlow(false);
    }
  }

  async function rehearseFlows() {
    setRehearsingFlow(true);
    setMessage('');
    try {
      const response = await crmApi.rehearseClientFlows(client.site_id, 24);
      const nextAdapter = {
        runtime_config: response.runtime_config,
        adapter_code: response.adapter_code,
      };
      setAdapter(nextAdapter);
      setActionDraft(formatActionJson(nextAdapter));
      setMessage('Flow rehearsal completed.');
    } catch (error) {
      setMessage(error instanceof Error ? error.message : 'Flow rehearsal failed.');
    } finally {
      setRehearsingFlow(false);
    }
  }

  async function refreshActionProposals() {
    setRefreshingProposals(true);
    setMessage('');
    try {
      const response = await crmApi.refreshClientAdapterActionProposals(client.site_id);
      setAdapter(response);
      setActionDraft(formatActionJson(response));
      setMessage('Action repair proposals refreshed.');
    } catch (error) {
      setMessage(error instanceof Error ? error.message : 'Action repair proposal refresh failed.');
    } finally {
      setRefreshingProposals(false);
    }
  }

  async function reviewActionProposal(proposal: Record<string, unknown>, decision: 'approve' | 'reject') {
    const key = proposalReviewKey(proposal);
    setReviewingProposal(`${decision}:${key}`);
    setMessage('');
    try {
      const response = await crmApi.reviewClientAdapterActionProposal(client.site_id, { proposal, decision });
      setAdapter(response);
      setActionDraft(formatActionJson(response));
      setMessage(decision === 'approve' ? 'Action repair proposal approved.' : 'Action repair proposal rejected.');
    } catch (error) {
      setMessage(error instanceof Error ? error.message : 'Action repair proposal review failed.');
    } finally {
      setReviewingProposal('');
    }
  }

  async function reviewFlowRepairProposal(proposal: Record<string, unknown>, decision: 'approve' | 'reject') {
    const key = flowRepairProposalKey(proposal);
    setReviewingFlowProposal(`${decision}:${key}`);
    setMessage('');
    try {
      const response = await crmApi.reviewClientFlowRepairProposal(client.site_id, { proposal, decision });
      setAdapter(response);
      setActionDraft(formatActionJson(response));
      setMessage(decision === 'approve' ? 'Flow repair plan approved.' : 'Flow repair plan rejected.');
    } catch (error) {
      setMessage(error instanceof Error ? error.message : 'Flow repair plan review failed.');
    } finally {
      setReviewingFlowProposal('');
    }
  }

  if (loading) {
    return (
      <div className="tab-content fade-in">
        <EmptyState text="Loading adapter configuration..." />
      </div>
    );
  }

  return (
    <div className="tab-content fade-in">
      <section className="section-row">
        <div>
          <h2 className="text-base font-semibold">Generated adapter</h2>
          <p className="mt-1 text-sm text-muted">
            AI Hub generated this runtime layer from the one-line script, crawl, and page observations.
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <Button variant="secondary" icon={Network} disabled={discoveringFlow} onClick={discoverFlows}>
            {discoveringFlow ? 'Discovering...' : 'Discover flows'}
          </Button>
          <Button variant="secondary" icon={ShieldCheck} disabled={rehearsingFlow} onClick={rehearseFlows}>
            {rehearsingFlow ? 'Rehearsing...' : 'Rehearse flows'}
          </Button>
          <StatusPill value={adapter?.runtime_config.enabled ? 'enabled' : 'disabled'} />
        </div>
      </section>

      {message ? <div className="notice notice-error">{message}</div> : null}

      <UniversalInstallerPanel compact />

      <AdapterOverviewPanels
        client={client}
        vertical={vertical}
        adapter={adapter}
        discovery={discovery}
        initialization={initialization}
        validation={validation}
        flowSummary={flowSummary}
        barrierSummary={barrierSummary}
        rehearsalSummary={rehearsalSummary}
        regression={regression}
        regressionSummary={regressionSummary}
        runtimeCapabilities={runtimeCapabilities}
        runtimeCapabilityRows={runtimeCapabilityRows}
        actionNames={actionNames}
        blockedActions={blockedActions}
        runtimeBlockedActions={runtimeBlockedActions}
        handoffActions={handoffActions}
        actionCandidates={actionCandidates}
        actionDraft={actionDraft}
        savingActions={savingActions}
        setActionDraft={setActionDraft}
        saveActionMap={saveActionMap}
        resetActionDraft={resetActionDraft}
      />
      <AdapterDiagnostics
        adapter={adapter}
        activePrompt={activePrompt}
        showAdvanced={showAdvanced}
        onToggleAdvanced={() => setShowAdvanced(!showAdvanced)}
        runtimeCapabilityRows={runtimeCapabilityRows}
        adapterPrompts={adapterPrompts}
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
        flow={flow}
        flowSummary={flowSummary}
        flowPrompts={flowPrompts}
        rehearsal={rehearsal}
        rehearsalSummary={rehearsalSummary}
        rehearsalSteps={rehearsalSteps}
        barriers={barriers}
        barrierSummary={barrierSummary}
        barrierFindings={barrierFindings}
        regression={regression}
        regressionSummary={regressionSummary}
        regressionChanges={regressionChanges}
        flowRepairProposals={flowRepairProposals}
        flowRepairReviews={flowRepairReviews}
        refreshingProposals={refreshingProposals}
        reviewingProposal={reviewingProposal}
        reviewingFlowProposal={reviewingFlowProposal}
        refreshActionProposals={refreshActionProposals}
        reviewActionProposal={reviewActionProposal}
        reviewFlowRepairProposal={reviewFlowRepairProposal}
      />
    </div>
  );
}
