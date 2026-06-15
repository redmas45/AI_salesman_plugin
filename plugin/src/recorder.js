import { AUDIO, STATUS } from "./constants";

export function setupRecorder(onStop, onStatusChange) {
  let mediaRecorder = null;
  let activeStream = null;
  let audioChunks = [];
  let isRecording = false;
  let discardCurrentAudio = false;

  async function startRecording() {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      activeStream = stream;
      discardCurrentAudio = false;
      mediaRecorder = new MediaRecorder(stream);
      audioChunks = [];

      mediaRecorder.ondataavailable = (e) => {
        if (e.data.size > 0) audioChunks.push(e.data);
      };

      mediaRecorder.onstop = async () => {
        const audioBlob = new Blob(audioChunks, { type: AUDIO.WEBM_MIME_TYPE });
        stopActiveStream();
        if (discardCurrentAudio) {
          discardCurrentAudio = false;
          return;
        }
        await onStop(audioBlob);
      };

      mediaRecorder.start();
      isRecording = true;
      onStatusChange(STATUS.RECORDING);
    } catch (err) {
      console.error("Microphone access denied", err);
      onStatusChange(STATUS.ERROR);
    }
  }

  function stopRecording({ discard = false } = {}) {
    discardCurrentAudio = discard;
    if (mediaRecorder && mediaRecorder.state !== "inactive") {
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
