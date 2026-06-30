"""Optional live browser smoke for the local Policy quote flow."""

from __future__ import annotations

from urllib.parse import urlparse

import httpx
import pytest

from agent.adapter_discovery import build_discovery


POLICY_FRONTEND_URL = "http://127.0.0.1:5183/"


@pytest.mark.asyncio
async def test_live_policy_quote_form_discovers_submit_and_navigates() -> None:
    if not _local_site_reachable(POLICY_FRONTEND_URL):
        pytest.skip(f"Policy frontend is not running at {POLICY_FRONTEND_URL}")

    playwright_api = pytest.importorskip("playwright.async_api")

    async with playwright_api.async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=True)
        page = await browser.new_page(viewport={"width": 1365, "height": 768})
        page.set_default_timeout(5000)
        await page.goto(POLICY_FRONTEND_URL, wait_until="networkidle")

        discovery = build_discovery(await page.evaluate(_collector_js())).to_dict()
        action = discovery["vertical_config"]["actions"]["START_QUOTE"]

        assert discovery["vertical_key"] == "insurance"
        assert action["submit_mode"] == "submit"
        assert action["fields"] == ["age_of_eldest_member", "city"]
        assert action["steps"][-1]["op"] == "submit"

        for step in action["steps"]:
            if step["op"] == "select":
                await page.locator(step["selector"]).first.select_option(value="27")
            elif step["op"] == "fill":
                await page.locator(step["selector"]).first.fill("Mumbai")
            elif step["op"] == "submit":
                await page.locator(step["selector"]).first.click()

        await page.wait_for_url("**/insurance/health", wait_until="networkidle", timeout=5000)

        assert urlparse(page.url).path == "/insurance/health"
        await browser.close()


def _local_site_reachable(url: str) -> bool:
    try:
        response = httpx.get(url, timeout=2.0)
        return response.status_code < 500
    except httpx.HTTPError:
        return False


