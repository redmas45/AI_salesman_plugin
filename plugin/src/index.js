import { injectStyles } from "./styles";
import { initWidget, addMessage, updateMessage } from "./widget";
import { setupRecorder } from "./recorder";
import { processAudio } from "./api";
import { config } from "./config";
import {
  AUTO_GREETING_DELAY_MS,
  AUTO_GREETING_VISIBLE_MS,
  ACTION_PARAMS,
  API_PATHS,
  CONVERSATION_HISTORY_LIMIT,
  DEFAULT_VISIBLE_RESET_DELAY_MS,
  STATUS,
  WIDGET_STATUS_POLL_INTERVAL_MS,
} from "./constants";

window.__mayabot_identifier = "voice-orb";
let activeRecorder = null;
let statusPollTimer = null;
let pendingSpeechText = "";
let selectedSpeechVoiceName = "";
const SPEECH_RATE = 1;
const SPEECH_PITCH = 1.08;
const VOICE_FALLBACK_DELAY_MS = 300;
const FEMALE_VOICE_HINTS = Object.freeze([
  "hannah",
  "zira",
  "aria",
  "jenny",
  "samantha",
  "victoria",
  "tessa",
  "moira",
  "karen",
  "female",
  "woman",
  "nova",
  "shimmer",
  "google us english",
  "microsoft aria",
]);

function boot() {
  if (window.__mayabotBooted || document.getElementById("mayabot-widget")) {
    return;
  }
  window.__mayabotBooted = true;

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

  function handleStatusChange(statusStr, detail = "") {
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
      elements.status.innerText = detail || "Try again";
      elements.status.classList.add("error");
      elements.btn.classList.remove("recording");
    }
  }

  const conversationHistory = [];
  let activeStreamNode = null;
  let activeStreamText = "";
  let processingTurn = false;

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

  function rememberConversation(role, content) {
    const cleanContent = String(content || "").trim();
    if (!cleanContent) return;
    conversationHistory.push({ role, content: cleanContent });
    if (conversationHistory.length > CONVERSATION_HISTORY_LIMIT) {
      conversationHistory.shift();
    }
  }

  function rememberActionResults(results) {
    const content = buildActionResultContent(results);
    if (content) rememberConversation("assistant", content);
  }

  function buildActionResultContent(results) {
    const rows = (Array.isArray(results) ? results : [])
      .map(actionResultSummary)
      .filter(Boolean)
      .slice(0, 4);
    return rows.length ? `[BROWSER_ACTION_RESULTS: ${rows.join(" | ")}]` : "";
  }

  function actionResultSummary(result) {
    if (!result || typeof result !== "object" || !result.action) return "";
    const parts = [
      cleanActionResultText(result.action, 40),
      `status=${cleanActionResultText(result.status, 24) || "unknown"}`,
    ];
    const finalPath = urlPath(result.final_url);
    if (finalPath) parts.push(`final_path=${cleanActionResultText(finalPath, 120)}`);
    if (result.reason) parts.push(`reason=${cleanActionResultText(result.reason, 80)}`);
    if (result.evidence?.rendered_product_count !== undefined) {
      parts.push(`rendered_products=${Number(result.evidence.rendered_product_count || 0)}`);
    }
    if (result.evidence?.rendered_entity_count !== undefined) {
      parts.push(`rendered_records=${Number(result.evidence.rendered_entity_count || 0)}`);
    }
    return parts.join(" ");
  }

  function cleanActionResultText(value, limit) {
    return String(value || "").replace(/\s+/g, " ").trim().slice(0, limit);
  }

  function urlPath(value) {
    try {
      const url = new URL(String(value || ""), window.location.href);
      return `${url.pathname}${url.search}${url.hash}`;
    } catch (_err) {
      return "";
    }
  }

  // Stop Callback
  async function handleStop(blob) {
    if (processingTurn) return;
    processingTurn = true;
    elements.btn.disabled = true;
    activeStreamNode = null;
    activeStreamText = "";
    try {
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
          rememberConversation("assistant", content);
          activeStreamNode = null;
          activeStreamText = "";
        },
        onActionResults: rememberActionResults,
        onStatusChange: handleStatusChange,
        onComplete: () => scheduleVisibleReset()
      }, conversationHistory);
    } finally {
      processingTurn = false;
      elements.btn.disabled = false;
      activeStreamNode = null;
      activeStreamText = "";
    }
  }

  const recorder = setupRecorder(handleStop, handleStatusChange);
  activeRecorder = recorder;

  elements.btn.addEventListener("click", () => {
    if (processingTurn) return;
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
      speakText(greeting);
    }, AUTO_GREETING_DELAY_MS);
  }
}

