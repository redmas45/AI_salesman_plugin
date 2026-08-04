import { injectStyles } from "./styles";
import { initWidget, addMessage, updateMessage } from "./ui";
import { setupRecorder } from "../audio/recorder";
import { processAudio, isSpeaking, resetTransport, stopPlayback } from "../runtime/api";
import { config } from "../core/config";
import { createConversationMemory } from "../session/conversationMemory";
import { createSessionReset, installSessionResetContract } from "../session/sessionReset";
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
    // The orb visual class is owned solely by applyOrbStateCopy above, so the
    // status line here never toggles it independently (no state race).
    if (statusStr === STATUS.RECORDING) {
      if (clearTimer) {
        window.clearTimeout(clearTimer);
        clearTimer = null;
      }
      elements.msgs.innerHTML = "";
      elements.chat.classList.add("visible");
      elements.status.innerText = "Listening...";
      elements.status.classList.add("listening");
    } else if (statusStr === STATUS.PROCESSING) {
      elements.chat.classList.add("visible");
      elements.status.innerText = "Analyzing...";
      elements.status.classList.add("processing");
    } else if (statusStr === STATUS.READY) {
      elements.status.innerText = "Ready";
      elements.status.classList.add("ready");
    } else if (statusStr === STATUS.ERROR) {
      elements.status.innerText = detail || "Try again";
      elements.status.classList.add("error");
    }
  }

  const conversationMemory = createConversationMemory();
  let activeStreamNode = null;
  let activeStreamText = "";
  let processingTurn = false;
  // One monotonic token owns the active turn. A callback (or a delayed response)
  // that belongs to a superseded or cancelled turn carries a stale token and is
  // ignored, so an older request can never overwrite the current state.
  let turnToken = 0;

  // Stop Callback
  async function handleStop(blob) {
    if (processingTurn) return;
    processingTurn = true;
    const myToken = ++turnToken;
    const isCurrent = () => myToken === turnToken;
    elements.btn.disabled = true;
    activeStreamNode = null;
    activeStreamText = "";
    try {
      await processAudio(blob, elements, {
        onUserMessage: (text) => {
          if (!isCurrent()) return;
          addMessage(elements, text, "user");
          conversationMemory.rememberUserMessage(text);
        },
        onAssistantChunk: (_chunk, fullText) => {
          if (!isCurrent()) return;
          activeStreamText = fullText;
          if (!activeStreamNode) {
            activeStreamNode = addMessage(elements, "", "ai");
          }
          updateMessage(elements, activeStreamNode, activeStreamText);
        },
        onAssistantMessage: (text, uiActions, meta = {}) => {
          if (!isCurrent()) return;
          if (meta.streamed && activeStreamNode) {
            updateMessage(elements, activeStreamNode, text);
          } else {
            addMessage(elements, text, "ai");
          }
          conversationMemory.rememberAssistantMessage(text, uiActions);
          activeStreamNode = null;
          activeStreamText = "";
        },
        onActionResults: (results) => {
          if (isCurrent()) conversationMemory.rememberActionResults(results);
        },
        onStatusChange: (statusStr, detail) => {
          if (isCurrent()) handleStatusChange(statusStr, detail);
        },
        onComplete: () => {
          if (isCurrent()) scheduleVisibleReset();
        },
        // Send the bounded, summarized history so the payload (and the prompt the
        // model reads) stays flat as the conversation grows: latest exchanges
        // verbatim, older turns condensed into one summary.
      }, conversationMemory.historyForRequest());
    } finally {
      if (isCurrent()) {
        processingTurn = false;
        elements.btn.disabled = false;
      }
      activeStreamNode = null;
      activeStreamText = "";
    }
  }

  // The customer stopped the current turn. Invalidate its callbacks, abort the
  // in-flight request as a cancellation (never a connection error), stop any
  // playback, and return to Ready. The page is never navigated or reloaded.
  function cancelActiveTurn() {
    turnToken += 1;
    resetTransport("user_cancel");
    stopPlayback();
    processingTurn = false;
    elements.btn.disabled = false;
    activeStreamNode = null;
    activeStreamText = "";
    emitRuntimeEvent({ event_type: "voice_turn_cancelled", stage: "orb_gesture", status: "cancelled" });
    handleStatusChange(STATUS.READY);
  }

  const recorder = setupRecorder(handleStop, handleStatusChange);
  activeRecorder = recorder;

  // A turn is "in flight" while its request is processing or its answer is
  // speaking. A single gesture on the orb during that window stops it.
  function turnInFlight() {
    return processingTurn || isSpeaking();
  }

  function handleKeyboardActivation() {
    if (turnInFlight()) {
      cancelActiveTurn();
      return;
    }
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
    elements.btn.setAttribute("data-orb-state", state);
    // The visual class follows the same single state so idle, listening, and
    // speaking are each distinct and never race one another.
    elements.btn.classList.toggle("recording", state === "recording");
    elements.btn.classList.toggle("speaking", state === "speaking");
  }

  applyOrbStateCopy("idle");

  elements.btn.addEventListener("click", (event) => {
    // Browsers emit a second click with detail=2 for a double-click. Ignore the
    // duplicate so a double-click does not immediately undo what the first did.
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
    if (turnInFlight()) cancelActiveTurn();
  };
  document.addEventListener("keydown", handleEscape);

  // Resume browser speech that autoplay blocked — but never when the gesture is on
  // the orb, where a tap means "stop", not "replay".
  const handlePlaybackReplay = (event) => {
    if (elements.btn.contains(event.target)) return;
    replayPendingSpeech();
  };
  document.addEventListener("pointerdown", handlePlaybackReplay, { capture: true });

  // Logout contract: the host calls this when IT decides the session is over.
  // Nothing is inferred from clicks or links on the host page.
  const removeSessionResetContract = installSessionResetContract(
    createSessionReset({
      cancelRecording: () => recorder.cancel(),
      stopPlayback,
      resetTransport,
      conversationMemory,
      clearOverlays: () => {
        elements.msgs.innerHTML = "";
        elements.chat.classList.remove("visible");
        document.getElementById("mayabot-product-panel")?.remove();
      },
      rotateSessionId: () => config.rotateSessionId(),
    }),
  );

  activeWidgetCleanup = () => {
    document.removeEventListener("keydown", handleEscape);
    document.removeEventListener("pointerdown", handlePlaybackReplay, { capture: true });
    removeSessionResetContract();
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
