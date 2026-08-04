import { config } from "../core/config";
import { executeActions } from "../actionExecutor";
import { isSpeechActive, replayPendingSpeech, resetSpeech, speakText } from "../audio/speech";
import {
  TRANSPORT_CATEGORY,
  VoiceTransportError,
  classifyThrownError,
  errorForResponse,
  isCancellation,
} from "./transportErrors";
import {
  API_PATHS,
  AUDIO,
  HTTP_METHODS,
  STATUS,
  WS_CONNECT_TIMEOUT_MS,
  WS_MESSAGES,
  WS_TURN_TIMEOUT_MS,
} from "../core/constants";
import { emitRuntimeEvent } from "./diagnostics";
import { readPageState } from "../adapter/runtime/visibleEntities";

const MAX_WS_RETRIES = 3;
const RUNTIME_GLOBAL = "AIHubAdapterRuntime";
const ADAPTER_GLOBAL = "AIHubAdapter";

function wsUrlFromApiBase(apiUrl, siteId) {
  const url = new URL(API_PATHS.SHOP_WS, apiUrl);
  url.protocol = url.protocol === "https:" ? "wss:" : "ws:";
  url.searchParams.set("site_id", siteId);
  url.searchParams.set("session_id", config.sessionId);
  return url.toString();
}

function blobToBase64(blob) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onloadend = () => {
      const result = String(reader.result || "");
      resolve(result.includes(",") ? result.split(",").pop() : result);
    };
    reader.onerror = () => reject(reader.error || new Error("Failed to read audio blob"));
    reader.readAsDataURL(blob);
  });
}

class AudioQueue {
  constructor() {
    this.queue = [];
    this.blocked = [];
    this.playing = false;
    this.current = null;
    this.lastPlaybackStartMs = 0;
    this.installUnlockListeners();
  }

  push(audioB64, fallbackText = "") {
    if (!audioB64) return;
    this.queue.push({ audioB64, fallbackText });
    this.playNext();
  }

  playNext() {
    if (this.playing || this.queue.length === 0) return;
    this.playing = true;
    const item = this.queue.shift();
    const audio = new Audio(AUDIO.DATA_WAV_PREFIX + item.audioB64);
    audio.preload = "auto";
    this.current = audio;
    // Track playback start for latency diagnostics (slice 13).
    audio.onplay = () => {
      this.lastPlaybackStartMs = typeof performance !== "undefined" ? performance.now() : 0;
    };
    audio.onended = () => {
      this.current = null;
      this.playing = false;
      this.playNext();
    };
    audio.onerror = () => {
      this.current = null;
      if (item.fallbackText) speakTextFallback(item.fallbackText);
      this.playing = false;
      this.playNext();
    };
    audio.play().catch((err) => {
      console.warn("Audio playback failed", err);
      this.current = null;
      if (this.isAutoplayBlocked(err)) {
        if (item.fallbackText) {
          speakTextFallback(item.fallbackText);
        } else {
          this.blocked.unshift(item);
        }
        this.playing = false;
        return;
      }
      if (item.fallbackText) speakTextFallback(item.fallbackText);
      this.playing = false;
      this.playNext();
    });
  }

  installUnlockListeners() {
    if (typeof window === "undefined") return;
    const retry = () => {
      this.retryBlocked();
      replayPendingSpeech();
    };
    window.addEventListener("pointerdown", retry, { capture: true, passive: true });
    window.addEventListener("keydown", retry, { capture: true });
    window.addEventListener("touchstart", retry, { capture: true, passive: true });
  }

  retryBlocked() {
    if (!this.blocked.length) return;
    this.queue.unshift(...this.blocked.splice(0));
    this.playNext();
  }

  speakInsteadOfBlocked(text) {
    if (!text || !this.blocked.length) return;
    this.blocked = [];
    speakTextFallback(text);
  }

  isAutoplayBlocked(error) {
    const text = `${error?.name || ""} ${error?.message || error || ""}`.toLowerCase();
    return text.includes("notallowed") || text.includes("user didn't interact") || text.includes("not allowed");
  }

