// WCAG 2.1 minimum contrast for body text. Below this the widget's own status
// line becomes unreadable on a pale host accent.
const MIN_TEXT_CONTRAST_RATIO = 4.5;

function parseColor(value) {
  const text = String(value || "").trim();
  const hex = text.match(/^#([0-9a-f]{3}|[0-9a-f]{6})$/i);
  if (hex) {
    const digits = hex[1].length === 3 ? hex[1].replace(/./g, (c) => c + c) : hex[1];
    return [0, 2, 4].map((index) => parseInt(digits.slice(index, index + 2), 16));
  }
  const parts = text.match(/rgba?\(([^)]+)\)/i);
  if (!parts) return null;
  const numbers = parts[1].split(",").map((part) => parseFloat(part));
  return numbers.length >= 3 && numbers.slice(0, 3).every((n) => !Number.isNaN(n))
    ? numbers.slice(0, 3)
    : null;
}

function relativeLuminance(rgb) {
  const channels = rgb.map((value) => {
    const scaled = value / 255;
    return scaled <= 0.03928 ? scaled / 12.92 : ((scaled + 0.055) / 1.055) ** 2.4;
  });
  return 0.2126 * channels[0] + 0.7152 * channels[1] + 0.0722 * channels[2];
}

function contrastRatio(first, second) {
  const [lighter, darker] = [relativeLuminance(first), relativeLuminance(second)].sort((a, b) => b - a);
  return (lighter + 0.05) / (darker + 0.05);
}

/**
 * An accent safe to render text in, on the widget's own surface.
 *
 * The host's brand colour is used when it is legible. When it is not - a pale
 * theme colour on a pale panel - it is darkened (or lightened in dark mode)
 * until it passes, and falls back to the body text colour if it never does.
 */
