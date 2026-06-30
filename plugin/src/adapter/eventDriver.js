export function activateElement(element) {
  if (!element) return false;
  prepareElement(element);
  dispatchPointerMousePair(element, "down");
  dispatchPointerMousePair(element, "up");
  if (typeof element.click === "function") {
    element.click();
  } else {
    dispatchMouseEvent(element, "click");
  }
  dispatchKeyboardActivation(element);
  return true;
}

export function enterText(element, value) {
  if (!element) return false;
  prepareElement(element);
  setNativeValue(element, clean(value));
  dispatchTextEvents(element);
  return true;
}

export function setControlChecked(element, checked) {
  if (!element) return false;
  prepareElement(element);
  if ("checked" in element) {
    element.checked = checked;
    dispatchTextEvents(element);
    return true;
  }
  element.setAttribute("aria-checked", checked ? "true" : "false");
  dispatchTextEvents(element);
  return true;
}

export function selectNativeOption(element, value) {
  if (!element || clean(element.tagName).toLowerCase() !== "select") return false;
  const wanted = clean(value).toLowerCase();
  const option = Array.from(element.options || []).find((item) => {
    const optionValue = clean(item.value).toLowerCase();
    const optionText = clean(item.textContent).toLowerCase();
    return optionValue === wanted ||
      optionText === wanted ||
      optionValue.includes(wanted) ||
      optionText.includes(wanted) ||
      wanted.includes(optionValue) ||
      wanted.includes(optionText);
  });
  if (option) element.value = option.value;
  else element.value = clean(value);
  dispatchTextEvents(element);
  return true;
}

export function submitFormElement(formOrSubmit) {
  if (!formOrSubmit) return false;
  const form = clean(formOrSubmit.tagName).toLowerCase() === "form" ? formOrSubmit : formOrSubmit.closest?.("form");
  if (form && typeof form.requestSubmit === "function") {
    form.requestSubmit();
    return true;
  }
  return activateElement(formOrSubmit);
}

function prepareElement(element) {
  try {
    element.scrollIntoView?.({ behavior: "smooth", block: "center", inline: "center" });
  } catch (_err) {
    // Ignore scroll failures from detached or browser-managed elements.
  }
  if (typeof element.focus === "function") {
    element.focus({ preventScroll: true });
  }
}

function setNativeValue(element, value) {
  if (shouldSetTextContent(element)) {
    element.textContent = value;
    return;
  }
  const prototype = Object.getPrototypeOf(element);
  const descriptor = Object.getOwnPropertyDescriptor(prototype, "value");
  if (descriptor?.set) {
    descriptor.set.call(element, value);
    return;
  }
  element.value = value;
}

function dispatchTextEvents(element) {
  dispatchInputEvent(element, "beforeinput");
  dispatchInputEvent(element, "input");
  element.dispatchEvent(new Event("change", { bubbles: true }));
}

function dispatchPointerMousePair(element, direction) {
  dispatchPointerEvent(element, `pointer${direction}`);
  dispatchMouseEvent(element, `mouse${direction}`);
}

function dispatchPointerEvent(element, type) {
  if (typeof PointerEvent !== "function") return;
  element.dispatchEvent(
    new PointerEvent(type, {
      bubbles: true,
      cancelable: true,
      pointerType: "mouse",
      isPrimary: true,
    }),
  );
}

function dispatchMouseEvent(element, type) {
  element.dispatchEvent(
    new MouseEvent(type, {
      bubbles: true,
      cancelable: true,
      view: window,
    }),
  );
}

function dispatchInputEvent(element, type) {
  if (typeof InputEvent === "function") {
    element.dispatchEvent(
      new InputEvent(type, {
        bubbles: true,
        cancelable: true,
        inputType: "insertText",
      }),
    );
    return;
  }
  element.dispatchEvent(new Event(type, { bubbles: true, cancelable: true }));
}

function dispatchKeyboardActivation(element) {
  const role = clean(element.getAttribute?.("role")).toLowerCase();
  if (!["button", "link", "menuitem", "option", "tab"].includes(role)) return;
  dispatchKey(element, "keydown", "Enter");
  dispatchKey(element, "keyup", "Enter");
  if (role === "button" || role === "tab") {
    dispatchKey(element, "keydown", " ");
    dispatchKey(element, "keyup", " ");
  }
}

function dispatchKey(element, type, key) {
  element.dispatchEvent(
    new KeyboardEvent(type, {
      bubbles: true,
      cancelable: true,
      key,
    }),
  );
}

function shouldSetTextContent(element) {
  const role = clean(element?.getAttribute?.("role")).toLowerCase();
  return Boolean(element?.isContentEditable || (!("value" in element) && ["searchbox", "textbox"].includes(role)));
}

function clean(value) {
  return String(value || "").trim();
}
