import type { CatalogProduct, ProductPreview } from '../../../types';

export const CATALOG_PAGE_LIMIT = 1000;

export interface DisplayProduct {
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

export function normalizeCatalogProduct(product: CatalogProduct | ProductPreview, index: number): DisplayProduct {
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

function firstText(...values: Array<string | number | null | undefined>): string {
  for (const value of values) {
    const text = String(value ?? '').trim();
    if (text) return text;
  }
  return '';
}
