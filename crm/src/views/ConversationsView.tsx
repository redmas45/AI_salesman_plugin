import { useState, useMemo, useEffect } from 'react';
import { Activity, ChevronDown, Search, X } from 'lucide-react';
import type { ConversationsResponse } from '../types';
import type { ClientWorkspaceTabId } from '../verticals/types';
import { Button } from '../components/ui/Button';
import { EmptyState } from '../components/ui/EmptyState';
import { StatusPill } from '../components/ui/Badge';
import { RangeControl } from '../components/shared/RangeControl';
import { number, shortTime } from '../utils/format';

export interface ConversationsViewProps {
  conversations: ConversationsResponse | null;
  range: string;
  onRangeChange: (range: string) => void;
  onOpenClient: (siteId: string, initialTab?: ClientWorkspaceTabId) => void;
}

type ConversationReviewFilter = 'all' | 'needs_review' | 'healthy';

export function ConversationsView({
  conversations,
  range,
  onRangeChange,
  onOpenClient,
}: ConversationsViewProps) {
  const [query, setQuery] = useState('');
  const [reviewFilter, setReviewFilter] = useState<ConversationReviewFilter>('all');
  const [page, setPage] = useState(1);
  const sessions = useMemo(
    () =>
      (conversations?.groups ?? []).flatMap((group) =>
        group.sessions.map((session) => ({
          ...session,
          date: group.date,
        })),
      ),
    [conversations],
  );
  const filteredSessions = useMemo(() => {
    const search = query.trim().toLowerCase();
    return sessions.filter((session) => {
      const needsReview = sessionNeedsReview(session);
      if (reviewFilter === 'needs_review' && !needsReview) return false;
      if (reviewFilter === 'healthy' && needsReview) return false;
      if (!search) return true;
      const haystack = [
        session.site_id,
        session.session_id,
        session.date,
        ...session.turns.flatMap((turn) => [turn.intent, turn.transcript, turn.response_text]),
      ]
        .join(' ')
        .toLowerCase();
      return haystack.includes(search);
    });
  }, [query, reviewFilter, sessions]);
  const pageCount = Math.max(1, Math.ceil(filteredSessions.length / 20));
  const pageSessions = filteredSessions.slice((page - 1) * 20, page * 20);

  useEffect(() => {
    setPage(1);
  }, [query, range]);

  useEffect(() => {
    if (page > pageCount) setPage(pageCount);
  }, [page, pageCount]);
  const totalTurns = filteredSessions.reduce((sum, session) => sum + session.turn_count, 0);
  const allTurns = sessions.reduce((sum, session) => sum + session.turn_count, 0);
  const needsReviewSessions = sessions.filter(sessionNeedsReview).length;
  const slowTurns = sessions.reduce((sum, session) => sum + session.turns.filter(turnIsSlow).length, 0);

  return (
    <div className="grid gap-4">
      <section className="section-row">
        <div>
          <h2 className="text-base font-semibold">Conversations</h2>
          <p className="mt-1 text-sm text-muted">Search and inspect visitor sessions for the selected range.</p>
        </div>
        <RangeControl value={range} onChange={onRangeChange} />
      </section>
      <ConversationInsightStrip
        totalSessions={sessions.length}
        totalTurns={allTurns}
        needsReviewSessions={needsReviewSessions}
        slowTurns={slowTurns}
        activeFilter={reviewFilter}
        onSelect={setReviewFilter}
      />
      <section className="client-board-toolbar" aria-label="Conversation filters">
        <label className="client-search">
          <Search size={15} aria-hidden="true" />
          <span className="sr-only">Search conversations</span>
          <input
            value={query}
            placeholder="Search site, session, transcript, response, or intent"
            onChange={(event) => setQuery(event.currentTarget.value)}
          />
          {query ? (
            <button type="button" aria-label="Clear conversation search" onClick={() => setQuery('')}>
              <X size={14} aria-hidden="true" />
            </button>
          ) : null}
        </label>
        <div className="client-board-counts">
          <span>{number(filteredSessions.length)} sessions</span>
          <span>{number(totalTurns)} turns</span>
          <span>{number(needsReviewSessions)} need review</span>
          <span>Page {number(page)} / {number(pageCount)}</span>
        </div>
      </section>
      {!pageSessions.length ? (
        <EmptyState title="No conversations logged" message="Try a wider range or wait for new visitor sessions to arrive." />
      ) : (
        <div className="grid gap-4">
          {pageSessions.map((session) => (
            <CrmConversationCard
              key={`${session.site_id}-${session.session_id}`}
              session={session}
              onOpenClient={onOpenClient}
            />
          ))}
          <PaginationControl page={page} pageCount={pageCount} onPageChange={setPage} />
        </div>
      )}
    </div>
  );
}

