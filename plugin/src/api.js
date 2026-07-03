import { config } from "./config";
import { executeActions } from "./actionExecutor";
import {
  API_PATHS,
  AUDIO,
  HTTP_METHODS,
  STATUS,
  WS_CONNECT_TIMEOUT_MS,
  WS_MESSAGES,
} from "./constants";

const MAX_WS_RETRIES = 3;
const FALLBACK_SPEECH_MAX_CHARS = 700;
const RUNTIME_GLOBAL = "AIHubAdapterRuntime";
const ADAPTER_GLOBAL = "AIHubAdapter";
let pendingFallbackSpeechText = "";

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
    audio.onended = () => {
      this.playing = false;
      this.playNext();
    };
    audio.onerror = () => {
      if (item.fallbackText) speakTextFallback(item.fallbackText);
      this.playing = false;
      this.playNext();
    };
    audio.play().catch((err) => {
      console.warn("Audio playback failed", err);
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
      replayFallbackSpeech();
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
}

const sharedAudioQueue = new AudioQueue();

class HttpTransport {
  async sendAudio(blob, callbacks, conversationHistory = []) {
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

    const res = await fetch(`${config.apiUrl}${API_PATHS.SHOP}`, {
      method: HTTP_METHODS.POST,
      body: formData,
    });

    if (!res.ok) throw new Error("AI Hub API request failed");

    const data = await res.json();
    if (data.transcript) callbacks.onUserMessage?.(data.transcript);
    if (data.response_text) callbacks.onAssistantMessage?.(data.response_text, data.ui_actions || []);
    callbacks.onStatusChange?.(STATUS.READY);

    if (data.audio_b64) {
      playAudioBase64(data.audio_b64, data.response_text || "");
    } else if (data.response_text) {
      speakTextFallback(data.response_text);
    }

    if (data.ui_actions && data.ui_actions.length > 0) {
      const actionResults = await executeActions(data.ui_actions);
      callbacks.onActionResults?.(actionResults);
    }
    callbacks.onComplete?.(data);
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
      ws.onerror = () => settleFailure(timer);
      ws.onclose = () => {
        this.connected = false;
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
    if (!connected) return false;

    this.callbacks = callbacks;
    this.turnText = "";
    this.receivedAudio = false;
    this.sendConfig(conversationHistory);
    const b64 = await blobToBase64(blob);
    this.sendJson({ type: WS_MESSAGES.AUDIO_CHUNK, data: b64, mime_type: blob?.type || "" });
    this.sendJson({ type: WS_MESSAGES.AUDIO_END, mime_type: blob?.type || "" });
    return true;
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
      callbacks.onAssistantChunk?.(msg.text || "", this.turnText);
      return true;
    }
    if (msg.type === WS_MESSAGES.AUDIO_CHUNK) {
      this.receivedAudio = Boolean(msg.audio_b64) || this.receivedAudio;
      this.audioQueue.push(msg.audio_b64);
      return true;
    }
    return false;
  }

  async handleDoneMessage(msg, callbacks) {
    const finalText = msg.response_text || this.turnText;
    callbacks.onAssistantMessage?.(finalText, msg.ui_actions || [], { streamed: true });
    callbacks.onStatusChange?.(STATUS.READY);
    if (!this.receivedAudio && finalText) {
      speakTextFallback(finalText);
    } else if (this.receivedAudio && finalText) {
      this.audioQueue.speakInsteadOfBlocked(finalText);
    }
    try {
      if (msg.ui_actions && msg.ui_actions.length > 0) {
        const actionResults = await executeActions(msg.ui_actions);
        callbacks.onActionResults?.(actionResults);
      }
      callbacks.onComplete?.(msg);
    } catch (err) {
      this.handleTransportError(err);
    } finally {
      this.callbacks = null;
    }
  }

  completeWithError(callbacks, message) {
    callbacks.onStatusChange?.(STATUS.ERROR, userFacingError(message));
    callbacks.onComplete?.({ error: message });
    this.callbacks = null;
  }

  handleTransportError(err) {
    console.error("AI Hub WebSocket transport failed", err);
    const callbacks = this.callbacks;
    if (callbacks) {
      this.completeWithError(callbacks, String(err));
    }
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
    console.error(err);
    callbacks.onStatusChange?.(STATUS.ERROR, userFacingError(err));
    callbacks.onComplete?.({ error: String(err) });
  }
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

function userFacingError(error) {
  const text = String(error?.message || error || "").toLowerCase();
  if (text.includes("quota")) return "Quota reached";
  if (text.includes("microphone") || text.includes("permission")) return "Mic unavailable";
  if (text.includes("network") || text.includes("fetch") || text.includes("api request")) return "Connection issue";
  return "Try again";
}

function speakTextFallback(text) {
  if (!text || !("speechSynthesis" in window) || !("SpeechSynthesisUtterance" in window)) return false;
  pendingFallbackSpeechText = String(text).slice(0, FALLBACK_SPEECH_MAX_CHARS);
  const utterance = new SpeechSynthesisUtterance(pendingFallbackSpeechText);
  utterance.rate = 1;
  utterance.pitch = 1;
  utterance.volume = 1;
  utterance.onstart = () => {
    pendingFallbackSpeechText = "";
  };
  utterance.onend = () => {
    pendingFallbackSpeechText = "";
  };
  try {
    window.speechSynthesis.cancel();
    window.speechSynthesis.resume();
    window.speechSynthesis.speak(utterance);
    return true;
  } catch (err) {
    console.warn("Fallback speech failed", err);
    return false;
  }
}

function replayFallbackSpeech() {
  if (!pendingFallbackSpeechText) return;
  speakTextFallback(pendingFallbackSpeechText);
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
  return null;
}
