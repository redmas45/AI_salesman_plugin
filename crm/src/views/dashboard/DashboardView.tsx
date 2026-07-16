import { useEffect, useState } from 'react';
import type { View, Overview, Client, AnalyticsResponse, ClientBoardSection } from '../../types';
import { crmApi } from '../../api';
import { healthState } from '../../utils/format';
import { clientRuntimeStatus } from '../../utils/clientStatus';
import { RangeControl } from '../../components/shared/RangeControl';
import { ProviderUsagePanel } from './ProviderUsagePanels';
import { DashboardOperationsBrief } from './DashboardOperations';
import {
  ClientRegistryPanel,
  DashboardTrendChart,
  HealthStatusPanel,
  RecentActivityFeed,
} from './DashboardPanels';

export interface DashboardViewProps {
  overview: Overview;
  clients: Client[];
  analytics: AnalyticsResponse | null;
  range: string;
  onRangeChange: (range: string) => void;
  onViewChange: (view: View) => void;
  onOpenSettings?: (focusKey?: string) => void;
  onOpenClientBoardSection: (section: ClientBoardSection) => void;
  onOpenClient: (siteId: string) => void;
}

export function DashboardView({
  overview,
  clients,
  analytics,
  range,
  onRangeChange,
  onViewChange,
  onOpenSettings,
  onOpenClientBoardSection,
  onOpenClient,
}: DashboardViewProps) {
  const [checkedProviderUsage, setCheckedProviderUsage] = useState<Overview['provider_usage'] | null>(null);
  const [checkingProvider, setCheckingProvider] = useState(false);
  const [providerCheckError, setProviderCheckError] = useState('');
  const effectiveProviderUsage = checkedProviderUsage ?? overview.provider_usage;
  const metrics = overview.metrics;
  const currentClientRows = clients.filter((client) => client.status !== 'available');
  const availableRows = clients.filter((client) => client.status === 'available');
  const currentClients = currentClientRows.length;
  const offlineCurrentClients = currentClientRows.filter((client) => clientRuntimeStatus(client) !== 'online').length;
  const availableClients = availableRows.length;
  const onlineAvailable = availableRows.filter((client) => clientRuntimeStatus(client) === 'online').length;
  const offlineAvailable = availableClients - onlineAvailable;
  const missingVectorClients = currentClientRows.filter((client) => client.catalog.missing_embeddings > 0).length;
  const degradedHealth = Object.values(overview.health).filter((value) => healthState(value) !== 'up').length;
  useEffect(() => {
    setCheckedProviderUsage(null);
  }, [overview.provider_usage?.checked_at]);

  async function handleCheckProviderUsage() {
    setCheckingProvider(true);
    setProviderCheckError('');
    try {
      const response = await crmApi.checkProviderUsage();
      setCheckedProviderUsage(response.provider_usage);
    } catch (error) {
      setProviderCheckError(error instanceof Error ? error.message : 'Provider check failed.');
    } finally {
      setCheckingProvider(false);
    }
  }

  return (
    <div className="grid gap-4">
      <section className="section-row">
        <div>
          <h2 className="text-base font-semibold">Operations home</h2>
          <p className="mt-1 text-sm text-muted">Client state, live installs, data quality, and service health with direct drilldowns.</p>
        </div>
        <RangeControl value={range} onChange={onRangeChange} />
      </section>
      <DashboardOperationsBrief
        providerUsage={effectiveProviderUsage}
        currentClients={currentClients}
        offlineCurrentClients={offlineCurrentClients}
        availableClients={availableClients}
        onlineAvailable={onlineAvailable}
        offlineAvailable={offlineAvailable}
        missingVectorClients={missingVectorClients}
        degradedHealth={degradedHealth}
        turnsToday={metrics.voice_turns_today ?? 0}
        onOpenClientBoardSection={onOpenClientBoardSection}
        onViewChange={onViewChange}
        onOpenSettings={onOpenSettings}
        onCheckProviderUsage={handleCheckProviderUsage}
        checkingProvider={checkingProvider}
        providerCheckError={providerCheckError}
      />
      <div className="dashboard-bento fade-in">
        <div className="bento-full card">
          <ProviderUsagePanel
            providerUsage={effectiveProviderUsage}
            onOpenUsage={() => onViewChange('usage')}
            onOpenSettings={onOpenSettings}
            onCheckProviderUsage={handleCheckProviderUsage}
            checkingProvider={checkingProvider}
            providerCheckError={providerCheckError}
          />
        </div>
        <div className="dashboard-bento-column bento-wide">
          <div className="card">
            <DashboardTrendChart analytics={analytics} range={range} onOpenAnalytics={() => onViewChange('analytics')} />
          </div>
          <div className="card">
            <RecentActivityFeed items={overview.recent_activity} onOpen={() => onViewChange('conversations')} />
          </div>
        </div>
        <div className="dashboard-bento-column bento-narrow">
          <div className="card">
            <ClientRegistryPanel clients={clients} onOpenClient={onOpenClient} onOpenSection={onOpenClientBoardSection} />
          </div>
          <div className="card">
            <HealthStatusPanel health={overview.health} onOpenHealth={() => onViewChange('health')} />
          </div>
        </div>
      </div>
    </div>
  );
}
