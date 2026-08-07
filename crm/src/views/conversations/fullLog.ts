/**
 * One complete, safe record of a conversation.
 *
 * Support cases turn on whether Maya's speech, the products she named, the page
 * the shopper was looking at and the action that ran all agreed. Reading that
 * from separate panels is slow and easy to get wrong, so the full log assembles
 * every relevant field for a session into one structure - and, importantly,
 * computes the disagreements rather than leaving a reviewer to spot them.
 *
 * Everything here is derived from data the CRM already holds. Nothing that could
 * identify a person beyond the session, and nothing that could authenticate as
 * anyone, is copied: see `REDACTED_KEY_PATTERN`.
 */

export const FULL_LOG_SCHEMA_VERSION = '1.0.0'

/** Keys whose values are never exported, matched case-insensitively. */
export const REDACTED_KEY_PATTERN =
  /(password|passwd|secret|token|api[_-]?key|authorization|auth|cookie|session[_-]?key|credential|bearer|signature|private|env|audio|raw_audio|payload_raw|card|cvv|iban|ssn|email|phone|address)/i

const REDACTED = '[redacted]'
const MAX_STRING_LENGTH = 4000
const MAX_ARRAY_LENGTH = 200
const MAX_DEPTH = 6

export type Json = string | number | boolean | null | Json[] | { [key: string]: Json }

/**
 * Copy a value, dropping anything sensitive and bounding its size.
 *
 * Redaction is by key name rather than by value inspection, so a secret is
 * removed even when its shape looks ordinary.
 */
export function sanitize(value: unknown, depth = 0): Json {
  if (value === null || value === undefined) return null
  if (typeof value === 'number' || typeof value === 'boolean') return value
  if (typeof value === 'string') {
    return value.length > MAX_STRING_LENGTH ? `${value.slice(0, MAX_STRING_LENGTH)}...[truncated]` : value
  }
  if (depth >= MAX_DEPTH) return REDACTED
  if (Array.isArray(value)) {
    return value.slice(0, MAX_ARRAY_LENGTH).map((item) => sanitize(item, depth + 1))
  }
  if (typeof value === 'object') {
    const out: { [key: string]: Json } = {}
    for (const [key, item] of Object.entries(value as Record<string, unknown>)) {
      out[key] = REDACTED_KEY_PATTERN.test(key) ? REDACTED : sanitize(item, depth + 1)
    }
    return out
  }
  return REDACTED
}

export interface TurnLike {
  created_at?: string
  request_id?: string
  turn_id?: string
  transcript?: string
  response_text?: string
  spoken_text?: string
  intent?: string
  status?: string
  transport?: string
  confidence?: number
  answer_scope?: string
  model?: string
  provider?: string
  tokens_used?: number
  cache_status?: string
  latency_ms?: unknown
  ui_actions?: unknown
  action_events?: unknown
  retrieved_ids?: string[]
  selected_ids?: string[]
  selected_names?: string[]
  matching_total?: number
  displayed_count?: number
  requested_count?: number
  constraints?: unknown
}

export interface ActionEventLike {
  action?: string
  status?: string
  reason?: string
  stage?: string
  duration_ms?: number
  requested_url?: string
  final_url?: string
  query?: string
  result_count?: number
  requested_ids?: string[]
  rendered_ids?: string[]
  rendered_product_count?: number
  visible_requested_count?: number
  [key: string]: unknown
}

export interface Mismatch {
  kind: string
  detail: string
  [key: string]: Json
}

const COUNT_IN_TEXT = /\bI found (\d+)\b/i

/**
 * The disagreements a reviewer would otherwise have to notice by eye.
 *
 * Each one is a specific way speech, the chosen records, the page and the action
 * outcome can contradict each other - the failure mode this whole log exists to
 * make visible.
 */