export function readableAccent(primaryColor, textColor, isDark) {
  const surface = isDark ? [24, 24, 27] : [255, 255, 255];
  const accent = parseColor(primaryColor);
  if (!accent) return textColor;
  if (contrastRatio(accent, surface) >= MIN_TEXT_CONTRAST_RATIO) return primaryColor;
  for (let step = 1; step <= 10; step += 1) {
    const factor = step / 10;
    const adjusted = accent.map((channel) =>
      Math.round(isDark ? channel + (255 - channel) * factor : channel * (1 - factor)),
    );
    if (contrastRatio(adjusted, surface) >= MIN_TEXT_CONTRAST_RATIO) {
      return `rgb(${adjusted.join(", ")})`;
    }
  }
  return textColor;
}

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

  // The accent is borrowed from the host site, so it can be any colour at all.
  // A host publishing a near-white theme colour rendered "Listening..." as
  // white text on the widget's white panel. Text always uses an accent proven
  // readable against the surface it sits on.
  const accentTextColor = readableAccent(primaryColor, textColor, isDark);

  const style = document.createElement("style");
  style.textContent = `
    :root {
      --mayabot-primary: ${primaryColor};
      --mayabot-accent-text: ${accentTextColor};
      --mayabot-surface: ${surfaceColor};
      --mayabot-border: ${surfaceBorder};
      --mayabot-text: ${textColor};
      --mayabot-user-bg: ${userMsgBg};
      --mayabot-bot-bg: ${botMsgBg};
    }

    #mayabot-widget {
      position: fixed;
      bottom: max(24px, env(safe-area-inset-bottom));
      left: auto;
      right: 24px;
      transform: none;
      z-index: 2147483647;
      font-family: Inter, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
      color: var(--mayabot-text);
      letter-spacing: 0;
      width: auto;
      max-width: calc(100vw - 32px);
      -webkit-font-smoothing: antialiased;
      contain: style;
      isolation: isolate;
    }

    #mayabot-btn {
      position: relative;
      z-index: 1;
      /* Keep touch activation immediate and prevent browser zoom/highlight from
         competing with the orb's single-click voice control. */
      touch-action: manipulation;
      -webkit-tap-highlight-color: transparent;
      user-select: none;
      -webkit-user-select: none;
      width: 64px;
      height: 64px;
      border-radius: 50%;
      /* Idle: a red microphone on a white orb, no ripple. The listening and
         speaking states below change the treatment so each state is distinct. */
      border: 1px solid rgba(0, 0, 0, 0.08);
      background: #ffffff;
      box-shadow: 0 12px 32px -8px rgba(0,0,0,0.25), 0 4px 12px rgba(0,0,0,0.12);
      color: #ef4444;
      display: flex;
      align-items: center;
      justify-content: center;
      cursor: pointer;
      transition: transform 0.3s cubic-bezier(0.25, 1, 0.5, 1), box-shadow 0.3s ease, background-color 0.2s ease;
      outline: none;
    }
    
    #mayabot-btn svg {
      position: relative;
      z-index: 2;
      width: 28px;
      height: 28px;
      transition: transform 0.3s ease;
    }

    .mayabot-btn-ring {
      position: absolute;
      inset: -6px;
      border-radius: inherit;
      border: 2px solid var(--mayabot-primary);
      /* No ripple at idle. The ring only animates while listening. */
      opacity: 0;
      pointer-events: none;
      transition: inset 0.3s ease, opacity 0.3s ease;
    }

    #mayabot-btn:hover {
      transform: translateY(-4px) scale(1.02);
      box-shadow: 0 16px 40px -8px var(--mayabot-primary), 0 8px 24px rgba(0,0,0,0.2);
    }
    
    #mayabot-btn:hover .mayabot-btn-ring {
      inset: -10px;
      opacity: 0.15;
    }

    /* Listening: active colour treatment with a visible ripple. */
    #mayabot-btn.recording {
      background: var(--mayabot-primary);
      color: #ffffff;
      box-shadow: 0 0 0 6px rgba(37, 99, 235, 0.18), 0 8px 24px rgba(0,0,0,0.18);
    }

    #mayabot-btn.recording .mayabot-btn-ring {
      opacity: 0.5;
      animation: mayabotRipple 1.4s ease-out infinite;
    }

    /* Speaking: distinct from idle and listening, and clearly stoppable. */
    #mayabot-btn.speaking {
      background: var(--mayabot-primary);
      color: #ffffff;
      box-shadow: 0 0 0 4px rgba(37, 99, 235, 0.14), 0 8px 24px rgba(0,0,0,0.18);
    }

    @keyframes mayabotRipple {
      0% { inset: -6px; opacity: 0.5; }
      100% { inset: -16px; opacity: 0; }
    }

    /* Docked to the right edge for the full height of the window, so a long
       comparison reads as a column beside the page instead of a box floating
       over the middle of it. */
    #mayabot-chat {
      position: fixed;
      top: 0;
      bottom: 0;
      left: auto;
      right: 0;
      height: 100vh;
      height: 100dvh;
      transform: translateX(24px);
      /* A fifth of the window, bounded so it stays readable on a small screen
         and does not sprawl on a wide one. */
      width: 20vw;
      min-width: 260px;
      max-width: 380px;
      max-height: none;
      overflow: hidden;
      overscroll-behavior: contain;
      /* Room for the orb and its toggle, which stay clickable above the panel. */
      padding-bottom: 112px;
      border-radius: 20px 0 0 20px;
      background: var(--mayabot-surface);
      backdrop-filter: blur(24px) saturate(180%);
      -webkit-backdrop-filter: blur(24px) saturate(180%);
      border: 1px solid var(--mayabot-border);
      border-radius: 20px;
      box-shadow: 0 24px 48px -12px rgba(0, 0, 0, 0.18), 0 0 0 1px rgba(255, 255, 255, 0.05) inset;
      padding: 20px;
      display: flex;
      flex-direction: column;
      gap: 16px;
      opacity: 0;
      pointer-events: none;
      visibility: hidden;
      transition: opacity 0.25s ease, transform 0.3s cubic-bezier(0.16, 1, 0.3, 1), visibility 0s linear 0.3s;
    }

    #mayabot-chat.visible {
      opacity: 1;
      pointer-events: all;
      visibility: visible;
      transform: translateX(0);
      transition-delay: 0s;
    }

    .mayabot-header {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 16px;
      padding-bottom: 16px;
      border-bottom: 1px solid var(--mayabot-border);
    }

    .mayabot-header strong {
      display: block;
      font-size: 16px;
      font-weight: 600;
      line-height: 1.3;
    }

    .mayabot-kicker {
      display: block;
      margin-bottom: 4px;
      color: var(--mayabot-accent-text);
      font-size: 11px;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 0.05em;
    }

    .mayabot-live-dot {
      width: 8px;
      height: 8px;
      border-radius: 50%;
      background: #10b981;
      box-shadow: 0 0 0 4px rgba(16, 185, 129, 0.15);
      flex: 0 0 auto;
    }

    #mayabot-msgs {
      padding-right: 4px;
      scrollbar-width: thin;
      scrollbar-color: var(--mayabot-border) transparent;
      display: flex;
      flex-direction: column;
      gap: 12px;
    }
    
    #mayabot-msgs::-webkit-scrollbar {
      width: 4px;
    }
    #mayabot-msgs::-webkit-scrollbar-thumb {
      background-color: var(--mayabot-border);
      border-radius: 4px;
    }

    .mayabot-msg {
      max-width: 85%;
      padding: 12px 16px;
      border-radius: 16px;
      font-size: 14.5px;
      line-height: 1.5;
      overflow-wrap: anywhere;
      animation: mayabotSlideUpFade 0.3s cubic-bezier(0.16, 1, 0.3, 1) forwards;
      opacity: 0;
      transform: translateY(10px);
    }

    .mayabot-msg.user {
      background: var(--mayabot-user-bg);
      align-self: flex-end;
      border-bottom-right-radius: 4px;
    }

    .mayabot-msg.ai {
      background: var(--mayabot-bot-bg);
      align-self: flex-start;
      border-bottom-left-radius: 4px;
      border: 1px solid var(--mayabot-border);
      box-shadow: 0 4px 12px rgba(0, 0, 0, 0.03);
    }

    #mayabot-msgs {
      flex: 1 1 auto;
      min-height: 0;
      overflow-y: auto;
      overscroll-behavior: contain;
      display: flex;
      flex-direction: column;
      gap: 8px;
      padding-right: 4px;
    }

    /* A small control directly above the orb, matching the direction the panel
       opens: collapsed leaves only the microphone, expanded shows the
       conversation so far. Centred on the 64px orb, clear of it by 8px. */
    #mayabot-toggle {
      position: absolute;
      right: 18px;
      bottom: 72px;
      z-index: 2;
      width: 28px;
      height: 28px;
      padding: 0;
      border-radius: 50%;
      border: 1px solid var(--mayabot-border);
      background: #ffffff;
      color: var(--mayabot-text);
      display: flex;
      align-items: center;
      justify-content: center;
      cursor: pointer;
      box-shadow: 0 4px 12px rgba(0, 0, 0, 0.16);
      transition: transform 0.25s ease, background-color 0.2s ease;
    }

    #mayabot-toggle svg {
      width: 14px;
      height: 14px;
    }

    #mayabot-toggle:hover {
      background: var(--mayabot-bot-bg);
    }

    #mayabot-toggle:focus-visible {
      outline: 2px solid var(--mayabot-accent-text);
      outline-offset: 2px;
    }

    /* Points up to open the column, down to close it. */
    #mayabot-toggle[aria-expanded="true"] svg {
      transform: rotate(180deg);
    }

    #mayabot-status {
      font-size: 12px;
      color: var(--mayabot-text);
      opacity: 0.6;
      text-align: center;
      min-height: 18px;
      margin-top: 4px;
      font-weight: 500;
      transition: color 0.3s ease, opacity 0.3s ease;
    }

    #mayabot-status.listening {
      color: var(--mayabot-accent-text);
      opacity: 1;
      animation: mayabotTextPulse 1.5s infinite ease-in-out;
    }

    #mayabot-status.processing {
      color: var(--mayabot-text);
      opacity: 0.8;
      animation: mayabotTextPulse 1.5s infinite ease-in-out;
    }

    @keyframes mayabotSlideUpFade {
      from { opacity: 0; transform: translateY(8px) scale(0.98); }
      to { opacity: 1; transform: translateY(0) scale(1); }
    }

    @keyframes mayabotTextPulse {
      0%, 100% { opacity: 0.5; }
      50% { opacity: 1; }
    }

    @media (max-width: 520px) {
      #mayabot-widget {
        right: 16px;
        bottom: max(88px, calc(env(safe-area-inset-bottom) + 72px));
      }
      #mayabot-btn {
        width: 56px;
        height: 56px;
      }
      #mayabot-chat {
        width: 100vw;
        min-width: 0;
        max-width: none;
        border-radius: 0;
      }
    }

    @media (prefers-reduced-motion: reduce) {
      #mayabot-btn,
      #mayabot-btn svg,
      .mayabot-btn-ring,
      #mayabot-chat,
      .mayabot-msg,
      #mayabot-status {
        animation: none !important;
        transition: none !important;
      }
    }
  `;
  document.head.appendChild(style);
}
