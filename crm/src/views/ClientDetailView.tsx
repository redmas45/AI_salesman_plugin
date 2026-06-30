/* eslint-disable react-hooks/purity */
import { useState, useEffect, useMemo, useCallback, useRef, type FormEvent, type ChangeEvent } from 'react';
import {
  ShieldCheck,
  PackageOpen,
  Gauge,
  ClipboardCheck,
  Copy,
  Settings,
  KeyRound,
  Trash2,
  Eye,
  
  AlertTriangle,
  XCircle,
  Search,
  ChevronDown,
  CheckCircle2,
  type LucideIcon,
} from 'lucide-react';
import { crmApi } from '../api';
import type {
  View,
  ClientBoardSection,
  Client,
  UsageEvent,
  CapabilitiesSummary,
  ReadinessReport,
  CrawlReport,
  OperationStatus,
  OperationStatusResponse,
  CatalogProduct,
  ProductPreview,
  SyncRun,
} from '../types';
import { Button } from '../components/ui/Button';
import { Panel } from '../components/ui/Panel';
import { StatusPill } from '../components/ui/Badge';
import { EmptyState } from '../components/ui/EmptyState';
import { Field } from '../components/ui/Field';
import { NoticeBanner } from '../components/shared/NoticeBanner';
import { TechnicalDetails } from '../components/shared/TechnicalDetails';
import { ActivityList } from '../components/shared/ActivityList';
import { CrawlButton } from '../components/shared/ClientActions';
import { UniversalInstallerPanel } from '../components/shared/UniversalInstallerPanel';
import { clientPanelHref } from '../utils/clientLinks';
import { panelPasswordLabel, money, number, percent, shortTime, labelize } from '../utils/format';
import { getCrmVertical } from '../verticals/registry';
import { clientWorkspaceTabs } from '../verticals/workspace';
import type { ClientWorkspaceTabDefinition, ClientWorkspaceTabId, CrmVerticalDefinition } from '../verticals/types';
import { AdapterTab } from './client-workspace/AdapterTab';
import { PromptTab } from './client-workspace/PromptTab';
import {
  CRAWL_OPERATION_STAGES,
  INTEGRATION_OPERATION_STAGES,
  OperationFeedbackPanel,
  OperatorRunSummary,
  READINESS_OPERATION_STAGES,
  minimumOperationDuration,
  normalizeTimelineStatus,
  operationLabel,
  operationBelongsToFeedback,
  operationMinimumRemainingMs,
  operationResultTab,
  operationStages,
  operationStepInterval,
  timestampMs,
  type OperationFeedbackState,
} from './client-workspace/OperationFeedback';
import { ClientOperatorCenter } from './client-workspace/OperatorCenter';

const CATALOG_PAGE_LIMIT = 1000;
const CATALOG_PAGE_SIZE = 12;
const CORE_CLIENT_TAB_IDS = new Set<ClientWorkspaceTabId>([
  'overview',
  'integration',
  'readiness',
  'catalog',
  'crawl',
  'activity',
  'adapter',
  'prompt',
  'controls',
]);

const SMOKE_TEST_OPERATION_STAGES = [
  'Preparing prompt set',
  'Running assistant responses',
  'Checking expected actions',
  'Comparing retrieved data',
  'Saving prompt evidence',
];

interface SmokeTestFeedbackState {
  status: 'running' | 'complete' | 'failed';
  stageIndex: number;
  startedAt: number;
  message: string;
}

const ACTION_LABELS: Record<string, string> = {
  ADD_TO_CART: 'Add to cart',
  CHECKOUT: 'Checkout',
  CLEAR_CART: 'Clear cart',
  CLEAR_FILTERS: 'Clear filters',
  CLEAR_HISTORY: 'Clear history',
  CAPTURE_LEAD: 'Capture lead',
  COMPARE_ENTITIES: 'Compare records',
  FILTER_PRODUCTS: 'Filter records',
  FILTER_ENTITIES: 'Filter records',
  HANDOFF_TO_AGENT: 'Agent handoff',
  HANDOFF_TO_HUMAN: 'Human handoff',
  HANDOFF_TO_LICENSED_AGENT: 'Licensed agent handoff',
  NAVIGATE_TO: 'Navigate',
  OPEN_CLAIM_FLOW: 'Open claims',
  OPEN_CONTACT: 'Open contact',
  OPEN_POLICY: 'Open policy',
  OPEN_RENEWAL_FLOW: 'Open renewal',
  REMOVE_FROM_CART: 'Remove from cart',
  SHOW_COMPARISON: 'Compare records',
  SHOW_ENTITIES: 'Show records',
  SHOW_PRODUCTS: 'Show records',
  SHOW_PRODUCT_DETAIL: 'Record detail',
  SORT_ENTITIES: 'Sort records',
  SORT_PRODUCTS: 'Sort records',
  START_QUOTE: 'Start quote',
  UPDATE_CART_QUANTITY: 'Update quantity',
  UPDATE_PREFERENCES: 'Update preferences',
};

interface DisplayProduct {
  id: string;
  name: string;
  brand: string;
  category: string;
  description: string;
  price: number;
  stock: number | null;
  imageUrl: string;
  vectorized: boolean;
  rating: number | null;
  reviewCount: number | null;
}

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
  const [capabilities, setCapabilities] = useState<CapabilitiesSummary | null>(null);
  const [scanReport, setScanReport] = useState<ReadinessReport | null>(null);
  const [crawlReport, setCrawlReport] = useState<CrawlReport | null>(null);
  const [catalogProducts, setCatalogProducts] = useState<CatalogProduct[]>([]);
  const [catalogLoading, setCatalogLoading] = useState(false);
  const [catalogError, setCatalogError] = useState('');
  const [reportError, setReportError] = useState('');
  const [smokeTesting, setSmokeTesting] = useState(false);
  const [smokeTestFeedback, setSmokeTestFeedback] = useState<SmokeTestFeedbackState | null>(null);
  const [standaloneSmokeReport, setStandaloneSmokeReport] = useState<Record<string, unknown> | null>(null);
  const [operationFeedback, setOperationFeedback] = useState<OperationFeedbackState | null>(null);
  const [operationStatus, setOperationStatus] = useState<OperationStatusResponse | null>(null);
  const operationFeedbackAnchorRef = useRef<HTMLDivElement | null>(null);
  const clientTabPanelRef = useRef<HTMLElement | null>(null);
  const crawling = crawlingSites.has(client.site_id);
  const autoIntegrating = autoIntegratingSites.has(client.site_id);
  const setupOrReadinessRunning =
    autoIntegrating
    || normalizeTimelineStatus(operationStatus?.operations.integration?.status) === 'running'
    || normalizeTimelineStatus(operationStatus?.operations.readiness?.status) === 'running';
  const automationLocked = client.status === 'available';
  const sourceStatus = clientRuntimeStatus(client);
  const sourceReachable = sourceStatus === 'online';
  const activeTabDefinition = workspaceTabs.find((tab) => tab.id === activeTab) ?? workspaceTabs[0]!;
  const reportRefreshKey = useMemo(
    () =>
      JSON.stringify({
        status: client.last_crawl_status || '',
        crawledAt: client.last_crawl_at || '',
        initialization: safeRecord(client.vertical_config).initialization || {},
        catalog: client.catalog,
      }),
    [client.last_crawl_status, client.last_crawl_at, client.vertical_config, client.catalog],
  );

  const refreshOperationStatus = useCallback(async () => {
    try {
      setOperationStatus(await crmApi.getOperationStatus(client.site_id));
    } catch {
      setOperationStatus(null);
    }
  }, [client.site_id]);

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

  useEffect(() => {
    if (!operationFeedback || operationFeedback.status !== 'running') return undefined;
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
    }, operationStepInterval(operationFeedback.kind));
    return () => window.clearInterval(timer);
  }, [operationFeedback?.kind, operationFeedback?.status]);

  useEffect(() => {
    if (!smokeTestFeedback || smokeTestFeedback.status !== 'running') return undefined;
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
  }, [smokeTestFeedback?.status]);

  useEffect(() => {
    if (!operationFeedback) return undefined;
    const timer = window.setTimeout(() => {
      operationFeedbackAnchorRef.current?.scrollIntoView({ block: 'start', behavior: 'smooth' });
    }, 80);
    return () => window.clearTimeout(timer);
  }, [operationFeedback?.kind, operationFeedback?.startedAt]);

  useEffect(() => {
    void refreshOperationStatus();
  }, [refreshOperationStatus, reportRefreshKey]);

  useEffect(() => {
    if (!operationFeedback || operationFeedback.status !== 'running') return undefined;
    const timer = window.setInterval(() => {
      void refreshOperationStatus();
    }, 2500);
    void refreshOperationStatus();
    return () => window.clearInterval(timer);
  }, [operationFeedback?.kind, operationFeedback?.status, refreshOperationStatus]);

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
  }, [operationFeedback, operationStatus]);

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
    if (!operationFeedback || operationFeedback.kind !== 'integration' || operationFeedback.status !== 'running') return undefined;
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
    const holdMs = operationMinimumRemainingMs(operationFeedback);
    if (holdMs > 0) {
      const timer = window.setTimeout(completeIntegration, holdMs);
      return () => window.clearTimeout(timer);
    }
    completeIntegration();
    return undefined;
  }, [autoIntegrating, operationFeedback?.kind, operationFeedback?.startedAt, operationFeedback?.status]);

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
    if (!operationFeedback || operationFeedback.kind !== 'crawl' || operationFeedback.status !== 'running') return undefined;
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
    const holdMs = operationMinimumRemainingMs(operationFeedback);
    if (holdMs > 0) {
      const timer = window.setTimeout(completeCrawl, holdMs);
      return () => window.clearTimeout(timer);
    }
    completeCrawl();
    return undefined;
  }, [crawling, operationFeedback?.kind, operationFeedback?.startedAt, operationFeedback?.status]);

  useEffect(() => {
    let cancelled = false;
    setReportError('');
    Promise.allSettled([
      crmApi.getCapabilities(client.site_id),
      crmApi.getScanReport(client.site_id),
      crmApi.getCrawlReport(client.site_id),
    ]).then(([capabilityResult, scanResult, crawlResult]) => {
      if (cancelled) return;
      if (capabilityResult.status === 'fulfilled') setCapabilities(capabilityResult.value);
      if (scanResult.status === 'fulfilled') setScanReport(scanResult.value.report);
      if (crawlResult.status === 'fulfilled') setCrawlReport(crawlResult.value.report);
      if ([capabilityResult, scanResult, crawlResult].some((result) => result.status === 'rejected')) {
        setReportError('Some client reports could not be loaded. Run a scan or refresh after the next crawl.');
      }
    });
    return () => {
      cancelled = true;
    };
  }, [client.site_id, reportRefreshKey]);

  useEffect(() => {
    let cancelled = false;
    setCatalogLoading(true);
    setCatalogError('');
    crmApi
      .catalogProducts(client.site_id, CATALOG_PAGE_LIMIT)
      .then((products) => {
        if (!cancelled) setCatalogProducts(products);
      })
      .catch((error: unknown) => {
        if (cancelled) return;
        setCatalogProducts([]);
        setCatalogError(error instanceof Error ? error.message : 'Full catalog failed to load. Showing preview data.');
      })
      .finally(() => {
        if (!cancelled) setCatalogLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [client.site_id, client.catalog.active_products, client.catalog.missing_embeddings, client.last_crawl_at]);

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

  const displayedProducts = catalogProducts.length
    ? catalogProducts.map(normalizeCatalogProduct)
    : (client.catalog_preview ?? []).map(normalizeCatalogProduct);

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
        onRemoveClient={() => onRemoveClient(client.site_id)}
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
      <section
        id={tabPanelId(activeTab)}
        ref={clientTabPanelRef}
        className="client-tab-panel"
        role="region"
        aria-label={activeTabDefinition.label}
      >
        {activeTab === 'overview' ? (
          <ClientOverviewTab
            client={client}
            capabilities={capabilities}
            crawlReport={crawlReport}
            onOpenTab={setActiveTab}
            vertical={vertical}
          />
        ) : null}
        {activeTab === 'integration' ? (
          <ClientIntegrationTab
            client={client}
            capabilities={capabilities}
            scanReport={scanReport}
            crawlReport={crawlReport}
            standaloneSmokeReport={standaloneSmokeReport}
            smokeTestFeedback={smokeTestFeedback}
            smokeTesting={smokeTesting}
            crawling={crawling}
            autoIntegrating={autoIntegrating}
            automationLocked={automationLocked}
            onRunAssistantSmokeTests={handleRunAssistantSmokeTests}
            onOpenTab={setActiveTab}
            vertical={vertical}
          />
        ) : null}
        {activeTab === 'readiness' ? (
          <ClientReadinessTab
            client={client}
            capabilities={capabilities}
            scanReport={scanReport}
            scanning={setupOrReadinessRunning}
            operationFeedback={operationFeedback}
            operationStatus={operationStatus}
            sourceReachable={sourceReachable}
            sourceStatus={sourceStatus}
            onRunSetup={handleStartIntegration}
            automationLocked={automationLocked}
            vertical={vertical}
          />
        ) : null}
        {activeTab === 'catalog' ? (
          <ClientCatalogTab
            products={displayedProducts}
            loading={catalogLoading}
            error={catalogError}
            fallbackCount={client.catalog_preview?.length ?? 0}
            totalProducts={client.catalog.active_products}
            onOpenTab={setActiveTab}
            vertical={vertical}
          />
        ) : null}
        {activeTab === 'crawl' ? (
          <ClientCrawlTab
            client={client}
            crawlReport={crawlReport}
            crawling={crawling}
            automationLocked={automationLocked}
            sourceReachable={sourceReachable}
            sourceStatus={sourceStatus}
            onTriggerCrawl={() => handleStartCrawl()}
            vertical={vertical}
          />
        ) : null}
        {activeTab === 'activity' ? <ClientActivityTab client={client} recentActivity={recentActivity} /> : null}
        {activeTab === 'adapter' ? <AdapterTab client={client} vertical={vertical} /> : null}
        {activeTab === 'prompt' ? <PromptTab client={client} vertical={vertical} /> : null}
        {activeTab === 'controls' ? (
          <ClientControlsTab
            client={client}
            automationLocked={automationLocked}
            onRemoveClient={onRemoveClient}
            onToggleClient={onToggleClient}
            onUpdateTokenLimits={onUpdateTokenLimits}
            onOpenPasswordDialog={onOpenPasswordDialog}
            onOpenTab={setActiveTab}
            onViewChange={onViewChange}
          />
        ) : null}
        {isExtensionTab(activeTab) ? (
          <VerticalExtensionTab tab={activeTabDefinition} vertical={vertical} />
        ) : null}
      </section>
    </div>
  );
}

function tabPanelId(tabId: ClientWorkspaceTabId) {
  return `client-tab-panel-${tabId}`;
}

function minimumDelay(startedAt: number, minimumMs: number) {
  const remainingMs = Math.max(0, minimumMs - (Date.now() - startedAt));
  if (!remainingMs) return Promise.resolve();
  return new Promise<void>((resolve) => window.setTimeout(resolve, remainingMs));
}

function minimumSmokeTestDuration() {
  return Math.max(SMOKE_TEST_OPERATION_STAGES.length * 900 + 400, 6200);
}

function clientRuntimeStatus(client: Client) {
  return String(client.runtime_status?.status || 'unknown').toLowerCase();
}

function ClientQuickPasswordReset({ client }: { client: Client }) {
  const [password, setPassword] = useState('');
  const [message, setMessage] = useState('');
  const [working, setWorking] = useState(false);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const nextPassword = password.trim();
    if (nextPassword.length < 12) {
      setMessage('Password must be at least 12 characters.');
      return;
    }
    setWorking(true);
    setMessage('');
    try {
      await crmApi.updateClientPanelPassword(client.site_id, { password: nextPassword, auto_generate: false });
      setPassword('');
      setMessage('Password updated successfully.');
    } catch (error) {
      setMessage(error instanceof Error ? error.message : 'Password update failed.');
    } finally {
      setWorking(false);
    }
  }

  const messageTone = message.toLowerCase().includes('failed') || message.toLowerCase().includes('must') ? 'error' : 'success';

  return (
    <form onSubmit={submit} className="flex flex-col gap-3">
      <div className="flex gap-2 items-end">
        <div className="flex-1">
          <Field
            label="New password"
            type="text"
            minLength={12}
            value={password}
            onChange={(event) => setPassword(event.currentTarget.value)}
            placeholder="Minimum 12 characters"
            autoComplete="off"
          />
        </div>
        <Button type="submit" disabled={working || password.length < 12}>
          Save Password
        </Button>
      </div>
      {message ? <NoticeBanner tone={messageTone} message={message} /> : null}
    </form>
  );
}

