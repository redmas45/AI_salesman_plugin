import type { Client, CapabilitiesSummary, CrawlReport, ReadinessReport } from '../../../types';
import { number, percent, shortTime } from '../../../utils/format';
import type { CrmVerticalDefinition } from '../../../verticals/types';
import type { IntegrationSmokeTest } from './integrationSmokeEvidence';
import { safeRecord, stringArray } from './integrationEvidenceUtils';

export { safeRecord } from './integrationEvidenceUtils';
export {
  assistantSmokeSummary,
  displayActionEvidenceSummary,
  integrationSmokeTests,
  smokeResponseTermsSummary,
  smokeResponseTermsTone,
  smokeRetrievalEvidenceSummary,
  smokeRetrievalTone,
  smokeTestHeadline,
} from './integrationSmokeEvidence';
export type { IntegrationSmokeTest } from './integrationSmokeEvidence';

export type IntegrationStageStatus = 'ok' | 'running' | 'pending' | 'skipped' | 'failed' | 'unknown';

export interface IntegrationStageRow {
  name: string;
  label: string;
  status: IntegrationStageStatus;
  message: string;
  detail: string;
  raw: Record<string, unknown>;
}

export interface IntegrationGap {
  severity: 'high' | 'medium' | 'low';
  title: string;
  detail: string;
}

const EXPECTED_INTEGRATION_STAGES = [
  {
    name: 'crawl',
    label: 'Content crawl',
    pending: 'No completed crawl stage is saved yet.',
    detail: 'Collects source pages, catalog rows, policy records, and knowledge records.',
  },
  {
    name: 'flow_discovery',
    label: 'Flow discovery',
    pending: 'No flow graph is saved yet.',
    detail: 'Finds routes, buttons, forms, fields, navigation paths, and possible adapter actions.',
  },
  {
    name: 'flow_rehearsal',
    label: 'Flow rehearsal',
    pending: 'No action rehearsal is saved yet.',
    detail: 'Safely checks whether discovered actions can run without completing high-risk final steps.',
  },
  {
    name: 'flow_regression',
    label: 'Regression check',
    pending: 'No baseline comparison is saved yet.',
    detail: 'Compares current routes/actions against the previous setup picture.',
  },
  {
    name: 'readiness_scan',
    label: 'Readiness scan',
    pending: 'No readiness evidence is saved yet.',
    detail: 'Summarizes platform, source coverage, supported actions, and automation gaps.',
  },
  {
    name: 'assistant_smoke_tests',
    label: 'Assistant smoke tests',
    pending: 'No assistant prompt smoke tests are saved yet.',
    detail: 'Runs real text prompts through Maya and verifies expected UI actions so CRM catches no-record or no-action failures.',
  },
];

export function integrationStageRows(
  initialization: Record<string, unknown>,
  evidence: {
    crawlReport: CrawlReport | null;
    flow: Record<string, unknown>;
    rehearsal: Record<string, unknown>;
    regression: Record<string, unknown>;
    scanReport: ReadinessReport | null;
  },
): IntegrationStageRow[] {
  const savedStages = Array.isArray(initialization.stages)
    ? initialization.stages.filter((stage): stage is Record<string, unknown> => Boolean(stage) && typeof stage === 'object')
    : [];
  return EXPECTED_INTEGRATION_STAGES.map((expected) => {
    const saved = savedStages.find((stage) => String(stage.name || '') === expected.name);
    if (saved) {
      return {
        name: expected.name,
        label: expected.label,
        status: integrationStageStatus(saved.status),
        message: String(saved.message || expected.pending),
        detail: integrationStageDetail(expected.name, saved, expected.detail),
        raw: saved,
      };
    }
    const inferred = inferredIntegrationStage(expected.name, evidence);
    return {
      name: expected.name,
      label: expected.label,
      status: inferred.status,
      message: inferred.message || expected.pending,
      detail: inferred.detail || expected.detail,
      raw: {},
    };
  });
}

export function liveIntegrationStageRows(stages: IntegrationStageRow[], autoIntegrating: boolean): IntegrationStageRow[] {
  if (!autoIntegrating || stages.some((stage) => stage.status === 'running')) return stages;
  return [
    {
      name: 'integration_queue',
      label: 'Backend queue',
      status: 'running',
      message: 'Setup run request accepted.',
      detail: 'Waiting for the first saved backend stage report; existing evidence below stays visible until replaced.',
      raw: {},
    },
    ...stages,
  ];
}

