import { injectStyles } from "./styles";
import { initWidget, addMessage, updateMessage } from "./ui";
import { setupRecorder } from "../audio/recorder";
import { processAudio, isSpeaking, stopPlayback } from "../runtime/api";
import { config } from "../core/config";
import { createConversationMemory } from "../session/conversationMemory";
import { emitRuntimeEvent } from "../runtime/diagnostics";
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
    applyOrbStateCopy(orbStateFor(statusStr));
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

  function stopSpeakingIfActive() {
    if (!isSpeaking()) return false;
    stopPlayback();
    emitRuntimeEvent({ event_type: "voice_playback_stopped", stage: "orb_gesture", status: "cancelled" });
    handleStatusChange(STATUS.READY);
    return true;
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
    recorder.toggle();
  }

  // The orb means different things in each state, so its accessible name and
  // tooltip must say what THIS click will do rather than a generic instruction.
  const ORB_STATE_COPY = {
    idle: {
      label: "Maya voice assistant. Click, press Enter, or press Space to talk.",
      title: "Click to talk",
    },
    recording: {
      label: "Maya is listening. Click once to send, or press Escape to cancel.",
      title: "Click once to send - Escape to cancel",
    },
    processing: {
      label: "Maya is working on your request. Please wait.",
      title: "Request in progress",
    },
    speaking: {
      label: "Maya is speaking. Click to stop, or press Escape to stop.",
      title: "Click to stop Maya",
    },
  };

  function orbStateFor(statusStr) {
    if (statusStr === STATUS.RECORDING) return "recording";
    if (statusStr === STATUS.PROCESSING) return "processing";
    return isSpeaking() ? "speaking" : "idle";
  }

  function applyOrbStateCopy(state) {
    const copy = ORB_STATE_COPY[state] || ORB_STATE_COPY.idle;
    elements.btn.setAttribute("aria-label", copy.label);
    elements.btn.setAttribute("title", copy.title);
  }

  applyOrbStateCopy("idle");

  elements.btn.addEventListener("click", (event) => {
    if (processingTurn) {
      stopSpeakingIfActive();
      return;
    }
    if (stopSpeakingIfActive()) return;
    // Browsers emit a second click with detail=2 for a double-click. The first
    // click already started recording, so ignore the duplicate instead of
    // immediately stopping it and replaying the open/close animation.
    if (event.detail > 1) return;
    handleKeyboardActivation();
  });

  const handleEscape = (event) => {
    if (event.key !== "Escape") return;
    if (isRecording) {
      recorder.cancel();
      emitRuntimeEvent({ event_type: "voice_recording_cancelled", stage: "keyboard_escape", status: "cancelled" });
      handleStatusChange(STATUS.READY);
      return;
    }
    stopSpeakingIfActive();
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
