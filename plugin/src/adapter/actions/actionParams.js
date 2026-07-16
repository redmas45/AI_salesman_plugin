import { clean } from "../dom/targetResolver";
import { schemaItemForParam, schemaParamKey } from "../dom/fieldSchema";

const MAX_REQUIRED_PARAMS = 20;
const VALUE_PARAM_OPERATIONS = new Set(["fill", "select", "set_value"]);

export function missingRequiredParams(actionConfig = {}, params = {}) {
  const requiredParams = requiredActionParams(actionConfig);
  return requiredParams.filter((param) => !hasRequiredParamValue(actionConfig, params, param));
}

export function stopForMissingParams(missingParams) {
  return {
    stopFallback: true,
    status: "blocked",
    reason: `missing_params:${missingParams.join(",")}`,
  };
}

export function isActionFallbackStop(result) {
  return Boolean(result && typeof result === "object" && result.stopFallback === true);
}

function requiredActionParams(actionConfig) {
  return uniqueParams([
    ...configuredRequiredFields(actionConfig),
    ...sequenceStepParams(actionConfig),
  ]);
}

function configuredRequiredFields(actionConfig) {
  const requiredFields = cleanFieldList(actionConfig?.required_fields);
  if (actionConfig?.required_fields_known === true || Array.isArray(actionConfig?.required_fields)) {
    return requiredFields;
  }
  return cleanFieldList(actionConfig?.fields);
}

function cleanFieldList(value) {
  if (!Array.isArray(value)) return [];
  return value.map(clean).filter(Boolean).slice(0, MAX_REQUIRED_PARAMS);
}

function hasRequiredParamValue(actionConfig, params, param) {
  if (hasParamValue(params, param)) return true;
  const schemaItem = schemaItemForParam(actionConfig?.field_schema, param);
  const schemaKey = schemaItem ? schemaParamKey(schemaItem, params) : "";
  return Boolean(schemaKey && hasParamValue(params, schemaKey));
}

function sequenceStepParams(actionConfig) {
  if (!Array.isArray(actionConfig?.steps)) return [];
  return actionConfig.steps
    .filter((step) => step?.optional !== true)
    .filter((step) => VALUE_PARAM_OPERATIONS.has(clean(step?.op || step?.type || step?.action).toLowerCase()))
    .filter((step) => !clean(step?.value))
    .map((step) => clean(step?.param || step?.parameter || step?.name))
    .filter(Boolean)
    .slice(0, MAX_REQUIRED_PARAMS);
}

function uniqueParams(values) {
  const rows = [];
  const seen = new Set();
  for (const value of values) {
    const param = clean(value);
    const key = param.toLowerCase();
    if (!param || seen.has(key)) continue;
    seen.add(key);
    rows.push(param);
    if (rows.length >= MAX_REQUIRED_PARAMS) break;
  }
  return rows;
}

function hasParamValue(params, param) {
  if (!params || typeof params !== "object") return false;
  if (!Object.prototype.hasOwnProperty.call(params, param)) return false;

  const value = params[param];
  if (value === null || value === undefined) return false;
  if (Array.isArray(value)) return value.length > 0;
  if (typeof value === "string") return value.trim().length > 0;
  return true;
}