function inferredIntegrationStage(
  name: string,
  evidence: {
    crawlReport: CrawlReport | null;
    flow: Record<string, unknown>;
    rehearsal: Record<string, unknown>;
    regression: Record<string, unknown>;
    scanReport: ReadinessReport | null;
  },
): Pick<IntegrationStageRow, 'status' | 'message' | 'detail'> {
  if (name === 'crawl' && evidence.crawlReport) {
    return {
      status: 'ok',
      message: `${number(evidence.crawlReport.product_count)} records from ${number(evidence.crawlReport.pages_visited)} visited pages.`,
      detail: `${number(evidence.crawlReport.pages_failed)} failed pages, ${percent(evidence.crawlReport.coverage_score)}% coverage.`,
    };
  }
  if (name === 'flow_discovery' && Object.keys(evidence.flow).length) {
    const summary = safeRecord(evidence.flow.summary);
    return {
      status: 'ok',
      message: flowSummaryText(summary),
      detail: `Engine: ${String(evidence.flow.engine || 'flow discovery')}.`,
    };
  }
  if (name === 'flow_rehearsal' && Object.keys(evidence.rehearsal).length) {
    return {
      status: 'ok',
      message: rehearsalSummaryText(safeRecord(evidence.rehearsal.summary)),
      detail: `Steps: ${Array.isArray(evidence.rehearsal.steps) ? evidence.rehearsal.steps.length : 0}.`,
    };
  }
  if (name === 'flow_regression' && Object.keys(evidence.regression).length) {
    return {
      status: 'ok',
      message: regressionSummaryText(evidence.regression.status, safeRecord(evidence.regression.summary)),
      detail: `Compared: ${String(evidence.regression.compared_at || '-')}.`,
    };
  }
  if (name === 'readiness_scan' && evidence.scanReport) {
    const supported = evidence.scanReport.capabilities.filter((capability) => capability.supported).length;
    return {
      status: 'ok',
      message: `${supported}/${evidence.scanReport.capabilities.length} checks supported.`,
      detail: `${evidence.scanReport.platform || 'unknown'} at ${percent(evidence.scanReport.platform_confidence)}% confidence.`,
    };
  }
  return { status: 'pending', message: '', detail: '' };
}

function integrationStageStatus(value: unknown): IntegrationStageStatus {
  const status = String(value || '').toLowerCase();
  if (status === 'ok') return 'ok';
  if (status === 'running') return 'running';
  if (status === 'skipped') return 'skipped';
  if (status === 'failed' || status === 'error') return 'failed';
  if (status === 'pending') return 'pending';
  return 'unknown';
}

function integrationStageDetail(name: string, stage: Record<string, unknown>, fallback: string) {
  if (name === 'flow_discovery') {
    const summary = safeRecord(stage.summary);
    if (Object.keys(summary).length) return flowSummaryText(summary);
  }
  if (name === 'flow_rehearsal') {
    const summary = safeRecord(stage.summary);
    if (Object.keys(summary).length) return rehearsalSummaryText(summary);
  }
  if (name === 'readiness_scan') {
    const supported = Number(stage.supported ?? 0);
    const total = Number(stage.total ?? 0);
    if (total) return `${supported}/${total} readiness checks supported.`;
  }
  if (name === 'assistant_smoke_tests') {
    const passed = Number(stage.passed ?? 0);
    const total = Number(stage.total ?? 0);
    const failed = Number(stage.failed ?? 0);
    if (total) return `${passed}/${total} prompts passed${failed ? `, ${failed} failed` : ''}.`;
  }
  if (stage.regression_status) return `Regression status: ${String(stage.regression_status)}.`;
  if (stage.started_at && integrationStageStatus(stage.status) === 'running') return `Started ${shortTime(String(stage.started_at))}.`;
  if (stage.completed_at) return `Completed ${shortTime(String(stage.completed_at))}.`;
  return fallback;
}

export function integrationInitializationSummary(initialization: Record<string, unknown>, autoIntegrating = false) {
  const status = String(initialization.status || '').trim();
  const stages = Array.isArray(initialization.stages)
    ? initialization.stages.filter((stage): stage is Record<string, unknown> => Boolean(stage) && typeof stage === 'object')
    : [];
  if (autoIntegrating && status !== 'running') {
    const existing = status || (stages.length ? 'previous evidence saved' : 'not started');
    return `running now - ${existing}`;
  }
  if (!status && !stages.length) return 'not started';
  const failed = stages.filter((stage) => integrationStageStatus(stage.status) === 'failed').length;
  const completed = stages.filter((stage) => integrationStageStatus(stage.status) === 'ok').length;
  const stageText = stages.length ? `${completed}/${stages.length} stages${failed ? `, ${failed} failed` : ''}` : '';
  return `${status || 'unknown'}${stageText ? ` - ${stageText}` : ''}`;
}

