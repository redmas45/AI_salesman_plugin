import { useState, useEffect, useMemo, type FormEvent, type ChangeEvent } from 'react';
import {
  ShieldCheck,
  PackageOpen,
  Gauge,
  ClipboardCheck,
  Settings,
  KeyRound,
  Trash2,
  Eye,
  AlertTriangle,
  XCircle,
  Search,
  ChevronDown,
  CheckCircle2,
  type LucideIcon,
} from 'lucide-react';
import { crmApi } from '../api';
import type {
  View,
  Client,
  UsageEvent,
  CapabilitiesSummary,
  ReadinessReport,
  CrawlReport,
  CatalogProduct,
  ProductPreview,
  SyncRun,
} from '../types';
import { Button } from '../components/ui/Button';
import { Panel } from '../components/ui/Panel';
import { StatusPill } from '../components/ui/Badge';
import { EmptyState } from '../components/ui/EmptyState';
import { Field } from '../components/ui/Field';
import { NoticeBanner } from '../components/shared/NoticeBanner';
import { TechnicalDetails } from '../components/shared/TechnicalDetails';
import { ActivityList } from '../components/shared/ActivityList';
import { CopyScriptButton, CrawlButton } from '../components/shared/ClientActions';
import { panelPasswordLabel, money, number, percent, shortTime, labelize } from '../utils/format';
import { getCrmVertical } from '../verticals/registry';
import { tab as verticalTab } from '../verticals/shared';
import type { ClientWorkspaceTabDefinition, ClientWorkspaceTabId, CrmVerticalDefinition } from '../verticals/types';
import { AdapterTab } from './client-workspace/AdapterTab';
import { PromptTab } from './client-workspace/PromptTab';

const CATALOG_PAGE_LIMIT = 1000;
const CATALOG_PAGE_SIZE = 12;
const CORE_CLIENT_TAB_IDS = new Set<ClientWorkspaceTabId>([
  'overview',
  'readiness',
  'catalog',
  'crawl',
  'activity',
  'adapter',
  'prompt',
  'controls',
]);

const ACTION_LABELS: Record<string, string> = {
  ADD_TO_CART: 'Add to cart',
  CHECKOUT: 'Checkout',
  CLEAR_CART: 'Clear cart',
  CLEAR_FILTERS: 'Clear filters',
  CLEAR_HISTORY: 'Clear history',
  FILTER_PRODUCTS: 'Filter products',
  NAVIGATE_TO: 'Navigate',
  REMOVE_FROM_CART: 'Remove from cart',
  SHOW_COMPARISON: 'Compare products',
  SHOW_PRODUCTS: 'Show products',
  SHOW_PRODUCT_DETAIL: 'Product detail',
  SORT_PRODUCTS: 'Sort products',
  UPDATE_CART_QUANTITY: 'Update quantity',
  UPDATE_PREFERENCES: 'Update preferences',
};

interface DisplayProduct {
  id: string;
  name: string;
  brand: string;
  category: string;
  description: string;
  price: number;
  stock: number | null;
  imageUrl: string;
  vectorized: boolean;
  rating: number | null;
  reviewCount: number | null;
}

export interface ClientDetailViewProps {
  client: Client;
  recentActivity: UsageEvent[];
  crawlingSites: Set<string>;
  onCopyScript: (client: Client) => Promise<void>;
  onTriggerCrawl: (siteId: string) => void;
  onRemoveClient: (siteId: string) => void;
  onToggleClient: (siteId: string, enabled: boolean) => void;
  onUpdateTokenLimits: (siteId: string, tokenLimit: number, sessionTokenLimit: number) => Promise<void>;
  onOpenPasswordDialog: (client: Client) => void;
  onViewChange: (view: View) => void;
}