  // Authoritative stop: cancel queued + active generated audio AND browser speech.
  stop() {
    this.queue = [];
    this.blocked = [];
    if (this.current) {
      try {
        this.current.pause();
        this.current.currentTime = 0;
      } catch (_err) {
        // Pausing a not-yet-started element can throw; ignore.
      }
      this.current.onended = null;
      this.current.onerror = null;
      this.current = null;
    }
    this.playing = false;
    resetSpeech();
  }

  isSpeaking() {
    return this.playing || this.queue.length > 0 || isSpeechActive();
  }
}

const sharedAudioQueue = new AudioQueue();

// Single authoritative playback controls for the orb / keyboard / stop button.
export function stopPlayback() {
  sharedAudioQueue.stop();
}

export function isSpeaking() {
  return sharedAudioQueue.isSpeaking();
}

/**
 * Close the socket and abort any in-flight HTTP turn.
 *
 * `reason` distinguishes a user stop from a logout/session reset: a user stop
 * must surface as cancellation, never as a connection error, so the aborted turn
 * is tagged rather than being classified from its AbortError.
 */
export function resetTransport(reason = "reset") {
  wsTransport.reset(reason);
  httpTransport.reset(reason);
}

class HttpTransport {
  constructor() {
    this.inFlight = null;
    this.cancelled = false;
  }

  /** Abort an in-flight turn so a reset cannot be answered after the fact. */
  reset(reason = "reset") {
    this.cancelled = reason === "user_cancel";
    try {
      this.inFlight?.abort();
    } catch (_err) {
      // An already-settled controller throws nothing useful.
    }
    this.inFlight = null;
  }

  async sendAudio(blob, callbacks, conversationHistory = []) {
    const startedAt = runtimeNow();
    emitRuntimeEvent({
      event_type: "voice_turn_started",
      stage: "http_request",
      status: "started",
      metadata: { transport: "http", audio_type: blob?.type || "unknown" },
    });
    const formData = new FormData();
    formData.append("audio", blob, audioFilenameForBlob(blob));
    formData.append("site_id", config.siteId);
    formData.append("session_id", config.sessionId);
    if (conversationHistory && conversationHistory.length > 0) {
      formData.append("conversation_history", JSON.stringify(conversationHistory));
    }
    const pageContext = currentPageContext();
    if (pageContext) {
      formData.append("page_context", JSON.stringify(pageContext));
    }

    let res;
    const controller = typeof AbortController === "function" ? new AbortController() : null;
    this.inFlight = controller;
    this.cancelled = false;
    try {
      res = await fetch(`${config.apiUrl}${API_PATHS.SHOP}`, {
        method: HTTP_METHODS.POST,
        body: formData,
        signal: controller?.signal,
      });
    } catch (err) {
      // A turn the customer stopped is cancellation, not a dropped connection.
      if (this.cancelled || err?.name === "AbortError") {
        throw new VoiceTransportError(TRANSPORT_CATEGORY.CANCELLED, { stage: "user_cancel" });
      }
      // A rejected fetch never reached the server: DNS, TLS, blocked CORS
      // preflight, or a dropped connection.
      throw classifyThrownError(err);
    }

    if (!res.ok) {
      // Keep the status, a bounded machine code and the correlation id for
      // diagnostics; the customer only ever sees the category phrase.
      throw errorForResponse(res, await safeJson(res));
    }

    const data = await res.json();
    if (data.transcript) callbacks.onUserMessage?.(data.transcript);

    // execute -> observe -> verify -> confirm.
    //
    // Maya used to speak first and act afterwards, so she could announce that a
    // page was opened, sorted or shown before the browser had done any of it -
    // and still claim success when the action then failed. The actions run and
    // settle first; only their observed outcome decides what is said.
    const actions = Array.isArray(data.ui_actions) ? data.ui_actions : [];
    let actionResults = [];
    if (actions.length > 0) {
      actionResults = await executeActions(actions);
      callbacks.onActionResults?.(actionResults);
    }

    // The full rich answer is displayed; a concise `spoken_text` is what is read
    // aloud (much faster TTS). Both are gated on the same confirmation, so a
    // failed action still replaces speech with the recovery message.
    const displayText = confirmedResponseText(data.response_text || "", actions, actionResults);
    if (displayText) callbacks.onAssistantMessage?.(displayText, actions);
    callbacks.onStatusChange?.(STATUS.READY);

    const confirmed = displayText === (data.response_text || "");
    const speechText = confirmed ? (data.spoken_text || data.response_text || "") : displayText;
    // Audio is only released once the text it narrates has been confirmed, so the
    // customer never hears a claim the screen contradicts.
    if (data.audio_b64 && confirmed) {
      playAudioBase64(data.audio_b64, speechText);
    } else if (speechText) {
      speakTextFallback(speechText);
    }

    callbacks.onComplete?.(data);
    emitRuntimeEvent({
      event_type: "voice_turn_completed",
      stage: "http_response",
      status: "ok",
      request_id: responseRequestId(res),
      duration_ms: runtimeNow() - startedAt,
      metadata: { transport: "http", action_count: data.ui_actions?.length || 0 },
    });
  }
}

