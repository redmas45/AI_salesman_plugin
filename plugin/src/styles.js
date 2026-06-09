export function injectStyles() {
  const style = document.createElement("style");
  style.textContent = `
    #shopbot-widget { position: fixed; bottom: 20px; right: 20px; z-index: 999999; font-family: system-ui, -apple-system, sans-serif; }
    #shopbot-btn { width: 60px; height: 60px; border-radius: 30px; background: #4F46E5; color: white; border: none; box-shadow: 0 4px 12px rgba(0,0,0,0.15); cursor: pointer; display: flex; align-items: center; justify-content: center; font-size: 24px; transition: transform 0.2s; }
    #shopbot-btn:hover { transform: scale(1.05); }
    #shopbot-btn.recording { background: #ef4444; animation: pulse 1.5s infinite; }
    #shopbot-chat { position: absolute; bottom: 80px; right: 0; width: 300px; background: white; border-radius: 12px; box-shadow: 0 8px 24px rgba(0,0,0,0.15); padding: 16px; display: none; flex-direction: column; gap: 12px; border: 1px solid #e5e7eb; }
    #shopbot-chat.visible { display: flex; }
    .shopbot-msg { padding: 10px 14px; border-radius: 12px; font-size: 14px; line-height: 1.4; }
    .shopbot-msg.user { background: #f3f4f6; color: #1f2937; align-self: flex-end; border-bottom-right-radius: 2px; }
    .shopbot-msg.ai { background: #4F46E5; color: white; align-self: flex-start; border-bottom-left-radius: 2px; }
    @keyframes pulse { 0% { box-shadow: 0 0 0 0 rgba(239, 68, 68, 0.7); } 70% { box-shadow: 0 0 0 15px rgba(239, 68, 68, 0); } 100% { box-shadow: 0 0 0 0 rgba(239, 68, 68, 0); } }
  `;
  document.head.appendChild(style);
}
