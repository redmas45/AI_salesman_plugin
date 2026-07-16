import { crmApi } from '../api';
import type { Client, Overview } from '../types';

interface CrawlPollingDeps {
  siteId: string;
  syncClient: (client: Client) => void;
  setOverview: (overview: Overview) => void;
  setCrawlingSites: (updater: (current: Set<string>) => Set<string>) => void;
  showError: (error: unknown, fallback: string) => void;
}

interface SetupPollingDeps {
  siteId: string;
  syncClient: (client: Client) => void;
  setOverview: (overview: Overview) => void;
  setAutoIntegratingSites: (updater: (current: Set<string>) => Set<string>) => void;
  showError: (error: unknown, fallback: string) => void;
}

const CRAWL_POLL_INTERVAL_MS = 5000;
const CRAWL_POLL_TIMEOUT_MS = 60000;
const SETUP_POLL_INTERVAL_MS = 10000;
const SETUP_POLL_TIMEOUT_MS = 30 * 60 * 1000;

export async function pollCrawlStatus({
  siteId,
  syncClient,
  setOverview,
  setCrawlingSites,
  showError,
}: CrawlPollingDeps) {
  const startedAt = Date.now();
  try {
    while (Date.now() - startedAt < CRAWL_POLL_TIMEOUT_MS) {
      await delay(CRAWL_POLL_INTERVAL_MS);
      const response = await crmApi.client(siteId);
      syncClient(response.client);
      const status = String(response.client.last_crawl_status || '').toLowerCase();
      if (status && status !== 'running' && status !== 'crawling') break;
    }
    setOverview(await crmApi.overview());
  } catch (error) {
    showError(error, 'Crawler status refresh failed.');
  } finally {
    setCrawlingSites((current) => {
      const next = new Set(current);
      next.delete(siteId);
      return next;
    });
  }
}

export async function pollAutoIntegrationStatus({
  siteId,
  syncClient,
  setOverview,
  setAutoIntegratingSites,
  showError,
}: SetupPollingDeps) {
  const startedAt = Date.now();
  try {
    while (Date.now() - startedAt < SETUP_POLL_TIMEOUT_MS) {
      await delay(SETUP_POLL_INTERVAL_MS);
      const response = await crmApi.client(siteId);
      syncClient(response.client);
      const initialization = response.client.vertical_config?.initialization as Record<string, unknown> | undefined;
      const status = String(initialization?.status || '').toLowerCase();
      if (status && status !== 'running') break;
    }
    setOverview(await crmApi.overview());
  } catch (error) {
    showError(error, 'Setup status refresh failed.');
  } finally {
    setAutoIntegratingSites((current) => {
      const next = new Set(current);
      next.delete(siteId);
      return next;
    });
  }
}

function delay(ms: number) {
  return new Promise((resolve) => window.setTimeout(resolve, ms));
}