class VoiceWebSocketTransport {
  constructor() {
    this.ws = null;
    this.connected = false;
    this.connecting = null;
    this.failed = false;
    this.retries = 0;
    this.audioQueue = sharedAudioQueue;
    this.callbacks = null;
    this.turnText = "";
    this.receivedAudio = false;
    this.pendingAudioChunks = [];
  }

  async ensureConnected(conversationHistory = []) {
    if (!this.canUseWebSocket()) {
      return false;
    }
    if (this.isOpen()) {
      return true;
    }
    if (this.connecting) {
      return this.connecting;
    }

    this.connecting = this.openConnection(conversationHistory);
    return this.connecting;
  }

  canUseWebSocket() {
    return !this.failed && config.useWebSocket && "WebSocket" in window;
  }

  isOpen() {
    return this.connected && this.ws?.readyState === WebSocket.OPEN;
  }

  openConnection(conversationHistory = []) {
    return new Promise((resolve) => {
      const ws = new WebSocket(wsUrlFromApiBase(config.apiUrl, config.siteId));
      let settled = false;
      this.ws = ws;
      const settleFailure = (timer = null) => {
        if (settled) return;
        settled = true;
        this.markConnectionFailed(resolve, timer, ws);
      };
      const timer = window.setTimeout(() => {
        settleFailure();
      }, WS_CONNECT_TIMEOUT_MS);
      ws.onopen = () => {
        if (settled) return;
        settled = true;
        this.handleConnectionOpen(timer, conversationHistory, resolve);
      };
      ws.onmessage = (event) => {
        this.handleMessage(event).catch((err) => this.handleTransportError(err));
      };
      ws.onerror = () => {
        if (settled) {
          this.failActiveTurn(TRANSPORT_CATEGORY.NETWORK);
          return;
        }
        settleFailure(timer);
      };
      ws.onclose = () => {
        this.connected = false;
        if (settled) {
          this.failActiveTurn(TRANSPORT_CATEGORY.NETWORK);
          return;
        }
        settleFailure(timer);
      };
    });
  }

  markConnectionOpen() {
    this.connected = true;
    this.connecting = null;
    this.retries = 0;
  }

  handleConnectionOpen(timer, conversationHistory, resolve) {
    window.clearTimeout(timer);
    this.markConnectionOpen();
    this.sendConfig(conversationHistory);
    resolve(true);
  }

  markConnectionFailed(resolve, timer = null, ws = null) {
    if (timer) window.clearTimeout(timer);
    this.connected = false;
    this.connecting = null;
    this.retries += 1;
    if (this.retries >= MAX_WS_RETRIES) this.failed = true;
    if (ws && ws.readyState !== WebSocket.CLOSED) {
      ws.close();
    }
    resolve(false);
  }

  sendConfig(conversationHistory = []) {
    this.sendJson({
      type: WS_MESSAGES.CONFIG,
      history: conversationHistory || [],
      session_id: config.sessionId,
      page_context: currentPageContext(),
    });
  }

  sendJson(payload) {
    if (!this.ws || this.ws.readyState !== WebSocket.OPEN) return false;
    this.ws.send(JSON.stringify(payload));
    return true;
  }

