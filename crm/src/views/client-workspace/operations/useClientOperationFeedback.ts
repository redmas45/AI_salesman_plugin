import { useCallback, useEffect, useRef, useState } from 'react';
import type { Dispatch, SetStateAction } from 'react';
import { crmApi } from '../../../api';
import type { OperationStatusResponse } from '../../../types';
import type { ClientWorkspaceTabId } from '../../../verticals/types';
import {
  CRAWL_OPERATION_STAGES,
  INTEGRATION_OPERATION_STAGES,
  normalizeTimelineStatus,
  operationBelongsToFeedback,
  operationLabel,
  operationMinimumRemainingMs,
  operationResultTab,
  operationStages,
  operationStepInterval,
  timestampMs,
  type OperationFeedbackState,
} from './OperationFeedback';

interface UseClientOperationFeedbackParams {
  autoIntegrating: boolean;
  crawling: boolean;
  reportRefreshKey: number | string;
  setActiveTab: Dispatch<SetStateAction<ClientWorkspaceTabId>>;
  siteId: string;
}

export function useClientOperationFeedback({
  autoIntegrating,
  crawling,
  reportRefreshKey,
  setActiveTab,
  siteId,
}: UseClientOperationFeedbackParams) {
  const [operationFeedback, setOperationFeedback] = useState<OperationFeedbackState | null>(null);
  const [operationStatus, setOperationStatus] = useState<OperationStatusResponse | null>(null);
  const operationFeedbackAnchorRef = useRef<HTMLDivElement | null>(null);
  const feedbackKind = operationFeedback?.kind;
  const feedbackStatus = operationFeedback?.status;
  const feedbackStartedAt = operationFeedback?.startedAt;

  const refreshOperationStatus = useCallback(async () => {
    try {
      setOperationStatus(await crmApi.getOperationStatus(siteId));
    } catch {
      setOperationStatus(null);
    }
  }, [siteId]);

  useEffect(() => {
    if (!feedbackKind || feedbackStatus !== 'running') return undefined;
    const timer = window.setInterval(() => {
      setOperationFeedback((current) => {
        if (!current || current.status !== 'running') return current;
        const stages = operationStages(current.kind);
        const nextIndex = Math.min(current.stageIndex + 1, stages.length - 1);
        return {
          ...current,
          stageIndex: nextIndex,
          message: stages[nextIndex] ?? current.message,
        };
      });
    }, operationStepInterval(feedbackKind));
    return () => window.clearInterval(timer);
  }, [feedbackKind, feedbackStatus]);

  useEffect(() => {
    if (!feedbackKind || feedbackStartedAt === undefined) return undefined;
    const timer = window.setTimeout(() => {
      operationFeedbackAnchorRef.current?.scrollIntoView({ block: 'start', behavior: 'smooth' });
    }, 80);
    return () => window.clearTimeout(timer);
  }, [feedbackKind, feedbackStartedAt]);

  useEffect(() => {
    void refreshOperationStatus();
  }, [refreshOperationStatus, reportRefreshKey]);

  useEffect(() => {
    if (!feedbackKind || feedbackStatus !== 'running') return undefined;
    const timer = window.setInterval(() => {
      void refreshOperationStatus();
    }, 2500);
    void refreshOperationStatus();
    return () => window.clearInterval(timer);
  }, [feedbackKind, feedbackStatus, refreshOperationStatus]);

  useEffect(() => {
    if (!operationStatus) return undefined;
    let completionTimer: number | undefined;
    if (operationFeedback?.status === 'running') {
      const current = operationStatus.operations[operationFeedback.kind];
      const status = normalizeTimelineStatus(current?.status);
      if ((status === 'complete' || status === 'failed') && operationBelongsToFeedback(current, operationFeedback)) {
        const nextStatus = status === 'complete' ? 'complete' : 'failed';
        const applyCompletion = () => {
          if (nextStatus === 'complete') setActiveTab(operationResultTab(operationFeedback.kind));
          setOperationFeedback((existing) => {
            if (!existing || existing.status !== 'running' || existing.kind !== operationFeedback.kind) return existing;
            return {
              ...existing,
              status: nextStatus,
              stageIndex: Math.max(0, (current?.stages.length ?? operationStages(existing.kind).length) - 1),
              message: current?.message || existing.message,
            };
          });
        };
        const holdMs = nextStatus === 'complete' ? operationMinimumRemainingMs(operationFeedback) : 0;
        if (holdMs > 0) {
          completionTimer = window.setTimeout(applyCompletion, holdMs);
        } else {
          applyCompletion();
        }
      }
      return () => {
        if (completionTimer) window.clearTimeout(completionTimer);
      };
    }
    if (operationFeedback) return;
    const runningKind = (['integration', 'crawl', 'readiness'] as const)
      .find((kind) => normalizeTimelineStatus(operationStatus.operations[kind]?.status) === 'running');
    if (!runningKind) return;
    const runningOperation = operationStatus.operations[runningKind];
    const runningStageIndex = Math.max(0, runningOperation.stages.findIndex((stage) => normalizeTimelineStatus(stage.status) === 'running'));
    setOperationFeedback({
      kind: runningKind,
      status: 'running',
      stageIndex: runningStageIndex,
      startedAt: timestampMs(runningOperation.started_at) || Date.now(),
      message: runningOperation.message || operationLabel(runningKind),
    });
    return undefined;
  }, [operationFeedback, operationStatus, setActiveTab]);

  useEffect(() => {
    if (autoIntegrating) {
      setOperationFeedback((current) => current ?? {
        kind: 'integration',
        status: 'running',
        stageIndex: 0,
        startedAt: Date.now(),
        message: 'Setup run is queued.',
      });
      return undefined;
    }
    if (feedbackKind !== 'integration' || feedbackStatus !== 'running' || feedbackStartedAt === undefined) return undefined;
    const completeIntegration = () => {
      setActiveTab('integration');
      setOperationFeedback((current) => {
        if (!current || current.kind !== 'integration' || current.status !== 'running') return current;
        return {
          ...current,
          status: 'complete',
          stageIndex: INTEGRATION_OPERATION_STAGES.length - 1,
          message: 'Setup evidence refreshed.',
        };
      });
    };
    const holdMs = operationMinimumRemainingMs({ kind: feedbackKind, startedAt: feedbackStartedAt });
    if (holdMs > 0) {
      const timer = window.setTimeout(completeIntegration, holdMs);
      return () => window.clearTimeout(timer);
    }
    completeIntegration();
    return undefined;
  }, [autoIntegrating, feedbackKind, feedbackStartedAt, feedbackStatus, setActiveTab]);

  useEffect(() => {
    if (crawling) {
      setOperationFeedback((current) => current ?? {
        kind: 'crawl',
        status: 'running',
        stageIndex: 0,
        startedAt: Date.now(),
        message: 'Crawl job is queued.',
      });
      return undefined;
    }
    if (feedbackKind !== 'crawl' || feedbackStatus !== 'running' || feedbackStartedAt === undefined) return undefined;
    const completeCrawl = () => {
      setActiveTab('crawl');
      setOperationFeedback((current) => {
        if (!current || current.kind !== 'crawl' || current.status !== 'running') return current;
        return {
          ...current,
          status: 'complete',
          stageIndex: CRAWL_OPERATION_STAGES.length - 1,
          message: 'Crawl report refreshed.',
        };
      });
    };
    const holdMs = operationMinimumRemainingMs({ kind: feedbackKind, startedAt: feedbackStartedAt });
    if (holdMs > 0) {
      const timer = window.setTimeout(completeCrawl, holdMs);
      return () => window.clearTimeout(timer);
    }
    completeCrawl();
    return undefined;
  }, [crawling, feedbackKind, feedbackStartedAt, feedbackStatus, setActiveTab]);

  return {
    operationFeedback,
    operationFeedbackAnchorRef,
    operationStatus,
    refreshOperationStatus,
    setOperationFeedback,
  };
}
