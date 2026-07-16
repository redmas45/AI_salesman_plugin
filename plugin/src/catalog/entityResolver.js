import { config } from "../core/config";
import { API_PATHS } from "../core/constants";

const ENTITY_TITLE_FIELDS = Object.freeze(["title", "name"]);
const ENTITY_SUMMARY_FIELDS = Object.freeze(["summary", "description", "body"]);
const ENTITY_IMAGE_FIELDS = Object.freeze(["image_url", "imageUrl", "image", "thumbnail"]);
const ENTITY_URL_FIELDS = Object.freeze(["url", "href", "permalink", "source_url"]);
const DEFAULT_ENTITY_TYPE = "knowledge_item";
const MAX_ENTITY_IDS = 30;

function clean(value) {
  if (value === null || value === undefined || typeof value === "object") return "";
  return String(value || "").trim();
}

function cleanIds(ids) {
  const seen = new Set();
  return (Array.isArray(ids) ? ids : [])
    .map(clean)
    .filter(Boolean)
    .filter((id) => {
      if (seen.has(id) || seen.size >= MAX_ENTITY_IDS) return false;
      seen.add(id);
      return true;
    });
}

function firstValue(raw, fields) {
  for (const field of fields) {
    const value = clean(raw?.[field]);
    if (value) return value;
  }
  return "";
}

function normalizedObject(value) {
  if (value && typeof value === "object" && !Array.isArray(value)) return value;
  return {};
}

function displayPrice(pricing) {
  const price = firstPositiveNumber([
    pricing?.price,
    pricing?.amount,
    pricing?.premium,
    pricing?.premium_min,
    pricing?.monthly_premium,
    pricing?.annual_premium,
    pricing?.min_price,
    pricing?.starting_price,
  ]);
  const currency = clean(pricing?.currency || "INR");
  if (!Number.isFinite(price) || price <= 0) return "";
  return `${currency} ${price.toLocaleString()}`;
}

function firstPositiveNumber(values) {
  for (const value of values) {
    const number = Number(String(value ?? "").replace(/,/g, ""));
    if (Number.isFinite(number) && number > 0) return number;
  }
  return 0;
}

function displayAvailability(availability) {
  if (!availability || typeof availability !== "object") return "";
  if (availability.in_stock === true) return "Available";
  if (availability.in_stock === false) return "Unavailable";
  return clean(availability.status || availability.availability || "");
}

function safeDetailUrl(rawUrl) {
  const value = clean(rawUrl);
  if (!value) return "";

  try {
    const url = new URL(value, window.location.origin);
    if (!/^https?:$/i.test(url.protocol)) return "";
    if (url.origin === window.location.origin) {
      return `${url.pathname}${url.search}${url.hash}`;
    }
    return url.toString();
  } catch (_error) {
    return "";
  }
}

function normalizeEntity(raw) {
  if (!raw) return null;

  const id = clean(raw.id);
  if (!id) return null;

  const pricing = normalizedObject(raw.pricing);
  const availability = normalizedObject(raw.availability);
  return {
    id,
    externalId: clean(raw.external_id),
    entityType: clean(raw.entity_type || raw.category_name) || DEFAULT_ENTITY_TYPE,
    title: firstValue(raw, ENTITY_TITLE_FIELDS) || id,
    subtitle: clean(raw.subtitle || raw.category_name || raw.entity_type),
    summary: firstValue(raw, ENTITY_SUMMARY_FIELDS),
    body: clean(raw.body),
    url: safeDetailUrl(firstValue(raw, ENTITY_URL_FIELDS)),
    imageUrl: firstValue(raw, ENTITY_IMAGE_FIELDS),
    attributes: normalizedObject(raw.attributes),
    pricing,
    availability,
    location: normalizedObject(raw.location),
    contact: normalizedObject(raw.contact),
    displayPrice: displayPrice(pricing),
    displayAvailability: displayAvailability(availability),
  };
}

export async function fetchHubEntitiesByIds(entityIds) {
  const ids = cleanIds(entityIds);
  if (!ids.length) return [];

  const url = new URL(API_PATHS.KNOWLEDGE_BY_IDS, config.apiUrl);
  url.searchParams.set("site_id", config.siteId);
  url.searchParams.set("ids", ids.join(","));

  const response = await fetch(url.toString(), { headers: { Accept: "application/json" } });
  if (!response.ok) throw new Error("Failed to fetch entities from AI Hub API");

  const entities = (await response.json()).map(normalizeEntity).filter(Boolean);
  const byId = new Map(entities.map((entity) => [String(entity.id), entity]));
  return ids.map((id) => byId.get(id)).filter(Boolean);
}

export async function resolveEntityDetailUrl(entityId) {
  const [entity] = await fetchHubEntitiesByIds([entityId]);
  return entity?.url || "";
}
