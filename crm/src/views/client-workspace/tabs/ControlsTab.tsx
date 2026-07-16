import { useEffect, useState, type ChangeEvent, type FormEvent } from 'react';
import { CheckCircle2, ClipboardCheck, Copy, Eye, KeyRound, Settings, Trash2 } from 'lucide-react';
import type { Client, View } from '../../../types';
import { Button } from '../../../components/ui/Button';
import { Panel } from '../../../components/ui/Panel';
import { StatusPill } from '../../../components/ui/Badge';
import { Field } from '../../../components/ui/Field';
import { clientPanelHref } from '../../../utils/clientLinks';
import { panelPasswordLabel } from '../../../utils/format';
import type { ClientWorkspaceTabId } from '../../../verticals/types';
import { KeyValue } from '../components/workspaceCards';
export function ClientControlsTab({
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

function normalizePositiveInteger(value: string) {
  const normalized = Math.max(1, Math.round(Number(value)));
  return String(Number.isFinite(normalized) ? normalized : 1);
}
