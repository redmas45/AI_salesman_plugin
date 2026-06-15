import { config } from "./config";
import { executeActions } from "./actions";
import {
  API_PATHS,
  AUDIO,
  HTTP_METHODS,
  STATUS,
  WS_CONNECT_TIMEOUT_MS,
  WS_MESSAGES,
} from "./constants";

const MAX_WS_RETRIES = 3;

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
    this.playing = false;
  }

  push(audioB64) {
    if (!audioB64) return;
    this.queue.push(audioB64);
    this.playNext();
  }

  playNext() {
    if (this.playing || this.queue.length === 0) return;
    this.playing = true;
    const audio = new Audio(AUDIO.DATA_WAV_PREFIX + this.queue.shift());
    audio.onended = () => {
      this.playing = false;
      this.playNext();
    };
    audio.onerror = () => {
      this.playing = false;
      this.playNext();
    };
    audio.play().catch((err) => {
      console.error("Audio playback failed", err);
      this.playing = false;
      this.playNext();
    });
  }
}

class HttpTransport {
  async sendAudio(blob, callbacks, conversationHistory = []) {
    const formData = new FormData();
    formData.append("audio", blob, AUDIO.WEBM_FILENAME);
    formData.append("site_id", config.siteId);
    formData.append("session_id", config.sessionId);
    if (conversationHistory && conversationHistory.length > 0) {
      formData.append("conversation_history", JSON.stringify(conversationHistory));
    }

    const res = await fetch(`${config.apiUrl}${API_PATHS.SHOP}`, {
      method: HTTP_METHODS.POST,
      body: formData,
    });

    if (!res.ok) throw new Error("ShopBot API request failed");

    const data = await res.json();
    if (data.transcript) callbacks.onUserMessage?.(data.transcript);
    if (data.response_text) callbacks.onAssistantMessage?.(data.response_text, data.ui_actions || []);
    callbacks.onStatusChange?.(STATUS.READY);

    if (data.audio_b64) {
      playAudioBase64(data.audio_b64);
    }

    if (data.ui_actions && data.ui_actions.length > 0) {
      await executeActions(data.ui_actions);
    }
    callbacks.onComplete?.(data);
  }
}

class ShopbotWebSocketTransport {
  constructor() {
    this.ws = null;
    this.connected = false;
    this.connecting = null;
    this.failed = false;
    this.retries = 0;
    this.audioQueue = new AudioQueue();
    this.callbacks = null;
    this.turnText = "";
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
    this.sendJson({ type: WS_MESSAGES.CONFIG, history: conversationHistory || [], session_id: config.sessionId });
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
    this.sendConfig(conversationHistory);
    const b64 = await blobToBase64(blob);
    this.sendJson({ type: WS_MESSAGES.AUDIO_CHUNK, data: b64 });
    this.sendJson({ type: WS_MESSAGES.AUDIO_END });
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
      this.audioQueue.push(msg.audio_b64);
      return true;
    }
    return false;
  }

  async handleDoneMessage(msg, callbacks) {
    const finalText = msg.response_text || this.turnText;
    callbacks.onAssistantMessage?.(finalText, msg.ui_actions || [], { streamed: true });
    callbacks.onStatusChange?.(STATUS.READY);
    try {
      if (msg.ui_actions && msg.ui_actions.length > 0) {
        await executeActions(msg.ui_actions);
      }
      callbacks.onComplete?.(msg);
    } catch (err) {
      this.handleTransportError(err);
    } finally {
      this.callbacks = null;
    }
  }

  completeWithError(callbacks, message) {
    callbacks.onStatusChange?.(STATUS.ERROR);
    callbacks.onComplete?.({ error: message });
    this.callbacks = null;
  }

  handleTransportError(err) {
    console.error("ShopBot WebSocket transport failed", err);
    const callbacks = this.callbacks;
    if (callbacks) {
      this.completeWithError(callbacks, String(err));
    }
  }
}

const httpTransport = new HttpTransport();
const wsTransport = new ShopbotWebSocketTransport();

export async function processAudio(blob, elements, callbacks, conversationHistory = []) {
  try {
    if (config.useWebSocket) {
      const sent = await wsTransport.sendAudio(blob, callbacks, conversationHistory);
      if (sent) return;
    }

    await httpTransport.sendAudio(blob, callbacks, conversationHistory);
  } catch (err) {
    console.error(err);
    callbacks.onStatusChange?.(STATUS.ERROR);
    callbacks.onComplete?.({ error: String(err) });
  }
}

function playAudioBase64(b64) {
  const audioSrc = AUDIO.DATA_WAV_PREFIX + b64;
  const audio = new Audio(audioSrc);
  audio.play().catch((e) => console.error("Audio playback failed", e));
}
