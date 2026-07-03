export declare const ACTIONS: {
  readonly ADD_TO_CART: "ADD_TO_CART";
  readonly BOOK_APPOINTMENT_REQUEST: "BOOK_APPOINTMENT_REQUEST";
  readonly BUILD_ITINERARY: "BUILD_ITINERARY";
  readonly BUILD_LEARNING_PATH: "BUILD_LEARNING_PATH";
  readonly CAPTURE_LEAD: "CAPTURE_LEAD";
  readonly CAPTURE_PATIENT_LEAD: "CAPTURE_PATIENT_LEAD";
  readonly CHECKOUT: "CHECKOUT";
  readonly CHECKOUT_HANDOFF: "CHECKOUT_HANDOFF";
  readonly CHECK_APPOINTMENT_AVAILABILITY: "CHECK_APPOINTMENT_AVAILABILITY";
  readonly CHECK_AVAILABILITY: "CHECK_AVAILABILITY";
  readonly CHECK_DELIVERY_AVAILABILITY: "CHECK_DELIVERY_AVAILABILITY";
  readonly CHECK_ELIGIBILITY_SOFT: "CHECK_ELIGIBILITY_SOFT";
  readonly CHECK_PREREQUISITES: "CHECK_PREREQUISITES";
  readonly CLEAR_CART: "CLEAR_CART";
  readonly CLEAR_FILTERS: "CLEAR_FILTERS";
  readonly CLEAR_HISTORY: "CLEAR_HISTORY";
  readonly COMPARE_ENTITIES: "COMPARE_ENTITIES";
  readonly CONTACT_AGENT: "CONTACT_AGENT";
  readonly FILTER_ENTITIES: "FILTER_ENTITIES";
  readonly FILTER_PRODUCTS: "FILTER_PRODUCTS";
  readonly HANDOFF_TO_ADVISOR: "HANDOFF_TO_ADVISOR";
  readonly HANDOFF_TO_AGENT: "HANDOFF_TO_AGENT";
  readonly HANDOFF_TO_CLINIC: "HANDOFF_TO_CLINIC";
  readonly HANDOFF_TO_HUMAN: "HANDOFF_TO_HUMAN";
  readonly HANDOFF_TO_LAWYER: "HANDOFF_TO_LAWYER";
  readonly HANDOFF_TO_LICENSED_AGENT: "HANDOFF_TO_LICENSED_AGENT";
  readonly HANDOFF_TO_RECRUITER: "HANDOFF_TO_RECRUITER";
  readonly JOIN_WAITLIST: "JOIN_WAITLIST";
  readonly MATCH_JOBS: "MATCH_JOBS";
  readonly NAVIGATE_TO: "NAVIGATE_TO";
  readonly OPEN_CLAIM_FLOW: "OPEN_CLAIM_FLOW";
  readonly OPEN_CONTACT: "OPEN_CONTACT";
  readonly OPEN_DISCLOSURE: "OPEN_DISCLOSURE";
  readonly OPEN_ENTITY_DETAIL: "OPEN_ENTITY_DETAIL";
  readonly OPEN_LOCATION: "OPEN_LOCATION";
  readonly OPEN_MAP: "OPEN_MAP";
  readonly OPEN_POLICY: "OPEN_POLICY";
  readonly OPEN_PROJECTS: "OPEN_PROJECTS";
  readonly OPEN_RENEWAL_FLOW: "OPEN_RENEWAL_FLOW";
  readonly OPEN_SERVICES: "OPEN_SERVICES";
  readonly OPEN_SYLLABUS: "OPEN_SYLLABUS";
  readonly OPEN_TELECONSULT: "OPEN_TELECONSULT";
  readonly REMOVE_FROM_CART: "REMOVE_FROM_CART";
  readonly REQUEST_APPOINTMENT: "REQUEST_APPOINTMENT";
  readonly REQUEST_CALLBACK: "REQUEST_CALLBACK";
  readonly REQUEST_CONSULTATION: "REQUEST_CONSULTATION";
  readonly REQUEST_COUNSELOR_CALLBACK: "REQUEST_COUNSELOR_CALLBACK";
  readonly REQUEST_ESTIMATE: "REQUEST_ESTIMATE";
  readonly REQUEST_SITE_VISIT: "REQUEST_SITE_VISIT";
  readonly REQUEST_TEST_DRIVE: "REQUEST_TEST_DRIVE";
  readonly REQUEST_VIEWING: "REQUEST_VIEWING";
  readonly RUN_AFFORDABILITY_CALCULATOR: "RUN_AFFORDABILITY_CALCULATOR";
  readonly RUN_CALCULATOR: "RUN_CALCULATOR";
  readonly RUN_DOM_SEQUENCE: "RUN_DOM_SEQUENCE";
  readonly SAVE_SEARCH: "SAVE_SEARCH";
  readonly SCHEDULE_ORDER: "SCHEDULE_ORDER";
  readonly SEARCH_AVAILABILITY: "SEARCH_AVAILABILITY";
  readonly SET_LOCATION: "SET_LOCATION";
  readonly SHOW_COMPARISON: "SHOW_COMPARISON";
  readonly SHOW_EMERGENCY_NOTICE: "SHOW_EMERGENCY_NOTICE";
  readonly SHOW_ENTITIES: "SHOW_ENTITIES";
  readonly SHOW_PRODUCT_DETAIL: "SHOW_PRODUCT_DETAIL";
  readonly SHOW_PRODUCTS: "SHOW_PRODUCTS";
  readonly SORT_ENTITIES: "SORT_ENTITIES";
  readonly SORT_PRODUCTS: "SORT_PRODUCTS";
  readonly START_APPLICATION: "START_APPLICATION";
  readonly START_BOOKING: "START_BOOKING";
  readonly START_ENROLLMENT: "START_ENROLLMENT";
  readonly START_INTAKE: "START_INTAKE";
  readonly START_QUOTE: "START_QUOTE";
  readonly START_TICKET_PURCHASE: "START_TICKET_PURCHASE";
  readonly UPDATE_CART_QUANTITY: "UPDATE_CART_QUANTITY";
  readonly UPDATE_PREFERENCES: "UPDATE_PREFERENCES";
};