  async sendAudio(blob, callbacks, conversationHistory = []) {
    const connected = await this.ensureConnected(conversationHistory);
    // Nothing was submitted, so an HTTP attempt cannot duplicate a turn.
    if (!connected) return false;

    this.callbacks = callbacks;
    this.turnText = "";
    this.receivedAudio = false;
    this.pendingAudioChunks = [];
    this.sendConfig(conversationHistory);
    const b64 = await blobToBase64(blob);

    const turnSettled = this.beginTurn();
    this.turnStartedAt = runtimeNow();
    emitRuntimeEvent({
      event_type: "voice_turn_started",
      stage: "websocket_send",
      status: "started",
      metadata: { transport: "websocket", audio_type: blob?.type || "unknown" },
    });
    const delivered =
      this.sendJson({ type: WS_MESSAGES.AUDIO_CHUNK, data: b64, mime_type: blob?.type || "" }) &&
      this.sendJson({ type: WS_MESSAGES.AUDIO_END, mime_type: blob?.type || "" });

    if (!delivered) {
      // The socket closed before any audio left the client, so falling back to
      // HTTP is still safe here.
      this.settleTurn();
      this.callbacks = null;
      return false;
    }

    // The audio is now with the server. The turn owns the rest of the lifecycle:
    // it ends only on done, error, close, or timeout - never merely on "sent".
    // Returning before that would clear the processing state early and could
    // produce a duplicate turn via the HTTP path.
    await turnSettled;
    return true;
  }

  beginTurn() {
    this.settleTurn();
    return new Promise((resolve) => {
      const timer = window.setTimeout(() => {
        this.failActiveTurn(TRANSPORT_CATEGORY.TIMEOUT);
      }, WS_TURN_TIMEOUT_MS);
      this.activeTurn = { resolve, timer };
    });
  }

  /** Release the waiting turn exactly once. */
  settleTurn() {
    const turn = this.activeTurn;
    this.activeTurn = null;
    if (!turn) return false;
    window.clearTimeout(turn.timer);
    turn.resolve();
    return true;
  }

  /** Terminal failure for an in-flight turn (close, timeout, socket error). */
  failActiveTurn(category) {
    if (!this.activeTurn) return;
    const callbacks = this.callbacks;
    this.callbacks = null;
    this.pendingAudioChunks = [];
    if (callbacks) {
      const error = new VoiceTransportError(category, { stage: "websocket" });
      callbacks.onStatusChange?.(STATUS.ERROR, error.customerMessage);
      callbacks.onComplete?.({ error: error.category });
      emitRuntimeEvent({
        event_type: "voice_turn_failed",
        stage: "websocket",
        severity: "error",
        status: "failed",
        message_code: error.code || error.category,
        duration_ms: runtimeNow() - (this.turnStartedAt || runtimeNow()),
        metadata: { transport: "websocket", category: error.category, http_status: error.status },
      });
    }
    this.settleTurn();
  }

  async handleMessage(event) {
    const callbacks = this.callbacks;
    if (!callbacks) return;

    const msg = this.parseMessage(event.data);
    if (!msg) {
      this.completeWithError(callbacks, "Invalid WebSocket message");
      return;
    }

    if (this.handleIncrementalMessage(msg, callbacks)) {
      return;
    }

    if (msg.type === WS_MESSAGES.DONE) {
      await this.handleDoneMessage(msg, callbacks);
      return;
    }

    if (msg.type === WS_MESSAGES.ERROR) {
      this.completeWithError(callbacks, msg.message || "WebSocket error");
    }
  }

  parseMessage(rawData) {
    try {
      const message = JSON.parse(rawData);
      return message && typeof message === "object" ? message : null;
    } catch (_err) {
      return null;
    }
  }

  handleIncrementalMessage(msg, callbacks) {
    if (msg.type === WS_MESSAGES.TRANSCRIPT) {
      callbacks.onUserMessage?.(msg.text || "");
      return true;
    }
    if (msg.type === WS_MESSAGES.TEXT_CHUNK) {
      this.turnText += msg.text || "";
      // Buffer action-dependent wording until the browser proves the requested
      // actions. Rendering a streamed success claim early recreates the same
      // truth problem as speaking it early.
      return true;
    }
    if (msg.type === WS_MESSAGES.AUDIO_CHUNK) {
      this.receivedAudio = Boolean(msg.audio_b64) || this.receivedAudio;
      if (msg.audio_b64) this.pendingAudioChunks.push(msg.audio_b64);
      return true;
    }
    return false;
  }