export function ClientDetailView({
  client,
  recentActivity,
  crawlingSites,
  onCopyScript,
  onTriggerCrawl,
  onRemoveClient,
  onToggleClient,
  onUpdateTokenLimits,
  onOpenPasswordDialog,
  onViewChange,
}: ClientDetailViewProps) {
  const vertical = getCrmVertical(client.vertical_key);
  const workspaceTabs = useMemo(() => withAdapterTab(vertical.clientTabs), [vertical.clientTabs]);
  const [activeTab, setActiveTab] = useState<ClientWorkspaceTabId>('overview');
  const [capabilities, setCapabilities] = useState<CapabilitiesSummary | null>(null);
  const [scanReport, setScanReport] = useState<ReadinessReport | null>(null);
  const [crawlReport, setCrawlReport] = useState<CrawlReport | null>(null);
  const [catalogProducts, setCatalogProducts] = useState<CatalogProduct[]>([]);
  const [catalogLoading, setCatalogLoading] = useState(false);
  const [catalogError, setCatalogError] = useState('');
  const [reportError, setReportError] = useState('');
  const [scanning, setScanning] = useState(false);
  const crawling = crawlingSites.has(client.site_id);
  const activeTabDefinition = workspaceTabs.find((tab) => tab.id === activeTab) ?? workspaceTabs[0]!;

  useEffect(() => {
    if (!workspaceTabs.some((tab) => tab.id === activeTab)) {
      setActiveTab(workspaceTabs[0]?.id ?? 'overview');
    }
  }, [activeTab, workspaceTabs]);

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
  }, [client.site_id]);

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
  }, [client.site_id]);

  async function handleRunScan() {
    setScanning(true);
    try {
      const res = await crmApi.scanClient(client.site_id);
      setScanReport(res.report);
      const nextCapabilities = await crmApi.getCapabilities(client.site_id);
      setCapabilities(nextCapabilities);
      setReportError('');
    } catch (error) {
      setReportError(error instanceof Error ? error.message : 'Readiness scan failed.');
    } finally {
      setScanning(false);
    }
  }

  const displayedProducts = catalogProducts.length
    ? catalogProducts.map(normalizeCatalogProduct)
    : (client.catalog_preview ?? []).map(normalizeCatalogProduct);

  return (
    <div className="client-detail">
      <section className="client-hero">
        <div>
          <span className="text-xs font-semibold uppercase text-muted">Client detail</span>
          <h2 className="mt-1 text-xl font-semibold">{client.name}</h2>
          <p className="mt-1 text-sm text-muted">{client.store_url}</p>
          <div className="mt-3 flex flex-wrap gap-2">
            <StatusPill value={client.status} />
            <StatusPill value={client.last_crawl_status || 'not_started'} />
            <span className="client-hero-chip">{vertical.label}</span>
            <span className="client-hero-chip">
              {number(client.catalog.active_products)} {vertical.entityLabelPlural}
            </span>
          </div>
        </div>
        <div className="flex flex-wrap gap-2">
          <CopyScriptButton client={client} onCopyScript={onCopyScript} />
          <CrawlButton siteId={client.site_id} label="Crawl now" active={crawling} onTriggerCrawl={onTriggerCrawl} />
          <Button variant="secondary" icon={KeyRound} onClick={() => onOpenPasswordDialog(client)}>
            Panel password
          </Button>
          <Button variant="secondary" onClick={() => onToggleClient(client.site_id, client.status !== 'live')}>
            {client.status === 'live' ? 'Disable widget' : 'Enable widget'}
          </Button>
          <Button variant="danger" icon={Trash2} onClick={() => onRemoveClient(client.site_id)}>
            Remove
          </Button>
        </div>
      </section>
      <nav className="client-tabs" aria-label="Client detail sections">
        {workspaceTabs.map((tab) => (
          <ClientTabButton key={tab.id} tab={tab} active={activeTab === tab.id} onClick={() => setActiveTab(tab.id)} />
        ))}
      </nav>
      {reportError ? <NoticeBanner tone="error" message={reportError} /> : null}
      {activeTab === 'overview' ? (
        <ClientOverviewTab
          client={client}
          capabilities={capabilities}
          crawlReport={crawlReport}
          onCopyScript={onCopyScript}
          onTriggerCrawl={onTriggerCrawl}
          onRunScan={handleRunScan}
          scanning={scanning}
          crawling={crawling}
          vertical={vertical}
        />
      ) : null}
      {activeTab === 'readiness' ? (
        <ClientReadinessTab
          capabilities={capabilities}
          scanReport={scanReport}
          scanning={scanning}
          onRunScan={handleRunScan}
          vertical={vertical}
        />
      ) : null}
      {activeTab === 'catalog' ? (
        <ClientCatalogTab
          products={displayedProducts}
          loading={catalogLoading}
          error={catalogError}
          fallbackCount={client.catalog_preview?.length ?? 0}
          totalProducts={client.catalog.active_products}
          crawling={crawling}
          onTriggerCrawl={() => onTriggerCrawl(client.site_id)}
          vertical={vertical}
        />
      ) : null}
      {activeTab === 'crawl' ? (
        <ClientCrawlTab
          client={client}
          crawlReport={crawlReport}
          crawling={crawling}
          onTriggerCrawl={() => onTriggerCrawl(client.site_id)}
          vertical={vertical}
        />
      ) : null}
      {activeTab === 'activity' ? <ClientActivityTab client={client} recentActivity={recentActivity} /> : null}
      {activeTab === 'adapter' ? <AdapterTab client={client} vertical={vertical} /> : null}
      {activeTab === 'prompt' ? <PromptTab client={client} vertical={vertical} /> : null}
      {activeTab === 'controls' ? (
        <ClientControlsTab
          client={client}
          scanning={scanning}
          crawling={crawling}
          onCopyScript={onCopyScript}
          onTriggerCrawl={onTriggerCrawl}
          onRunScan={handleRunScan}
          onRemoveClient={onRemoveClient}
          onToggleClient={onToggleClient}
          onUpdateTokenLimits={onUpdateTokenLimits}
          onOpenPasswordDialog={onOpenPasswordDialog}
          onViewChange={onViewChange}
        />
      ) : null}
      {isExtensionTab(activeTab) ? (
        <VerticalExtensionTab tab={activeTabDefinition} vertical={vertical} />
      ) : null}
    </div>
  );
}

