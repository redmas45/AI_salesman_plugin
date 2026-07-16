import { useState, type FormEvent } from 'react';
import { ClipboardCheck, Eye, Gauge, PackageOpen, Settings, ShieldCheck, type LucideIcon } from 'lucide-react';
import { crmApi } from '../../../api';
import type { Client, CapabilitiesSummary, CrawlReport } from '../../../types';
import { Button } from '../../../components/ui/Button';
import { Panel } from '../../../components/ui/Panel';
import { EmptyState } from '../../../components/ui/EmptyState';
import { Field } from '../../../components/ui/Field';
import { NoticeBanner } from '../../../components/shared/NoticeBanner';
import { UniversalInstallerPanel } from '../../../components/shared/UniversalInstallerPanel';
import { number, percent, shortTime } from '../../../utils/format';
import type { ClientWorkspaceTabId, CrmVerticalDefinition } from '../../../verticals/types';
import { safeRecord } from '../evidence/integrationEvidence';
import { ActionChipGrid } from '../components/actionChips';
import { KeyValue, Meter, MetricCard } from '../components/workspaceCards';
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

export function ClientOverviewTab({
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

function activeEntityTitle(vertical: CrmVerticalDefinition) {
  const text = vertical.entityLabelPlural || 'items';
  return text.charAt(0).toUpperCase() + text.slice(1);
}
