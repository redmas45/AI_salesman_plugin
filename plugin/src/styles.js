export function injectStyles() {
  // Auto-detect client website's primary color
  let primaryColor = "#5d5fef"; // Premium vibrant indigo fallback
  const metaTheme = document.querySelector('meta[name="theme-color"]');
  if (metaTheme && metaTheme.content) {
    primaryColor = metaTheme.content;
  } else {
    const btn = document.querySelector('button[class*="primary"], .btn-primary, [data-primary]');
    if (btn) {
      const bg = window.getComputedStyle(btn).backgroundColor;
      if (bg && bg !== 'rgba(0, 0, 0, 0)' && bg !== 'transparent') {
        primaryColor = bg;
      }
    }
  }

  // Check if dark mode is preferred by client site or OS
  const isDark = window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches;
  const surfaceColor = isDark ? "rgba(24, 24, 27, 0.75)" : "rgba(255, 255, 255, 0.85)";
  const surfaceBorder = isDark ? "rgba(255, 255, 255, 0.1)" : "rgba(0, 0, 0, 0.08)";
  const textColor = isDark ? "#f3f4f6" : "#111827";
  const userMsgBg = isDark ? "rgba(255, 255, 255, 0.1)" : "rgba(0, 0, 0, 0.05)";
  const botMsgBg = isDark ? "rgba(0, 0, 0, 0.25)" : "#ffffff";

  const style = document.createElement("style");
  style.textContent = `
    :root {
      --shopbot-primary: ${primaryColor};
      --shopbot-surface: ${surfaceColor};
      --shopbot-border: ${surfaceBorder};
      --shopbot-text: ${textColor};
      --shopbot-user-bg: ${userMsgBg};
      --shopbot-bot-bg: ${botMsgBg};
    }

    #shopbot-widget {
      position: fixed;
      bottom: max(24px, env(safe-area-inset-bottom));
      left: 50%;
      right: auto;
      transform: translateX(-50%);
      z-index: 2147483647;
      font-family: Inter, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
      color: var(--shopbot-text);
      letter-spacing: -0.01em;
      width: auto;
      max-width: calc(100vw - 32px);
      -webkit-font-smoothing: antialiased;
    }

    #shopbot-btn {
      position: relative;
      width: 64px;
      height: 64px;
      border-radius: 50%;
      border: 1px solid rgba(255, 255, 255, 0.15);
      background: var(--shopbot-primary);
      box-shadow: 0 12px 32px -8px var(--shopbot-primary), 0 4px 12px rgba(0,0,0,0.15);
      color: #ffffff;
      display: flex;
      align-items: center;
      justify-content: center;
      cursor: pointer;
      transition: all 0.3s cubic-bezier(0.25, 1, 0.5, 1);
      outline: none;
    }
    
    #shopbot-btn svg {
      position: relative;
      z-index: 2;
      width: 28px;
      height: 28px;
      transition: transform 0.3s ease;
    }

    .shopbot-btn-ring {
      position: absolute;
      inset: -6px;
      border-radius: inherit;
      border: 2px solid var(--shopbot-primary);
      opacity: 0.4;
      pointer-events: none;
      transition: all 0.3s ease;
    }

    #shopbot-btn:hover {
      transform: translateY(-4px) scale(1.02);
      box-shadow: 0 16px 40px -8px var(--shopbot-primary), 0 8px 24px rgba(0,0,0,0.2);
    }
    
    #shopbot-btn:hover .shopbot-btn-ring {
      inset: -10px;
      opacity: 0.15;
    }

    #shopbot-btn.recording {
      background: #ef4444;
      box-shadow: 0 0 0 0 rgba(239, 68, 68, 0.7);
      animation: shopbotPulseRecord 1.5s infinite cubic-bezier(0.66, 0, 0, 1);
    }

    #shopbot-chat {
      position: absolute;
      bottom: 96px;
      left: 50%;
      transform: translateX(-50%) translateY(20px) scale(0.95);
      width: min(400px, calc(100vw - 32px));
      max-height: min(600px, calc(100vh - 140px));
      background: var(--shopbot-surface);
      backdrop-filter: blur(24px) saturate(180%);
      -webkit-backdrop-filter: blur(24px) saturate(180%);
      border: 1px solid var(--shopbot-border);
      border-radius: 20px;
      box-shadow: 0 24px 48px -12px rgba(0, 0, 0, 0.18), 0 0 0 1px rgba(255, 255, 255, 0.05) inset;
      padding: 20px;
      display: flex;
      flex-direction: column;
      gap: 16px;
      opacity: 0;
      pointer-events: none;
      visibility: hidden;
      transition: all 0.4s cubic-bezier(0.16, 1, 0.3, 1);
    }

    #shopbot-chat.visible {
      opacity: 1;
      pointer-events: all;
      visibility: visible;
      transform: translateX(-50%) translateY(0) scale(1);
    }

    .shopbot-header {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 16px;
      padding-bottom: 16px;
      border-bottom: 1px solid var(--shopbot-border);
    }

    .shopbot-header strong {
      display: block;
      font-size: 16px;
      font-weight: 600;
      line-height: 1.3;
    }

    .shopbot-kicker {
      display: block;
      margin-bottom: 4px;
      color: var(--shopbot-primary);
      font-size: 11px;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 0.05em;
    }

    .shopbot-live-dot {
      width: 8px;
      height: 8px;
      border-radius: 50%;
      background: #10b981;
      box-shadow: 0 0 0 4px rgba(16, 185, 129, 0.15);
      flex: 0 0 auto;
    }

    #shopbot-msgs {
      padding-right: 4px;
      scrollbar-width: thin;
      scrollbar-color: var(--shopbot-border) transparent;
      display: flex;
      flex-direction: column;
      gap: 12px;
    }
    
    #shopbot-msgs::-webkit-scrollbar {
      width: 4px;
    }
    #shopbot-msgs::-webkit-scrollbar-thumb {
      background-color: var(--shopbot-border);
      border-radius: 4px;
    }

    .shopbot-msg {
      max-width: 85%;
      padding: 12px 16px;
      border-radius: 16px;
      font-size: 14.5px;
      line-height: 1.5;
      overflow-wrap: anywhere;
      animation: shopbotSlideUpFade 0.3s cubic-bezier(0.16, 1, 0.3, 1) forwards;
      opacity: 0;
      transform: translateY(10px);
    }

    .shopbot-msg.user {
      background: var(--shopbot-user-bg);
      align-self: flex-end;
      border-bottom-right-radius: 4px;
    }

    .shopbot-msg.ai {
      background: var(--shopbot-bot-bg);
      align-self: flex-start;
      border-bottom-left-radius: 4px;
      border: 1px solid var(--shopbot-border);
      box-shadow: 0 4px 12px rgba(0, 0, 0, 0.03);
    }

    #shopbot-status {
      font-size: 12px;
      color: var(--shopbot-text);
      opacity: 0.6;
      text-align: center;
      min-height: 18px;
      margin-top: 4px;
      font-weight: 500;
      transition: all 0.3s ease;
    }

    #shopbot-status.listening {
      color: var(--shopbot-primary);
      opacity: 1;
      animation: shopbotTextPulse 1.5s infinite ease-in-out;
    }

    #shopbot-status.processing {
      color: var(--shopbot-text);
      opacity: 0.8;
      animation: shopbotTextPulse 1.5s infinite ease-in-out;
    }

    @keyframes shopbotSlideUpFade {
      from { opacity: 0; transform: translateY(8px) scale(0.98); }
      to { opacity: 1; transform: translateY(0) scale(1); }
    }

    @keyframes shopbotTextPulse {
      0%, 100% { opacity: 0.5; }
      50% { opacity: 1; }
    }

    @keyframes shopbotPulseRecord {
      to { box-shadow: 0 0 0 24px rgba(239, 68, 68, 0); }
    }

    @media (max-width: 520px) {
      #shopbot-widget {
        bottom: max(16px, env(safe-area-inset-bottom));
      }
      #shopbot-btn {
        width: 56px;
        height: 56px;
      }
      #shopbot-chat {
        bottom: 84px;
        width: calc(100vw - 32px);
      }
    }
  `;
  document.head.appendChild(style);
}
