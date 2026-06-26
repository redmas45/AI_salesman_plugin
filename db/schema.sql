CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS categories (
    id      BIGINT PRIMARY KEY,
    name    TEXT NOT NULL,
    slug    TEXT NOT NULL,
    UNIQUE (name),
    UNIQUE (slug)
);

CREATE TABLE IF NOT EXISTS products (
    id              BIGINT PRIMARY KEY,
    variant_id      BIGINT,
    name            TEXT NOT NULL,
    brand           TEXT NOT NULL,
    category_id     BIGINT NOT NULL,
    description     TEXT NOT NULL,
    price           REAL NOT NULL,          -- INR
    original_price  REAL,                   -- INR (for discount display)
    color           TEXT,
    size_options    TEXT,                   -- JSON array e.g. '["S","M","L"]'
    tags            TEXT,                   -- JSON array e.g. '["casual","summer"]'
    rating          REAL DEFAULT 0.0,
    review_count    INTEGER DEFAULT 0,
    stock           INTEGER DEFAULT 100,
    image_url       TEXT,
    is_active       INTEGER DEFAULT 1,
    embedding       vector(384),
    FOREIGN KEY (category_id) REFERENCES categories(id)
);

CREATE TABLE IF NOT EXISTS catalog_source_products (
    source_name         TEXT NOT NULL,
    source_product_id   TEXT NOT NULL,
    product_id          BIGINT NOT NULL,
    name                TEXT NOT NULL,
    brand               TEXT,
    category            TEXT,
    price               REAL,
    stock               INTEGER,
    image_url           TEXT,
    raw_product         TEXT NOT NULL,
    is_active           INTEGER DEFAULT 1,
    last_seen_at        TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (source_name, source_product_id)
);

CREATE TABLE IF NOT EXISTS catalog_sync_runs (
    id                  SERIAL PRIMARY KEY,
    source_name         TEXT NOT NULL,
    source_count        INTEGER NOT NULL DEFAULT 0,
    changed_count       INTEGER NOT NULL DEFAULT 0,
    deactivated_count   INTEGER NOT NULL DEFAULT 0,
    vectorized_count    INTEGER NOT NULL DEFAULT 0,
    created_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_products_category ON products(category_id);
CREATE INDEX IF NOT EXISTS idx_products_price ON products(price);
CREATE INDEX IF NOT EXISTS idx_products_color ON products(color);
CREATE INDEX IF NOT EXISTS idx_products_rating ON products(rating DESC);
CREATE INDEX IF NOT EXISTS idx_products_embedding ON products USING hnsw (embedding vector_cosine_ops);
CREATE INDEX IF NOT EXISTS idx_catalog_source_products_source ON catalog_source_products(source_name, is_active);

CREATE TABLE IF NOT EXISTS cart (
    id          SERIAL PRIMARY KEY,
    product_id  BIGINT NOT NULL,
    quantity    INTEGER NOT NULL DEFAULT 1,
    added_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (product_id) REFERENCES products(id)
);

CREATE TABLE IF NOT EXISTS user_profile (
    id              SERIAL PRIMARY KEY,
    address         TEXT,
    payment_method  TEXT,
    preferences     TEXT
);

-- Phase 2: Product Variants
CREATE TABLE IF NOT EXISTS product_variants (
    id              BIGINT PRIMARY KEY,
    product_id      BIGINT NOT NULL,
    sku             TEXT,
    title           TEXT NOT NULL,
    option1_name    TEXT,
    option1_value   TEXT,
    option2_name    TEXT,
    option2_value   TEXT,
    option3_name    TEXT,
    option3_value   TEXT,
    price           REAL NOT NULL,
    compare_at_price REAL,
    stock           INTEGER DEFAULT 0,
    available       BOOLEAN DEFAULT true,
    image_url       TEXT,
    cart_id         TEXT,
    position        INTEGER DEFAULT 0,
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_product_variants_product ON product_variants(product_id);
CREATE INDEX IF NOT EXISTS idx_product_variants_sku ON product_variants(sku);

CREATE TABLE IF NOT EXISTS knowledge_sources (
    id              TEXT PRIMARY KEY,
    source_type     TEXT NOT NULL,
    source_name     TEXT NOT NULL,
    source_url      TEXT NOT NULL DEFAULT '',
    status          TEXT NOT NULL DEFAULT 'active',
    metadata_json   TEXT NOT NULL DEFAULT '{}',
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS knowledge_items (
    id                  TEXT PRIMARY KEY,
    external_id         TEXT NOT NULL DEFAULT '',
    entity_type         TEXT NOT NULL,
    title               TEXT NOT NULL,
    subtitle            TEXT NOT NULL DEFAULT '',
    summary             TEXT NOT NULL DEFAULT '',
    body                TEXT NOT NULL DEFAULT '',
    url                 TEXT NOT NULL DEFAULT '',
    image_url           TEXT NOT NULL DEFAULT '',
    source_id           TEXT NOT NULL DEFAULT '',
    attributes_json     TEXT NOT NULL DEFAULT '{}',
    pricing_json        TEXT NOT NULL DEFAULT '{}',
    availability_json   TEXT NOT NULL DEFAULT '{}',
    location_json       TEXT NOT NULL DEFAULT '{}',
    contact_json        TEXT NOT NULL DEFAULT '{}',
    policy_json         TEXT NOT NULL DEFAULT '{}',
    risk_tags_json      TEXT NOT NULL DEFAULT '[]',
    is_active           INTEGER NOT NULL DEFAULT 1,
    embedding           vector(384),
    last_seen_at        TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_knowledge_items_type
    ON knowledge_items(entity_type, is_active);
CREATE INDEX IF NOT EXISTS idx_knowledge_items_source
    ON knowledge_items(source_id, is_active);
CREATE INDEX IF NOT EXISTS idx_knowledge_items_embedding
    ON knowledge_items USING hnsw (embedding vector_cosine_ops);

-- Phase 3: Crawl Report storage
ALTER TABLE catalog_sync_runs ADD COLUMN IF NOT EXISTS report_json TEXT NOT NULL DEFAULT '';
