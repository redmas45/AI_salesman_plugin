import { injectStyles } from "./styles";
import { initWidget, addMessage } from "./widget";
import { setupRecorder } from "./recorder";
import { processAudio } from "./api";

// Initialize UI
window.__shopbot_identifier = "voice-orb";
function boot() {
  if (window.__shopbotBooted || document.getElementById("shopbot-widget")) {
    return;
  }
  window.__shopbotBooted = true;

  injectStyles();
  const elements = initWidget();

  // Status Callback
  let clearTimer = null;
  function scheduleVisibleReset(delayMs = 2400) {
    if (clearTimer) window.clearTimeout(clearTimer);
    clearTimer = window.setTimeout(() => {
      elements.msgs.innerHTML = "";
      elements.chat.classList.remove("visible");
      clearTimer = null;
    }, delayMs);
  }

  function handleStatusChange(statusStr) {
    elements.status.className = ""; // Reset all classes
    if (statusStr === "recording") {
      if (clearTimer) {
        window.clearTimeout(clearTimer);
        clearTimer = null;
      }
      elements.msgs.innerHTML = "";
      elements.btn.classList.add("recording");
      elements.chat.classList.add("visible");
      elements.status.innerText = "Listening...";
      elements.status.classList.add("listening");
    } else if (statusStr === "processing") {
      elements.btn.classList.remove("recording");
      elements.chat.classList.add("visible");
      elements.status.innerText = "Analyzing...";
      elements.status.classList.add("processing");
    } else if (statusStr === "ready") {
      elements.status.innerText = "Ready";
      elements.status.classList.add("ready");
    } else if (statusStr === "error") {
      elements.status.innerText = "Error";
      elements.status.classList.add("error");
      elements.btn.classList.remove("recording");
    }
  }

  // Message history cache (limit to last 12 messages)
  const conversationHistory = [];

  // Extract product IDs from ui_actions and append them as context to assistant content.
  // This lets the backend resolve ordinal references like "add the first one" in follow-up turns.
  function buildAssistantContent(text, uiActions) {
    const productIds = [];
    for (const action of (uiActions || [])) {
      const params = action.params || {};
      if (params.product_ids && Array.isArray(params.product_ids)) {
        for (const pid of params.product_ids) {
          if (!productIds.includes(pid)) productIds.push(pid);
        }
      }
      if (params.product_id && !productIds.includes(params.product_id)) {
        productIds.push(params.product_id);
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
    await processAudio(blob, elements, {
      onMessage: (text, role, uiActions) => {
        addMessage(elements, text, role);
        const apiRole = role === "ai" ? "assistant" : role;
        // For assistant messages, embed product IDs so next turn has context
        const content = apiRole === "assistant" ? buildAssistantContent(text, uiActions) : text;
        conversationHistory.push({ role: apiRole, content });
        if (conversationHistory.length > 12) {
          conversationHistory.shift();
        }
      },
      onStatusChange: handleStatusChange,
      onComplete: () => scheduleVisibleReset()
    }, conversationHistory);
  }

  // Setup Recorder
  const recorder = setupRecorder(handleStop, handleStatusChange);

  // Bind Button
  elements.btn.addEventListener("click", () => {
    recorder.toggle();
  });
}

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", boot);
} else {
  boot();
}
