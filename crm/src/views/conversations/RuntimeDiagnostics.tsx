import { useEffect, useRef, useState } from 'react';
import { Check, Copy, Download } from 'lucide-react';
import type { ConversationSession, RuntimeDiagnosticEvent } from '../../types';
import { StatusPill } from '../../components/ui/Badge';
import { Button } from '../../components/ui/Button';
import { number, shortTime } from '../../utils/format';

const COPY_FEEDBACK_MS = 2000;

export function RuntimeDiagnosticActions({ session }: { session: ConversationSession }) {
  const { state, copy } = useDiagnosticClipboard();
  if (!session.runtime_events?.length) return null;
  return (
    <>
      <Button variant="secondary" size="sm" type="button" icon={state === 'copied' ? Check : Copy} onClick={() => copy(formatDiagnostics(session))}>
        {state === 'copied' ? 'Diagnostics copied' : state === 'error' ? 'Copy failed' : 'Copy diagnostics'}
      </Button>
      <Button variant="secondary" size="sm" type="button" icon={Download} onClick={() => downloadDiagnostics(session)}>
        Export JSON
      </Button>
    </>
  );
}

export function RuntimeDiagnosticsTimeline({ events }: { events: RuntimeDiagnosticEvent[] }) {
  const ordered = [...events].sort((left, right) => left.occurred_at.localeCompare(right.occurred_at));
  return (
    <section className="runtime-diagnostics" aria-label="Frontend and backend runtime diagnostics">
      <div className="runtime-diagnostics-head">
        <strong>Runtime diagnostics</strong>
        <span>{ordered.length} events</span>
      </div>
      {ordered.map((event, index) => (
        <div className={`runtime-diagnostic-event ${event.severity}`} key={`${event.occurred_at}-${event.source}-${event.event_type}-${index}`}>
          <div>
            <StatusPill value={event.source} />
            <strong>{event.event_type.replaceAll('_', ' ')}</strong>
            <span>{event.component}{event.stage ? ` / ${event.stage}` : ''}</span>
          </div>
          <div>
            <span>{shortTime(event.occurred_at)}</span>
            <StatusPill value={event.status} />
            {event.message_code ? <code>{event.message_code}</code> : null}
            {event.request_id ? <code>request {event.request_id}</code> : null}
            {event.duration_ms ? <span>{number(event.duration_ms)} ms</span> : null}
          </div>
        </div>
      ))}
    </section>
  );
}

function formatDiagnostics(session: ConversationSession): string {
  const header = `Runtime diagnostics ${session.session_id} (${session.site_id})`;
  const body = (session.runtime_events ?? []).map(formatDiagnosticLine).join('\n');
  return `${header}\n\n${body || 'No runtime diagnostics recorded.'}`;
}

function formatDiagnosticLine(event: RuntimeDiagnosticEvent): string {
  const identity = [event.source, event.component, event.stage].filter(Boolean).join('/');
  const request = event.request_id ? ` request=${event.request_id}` : '';
  const duration = event.duration_ms ? ` duration=${Math.round(event.duration_ms)}ms` : '';
  const code = event.message_code ? ` code=${event.message_code}` : '';
  return `${event.occurred_at} ${event.severity.toUpperCase()} ${identity} ${event.event_type} status=${event.status}${code}${request}${duration}`;
}

function downloadDiagnostics(session: ConversationSession): void {
  const payload = { site_id: session.site_id, session_id: session.session_id, exported_at: new Date().toISOString(), runtime_events: session.runtime_events ?? [] };
  const blob = new Blob([JSON.stringify(payload, null, 2)], { type: 'application/json' });
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = `ai-hub-diagnostics-${safeFilenamePart(session.session_id)}.json`;
  link.click();
  window.setTimeout(() => URL.revokeObjectURL(url), 0);
}

function safeFilenamePart(value: string): string {
  return String(value || 'session').replace(/[^a-z0-9_-]+/gi, '_').slice(0, 80) || 'session';
}

function useDiagnosticClipboard(): { state: 'idle' | 'copied' | 'error'; copy: (text: string) => void } {
  const [state, setState] = useState<'idle' | 'copied' | 'error'>('idle');
  const resetTimer = useRef<number | null>(null);
  useEffect(() => () => { if (resetTimer.current !== null) window.clearTimeout(resetTimer.current); }, []);
  const copy = (text: string) => {
    void writeDiagnosticClipboard(text).then(() => setState('copied')).catch(() => setState('error')).finally(() => {
      if (resetTimer.current !== null) window.clearTimeout(resetTimer.current);
      resetTimer.current = window.setTimeout(() => setState('idle'), COPY_FEEDBACK_MS);
    });
  };
  return { state, copy };
}

async function writeDiagnosticClipboard(text: string): Promise<void> {
  if (navigator.clipboard?.writeText) return navigator.clipboard.writeText(text);
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
