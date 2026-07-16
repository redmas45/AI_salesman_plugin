import { AlertTriangle, CheckCircle2, ChevronDown, CloudCog, Info, Settings } from 'lucide-react';
import type { Overview } from '../../types';
import { EmptyState } from '../../components/ui/EmptyState';
import { StatusPill } from '../../components/ui/Badge';
import { number } from '../../utils/format';

export function ProviderCompactAlert({
  providerUsage,
  onOpenUsage,
  onOpenSettings,
  onCheckProviderUsage,
  checkingProvider,
  providerCheckError,
}: {
  providerUsage: Overview['provider_usage'];
  onOpenUsage: () => void;
  onOpenSettings?: (focusKey?: string) => void;
  onCheckProviderUsage: () => void | Promise<void>;
  checkingProvider: boolean;
  providerCheckError: string;
}) {
  const latest = providerUsage?.recent_events?.[0];
  const copy = providerAlertCopy(providerUsage?.status || 'unverified');
  const detail = latest?.message || copy.summary;
  const settingsKey = 'AZURE_OPENAI_API_KEY';
  return (
    <details className="dashboard-provider-alert" role="alert">
      <summary>
        <AlertTriangle size={18} aria-hidden="true" />
        <span>
          <strong>{copy.title}</strong>
          <small>{copy.summary}</small>
        </span>
        <ChevronDown size={16} aria-hidden="true" />
      </summary>
      <div className="dashboard-provider-alert-body">
        <p>{shortProviderMessage(detail)}</p>
        <div className="dashboard-provider-alert-actions">
          <button type="button" onClick={onCheckProviderUsage} disabled={checkingProvider}>
            {checkingProvider ? 'Checking...' : 'Check runtime'}
          </button>
          <button type="button" onClick={onOpenUsage}>Open usage</button>
          <button type="button" onClick={() => onOpenSettings?.(settingsKey)}>Configure</button>
        </div>
        {providerCheckError ? <p className="provider-check-error">{providerCheckError}</p> : null}
      </div>
    </details>
  );
}

export function ProviderUsagePanel({
  providerUsage,
  onOpenUsage,
  onOpenSettings,
  onCheckProviderUsage,
  checkingProvider,
  providerCheckError,
}: {
  providerUsage: Overview['provider_usage'];
  onOpenUsage: () => void;
  onOpenSettings?: (focusKey?: string) => void;
  onCheckProviderUsage: () => void | Promise<void>;
  checkingProvider: boolean;
  providerCheckError: string;
}) {
  if (!providerUsage) {
    return <EmptyState title="Provider usage unavailable" message="Refresh CRM to load AI provider monitoring." />;
  }

  const statusTone = providerUsage.status === 'quota_exhausted' || providerUsage.status === 'not_configured' || providerUsage.status === 'error'
    ? 'bad'
    : 'ok';
  const latest = providerUsage.recent_events?.[0];

  return (
    <section className="provider-usage-panel">
      <div className="provider-usage-head">
        <div>
          <span className="kpi-label">AI provider usage</span>
          <h3>Azure OpenAI runtime</h3>
        </div>
        <StatusPill value={providerStatusLabel(providerUsage.status)} />
      </div>
      <div className="provider-usage-grid">
        <ProviderMetric label="Chat" value={providerUsage.llm_model || '-'} />
        <ProviderMetric label="STT" value={providerUsage.stt_model || '-'} />
        <ProviderMetric label="TTS" value={providerUsage.tts_model || '-'} />
        <ProviderMetric label="Local tokens" value={number(providerUsage.local_tokens.estimated_total)} />
      </div>
      <div className={`provider-usage-state ${statusTone}`}>
        <CloudCog size={18} />
        <div>
          <strong>{providerStatusMessage(providerUsage)}</strong>
          <span>{providerStatusDetail(providerUsage)}</span>
        </div>
      </div>
      {providerCheckError ? <p className="provider-check-error">{providerCheckError}</p> : null}
      <details className="crm-disclosure provider-usage-details">
        <summary>
          <Info size={15} aria-hidden="true" />
          <span>Data source and latest provider event</span>
          <ChevronDown size={15} aria-hidden="true" />
        </summary>
        <div className="provider-data-source">
          <div>
            <strong>Local tokens</strong>
            <span>CRM usage events recorded after widget turns.</span>
          </div>
          <div>
            <strong>Provider status</strong>
            <span>LLM provider events recorded by the runtime.</span>
          </div>
          <div>
            <strong>Billing</strong>
            <span>{providerUsage.billing.message}</span>
          </div>
          {latest ? <code>{shortProviderMessage(latest.message)}</code> : null}
        </div>
      </details>
      <div className="provider-usage-footer">
        <span>
          Billing source: Azure Cost Management
        </span>
        <div className="provider-usage-actions">
          <button type="button" onClick={onCheckProviderUsage} disabled={checkingProvider}>
            <CheckCircle2 size={14} aria-hidden="true" />
            {checkingProvider ? 'Checking...' : 'Check runtime'}
          </button>
          <button type="button" onClick={() => onOpenSettings?.('AZURE_OPENAI_API_KEY')}>
            <Settings size={14} aria-hidden="true" />
            Configure
          </button>
          <button type="button" onClick={onOpenUsage}>Open usage</button>
        </div>
      </div>
    </section>
  );
}

