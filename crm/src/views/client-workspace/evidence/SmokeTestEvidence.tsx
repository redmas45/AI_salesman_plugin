import type { ReactNode } from 'react';
import {
  displayActionEvidenceSummary,
  smokeResponseTermsSummary,
  smokeResponseTermsTone,
  smokeRetrievalEvidenceSummary,
  smokeRetrievalTone,
  type IntegrationSmokeTest,
} from './integrationEvidence';

export function SmokeTestEvidence({ test }: { test: IntegrationSmokeTest }): ReactNode {
  return (
    <div className="smoke-evidence-grid">
      <SmokeEvidenceLine label="Expected actions" value={test.expectedActions.join(', ') || 'none'} />
      <SmokeEvidenceLine label="Actual actions" value={test.actualActions.join(', ') || 'none'} />
      <SmokeEvidenceLine label="Matched actions" value={test.matchedActions.join(', ') || 'none'} tone={test.matchedActions.length ? 'ok' : 'warn'} />
      <SmokeEvidenceLine label="Intent" value={test.intent || 'unknown'} />
      <SmokeEvidenceLine label="Failure kind" value={test.failureKind || 'none'} tone={test.failureKind ? 'bad' : 'ok'} />
      <SmokeEvidenceLine label="Action IDs" value={displayActionEvidenceSummary(test.displayActionEvidence) || 'no display action IDs captured'} tone={test.displayActionEvidence.length ? 'ok' : 'warn'} />
      <SmokeEvidenceLine label="Data evidence" value={smokeRetrievalEvidenceSummary(test.retrievalEvidence) || 'no retrieval evidence saved'} tone={smokeRetrievalTone(test.retrievalEvidence)} />
      <SmokeEvidenceLine label="Response terms" value={smokeResponseTermsSummary(test)} tone={smokeResponseTermsTone(test)} />
      <SmokeEvidenceLine label="Fix" value={test.recommendedFix || 'No fix needed from this smoke result.'} tone={test.recommendedFix ? 'warn' : 'ok'} />
      {test.responseExcerpt ? <SmokeEvidenceLine label="Response excerpt" value={test.responseExcerpt} wide /> : null}
    </div>
  );
}

function SmokeEvidenceLine({
  label,
  value,
  tone = 'neutral',
  wide = false,
}: {
  label: string;
  value: string;
  tone?: 'ok' | 'warn' | 'bad' | 'neutral';
  wide?: boolean;
}): ReactNode {
  return (
    <div className={`smoke-evidence-line smoke-evidence-${tone}${wide ? ' smoke-evidence-wide' : ''}`}>
      <span>{label}</span>
      <b>{value}</b>
    </div>
  );
}
