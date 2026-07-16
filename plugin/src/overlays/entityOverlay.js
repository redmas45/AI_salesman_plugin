import { ACTION_PARAMS, DEFAULT_ENTITY_RECOMMENDATION_TITLE, OVERLAY_COLLAPSE_DELAY_MS } from "../core/constants";
import { fetchHubEntitiesByIds, resolveEntityDetailUrl } from "../catalog/entityResolver";
import { ensureEntityOverlayStyles } from "./entityOverlayStyles";

const TYPE_WORD_LIMIT = 2;
const ASC_MISSING_NUMBER = Number.POSITIVE_INFINITY;
const DESC_MISSING_NUMBER = Number.NEGATIVE_INFINITY;
const MAX_EVIDENCE_IDS = 12;
let currentEntities = [];
let currentTitle = DEFAULT_ENTITY_RECOMMENDATION_TITLE;

function escapeHtml(value) {
  return String(value ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}

function readableType(value) {
  return String(value || "item")
    .replace(/[_-]+/g, " ")
    .trim()
    .split(/\s+/)
    .slice(0, TYPE_WORD_LIMIT)
    .join(" ");
}

function ensurePanel() {
  ensureEntityOverlayStyles();

  let panel = document.getElementById("mayabot-entity-panel");
  if (panel) return panel;

  panel = document.createElement("div");
  panel.id = "mayabot-entity-panel";
  panel.setAttribute("aria-live", "polite");
  panel.innerHTML = `
    <div class="mayabot-entity-header">
      <h2 class="mayabot-entity-title">${DEFAULT_ENTITY_RECOMMENDATION_TITLE}</h2>
      <button class="mayabot-entity-close" type="button" aria-label="Close recommendations">&times;</button>
    </div>
    <div class="mayabot-entity-grid"></div>
  `;
  panel.querySelector(".mayabot-entity-close").addEventListener("click", () => {
    panel.classList.remove("active");
  });
  document.body.appendChild(panel);
  return panel;
}

function countClass(count) {
  if (count <= 1) return "count-1";
  if (count === 2) return "count-2";
  if (count === 3) return "count-3";
  return "count-many";
}

function cardCount(count) {
  if (count <= 1) return 1;
  if (count === 2) return 2;
  return 3;
}

function overlayResult(requestedIds, entities, reason = "") {
  const renderedIds = (Array.isArray(entities) ? entities : [])
    .map((entity) => String(entity?.id ?? "").trim())
    .filter(Boolean);
  const renderedCount = renderedIds.length;
  const requestedCount = requestedIds.length;
  const status = renderedCount > 0 ? "succeeded" : "failed";
  return {
    status,
    stage: "entity_overlay",
    reason: reason || (status === "succeeded" ? "" : "no_matching_entities_rendered"),
    evidence: {
      requested_entity_count: requestedCount,
      rendered_entity_count: renderedCount,
      missing_entity_count: Math.max(requestedCount - renderedCount, 0),
      requested_entity_ids: requestedIds.slice(0, MAX_EVIDENCE_IDS).join(","),
      rendered_entity_ids: renderedIds.slice(0, MAX_EVIDENCE_IDS).join(","),
    },
  };
}

function entityFacts(entity) {
  return [
    entity.displayPrice,
    entity.displayAvailability,
    entity.location?.city,
    entity.attributes?.category,
  ]
    .map((value) => String(value || "").trim())
    .filter(Boolean)
    .slice(0, 3);
}

function entityMediaMarkup(entity) {
  if (entity.imageUrl) {
    return `
      <div class="mayabot-entity-media">
        <img src="${escapeHtml(entity.imageUrl)}" alt="${escapeHtml(entity.title)}">
      </div>
    `;
  }
  return `
    <div class="mayabot-entity-media">
      <div class="mayabot-entity-badge">${escapeHtml(readableType(entity.entityType))}</div>
    </div>
  `;
}

function entityFactsMarkup(entity) {
  const facts = entityFacts(entity);
  if (!facts.length) return "";
  return `
    <div class="mayabot-entity-facts">
      ${facts.map((fact) => `<span class="mayabot-entity-fact">${escapeHtml(fact)}</span>`).join("")}
    </div>
  `;
}

function entityActionMarkup(entity) {
  if (!entity.url) return "";
  return `
    <div class="mayabot-entity-actions">
      <button type="button" data-view-entity="${escapeHtml(entity.id)}">Open</button>
    </div>
  `;
}

function renderEntities(entities, title) {
  const panel = ensurePanel();
  const grid = panel.querySelector(".mayabot-entity-grid");
  const heading = panel.querySelector(".mayabot-entity-title");
  const count = entities.length;
  currentEntities = Array.isArray(entities) ? [...entities] : [];
  currentTitle = title || DEFAULT_ENTITY_RECOMMENDATION_TITLE;

  panel.classList.remove("count-1", "count-2", "count-3", "count-many");
  panel.classList.add(countClass(count));
  panel.style.setProperty("--mayabot-entity-card-count", String(cardCount(count)));
  heading.textContent = currentTitle;

  if (!count) {
    grid.innerHTML = `<p class="mayabot-entity-empty">No matching records are currently available.</p>`;
    panel.classList.add("active");
    collapseVoiceBubble();
    return;
  }

  grid.innerHTML = entities
    .map((entity) => {
      const safeId = escapeHtml(entity.id);
      return `
        <article class="mayabot-entity-card" data-entity-id="${safeId}">
          ${entityMediaMarkup(entity)}
          <h3 class="mayabot-entity-name">${escapeHtml(entity.title)}</h3>
          <p class="mayabot-entity-meta">${escapeHtml(entity.subtitle || readableType(entity.entityType))}</p>
          <p class="mayabot-entity-summary">${escapeHtml(entity.summary || entity.body || "Details are available on the website.")}</p>
          ${entityFactsMarkup(entity)}
          ${entityActionMarkup(entity)}
        </article>
      `;
    })
    .join("");

  grid.querySelectorAll("[data-view-entity]").forEach((button) => {
    button.addEventListener("click", async () => {
      await openEntityDetail(button.getAttribute("data-view-entity"));
    });
  });

  panel.classList.add("active");
  collapseVoiceBubble();
}

function openUrl(url) {
  if (!url) return false;
  try {
    const parsed = new URL(url, window.location.origin);
    if (parsed.origin === window.location.origin) {
      window.location.href = `${parsed.pathname}${parsed.search}${parsed.hash}`;
      return true;
    }
    window.open(parsed.toString(), "_blank", "noopener,noreferrer");
    return true;
  } catch (_error) {
    return false;
  }
}

function collapseVoiceBubble() {
  window.setTimeout(() => {
    const chat = document.getElementById("mayabot-chat");
    const messages = document.getElementById("mayabot-msgs");
    if (messages) messages.innerHTML = "";
    if (chat) chat.classList.remove("visible");
  }, OVERLAY_COLLAPSE_DELAY_MS);
}

export async function openEntityDetail(entityId) {
  const entityUrl = await resolveEntityDetailUrl(entityId);
  return openUrl(entityUrl);
}

export async function showEntityOverlay(entityIds, title = DEFAULT_ENTITY_RECOMMENDATION_TITLE) {
  const requestedIds = entityIdsFromParams({ [ACTION_PARAMS.ENTITY_IDS]: entityIds });
  if (!requestedIds.length) {
    renderEntities([], title);
    return overlayResult([], [], "missing_entity_ids");
  }

  try {
    const entities = await fetchHubEntitiesByIds(requestedIds);
    renderEntities(entities, title);
    return overlayResult(requestedIds, entities);
  } catch (error) {
    console.warn("[AI Hub Widget] Entity overlay failed:", error);
    renderEntities([], title);
    return overlayResult(requestedIds, [], "entity_overlay_fetch_failed");
  }
}

export function entityIdsFromParams(params) {
  const ids = params[ACTION_PARAMS.ENTITY_IDS] || params.ids || params.items || [];
  const seen = new Set();
  return (Array.isArray(ids) ? ids : [])
    .map((id) => String(id ?? "").trim())
    .filter(Boolean)
    .filter((id) => {
      if (seen.has(id)) return false;
      seen.add(id);
      return true;
    });
}

export function sortEntityOverlay(params = {}) {
  if (!currentEntities.length) return false;

  const sortBy = String(params.sort_by || params.sortBy || "price_asc").trim().toLowerCase();
  const sorted = [...currentEntities].sort((left, right) => compareEntities(left, right, sortBy));
  const title = sortedTitle(currentTitle, sortBy);
  renderEntities(sorted, title);
  return true;
}

function compareEntities(left, right, sortBy) {
  if (sortBy === "price_desc") {
    return entityPrice(right, DESC_MISSING_NUMBER) - entityPrice(left, DESC_MISSING_NUMBER);
  }
  if (sortBy === "rating") {
    return entityRating(right, DESC_MISSING_NUMBER) - entityRating(left, DESC_MISSING_NUMBER);
  }
  if (sortBy === "newest") {
    return entityTime(right) - entityTime(left);
  }
  return entityPrice(left, ASC_MISSING_NUMBER) - entityPrice(right, ASC_MISSING_NUMBER);
}

function entityPrice(entity, missingValue) {
  return firstNumeric(
    [
      entity?.pricing?.price,
      entity?.pricing?.amount,
      entity?.pricing?.premium,
      entity?.pricing?.premium_min,
      entity?.pricing?.monthly_premium,
      entity?.pricing?.annual_premium,
      entity?.pricing?.min_price,
      entity?.pricing?.starting_price,
      entity?.attributes?.price,
      entity?.attributes?.amount,
      entity?.attributes?.premium,
      entity?.attributes?.monthly_premium,
      entity?.attributes?.annual_premium,
      entity?.displayPrice,
    ],
    missingValue,
  );
}

function entityRating(entity, missingValue) {
  return firstNumeric(
    [
      entity?.attributes?.rating,
      entity?.attributes?.review_rating,
      entity?.attributes?.stars,
      entity?.availability?.rating,
    ],
    missingValue,
  );
}

function entityTime(entity) {
  const raw = entity?.attributes?.updated_at || entity?.attributes?.date || entity?.availability?.updated_at || "";
  const time = Date.parse(String(raw || ""));
  return Number.isFinite(time) ? time : 0;
}

function firstNumeric(values, fallback) {
  for (const value of values) {
    const number = numericValue(value);
    if (Number.isFinite(number)) return number;
  }
  return fallback;
}

function numericValue(value) {
  if (typeof value === "number") return value;
  const match = String(value ?? "").replace(/,/g, "").match(/-?\d+(?:\.\d+)?/);
  return match ? Number(match[0]) : Number.NaN;
}

function sortedTitle(title, sortBy) {
  const suffixes = {
    price_asc: "sorted low to high",
    price_desc: "sorted high to low",
    rating: "sorted by rating",
    newest: "newest first",
  };
  const cleanTitle = String(title || DEFAULT_ENTITY_RECOMMENDATION_TITLE).replace(/\s+-\s+sorted.*$/i, "");
  return `${cleanTitle} - ${suffixes[sortBy] || suffixes.price_asc}`;
}
