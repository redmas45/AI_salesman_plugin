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

// How long a first click waits to see whether it is really a double click.
const DOUBLE_CLICK_WINDOW_MS = 280;

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
  let autoGreetTimer = null;
  let isRecording = false;
  function scheduleVisibleReset(delayMs = DEFAULT_VISIBLE_RESET_DELAY_MS) {
    if (clearTimer) window.clearTimeout(clearTimer);
    clearTimer = window.setTimeout(() => {
      elements.msgs.innerHTML = "";
      elements.chat.classList.remove("visible");
      clearTimer = null;
    }, delayMs);
  }

  function handleStatusChange(statusStr, detail = "") {
    // The recorder is the source of truth for whether the mic is open.
    isRecording = statusStr === STATUS.RECORDING;
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

  // ---------------------------------------------------------------------------
  // Orb gesture state machine (the single owner of orb intent).
  //
  //   speaking  + click        -> stop all playback, never record
  //   speaking  + double click -> stop, then start recording exactly once
  //   idle      + click        -> nothing (a stray click must not open the mic)
  //   idle      + double click -> start recording exactly once
  //   recording + click        -> stop and submit
  //   Enter/Space              -> direct toggle, so keyboard users need no timing
  //
  // Recording is only ever started from the second click of a pair, so the two
  // click events a double click produces cannot toggle recording twice.
  // ---------------------------------------------------------------------------
  let pendingClickTimer = null;
  let clickCount = 0;

  function clearPendingClick() {
    if (pendingClickTimer) window.clearTimeout(pendingClickTimer);
    pendingClickTimer = null;
    clickCount = 0;
  }

  function stopSpeakingIfActive() {
    if (!isSpeaking()) return false;
    stopPlayback();
    handleStatusChange(STATUS.READY);
    return true;
  }

  function startRecordingOnce() {
    if (isRecording) return;
    recorder.toggle();
  }

  function handleKeyboardActivation() {
    if (processingTurn) {
      stopSpeakingIfActive();
      return;
    }
    if (isRecording) {
      recorder.toggle();
      return;
    }
    if (stopSpeakingIfActive()) return;
    startRecordingOnce();
  }

  elements.btn.setAttribute(
    "aria-label",
    "Maya voice assistant. Double-click to talk; click to stop. Press Enter or Space to talk.",
  );
  elements.btn.setAttribute("title", "Double-click to talk; click to stop");

  elements.btn.addEventListener("click", (event) => {
    // Enter/Space on a button synthesises a click with detail 0. Keyboard users
    // get a direct toggle rather than having to double-press.
    if (event.detail === 0) {
      handleKeyboardActivation();
      return;
    }
    if (processingTurn) {
      stopSpeakingIfActive();
      return;
    }

    if (isRecording) {
      clearPendingClick();
      recorder.toggle();
      return;
    }

    clickCount += 1;
    if (clickCount === 1) {
      // Stop immediately so speech never continues while the user waits to see
      // whether this becomes a double click.
      stopSpeakingIfActive();
      pendingClickTimer = window.setTimeout(clearPendingClick, DOUBLE_CLICK_WINDOW_MS);
      return;
    }
    clearPendingClick();
    startRecordingOnce();
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
    // Every timer this boot created must die with it, or a disable/enable cycle
    // leaves callbacks firing against removed nodes.
    clearPendingClick();
    if (clearTimer) window.clearTimeout(clearTimer);
    clearTimer = null;
    if (autoGreetTimer) window.clearTimeout(autoGreetTimer);
    autoGreetTimer = null;
    activeWidgetCleanup = null;
  };

  if (shouldAutoGreet()) {
    markAutoGreeted();
    autoGreetTimer = window.setTimeout(() => {
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
