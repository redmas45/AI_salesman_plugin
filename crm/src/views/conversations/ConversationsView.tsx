import { useState, useMemo, useEffect, useRef } from 'react';
import { Check, ChevronDown, Copy, FileText, Search, X } from 'lucide-react';
import type { ActionExecutionEvent, ConversationsResponse } from '../../types';
import { Button, IconButton } from '../../components/ui/Button';
import { EmptyState } from '../../components/ui/EmptyState';
import { StatusPill } from '../../components/ui/Badge';
import { RangeControl } from '../../components/shared/RangeControl';
import { PaginationControl } from '../../components/shared/controls/PaginationControl';
import { number, shortTime } from '../../utils/format';
import { RuntimeDiagnosticsTimeline } from './RuntimeDiagnostics';
import { FullLogPanel } from './FullLogPanel';

const CONVERSATION_PAGE_SIZE = 6;

export interface ConversationsViewProps {
  conversations: ConversationsResponse | null;
  range: string;
  onRangeChange: (range: string) => void;
}

type ConversationReviewFilter = 'all' | 'needs_review' | 'healthy';

export function ConversationsView({
  conversations,
  range,
  onRangeChange,
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
        ...(session.runtime_events ?? []).flatMap((event) => [event.source, event.component, event.stage, event.event_type, event.message_code, event.request_id]),
      ]
        .join(' ')
        .toLowerCase();
      return haystack.includes(search);
    });
  }, [query, reviewFilter, sessions]);
  const pageCount = Math.max(1, Math.ceil(filteredSessions.length / CONVERSATION_PAGE_SIZE));
  const pageSessions = filteredSessions.slice(
    (page - 1) * CONVERSATION_PAGE_SIZE,
    page * CONVERSATION_PAGE_SIZE,
  );

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
            <CrmConversationCard key={`${session.site_id}-${session.session_id}`} session={session} />
          ))}
          <PaginationControl
            page={page}
            pageCount={pageCount}
            pageSize={CONVERSATION_PAGE_SIZE}
            totalItems={filteredSessions.length}
            itemLabel="sessions"
            onPageChange={setPage}
          />
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

type CopyState = 'idle' | 'copied' | 'error';
type ConversationSession = ConversationsResponse['groups'][number]['sessions'][number] & { date: string };

const COPY_FEEDBACK_MS = 2000;

async function writeClipboardText(text: string): Promise<void> {
  if (navigator.clipboard?.writeText) {
    await navigator.clipboard.writeText(text);
    return;
  }

  const textarea = document.createElement('textarea');
  textarea.value = text;
  textarea.setAttribute('readonly', '');
  textarea.style.position = 'fixed';
  textarea.style.opacity = '0';
  document.body.appendChild(textarea);
  textarea.select();
  try {
    if (!document.execCommand('copy')) throw new Error('Clipboard copy was rejected');
  } finally {
    textarea.remove();
  }
}

function useClipboard(): { state: CopyState; copy: (text: string) => void } {
  const [state, setState] = useState<CopyState>('idle');
  const resetTimer = useRef<number | null>(null);

  useEffect(
    () => () => {
      if (resetTimer.current !== null) window.clearTimeout(resetTimer.current);
    },
    [],
  );

  const copy = (text: string) => {
    void writeClipboardText(text)
      .then(() => setState('copied'))
      .catch(() => setState('error'))
      .finally(() => {
        if (resetTimer.current !== null) window.clearTimeout(resetTimer.current);
        resetTimer.current = window.setTimeout(() => setState('idle'), COPY_FEEDBACK_MS);
      });
  };
  return { state, copy };
}

function CopyTurnButton({ text, label }: { text: string; label: string }) {
  const { state, copy } = useClipboard();
  const accessibleLabel =
    state === 'copied' ? `${label} copied` : state === 'error' ? `Copying ${label.toLowerCase()} failed` : `Copy ${label.toLowerCase()}`;
  return (
    <>
      <IconButton
        icon={state === 'copied' ? Check : Copy}
        label={accessibleLabel}
        tone={state === 'error' ? 'danger' : 'default'}
        onClick={() => copy(text)}
      />
      <span className="sr-only" aria-live="polite">{state === 'copied' ? `${label} copied` : state === 'error' ? `Copying ${label.toLowerCase()} failed` : ''}</span>
    </>
  );
}

function formatConversationForCopy(session: ConversationSession): string {
  const header = `Conversation ${session.session_id} (${session.site_id}, ${session.date})`;
  const body = session.turns
    .map((turn) => `User: ${turn.transcript || '-'}\nMaya: ${turn.response_text || '-'}`)
    .join('\n\n');
  return `${header}\n\n${body}`;
}


