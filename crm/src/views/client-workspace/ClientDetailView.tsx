import { useState, useEffect, useMemo, useCallback, useRef } from 'react';
import { crmApi } from '../../api';
import type {
  View,
  ClientBoardSection,
  Client,
  UsageEvent,
} from '../../types';
import { NoticeBanner } from '../../components/shared/NoticeBanner';
import { getCrmVertical } from '../../verticals/registry';
import { clientWorkspaceTabs } from '../../verticals/workspace';
import type { ClientWorkspaceTabId } from '../../verticals/types';
import { ClientWorkspaceTabPanel } from './tabs/ClientWorkspaceTabPanel';
import { useClientCatalogProducts, useClientReports } from './hooks/useClientWorkspaceData';
import { SMOKE_TEST_OPERATION_STAGES, minimumSmokeTestDuration, type SmokeTestFeedbackState } from './operations/promptSmokeModel';
import {
  CRAWL_OPERATION_STAGES,
  INTEGRATION_OPERATION_STAGES,
  OperationFeedbackPanel,
  normalizeTimelineStatus,
} from './operations/OperationFeedback';
import { ClientOperatorCenter } from './operator/OperatorCenter';
import { useClientOperationFeedback } from './operations/useClientOperationFeedback';

export interface ClientDetailViewProps {
  client: Client;
  initialTab: ClientWorkspaceTabId;
  clientTabRequestKey: number;
  recentActivity: UsageEvent[];
  crawlingSites: Set<string>;
  autoIntegratingSites: Set<string>;
  onActivateClient: (siteId: string) => void;
  onTriggerCrawl: (siteId: string) => void;
  onAutoIntegrate: (siteId: string) => void;
  onRemoveClient: (siteId: string) => void;
  onMoveClientToAvailable: (siteId: string) => void;
  onToggleClient: (siteId: string, enabled: boolean) => void;
  onUpdateTokenLimits: (siteId: string, tokenLimit: number, sessionTokenLimit: number) => Promise<void>;
  onOpenPasswordDialog: (client: Client) => void;
  onViewChange: (view: View) => void;
  onOpenClientBoardSection: (section: ClientBoardSection) => void;
  onWorkspaceTabChange: (tabId: ClientWorkspaceTabId) => void;
}