function withAdapterTab(tabs: ClientWorkspaceTabDefinition[]) {
  if (tabs.some((item) => item.id === 'adapter')) return tabs;
  const promptIndex = tabs.findIndex((item) => item.id === 'prompt');
  const insertAt = promptIndex >= 0 ? promptIndex : tabs.length;
  return [
    ...tabs.slice(0, insertAt),
    verticalTab('adapter', 'Adapter'),
    ...tabs.slice(insertAt),
  ];
}

function ClientTabButton({
  tab,
  active,
  onClick,
}: {
  tab: ClientWorkspaceTabDefinition;
  active: boolean;
  onClick: () => void;
}) {
  const Icon = tab.icon;
  return (
    <button className={`client-tab-btn ${active ? 'active' : ''}`} type="button" onClick={onClick}>
      <Icon size={15} aria-hidden="true" />
      <span>{tab.label}</span>
    </button>
  );
}

function ClientOverviewTab({
  client,
  capabilities,
  crawlReport,
  scanning,
  crawling,
  onCopyScript,
  onTriggerCrawl,
  onRunScan,
  vertical,
}: {
  client: Client;
  capabilities: CapabilitiesSummary | null;
  crawlReport: CrawlReport | null;
  scanning: boolean;
  crawling: boolean;
  onCopyScript: (client: Client) => Promise<void>;
  onTriggerCrawl: (siteId: string) => void;
  onRunScan: () => void;
  vertical: CrmVerticalDefinition;
}) {
  return (
    <div className="tab-content fade-in">
      <div className="grid gap-3 md:grid-cols-2 2xl:grid-cols-4">
        <MetricCard
          label={`Active ${vertical.entityLabelPlural}`}
          value={client.catalog.active_products}
          detail={`${number(client.catalog.categories ?? 0)} groups`}
        />
        <MetricCard label="Missing vectors" value={client.catalog.missing_embeddings} detail="Needs RAG sync" />
        <MetricCard label="Voice turns" value={client.usage.total_turns} detail={`${number(client.usage.turns_today)} today`} />
        <MetricCard label="Crawl coverage" value={`${percent(crawlReport?.coverage_score ?? 0)}%`} detail={client.last_crawl_status || 'not started'} />
      </div>
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
        <Panel
          title="One-line client script"
          action={
            <CopyScriptButton client={client} onCopyScript={onCopyScript} compact />
          }
        >
          <pre className="code-block install-script">{client.script_tag}</pre>
        </Panel>
      </div>
      <div className="grid gap-4 xl:grid-cols-2">
        <Panel title="Readiness at a glance">
          <CapabilitySnapshot capabilities={capabilities} />
        </Panel>
        <Panel title="Next useful checks">
          <div className="action-board">
            <ActionTile icon={ShieldCheck} title="Run a readiness scan" text={`Confirm ${vertical.entityLabelPlural}, sources, and supported actions before a client demo.`} />
            <ActionTile icon={PackageOpen} title={`Spot-check ${vertical.entityLabelPlural}`} text="Review names, media, source coverage, and vector state." />
            <ActionTile icon={Gauge} title="Refresh crawl data" text="Run a crawl after source or layout changes." />
          </div>
          <div className="mt-4 flex flex-wrap gap-2">
            <Button variant="secondary" disabled={scanning} onClick={onRunScan}>
              {scanning ? 'Scanning...' : 'Run readiness'}
            </Button>
            <CrawlButton siteId={client.site_id} label="Crawl now" active={crawling} onTriggerCrawl={onTriggerCrawl} />
          </div>
        </Panel>
      </div>
    </div>
  );
}

function CapabilitySnapshot({ capabilities }: { capabilities: CapabilitiesSummary | null }) {
  const [filter, setFilter] = useState<'supported' | 'unsupported'>('supported');
  if (!capabilities) return <EmptyState text="No readiness scan is available yet." />;
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
          <span className="text-xs text-muted">Needs attention</span>
          <strong className="mt-1 block text-xl">{capabilities.unsupported.length}</strong>
        </button>
      </div>
      <ActionChipGrid actions={filter === 'supported' ? capabilities.supported : capabilities.unsupported} />
    </div>
  );
}

function ActionTile({ icon: Icon, title, text }: { icon: LucideIcon; title: string; text: string }) {
  return (
    <article className="action-tile">
      <Icon size={18} aria-hidden="true" />
      <div>
        <strong>{title}</strong>
        <p>{text}</p>
      </div>
    </article>
  );
}

