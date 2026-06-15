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
    if (this.failed || !config.useWebSocket || !("WebSocket" in window)) {
      return false;
    }
    if (this.connected && this.ws?.readyState === WebSocket.OPEN) {
      return true;
    }
    if (this.connecting) {
      return this.connecting;
    }

    this.connecting = new Promise((resolve) => {
      const ws = new WebSocket(wsUrlFromApiBase(config.apiUrl, config.siteId));
      this.ws = ws;

      const fail = () => {
        this.connected = false;
        this.connecting = null;
        this.retries += 1;
        if (this.retries >= MAX_WS_RETRIES) this.failed = true;
        resolve(false);
      };

      const timer = window.setTimeout(fail, WS_CONNECT_TIMEOUT_MS);

      ws.onopen = () => {
        window.clearTimeout(timer);
        this.connected = true;
        this.connecting = null;
        this.retries = 0;
        this.sendJson({ type: WS_MESSAGES.CONFIG, history: conversationHistory || [], session_id: config.sessionId });
        resolve(true);
      };

      ws.onmessage = (event) => this.handleMessage(event);
      ws.onerror = fail;
      ws.onclose = () => {
        this.connected = false;
      };
    });

    return this.connecting;
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
    this.sendJson({ type: WS_MESSAGES.CONFIG, history: conversationHistory || [], session_id: config.sessionId });
    const b64 = await blobToBase64(blob);
    this.sendJson({ type: WS_MESSAGES.AUDIO_CHUNK, data: b64 });
    this.sendJson({ type: WS_MESSAGES.AUDIO_END });
    return true;
  }

  async handleMessage(event) {
    const callbacks = this.callbacks;
    if (!callbacks) return;

    let msg = {};
    try {
      msg = JSON.parse(event.data);
    } catch (_err) {
      callbacks.onComplete?.({ error: "Invalid WebSocket message" });
      return;
    }

    if (msg.type === WS_MESSAGES.TRANSCRIPT) {
      callbacks.onUserMessage?.(msg.text || "");
      return;
    }

    if (msg.type === WS_MESSAGES.TEXT_CHUNK) {
      this.turnText += msg.text || "";
      callbacks.onAssistantChunk?.(msg.text || "", this.turnText);
      return;
    }

    if (msg.type === WS_MESSAGES.AUDIO_CHUNK) {
      this.audioQueue.push(msg.audio_b64);
      return;
    }

    if (msg.type === WS_MESSAGES.DONE) {
      const finalText = msg.response_text || this.turnText;
      callbacks.onAssistantMessage?.(finalText, msg.ui_actions || [], { streamed: true });
      callbacks.onStatusChange?.(STATUS.READY);
      if (msg.ui_actions && msg.ui_actions.length > 0) {
        await executeActions(msg.ui_actions);
      }
      callbacks.onComplete?.(msg);
      this.callbacks = null;
      return;
    }

    if (msg.type === WS_MESSAGES.ERROR) {
      callbacks.onStatusChange?.(STATUS.ERROR);
      callbacks.onComplete?.({ error: msg.message || "WebSocket error" });
      this.callbacks = null;
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
