import { config } from "../core/config";

const SPEECH_RATE = 1;
const SPEECH_PITCH = 1.08;
const VOICE_FALLBACK_DELAY_MS = 300;
const FEMALE_VOICE_HINTS = Object.freeze([
  "hannah",
  "sonia",
  "libby",
  "ava",
  "susan",
  "hazel",
  "heera",
  "salli",
  "joanna",
  "amy",
  "emma",
  "olivia",
  "natasha",
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

let pendingSpeechText = "";
let selectedSpeechVoiceName = "";

export function speakText(text) {
  if (!("speechSynthesis" in window) || !("SpeechSynthesisUtterance" in window)) return false;
  pendingSpeechText = text;
  const speak = () => {
    try {
      const utterance = new SpeechSynthesisUtterance(text);
      const voice = preferredSpeechVoice(window.speechSynthesis.getVoices());
      if (!voice) {
        pendingSpeechText = "";
        return false;
      }
      if (voice) utterance.voice = voice;
      utterance.rate = SPEECH_RATE;
      utterance.pitch = SPEECH_PITCH;
      utterance.onstart = clearPendingSpeech;
      utterance.onend = clearPendingSpeech;
      window.speechSynthesis.cancel();
      window.speechSynthesis.resume();
      window.speechSynthesis.speak(utterance);
      return true;
    } catch (_err) {
      // Browser speech synthesis is best-effort only.
      return false;
    }
  };

  if (window.speechSynthesis.getVoices().length > 0) {
    return speak();
  }

  window.speechSynthesis.onvoiceschanged = speak;
  window.setTimeout(speak, VOICE_FALLBACK_DELAY_MS);
  return true;
}

export function replayPendingSpeech() {
  if (!pendingSpeechText) return;
  speakText(pendingSpeechText);
}

export function resetSpeech() {
  pendingSpeechText = "";
  selectedSpeechVoiceName = "";
  try {
    window.speechSynthesis?.cancel();
  } catch (_err) {
    // Browser speech synthesis cancellation is best-effort only.
  }
}

function preferredSpeechVoice(voices) {
  if (!Array.isArray(voices) || voices.length === 0) return null;
  const selectedVoice = configuredVoice(voices) || preferenceVoice(voices);
  if (selectedVoice) selectedSpeechVoiceName = selectedVoice.name;
  return selectedVoice;
}

function configuredVoice(voices) {
  if (selectedSpeechVoiceName) {
    const selectedVoice = voices.find((voice) => voice.name === selectedSpeechVoiceName);
    if (selectedVoice) return selectedVoice;
  }
  const requestedName = String(config.speechVoiceName || "").toLowerCase();
  return requestedName
    ? voices.find((voice) => voice.name.toLowerCase() === requestedName) || null
    : null;
}

function preferenceVoice(voices) {
  if (config.speechVoicePreference.toLowerCase() !== "female") {
    return voices.find((voice) => voice.default) || voices[0];
  }
  return voices.find((voice) => FEMALE_VOICE_HINTS.some((hint) => voice.name.toLowerCase().includes(hint))) || null;
}

function clearPendingSpeech() {
  pendingSpeechText = "";
}
