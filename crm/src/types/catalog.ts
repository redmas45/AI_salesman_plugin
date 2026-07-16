export interface CatalogSource {
  source_name?: string;
  active_products?: number;
  total_products?: number;
  last_seen_at?: string;
}

export interface SyncRun {
  id?: number;
  source_name?: string;
  source_count?: number;
  changed_count?: number;
  deactivated_count?: number;
  vectorized_count?: number;
  created_at?: string;
}

export interface CatalogSummary {
  total_products: number;
  active_products: number;
  missing_embeddings: number;
  categories?: number;
  sources?: CatalogSource[];
  last_sync?: SyncRun | null;
  error?: string;
}

export interface ProductPreview {
  id?: string | number;
  product_id?: string | number;
  name?: string;
  brand?: string;
  category?: string;
  category_name?: string;
  price?: number;
  stock?: number;
  image_url?: string | null;
  is_active?: boolean | number;
  has_embedding?: boolean | number;
}

export interface CatalogProduct {
  id: string;
  name: string;
  brand?: string;
  category_name?: string;
  category?: string;
  description?: string;
  price: number;
  original_price?: number | null;
  rating?: number;
  review_count?: number;
  stock?: number;
  image_url?: string | null;
  has_embedding?: boolean | number;
}

export interface KnowledgeStats {
  total_items: number;
  active_items: number;
  missing_embeddings: number;
  entity_types: number;
}

export interface KnowledgeItem {
  id: string;
  external_id?: string;
  entity_type: string;
  title: string;
  subtitle?: string;
  summary?: string;
  body?: string;
  url?: string;
  image_url?: string;
  source_id?: string;
  attributes?: Record<string, unknown>;
  pricing?: Record<string, unknown>;
  availability?: Record<string, unknown>;
  has_embedding?: boolean | number;
  updated_at?: string;
}

export interface KnowledgeResponse {
  stats: KnowledgeStats;
  items: KnowledgeItem[];
}