function ConversationInsightStrip({
  totalSessions,
  totalTurns,
  needsReviewSessions,
  slowTurns,
  activeFilter,
  onSelect,
}: {
  totalSessions: number;
  totalTurns: number;
  needsReviewSessions: number;
  slowTurns: number;
  activeFilter: ConversationReviewFilter;
  onSelect: (filter: ConversationReviewFilter) => void;
}) {
  return (
    <section className="conversation-insight-grid" aria-label="Conversation review filters">
      <ConversationInsightCard
        label="Sessions"
        value={totalSessions}
        detail={`${number(totalTurns)} turns in range`}
        active={activeFilter === 'all'}
        onClick={() => onSelect('all')}
      />
      <ConversationInsightCard
        label="Needs review"
        value={needsReviewSessions}
        detail="Errors or slow turns"
        tone={needsReviewSessions ? 'warn' : 'idle'}
        active={activeFilter === 'needs_review'}
        onClick={() => onSelect('needs_review')}
      />
      <ConversationInsightCard
        label="Healthy"
        value={Math.max(0, totalSessions - needsReviewSessions)}
        detail="No visible issue flags"
        active={activeFilter === 'healthy'}
        onClick={() => onSelect('healthy')}
      />
      <ConversationInsightCard
        label="Slow turns"
        value={slowTurns}
        detail="Over 3 seconds latency"
        tone={slowTurns ? 'warn' : 'idle'}
        active={activeFilter === 'needs_review' && slowTurns > 0}
        onClick={() => onSelect('needs_review')}
      />
    </section>
  );
}

function ConversationInsightCard({
  label,
  value,
  detail,
  tone = 'neutral',
  active,
  onClick,
}: {
  label: string;
  value: number;
  detail: string;
  tone?: 'neutral' | 'warn' | 'idle';
  active: boolean;
  onClick: () => void;
}) {
  return (
    <button className={`conversation-insight-card ${tone} ${active ? 'active' : ''}`} type="button" aria-pressed={active} onClick={onClick}>
      <span>{label}</span>
      <strong>{number(value)}</strong>
      <small>{detail}</small>
    </button>
  );
}

function CrmConversationCard({
  session,
  onOpenClient,
}: {
  session: ConversationsResponse['groups'][number]['sessions'][number] & { date: string };
  onOpenClient: (siteId: string, initialTab?: ClientWorkspaceTabId) => void;
}) {
  const [open, setOpen] = useState(false);
  const turns = open ? session.turns : session.turns.slice(0, 1);
  const latestTurn = session.turns[0];
  const needsReview = sessionNeedsReview(session);
  return (
    <article className={`convo-card ${needsReview ? 'needs-review' : ''}`}>
      <button className="convo-header" type="button" aria-expanded={open} onClick={() => setOpen((current) => !current)}>
        <div className="convo-header-copy">
          <div className="convo-title-row">
            <strong>{session.site_id}</strong>
            <code>{session.session_id}</code>
            {needsReview ? <StatusPill value="needs review" /> : null}
          </div>
          <span>
            {session.date} / {number(session.turn_count)} turns / {number(session.tokens_used)} tokens
          </span>
        </div>
        <span className={`convo-expand-btn ${open ? 'open' : ''}`} aria-hidden="true">
          <ChevronDown size={16} />
        </span>
      </button>
      <div className="convo-card-actions">
        <Button
          variant="secondary"
          size="sm"
          type="button"
          icon={Activity}
          onClick={() => onOpenClient(session.site_id, 'activity')}
        >
          Open client activity
        </Button>
        <span>
          Latest intent: <strong>{latestTurn?.intent || 'unknown'}</strong>
        </span>
      </div>
      <div className="convo-turns">
        {turns.map((turn, index) => (
          <div key={`${turn.created_at}-${turn.transcript}-${index}`} className="grid gap-3">
            <div className="turn-user">
              <span className="turn-avatar">U</span>
              <div className="turn-body">
                <p>{turn.transcript || '-'}</p>
                <div className="turn-meta">
                  <span>{shortTime(turn.created_at)}</span>
                  <span>{turn.transport}</span>
                  <StatusPill value={turn.status || 'ok'} />
                </div>
              </div>
            </div>
            <div className="turn-ai">
              <span className="turn-avatar">AI</span>
              <div className="turn-body">
                <p>{turn.response_text || '-'}</p>
                <div className="turn-meta">
                  <span>{turn.intent || 'unknown'}</span>
                  <span>{number(turn.tokens)} tokens</span>
                  <span>{number(turn.latency_ms)} ms</span>
                </div>
              </div>
            </div>
          </div>
        ))}
        {session.turns.length > 1 ? (
          <Button variant="ghost" size="sm" type="button" onClick={() => setOpen((current) => !current)}>
            {open ? 'Show less' : `Show ${session.turns.length - 1} more turns`}
          </Button>
        ) : null}
      </div>
    </article>
  );
}

function sessionNeedsReview(session: ConversationsResponse['groups'][number]['sessions'][number]) {
  return session.turns.some((turn) => turnIsError(turn) || turnIsSlow(turn));
}

function turnIsError(turn: ConversationsResponse['groups'][number]['sessions'][number]['turns'][number]) {
  const status = String(turn.status || 'ok').toLowerCase();
  return ['error', 'failed', 'failure', 'timeout', 'blocked'].some((token) => status.includes(token));
}

function turnIsSlow(turn: ConversationsResponse['groups'][number]['sessions'][number]['turns'][number]) {
  return Number(turn.latency_ms || 0) >= 3000;
}

function PaginationControl({
  page,
  pageCount,
  onPageChange,
}: {
  page: number;
  pageCount: number;
  onPageChange: (page: number) => void;
}) {
  return (
    <div className="pagination-control">
      <Button variant="secondary" disabled={page <= 1} onClick={() => onPageChange(page - 1)}>
        Previous
      </Button>
      <span>
        Page {page} of {pageCount}
      </span>
      <Button variant="secondary" disabled={page >= pageCount} onClick={() => onPageChange(page + 1)}>
        Next
      </Button>
    </div>
  );
}