export function currentIntegrationStageLabel(stages: IntegrationStageRow[]) {
  const running = stages.find((stage) => stage.status === 'running');
  if (running) return running.label;
  const failed = stages.find((stage) => stage.status === 'failed');
  if (failed) return `${failed.label} failed`;
  const pending = stages.find((stage) => stage.status === 'pending' || stage.status === 'unknown');
  return pending ? `${pending.label} pending` : 'complete';
}

function flowSummaryText(summary: Record<string, unknown>) {
  const pages = Number(summary.pages ?? 0);
  const actions = Number(summary.actions ?? 0);
  if (!pages && !actions) return 'pending';
  return `${number(pages)} pages, ${number(actions)} actions`;
}

function rehearsalSummaryText(summary: Record<string, unknown>) {
  const total = Number(summary.total ?? 0);
  const supported = Number(summary.supported ?? 0);
  const blocked = Number(summary.blocked ?? 0);
  if (!total) return 'pending';
  return `${number(supported)}/${number(total)} supported${blocked ? `, ${number(blocked)} blocked` : ''}`;
}

function regressionSummaryText(status: unknown, summary: Record<string, unknown>) {
  const changes = Number(summary.changes ?? 0);
  const high = Number(summary.high ?? 0);
  const medium = Number(summary.medium ?? 0);
  const statusText = String(status || '');
  if (summary.baseline) return 'baseline saved';
  if (!statusText && !Object.keys(summary).length) return 'pending';
  if (!changes) return statusText || 'stable';
  return `${number(changes)} change${changes === 1 ? '' : 's'} (${number(high)} high, ${number(medium)} medium)`;
}

export function integrationScore(
  client: Client,
  capabilities: CapabilitiesSummary | null,
  stages: IntegrationStageRow[],
  flow: Record<string, unknown>,
  rehearsal: Record<string, unknown>,
  actionHealth: Record<string, unknown>,
  smokeTests: IntegrationSmokeTest[] = [],
) {
  const checks = [
    client.status !== 'available',
    client.catalog.active_products > 0,
    client.catalog.active_products === 0 || client.catalog.missing_embeddings < client.catalog.active_products,
    stages.some((stage) => stage.name === 'crawl' && stage.status === 'ok'),
    Object.keys(flow).length > 0,
    Object.keys(rehearsal).length > 0,
    Boolean(capabilities && capabilities.supported.length > 0),
    Boolean(capabilities && capabilities.unsupported.length === 0),
    smokeTests.length > 0 && smokeTests.every((test) => test.status === 'ok'),
    Number(safeRecord(actionHealth.summary).needs_repair ?? 0) === 0,
    Boolean(client.panel_password_configured),
  ];
  const ready = checks.filter(Boolean).length;
  return Math.round((ready / checks.length) * 100);
}

export function integrationGaps(
  client: Client,
  capabilities: CapabilitiesSummary | null,
  stages: IntegrationStageRow[],
  flow: Record<string, unknown>,
  actionHealth: Record<string, unknown>,
  actionPolicy: Record<string, unknown>,
  automationLocked: boolean,
  smokeTests: IntegrationSmokeTest[] = [],
): IntegrationGap[] {
  const gaps: IntegrationGap[] = [];
  if (automationLocked) {
    gaps.push({
      severity: 'high',
      title: 'Client is still Available',
      detail: 'Move it to Current before setup. This action only changes lifecycle state; it does not start crawling.',
    });
  }
  if (!stages.some((stage) => stage.status === 'ok')) {
    gaps.push({
      severity: 'high',
      title: 'No setup run evidence',
      detail: 'Run setup to produce crawl, flow, rehearsal, regression, and readiness evidence.',
    });
  }
  if (client.catalog.active_products <= 0) {
    gaps.push({
      severity: 'high',
      title: 'No active records',
      detail: 'The assistant cannot compare or recommend reliably until crawl/data sync loads source records.',
    });
  }
  if (client.catalog.missing_embeddings > 0) {
    gaps.push({
      severity: 'medium',
      title: 'Vector sync is incomplete',
      detail: `${number(client.catalog.missing_embeddings)} records are missing embeddings, so retrieval may miss relevant records.`,
    });
  }
  if (!Object.keys(flow).length) {
    gaps.push({
      severity: 'medium',
      title: 'No flow graph',
      detail: 'Navigation, forms, and action routing are not fully mapped yet. Run setup or Discover flows.',
    });
  }
  const failedSmokeTests = smokeTests.filter((test) => test.status === 'failed');
  if (failedSmokeTests.length) {
    gaps.push({
      severity: 'high',
      title: 'Assistant smoke tests failed',
      detail: `${failedSmokeTests.length} real prompt(s) failed. First failure: ${failedSmokeTests[0].reason || failedSmokeTests[0].prompt}`,
    });
  } else if (!automationLocked && !smokeTests.length) {
    gaps.push({
      severity: 'medium',
      title: 'Assistant smoke tests have not run',
      detail: 'Run prompt tests so CRM verifies comparison, sorting, navigation, and recommendation prompts instead of relying on visual readiness alone.',
    });
  }
  const unsupported = capabilities?.unsupported ?? [];
  if (unsupported.length) {
    gaps.push({
      severity: 'medium',
      title: 'Readiness has unsupported checks',
      detail: `${unsupported.length} check(s) still need automation or a safer handoff rule: ${unsupported.slice(0, 5).join(', ')}.`,
    });
  }
  const needsRepair = Number(safeRecord(actionHealth.summary).needs_repair ?? 0);
  if (needsRepair > 0) {
    gaps.push({
      severity: 'high',
      title: 'Runtime action failures need repair',
      detail: `${needsRepair} action(s) need selector, route, or policy repair from recent runtime evidence.`,
    });
  }
  const blocked = stringArray(actionPolicy.blocked_actions);
  if (blocked.length) {
    gaps.push({
      severity: 'low',
      title: 'Some actions require handoff',
      detail: `${blocked.slice(0, 5).join(', ')} are intentionally blocked by policy or provider constraints.`,
    });
  }
  if (!client.panel_password_configured) {
    gaps.push({
      severity: 'medium',
      title: 'Client panel password is not configured',
      detail: 'Set or generate a panel password before sharing the client-facing analytics panel.',
    });
  }
  return gaps;
}

