import {
  CheckCircle2,
  Gauge,
  PackageOpen,
  WifiOff,
  type LucideIcon,
} from 'lucide-react';
import type { ClientBoardSection, Overview, View } from '../../types';
import { number } from '../../utils/format';
import { ProviderCompactAlert } from './ProviderUsagePanels';

export function DashboardOperationsBrief({
  providerUsage,
  currentClients,
  offlineCurrentClients,
  availableClients,
  onlineAvailable,
  offlineAvailable,
  missingVectorClients,
  degradedHealth,
  turnsToday,
  onOpenClientBoardSection,
  onViewChange,
  onOpenSettings,
  onCheckProviderUsage,
  checkingProvider,
  providerCheckError,
}: {
  providerUsage: Overview['provider_usage'];
  currentClients: number;
  offlineCurrentClients: number;
  availableClients: number;
  onlineAvailable: number;
  offlineAvailable: number;
  missingVectorClients: number;
  degradedHealth: number;
  turnsToday: number;
  onOpenClientBoardSection: (section: ClientBoardSection) => void;
  onViewChange: (view: View) => void;
  onOpenSettings?: (focusKey?: string) => void;
  onCheckProviderUsage: () => void | Promise<void>;
  checkingProvider: boolean;
  providerCheckError: string;
}) {
  const providerNeedsReview = providerUsage?.status !== 'ok';
  const attentionCount = offlineCurrentClients + onlineAvailable + offlineAvailable + missingVectorClients + degradedHealth + (providerNeedsReview ? 1 : 0);
  return (
    <section className="dashboard-ops-console fade-in" aria-label="Operations center">
      <div className="dashboard-ops-top">
        <div className="dashboard-ops-summary">
          <span>Attention queue</span>
          <strong>{attentionCount ? `${number(attentionCount)} item${attentionCount === 1 ? '' : 's'} need review` : 'No current blockers'}</strong>
          <small>{number(currentClients)} clients, {number(availableClients)} pending installs, {number(turnsToday)} turns today</small>
        </div>
        {providerNeedsReview ? (
          <ProviderCompactAlert
            providerUsage={providerUsage}
            onOpenUsage={() => onViewChange('usage')}
            onOpenSettings={onOpenSettings}
            onCheckProviderUsage={onCheckProviderUsage}
            checkingProvider={checkingProvider}
            providerCheckError={providerCheckError}
          />
        ) : (
          <button className="dashboard-provider-ok" type="button" onClick={() => onViewChange('usage')}>
            <CheckCircle2 size={18} aria-hidden="true" />
            <span>AI provider</span>
            <strong>Runtime ready</strong>
            <small>Open usage and provider monitoring</small>
          </button>
        )}
      </div>
      <div className="dashboard-attention-grid" aria-label="Attention queue">
        <DashboardAttentionCard
          icon={WifiOff}
          label="Offline clients"
          value={offlineCurrentClients}
          detail="Current clients whose source site is unreachable"
          tone={offlineCurrentClients ? 'bad' : 'idle'}
          action="Review clients"
          onClick={() => onOpenClientBoardSection('current')}
        />
        <DashboardAttentionCard
          icon={PackageOpen}
          label="Pending installs"
          value={availableClients}
          detail={`${number(onlineAvailable)} online, ${number(offlineAvailable)} offline`}
          tone={offlineAvailable ? 'warn' : onlineAvailable ? 'ok' : 'idle'}
          action="Review installs"
          onClick={() => onOpenClientBoardSection('available')}
        />
        <DashboardAttentionCard
          icon={PackageOpen}
          label="Vector gaps"
          value={missingVectorClients}
          detail="Current clients with missing knowledge vectors"
          tone={missingVectorClients ? 'warn' : 'idle'}
          action="Open data"
          onClick={() => onViewChange('catalogs')}
        />
        <DashboardAttentionCard
          icon={Gauge}
          label="Health issues"
          value={degradedHealth}
          detail="Runtime checks not currently healthy"
          tone={degradedHealth ? 'bad' : 'idle'}
          action="Open health"
          onClick={() => onViewChange('health')}
        />
      </div>
    </section>
  );
}

function DashboardAttentionCard({
  icon: Icon,
  label,
  value,
  detail,
  tone,
  action,
  onClick,
}: {
  icon: LucideIcon;
  label: string;
  value: number;
  detail: string;
  tone: 'ok' | 'warn' | 'bad' | 'idle';
  action: string;
  onClick: () => void;
}) {
  return (
    <button className={`dashboard-attention-card ${tone}`} type="button" onClick={onClick}>
      <Icon size={17} aria-hidden="true" />
      <span>{label}</span>
      <strong>{number(value)}</strong>
      <small>{detail}</small>
      <em>{action}</em>
    </button>
  );
}
