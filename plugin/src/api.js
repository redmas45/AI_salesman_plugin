import { config } from "./config";
import { executeActions } from "./actions";

export async function processAudio(blob, elements, callbacks, conversationHistory = []) {
  const formData = new FormData();
  formData.append("audio", blob, "audio.webm");
  formData.append("site_id", config.siteId);
  if (conversationHistory && conversationHistory.length > 0) {
    formData.append("conversation_history", JSON.stringify(conversationHistory));
  }

  try {
    const res = await fetch(`${config.apiUrl}/v1/shop`, {
      method: "POST",
      body: formData,
    });
    
    if (!res.ok) throw new Error("API Error");

    const data = await res.json();
    
    if (data.transcript) callbacks.onMessage(data.transcript, "user");
    if (data.response_text) {
      // Pass ui_actions alongside response so history can track product IDs
      callbacks.onMessage(data.response_text, "ai", data.ui_actions || []);
    }
    callbacks.onStatusChange("ready");

    // Play audio
    if (data.audio_b64) {
      playAudioBase64(data.audio_b64);
    }

    // Execute UI Actions
    if (data.ui_actions && data.ui_actions.length > 0) {
      executeActions(data.ui_actions);
    }

  } catch (err) {
    console.error(err);
    callbacks.onStatusChange("error");
  }
}

function playAudioBase64(b64) {
  const audioSrc = "data:audio/wav;base64," + b64;
  const audio = new Audio(audioSrc);
  audio.play().catch(e => console.error("Audio playback failed", e));
}