function ClientReadinessTab({
  capabilities,
  scanReport,
  scanning,
  onRunScan,
  vertical,
}: {
  capabilities: CapabilitiesSummary | null;
  scanReport: ReadinessReport | null;
  scanning: boolean;
  onRunScan: () => void;
  vertical: CrmVerticalDefinition;
}) {
  return (
    <div className="tab-content fade-in">
      <section className="section-row">
        <div>
          <h2 className="text-base font-semibold">Readiness checks</h2>
          <p className="mt-1 text-sm text-muted">
            Plain checks for {vertical.entityLabelPlural}, source coverage, handoff points, and allowed actions.
          </p>
        </div>
        <Button variant="secondary" disabled={scanning} icon={ShieldCheck} onClick={onRunScan}>
          {scanning ? 'Scanning...' : 'Run readiness scan'}
        </Button>
      </section>
      <div className="grid gap-3 md:grid-cols-3">
        <MetricCard label="Platform" value={scanReport?.platform || capabilities?.platform || 'unknown'} detail={`${percent(scanReport?.platform_confidence ?? capabilities?.platform_confidence ?? 0)}% confidence`} />
        <MetricCard label="Supported checks" value={capabilities?.supported.length ?? 0} detail={`${vertical.label} actions`} />
        <MetricCard label="Unsupported checks" value={capabilities?.unsupported.length ?? 0} detail="Needs adapter or crawl work" />
      </div>
      <Panel title="Capability report">
        {scanReport?.capabilities.length ? (
          <div className="capability-grid">
            {scanReport.capabilities.map((capability) => (
              <CapabilityReportCard key={capability.name} capability={capability} />
            ))}
          </div>
        ) : (
          <EmptyState text="Run the readiness scanner to generate a readable capability report." />
        )}
      </Panel>
      <div className="grid gap-4 xl:grid-cols-[0.8fr_1.2fr] items-start">
        <Panel title="Supported customer actions">
          <ActionChipGrid actions={capabilities?.allowed_actions ?? []} />
        </Panel>
        <TechnicalDetails title="Advanced readiness JSON" data={scanReport} />
      </div>
    </div>
  );
}

function CapabilityReportCard({ capability }: { capability: ReadinessReport['capabilities'][number] }) {
  const Icon = capability.supported ? CheckCircle2 : capability.confidence >= 0.5 ? AlertTriangle : XCircle;
  const tone = capability.supported ? 'ok' : capability.confidence >= 0.5 ? 'warn' : 'bad';
  return (
    <article className={`capability-card capability-card-${tone}`}>
      <div className="capability-card-head">
        <Icon size={18} aria-hidden="true" />
        <StatusPill value={capability.supported ? 'supported' : 'needs work'} />
      </div>
      <h3>{labelize(capability.name)}</h3>
      <strong>{percent(capability.confidence)}% confidence</strong>
      <p>{capability.evidence || 'No scanner evidence was saved for this check.'}</p>
    </article>
  );
}

function ActionChipGrid({ actions }: { actions: string[] }) {
  if (!actions.length) return <EmptyState text="No UI actions are allowed yet." />;
  return (
    <div className="action-chip-grid">
      {actions.map((action) => (
        <span key={action} className="action-chip">
          {ACTION_LABELS[action] || labelize(action)}
        </span>
      ))}
    </div>
  );
}

