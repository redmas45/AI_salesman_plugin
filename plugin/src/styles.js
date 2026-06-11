export function injectStyles() {
  const style = document.createElement("style");
  style.textContent = `
    #shopbot-widget { position: fixed; bottom: 20px; left: 50%; transform: translateX(-50%); z-index: 999999; font-family: system-ui, -apple-system, sans-serif; }
    #shopbot-btn {
      width: 60px; height: 60px; border-radius: 50%;
      border: 1px solid rgba(255, 255, 255, 0.2);
      background: rgba(10, 10, 10, 0.85);
      backdrop-filter: blur(12px); -webkit-backdrop-filter: blur(12px);
      box-shadow: 0 10px 30px rgba(0, 0, 0, 0.3), inset 0 0 15px rgba(255, 255, 255, 0.1);
      color: white; display: flex; align-items: center; justify-content: center;
      cursor: pointer; transition: all 0.5s cubic-bezier(0.16, 1, 0.3, 1);
      outline: none;
    }
    #shopbot-btn:hover {
      transform: scale(1.05) translateY(-3px);
      box-shadow: 0 15px 40px rgba(0,0,0,0.4), 0 0 20px rgba(139,92,246,0.4), inset 0 0 15px rgba(255,255,255,0.2);
      border-color: rgba(255,255,255,0.4);
    }
    #shopbot-btn.recording {
      background: rgba(239, 68, 68, 0.85);
      border-color: rgba(255, 255, 255, 0.4);
      animation: pulse 1.5s infinite cubic-bezier(0.66, 0, 0, 1);
    }
    #shopbot-chat {
      position: absolute; bottom: 80px; left: 50%; transform: translateX(-50%); width: 320px;
      background: rgba(10, 10, 10, 0.85);
      backdrop-filter: blur(12px); -webkit-backdrop-filter: blur(12px);
      border: 1px solid rgba(255, 255, 255, 0.15);
      border-radius: 16px;
      box-shadow: 0 10px 30px rgba(0,0,0,0.3), inset 0 0 15px rgba(255,255,255,0.05);
      padding: 16px; display: none; flex-direction: column; gap: 12px;
      color: white;
    }
    #shopbot-chat.visible { display: flex; }
    .shopbot-msg { padding: 12px 16px; border-radius: 12px; font-size: 14px; line-height: 1.5; }
    .shopbot-msg.user { background: rgba(255, 255, 255, 0.1); color: white; align-self: flex-end; border-bottom-right-radius: 4px; border: 1px solid rgba(255, 255, 255, 0.1); }
    .shopbot-msg.ai { background: rgba(139, 92, 246, 0.8); color: white; align-self: flex-start; border-bottom-left-radius: 4px; border: 1px solid rgba(255, 255, 255, 0.2); }
    #shopbot-status {
      font-size: 14px;
      color: rgba(255, 255, 255, 0.7);
      text-align: center;
      margin-top: 6px;
      transition: all 0.3s ease;
      font-weight: 500;
    }
    #shopbot-status.listening {
      font-size: 18px;
      color: #f87171; /* Brighter red */
      font-weight: 600;
      text-shadow: 0 0 8px rgba(239, 68, 68, 0.5);
      animation: textPulse 1.5s infinite ease-in-out;
    }
    #shopbot-status.processing {
      font-size: 16px;
      color: #c084fc; /* Purple */
      font-weight: 600;
      animation: textPulse 1.5s infinite ease-in-out;
    }
    #shopbot-status.ready {
      color: #4ade80; /* Green */
    }
    #shopbot-status.error {
      color: #f87171; /* Red */
      font-weight: 600;
    }
    @keyframes textPulse {
      0%, 100% { opacity: 0.7; transform: scale(0.98); }
      50% { opacity: 1; transform: scale(1.02); }
    }
    @keyframes pulse {
      to { box-shadow: 0 0 0 20px rgba(239, 68, 68, 0); }
    }
  `;
  document.head.appendChild(style);
}