function ClientOverviewTab({
  client,
  capabilities,
  crawlReport,
  onOpenTab,
  vertical,
}: {
  client: Client;
  capabilities: CapabilitiesSummary | null;
  crawlReport: CrawlReport | null;
  onOpenTab: (tab: ClientWorkspaceTabId) => void;
  vertical: CrmVerticalDefinition;
}) {
  return (
    <div className="tab-content fade-in">
      <div className="grid gap-3 md:grid-cols-2 2xl:grid-cols-4">
        <MetricCard
          label={`Active ${vertical.entityLabelPlural}`}
          value={client.catalog.active_products}
          detail={`${number(client.catalog.categories ?? 0)} groups`}
          onClick={() => onOpenTab('catalog')}
        />
        <MetricCard label="Missing vectors" value={client.catalog.missing_embeddings} detail="Needs RAG sync" onClick={() => onOpenTab('catalog')} />
        <MetricCard label="Voice turns" value={client.usage.total_turns} detail={`${number(client.usage.turns_today)} today`} onClick={() => onOpenTab('activity')} />
        <MetricCard label="Crawl coverage" value={`${percent(crawlReport?.coverage_score ?? 0)}%`} detail={client.last_crawl_status || 'not started'} onClick={() => onOpenTab('crawl')} />
      </div>
      <ClientWorkspaceMap
        client={client}
        capabilities={capabilities}
        crawlReport={crawlReport}
        vertical={vertical}
        onOpenTab={onOpenTab}
      />
      <div className="grid gap-4 xl:grid-cols-[0.9fr_1.1fr]">
        <Panel title="Client identity">
          <KeyValue label="Site ID" value={client.site_id} />
          <KeyValue label="Origin" value={client.allowed_origin} />
          <KeyValue label="Deploy mode" value={client.deploy_mode} />
          <KeyValue label="Vertical" value={client.vertical_label || vertical.label} />
          <KeyValue label="Risk level" value={client.risk_level || vertical.riskLevel} />
          <KeyValue label="Plan" value={client.plan} />
          <KeyValue label="Adapter" value={client.adapter_name} />
          <KeyValue label="Last crawl" value={shortTime(client.last_crawl_at)} />
        </Panel>
        <div className="flex flex-col gap-4">
          <Panel title="Security & Access">
            <div className="mb-4 text-sm text-muted">
              The client panel password is encrypted (PBKDF2) and cannot be viewed. Set a new password below.
            </div>
            <ClientQuickPasswordReset client={client} />
          </Panel>
          <UniversalInstallerPanel compact />
        </div>
      </div>
      <div className="grid gap-4 xl:grid-cols-2">
        <Panel title="Readiness at a glance">
          <CapabilitySnapshot capabilities={capabilities} />
        </Panel>
        <Panel title="Next useful checks">
          <div className="action-board">
            <ActionTile
              icon={ShieldCheck}
              title="Readiness output"
              text={`Review supported actions, gaps, and evidence before a client demo.`}
              actionLabel="Open readiness"
              onClick={() => onOpenTab('readiness')}
            />
            <ActionTile
              icon={PackageOpen}
              title={`Spot-check ${vertical.entityLabelPlural}`}
              text="Review names, media, source coverage, and vector state."
              actionLabel="Open catalog"
              onClick={() => onOpenTab('catalog')}
            />
            <ActionTile
              icon={Gauge}
              title="Crawl report"
              text="Inspect source coverage, failed URLs, blocked pages, and sync history."
              actionLabel="Open crawl"
              onClick={() => onOpenTab('crawl')}
            />
          </div>
        </Panel>
      </div>
    </div>
  );
}

function ClientWorkspaceMap({
  client,
  capabilities,
  crawlReport,
  vertical,
  onOpenTab,
}: {
  client: Client;
  capabilities: CapabilitiesSummary | null;
  crawlReport: CrawlReport | null;
  vertical: CrmVerticalDefinition;
  onOpenTab: (tab: ClientWorkspaceTabId) => void;
}) {
  const unsupported = capabilities?.unsupported.length ?? 0;
  const supported = capabilities?.supported.length ?? 0;
  const setupState = setupEvidenceState(client);
  const crawlState = client.last_crawl_status || 'not started';
  const vectorState = client.catalog.missing_embeddings
    ? `${number(client.catalog.missing_embeddings)} missing`
    : 'ready';
  const cards: Array<{
    tab: ClientWorkspaceTabId;
    icon: LucideIcon;
    title: string;
    status: string;
    detail: string;
    tone: 'ok' | 'warn' | 'idle';
  }> = [
    {
      tab: 'readiness',
      icon: ShieldCheck,
      title: 'Readiness',
      status: capabilities ? `${number(supported)} supported / ${number(unsupported)} gaps` : 'not scanned',
      detail: capabilities
        ? 'Review supported actions, blocked capabilities, and saved evidence.'
        : 'Run a scan to see exactly what is ready and what needs work.',
      tone: capabilities ? (unsupported ? 'warn' : 'ok') : 'idle',
    },
    {
      tab: 'integration',
      icon: ClipboardCheck,
      title: 'Setup evidence',
      status: setupState,
      detail: 'One place for crawl, route discovery, rehearsal, readiness, and prompt evidence.',
      tone: setupState === 'saved' ? 'ok' : 'idle',
    },
    {
      tab: 'catalog',
      icon: PackageOpen,
      title: `${activeEntityTitle(vertical)} data`,
      status: `${number(client.catalog.active_products)} active / ${vectorState}`,
      detail: `Inspect source records, vectors, and ${vertical.entityLabelPlural} that Maya can cite.`,
      tone: client.catalog.active_products && !client.catalog.missing_embeddings ? 'ok' : 'warn',
    },
    {
      tab: 'crawl',
      icon: Gauge,
      title: 'Crawl report',
      status: `${crawlState} / ${percent(crawlReport?.coverage_score ?? 0)}% coverage`,
      detail: 'Open pages, failures, blocked URLs, source metadata, and sync outcome.',
      tone: crawlReport?.coverage_score ? 'ok' : 'idle',
    },
    {
      tab: 'activity',
      icon: Eye,
      title: 'Recent activity',
      status: `${number(client.usage.total_turns)} turns`,
      detail: 'Inspect real sessions and whether the assistant produced useful responses.',
      tone: client.usage.total_turns ? 'ok' : 'idle',
    },
    {
      tab: 'controls',
      icon: Settings,
      title: 'Runtime controls',
      status: client.status,
      detail: 'Widget state, token limits, owner panel password, and remove-client controls.',
      tone: client.status === 'live' ? 'ok' : 'idle',
    },
  ];

  return (
    <Panel title="Workspace map">
      <div className="client-workspace-map">
        {cards.map((card) => {
          const Icon = card.icon;
          return (
            <button
              key={card.tab}
              className={`client-workspace-card ${card.tone}`}
              type="button"
              onClick={() => onOpenTab(card.tab)}
            >
              <Icon aria-hidden="true" />
              <span>
                <strong>{card.title}</strong>
                <small>{card.status}</small>
                <em>{card.detail}</em>
              </span>
            </button>
          );
        })}
      </div>
    </Panel>
  );
}

function setupEvidenceState(client: Client) {
  const initialization = safeRecord(safeRecord(client.vertical_config).initialization);
  const stages = Array.isArray(initialization.stages) ? initialization.stages : [];
  if (stages.length) return 'saved';
  if (client.last_crawl_at) return 'partial';
  return 'not run';
}

function ClientIntegrationTab({
  client,
  capabilities,
  scanReport,
  crawlReport,
  standaloneSmokeReport,
  smokeTestFeedback,
  smokeTesting,
  crawling,
  autoIntegrating,
  automationLocked,
  onRunAssistantSmokeTests,
  onOpenTab,
  vertical,
}: {
  client: Client;
  capabilities: CapabilitiesSummary | null;
  scanReport: ReadinessReport | null;
  crawlReport: CrawlReport | null;
  standaloneSmokeReport: Record<string, unknown> | null;
  smokeTestFeedback: SmokeTestFeedbackState | null;
  smokeTesting: boolean;
  crawling: boolean;
  autoIntegrating: boolean;
  automationLocked: boolean;
  onRunAssistantSmokeTests: () => void;
  onOpenTab: (tab: ClientWorkspaceTabId) => void;
  vertical: CrmVerticalDefinition;
}) {
  const verticalConfig = safeRecord(client.vertical_config);
  const initialization = safeRecord(verticalConfig.initialization);
  const flow = safeRecord(verticalConfig.flow);
  const rehearsal = safeRecord(verticalConfig.rehearsal);
  const regression = safeRecord(verticalConfig.regression);
  const actionHealth = safeRecord(verticalConfig.action_health);
  const actionPolicy = safeRecord(verticalConfig.action_policy);
  const savedStandaloneSmokeReport = safeRecord(verticalConfig.assistant_smoke_tests);
  const latestStandaloneSmokeReport = standaloneSmokeReport ?? savedStandaloneSmokeReport;
  const stageRows = integrationStageRows(initialization, {
    crawlReport,
    flow,
    rehearsal,
    regression,
    scanReport,
  });
  const visibleStageRows = liveIntegrationStageRows(stageRows, autoIntegrating);
  const preferStandaloneSmokeReport = Boolean(standaloneSmokeReport);
  const smokeTests = integrationSmokeTests(stageRows, latestStandaloneSmokeReport, preferStandaloneSmokeReport);
  const score = integrationScore(client, capabilities, stageRows, flow, rehearsal, actionHealth, smokeTests);
  const gaps = integrationGaps(client, capabilities, stageRows, flow, actionHealth, actionPolicy, automationLocked, smokeTests);
  const fixes = integrationFixes(gaps, vertical);

  return (
    <div className="tab-content fade-in">
      <section className="section-row">
        <div>
          <h2 className="text-base font-semibold">Setup run</h2>
          <p className="mt-1 text-sm text-muted">
            One guided evidence run for crawl, adapter discovery, action rehearsal, readiness, prompt checks, gaps, and next fixes.
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Button variant="secondary" icon={ClipboardCheck} disabled={smokeTesting || automationLocked} onClick={onRunAssistantSmokeTests}>
            {smokeTesting ? 'Testing prompts...' : 'Run prompt tests'}
          </Button>
        </div>
      </section>

      {automationLocked ? (
        <NoticeBanner
          tone="info"
          message="This client is Available. Move it to Current before running setup; activation itself will not crawl or start setup."
        />
      ) : null}
      {autoIntegrating ? (
        <NoticeBanner
          tone="info"
          message="Setup run is queued or running now. This view refreshes backend stage evidence every 10 seconds until the run finishes."
        />
      ) : null}
      <PromptSmokeRunConsole
        feedback={smokeTestFeedback}
        latestReport={latestStandaloneSmokeReport}
        onOpenEvidence={() => {
          document.getElementById('assistant-prompt-evidence')?.scrollIntoView({ behavior: 'smooth', block: 'start' });
        }}
      />

      <div className="integration-score-grid">
        <section className="card integration-score-card">
          <span className="kpi-label">Setup picture</span>
          <strong className="kpi-value">{score}%</strong>
          <p className="text-sm text-muted">Weighted from lifecycle, crawl data, vectors, flow discovery, rehearsal, readiness, action health, and prompt evidence.</p>
        </section>
        <Panel title="Current status">
          <KeyValue label="Lifecycle" value={automationLocked ? 'Available discovery' : 'Current client'} />
          <KeyValue label="Pipeline" value={integrationInitializationSummary(initialization, autoIntegrating)} />
          <KeyValue label="Current stage" value={currentIntegrationStageLabel(visibleStageRows)} />
          <KeyValue label="Next action" value={nextIntegrationAction(gaps, automationLocked, autoIntegrating)} />
          <KeyValue label="Catalog / knowledge" value={`${number(client.catalog.active_products)} active, ${number(client.catalog.missing_embeddings)} missing vectors`} />
          <KeyValue label="Readiness" value={capabilities ? `${capabilities.supported.length} supported, ${capabilities.unsupported.length} needs work` : 'not scanned'} />
          <KeyValue label="Prompt tests" value={assistantSmokeSummary(stageRows, latestStandaloneSmokeReport, preferStandaloneSmokeReport)} />
          <KeyValue label="Action health" value={actionHealthSummary(actionHealth)} />
          <KeyValue label="Evidence refresh" value={autoIntegrating || crawling ? 'polling from backend' : 'refreshes after setup, crawl, or scan changes'} />
        </Panel>
        <IntegrationEvidenceMap
          client={client}
          capabilities={capabilities}
          crawlReport={crawlReport}
          visibleStageRows={visibleStageRows}
          smokeSummary={assistantSmokeSummary(stageRows, latestStandaloneSmokeReport, preferStandaloneSmokeReport)}
          onOpenTab={onOpenTab}
        />
      </div>

      <DomainActionCoveragePanel
        scanReport={scanReport}
        vertical={vertical}
        onOpenTab={onOpenTab}
      />
      <ReadinessGapEvidencePanel
        scanReport={scanReport}
        onOpenTab={onOpenTab}
      />

      <Panel title="Setup stages">
        <div className="integration-stage-list">
          {visibleStageRows.map((stage) => (
            <article key={stage.name} className={`integration-stage integration-stage-${stage.status}`}>
              <div className="integration-stage-head">
                <StatusPill value={stage.status} />
                <strong>{stage.label}</strong>
              </div>
              <p>{stage.message}</p>
              <small>{stage.detail}</small>
            </article>
          ))}
        </div>
      </Panel>

      {smokeTests.length ? (
        <Panel title="Assistant prompt smoke tests">
          <div id="assistant-prompt-evidence" className="panel-anchor" />
          <div className="integration-list">
            {smokeTests.map((test) => (
              <article key={test.name} className={`integration-list-item ${test.status === 'failed' ? 'high' : ''}`}>
                <StatusPill value={test.status} />
                <div>
                  <strong>{test.prompt}</strong>
                  <p>{smokeTestHeadline(test)}</p>
                  <SmokeTestEvidence test={test} />
                </div>
              </article>
            ))}
          </div>
        </Panel>
      ) : null}

      <div className="grid gap-4 xl:grid-cols-2">
        <Panel title="What is still pending">
          {gaps.length ? (
            <div className="integration-list">
              {gaps.map((gap) => (
                <article key={gap.title} className={`integration-list-item ${gap.severity}`}>
                  <StatusPill value={gap.severity} />
                  <div>
                    <strong>{gap.title}</strong>
                    <p>{gap.detail}</p>
                  </div>
                </article>
              ))}
            </div>
          ) : (
            <EmptyState title="No blocking gaps found" message="The latest CRM evidence does not show a blocking setup gap. Keep testing real prompts after site layout changes." />
          )}
        </Panel>
        <Panel title="Recommended fixes">
          <div className="integration-list">
            {fixes.map((fix) => (
              <article key={fix.title} className="integration-list-item">
                <StatusPill value={fix.kind} />
                <div>
                  <strong>{fix.title}</strong>
                  <p>{fix.detail}</p>
                </div>
              </article>
            ))}
          </div>
        </Panel>
      </div>

      <div className="grid gap-4">
        <TechnicalDetails title="Saved initialization report JSON" data={initialization} />
      </div>
    </div>
  );
}

