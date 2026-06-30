import { clean } from "./targetResolver";

const MAX_SCHEMA_ITEMS = 20;
const MAX_OPTION_ITEMS = 20;

export function schemaItems(fieldSchema) {
  if (!Array.isArray(fieldSchema)) return [];
  return fieldSchema
    .slice(0, MAX_SCHEMA_ITEMS)
    .filter((item) => item && typeof item === "object" && clean(item.param));
}

export function schemaKeysForItem(item) {
  return uniqueTokens([
    item?.param,
    item?.label,
    item?.autocomplete,
    ...optionTextValues(item?.options),
  ]);
}

export function schemaItemForParam(fieldSchema, param) {
  const wanted = normalizeKey(param);
  if (!wanted) return null;
  return schemaItems(fieldSchema).find((item) => schemaKeysForItem(item).has(wanted)) || null;
}

export function schemaValueForItem(item, value) {
  const option = matchingOption(item?.options, value);
  return option?.value || option?.label || value;
}

export function normalizeSchemaValue(fieldSchema, param, value) {
  const item = schemaItemForParam(fieldSchema, param);
  return item ? schemaValueForItem(item, value) : value;
}

export function schemaParamKey(item, params) {
  if (!params || typeof params !== "object") return "";
  const aliases = schemaKeysForItem(item);
  return Object.keys(params).find((key) => aliases.has(normalizeKey(key)) && hasUsableValue(params[key])) || "";
}

function matchingOption(options, value) {
  const wanted = normalizeText(value);
  if (!wanted || !Array.isArray(options)) return null;

  return options.slice(0, MAX_OPTION_ITEMS).find((option) => {
    const label = normalizeText(option?.label);
    const optionValue = normalizeText(option?.value);
    return textMatchesOption(wanted, label) || textMatchesOption(wanted, optionValue);
  });
}

function textMatchesOption(wanted, optionText) {
  if (!wanted || !optionText) return false;
  return optionText === wanted || optionText.includes(wanted) || wanted.includes(optionText);
}

function optionTextValues(options) {
  if (!Array.isArray(options)) return [];
  return options.slice(0, MAX_OPTION_ITEMS).flatMap((option) => [option?.label, option?.value]);
}

function uniqueTokens(values) {
  return new Set(values.flatMap(tokenize).filter(Boolean));
}

function hasUsableValue(value) {
  if (typeof value === "boolean" || typeof value === "number") return true;
  return clean(value) !== "";
}

function tokenize(value) {
  const normalized = normalizeText(value);
  if (!normalized) return [];
  return [...new Set([normalizeKey(value), ...normalized.split(" ")].filter(Boolean))];
}

function normalizeKey(value) {
  return clean(value).toLowerCase().replace(/[^a-z0-9]+/g, "_").replace(/^_+|_+$/g, "");
}

function normalizeText(value) {
  return clean(value).toLowerCase().replace(/[^a-z0-9]+/g, " ").replace(/\s+/g, " ").trim();
}