function ClientCatalogTab({
  products,
  loading,
  error,
  fallbackCount,
  totalProducts,
  crawling,
  onTriggerCrawl,
  vertical,
}: {
  products: DisplayProduct[];
  loading: boolean;
  error: string;
  fallbackCount: number;
  totalProducts: number;
  crawling: boolean;
  onTriggerCrawl: () => void;
  vertical: CrmVerticalDefinition;
}) {
  const [query, setQuery] = useState('');
  const [category, setCategory] = useState('all');
  const [vectorFilter, setVectorFilter] = useState('all');
  const [page, setPage] = useState(1);
  const categories = useMemo(() => uniqueProductCategories(products), [products]);
  const visibleProducts = useMemo(
    () => filterProducts(products, query, category, vectorFilter),
    [category, products, query, vectorFilter],
  );
  const pageCount = Math.max(1, Math.ceil(visibleProducts.length / CATALOG_PAGE_SIZE));
  const pageProducts = visibleProducts.slice((page - 1) * CATALOG_PAGE_SIZE, page * CATALOG_PAGE_SIZE);

  useEffect(() => {
    setPage(1);
  }, [category, query, vectorFilter]);

  useEffect(() => {
    if (page > pageCount) setPage(pageCount);
  }, [page, pageCount]);

  return (
    <div className="tab-content fade-in">
      <section className="section-row">
        <div>
          <h2 className="text-base font-semibold">{activeEntityTitle(vertical)} review</h2>
          <p className="mt-1 text-sm text-muted">
            Media, source data, category grouping, and vector status in one focused view.
          </p>
        </div>
        <CrawlButton label="Crawl now" active={crawling} onTriggerCrawl={onTriggerCrawl} />
      </section>
      {error ? <NoticeBanner tone="info" message={`${error} ${fallbackCount ? `Using ${fallbackCount} preview rows.` : ''}`} /> : null}
      <div className="grid gap-3 md:grid-cols-3">
        <MetricCard label={`Loaded ${vertical.entityLabelPlural}`} value={products.length} detail={`${number(totalProducts)} total active`} />
        <MetricCard label="Visible after filters" value={visibleProducts.length} detail={loading ? 'Refreshing catalog' : `Page ${page} of ${pageCount}`} />
        <MetricCard label="Categories" value={categories.length} detail={`Detected in loaded ${vertical.entityLabelPlural}`} />
      </div>
      <div className="catalog-toolbar">
        <label className="field catalog-search-field">
          <span>Search {vertical.entityLabelPlural}</span>
          <div className="input-with-icon">
            <Search size={15} aria-hidden="true" />
            <input value={query} placeholder="Name, brand, or description" onChange={(event) => setQuery(event.currentTarget.value)} />
          </div>
        </label>
        <label className="field">
          <span>Category</span>
          <select value={category} onChange={(event) => setCategory(event.currentTarget.value)}>
            <option value="all">All categories</option>
            {categories.map((item) => (
              <option key={item} value={item}>
                {item}
              </option>
            ))}
          </select>
        </label>
        <label className="field">
          <span>Vector state</span>
          <select value={vectorFilter} onChange={(event) => setVectorFilter(event.currentTarget.value)}>
            <option value="all">All rows</option>
            <option value="vectorized">Vectorized</option>
            <option value="pending">Pending vector</option>
            <option value="in_stock">In stock</option>
            <option value="out_of_stock">Out of stock</option>
          </select>
        </label>
      </div>
      {pageProducts.length ? (
        <>
          <div className="product-gallery">
            {pageProducts.map((product) => (
              <CatalogProductCard key={product.id} product={product} />
            ))}
          </div>
          <PaginationControl page={page} pageCount={pageCount} onPageChange={setPage} />
        </>
      ) : loading ? (
        <div className="product-gallery">
          {Array.from({ length: 6 }).map((_, index) => (
            <SkeletonCard key={index} height={320} />
          ))}
        </div>
      ) : (
        <EmptyState title={`No ${vertical.entityLabelPlural} match`} message="Adjust the search, category, or vector filters to widen this view." />
      )}
    </div>
  );
}

function CatalogProductCard({ product }: { product: DisplayProduct }) {
  return (
    <article className="catalog-product-card">
      <ProductImage product={product} />
      <div className="catalog-product-body">
        <div className="flex items-start justify-between gap-3">
          <div>
            <span className="text-xs font-semibold uppercase text-muted">{product.brand || product.category}</span>
            <h3>{product.name}</h3>
          </div>
          <StatusPill value={product.vectorized ? 'vectorized' : 'pending vector'} />
        </div>
        <p>{product.description || `${product.category} product indexed for AI shopping.`}</p>
        <div className="catalog-product-meta">
          <strong>{money(product.price)}</strong>
          <span>{product.stock == null ? 'Stock unknown' : `${number(product.stock)} in stock`}</span>
          {product.rating != null ? <span>{product.rating.toFixed(1)} rating</span> : null}
        </div>
      </div>
    </article>
  );
}

function PaginationControl({
  page,
  pageCount,
  onPageChange,
}: {
  page: number;
  pageCount: number;
  onPageChange: (page: number) => void;
}) {
  return (
    <div className="pagination-control">
      <Button variant="secondary" disabled={page <= 1} onClick={() => onPageChange(page - 1)}>
        Previous
      </Button>
      <span>
        Page {page} of {pageCount}
      </span>
      <Button variant="secondary" disabled={page >= pageCount} onClick={() => onPageChange(page + 1)}>
        Next
      </Button>
    </div>
  );
}

function ProductImage({ product }: { product: DisplayProduct }) {
  const [failed, setFailed] = useState(false);
  if (!product.imageUrl || failed) {
    return (
      <div className="catalog-product-fallback">
        <PackageOpen size={28} aria-hidden="true" />
        <span>{product.category || 'Product'}</span>
      </div>
    );
  }
  return <img className="catalog-product-image" src={product.imageUrl} alt={product.name} loading="lazy" onError={() => setFailed(true)} />;
}

