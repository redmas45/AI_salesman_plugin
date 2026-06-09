export function setupRecorder(onStop, onStatusChange) {
  let mediaRecorder = null;
  let audioChunks = [];
  let isRecording = false;

  async function startRecording() {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      mediaRecorder = new MediaRecorder(stream);
      audioChunks = [];

      mediaRecorder.ondataavailable = (e) => {
        if (e.data.size > 0) audioChunks.push(e.data);
      };

      mediaRecorder.onstop = async () => {
        const audioBlob = new Blob(audioChunks, { type: "audio/webm" });
        stream.getTracks().forEach((track) => track.stop());
        await onStop(audioBlob);
      };

      mediaRecorder.start();
      isRecording = true;
      onStatusChange("recording");
    } catch (err) {
      console.error("Microphone access denied", err);
      onStatusChange("error");
    }
  }

  function stopRecording() {
    if (mediaRecorder && mediaRecorder.state !== "inactive") {
      mediaRecorder.stop();
    }
    isRecording = false;
    onStatusChange("processing");
  }

  function toggle() {
    if (isRecording) {
      stopRecording();
    } else {
      startRecording();
    }
  }

  return { toggle };
}
