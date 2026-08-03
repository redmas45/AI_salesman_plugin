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
let pendingVoiceTimer = null;
let speechGeneration = 0;

export function speakText(text) {
  if (!("speechSynthesis" in window) || !("SpeechSynthesisUtterance" in window)) return false;
  cancelPendingVoiceLoad();
  const generation = ++speechGeneration;
  pendingSpeechText = text;
  const speak = () => {
    if (generation !== speechGeneration || pendingSpeechText !== text) return false;
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
      cancelPendingVoiceLoad();
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
  pendingVoiceTimer = window.setTimeout(() => {
    pendingVoiceTimer = null;
    speak();
  }, VOICE_FALLBACK_DELAY_MS);
  return true;
}

export function replayPendingSpeech() {
  if (!pendingSpeechText) return;
  speakText(pendingSpeechText);
}

export function isSpeechActive() {
  try {
    return Boolean(pendingSpeechText) || Boolean(window.speechSynthesis?.speaking) || Boolean(window.speechSynthesis?.pending);
  } catch (_err) {
    return Boolean(pendingSpeechText);
  }
}

export function resetSpeech() {
  speechGeneration += 1;
  cancelPendingVoiceLoad();
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
  cancelPendingVoiceLoad();
  pendingSpeechText = "";
}

function cancelPendingVoiceLoad() {
  if (pendingVoiceTimer) window.clearTimeout(pendingVoiceTimer);
  pendingVoiceTimer = null;
  if (window.speechSynthesis) window.speechSynthesis.onvoiceschanged = null;
}
