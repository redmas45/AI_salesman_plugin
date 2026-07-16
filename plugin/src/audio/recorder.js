import { AUDIO, STATUS } from "../core/constants";

const AUDIO_MIME_CANDIDATES = [
  "audio/webm;codecs=opus",
  "audio/webm",
  "audio/ogg;codecs=opus",
  "audio/ogg",
  "audio/mp4",
];
const RECORDING_TIMESLICE_MS = 250;
const MIN_AUDIO_BYTES = 128;

export function setupRecorder(onStop, onStatusChange) {
  let mediaRecorder = null;
  let activeStream = null;
  let audioChunks = [];
  let isRecording = false;
  let isStarting = false;
  let discardCurrentAudio = false;

  async function startRecording() {
    if (isStarting || isRecording) return;
    isStarting = true;
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      activeStream = stream;
      discardCurrentAudio = false;
      const mimeType = supportedAudioMimeType();
      mediaRecorder = new MediaRecorder(stream, mimeType ? { mimeType } : undefined);
      audioChunks = [];

      mediaRecorder.ondataavailable = (e) => {
        if (e.data.size > 0) audioChunks.push(e.data);
      };

      mediaRecorder.onstop = async () => {
        const audioBlob = new Blob(audioChunks, { type: mediaRecorder.mimeType || mimeType || AUDIO.WEBM_MIME_TYPE });
        stopActiveStream();
        if (discardCurrentAudio) {
          discardCurrentAudio = false;
          return;
        }
        if (audioBlob.size < MIN_AUDIO_BYTES) {
          console.warn("Microphone recording was empty or too short", { size: audioBlob.size });
          onStatusChange(STATUS.READY);
          return;
        }
        await onStop(audioBlob);
      };

      mediaRecorder.onerror = (event) => {
        console.error("Microphone recording failed", event.error || event);
        isRecording = false;
        isStarting = false;
        stopActiveStream();
        onStatusChange(STATUS.ERROR, "Recording failed");
      };

      mediaRecorder.start(RECORDING_TIMESLICE_MS);
      isRecording = true;
      onStatusChange(STATUS.RECORDING);
    } catch (err) {
      console.error("Microphone access denied", err);
      onStatusChange(STATUS.ERROR, "Mic unavailable");
    } finally {
      isStarting = false;
    }
  }

  function stopRecording({ discard = false } = {}) {
    discardCurrentAudio = discard;
    if (mediaRecorder && mediaRecorder.state !== "inactive") {
      try {
        mediaRecorder.requestData();
      } catch (_err) {
        // Some browsers throw if no data is ready yet; stop still flushes what exists.
      }
      mediaRecorder.stop();
      isRecording = false;
      if (!discard) onStatusChange(STATUS.PROCESSING);
      return;
    }
    isRecording = false;
    stopActiveStream();
    if (!discard) onStatusChange(STATUS.PROCESSING);
  }

  function toggle() {
    if (isStarting) return;
    if (isRecording) {
      stopRecording();
    } else {
      startRecording();
    }
  }

  function cancel() {
    stopRecording({ discard: true });
  }

  function stopActiveStream() {
    if (!activeStream) return;
    activeStream.getTracks().forEach((track) => track.stop());
    activeStream = null;
  }

  return { toggle, cancel };
}

function supportedAudioMimeType() {
  if (!("MediaRecorder" in window) || typeof MediaRecorder.isTypeSupported !== "function") {
    return "";
  }
  return AUDIO_MIME_CANDIDATES.find((mimeType) => MediaRecorder.isTypeSupported(mimeType)) || "";
}
