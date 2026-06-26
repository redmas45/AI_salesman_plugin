import { useEffect, useMemo, useState } from 'react';
import { Code2, FileText, Plug } from 'lucide-react';
import { crmApi } from '../../api';
import type { AdapterConfigResponse, Client, PromptProfileResponse } from '../../types';
import type { CrmVerticalDefinition } from '../../verticals/types';
import { EmptyState } from '../../components/ui/EmptyState';
import { Panel } from '../../components/ui/Panel';
import { StatusPill } from '../../components/ui/Badge';
import { TechnicalDetails } from '../../components/shared/TechnicalDetails';

interface AdapterTabProps {
  client: Client;
  vertical: CrmVerticalDefinition;
}

export function AdapterTab({ client, vertical }: AdapterTabProps) {
  const [adapter, setAdapter] = useState<AdapterConfigResponse | null>(null);
  const [promptProfile, setPromptProfile] = useState<PromptProfileResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState('');

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setMessage('');
    Promise.all([crmApi.getClientAdapter(client.site_id), crmApi.getPromptProfile(client.site_id)])
      .then(([adapterResponse, promptResponse]) => {
        if (cancelled) return;
        setAdapter(adapterResponse);
        setPromptProfile(promptResponse);
      })
      .catch((error: unknown) => {
        if (!cancelled) setMessage(error instanceof Error ? error.message : 'Adapter details failed to load.');
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [client.site_id]);

  const actionNames = useMemo(() => {
    const actions = adapter?.runtime_config.adapter.actions ?? {};
    return Object.keys(actions).sort();
  }, [adapter]);

  const activePrompt = promptProfile?.active_version ?? null;

  if (loading) {
    return (
      <div className="tab-content fade-in">
        <EmptyState text="Loading adapter configuration..." />
      </div>
    );
  }

  return (
    <div className="tab-content fade-in">
      <section className="section-row">
        <div>
          <h2 className="text-base font-semibold">Generated adapter</h2>
          <p className="mt-1 text-sm text-muted">
            AI Hub generated this runtime layer from the one-line script, crawl, and page observations.
          </p>
        </div>
        <StatusPill value={adapter?.runtime_config.enabled ? 'enabled' : 'disabled'} />
      </section>

      {message ? <div className="notice notice-error">{message}</div> : null}

      <div className="grid gap-4 xl:grid-cols-[0.95fr_1.05fr]">
        <Panel title="Universal install script" action={<Plug size={16} aria-hidden="true" />}>
          <pre className="code-block install-script">{client.script_tag}</pre>
          <div className="mt-3 grid gap-2 text-sm">
            <KeyValue label="Adapter mode" value={adapter?.runtime_config.adapter.mode || '-'} />
            <KeyValue label="Platform" value={adapter?.runtime_config.adapter.platform || 'auto'} />
            <KeyValue label="Vertical" value={String(adapter?.runtime_config.vertical.key || vertical.key)} />
            <KeyValue
              label="Selectors"
              value={adapter?.runtime_config.adapter.selector_validated ? 'validated' : 'generated'}
            />
          </div>
        </Panel>

        <Panel title="Detected actions" action={<Code2 size={16} aria-hidden="true" />}>
          {actionNames.length ? (
            <div className="action-chip-grid">
              {actionNames.map((action) => (
                <span key={action} className="action-chip">
                  {action}
                </span>
              ))}
            </div>
          ) : (
            <EmptyState text="No generated actions yet. Open the client site with the install script, then run crawl/readiness." />
          )}
        </Panel>
      </div>

      <div className="grid gap-4 xl:grid-cols-2">
        <Panel title="Generated adapter code">
          <pre className="code-block install-script">{adapter?.adapter_code || '// Adapter code is not generated yet.'}</pre>
        </Panel>
        <Panel title="Generated prompt preview" action={<FileText size={16} aria-hidden="true" />}>
          {activePrompt ? (
            <div className="grid gap-3">
              <KeyValue label="Version" value={`v${activePrompt.version} ${activePrompt.status}`} />
              <pre className="code-block install-script">{activePrompt.system_prompt}</pre>
              {activePrompt.developer_rules ? (
                <pre className="code-block install-script">{activePrompt.developer_rules}</pre>
              ) : null}
            </div>
          ) : (
            <EmptyState text="No prompt profile exists yet." />
          )}
        </Panel>
      </div>

      <TechnicalDetails title="Generated runtime config JSON" data={adapter?.runtime_config ?? null} />
    </div>
  );
}

function KeyValue({ label, value }: { label: string; value: string | number | null | undefined }) {
  return (
    <div className="grid grid-cols-[130px_minmax(0,1fr)] gap-3 border-b border-line py-2 last:border-b-0">
      <span className="text-muted">{label}</span>
      <strong className="min-w-0 overflow-wrap-anywhere">{value == null || value === '' ? '-' : value}</strong>
    </div>
  );
}
