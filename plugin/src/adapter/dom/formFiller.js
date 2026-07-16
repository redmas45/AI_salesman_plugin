import { FIELD_SELECTOR } from "./controlSelectors";
import { enterText, selectNativeOption, setControlChecked } from "./eventDriver";
import { schemaItems, schemaKeysForItem, schemaParamKey, schemaValueForItem } from "./fieldSchema";
import { clean, elementText } from "./targetResolver";

const SKIPPED_INPUT_TYPES = new Set(["button", "file", "hidden", "image", "password", "reset", "submit"]);
const CHECKABLE_TYPES = new Set(["checkbox", "radio"]);
const FIELD_ALIAS_GROUPS = Object.freeze([
  ["name", "full_name", "fullname", "first_name", "last_name", "contact_name"],
  ["email", "email_address", "mail"],
  ["phone", "mobile", "telephone", "tel", "contact_number", "whatsapp"],
  ["query", "q", "search", "keyword", "term"],
  ["message", "comment", "notes", "details", "description"],
  ["address", "city", "location", "postcode", "postal_code", "zip"],
  ["date", "time", "appointment", "check_in", "check_out", "departure", "arrival"],
  ["budget", "price", "amount", "loan_amount", "coverage_amount", "sum_insured"],
  ["destination", "origin", "from", "to", "pickup", "dropoff"],
  ["guests", "travellers", "travelers", "adults", "children", "quantity"],
  ["coverage", "coverage_type", "policy_type", "plan", "service", "category"],
  ["property", "property_type", "bedrooms", "area", "project_type"],
]);

export function fillFormFields(form, params = {}, options = {}) {
  const fields = candidateFields(form, options.fallbackInput);
  const fieldSchema = schemaItems(options.fieldSchema);
  let filled = 0;
  for (const field of fields) {
    if (fillField(field, params, form, fieldSchema)) filled += 1;
  }
  return { filled, total: fields.length };
}

function candidateFields(form, fallbackInput) {
  const fields = Array.from(form?.querySelectorAll?.(FIELD_SELECTOR) || []);
  if (fallbackInput && !fields.includes(fallbackInput)) fields.unshift(fallbackInput);
  return fields.filter((field) => !shouldSkipField(field));
}

function fillField(field, params, form, fieldSchema) {
  const schemaItem = matchingSchemaItem(field, fieldSchema);
  const paramKey = matchingParamKey(field, params, schemaItem);
  if (!paramKey) return false;

  const value = schemaItem ? schemaValueForItem(schemaItem, params[paramKey]) : params[paramKey];
  const inputType = fieldType(field);
  if (CHECKABLE_TYPES.has(inputType)) {
    return fillCheckableField(field, value, form);
  }
  if (clean(field.tagName).toLowerCase() === "select") {
    return selectNativeOption(field, value);
  }
  return enterText(field, value);
}

function matchingParamKey(field, params, schemaItem) {
  const keys = Object.keys(params || {}).filter((key) => hasUsableValue(params[key]));
  if (!keys.length) return "";

  const schemaKey = schemaItem ? schemaParamKey(schemaItem, params) : "";
  if (schemaKey) return schemaKey;

  const fieldTokens = descriptorTokens(field);
  const directKey = keys.find((key) => fieldTokens.has(normalizeKey(key)));
  if (directKey) return directKey;

  const aliasKey = keys.find((key) => aliasMatches(fieldTokens, normalizeKey(key)));
  if (aliasKey) return aliasKey;

  return bestTokenOverlapKey(fieldTokens, keys);
}

function matchingSchemaItem(field, fieldSchema) {
  if (!fieldSchema.length) return null;
  const fieldTokens = descriptorTokens(field);
  let bestItem = null;
  let bestScore = 0;
  for (const item of fieldSchema) {
    const score = schemaOverlapScore(fieldTokens, item);
    if (score > bestScore) {
      bestScore = score;
      bestItem = item;
    }
  }
  return bestScore > 0 ? bestItem : null;
}

function schemaOverlapScore(fieldTokens, item) {
  let score = 0;
  for (const token of schemaKeysForItem(item)) {
    if (fieldTokens.has(token)) score += 1;
  }
  return score;
}