export function detectMismatches(turn: TurnLike): Mismatch[] {
  const mismatches: Mismatch[] = []
  const events: ActionEventLike[] = Array.isArray(turn.action_events)
    ? (turn.action_events as ActionEventLike[])
    : []
  const spoken = String(turn.response_text || '')

  const claimed = COUNT_IN_TEXT.exec(spoken)
  const rendered = events.find((event) => typeof event.rendered_product_count === 'number')
  if (claimed && rendered && typeof rendered.rendered_product_count === 'number') {
    const claimedCount = Number(claimed[1])
    if (claimedCount !== rendered.rendered_product_count) {
      mismatches.push({
        kind: 'response_count_vs_rendered_count',
        detail: `answer claimed ${claimedCount}, page rendered ${rendered.rendered_product_count}`,
      })
    }
  }

  const selected = (turn.selected_ids || []).map(String).filter(Boolean)
  const renderedIds = events.flatMap((event) => (event.rendered_ids || []).map(String))
  if (selected.length && renderedIds.length) {
    const missing = selected.filter((id) => !renderedIds.includes(id))
    if (missing.length) {
      mismatches.push({
        kind: 'selected_ids_vs_rendered_ids',
        detail: `${missing.length} of ${selected.length} named records were not on the page`,
      })
    }
  }

  const failed = events.filter((event) => String(event.status || '') === 'failed')
  if (failed.length && !/could not|couldn't|unable|sorry|not available/i.test(spoken)) {
    mismatches.push({
      kind: 'success_claim_vs_failed_action',
      detail: `${failed.length} action(s) failed (${failed
        .map((event) => `${event.action}:${event.reason || 'unknown'}`)
        .join(', ')}) but the answer did not say so`,
    })
  }

  const emptied = events.find((event) => event.result_count === 0)
  if (emptied && /\bI found\b/i.test(spoken)) {
    mismatches.push({
      kind: 'spoken_text_vs_visible_result',
      detail: `answer claimed results while the page showed none for "${emptied.query || ''}"`,
    })
  }
  return mismatches
}

export interface SessionLike {
  session_id?: string
  site_id?: string
  date?: string
  turn_count?: number
  tokens_used?: number
  turns?: readonly TurnLike[]
  runtime_events?: unknown[]
}

/** Assemble the exportable record for one session. */
export function buildFullLog(session: SessionLike, exportedAt: string): Json {
  const turns = session.turns || []
  const loggedTurns = turns.map((turn) => ({
    request_id: turn.request_id || turn.turn_id || null,
    occurred_at: turn.created_at || null,
    transport: turn.transport || null,
    user_transcript: sanitize(turn.transcript ?? null),
    assistant_response: sanitize(turn.response_text ?? null),
    spoken_text: sanitize(turn.spoken_text ?? null),
    intent: turn.intent || null,
    status: turn.status || null,
    confidence: turn.confidence ?? null,
    answer_scope: turn.answer_scope || null,
    usage: sanitize({
      model: turn.model ?? null,
      provider: turn.provider ?? null,
      tokens_used: turn.tokens_used ?? null,
      cache_status: turn.cache_status ?? null,
      latency_ms: turn.latency_ms ?? null,
    }),
    resolution: sanitize({
      constraints: turn.constraints ?? null,
      requested_count: turn.requested_count ?? null,
      matching_total: turn.matching_total ?? null,
      displayed_count: turn.displayed_count ?? null,
      retrieved_ids: turn.retrieved_ids ?? null,
      selected_ids: turn.selected_ids ?? null,
      selected_names: turn.selected_names ?? null,
    }),
    planned_actions: sanitize(turn.ui_actions ?? []),
    browser_action_events: sanitize(turn.action_events ?? []),
    mismatches: detectMismatches(turn),
  }))

  return {
    schema_version: FULL_LOG_SCHEMA_VERSION,
    exported_at: exportedAt,
    session: {
      session_id: session.session_id || null,
      site_id: session.site_id || null,
      date: session.date || null,
      turn_count: session.turn_count ?? turns.length,
      tokens_used: session.tokens_used ?? null,
      first_turn_at: turns[0]?.created_at || null,
      last_turn_at: turns[turns.length - 1]?.created_at || null,
    },
    turns: loggedTurns,
    runtime_events: sanitize(session.runtime_events ?? []),
    mismatch_summary: loggedTurns.flatMap((turn) =>
      turn.mismatches.map((mismatch) => ({ request_id: turn.request_id, ...mismatch })),
    ),
  }
}

export function fullLogFilename(session: SessionLike): string {
  const id = String(session.session_id || 'session').replace(/[^a-zA-Z0-9_-]/g, '')
  return `conversation-${id || 'session'}-full-log.json`
}
