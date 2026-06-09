(function () {
  const WIDGET_DEFAULTS = {
    apiUrl: "__AI_PUBLIC_API_URL__",
    siteId: "__AI_DEFAULT_SITE_ID__",
    fallbackSiteId: "site_1",
  };

  const ALLOWED_ACTIONS = new Set([
    "SHOW_PRODUCTS",
    "FILTER_PRODUCTS",
    "NAVIGATE_TO",
    "SORT_PRODUCTS",
    "ADD_TO_CART",
    "REMOVE_FROM_CART",
    "SHOW_PRODUCT_DETAIL",
    "CLEAR_FILTERS",
    "CLEAR_CART",
    "CHECKOUT",
    "UPDATE_CART_QUANTITY",
  ]);

  const SITE_ID_RE = /^[a-z0-9_]+$/;
  const SAFE_SCHEME_RE = /^https?:$/i;

  function normalizeText(value) {
    return typeof value === "string" ? value.trim() : "";
  }

  function sanitizeSiteId(raw) {
    const cleaned = normalizeText(raw)
      .toLowerCase()
      .replace(/[^a-z0-9_-]/g, "_")
      .replace(/_+/g, "_")
      .replace(/^_+|_+$/g, "");

    if (!cleaned) {
      return WIDGET_DEFAULTS.fallbackSiteId;
    }
    if (!isNaN(Number(cleaned[0]))) {
      return `site_${cleaned}`;
    }
    if (SITE_ID_RE.test(cleaned)) {
      return cleaned;
    }
    return cleaned.slice(0, 80);
  }

  function resolveApiUrl(raw) {
    const value = normalizeText(raw);
    if (!value || value.includes("__AI_")) {
      return "";
    }

    try {
      const parsed = new URL(value, window.location.href);
      if (!SAFE_SCHEME_RE.test(parsed.protocol)) {
        return "";
      }
      return `${parsed.protocol}//${parsed.host}`;
    } catch (_err) {
      return "";
    }
  }

  function resolveWidgetConfig() {
    const currentScript = document.currentScript;
    const scriptUrl = currentScript && currentScript.src ? new URL(currentScript.src, window.location.href) : null;
    const siteIdSource =
      scriptUrl?.searchParams.get("site") ||
      scriptUrl?.searchParams.get("site_id") ||
      scriptUrl?.searchParams.get("shop") ||
      currentScript?.getAttribute("data-site-id") ||
      WIDGET_DEFAULTS.siteId ||
      WIDGET_DEFAULTS.fallbackSiteId;
    const apiUrlSource =
      currentScript?.getAttribute("data-api-url") ||
      scriptUrl?.searchParams.get("api") ||
      scriptUrl?.searchParams.get("api-url") ||
      WIDGET_DEFAULTS.apiUrl ||
      "";

    return {
      siteId: sanitizeSiteId(siteIdSource),
      apiUrl: resolveApiUrl(apiUrlSource) || window.location.origin,
    };
  }

  function isShopifyStorefront() {
    return Boolean(
      window.Shopify ||
        window.ShopifyAnalytics ||
        window.ShopifyBuy ||
        document.querySelector('meta[name="shopify-checkout-api-token"]')
    );
  }

  function safeInternalPath(raw) {
    try {
      const nextUrl = new URL(raw, window.location.href);
      if (nextUrl.origin !== window.location.origin) {
        return "/";
      }
      return `${nextUrl.pathname}${nextUrl.search}${nextUrl.hash}`;
    } catch (_err) {
      return "/";
    }
  }

  function waitForBody(callback, retries = 0) {
    if (document.body) {
      callback();
      return;
    }
    if (retries > 100) {
      console.error("ShopBot: document.body not found after waiting.");
      return;
    }
    setTimeout(() => waitForBody(callback, retries + 1), 50);
  }

  function injectStyles() {
    const style = document.createElement("style");
    style.textContent = `
      .voice-orb-wrapper {
        position: fixed;
        bottom: 20px;
        left: 50%;
        transform: translateX(-50%);
        z-index: 999999;
        display: flex;
        flex-direction: column-reverse;
        align-items: center;
        gap: 12px;
        font-family: system-ui, -apple-system, sans-serif;
      }
      
      .voice-orb {
        width: 65px;
        height: 65px;
        border-radius: 50%;
        border: 1px solid rgba(255, 255, 255, 0.2);
        display: flex;
        align-items: center;
        justify-content: center;
        cursor: pointer;
        position: relative;
        transition: all 0.5s cubic-bezier(0.16, 1, 0.3, 1);
        background: rgba(10, 10, 10, 0.85);
        backdrop-filter: blur(12px);
        -webkit-backdrop-filter: blur(12px);
        box-shadow:
          0 10px 30px rgba(0, 0, 0, 0.3),
          inset 0 0 15px rgba(255, 255, 255, 0.1);
        color: #fff;
      }
      
      .voice-orb:hover {
        transform: scale(1.05) translateY(-5px);
        box-shadow:
          0 15px 40px rgba(0, 0, 0, 0.4),
          0 0 20px rgba(59, 130, 246, 0.4),
          inset 0 0 15px rgba(255, 255, 255, 0.2);
        border: 1px solid rgba(255, 255, 255, 0.4);
      }
      
      .voice-orb:active {
        transform: scale(0.95);
      }
      
      .voice-orb::before {
        content: '';
        position: absolute;
        inset: -2px;
        border-radius: 50%;
        background: inherit;
        z-index: -1;
        filter: blur(10px);
        opacity: 0;
        transition: opacity 0.4s ease;
      }
      
      .voice-orb:hover::before {
        opacity: 0.5;
        background: conic-gradient(from 0deg, #3b82f6, #8b5cf6, #ec4899, #3b82f6);
        animation: rotateAura 3s linear infinite;
      }
      
      .voice-orb.listening {
        background: rgba(236, 72, 153, 0.9);
        border-color: rgba(255, 255, 255, 0.5);
        animation: orbBreathe 2s ease-in-out infinite;
      }
      
      .voice-orb.listening::before {
        opacity: 1;
        background: conic-gradient(from 0deg, #ec4899, #f43f5e, #ec4899);
        animation: rotateAura 2s linear infinite;
      }
      
      .voice-orb.processing {
        background: rgba(59, 130, 246, 0.9);
        border-color: rgba(255, 255, 255, 0.5);
        animation: orbPulse 1.5s ease-in-out infinite;
      }
      
      .voice-orb.processing::before {
        opacity: 1;
        background: conic-gradient(from 0deg, #3b82f6, #06b6d4, #3b82f6);
        animation: rotateAura 1.5s linear infinite;
      }
      
      @keyframes orbBreathe {
        0%, 100% {
          transform: scale(1);
          box-shadow: 0 10px 30px rgba(236, 72, 153, 0.4), inset 0 0 15px rgba(255, 255, 255, 0.3);
        }
        50% {
          transform: scale(1.1);
          box-shadow: 0 20px 50px rgba(236, 72, 153, 0.6), inset 0 0 20px rgba(255, 255, 255, 0.5);
        }
      }
      
      @keyframes orbPulse {
        0%, 100% {
          transform: scale(1);
          box-shadow: 0 10px 30px rgba(59, 130, 246, 0.4), inset 0 0 15px rgba(255, 255, 255, 0.3);
        }
        50% {
          transform: scale(1.08);
          box-shadow: 0 25px 60px rgba(59, 130, 246, 0.7), inset 0 0 25px rgba(255, 255, 255, 0.5);
        }
      }
      
      @keyframes rotateAura {
        0% { transform: rotate(0deg) scale(1.1); }
        100% { transform: rotate(360deg) scale(1.1); }
      }
      
      /* Chat bubble */
      #shopbot-chat {
        width: 320px;
        background: rgba(255, 255, 255, 0.95);
      }
      
      .voice-tooltip {
        background: rgba(15, 23, 42, 0.85);
        backdrop-filter: blur(16px);
        -webkit-backdrop-filter: blur(16px);
        padding: 1rem 2rem;
        border-radius: 24px;
        border: 1px solid rgba(255, 255, 255, 0.15);
        box-shadow: 
          0 20px 40px rgba(0, 0, 0, 0.2),
          0 0 0 1px rgba(255, 255, 255, 0.05) inset;
        max-width: 90vw;
        width: max-content;
        opacity: 0;
        transform: translateY(20px) scale(0.95);
        transition: all 0.4s cubic-bezier(0.16, 1, 0.3, 1);
        pointer-events: none;
        text-align: center;
        font-size: 1.15rem;
        font-weight: 500;
        color: #f8fafc;
        line-height: 1.5;
        letter-spacing: 0.3px;
      }
      
      .voice-tooltip.visible {
        opacity: 1;
        transform: translateY(0) scale(1);
      }
      
      .visualizer {
        display: flex;
        align-items: center;
        justify-content: center;
        gap: 5px;
        height: 24px;
      }
      
      .visualizer-bar {
        width: 4px;
        background-color: #38bdf8;
        border-radius: 4px;
        animation: waveBar 1.2s cubic-bezier(0.4, 0, 0.2, 1) infinite;
        box-shadow: 0 0 8px rgba(56, 189, 248, 0.6);
      }
      
      .visualizer-bar:nth-child(1) { animation-delay: 0.0s; }
      .visualizer-bar:nth-child(2) { animation-delay: 0.15s; }
      .visualizer-bar:nth-child(3) { animation-delay: 0.3s; }
      .visualizer-bar:nth-child(4) { animation-delay: 0.45s; }
      .visualizer-bar:nth-child(5) { animation-delay: 0.6s; }
      
      @keyframes waveBar {
        0%, 100% { height: 6px; opacity: 0.5; }
        50% { height: 24px; opacity: 1; background-color: #818cf8; }
      }
    `;
    document.head.appendChild(style);
  }

  function createWidget() {
    const widget = document.createElement("div");
    widget.id = "shopbot-widget";
    widget.className = "voice-orb-wrapper";
    widget.innerHTML = `
      <div id="shopbot-tooltip" class="voice-tooltip">
        <div id="shopbot-visualizer" class="visualizer" style="display: none; margin-bottom: 0.5rem;">
          <div class="visualizer-bar"></div><div class="visualizer-bar"></div>
          <div class="visualizer-bar"></div><div class="visualizer-bar"></div><div class="visualizer-bar"></div>
        </div>
        <span id="shopbot-message">Click to speak</span>
      </div>
      <button id="shopbot-btn" class="voice-orb">
        <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 2a3 3 0 0 0-3 3v7a3 3 0 0 0 6 0V5a3 3 0 0 0-3-3Z"></path><path d="M19 10v2a7 7 0 0 1-14 0v-2"></path><line x1="12" x2="12" y1="19" y2="22"></line></svg>
      </button>
    `;
    document.body.appendChild(widget);

    return {
      btn: document.getElementById("shopbot-btn"),
      tooltip: document.getElementById("shopbot-tooltip"),
      message: document.getElementById("shopbot-message"),
      visualizer: document.getElementById("shopbot-visualizer"),
    };
  }

  let streamInterval = null;
  let vanishTimeout = null;
  let ui = null;

  function updateTooltip(text, isProcessing = false) {
    ui.message.innerText = text;
    if (text || isProcessing) {
      ui.tooltip.classList.add("visible");
    } else {
      ui.tooltip.classList.remove("visible");
    }
    ui.visualizer.style.display = isProcessing ? "flex" : "none";
  }

  function setupAudioRecorder(processAudioCallback, setStatus) {
    let recorder = null;
    let audioChunks = [];
    let isRecording = false;

    function getMicErrorMessage(err) {
      if (!window.isSecureContext) {
        return "Mic needs HTTPS";
      }
      if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
        return "Mic not supported";
      }
      if (typeof MediaRecorder === "undefined") {
        return "Recording not supported";
      }
      if (err && err.name === "NotAllowedError") {
        return "Mic blocked. Allow permission";
      }
      if (err && err.name === "NotFoundError") {
        return "No microphone found";
      }
      if (err && err.name === "NotReadableError") {
        return "Mic is busy";
      }
      return "Mic error. Check permission";
    }

    async function toggle(e) {
      if (e) e.preventDefault();

      // If currently recording, STOP it
      if (isRecording) {
        if (recorder && recorder.state !== "inactive") {
          recorder.stop();
        }
        isRecording = false;
        if (recorder) setStatus("processing");
        return;
      }

      // Otherwise, START recording
      try {
        if (!window.isSecureContext) {
          throw new Error("Browser microphone access requires HTTPS.");
        }
        if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
          throw new Error("navigator.mediaDevices.getUserMedia is unavailable.");
        }
        if (typeof MediaRecorder === "undefined") {
          throw new Error("MediaRecorder is unavailable in this browser.");
        }

        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });

        recorder = new MediaRecorder(stream);
        audioChunks = [];

        recorder.ondataavailable = (e) => {
          if (e.data.size > 0) audioChunks.push(e.data);
        };

        recorder.onstop = async () => {
          const audioBlob = new Blob(audioChunks, { type: "audio/webm" });
          stream.getTracks().forEach((track) => track.stop());
          await processAudioCallback(audioBlob);
        };

        recorder.start();
        isRecording = true;
        setStatus("listening");
      } catch (err) {
        console.error("ShopBot microphone error", err && err.name, err && err.message, err);
        setStatus("error", getMicErrorMessage(err));
      }
    }

    return { toggle };
  }

  const config = resolveWidgetConfig();

  function executeUiActions(actions, transcript) {
    if (!Array.isArray(actions) || actions.length === 0) {
      if (transcript) {
        window.dispatchEvent(new CustomEvent("shopbot:setSearchText", { detail: transcript }));
      }
      return;
    }

    let queryToDisplay = transcript;
    const cleanedActions = actions.filter((action) => {
      if (!action || typeof action.action !== "string") {
        return false;
      }
      return ALLOWED_ACTIONS.has(normalizeText(action.action));
    });

    cleanedActions.forEach((action) => {
      const params = action.params || action.parameters || {};
      const searchQuery = normalizeText(params.search_query || params.query);
      if (searchQuery) {
        queryToDisplay = searchQuery;
      }
    });

    if (queryToDisplay) {
      window.dispatchEvent(new CustomEvent("shopbot:setSearchText", { detail: queryToDisplay }));
    }

    cleanedActions.forEach((action) => {
      const actionName = normalizeText(action.action);
      const params = action.params || action.parameters || {};

      console.log("ShopBot executing action:", actionName, params);

      if (window.ShopBotConfig) {
        if (window.ShopBotConfig.handleAction) {
          window.ShopBotConfig.handleAction(actionName, params);
          return;
        }
        if (actionName === "ADD_TO_CART" && window.ShopBotConfig.onAddToCart) {
          window.ShopBotConfig.onAddToCart(params.product_id, params.quantity);
          return;
        }
        if (actionName === "CLEAR_CART" && window.ShopBotConfig.onClearCart) {
          window.ShopBotConfig.onClearCart();
          return;
        }
        if (actionName === "FILTER_PRODUCTS" && window.ShopBotConfig.onFilter) {
          window.ShopBotConfig.onFilter(params);
          return;
        }
      }

      if (!isShopifyStorefront()) {
        window.dispatchEvent(new CustomEvent("shopbot:action", { detail: action }));
        return;
      }

      if (actionName === "CLEAR_CART") {
        fetch("/cart/clear.js", {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
        })
          .then((response) => response.json())
          .then((data) => {
            console.log("Successfully cleared cart:", data);
            window.location.href = "/cart";
          })
          .catch((error) => {
            console.error("Error clearing cart:", error);
            window.dispatchEvent(new CustomEvent("shopbot:action", { detail: action }));
          });
        return;
      }

      if (actionName === "ADD_TO_CART" && params.variant_id) {
        const variantId = Number(params.variant_id);
        const quantity = Number(params.quantity || 1);
        if (!Number.isFinite(variantId) || variantId <= 0 || !Number.isFinite(quantity) || quantity <= 0) {
          return;
        }

        fetch("/cart/add.js", {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            items: [{ id: variantId, quantity: Number(quantity) }],
          }),
        })
          .then((response) => response.json())
          .then((data) => {
            console.log("Successfully added to cart:", data);
            window.location.href = "/cart";
          })
          .catch((error) => {
            console.error("Error adding to cart:", error);
            window.dispatchEvent(new CustomEvent("shopbot:action", { detail: action }));
          });
        return;
      }

      if (actionName === "NAVIGATE_TO" && params.page) {
        window.location.href = safeInternalPath(params.page);
        return;
      }

      window.dispatchEvent(new CustomEvent("shopbot:action", { detail: action }));
    });
  }

  async function processAudio(audioBlob, callbacks) {
    const timeoutMs = 30000;
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), timeoutMs);

    const formData = new FormData();
    formData.append("audio", audioBlob, "audio.webm");
    formData.append("site_id", config.siteId || WIDGET_DEFAULTS.fallbackSiteId);

    try {
      const response = await fetch(`${config.apiUrl}/v1/shop`, {
        method: "POST",
        body: formData,
        mode: "cors",
        signal: controller.signal,
      });

      if (!response.ok) throw new Error("API Error");

      const result = await response.json();

      if (result.ui_actions && result.ui_actions.length > 0) {
        executeUiActions(result.ui_actions, result.transcript);
      } else if (result.transcript) {
        window.dispatchEvent(new CustomEvent("shopbot:setSearchText", { detail: result.transcript }));
      }

      callbacks.onResponse(result.response_text, result.audio_b64);
    } catch (err) {
      console.error(err);
      callbacks.onStatusChange("error");
    } finally {
      clearTimeout(timeoutId);
    }
  }

  let audioObj = null;

  function playAudio(base64Audio, onEnded) {
    if (audioObj) audioObj.pause();
    const src = "data:audio/wav;base64," + base64Audio;
    audioObj = new Audio(src);
    audioObj.play().catch((e) => console.error("Audio playback failed", e));
    audioObj.onended = onEnded;
  }

  // --- Initialization ---
  function init() {
    if (window.__shopbotLoaded) {
      return;
    }
    window.__shopbotLoaded = true;

    injectStyles();
    ui = createWidget();
    if (!ui) {
      console.error("ShopBot: failed to initialize UI");
      return;
    }

    function updateStatus(status, message) {
      ui.btn.className = "voice-orb"; // reset classes
      if (status === "listening") {
        ui.btn.classList.add("listening");
        updateTooltip("Listening...", false);
      } else if (status === "processing") {
        ui.btn.classList.add("processing");
        updateTooltip("AI thinking...", true);
      } else if (status === "ready") {
        // Don't reset tooltip instantly on ready, let vanishTimeout handle it if needed
      } else if (status === "error") {
        updateTooltip(message || "Mic error. Check permission", false);
        setTimeout(() => updateTooltip("Click to speak", false), 3000);
      }
    }

    const recorder = setupAudioRecorder(
      (blob) => processAudio(blob, {
        onStatusChange: updateStatus,
        onResponse: (text, audioB64) => {
          if (streamInterval) clearInterval(streamInterval);
          if (vanishTimeout) clearTimeout(vanishTimeout);

          updateStatus("ready");

          const words = (text || "Done.").split(' ');
          let wordIdx = 0;
          updateTooltip('', false);

          streamInterval = setInterval(() => {
            if (wordIdx < words.length) {
              updateTooltip(words.slice(0, wordIdx + 1).join(' '), false);
              wordIdx++;
            } else {
              clearInterval(streamInterval);
            }
          }, 200);

          if (audioB64) {
            playAudio(audioB64, () => {
              vanishTimeout = setTimeout(() => updateTooltip('', false), 500);
            });
          } else {
            const totalDuration = Math.max(3000, words.length * 200 + 1000);
            vanishTimeout = setTimeout(() => updateTooltip('', false), totalDuration);
          }
        }
      }),
      updateStatus
    );

    ui.btn.addEventListener("click", recorder.toggle);
    // Add touch support to prevent default context menus, while still triggering click
    ui.btn.addEventListener("touchstart", (e) => { e.preventDefault(); recorder.toggle(); }, { passive: false });
  }

  waitForBody(init);

})();
