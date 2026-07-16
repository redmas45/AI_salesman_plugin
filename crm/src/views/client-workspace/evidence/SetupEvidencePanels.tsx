import { ShieldCheck } from 'lucide-react';
import type { ReadinessReport } from '../../../types';
import type { ClientWorkspaceTabId, CrmVerticalDefinition } from '../../../verticals/types';
import { Button } from '../../../components/ui/Button';
import { Panel } from '../../../components/ui/Panel';
import { StatusPill } from '../../../components/ui/Badge';
import { EmptyState } from '../../../components/ui/EmptyState';
import { labelize, percent } from '../../../utils/format';
import { actionLabel } from '../components/actionLabels';
import { automationHintForCapability, readinessGapRows } from './readinessHelpers';

export function DomainActionCoveragePanel({
  scanReport,
  vertical,
  onOpenTab,
}: {
  scanReport: ReadinessReport | null;
  vertical: CrmVerticalDefinition;
  onOpenTab: (tab: ClientWorkspaceTabId) => void;
}) {
  const rows = domainActionRows(scanReport);
  const summary = domainActionSummary(scanReport);
  const supported = rows.filter((row) => row.supported).length;
  const total = rows.length;
  const complete = total > 0 && supported === total && (summary?.supported ?? true);
  const status = complete ? 'supported' : total > 0 ? 'needs work' : 'pending';
  const expectedActions = rows.length ? rows.map((row) => row.action) : domainActionPreview(vertical);
  return (
    <Panel
      title="Domain action coverage"
      action={
        <div className="domain-action-panel-actions">
          <Button variant="secondary" size="sm" onClick={() => onOpenTab('readiness')}>
            Open readiness
          </Button>
          <Button variant="secondary" size="sm" onClick={() => onOpenTab('adapter')}>
            Open adapter
          </Button>
        </div>
      }
    >
      <article className={`domain-action-summary ${complete ? 'ok' : 'warn'}`}>
        <div>
          <span>{vertical.label} action contract</span>
          <strong>{total ? `${supported}/${total} expected actions covered` : `${expectedActions.length} expected actions awaiting scan evidence`}</strong>
          <p>{summary?.evidence || 'Pending means no saved action-contract result exists yet. Run readiness or setup, then this panel will show covered and missing expected actions.'}</p>
        </div>
        <StatusPill value={status} />
      </article>
      {rows.length ? (
        <div className="domain-action-grid">
          {rows.map((row) => (
            <button key={row.action} type="button" className={`domain-action-row ${row.supported ? 'ok' : 'bad'}`} onClick={() => onOpenTab('readiness')}>
              <div className="domain-action-row-head">
                <div>
                  <strong>{actionLabel(row.action)}</strong>
                  <small>{row.action}</small>
                </div>
                <StatusPill value={row.supported ? 'supported' : 'needs work'} />
              </div>
              <p>{row.evidence || 'No scanner evidence was saved for this expected action.'}</p>
              <small>{percent(row.confidence)}% confidence</small>
            </button>
          ))}
        </div>
      ) : (
        <div className="domain-action-empty-board">
          <div className="domain-action-empty-main">
            <div>
              <span>Waiting for first evidence</span>
              <strong>No saved action evidence yet</strong>
              <p>
                Pending means this section has the expected action list, but no saved readiness/setup result has compared it with the live adapter yet.
              </p>
            </div>
            <div className="domain-action-panel-actions">
              <Button variant="secondary" size="sm" onClick={(event) => {
                event.stopPropagation();
                onOpenTab('readiness');
              }}>
                View readiness output
              </Button>
              <Button variant="secondary" size="sm" onClick={(event) => {
                event.stopPropagation();
                onOpenTab('adapter');
              }}>
                Inspect adapter
              </Button>
            </div>
          </div>
          <div className="domain-action-preview-grid" aria-label="Expected actions to verify">
            {expectedActions.map((action) => (
              <button key={action} type="button" onClick={() => onOpenTab('readiness')}>
                <ShieldCheck size={14} aria-hidden="true" />
                <span>
                  <strong>{actionLabel(action)}</strong>
                  <small>Open readiness output</small>
                </span>
              </button>
            ))}
          </div>
          <div className="domain-action-run-path" aria-label="Setup run path">
            <span>Readiness</span>
            <i aria-hidden="true" />
            <span>Discovery</span>
            <i aria-hidden="true" />
            <span>Rehearsal</span>
            <i aria-hidden="true" />
            <span>Evidence saved</span>
          </div>
        </div>
      )}
    </Panel>
  );
}

function domainActionPreview(vertical: CrmVerticalDefinition) {
  const actions = vertical.actionTypes?.length
    ? vertical.actionTypes
    : vertical.readinessChecks.map((check) => check.toUpperCase());
  return actions.slice(0, 8);
}

function domainActionSummary(scanReport: ReadinessReport | null) {
  return scanReport?.capabilities.find((capability) => capability.name === 'domain_action_coverage') ?? null;
}

function domainActionRows(scanReport: ReadinessReport | null) {
  return (scanReport?.capabilities ?? [])
    .filter((capability) => capability.name.startsWith('expected_action:'))
    .map((capability) => ({
      action: capability.name.replace('expected_action:', ''),
      supported: capability.supported,
      confidence: capability.confidence,
      evidence: capability.evidence,
    }));
}

export function ReadinessGapEvidencePanel({
  scanReport,
  onOpenTab,
}: {
  scanReport: ReadinessReport | null;
  onOpenTab: (tab: ClientWorkspaceTabId) => void;
}) {
  const gaps = readinessGapRows(scanReport);
  return (
    <Panel
      title="Readiness checks needing automation"
      action={
        gaps.length ? (
          <Button variant="secondary" size="sm" onClick={() => onOpenTab('readiness')}>
            Open readiness
          </Button>
        ) : null
      }
    >
      {gaps.length ? (
        <div className="integration-list">
          {gaps.map((capability) => (
            <article key={capability.name} className={`integration-list-item ${capability.confidence >= 0.5 ? 'medium' : 'high'}`}>
              <StatusPill value="needs work" />
              <div>
                <strong>{labelize(capability.name)}</strong>
                <p>{capability.evidence || 'No scanner evidence was saved for this readiness check.'}</p>
                <p>
                  {percent(capability.confidence)}% confidence. {automationHintForCapability(capability.name)}
                </p>
              </div>
            </article>
          ))}
        </div>
      ) : (
        <EmptyState
          title={scanReport ? 'No unsupported readiness checks found' : 'No readiness evidence yet'}
          message={scanReport ? 'The latest readiness evidence does not show any non-domain checks needing automation.' : 'Use the operator center to run setup; per-check evidence will appear here afterward.'}
        />
      )}
    </Panel>
  );
}
