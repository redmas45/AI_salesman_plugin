import type { Client } from '../types';
import { Button } from '../components/ui/Button';
import { Panel } from '../components/ui/Panel';
import { CrawlButton } from '../components/shared/ClientActions';
import { MiniMetric } from './ClientDetailView';

export interface CatalogsViewProps {
  clients: Client[];
  crawlingSites: Set<string>;
  onOpenClient: (siteId: string) => void;
  onTriggerCrawl: (siteId: string) => void;
}

export function CatalogsView({
  clients,
  crawlingSites,
  onOpenClient,
  onTriggerCrawl,
}: CatalogsViewProps) {
  return (
    <div className="grid gap-4 xl:grid-cols-2">
      {clients.map((client) => (
        <Panel key={client.site_id} title={client.name}>
          <div className="grid gap-3 sm:grid-cols-3">
            <MiniMetric label="Products" value={client.catalog.active_products} />
            <MiniMetric label="Categories" value={client.catalog.categories ?? 0} />
            <MiniMetric label="Missing vectors" value={client.catalog.missing_embeddings} />
          </div>
          <div className="mt-4 flex flex-wrap gap-2">
            <Button variant="secondary" onClick={() => onOpenClient(client.site_id)}>
              Open detail
            </Button>
            <CrawlButton
              siteId={client.site_id}
              label="Crawl now"
              active={crawlingSites.has(client.site_id)}
              onTriggerCrawl={onTriggerCrawl}
            />
          </div>
        </Panel>
      ))}
    </div>
  );
}
