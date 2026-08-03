import { injectStyles } from "./styles";
import { initWidget, addMessage, updateMessage } from "./ui";
import { setupRecorder } from "../audio/recorder";
import { processAudio, isSpeaking, stopPlayback } from "../runtime/api";
import { config } from "../core/config";
import { createConversationMemory } from "../session/conversationMemory";
import { replayPendingSpeech, speakText } from "../audio/speech";
import { startWidgetAvailabilityLoop } from "../session/widgetAvailability";
import {
  AUTO_GREETING_DELAY_MS,
  AUTO_GREETING_VISIBLE_MS,
  DEFAULT_VISIBLE_RESET_DELAY_MS,
  STATUS,
} from "../core/constants";

window.__mayabot_identifier = "voice-orb";
let activeRecorder = null;
let activeWidgetCleanup = null;

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

  const conversationMemory = createConversationMemory();
  let activeStreamNode = null;
  let activeStreamText = "";
  let processingTurn = false;

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
          conversationMemory.rememberUserMessage(text);
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
          conversationMemory.rememberAssistantMessage(text, uiActions);
          activeStreamNode = null;
          activeStreamText = "";
        },
        onActionResults: conversationMemory.rememberActionResults,
        onStatusChange: handleStatusChange,
        onComplete: () => scheduleVisibleReset()
      }, conversationMemory.history);
    } finally {
      processingTurn = false;
      elements.btn.disabled = false;
      activeStreamNode = null;
      activeStreamText = "";
    }
  }

  const recorder = setupRecorder(handleStop, handleStatusChange);
  activeRecorder = recorder;

  // While Maya is speaking, the orb is a Stop control. Interrupting speech must
  // never start a recording. The target handler runs after window capture replay
  // listeners and immediately cancels anything they attempted to resume.
  let justStoppedPlayback = false;
  let stopClickGuardTimer = null;
  function stopSpeakingIfActive() {
    if (!isSpeaking()) return false;
    stopPlayback();
    handleStatusChange(STATUS.READY);
    return true;
  }

  elements.btn.setAttribute("aria-label", "Maya voice assistant. Tap to talk, or tap to stop when speaking.");
  elements.btn.setAttribute("title", "Tap to talk — tap or press Escape to stop Maya");

  elements.btn.addEventListener(
    "pointerdown",
    () => {
      if (!stopSpeakingIfActive()) return;
      justStoppedPlayback = true;
      if (stopClickGuardTimer) window.clearTimeout(stopClickGuardTimer);
      stopClickGuardTimer = window.setTimeout(() => {
        justStoppedPlayback = false;
        stopClickGuardTimer = null;
      }, 750);
    },
    { capture: true },
  );

  elements.btn.addEventListener("click", () => {
    if (justStoppedPlayback) {
      justStoppedPlayback = false;
      if (stopClickGuardTimer) window.clearTimeout(stopClickGuardTimer);
      stopClickGuardTimer = null;
      return;
    }
    if (processingTurn) return;
    if (stopSpeakingIfActive()) return;
    recorder.toggle();
  });

  const handleEscape = (event) => {
    if (event.key === "Escape") stopSpeakingIfActive();
  };
  document.addEventListener("keydown", handleEscape);

  // Resume browser speech that autoplay blocked — but never when the gesture is on
  // the orb, where a tap means "stop", not "replay".
  const handlePlaybackReplay = (event) => {
    if (elements.btn.contains(event.target)) return;
    replayPendingSpeech();
  };
  document.addEventListener("pointerdown", handlePlaybackReplay, { capture: true });

  activeWidgetCleanup = () => {
    document.removeEventListener("keydown", handleEscape);
    document.removeEventListener("pointerdown", handlePlaybackReplay, { capture: true });
    if (stopClickGuardTimer) window.clearTimeout(stopClickGuardTimer);
    activeWidgetCleanup = null;
  };

  if (shouldAutoGreet()) {
    markAutoGreeted();
    window.setTimeout(() => {
      if (conversationMemory.history.length > 0) return;
      const greeting = `Welcome to ${config.brandName}. How can I help you today?`;
      addMessage(elements, greeting, "ai");
      handleStatusChange(STATUS.READY);
      scheduleVisibleReset(AUTO_GREETING_VISIBLE_MS);
      speakText(greeting);
    }, AUTO_GREETING_DELAY_MS);
  }
}

function shutdownWidget() {
  activeRecorder?.cancel();
  activeRecorder = null;
  activeWidgetCleanup?.();
  stopPlayback();
  window.__mayabotBooted = false;
  document.getElementById("mayabot-widget")?.remove();
  document.getElementById("mayabot-product-panel")?.remove();
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
  document.addEventListener("DOMContentLoaded", () => startWidgetAvailabilityLoop({ boot, shutdownWidget }));
} else {
  startWidgetAvailabilityLoop({ boot, shutdownWidget });
}
