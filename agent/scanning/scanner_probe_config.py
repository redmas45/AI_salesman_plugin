"""Probe constants for AI readiness scanner platform detection."""

SCAN_TIMEOUT_SECONDS = 10
MAX_PROBE_URLS = 20

SHOPIFY_SIGNALS: tuple[tuple[str, str, float], ...] = (
    ("meta", r'content=["\']shopify', 0.4),
    ("html", r'cdn\.shopify\.com', 0.3),
    ("html", r'Shopify\.shop', 0.3),
    ("html", r'shopify-section', 0.2),
    ("header", r'x-shopify', 0.4),
)

WOOCOMMERCE_SIGNALS: tuple[tuple[str, str, float], ...] = (
    ("html", r'woocommerce', 0.3),
    ("html", r'wc-block', 0.2),
    ("html", r'wp-content/plugins/woocommerce', 0.4),
    ("html", r'wc_add_to_cart_params', 0.3),
    ("header", r'x-powered-by.*wordpress', 0.2),
)

SHOPIFY_CATALOG_PROBES: tuple[str, ...] = (
    "/products.json",
    "/collections/all/products.json",
)

WOOCOMMERCE_CATALOG_PROBES: tuple[str, ...] = (
    "/wp-json/wc/store/products?per_page=1",
    "/wp-json/wc/store/v1/products?per_page=1",
)

GENERIC_CATALOG_PROBES: tuple[str, ...] = (
    "/api/products",
    "/api/products.json",
)

SHOPIFY_CART_PROBES: tuple[str, ...] = (
    "/cart.js",
    "/cart/add.js",
)

WOOCOMMERCE_CART_PROBES: tuple[str, ...] = (
    "/wp-json/wc/store/cart",
)

GENERIC_CART_PROBES: tuple[str, ...] = (
    "/cart",
)

SHOPIFY_CHECKOUT_PROBES: tuple[str, ...] = (
    "/checkout",
)

WOOCOMMERCE_CHECKOUT_PROBES: tuple[str, ...] = (
    "/checkout",
)
