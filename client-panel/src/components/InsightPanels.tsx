
import { type FormEvent, useEffect, useMemo, useState } from 'react';
import {
  buildCatalogOpportunities,
  buildIntentSignals,
  buildTodayBrief,
  fullSessionsRemaining,
  makeVisitSnapshot,
  readVisitSnapshot,
  simulateQuestion,
  tokenDaysLeft,
  visitChanges,
  writeVisitSnapshot,
  type BriefItem,
} from '../insights';
import type { Analytics, ClientSummary, RankRow } from '../types';
import { number, type ConversationPreview } from '../utils';
import { panelText } from '../verticalText';
import { EmptyState, PanelHeader } from './ui';

export function TodayBrief({
  client,
  analytics,
  sessions,
}: {
  client: ClientSummary;
  analytics: Analytics;
  sessions: ConversationPreview[];
}) {
  return (
    <section className="panel insight-panel today-brief">
      <PanelHeader title="Today's brief" detail="what matters now" />
      <InsightList items={buildTodayBrief(client, analytics, sessions)} />
    </section>
  );
}

export function SinceLastVisit({
  client,
  analytics,
  sessions,
}: {
  client: ClientSummary;
  analytics: Analytics;
  sessions: ConversationPreview[];
}) {
  const currentSnapshot = useMemo(
    () => makeVisitSnapshot(client, analytics, sessions),
    [client, analytics, sessions],
  );
  const [previousSnapshot] = useState(() => readVisitSnapshot(client.site_id));
  const changes = useMemo(
    () => visitChanges(previousSnapshot, currentSnapshot),
    [previousSnapshot, currentSnapshot],
  );

  useEffect(() => {
    writeVisitSnapshot(currentSnapshot);
  }, [currentSnapshot]);

  return (
    <section className="panel insight-panel">
      <PanelHeader title="Since last visit" detail={previousSnapshot ? 'browser memory' : 'new baseline'} />
      <InsightList items={changes} compact />
    </section>
  );
}

export function IntentInbox({ client, sessions }: { client: ClientSummary; sessions: ConversationPreview[] }) {
  const text = panelText(client);
  const signals = buildIntentSignals(sessions);
  const activeSignals = signals.filter((signal) => signal.count > 0);

  return (
    <section className="panel insight-panel">
      <PanelHeader title={`${text.customerSingular} intent inbox`} detail={`${number(activeSignals.length)} active groups`} />
      {activeSignals.length ? (
        <div className="intent-inbox-grid">
          {activeSignals.map((signal) => (
            <article className={`intent-card intent-${signal.key}`} key={signal.key}>
              <div>
                <span>{signal.detail}</span>
                <strong>{signal.label}</strong>
              </div>
              <p>{signal.action}</p>
              {signal.sample ? <small>"{signal.sample}"</small> : null}
            </article>
          ))}
        </div>
      ) : (
        <EmptyState title="No intent clusters yet" message={`Intent groups will appear when ${text.customerSingular} questions contain enough signal.`} compact />
      )}
    </section>
  );
}

export function CatalogOpportunityMap({
  client,
  topProducts,
}: {
  client: ClientSummary;
  topProducts: RankRow[];
}) {
  const text = panelText(client);
  return (
    <section className="panel insight-panel">
      <PanelHeader title={text.opportunityTitle} detail="demand to action" />
      <InsightList items={buildCatalogOpportunities(client, topProducts)} />
    </section>
  );
}

export function StoreQuestionSimulator({
  client,
  analytics,
  sessions,
}: {
  client: ClientSummary;
  analytics: Analytics;
  sessions: ConversationPreview[];
}) {
  const text = panelText(client);
  const [question, setQuestion] = useState('');
  const [submittedQuestion, setSubmittedQuestion] = useState('');
  const result = simulateQuestion(submittedQuestion, analytics, sessions, client);

  function submit(event: FormEvent<HTMLFormElement>): void {
    event.preventDefault();
    setSubmittedQuestion(question);
  }

  return (
    <section className="panel simulator-panel">
      <PanelHeader title={text.simulatorTitle} detail="signal preview" />
      <form className="simulator-form" onSubmit={submit}>
        <label className="field">
          <span>{text.simulatorLabel}</span>
          <input
            value={question}
            onChange={(event) => setQuestion(event.currentTarget.value)}
            placeholder={text.simulatorPlaceholder}
          />
        </label>
        <button className="btn btn-secondary" type="submit">Preview handling</button>
      </form>
      <InsightList items={result} compact />
      <p className="muted simulator-note">This preview uses dashboard signals. A live assistant test endpoint can replace it later.</p>
    </section>
  );
}

export function TokenForecast({
  client,
  analytics,
}: {
  client: ClientSummary;
  analytics: Analytics;
}) {
  const daysLeft = tokenDaysLeft(client, analytics);
  const fullSessions = fullSessionsRemaining(client);
  const runway = Number.isFinite(daysLeft) && daysLeft > 0 ? `${Math.ceil(daysLeft)} days` : 'not enough usage';

  return (
    <section className="panel insight-panel">
      <PanelHeader title="Token forecast" detail="current pace" />
      <div className="forecast-grid">
        <div className="forecast-card">
          <span>Quota runway</span>
          <strong>{runway}</strong>
          <small>Based on the selected range.</small>
        </div>
        <div className="forecast-card">
          <span>Full sessions left</span>
          <strong>{number(fullSessions)}</strong>
          <small>At the current per-session cap.</small>
        </div>
      </div>
    </section>
  );
}

function InsightList({ items, compact = false }: { items: BriefItem[]; compact?: boolean }) {
  return (
    <div className={`insight-list ${compact ? 'compact' : ''}`}>
      {items.map((item) => (
        <article className={`insight-item insight-${item.tone}`} key={`${item.title}-${item.meta}`}>
          <div className="insight-marker" aria-hidden="true" />
          <div>
            <span>{item.meta}</span>
            <strong>{item.title}</strong>
            <p>{item.detail}</p>
          </div>
        </article>
      ))}
    </div>
  );
}
