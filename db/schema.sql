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
