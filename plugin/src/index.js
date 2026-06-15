import { injectStyles } from "./styles";
import { initWidget, addMessage, updateMessage } from "./widget";
import { setupRecorder } from "./recorder";
import { processAudio } from "./api";
import { config } from "./config";
import {
  AUTO_GREETING_DELAY_MS,
  AUTO_GREETING_VISIBLE_MS,
  ACTION_PARAMS,
  CONVERSATION_HISTORY_LIMIT,
  DEFAULT_VISIBLE_RESET_DELAY_MS,
  STATUS,
} from "./constants";

window.__shopbot_identifier = "voice-orb";
function boot() {
  if (window.__shopbotBooted || document.getElementById("shopbot-widget")) {
    return;
  }
  window.__shopbotBooted = true;

  injectStyles();
  const elements = initWidget();

  let clearTimer = null;
  function scheduleVisibleReset(delayMs = DEFAULT_VISIBLE_RESET_DELAY_MS) {
    if (clearTimer) window.clearTimeout(clearTimer);
    clearTimer = window.setTimeout(() => {
      elements.msgs.innerHTML = "";
      elements.chat.classList.remove("visible");
      clearTimer = null;
    }, delayMs);
  }

  function handleStatusChange(statusStr) {
    elements.status.className = "";
    if (statusStr === STATUS.RECORDING) {
      if (clearTimer) {
        window.clearTimeout(clearTimer);
        clearTimer = null;
      }
      elements.msgs.innerHTML = "";
      elements.btn.classList.add("recording");
      elements.chat.classList.add("visible");
      elements.status.innerText = "Listening...";
      elements.status.classList.add("listening");
    } else if (statusStr === STATUS.PROCESSING) {
      elements.btn.classList.remove("recording");
      elements.chat.classList.add("visible");
      elements.status.innerText = "Analyzing...";
      elements.status.classList.add("processing");
    } else if (statusStr === STATUS.READY) {
      elements.status.innerText = "Ready";
      elements.status.classList.add("ready");
    } else if (statusStr === STATUS.ERROR) {
      elements.status.innerText = "Error";
      elements.status.classList.add("error");
      elements.btn.classList.remove("recording");
    }
  }

  const conversationHistory = [];
  let activeStreamNode = null;
  let activeStreamText = "";

  // Extract product IDs from ui_actions and append them as context to assistant content.
  // This lets the backend resolve ordinal references like "add the first one" in follow-up turns.
  function buildAssistantContent(text, uiActions) {
    const productIds = [];
    for (const action of (uiActions || [])) {
      const params = action.params || {};
      if (params[ACTION_PARAMS.PRODUCT_IDS] && Array.isArray(params[ACTION_PARAMS.PRODUCT_IDS])) {
        for (const pid of params[ACTION_PARAMS.PRODUCT_IDS]) {
          if (!productIds.includes(pid)) productIds.push(pid);
        }
      }
      if (params[ACTION_PARAMS.PRODUCT_ID] && !productIds.includes(params[ACTION_PARAMS.PRODUCT_ID])) {
        productIds.push(params[ACTION_PARAMS.PRODUCT_ID]);
      }
    }
    if (productIds.length > 0) {
      // Append a machine-readable product ID list the backend can parse
      return text + ` [PRODUCT_IDS: ${productIds.join(",")}]`;
    }
    return text;
  }

  // Stop Callback
  async function handleStop(blob) {
    activeStreamNode = null;
    activeStreamText = "";
    await processAudio(blob, elements, {
      onUserMessage: (text) => {
        addMessage(elements, text, "user");
        conversationHistory.push({ role: "user", content: text });
        if (conversationHistory.length > CONVERSATION_HISTORY_LIMIT) {
          conversationHistory.shift();
        }
      },
      onAssistantChunk: (_chunk, fullText) => {
        activeStreamText = fullText;
        if (!activeStreamNode) {
          activeStreamNode = addMessage(elements, "", "ai");
        }
        updateMessage(elements, activeStreamNode, activeStreamText);
      },
      onAssistantMessage: (text, uiActions, meta = {}) => {
        if (meta.streamed && activeStreamNode) {
          updateMessage(elements, activeStreamNode, text);
        } else {
          addMessage(elements, text, "ai");
        }
        const content = buildAssistantContent(text, uiActions);
        conversationHistory.push({ role: "assistant", content });
        if (conversationHistory.length > CONVERSATION_HISTORY_LIMIT) {
          conversationHistory.shift();
        }
        activeStreamNode = null;
        activeStreamText = "";
      },
      onStatusChange: handleStatusChange,
      onComplete: () => scheduleVisibleReset()
    }, conversationHistory);
  }

  const recorder = setupRecorder(handleStop, handleStatusChange);

  elements.btn.addEventListener("click", () => {
    recorder.toggle();
  });

  if (shouldAutoGreet()) {
    markAutoGreeted();
    window.setTimeout(() => {
      if (conversationHistory.length > 0) return;
      const greeting = `Welcome to ${config.brandName}. How can I help you today?`;
      addMessage(elements, greeting, "ai");
      handleStatusChange(STATUS.READY);
      scheduleVisibleReset(AUTO_GREETING_VISIBLE_MS);
      try {
        if ("speechSynthesis" in window) {
          const utterance = new SpeechSynthesisUtterance(greeting);
          utterance.rate = 1;
          utterance.pitch = 1;
          window.speechSynthesis.speak(utterance);
        }
      } catch (_err) {
        // Browser speech synthesis is best-effort only.
      }
    }, AUTO_GREETING_DELAY_MS);
  }
}

function shouldAutoGreet() {
  if (!config.autoGreet || !isHomePage()) return false;
  try {
    return window.sessionStorage.getItem(autoGreetKey()) !== "1";
  } catch (_err) {
    return !window.__shopbotAutoGreeted;
  }
}

function markAutoGreeted() {
  window.__shopbotAutoGreeted = true;
  try {
    window.sessionStorage.setItem(autoGreetKey(), "1");
  } catch (_err) {
    // sessionStorage may be unavailable in some embedded/privacy contexts.
  }
}

function autoGreetKey() {
  return `shopbot:auto-greeted:${config.siteId}`;
}

function isHomePage() {
  const path = window.location.pathname.replace(/\/+$/, "") || "/";
  return path === "/" || path.endsWith("/index.html");
}

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", boot);
} else {
  boot();
}
