import { useEffect, useState } from 'react';
import { Button } from '../../../components/ui/Button';
import { number } from '../../../utils/format';
import {
  SMOKE_TEST_OPERATION_STAGES,
  minimumSmokeTestDuration,
  type SmokeTestFeedbackState,
} from './promptSmokeModel';

export function PromptSmokeRunConsole({
  feedback,
  latestReport,
  onOpenEvidence,
}: {
  feedback: SmokeTestFeedbackState | null;
  latestReport: Record<string, unknown>;
  onOpenEvidence: () => void;
}) {
  const hasSavedEvidence = Array.isArray(latestReport.tests) && latestReport.tests.length > 0;
  const status = feedback?.status ?? 'complete';
  const nowMs = useCurrentTime(status === 'running');
  if (!feedback && !hasSavedEvidence) return null;

  const stageIndex = feedback?.stageIndex ?? SMOKE_TEST_OPERATION_STAGES.length - 1;
  const progress = status === 'complete'
    ? 100
    : status === 'failed'
    ? 100
    : Math.min(94, Math.round(((stageIndex + 1) / SMOKE_TEST_OPERATION_STAGES.length) * 100));
  const startedAt = feedback?.startedAt ? new Date(feedback.startedAt).toLocaleTimeString() : '';
  const elapsedSeconds = feedback ? Math.max(0, Math.round((nowMs - feedback.startedAt) / 1000)) : 0;
  const remainingSeconds = status === 'running'
    ? Math.max(1, Math.ceil((minimumSmokeTestDuration() - (nowMs - (feedback?.startedAt ?? nowMs))) / 1000))
    : 0;
  const total = Number(latestReport.total ?? 0);
  const passed = Number(latestReport.passed ?? 0);
  const failed = Number(latestReport.failed ?? 0);
  const reportSummary = total
    ? `${number(passed)}/${number(total)} passed${failed ? `, ${number(failed)} failed` : ''}`
    : hasSavedEvidence
    ? `${number((latestReport.tests as unknown[]).length)} saved checks`
    : 'Waiting for saved evidence';
  const title = status === 'running'
    ? 'Prompt checks running'
    : status === 'failed'
    ? 'Prompt checks need retry'
    : 'Prompt evidence ready';
  const message = feedback?.message || String(latestReport.message || reportSummary);

  return (
    <section className={`smoke-run-console ${status}`} aria-live={status === 'running' ? 'polite' : undefined}>
      <div className="smoke-run-head">
        <div>
          <span>{title}</span>
          <strong>{message}</strong>
        </div>
        <div className="smoke-run-meta">
          <span>{number(progress)}%</span>
          {startedAt ? <span>Started {startedAt}</span> : null}
          {elapsedSeconds ? <span>{number(elapsedSeconds)}s elapsed</span> : null}
          {remainingSeconds ? <span>~{number(remainingSeconds)}s left</span> : null}
          <span>{reportSummary}</span>
        </div>
      </div>
      <div className="smoke-run-progress" aria-label={`${progress}% complete`}>
        <span style={{ width: `${progress}%` }} />
      </div>
      <ol className="smoke-run-stages" aria-label="Prompt smoke check stages">
        {SMOKE_TEST_OPERATION_STAGES.map((stage, index) => {
          const stageStatus = promptSmokeStageStatus(index, status, stageIndex);
          return (
            <li key={stage} className={stageStatus}>
              <span aria-hidden="true" />
              <strong>{stage}</strong>
            </li>
          );
        })}
      </ol>
      <div className="smoke-run-actions">
        <Button variant="secondary" size="sm" onClick={onOpenEvidence}>
          View prompt evidence
        </Button>
      </div>
    </section>
  );
}

function useCurrentTime(running: boolean): number {
  const [nowMs, setNowMs] = useState(() => Date.now());
  useEffect(() => {
    if (!running) return undefined;
    const timer = window.setInterval(() => setNowMs(Date.now()), 1000);
    return () => window.clearInterval(timer);
  }, [running]);
  return nowMs;
}

function promptSmokeStageStatus(index: number, status: SmokeTestFeedbackState['status'], stageIndex: number) {
  if (index < stageIndex) return 'complete';
  if (index === stageIndex) return status;
  return 'pending';
}
