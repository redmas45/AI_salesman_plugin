export function initWidget() {
  const container = document.createElement("div");
  container.id = "shopbot-widget";
  container.innerHTML = `
    <div id="shopbot-chat">
      <div id="shopbot-msgs" style="max-height: 300px; overflow-y: auto; display: flex; flex-direction: column; gap: 8px;"></div>
      <div id="shopbot-status" style="font-size: 12px; color: #6b7280; text-align: center;">Ready</div>
    </div>
    <button id="shopbot-btn">🎤</button>
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