function ClientCrawlTab({
  client,
  crawlReport,
  crawling,
  onTriggerCrawl,
  vertical,
}: {
  client: Client;
  crawlReport: CrawlReport | null;
  crawling: boolean;
  onTriggerCrawl: () => void;
  vertical: CrmVerticalDefinition;
}) {
  return (
    <div className="tab-content fade-in">
      <section className="section-row">
        <div>
          <h2 className="text-base font-semibold">Crawl history</h2>
          <p className="mt-1 text-sm text-muted">Coverage, failures, blocked pages, and recent sync runs.</p>
        </div>
        <CrawlButton label="Start crawl" active={crawling} onTriggerCrawl={onTriggerCrawl} />
      </section>
      <CrawlReportSummary report={crawlReport} vertical={vertical} />
      <div className="grid gap-4 xl:grid-cols-[1.1fr_0.9fr]">
        <Panel title="Priority crawl details">
          {crawlReport ? (
            <div className="grid gap-4">
              <Meter label="Coverage score" value={percent(crawlReport.coverage_score)} tone="accent" />
              <div className="grid gap-3 sm:grid-cols-3">
                <MiniMetric label="Visited pages" value={crawlReport.pages_visited} />
                <MiniMetric label="Failed pages" value={crawlReport.pages_failed} />
                <MiniMetric label="Blocked pages" value={crawlReport.pages_blocked} />
              </div>
              <UrlList title="Failed URLs" urls={crawlReport.failed_urls} />
              <UrlList title="Blocked URLs" urls={crawlReport.blocked_urls} />
              <TechnicalDetails title="Advanced crawl JSON" data={crawlReport} />
            </div>
          ) : (
            <EmptyState text="No crawl report is saved yet. Run a crawl to generate one." />
          )}
        </Panel>
        <Panel title="Sync run history">
          <SyncRunTimeline runs={client.sync_runs ?? []} />
        </Panel>
      </div>
    </div>
  );
}

function CrawlReportSummary({ report, vertical }: { report: CrawlReport | null; vertical: CrmVerticalDefinition }) {
  if (!report) return <EmptyState text="Crawl report will appear here after the next priority crawl." />;
  return (
    <div className="grid gap-3 md:grid-cols-2 2xl:grid-cols-5">
      <MetricCard label={`${activeEntityTitle(vertical)} found`} value={report.product_count} detail="Extracted source rows" />
      <MetricCard label="Variants found" value={report.variant_count} detail="Entity options" />
      <MetricCard label="Categories found" value={report.category_count} detail="Navigation coverage" />
      <MetricCard label="Duration" value={`${number(report.duration_ms)} ms`} detail={shortTime(report.created_at)} />
      <MetricCard label="Stopped by limit" value={report.stopped_by_limit ? 'Yes' : 'No'} detail={report.source_type || 'crawler'} />
    </div>
  );
}

function SyncRunTimeline({ runs }: { runs: SyncRun[] }) {
  if (!runs.length) return <EmptyState text="No sync runs are recorded yet." />;
  return (
    <div className="sync-timeline">
      {runs.map((run) => (
        <article key={`${run.id}-${run.created_at}`} className="sync-run-card">
          <div className="sync-run-dot" />
          <div>
            <div className="flex flex-wrap items-center justify-between gap-2">
              <strong>{run.source_name || 'catalog sync'}</strong>
              <span className="text-xs text-muted">{shortTime(run.created_at)}</span>
            </div>
            <div className="sync-run-metrics">
              <span>{number(run.source_count)} sourced</span>
              <span>{number(run.changed_count)} changed</span>
              <span>{number(run.vectorized_count)} vectorized</span>
              <span>{number(run.deactivated_count)} inactive</span>
            </div>
          </div>
        </article>
      ))}
    </div>
  );
}

function UrlList({ title, urls }: { title: string; urls: string[] }) {
  const [open, setOpen] = useState(false);
  if (!urls.length) return null;
  return (
    <div className="url-list">
      <button className="summary-toggle" type="button" onClick={() => setOpen((current) => !current)}>
        <ChevronDown className={open ? 'open' : ''} size={16} aria-hidden="true" />
        <span>{title} ({urls.length})</span>
      </button>
      {open ? (
        <div className="grid gap-2 pt-3">
        {urls.slice(0, 12).map((url) => (
          <code key={url}>{url}</code>
        ))}
        </div>
      ) : null}
    </div>
  );
}

