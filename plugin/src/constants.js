import { ACTIONS, ACTION_PARAMS, API_PATHS, WS_MESSAGES } from "@ai-hub/contracts";

export { ACTIONS, ACTION_PARAMS, API_PATHS, WS_MESSAGES };

export const CART_PAGE_TARGETS = new Set(["cart", "/cart"]);
export const DEFAULT_RECOMMENDATION_TITLE = "Recommended products";
export const DEFAULT_ENTITY_RECOMMENDATION_TITLE = "Relevant options";

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
export const WIDGET_STATUS_POLL_INTERVAL_MS = 3000;

export const EVENTS = Object.freeze({
  MAYABOT_ACTION: "mayabot:action",
});

export const WS_CONNECT_TIMEOUT_MS = 2500;
