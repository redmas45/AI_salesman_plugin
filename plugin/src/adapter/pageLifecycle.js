import { CLICKABLE_SELECTOR, FIELD_SELECTOR } from "./controlSelectors";
import { queryElementsDeep, searchRoots } from "./deepDom";

const PAGE_OBSERVER_FLAG = "__aihubAdapterPageObserver";
const DISCOVERY_DELAY_MS = 650;
const DOM_MUTATION_DELAY_MS = 1200;
const MIN_DOM_DISCOVERY_INTERVAL_MS = 6000;
const CONTROL_SELECTOR = ["form", "iframe", CLICKABLE_SELECTOR, FIELD_SELECTOR].join(", ");
const MUTATION_ATTRIBUTE_FILTER = [
  "action",
  "aria-hidden",
  "class",
  "disabled",
  "hidden",
  "href",
  "name",
  "placeholder",
  "style",
  "type",
];

function currentPageKey() {
  return `${window.location.origin}${window.location.pathname}${window.location.search}${window.location.hash}`;
}

function pageStructureSignature() {
  return [
    currentPageKey(),
    queryElementsDeep("form").length,
    queryElementsDeep(CLICKABLE_SELECTOR).length,
    queryElementsDeep("a[href]").length,
    queryElementsDeep(FIELD_SELECTOR).length,
    queryElementsDeep("iframe").length,
  ].join("|");
}

function patchHistoryMethod(methodName, notify) {
  const original = window.history?.[methodName];
  if (typeof original !== "function") return;

  window.history[methodName] = function patchedHistoryMethod(...args) {
    const result = original.apply(this, args);
    notify();
    return result;
  };
}

export function installPageObserver(onPageChange, onContentChange = onPageChange) {
  if (window[PAGE_OBSERVER_FLAG]) return;
  window[PAGE_OBSERVER_FLAG] = true;

  let lastPageKey = currentPageKey();
  let lastContentSignature = pageStructureSignature();
  let lastContentDiscoveryAt = 0;
  let timer = null;
  let mutationTimer = null;
  const notify = () => {
    window.clearTimeout(timer);
    timer = window.setTimeout(() => {
      const nextPageKey = currentPageKey();
      if (nextPageKey === lastPageKey) return;
      lastPageKey = nextPageKey;
      onPageChange({ key: nextPageKey, url: window.location.href });
    }, DISCOVERY_DELAY_MS);
  };
  const notifyContent = () => {
    window.clearTimeout(mutationTimer);
    const elapsed = Date.now() - lastContentDiscoveryAt;
    const delay = Math.max(DOM_MUTATION_DELAY_MS, MIN_DOM_DISCOVERY_INTERVAL_MS - elapsed);
    mutationTimer = window.setTimeout(() => {
      const nextSignature = pageStructureSignature();
      if (nextSignature === lastContentSignature) return;
      lastContentSignature = nextSignature;
      lastContentDiscoveryAt = Date.now();
      onContentChange({ key: nextSignature, url: window.location.href, reason: "dom_mutation" });
    }, delay);
  };

  patchHistoryMethod("pushState", notify);
  patchHistoryMethod("replaceState", notify);
  window.addEventListener("popstate", notify);
  window.addEventListener("hashchange", notify);
  installMutationObserver(notifyContent);
}

function installMutationObserver(notifyContent) {
  if (typeof MutationObserver !== "function") return;
  const observedRoots = new Set();
  const observer = new MutationObserver((mutations) => {
    observeAvailableRoots();
    if (!mutations.some(isRelevantMutation)) return;
    notifyContent();
  });
  const observeAvailableRoots = () => {
    for (const root of searchRoots()) {
      const target = root.body || root;
      if (!target || observedRoots.has(target)) continue;
      observedRoots.add(target);
      observer.observe(target, {
        attributes: true,
        attributeFilter: MUTATION_ATTRIBUTE_FILTER,
        childList: true,
        subtree: true,
      });
    }
  };
  observeAvailableRoots();
}

function isRelevantMutation(mutation) {
  if (isWidgetNode(mutation.target)) return false;
  if (mutation.type === "attributes") {
    return elementTouchesControls(mutation.target);
  }
  return Array.from(mutation.addedNodes || []).some(elementTouchesControls);
}

function elementTouchesControls(node) {
  if (!node || node.nodeType !== 1 || isWidgetNode(node)) return false;
  return node.matches?.(CONTROL_SELECTOR) || Boolean(node.querySelector?.(CONTROL_SELECTOR));
}

function isWidgetNode(node) {
  const element = node?.nodeType === 1 ? node : node?.parentElement;
  return Boolean(element?.closest?.("#mayabot-widget, #mayabot-product-panel"));
}
