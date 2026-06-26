const REGISTER_PATH = "/v1/widget/register";
const MAX_TEXT_CHARS = 2500;
const MAX_ELEMENTS = 80;
const ATTRIBUTES_FOR_SELECTOR = ["data-testid", "data-test", "data-action", "aria-label", "name"];
const CLICKABLE_SELECTOR = "button, a, input[type='button'], input[type='submit']";
const FORM_SELECTOR = "form";
const INPUT_SELECTOR = "input[type='search'], input[name], input[placeholder], select";

function clean(value) {
  return String(value || "").replace(/\s+/g, " ").trim();
}

function apiUrl(path, apiBaseUrl) {
  return new URL(path, apiBaseUrl).toString();
}

function textSample() {
  return clean(document.body?.innerText || "").slice(0, MAX_TEXT_CHARS);
}

function cssEscape(value) {
  if (window.CSS?.escape) return window.CSS.escape(value);
  return String(value).replace(/["\\]/g, "\\$&");
}

function selectorFor(element) {
  if (!element || element.nodeType !== 1) return "";
  if (element.id) return `#${cssEscape(element.id)}`;

  for (const attr of ATTRIBUTES_FOR_SELECTOR) {
    const value = element.getAttribute(attr);
    if (value) return `${element.tagName.toLowerCase()}[${attr}="${cssEscape(value)}"]`;
  }

  const classes = Array.from(element.classList || []).slice(0, 2);
  if (classes.length > 0) {
    return `${element.tagName.toLowerCase()}.${classes.map(cssEscape).join(".")}`;
  }

  return element.tagName.toLowerCase();
}

function clickableElements() {
  return Array.from(document.querySelectorAll(CLICKABLE_SELECTOR))
    .slice(0, MAX_ELEMENTS)
    .map((element) => ({
      label: clean(element.innerText || element.value || element.getAttribute("aria-label")),
      selector: selectorFor(element),
      href: element.href || "",
    }))
    .filter((element) => element.label || element.href);
}

function linkElements() {
  return Array.from(document.querySelectorAll("a[href]"))
    .slice(0, MAX_ELEMENTS)
    .map((element) => ({
      label: clean(element.innerText || element.getAttribute("aria-label")),
      selector: selectorFor(element),
      href: element.href || "",
    }))
    .filter((element) => element.href);
}

function formElements() {
  return Array.from(document.querySelectorAll(FORM_SELECTOR))
    .slice(0, MAX_ELEMENTS)
    .map((form) => {
      const input = form.querySelector(INPUT_SELECTOR);
      const submit = form.querySelector("button[type='submit'], input[type='submit'], button");
      return {
        label: clean(form.innerText || input?.getAttribute("placeholder") || input?.getAttribute("name")),
        selector: selectorFor(form),
        input_selector: selectorFor(input),
        submit_selector: selectorFor(submit),
      };
    })
    .filter((form) => form.input_selector);
}

function platformHints() {
  return {
    shopify: Boolean(window.Shopify || document.querySelector('script[src*="cdn.shopify.com"]')),
    woocommerce: Boolean(document.body?.classList?.contains("woocommerce") || window.wc_add_to_cart_params),
  };
}

export function collectDiscoveryPayload(siteId) {
  return {
    site_id: siteId,
    origin: window.location.origin,
    url: window.location.href,
    title: document.title || "",
    text_sample: textSample(),
    buttons: clickableElements(),
    links: linkElements(),
    forms: formElements(),
    platform_hints: platformHints(),
  };
}

export async function registerPageDiscovery(apiBaseUrl, siteId) {
  const payload = collectDiscoveryPayload(siteId);
  try {
    await fetch(apiUrl(REGISTER_PATH, apiBaseUrl), {
      method: "POST",
      headers: {
        Accept: "application/json",
        "Content-Type": "application/json",
      },
      body: JSON.stringify(payload),
      keepalive: true,
    });
  } catch (err) {
    console.warn("[AIHubAdapter] Discovery registration failed.", err);
  }
}
