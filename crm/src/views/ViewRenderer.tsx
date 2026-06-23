import type {
  View,
  Overview,
  Client,
  ConversationsResponse,
  AnalyticsResponse,
  SettingsResponse,
} from '../types';
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
  conversations: ConversationsResponse | null;
  analytics: AnalyticsResponse | null;
  settings: SettingsResponse | null;
  range: string;
  crawlingSites: Set<string>;
  onRangeChange: (range: string) => void;
  onViewChange: (view: View) => void;
  onAddClient: () => void;
  onOpenClient: (siteId: string) => void;
  onCopyScript: (client: Client) => Promise<void>;
  onTriggerCrawl: (siteId: string) => void;
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
          recentActivity={props.overview.recent_activity.filter((item) => item.site_id === props.selectedClient?.site_id)}
        />
      ) : (
        <ClientsView {...props} />
      );
    case 'catalogs':
      return (
        <CatalogsView
          clients={props.clients}
          crawlingSites={props.crawlingSites}
          onOpenClient={props.onOpenClient}
          onTriggerCrawl={props.onTriggerCrawl}
        />
      );
    case 'usage':
      return <UsageView clients={props.clients} recentActivity={props.overview.recent_activity} />;
    case 'conversations':
      return (
        <ConversationsView
          conversations={props.conversations}
          range={props.range}
          onRangeChange={props.onRangeChange}
        />
      );
    case 'analytics':
      return (
        <AnalyticsView
          analytics={props.analytics}
          range={props.range}
          onRangeChange={props.onRangeChange}
          onGenerateSummary={props.onGenerateSummary}
        />
      );
    case 'adapters':
      return <AdaptersView clients={props.clients} onOpenClient={props.onOpenClient} />;
    case 'settings':
      return <SettingsView settings={props.settings} onSave={props.onSaveSettings} />;
    case 'health':
      return <HealthView health={props.overview.health} clients={props.clients} />;
    default:
      return <DashboardView {...props} />;
  }
}