export function ClientDetailView({
  client,
  initialTab,
  clientTabRequestKey,
  recentActivity,
  crawlingSites,
  autoIntegratingSites,
  onActivateClient,
  onTriggerCrawl,
  onAutoIntegrate,
  onRemoveClient,
  onMoveClientToAvailable,
  onToggleClient,
  onUpdateTokenLimits,
  onOpenPasswordDialog,
  onViewChange,
  onOpenClientBoardSection,
  onWorkspaceTabChange,
}: ClientDetailViewProps) {
  const vertical = getCrmVertical(client.vertical_key);
  const workspaceTabs = useMemo(() => clientWorkspaceTabs(client), [client]);
  const [activeTab, setActiveTab] = useState<ClientWorkspaceTabId>('overview');
  const { capabilities, scanReport, crawlReport, reportError, setReportError, reportRefreshKey } = useClientReports(client);
  const { catalogError, catalogLoading, displayedProducts } = useClientCatalogProducts(client);
  const [smokeTesting, setSmokeTesting] = useState(false);
  const [smokeTestFeedback, setSmokeTestFeedback] = useState<SmokeTestFeedbackState | null>(null);
  const [standaloneSmokeReport, setStandaloneSmokeReport] = useState<Record<string, unknown> | null>(null);
  const clientTabPanelRef = useRef<HTMLElement | null>(null);
  const crawling = crawlingSites.has(client.site_id);
  const autoIntegrating = autoIntegratingSites.has(client.site_id);
  const {
    operationFeedback,
    operationFeedbackAnchorRef,
    operationStatus,
    refreshOperationStatus,
    setOperationFeedback,
  } = useClientOperationFeedback({
    autoIntegrating,
    crawling,
    reportRefreshKey,
    setActiveTab,
    siteId: client.site_id,
  });
  const setupOrReadinessRunning =
    autoIntegrating
    || normalizeTimelineStatus(operationStatus?.operations.integration?.status) === 'running'
    || normalizeTimelineStatus(operationStatus?.operations.readiness?.status) === 'running';
  const automationLocked = client.status === 'available';
  const sourceStatus = clientRuntimeStatus(client);
  const sourceReachable = sourceStatus === 'online';
  const activeTabDefinition = workspaceTabs.find((tab) => tab.id === activeTab) ?? workspaceTabs[0]!;

  const openWorkspaceTab = useCallback((tabId: ClientWorkspaceTabId) => {
    const shouldScroll = tabId !== activeTab;
    setActiveTab(tabId);
    if (shouldScroll) {
      window.setTimeout(() => {
        clientTabPanelRef.current?.scrollIntoView({ block: 'start', behavior: 'smooth' });
      }, 40);
    }
  }, [activeTab]);

  useEffect(() => {
    if (!workspaceTabs.some((tab) => tab.id === activeTab)) {
      setActiveTab(workspaceTabs[0]?.id ?? 'overview');
    }
  }, [activeTab, workspaceTabs]);

  useEffect(() => {
    if (workspaceTabs.some((tab) => tab.id === initialTab)) {
      setActiveTab(initialTab);
    }
  }, [client.site_id, initialTab, workspaceTabs]);

  useEffect(() => {
    if (!clientTabRequestKey || !workspaceTabs.some((tab) => tab.id === initialTab)) return;
    setActiveTab(initialTab);
    const timer = window.setTimeout(() => {
      clientTabPanelRef.current?.scrollIntoView({ block: 'start', behavior: 'smooth' });
    }, 40);
    return () => window.clearTimeout(timer);
  }, [clientTabRequestKey, initialTab, workspaceTabs]);

  useEffect(() => {
    setStandaloneSmokeReport(null);
    setSmokeTestFeedback(null);
  }, [client.site_id]);

  useEffect(() => {
    onWorkspaceTabChange(activeTab);
  }, [activeTab, onWorkspaceTabChange]);

  const smokeTestStatus = smokeTestFeedback?.status;
  useEffect(() => {
    if (smokeTestStatus !== 'running') return undefined;
    const timer = window.setInterval(() => {
      setSmokeTestFeedback((current) => {
        if (!current || current.status !== 'running') return current;
        const nextIndex = Math.min(current.stageIndex + 1, SMOKE_TEST_OPERATION_STAGES.length - 1);
        return {
          ...current,
          stageIndex: nextIndex,
          message: SMOKE_TEST_OPERATION_STAGES[nextIndex] ?? current.message,
        };
      });
    }, 900);
    return () => window.clearInterval(timer);
  }, [smokeTestStatus]);

  function blockIfSourceUnavailable(actionLabel: string) {
    if (automationLocked) {
      setReportError('Move this install to Current before running website operations.');
      return true;
    }
    if (sourceReachable) return false;
    setReportError(`Cannot ${actionLabel} because the source website is ${sourceStatus}. Start the website, refresh AI Hub, then try again. Owner panel remains available because AI Hub hosts it.`);
    return true;
  }

  async function handleRunAssistantSmokeTests() {
    const startedAt = Date.now();
    setActiveTab('integration');
    setSmokeTesting(true);
    setReportError('');
    setSmokeTestFeedback({
      status: 'running',
      stageIndex: 0,
      startedAt,
      message: SMOKE_TEST_OPERATION_STAGES[0],
    });
    try {
      const response = await crmApi.runAssistantSmokeTests(client.site_id);
      setStandaloneSmokeReport(response.report);
      await minimumDelay(startedAt, minimumSmokeTestDuration());
      setSmokeTestFeedback({
        status: 'complete',
        stageIndex: SMOKE_TEST_OPERATION_STAGES.length - 1,
        startedAt,
        message: 'Prompt evidence saved and ready to inspect.',
      });
    } catch (error) {
      setReportError(error instanceof Error ? error.message : 'Assistant smoke tests failed.');
      setSmokeTestFeedback({
        status: 'failed',
        stageIndex: SMOKE_TEST_OPERATION_STAGES.length - 1,
        startedAt,
        message: error instanceof Error ? error.message : 'Assistant smoke tests failed.',
      });
    } finally {
      setSmokeTesting(false);
    }
  }

  function handleStartIntegration() {
    if (blockIfSourceUnavailable('run setup')) return;
    setActiveTab('integration');
    setOperationFeedback({
      kind: 'integration',
      status: 'running',
      stageIndex: 0,
      startedAt: Date.now(),
      message: INTEGRATION_OPERATION_STAGES[0],
    });
    void refreshOperationStatus();
    onAutoIntegrate(client.site_id);
  }

  async function handleCancelIntegration() {
    setReportError('');
    try {
      const response = await crmApi.cancelAutoIntegrateClient(client.site_id);
      setOperationFeedback((current) => {
        if (!current || current.kind !== 'integration' || current.status !== 'running') return current;
        return {
          ...current,
          message: response.message,
        };
      });
      await refreshOperationStatus();
    } catch (error) {
      setReportError(error instanceof Error ? error.message : 'Setup stop request failed.');
      await refreshOperationStatus();
    }
  }

  function handleStartCrawl() {
    if (blockIfSourceUnavailable('crawl source')) return;
    setActiveTab('crawl');
    setOperationFeedback({
      kind: 'crawl',
      status: 'running',
      stageIndex: 0,
      startedAt: Date.now(),
      message: CRAWL_OPERATION_STAGES[0],
    });
    void refreshOperationStatus();
    onTriggerCrawl(client.site_id);
  }

  return (
    <div className="client-detail">
      <ClientOperatorCenter
        client={client}
        vertical={vertical}
        automationLocked={automationLocked}
        sourceReachable={sourceReachable}
        sourceStatus={sourceStatus}
        scanning={setupOrReadinessRunning}
        crawling={crawling}
        autoIntegrating={autoIntegrating}
        operationFeedback={operationFeedback}
        operationStatus={operationStatus}
        onBack={() => onOpenClientBoardSection('all')}
        onActivate={() => onActivateClient(client.site_id)}
        onRunIntegration={handleStartIntegration}
        onRunCrawl={() => handleStartCrawl()}
        onRemoveClient={() => onMoveClientToAvailable(client.site_id)}
        onOpenPasswordDialog={() => onOpenPasswordDialog(client)}
        onToggleWidget={() => onToggleClient(client.site_id, client.status !== 'live')}
        onOpenControls={() => openWorkspaceTab('controls')}
        onOpenOutput={openWorkspaceTab}
      />
      {automationLocked ? (
        <NoticeBanner
          tone="info"
          message="This client is Available. Move it to Current before running setup, crawls, or widget controls."
        />
      ) : null}
      {reportError ? <NoticeBanner tone="error" message={reportError} /> : null}
      <div className="operation-feedback-anchor" ref={operationFeedbackAnchorRef}>
        <OperationFeedbackPanel
          feedback={operationFeedback}
          backendOperation={operationFeedback ? operationStatus?.operations?.[operationFeedback.kind] ?? null : null}
          onViewResult={openWorkspaceTab}
          onCancel={() => {
            void handleCancelIntegration();
          }}
          onRetry={(kind) => {
            if (kind === 'readiness') {
              handleStartIntegration();
              return;
            }
            if (kind === 'crawl') {
              handleStartCrawl();
              return;
            }
            handleStartIntegration();
          }}
          onDismiss={() => setOperationFeedback(null)}
        />
      </div>
      <ClientWorkspaceTabPanel
        activeTab={activeTab}
        activeTabDefinition={activeTabDefinition}
        automationLocked={automationLocked}
        autoIntegrating={autoIntegrating}
        capabilities={capabilities}
        catalogError={catalogError}
        catalogLoading={catalogLoading}
        client={client}
        crawlReport={crawlReport}
        crawling={crawling}
        displayedProducts={displayedProducts}
        onOpenPasswordDialog={onOpenPasswordDialog}
        onOpenTab={setActiveTab}
        onRemoveClient={onRemoveClient}
        onRunAssistantSmokeTests={handleRunAssistantSmokeTests}
        onRunSetup={handleStartIntegration}
        onToggleClient={onToggleClient}
        onTriggerCrawl={handleStartCrawl}
        onUpdateTokenLimits={onUpdateTokenLimits}
        onViewChange={onViewChange}
        operationFeedback={operationFeedback}
        operationStatus={operationStatus}
        recentActivity={recentActivity}
        scanReport={scanReport}
        setupOrReadinessRunning={setupOrReadinessRunning}
        smokeTestFeedback={smokeTestFeedback}
        smokeTesting={smokeTesting}
        sourceReachable={sourceReachable}
        sourceStatus={sourceStatus}
        standaloneSmokeReport={standaloneSmokeReport}
        tabPanelRef={clientTabPanelRef}
        vertical={vertical}
      />
    </div>
  );
}

function minimumDelay(startedAt: number, minimumMs: number) {
  const remainingMs = Math.max(0, minimumMs - (Date.now() - startedAt));
  if (!remainingMs) return Promise.resolve();
  return new Promise<void>((resolve) => window.setTimeout(resolve, remainingMs));
}

function clientRuntimeStatus(client: Client) {
  return String(client.runtime_status?.status || 'unknown').toLowerCase();
}
