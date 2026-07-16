import { labelize, number } from '../../../utils/format';
import { recordArray, safeRecord, stringArray } from './integrationEvidenceUtils';
import type { IntegrationStageRow, IntegrationStageStatus } from './integrationEvidence';

export interface IntegrationSmokeTest {
  name: string;
  prompt: string;
  status: IntegrationStageStatus;
  expectedActions: string[];
  actualActions: string[];
  matchedActions: string[];
  expectedResponseTerms: string[];
  matchedResponseTerms: string[];
  requiredResponseTerms: string[];
  matchedRequiredResponseTerms: string[];
  displayActionEvidence: Record<string, unknown>[];
  retrievalEvidence: Record<string, unknown>;
  intent: string;
  responseExcerpt: string;
  failureKind: string;
  reason: string;
  recommendedFix: string;
}

export function assistantSmokeSummary(
  stages: IntegrationStageRow[],
  standaloneReport: Record<string, unknown>,
  preferStandalone = false,
) {
  const stage = stages.find((item) => item.name === 'assistant_smoke_tests');
  const standaloneHasTests = Array.isArray(standaloneReport.tests) && standaloneReport.tests.length > 0;
  const source = preferStandalone && standaloneHasTests ? standaloneReport : stage ? stage.raw : standaloneReport;
  if (!Object.keys(source).length) return 'not run';
  const status = String(source.status || 'unknown');
  const passed = Number(source.passed ?? 0);
  const total = Number(source.total ?? 0);
  const failed = Number(source.failed ?? 0);
  const mode = source === standaloneReport ? 'quick run' : 'setup run';
  if (!total) return `${status} from ${mode}`;
  return `${passed}/${total} passed${failed ? `, ${failed} failed` : ''} from ${mode}`;
}

export function integrationSmokeTests(
  stages: IntegrationStageRow[],
  standaloneReport: Record<string, unknown> = {},
  preferStandalone = false,
): IntegrationSmokeTest[] {
  const stage = stages.find((item) => item.name === 'assistant_smoke_tests');
  const standaloneTests: unknown[] = Array.isArray(standaloneReport.tests) ? standaloneReport.tests : [];
  const stageTests: unknown[] = Array.isArray(stage?.raw.tests) ? stage.raw.tests : [];
  const rawTests = preferStandalone && standaloneTests.length ? standaloneTests : stageTests.length ? stageTests : standaloneTests;
  return rawTests
    .filter((item): item is Record<string, unknown> => Boolean(item) && typeof item === 'object')
    .map((item) => ({
      name: String(item.name || item.prompt || 'smoke_test'),
      prompt: String(item.prompt || item.name || 'Prompt smoke test'),
      status: integrationStageStatus(item.status),
      expectedActions: stringArray(item.expected_actions),
      actualActions: stringArray(item.actual_actions),
      matchedActions: stringArray(item.matched_actions),
      expectedResponseTerms: stringArray(item.expected_response_terms_any),
      matchedResponseTerms: stringArray(item.matched_response_terms),
      requiredResponseTerms: stringArray(item.expected_response_terms_all),
      matchedRequiredResponseTerms: stringArray(item.matched_response_terms_all),
      displayActionEvidence: recordArray(item.display_action_evidence),
      retrievalEvidence: safeRecord(item.retrieval_evidence),
      intent: String(item.intent || ''),
      responseExcerpt: String(item.response_excerpt || ''),
      failureKind: String(item.failure_kind || ''),
      reason: String(item.reason || ''),
      recommendedFix: String(item.recommended_fix || ''),
    }));
}

export function smokeTestHeadline(test: IntegrationSmokeTest) {
  if (test.reason) return test.reason;
  if (test.status === 'ok') return 'Passed: expected actions, action IDs, data retrieval, and response checks are aligned.';
  return 'Needs review: compare the expected action, retrieved data, action IDs, and response text below.';
}

export function smokeResponseTermsSummary(test: IntegrationSmokeTest) {
  const parts = [];
  if (test.expectedResponseTerms.length) {
    parts.push(`any: expected ${test.expectedResponseTerms.join(', ')}; matched ${test.matchedResponseTerms.join(', ') || 'none'}`);
  }
  if (test.requiredResponseTerms.length) {
    parts.push(`all: expected ${test.requiredResponseTerms.join(', ')}; matched ${test.matchedRequiredResponseTerms.join(', ') || 'none'}`);
  }
  return parts.join(' / ') || 'no response term check configured';
}

export function smokeResponseTermsTone(test: IntegrationSmokeTest): 'ok' | 'warn' | 'neutral' {
  const anyOk = !test.expectedResponseTerms.length || test.matchedResponseTerms.length > 0;
  const allOk = !test.requiredResponseTerms.length || test.matchedRequiredResponseTerms.length >= test.requiredResponseTerms.length;
  if (!test.expectedResponseTerms.length && !test.requiredResponseTerms.length) return 'neutral';
  return anyOk && allOk ? 'ok' : 'warn';
}

export function smokeRetrievalTone(evidence: Record<string, unknown>): 'ok' | 'warn' | 'bad' | 'neutral' {
  if (!Object.keys(evidence).length) return 'warn';
  const issue = String(evidence.issue || '').toLowerCase();
  if (issue === 'ok') return 'ok';
  if (issue === 'no_active_records' || issue === 'retrieval_returned_zero' || issue === 'all_vectors_missing') return 'bad';
  return 'warn';
}

export function displayActionEvidenceSummary(items: Record<string, unknown>[]) {
  return items.map((item) => {
    const action = String(item.action || 'action');
    const idParam = String(item.id_param || 'ids');
    const count = Number(item.id_count ?? 0);
    const ids = stringArray(item.ids).slice(0, 3).join(', ');
    return `${action}: ${number(count)} ${idParam}${ids ? ` (${ids})` : ''}`;
  }).join(' / ');
}

export function smokeRetrievalEvidenceSummary(evidence: Record<string, unknown>) {
  if (!Object.keys(evidence).length) return '';
  const source = String(evidence.source || 'records');
  const retrieved = Number(evidence.retrieved_count ?? 0);
  const active = Number(evidence.active_records ?? 0);
  const missing = Number(evidence.missing_embeddings ?? 0);
  const issue = labelize(String(evidence.issue || 'unknown'));
  const titles = stringArray(evidence.retrieved_titles).slice(0, 3).join(', ');
  const summary = `${number(retrieved)} retrieved / ${number(active)} active ${source}; ${number(missing)} missing vectors; issue: ${issue}`;
  return titles ? `${summary}; samples: ${titles}` : summary;
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