export type UiActionName = (typeof ACTIONS)[keyof typeof ACTIONS];

export declare const ACTION_PARAMS: {
  readonly ENTITY_ID: "entity_id";
  readonly ENTITY_IDS: "entity_ids";
  readonly MESSAGE: "message";
  readonly PAGE: "page";
  readonly PRODUCT_ID: "product_id";
  readonly PRODUCT_IDS: "product_ids";
  readonly QUANTITY: "quantity";
  readonly REASON: "reason";
  readonly SEARCH_QUERY: "search_query";
  readonly URL: "url";
};

export type UiActionParamName = (typeof ACTION_PARAMS)[keyof typeof ACTION_PARAMS];

export declare const ACTION_EVENT_STATUSES: {
  readonly BLOCKED: "blocked";
  readonly EXECUTING: "executing";
  readonly FAILED: "failed";
  readonly REQUESTED: "requested";
  readonly SKIPPED: "skipped";
  readonly SUCCEEDED: "succeeded";
  readonly UNKNOWN: "unknown";
};

export type ActionEventStatus = (typeof ACTION_EVENT_STATUSES)[keyof typeof ACTION_EVENT_STATUSES];

export interface UiAction<TParams extends Record<string, unknown> = Record<string, unknown>> {
  action: UiActionName;
  params?: TParams;
  request_id?: string;
  turn_id?: string;
  sequence?: number;
}

export interface BrowserActionEvent {
  site_id: string;
  origin: string;
  url: string;
  occurred_at: string;
  request_id: string;
  turn_id: string;
  sequence: number;
  action: UiActionName | string;
  status: ActionEventStatus | string;
  stage?: string;
  reason?: string;
  duration_ms?: number;
  param_keys?: string[];
  requested_url?: string;
  final_url?: string;
  evidence?: Record<string, unknown>;
}

export declare const API_PATHS: {
  readonly KNOWLEDGE_BY_IDS: "/v1/knowledge/by-ids";
  readonly PRODUCTS_BY_IDS: "/v1/products/by-ids";
  readonly SHOP: "/v1/shop";
  readonly SHOP_WS: "/v1/ws/shop";
  readonly WIDGET_STATUS: "/v1/widget/status";
};

export declare const WS_MESSAGES: {
  readonly AUDIO_CHUNK: "audio_chunk";
  readonly AUDIO_END: "audio_end";
  readonly CONFIG: "config";
  readonly DONE: "done";
  readonly ERROR: "error";
  readonly TEXT_CHUNK: "text_chunk";
  readonly TRANSCRIPT: "transcript";
};

export declare function isKnownAction(value: unknown): value is UiActionName;
