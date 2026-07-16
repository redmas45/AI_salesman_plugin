import type { IntegrationSummary } from '../types';
import { number } from '../utils';
import { EmptyState, KeyLine, PanelHeader, Progress, StatusPill } from './ui';

export function IntegrationHealth({ integration }: { integration?: IntegrationSummary }) {
  if (!integration) {
    return (
      <section className="panel integration-health">
        <PanelHeader title="Setup health" detail="AI Hub evidence" />
        <EmptyState
          title="No setup summary yet"
          message="Ask the AI Hub admin to refresh the client panel after running readiness or setup."
          compact
        />
      </section>
    );
  }

  const unsupported = integration.readiness.unsupported.slice(0, 3);
  const informational = integration.readiness.informational?.slice(0, 3) ?? [];
  return (
    <section className="panel integration-health">
      <PanelHeader title="Setup health" detail="AI Hub evidence" />
      <div className="integration-health-head">
        <div>
          <span>Overall readiness</span>
          <strong>{number(integration.score)}%</strong>
        </div>
        <StatusPill label={statusLabel(integration.status)} />
      </div>
      <Progress value={integration.score} danger={integration.score < 75} />
      <div className="integration-health-grid">
        <KeyLine label="Records indexed" value={number(integration.active_records)} />
        <KeyLine label="Missing vectors" value={number(integration.missing_vectors)} />
        <KeyLine
          label="Domain actions"
          value={`${number(integration.domain_actions.covered)}/${number(integration.domain_actions.total)} covered`}
        />
        <KeyLine
          label="Prompt tests"
          value={`${number(integration.prompt_tests.passed)}/${number(integration.prompt_tests.total)} passed`}
        />
      </div>
      <div className="integration-health-note">
        <strong>Next action</strong>
        <p>{integration.next_action}</p>
      </div>
      <div className="integration-health-note">
        <strong>Domain evidence</strong>
        <p>{integration.domain_actions.evidence}</p>
      </div>
      {unsupported.length ? (
        <div className="integration-gap-list">
          {unsupported.map((row) => (
            <article key={row.name}>
              <strong>{labelize(row.name)}</strong>
              <span>{number(Math.round(row.confidence * 100))}% confidence</span>
              <p>{row.evidence}</p>
            </article>
          ))}
        </div>
      ) : null}
      {informational.length ? (
        <div className="integration-gap-list">
          {informational.map((row) => (
            <article key={row.name}>
              <strong>{labelize(row.name)}</strong>
              <span>Informational</span>
              <p>{row.evidence}</p>
            </article>
          ))}
        </div>
      ) : null}
    </section>
  );
}

function statusLabel(status: string) {
  if (status === 'ready') return 'Ready';
  if (status === 'watch') return 'Watch';
  if (status === 'needs_work') return 'Needs work';
  return 'Pending';
}

function labelize(value: string) {
  return value
    .replace(/[_:-]+/g, ' ')
    .replace(/\s+/g, ' ')
    .trim()
    .replace(/\b\w/g, (letter) => letter.toUpperCase());
}
