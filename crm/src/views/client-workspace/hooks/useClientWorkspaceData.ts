import { useEffect, useMemo, useState } from 'react';
import { crmApi } from '../../../api';
import type {
  CapabilitiesSummary,
  CatalogProduct,
  Client,
  CrawlReport,
  ReadinessReport,
} from '../../../types';
import { CATALOG_PAGE_LIMIT, normalizeCatalogProduct, type DisplayProduct } from '../catalog/catalogProducts';
import { safeRecord } from '../evidence/integrationEvidence';

export function useClientReports(client: Client) {
  const [capabilities, setCapabilities] = useState<CapabilitiesSummary | null>(null);
  const [scanReport, setScanReport] = useState<ReadinessReport | null>(null);
  const [crawlReport, setCrawlReport] = useState<CrawlReport | null>(null);
  const [reportError, setReportError] = useState('');
  const reportRefreshKey = useMemo(
    () =>
      JSON.stringify({
        status: client.last_crawl_status || '',
        crawledAt: client.last_crawl_at || '',
        initialization: safeRecord(client.vertical_config).initialization || {},
        catalog: client.catalog,
      }),
    [client.last_crawl_status, client.last_crawl_at, client.vertical_config, client.catalog],
  );

  useEffect(() => {
    let cancelled = false;
    setReportError('');
    Promise.allSettled([
      crmApi.getCapabilities(client.site_id),
      crmApi.getScanReport(client.site_id),
      crmApi.getCrawlReport(client.site_id),
    ]).then(([capabilityResult, scanResult, crawlResult]) => {
      if (cancelled) return;
      if (capabilityResult.status === 'fulfilled') setCapabilities(capabilityResult.value);
      if (scanResult.status === 'fulfilled') setScanReport(scanResult.value.report);
      if (crawlResult.status === 'fulfilled') setCrawlReport(crawlResult.value.report);
      if ([capabilityResult, scanResult, crawlResult].some((result) => result.status === 'rejected')) {
        setReportError('Some client reports could not be loaded. Run a scan or refresh after the next crawl.');
      }
    });
    return () => {
      cancelled = true;
    };
  }, [client.site_id, reportRefreshKey]);

  return {
    capabilities,
    scanReport,
    crawlReport,
    reportError,
    setReportError,
    reportRefreshKey,
  };
}

export function useClientCatalogProducts(client: Client) {
  const [catalogProducts, setCatalogProducts] = useState<CatalogProduct[]>([]);
  const [catalogLoading, setCatalogLoading] = useState(false);
  const [catalogError, setCatalogError] = useState('');

  useEffect(() => {
    let cancelled = false;
    setCatalogLoading(true);
    setCatalogError('');
    crmApi
      .catalogProducts(client.site_id, CATALOG_PAGE_LIMIT)
      .then((products) => {
        if (!cancelled) setCatalogProducts(products);
      })
      .catch((error: unknown) => {
        if (cancelled) return;
        setCatalogProducts([]);
        setCatalogError(error instanceof Error ? error.message : 'Full catalog failed to load. Showing preview data.');
      })
      .finally(() => {
        if (!cancelled) setCatalogLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [client.site_id, client.catalog.active_products, client.catalog.missing_embeddings, client.last_crawl_at]);

  const displayedProducts: DisplayProduct[] = catalogProducts.length
    ? catalogProducts.map(normalizeCatalogProduct)
    : (client.catalog_preview ?? []).map(normalizeCatalogProduct);

  return {
    catalogError,
    catalogLoading,
    displayedProducts,
  };
}
