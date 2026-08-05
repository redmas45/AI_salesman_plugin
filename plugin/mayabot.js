(()=>{function hn(){let t="#5d5fef",e=document.querySelector('meta[name="theme-color"]');if(e&&e.content)t=e.content;else{let f=document.querySelector('button[class*="primary"], .btn-primary, [data-primary]');if(f){let A=window.getComputedStyle(f).backgroundColor;A&&A!=="rgba(0, 0, 0, 0)"&&A!=="transparent"&&(t=A)}}let n=window.matchMedia&&window.matchMedia("(prefers-color-scheme: dark)").matches,r=n?"rgba(24, 24, 27, 0.75)":"rgba(255, 255, 255, 0.85)",o=n?"rgba(255, 255, 255, 0.1)":"rgba(0, 0, 0, 0.08)",i=n?"#f3f4f6":"#111827",a=n?"rgba(255, 255, 255, 0.1)":"rgba(0, 0, 0, 0.05)",s=n?"rgba(0, 0, 0, 0.25)":"#ffffff",u=document.createElement("style");u.textContent=`
    :root {
      --mayabot-primary: ${t};
      --mayabot-surface: ${r};
      --mayabot-border: ${o};
      --mayabot-text: ${i};
      --mayabot-user-bg: ${a};
      --mayabot-bot-bg: ${s};
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
      contain: layout style;
      isolation: isolate;
    }

    #mayabot-btn {
      position: relative;
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

    #mayabot-chat {
      position: absolute;
      bottom: 96px;
      left: auto;
      right: 0;
      transform: translateY(20px) scale(0.95);
      width: min(400px, calc(100vw - 32px));
      max-height: min(600px, calc(100vh - 140px));
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
      transform: translateY(0) scale(1);
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
      color: var(--mayabot-primary);
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
      color: var(--mayabot-primary);
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
        bottom: 84px;
        width: calc(100vw - 32px);
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
  `,document.head.appendChild(u)}var ue="site_1",Go="__AI_";var Ko="aihub:auto-site-id:",Qo=["data-aihub-scope","data-site-scope"],Xo=["data-site-id","data-aihub-site-id"];function S(t){return String(t||"").trim()}function yt(t){return S(t).replace(/\/+$/,"")}function gn(t,e,n,r=ue){return Jo(t,e,n)||Zo()||S(r)||ue}function Jo(t,e,n){for(let i of Xo){let a=S(t?.getAttribute(i));if(a)return a}let r=S(e?.searchParams.get("site"))||S(e?.searchParams.get("site_id"))||S(e?.searchParams.get("shop"));if(r)return r;let o=S(n);return o&&!o.startsWith(Go)?o:""}function Zo(){let t=ti(),e=`${Ko}${t}`,n=ci(e);if(n){let s=ai(n);return s!==n&&yn(e,s),s}let r=S(window.location.host||window.location.hostname||"site"),o=bn(),i=ii(`${r}${o?`_${o.replace(/\//g,"_")}`:""}`),a=Tn(`auto_${i}_${si(t)}`);return yn(e,a),a}function ti(){return`${window.location.origin}${bn()}`}function bn(){return ei()}function ei(){for(let e of Qo){let n=S(ni()?.getAttribute(e));if(n)return _n(n)}let t=document.querySelector("meta[name='aihub-site-scope']")?.getAttribute("content");return _n(t)}function ni(){return document.currentScript}function _n(t){let e=S(t);if(!e||e==="/")return"";try{let r=new URL(e,window.location.href);if(r.origin===window.location.origin){let[o]=ri(r.pathname);return o?`/${o}`:""}}catch{}let[n]=e.replace(/^\/+/,"").split("/");return n?`/${n}`:""}function ri(t=window.location.pathname){return S(t).split("/").map(e=>oi(e).trim()).filter(Boolean)}function oi(t){try{return decodeURIComponent(t)}catch{return String(t||"")}}function ii(t){return S(t).toLowerCase().replace(/[^a-z0-9]+/g,"_").replace(/^_+|_+$/g,"")||"site"}function Tn(t){return S(t).slice(0,80).replace(/_+$/g,"")||ue}function ai(t){let e=S(t);return e.startsWith("auto_")?Tn(e.toLowerCase().replace(/[^a-z0-9]+/g,"_").replace(/^_+|_+$/g,"")):e}function si(t){let e=2166136261,n=S(t);for(let r=0;r<n.length;r+=1)e^=n.charCodeAt(r),e=Math.imul(e,16777619);return(e>>>0).toString(36)}function ci(t){try{return S(window.localStorage.getItem(t))}catch{return""}}function yn(t,e){try{window.localStorage.setItem(t,e)}catch{}}var Y=document.currentScript,An="__AI_PUBLIC_API_URL__",ui="__AI_DEFAULT_SITE_ID__",En="mayabot:session:",li="Maya",di="AI Salesperson",pi="female";function K(t){return String(t||"").trim()}function fi(){let t=K(Y?.getAttribute("src"));if(!t)return null;try{return new URL(t,window.location.href)}catch{return null}}function mi(t){let e=K(Y?.getAttribute("data-api-url"));if(e)return yt(e);if(!An.startsWith("__AI_"))return yt(An);if(t?.origin){let n=t.pathname.replace(/\/mayabot(?:-widget)?\.js$/,"");return yt(`${t.origin}${n}`)}return yt(window.location.origin)}function hi(t){let e=`${En}${t}`;try{let n=window.sessionStorage.getItem(e);if(n)return n;let r=de(t);return window.sessionStorage.setItem(e,r),r}catch{return de(t)}}function _i(t){let e=de(t);try{window.sessionStorage.setItem(`${En}${t}`,e)}catch{}return e}function de(t){let e=window.crypto?.randomUUID?.()||`${Date.now()}-${Math.random().toString(16).slice(2)}`;return`${t}-${e}`.slice(0,120)}var Sn=fi(),le=gn(Y,Sn,ui),d={siteId:le,get sessionId(){return hi(le)},rotateSessionId(){return _i(le)},apiUrl:mi(Sn),useWebSocket:K(Y?.getAttribute("data-use-websocket")).toLowerCase()==="true",autoGreet:K(Y?.getAttribute("data-auto-greet")).toLowerCase()!=="false",brandName:K(Y?.getAttribute("data-brand"))||li,assistantTitle:K(Y?.getAttribute("data-assistant-title"))||di,speechVoiceName:K(Y?.getAttribute("data-speech-voice")),speechVoicePreference:K(Y?.getAttribute("data-speech-voice-preference"))||pi};function wn(){let t=document.createElement("div");return t.id="mayabot-widget",t.innerHTML=`
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
  `,document.body.appendChild(t),t.querySelector(".mayabot-kicker").textContent=d.brandName,t.querySelector(".mayabot-title").textContent=d.assistantTitle,{btn:document.getElementById("mayabot-btn"),chat:document.getElementById("mayabot-chat"),msgs:document.getElementById("mayabot-msgs"),status:document.getElementById("mayabot-status")}}function gt(t,e,n){t.chat.classList.add("visible");let r=document.createElement("div");return r.className=`mayabot-msg ${n}`,r.innerText=e,t.msgs.appendChild(r),t.msgs.scrollTop=t.msgs.scrollHeight,r}function pe(t,e,n){e&&(e.innerText=n,t.msgs.scrollTop=t.msgs.scrollHeight)}var c=Object.freeze({ADD_TO_CART:"ADD_TO_CART",BOOK_APPOINTMENT_REQUEST:"BOOK_APPOINTMENT_REQUEST",BUILD_ITINERARY:"BUILD_ITINERARY",BUILD_LEARNING_PATH:"BUILD_LEARNING_PATH",CAPTURE_LEAD:"CAPTURE_LEAD",CAPTURE_PATIENT_LEAD:"CAPTURE_PATIENT_LEAD",CHECKOUT:"CHECKOUT",CHECKOUT_HANDOFF:"CHECKOUT_HANDOFF",CHECK_APPOINTMENT_AVAILABILITY:"CHECK_APPOINTMENT_AVAILABILITY",CHECK_AVAILABILITY:"CHECK_AVAILABILITY",CHECK_DELIVERY_AVAILABILITY:"CHECK_DELIVERY_AVAILABILITY",CHECK_ELIGIBILITY_SOFT:"CHECK_ELIGIBILITY_SOFT",CHECK_PREREQUISITES:"CHECK_PREREQUISITES",CLEAR_CART:"CLEAR_CART",CLEAR_FILTERS:"CLEAR_FILTERS",CLEAR_HISTORY:"CLEAR_HISTORY",COMPARE_ENTITIES:"COMPARE_ENTITIES",CONTACT_AGENT:"CONTACT_AGENT",FILTER_ENTITIES:"FILTER_ENTITIES",FILTER_PRODUCTS:"FILTER_PRODUCTS",HANDOFF_TO_ADVISOR:"HANDOFF_TO_ADVISOR",HANDOFF_TO_AGENT:"HANDOFF_TO_AGENT",HANDOFF_TO_CLINIC:"HANDOFF_TO_CLINIC",HANDOFF_TO_HUMAN:"HANDOFF_TO_HUMAN",HANDOFF_TO_LAWYER:"HANDOFF_TO_LAWYER",HANDOFF_TO_LICENSED_AGENT:"HANDOFF_TO_LICENSED_AGENT",HANDOFF_TO_RECRUITER:"HANDOFF_TO_RECRUITER",JOIN_WAITLIST:"JOIN_WAITLIST",MATCH_JOBS:"MATCH_JOBS",NAVIGATE_TO:"NAVIGATE_TO",OPEN_CLAIM_FLOW:"OPEN_CLAIM_FLOW",OPEN_CONTACT:"OPEN_CONTACT",OPEN_DISCLOSURE:"OPEN_DISCLOSURE",OPEN_ENTITY_DETAIL:"OPEN_ENTITY_DETAIL",OPEN_LOCATION:"OPEN_LOCATION",OPEN_MAP:"OPEN_MAP",OPEN_POLICY:"OPEN_POLICY",OPEN_PROJECTS:"OPEN_PROJECTS",OPEN_RENEWAL_FLOW:"OPEN_RENEWAL_FLOW",OPEN_SERVICES:"OPEN_SERVICES",OPEN_SYLLABUS:"OPEN_SYLLABUS",OPEN_TELECONSULT:"OPEN_TELECONSULT",REMOVE_FROM_CART:"REMOVE_FROM_CART",REQUEST_APPOINTMENT:"REQUEST_APPOINTMENT",REQUEST_CALLBACK:"REQUEST_CALLBACK",REQUEST_CONSULTATION:"REQUEST_CONSULTATION",REQUEST_COUNSELOR_CALLBACK:"REQUEST_COUNSELOR_CALLBACK",REQUEST_ESTIMATE:"REQUEST_ESTIMATE",REQUEST_SITE_VISIT:"REQUEST_SITE_VISIT",REQUEST_TEST_DRIVE:"REQUEST_TEST_DRIVE",REQUEST_VIEWING:"REQUEST_VIEWING",RUN_AFFORDABILITY_CALCULATOR:"RUN_AFFORDABILITY_CALCULATOR",RUN_CALCULATOR:"RUN_CALCULATOR",RUN_DOM_SEQUENCE:"RUN_DOM_SEQUENCE",SAVE_SEARCH:"SAVE_SEARCH",SCHEDULE_ORDER:"SCHEDULE_ORDER",SEARCH_AVAILABILITY:"SEARCH_AVAILABILITY",SET_LOCATION:"SET_LOCATION",SHOW_COMPARISON:"SHOW_COMPARISON",SHOW_EMERGENCY_NOTICE:"SHOW_EMERGENCY_NOTICE",SHOW_ENTITIES:"SHOW_ENTITIES",SHOW_PRODUCT_DETAIL:"SHOW_PRODUCT_DETAIL",SHOW_PRODUCTS:"SHOW_PRODUCTS",SORT_ENTITIES:"SORT_ENTITIES",SORT_PRODUCTS:"SORT_PRODUCTS",START_APPLICATION:"START_APPLICATION",START_BOOKING:"START_BOOKING",START_ENROLLMENT:"START_ENROLLMENT",START_INTAKE:"START_INTAKE",START_QUOTE:"START_QUOTE",START_TICKET_PURCHASE:"START_TICKET_PURCHASE",UPDATE_CART_QUANTITY:"UPDATE_CART_QUANTITY",UPDATE_PREFERENCES:"UPDATE_PREFERENCES"}),p=Object.freeze({ENTITY_ID:"entity_id",ENTITY_IDS:"entity_ids",MESSAGE:"message",PAGE:"page",PRODUCT_ID:"product_id",PRODUCT_IDS:"product_ids",PRODUCT_NAME:"product_name",QUANTITY:"quantity",REASON:"reason",SEARCH_QUERY:"search_query",URL:"url"}),Pu=Object.freeze({BLOCKED:"blocked",EXECUTING:"executing",FAILED:"failed",REQUESTED:"requested",SKIPPED:"skipped",SUCCEEDED:"succeeded",UNKNOWN:"unknown"}),U=Object.freeze({KNOWLEDGE_BY_IDS:"/v1/knowledge/by-ids",PRODUCTS_BY_IDS:"/v1/products/by-ids",SHOP:"/v1/shop",SHOP_WS:"/v1/ws/shop",WIDGET_STATUS:"/v1/widget/status"}),k=Object.freeze({AUDIO_CHUNK:"audio_chunk",AUDIO_END:"audio_end",CONFIG:"config",DONE:"done",ERROR:"error",TEXT_CHUNK:"text_chunk",TRANSCRIPT:"transcript"});var In=new Set(["cart","/cart"]),$="Recommended products",Q="Relevant options",bt=Object.freeze({DATA_WAV_PREFIX:"data:audio/wav;base64,",WEBM_FILENAME:"audio.webm",WEBM_MIME_TYPE:"audio/webm"}),On=Object.freeze({POST:"POST"}),y=Object.freeze({ERROR:"error",PROCESSING:"processing",READY:"ready",RECORDING:"recording"});var Rn=2400,Cn=900,xn=4200,fe=1,lt=180,Nn=3e3,Tt=Object.freeze({MAYABOT_ACTION:"mayabot:action"}),vn=2500,Ln=45e3;var yi=["audio/webm;codecs=opus","audio/webm","audio/ogg;codecs=opus","audio/ogg","audio/mp4"],gi=250,bi=128;function Pn(t,e){let n=null,r=null,o=[],i=!1,a=!1,s=!1;async function u(){if(!(a||i)){a=!0;try{let b=await navigator.mediaDevices.getUserMedia({audio:!0});r=b,s=!1;let C=Ti();n=new MediaRecorder(b,C?{mimeType:C}:void 0),o=[],n.ondataavailable=I=>{I.data.size>0&&o.push(I.data)},n.onstop=async()=>{let I=new Blob(o,{type:n.mimeType||C||bt.WEBM_MIME_TYPE});if(R(),s){s=!1;return}if(I.size<bi){console.warn("Microphone recording was empty or too short",{size:I.size}),e(y.READY);return}await t(I)},n.onerror=I=>{console.error("Microphone recording failed",I.error||I),i=!1,a=!1,R(),e(y.ERROR,"Recording failed")},n.start(gi),i=!0,e(y.RECORDING)}catch(b){console.error("Microphone access denied",b),e(y.ERROR,"Mic unavailable")}finally{a=!1}}}function f({discard:b=!1}={}){if(s=b,n&&n.state!=="inactive"){try{n.requestData()}catch{}n.stop(),i=!1,b||e(y.PROCESSING);return}i=!1,R(),b||e(y.PROCESSING)}function A(){a||(i?f():u())}function v(){f({discard:!0})}function R(){r&&(r.getTracks().forEach(b=>b.stop()),r=null)}return{toggle:A,cancel:v}}function Ti(){return!("MediaRecorder"in window)||typeof MediaRecorder.isTypeSupported!="function"?"":yi.find(t=>MediaRecorder.isTypeSupported(t))||""}var Dn="shopify",Un="woocommerce",Ai="custom";function Ut(t){let e=String(t||"").trim();return/^\d+$/.test(e)?e:""}function kt(t,e=1){let n=Number(t?.[p.QUANTITY]);return Number.isFinite(n)&&n>0?Math.floor(n):e}async function nt(t,e){return(await fetch(new URL(t,window.location.origin),{method:"POST",headers:{Accept:"application/json","Content-Type":"application/json"},body:JSON.stringify(e),credentials:"same-origin"})).ok}function Ei(){return Si()?Dn:wi()?Un:Ai}async function kn(t){let e=Ei();return e===Dn?Ii(t):e===Un?Oi(t):!1}function Si(){return!!(window.Shopify||document.querySelector('meta[name="shopify-checkout-api-token"]')||document.querySelector('script[src*="cdn.shopify.com"]'))}function wi(){return!!(document.body?.classList?.contains("woocommerce")||window.wc_add_to_cart_params||document.querySelector('link[href*="woocommerce"], script[src*="woocommerce"]'))}async function Ii(t){let e=t.parameters||{};if(t.action===c.ADD_TO_CART){let n=Ut(e.variant_id||e.cart_id||e[p.PRODUCT_ID]);return n?nt("/cart/add.js",{items:[{id:n,quantity:kt(e)}]}):!1}if(t.action===c.REMOVE_FROM_CART){let n=Ut(e.cart_id||e.variant_id||e[p.PRODUCT_ID]);return n?nt("/cart/change.js",{id:n,quantity:0}):!1}if(t.action===c.UPDATE_CART_QUANTITY){let n=Ut(e.cart_id||e.variant_id||e[p.PRODUCT_ID]);return n?nt("/cart/change.js",{id:n,quantity:kt(e,0)}):!1}return t.action===c.CLEAR_CART?nt("/cart/clear.js",{}):t.action===c.CHECKOUT?Mt("/checkout"):Mn(t)?Mt("/cart"):!1}async function Oi(t){let e=t.parameters||{};if(t.action===c.ADD_TO_CART){let n=Ut(e.variant_id||e.cart_id||e[p.PRODUCT_ID]);return n?nt("/wp-json/wc/store/cart/add-item",{id:Number(n),quantity:kt(e)}):!1}if(t.action===c.REMOVE_FROM_CART){let n=String(e.cart_key||e.key||"").trim();return n?nt("/wp-json/wc/store/cart/remove-item",{key:n}):!1}if(t.action===c.UPDATE_CART_QUANTITY){let n=String(e.cart_key||e.key||"").trim();return n?nt("/wp-json/wc/store/cart/update-item",{key:n,quantity:kt(e,0)}):!1}return t.action===c.CHECKOUT?Mt("/checkout"):Mn(t)?Mt("/cart"):!1}function Mn(t){return t.action===c.NAVIGATE_TO&&In.has(t.parameters?.[p.PAGE])}function Mt(t){return window.location.href=t,!0}var Ri="/v1/widget/action-event";function P(t){return String(t||"").trim()}function Ci(t,e){return new URL(t,e).toString()}function xi(t){return!t||typeof t!="object"?[]:Object.keys(t).map(e=>P(e)).filter(Boolean).slice(0,20)}function Ni(t){if(!t||typeof t!="object")return{};let e={};for(let[n,r]of Object.entries(t).slice(0,20)){let o=P(n).slice(0,80);o&&(typeof r=="boolean"||r===null?e[o]=r:typeof r=="number"?e[o]=Number.isFinite(r)?r:0:e[o]=P(r).slice(0,240))}return e}async function Ft(t,e,n,r){if(!t||!e||!n?.action)return;let o=JSON.stringify({site_id:e,origin:window.location.origin,url:window.location.href,occurred_at:new Date().toISOString(),request_id:P(n.request_id||n.action_request_id),turn_id:P(n.turn_id),sequence:Number(n.sequence||0),action:P(n.action).toUpperCase(),status:P(r?.status)||"unknown",stage:P(r?.stage),reason:P(r?.reason),duration_ms:Number(r?.duration_ms||0),param_keys:xi(n.parameters||n.params),requested_url:P(r?.requested_url),final_url:P(r?.final_url||window.location.href),evidence:Ni(r?.evidence)}),i=Ci(Ri,t);if(!vi(i,o))try{await fetch(i,{method:"POST",headers:{Accept:"application/json","Content-Type":"application/json"},body:o,keepalive:!0})}catch(a){console.warn("[AIHubAdapter] Action execution report failed.",a)}}function vi(t,e){if(typeof navigator>"u"||typeof navigator.sendBeacon!="function"||typeof Blob!="function")return!1;try{return navigator.sendBeacon(t,new Blob([e],{type:"application/json"}))}catch{return!1}}function x(t){if(!t||typeof t!="string")return[];let e=[];for(let n of Li()){try{e.push(...Array.from(n.querySelectorAll(t)))}catch{return[]}if(e.length>=600)return e.slice(0,600)}return ki(e)}function Li(){let t=[],e=new Set,n=[document];for(;n.length&&t.length<60;){let r=n.shift();!r||e.has(r)||(e.add(r),t.push(r),n.push(...Pi(r)))}return t}function Pi(t){let e=[];for(let n of Di(t)){n.shadowRoot&&e.push(n.shadowRoot);let r=Ui(n);r&&e.push(r)}return e}function Di(t){try{return Array.from(t.querySelectorAll("*"))}catch{return[]}}function Ui(t){if(String(t?.tagName||"").toLowerCase()!=="iframe")return null;try{let e=t.contentDocument;return e?.documentElement?e:null}catch{return null}}function ki(t){return Array.from(new Set(t))}var ju=Object.freeze([l("stripe",["stripe","stripe.com","checkout.stripe.com","js.stripe.com"]),l("paypal",["paypal","paypal.com","paypalobjects.com"]),l("razorpay",["razorpay","checkout.razorpay.com"]),l("paytm",["paytm","securegw.paytm.in"]),l("cashfree",["cashfree","cashfree.com"]),l("checkout.com",["checkout.com","cko-session-id"]),l("adyen",["adyen","checkoutshopper"]),l("square",["squareup","squarecdn","square.site"]),l("braintree",["braintree","braintreegateway"]),l("mollie",["mollie","mollie.com"]),l("klarna",["klarna","klarna.com"]),l("afterpay",["afterpay","afterpay.com","clearpay"]),l("payu",["payu","payu.in","payu.com"]),l("paystack",["paystack","paystack.co"]),l("phonepe",["phonepe","phonepe.com"]),l("billdesk",["billdesk","billdesk.com"]),l("authorize.net",["authorize.net","accept.authorize.net"])]),Fn=Object.freeze([l("calendly",["calendly","calendly.com"]),l("acuity",["acuityscheduling","squarespace scheduling"]),l("booksy",["booksy","booksy.com"]),l("zocdoc",["zocdoc","zocdoc.com"]),l("appointlet",["appointlet","appointlet.com"]),l("setmore",["setmore","setmore.com"]),l("cal.com",["cal.com","calcom"]),l("google_calendar",["calendar.google.com","google calendar"]),l("microsoft_bookings",["microsoft bookings","outlook.office365.com/book"]),l("simplybook",["simplybook","simplybook.me"]),l("tidycal",["tidycal","tidycal.com"]),l("savvycal",["savvycal","savvycal.com"]),l("fresha",["fresha","fresha.com"])]),Hn=Object.freeze([l("google_maps",["google.com/maps","maps.googleapis","maps.google"]),l("mapbox",["mapbox","mapbox.com"]),l("openstreetmap",["openstreetmap","osm.org"]),l("leaflet",["leaflet","leafletjs"]),l("here_maps",["here.com","hereapi","wego.here.com"]),l("bing_maps",["bing.com/maps","virtualearth"]),l("mappls",["mappls","mapmyindia"])]),Bn=Object.freeze([l("whatsapp",["wa.me","api.whatsapp.com","web.whatsapp.com"]),l("telegram",["t.me/","telegram.me"]),l("messenger",["m.me/","messenger.com/t"]),l("zendesk",["zendesk.com","zdassets.com/hc"]),l("intercom",["intercom.help","intercom.com"]),l("freshchat",["freshchat.com"])]),qu=Object.freeze([l("recaptcha",["recaptcha","g-recaptcha","google.com/recaptcha"]),l("hcaptcha",["hcaptcha","h-captcha"]),l("turnstile",["turnstile","challenges.cloudflare.com"]),l("cloudflare_challenge",["cf-chl","cloudflare challenge"])]);function l(t,e){return{name:t,tokens:e}}function me(t,e,n=10){let r=he(t);return e.filter(o=>o.tokens.some(i=>r.includes(i))).map(o=>o.name).slice(0,n)}function he(t){return String(t||"").replace(/\s+/g," ").trim().toLowerCase()}var Yn="a[href], iframe[src]",Mi="a[href]",jn=new Set(["http:","https:"]),Ht=new Set(["mailto:","tel:"]),Fi=Object.freeze([p.URL,"href","link","target_url","provider_url","booking_url","appointment_url","calendar_url","map_url","location_url","contact_url"]),qn=new Set([c.OPEN_MAP,c.OPEN_LOCATION,c.SET_LOCATION]),Vn=new Set([c.CHECK_APPOINTMENT_AVAILABILITY,c.REQUEST_APPOINTMENT,c.BOOK_APPOINTMENT_REQUEST,c.REQUEST_CONSULTATION,c.REQUEST_SITE_VISIT,c.START_BOOKING]),zn=new Set([c.OPEN_CONTACT,c.CONTACT_AGENT,c.REQUEST_CALLBACK,c.REQUEST_COUNSELOR_CALLBACK,c.HANDOFF_TO_ADVISOR,c.HANDOFF_TO_AGENT,c.HANDOFF_TO_CLINIC,c.HANDOFF_TO_HUMAN,c.HANDOFF_TO_LAWYER,c.HANDOFF_TO_LICENSED_AGENT,c.HANDOFF_TO_RECRUITER]);function Wn(t){let e=Qn(t);return qn.has(e)||Vn.has(e)||zn.has(e)}async function Gn(t){let e=Qn(t);return qn.has(e)?_e(t,Hn,Yn,ye):Vn.has(e)?_e(t,Fn,Yn,ye):zn.has(e)?_e(t,Bn,Mi,$i):!1}function _e(t,e,n,r){let o=Hi(t?.parameters||t?.params||{},e,r);if(o)return $n(o);let i=Bi(n,e,r);return i?$n(i):!1}function Hi(t,e,n){for(let r of Fi){let o=Kn(t?.[r]);if(o&&n(o,e))return o}return null}function Bi(t,e,n){for(let r of x(t)){let o=Yi(r);if(!(!o||!n(o,e))&&ji(o,r,e))return o}return null}function Yi(t){return Kn(t?.getAttribute?.("href")||t?.getAttribute?.("src"))}function ye(t,e){return jn.has(t.protocol)&&me(t.href,e).length>0}function $i(t,e){return Ht.has(t.protocol)?!0:ye(t,e)}function ji(t,e,n){if(Ht.has(t.protocol))return!0;let r=[t.href,e?.textContent||"",e?.getAttribute?.("aria-label")||"",e?.getAttribute?.("title")||""].join(" ");return me(he(r),n).length>0}function $n(t){if(Ht.has(t.protocol)||t.origin===window.location.origin)return window.location.href=t.href,!0;let e=window.open(t.href,"_blank","noopener,noreferrer");return e?(e.opener=null,!0):(window.location.href=t.href,!0)}function Kn(t){let e=String(t||"").trim();if(!e||e.startsWith("#"))return null;try{let n=new URL(e,window.location.href);return jn.has(n.protocol)||Ht.has(n.protocol)?n:null}catch{return null}}function Qn(t){return String(t?.action||"").trim().toUpperCase()}var qi=Object.freeze(["title","name"]),Vi=Object.freeze(["summary","description","body"]),zi=Object.freeze(["image_url","imageUrl","image","thumbnail"]),Wi=Object.freeze(["url","href","permalink","source_url"]),Gi="knowledge_item",Ki=30;function M(t){return t==null||typeof t=="object"?"":String(t||"").trim()}function Qi(t){let e=new Set;return(Array.isArray(t)?t:[]).map(M).filter(Boolean).filter(n=>e.has(n)||e.size>=Ki?!1:(e.add(n),!0))}function Bt(t,e){for(let n of e){let r=M(t?.[n]);if(r)return r}return""}function At(t){return t&&typeof t=="object"&&!Array.isArray(t)?t:{}}function Xi(t){let e=Ji([t?.price,t?.amount,t?.premium,t?.premium_min,t?.monthly_premium,t?.annual_premium,t?.min_price,t?.starting_price]),n=M(t?.currency||"INR");return!Number.isFinite(e)||e<=0?"":`${n} ${e.toLocaleString()}`}function Ji(t){for(let e of t){let n=Number(String(e??"").replace(/,/g,""));if(Number.isFinite(n)&&n>0)return n}return 0}function Zi(t){return!t||typeof t!="object"?"":t.in_stock===!0?"Available":t.in_stock===!1?"Unavailable":M(t.status||t.availability||"")}function ta(t){let e=M(t);if(!e)return"";try{let n=new URL(e,window.location.origin);return/^https?:$/i.test(n.protocol)?n.origin===window.location.origin?`${n.pathname}${n.search}${n.hash}`:n.toString():""}catch{return""}}function ea(t){if(!t)return null;let e=M(t.id);if(!e)return null;let n=At(t.pricing),r=At(t.availability);return{id:e,externalId:M(t.external_id),entityType:M(t.entity_type||t.category_name)||Gi,title:Bt(t,qi)||e,subtitle:M(t.subtitle||t.category_name||t.entity_type),summary:Bt(t,Vi),body:M(t.body),url:ta(Bt(t,Wi)),imageUrl:Bt(t,zi),attributes:At(t.attributes),pricing:n,availability:r,location:At(t.location),contact:At(t.contact),displayPrice:Xi(n),displayAvailability:Zi(r)}}async function ge(t){let e=Qi(t);if(!e.length)return[];let n=new URL(U.KNOWLEDGE_BY_IDS,d.apiUrl);n.searchParams.set("site_id",d.siteId),n.searchParams.set("ids",e.join(","));let r=await fetch(n.toString(),{headers:{Accept:"application/json"}});if(!r.ok)throw new Error("Failed to fetch entities from AI Hub API");let o=(await r.json()).map(ea).filter(Boolean),i=new Map(o.map(a=>[String(a.id),a]));return e.map(a=>i.get(a)).filter(Boolean)}async function Xn(t){let[e]=await ge([t]);return e?.url||""}function Jn(){if(document.getElementById("mayabot-entity-overlay-styles"))return;let t=document.createElement("style");t.id="mayabot-entity-overlay-styles",t.textContent=`
    #mayabot-entity-panel {
      position: fixed;
      left: 50%;
      bottom: 96px;
      z-index: 2147483638;
      width: min(calc(100vw - 32px), var(--mayabot-entity-panel-width, 760px));
      max-height: min(72vh, 620px);
      transform: translate(-50%, calc(100% + 32px));
      opacity: 0;
      pointer-events: none;
      display: flex;
      flex-direction: column;
      overflow: hidden;
      border: 1px solid rgba(22, 22, 21, 0.12);
      border-radius: 8px;
      background: rgba(247, 247, 243, 0.97);
      box-shadow: 0 24px 70px rgba(22, 22, 21, 0.18);
      color: #161615;
      font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      transition: transform 0.26s cubic-bezier(0.16, 1, 0.3, 1), opacity 0.2s ease;
    }
    #mayabot-entity-panel.active {
      transform: translate(-50%, 0);
      opacity: 1;
      pointer-events: auto;
    }
    #mayabot-entity-panel.count-1 { --mayabot-entity-panel-width: 420px; }
    #mayabot-entity-panel.count-2 { --mayabot-entity-panel-width: 660px; }
    #mayabot-entity-panel.count-3,
    #mayabot-entity-panel.count-many { --mayabot-entity-panel-width: 980px; }
    .mayabot-entity-header {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 14px;
      padding: 14px 16px;
      border-bottom: 1px solid rgba(22, 22, 21, 0.1);
    }
    .mayabot-entity-title {
      margin: 0;
      color: #161615;
      font-size: 15px;
      font-weight: 800;
      line-height: 1.25;
      letter-spacing: 0;
    }
    .mayabot-entity-close {
      display: grid;
      place-items: center;
      width: 34px;
      height: 34px;
      flex: 0 0 auto;
      border: 1px solid rgba(22, 22, 21, 0.14);
      border-radius: 8px;
      background: #ffffff;
      color: #161615;
      cursor: pointer;
      font-size: 20px;
      line-height: 1;
    }
    .mayabot-entity-grid {
      display: grid;
      grid-template-columns: repeat(var(--mayabot-entity-card-count, 2), minmax(0, 1fr));
      gap: 12px;
      padding: 14px;
      overflow: auto;
      scrollbar-width: thin;
    }
    .mayabot-entity-card {
      display: grid;
      grid-template-rows: auto auto auto 1fr auto;
      gap: 10px;
      min-width: 0;
      border: 1px solid rgba(22, 22, 21, 0.1);
      border-radius: 8px;
      background: #ffffff;
      padding: 12px;
    }
    .mayabot-entity-media {
      display: grid;
      place-items: center;
      min-height: 116px;
      border-radius: 8px;
      background: #f1f2ee;
      overflow: hidden;
    }
    .mayabot-entity-media img {
      width: 100%;
      height: 150px;
      object-fit: contain;
      padding: 8px;
    }
    .mayabot-entity-badge {
      display: grid;
      place-items: center;
      width: 100%;
      min-height: 116px;
      padding: 12px;
      color: #534d44;
      font-size: 13px;
      font-weight: 760;
      text-align: center;
      text-transform: capitalize;
    }
    .mayabot-entity-name {
      margin: 0;
      min-height: 38px;
      color: #161615;
      font-size: 14px;
      font-weight: 760;
      line-height: 1.35;
      display: -webkit-box;
      -webkit-line-clamp: 2;
      -webkit-box-orient: vertical;
      overflow: hidden;
    }
    .mayabot-entity-meta {
      margin: 0;
      color: #686660;
      font-size: 12px;
      line-height: 1.35;
      overflow-wrap: anywhere;
      text-transform: capitalize;
    }
    .mayabot-entity-summary {
      margin: 0;
      color: #3d3933;
      font-size: 13px;
      line-height: 1.42;
      display: -webkit-box;
      -webkit-line-clamp: 4;
      -webkit-box-orient: vertical;
      overflow: hidden;
    }
    .mayabot-entity-facts {
      display: flex;
      flex-wrap: wrap;
      gap: 6px;
    }
    .mayabot-entity-fact {
      border: 1px solid rgba(22, 22, 21, 0.1);
      border-radius: 999px;
      padding: 5px 8px;
      color: #534d44;
      background: #f7f7f3;
      font-size: 11px;
      font-weight: 700;
      line-height: 1;
      overflow-wrap: anywhere;
    }
    .mayabot-entity-actions {
      display: flex;
      justify-content: flex-end;
      align-self: end;
    }
    .mayabot-entity-actions button {
      min-height: 36px;
      min-width: 86px;
      border: 1px solid rgba(22, 22, 21, 0.12);
      border-radius: 8px;
      background: #161615;
      color: #ffffff;
      cursor: pointer;
      font-size: 12px;
      font-weight: 760;
      line-height: 1;
    }
    .mayabot-entity-empty {
      margin: 0;
      padding: 14px;
      color: #686660;
      font-size: 14px;
    }
    @media (max-width: 720px) {
      #mayabot-entity-panel {
        bottom: 86px;
        width: min(calc(100vw - 20px), 520px);
      }
      #mayabot-entity-panel.count-2,
      #mayabot-entity-panel.count-3,
      #mayabot-entity-panel.count-many {
        --mayabot-entity-card-count: 2;
      }
      .mayabot-entity-grid {
        padding: 12px;
      }
      .mayabot-entity-media img {
        height: 132px;
      }
    }
    @media (max-width: 430px) {
      #mayabot-entity-panel {
        bottom: 82px;
      }
      #mayabot-entity-panel.count-1,
      #mayabot-entity-panel.count-2,
      #mayabot-entity-panel.count-3,
      #mayabot-entity-panel.count-many {
        --mayabot-entity-card-count: 1;
      }
    }
  `,document.head.appendChild(t)}var na=2,Zn=Number.POSITIVE_INFINITY,Yt=Number.NEGATIVE_INFINITY,tr=12,Te=[],Ae=Q;function j(t){return String(t??"").replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;").replace(/"/g,"&quot;").replace(/'/g,"&#039;")}function or(t){return String(t||"item").replace(/[_-]+/g," ").trim().split(/\s+/).slice(0,na).join(" ")}function ra(){Jn();let t=document.getElementById("mayabot-entity-panel");return t||(t=document.createElement("div"),t.id="mayabot-entity-panel",t.setAttribute("aria-live","polite"),t.innerHTML=`
    <div class="mayabot-entity-header">
      <h2 class="mayabot-entity-title">${Q}</h2>
      <button class="mayabot-entity-close" type="button" aria-label="Close recommendations">&times;</button>
    </div>
    <div class="mayabot-entity-grid"></div>
  `,t.querySelector(".mayabot-entity-close").addEventListener("click",()=>{t.classList.remove("active")}),document.body.appendChild(t),t)}function oa(t){return t<=1?"count-1":t===2?"count-2":t===3?"count-3":"count-many"}function ia(t){return t<=1?1:t===2?2:3}function be(t,e,n=""){let r=(Array.isArray(e)?e:[]).map(s=>String(s?.id??"").trim()).filter(Boolean),o=r.length,i=t.length,a=o>0?"succeeded":"failed";return{status:a,stage:"entity_overlay",reason:n||(a==="succeeded"?"":"no_matching_entities_rendered"),evidence:{requested_entity_count:i,rendered_entity_count:o,missing_entity_count:Math.max(i-o,0),requested_entity_ids:t.slice(0,tr).join(","),rendered_entity_ids:r.slice(0,tr).join(",")}}}function aa(t){return[t.displayPrice,t.displayAvailability,t.location?.city,t.attributes?.category].map(e=>String(e||"").trim()).filter(Boolean).slice(0,3)}function sa(t){return t.imageUrl?`
      <div class="mayabot-entity-media">
        <img src="${j(t.imageUrl)}" alt="${j(t.title)}">
      </div>
    `:`
    <div class="mayabot-entity-media">
      <div class="mayabot-entity-badge">${j(or(t.entityType))}</div>
    </div>
  `}function ca(t){let e=aa(t);return e.length?`
    <div class="mayabot-entity-facts">
      ${e.map(n=>`<span class="mayabot-entity-fact">${j(n)}</span>`).join("")}
    </div>
  `:""}function ua(t){return t.url?`
    <div class="mayabot-entity-actions">
      <button type="button" data-view-entity="${j(t.id)}">Open</button>
    </div>
  `:""}function jt(t,e){let n=ra(),r=n.querySelector(".mayabot-entity-grid"),o=n.querySelector(".mayabot-entity-title"),i=t.length;if(Te=Array.isArray(t)?[...t]:[],Ae=e||Q,n.classList.remove("count-1","count-2","count-3","count-many"),n.classList.add(oa(i)),n.style.setProperty("--mayabot-entity-card-count",String(ia(i))),o.textContent=Ae,!i){r.innerHTML='<p class="mayabot-entity-empty">No matching records are currently available.</p>',n.classList.add("active"),er();return}r.innerHTML=t.map(a=>`
        <article class="mayabot-entity-card" data-entity-id="${j(a.id)}">
          ${sa(a)}
          <h3 class="mayabot-entity-name">${j(a.title)}</h3>
          <p class="mayabot-entity-meta">${j(a.subtitle||or(a.entityType))}</p>
          <p class="mayabot-entity-summary">${j(a.summary||a.body||"Details are available on the website.")}</p>
          ${ca(a)}
          ${ua(a)}
        </article>
      `).join(""),r.querySelectorAll("[data-view-entity]").forEach(a=>{a.addEventListener("click",async()=>{await Ee(a.getAttribute("data-view-entity"))})}),n.classList.add("active"),er()}function la(t){if(!t)return!1;try{let e=new URL(t,window.location.origin);return e.origin===window.location.origin?(window.location.href=`${e.pathname}${e.search}${e.hash}`,!0):(window.open(e.toString(),"_blank","noopener,noreferrer"),!0)}catch{return!1}}function er(){window.setTimeout(()=>{let t=document.getElementById("mayabot-chat"),e=document.getElementById("mayabot-msgs");e&&(e.innerHTML=""),t&&t.classList.remove("visible")},lt)}async function Ee(t){let e=await Xn(t);return la(e)}async function ir(t,e=Q){let n=Se({[p.ENTITY_IDS]:t});if(!n.length)return jt([],e),be([],[],"missing_entity_ids");try{let r=await ge(n);return jt(r,e),be(n,r)}catch(r){return console.warn("[AI Hub Widget] Entity overlay failed:",r),jt([],e),be(n,[],"entity_overlay_fetch_failed")}}function Se(t){let e=t[p.ENTITY_IDS]||t.ids||t.items||[],n=new Set;return(Array.isArray(e)?e:[]).map(r=>String(r??"").trim()).filter(Boolean).filter(r=>n.has(r)?!1:(n.add(r),!0))}function ar(t={}){if(!Te.length)return!1;let e=String(t.sort_by||t.sortBy||"price_asc").trim().toLowerCase(),n=[...Te].sort((o,i)=>da(o,i,e)),r=fa(Ae,e);return jt(n,r),!0}function da(t,e,n){return n==="price_desc"?$t(e,Yt)-$t(t,Yt):n==="rating"?nr(e,Yt)-nr(t,Yt):n==="newest"?rr(e)-rr(t):$t(t,Zn)-$t(e,Zn)}function $t(t,e){return sr([t?.pricing?.price,t?.pricing?.amount,t?.pricing?.premium,t?.pricing?.premium_min,t?.pricing?.monthly_premium,t?.pricing?.annual_premium,t?.pricing?.min_price,t?.pricing?.starting_price,t?.attributes?.price,t?.attributes?.amount,t?.attributes?.premium,t?.attributes?.monthly_premium,t?.attributes?.annual_premium,t?.displayPrice],e)}function nr(t,e){return sr([t?.attributes?.rating,t?.attributes?.review_rating,t?.attributes?.stars,t?.availability?.rating],e)}function rr(t){let e=t?.attributes?.updated_at||t?.attributes?.date||t?.availability?.updated_at||"",n=Date.parse(String(e||""));return Number.isFinite(n)?n:0}function sr(t,e){for(let n of t){let r=pa(n);if(Number.isFinite(r))return r}return e}function pa(t){if(typeof t=="number")return t;let e=String(t??"").replace(/,/g,"").match(/-?\d+(?:\.\d+)?/);return e?Number(e[0]):Number.NaN}function fa(t,e){let n={price_asc:"sorted low to high",price_desc:"sorted high to low",rating:"sorted by rating",newest:"newest first"};return`${String(t||Q).replace(/\s+-\s+sorted.*$/i,"")} - ${n[e]||n.price_asc}`}function cr(t){return t.action===c.SHOW_ENTITIES||t.action===c.COMPARE_ENTITIES||t.action===c.OPEN_ENTITY_DETAIL||t.action===c.SORT_ENTITIES}async function ur(t){return t.action===c.SHOW_ENTITIES||t.action===c.COMPARE_ENTITIES?ma(t.parameters||{}):t.action===c.OPEN_ENTITY_DETAIL?Ee(t.parameters?.[p.ENTITY_ID]||t.parameters?.id):t.action===c.SORT_ENTITIES?ar(t.parameters||{}):!1}function ma(t){return ir(Se(t),t[p.SEARCH_QUERY]||t.title||Q)}var Et="mayabot-handoff-panel",lr="mayabot-handoff-overlay-styles",ha=Object.freeze(["contact","support","help"]),_a=Object.freeze(["checkout","cart"]),mr=new Set([c.CHECKOUT_HANDOFF,c.HANDOFF_TO_ADVISOR,c.HANDOFF_TO_AGENT,c.HANDOFF_TO_CLINIC,c.HANDOFF_TO_HUMAN,c.HANDOFF_TO_LAWYER,c.HANDOFF_TO_LICENSED_AGENT,c.HANDOFF_TO_RECRUITER]),dr=Object.freeze({[c.CHECKOUT_HANDOFF]:{title:"Checkout needs your confirmation",body:"This step may include payment or a secure checkout page. I can take you there, then you complete the final step yourself.",primary:"Open checkout"},[c.HANDOFF_TO_ADVISOR]:{title:"Advisor handoff",body:"This request needs a qualified advisor. I can open the contact path so the site team can continue.",primary:"Contact advisor"},[c.HANDOFF_TO_AGENT]:{title:"Agent handoff",body:"This step needs an agent or account-specific help. I can open the contact path for follow-up.",primary:"Contact agent"},[c.HANDOFF_TO_CLINIC]:{title:"Clinic handoff",body:"This request needs clinic confirmation. I can open the appointment or contact path for the next step.",primary:"Contact clinic"},[c.HANDOFF_TO_HUMAN]:{title:"Human handoff",body:"This step needs human confirmation. I can open the most relevant contact path.",primary:"Open contact"},[c.HANDOFF_TO_LAWYER]:{title:"Legal handoff",body:"This request needs a legal professional. I can open the consultation or contact path.",primary:"Contact lawyer"},[c.HANDOFF_TO_LICENSED_AGENT]:{title:"Licensed agent handoff",body:"This request needs a licensed agent. I can open the quote or contact path for follow-up.",primary:"Contact agent"},[c.HANDOFF_TO_RECRUITER]:{title:"Recruiter handoff",body:"This request needs recruiter review. I can open the application or contact path.",primary:"Contact recruiter"}});function dt(t){return String(t??"").replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;").replace(/"/g,"&quot;").replace(/'/g,"&#039;")}function rt(t){return String(t||"").trim()}function ya(){if(document.getElementById(lr))return;let t=document.createElement("style");t.id=lr,t.textContent=`
    #${Et} {
      position: fixed;
      left: 50%;
      bottom: 96px;
      z-index: 2147483639;
      width: min(calc(100vw - 32px), 460px);
      transform: translate(-50%, calc(100% + 32px));
      opacity: 0;
      pointer-events: none;
      border: 1px solid rgba(22, 22, 21, 0.12);
      border-radius: 8px;
      background: rgba(255, 255, 255, 0.98);
      box-shadow: 0 24px 70px rgba(22, 22, 21, 0.18);
      color: #161615;
      font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      transition: transform 0.26s cubic-bezier(0.16, 1, 0.3, 1), opacity 0.2s ease;
    }
    #${Et}.active {
      transform: translate(-50%, 0);
      opacity: 1;
      pointer-events: auto;
    }
    .mayabot-handoff-body {
      display: grid;
      gap: 12px;
      padding: 16px;
    }
    .mayabot-handoff-top {
      display: flex;
      align-items: start;
      justify-content: space-between;
      gap: 14px;
    }
    .mayabot-handoff-title {
      margin: 0;
      color: #161615;
      font-size: 16px;
      font-weight: 800;
      line-height: 1.25;
      letter-spacing: 0;
    }
    .mayabot-handoff-close {
      display: grid;
      place-items: center;
      width: 34px;
      height: 34px;
      flex: 0 0 auto;
      border: 1px solid rgba(22, 22, 21, 0.14);
      border-radius: 8px;
      background: #ffffff;
      color: #161615;
      cursor: pointer;
      font-size: 20px;
      line-height: 1;
    }
    .mayabot-handoff-text {
      margin: 0;
      color: #534d44;
      font-size: 14px;
      line-height: 1.45;
    }
    .mayabot-handoff-reason {
      margin: 0;
      border-left: 3px solid #d9b66f;
      padding: 8px 10px;
      background: #fbf6ea;
      color: #534d44;
      font-size: 12px;
      line-height: 1.35;
      overflow-wrap: anywhere;
    }
    .mayabot-handoff-meta {
      display: grid;
      gap: 4px;
      margin: 0;
      color: #6f665b;
      font-size: 12px;
      line-height: 1.35;
      overflow-wrap: anywhere;
    }
    .mayabot-handoff-meta strong {
      color: #161615;
      font-weight: 760;
    }
    .mayabot-handoff-actions {
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      justify-content: flex-end;
    }
    .mayabot-handoff-actions button {
      min-height: 38px;
      border: 1px solid rgba(22, 22, 21, 0.12);
      border-radius: 8px;
      background: #161615;
      color: #ffffff;
      cursor: pointer;
      font-size: 13px;
      font-weight: 760;
      line-height: 1;
      padding: 0 14px;
    }
    .mayabot-handoff-actions button.secondary {
      background: #ffffff;
      color: #161615;
    }
    @media (max-width: 430px) {
      #${Et} {
        bottom: 82px;
        width: min(calc(100vw - 20px), 420px);
      }
    }
  `,document.head.appendChild(t)}function ga(){ya();let t=document.getElementById(Et);return t||(t=document.createElement("div"),t.id=Et,t.setAttribute("aria-live","polite"),document.body.appendChild(t),t)}function ba(){return window.AIHubAdapterRuntime?.config?.adapter?.routes||window.AIHubAdapter?.config?.adapter?.routes||{}}function Ta(t,e){let n=pr(e[p.URL]||e.path||e.href||e.handoff_flow?.page_url);if(n)return n;let r=ba(),o=t===c.CHECKOUT_HANDOFF?_a:ha;for(let i of o){let a=pr(r[i]);if(a)return a}return""}function pr(t){let e=rt(t);if(!e)return"";try{let n=new URL(e,window.location.origin);return n.origin!==window.location.origin?"":`${n.pathname}${n.search}${n.hash}`||"/"}catch{return""}}function Aa(t){return dr[t]||dr[c.HANDOFF_TO_HUMAN]}function Ea(t){return t&&typeof t=="object"?t:{}}function Sa(t,e){return rt(t.title)||e}function wa(t,e,n){return rt(e[p.MESSAGE])||rt(t.handling)||n}function Ia(t,e){return rt(e[p.REASON]||e.reason||e.blocked_reason||t.key)}function Oa(t){let e=[["Provider",t.provider_label||t.provider],["Boundary",t.automation_boundary],["Recovery",t.recovery],["Evidence",t.evidence],["Page",t.page_url]].filter(([,n])=>rt(n));return e.length?`
    <p class="mayabot-handoff-meta">
      ${e.map(([n,r])=>`<span><strong>${dt(n)}:</strong> ${dt(r)}</span>`).join("")}
    </p>
  `:""}function fr(t){t.classList.remove("active")}function Ra(){window.setTimeout(()=>{let t=document.getElementById("mayabot-chat"),e=document.getElementById("mayabot-msgs");e&&(e.innerHTML=""),t&&t.classList.remove("visible")},lt)}function hr(t,e={}){let n=rt(t).toUpperCase(),r=Aa(n),o=Ea(e.handoff_flow),i=ga(),a=Ta(n,e),s=Sa(o,r.title),u=wa(o,e,r.body),f=Ia(o,e);return i.innerHTML=`
    <div class="mayabot-handoff-body">
      <div class="mayabot-handoff-top">
        <h2 class="mayabot-handoff-title">${dt(s)}</h2>
        <button class="mayabot-handoff-close" type="button" aria-label="Close handoff">&times;</button>
      </div>
      <p class="mayabot-handoff-text">${dt(u)}</p>
      ${Oa(o)}
      ${f?`<p class="mayabot-handoff-reason">${dt(f)}</p>`:""}
      <div class="mayabot-handoff-actions">
        <button type="button" class="secondary" data-close-handoff>Close</button>
        ${a?`<button type="button" data-open-handoff>${dt(r.primary)}</button>`:""}
      </div>
    </div>
  `,i.querySelector(".mayabot-handoff-close")?.addEventListener("click",()=>fr(i)),i.querySelector("[data-close-handoff]")?.addEventListener("click",()=>fr(i)),i.querySelector("[data-open-handoff]")?.addEventListener("click",()=>{window.location.href=a}),i.classList.add("active"),Ra(),!0}function _r(t){return mr.has(t.action)}function yr(t){return hr(t.action,t.parameters||{})}function br(t){return t.action===c.NAVIGATE_TO&&!!Ar(t.parameters?.[p.PAGE])}function Tr(t){return window.location.href=Ar(t.parameters?.[p.PAGE]),!0}function Ar(t){let e=String(t||"").trim();if(!e||Er(e)||/^https?:\/\//i.test(e))return"";if(e==="home"||e==="/")return"/";let n=Ca(e);if(n)return n;let r=e.replace(/^\/+|\/+$/g,"");return r?`/${r}`:"/"}function Ca(t){let e=window.AIHubAdapterRuntime?.config?.adapter?.routes||window.AIHubAdapter?.config?.adapter?.routes||{},n=xa(t);for(let r of n){let o=e[r],i=gr(o);if(i)return i}for(let[r,o]of Object.entries(e)){if(!n.includes(we(r)))continue;let i=gr(o);if(i)return i}return""}function xa(t){let e=we(t),n=String(t||"").trim().replace(/^\/+|\/+$/g,"").toLowerCase(),r=n.split("?")[0].split("#")[0].split("/").filter(Boolean).pop()||"";return Array.from(new Set([e,n,we(r)].filter(Boolean)))}function we(t){return String(t||"").trim().toLowerCase().replace(/[^a-z0-9/_\s-]+/g," ").replace(/[_-]+/g," ").replace(/\s+/g," ").trim().replace(/\s+/g,"-")}function gr(t){let e=String(t||"").trim();if(!e||Er(e))return"";if(/^https?:\/\//i.test(e))try{let n=new URL(e);return n.origin!==window.location.origin?"":`${n.pathname||"/"}${n.search||""}${n.hash||""}`}catch{return""}return e.startsWith("/")?e:`/${e.replace(/^\/+/,"")}`}function Er(t){return/^(?:javascript:|data:|\/\/)/i.test(String(t||"").trim())}function Sr(t){let e=t?.params||t?.parameters||{};return{...t||{},action:String(t?.action||"").trim().toUpperCase(),params:e,parameters:e}}var Ie="AIHubAdapterRuntime",Oe="AIHubAdapter";function Na(t){let e=t?.params||t?.parameters||{};return{...t||{},params:e,parameters:e}}function St(){return!!(window[Ie]?.executeAction||window[Oe]?.handleAction)}async function Re(t){return(await wt(t)).succeeded}async function wt(t){let e=Na(t);if(window[Ie]?.executeAction){let n=window[Ie],r=await n.executeAction(e)===!0,o=n.lastActionResult||{};return{succeeded:r,handled:o.handled===!0||r,status:o.status||(r?"ok":"not_handled"),reason:o.reason||"",blocked:o.status==="blocked",disabled:o.status==="disabled"}}if(window[Oe]?.handleAction){let n=await window[Oe].handleAction(e)===!0;return{succeeded:n,handled:n,status:n?"ok":"not_handled",reason:"",blocked:!1,disabled:!1}}return{succeeded:!1,handled:!1,status:"missing_adapter",reason:"",blocked:!1,disabled:!1}}var va=Object.freeze([{path:"/api/products?per_page=96",routePrefix:"/product/"},{path:"/api/products",routePrefix:"/product/"},{path:"/api/products.json",routePrefix:""},{path:"/products.json",routePrefix:"/products/"},{path:"/collections/all/products.json",routePrefix:"/products/"}]),La=Object.freeze(["products","data","items","results"]),Ir=Object.freeze(["id","product_id","handle","sku"]),Or=Object.freeze(["name","title"]),Pa=Object.freeze(["url","href","permalink","product_url"]),Da=Object.freeze(["image_url","imageUrl","image_src","imageSrc","image","images","media","thumbnail","thumbnail_url","featured_image","featuredImage","featured_image_url"]),Ua=Object.freeze(["brand","vendor"]),ka=Object.freeze(["category","category_name","product_type"]),Ma=Object.freeze(["description","summary","body_html"]),Fa=Object.freeze(["original_price","compare_at_price","regular_price"]),Rr=Object.freeze(["currency","currency_code"]),Ha=Object.freeze(["display_price","price_text","formatted_price"]),Ba="Unknown Brand",Ya="Products",$a="/",ja=/^[a-z0-9][a-z0-9-]*$/i,Ce=null;function D(t){return t==null||typeof t=="object"?"":String(t||"").trim()}function ve(t){return D(t).toLowerCase().replace(/[^a-z0-9]+/g," ").trim()}function Cr(t){let e=new Set(["a","am","an","and","ask","asked","did","for","me","not","on","only","please","show","some","the","to","wanna","want","what","with","you","your"]),n=[],r=new Set;for(let o of qa(ve(t)).split(" ")){let i=Va(o);i.length<=1||e.has(i)||r.has(i)||(n.push(i),r.add(i))}return n}function qa(t){return t.replace(/\b(?:i\s+)?did\s+not\s+ask\s+for\s+(?:a\s+|an\s+)?[a-z0-9]+\b/g," ")}function Va(t){return["phone","phones","mobile","mobiles"].includes(t)?"phone":["book","books"].includes(t)?"books":t}function Le(t,e){return e.map(n=>D(t?.[n])).filter(Boolean)}function F(t,e){return Le(t,e)[0]||""}function qt(t){let e=D(t).replace(/,/g,"");if(!e)return 0;let n=e.match(/-?\d+(?:\.\d+)?/),r=Number(n?n[0]:e);return Number.isFinite(r)?r:0}function za(t,e){let n=F(t,Ha);if(n)return n;let r=F(t,Rr).toUpperCase();return e>0&&r?`${r} ${e.toLocaleString()}`:e>0?e.toLocaleString():""}function Wa(t){for(let e of Da){let n=xe(t?.[e]);if(n)return n}return""}function xe(t){if(!t)return"";if(Array.isArray(t)){for(let e of t){let n=xe(e);if(n)return n}return""}if(typeof t=="object"){for(let e of["src","url","image_url","imageUrl","image_src","imageSrc","thumbnail","thumbnail_url","featured_image","featuredImage","featured_image_url"]){let n=xe(t[e]);if(n)return n}return""}return Ga(t)}function Ga(t){let e=D(t);if(!e||/^javascript:/i.test(e))return"";if(/^data:image\//i.test(e))return e;try{let n=new URL(e,window.location.origin);return["http:","https:"].includes(n.protocol)?n.toString():""}catch{return""}}function Ka(t){let e=D(t);if(!e)return"";try{let n=new URL(e,window.location.origin);return n.origin!==window.location.origin?"":`${n.pathname}${n.search}${n.hash}`}catch{return""}}function Qa(t,e,n){let r=Ka(F(t,Pa));return r||(!ja.test(e)||!/[a-z]/i.test(e)||!n?.routePrefix?"":`${n.routePrefix}${encodeURIComponent(e)}${$a}`)}function Pe(t,e={}){if(!t)return null;let n=F(t,Ir),r=D(t.handle||t.slug||t.product_handle),o=F(t,Or),i=qt(t.price||t.amount||t.cost),a=qt(F(t,Fa));return!n&&!r?null:{id:n,handle:r,name:o,title:D(t.title||o),brand:F(t,Ua)||Ba,category:F(t,ka)||Ya,description:F(t,Ma),price:Number.isFinite(i)?i:0,originalPrice:Number.isFinite(a)?a:0,displayPrice:za(t,i),currency:F(t,Rr),rating:qt(t.rating||t.review_rating),reviewCount:qt(t.review_count||t.reviews_count||t.reviews),imageUrl:Wa(t),url:Qa(t,r||n,e)}}function Xa(t){return Le(t,Ir)}function wr(t){return Le(t,Or).map(ve)}function xr(t,e){let n=D(e);return!!(n&&Xa(t).includes(n))}function Nr(t,e){let n=Cr(e);if(!n.length)return!1;let r=ve([t?.name,t?.title,t?.brand,t?.category,t?.category_name,t?.product_type,t?.description,t?.tags].join(" "));return n.every(o=>r.includes(o)||r.includes(o.replace(/s$/,"")))}function Ja(t,e){let n=new Set(wr(e));return wr(t).some(r=>n.has(r))}function Za(t,e){return!!(t?.imageUrl&&t.imageUrl===e?.imageUrl)}function ts(t){if(Array.isArray(t))return t;for(let e of La){let n=t?.[e];if(Array.isArray(n))return n}return[]}async function es(t){try{let e=await fetch(new URL(t.path,window.location.origin),{headers:{Accept:"application/json"}});if(!e.ok)return[];let n=await e.json();return ts(n).map(r=>Pe(r,t)).filter(Boolean)}catch(e){return console.warn(`[AI Hub Widget] Catalog endpoint lookup failed for ${t.path}:`,e),[]}}async function Ne(){return Ce||(Ce=Promise.all(va.map(es)).then(t=>t.flat())),Ce}async function ns(t,e=120){if(!Cr(t).length)return[];let r=new URL("/v1/products",d.apiUrl);r.searchParams.set("site_id",d.siteId),r.searchParams.set("limit",String(e));try{let o=await fetch(r.toString(),{headers:{Accept:"application/json"}});return o.ok?(await o.json()).map(i=>Pe(i)).filter(Boolean).filter(i=>Nr(i,t)).slice(0,12):[]}catch(o){return console.warn("[AI Hub Widget] Hub product search fallback failed:",o),[]}}async function vr(t,e=""){let n=(Array.isArray(t)?t:[]).map(D).filter(Boolean),r=[],o="",i="";if(n.length)try{r=await Lr(n),o="hub_by_ids"}catch(a){i="hub_product_lookup_failed",console.warn("[AI Hub Widget] Hub product ID lookup failed:",a)}if(!r.length&&n.length){let a=await Ne();r=n.map(s=>a.find(u=>xr(u,s))).filter(Boolean),r.length&&(o="host_by_ids")}return!r.length&&e&&(r=await ns(e),r.length&&(o="hub_search")),!r.length&&e&&(r=(await Ne()).filter(s=>Nr(s,e)).slice(0,12),r.length&&(o="host_search")),{products:r,source:o,reason:r.length?"":i||"no_matching_products_rendered"}}async function Lr(t){let e=(Array.isArray(t)?t:[]).map(D).filter(Boolean);if(!e.length)return[];let n=new URL(U.PRODUCTS_BY_IDS,d.apiUrl);n.searchParams.set("site_id",d.siteId),n.searchParams.set("ids",e.join(","));let r=await fetch(n.toString(),{headers:{Accept:"application/json"}});if(!r.ok)throw new Error("Failed to fetch products from AI Hub API");let o=(await r.json()).map(a=>Pe(a)).filter(Boolean),i=new Map(o.map(a=>[String(a.id),a]));return e.map(a=>i.get(a)).filter(Boolean)}async function Vt(t){let e=D(t);if(!e)return"";let[n]=await Lr([e]);if(n?.url)return n.url;let r=await Ne(),o=r.find(a=>xr(a,e));return o?.url?o.url:n&&r.find(a=>Ja(a,n)||Za(a,n))?.url||""}var rs=1,os=1.08,is=300,as=Object.freeze(["hannah","sonia","libby","ava","susan","hazel","heera","salli","joanna","amy","emma","olivia","natasha","zira","aria","jenny","samantha","victoria","tessa","moira","karen","female","woman","nova","shimmer","google us english","microsoft aria"]),q="",zt="",It=null,De=0;function ot(t){if(!("speechSynthesis"in window)||!("SpeechSynthesisUtterance"in window))return!1;Wt();let e=++De;q=t;let n=()=>{if(e!==De||q!==t)return!1;try{let r=new SpeechSynthesisUtterance(t),o=ss(window.speechSynthesis.getVoices());return o?(o&&(r.voice=o),r.rate=rs,r.pitch=os,r.onstart=Pr,r.onend=Pr,Wt(),window.speechSynthesis.cancel(),window.speechSynthesis.resume(),window.speechSynthesis.speak(r),!0):(q="",!1)}catch{return!1}};return window.speechSynthesis.getVoices().length>0?n():(window.speechSynthesis.onvoiceschanged=n,It=window.setTimeout(()=>{It=null,n()},is),!0)}function Gt(){q&&ot(q)}function Dr(){try{return!!q||!!window.speechSynthesis?.speaking||!!window.speechSynthesis?.pending}catch{return!!q}}function Kt(){De+=1,Wt(),q="",zt="";try{window.speechSynthesis?.cancel()}catch{}}function ss(t){if(!Array.isArray(t)||t.length===0)return null;let e=cs(t)||us(t);return e&&(zt=e.name),e}function cs(t){if(zt){let n=t.find(r=>r.name===zt);if(n)return n}let e=String(d.speechVoiceName||"").toLowerCase();return e&&t.find(n=>n.name.toLowerCase()===e)||null}function us(t){return d.speechVoicePreference.toLowerCase()!=="female"?t.find(e=>e.default)||t[0]:t.find(e=>as.some(n=>e.name.toLowerCase().includes(n)))||null}function Pr(){Wt(),q=""}function Wt(){It&&window.clearTimeout(It),It=null,window.speechSynthesis&&(window.speechSynthesis.onvoiceschanged=null)}var ls=["data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='320' height='240' viewBox='0 0 320 240'%3E","%3Crect width='320' height='240' fill='%23f1f2ee'/%3E","%3Cpath d='M98 156h124l-31-40-25 30-17-22-51 32Z' fill='%23c8c3ba'/%3E","%3Ccircle cx='117' cy='95' r='17' fill='%23d8d3ca'/%3E","%3Ctext x='160' y='198' text-anchor='middle' fill='%23686660' font-family='Arial,sans-serif' font-size='16'%3EImage pending%3C/text%3E","%3C/svg%3E"].join(""),Ur=12,ds=4,ps=6,fs=700,Xt=[],ke=$,Jt=new Map,Me=!1;function ms(){try{Kt()}catch{}}function X(t){return String(t??"").replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;").replace(/"/g,"&quot;").replace(/'/g,"&#039;")}function hs(){if(document.getElementById("mayabot-product-overlay-styles"))return;let t=document.createElement("style");t.id="mayabot-product-overlay-styles",t.textContent=`
    #mayabot-product-panel {
      position: fixed;
      left: 50%;
      bottom: 96px;
      z-index: 2147483638;
      width: min(calc(100vw - 32px), var(--mayabot-panel-width, 720px));
      max-height: min(72vh, var(--mayabot-panel-max-height, 560px));
      transform: translate(-50%, calc(100% + 32px));
      opacity: 0;
      pointer-events: none;
      display: flex;
      flex-direction: column;
      overflow: hidden;
      border: 1px solid rgba(22, 22, 21, 0.12);
      border-radius: 8px;
      background: rgba(247, 247, 243, 0.97);
      box-shadow: 0 24px 70px rgba(22, 22, 21, 0.18);
      color: #161615;
      font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      transition: transform 0.26s cubic-bezier(0.16, 1, 0.3, 1), opacity 0.2s ease;
    }
    #mayabot-product-panel.active {
      transform: translate(-50%, 0);
      opacity: 1;
      pointer-events: auto;
    }
    #mayabot-product-panel.count-1 { --mayabot-panel-width: 360px; --mayabot-panel-max-height: 470px; }
    #mayabot-product-panel.count-2 { --mayabot-panel-width: 600px; --mayabot-panel-max-height: 500px; }
    #mayabot-product-panel.count-3 { --mayabot-panel-width: 860px; --mayabot-panel-max-height: 520px; }
    #mayabot-product-panel.count-many { --mayabot-panel-width: 980px; --mayabot-panel-max-height: 620px; }
    .mayabot-product-header {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 14px;
      padding: 14px 16px;
      border-bottom: 1px solid rgba(22, 22, 21, 0.1);
    }
    .mayabot-product-title {
      margin: 0;
      color: #161615;
      font-size: 15px;
      font-weight: 800;
      line-height: 1.25;
      letter-spacing: 0;
    }
    .mayabot-product-close {
      display: grid;
      place-items: center;
      width: 34px;
      height: 34px;
      flex: 0 0 auto;
      border: 1px solid rgba(22, 22, 21, 0.14);
      border-radius: 8px;
      background: #ffffff;
      color: #161615;
      cursor: pointer;
      font-size: 20px;
      line-height: 1;
    }
    .mayabot-product-grid {
      display: grid;
      grid-template-columns: repeat(var(--mayabot-card-count, 2), minmax(0, 1fr));
      gap: 12px;
      padding: 14px;
      overflow: auto;
      scrollbar-width: thin;
    }
    .mayabot-product-card {
      display: flex;
      flex-direction: column;
      gap: 9px;
      min-width: 0;
      border: 1px solid rgba(22, 22, 21, 0.1);
      border-radius: 8px;
      background: #ffffff;
      padding: 12px;
    }
    /* Facts flow naturally: the grid is the single scroll area, so there is no
       nested scroll trap. Add/View stay reachable by scrolling the grid. */
    .mayabot-product-facts {
      margin: 0;
      display: grid;
      gap: 6px;
      flex: 0 0 auto;
      min-height: 0;
      font-size: 12px;
      line-height: 1.35;
    }
    .mayabot-fact {
      display: grid;
      grid-template-columns: minmax(64px, 38%) 1fr;
      gap: 8px;
      align-items: start;
      border-top: 1px solid rgba(22, 22, 21, 0.07);
      padding-top: 5px;
    }
    .mayabot-fact:first-child { border-top: 0; padding-top: 0; }
    .mayabot-fact dt {
      margin: 0;
      color: rgba(22, 22, 21, 0.55);
      font-weight: 600;
      overflow-wrap: anywhere;
    }
    .mayabot-fact dd {
      margin: 0;
      color: #161615;
      overflow-wrap: anywhere;
    }
    .mayabot-product-image {
      width: 100%;
      height: clamp(132px, 18vw, 178px);
      object-fit: contain;
      border-radius: 8px;
      background: #f1f2ee;
      padding: 8px;
      mix-blend-mode: multiply;
    }
    .mayabot-product-name {
      margin: 0;
      min-height: 38px;
      color: #161615;
      font-size: 14px;
      font-weight: 760;
      line-height: 1.35;
      display: -webkit-box;
      -webkit-line-clamp: 2;
      -webkit-box-orient: vertical;
      overflow: hidden;
    }
    .mayabot-product-meta {
      margin: 0;
      color: #686660;
      font-size: 13px;
      line-height: 1.35;
      overflow-wrap: anywhere;
    }
    .mayabot-product-actions {
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 8px;
      align-self: stretch;
      margin-top: auto;
      flex: 0 0 auto;
    }
    .mayabot-product-actions button {
      min-height: 36px;
      border: 1px solid rgba(22, 22, 21, 0.12);
      border-radius: 8px;
      background: #161615;
      color: #ffffff;
      cursor: pointer;
      font-size: 12px;
      font-weight: 760;
      line-height: 1;
    }
    .mayabot-product-actions button.secondary {
      background: #ffffff;
      color: #161615;
    }
    .mayabot-product-empty {
      margin: 0;
      padding: 14px;
      color: #686660;
      font-size: 14px;
    }
    /* Speak-choice prompt: asked once per comparison, above the grid so it is
       reachable without scrolling and never overlaps the results. */
    .mayabot-compare-speak {
      display: none;
      align-items: center;
      gap: 10px;
      flex: 0 0 auto;
      padding: 11px 16px;
      border-bottom: 1px solid rgba(22, 22, 21, 0.1);
      background: #fbfbf8;
      font-size: 13px;
      line-height: 1.35;
    }
    #mayabot-product-panel.ask-speak .mayabot-compare-speak { display: flex; }
    .mayabot-compare-speak p { margin: 0; flex: 1 1 auto; overflow-wrap: anywhere; }
    .mayabot-compare-speak button {
      min-height: 32px;
      padding: 0 14px;
      border: 1px solid rgba(22, 22, 21, 0.14);
      border-radius: 8px;
      background: #161615;
      color: #ffffff;
      cursor: pointer;
      font-size: 12px;
      font-weight: 700;
    }
    .mayabot-compare-speak button.secondary { background: #ffffff; color: #161615; }
    @media (max-width: 720px) {
      #mayabot-product-panel {
        bottom: 86px;
        width: min(calc(100vw - 20px), 520px);
      }
      #mayabot-product-panel.count-2,
      #mayabot-product-panel.count-3,
      #mayabot-product-panel.count-many {
        --mayabot-card-count: 2;
      }
      .mayabot-product-grid {
        padding: 12px;
      }
      .mayabot-product-image {
        height: clamp(118px, 32vw, 150px);
      }
    }
    @media (max-width: 430px) {
      #mayabot-product-panel {
        bottom: 82px;
      }
      .mayabot-product-grid {
        grid-template-columns: minmax(0, 1fr);
      }
    }
  `,document.head.appendChild(t)}function _s(){hs();let t=document.getElementById("mayabot-product-panel");return t||(t=document.createElement("div"),t.id="mayabot-product-panel",t.setAttribute("aria-live","polite"),t.setAttribute("role","dialog"),t.setAttribute("tabindex","-1"),t.innerHTML=`
    <div class="mayabot-product-header">
      <h2 class="mayabot-product-title">${$}</h2>
      <button class="mayabot-product-close" type="button" aria-label="Close recommendations">&times;</button>
    </div>
    <div class="mayabot-compare-speak" role="group" aria-label="Speak comparison">
      <p>Would you like me to speak all the comparison points?</p>
      <button type="button" class="mayabot-compare-yes">Yes</button>
      <button type="button" class="mayabot-compare-no secondary">No</button>
    </div>
    <div class="mayabot-product-grid"></div>
  `,t.querySelector(".mayabot-product-close").addEventListener("click",kr),t.querySelector(".mayabot-compare-yes").addEventListener("click",()=>Mr(!0)),t.querySelector(".mayabot-compare-no").addEventListener("click",()=>Mr(!1)),t.addEventListener("keydown",e=>{e.key==="Escape"&&kr()}),document.body.appendChild(t),t)}function kr(){let t=document.getElementById("mayabot-product-panel");t&&(t.classList.remove("active","ask-speak"),ms())}function Mr(t){let e=document.getElementById("mayabot-product-panel");if(e&&e.classList.remove("ask-speak"),Me=!0,t){let n=gs(Xt);n&&ot(n)}}function ys(t,e){let n=document.getElementById("mayabot-product-panel");if(!n)return;if(!(e&&Array.isArray(t)&&t.length>=2)||Me){n.classList.remove("ask-speak");return}n.classList.add("ask-speak"),window.setTimeout(()=>n.querySelector(".mayabot-compare-yes")?.focus(),0)}function gs(t){let e=[];for(let n of(t||[]).slice(0,ds)){let o=(Jt.get(String(n.id))||[]).slice(0,ps).map(a=>`${a.label}: ${a.value}`).join(", "),i=n.name||n.title||"This product";e.push(o?`${i}. ${o}.`:`${i}.`)}return e.join(" ").slice(0,fs)}async function bs(t){let e={action:c.ADD_TO_CART,params:{[p.PRODUCT_ID]:t,[p.QUANTITY]:fe},parameters:{[p.PRODUCT_ID]:t,[p.QUANTITY]:fe}};St()&&await Re(e)||window.dispatchEvent(new CustomEvent(Tt.MAYABOT_ACTION,{detail:e}))}async function Ts(t){try{let n=await Vt(t);if(n){window.location.href=n;return}}catch(n){console.warn("[AI Hub Widget] Product detail URL lookup failed:",n)}let e={action:c.SHOW_PRODUCT_DETAIL,params:{[p.PRODUCT_ID]:t},parameters:{[p.PRODUCT_ID]:t}};St()&&await Re(e)||window.dispatchEvent(new CustomEvent(Tt.MAYABOT_ACTION,{detail:e}))}function As(t){return t<=1?"count-1":t===2?"count-2":t===3?"count-3":"count-many"}function Es(t){return t<=1?1:t===2?2:3}function Ss(t){let e=new Set;return(Array.isArray(t)?t:[]).map(n=>String(n??"").trim()).filter(Boolean).filter(n=>e.has(n)?!1:(e.add(n),!0))}function Ue(t,e,n="",r={}){let o=(Array.isArray(e)?e:[]).map(u=>String(u?.id??"").trim()).filter(Boolean),i=o.length,a=t.length,s=i>0?"succeeded":"failed";return{status:s,stage:"product_overlay",reason:n||(s==="succeeded"?"":"no_matching_products_rendered"),evidence:{requested_product_count:a,rendered_product_count:i,missing_product_count:Math.max(a-i,0),requested_product_ids:t.slice(0,Ur).join(","),rendered_product_ids:o.slice(0,Ur).join(","),lookup_source:r.source||"",search_query:r.searchQuery||""}}}function ws(t){let e=String(t?.displayPrice||"").trim();if(e)return e;let n=Number(t?.price||0);return Number.isFinite(n)&&n>0?n.toLocaleString():"Price unavailable"}var Is=6,Os=24,Rs=120;function Cs(t){let e=new Map;return Array.isArray(t)&&t.forEach(n=>{if(!n||typeof n!="object")return;let r=String(n.product_id||"").trim();if(!r||!Array.isArray(n.facts))return;let o=n.facts.filter(i=>i&&typeof i=="object"&&i.label&&i.value).slice(0,Is).map(i=>({label:String(i.label).slice(0,Os),value:String(i.value).slice(0,Rs)}));o.length&&e.set(r,o)}),e}function xs(t){let e=Jt.get(String(t));return!e||!e.length?"":`<dl class="mayabot-product-facts">${e.map(r=>`<div class="mayabot-fact"><dt>${X(r.label)}</dt><dd>${X(r.value)}</dd></div>`).join("")}</dl>`}function Qt(t,e){let n=_s(),r=n.querySelector(".mayabot-product-grid"),o=n.querySelector(".mayabot-product-title"),i=t.length;if(Xt=Array.isArray(t)?[...t]:[],ke=e||$,n.classList.remove("count-1","count-2","count-3","count-many"),n.classList.add(As(i)),n.style.setProperty("--mayabot-card-count",String(Es(i))),o.textContent=ke,!i){r.innerHTML='<p class="mayabot-product-empty">No matching products are currently available.</p>',n.classList.add("active");return}r.innerHTML=t.map(a=>{let s=X(a.id);return`
        <article class="mayabot-product-card" data-product-id="${s}">
          <img class="mayabot-product-image" src="${X(a.imageUrl||ls)}" alt="${X(a.name)}">
          <h3 class="mayabot-product-name">${X(a.name||a.title||"Product")}</h3>
          <p class="mayabot-product-meta">${X(a.brand)} - ${X(ws(a))}</p>
          ${xs(a.id)}
          <div class="mayabot-product-actions">
            <button type="button" data-add="${s}">Add</button>
            <button type="button" class="secondary" data-view="${s}">View</button>
          </div>
        </article>
      `}).join(""),r.querySelectorAll("[data-add]").forEach(a=>{a.addEventListener("click",async()=>{await bs(a.getAttribute("data-add"))})}),r.querySelectorAll("[data-view]").forEach(a=>{a.addEventListener("click",async()=>{await Ts(a.getAttribute("data-view"))})}),n.classList.add("active"),t.length>0&&Ns()}function Ns(){window.setTimeout(()=>{let t=document.getElementById("mayabot-chat"),e=document.getElementById("mayabot-msgs");e&&(e.innerHTML=""),t&&t.classList.remove("visible")},lt)}async function Hr(t,e=$,n={}){let r=Ss(t),o=String(n.searchQuery||"").trim();Jt=Cs(n.comparisonFacts);let i=Jt.size>0;if(Me=!1,!r.length&&!o)return Qt([],e),Ue([],[],"missing_product_ids");try{let{products:a,source:s,reason:u}=await vr(r,o);return Qt(a,e),ys(a,i),Ue(r,a,u,{source:s,searchQuery:o})}catch(a){return console.warn("[AI Hub Widget] Product overlay failed:",a),Qt([],e),Ue(r,[],"product_overlay_fetch_failed",{searchQuery:o})}}function Br(t={}){if(!Xt.length)return!1;let e=String(t.sort_by||t.sortBy||"price_asc").trim().toLowerCase(),n=[...Xt].sort((r,o)=>vs(r,o,e));return Qt(n,Ls(ke,e)),!0}function vs(t,e,n){return n==="price_desc"?pt(e.price,Number.NEGATIVE_INFINITY)-pt(t.price,Number.NEGATIVE_INFINITY):n==="rating"?pt(e.rating||e.review_rating,Number.NEGATIVE_INFINITY)-pt(t.rating||t.review_rating,Number.NEGATIVE_INFINITY):n==="newest"?Fr(e)-Fr(t):pt(t.price,Number.POSITIVE_INFINITY)-pt(e.price,Number.POSITIVE_INFINITY)}function pt(t,e){let n=String(t??"").replace(/,/g,"").match(/-?\d+(?:\.\d+)?/);if(!n)return e;let r=Number(n[0]);return Number.isFinite(r)?r:e}function Fr(t){let e=t?.updated_at||t?.created_at||t?.date||"",n=Date.parse(String(e||""));return Number.isFinite(n)?n:0}function Ls(t,e){let n={price_asc:"sorted low to high",price_desc:"sorted high to low",rating:"sorted by rating",newest:"newest first"};return`${String(t||$).replace(/\s+-\s+sorted.*$/i,"")} - ${n[e]||n.price_asc}`}function $r(t){return t.action===c.SHOW_PRODUCTS||t.action===c.SHOW_COMPARISON||t.action===c.SHOW_PRODUCT_DETAIL||t.action===c.SORT_PRODUCTS}async function jr(t){return t.action===c.SHOW_COMPARISON?Yr(t.parameters||{},"Product comparison",{syncListing:!1,comparisonFacts:(t.parameters||{}).comparison}):t.action===c.SHOW_PRODUCTS?Yr(t.parameters||{},$):t.action===c.SHOW_PRODUCT_DETAIL?Us(t.parameters||{}):t.action===c.SORT_PRODUCTS?Br(t.parameters||{}):!1}async function Yr(t,e=$,n={}){let r=Array.isArray(t[p.PRODUCT_IDS])?t[p.PRODUCT_IDS]:[],o=Ds(t),a=n.syncListing!==!1?await Ps(o):{succeeded:!1,handled:!1,status:"skipped",stage:"product_display_sync",reason:"comparison_overlay"},s=await Hr(r,t.title||o||e,{searchQuery:o,comparisonFacts:n.comparisonFacts}),u={...s.evidence||{},listing_sync_status:a.status||"",listing_sync_stage:a.stage||"",listing_sync_reason:a.reason||""};return s.status!=="succeeded"?{...s,evidence:u}:o&&a.handled&&!a.succeeded?{status:"failed",stage:"product_display_sync",reason:a.reason||a.status||"listing_sync_failed",evidence:u}:{...s,stage:a.succeeded?"product_display_sync":s.stage,evidence:u}}async function Ps(t){let e=qr(t);return e?wt({action:c.FILTER_PRODUCTS,params:{[p.SEARCH_QUERY]:e,query:e,q:e}}):{succeeded:!1,handled:!1,status:"skipped",stage:"product_display_sync",reason:"missing_search_query"}}function Ds(t){return qr(t[p.SEARCH_QUERY]||t.search||t.query||t.q||"")}function qr(t){return String(t||"").trim()}async function Us(t){let e="";try{e=await Vt(t[p.PRODUCT_ID])}catch(n){return console.warn("[AI Hub Widget] Product detail URL lookup failed:",n),!1}return e?(window.location.href=e,!0):!1}var Fe="stop_action_fallback",ks=new Set([c.SHOW_PRODUCTS,c.SHOW_COMPARISON,c.SHOW_PRODUCT_DETAIL,c.SORT_PRODUCTS]);function Vr(t){return St()&&!ks.has(t.action)}async function zr(t){let e=await wt(t);return e.succeeded?!0:e.blocked||e.disabled?Fe:!1}function Wr(t){return window.dispatchEvent(new CustomEvent(Tt.MAYABOT_ACTION,{detail:t})),{status:"requested",stage:"browser_event",reason:"event_dispatched_without_confirmation"}}var Ms=12,Fs=8,Hs=80,Gr=Object.freeze([["data-entity-id",""],["data-product-id","product"],["data-listing-id","listing"],["data-offer-id","offer"],["data-plan-id","plan"],["data-item-id",""]]),Bs="data-entity-type",Ys="entity",Kr=Object.freeze(["sort","sort_by","sortby","orderby","order_by","order"]),$s=Object.freeze(["page","p","offset","cursor","q","query","search","token","session","email","phone","name","address","utm_source","utm_medium","utm_campaign"]),js=Object.freeze([["price","[data-price], [itemprop='price'], .price"],["rating","[data-rating], [itemprop='ratingValue'], .rating"],["availability","[data-availability], [itemprop='availability'], .availability, .stock"]]);function H(t){return String(t||"").replace(/\s+/g," ").trim().slice(0,Hs)}function qs(t){if(!t||typeof t.getBoundingClientRect!="function")return!1;let e=t.getBoundingClientRect();if(e.width<=0||e.height<=0)return!1;let n=t.ownerDocument?.defaultView,r=n?.getComputedStyle?.(t);if(r&&(r.visibility==="hidden"||r.display==="none"))return!1;let o=t.ownerDocument?.documentElement,i=Number(n?.innerWidth||o?.clientWidth||0),a=Number(n?.innerHeight||o?.clientHeight||0);return i>0&&a>0&&e.bottom>0&&e.right>0&&e.top<a&&e.left<i}function Vs(t){for(let[e,n]of Gr){let r=H(t.getAttribute(e));if(r)return{id:r,impliedType:n}}return null}function zs(t,e){return H(t.getAttribute(Bs)).toLowerCase()||e||Ys}function Ws(t){let e=t.querySelector?.("h1, h2, h3, h4, [data-entity-name], [itemprop='name']");return H(e?.textContent||t.getAttribute("aria-label")||t.getAttribute("title"))}function Gs(t){let e=t.matches?.("a[href]")?t:t.querySelector?.("a[href]");return ec(e?.href||"")}function Ks(t){let e={};for(let[n,r]of js){let o=t.querySelector?.(r);if(!o)continue;let i=H(o.getAttribute?.("content")||o.getAttribute?.(`data-${n}`)||o.textContent);i&&(e[n]=i)}return e}function Qs(){return Gr.map(([t])=>`[${t}]`).join(",")}function Xs(){let t=new Set,e=[];for(let n of x(Qs())){if(e.length>=Ms)break;let r=Vs(n);!r||t.has(r.id)||!qs(n)||(t.add(r.id),e.push({id:r.id,entity_type:zs(n,r.impliedType),label:Ws(n),route:Gs(n),facts:Ks(n)}))}return e}function Js(){let t=Qr();if(!t)return{};let e={};for(let[n,r]of t.entries()){let o=n.toLowerCase();if(!($s.includes(o)||Kr.includes(o))){if(Object.keys(e).length>=Fs)break;e[H(n)]=H(r)}}return e}function Zs(){let t=Qr();for(let n of Kr){let r=H(t?.get?.(n));if(r)return r}let e=x("select[name*='sort' i], select[id*='sort' i]")[0];return H(e?.value)}function tc(){try{return{path:H(window.location.pathname)||"/",search:H(window.location.search)}}catch{return{path:"",search:""}}}function Zt(){return{route:tc(),filters:Js(),sort:Zs(),visible_entities:Xs()}}function Qr(){try{return new URLSearchParams(window.location.search)}catch{return null}}function ec(t){if(!t)return"";try{let e=new URL(t,window.location.origin);return e.origin!==window.location.origin?"":`${e.pathname}${e.search}`||"/"}catch{return""}}var Ml=Object.freeze(["CHECKOUT","CLEAR_CART","REMOVE_FROM_CART","UPDATE_CART_QUANTITY","CLEAR_HISTORY","SUBMIT_PAYMENT","PLACE_ORDER"]);var T=Object.freeze({DISPLAY:"display",NAVIGATION:"navigation",DETAIL:"detail",FILTER:"filter",SORT:"sort",CART:"cart",NONE:"none"}),nc=1200,rc=60,oc=Object.freeze({SHOW_PRODUCTS:T.DISPLAY,SHOW_ENTITIES:T.DISPLAY,SHOW_COMPARISON:T.DISPLAY,COMPARE_ENTITIES:T.DISPLAY,NAVIGATE_TO:T.NAVIGATION,SHOW_PRODUCT_DETAIL:T.DETAIL,OPEN_ENTITY_DETAIL:T.DETAIL,FILTER_PRODUCTS:T.FILTER,CLEAR_FILTERS:T.FILTER,SORT_PRODUCTS:T.SORT,SORT_ENTITIES:T.SORT,ADD_TO_CART:T.CART,REMOVE_FROM_CART:T.CART,UPDATE_CART_QUANTITY:T.CART,CLEAR_CART:T.CART}),ic="[data-cart-count], [data-testid='cart-count'], .cart-count, #cart-count";function Jr(t){return oc[String(t||"").toUpperCase()]||T.NONE}function Ye(){let t=Zt();return{path:t.route.path,search:t.route.search,filters:t.filters,sort:String(t.sort||"").toLowerCase(),visibleIds:t.visible_entities.map(e=>String(e.id)),cartCount:ac()}}function ac(){let t=document.querySelector(ic);if(!t)return null;let e=t.getAttribute("data-cart-count")??t.textContent,n=Number.parseInt(String(e||"").replace(/[^\d-]/g,""),10);return Number.isFinite(n)?n:null}function Zr(t){let e=[];for(let n of["product_ids","entity_ids"])Array.isArray(t[n])&&e.push(...t[n].map(String));for(let n of["product_id","entity_id"])t[n]&&e.push(String(t[n]));return e}function Ot(t){let e=String(t||"").split("?")[0].split("#")[0];return e.length>1?e.replace(/\/+$/,""):e}function He(t){return String(t||"").trim().toLowerCase().replace(/[^a-z0-9/_\s-]+/g," ").replace(/[_-]+/g," ").replace(/\s+/g," ").trim().replace(/\s+/g,"-")}function Xr(t){let e=String(t||"").trim();if(!e||/^(?:javascript:|data:|\/\/)/i.test(e))return"";try{let n=new URL(e,window.location.origin);return n.origin!==window.location.origin?"":Ot(n.pathname||"/")}catch{return""}}function sc(t){let e=String(t||"").trim();if(!e)return"";if(e==="/"||He(e)==="home")return"/";let n=window.AIHubAdapterRuntime?.config?.adapter?.routes||window.AIHubAdapter?.config?.adapter?.routes||{},r=He(e);for(let[o,i]of Object.entries(n)){if(He(o)!==r)continue;let a=Xr(i);if(a)return a}return e.startsWith("/")||/^https?:\/\//i.test(e)?Xr(e):Ot(`/${r}`)}function cc(t,e){let n=Zr(t);return n.length?n.filter(o=>!e.visibleIds.includes(o)).length?{satisfied:!1,reason:"requested_records_not_visible"}:{satisfied:!0,reason:""}:e.visibleIds.length>0?{satisfied:!0,reason:""}:{satisfied:!1,reason:"nothing_visible"}}function uc(t,e,n){let r=sc(t.page),o=Ot(e.path);return r&&o===r?{satisfied:!0,reason:""}:!r&&o!==Ot(n.path)?{satisfied:!0,reason:""}:r&&o!==Ot(n.path)?{satisfied:!1,reason:"wrong_route"}:{satisfied:!1,reason:"route_unchanged"}}function lc(t,e,n){let r=Zr(t)[0];return r?`${e.path}${e.search}`.includes(r)?{satisfied:!0,reason:""}:e.visibleIds.includes(r)&&e.path!==n.path?{satisfied:!0,reason:""}:{satisfied:!1,reason:"record_not_opened"}:{satisfied:!1,reason:"no_record_requested"}}function dc(t,e,n){if(t==="CLEAR_FILTERS")return Object.keys(n.filters).length===0?{satisfied:!0,reason:""}:{satisfied:!1,reason:"filters_still_active"};let r=new Map(Object.entries(n.filters).map(([u,f])=>[u.toLowerCase(),Be(f)])),o=e.filters&&typeof e.filters=="object"?e.filters:e,i=new Set(["product_ids","entity_ids","page","search_query","query","q","request_id"]),a=Object.entries(o||{}).filter(([u,f])=>!i.has(u.toLowerCase())&&Be(f));return a.length?a.every(([u,f])=>{let A=r.get(u.toLowerCase());return A!==void 0&&A===Be(f)})?{satisfied:!0,reason:""}:{satisfied:!1,reason:"filter_value_mismatch"}:r.size>0?{satisfied:!0,reason:""}:{satisfied:!1,reason:"no_filter_observed"}}function Be(t){return(Array.isArray(t)?t:[t]).map(n=>String(n??"").trim().toLowerCase()).filter(Boolean).sort().join(",")}function pc(t,e,n){let r=String(t.sort_by||"").toLowerCase();return r&&e.sort&&e.sort.includes(r.split("_")[0])?{satisfied:!0,reason:""}:e.visibleIds.join(",")!==n.visibleIds.join(",")?{satisfied:!0,reason:""}:{satisfied:!1,reason:"order_unchanged"}}function fc(t,e,n){if(n.cartCount===null||e.cartCount===null)return{satisfied:!1,reason:"cart_state_unobservable"};let r=e.cartCount>n.cartCount,o=e.cartCount<n.cartCount;return t==="ADD_TO_CART"?r?{satisfied:!0,reason:""}:{satisfied:!1,reason:"cart_unchanged"}:t==="REMOVE_FROM_CART"?o?{satisfied:!0,reason:""}:{satisfied:!1,reason:"cart_unchanged"}:t==="CLEAR_CART"?e.cartCount===0?{satisfied:!0,reason:""}:{satisfied:!1,reason:"cart_not_empty"}:e.cartCount!==n.cartCount?{satisfied:!0,reason:""}:{satisfied:!1,reason:"cart_unchanged"}}function mc(t,e,n){let r=String(t?.action||"").toUpperCase(),o=t?.parameters||t?.params||{},i=Jr(r);return i===T.DISPLAY?cc(o,e):i===T.NAVIGATION?uc(o,e,n):i===T.DETAIL?lc(o,e,n):i===T.FILTER?dc(r,o,e):i===T.SORT?pc(o,e,n):i===T.CART?fc(r,e,n):{satisfied:!0,reason:"no_postcondition"}}async function to(t,e){let n=Jr(t?.action);if(n===T.NONE)return{family:n,verified:!0,reason:"no_postcondition"};let r=Date.now()+nc,o={satisfied:!1,reason:"not_observed"};for(;Date.now()<r&&(o=mc(t,Ye(),e),!o.satisfied);)await hc(rc);return{family:n,verified:o.satisfied,reason:o.reason}}function hc(t){return new Promise(e=>window.setTimeout(e,t))}var _=Object.freeze({searchForm:"search-form",searchInput:"search-input",searchSubmit:"search-submit",searchResults:"search-results",addToCart:"add-to-cart",cartButton:"cart-button",cartLineItem:"cart-line-item",navLink:"nav-link",productCard:"product-card",productLink:"product-link",productName:"product-name",productDetail:"product-detail",productTitle:"product-title"}),$e="data-aihub-nav",eo="data-entity-name",J=4e3,no=1500,_c=80,yc='[id^="mayabot"], [data-aihub-widget]';function ft(t){return!!t&&!t.closest?.(yc)}var mt=t=>`[data-aihub-role="${t}"]`,at=t=>x(mt(t)).filter(ft),w=t=>at(t)[0]||null;function gc(t){let e=g(t);return e&&x(`[data-product-id="${je(e)}"]`).find(ft)||null}function g(t){return String(t??"").trim()}function je(t){return window.CSS?.escape?window.CSS.escape(t):g(t).replace(/["\\]/g,"\\$&")}async function V(t,e){let n=Date.now()+e;for(;;){let r=t();if(r)return r;if(Date.now()>=n)return null;await new Promise(o=>window.setTimeout(o,_c))}}function z(){return!!(w(_.searchForm)||w(_.searchInput)||w(_.searchSubmit))}function Rt(){return!!w(_.addToCart)}function Ct(){return at(_.navLink).length>0}function st(){return Ve().length>0}function W(t){let e=String(t||"").split("?")[0].split("#")[0];return e.length>1?e.replace(/\/+$/,""):e||"/"}function qe(t){try{let e=new URL(String(t||""),window.location.origin);return e.origin!==window.location.origin?"":`${e.pathname}${e.search}`||"/"}catch{return""}}function xt(t){return g(t).toLowerCase().replace(/[^a-z0-9]+/g," ").trim()}function it(t){return g(t).toLowerCase().replace(/[\s\-_/\\,.:;|]+/g," ").replace(/\s+/g," ").trim()}function Ve(){let t=at(_.productCard);return t.length?t:x("[data-product-id]").filter(ft)}function te(t){let e=g(t?.getAttribute?.(eo));return e||g(t?.querySelector?.(mt(_.productName))?.textContent)}var ze="product_id",bc="product_name";function ee(t,e){let n=gc(t);if(n)return{card:n,matchedBy:ze};let r=it(e);if(!r)return null;let o=Ve().filter(i=>it(te(i))===r);return o.length===1?{card:o[0],matchedBy:bc}:o.length>1?{ambiguous:!0,matchCount:o.length}:null}function ct(t,e,n=""){return{handled:!0,status:"succeeded",self_verified:!0,stage:t,reason:n,evidence:e||{}}}function E(t,e,n){return{handled:!0,status:"failed",stage:t,reason:e,evidence:n||{}}}function ro(t,e,n){return{handled:!0,status:"unconfirmed",stage:t,reason:e,evidence:n||{}}}function oo(t,e){return{handled:!0,status:"unsupported_host",stage:t,reason:e,evidence:{}}}function Z(t){return t?(uo(t),io(t,"down"),io(t,"up"),typeof t.click=="function"?t.click():lo(t,"click"),Sc(t),!0):!1}function so(t,e){return t?(uo(t),Tc(t,re(e)),Ac(t),!0):!1}function co(t){if(!t)return!1;let e=re(t.tagName).toLowerCase()==="form"?t:t.closest?.("form");return e&&typeof e.requestSubmit=="function"?(e.requestSubmit(),!0):Z(t)}function uo(t){try{t.scrollIntoView?.({behavior:"smooth",block:"center",inline:"center"})}catch{}typeof t.focus=="function"&&t.focus({preventScroll:!0})}function Tc(t,e){if(wc(t)){t.textContent=e;return}let n=Object.getPrototypeOf(t),r=Object.getOwnPropertyDescriptor(n,"value");if(r?.set){r.set.call(t,e);return}t.value=e}function Ac(t){ao(t,"beforeinput"),ao(t,"input"),t.dispatchEvent(new Event("change",{bubbles:!0}))}function io(t,e){Ec(t,`pointer${e}`),lo(t,`mouse${e}`)}function Ec(t,e){typeof PointerEvent=="function"&&t.dispatchEvent(new PointerEvent(e,{bubbles:!0,cancelable:!0,pointerType:"mouse",isPrimary:!0}))}function lo(t,e){t.dispatchEvent(new MouseEvent(e,{bubbles:!0,cancelable:!0,view:window}))}function ao(t,e){if(typeof InputEvent=="function"){t.dispatchEvent(new InputEvent(e,{bubbles:!0,cancelable:!0,inputType:"insertText"}));return}t.dispatchEvent(new Event(e,{bubbles:!0,cancelable:!0}))}function Sc(t){let e=re(t.getAttribute?.("role")).toLowerCase();["button","link","menuitem","option","tab"].includes(e)&&(ne(t,"keydown","Enter"),ne(t,"keyup","Enter"),(e==="button"||e==="tab")&&(ne(t,"keydown"," "),ne(t,"keyup"," ")))}function ne(t,e,n){t.dispatchEvent(new KeyboardEvent(e,{bubbles:!0,cancelable:!0,key:n}))}function wc(t){let e=re(t?.getAttribute?.("role")).toLowerCase();return!!(t?.isContentEditable||!("value"in t)&&["searchbox","textbox"].includes(e))}function re(t){return String(t||"").trim()}function Ic(t){try{let e=`${window.location.pathname}${window.location.search}`.toLowerCase();return e.includes(encodeURIComponent(t).toLowerCase())||e.includes(t.toLowerCase())}catch{return!1}}var Oc=1;function Rc(t){let e=g(t).split(/\s+/).filter(n=>n.length>2);return e.length<2?"":e.reduce((n,r)=>r.length>n.length?r:n,"")}async function Nt(t,{broadenIfSparse:e=!1}={}){let n=g(t);if(!z())return null;if(!n)return oo("host_search","empty_query");let r=await po(n);if(!e||!r||r.status!=="succeeded")return r;let o=r.evidence?.result_count;if(typeof o!="number"||o>Oc)return r;let i=Rc(n);if(!i||i===n)return r;let a=await po(i);return a?.status==="succeeded"&&(a.evidence?.result_count||0)>o?{...a,evidence:{...a.evidence,broadened_from:n}}:r}async function po(t){let e=w(_.searchInput);if(!e){let s=w(_.searchSubmit)||w(_.searchForm);s&&Z(s),e=await V(()=>w(_.searchInput),no)}if(!e)return E("host_search","search_input_unavailable");so(e,t);let n=e.closest?.("form")||w(_.searchForm);co(n||w(_.searchSubmit)||e);let r=await V(()=>{let s=w(_.searchResults);return!s||s.getAttribute("data-results-loading")==="true"?null:s},J);if(!r)return ro("host_search","results_not_settled");let o=Number(r.getAttribute("data-result-count")),i={result_count:Number.isFinite(o)?o:null,query:r.getAttribute("data-query")||"",route:`${window.location.pathname}${window.location.search}`,route_reflects_query:Ic(t)};return i.route_reflects_query||i.query.toLowerCase().includes(t.toLowerCase())?r.getAttribute("data-results-empty")==="true"||i.result_count===0?E("host_search","no_results",i):ct("host_search",i):E("host_search","query_not_reflected",i)}var vt="host_add_to_cart",Lt="host_product_detail";function We(){let t=w(_.cartButton)||x("[data-cart-count]").find(ft)||null;if(!t)return null;let e=Number(t.getAttribute("data-cart-count"));return Number.isFinite(e)?e:null}function Ge(){return at(_.cartLineItem).map(t=>g(t.getAttribute("data-product-id"))).filter(Boolean)}function Cc(t){return!!t.disabled||t.getAttribute("aria-disabled")==="true"}async function fo(t,e,n){let r=ee(e,n);if(!r&&n&&z()){let o=await Nt(n);o&&o.status==="succeeded"&&(r=ee(e,n))}return r?r.ambiguous?{error:E(t,"ambiguous_product",{product_name:g(n),match_count:r.matchCount})}:r:{error:E(t,"product_not_on_page",{product_id:g(e),product_name:g(n)})}}function xc(t,e){let n=g(e);if(n){let r=x(`${mt(_.addToCart)}[data-product-id="${je(n)}"]`).find(ft);if(r)return r}return t?.querySelector?.(mt(_.addToCart))||null}async function Ke(t){if(!Rt()&&!st())return null;let e=g(t?.product_id||t?.entity_id),n=g(t?.product_name),r=await fo(vt,e,n);if(r.error)return r.error;let o=g(r.card.getAttribute("data-product-id"))||e,i=xc(r.card,r.matchedBy===ze?e:o);if(!i)return E(vt,"add_control_missing",{product_id:o,product_name:n});if(Cc(i))return E(vt,"add_control_disabled",{product_id:o,product_name:n});let a=We(),s=Ge();Z(i);let u=await V(()=>{let A=We(),v=Ge(),R=a!=null&&A!=null&&A>a,b=o&&v.includes(o)&&!s.includes(o),C=v.length>s.length;return R||b||C?{afterCount:A,lines:v}:null},J),f={cart_before:a,cart_after:We(),product_id:o,product_name:n,matched_by:r.matchedBy};return u?ct(vt,{...f,line_item_present:o?Ge().includes(o):!0}):E(vt,"cart_unchanged",f)}function Nc(t){return t?.querySelector?.(mt(_.productLink))||t?.querySelector?.("a[href]")||null}function vc(t,e){let n=w(_.productDetail),r=it(e);if(n){let i=g(n.getAttribute("data-product-id"));if(t&&i&&i===t)return"product_id";let a=it(te(n));if(r&&a&&a===r)return"product_name"}let o=w(_.productTitle);return o&&r&&it(o.textContent)===r?"product_title":""}async function Qe(t){if(!st()&&!z())return null;let e=g(t?.product_id||t?.entity_id),n=g(t?.product_name),r=await fo(Lt,e,n);if(r.error)return r.error;let o=g(r.card.getAttribute("data-product-id"))||e,i=Nc(r.card);if(!i)return E(Lt,"product_link_missing",{product_id:o,product_name:n});let a=W(window.location.pathname);Z(i);let s=await V(()=>vc(o,n)||null,J),u={product_id:o,product_name:n,matched_by:r.matchedBy,route:`${window.location.pathname}${window.location.search}`,verified_by:s||""};return s?ct(Lt,u):W(window.location.pathname)===a?E(Lt,"route_unchanged",u):E(Lt,"product_page_not_confirmed",u)}var Pt="host_navigate",Lc="main, [data-aihub-role='search-results'], [data-product-id]";function Pc(t){let e=xt(t);if(!e)return null;let n=at(_.navLink),r=s=>[xt(s.getAttribute($e)),xt(s.textContent),xt(qe(s.getAttribute("href")||s.href))].filter(Boolean),o=n.find(s=>r(s).includes(e));if(o)return o;let i=null,a=0;for(let s of n)for(let u of r(s))!e.includes(u)&&!u.includes(e)||u.length>a&&(a=u.length,i=s);return i}function Dc(t){try{return new URL(String(t||""),window.location.origin).searchParams}catch{return new URLSearchParams}}function Uc(t){if(W(window.location.pathname)!==W(t))return!1;let e=new URLSearchParams(window.location.search);for(let[n,r]of Dc(t).entries())if(e.get(n)!==r)return!1;return!0}async function Xe(t){if(!Ct())return null;let e=Pc(t);if(!e)return E(Pt,"no_matching_nav_target",{target:g(t)});let n=qe(e.getAttribute("href")||e.href),r=W(window.location.pathname);Z(e);let o=await V(()=>n&&Uc(n)?!0:null,J),i=W(window.location.pathname),a={target:g(t),expected:W(n),route:`${window.location.pathname}${window.location.search}`};return o?await V(()=>document.querySelector(Lc)?!0:null,J)?ct(Pt,a):E(Pt,"page_not_ready",a):i!==r?E(Pt,"wrong_route",{...a,actual:i}):E(Pt,"route_unchanged",{...a,actual:i})}var ho=new Set([c.FILTER_PRODUCTS,c.SHOW_PRODUCTS]),_o=new Set([c.SHOW_PRODUCT_DETAIL]);function oe(t){return t.parameters||t.params||{}}function yo(t){let e=oe(t);return String(e[p.SEARCH_QUERY]||e.search||e.query||e.q||"").trim()}function go(t){let e=oe(t);return String(e[p.PAGE]||e.page||e.target||"").trim()}function mo(t){let e=oe(t);return!!(e[p.PRODUCT_ID]||e.entity_id||String(e[p.PRODUCT_NAME]||"").trim())}function bo(t){let e=t.action;return e===c.ADD_TO_CART?(Rt()||st())&&mo(t):_o.has(e)?(st()||z())&&mo(t):ho.has(e)?z()&&!!yo(t):e===c.NAVIGATE_TO?Ct()&&!!go(t):!1}async function To(t){let e=t.action,n=oe(t);if(e===c.ADD_TO_CART)return Ke(n);if(_o.has(e))return Qe(n);if(ho.has(e)){let r=yo(t);return r?Nt(r,{broadenIfSparse:!0}):null}if(e===c.NAVIGATE_TO){let r=go(t);return r?Xe(r):null}return null}var kc=Object.freeze([{name:"host_contract",canExecute:bo,execute:To},{name:"runtime_adapter",canExecute:Vr,execute:zr},{name:"product_overlay",canExecute:$r,execute:jr},{name:"entity_overlay",canExecute:cr,execute:ur},{name:"handoff_overlay",canExecute:_r,execute:yr},{name:"platform_adapter",canExecute:()=>!0,execute:kn},{name:"provider_adapter",canExecute:Wn,execute:Gn},{name:"navigation",canExecute:br,execute:Tr},{name:"browser_event",canExecute:()=>!0,execute:Wr}]);async function Ze(t){let e=[];for(let n of t||[]){let r=Sr(n),o=await Mc(r);o&&e.push(o)}return e}async function Mc(t){if(!t.action)return;let e=Date.now(),n=window.location.href,r=Ye();await Ft(d.apiUrl,d.siteId,t,{status:"requested",stage:"widget_dispatch",requested_url:n,final_url:n,evidence:Je(t,n,n)}),await Ft(d.apiUrl,d.siteId,t,{status:"executing",stage:"widget_dispatch",requested_url:n,final_url:window.location.href,evidence:Je(t,n,window.location.href)});let o;try{o=await Fc(t)}catch(u){o={status:"failed",stage:"widget_dispatch",reason:u instanceof Error?u.message:"execution_error"}}let i=o.status==="succeeded"&&o.self_verified?{family:o.stage||"host_contract",verified:!0,reason:o.reason||""}:o.status==="succeeded"?await to(t,r):{family:"none",verified:!1,reason:o.reason||"execution_failed"},a=window.location.href,s={...Je(t,n,a,o),postcondition_family:i.family,postcondition_verified:i.verified,postcondition_reason:i.reason};return await Ft(d.apiUrl,d.siteId,t,{status:o.status,stage:o.stage,reason:o.reason,duration_ms:Date.now()-e,requested_url:n,final_url:a,evidence:s}),{action:t.action,request_id:t.request_id||t.action_request_id||"",turn_id:t.turn_id||"",sequence:Number(t.sequence||0),status:o.status,stage:o.stage,reason:o.reason,verified:i.verified,postcondition:i.family,requested_url:n,final_url:a,evidence:s}}async function Fc(t){if(!t.action)return{status:"failed",stage:"normalization",reason:"missing_action"};for(let e of kc){if(!e.canExecute(t))continue;let n=await e.execute(t),r=Hc(n,e.name);if(r)return r}return{status:"failed",stage:"all",reason:"no_executor_succeeded"}}function Hc(t,e){if(t===!0)return{status:"succeeded",stage:e,reason:""};if(t===Fe)return{status:"blocked",stage:e,reason:"action_blocked"};if(!t||typeof t!="object")return null;let n=String(t.status||"").trim().toLowerCase();return n?{status:n,stage:String(t.stage||e).trim()||e,reason:String(t.reason||"").trim(),self_verified:!!t.self_verified,evidence:t.evidence&&typeof t.evidence=="object"?t.evidence:{}}:null}function Je(t,e,n,r={}){let o=t.parameters||t.params||{},i={requested_url:e,final_url:n,url_changed:e!==n,path_changed:Ao(e)!==Ao(n),title:document.title||"",stage:r.stage||"",result_status:r.status||""};return o.page&&(i.target_page=o.page),o.product_id&&(i.product_id=o.product_id),o.entity_id&&(i.entity_id=o.entity_id),Array.isArray(o.product_ids)&&(i.product_count=o.product_ids.length),Array.isArray(o.entity_ids)&&(i.entity_count=o.entity_ids.length),{...i,...r.evidence&&typeof r.evidence=="object"?r.evidence:{}}}function Ao(t){try{return new URL(t,window.location.href).pathname}catch{return""}}var m=Object.freeze({CANCELLED:"cancelled",NETWORK:"network",TIMEOUT:"timeout",ACCESS_DENIED:"access_denied",INVALID_REQUEST:"invalid_request",PAYLOAD_TOO_LARGE:"payload_too_large",UNSUPPORTED_MEDIA:"unsupported_media",RATE_LIMITED:"rate_limited",PROVIDER_UNAVAILABLE:"provider_unavailable",SERVER_ERROR:"server_error",MICROPHONE:"microphone",UNKNOWN:"unknown"}),Eo=Object.freeze({[m.CANCELLED]:"Stopped",[m.NETWORK]:"Connection issue",[m.TIMEOUT]:"Timed out",[m.ACCESS_DENIED]:"Access denied",[m.INVALID_REQUEST]:"Try again",[m.PAYLOAD_TOO_LARGE]:"Recording too long",[m.UNSUPPORTED_MEDIA]:"Audio not supported",[m.RATE_LIMITED]:"Service busy",[m.PROVIDER_UNAVAILABLE]:"Service unavailable",[m.SERVER_ERROR]:"Service error",[m.MICROPHONE]:"Mic unavailable",[m.UNKNOWN]:"Try again"}),So=64,O=class extends Error{constructor(e,{status:n=0,code:r="",requestId:o="",stage:i=""}={}){super(`voice_transport_${e}`),this.name="VoiceTransportError",this.category=e,this.status=Number(n)||0,this.code=String(r||"").slice(0,So),this.requestId=String(o||"").slice(0,So),this.stage=i}get customerMessage(){return Bc(this.category)}toDiagnostics(){return{category:this.category,status:this.status,code:this.code,request_id:this.requestId,stage:this.stage}}};function Bc(t){return Eo[t]||Eo[m.UNKNOWN]}function wo(t){return t instanceof O&&t.category===m.CANCELLED}function Yc(t){let e=Number(t)||0;return e===401||e===403?m.ACCESS_DENIED:e===408?m.TIMEOUT:e===413?m.PAYLOAD_TOO_LARGE:e===415?m.UNSUPPORTED_MEDIA:e===429?m.RATE_LIMITED:e===502||e===503||e===504?m.PROVIDER_UNAVAILABLE:e>=500?m.SERVER_ERROR:e>=400?m.INVALID_REQUEST:m.UNKNOWN}function Dt(t){if(t instanceof O)return t;let e=String(t?.message||t||"").toLowerCase();return t?.name==="AbortError"||e.includes("abort")||e.includes("timeout")||e.includes("timed out")?new O(m.TIMEOUT):e.includes("microphone")||e.includes("permission")||e.includes("notallowed")?new O(m.MICROPHONE):t?.name==="TypeError"||e.includes("failed to fetch")||e.includes("network")||e.includes("load failed")?new O(m.NETWORK):new O(m.UNKNOWN)}function Io(t,e=null){let n=Number(t?.status)||0,r=t?.headers?.get?.("x-request-id")||t?.headers?.get?.("x-correlation-id")||"",o=e&&typeof e=="object"&&(e.code||e.error_code)||"",i=/^[A-Za-z0-9_.:-]{1,64}$/.test(String(o||""))?String(o):"";return new O(Yc(n),{status:n,code:i,requestId:r,stage:"http_response"})}var $c="/v1/widget/runtime-event",jc=16;function N(t={}){let e=JSON.stringify({client_id:d.siteId,site_id:d.siteId,origin:window.location.origin,occurred_at:new Date().toISOString(),session_id:d.sessionId,turn_id:B(t.turn_id,80),request_id:B(t.request_id,80),component:B(t.component||"voice",60),stage:B(t.stage,80),event_type:B(t.event_type||"runtime_event",80),severity:B(t.severity||"info",20),status:B(t.status||"ok",20),message_code:B(t.message_code,80),duration_ms:Oo(t.duration_ms),metadata:qc(t.metadata)}),n=new URL($c,d.apiUrl).toString();fetch(n,{method:"POST",headers:{Accept:"application/json","Content-Type":"application/json"},body:e,keepalive:!0}).catch(()=>{})}function qc(t){if(!t||typeof t!="object"||Array.isArray(t))return{};let e={};for(let[n,r]of Object.entries(t).slice(0,jc)){let o=B(n,60).toLowerCase();!o||Vc(o)||(typeof r=="boolean"||r===null?e[o]=r:typeof r=="number"?e[o]=Oo(r):typeof r=="string"&&(e[o]=B(r,120)))}return e}function Vc(t){return["audio","transcript","response","error","exception","token","secret"].some(e=>t.includes(e))}function B(t,e){return String(t||"").replace(/\s+/g," ").trim().slice(0,e)}function Oo(t){let e=Number(t||0);return Number.isFinite(e)?Math.max(0,e):0}var zc=3,Wc="AIHubAdapterRuntime",Gc="AIHubAdapter";function Kc(t,e){let n=new URL(U.SHOP_WS,t);return n.protocol=n.protocol==="https:"?"wss:":"ws:",n.searchParams.set("site_id",e),n.searchParams.set("session_id",d.sessionId),n.toString()}function Qc(t){return new Promise((e,n)=>{let r=new FileReader;r.onloadend=()=>{let o=String(r.result||"");e(o.includes(",")?o.split(",").pop():o)},r.onerror=()=>n(r.error||new Error("Failed to read audio blob")),r.readAsDataURL(t)})}var tn=class{constructor(){this.queue=[],this.blocked=[],this.playing=!1,this.current=null,this.lastPlaybackStartMs=0,this.installUnlockListeners()}push(e,n=""){e&&(this.queue.push({audioB64:e,fallbackText:n}),this.playNext())}playNext(){if(this.playing||this.queue.length===0)return;this.playing=!0;let e=this.queue.shift(),n=new Audio(bt.DATA_WAV_PREFIX+e.audioB64);n.preload="auto",this.current=n,n.onplay=()=>{this.lastPlaybackStartMs=typeof performance<"u"?performance.now():0},n.onended=()=>{this.current=null,this.playing=!1,this.playNext()},n.onerror=()=>{this.current=null,e.fallbackText&&tt(e.fallbackText),this.playing=!1,this.playNext()},n.play().catch(r=>{if(console.warn("Audio playback failed",r),this.current=null,this.isAutoplayBlocked(r)){e.fallbackText?tt(e.fallbackText):this.blocked.unshift(e),this.playing=!1;return}e.fallbackText&&tt(e.fallbackText),this.playing=!1,this.playNext()})}installUnlockListeners(){if(typeof window>"u")return;let e=()=>{this.retryBlocked(),Gt()};window.addEventListener("pointerdown",e,{capture:!0,passive:!0}),window.addEventListener("keydown",e,{capture:!0}),window.addEventListener("touchstart",e,{capture:!0,passive:!0})}retryBlocked(){this.blocked.length&&(this.queue.unshift(...this.blocked.splice(0)),this.playNext())}speakInsteadOfBlocked(e){!e||!this.blocked.length||(this.blocked=[],tt(e))}isAutoplayBlocked(e){let n=`${e?.name||""} ${e?.message||e||""}`.toLowerCase();return n.includes("notallowed")||n.includes("user didn't interact")||n.includes("not allowed")}stop(){if(this.queue=[],this.blocked=[],this.current){try{this.current.pause(),this.current.currentTime=0}catch{}this.current.onended=null,this.current.onerror=null,this.current=null}this.playing=!1,Kt()}isSpeaking(){return this.playing||this.queue.length>0||Dr()}},ie=new tn;function ae(){ie.stop()}function rn(){return ie.isSpeaking()}function on(t="reset"){xo.reset(t),Co.reset(t)}var en=class{constructor(){this.inFlight=null,this.cancelled=!1}reset(e="reset"){this.cancelled=e==="user_cancel";try{this.inFlight?.abort()}catch{}this.inFlight=null}async sendAudio(e,n,r=[]){let o=G();N({event_type:"voice_turn_started",stage:"http_request",status:"started",metadata:{transport:"http",audio_type:e?.type||"unknown"}});let i=new FormData;i.append("audio",e,Zc(e)),i.append("site_id",d.siteId),i.append("session_id",d.sessionId),r&&r.length>0&&i.append("conversation_history",JSON.stringify(r));let a=Po();a&&i.append("page_context",JSON.stringify(a));let s,u=typeof AbortController=="function"?new AbortController:null;this.inFlight=u,this.cancelled=!1;try{s=await fetch(`${d.apiUrl}${U.SHOP}`,{method:On.POST,body:i,signal:u?.signal})}catch(I){throw this.cancelled||I?.name==="AbortError"?new O(m.CANCELLED,{stage:"user_cancel"}):Dt(I)}if(!s.ok)throw Io(s,await nu(s));let f=await s.json();f.transcript&&n.onUserMessage?.(f.transcript);let A=Array.isArray(f.ui_actions)?f.ui_actions:[],v=[];A.length>0&&(v=await Ze(A),n.onActionResults?.(v));let R=f.response_text||"",b=vo(R,A,v,f.success_text||"");b&&n.onAssistantMessage?.(b,A),n.onStatusChange?.(y.READY);let C=b===R;C&&f.audio_b64?Jc(f.audio_b64,f.spoken_text||R):C?tt(f.spoken_text||R):b&&tt(b),n.onComplete?.(f),N({event_type:"voice_turn_completed",stage:"http_response",status:"ok",request_id:Xc(s),duration_ms:G()-o,metadata:{transport:"http",action_count:f.ui_actions?.length||0}})}},nn=class{constructor(){this.ws=null,this.connected=!1,this.connecting=null,this.failed=!1,this.retries=0,this.audioQueue=ie,this.callbacks=null,this.turnText="",this.receivedAudio=!1,this.pendingAudioChunks=[]}async ensureConnected(e=[]){return this.canUseWebSocket()?this.isOpen()?!0:this.connecting?this.connecting:(this.connecting=this.openConnection(e),this.connecting):!1}canUseWebSocket(){return!this.failed&&d.useWebSocket&&"WebSocket"in window}isOpen(){return this.connected&&this.ws?.readyState===WebSocket.OPEN}openConnection(e=[]){return new Promise(n=>{let r=new WebSocket(Kc(d.apiUrl,d.siteId)),o=!1;this.ws=r;let i=(s=null)=>{o||(o=!0,this.markConnectionFailed(n,s,r))},a=window.setTimeout(()=>{i()},vn);r.onopen=()=>{o||(o=!0,this.handleConnectionOpen(a,e,n))},r.onmessage=s=>{this.handleMessage(s).catch(u=>this.handleTransportError(u))},r.onerror=()=>{if(o){this.failActiveTurn(m.NETWORK);return}i(a)},r.onclose=()=>{if(this.connected=!1,o){this.failActiveTurn(m.NETWORK);return}i(a)}})}markConnectionOpen(){this.connected=!0,this.connecting=null,this.retries=0}handleConnectionOpen(e,n,r){window.clearTimeout(e),this.markConnectionOpen(),this.sendConfig(n),r(!0)}markConnectionFailed(e,n=null,r=null){n&&window.clearTimeout(n),this.connected=!1,this.connecting=null,this.retries+=1,this.retries>=zc&&(this.failed=!0),r&&r.readyState!==WebSocket.CLOSED&&r.close(),e(!1)}sendConfig(e=[]){this.sendJson({type:k.CONFIG,history:e||[],session_id:d.sessionId,page_context:Po()})}sendJson(e){return!this.ws||this.ws.readyState!==WebSocket.OPEN?!1:(this.ws.send(JSON.stringify(e)),!0)}async sendAudio(e,n,r=[]){if(!await this.ensureConnected(r))return!1;this.callbacks=n,this.turnText="",this.receivedAudio=!1,this.pendingAudioChunks=[],this.sendConfig(r);let i=await Qc(e),a=this.beginTurn();return this.turnStartedAt=G(),N({event_type:"voice_turn_started",stage:"websocket_send",status:"started",metadata:{transport:"websocket",audio_type:e?.type||"unknown"}}),this.sendJson({type:k.AUDIO_CHUNK,data:i,mime_type:e?.type||""})&&this.sendJson({type:k.AUDIO_END,mime_type:e?.type||""})?(await a,!0):(this.settleTurn(),this.callbacks=null,!1)}beginTurn(){return this.settleTurn(),new Promise(e=>{let n=window.setTimeout(()=>{this.failActiveTurn(m.TIMEOUT)},Ln);this.activeTurn={resolve:e,timer:n}})}settleTurn(){let e=this.activeTurn;return this.activeTurn=null,e?(window.clearTimeout(e.timer),e.resolve(),!0):!1}failActiveTurn(e){if(!this.activeTurn)return;let n=this.callbacks;if(this.callbacks=null,this.pendingAudioChunks=[],n){let r=new O(e,{stage:"websocket"});n.onStatusChange?.(y.ERROR,r.customerMessage),n.onComplete?.({error:r.category}),N({event_type:"voice_turn_failed",stage:"websocket",severity:"error",status:"failed",message_code:r.code||r.category,duration_ms:G()-(this.turnStartedAt||G()),metadata:{transport:"websocket",category:r.category,http_status:r.status}})}this.settleTurn()}async handleMessage(e){let n=this.callbacks;if(!n)return;let r=this.parseMessage(e.data);if(!r){this.completeWithError(n,"Invalid WebSocket message");return}if(!this.handleIncrementalMessage(r,n)){if(r.type===k.DONE){await this.handleDoneMessage(r,n);return}r.type===k.ERROR&&this.completeWithError(n,r.message||"WebSocket error")}}parseMessage(e){try{let n=JSON.parse(e);return n&&typeof n=="object"?n:null}catch{return null}}handleIncrementalMessage(e,n){return e.type===k.TRANSCRIPT?(n.onUserMessage?.(e.text||""),!0):e.type===k.TEXT_CHUNK?(this.turnText+=e.text||"",!0):e.type===k.AUDIO_CHUNK?(this.receivedAudio=!!e.audio_b64||this.receivedAudio,e.audio_b64&&this.pendingAudioChunks.push(e.audio_b64),!0):!1}async handleDoneMessage(e,n){let r=e.response_text||this.turnText;try{let o=Array.isArray(e.ui_actions)?e.ui_actions:[],i=[];o.length>0&&(i=await Ze(o),n.onActionResults?.(i));let a=vo(r,o,i,e.success_text||"");n.onAssistantMessage?.(a,o,{streamed:!0}),n.onStatusChange?.(y.READY);let s=a===r;if(this.receivedAudio&&s)for(let u of this.pendingAudioChunks)this.audioQueue.push(u);else s?tt(e.spoken_text||r):a&&tt(a);n.onComplete?.(e),N({event_type:"voice_turn_completed",stage:"websocket_done",status:"ok",duration_ms:G()-(this.turnStartedAt||G()),metadata:{transport:"websocket",action_count:e.ui_actions?.length||0}})}catch(o){this.handleTransportError(o)}finally{this.pendingAudioChunks=[],this.callbacks=null,this.settleTurn()}}completeWithError(e,n){e.onStatusChange?.(y.ERROR,Lo(n)),e.onComplete?.({error:n});let r=Dt(n);N({event_type:"voice_turn_failed",stage:"websocket_message",severity:"error",status:"failed",message_code:r.code||r.category,duration_ms:G()-(this.turnStartedAt||G()),metadata:{transport:"websocket",category:r.category,http_status:r.status}}),this.callbacks=null,this.settleTurn()}handleTransportError(e){console.error("AI Hub WebSocket transport failed",e);let n=this.callbacks;n&&this.completeWithError(n,String(e))}reset(e="reset"){this.callbacks=null,this.turnText="",this.receivedAudio=!1,this.pendingAudioChunks=[],this.settleTurn();try{this.ws?.close()}catch{}this.ws=null,this.connected=!1,this.connecting=null,this.failed=!1,this.retries=0}},Co=new en,xo=new nn;async function No(t,e,n,r=[]){try{if(d.useWebSocket&&await xo.sendAudio(t,n,r))return;await Co.sendAudio(t,n,r)}catch(o){let i=o instanceof O?o:Dt(o);if(wo(i)){N({event_type:"voice_turn_cancelled",stage:i.stage||"transport",status:"cancelled",metadata:{transport:d.useWebSocket?"websocket_or_http":"http"}}),n.onStatusChange?.(y.READY),n.onComplete?.({cancelled:!0});return}console.error(o),N({event_type:"voice_turn_failed",stage:i.stage||"transport",severity:"error",status:"failed",request_id:i.requestId,message_code:i.code||i.category,metadata:{transport:d.useWebSocket?"websocket_or_http":"http",category:i.category,http_status:i.status}}),n.onStatusChange?.(y.ERROR,Lo(o)),n.onComplete?.({error:String(o)})}}function Xc(t){return t?.headers?.get?.("x-request-id")||t?.headers?.get?.("x-correlation-id")||""}function G(){return typeof performance<"u"?performance.now():Date.now()}function Jc(t,e=""){ie.push(t,e)}function Zc(t){let e=String(t?.type||"").toLowerCase();return e.includes("mp4")?"audio.mp4":e.includes("ogg")?"audio.ogg":e.includes("wav")?"audio.wav":bt.WEBM_FILENAME}var tu=/\b(opened|opening|taking you|took you|navigat|sorted|sorting|filtered|filtering|showing|shown|displayed|added to (?:your )?cart|here (?:it |they )?(?:is|are))\b/i,eu=/\b(?:i(?:'ll| will)\s+try\s+to|i'?m\s+(?:going\s+to|about\s+to)|let me)\b/i,Ro="I could not complete that on the page. The site may not have responded - please try again, or do it manually.";function vo(t,e,n,r=""){let o=String(t||"");if(!o||!Array.isArray(e)||e.length===0)return o;let i=String(r||"");if(!(!!i||tu.test(o)||eu.test(o)))return o;let s=Array.isArray(n)?n:[];return s.length!==e.length||!s.every(f=>f?.status==="succeeded"&&f?.verified!==!1)?Ro:i||o}async function nu(t){try{return await t.json()}catch{return null}}function Lo(t){if(t instanceof O)return t.customerMessage;let e=String(t?.message||t||"").toLowerCase();return e.includes("quota")?"Quota reached":e.includes("transcription")||e.includes("speech")?"Voice unavailable":Dt(t).customerMessage}function tt(t){return t?ot(String(t).slice(0,700)):!1}function Po(){let t=window[Wc],e=window[Gc];try{if(typeof t?.getContext=="function")return t.getContext();if(typeof e?.getContext=="function")return e.getContext()}catch(n){console.warn("[AI Hub Widget] Page context collection failed:",n)}return ru()}function ru(){try{return{title:document.title||"",url:window.location.href,path:window.location.pathname,...Zt()}}catch(t){return console.warn("[AI Hub Widget] Local page state collection failed:",t),null}}var ou=4,iu=40,au=24,su=80,cu=120,an=6,uu=40,lu=600,du=6,pu=12,Do=/\[PRODUCT_IDS:\s*([^\]]+)\]/g;function Uo(){let t=[];function e(n,r){let o=String(r||"").trim();o&&(t.push({role:n,content:o}),t.length>uu&&t.shift())}return{history:t,historyForRequest(){if(t.length<=an)return t.map(i=>({...i}));let n=t.slice(0,t.length-an),r=t.slice(t.length-an).map(i=>({...i})),o=fu(n);return o?[o,...r]:r},clear(){t.length=0},rememberUserMessage(n){e("user",n)},rememberAssistantMessage(n,r){e("assistant",mu(n,r))},rememberActionResults(n){let r=_u(n);r&&e("assistant",r)}}}function fu(t){let e=[],n=[];for(let o of t){o.role==="user"&&e.length<du&&e.push(o.content.replace(/\s+/g," ").trim().slice(0,80));let i;for(Do.lastIndex=0;(i=Do.exec(o.content))!==null;)sn(n,i[1].split(",").map(a=>a.trim()))}let r=[];return e.length&&r.push(`Earlier the customer asked: ${e.join("; ")}.`),n.length&&r.push(`Products discussed: ${n.slice(0,pu).join(", ")}.`),r.length?{role:"system",content:`[CONVERSATION_SUMMARY] ${r.join(" ")}`.slice(0,lu)}:null}function mu(t,e){let n=hu(e);return n.length?`${t} [PRODUCT_IDS: ${n.join(",")}]`:t}function hu(t){let e=[];for(let n of t||[]){let r=n.params||{};sn(e,r[p.PRODUCT_IDS]),sn(e,[r[p.PRODUCT_ID]])}return e}function sn(t,e){for(let n of Array.isArray(e)?e:[])n&&!t.includes(n)&&t.push(n)}function _u(t){let e=(Array.isArray(t)?t:[]).map(yu).filter(Boolean).slice(0,ou);return e.length?`[BROWSER_ACTION_RESULTS: ${e.join(" | ")}]`:""}function yu(t){if(!t||typeof t!="object"||!t.action)return"";let e=[se(t.action,iu),`status=${se(t.status,au)||"unknown"}`],n=bu(t.final_url);return n&&e.push(`final_path=${se(n,cu)}`),t.reason&&e.push(`reason=${se(t.reason,su)}`),gu(e,t.evidence),e.join(" ")}function gu(t,e={}){e.rendered_product_count!==void 0&&t.push(`rendered_products=${Number(e.rendered_product_count||0)}`),e.rendered_entity_count!==void 0&&t.push(`rendered_records=${Number(e.rendered_entity_count||0)}`)}function se(t,e){return String(t||"").replace(/\s+/g," ").trim().slice(0,e)}function bu(t){try{let e=new URL(String(t||""),window.location.href);return`${e.pathname}${e.search}${e.hash}`}catch{return""}}var ko="aihub:session-reset",ce="AIHub",Tu=Object.freeze(["mayabot:","aihub:"]);function Au(t){let e=[];for(let n=0;n<t.length;n+=1){let r=t.key(n);r&&Tu.some(o=>r.startsWith(o))&&e.push(r)}return e}function Mo(t){if(!t)return[];try{let e=Au(t);for(let n of e)t.removeItem(n);return e}catch{return[]}}function Eu(){let t=[];try{t.push(...Mo(window.sessionStorage))}catch{}try{t.push(...Mo(window.localStorage))}catch{}return t}function Fo({cancelRecording:t,stopPlayback:e,resetTransport:n,conversationMemory:r,clearOverlays:o,rotateSessionId:i}={}){return function(){let s={stopped_recording:!1,stopped_audio:!1,cleared_keys:[],session_id:""};return s.stopped_recording=ht(t),s.stopped_audio=ht(e),ht(n),ht(()=>r?.clear?.()),ht(o),s.cleared_keys=Eu(),s.session_id=String(ht(i)||""),s}}function ht(t){if(typeof t!="function")return!1;try{let e=t();return e===void 0?!0:e}catch(e){return console.warn("[AI Hub Widget] Session reset step failed:",e),!1}}function Ho(t){let e=window[ce]||{};e.resetSession=t,window[ce]=e;let n=()=>t();return window.addEventListener(ko,n),()=>{window.removeEventListener(ko,n),window[ce]?.resetSession===t&&delete window[ce].resetSession}}var Bo=null;function cn(t){Bo||(Yo(t),Bo=window.setInterval(()=>Yo(t),Nn))}async function Yo({boot:t,shutdownWidget:e}){try{if(await Su()){t();return}e()}catch{t()}}async function Su(){let t=new URL(U.WIDGET_STATUS,d.apiUrl);t.searchParams.set("site_id",d.siteId);let e=await fetch(t.toString(),{cache:"no-store",headers:{Accept:"application/json"}});return e.ok?(await e.json()).enabled!==!1:!0}window.__mayabot_identifier="voice-orb";var un=null,ln=null;function $o(){if(window.__mayabotBooted||document.getElementById("mayabot-widget"))return;window.__mayabotBooted=!0,hn();let t=wn(),e=null,n=null,r=!1;function o(h=Rn){e&&window.clearTimeout(e),e=window.setTimeout(()=>{t.msgs.innerHTML="",t.chat.classList.remove("visible"),e=null},h)}function i(h,ut=""){r=h===y.RECORDING,pn(Vo(h)),t.status.className="",h===y.RECORDING?(e&&(window.clearTimeout(e),e=null),t.msgs.innerHTML="",t.chat.classList.add("visible"),t.status.innerText="Listening...",t.status.classList.add("listening")):h===y.PROCESSING?(t.chat.classList.add("visible"),t.status.innerText="Analyzing...",t.status.classList.add("processing")):h===y.READY?(t.status.innerText="Ready",t.status.classList.add("ready")):h===y.ERROR&&(t.status.innerText=ut||"Try again",t.status.classList.add("error"))}let a=Uo(),s=null,u="",f=!1,A=0;async function v(h){if(f)return;f=!0;let ut=++A,et=()=>ut===A;t.btn.disabled=!0,s=null,u="";try{await No(h,t,{onUserMessage:L=>{et()&&(gt(t,L,"user"),a.rememberUserMessage(L))},onAssistantChunk:(L,_t)=>{et()&&(u=_t,s||(s=gt(t,"","ai")),pe(t,s,u))},onAssistantMessage:(L,_t,Wo={})=>{et()&&(Wo.streamed&&s?pe(t,s,L):gt(t,L,"ai"),a.rememberAssistantMessage(L,_t),s=null,u="")},onActionResults:L=>{et()&&a.rememberActionResults(L)},onStatusChange:(L,_t)=>{et()&&i(L,_t)},onComplete:()=>{et()&&o()}},a.historyForRequest())}finally{et()&&(f=!1,t.btn.disabled=!1),s=null,u=""}}function R(){A+=1,on("user_cancel"),ae(),f=!1,t.btn.disabled=!1,s=null,u="",N({event_type:"voice_turn_cancelled",stage:"orb_gesture",status:"cancelled"}),i(y.READY)}let b=Pn(v,i);un=b;function C(){return f||rn()}function I(){if(C()){R();return}b.toggle()}let dn={idle:{label:"Maya voice assistant. Click, press Enter, or press Space to talk.",title:"Click to talk"},recording:{label:"Maya is listening. Click once to send, or press Escape to cancel.",title:"Click once to send - Escape to cancel"},processing:{label:"Maya is working on your request. Please wait.",title:"Request in progress"},speaking:{label:"Maya is speaking. Click to stop, or press Escape to stop.",title:"Click to stop Maya"}};function Vo(h){return h===y.RECORDING?"recording":h===y.PROCESSING?"processing":rn()?"speaking":"idle"}function pn(h){let ut=dn[h]||dn.idle;t.btn.setAttribute("aria-label",ut.label),t.btn.setAttribute("title",ut.title),t.btn.setAttribute("data-orb-state",h),t.btn.classList.toggle("recording",h==="recording"),t.btn.classList.toggle("speaking",h==="speaking")}pn("idle"),t.btn.addEventListener("click",h=>{h.detail>1||I()});let fn=h=>{if(h.key==="Escape"){if(r){b.cancel(),N({event_type:"voice_recording_cancelled",stage:"keyboard_escape",status:"cancelled"}),i(y.READY);return}C()&&R()}};document.addEventListener("keydown",fn);let mn=h=>{t.btn.contains(h.target)||Gt()};document.addEventListener("pointerdown",mn,{capture:!0});let zo=Ho(Fo({cancelRecording:()=>b.cancel(),stopPlayback:ae,resetTransport:on,conversationMemory:a,clearOverlays:()=>{t.msgs.innerHTML="",t.chat.classList.remove("visible"),document.getElementById("mayabot-product-panel")?.remove()},rotateSessionId:()=>d.rotateSessionId()}));ln=()=>{document.removeEventListener("keydown",fn),document.removeEventListener("pointerdown",mn,{capture:!0}),zo(),e&&window.clearTimeout(e),e=null,n&&window.clearTimeout(n),n=null,ln=null},wu()&&(Iu(),n=window.setTimeout(()=>{if(a.history.length>0)return;let h=`Welcome to ${d.brandName}. How can I help you today?`;gt(t,h,"ai"),i(y.READY),o(xn),ot(h)},Cn))}function jo(){un?.cancel(),un=null,ln?.(),ae(),window.__mayabotBooted=!1,document.getElementById("mayabot-widget")?.remove(),document.getElementById("mayabot-product-panel")?.remove()}function wu(){if(!d.autoGreet||!Ou())return!1;try{return window.sessionStorage.getItem(qo())!=="1"}catch{return!window.__mayabotAutoGreeted}}function Iu(){window.__mayabotAutoGreeted=!0;try{window.sessionStorage.setItem(qo(),"1")}catch{}}function qo(){return`mayabot:auto-greeted:${d.siteId}`}function Ou(){let t=window.location.pathname.replace(/\/+$/,"")||"/";return t==="/"||t.endsWith("/index.html")}document.readyState==="loading"?document.addEventListener("DOMContentLoaded",()=>cn({boot:$o,shutdownWidget:jo})):cn({boot:$o,shutdownWidget:jo});})();
