import { ExternalLink } from 'lucide-react';
import type { Client } from '../types';
import { Button } from '../components/ui/Button';
import { StatusPill } from '../components/ui/Badge';
import { EmptyState } from '../components/ui/EmptyState';
import { number } from '../utils/format';

export interface AdaptersViewProps {
  clients: Client[];
  onOpenClient: (siteId: string) => void;
}

export function AdaptersView({ clients, onOpenClient }: AdaptersViewProps) {
  if (!clients.length) {
    return <EmptyState title="No adapters yet" message="Add a client before configuring storefront adapters." />;
  }

  return (
    <div className="adapter-grid fade-in">
      {clients.map((client) => {
        const configured = Boolean(client.adapter_name && client.adapter_name !== '-');
        return (
          <article key={client.site_id} className="card adapter-card interactive">
            <div className="adapter-card-top">
              <div>
                <span className="adapter-eyebrow">{client.deploy_mode || 'storefront'}</span>
                <h2>{client.name}</h2>
              </div>
              <StatusPill value={client.status} />
            </div>
            <div className="adapter-detail-list">
              <KeyValue label="Adapter" value={configured ? client.adapter_name : 'Not configured'} />
              <KeyValue label="Origin" value={configured ? (client.allowed_origin || client.store_url || '-') : '-'} />
              <KeyValue label="Products" value={number(client.catalog.active_products)} />
            </div>
            {!configured ? (
              <div className="adapter-empty-note">
                <strong>No adapter configured</strong>
                <span>Open the client workspace to finish adapter setup.</span>
              </div>
            ) : null}
            <div className="adapter-actions">
              <Button variant="secondary" size="sm" type="button" onClick={() => onOpenClient(client.site_id)}>
                Test connection
              </Button>
              <Button
                variant="ghost"
                size="sm"
                type="button"
                icon={ExternalLink}
                onClick={() => window.open(client.store_url, '_blank', 'noopener,noreferrer')}
              >
                Open store
              </Button>
            </div>
          </article>
        );
      })}
    </div>
  );
}

function KeyValue({ label, value }: { label: string; value: string | number | null | undefined }) {
  return (
    <div className="grid grid-cols-[130px_minmax(0,1fr)] gap-3 border-b border-line py-2 text-sm last:border-b-0">
      <span className="text-muted">{label}</span>
      <strong className="min-w-0 overflow-wrap-anywhere">{value == null || value === '' ? '-' : value}</strong>
    </div>
  );
}
