import type { RefObject } from 'react';
import type {
  CapabilitiesSummary,
  Client,
  CrawlReport,
  OperationStatusResponse,
  ReadinessReport,
  UsageEvent,
  View,
} from '../../../types';
import type {
  ClientWorkspaceTabDefinition,
  ClientWorkspaceTabId,
  CrmVerticalDefinition,
} from '../../../verticals/types';
import { AdapterTab } from '../adapter/AdapterTab';
import { ActionChipGrid } from '../components/actionChips';
import { ClientActivityTab } from './ActivityTab';
import { ClientCatalogTab } from '../catalog/CatalogTab';
import type { DisplayProduct } from '../catalog/catalogProducts';
import { ClientControlsTab } from './ControlsTab';
import { ClientCrawlTab } from './CrawlTab';
import { ClientIntegrationTab } from './IntegrationTab';
import type { OperationFeedbackState } from '../operations/OperationFeedback';
import { ClientOverviewTab } from './OverviewTab';
import { PromptTab } from './PromptTab';
import type { SmokeTestFeedbackState } from '../operations/promptSmokeModel';
import { ClientReadinessTab } from './ReadinessTab';
import { VerticalExtensionTab } from './VerticalExtensionTab';

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

export function ClientWorkspaceTabPanel({
  activeTab,
  activeTabDefinition,
  automationLocked,
  autoIntegrating,
  capabilities,
  catalogError,
  catalogLoading,
  client,
  crawlReport,
  crawling,
  displayedProducts,
  onOpenPasswordDialog,
  onOpenTab,
  onRemoveClient,
  onRunAssistantSmokeTests,
  onRunSetup,
  onToggleClient,
  onTriggerCrawl,
  onUpdateTokenLimits,
  onViewChange,
  operationFeedback,
  operationStatus,
  recentActivity,
  scanReport,
  setupOrReadinessRunning,
  smokeTestFeedback,
  smokeTesting,
  sourceReachable,
  sourceStatus,
  standaloneSmokeReport,
  tabPanelRef,
  vertical,
}: {
  activeTab: ClientWorkspaceTabId;
  activeTabDefinition: ClientWorkspaceTabDefinition;
  automationLocked: boolean;
  autoIntegrating: boolean;
  capabilities: CapabilitiesSummary | null;
  catalogError: string;
  catalogLoading: boolean;
  client: Client;
  crawlReport: CrawlReport | null;
  crawling: boolean;
  displayedProducts: DisplayProduct[];
  onOpenPasswordDialog: (client: Client) => void;
  onOpenTab: (tab: ClientWorkspaceTabId) => void;
  onRemoveClient: (siteId: string) => void;
  onRunAssistantSmokeTests: () => void | Promise<void>;
  onRunSetup: () => void;
  onToggleClient: (siteId: string, enabled: boolean) => void;
  onTriggerCrawl: () => void;
  onUpdateTokenLimits: (siteId: string, tokenLimit: number, sessionTokenLimit: number) => Promise<void>;
  onViewChange: (view: View) => void;
  operationFeedback: OperationFeedbackState | null;
  operationStatus: OperationStatusResponse | null;
  recentActivity: UsageEvent[];
  scanReport: ReadinessReport | null;
  setupOrReadinessRunning: boolean;
  smokeTestFeedback: SmokeTestFeedbackState | null;
  smokeTesting: boolean;
  sourceReachable: boolean;
  sourceStatus: string;
  standaloneSmokeReport: Record<string, unknown> | null;
  tabPanelRef: RefObject<HTMLElement | null>;
  vertical: CrmVerticalDefinition;
}) {
  return (
    <section
      id={tabPanelId(activeTab)}
      ref={tabPanelRef}
      className="client-tab-panel"
      role="region"
      aria-label={activeTabDefinition.label}
    >
      {activeTab === 'overview' ? (
        <ClientOverviewTab
          client={client}
          capabilities={capabilities}
          crawlReport={crawlReport}
          onOpenTab={onOpenTab}
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
          onRunAssistantSmokeTests={onRunAssistantSmokeTests}
          onOpenTab={onOpenTab}
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
          onRunSetup={onRunSetup}
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
          onOpenTab={onOpenTab}
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
          onTriggerCrawl={onTriggerCrawl}
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
          onOpenTab={onOpenTab}
          onViewChange={onViewChange}
        />
      ) : null}
      {isExtensionTab(activeTab) ? (
        <VerticalExtensionTab tab={activeTabDefinition} vertical={vertical} renderActions={(actions) => <ActionChipGrid actions={actions} />} />
      ) : null}
    </section>
  );
}

function tabPanelId(tabId: ClientWorkspaceTabId) {
  return `client-tab-panel-${tabId}`;
}

function isExtensionTab(tab: ClientWorkspaceTabId) {
  return !CORE_CLIENT_TAB_IDS.has(tab);
}
