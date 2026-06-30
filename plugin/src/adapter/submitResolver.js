const EXPLICIT_SUBMIT_SELECTOR = "button[type='submit'], input[type='submit'], input[type='image']";
const BUTTON_SELECTOR = "button, input[type='button'], [role='button']";
const SUBMIT_INTENT_PATTERN =
  /\b(apply|book|calculate|check|checkout|compare|continue|estimate|find|get|join|next|order|pay|quote|quotes|request|reserve|save|schedule|search|send|show|submit)\b/i;

export function submitElementFor(form) {
  if (!form?.querySelectorAll) return null;

  const explicit = firstVisible(form.querySelectorAll(EXPLICIT_SUBMIT_SELECTOR));
  if (explicit) return explicit;

  const buttons = visibleElements(form.querySelectorAll(BUTTON_SELECTOR));
  const submitLike = buttons.find((button) => SUBMIT_INTENT_PATTERN.test(elementText(button)));
  return submitLike || buttons[0] || null;
}

export function submitTextFor(element) {
  return elementText(element);
}

function firstVisible(elements) {
  return visibleElements(elements)[0] || null;
}

function visibleElements(elements) {
  return Array.from(elements || []).filter(isVisibleElement);
}

function isVisibleElement(element) {
  if (!element || element.hidden || element.getAttribute?.("aria-hidden") === "true") return false;
  const style = window.getComputedStyle?.(element);
  return !(style && (style.display === "none" || style.visibility === "hidden"));
}

function elementText(element) {
  return clean(
    element?.innerText ||
      element?.textContent ||
      element?.value ||
      element?.getAttribute?.("aria-label") ||
      element?.getAttribute?.("title") ||
      element?.getAttribute?.("name") ||
      element?.getAttribute?.("data-testid"),
  );
}

function clean(value) {
  return String(value || "").replace(/\s+/g, " ").trim();
}
