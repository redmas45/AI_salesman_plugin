// Bound shadow-root traversal so malformed pages cannot make discovery unbounded.
const MAX_SEARCH_ROOTS = 60;
const MAX_RESULTS_PER_QUERY = 600;

export function queryElementDeep(selector) {
  return queryElementsDeep(selector)[0] || null;
}

export function queryElementsDeep(selector) {
  if (!selector || typeof selector !== "string") return [];
  const results = [];
  for (const root of searchRoots()) {
    try {
      results.push(...Array.from(root.querySelectorAll(selector)));
    } catch (_err) {
      return [];
    }
    if (results.length >= MAX_RESULTS_PER_QUERY) return results.slice(0, MAX_RESULTS_PER_QUERY);
  }
  return uniqueElements(results);
}

export function searchRoots() {
  const roots = [];
  const seen = new Set();
  const queue = [document];

  while (queue.length && roots.length < MAX_SEARCH_ROOTS) {
    const root = queue.shift();
    if (!root || seen.has(root)) continue;
    seen.add(root);
    roots.push(root);
    queue.push(...nestedRoots(root));
  }

  return roots;
}

function nestedRoots(root) {
  const nested = [];
  for (const element of allElements(root)) {
    if (element.shadowRoot) nested.push(element.shadowRoot);
    const frameDocument = sameOriginFrameDocument(element);
    if (frameDocument) nested.push(frameDocument);
  }
  return nested;
}

function allElements(root) {
  try {
    return Array.from(root.querySelectorAll("*"));
  } catch (_err) {
    return [];
  }
}

function sameOriginFrameDocument(element) {
  if (String(element?.tagName || "").toLowerCase() !== "iframe") return null;
  try {
    const frameDocument = element.contentDocument;
    if (!frameDocument?.documentElement) return null;
    return frameDocument;
  } catch (_err) {
    return null;
  }
}

function uniqueElements(elements) {
  return Array.from(new Set(elements));
}