export function integrationFixes(gaps: IntegrationGap[], vertical: CrmVerticalDefinition) {
  if (!gaps.length) {
    return [
      {
        kind: 'ok',
        title: 'Run real prompt smoke tests',
        detail: `Use the prompts below to verify comparison, navigation, recommendations, and ${vertical.entityLabelPlural} retrieval after every site change.`,
      },
    ];
  }
  return gaps.slice(0, 6).map((gap) => ({
    kind: gap.severity,
    title: fixTitleForGap(gap.title),
    detail: fixDetailForGap(gap.title),
  }));
}

function fixTitleForGap(title: string) {
  if (title.includes('Available')) return 'Move to Current, then run setup';
  if (title.includes('smoke tests')) return 'Repair prompt, retrieval, or adapter action mapping';
  if (title.includes('records')) return 'Refresh crawl/data sync';
  if (title.includes('Vector')) return 'Run crawl or vector sync';
  if (title.includes('flow')) return 'Run flow discovery and rehearsal';
  if (title.includes('Readiness')) return 'Run setup and inspect unsupported checks';
  if (title.includes('action failures')) return 'Approve or repair adapter proposals';
  if (title.includes('panel password')) return 'Generate a client panel password';
  return 'Review the setup evidence';
}

function fixDetailForGap(title: string) {
  if (title.includes('Available')) return 'Use Add to current first. Then the setup run will crawl, discover flows, rehearse actions, and rescan readiness.';
  if (title.includes('smoke tests')) return 'Open the smoke-test panel below, compare expected vs actual actions, then inspect Data storage, Prompt profile, and Adapter evidence for the failing prompt.';
  if (title.includes('records')) return 'Confirm the source website is live, then run setup. If records stay empty, inspect Data storage and Crawl report.';
  if (title.includes('Vector')) return 'Run a crawl so missing embeddings can be refreshed for retrieval.';
  if (title.includes('flow')) return 'Open Adapter evidence after the setup run to review routes, selectors, barriers, and repair proposals.';
  if (title.includes('Readiness')) return 'Unsupported checks explain what is not automated and whether it needs a custom adapter or handoff.';
  if (title.includes('action failures')) return 'Use Adapter evidence to approve safe repairs or keep provider-gated actions as handoff-only.';
  if (title.includes('panel password')) return 'Use Manage password before sharing the Client Panel URL.';
  return 'Open the related tab listed below and inspect the saved evidence.';
}

export function nextIntegrationAction(gaps: IntegrationGap[], automationLocked: boolean, autoIntegrating: boolean) {
  if (automationLocked) return 'Move client to Current; activation will not crawl or run setup.';
  if (autoIntegrating) return 'Wait for backend stage evidence to refresh.';
  const high = gaps.find((gap) => gap.severity === 'high');
  if (high) return high.title;
  const medium = gaps.find((gap) => gap.severity === 'medium');
  if (medium) return medium.title;
  if (gaps.length) return gaps[0].title;
  return 'Run real browser prompts after any website layout or catalog change.';
}

export function actionHealthSummary(actionHealth: Record<string, unknown>) {
  const summary = safeRecord(actionHealth.summary);
  if (!Object.keys(summary).length) return 'no runtime failures reported';
  return `${number(Number(summary.tracked ?? 0))} tracked, ${number(Number(summary.needs_repair ?? 0))} need repair`;
}
