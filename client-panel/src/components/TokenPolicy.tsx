import { type FormEvent, useState } from 'react';
import { updateSessionLimit } from '../api';
import type { ClientSummary } from '../types';
import { normalizePositiveInteger, number, percent } from '../utils';
import { panelText } from '../verticalText';
import { PanelHeader, Progress } from './ui';

export function TokenSnapshot({
  client,
  onLimitUpdated,
}: {
  client: ClientSummary;
  onLimitUpdated: (client: ClientSummary) => void;
}) {
  return (
    <section className="panel">
      <PanelHeader title="Token snapshot" detail={client.status} />
      <Progress value={percent(client.quota.client.used, client.quota.client.limit)} />
      <p className="muted">
        {number(client.quota.client.used)} of {number(client.quota.client.limit)} purchased tokens used.
      </p>
      <TokenLimitForm client={client} onLimitUpdated={onLimitUpdated} compact />
    </section>
  );
}

export function TokenPolicy({
  client,
  onLimitUpdated,
}: {
  client: ClientSummary;
  onLimitUpdated: (client: ClientSummary) => void;
}) {
  const text = panelText(client);
  return (
    <section className="panel">
      <PanelHeader title={text.sessionLimitTitle} detail="editable" />
      <Progress value={percent(client.quota.client.used, client.quota.client.limit)} />
      <p className="muted">
        {number(client.quota.client.remaining)} purchased tokens remain. {text.sessionLimitDetail}
      </p>
      <TokenLimitForm client={client} onLimitUpdated={onLimitUpdated} />
    </section>
  );
}

function TokenLimitForm({
  client,
  compact = false,
  onLimitUpdated,
}: {
  client: ClientSummary;
  compact?: boolean;
  onLimitUpdated: (client: ClientSummary) => void;
}) {
  const [limit, setLimit] = useState(String(client.session_token_limit));
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState('');

  async function submit(event: FormEvent<HTMLFormElement>): Promise<void> {
    event.preventDefault();
    setBusy(true);
    setMessage('');
    try {
      const updated = await updateSessionLimit(Number(limit));
      onLimitUpdated(updated);
      setMessage('Saved.');
    } catch (err) {
      setMessage(err instanceof Error ? err.message : 'Policy update failed.');
    } finally {
      setBusy(false);
    }
  }

  return (
    <form className={`policy-form ${compact ? 'compact' : ''}`} onSubmit={submit}>
      <label>
        <span>{panelText(client).sessionLimitTitle}</span>
        <input
          value={limit}
          onChange={(event) => setLimit(event.currentTarget.value)}
          onBlur={() => setLimit(normalizePositiveInteger(limit))}
          type="number"
          min={1}
          max={1000000}
          step={1}
        />
      </label>
      <button className="btn btn-secondary" type="submit" disabled={busy}>Save limit</button>
      {message ? <p className="muted">{message}</p> : null}
    </form>
  );
}