function ProviderMetric({ label, value, onClick }: { label: string; value: string | number; onClick?: () => void }) {
  const content = (
    <>
      <span>{label}</span>
      <strong>{value}</strong>
    </>
  );
  if (onClick) {
    return (
      <button className="provider-usage-metric interactive" type="button" onClick={onClick}>
        {content}
      </button>
    );
  }
  return <div className="provider-usage-metric">{content}</div>;
}

function providerStatusLabel(status: string) {
  if (status === 'quota_exhausted') return 'quota exhausted';
  if (status === 'not_configured') return 'not configured';
  if (status === 'unverified') return 'verification needed';
  if (status === 'error') return 'provider error';
  return status || 'unknown';
}

function providerStatusMessage(providerUsage: NonNullable<Overview['provider_usage']>) {
  if (providerUsage.status === 'quota_exhausted') return 'Azure quota is exhausted. Customer AI turns are blocked.';
  if (providerUsage.status === 'not_configured') return 'Azure OpenAI configuration is incomplete.';
  if (providerUsage.status === 'error') return 'Azure rejected or failed the latest runtime check.';
  if (providerUsage.status === 'unverified') return 'Azure access has not been verified recently.';
  if (providerUsage.status === 'ok') return 'Azure runtime check passed. Maya can answer customer turns.';
  return 'Azure provider status is unavailable.';
}

function providerStatusDetail(providerUsage: NonNullable<Overview['provider_usage']>) {
  if (providerUsage.status === 'quota_exhausted') return 'The runtime key exists, but Azure is rejecting chat calls for quota or billing.';
  if (providerUsage.status === 'not_configured') return 'Set the Azure key, base URL, and chat deployment before Maya can answer.';
  if (providerUsage.status === 'error') return 'Customer AI turns may be blocked. Check the latest event and verify the runtime key.';
  if (providerUsage.status === 'unverified') return 'Run a live provider check before relying on Maya in a demo or client session.';
  return providerUsage.billing.message || 'Provider usage is being monitored from CRM.';
}

function providerAlertCopy(status: string) {
  if (status === 'quota_exhausted') return { title: 'Azure quota exhausted', summary: 'Customer AI turns are paused until billing or quota is restored.' };
  if (status === 'not_configured') return { title: 'Azure OpenAI not configured', summary: 'Customer AI turns are paused until runtime configuration is complete.' };
  if (status === 'error') return { title: 'Azure provider error', summary: 'The latest runtime check failed. Review the event before a client demo.' };
  return { title: 'Azure access needs verification', summary: 'The last successful provider check is stale or missing.' };
}

function shortProviderMessage(message: string) {
  return message.replace(/\s+/g, ' ').trim().slice(0, 260);
}