function speakText(text) {
  if (!("speechSynthesis" in window) || !("SpeechSynthesisUtterance" in window)) return;
  pendingSpeechText = text;
  const speak = () => {
    try {
      const utterance = new SpeechSynthesisUtterance(text);
      const voice = preferredSpeechVoice(window.speechSynthesis.getVoices());
      if (voice) utterance.voice = voice;
      utterance.rate = SPEECH_RATE;
      utterance.pitch = SPEECH_PITCH;
      utterance.onstart = () => {
        pendingSpeechText = "";
      };
      utterance.onend = () => {
        pendingSpeechText = "";
      };
      window.speechSynthesis.cancel();
      window.speechSynthesis.resume();
      window.speechSynthesis.speak(utterance);
    } catch (_err) {
      // Browser speech synthesis is best-effort only.
    }
  };

  if (window.speechSynthesis.getVoices().length > 0) {
    speak();
    return;
  }

  window.speechSynthesis.onvoiceschanged = speak;
  window.setTimeout(speak, VOICE_FALLBACK_DELAY_MS);
}

function preferredSpeechVoice(voices) {
  if (!Array.isArray(voices) || voices.length === 0) return null;
  if (selectedSpeechVoiceName) {
    const selectedVoice = voices.find((voice) => voice.name === selectedSpeechVoiceName);
    if (selectedVoice) return selectedVoice;
  }
  const requestedName = config.speechVoiceName.toLowerCase();
  if (requestedName) {
    const exactVoice = voices.find((voice) => voice.name.toLowerCase() === requestedName);
    if (exactVoice) {
      selectedSpeechVoiceName = exactVoice.name;
      return exactVoice;
    }
  }
  let selectedVoice = null;
  if (config.speechVoicePreference.toLowerCase() !== "female") {
    selectedVoice = voices.find((voice) => voice.default) || voices[0];
  } else {
    selectedVoice = (
      voices.find((voice) => FEMALE_VOICE_HINTS.some((hint) => voice.name.toLowerCase().includes(hint))) ||
      voices.find((voice) => voice.default) ||
      voices[0]
    );
  }
  if (selectedVoice) selectedSpeechVoiceName = selectedVoice.name;
  return selectedVoice;
}

function replayPendingSpeech() {
  if (!pendingSpeechText) return;
  speakText(pendingSpeechText);
}

function shutdownWidget() {
  activeRecorder?.cancel();
  activeRecorder = null;
  selectedSpeechVoiceName = "";
  window.__mayabotBooted = false;
  document.getElementById("mayabot-widget")?.remove();
  document.getElementById("mayabot-product-panel")?.remove();
  try {
    window.speechSynthesis?.cancel();
  } catch (_err) {
    // Browser speech synthesis cancellation is best-effort only.
  }
}

async function fetchWidgetEnabled() {
  const url = new URL(API_PATHS.WIDGET_STATUS, config.apiUrl);
  url.searchParams.set("site_id", config.siteId);
  const response = await fetch(url.toString(), {
    cache: "no-store",
    headers: { Accept: "application/json" },
  });
  if (!response.ok) return true;
  const data = await response.json();
  return data.enabled !== false;
}

async function syncWidgetAvailability() {
  try {
    const enabled = await fetchWidgetEnabled();
    if (enabled) {
      boot();
      return;
    }
    shutdownWidget();
  } catch (_err) {
    boot();
  }
}

function startWidgetAvailabilityLoop() {
  if (statusPollTimer) return;
  syncWidgetAvailability();
  statusPollTimer = window.setInterval(syncWidgetAvailability, WIDGET_STATUS_POLL_INTERVAL_MS);
}

function shouldAutoGreet() {
  if (!config.autoGreet || !isHomePage()) return false;
  try {
    return window.sessionStorage.getItem(autoGreetKey()) !== "1";
  } catch (_err) {
    return !window.__mayabotAutoGreeted;
  }
}

function markAutoGreeted() {
  window.__mayabotAutoGreeted = true;
  try {
    window.sessionStorage.setItem(autoGreetKey(), "1");
  } catch (_err) {
    // sessionStorage may be unavailable in some embedded/privacy contexts.
  }
}

function autoGreetKey() {
  return `mayabot:auto-greeted:${config.siteId}`;
}

function isHomePage() {
  const path = window.location.pathname.replace(/\/+$/, "") || "/";
  return path === "/" || path.endsWith("/index.html");
}

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", startWidgetAvailabilityLoop);
} else {
  startWidgetAvailabilityLoop();
}

document.addEventListener("pointerdown", replayPendingSpeech, { capture: true });
