export const ACTIONS = Object.freeze({
  ADD_TO_CART: "ADD_TO_CART",
  CHECKOUT: "CHECKOUT",
  CLEAR_CART: "CLEAR_CART",
  FILTER_PRODUCTS: "FILTER_PRODUCTS",
  NAVIGATE_TO: "NAVIGATE_TO",
  REMOVE_FROM_CART: "REMOVE_FROM_CART",
  SHOW_COMPARISON: "SHOW_COMPARISON",
  SHOW_PRODUCT_DETAIL: "SHOW_PRODUCT_DETAIL",
  SHOW_PRODUCTS: "SHOW_PRODUCTS",
  UPDATE_CART_QUANTITY: "UPDATE_CART_QUANTITY",
});

export const ACTION_PARAMS = Object.freeze({
  PAGE: "page",
  PRODUCT_ID: "product_id",
  PRODUCT_IDS: "product_ids",
  QUANTITY: "quantity",
  SEARCH_QUERY: "search_query",
});

export const CART_PAGE_TARGETS = new Set(["cart", "/cart"]);
export const DEFAULT_RECOMMENDATION_TITLE = "Recommended products";

export const API_PATHS = Object.freeze({
  PRODUCTS_BY_IDS: "/v1/products/by-ids",
  SHOP: "/v1/shop",
  SHOP_WS: "/v1/ws/shop",
});

export const AUDIO = Object.freeze({
  DATA_WAV_PREFIX: "data:audio/wav;base64,",
  WEBM_FILENAME: "audio.webm",
  WEBM_MIME_TYPE: "audio/webm",
});

export const HTTP_METHODS = Object.freeze({
  POST: "POST",
});

export const STATUS = Object.freeze({
  ERROR: "error",
  PROCESSING: "processing",
  READY: "ready",
  RECORDING: "recording",
});

export const CONVERSATION_HISTORY_LIMIT = 12;
export const DEFAULT_VISIBLE_RESET_DELAY_MS = 2400;
export const AUTO_GREETING_DELAY_MS = 900;
export const AUTO_GREETING_VISIBLE_MS = 4200;
export const DEFAULT_CART_QUANTITY = 1;
export const OVERLAY_COLLAPSE_DELAY_MS = 180;

export const EVENTS = Object.freeze({
  SHOPBOT_ACTION: "shopbot:action",
});

export const WS_CONNECT_TIMEOUT_MS = 2500;

export const WS_MESSAGES = Object.freeze({
  AUDIO_CHUNK: "audio_chunk",
  AUDIO_END: "audio_end",
  CONFIG: "config",
  DONE: "done",
  ERROR: "error",
  TEXT_CHUNK: "text_chunk",
  TRANSCRIPT: "transcript",
});