  async handleDoneMessage(msg, callbacks) {
    const finalText = msg.response_text || this.turnText;
    try {
      const actions = Array.isArray(msg.ui_actions) ? msg.ui_actions : [];
      let actionResults = [];
      if (actions.length > 0) {
        actionResults = await executeActions(actions);
        callbacks.onActionResults?.(actionResults);
      }

      const displayText = confirmedResponseText(finalText, actions, actionResults);
      callbacks.onAssistantMessage?.(displayText, actions, { streamed: true });
      callbacks.onStatusChange?.(STATUS.READY);
      const confirmed = displayText === finalText;
      const speechText = confirmed ? (msg.spoken_text || finalText) : displayText;
      if (this.receivedAudio && confirmed) {
        for (const chunk of this.pendingAudioChunks) this.audioQueue.push(chunk);
      } else if (speechText) {
        speakTextFallback(speechText);
      }
      callbacks.onComplete?.(msg);
      emitRuntimeEvent({
        event_type: "voice_turn_completed",
        stage: "websocket_done",
        status: "ok",
        duration_ms: runtimeNow() - (this.turnStartedAt || runtimeNow()),
        metadata: { transport: "websocket", action_count: msg.ui_actions?.length || 0 },
      });
    } catch (err) {
      this.handleTransportError(err);
    } finally {
      this.pendingAudioChunks = [];
      this.callbacks = null;
      this.settleTurn();
    }
  }

  completeWithError(callbacks, message) {
    callbacks.onStatusChange?.(STATUS.ERROR, userFacingError(message));
    callbacks.onComplete?.({ error: message });
    const error = classifyThrownError(message);
    emitRuntimeEvent({
      event_type: "voice_turn_failed",
      stage: "websocket_message",
      severity: "error",
      status: "failed",
      message_code: error.code || error.category,
      duration_ms: runtimeNow() - (this.turnStartedAt || runtimeNow()),
      metadata: { transport: "websocket", category: error.category, http_status: error.status },
    });
    this.callbacks = null;
    this.settleTurn();
  }

  handleTransportError(err) {
    console.error("AI Hub WebSocket transport failed", err);
    const callbacks = this.callbacks;
    if (callbacks) {
      this.completeWithError(callbacks, String(err));
    }
  }

  /**
   * Drop the socket and every scrap of turn state.
   *
   * A reset must leave nothing that could deliver the previous customer's answer
   * into the next customer's session, so buffered text and audio go too. Dropping
   * the callbacks first means the socket close below cannot fail the turn as a
   * network error - a user stop settles quietly.
   */
  reset(_reason = "reset") {
    this.callbacks = null;
    this.turnText = "";
    this.receivedAudio = false;
    this.pendingAudioChunks = [];
    this.settleTurn();
    try {
      this.ws?.close();
    } catch (_err) {
      // Closing an already-closed socket is not an error worth surfacing.
    }
    this.ws = null;
    this.connected = false;
    this.connecting = null;
    this.failed = false;
    this.retries = 0;
  }
}

const httpTransport = new HttpTransport();
const wsTransport = new VoiceWebSocketTransport();

export async function processAudio(blob, elements, callbacks, conversationHistory = []) {
  try {
    if (config.useWebSocket) {
      const sent = await wsTransport.sendAudio(blob, callbacks, conversationHistory);
      if (sent) return;
    }

    await httpTransport.sendAudio(blob, callbacks, conversationHistory);
  } catch (err) {
    const diagnostic = err instanceof VoiceTransportError ? err : classifyThrownError(err);
    // A turn the customer stopped is not a failure: report it as cancellation and
    // return to Ready, never to a connection/timeout error banner.
    if (isCancellation(diagnostic)) {
      emitRuntimeEvent({
        event_type: "voice_turn_cancelled",
        stage: diagnostic.stage || "transport",
        status: "cancelled",
        metadata: { transport: config.useWebSocket ? "websocket_or_http" : "http" },
      });
      callbacks.onStatusChange?.(STATUS.READY);
      callbacks.onComplete?.({ cancelled: true });
      return;
    }
    console.error(err);
    emitRuntimeEvent({
      event_type: "voice_turn_failed",
      stage: diagnostic.stage || "transport",
      severity: "error",
      status: "failed",
      request_id: diagnostic.requestId,
      message_code: diagnostic.code || diagnostic.category,
      metadata: {
        transport: config.useWebSocket ? "websocket_or_http" : "http",
        category: diagnostic.category,
        http_status: diagnostic.status,
      },
    });
    callbacks.onStatusChange?.(STATUS.ERROR, userFacingError(err));
    callbacks.onComplete?.({ error: String(err) });
  }
}

