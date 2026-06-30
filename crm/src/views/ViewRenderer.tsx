import type {
  View,
  Overview,
  Client,
  ConversationsResponse,
  AnalyticsResponse,
  SettingsResponse,
  VerticalDefinition,
  ClientBoardSection,
  AnalyticsSectionId,
} from '../types';
import type { ClientWorkspaceTabId } from '../verticals/types';
import { DashboardView } from './DashboardView';
import { ClientsView } from './ClientsView';
import { ClientDetailView } from './ClientDetailView';
import { CatalogsView } from './CatalogsView';
import { UsageView } from './UsageView';
import { ConversationsView } from './ConversationsView';
import { AnalyticsView } from './AnalyticsView';
import { AdaptersView } from './AdaptersView';
import { SettingsView } from './SettingsView';
import { HealthView } from './HealthView';

export interface ViewRendererProps {
  view: View;
  overview: Overview;
  clients: Client[];
  selectedClient: Client | null;
  clientInitialTab: ClientWorkspaceTabId;
  clientTabRequestKey: number;
  clientBoardSection: ClientBoardSection;
  analyticsSection: AnalyticsSectionId;
  conversations: ConversationsResponse | null;
  analytics: AnalyticsResponse | null;
  settings: SettingsResponse | null;
  settingsFocusKey: string;
  verticals: VerticalDefinition[];
  range: string;
  busy: boolean;
  crawlingSites: Set<string>;
  autoIntegratingSites: Set<string>;
  onRangeChange: (range: string) => void;
  onViewChange: (view: View) => void;
  onOpenSettings: (focusKey?: string) => void;
  onOpenClientBoardSection: (section: ClientBoardSection) => void;
  onOpenAnalyticsSection: (section: AnalyticsSectionId) => void;
  onAddClient: () => void;
  onOpenClient: (siteId: string, initialTab?: ClientWorkspaceTabId) => void;
  onClientWorkspaceTabChange: (tabId: ClientWorkspaceTabId) => void;
  onActivateClient: (siteId: string) => void;
  onTriggerCrawl: (siteId: string) => void;
  onAutoIntegrate: (siteId: string) => void;
  onRemoveClient: (siteId: string) => void;
  onToggleClient: (siteId: string, enabled: boolean) => void;
  onUpdateTokenLimits: (siteId: string, tokenLimit: number, sessionTokenLimit: number) => Promise<void>;
  onOpenPasswordDialog: (client: Client) => void;
  onSaveSettings: (values: Record<string, string>) => Promise<SettingsResponse>;
  onGenerateSummary: () => void;
}

export function ViewRenderer(props: ViewRendererProps) {
  switch (props.view) {
    case 'clients':
      return <ClientsView {...props} />;
    case 'client-detail':
      return props.selectedClient ? (
        <ClientDetailView
          {...props}
          client={props.selectedClient}
          initialTab={props.clientInitialTab}
          onWorkspaceTabChange={props.onClientWorkspaceTabChange}
          recentActivity={props.overview.recent_activity.filter((item) => item.site_id === props.selectedClient?.site_id)}
        />
      ) : (
        <ClientsView {...props} />
      );
    case 'catalogs':
      return (
        <CatalogsView
          clients={props.clients}
          onOpenClient={props.onOpenClient}
        />
      );
    case 'usage':
      return (
        <UsageView
          clients={props.clients}
          recentActivity={props.overview.recent_activity}
          onOpenClient={props.onOpenClient}
        />
      );
    case 'conversations':
      return (
        <ConversationsView
          conversations={props.conversations}
          range={props.range}
          onRangeChange={props.onRangeChange}
          onOpenClient={props.onOpenClient}
        />
      );
    case 'analytics':
      return (
        <AnalyticsView
          analytics={props.analytics}
          range={props.range}
          activeSection={props.analyticsSection}
          onRangeChange={props.onRangeChange}
          onGenerateSummary={props.onGenerateSummary}
          onOpenClient={props.onOpenClient}
        />
      );
    case 'adapters':
      return <AdaptersView clients={props.clients} onOpenClient={props.onOpenClient} />;
    case 'settings':
      return <SettingsView settings={props.settings} focusKey={props.settingsFocusKey} onSave={props.onSaveSettings} />;
    case 'health':
      return (
        <HealthView
          health={props.overview.health}
          clients={props.clients}
          verticals={props.verticals}
          onViewChange={props.onViewChange}
          onOpenClientBoardSection={props.onOpenClientBoardSection}
        />
      );
    default:
      return <DashboardView {...props} onOpenSettings={props.onOpenSettings} />;
  }
}
