import { config } from "../core/config";

export function initWidget() {
  const container = document.createElement("div");
  container.id = "mayabot-widget";
  container.innerHTML = `
    <div id="mayabot-chat">
      <div class="mayabot-header">
        <div>
          <span class="mayabot-kicker"></span>
          <strong class="mayabot-title"></strong>
        </div>
        <span class="mayabot-live-dot" aria-hidden="true"></span>
      </div>
      <div id="mayabot-msgs" style="max-height: 300px; overflow-y: auto; display: flex; flex-direction: column; gap: 8px;"></div>
      <div id="mayabot-status">Ready</div>
    </div>
    <button id="mayabot-btn" aria-label="Talk to Maya">
      <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <path d="M12 2a3 3 0 0 0-3 3v7a3 3 0 0 0 6 0V5a3 3 0 0 0-3-3Z"/>
        <path d="M19 10v2a7 7 0 0 1-14 0v-2"/>
        <line x1="12" x2="12" y1="19" y2="22"/>
      </svg>
      <span class="mayabot-btn-ring" aria-hidden="true"></span>
    </button>
  `;
  document.body.appendChild(container);
  container.querySelector(".mayabot-kicker").textContent = config.brandName;
  container.querySelector(".mayabot-title").textContent = config.assistantTitle;

  return {
    btn: document.getElementById("mayabot-btn"),
    chat: document.getElementById("mayabot-chat"),
    msgs: document.getElementById("mayabot-msgs"),
    status: document.getElementById("mayabot-status")
  };
}

export function addMessage(elements, text, role) {
  elements.chat.classList.add("visible");
  const div = document.createElement("div");
  div.className = `mayabot-msg ${role}`;
  div.innerText = text;
  elements.msgs.appendChild(div);
  elements.msgs.scrollTop = elements.msgs.scrollHeight;
  return div;
}

export function updateMessage(elements, node, text) {
  if (!node) return;
  node.innerText = text;
  elements.msgs.scrollTop = elements.msgs.scrollHeight;
}