def _collector_js() -> str:
    return r"""
    () => {
      const clean = (value, max = 0) => {
        const text = String(value || "").replace(/\s+/g, " ").trim();
        return max > 0 ? text.slice(0, max) : text;
      };
      const cssEscape = (value) => window.CSS?.escape ? window.CSS.escape(value) : String(value).replace(/["\\]/g, "\\$&");
      const selectorFor = (element) => {
        if (!element || element.nodeType !== 1) return "";
        if (element.id) return `#${cssEscape(element.id)}`;
        for (const attr of ["data-testid", "data-test", "data-action", "aria-label", "name"]) {
          const value = element.getAttribute(attr);
          if (value) return `${element.tagName.toLowerCase()}[${attr}="${cssEscape(value)}"]`;
        }
        const classes = Array.from(element.classList || []).slice(0, 2);
        return classes.length ? `${element.tagName.toLowerCase()}.${classes.map(cssEscape).join(".")}` : element.tagName.toLowerCase();
      };
      const textFor = (element) => clean(
        element?.innerText ||
        element?.textContent ||
        element?.value ||
        element?.getAttribute?.("aria-label") ||
        element?.getAttribute?.("title") ||
        element?.getAttribute?.("name") ||
        element?.getAttribute?.("data-testid")
      );
      const visible = (elements) => Array.from(elements || []).filter((element) => {
        const style = window.getComputedStyle?.(element);
        return element && !element.hidden && element.getAttribute?.("aria-hidden") !== "true" &&
          !(style && (style.display === "none" || style.visibility === "hidden"));
      });
      const submitFor = (form) => {
        const explicit = visible(form.querySelectorAll("button[type='submit'], input[type='submit'], input[type='image']"))[0];
        if (explicit) return explicit;
        const buttons = visible(form.querySelectorAll("button, input[type='button'], [role='button']"));
        return buttons.find((button) => /\b(apply|book|calculate|check|checkout|compare|continue|estimate|find|get|join|next|order|pay|quote|quotes|request|reserve|save|schedule|search|send|show|submit)\b/i.test(textFor(button))) ||
          buttons[0] ||
          null;
      };
      const labelFor = (field) => {
        const labelTextWithoutControls = (label) => {
          if (!label) return "";
          const clone = label.cloneNode(true);
          clone.querySelectorAll("input, select, textarea, option, [contenteditable='true'], [role='checkbox'], [role='combobox'], [role='listbox'], [role='radio'], [role='searchbox'], [role='textbox']").forEach((node) => node.remove());
          return clean(clone.innerText || clone.textContent, 160);
        };
        const id = field.id || field.getAttribute("id");
        const explicit = id ? labelTextWithoutControls(document.querySelector(`label[for="${cssEscape(id)}"]`)) : "";
        const wrapping = labelTextWithoutControls(field.closest?.("label"));
        const containerLabel = field.parentElement?.querySelector?.("label");
        const nearby = containerLabel && !containerLabel.contains(field) ? labelTextWithoutControls(containerLabel) : "";
        const previous = field.previousElementSibling?.tagName?.toLowerCase() === "label" ? labelTextWithoutControls(field.previousElementSibling) : "";
        return clean(explicit || wrapping || nearby || previous || field.getAttribute("aria-label"), 160);
      };
      const fieldSelector = [
        "input:not([type='hidden']):not([type='submit']):not([type='button']):not([type='reset'])",
        "select",
        "textarea",
        "[contenteditable='true']",
        "[role='checkbox']",
        "[role='combobox']",
        "[role='listbox']",
        "[role='radio']",
        "[role='searchbox']",
        "[role='textbox']",
      ].join(",");
      const formFields = (form) => Array.from(form.querySelectorAll(fieldSelector)).slice(0, 12).map((field) => ({
        selector: selectorFor(field),
        name: clean(field.getAttribute("name") || field.id || field.getAttribute("aria-label"), 160),
        label: labelFor(field),
        type: clean(field.getAttribute("type") || field.tagName, 40).toLowerCase(),
        placeholder: clean(field.getAttribute("placeholder"), 160),
        required: Boolean(field.required || field.hasAttribute("required") || field.getAttribute("aria-required") === "true"),
        options: Array.from(field.querySelectorAll?.("option") || []).slice(0, 20).map((option) => ({
          label: clean(option.label || option.innerText || option.textContent, 160),
          value: clean(option.value || option.getAttribute("value"), 160),
        })).filter((option) => option.label || option.value),
      })).filter((field) => field.selector);
      const forms = Array.from(document.querySelectorAll("form")).slice(0, 80).map((form) => {
        const input = form.querySelector(fieldSelector);
        const submit = submitFor(form);
        return {
          label: clean([textFor(submit), form.innerText || input?.getAttribute("placeholder") || input?.getAttribute("name") || input?.getAttribute("aria-label")].filter(Boolean).join(" "), 160),
          selector: selectorFor(form),
          input_selector: selectorFor(input),
          submit_selector: selectorFor(submit),
          fields: formFields(form),
        };
      }).filter((form) => form.input_selector);
      const buttons = Array.from(document.querySelectorAll("button, a[href], input[type='button'], input[type='submit'], [role='button']")).slice(0, 80).map((element) => ({
        label: clean(textFor(element), 160),
        selector: selectorFor(element),
        href: clean(element.href || "", 600),
      })).filter((element) => element.label || element.href);
      const links = Array.from(document.querySelectorAll("a[href]")).slice(0, 80).map((element) => ({
        label: clean(textFor(element), 160),
        selector: selectorFor(element),
        href: clean(element.href || "", 600),
      })).filter((element) => element.href);
      return {
        site_id: "policy-live-smoke",
        origin: window.location.origin,
        url: window.location.href,
        title: document.title || "",
        text_sample: clean(document.body?.innerText || "").slice(0, 2500),
        html_sample: clean(document.body?.innerHTML || "").slice(0, 6000),
        buttons,
        links,
        forms,
        platform_hints: {},
        barrier_hints: {},
      };
    }
    """
