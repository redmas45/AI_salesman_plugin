import { useEffect, useMemo, useState } from 'react';
import { AlertTriangle, CheckCircle2, Code2, FileText, Network, Plug, RotateCcw, Save, ShieldCheck, XCircle } from 'lucide-react';
import { crmApi } from '../../api';
import type { AdapterConfigResponse, Client, PromptProfileResponse } from '../../types';
import type { CrmVerticalDefinition } from '../../verticals/types';
import { Button } from '../../components/ui/Button';
import { EmptyState } from '../../components/ui/EmptyState';
import { Panel } from '../../components/ui/Panel';
import { StatusPill } from '../../components/ui/Badge';
import { TechnicalDetails } from '../../components/shared/TechnicalDetails';
import { UniversalInstallerPanel } from '../../components/shared/UniversalInstallerPanel';

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
  const [reviewingCandidate, setReviewingCandidate] = useState('');
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
  const pendingCandidates = useMemo(() => {
    return actionCandidates.filter((candidate) => {
      const reviewLabel = candidateReviewLabel(candidate, actionReviews);
      return reviewLabel === 'pending';
    });
  }, [actionCandidates, actionReviews]);
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

  async function reviewActionCandidate(candidate: Record<string, unknown>, decision: 'approve' | 'reject') {
    const key = candidateReviewKey(candidate);
    setReviewingCandidate(`${decision}:${key}`);
    setMessage('');
    try {
      const response = await crmApi.reviewClientAdapterAction(client.site_id, { candidate, decision });
      setAdapter(response);
      setActionDraft(formatActionJson(response));
      setMessage(decision === 'approve' ? 'Action candidate approved.' : 'Action candidate rejected.');
    } catch (error) {
      setMessage(error instanceof Error ? error.message : 'Action candidate review failed.');
    } finally {
      setReviewingCandidate('');
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

      <div className="grid gap-4 xl:grid-cols-2">
        <div className="grid gap-4 align-start">
          <Panel title="Detected runtime binding" action={<Plug size={16} aria-hidden="true" />}>
            <div className="mt-3 grid gap-2 text-sm">
              <KeyValue label="Site ID" value={client.site_id} />
              <KeyValue label="Origin" value={client.allowed_origin || client.store_url} />
              <KeyValue label="Adapter mode" value={adapter?.runtime_config.adapter.mode || '-'} />
              <KeyValue label="Platform" value={adapter?.runtime_config.adapter.platform || 'auto'} />
              <KeyValue label="Vertical" value={String(adapter?.runtime_config.vertical.key || vertical.key)} />
              <KeyValue label="Discovery" value={formatConfidence(discovery.confidence)} />
              <KeyValue
                label="Vertical decision"
                value={verticalDecisionLabel(discovery, String(adapter?.runtime_config.vertical.key || vertical.key))}
              />
              <KeyValue label="Initialization" value={initializationSummary(initialization)} />
              <KeyValue label="Action policy" value={actionPolicySummary(blockedActions, handoffActions)} />
              <KeyValue label="Validation" value={validationSummary(validation.summary)} />
              <KeyValue label="Flow graph" value={flowSummaryText(flowSummary)} />
              <KeyValue label="Barriers" value={barrierSummaryText(barrierSummary)} />
              <KeyValue label="Rehearsal" value={rehearsalSummaryText(rehearsalSummary)} />
              <KeyValue label="Site changes" value={regressionSummaryText(regression.status, regressionSummary)} />
              <KeyValue label="Script runtime" value={capabilitySummary(runtimeCapabilities)} />
              <KeyValue
                label="Selectors"
                value={adapter?.runtime_config.adapter.selector_validated ? 'validated' : 'generated'}
              />
            </div>
          </Panel>

          <Panel title="Detected actions" action={<Code2 size={16} aria-hidden="true" />}>
            {actionNames.length ? (
              <div className="action-chip-grid">
                {actionNames.map((action) => (
                  <span key={action} className="action-chip">
                    {action}
                  </span>
                ))}
              </div>
            ) : (
              <EmptyState text="No generated actions yet. Open the client site with the install script, then run crawl/readiness." />
            )}
          </Panel>
        </div>

        <div className="grid gap-4 align-start">
          <Panel title="Live action candidates (pending review)">
            {pendingCandidates.length ? (
              <div className="grid gap-3">
                {pendingCandidates.slice(0, 12).map((candidate) => (
                  <div
                    key={`${String(candidate.kind)}-${String(candidate.action)}-${String(candidate.selector)}-${String(candidate.path)}`}
                    className="rounded-md border border-line p-3 bg-card"
                  >
                    <div className="flex flex-wrap items-center justify-between gap-2">
                      <strong className="text-sm">{candidateLabel(candidate)}</strong>
                      <StatusPill value={String(candidate.type || candidate.kind || 'candidate')} />
                    </div>
                    <div className="mt-2 grid gap-1 text-sm text-muted">
                      <span>Action: {String(candidate.action || 'unmapped')}</span>
                      <span>Target: {candidateTarget(candidate)}</span>
                      <span>Confidence: {formatConfidence(candidate.confidence)}</span>
                    </div>
                    <div className="mt-3 flex flex-wrap items-center gap-2">
                      <Button
                        size="sm"
                        icon={CheckCircle2}
                        disabled={Boolean(reviewingCandidate)}
                        onClick={() => reviewActionCandidate(candidate, 'approve')}
                      >
                        {reviewingCandidate === `approve:${candidateReviewKey(candidate)}` ? 'Approving...' : 'Approve'}
                      </Button>
                      <Button
                        size="sm"
                        variant="secondary"
                        icon={XCircle}
                        disabled={Boolean(reviewingCandidate)}
                        onClick={() => reviewActionCandidate(candidate, 'reject')}
                      >
                        {reviewingCandidate === `reject:${candidateReviewKey(candidate)}` ? 'Rejecting...' : 'Reject'}
                      </Button>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <EmptyState text="All action candidates have been approved or reviewed automatically!" />
            )}
          </Panel>

          <Panel title="Action map editor">
            <div className="grid gap-3">
              <textarea
                className="textarea textarea-lg code-textarea"
                value={actionDraft}
                onChange={(event) => setActionDraft(event.currentTarget.value)}
                spellCheck={false}
              />
              <div className="flex flex-wrap items-center gap-2">
                <Button icon={Save} disabled={savingActions} onClick={saveActionMap}>
                  {savingActions ? 'Saving...' : 'Save actions'}
                </Button>
                <Button variant="secondary" icon={RotateCcw} disabled={savingActions} onClick={resetActionDraft}>
                  Reset
                </Button>
                {message ? <span className="text-sm text-muted">{message}</span> : null}
              </div>
            </div>
          </Panel>
        </div>
      </div>

      <div className="mt-6 flex flex-col items-center justify-center p-6 border border-line rounded-lg bg-soft">
        <h3 className="text-sm font-semibold text-muted">Troubleshooting & Diagnostics</h3>
        <p className="mt-1 text-xs text-muted mb-4">Access prompt generation, action policies, site changes, and logs.</p>
        <Button variant="secondary" onClick={() => setShowAdvanced(!showAdvanced)}>
          {showAdvanced ? 'Hide Advanced Diagnostics & Tools' : 'Show Advanced Diagnostics & Tools'}
        </Button>
      </div>

      {showAdvanced && (
        <div className="grid gap-4 xl:grid-cols-2 mt-4 fade-in">
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
                        Inferred: {String(event.inferred_action || 'unmapped')} (
                        {formatConfidence(event.inference_confidence)})
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
                  <div
                    key={`${String(proposal.action)}-${proposalReviewKey(proposal)}`}
                    className="rounded-md border border-line p-3"
                  >
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
                      <Button
                        size="sm"
                        icon={CheckCircle2}
                        disabled={Boolean(reviewingProposal)}
                        onClick={() => reviewActionProposal(proposal, 'approve')}
                      >
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

          <Panel title="Runtime repairs">
            {actionRepairs.length ? (
              <div className="grid gap-3">
                {actionRepairs.slice(0, 10).map((repair) => (
                  <div
                    key={`${String(repair.action)}-${String(repair.applied_at)}-${String(repair.last_url)}`}
                    className="rounded-md border border-line p-3"
                  >
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

          <Panel title="Action execution">
            {actionEvents.length ? (
              <div className="grid gap-3">
                {actionEvents.slice(0, 10).map((event) => (
                  <div
                    key={`${String(event.action)}-${String(event.stage)}-${String(event.occurred_at)}`}
                    className="rounded-md border border-line p-3"
                  >
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

          <Panel title="Action review history">
            {actionReviews.length ? (
              <div className="grid gap-3">
                {actionReviews.map((review) => (
                  <div
                    key={`${String(review.key)}-${String(review.reviewed_at)}`}
                    className="rounded-md border border-line p-3"
                  >
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

          <Panel title="Action policy" action={<ShieldCheck size={16} aria-hidden="true" />}>
            {blockedActions.length || handoffActions.length || handoffFlows.length || policyNotes.length ? (
              <div className="grid gap-3 text-sm">
                <KeyValue label="Blocked" value={blockedActions.length ? blockedActions.join(', ') : 'none'} />
                <KeyValue label="Runtime repair" value={runtimeBlockedActions.length ? runtimeBlockedActions.join(', ') : 'none'} />
                <KeyValue label="Handoff" value={handoffActions.length ? handoffActions.join(', ') : 'none'} />
                {handoffFlows.length ? (
                  <div className="grid gap-2">
                    <strong className="text-sm">Handoff flows</strong>
                    <div className="grid gap-2">
                      {handoffFlows.map((flow) => (
                        <div
                          key={`${String(flow.key)}-${String(flow.action)}-${String(flow.page_url)}`}
                          className="rounded-md border border-line p-2"
                        >
                          <div className="flex flex-wrap items-center justify-between gap-2">
                            <strong>{String(flow.title || flow.key || 'Handoff')}</strong>
                            <StatusPill value={String(flow.severity || 'unknown')} />
                          </div>
                          <p className="mt-1 text-muted">{handoffFlowLabel(flow)}</p>
                        </div>
                      ))}
                    </div>
                  </div>
                ) : null}
                {policyNotes.length ? (
                  <div className="grid gap-2">
                    <strong className="text-sm">Policy notes</strong>
                    <div className="grid gap-2">
                      {policyNotes.map((note) => (
                        <div key={`${String(note.key)}-${String(note.severity)}`} className="rounded-md border border-line p-2">
                          <div className="flex flex-wrap items-center justify-between gap-2">
                            <strong>{String(note.key || '-')}</strong>
                            <StatusPill value={String(note.severity || 'unknown')} />
                          </div>
                          <p className="mt-1 text-muted">{String(note.handling || note.evidence || '-')}</p>
                        </div>
                      ))}
                    </div>
                  </div>
                ) : null}
                {policyEvents.length ? (
                  <div className="grid gap-2">
                    <strong className="text-sm">Recent blocked attempts</strong>
                    <div className="grid gap-2">
                      {policyEvents.map((event) => (
                        <div
                          key={`${String(event.action)}-${String(event.occurred_at)}-${String(event.reason)}`}
                          className="rounded-md border border-line p-2"
                        >
                          <div className="flex flex-wrap items-center justify-between gap-2">
                            <strong>{String(event.action || '-')}</strong>
                            <StatusPill value={String(event.status || 'blocked')} />
                          </div>
                          <p className="mt-1 text-muted">{policyEventLabel(event)}</p>
                        </div>
                      ))}
                    </div>
                  </div>
                ) : null}
              </div>
            ) : (
              <EmptyState text="No action restrictions from barrier policy." />
            )}
          </Panel>

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

          <Panel title="Flow rehearsal" action={<ShieldCheck size={16} aria-hidden="true" />}>
            {Object.keys(rehearsalSummary).length ? (
              <div className="grid gap-3">
                <div className="grid gap-2 text-sm">
                  <KeyValue label="Engine" value={String(rehearsal.engine || '-')} />
                  <KeyValue label="Supported" value={rehearsalSummaryText(rehearsalSummary)} />
                  <KeyValue label="Confirmations" value={Number(rehearsalSummary.needs_confirmation ?? 0)} />
                </div>
                {rehearsalSteps.length ? (
                  <div className="grid gap-2">
                    <strong className="text-sm">Checked targets</strong>
                    <div className="grid gap-2">
                      {rehearsalSteps.map((step) => (
                        <div
                          key={`${String(step.action_name)}-${String(step.target)}-${String(step.status)}`}
                          className="rounded-md border border-line p-2 text-sm"
                        >
                          <div className="flex flex-wrap items-center justify-between gap-2">
                            <strong>{String(step.action_name || '-')}</strong>
                            <StatusPill value={String(step.status || 'unknown')} />
                          </div>
                          <p className="mt-1 text-muted">{rehearsalStepLabel(step)}</p>
                        </div>
                      ))}
                    </div>
                  </div>
                ) : null}
              </div>
            ) : (
              <EmptyState text="Run rehearsal after flow discovery to safely verify generated routes, selectors, and form targets." />
            )}
          </Panel>

          <Panel title="Automation barriers" action={<AlertTriangle size={16} aria-hidden="true" />}>
            {Object.keys(barrierSummary).length ? (
              <div className="grid gap-3">
                <div className="grid gap-2 text-sm">
                  <KeyValue label="Detected" value={barrierSummaryText(barrierSummary)} />
                  <KeyValue label="Last scan" value={String(barriers.detected_at || '-')} />
                </div>
                {barrierFindings.length ? (
                  <div className="grid gap-2">
                    <strong className="text-sm">Hard cases</strong>
                    <div className="grid gap-2">
                      {barrierFindings.map((finding) => (
                        <div
                          key={`${String(finding.key)}-${String(finding.page_url)}`}
                          className="rounded-md border border-line p-2 text-sm"
                        >
                          <div className="flex flex-wrap items-center justify-between gap-2">
                            <strong>{String(finding.label || finding.key || '-')}</strong>
                            <StatusPill value={String(finding.severity || 'unknown')} />
                          </div>
                          <p className="mt-1 text-muted">{barrierFindingLabel(finding)}</p>
                        </div>
                      ))}
                    </div>
                  </div>
                ) : (
                  <EmptyState text="No hard automation barriers detected in the latest flow discovery." />
                )}
              </div>
            ) : (
              <EmptyState text="Run flow discovery to detect CAPTCHA, auth, iframe, payment, calendar, map, and upload barriers." />
            )}
          </Panel>

          <Panel title="Site changes" action={<AlertTriangle size={16} aria-hidden="true" />}>
            {Object.keys(regressionSummary).length ? (
              <div className="grid gap-3">
                <div className="grid gap-2 text-sm">
                  <KeyValue label="Status" value={String(regression.status || '-')} />
                  <KeyValue label="Changes" value={regressionSummaryText(regression.status, regressionSummary)} />
                  <KeyValue label="Compared" value={String(regression.compared_at || '-')} />
                </div>
                {regressionChanges.length ? (
                  <div className="grid gap-2">
                    <strong className="text-sm">Detected drift</strong>
                    <div className="grid gap-2">
                      {regressionChanges.map((change) => (
                        <div
                          key={`${String(change.kind)}-${String(change.item)}-${String(change.current)}`}
                          className="rounded-md border border-line p-2 text-sm"
                        >
                          <div className="flex flex-wrap items-center justify-between gap-2">
                            <strong>{String(change.item || '-')}</strong>
                            <StatusPill value={String(change.severity || 'unknown')} />
                          </div>
                          <p className="mt-1 text-muted">{regressionChangeLabel(change)}</p>
                        </div>
                      ))}
                    </div>
                  </div>
                ) : (
                  <EmptyState text="No route or action drift detected in the latest comparison." />
                )}
                {flowRepairProposals.length ? (
                  <div className="grid gap-2">
                    <strong className="text-sm">Repair plans</strong>
                    <div className="grid gap-2">
                      {flowRepairProposals.map((proposal) => (
                        <div
                          key={`${String(proposal.key)}-${String(proposal.kind)}`}
                          className="rounded-md border border-line p-2 text-sm"
                        >
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
                      ))}
                    </div>
                  </div>
                ) : null}
              </div>
            ) : (
              <EmptyState text="Run setup twice to compare current flow evidence against the previous site state." />
            )}
          </Panel>

          <Panel title="Generated adapter code">
            <pre className="code-block install-script">{adapter?.adapter_code || '// Adapter code is not generated yet.'}</pre>
          </Panel>

          <Panel title="Generated prompt preview" action={<FileText size={16} aria-hidden="true" />}>
            {activePrompt ? (
              <div className="grid gap-3">
                <KeyValue label="Version" value={`v${activePrompt.version} ${activePrompt.status}`} />
                <pre className="code-block install-script">{activePrompt.system_prompt}</pre>
                {activePrompt.developer_rules ? (
                  <pre className="code-block install-script">{activePrompt.developer_rules}</pre>
                ) : null}
              </div>
            ) : (
              <EmptyState text="No prompt profile exists yet." />
            )}
          </Panel>
        </div>
      )}

      <TechnicalDetails title="Generated runtime config JSON" data={adapter?.runtime_config ?? null} />
    </div>
  );
}

function KeyValue({ label, value }: { label: string; value: string | number | null | undefined }) {
  return (
    <div className="grid grid-cols-[130px_minmax(0,1fr)] gap-3 border-b border-line py-2 last:border-b-0">
      <span className="text-muted">{label}</span>
      <strong className="min-w-0 overflow-wrap-anywhere">{value == null || value === '' ? '-' : value}</strong>
    </div>
  );
}

function actionConfig(value: unknown): Record<string, unknown> {
  return value && typeof value === 'object' ? (value as Record<string, unknown>) : {};
}

function actionTarget(config: Record<string, unknown>) {
  const steps = Array.isArray(config.steps) ? config.steps : [];
  if (steps.length) return `${steps.length} sequence step${steps.length === 1 ? '' : 's'}`;
  return String(config.path || config.selector || config.form || config.input || '-');
}

function candidateLabel(candidate: Record<string, unknown>) {
  return String(candidate.label || candidate.action || candidate.kind || 'Candidate');
}

function candidateTarget(candidate: Record<string, unknown>) {
  const fields = Array.isArray(candidate.fields) ? candidate.fields.map(String).filter(Boolean) : [];
  if (fields.length) return `fields: ${fields.slice(0, 6).join(', ')}`;
  return String(candidate.selector || candidate.path || '-');
}

function candidateReviewKey(candidate: Record<string, unknown>) {
  return [
    candidate.action,
    candidate.kind,
    candidate.type,
    candidate.selector,
    candidate.path,
    candidate.label,
  ]
    .map((item) => String(item || '').trim())
    .join('|');
}

function candidateReviewLabel(candidate: Record<string, unknown>, reviews: Record<string, unknown>[]) {
  const key = candidateReviewKey(candidate);
  const review = reviews.find((item) => candidateReviewKey(item) === key);
  if (!review) return 'pending';
  return `${String(review.decision || 'reviewed')} ${String(review.reviewed_at || '')}`.trim();
}

function proposalTarget(proposal: Record<string, unknown>) {
  const config = actionConfig(proposal.config);
  return String(config.selector || config.input || config.path || config.form || '-');
}

function proposalReviewKey(proposal: Record<string, unknown>) {
  const config = actionConfig(proposal.config);
  return [
    proposal.action,
    proposal.kind,
    proposal.source,
    config.type,
    config.selector || config.input,
    config.path,
  ]
    .map((item) => String(item || '').trim())
    .join('|');
}

function proposalReviewLabel(proposal: Record<string, unknown>, reviews: Record<string, unknown>[]) {
  const key = proposalReviewKey(proposal);
  const review = reviews.find((item) => proposalReviewKey(item) === key);
  if (!review) return 'pending';
  return `${String(review.decision || 'reviewed')} ${String(review.reviewed_at || '')}`.trim();
}

function flowRepairProposalKey(proposal: Record<string, unknown>) {
  const patch = actionConfig(proposal.patch);
  return [
    proposal.proposal_key || proposal.key,
    proposal.kind,
    proposal.scope,
    proposal.item,
    JSON.stringify(actionConfig(patch.routes)),
    JSON.stringify(actionConfig(patch.actions)),
  ]
    .map((item) => String(item || '').trim())
    .join('|');
}

function flowRepairReviewLabel(proposal: Record<string, unknown>, reviews: Record<string, unknown>[]) {
  const key = flowRepairProposalKey(proposal);
  const review = reviews.find((item) => flowRepairProposalKey(item) === key);
  if (!review) return 'pending';
  return `${String(review.decision || 'reviewed')} ${String(review.reviewed_at || '')}`.trim();
}

function flowRepairHasPatch(proposal: Record<string, unknown>) {
  const patch = actionConfig(proposal.patch);
  return Object.keys(actionConfig(patch.routes)).length > 0 || Object.keys(actionConfig(patch.actions)).length > 0;
}

function flowRepairPatchLabel(proposal: Record<string, unknown>) {
  const patch = actionConfig(proposal.patch);
  const routes = Object.keys(actionConfig(patch.routes)).length;
  const actions = Object.keys(actionConfig(patch.actions)).length;
  if (!routes && !actions) return 'manual review only';
  return `${routes} route${routes === 1 ? '' : 's'}, ${actions} action${actions === 1 ? '' : 's'}`;
}

function interactionTarget(event: Record<string, unknown>) {
  const form = actionConfig(event.form);
  const fields = Array.isArray(form.fields)
    ? form.fields
        .map((field) => actionConfig(field).name || actionConfig(field).placeholder)
        .map(String)
        .filter(Boolean)
    : [];
  if (fields.length) return `fields: ${fields.slice(0, 6).join(', ')}`;
  return String(event.selector || event.href || '-');
}

function formatConfidence(value: unknown) {
  const numeric = Number(value);
  if (!Number.isFinite(numeric) || numeric <= 0) return '-';
  return `${Math.round(numeric * 100)}%`;
}

function verticalDecisionLabel(discovery: Record<string, unknown>, runtimeVerticalKey: string) {
  const detected = String(discovery.detected_vertical_key || runtimeVerticalKey || '').trim();
  const applied = String(discovery.applied_vertical_key || runtimeVerticalKey || '').trim();
  const decision = String(discovery.vertical_decision || '').replace(/_/g, ' ').trim();
  if (!detected && !applied && !decision) return '-';
  const flow = detected && applied ? `${detected} -> ${applied}` : detected || applied || '-';
  return decision ? `${flow} (${decision})` : flow;
}

function formatActionJson(adapter: AdapterConfigResponse | null) {
  return JSON.stringify(adapter?.runtime_config.adapter.actions ?? {}, null, 2);
}

function validationSummary(value: unknown) {
  const summary = actionConfig(value);
  const total = Number(summary.total ?? 0);
  const supported = Number(summary.supported ?? 0);
  const repairs = Number(summary.repair_suggestions ?? 0);
  if (!total) return 'pending';
  return `${supported}/${total} supported${repairs ? `, ${repairs} repair` : ''}`;
}

function initializationSummary(value: Record<string, unknown>) {
  const status = String(value.status || '').trim();
  const stages = Array.isArray(value.stages) ? value.stages : [];
  if (!status && !stages.length) return 'pending';
  const failed = stages.filter((stage) => actionConfig(stage).status === 'failed').length;
  const completed = stages.filter((stage) => actionConfig(stage).status === 'ok').length;
  const stageText = stages.length ? `${completed}/${stages.length} stages${failed ? `, ${failed} failed` : ''}` : '';
  return `${status || 'unknown'}${stageText ? ` - ${stageText}` : ''}`;
}

function actionPolicySummary(blockedActions: string[], handoffActions: string[]) {
  if (!blockedActions.length && !handoffActions.length) return 'no restrictions';
  const blockedText = blockedActions.length ? `${blockedActions.length} blocked` : 'none blocked';
  const handoffText = handoffActions.length ? `${handoffActions.length} handoff` : 'no handoff';
  return `${blockedText}, ${handoffText}`;
}

function handoffFlowLabel(flow: Record<string, unknown>) {
  const action = String(flow.action || 'HANDOFF_TO_HUMAN');
  const provider = String(flow.provider_label || flow.provider || '');
  const evidence = String(flow.evidence || '');
  const handling = String(flow.handling || '');
  const boundary = String(flow.automation_boundary || '');
  const adminAction = String(flow.admin_action || '');
  const recovery = String(flow.recovery || '');
  const pageUrl = String(flow.page_url || '-');
  const providerText = provider ? ` via ${provider}` : '';
  return `${action}${providerText} at ${pageUrl}${evidence ? ` - ${evidence}` : ''}${handling ? ` ${handling}` : ''}${boundary ? ` Boundary: ${boundary}` : ''}${adminAction ? ` Admin: ${adminAction}` : ''}${recovery ? ` Recovery: ${recovery}` : ''}`;
}

function policyEventLabel(event: Record<string, unknown>) {
  const reason = String(event.reason || 'blocked by runtime policy');
  const url = String(event.url || '-');
  const occurredAt = String(event.occurred_at || '');
  return `${reason} at ${url}${occurredAt ? ` (${occurredAt})` : ''}`;
}

function validationLabel(value: unknown) {
  const evidence = actionConfig(value);
  if (!Object.keys(evidence).length) return 'pending browser check';
  const status = String(evidence.status || 'unknown');
  const confidence = formatConfidence(evidence.confidence);
  return `${status}${confidence === '-' ? '' : ` (${confidence})`}`;
}

function readinessParamText(value: unknown) {
  const params = stringList(value);
  return params.length ? params.join(', ') : '-';
}

function repairTargetLabel(value: unknown) {
  const repair = actionConfig(value);
  if (!Object.keys(repair).length) return '-';
  const target = String(repair.path || repair.selector || repair.form || repair.input || repair.submit || repair.label || '-');
  const confidence = formatConfidence(repair.confidence);
  return `${String(repair.type || 'repair')}: ${target}${confidence === '-' ? '' : ` (${confidence})`}`;
}

function flowSummaryText(summary: Record<string, unknown>) {
  const pages = Number(summary.pages ?? 0);
  const actions = Number(summary.actions ?? 0);
  if (!pages && !actions) return 'pending';
  return `${pages} pages, ${actions} actions`;
}

function rehearsalSummaryText(summary: Record<string, unknown>) {
  const total = Number(summary.total ?? 0);
  const supported = Number(summary.supported ?? 0);
  const blocked = Number(summary.blocked ?? 0);
  if (!total) return 'pending';
  return `${supported}/${total} supported${blocked ? `, ${blocked} blocked` : ''}`;
}

function barrierSummaryText(summary: Record<string, unknown>) {
  const total = Number(summary.total ?? 0);
  const high = Number(summary.high ?? 0);
  const medium = Number(summary.medium ?? 0);
  if (!Object.keys(summary).length) return 'pending';
  if (!total) return 'none detected';
  return `${total} detected (${high} high, ${medium} medium)`;
}

function barrierFindingLabel(finding: Record<string, unknown>) {
  const pageUrl = String(finding.page_url || '-');
  const evidence = String(finding.evidence || '');
  const handling = String(finding.handling || '');
  return `${pageUrl}${evidence ? ` - ${evidence}` : ''}${handling ? ` ${handling}` : ''}`;
}

function rehearsalStepLabel(step: Record<string, unknown>) {
  const target = String(step.target || '-');
  const evidence = String(step.evidence || step.blocker || '');
  const confirmation = step.requires_confirmation ? ' Requires confirmation.' : '';
  return `${target}${evidence ? ` - ${evidence}` : ''}${confirmation}`;
}

function regressionSummaryText(status: unknown, summary: Record<string, unknown>) {
  const changes = Number(summary.changes ?? 0);
  const high = Number(summary.high ?? 0);
  const medium = Number(summary.medium ?? 0);
  const statusText = String(status || '');
  if (summary.baseline) return 'baseline saved';
  if (!statusText && !Object.keys(summary).length) return 'pending';
  if (!changes) return statusText || 'stable';
  return `${changes} change${changes === 1 ? '' : 's'} (${high} high, ${medium} medium)`;
}

function regressionChangeLabel(change: Record<string, unknown>) {
  const kind = String(change.kind || 'change');
  const previous = String(change.previous || '-');
  const current = String(change.current || '-');
  const evidence = String(change.evidence || '');
  return `${kind}: ${previous} -> ${current}${evidence ? ` - ${evidence}` : ''}`;
}

function flowRepairProposalLabel(proposal: Record<string, unknown>) {
  const confidence = Math.round(Number(proposal.confidence || 0) * 100);
  const scope = String(proposal.scope || 'flow');
  const reason = String(proposal.reason || 'Review this flow repair before applying changes.');
  return `${scope} repair plan (${confidence}% confidence): ${reason}`;
}

function capabilitySummary(capabilities: Record<string, unknown>) {
  if (!Object.keys(capabilities).length) return 'pending';
  const loaded = capabilities.script_loaded ? 'loaded' : 'not reported';
  const secure = capabilities.secure_context ? 'secure' : 'not secure';
  const mic = String(capabilities.microphone_permission || 'unknown');
  return `${loaded}, ${secure}, mic ${mic}`;
}

function capabilityRows(capabilities: Record<string, unknown>) {
  if (!Object.keys(capabilities).length) return [];
  return [
    { label: 'Reported', value: String(capabilities.reported_at || '-') },
    { label: 'Origin', value: String(capabilities.origin || '-') },
    { label: 'Secure context', value: yesNo(capabilities.secure_context) },
    { label: 'Top window', value: yesNo(capabilities.top_level_window) },
    { label: 'Mic permission', value: String(capabilities.microphone_permission || 'unknown') },
    { label: 'Mic API', value: yesNo(capabilities.get_user_media_api) },
    { label: 'Permissions API', value: yesNo(capabilities.permissions_api) },
    { label: 'Session storage', value: String(capabilities.session_storage || '-') },
    { label: 'Local storage', value: String(capabilities.local_storage || '-') },
    { label: 'Iframes', value: Number(capabilities.iframe_count ?? 0) },
  ];
}

function yesNo(value: unknown) {
  return value ? 'yes' : 'no';
}

function stringList(value: unknown) {
  return Array.isArray(value) ? value.map((item) => String(item || '').trim()).filter(Boolean).slice(0, 10) : [];
}

function recordList(value: unknown) {
  return Array.isArray(value)
    ? value.filter((item): item is Record<string, unknown> => Boolean(item) && typeof item === 'object').slice(0, 12)
    : [];
}