function responseRequestId(response) {
  return response?.headers?.get?.("x-request-id") || response?.headers?.get?.("x-correlation-id") || "";
}

function runtimeNow() {
  return typeof performance !== "undefined" ? performance.now() : Date.now();
}

function playAudioBase64(b64, fallbackText = "") {
  sharedAudioQueue.push(b64, fallbackText);
}

function audioFilenameForBlob(blob) {
  const type = String(blob?.type || "").toLowerCase();
  if (type.includes("mp4")) return "audio.mp4";
  if (type.includes("ogg")) return "audio.ogg";
  if (type.includes("wav")) return "audio.wav";
  return AUDIO.WEBM_FILENAME;
}

// Phrases that assert a browser action already happened. If the action did not
// actually succeed, saying these is simply untrue.
const ACTION_CLAIM_RE =
  /\b(opened|opening|taking you|took you|navigat|sorted|sorting|filtered|filtering|showing|shown|displayed|added to (?:your )?cart|here (?:it |they )?(?:is|are))\b/i;

const ACTION_RECOVERY_TEXT =
  "I could not complete that on the page. The site may not have responded - please try again, or do it manually.";

/**
 * Return the text that is actually true after the actions settled.
 *
 * When a turn made no claim about the page, or every action succeeded, the
 * original wording stands. When an action that the wording depends on failed,
 * the claim is replaced by a specific recovery message rather than a success
 * sentence the screen contradicts.
 */
export function confirmedResponseText(responseText, actions, actionResults) {
  const text = String(responseText || "");
  if (!text || !Array.isArray(actions) || actions.length === 0) return text;
  if (!ACTION_CLAIM_RE.test(text)) return text;

  const results = Array.isArray(actionResults) ? actionResults : [];
  if (results.length !== actions.length) return ACTION_RECOVERY_TEXT;

  // Both conditions are required. `status` is what the executor reported;
  // `verified` is what the page was observed to actually look like afterwards.
  // A sort the site ignored, or an overlay that rendered no rows, returns
  // succeeded but fails its postcondition - and must not be narrated as done.
  const everyConfirmed = results.every(
    (result) => result?.status === "succeeded" && result?.verified !== false,
  );
  return everyConfirmed ? text : ACTION_RECOVERY_TEXT;
}

/** Read a JSON body without letting a malformed payload mask the real status. */
async function safeJson(response) {
  try {
    return await response.json();
  } catch (_err) {
    return null;
  }
}

/**
 * Customer-facing text for a failed turn.
 *
 * Typed transport errors answer directly from their category. Anything else is
 * classified first, so a server fault can never be reported as a connectivity
 * fault (and vice versa). Server-supplied text is never rendered.
 */
function userFacingError(error) {
  if (error instanceof VoiceTransportError) return error.customerMessage;

  const text = String(error?.message || error || "").toLowerCase();
  if (text.includes("quota")) return "Quota reached";
  if (text.includes("transcription") || text.includes("speech")) return "Voice unavailable";
  return classifyThrownError(error).customerMessage;
}

function speakTextFallback(text) {
  if (!text) return false;
  return speakText(String(text).slice(0, 700));
}

function currentPageContext() {
  const runtime = window[RUNTIME_GLOBAL];
  const adapter = window[ADAPTER_GLOBAL];
  try {
    if (typeof runtime?.getContext === "function") return runtime.getContext();
    if (typeof adapter?.getContext === "function") return adapter.getContext();
  } catch (err) {
    console.warn("[AI Hub Widget] Page context collection failed:", err);
  }
  // The adapter bundle is optional, but what the customer can see is not. Without
  // it, a page question had no screen to be answered from and an action claim had
  // nothing to be checked against, so the base install reads the state itself.
  return localPageContext();
}

function localPageContext() {
  try {
    return {
      title: document.title || "",
      url: window.location.href,
      path: window.location.pathname,
      ...readPageState(),
    };
  } catch (err) {
    console.warn("[AI Hub Widget] Local page state collection failed:", err);
    return null;
  }
}
