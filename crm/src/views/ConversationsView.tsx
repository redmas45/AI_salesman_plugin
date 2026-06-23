import { useState, useMemo, useEffect } from 'react';
import { ChevronDown } from 'lucide-react';
import type { ConversationsResponse } from '../types';
import { Button } from '../components/ui/Button';
import { EmptyState } from '../components/ui/EmptyState';
import { StatusPill } from '../components/ui/Badge';
import { RangeControl } from '../components/shared/RangeControl';
import { number, shortTime } from '../utils/format';

export interface ConversationsViewProps {
  conversations: ConversationsResponse | null;
  range: string;
  onRangeChange: (range: string) => void;
}

export function ConversationsView({
  conversations,
  range,
  onRangeChange,
}: ConversationsViewProps) {
  const [query, setQuery] = useState('');
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
    if (!search) return sessions;
    return sessions.filter((session) => {
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
  }, [query, sessions]);
  const pageCount = Math.max(1, Math.ceil(filteredSessions.length / 20));
  const pageSessions = filteredSessions.slice((page - 1) * 20, page * 20);

  useEffect(() => {
    setPage(1);
  }, [query, range]);

  useEffect(() => {
    if (page > pageCount) setPage(pageCount);
  }, [page, pageCount]);

  return (
    <div className="grid gap-4">
      <section className="section-row">
        <div>
          <h2 className="text-base font-semibold">Conversations</h2>
          <p className="mt-1 text-sm text-muted">Search and inspect shopper sessions for the selected range.</p>
        </div>
        <RangeControl value={range} onChange={onRangeChange} />
      </section>
      <div className="convo-toolbar card">
        <label className="field" style={{ minWidth: 280, flex: '1 1 320px' }}>
          <span>Search conversations</span>
          <input value={query} placeholder="Site, session, transcript, response, or intent" onChange={(event) => setQuery(event.currentTarget.value)} />
        </label>
        <span className="badge badge-muted">{number(filteredSessions.length)} sessions</span>
      </div>
      {!pageSessions.length ? (
        <EmptyState title="No conversations logged" message="Try a wider range or wait for new shopper sessions to arrive." />
      ) : (
        <div className="grid gap-4">
          {pageSessions.map((session) => (
            <CrmConversationCard key={`${session.site_id}-${session.session_id}`} session={session} />
          ))}
          <PaginationControl page={page} pageCount={pageCount} onPageChange={setPage} />
        </div>
      )}
    </div>
  );
}

function CrmConversationCard({
  session,
}: {
  session: ConversationsResponse['groups'][number]['sessions'][number] & { date: string };
}) {
  const [open, setOpen] = useState(false);
  const turns = open ? session.turns : session.turns.slice(0, 1);
  return (
    <article className="convo-card">
      <button className="convo-header" type="button" aria-expanded={open} onClick={() => setOpen((current) => !current)}>
        <div className="convo-header-copy">
          <div className="convo-title-row">
            <strong>{session.site_id}</strong>
            <code>{session.session_id}</code>
          </div>
          <span>
            {session.date} · {number(session.turn_count)} turns · {number(session.tokens_used)} tokens
          </span>
        </div>
        <span className={`convo-expand-btn ${open ? 'open' : ''}`} aria-hidden="true">
          <ChevronDown size={16} />
        </span>
      </button>
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
