import { useCallback, useEffect, useMemo, useRef } from 'react'
import { Download, X } from 'lucide-react'
import { Button } from '../../components/ui/Button'
import { buildFullLog, fullLogFilename, type SessionLike } from './fullLog'

/**
 * The complete record of one conversation, in a restrained drawer.
 *
 * Kept out of ConversationsView because that file is already at its size budget,
 * and because the export logic is worth testing on its own. Download lives here
 * rather than in the card toolbar so the toolbar stays two controls wide.
 */
export function FullLogPanel({
  session,
  open,
  onClose,
}: {
  session: SessionLike
  open: boolean
  onClose: () => void
}) {
  const closeRef = useRef<HTMLButtonElement>(null)
  const previouslyFocused = useRef<Element | null>(null)

  const log = useMemo(
    () => (open ? buildFullLog(session, new Date().toISOString()) : null),
    [session, open],
  )

  useEffect(() => {
    if (!open) return
    previouslyFocused.current = document.activeElement
    closeRef.current?.focus()
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') onClose()
    }
    document.addEventListener('keydown', onKeyDown)
    return () => {
      document.removeEventListener('keydown', onKeyDown)
      // Send focus back where it came from, so keyboard users are not stranded.
      ;(previouslyFocused.current as HTMLElement | null)?.focus?.()
    }
  }, [open, onClose])

  const download = useCallback(() => {
    if (!log) return
    const blob = new Blob([JSON.stringify(log, null, 2)], { type: 'application/json' })
    const url = URL.createObjectURL(blob)
    const anchor = document.createElement('a')
    anchor.href = url
    anchor.download = fullLogFilename(session)
    anchor.click()
    URL.revokeObjectURL(url)
  }, [log, session])

  if (!open || !log) return null

  const mismatches = (log as { mismatch_summary?: { kind: string; detail: string }[] }).mismatch_summary || []

  return (
    <div className="full-log-backdrop" role="presentation" onClick={onClose}>
      <aside
        className="full-log-panel"
        role="dialog"
        aria-modal="true"
        aria-label={`Full log for session ${session.session_id || ''}`}
        onClick={(event) => event.stopPropagation()}
      >
        <header className="full-log-header">
          <div>
            <span className="full-log-kicker">Full log</span>
            <strong>{session.session_id}</strong>
          </div>
          <div className="full-log-header-actions">
            <Button variant="secondary" size="sm" type="button" icon={Download} onClick={download}>
              Download JSON
            </Button>
            <button
              ref={closeRef}
              type="button"
              className="full-log-close"
              aria-label="Close full log"
              onClick={onClose}
            >
              <X size={16} />
            </button>
          </div>
        </header>

        {mismatches.length ? (
          <div className="full-log-mismatches" role="status">
            <strong>{mismatches.length} disagreement(s) detected</strong>
            <ul>
              {mismatches.map((mismatch, index) => (
                <li key={`${mismatch.kind}-${index}`}>
                  <code>{mismatch.kind}</code> - {mismatch.detail}
                </li>
              ))}
            </ul>
          </div>
        ) : null}

        <pre className="full-log-body" tabIndex={0}>
          {JSON.stringify(log, null, 2)}
        </pre>
      </aside>
    </div>
  )
}
