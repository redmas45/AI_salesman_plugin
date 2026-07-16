import { labelsForAction } from "../actions/actionLabels";
import { CLICKABLE_SELECTOR, FORM_INPUT_SELECTOR } from "./controlSelectors";
import { queryElementDeep, queryElementsDeep } from "./deepDom";
import { submitElementFor } from "./submitResolver";

const ACTION_REPORT_PATH = "/v1/widget/action-report";
const VALIDATED_PAGES = "__aihubAdapterValidatedPages";
const VALIDATION_WAIT_MS = 3000;
const VALIDATION_POLL_MS = 150;

function clean(value) {
  return String(value || "").replace(/\s+/g, " ").trim();
}

function apiUrl(path, apiBaseUrl) {
  return new URL(path, apiBaseUrl).toString();
}

function cssEscape(value) {
  if (window.CSS?.escape) return window.CSS.escape(value);
  return String(value).replace(/["\\]/g, "\\$&");
}

function selectorFor(element) {
  if (!element || element.nodeType !== 1) return "";
  if (element.id) return `#${cssEscape(element.id)}`;

  for (const attr of ["data-testid", "data-test", "data-action", "aria-label", "name"]) {
    const value = element.getAttribute(attr);
    if (value) return `${element.tagName.toLowerCase()}[${attr}="${cssEscape(value)}"]`;
  }

  const classes = Array.from(element.classList || []).slice(0, 2);
  if (classes.length > 0) {
    return `${element.tagName.toLowerCase()}.${classes.map(cssEscape).join(".")}`;
  }
  return element.tagName.toLowerCase();
}

function queryElement(selector) {
  return queryElementDeep(selector);
}

function elementText(element) {
  return clean(element?.innerText || element?.value || element?.getAttribute?.("aria-label") || element?.getAttribute?.("title")).toLowerCase();
}

function findClickableByLabels(labels) {
  for (const element of queryElementsDeep(CLICKABLE_SELECTOR)) {
    const text = elementText(element);
    if (labels.some((label) => text.includes(label))) return element;
  }
  return null;
}

function findFormByLabels(labels) {
  for (const form of queryElementsDeep("form")) {
    const formText = clean(form.innerText).toLowerCase();
    const input = form.querySelector(FORM_INPUT_SELECTOR);
    if (!input) continue;
    if (!labels.length || labels.some((label) => formText.includes(label))) return form;
  }
  return null;
}

function sameOriginPath(path) {
  const target = clean(path);
  if (!target || /^https?:\/\//i.test(target) || target.startsWith("javascript:")) return "";
  try {
    const url = new URL(target, window.location.origin);
    if (url.origin !== window.location.origin) return "";
    return `${url.pathname}${url.search}${url.hash}`;
  } catch (_err) {
    return "";
  }
}

function currentPagePath() {
  return `${window.location.pathname}${window.location.search}${window.location.hash}`;
}

function actionPagePath(actionConfig) {
  return sameOriginPath(actionConfig.page_path || actionConfig.pagePath || actionConfig.source_path || actionConfig.sourcePath);
}

function pageScopedEvidence(type, actionConfig) {
  const pagePath = actionPagePath(actionConfig);
  if (!pagePath || pagePath === currentPagePath()) return null;
  return {
    type,
    status: "page_scoped",
    target: pagePath,
    supported: true,
    confidence: 0.65,
    evidence: "Action target belongs to a different same-origin page; current-page validation skipped.",
  };
}

function validateNavigate(actionConfig) {
  const path = sameOriginPath(actionConfig.path);
  return {
    type: "navigate",
    status: path ? "ok" : "missing_target",
    target: path || clean(actionConfig.path),
    supported: Boolean(path),
    confidence: path ? 0.75 : 0.2,
    evidence: path ? "Same-origin navigation path is safe to use." : "Navigation path is missing or external.",
  };
}

function validateHandoff(actionConfig) {
  const path = sameOriginPath(actionConfig.path);
  return {
    type: "handoff",
    status: path ? "ok" : "missing_target",
    target: path || clean(actionConfig.path),
    supported: Boolean(path),
    confidence: path ? 0.75 : 0.2,
    evidence: path ? "Handoff overlay can open a same-origin contact path." : "Handoff contact path is missing or external.",
  };
}

function validateClick(actionName, actionConfig) {
  const scoped = pageScopedEvidence("click", actionConfig);
  if (scoped) return scoped;

  const configured = queryElement(actionConfig.selector);
  if (configured) {
    return supportedEvidence("click", actionConfig.selector, "Configured click selector exists in the live DOM.");
  }

  const labels = labelsForAction(actionName, actionConfig);
  const repairElement = findClickableByLabels(labels);
  return missingEvidence("click", clean(actionConfig.selector), repairElement);
}

function validateForm(actionName, actionConfig) {
  const scoped = pageScopedEvidence("form", actionConfig);
  if (scoped) return scoped;

  const form = queryElement(actionConfig.form);
  const input = queryElement(actionConfig.input);
  const submit = queryElement(actionConfig.submit);
  if (input && (form || submit)) {
    return supportedEvidence("form", actionConfig.form || actionConfig.input, "Configured form/input selectors exist in the live DOM.");
  }

  const repairForm = findFormByLabels(labelsForAction(actionName, actionConfig));
  const repairInput = repairForm?.querySelector(FORM_INPUT_SELECTOR);
  const repairSubmit = submitElementFor(repairForm);
  if (!repairForm || !repairInput) {
    return missingEvidence("form", clean(actionConfig.form || actionConfig.input), null);
  }

  return {
    type: "form",
    status: "repair_suggested",
    target: clean(actionConfig.form || actionConfig.input),
    supported: false,
    confidence: 0.35,
    evidence: "Configured form was missing; a likely replacement form was found.",
    repair: {
      type: "form",
      form: selectorFor(repairForm),
      input: selectorFor(repairInput),
      submit: selectorFor(repairSubmit),
      confidence: 0.72,
    },
  };
}

function validateSequence(actionConfig) {
  const scoped = pageScopedEvidence("sequence", actionConfig);
  if (scoped) return scoped;

  const steps = Array.isArray(actionConfig.steps) ? actionConfig.steps : [];
  if (!steps.length) {
    return missingSequenceEvidence("No sequence steps are configured.", 0, 0);
  }

  const checkedSteps = steps.filter((step) => stepNeedsLiveTarget(step));
  const missingSteps = checkedSteps.filter((step) => !stepTargetExists(step));
  if (!missingSteps.length) {
    return supportedEvidence("sequence", `${steps.length} step(s)`, "Configured sequence targets exist in the live DOM.");
  }
  return missingSequenceEvidence("One or more configured sequence targets are missing.", checkedSteps.length, missingSteps.length);
}

function stepNeedsLiveTarget(step) {
  const op = clean(step?.op || step?.type || step?.action).toLowerCase();
  return ["check", "click", "fill", "focus", "select", "set_value", "submit", "uncheck", "wait_for"].includes(op);
}

function stepTargetExists(step) {
  if (queryElement(step?.selector)) return true;
  const label = clean(step?.label || step?.text);
  if (!label) return false;
  return Boolean(findClickableByLabels([label.toLowerCase()]));
}

function missingSequenceEvidence(evidence, checkedCount, missingCount) {
  return {
    type: "sequence",
    status: "missing",
    target: `${missingCount}/${checkedCount} missing target(s)`,
    supported: false,
    confidence: 0.3,
    evidence,
  };
}

function supportedEvidence(type, target, evidence) {
  return {
    type,
    status: "ok",
    target: clean(target),
    supported: true,
    confidence: 0.9,
    evidence,
  };
}

function missingEvidence(type, target, repairElement) {
  if (!repairElement) {
    return {
      type,
      status: "missing",
      target,
      supported: false,
      confidence: 0.25,
      evidence: "Configured target was not found in the live DOM.",
    };
  }
  return {
    type,
    status: "repair_suggested",
    target,
    supported: false,
    confidence: 0.35,
    evidence: "Configured target was missing; a likely replacement was found by label.",
    repair: {
      type: "click",
      selector: selectorFor(repairElement),
      label: clean(elementText(repairElement)),
      confidence: 0.72,
    },
  };
}

function validateAction(actionName, actionConfig) {
  const type = clean(actionConfig?.type).toLowerCase();
  if (type === "navigate") return validateNavigate(actionConfig);
  if (type === "click") return validateClick(actionName, actionConfig);
  if (type === "form") return validateForm(actionName, actionConfig);
  if (type === "sequence") return validateSequence(actionConfig);
  if (type === "handoff") return validateHandoff(actionConfig);
  return {
    type,
    status: "unsupported_type",
    target: "",
    supported: false,
    confidence: 0.1,
    evidence: "Action config type is not supported by the universal adapter.",
  };
}

async function postValidationReport(apiBaseUrl, siteId, actions) {
  await fetch(apiUrl(ACTION_REPORT_PATH, apiBaseUrl), {
    method: "POST",
    headers: {
      Accept: "application/json",
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      site_id: siteId,
      origin: window.location.origin,
      url: window.location.href,
      validated_at: new Date().toISOString(),
      actions,
    }),
    keepalive: true,
  });
}

function pageValidationKey(siteId) {
  return `${siteId}:${window.location.origin}${window.location.pathname}${window.location.search}${window.location.hash}`;
}

function sleep(ms) {
  return new Promise((resolve) => window.setTimeout(resolve, ms));
}

function validationNeedsAsyncWait(result) {
  return ["missing"].includes(clean(result?.status).toLowerCase());
}

async function waitForValidationTargets(actions) {
  const entries = Object.entries(actions);
  const deadline = Date.now() + VALIDATION_WAIT_MS;
  while (Date.now() < deadline) {
    const hasPendingTarget = entries.some(([actionName, actionConfig]) => validationNeedsAsyncWait(validateAction(actionName, actionConfig || {})));
    if (!hasPendingTarget) return;
    await sleep(VALIDATION_POLL_MS);
  }
}

export async function validateRuntimeActions(apiBaseUrl, siteId, runtimeConfig) {
  const actions = runtimeConfig?.adapter?.actions || {};
  if (!Object.keys(actions).length) return;

  const key = pageValidationKey(siteId);
  window[VALIDATED_PAGES] = window[VALIDATED_PAGES] || {};
  if (window[VALIDATED_PAGES][key]) return;
  window[VALIDATED_PAGES][key] = true;

  await waitForValidationTargets(actions);

  const report = {};
  for (const [actionName, actionConfig] of Object.entries(actions)) {
    report[actionName] = validateAction(actionName, actionConfig || {});
  }

  try {
    await postValidationReport(apiBaseUrl, siteId, report);
  } catch (err) {
    console.warn("[AIHubAdapter] Action validation report failed.", err);
  }
}
