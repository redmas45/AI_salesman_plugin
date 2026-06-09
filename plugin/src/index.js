import { injectStyles } from "./styles";
import { initWidget, addMessage } from "./widget";
import { setupRecorder } from "./recorder";
import { processAudio } from "./api";

// Initialize UI
injectStyles();
const elements = initWidget();

// Status Callback
function handleStatusChange(statusStr) {
  if (statusStr === "recording") {
    elements.btn.classList.add("recording");
    elements.chat.classList.add("visible");
    elements.status.innerText = "Listening...";
  } else if (statusStr === "processing") {
    elements.btn.classList.remove("recording");
    elements.status.innerText = "Processing...";
  } else if (statusStr === "ready") {
    elements.status.innerText = "Ready";
  } else if (statusStr === "error") {
    elements.status.innerText = "Error";
    elements.btn.classList.remove("recording");
  }
}

// Stop Callback
async function handleStop(blob) {
  await processAudio(blob, elements, {
    onMessage: (text, role) => addMessage(elements, text, role),
    onStatusChange: handleStatusChange
  });
}

// Setup Recorder
const recorder = setupRecorder(handleStop, handleStatusChange);

// Bind Button
elements.btn.addEventListener("click", () => {
  recorder.toggle();
});