function descriptorTokens(field) {
  return new Set(
    [
      field.getAttribute?.("name"),
      field.id,
      field.getAttribute?.("placeholder"),
      field.getAttribute?.("aria-label"),
      field.getAttribute?.("title"),
      field.getAttribute?.("autocomplete"),
      fieldType(field),
      labelText(field),
      elementText(field),
    ]
      .flatMap(tokenize)
      .filter(Boolean),
  );
}

function labelText(field) {
  const parts = [closestLabelText(field), explicitLabelText(field), labelledByText(field), nearbyLabelText(field)];
  return parts.map(clean).filter(Boolean).join(" ");
}

function explicitLabelText(field) {
  const id = clean(field.id);
  if (!id) return "";
  const selector = `label[for="${cssEscape(id)}"]`;
  return labelTextWithoutControls(field.ownerDocument?.querySelector?.(selector));
}

function closestLabelText(field) {
  return labelTextWithoutControls(field.closest?.("label"));
}

function labelledByText(field) {
  const ids = clean(field.getAttribute?.("aria-labelledby")).split(/\s+/).filter(Boolean);
  return ids.map((id) => elementText(field.ownerDocument?.getElementById?.(id))).join(" ");
}

function nearbyLabelText(field) {
  const container = field.parentElement;
  if (!container) return "";
  const label = container.querySelector?.("label");
  if (label && !label.contains(field)) return labelTextWithoutControls(label);
  const previous = field.previousElementSibling;
  if (clean(previous?.tagName).toLowerCase() === "label") return labelTextWithoutControls(previous);
  return "";
}

function labelTextWithoutControls(label) {
  if (!label) return "";
  const clone = label.cloneNode(true);
  clone.querySelectorAll?.(`${FIELD_SELECTOR}, option`).forEach((node) => node.remove());
  return clean(clone.innerText || clone.textContent);
}

function fillCheckableField(field, value, form) {
  if (typeof value === "boolean") return setControlChecked(field, value);

  const wanted = normalizeText(value);
  if (!wanted) return false;
  const group = radioGroup(field, form);
  const match = group.find((item) => checkableMatches(item, wanted));
  return setControlChecked(match || field, true);
}

function radioGroup(field, form) {
  if (fieldType(field) !== "radio") return [field];
  const name = clean(field.getAttribute?.("name"));
  if (!name) return [field];
  return Array.from(
    form?.querySelectorAll?.(`input[type="radio"][name="${cssEscape(name)}"], [role="radio"][name="${cssEscape(name)}"]`) || [field],
  );
}

function checkableMatches(field, wanted) {
  const text = normalizeText([field.value, labelText(field), elementText(field)].join(" "));
  return text === wanted || text.includes(wanted) || wanted.includes(text);
}

function aliasMatches(fieldTokens, paramKey) {
  return FIELD_ALIAS_GROUPS.some((group) => group.includes(paramKey) && group.some((alias) => fieldTokens.has(alias)));
}

function bestTokenOverlapKey(fieldTokens, keys) {
  let bestKey = "";
  let bestScore = 0;
  for (const key of keys) {
    const tokens = tokenize(key);
    const score = tokens.filter((token) => fieldTokens.has(token)).length;
    if (score > bestScore) {
      bestScore = score;
      bestKey = key;
    }
  }
  return bestScore > 0 ? bestKey : "";
}

function shouldSkipField(field) {
  return SKIPPED_INPUT_TYPES.has(fieldType(field)) || field.disabled || field.readOnly;
}

function hasUsableValue(value) {
  if (typeof value === "boolean" || typeof value === "number") return true;
  return clean(value) !== "";
}

function fieldType(field) {
  const role = clean(field.getAttribute?.("role")).toLowerCase();
  if (role === "radio" || role === "checkbox") return role;
  return clean(field.getAttribute?.("type") || field.tagName).toLowerCase();
}

function tokenize(value) {
  const normalized = normalizeText(value);
  if (!normalized) return [];
  const compact = normalizeKey(value);
  return [...new Set([compact, ...normalized.split(" ")].filter(Boolean))];
}

function normalizeKey(value) {
  return clean(value).toLowerCase().replace(/[^a-z0-9]+/g, "_").replace(/^_+|_+$/g, "");
}

function normalizeText(value) {
  return clean(value).toLowerCase().replace(/[^a-z0-9]+/g, " ").replace(/\s+/g, " ").trim();
}

function cssEscape(value) {
  return window.CSS?.escape ? window.CSS.escape(value) : clean(value).replace(/["\\]/g, "\\$&");
}