function ClientActivityTab({ client, recentActivity }: { client: Client; recentActivity: UsageEvent[] }) {
  const tokenLimit = client.quota.client.limit || client.token_limit || 0;
  const tokenUsed = client.quota.client.used || client.usage.tokens_estimated || 0;
  const tokenRemaining = client.quota.client.remaining || Math.max(0, tokenLimit - tokenUsed);
  const tokenPct = tokenLimit ? Math.round((tokenUsed / tokenLimit) * 100) : 0;

  return (
    <div className="tab-content fade-in">
      <div className="grid gap-3 md:grid-cols-3">
        <MetricCard label="Total turns" value={client.usage.total_turns} detail="All time" />
        <MetricCard label="Turns today" value={client.usage.turns_today} detail="Since midnight" />
        <MetricCard label="Avg latency" value={`${number(client.usage.avg_latency_ms)} ms`} detail="Voice response" />
      </div>
      <div className="activity-insight-grid">
        <Panel title="Recent customer activity">
          <ActivityList items={recentActivity} />
          {recentActivity.length > 0 && recentActivity.length < 5 ? (
            <div className="activity-nudge">
              More activity will appear as your AI widget receives traffic.
            </div>
          ) : null}
        </Panel>
        <section className="card token-burn-card">
          <div className="card-header">
            <div>
              <h3>Token burn</h3>
              <span className="card-meta">Client quota pressure</span>
            </div>
            <span className="badge badge-blue">{number(tokenPct)}%</span>
          </div>
          <div className="token-burn-meter">
            <span style={{ width: `${Math.max(3, Math.min(100, tokenPct))}%` }} />
          </div>
          <div className="token-burn-stats">
            <KeyValue label="Used" value={`${number(tokenUsed)} tokens`} />
            <KeyValue label="Remaining" value={`${number(tokenRemaining)} tokens`} />
            <KeyValue label="Session cap" value={`${number(client.session_token_limit ?? 0)} tokens`} />
          </div>
        </section>
      </div>
    </div>
  );
}

function VerticalExtensionTab({
  tab,
  vertical,
}: {
  tab: ClientWorkspaceTabDefinition;
  vertical: CrmVerticalDefinition;
}) {
  return (
    <div className="tab-content fade-in">
      <section className="section-row">
        <div>
          <h2 className="text-base font-semibold">{tab.label}</h2>
          <p className="mt-1 text-sm text-muted">
            {vertical.label} workspace for {vertical.entityLabelPlural}.
          </p>
        </div>
        <StatusPill value={vertical.riskLevel} />
      </section>
      <div className="grid gap-4 xl:grid-cols-2">
        <Panel title="Entity model">
          <ActionChipGrid actions={vertical.entityTypes} />
        </Panel>
        <Panel title="Readiness focus">
          <ActionChipGrid actions={vertical.readinessChecks} />
        </Panel>
      </div>
      <Panel title={`${tab.label} records`}>
        <EmptyState
          title="No records yet"
          message={`No ${tab.label.toLowerCase()} records are loaded for this client yet.`}
        />
      </Panel>
    </div>
  );
}