function CopyConversationButton({ session }: { session: ConversationSession }) {
  const { state, copy } = useClipboard();
  const label = state === 'copied' ? 'Copied' : state === 'error' ? 'Copy failed' : 'Copy conversation';
  return (
    <>
      <Button
        variant="secondary"
        size="sm"
        type="button"
        icon={state === 'copied' ? Check : Copy}
        aria-label={state === 'copied' ? 'Conversation copied' : state === 'error' ? 'Copying conversation failed' : 'Copy the whole conversation to the clipboard'}
        onClick={() => copy(formatConversationForCopy(session))}
      >
        {label}
      </Button>
      <span className="sr-only" aria-live="polite">{state === 'copied' ? 'Conversation copied' : state === 'error' ? 'Copying conversation failed' : ''}</span>
    </>
  );
}

function CrmConversationCard({ session }: { session: ConversationSession }) {
  const [open, setOpen] = useState(false);
  const [fullLogOpen, setFullLogOpen] = useState(false);
  const turns = open ? session.turns : session.turns.slice(0, 1);
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
      {/* Exactly two controls: copy the conversation, or open the full record.
          Diagnostics, JSON export and client activity moved into the full log,
          which is where someone investigating a session actually needs them. */}
      <div className="convo-card-actions">
        <CopyConversationButton session={session} />
        <Button
          variant="secondary"
          size="sm"
          type="button"
          icon={FileText}
          aria-haspopup="dialog"
          aria-expanded={fullLogOpen}
          onClick={() => setFullLogOpen(true)}
        >
          Full log
        </Button>
      </div>
      <FullLogPanel session={session} open={fullLogOpen} onClose={() => setFullLogOpen(false)} />
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
                  <CopyTurnButton text={turn.transcript || ''} label="Customer message" />
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
                  <CopyTurnButton text={turn.response_text || ''} label="Maya reply" />
                </div>
              </div>
            </div>
            {turn.action_events?.length ? <TurnActionEvidence events={turn.action_events} /> : null}
          </div>
        ))}
        {session.turns.length > 1 ? (
          <Button variant="ghost" size="sm" type="button" onClick={() => setOpen((current) => !current)}>
            {open ? 'Show less' : `Show ${session.turns.length - 1} more turns`}
          </Button>
        ) : null}
        {open && session.runtime_events?.length ? <RuntimeDiagnosticsTimeline events={session.runtime_events} /> : null}
      </div>
    </article>
  );
}

function TurnActionEvidence({ events }: { events: ActionExecutionEvent[] }) {
  return (
    <div className="turn-action-evidence" aria-label="Browser action evidence">
      {events.map((event, index) => (
        <div key={`${event.request_id || event.action}-${event.occurred_at}-${index}`} className={`turn-action-event ${actionEventTone(event.status)}`}>
          <div className="turn-action-event-head">
            <strong>{event.action || 'ACTION'}</strong>
            <StatusPill value={actionStatusLabel(event.status)} />
            {event.url_changed ? <span>URL changed</span> : null}
          </div>
          <div className="turn-action-event-meta">
            <span>{event.stage || 'browser'}</span>
            {event.duration_ms ? <span>{number(event.duration_ms)} ms</span> : null}
            {event.request_id ? <code>{event.request_id}</code> : null}
          </div>
          <small>{actionEventDestination(event)}</small>
          {event.reason ? <small>{event.reason}</small> : null}
        </div>
      ))}
    </div>
  );
}

function actionStatusLabel(status: string) {
  const normalized = String(status || '').toLowerCase();
  if (normalized === 'succeeded' || normalized === 'ok') return 'succeeded';
  if (normalized === 'requested' || normalized === 'executing') return normalized;
  if (normalized === 'needs_handoff') return 'handoff';
  if (normalized === 'blocked') return 'blocked';
  if (normalized === 'failed' || normalized === 'error') return 'failed';
  return normalized || 'unknown';
}

function actionEventTone(status: string) {
  const normalized = String(status || '').toLowerCase();
  if (normalized === 'succeeded' || normalized === 'ok') return 'ok';
  if (normalized === 'failed' || normalized === 'error' || normalized === 'blocked') return 'bad';
  if (normalized === 'requested' || normalized === 'executing' || normalized === 'needs_handoff') return 'warn';
  return 'idle';
}

function actionEventDestination(event: ActionExecutionEvent) {
  const finalUrl = event.final_url || '';
  if (!finalUrl) return 'No final URL reported';
  try {
    const url = new URL(finalUrl);
    return `Final URL: ${url.pathname}${url.search}${url.hash}`;
  } catch {
    return `Final URL: ${finalUrl}`;
  }
}

function sessionNeedsReview(session: ConversationsResponse['groups'][number]['sessions'][number]) {
  return session.turns.some((turn) => turnIsError(turn) || turnIsSlow(turn))
    || (session.runtime_events ?? []).some((event) => event.severity === 'error' || event.status === 'failed');
}

function turnIsError(turn: ConversationsResponse['groups'][number]['sessions'][number]['turns'][number]) {
  const status = String(turn.status || 'ok').toLowerCase();
  return ['error', 'failed', 'failure', 'timeout', 'blocked'].some((token) => status.includes(token));
}

function turnIsSlow(turn: ConversationsResponse['groups'][number]['sessions'][number]['turns'][number]) {
  return Number(turn.latency_ms || 0) >= 3000;
}
