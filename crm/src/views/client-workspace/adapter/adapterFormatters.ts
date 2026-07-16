import type { AdapterConfigResponse } from '../../../types';

export function actionConfig(value: unknown): Record<string, unknown> {
  return value && typeof value === 'object' ? (value as Record<string, unknown>) : {};
}

export function actionTarget(config: Record<string, unknown>) {
  const steps = Array.isArray(config.steps) ? config.steps : [];
  if (steps.length) return `${steps.length} sequence step${steps.length === 1 ? '' : 's'}`;
  return String(config.path || config.selector || config.form || config.input || '-');
}

export function candidateTarget(candidate: Record<string, unknown>) {
  const fields = Array.isArray(candidate.fields) ? candidate.fields.map(String).filter(Boolean) : [];
  if (fields.length) return `fields: ${fields.slice(0, 6).join(', ')}`;
  return String(candidate.selector || candidate.path || '-');
}

export function proposalTarget(proposal: Record<string, unknown>) {
  const config = actionConfig(proposal.config);
  return String(config.selector || config.input || config.path || config.form || '-');
}

export function proposalReviewKey(proposal: Record<string, unknown>) {
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

export function proposalReviewLabel(proposal: Record<string, unknown>, reviews: Record<string, unknown>[]) {
  const key = proposalReviewKey(proposal);
  const review = reviews.find((item) => proposalReviewKey(item) === key);
  if (!review) return 'pending';
  return `${String(review.decision || 'reviewed')} ${String(review.reviewed_at || '')}`.trim();
}

export function flowRepairProposalKey(proposal: Record<string, unknown>) {
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

export function flowRepairReviewLabel(proposal: Record<string, unknown>, reviews: Record<string, unknown>[]) {
  const key = flowRepairProposalKey(proposal);
  const review = reviews.find((item) => flowRepairProposalKey(item) === key);
  if (!review) return 'pending';
  return `${String(review.decision || 'reviewed')} ${String(review.reviewed_at || '')}`.trim();
}

export function flowRepairHasPatch(proposal: Record<string, unknown>) {
  const patch = actionConfig(proposal.patch);
  return Object.keys(actionConfig(patch.routes)).length > 0 || Object.keys(actionConfig(patch.actions)).length > 0;
}

export function flowRepairPatchLabel(proposal: Record<string, unknown>) {
  const patch = actionConfig(proposal.patch);
  const routes = Object.keys(actionConfig(patch.routes)).length;
  const actions = Object.keys(actionConfig(patch.actions)).length;
  if (!routes && !actions) return 'manual review only';
  return `${routes} route${routes === 1 ? '' : 's'}, ${actions} action${actions === 1 ? '' : 's'}`;
}

export function interactionTarget(event: Record<string, unknown>) {
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

export function formatConfidence(value: unknown) {
  const numeric = Number(value);
  if (!Number.isFinite(numeric) || numeric <= 0) return '-';
  return `${Math.round(numeric * 100)}%`;
}

export function verticalDecisionLabel(discovery: Record<string, unknown>, runtimeVerticalKey: string) {
  const detected = String(discovery.detected_vertical_key || runtimeVerticalKey || '').trim();
  const applied = String(discovery.applied_vertical_key || runtimeVerticalKey || '').trim();
  const decision = String(discovery.vertical_decision || '').replace(/_/g, ' ').trim();
  if (!detected && !applied && !decision) return '-';
  const flow = detected && applied ? `${detected} -> ${applied}` : detected || applied || '-';
  return decision ? `${flow} (${decision})` : flow;
}

export function formatActionJson(adapter: AdapterConfigResponse | null) {
  return JSON.stringify(adapter?.runtime_config.adapter.actions ?? {}, null, 2);
}

export function validationSummary(value: unknown) {
  const summary = actionConfig(value);
  const total = Number(summary.total ?? 0);
  const supported = Number(summary.supported ?? 0);
  const repairs = Number(summary.repair_suggestions ?? 0);
  if (!total) return 'pending';
  return `${supported}/${total} supported${repairs ? `, ${repairs} repair` : ''}`;
}

export function initializationSummary(value: Record<string, unknown>) {
  const status = String(value.status || '').trim();
  const stages = Array.isArray(value.stages) ? value.stages : [];
  if (!status && !stages.length) return 'pending';
  const failed = stages.filter((stage) => actionConfig(stage).status === 'failed').length;
  const completed = stages.filter((stage) => actionConfig(stage).status === 'ok').length;
  const stageText = stages.length ? `${completed}/${stages.length} stages${failed ? `, ${failed} failed` : ''}` : '';
  return `${status || 'unknown'}${stageText ? ` - ${stageText}` : ''}`;
}

export function actionPolicySummary(blockedActions: string[], handoffActions: string[]) {
  if (!blockedActions.length && !handoffActions.length) return 'no restrictions';
  const blockedText = blockedActions.length ? `${blockedActions.length} blocked` : 'none blocked';
  const handoffText = handoffActions.length ? `${handoffActions.length} handoff` : 'no handoff';
  return `${blockedText}, ${handoffText}`;
}

export function handoffFlowLabel(flow: Record<string, unknown>) {
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

export function policyEventLabel(event: Record<string, unknown>) {
  const reason = String(event.reason || 'blocked by runtime policy');
  const url = String(event.url || '-');
  const occurredAt = String(event.occurred_at || '');
  return `${reason} at ${url}${occurredAt ? ` (${occurredAt})` : ''}`;
}

export function validationLabel(value: unknown) {
  const evidence = actionConfig(value);
  if (!Object.keys(evidence).length) return 'pending browser check';
  const status = String(evidence.status || 'unknown');
  const confidence = formatConfidence(evidence.confidence);
  return `${status}${confidence === '-' ? '' : ` (${confidence})`}`;
}

export function readinessParamText(value: unknown) {
  const params = stringList(value);
  return params.length ? params.join(', ') : '-';
}

export function repairTargetLabel(value: unknown) {
  const repair = actionConfig(value);
  if (!Object.keys(repair).length) return '-';
  const target = String(repair.path || repair.selector || repair.form || repair.input || repair.submit || repair.label || '-');
  const confidence = formatConfidence(repair.confidence);
  return `${String(repair.type || 'repair')}: ${target}${confidence === '-' ? '' : ` (${confidence})`}`;
}

export function flowSummaryText(summary: Record<string, unknown>) {
  const pages = Number(summary.pages ?? 0);
  const actions = Number(summary.actions ?? 0);
  if (!pages && !actions) return 'pending';
  return `${pages} pages, ${actions} actions`;
}

export function rehearsalSummaryText(summary: Record<string, unknown>) {
  const total = Number(summary.total ?? 0);
  const supported = Number(summary.supported ?? 0);
  const blocked = Number(summary.blocked ?? 0);
  if (!total) return 'pending';
  return `${supported}/${total} supported${blocked ? `, ${blocked} blocked` : ''}`;
}

export function barrierSummaryText(summary: Record<string, unknown>) {
  const total = Number(summary.total ?? 0);
  const high = Number(summary.high ?? 0);
  const medium = Number(summary.medium ?? 0);
  if (!Object.keys(summary).length) return 'pending';
  if (!total) return 'none detected';
  return `${total} detected (${high} high, ${medium} medium)`;
}

export function barrierFindingLabel(finding: Record<string, unknown>) {
  const pageUrl = String(finding.page_url || '-');
  const evidence = String(finding.evidence || '');
  const handling = String(finding.handling || '');
  return `${pageUrl}${evidence ? ` - ${evidence}` : ''}${handling ? ` ${handling}` : ''}`;
}

export function rehearsalStepLabel(step: Record<string, unknown>) {
  const target = String(step.target || '-');
  const evidence = String(step.evidence || step.blocker || '');
  const confirmation = step.requires_confirmation ? ' Requires confirmation.' : '';
  return `${target}${evidence ? ` - ${evidence}` : ''}${confirmation}`;
}

export function regressionSummaryText(status: unknown, summary: Record<string, unknown>) {
  const changes = Number(summary.changes ?? 0);
  const high = Number(summary.high ?? 0);
  const medium = Number(summary.medium ?? 0);
  const statusText = String(status || '');
  if (summary.baseline) return 'baseline saved';
  if (!statusText && !Object.keys(summary).length) return 'pending';
  if (!changes) return statusText || 'stable';
  return `${changes} change${changes === 1 ? '' : 's'} (${high} high, ${medium} medium)`;
}

export function regressionChangeLabel(change: Record<string, unknown>) {
  const kind = String(change.kind || 'change');
  const previous = String(change.previous || '-');
  const current = String(change.current || '-');
  const evidence = String(change.evidence || '');
  return `${kind}: ${previous} -> ${current}${evidence ? ` - ${evidence}` : ''}`;
}

export function flowRepairProposalLabel(proposal: Record<string, unknown>) {
  const confidence = Math.round(Number(proposal.confidence || 0) * 100);
  const scope = String(proposal.scope || 'flow');
  const reason = String(proposal.reason || 'Review this flow repair before applying changes.');
  return `${scope} repair plan (${confidence}% confidence): ${reason}`;
}

export function capabilitySummary(capabilities: Record<string, unknown>) {
  if (!Object.keys(capabilities).length) return 'pending';
  const loaded = capabilities.script_loaded ? 'loaded' : 'not reported';
  const secure = capabilities.secure_context ? 'secure' : 'not secure';
  const mic = String(capabilities.microphone_permission || 'unknown');
  return `${loaded}, ${secure}, mic ${mic}`;
}

export function capabilityRows(capabilities: Record<string, unknown>) {
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

export function yesNo(value: unknown) {
  return value ? 'yes' : 'no';
}

export function stringList(value: unknown) {
  return Array.isArray(value) ? value.map((item) => String(item || '').trim()).filter(Boolean).slice(0, 10) : [];
}

export function recordList(value: unknown) {
  return Array.isArray(value)
    ? value.filter((item): item is Record<string, unknown> => Boolean(item) && typeof item === 'object').slice(0, 12)
    : [];
}
