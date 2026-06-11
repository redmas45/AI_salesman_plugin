export function initWidget() {
  const container = document.createElement("div");
  container.id = "shopbot-widget";
  container.innerHTML = `
    <div id="shopbot-chat">
      <div id="shopbot-msgs" style="max-height: 300px; overflow-y: auto; display: flex; flex-direction: column; gap: 8px;"></div>
      <div id="shopbot-status">Ready</div>
    </div>
    <button id="shopbot-btn" aria-label="Voice Assistant">
      <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <path d="M12 2a3 3 0 0 0-3 3v7a3 3 0 0 0 6 0V5a3 3 0 0 0-3-3Z"/>
        <path d="M19 10v2a7 7 0 0 1-14 0v-2"/>
        <line x1="12" x2="12" y1="19" y2="22"/>
      </svg>
    </button>
  `;
  document.body.appendChild(container);

  return {
    btn: document.getElementById("shopbot-btn"),
    chat: document.getElementById("shopbot-chat"),
    msgs: document.getElementById("shopbot-msgs"),
    status: document.getElementById("shopbot-status")
  };
}

export function addMessage(elements, text, role) {
  elements.chat.classList.add("visible");
  const div = document.createElement("div");
  div.className = `shopbot-msg ${role}`;
  div.innerText = text;
  elements.msgs.appendChild(div);
  elements.msgs.scrollTop = elements.msgs.scrollHeight;
}
