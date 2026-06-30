export const CLICKABLE_SELECTOR = [
  "button",
  "a[href]",
  "summary",
  "input[type='button']",
  "input[type='submit']",
  "[role='button']",
  "[role='link']",
  "[role='menuitem']",
  "[role='option']",
  "[role='tab']",
  "[aria-haspopup]",
  "[tabindex]:not([tabindex='-1'])",
].join(", ");

export const FIELD_SELECTOR = [
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
].join(", ");

export const FORM_INPUT_SELECTOR = FIELD_SELECTOR;

export const SUBMIT_SELECTOR = [
  "button[type='submit']",
  "input[type='submit']",
  "button",
  "[role='button']",
].join(", ");