function PromptSmokeRunConsole({
  feedback,
  latestReport,
  onOpenEvidence,
}: {
  feedback: SmokeTestFeedbackState | null;
  latestReport: Record<string, unknown>;
  onOpenEvidence: () => void;
}) {
  const hasSavedEvidence = Array.isArray(latestReport.tests) && latestReport.tests.length > 0;
  if (!feedback && !hasSavedEvidence) return null;

  const status = feedback?.status ?? 'complete';
  const stageIndex = feedback?.stageIndex ?? SMOKE_TEST_OPERATION_STAGES.length - 1;
  const progress = status === 'complete'
    ? 100
    : status === 'failed'
    ? 100
    : Math.min(94, Math.round(((stageIndex + 1) / SMOKE_TEST_OPERATION_STAGES.length) * 100));
  const startedAt = feedback?.startedAt ? new Date(feedback.startedAt).toLocaleTimeString() : '';
  const elapsedSeconds = feedback ? Math.max(0, Math.round((Date.now() - feedback.startedAt) / 1000)) : 0;
  const remainingSeconds = status === 'running'
    ? Math.max(1, Math.ceil((minimumSmokeTestDuration() - (Date.now() - (feedback?.startedAt ?? Date.now()))) / 1000))
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

function promptSmokeStageStatus(index: number, status: SmokeTestFeedbackState['status'], stageIndex: number) {
  if (index < stageIndex) return 'complete';
  if (index === stageIndex) return status;
  return 'pending';
}

function CapabilitySnapshot({ capabilities }: { capabilities: CapabilitiesSummary | null }) {
  const [filter, setFilter] = useState<'supported' | 'unsupported'>('supported');
  if (!capabilities) return <EmptyState text="No readiness evidence is available yet." />;
  const confidence = percent(capabilities.platform_confidence);
  return (
    <div className="readiness-snapshot">
      <div>
        <span className="text-xs font-semibold uppercase text-muted">Detected platform</span>
        <strong>{capabilities.platform || 'unknown'}</strong>
        <small>{confidence}% confidence</small>
      </div>
      <Meter label="Platform confidence" value={confidence} tone="accent" />
      <div className="grid gap-3 sm:grid-cols-2">
        <button
          className={`card interactive text-left p-3 ${filter === 'supported' ? 'ring-2 ring-accent' : ''}`}
          onClick={() => setFilter('supported')}
          type="button"
        >
          <span className="text-xs text-muted">Supported checks</span>
          <strong className="mt-1 block text-xl">{capabilities.supported.length}</strong>
        </button>
        <button
          className={`card interactive text-left p-3 ${filter === 'unsupported' ? 'ring-2 ring-accent' : ''}`}
          onClick={() => setFilter('unsupported')}
          type="button"
        >
          <span className="text-xs text-muted">Needs automation</span>
          <strong className="mt-1 block text-xl">{capabilities.unsupported.length}</strong>
        </button>
      </div>
      <ActionChipGrid actions={filter === 'supported' ? capabilities.supported : capabilities.unsupported} />
    </div>
  );
}

function IntegrationEvidenceMap({
  client,
  capabilities,
  crawlReport,
  visibleStageRows,
  smokeSummary,
  onOpenTab,
}: {
  client: Client;
  capabilities: CapabilitiesSummary | null;
  crawlReport: CrawlReport | null;
  visibleStageRows: IntegrationStageRow[];
  smokeSummary: string;
  onOpenTab: (tab: ClientWorkspaceTabId) => void;
}) {
  const readinessTotal = (capabilities?.supported.length ?? 0) + (capabilities?.unsupported.length ?? 0);
  return (
    <Panel title="Evidence map">
      <div className="evidence-link-grid">
        <EvidenceLink
          icon={PackageOpen}
          label="Data"
          value={`${number(client.catalog.active_products)} active`}
          detail={`${number(client.catalog.missing_embeddings)} missing vectors`}
          onClick={() => onOpenTab('catalog')}
        />
        <EvidenceLink
          icon={Gauge}
          label="Crawl"
          value={crawlReport ? `${number(crawlReport.pages_visited)} pages` : 'not saved'}
          detail={client.last_crawl_status || 'not started'}
          onClick={() => onOpenTab('crawl')}
        />
        <EvidenceLink
          icon={ShieldCheck}
          label="Readiness"
          value={capabilities ? `${capabilities.supported.length}/${readinessTotal} checks` : 'not scanned'}
          detail={capabilities ? `${capabilities.unsupported.length} need work` : 'run setup'}
          onClick={() => onOpenTab('readiness')}
        />
        <EvidenceLink
          icon={Settings}
          label="Adapter"
          value={currentIntegrationStageLabel(visibleStageRows)}
          detail="actions, candidates, repairs"
          onClick={() => onOpenTab('adapter')}
        />
        <EvidenceLink
          icon={ClipboardCheck}
          label="Prompts"
          value={smokeSummary}
          detail="profile and smoke checks"
          onClick={() => onOpenTab('prompt')}
        />
        <EvidenceLink
          icon={KeyRound}
          label="Owner access"
          value={panelPasswordLabel(client)}
          detail="managed from Controls"
          onClick={() => onOpenTab('controls')}
        />
      </div>
    </Panel>
  );
}

function EvidenceLink({
  icon: Icon,
  label,
  value,
  detail,
  onClick,
}: {
  icon: LucideIcon;
  label: string;
  value: string;
  detail: string;
  onClick: () => void;
}) {
  return (
    <button className="evidence-link-card" type="button" onClick={onClick}>
      <Icon aria-hidden="true" />
      <span>
        <small>{label}</small>
        <strong>{value}</strong>
        <em>{detail}</em>
      </span>
    </button>
  );
}

function DomainActionCoveragePanel({
  scanReport,
  vertical,
  onOpenTab,
}: {
  scanReport: ReadinessReport | null;
  vertical: CrmVerticalDefinition;
  onOpenTab: (tab: ClientWorkspaceTabId) => void;
}) {
  const rows = domainActionRows(scanReport);
  const summary = domainActionSummary(scanReport);
  const supported = rows.filter((row) => row.supported).length;
  const total = rows.length;
  const complete = total > 0 && supported === total && (summary?.supported ?? true);
  const status = complete ? 'supported' : total > 0 ? 'needs work' : 'pending';
  const expectedActions = rows.length ? rows.map((row) => row.action) : domainActionPreview(vertical);
  return (
    <Panel
      title="Domain action coverage"
      action={
        <div className="domain-action-panel-actions">
          <Button variant="secondary" size="sm" onClick={() => onOpenTab('readiness')}>
            Open readiness
          </Button>
          <Button variant="secondary" size="sm" onClick={() => onOpenTab('adapter')}>
            Open adapter
          </Button>
        </div>
      }
    >
      <article className={`domain-action-summary ${complete ? 'ok' : 'warn'}`}>
        <div>
          <span>{vertical.label} action contract</span>
          <strong>{total ? `${supported}/${total} expected actions covered` : `${expectedActions.length} expected actions awaiting scan evidence`}</strong>
          <p>{summary?.evidence || 'Pending means no saved action-contract result exists yet. Run readiness or setup, then this panel will show covered and missing expected actions.'}</p>
        </div>
        <StatusPill value={status} />
      </article>
      {rows.length ? (
        <div className="domain-action-grid">
          {rows.map((row) => (
            <button key={row.action} type="button" className={`domain-action-row ${row.supported ? 'ok' : 'bad'}`} onClick={() => onOpenTab('readiness')}>
              <div className="domain-action-row-head">
                <div>
                  <strong>{actionLabel(row.action)}</strong>
                  <small>{row.action}</small>
                </div>
                <StatusPill value={row.supported ? 'supported' : 'needs work'} />
              </div>
              <p>{row.evidence || 'No scanner evidence was saved for this expected action.'}</p>
              <small>{percent(row.confidence)}% confidence</small>
            </button>
          ))}
        </div>
      ) : (
        <div className="domain-action-empty-board">
          <div className="domain-action-empty-main">
            <div>
              <span>Waiting for first evidence</span>
              <strong>No saved action evidence yet</strong>
              <p>
                Pending means this section has the expected action list, but no saved readiness/setup result has compared it with the live adapter yet.
              </p>
            </div>
            <div className="domain-action-panel-actions">
              <Button variant="secondary" size="sm" onClick={(event) => {
                event.stopPropagation();
                onOpenTab('readiness');
              }}>
                View readiness output
              </Button>
              <Button variant="secondary" size="sm" onClick={(event) => {
                event.stopPropagation();
                onOpenTab('adapter');
              }}>
                Inspect adapter
              </Button>
            </div>
          </div>
          <div className="domain-action-preview-grid" aria-label="Expected actions to verify">
            {expectedActions.map((action) => (
              <button key={action} type="button" onClick={() => onOpenTab('readiness')}>
                <ShieldCheck size={14} aria-hidden="true" />
                <span>
                  <strong>{actionLabel(action)}</strong>
                  <small>Open readiness output</small>
                </span>
              </button>
            ))}
          </div>
          <div className="domain-action-run-path" aria-label="Setup run path">
            <span>Readiness</span>
            <i aria-hidden="true" />
            <span>Discovery</span>
            <i aria-hidden="true" />
            <span>Rehearsal</span>
            <i aria-hidden="true" />
            <span>Evidence saved</span>
          </div>
        </div>
      )}
    </Panel>
  );
}

function domainActionPreview(vertical: CrmVerticalDefinition) {
  const actions = vertical.actionTypes?.length
    ? vertical.actionTypes
    : vertical.readinessChecks.map((check) => check.toUpperCase());
  return actions.slice(0, 8);
}

function domainActionSummary(scanReport: ReadinessReport | null) {
  return scanReport?.capabilities.find((capability) => capability.name === 'domain_action_coverage') ?? null;
}

function domainActionRows(scanReport: ReadinessReport | null) {
  return (scanReport?.capabilities ?? [])
    .filter((capability) => capability.name.startsWith('expected_action:'))
    .map((capability) => ({
      action: capability.name.replace('expected_action:', ''),
      supported: capability.supported,
      confidence: capability.confidence,
      evidence: capability.evidence,
    }));
}

function ReadinessGapEvidencePanel({
  scanReport,
  onOpenTab,
}: {
  scanReport: ReadinessReport | null;
  onOpenTab: (tab: ClientWorkspaceTabId) => void;
}) {
  const gaps = readinessGapRows(scanReport);
  return (
    <Panel
      title="Readiness checks needing automation"
      action={
        gaps.length ? (
          <Button variant="secondary" size="sm" onClick={() => onOpenTab('readiness')}>
            Open readiness
          </Button>
        ) : null
      }
    >
      {gaps.length ? (
        <div className="integration-list">
          {gaps.map((capability) => (
            <article key={capability.name} className={`integration-list-item ${capability.confidence >= 0.5 ? 'medium' : 'high'}`}>
              <StatusPill value="needs work" />
              <div>
                <strong>{labelize(capability.name)}</strong>
                <p>{capability.evidence || 'No scanner evidence was saved for this readiness check.'}</p>
                <p>
                  {percent(capability.confidence)}% confidence. {automationHintForCapability(capability.name)}
                </p>
              </div>
            </article>
          ))}
        </div>
      ) : (
        <EmptyState
          title={scanReport ? 'No unsupported readiness checks found' : 'No readiness evidence yet'}
          message={scanReport ? 'The latest readiness evidence does not show any non-domain checks needing automation.' : 'Use the operator center to run setup; per-check evidence will appear here afterward.'}
        />
      )}
    </Panel>
  );
}

function readinessGapRows(scanReport: ReadinessReport | null) {
  return (scanReport?.capabilities ?? []).filter(
    (capability) => !capability.supported && !capability.name.startsWith('expected_action:'),
  );
}

function actionLabel(action: string) {
  return ACTION_LABELS[action] || labelize(action);
}

function ActionTile({
  icon: Icon,
  title,
  text,
  actionLabel,
  disabled = false,
  onClick,
}: {
  icon: LucideIcon;
  title: string;
  text: string;
  actionLabel?: string;
  disabled?: boolean;
  onClick?: () => void;
}) {
  const content = (
    <>
      <Icon size={18} aria-hidden="true" />
      <div>
        <strong>{title}</strong>
        <p>{text}</p>
        {actionLabel ? <span>{actionLabel}</span> : null}
      </div>
    </>
  );
  if (onClick) {
    return (
      <button className="action-tile interactive" type="button" disabled={disabled} onClick={onClick}>
        {content}
      </button>
    );
  }
  return <article className="action-tile">{content}</article>;
}

function ClientReadinessTab({
  capabilities,
  scanReport,
  scanning,
  operationFeedback,
  operationStatus,
  sourceReachable,
  sourceStatus,
  automationLocked,
  onRunSetup,
  vertical,
}: {
  client: Client;
  capabilities: CapabilitiesSummary | null;
  scanReport: ReadinessReport | null;
  scanning: boolean;
  operationFeedback: OperationFeedbackState | null;
  operationStatus: OperationStatusResponse | null;
  sourceReachable: boolean;
  sourceStatus: string;
  automationLocked: boolean;
  onRunSetup: () => void;
  vertical: CrmVerticalDefinition;
}) {
  const [filter, setFilter] = useState<'needs' | 'supported' | 'all'>('needs');
  const rows = scanReport?.capabilities ?? [];
  const supported = rows.filter((capability) => capability.supported);
  const unsupported = rows.filter((capability) => !capability.supported);
  const unsupportedNonDomain = readinessGapRows(scanReport);
  const filteredRows = filter === 'all'
    ? rows
    : filter === 'supported'
    ? supported
    : unsupported;
  const confidence = percent(scanReport?.platform_confidence ?? capabilities?.platform_confidence ?? 0);
  const platform = String(scanReport?.platform || capabilities?.platform || 'unknown');
  const latestScanUnreachable = Boolean(scanReport && platform.toLowerCase() === 'unreachable');
  const readinessFeedback = operationFeedback?.kind === 'readiness' ? operationFeedback : null;
  const readinessOperation = operationStatus?.operations.readiness ?? null;
  return (
    <div className="tab-content fade-in">
      <section className="section-row">
        <div>
          <h2 className="text-base font-semibold">Readiness checks</h2>
          <p className="mt-1 text-sm text-muted">
            Current capability evidence for {vertical.entityLabelPlural}, source coverage, handoff points, and allowed actions.
          </p>
        </div>
        <Button variant="secondary" disabled={scanning || automationLocked || !sourceReachable} icon={Gauge} onClick={onRunSetup}>
          {scanning ? 'Setup running...' : 'Run setup'}
        </Button>
      </section>
      {!automationLocked && !sourceReachable ? (
        <NoticeBanner
          tone="info"
          message={`Setup is locked because the source website is ${sourceStatus}. Start the website and refresh AI Hub first. Owner panel remains available.`}
        />
      ) : null}
      <ReadinessRunConsole
        feedback={readinessFeedback}
        operation={readinessOperation}
        scanReport={scanReport}
        automationLocked={automationLocked}
      />
      <div className="readiness-summary-grid">
        <section className="card readiness-score-card">
          <span className="kpi-label">Readiness picture</span>
          <strong className="kpi-value">{latestScanUnreachable ? 'unreachable' : scanReport ? `${supported.length}/${rows.length}` : '-'}</strong>
          <p className="text-sm text-muted">
            {latestScanUnreachable
              ? 'Latest scan was saved, but the scanner could not reach the source website.'
              : rows.length
              ? `${unsupported.length} check(s) need work. ${confidence}% platform confidence.`
              : scanReport
              ? 'Latest scan saved no capability rows. Run setup if source and adapter evidence changed.'
              : 'Run setup to save the first readiness evidence set.'}
          </p>
        </section>
        <Panel title="Scan summary">
          <KeyValue label="Platform" value={platform} />
          <KeyValue label="Supported" value={supported.length} />
          <KeyValue label="Needs work" value={unsupported.length} />
          <KeyValue label="Domain" value={vertical.label} />
          <KeyValue label="Allowed actions" value={capabilities?.allowed_actions.length ?? 0} />
        </Panel>
        <Panel title="Next operator step">
          <div className="readiness-next-step">
            <StatusPill value={automationLocked ? 'available' : latestScanUnreachable || unsupported.length ? 'needs work' : rows.length ? 'ready' : 'pending'} />
            <strong>{readinessNextStep(rows.length, unsupported.length, automationLocked, latestScanUnreachable, Boolean(scanReport))}</strong>
            <p>
              {automationLocked
                ? 'Move this install to Current before scanning or changing runtime state.'
                : latestScanUnreachable
                ? 'Start the source website, refresh AI Hub, then rerun readiness. In Docker, localhost URLs are probed through the host alias too.'
                : unsupported.length
                ? 'Use the unsupported evidence below to decide whether to run setup from the operator center, repair adapter actions, or inspect source data.'
                : rows.length
                ? 'No readiness blockers are visible in the latest scan. Re-scan after source-site layout or data changes.'
                : scanReport
                ? 'The latest scan completed without capability rows. Use setup to rebuild crawl, discovery, rehearsal, and readiness evidence.'
                : 'Run setup to create the first crawl, discovery, readiness, and prompt evidence set. The staged monitor will keep progress visible.'}
            </p>
          </div>
        </Panel>
      </div>
      {unsupportedNonDomain.length ? (
        <NoticeBanner
          tone="info"
          message={`${unsupportedNonDomain.length} non-domain readiness check(s) need work. The cards below show evidence and the recommended fix path.`}
        />
      ) : null}
      <Panel
        title="Capability report"
        action={
          rows.length ? (
            <div className="readiness-filter" role="group" aria-label="Readiness report filter">
              {(['needs', 'supported', 'all'] as const).map((item) => (
                <button
                  key={item}
                  type="button"
                  className={filter === item ? 'active' : ''}
                  onClick={() => setFilter(item)}
                >
                  {item === 'needs' ? 'Needs work' : item === 'supported' ? 'Supported' : 'All'}
                </button>
              ))}
            </div>
          ) : null
        }
      >
        {filteredRows.length ? (
          <div className="capability-grid">
            {filteredRows.map((capability) => (
              <CapabilityReportCard
                key={capability.name}
                capability={capability}
                canRunSetup={!automationLocked && sourceReachable && !scanning}
                sourceStatus={sourceStatus}
                onRunSetup={onRunSetup}
              />
            ))}
          </div>
        ) : rows.length ? (
          <EmptyState title="No checks in this filter" message="Switch filters to inspect supported checks or the full report." />
        ) : (
          <EmptyState text="Run setup to generate a readable capability report." />
        )}
      </Panel>
      <div className="grid gap-4 xl:grid-cols-[0.8fr_1.2fr] items-start">
        <Panel title="Supported customer actions">
          <ActionChipGrid actions={capabilities?.allowed_actions ?? []} />
        </Panel>
        <TechnicalDetails title="Advanced readiness JSON" data={scanReport} />
      </div>
    </div>
  );
}

function ReadinessRunConsole({
  feedback,
  operation,
  scanReport,
  automationLocked,
}: {
  feedback: OperationFeedbackState | null;
  operation: OperationStatus | null;
  scanReport: ReadinessReport | null;
  automationLocked: boolean;
}) {
  const visibleOperation = visibleReadinessOperation(operation, feedback);
  const status = feedback?.status || normalizeTimelineStatus(visibleOperation?.status);
  const etaSeconds = Math.ceil(minimumOperationDuration('readiness') / 1000);
  const heading = automationLocked
    ? 'Activate before scanning'
    : status === 'running'
    ? 'Readiness scan running'
    : status === 'complete'
    ? 'Latest readiness evidence saved'
    : status === 'failed'
    ? 'Readiness scan needs retry'
    : scanReport
    ? 'Readiness evidence is available'
    : 'Ready to scan';
  const copy = automationLocked
    ? 'Move this install to Current before AI Hub scans or changes runtime state.'
    : status === 'running'
    ? 'The scanner is moving through stages now. This page stays live and the saved report appears here when the run finishes.'
    : status === 'complete'
    ? 'The latest scan output is saved below. Re-run after website, adapter, or source-data changes.'
    : status === 'failed'
    ? 'The last scan failed. Use retry from the operation monitor or run the scan again from this page.'
    : `A scan takes at least about ${number(etaSeconds)} seconds in the UI so progress, ETA, stages, and logs are visible instead of flashing.`;
  return (
    <section className={`readiness-run-console ${status}`}>
      <div className="readiness-run-console-head">
        <div>
          <span>Scanner console</span>
          <strong>{heading}</strong>
          <p>{copy}</p>
        </div>
        <StatusPill value={automationLocked ? 'available' : status === 'pending' ? 'ready' : status} />
      </div>
      <OperatorRunSummary feedback={feedback} backendOperation={visibleOperation} />
      <ol className="readiness-run-stage-preview" aria-label="Readiness scan stages">
        {READINESS_OPERATION_STAGES.map((stage, index) => {
          const stageStatus = readinessStageStatus(index, feedback, visibleOperation);
          return (
            <li key={stage} className={stageStatus}>
              <span aria-hidden="true" />
              <strong>{stage}</strong>
            </li>
          );
        })}
      </ol>
    </section>
  );
}

function visibleReadinessOperation(
  operation: OperationStatus | null,
  feedback: OperationFeedbackState | null,
) {
  if (!operation) return null;
  const status = normalizeTimelineStatus(operation.status);
  if (status === 'pending' && !operation.stages.some((stage) => normalizeTimelineStatus(stage.status) !== 'pending')) {
    return null;
  }
  if (!feedback || feedback.status !== 'running') return operation;
  return operationBelongsToFeedback(operation, feedback) ? operation : null;
}

function readinessStageStatus(
  index: number,
  feedback: OperationFeedbackState | null,
  operation: OperationStatus | null,
) {
  const backendStage = !feedback ? operation?.stages[index] : null;
  if (backendStage) return normalizeTimelineStatus(backendStage.status);
  if (!feedback) return 'pending';
  if (feedback.status === 'complete') return 'complete';
  if (index < feedback.stageIndex) return 'complete';
  if (index === feedback.stageIndex) return feedback.status;
  return 'pending';
}

function CapabilityReportCard({
  capability,
  canRunSetup,
  sourceStatus,
  onRunSetup,
}: {
  capability: ReadinessReport['capabilities'][number];
  canRunSetup: boolean;
  sourceStatus: string;
  onRunSetup: () => void;
}) {
  const Icon = capability.supported ? CheckCircle2 : capability.confidence >= 0.5 ? AlertTriangle : XCircle;
  const tone = capability.supported ? 'ok' : capability.confidence >= 0.5 ? 'warn' : 'bad';
  const hint = automationHintForCapability(capability.name);
  return (
    <article className={`capability-card capability-card-${tone}`}>
      <div className="capability-card-head">
        <Icon size={18} aria-hidden="true" />
        <StatusPill value={capability.supported ? 'supported' : 'needs work'} />
      </div>
      <h3>{labelize(capability.name)}</h3>
      <strong>{percent(capability.confidence)}% confidence</strong>
      <p>{capability.evidence || 'No scanner evidence was saved for this check.'}</p>
      {!capability.supported ? (
        <button
          className="capability-card-action capability-card-action-button"
          type="button"
          disabled={!canRunSetup}
          title={canRunSetup ? 'Run setup to rebuild evidence for this gap.' : `Setup is unavailable while source is ${sourceStatus}.`}
          onClick={onRunSetup}
        >
          <small>Suggested fix</small>
          <strong>{canRunSetup ? hint : `Source ${sourceStatus}. Start the website, refresh AI Hub, then run setup.`}</strong>
        </button>
      ) : null}
    </article>
  );
}

function readinessNextStep(
  rowCount: number,
  unsupportedCount: number,
  automationLocked: boolean,
  unreachable = false,
  hasScan = false,
) {
  if (automationLocked) return 'Activate before scanning';
  if (unreachable) return 'Source unreachable in latest scan';
  if (!rowCount && hasScan) return 'Rebuild evidence with setup';
  if (!rowCount) return 'Run setup';
  if (unsupportedCount) return 'Review unsupported evidence';
  return 'Ready, keep monitoring';
}

function automationHintForCapability(name: string) {
  const key = String(name || '').toLowerCase().replace(/[_-]+/g, ' ');
  if (key.includes('flow graph')) return 'Run setup to discover browser flows and save routes/actions.';
  if (key.includes('rehearsal')) return 'Run setup to safely rehearse discovered actions without submitting final outcomes.';
  if (key.includes('confirmation')) return 'Review adapter policy so risky steps require confirmation.';
  if (key.includes('cart') || key.includes('checkout')) return 'Run setup to re-crawl and validate cart or checkout readiness.';
  if (key.includes('catalog') || key.includes('variant')) return 'Run setup or crawl source data to refresh records and vectors.';
  return 'Run setup to refresh crawl, flow discovery, rehearsal, regression, and readiness evidence.';
}

function ActionChipGrid({ actions }: { actions: string[] }) {
  if (!actions.length) return <EmptyState text="No UI actions are allowed yet." />;
  return (
    <div className="action-chip-grid">
      {actions.map((action) => (
        <span key={action} className="action-chip">
          {actionLabel(action)}
        </span>
      ))}
    </div>
  );
}

function ClientCatalogTab({
  products,
  loading,
  error,
  fallbackCount,
  totalProducts,
  onOpenTab,
  vertical,
}: {
  products: DisplayProduct[];
  loading: boolean;
  error: string;
  fallbackCount: number;
  totalProducts: number;
  onOpenTab: (tab: ClientWorkspaceTabId) => void;
  vertical: CrmVerticalDefinition;
}) {
  const [query, setQuery] = useState('');
  const [category, setCategory] = useState('all');
  const [vectorFilter, setVectorFilter] = useState('all');
  const [page, setPage] = useState(1);
  const categories = useMemo(() => uniqueProductCategories(products), [products]);
  const categoryCounts = useMemo(() => productCategoryCounts(products), [products]);
  const visibleProducts = useMemo(
    () => filterProducts(products, query, category, vectorFilter),
    [category, products, query, vectorFilter],
  );
  const vectorizedCount = products.filter((product) => product.vectorized).length;
  const pendingVectorCount = Math.max(0, products.length - vectorizedCount);
  const inStockCount = products.filter((product) => product.stock == null || product.stock > 0).length;
  const pageCount = Math.max(1, Math.ceil(visibleProducts.length / CATALOG_PAGE_SIZE));
  const pageProducts = visibleProducts.slice((page - 1) * CATALOG_PAGE_SIZE, page * CATALOG_PAGE_SIZE);

  useEffect(() => {
    setPage(1);
  }, [category, query, vectorFilter]);

  useEffect(() => {
    if (page > pageCount) setPage(pageCount);
  }, [page, pageCount]);

  return (
    <div className="tab-content fade-in">
      <section className="section-row">
        <div>
          <h2 className="text-base font-semibold">{activeEntityTitle(vertical)} review</h2>
          <p className="mt-1 text-sm text-muted">
            Media, source data, category grouping, and vector status in one focused view.
          </p>
        </div>
        <Button variant="secondary" icon={Gauge} onClick={() => onOpenTab('crawl')}>
          Crawl report
        </Button>
      </section>
      {error ? <NoticeBanner tone="info" message={`${error} ${fallbackCount ? `Using ${fallbackCount} preview rows.` : ''}`} /> : null}
      <div className="data-health-grid">
        <DataHealthCard label="Vectorized" value={`${number(vectorizedCount)}/${number(products.length)}`} detail={`${number(pendingVectorCount)} pending vectors`} tone={pendingVectorCount ? 'warn' : 'ok'} onClick={() => setVectorFilter(pendingVectorCount ? 'pending' : 'vectorized')} />
        <DataHealthCard label="Availability" value={`${number(inStockCount)} usable`} detail={`${number(Math.max(0, products.length - inStockCount))} out of stock`} tone="neutral" onClick={() => setVectorFilter('in_stock')} />
        <DataHealthCard label="Source groups" value={number(categories.length)} detail="Filter by group below" tone="neutral" onClick={() => setCategory('all')} />
      </div>
      <div className="grid gap-3 md:grid-cols-3">
        <MetricCard
          label={`Loaded ${vertical.entityLabelPlural}`}
          value={products.length}
          detail={`${number(totalProducts)} total active`}
          onClick={() => {
            setQuery('');
            setCategory('all');
            setVectorFilter('all');
            onOpenTab('catalog');
          }}
        />
        <MetricCard
          label="Visible after filters"
          value={visibleProducts.length}
          detail={loading ? 'Refreshing catalog' : `Page ${page} of ${pageCount}`}
          onClick={() => setPage(1)}
        />
        <MetricCard
          label="Groups"
          value={categories.length}
          detail={`Click a group below to filter ${vertical.entityLabelPlural}`}
          onClick={() => setCategory('all')}
        />
      </div>
      <div className="catalog-toolbar">
        <label className="field catalog-search-field">
          <span>Search {vertical.entityLabelPlural}</span>
          <div className="input-with-icon">
            <Search size={15} aria-hidden="true" />
            <input value={query} placeholder="Name, brand, or description" onChange={(event) => setQuery(event.currentTarget.value)} />
          </div>
        </label>
        <label className="field">
          <span>Category</span>
          <select value={category} onChange={(event) => setCategory(event.currentTarget.value)}>
            <option value="all">All categories</option>
            {categories.map((item) => (
              <option key={item} value={item}>
                {item}
              </option>
            ))}
          </select>
        </label>
        <label className="field">
          <span>Vector state</span>
          <select value={vectorFilter} onChange={(event) => setVectorFilter(event.currentTarget.value)}>
            <option value="all">All rows</option>
            <option value="vectorized">Vectorized</option>
            <option value="pending">Pending vector</option>
            <option value="in_stock">In stock</option>
            <option value="out_of_stock">Out of stock</option>
          </select>
        </label>
      </div>
      {categories.length ? (
        <details className="crm-disclosure category-group-disclosure" open={categories.length <= 8 || category !== 'all'}>
          <summary>
            <span>{vertical.entityLabelPlural} groups</span>
            <strong>{category === 'all' ? `${number(categories.length)} groups` : category}</strong>
          </summary>
          <div className="category-group-panel" aria-label={`${vertical.entityLabelPlural} groups`}>
            <button
              className={`category-group-chip ${category === 'all' ? 'active' : ''}`}
              type="button"
              onClick={() => setCategory('all')}
            >
              All groups <span>{number(products.length)}</span>
            </button>
            {categories.map((item) => (
              <button
                key={item}
                className={`category-group-chip ${category === item ? 'active' : ''}`}
                type="button"
                onClick={() => setCategory(item)}
              >
                {item} <span>{number(categoryCounts[item] ?? 0)}</span>
              </button>
            ))}
          </div>
        </details>
      ) : null}
      {pageProducts.length ? (
        <>
          <div className="product-gallery">
            {pageProducts.map((product) => (
              <CatalogProductCard key={product.id} product={product} vertical={vertical} />
            ))}
          </div>
          <PaginationControl page={page} pageCount={pageCount} onPageChange={setPage} />
        </>
      ) : loading ? (
        <div className="product-gallery">
          {Array.from({ length: 6 }).map((_, index) => (
            <SkeletonCard key={index} height={320} />
          ))}
        </div>
      ) : (
        <EmptyState title={`No ${vertical.entityLabelPlural} match`} message="Adjust the search, category, or vector filters to widen this view." />
      )}
    </div>
  );
}

function DataHealthCard({
  label,
  value,
  detail,
  tone,
  onClick,
}: {
  label: string;
  value: string | number;
  detail: string;
  tone: 'ok' | 'warn' | 'neutral';
  onClick: () => void;
}) {
  return (
    <button className={`data-health-card ${tone}`} type="button" onClick={onClick}>
      <span>{label}</span>
      <strong>{value}</strong>
      <small>{detail}</small>
    </button>
  );
}

function CatalogProductCard({ product, vertical }: { product: DisplayProduct; vertical: CrmVerticalDefinition }) {
  return (
    <article className="catalog-product-card">
      <ProductImage product={product} vertical={vertical} />
      <div className="catalog-product-body">
        <div className="flex items-start justify-between gap-3">
          <div>
            <span className="text-xs font-semibold uppercase text-muted">{product.brand || product.category}</span>
            <h3>{product.name}</h3>
          </div>
          <StatusPill value={product.vectorized ? 'vectorized' : 'pending vector'} />
        </div>
        <p>{product.description || `${product.category} ${vertical.entityLabelSingular} indexed for Maya.`}</p>
        <div className="catalog-product-meta">
          <strong>{money(product.price)}</strong>
          <span>{product.stock == null ? 'Stock unknown' : `${number(product.stock)} in stock`}</span>
          {product.rating != null ? <span>{product.rating.toFixed(1)} rating</span> : null}
        </div>
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

function ProductImage({ product, vertical }: { product: DisplayProduct; vertical: CrmVerticalDefinition }) {
  const [failed, setFailed] = useState(false);
  if (!product.imageUrl || failed) {
    return (
      <div className="catalog-product-fallback">
        <PackageOpen size={28} aria-hidden="true" />
        <span>{product.category || vertical.entityLabelSingular}</span>
      </div>
    );
  }
  return <img className="catalog-product-image" src={product.imageUrl} alt={product.name} loading="lazy" onError={() => setFailed(true)} />;
}

function ClientCrawlTab({
  client,
  crawlReport,
  crawling,
  automationLocked,
  sourceReachable,
  sourceStatus,
  onTriggerCrawl,
  vertical,
}: {
  client: Client;
  crawlReport: CrawlReport | null;
  crawling: boolean;
  automationLocked: boolean;
  sourceReachable: boolean;
  sourceStatus: string;
  onTriggerCrawl: () => void;
  vertical: CrmVerticalDefinition;
}) {
  return (
    <div className="tab-content fade-in">
      <section className="section-row">
        <div>
          <h2 className="text-base font-semibold">Crawl report</h2>
          <p className="mt-1 text-sm text-muted">Source coverage, page issues, extraction totals, and sync history.</p>
        </div>
        <CrawlButton label="Start crawl" active={crawling} disabled={automationLocked || !sourceReachable} onTriggerCrawl={onTriggerCrawl} />
      </section>
      {!automationLocked && !sourceReachable ? (
        <NoticeBanner
          tone="info"
          message={`Crawl is locked because the source website is ${sourceStatus}. AI Hub cannot refresh products, records, pages, or flows until the site is online.`}
        />
      ) : null}
      <CrawlReportSummary report={crawlReport} vertical={vertical} />
      <div className="grid gap-4 xl:grid-cols-[1.1fr_0.9fr]">
        <Panel title="Crawl issues">
          {crawlReport ? (
            <CrawlIssueBoard report={crawlReport} />
          ) : (
            <EmptyState text="No crawl report is saved yet. Run a crawl to generate one." />
          )}
        </Panel>
        <Panel title="Sync run history">
          <SyncRunTimeline runs={client.sync_runs ?? []} />
        </Panel>
      </div>
      {crawlReport ? <TechnicalDetails title="Advanced crawl JSON" data={crawlReport} /> : null}
    </div>
  );
}

function CrawlReportSummary({ report, vertical }: { report: CrawlReport | null; vertical: CrmVerticalDefinition }) {
  if (!report) return <EmptyState text="Crawl report will appear here after the next priority crawl." />;
  const issueCount = report.pages_failed + report.pages_blocked;
  return (
    <div className="grid gap-3 md:grid-cols-2 2xl:grid-cols-5">
      <MetricCard label={`${activeEntityTitle(vertical)} found`} value={report.product_count} detail="Extracted source rows" />
      <MetricCard label="Variants found" value={report.variant_count} detail="Entity options" />
      <MetricCard label="Categories found" value={report.category_count} detail="Navigation coverage" />
      <MetricCard label="Page issues" value={issueCount} detail={`${number(report.pages_failed)} failed, ${number(report.pages_blocked)} blocked`} />
      <MetricCard label="Stopped by limit" value={report.stopped_by_limit ? 'Yes' : 'No'} detail={report.source_type || 'crawler'} />
    </div>
  );
}

function CrawlIssueBoard({ report }: { report: CrawlReport }) {
  const issueCount = report.pages_failed + report.pages_blocked;
  return (
    <div className="crawl-report-board">
      <div className="crawl-coverage-card">
        <div>
          <span>Coverage score</span>
          <strong>{percent(report.coverage_score)}%</strong>
          <p>{issueCount ? `${number(issueCount)} page issue(s) need review.` : 'No failed or blocked pages were saved in this report.'}</p>
        </div>
        <Meter label="Coverage" value={percent(report.coverage_score)} tone="accent" />
      </div>
      <div className="crawl-issue-grid">
        <CrawlIssueCard title="Failed pages" count={report.pages_failed} urls={report.failed_urls} />
        <CrawlIssueCard title="Blocked pages" count={report.pages_blocked} urls={report.blocked_urls} />
      </div>
      <div className="crawl-run-meta">
        <KeyValue label="Visited pages" value={report.pages_visited} />
        <KeyValue label="Duration" value={`${number(report.duration_ms)} ms`} />
        <KeyValue label="Created" value={shortTime(report.created_at)} />
      </div>
    </div>
  );
}

function CrawlIssueCard({ title, count, urls }: { title: string; count: number; urls: string[] }) {
  return (
    <article className={`crawl-issue-card ${count ? 'warn' : 'ok'}`}>
      <div className="crawl-issue-head">
        <strong>{title}</strong>
        <StatusPill value={count ? 'needs review' : 'ok'} />
      </div>
      <span>{number(count)}</span>
      {count ? <UrlList title="Inspect URLs" urls={urls} /> : <p>No URLs in this group.</p>}
    </article>
  );
}

function SyncRunTimeline({ runs }: { runs: SyncRun[] }) {
  if (!runs.length) return <EmptyState text="No sync runs are recorded yet." />;
  return (
    <div className="sync-timeline">
      {runs.map((run) => (
        <article key={`${run.id}-${run.created_at}`} className="sync-run-card">
          <div className="sync-run-dot" />
          <div>
            <div className="flex flex-wrap items-center justify-between gap-2">
              <strong>{run.source_name || 'catalog sync'}</strong>
              <span className="text-xs text-muted">{shortTime(run.created_at)}</span>
            </div>
            <div className="sync-run-metrics">
              <span>{number(run.source_count)} sourced</span>
              <span>{number(run.changed_count)} changed</span>
              <span>{number(run.vectorized_count)} vectorized</span>
              <span>{number(run.deactivated_count)} inactive</span>
            </div>
          </div>
        </article>
      ))}
    </div>
  );
}

function UrlList({ title, urls }: { title: string; urls: string[] }) {
  const [open, setOpen] = useState(false);
  if (!urls.length) return null;
  return (
    <div className="url-list">
      <button className="summary-toggle" type="button" onClick={() => setOpen((current) => !current)}>
        <ChevronDown className={open ? 'open' : ''} size={16} aria-hidden="true" />
        <span>{title} ({urls.length})</span>
      </button>
      {open ? (
        <div className="grid gap-2 pt-3">
        {urls.slice(0, 12).map((url) => (
          <code key={url}>{url}</code>
        ))}
        </div>
      ) : null}
    </div>
  );
}

function ClientActivityTab({ client, recentActivity }: { client: Client; recentActivity: UsageEvent[] }) {
  const tokenLimit = client.quota.client.limit || client.token_limit || 0;
  const tokenUsed = client.quota.client.used || client.usage.tokens_estimated || 0;
  const tokenRemaining = client.quota.client.remaining || Math.max(0, tokenLimit - tokenUsed);
  const tokenPct = tokenLimit ? Math.round((tokenUsed / tokenLimit) * 100) : 0;

  return (
    <div className="tab-content fade-in">
      <div className="grid gap-3 md:grid-cols-3">
        <MetricCard label="Total turns" value={client.usage.total_turns} detail="All time" />
        <MetricCard label="Turns today" value={client.usage.turns_today} detail="Since midnight" />
        <MetricCard label="Avg latency" value={`${number(client.usage.avg_latency_ms)} ms`} detail="Voice response" />
      </div>
      <div className="activity-insight-grid">
        <Panel title="Recent customer activity">
          <ActivityList items={recentActivity} />
          {recentActivity.length > 0 && recentActivity.length < 5 ? (
            <div className="activity-nudge">
              More activity will appear as your AI widget receives traffic.
            </div>
          ) : null}
        </Panel>
        <section className="card token-burn-card">
          <div className="card-header">
            <div>
              <h3>Token burn</h3>
              <span className="card-meta">Client quota pressure</span>
            </div>
            <span className="badge badge-blue">{number(tokenPct)}%</span>
          </div>
          <div className="token-burn-meter">
            <span style={{ width: `${Math.max(3, Math.min(100, tokenPct))}%` }} />
          </div>
          <div className="token-burn-stats">
            <KeyValue label="Used" value={`${number(tokenUsed)} tokens`} />
            <KeyValue label="Remaining" value={`${number(tokenRemaining)} tokens`} />
            <KeyValue label="Session cap" value={`${number(client.session_token_limit ?? 0)} tokens`} />
          </div>
        </section>
      </div>
    </div>
  );
}

function VerticalExtensionTab({
  tab,
  vertical,
}: {
  tab: ClientWorkspaceTabDefinition;
  vertical: CrmVerticalDefinition;
}) {
  return (
    <div className="tab-content fade-in">
      <section className="section-row">
        <div>
          <h2 className="text-base font-semibold">{tab.label}</h2>
          <p className="mt-1 text-sm text-muted">
            {extensionTabDescription(tab.id, vertical)}
          </p>
        </div>
        <StatusPill value={vertical.riskLevel} />
      </section>
      <div className="grid gap-4 xl:grid-cols-2">
        <Panel title="Entity model">
          <ActionChipGrid actions={vertical.entityTypes} />
        </Panel>
        <Panel title="Readiness focus">
          <ActionChipGrid actions={vertical.readinessChecks} />
        </Panel>
      </div>
      <Panel title={`${tab.label} records`}>
        <EmptyState
          title="No records yet"
          message={extensionTabEmptyMessage(tab.id, tab.label)}
        />
      </Panel>
    </div>
  );
}

function extensionTabDescription(tabId: ClientWorkspaceTabId, vertical: CrmVerticalDefinition) {
  if (tabId === 'leads') {
    return 'Leads are visitor intents Maya can capture or hand off: quote requests, callbacks, applications, appointment requests, and contact details. They are not completed purchases, policies, approvals, or claims.';
  }
  if (tabId === 'quote_flows') {
    return 'Quote flows show the fields and steps Maya can prepare for the website without claiming eligibility, premium finality, or policy issuance.';
  }
  if (tabId === 'compliance') {
    return 'Compliance tracks high-risk boundaries, confirmation rules, disclosures, and handoff requirements for this vertical.';
  }
  return `${vertical.label} workspace for ${vertical.entityLabelPlural}.`;
}

function extensionTabEmptyMessage(tabId: ClientWorkspaceTabId, label: string) {
  if (tabId === 'leads') {
    return 'No lead events are loaded yet. When visitors ask Maya for callbacks, quotes, applications, or contact handoff, those intents can appear here.';
  }
  if (tabId === 'quote_flows') {
    return 'No quote flow records are loaded yet. Run setup to rediscover forms, required fields, and safe handoff boundaries.';
  }
  return `No ${label.toLowerCase()} records are loaded for this client yet.`;
}

function ClientControlsTab({
  client,
  automationLocked,
  onRemoveClient,
  onToggleClient,
  onUpdateTokenLimits,
  onOpenPasswordDialog,
  onOpenTab,
  onViewChange,
}: {
  client: Client;
  automationLocked: boolean;
  onRemoveClient: (siteId: string) => void;
  onToggleClient: (siteId: string, enabled: boolean) => void;
  onUpdateTokenLimits: (siteId: string, tokenLimit: number, sessionTokenLimit: number) => Promise<void>;
  onOpenPasswordDialog: (client: Client) => void;
  onOpenTab: (tab: ClientWorkspaceTabId) => void;
  onViewChange: (view: View) => void;
}) {
  return (
    <div className="tab-content fade-in">
      <section className="section-row">
        <div>
          <h2 className="text-base font-semibold">Controls</h2>
          <p className="mt-1 text-sm text-muted">
            Configure owner access, token limits, widget state, adapter settings, and high-risk account actions.
          </p>
        </div>
        <Button variant="secondary" icon={Settings} onClick={() => onViewChange('settings')}>
          Global settings
        </Button>
      </section>
      <div className="control-card-grid">
        <div className="card">
          <div className="card-header">
            <h3>Owner panel access</h3>
            <span className="card-meta">Client-facing workspace</span>
          </div>
          <ClientPanelShareBlock client={client} panelUrl={clientPanelHref(client.site_id)} onOpenPasswordDialog={onOpenPasswordDialog} />
        </div>
        <Panel title="Runtime switches">
          <div className="settings-action-list">
            <button
              className="settings-action-row"
              type="button"
              disabled={automationLocked}
              onClick={() => onToggleClient(client.site_id, client.status !== 'live')}
            >
              <Eye aria-hidden="true" />
              <span>
                <strong>{client.status === 'live' ? 'Disable widget' : 'Enable widget'}</strong>
                <small>{automationLocked ? 'Activate this client before changing widget state.' : `Current widget state: ${client.status}.`}</small>
              </span>
              <StatusPill value={client.status} />
            </button>
            <button className="settings-action-row" type="button" onClick={() => onOpenPasswordDialog(client)}>
              <KeyRound aria-hidden="true" />
              <span>
                <strong>Panel password</strong>
                <small>Set, reset, or revoke the owner-facing panel credential.</small>
              </span>
              <StatusPill value={panelPasswordLabel(client)} />
            </button>
            <button className="settings-action-row" type="button" onClick={() => onOpenTab('adapter')}>
              <Settings aria-hidden="true" />
              <span>
                <strong>Adapter configuration</strong>
                <small>Review generated action maps, action candidates, and repair proposals.</small>
              </span>
            </button>
            <button className="settings-action-row" type="button" onClick={() => onOpenTab('prompt')}>
              <ClipboardCheck aria-hidden="true" />
              <span>
                <strong>Prompt profile</strong>
                <small>Inspect the client-specific assistant prompt, safety notes, and versions.</small>
              </span>
            </button>
          </div>
        </Panel>
      </div>
      <div className="control-card-grid">
        <TokenLimitsPanel client={client} onUpdateTokenLimits={onUpdateTokenLimits} />
        <Panel title="Install and policy state">
          <KeyValue label="Client token limit" value={client.token_limit} />
          <KeyValue label="Session token limit" value={client.session_token_limit} />
          <KeyValue label="Panel password" value={panelPasswordLabel(client)} />
          <KeyValue label="Panel credential" value="Separate from CRM admin token" />
          <KeyValue label="Widget status" value={client.status} />
          <KeyValue label="Crawler status" value={client.last_crawl_status || 'not_started'} />
          <KeyValue label="Lifecycle" value={automationLocked ? 'Available discovery' : 'Current client'} />
          <KeyValue label="Installer" value="Universal script from Adapter workspace" />
        </Panel>
      </div>
      <section className="card danger-zone">
        <div className="card-header">
          <h3>Danger zone</h3>
          <span className="card-meta">Destructive actions</span>
        </div>
        <div className="flex flex-wrap gap-2">
          <Button variant="danger" icon={Trash2} onClick={() => onRemoveClient(client.site_id)}>
            Remove client
          </Button>
          <Button variant="danger" icon={KeyRound} onClick={() => onOpenPasswordDialog(client)}>
            Manage password revoke
          </Button>
        </div>
      </section>
    </div>
  );
}

function TokenLimitsPanel({
  client,
  onUpdateTokenLimits,
}: {
  client: Client;
  onUpdateTokenLimits: (siteId: string, tokenLimit: number, sessionTokenLimit: number) => Promise<void>;
}) {
  const [tokenLimit, setTokenLimit] = useState(String(client.token_limit ?? client.quota.client.limit ?? 5000));
  const [sessionTokenLimit, setSessionTokenLimit] = useState(
    String(client.session_token_limit ?? client.quota.session.limit ?? 1000),
  );
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState('');

  useEffect(() => {
    setTokenLimit(String(client.token_limit ?? client.quota.client.limit ?? 5000));
    setSessionTokenLimit(String(client.session_token_limit ?? client.quota.session.limit ?? 1000));
    setMessage('');
  }, [client.site_id, client.token_limit, client.session_token_limit, client.quota.client.limit, client.quota.session.limit]);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const nextTokenLimit = Number(tokenLimit);
    const nextSessionTokenLimit = Number(sessionTokenLimit);
    if (!Number.isInteger(nextTokenLimit) || nextTokenLimit < 1) {
      setMessage('Client token limit must be a positive whole number.');
      return;
    }
    if (!Number.isInteger(nextSessionTokenLimit) || nextSessionTokenLimit < 1) {
      setMessage('Session token limit must be a positive whole number.');
      return;
    }
    if (nextSessionTokenLimit > nextTokenLimit) {
      setMessage('Session token limit cannot be greater than the client token limit.');
      return;
    }

    setSaving(true);
    setMessage('');
    try {
      await onUpdateTokenLimits(client.site_id, nextTokenLimit, nextSessionTokenLimit);
      setMessage('Saved.');
    } catch (error) {
      setMessage(error instanceof Error ? error.message : 'Token limit update failed.');
    } finally {
      setSaving(false);
    }
  }

  return (
    <Panel title="Token limits">
      <form className="grid gap-3" onSubmit={submit}>
        <div className="grid gap-3 md:grid-cols-2">
          <Field
            label="Client total token limit"
            type="number"
            min={1}
            step={1}
            value={tokenLimit}
            onChange={(event: ChangeEvent<HTMLInputElement>) => setTokenLimit(event.currentTarget.value)}
            onBlur={() => setTokenLimit(normalizePositiveInteger(tokenLimit))}
          />
          <Field
            label="Per visitor/session limit"
            type="number"
            min={1}
            step={1}
            value={sessionTokenLimit}
            onChange={(event: ChangeEvent<HTMLInputElement>) => setSessionTokenLimit(event.currentTarget.value)}
            onBlur={() => setSessionTokenLimit(normalizePositiveInteger(sessionTokenLimit))}
          />
        </div>
        <div className="grid gap-4 sm:grid-cols-3 py-2">
          <div className="flex flex-col gap-1 border-b border-line pb-2 sm:border-0 sm:pb-0">
            <span className="text-xs text-muted">Used</span>
            <strong className="text-lg text-ink">{client.quota.client.used}</strong>
          </div>
          <div className="flex flex-col gap-1 border-b border-line pb-2 sm:border-0 sm:pb-0">
            <span className="text-xs text-muted">Remaining</span>
            <strong className="text-lg text-ink">{client.quota.client.remaining}</strong>
          </div>
          <div className="flex flex-col gap-1">
            <span className="text-xs text-muted">Session remaining</span>
            <strong className="text-lg text-ink">{client.quota.session.remaining}</strong>
          </div>
        </div>
        <div className="flex flex-wrap items-center gap-3">
          <Button type="submit" disabled={saving}>
            {saving ? 'Saving...' : 'Save token limits'}
          </Button>
          {message ? <span className="text-sm text-muted">{message}</span> : null}
        </div>
      </form>
    </Panel>
  );
}

function MetricCard({
  label,
  value,
  detail,
  onClick,
}: {
  label: string;
  value: string | number;
  detail: string;
  onClick?: () => void;
}) {
  const content = (
    <>
      <span className="text-xs font-semibold text-muted">{label}</span>
      <strong className="mt-2 block truncate text-2xl font-semibold">{typeof value === 'number' ? number(value) : value}</strong>
      <small className="mt-1 block text-xs text-muted">{detail}</small>
    </>
  );
  if (onClick) {
    return (
      <button className="card interactive text-left" type="button" onClick={onClick}>
        {content}
      </button>
    );
  }
  return <div className="card">{content}</div>;
}

export function MiniMetric({ label, value, onClick }: { label: string; value: number; onClick?: () => void }) {
  const content = (
    <>
      <span className="text-xs text-muted">{label}</span>
      <strong className="mt-1 block text-xl">{number(value)}</strong>
    </>
  );
  if (onClick) {
    return (
      <button className="mini-metric interactive" type="button" onClick={onClick}>
        {content}
      </button>
    );
  }
  return (
    <div className="mini-metric">
      {content}
    </div>
  );
}

function KeyValue({ label, value }: { label: string; value: string | number | null | undefined }) {
  return (
    <div className="grid grid-cols-[130px_minmax(0,1fr)] gap-3 border-b border-line py-2 text-sm last:border-b-0">
      <span className="text-muted">{label}</span>
      <strong className="min-w-0 overflow-wrap-anywhere">{value == null || value === '' ? '-' : value}</strong>
    </div>
  );
}

function ClientPanelShareBlock({
  client,
  panelUrl,
  onOpenPasswordDialog,
}: {
  client: Client;
  panelUrl: string;
  onOpenPasswordDialog: (client: Client) => void;
}) {
  const [copied, setCopied] = useState<'url' | 'site' | 'handoff' | ''>('');
  const passwordLabel = panelPasswordLabel(client);
  const passwordShareText =
    passwordLabel === 'configured'
      ? 'Use the panel password set in CRM'
      : 'Set or reset the panel password in CRM before sharing';
  const handoffText = [
    `Client panel: ${panelUrl}`,
    `Site ID: ${client.site_id}`,
    `Password: ${passwordShareText}`,
  ].join('\n');

  async function copyValue(kind: 'url' | 'site' | 'handoff', value: string) {
    await navigator.clipboard?.writeText(value);
    setCopied(kind);
  }

  return (
    <div className="client-panel-share">
      <div className="client-panel-share-grid">
        <div className="client-panel-share-item">
          <span>Panel URL</span>
          <code>{panelUrl}</code>
          <Button type="button" variant="ghost" size="sm" icon={copied === 'url' ? CheckCircle2 : Copy} onClick={() => copyValue('url', panelUrl)}>
            {copied === 'url' ? 'Copied' : 'Copy URL'}
          </Button>
        </div>
        <div className="client-panel-share-item">
          <span>Site ID</span>
          <code>{client.site_id}</code>
          <Button type="button" variant="ghost" size="sm" icon={copied === 'site' ? CheckCircle2 : Copy} onClick={() => copyValue('site', client.site_id)}>
            {copied === 'site' ? 'Copied' : 'Copy ID'}
          </Button>
        </div>
        <div className="client-panel-share-item">
          <span>Password</span>
          <strong>{passwordLabel}</strong>
          <Button type="button" variant="ghost" size="sm" icon={KeyRound} onClick={() => onOpenPasswordDialog(client)}>
            Manage
          </Button>
        </div>
      </div>
      <div className="client-panel-share-actions">
        <a href={panelUrl} target="_blank" rel="noopener noreferrer" className="btn btn-secondary">
          <Eye size={14} aria-hidden="true" /> Open panel
        </a>
        <Button type="button" variant="ghost" icon={copied === 'handoff' ? CheckCircle2 : Copy} onClick={() => copyValue('handoff', handoffText)}>
          {copied === 'handoff' ? 'Copied' : 'Copy handoff'}
        </Button>
      </div>
    </div>
  );
}

function Meter({ label, value, tone }: { label: string; value: number; tone: 'accent' | 'danger' }) {
  return (
    <div className="grid gap-2">
      <div className="flex items-center justify-between gap-3 text-sm">
        <span className="text-muted">{label}</span>
        <strong>{number(value)}%</strong>
      </div>
      <div className={`meter meter-${tone}`}>
        <span style={{ width: `${Math.max(0, Math.min(100, value))}%` }} />
      </div>
    </div>
  );
}

function SkeletonCard({ height = 120 }: { height?: number }) {
  return <div className="skeleton" style={{ height, borderRadius: 'var(--radius)' }} />;
}

function normalizeCatalogProduct(product: CatalogProduct | ProductPreview, index: number): DisplayProduct {
  const productId = 'product_id' in product ? product.product_id : undefined;
  const id = String(product.id ?? productId ?? `product-${index}`);
  const category = firstText(product.category_name, product.category, 'Uncategorized');
  return {
    id,
    name: firstText(product.name, `Product ${index + 1}`),
    brand: firstText(product.brand, ''),
    category,
    description: 'description' in product ? firstText(product.description, '') : '',
    price: Number(product.price ?? 0),
    stock: typeof product.stock === 'number' ? product.stock : null,
    imageUrl: firstText(product.image_url, ''),
    vectorized: 'has_embedding' in product ? Boolean(product.has_embedding) : true,
    rating: 'rating' in product && typeof product.rating === 'number' ? product.rating : null,
    reviewCount: 'review_count' in product && typeof product.review_count === 'number' ? product.review_count : null,
  };
}

function uniqueProductCategories(products: DisplayProduct[]) {
  return Array.from(new Set(products.map((product) => product.category).filter(Boolean))).sort((left, right) =>
    left.localeCompare(right),
  );
}

function productCategoryCounts(products: DisplayProduct[]) {
  return products.reduce<Record<string, number>>((counts, product) => {
    const category = product.category || 'Uncategorized';
    counts[category] = (counts[category] ?? 0) + 1;
    return counts;
  }, {});
}

function filterProducts(products: DisplayProduct[], query: string, category: string, vectorFilter: string) {
  const search = query.trim().toLowerCase();
  return products.filter((product) => {
    const matchesSearch =
      !search ||
      [product.name, product.brand, product.category, product.description].some((value) =>
        value.toLowerCase().includes(search),
      );
    const matchesCategory = category === 'all' || product.category === category;
    const matchesVector =
      vectorFilter === 'all' ||
      (vectorFilter === 'vectorized' && product.vectorized) ||
      (vectorFilter === 'pending' && !product.vectorized) ||
      (vectorFilter === 'in_stock' && (product.stock ?? 0) > 0) ||
      (vectorFilter === 'out_of_stock' && product.stock === 0);
    return matchesSearch && matchesCategory && matchesVector;
  });
}

function firstText(...values: Array<string | number | null | undefined>) {
  for (const value of values) {
    const text = String(value ?? '').trim();
    if (text) return text;
  }
  return '';
}

type IntegrationStageStatus = 'ok' | 'running' | 'pending' | 'skipped' | 'failed' | 'unknown';

interface IntegrationStageRow {
  name: string;
  label: string;
  status: IntegrationStageStatus;
  message: string;
  detail: string;
  raw: Record<string, unknown>;
}

interface IntegrationGap {
  severity: 'high' | 'medium' | 'low';
  title: string;
  detail: string;
}

interface IntegrationSmokeTest {
  name: string;
  prompt: string;
  status: IntegrationStageStatus;
  expectedActions: string[];
  actualActions: string[];
  matchedActions: string[];
  expectedResponseTerms: string[];
  matchedResponseTerms: string[];
  requiredResponseTerms: string[];
  matchedRequiredResponseTerms: string[];
  displayActionEvidence: Record<string, unknown>[];
  retrievalEvidence: Record<string, unknown>;
  intent: string;
  responseExcerpt: string;
  failureKind: string;
  reason: string;
  recommendedFix: string;
}

const EXPECTED_INTEGRATION_STAGES = [
  {
    name: 'crawl',
    label: 'Content crawl',
    pending: 'No completed crawl stage is saved yet.',
    detail: 'Collects source pages, catalog rows, policy records, and knowledge records.',
  },
  {
    name: 'flow_discovery',
    label: 'Flow discovery',
    pending: 'No flow graph is saved yet.',
    detail: 'Finds routes, buttons, forms, fields, navigation paths, and possible adapter actions.',
  },
  {
    name: 'flow_rehearsal',
    label: 'Flow rehearsal',
    pending: 'No action rehearsal is saved yet.',
    detail: 'Safely checks whether discovered actions can run without completing high-risk final steps.',
  },
  {
    name: 'flow_regression',
    label: 'Regression check',
    pending: 'No baseline comparison is saved yet.',
    detail: 'Compares current routes/actions against the previous setup picture.',
  },
  {
    name: 'readiness_scan',
    label: 'Readiness scan',
    pending: 'No readiness evidence is saved yet.',
    detail: 'Summarizes platform, source coverage, supported actions, and automation gaps.',
  },
  {
    name: 'assistant_smoke_tests',
    label: 'Assistant smoke tests',
    pending: 'No assistant prompt smoke tests are saved yet.',
    detail: 'Runs real text prompts through Maya and verifies expected UI actions so CRM catches no-record or no-action failures.',
  },
];

function integrationStageRows(
  initialization: Record<string, unknown>,
  evidence: {
    crawlReport: CrawlReport | null;
    flow: Record<string, unknown>;
    rehearsal: Record<string, unknown>;
    regression: Record<string, unknown>;
    scanReport: ReadinessReport | null;
  },
): IntegrationStageRow[] {
  const savedStages = Array.isArray(initialization.stages)
    ? initialization.stages.filter((stage): stage is Record<string, unknown> => Boolean(stage) && typeof stage === 'object')
    : [];
  return EXPECTED_INTEGRATION_STAGES.map((expected) => {
    const saved = savedStages.find((stage) => String(stage.name || '') === expected.name);
    if (saved) {
      return {
        name: expected.name,
        label: expected.label,
        status: integrationStageStatus(saved.status),
        message: String(saved.message || expected.pending),
        detail: integrationStageDetail(expected.name, saved, expected.detail),
        raw: saved,
      };
    }
    const inferred = inferredIntegrationStage(expected.name, evidence);
    return {
      name: expected.name,
      label: expected.label,
      status: inferred.status,
      message: inferred.message || expected.pending,
      detail: inferred.detail || expected.detail,
      raw: {},
    };
  });
}

function liveIntegrationStageRows(stages: IntegrationStageRow[], autoIntegrating: boolean): IntegrationStageRow[] {
  if (!autoIntegrating || stages.some((stage) => stage.status === 'running')) return stages;
  return [
    {
      name: 'integration_queue',
      label: 'Backend queue',
      status: 'running',
      message: 'Setup run request accepted.',
      detail: 'Waiting for the first saved backend stage report; existing evidence below stays visible until replaced.',
      raw: {},
    },
    ...stages,
  ];
}

function inferredIntegrationStage(
  name: string,
  evidence: {
    crawlReport: CrawlReport | null;
    flow: Record<string, unknown>;
    rehearsal: Record<string, unknown>;
    regression: Record<string, unknown>;
    scanReport: ReadinessReport | null;
  },
): Pick<IntegrationStageRow, 'status' | 'message' | 'detail'> {
  if (name === 'crawl' && evidence.crawlReport) {
    return {
      status: 'ok',
      message: `${number(evidence.crawlReport.product_count)} records from ${number(evidence.crawlReport.pages_visited)} visited pages.`,
      detail: `${number(evidence.crawlReport.pages_failed)} failed pages, ${percent(evidence.crawlReport.coverage_score)}% coverage.`,
    };
  }
  if (name === 'flow_discovery' && Object.keys(evidence.flow).length) {
    const summary = safeRecord(evidence.flow.summary);
    return {
      status: 'ok',
      message: flowSummaryText(summary),
      detail: `Engine: ${String(evidence.flow.engine || 'flow discovery')}.`,
    };
  }
  if (name === 'flow_rehearsal' && Object.keys(evidence.rehearsal).length) {
    return {
      status: 'ok',
      message: rehearsalSummaryText(safeRecord(evidence.rehearsal.summary)),
      detail: `Steps: ${Array.isArray(evidence.rehearsal.steps) ? evidence.rehearsal.steps.length : 0}.`,
    };
  }
  if (name === 'flow_regression' && Object.keys(evidence.regression).length) {
    return {
      status: 'ok',
      message: regressionSummaryText(evidence.regression.status, safeRecord(evidence.regression.summary)),
      detail: `Compared: ${String(evidence.regression.compared_at || '-')}.`,
    };
  }
  if (name === 'readiness_scan' && evidence.scanReport) {
    const supported = evidence.scanReport.capabilities.filter((capability) => capability.supported).length;
    return {
      status: 'ok',
      message: `${supported}/${evidence.scanReport.capabilities.length} checks supported.`,
      detail: `${evidence.scanReport.platform || 'unknown'} at ${percent(evidence.scanReport.platform_confidence)}% confidence.`,
    };
  }
  return { status: 'pending', message: '', detail: '' };
}

function integrationStageStatus(value: unknown): IntegrationStageStatus {
  const status = String(value || '').toLowerCase();
  if (status === 'ok') return 'ok';
  if (status === 'running') return 'running';
  if (status === 'skipped') return 'skipped';
  if (status === 'failed' || status === 'error') return 'failed';
  if (status === 'pending') return 'pending';
  return 'unknown';
}

function integrationStageDetail(name: string, stage: Record<string, unknown>, fallback: string) {
  if (name === 'flow_discovery') {
    const summary = safeRecord(stage.summary);
    if (Object.keys(summary).length) return flowSummaryText(summary);
  }
  if (name === 'flow_rehearsal') {
    const summary = safeRecord(stage.summary);
    if (Object.keys(summary).length) return rehearsalSummaryText(summary);
  }
  if (name === 'readiness_scan') {
    const supported = Number(stage.supported ?? 0);
    const total = Number(stage.total ?? 0);
    if (total) return `${supported}/${total} readiness checks supported.`;
  }
  if (name === 'assistant_smoke_tests') {
    const passed = Number(stage.passed ?? 0);
    const total = Number(stage.total ?? 0);
    const failed = Number(stage.failed ?? 0);
    if (total) return `${passed}/${total} prompts passed${failed ? `, ${failed} failed` : ''}.`;
  }
  if (stage.regression_status) return `Regression status: ${String(stage.regression_status)}.`;
  if (stage.started_at && integrationStageStatus(stage.status) === 'running') return `Started ${shortTime(String(stage.started_at))}.`;
  if (stage.completed_at) return `Completed ${shortTime(String(stage.completed_at))}.`;
  return fallback;
}

function integrationInitializationSummary(initialization: Record<string, unknown>, autoIntegrating = false) {
  const status = String(initialization.status || '').trim();
  const stages = Array.isArray(initialization.stages)
    ? initialization.stages.filter((stage): stage is Record<string, unknown> => Boolean(stage) && typeof stage === 'object')
    : [];
  if (autoIntegrating && status !== 'running') {
    const existing = status || (stages.length ? 'previous evidence saved' : 'not started');
    return `running now - ${existing}`;
  }
  if (!status && !stages.length) return 'not started';
  const failed = stages.filter((stage) => integrationStageStatus(stage.status) === 'failed').length;
  const completed = stages.filter((stage) => integrationStageStatus(stage.status) === 'ok').length;
  const stageText = stages.length ? `${completed}/${stages.length} stages${failed ? `, ${failed} failed` : ''}` : '';
  return `${status || 'unknown'}${stageText ? ` - ${stageText}` : ''}`;
}

function currentIntegrationStageLabel(stages: IntegrationStageRow[]) {
  const running = stages.find((stage) => stage.status === 'running');
  if (running) return running.label;
  const failed = stages.find((stage) => stage.status === 'failed');
  if (failed) return `${failed.label} failed`;
  const pending = stages.find((stage) => stage.status === 'pending' || stage.status === 'unknown');
  return pending ? `${pending.label} pending` : 'complete';
}

function flowSummaryText(summary: Record<string, unknown>) {
  const pages = Number(summary.pages ?? 0);
  const actions = Number(summary.actions ?? 0);
  if (!pages && !actions) return 'pending';
  return `${number(pages)} pages, ${number(actions)} actions`;
}

function rehearsalSummaryText(summary: Record<string, unknown>) {
  const total = Number(summary.total ?? 0);
  const supported = Number(summary.supported ?? 0);
  const blocked = Number(summary.blocked ?? 0);
  if (!total) return 'pending';
  return `${number(supported)}/${number(total)} supported${blocked ? `, ${number(blocked)} blocked` : ''}`;
}

function regressionSummaryText(status: unknown, summary: Record<string, unknown>) {
  const changes = Number(summary.changes ?? 0);
  const high = Number(summary.high ?? 0);
  const medium = Number(summary.medium ?? 0);
  const statusText = String(status || '');
  if (summary.baseline) return 'baseline saved';
  if (!statusText && !Object.keys(summary).length) return 'pending';
  if (!changes) return statusText || 'stable';
  return `${number(changes)} change${changes === 1 ? '' : 's'} (${number(high)} high, ${number(medium)} medium)`;
}

function integrationScore(
  client: Client,
  capabilities: CapabilitiesSummary | null,
  stages: IntegrationStageRow[],
  flow: Record<string, unknown>,
  rehearsal: Record<string, unknown>,
  actionHealth: Record<string, unknown>,
  smokeTests: IntegrationSmokeTest[] = [],
) {
  const checks = [
    client.status !== 'available',
    client.catalog.active_products > 0,
    client.catalog.active_products === 0 || client.catalog.missing_embeddings < client.catalog.active_products,
    stages.some((stage) => stage.name === 'crawl' && stage.status === 'ok'),
    Object.keys(flow).length > 0,
    Object.keys(rehearsal).length > 0,
    Boolean(capabilities && capabilities.supported.length > 0),
    Boolean(capabilities && capabilities.unsupported.length === 0),
    smokeTests.length > 0 && smokeTests.every((test) => test.status === 'ok'),
    Number(safeRecord(actionHealth.summary).needs_repair ?? 0) === 0,
    Boolean(client.panel_password_configured),
  ];
  const ready = checks.filter(Boolean).length;
  return Math.round((ready / checks.length) * 100);
}

function integrationGaps(
  client: Client,
  capabilities: CapabilitiesSummary | null,
  stages: IntegrationStageRow[],
  flow: Record<string, unknown>,
  actionHealth: Record<string, unknown>,
  actionPolicy: Record<string, unknown>,
  automationLocked: boolean,
  smokeTests: IntegrationSmokeTest[] = [],
): IntegrationGap[] {
  const gaps: IntegrationGap[] = [];
  if (automationLocked) {
    gaps.push({
      severity: 'high',
      title: 'Client is still Available',
      detail: 'Move it to Current before setup. This action only changes lifecycle state; it does not start crawling.',
    });
  }
  if (!stages.some((stage) => stage.status === 'ok')) {
    gaps.push({
      severity: 'high',
      title: 'No setup run evidence',
      detail: 'Run setup to produce crawl, flow, rehearsal, regression, and readiness evidence.',
    });
  }
  if (client.catalog.active_products <= 0) {
    gaps.push({
      severity: 'high',
      title: 'No active records',
      detail: 'The assistant cannot compare or recommend reliably until crawl/data sync loads source records.',
    });
  }
  if (client.catalog.missing_embeddings > 0) {
    gaps.push({
      severity: 'medium',
      title: 'Vector sync is incomplete',
      detail: `${number(client.catalog.missing_embeddings)} records are missing embeddings, so retrieval may miss relevant records.`,
    });
  }
  if (!Object.keys(flow).length) {
    gaps.push({
      severity: 'medium',
      title: 'No flow graph',
      detail: 'Navigation, forms, and action routing are not fully mapped yet. Run setup or Discover flows.',
    });
  }
  const failedSmokeTests = smokeTests.filter((test) => test.status === 'failed');
  if (failedSmokeTests.length) {
    gaps.push({
      severity: 'high',
      title: 'Assistant smoke tests failed',
      detail: `${failedSmokeTests.length} real prompt(s) failed. First failure: ${failedSmokeTests[0].reason || failedSmokeTests[0].prompt}`,
    });
  } else if (!automationLocked && !smokeTests.length) {
    gaps.push({
      severity: 'medium',
      title: 'Assistant smoke tests have not run',
      detail: 'Run prompt tests so CRM verifies comparison, sorting, navigation, and recommendation prompts instead of relying on visual readiness alone.',
    });
  }
  const unsupported = capabilities?.unsupported ?? [];
  if (unsupported.length) {
    gaps.push({
      severity: 'medium',
      title: 'Readiness has unsupported checks',
      detail: `${unsupported.length} check(s) still need automation or a safer handoff rule: ${unsupported.slice(0, 5).join(', ')}.`,
    });
  }
  const needsRepair = Number(safeRecord(actionHealth.summary).needs_repair ?? 0);
  if (needsRepair > 0) {
    gaps.push({
      severity: 'high',
      title: 'Runtime action failures need repair',
      detail: `${needsRepair} action(s) need selector, route, or policy repair from recent runtime evidence.`,
    });
  }
  const blocked = stringArray(actionPolicy.blocked_actions);
  if (blocked.length) {
    gaps.push({
      severity: 'low',
      title: 'Some actions require handoff',
      detail: `${blocked.slice(0, 5).join(', ')} are intentionally blocked by policy or provider constraints.`,
    });
  }
  if (!client.panel_password_configured) {
    gaps.push({
      severity: 'medium',
      title: 'Client panel password is not configured',
      detail: 'Set or generate a panel password before sharing the client-facing analytics panel.',
    });
  }
  return gaps;
}

function integrationFixes(gaps: IntegrationGap[], vertical: CrmVerticalDefinition) {
  if (!gaps.length) {
    return [
      {
        kind: 'ok',
        title: 'Run real prompt smoke tests',
        detail: `Use the prompts below to verify comparison, navigation, recommendations, and ${vertical.entityLabelPlural} retrieval after every site change.`,
      },
    ];
  }
  return gaps.slice(0, 6).map((gap) => ({
    kind: gap.severity,
    title: fixTitleForGap(gap.title),
    detail: fixDetailForGap(gap.title),
  }));
}

function fixTitleForGap(title: string) {
  if (title.includes('Available')) return 'Move to Current, then run setup';
  if (title.includes('smoke tests')) return 'Repair prompt, retrieval, or adapter action mapping';
  if (title.includes('records')) return 'Refresh crawl/data sync';
  if (title.includes('Vector')) return 'Run crawl or vector sync';
  if (title.includes('flow')) return 'Run flow discovery and rehearsal';
  if (title.includes('Readiness')) return 'Run setup and inspect unsupported checks';
  if (title.includes('action failures')) return 'Approve or repair adapter proposals';
  if (title.includes('panel password')) return 'Generate a client panel password';
  return 'Review the setup evidence';
}

function fixDetailForGap(title: string) {
  if (title.includes('Available')) return 'Use Add to current first. Then the setup run will crawl, discover flows, rehearse actions, and rescan readiness.';
  if (title.includes('smoke tests')) return 'Open the smoke-test panel below, compare expected vs actual actions, then inspect Data storage, Prompt profile, and Adapter evidence for the failing prompt.';
  if (title.includes('records')) return 'Confirm the source website is live, then run setup. If records stay empty, inspect Data storage and Crawl report.';
  if (title.includes('Vector')) return 'Run a crawl so missing embeddings can be refreshed for retrieval.';
  if (title.includes('flow')) return 'Open Adapter evidence after the setup run to review routes, selectors, barriers, and repair proposals.';
  if (title.includes('Readiness')) return 'Unsupported checks explain what is not automated and whether it needs a custom adapter or handoff.';
  if (title.includes('action failures')) return 'Use Adapter evidence to approve safe repairs or keep provider-gated actions as handoff-only.';
  if (title.includes('panel password')) return 'Use Manage password before sharing the Client Panel URL.';
  return 'Open the related tab listed below and inspect the saved evidence.';
}

function nextIntegrationAction(gaps: IntegrationGap[], automationLocked: boolean, autoIntegrating: boolean) {
  if (automationLocked) return 'Move client to Current; activation will not crawl or run setup.';
  if (autoIntegrating) return 'Wait for backend stage evidence to refresh.';
  const high = gaps.find((gap) => gap.severity === 'high');
  if (high) return high.title;
  const medium = gaps.find((gap) => gap.severity === 'medium');
  if (medium) return medium.title;
  if (gaps.length) return gaps[0].title;
  return 'Run real browser prompts after any website layout or catalog change.';
}

function actionHealthSummary(actionHealth: Record<string, unknown>) {
  const summary = safeRecord(actionHealth.summary);
  if (!Object.keys(summary).length) return 'no runtime failures reported';
  return `${number(Number(summary.tracked ?? 0))} tracked, ${number(Number(summary.needs_repair ?? 0))} need repair`;
}

function assistantSmokeSummary(
  stages: IntegrationStageRow[],
  standaloneReport: Record<string, unknown>,
  preferStandalone = false,
) {
  const stage = stages.find((item) => item.name === 'assistant_smoke_tests');
  const standaloneHasTests = Array.isArray(standaloneReport.tests) && standaloneReport.tests.length > 0;
  const source = preferStandalone && standaloneHasTests ? standaloneReport : stage ? stage.raw : standaloneReport;
  if (!Object.keys(source).length) return 'not run';
  const status = String(source.status || 'unknown');
  const passed = Number(source.passed ?? 0);
  const total = Number(source.total ?? 0);
  const failed = Number(source.failed ?? 0);
  const mode = source === standaloneReport ? 'quick run' : 'setup run';
  if (!total) return `${status} from ${mode}`;
  return `${passed}/${total} passed${failed ? `, ${failed} failed` : ''} from ${mode}`;
}

function integrationSmokeTests(
  stages: IntegrationStageRow[],
  standaloneReport: Record<string, unknown> = {},
  preferStandalone = false,
): IntegrationSmokeTest[] {
  const stage = stages.find((item) => item.name === 'assistant_smoke_tests');
  const standaloneTests: unknown[] = Array.isArray(standaloneReport.tests) ? standaloneReport.tests : [];
  const stageTests: unknown[] = Array.isArray(stage?.raw.tests) ? stage.raw.tests : [];
  const rawTests = preferStandalone && standaloneTests.length ? standaloneTests : stageTests.length ? stageTests : standaloneTests;
  return rawTests
    .filter((item): item is Record<string, unknown> => Boolean(item) && typeof item === 'object')
    .map((item) => ({
      name: String(item.name || item.prompt || 'smoke_test'),
      prompt: String(item.prompt || item.name || 'Prompt smoke test'),
      status: integrationStageStatus(item.status),
      expectedActions: stringArray(item.expected_actions),
      actualActions: stringArray(item.actual_actions),
      matchedActions: stringArray(item.matched_actions),
      expectedResponseTerms: stringArray(item.expected_response_terms_any),
      matchedResponseTerms: stringArray(item.matched_response_terms),
      requiredResponseTerms: stringArray(item.expected_response_terms_all),
      matchedRequiredResponseTerms: stringArray(item.matched_response_terms_all),
      displayActionEvidence: recordArray(item.display_action_evidence),
      retrievalEvidence: safeRecord(item.retrieval_evidence),
      intent: String(item.intent || ''),
      responseExcerpt: String(item.response_excerpt || ''),
      failureKind: String(item.failure_kind || ''),
      reason: String(item.reason || ''),
      recommendedFix: String(item.recommended_fix || ''),
    }));
}

function SmokeTestEvidence({ test }: { test: IntegrationSmokeTest }) {
  return (
    <div className="smoke-evidence-grid">
      <SmokeEvidenceLine label="Expected actions" value={test.expectedActions.join(', ') || 'none'} />
      <SmokeEvidenceLine label="Actual actions" value={test.actualActions.join(', ') || 'none'} />
      <SmokeEvidenceLine label="Matched actions" value={test.matchedActions.join(', ') || 'none'} tone={test.matchedActions.length ? 'ok' : 'warn'} />
      <SmokeEvidenceLine label="Intent" value={test.intent || 'unknown'} />
      <SmokeEvidenceLine label="Failure kind" value={test.failureKind || 'none'} tone={test.failureKind ? 'bad' : 'ok'} />
      <SmokeEvidenceLine label="Action IDs" value={displayActionEvidenceSummary(test.displayActionEvidence) || 'no display action IDs captured'} tone={test.displayActionEvidence.length ? 'ok' : 'warn'} />
      <SmokeEvidenceLine label="Data evidence" value={smokeRetrievalEvidenceSummary(test.retrievalEvidence) || 'no retrieval evidence saved'} tone={smokeRetrievalTone(test.retrievalEvidence)} />
      <SmokeEvidenceLine label="Response terms" value={smokeResponseTermsSummary(test)} tone={smokeResponseTermsTone(test)} />
      <SmokeEvidenceLine label="Fix" value={test.recommendedFix || 'No fix needed from this smoke result.'} tone={test.recommendedFix ? 'warn' : 'ok'} />
      {test.responseExcerpt ? <SmokeEvidenceLine label="Response excerpt" value={test.responseExcerpt} wide /> : null}
    </div>
  );
}

function SmokeEvidenceLine({
  label,
  value,
  tone = 'neutral',
  wide = false,
}: {
  label: string;
  value: string;
  tone?: 'ok' | 'warn' | 'bad' | 'neutral';
  wide?: boolean;
}) {
  return (
    <div className={`smoke-evidence-line smoke-evidence-${tone}${wide ? ' smoke-evidence-wide' : ''}`}>
      <span>{label}</span>
      <b>{value}</b>
    </div>
  );
}

function smokeTestHeadline(test: IntegrationSmokeTest) {
  if (test.reason) return test.reason;
  if (test.status === 'ok') return 'Passed: expected actions, action IDs, data retrieval, and response checks are aligned.';
  return 'Needs review: compare the expected action, retrieved data, action IDs, and response text below.';
}

function smokeResponseTermsSummary(test: IntegrationSmokeTest) {
  const parts = [];
  if (test.expectedResponseTerms.length) {
    parts.push(`any: expected ${test.expectedResponseTerms.join(', ')}; matched ${test.matchedResponseTerms.join(', ') || 'none'}`);
  }
  if (test.requiredResponseTerms.length) {
    parts.push(`all: expected ${test.requiredResponseTerms.join(', ')}; matched ${test.matchedRequiredResponseTerms.join(', ') || 'none'}`);
  }
  return parts.join(' / ') || 'no response term check configured';
}

function smokeResponseTermsTone(test: IntegrationSmokeTest): 'ok' | 'warn' | 'neutral' {
  const anyOk = !test.expectedResponseTerms.length || test.matchedResponseTerms.length > 0;
  const allOk = !test.requiredResponseTerms.length || test.matchedRequiredResponseTerms.length >= test.requiredResponseTerms.length;
  if (!test.expectedResponseTerms.length && !test.requiredResponseTerms.length) return 'neutral';
  return anyOk && allOk ? 'ok' : 'warn';
}

function smokeRetrievalTone(evidence: Record<string, unknown>): 'ok' | 'warn' | 'bad' | 'neutral' {
  if (!Object.keys(evidence).length) return 'warn';
  const issue = String(evidence.issue || '').toLowerCase();
  if (issue === 'ok') return 'ok';
  if (issue === 'no_active_records' || issue === 'retrieval_returned_zero' || issue === 'all_vectors_missing') return 'bad';
  return 'warn';
}

function displayActionEvidenceSummary(items: Record<string, unknown>[]) {
  return items.map((item) => {
    const action = String(item.action || 'action');
    const idParam = String(item.id_param || 'ids');
    const count = Number(item.id_count ?? 0);
    const ids = stringArray(item.ids).slice(0, 3).join(', ');
    return `${action}: ${number(count)} ${idParam}${ids ? ` (${ids})` : ''}`;
  }).join(' / ');
}

function smokeRetrievalEvidenceSummary(evidence: Record<string, unknown>) {
  if (!Object.keys(evidence).length) return '';
  const source = String(evidence.source || 'records');
  const retrieved = Number(evidence.retrieved_count ?? 0);
  const active = Number(evidence.active_records ?? 0);
  const missing = Number(evidence.missing_embeddings ?? 0);
  const issue = labelize(String(evidence.issue || 'unknown'));
  const titles = stringArray(evidence.retrieved_titles).slice(0, 3).join(', ');
  const summary = `${number(retrieved)} retrieved / ${number(active)} active ${source}; ${number(missing)} missing vectors; issue: ${issue}`;
  return titles ? `${summary}; samples: ${titles}` : summary;
}

function stringArray(value: unknown) {
  return Array.isArray(value) ? value.map((item) => String(item || '').trim()).filter(Boolean) : [];
}

function recordArray(value: unknown): Record<string, unknown>[] {
  return Array.isArray(value) ? value.map(safeRecord).filter((item) => Object.keys(item).length > 0) : [];
}

function safeRecord(value: unknown): Record<string, unknown> {
  return value && typeof value === 'object' && !Array.isArray(value) ? value as Record<string, unknown> : {};
}

function isExtensionTab(tab: ClientWorkspaceTabId) {
  return !CORE_CLIENT_TAB_IDS.has(tab);
}

function activeEntityTitle(vertical: CrmVerticalDefinition) {
  const text = vertical.entityLabelPlural || 'items';
  return text.charAt(0).toUpperCase() + text.slice(1);
}

function normalizePositiveInteger(value: string) {
  const normalized = Math.max(1, Math.round(Number(value)));
  return String(Number.isFinite(normalized) ? normalized : 1);
}
