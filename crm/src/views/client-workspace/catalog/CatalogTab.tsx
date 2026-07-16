import { useEffect, useMemo, useState } from 'react';
import { Gauge, PackageOpen, Search } from 'lucide-react';
import { Button } from '../../../components/ui/Button';
import { StatusPill } from '../../../components/ui/Badge';
import { EmptyState } from '../../../components/ui/EmptyState';
import { NoticeBanner } from '../../../components/shared/NoticeBanner';
import { PaginationControl } from '../../../components/shared/controls/PaginationControl';
import { money, number } from '../../../utils/format';
import type { ClientWorkspaceTabId, CrmVerticalDefinition } from '../../../verticals/types';
import { MetricCard, SkeletonCard } from '../components/workspaceCards';
import type { DisplayProduct } from './catalogProducts';

const CATALOG_PAGE_SIZE = 6;

export function ClientCatalogTab({
  products,
  loading,
  error,
  fallbackCount,
  totalProducts,
  onOpenTab,
  vertical,
}: {
  products: DisplayProduct[];
  loading: boolean;
  error: string;
  fallbackCount: number;
  totalProducts: number;
  onOpenTab: (tab: ClientWorkspaceTabId) => void;
  vertical: CrmVerticalDefinition;
}) {
  const [query, setQuery] = useState('');
  const [category, setCategory] = useState('all');
  const [vectorFilter, setVectorFilter] = useState('all');
  const [page, setPage] = useState(1);
  const categories = useMemo(() => uniqueProductCategories(products), [products]);
  const categoryCounts = useMemo(() => productCategoryCounts(products), [products]);
  const visibleProducts = useMemo(
    () => filterProducts(products, query, category, vectorFilter),
    [category, products, query, vectorFilter],
  );
  const vectorizedCount = products.filter((product) => product.vectorized).length;
  const pendingVectorCount = Math.max(0, products.length - vectorizedCount);
  const inStockCount = products.filter((product) => product.stock == null || product.stock > 0).length;
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
        <Button variant="secondary" icon={Gauge} onClick={() => onOpenTab('crawl')}>
          Crawl report
        </Button>
      </section>
      {error ? <NoticeBanner tone="info" message={`${error} ${fallbackCount ? `Using ${fallbackCount} preview rows.` : ''}`} /> : null}
      <div className="data-health-grid">
        <DataHealthCard label="Vectorized" value={`${number(vectorizedCount)}/${number(products.length)}`} detail={`${number(pendingVectorCount)} pending vectors`} tone={pendingVectorCount ? 'warn' : 'ok'} onClick={() => setVectorFilter(pendingVectorCount ? 'pending' : 'vectorized')} />
        <DataHealthCard label="Availability" value={`${number(inStockCount)} usable`} detail={`${number(Math.max(0, products.length - inStockCount))} out of stock`} tone="neutral" onClick={() => setVectorFilter('in_stock')} />
        <DataHealthCard label="Source groups" value={number(categories.length)} detail="Filter by group below" tone="neutral" onClick={() => setCategory('all')} />
      </div>
      <div className="grid gap-3 md:grid-cols-3">
        <MetricCard
          label={`Loaded ${vertical.entityLabelPlural}`}
          value={products.length}
          detail={`${number(totalProducts)} total active`}
          onClick={() => {
            setQuery('');
            setCategory('all');
            setVectorFilter('all');
            onOpenTab('catalog');
          }}
        />
        <MetricCard
          label="Visible after filters"
          value={visibleProducts.length}
          detail={loading ? 'Refreshing catalog' : `Page ${page} of ${pageCount}`}
          onClick={() => setPage(1)}
        />
        <MetricCard
          label="Groups"
          value={categories.length}
          detail={`Click a group below to filter ${vertical.entityLabelPlural}`}
          onClick={() => setCategory('all')}
        />
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
      {categories.length ? (
        <details className="crm-disclosure category-group-disclosure" open={categories.length <= 8 || category !== 'all'}>
          <summary>
            <span>{vertical.entityLabelPlural} groups</span>
            <strong>{category === 'all' ? `${number(categories.length)} groups` : category}</strong>
          </summary>
          <div className="category-group-panel" aria-label={`${vertical.entityLabelPlural} groups`}>
            <button
              className={`category-group-chip ${category === 'all' ? 'active' : ''}`}
              type="button"
              onClick={() => setCategory('all')}
            >
              All groups <span>{number(products.length)}</span>
            </button>
            {categories.map((item) => (
              <button
                key={item}
                className={`category-group-chip ${category === item ? 'active' : ''}`}
                type="button"
                onClick={() => setCategory(item)}
              >
                {item} <span>{number(categoryCounts[item] ?? 0)}</span>
              </button>
            ))}
          </div>
        </details>
      ) : null}
      {pageProducts.length ? (
        <>
          <div className="product-gallery">
            {pageProducts.map((product) => (
              <CatalogProductCard key={product.id} product={product} vertical={vertical} />
            ))}
          </div>
          <PaginationControl
            page={page}
            pageCount={pageCount}
            pageSize={CATALOG_PAGE_SIZE}
            totalItems={visibleProducts.length}
            itemLabel={vertical.entityLabelPlural}
            onPageChange={setPage}
          />
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

function DataHealthCard({
  label,
  value,
  detail,
  tone,
  onClick,
}: {
  label: string;
  value: string | number;
  detail: string;
  tone: 'ok' | 'warn' | 'neutral';
  onClick: () => void;
}) {
  return (
    <button className={`data-health-card ${tone}`} type="button" onClick={onClick}>
      <span>{label}</span>
      <strong>{value}</strong>
      <small>{detail}</small>
    </button>
  );
}

function CatalogProductCard({ product, vertical }: { product: DisplayProduct; vertical: CrmVerticalDefinition }) {
  return (
    <article className="catalog-product-card">
      <ProductImage product={product} vertical={vertical} />
      <div className="catalog-product-body">
        <div className="flex items-start justify-between gap-3">
          <div>
            <span className="text-xs font-semibold uppercase text-muted">{product.brand || product.category}</span>
            <h3>{product.name}</h3>
          </div>
          <StatusPill value={product.vectorized ? 'vectorized' : 'pending vector'} />
        </div>
        <p>{product.description || `${product.category} ${vertical.entityLabelSingular} indexed for Maya.`}</p>
        <div className="catalog-product-meta">
          <strong>{money(product.price)}</strong>
          <span>{product.stock == null ? 'Stock unknown' : `${number(product.stock)} in stock`}</span>
          {product.rating != null ? <span>{product.rating.toFixed(1)} rating</span> : null}
        </div>
      </div>
    </article>
  );
}


function ProductImage({ product, vertical }: { product: DisplayProduct; vertical: CrmVerticalDefinition }) {
  const [failed, setFailed] = useState(false);
  if (!product.imageUrl || failed) {
    return (
      <div className="catalog-product-fallback">
        <PackageOpen size={28} aria-hidden="true" />
        <span>{product.category || vertical.entityLabelSingular}</span>
      </div>
    );
  }
  return <img className="catalog-product-image" src={product.imageUrl} alt={product.name} loading="lazy" onError={() => setFailed(true)} />;
}

function uniqueProductCategories(products: DisplayProduct[]) {
  return Array.from(new Set(products.map((product) => product.category).filter(Boolean))).sort((left, right) =>
    left.localeCompare(right),
  );
}

function productCategoryCounts(products: DisplayProduct[]) {
  return products.reduce<Record<string, number>>((counts, product) => {
    const category = product.category || 'Uncategorized';
    counts[category] = (counts[category] ?? 0) + 1;
    return counts;
  }, {});
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

function activeEntityTitle(vertical: CrmVerticalDefinition) {
  const text = vertical.entityLabelPlural || 'items';
  return text.charAt(0).toUpperCase() + text.slice(1);
}
