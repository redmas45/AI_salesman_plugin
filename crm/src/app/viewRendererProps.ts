import type {
  AnalyticsResponse,
  AnalyticsSectionId,
  Client,
  ClientBoardSection,
  ConversationsResponse,
  Overview,
  SettingsResponse,
  VerticalDefinition,
  View,
} from '../types';
import type { ClientWorkspaceTabId } from '../verticals/types';
import type { ViewRendererProps } from '../views/ViewRenderer';

interface ViewRendererActions {
  onActivateClient: (siteId: string) => void;
  onAddClient: () => void;
  onAutoIntegrate: (siteId: string) => void;
  onClientWorkspaceTabChange: (tabId: ClientWorkspaceTabId) => void;
  onGenerateSummary: () => void;
  onMoveClientToAvailable: (siteId: string) => void;
  onOpenAnalyticsSection: (section: AnalyticsSectionId) => void;
  onOpenClient: (siteId: string, initialTab?: ClientWorkspaceTabId) => void;
  onOpenClientBoardSection: (section: ClientBoardSection) => void;
  onOpenPasswordDialog: (client: Client) => void;
  onOpenSettings: (focusKey?: string) => void;
  onRangeChange: (range: string) => void;
  onRemoveClient: (siteId: string) => void;
  onSaveSettings: (values: Record<string, string>) => Promise<SettingsResponse>;
  onToggleClient: (siteId: string, enabled: boolean) => void;
  onTriggerCrawl: (siteId: string) => void;
  onUpdateTokenLimits: (siteId: string, tokenLimit: number, sessionTokenLimit: number) => Promise<void>;
  onViewChange: (view: View) => void;
}

interface ViewRendererState {
  analytics: AnalyticsResponse | null;
  analyticsSection: AnalyticsSectionId;
  autoIntegratingSites: Set<string>;
  busy: boolean;
  clientBoardSection: ClientBoardSection;
  clientInitialTab: ClientWorkspaceTabId;
  clientTabRequestKey: number;
  clients: Client[];
  conversations: ConversationsResponse | null;
  crawlingSites: Set<string>;
  overview: Overview;
  range: string;
  selectedClient: Client | null;
  settings: SettingsResponse | null;
  settingsFocusKey: string;
  verticals: VerticalDefinition[];
  view: View;
}

export function createViewRendererProps(
  state: ViewRendererState,
  actions: ViewRendererActions,
): ViewRendererProps {
  return {
    ...state,
    ...actions,
  };
}