function ClientControlsTab({
  client,
  scanning,
  crawling,
  onCopyScript,
  onTriggerCrawl,
  onRunScan,
  onRemoveClient,
  onToggleClient,
  onUpdateTokenLimits,
  onOpenPasswordDialog,
  onViewChange,
}: {
  client: Client;
  scanning: boolean;
  crawling: boolean;
  onCopyScript: (client: Client) => Promise<void>;
  onTriggerCrawl: (siteId: string) => void;
  onRunScan: () => void;
  onRemoveClient: (siteId: string) => void;
  onToggleClient: (siteId: string, enabled: boolean) => void;
  onUpdateTokenLimits: (siteId: string, tokenLimit: number, sessionTokenLimit: number) => Promise<void>;
  onOpenPasswordDialog: (client: Client) => void;
  onViewChange: (view: View) => void;
}) {
  return (
    <div className="tab-content fade-in">
      <div className="control-card-grid">
        <Panel title="Operator controls">
          <div className="control-grid">
            <CopyScriptButton client={client} onCopyScript={onCopyScript} />
            <CrawlButton siteId={client.site_id} label="Run crawler" active={crawling} onTriggerCrawl={onTriggerCrawl} />
            <Button variant="secondary" icon={ClipboardCheck} disabled={scanning} onClick={onRunScan}>
              {scanning ? 'Scanning...' : 'Run readiness'}
            </Button>
            <Button variant="secondary" icon={Settings} onClick={() => onViewChange('settings')}>
              Global settings
            </Button>
            <Button variant="secondary" icon={Eye} onClick={() => onToggleClient(client.site_id, client.status !== 'live')}>
              {client.status === 'live' ? 'Disable widget' : 'Enable widget'}
            </Button>
          </div>
        </Panel>
        <div className="card">
          <div className="card-header">
            <h3>Client Panel</h3>
            <span className="card-meta">Client-facing</span>
          </div>
          <p style={{ fontSize: 13, color: 'var(--muted)', margin: '0 0 14px' }}>
            Direct your client to their analytics panel. They log in with their site ID and the panel password you set.
          </p>
          <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
            <a
              href={`/client-panel/${client.site_id}`}
              target="_blank"
              rel="noopener noreferrer"
              className="btn btn-secondary"
            >
              <Eye size={14} aria-hidden="true" /> Open client panel
            </a>
            <button className="btn btn-ghost" type="button" onClick={() => onOpenPasswordDialog(client)}>
              <KeyRound size={14} aria-hidden="true" /> Manage password
            </button>
          </div>
        </div>
      </div>
      <div className="control-card-grid">
        <TokenLimitsPanel client={client} onUpdateTokenLimits={onUpdateTokenLimits} />
        <Panel title="Runtime limits and install">
          <KeyValue label="Client token limit" value={client.token_limit} />
          <KeyValue label="Session token limit" value={client.session_token_limit} />
          <KeyValue label="Panel password" value={panelPasswordLabel(client)} />
          <KeyValue label="Widget status" value={client.status} />
          <KeyValue label="Crawler status" value={client.last_crawl_status || 'not_started'} />
          <pre className="code-block install-script mt-4">{client.script_tag}</pre>
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
            label="Per shopper/session limit"
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

function MetricCard({
  label,
  value,
  detail,
  onClick,
}: {
  label: string;
  value: string | number;
  detail: string;
  onClick?: () => void;
}) {
  const content = (
    <>
      <span className="text-xs font-semibold text-muted">{label}</span>
      <strong className="mt-2 block truncate text-2xl font-semibold">{typeof value === 'number' ? number(value) : value}</strong>
      <small className="mt-1 block text-xs text-muted">{detail}</small>
    </>
  );
  if (onClick) {
    return (
      <button className="card interactive text-left" type="button" onClick={onClick}>
        {content}
      </button>
    );
  }
  return <div className="card">{content}</div>;
}

export function MiniMetric({ label, value }: { label: string; value: number }) {
  return (
    <div className="rounded-lg border border-line bg-soft p-3">
      <span className="text-xs text-muted">{label}</span>
      <strong className="mt-1 block text-xl">{number(value)}</strong>
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

function Meter({ label, value, tone }: { label: string; value: number; tone: 'accent' | 'danger' }) {
  return (
    <div className="grid gap-2">
      <div className="flex items-center justify-between gap-3 text-sm">
        <span className="text-muted">{label}</span>
        <strong>{number(value)}%</strong>
      </div>
      <div className={`meter meter-${tone}`}>
        <span style={{ width: `${Math.max(0, Math.min(100, value))}%` }} />
      </div>
    </div>
  );
}

function SkeletonCard({ height = 120 }: { height?: number }) {
  return <div className="skeleton" style={{ height, borderRadius: 'var(--radius)' }} />;
}

function normalizeCatalogProduct(product: CatalogProduct | ProductPreview, index: number): DisplayProduct {
  const productId = 'product_id' in product ? product.product_id : undefined;
  const id = String(product.id ?? productId ?? `product-${index}`);
  const category = firstText(product.category_name, product.category, 'Uncategorized');
  return {
    id,
    name: firstText(product.name, `Product ${index + 1}`),
    brand: firstText(product.brand, ''),
    category,
    description: 'description' in product ? firstText(product.description, '') : '',
    price: Number(product.price ?? 0),
    stock: typeof product.stock === 'number' ? product.stock : null,
    imageUrl: firstText(product.image_url, ''),
    vectorized: 'has_embedding' in product ? Boolean(product.has_embedding) : true,
    rating: 'rating' in product && typeof product.rating === 'number' ? product.rating : null,
    reviewCount: 'review_count' in product && typeof product.review_count === 'number' ? product.review_count : null,
  };
}

function uniqueProductCategories(products: DisplayProduct[]) {
  return Array.from(new Set(products.map((product) => product.category).filter(Boolean))).sort((left, right) =>
    left.localeCompare(right),
  );
}

function filterProducts(products: DisplayProduct[], query: string, category: string, vectorFilter: string) {
  const search = query.trim().toLowerCase();
  return products.filter((product) => {
    const matchesSearch =
      !search ||
      [product.name, product.brand, product.category, product.description].some((value) =>
        value.toLowerCase().includes(search),
      );
    const matchesCategory = category === 'all' || product.category === category;
    const matchesVector =
      vectorFilter === 'all' ||
      (vectorFilter === 'vectorized' && product.vectorized) ||
      (vectorFilter === 'pending' && !product.vectorized) ||
      (vectorFilter === 'in_stock' && (product.stock ?? 0) > 0) ||
      (vectorFilter === 'out_of_stock' && product.stock === 0);
    return matchesSearch && matchesCategory && matchesVector;
  });
}

function firstText(...values: Array<string | number | null | undefined>) {
  for (const value of values) {
    const text = String(value ?? '').trim();
    if (text) return text;
  }
  return '';
}

function isExtensionTab(tab: ClientWorkspaceTabId) {
  return !CORE_CLIENT_TAB_IDS.has(tab);
}

function activeEntityTitle(vertical: CrmVerticalDefinition) {
  const text = vertical.entityLabelPlural || 'items';
  return text.charAt(0).toUpperCase() + text.slice(1);
}

function normalizePositiveInteger(value: string) {
  const normalized = Math.max(1, Math.round(Number(value)));
  return String(Number.isFinite(normalized) ? normalized : 1);
}
