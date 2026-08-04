(()=>{function be(){let t="#5d5fef",e=document.querySelector('meta[name="theme-color"]');if(e&&e.content)t=e.content;else{let f=document.querySelector('button[class*="primary"], .btn-primary, [data-primary]');if(f){let g=window.getComputedStyle(f).backgroundColor;g&&g!=="rgba(0, 0, 0, 0)"&&g!=="transparent"&&(t=g)}}let n=window.matchMedia&&window.matchMedia("(prefers-color-scheme: dark)").matches,r=n?"rgba(24, 24, 27, 0.75)":"rgba(255, 255, 255, 0.85)",o=n?"rgba(255, 255, 255, 0.1)":"rgba(0, 0, 0, 0.08)",i=n?"#f3f4f6":"#111827",a=n?"rgba(255, 255, 255, 0.1)":"rgba(0, 0, 0, 0.05)",c=n?"rgba(0, 0, 0, 0.25)":"#ffffff",p=document.createElement("style");p.textContent=`
    :root {
      --mayabot-primary: ${t};
      --mayabot-surface: ${r};
      --mayabot-border: ${o};
      --mayabot-text: ${i};
      --mayabot-user-bg: ${a};
      --mayabot-bot-bg: ${c};
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
      border: 1px solid rgba(255, 255, 255, 0.15);
      background: var(--mayabot-primary);
      box-shadow: 0 12px 32px -8px var(--mayabot-primary), 0 4px 12px rgba(0,0,0,0.15);
      color: #ffffff;
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
      opacity: 0.4;
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

    #mayabot-btn.recording {
      background: #ef4444;
      box-shadow: 0 0 0 6px rgba(239, 68, 68, 0.2), 0 8px 24px rgba(0,0,0,0.18);
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
  `,document.head.appendChild(p)}var vt="site_1",kr="__AI_";var Mr="aihub:auto-site-id:",Fr=["data-aihub-scope","data-site-scope"],Hr=["data-site-id","data-aihub-site-id"];function A(t){return String(t||"").trim()}function X(t){return A(t).replace(/\/+$/,"")}function we(t,e,n,r=vt){return Br(t,e,n)||Yr()||A(r)||vt}function Br(t,e,n){for(let i of Hr){let a=A(t?.getAttribute(i));if(a)return a}let r=A(e?.searchParams.get("site"))||A(e?.searchParams.get("site_id"))||A(e?.searchParams.get("shop"));if(r)return r;let o=A(n);return o&&!o.startsWith(kr)?o:""}function Yr(){let t=jr(),e=`${Mr}${t}`,n=Qr(e);if(n){let c=Gr(n);return c!==n&&Ie(e,c),c}let r=A(window.location.host||window.location.hostname||"site"),o=Oe(),i=qr(`${r}${o?`_${o.replace(/\//g,"_")}`:""}`),a=Re(`auto_${i}_${Kr(t)}`);return Ie(e,a),a}function jr(){return`${window.location.origin}${Oe()}`}function Oe(){return Vr()}function Vr(){for(let e of Fr){let n=A($r()?.getAttribute(e));if(n)return Se(n)}let t=document.querySelector("meta[name='aihub-site-scope']")?.getAttribute("content");return Se(t)}function $r(){return document.currentScript}function Se(t){let e=A(t);if(!e||e==="/")return"";try{let r=new URL(e,window.location.href);if(r.origin===window.location.origin){let[o]=zr(r.pathname);return o?`/${o}`:""}}catch{}let[n]=e.replace(/^\/+/,"").split("/");return n?`/${n}`:""}function zr(t=window.location.pathname){return A(t).split("/").map(e=>Wr(e).trim()).filter(Boolean)}function Wr(t){try{return decodeURIComponent(t)}catch{return String(t||"")}}function qr(t){return A(t).toLowerCase().replace(/[^a-z0-9]+/g,"_").replace(/^_+|_+$/g,"")||"site"}function Re(t){return A(t).slice(0,80).replace(/_+$/g,"")||vt}function Gr(t){let e=A(t);return e.startsWith("auto_")?Re(e.toLowerCase().replace(/[^a-z0-9]+/g,"_").replace(/^_+|_+$/g,"")):e}function Kr(t){let e=2166136261,n=A(t);for(let r=0;r<n.length;r+=1)e^=n.charCodeAt(r),e=Math.imul(e,16777619);return(e>>>0).toString(36)}function Qr(t){try{return A(window.localStorage.getItem(t))}catch{return""}}function Ie(t,e){try{window.localStorage.setItem(t,e)}catch{}}var D=document.currentScript,xe="__AI_PUBLIC_API_URL__",Xr="__AI_DEFAULT_SITE_ID__",Ce="mayabot:session:",Jr="Maya",Zr="AI Salesperson",to="female";function B(t){return String(t||"").trim()}function eo(){let t=B(D?.getAttribute("src"));if(!t)return null;try{return new URL(t,window.location.href)}catch{return null}}function no(t){let e=B(D?.getAttribute("data-api-url"));if(e)return X(e);if(!xe.startsWith("__AI_"))return X(xe);if(t?.origin){let n=t.pathname.replace(/\/mayabot(?:-widget)?\.js$/,"");return X(`${t.origin}${n}`)}return X(window.location.origin)}function ro(t){let e=`${Ce}${t}`;try{let n=window.sessionStorage.getItem(e);if(n)return n;let r=Pt(t);return window.sessionStorage.setItem(e,r),r}catch{return Pt(t)}}function oo(t){let e=Pt(t);try{window.sessionStorage.setItem(`${Ce}${t}`,e)}catch{}return e}function Pt(t){let e=window.crypto?.randomUUID?.()||`${Date.now()}-${Math.random().toString(16).slice(2)}`;return`${t}-${e}`.slice(0,120)}var Ne=eo(),Lt=we(D,Ne,Xr),l={siteId:Lt,get sessionId(){return ro(Lt)},rotateSessionId(){return oo(Lt)},apiUrl:no(Ne),useWebSocket:B(D?.getAttribute("data-use-websocket")).toLowerCase()==="true",autoGreet:B(D?.getAttribute("data-auto-greet")).toLowerCase()!=="false",brandName:B(D?.getAttribute("data-brand"))||Jr,assistantTitle:B(D?.getAttribute("data-assistant-title"))||Zr,speechVoiceName:B(D?.getAttribute("data-speech-voice")),speechVoicePreference:B(D?.getAttribute("data-speech-voice-preference"))||to};function ve(){let t=document.createElement("div");return t.id="mayabot-widget",t.innerHTML=`
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
  `,document.body.appendChild(t),t.querySelector(".mayabot-kicker").textContent=l.brandName,t.querySelector(".mayabot-title").textContent=l.assistantTitle,{btn:document.getElementById("mayabot-btn"),chat:document.getElementById("mayabot-chat"),msgs:document.getElementById("mayabot-msgs"),status:document.getElementById("mayabot-status")}}function J(t,e,n){t.chat.classList.add("visible");let r=document.createElement("div");return r.className=`mayabot-msg ${n}`,r.innerText=e,t.msgs.appendChild(r),t.msgs.scrollTop=t.msgs.scrollHeight,r}function Dt(t,e,n){e&&(e.innerText=n,t.msgs.scrollTop=t.msgs.scrollHeight)}var s=Object.freeze({ADD_TO_CART:"ADD_TO_CART",BOOK_APPOINTMENT_REQUEST:"BOOK_APPOINTMENT_REQUEST",BUILD_ITINERARY:"BUILD_ITINERARY",BUILD_LEARNING_PATH:"BUILD_LEARNING_PATH",CAPTURE_LEAD:"CAPTURE_LEAD",CAPTURE_PATIENT_LEAD:"CAPTURE_PATIENT_LEAD",CHECKOUT:"CHECKOUT",CHECKOUT_HANDOFF:"CHECKOUT_HANDOFF",CHECK_APPOINTMENT_AVAILABILITY:"CHECK_APPOINTMENT_AVAILABILITY",CHECK_AVAILABILITY:"CHECK_AVAILABILITY",CHECK_DELIVERY_AVAILABILITY:"CHECK_DELIVERY_AVAILABILITY",CHECK_ELIGIBILITY_SOFT:"CHECK_ELIGIBILITY_SOFT",CHECK_PREREQUISITES:"CHECK_PREREQUISITES",CLEAR_CART:"CLEAR_CART",CLEAR_FILTERS:"CLEAR_FILTERS",CLEAR_HISTORY:"CLEAR_HISTORY",COMPARE_ENTITIES:"COMPARE_ENTITIES",CONTACT_AGENT:"CONTACT_AGENT",FILTER_ENTITIES:"FILTER_ENTITIES",FILTER_PRODUCTS:"FILTER_PRODUCTS",HANDOFF_TO_ADVISOR:"HANDOFF_TO_ADVISOR",HANDOFF_TO_AGENT:"HANDOFF_TO_AGENT",HANDOFF_TO_CLINIC:"HANDOFF_TO_CLINIC",HANDOFF_TO_HUMAN:"HANDOFF_TO_HUMAN",HANDOFF_TO_LAWYER:"HANDOFF_TO_LAWYER",HANDOFF_TO_LICENSED_AGENT:"HANDOFF_TO_LICENSED_AGENT",HANDOFF_TO_RECRUITER:"HANDOFF_TO_RECRUITER",JOIN_WAITLIST:"JOIN_WAITLIST",MATCH_JOBS:"MATCH_JOBS",NAVIGATE_TO:"NAVIGATE_TO",OPEN_CLAIM_FLOW:"OPEN_CLAIM_FLOW",OPEN_CONTACT:"OPEN_CONTACT",OPEN_DISCLOSURE:"OPEN_DISCLOSURE",OPEN_ENTITY_DETAIL:"OPEN_ENTITY_DETAIL",OPEN_LOCATION:"OPEN_LOCATION",OPEN_MAP:"OPEN_MAP",OPEN_POLICY:"OPEN_POLICY",OPEN_PROJECTS:"OPEN_PROJECTS",OPEN_RENEWAL_FLOW:"OPEN_RENEWAL_FLOW",OPEN_SERVICES:"OPEN_SERVICES",OPEN_SYLLABUS:"OPEN_SYLLABUS",OPEN_TELECONSULT:"OPEN_TELECONSULT",REMOVE_FROM_CART:"REMOVE_FROM_CART",REQUEST_APPOINTMENT:"REQUEST_APPOINTMENT",REQUEST_CALLBACK:"REQUEST_CALLBACK",REQUEST_CONSULTATION:"REQUEST_CONSULTATION",REQUEST_COUNSELOR_CALLBACK:"REQUEST_COUNSELOR_CALLBACK",REQUEST_ESTIMATE:"REQUEST_ESTIMATE",REQUEST_SITE_VISIT:"REQUEST_SITE_VISIT",REQUEST_TEST_DRIVE:"REQUEST_TEST_DRIVE",REQUEST_VIEWING:"REQUEST_VIEWING",RUN_AFFORDABILITY_CALCULATOR:"RUN_AFFORDABILITY_CALCULATOR",RUN_CALCULATOR:"RUN_CALCULATOR",RUN_DOM_SEQUENCE:"RUN_DOM_SEQUENCE",SAVE_SEARCH:"SAVE_SEARCH",SCHEDULE_ORDER:"SCHEDULE_ORDER",SEARCH_AVAILABILITY:"SEARCH_AVAILABILITY",SET_LOCATION:"SET_LOCATION",SHOW_COMPARISON:"SHOW_COMPARISON",SHOW_EMERGENCY_NOTICE:"SHOW_EMERGENCY_NOTICE",SHOW_ENTITIES:"SHOW_ENTITIES",SHOW_PRODUCT_DETAIL:"SHOW_PRODUCT_DETAIL",SHOW_PRODUCTS:"SHOW_PRODUCTS",SORT_ENTITIES:"SORT_ENTITIES",SORT_PRODUCTS:"SORT_PRODUCTS",START_APPLICATION:"START_APPLICATION",START_BOOKING:"START_BOOKING",START_ENROLLMENT:"START_ENROLLMENT",START_INTAKE:"START_INTAKE",START_QUOTE:"START_QUOTE",START_TICKET_PURCHASE:"START_TICKET_PURCHASE",UPDATE_CART_QUANTITY:"UPDATE_CART_QUANTITY",UPDATE_PREFERENCES:"UPDATE_PREFERENCES"}),d=Object.freeze({ENTITY_ID:"entity_id",ENTITY_IDS:"entity_ids",MESSAGE:"message",PAGE:"page",PRODUCT_ID:"product_id",PRODUCT_IDS:"product_ids",QUANTITY:"quantity",REASON:"reason",SEARCH_QUERY:"search_query",URL:"url"}),$s=Object.freeze({BLOCKED:"blocked",EXECUTING:"executing",FAILED:"failed",REQUESTED:"requested",SKIPPED:"skipped",SUCCEEDED:"succeeded",UNKNOWN:"unknown"}),C=Object.freeze({KNOWLEDGE_BY_IDS:"/v1/knowledge/by-ids",PRODUCTS_BY_IDS:"/v1/products/by-ids",SHOP:"/v1/shop",SHOP_WS:"/v1/ws/shop",WIDGET_STATUS:"/v1/widget/status"}),N=Object.freeze({AUDIO_CHUNK:"audio_chunk",AUDIO_END:"audio_end",CONFIG:"config",DONE:"done",ERROR:"error",TEXT_CHUNK:"text_chunk",TRANSCRIPT:"transcript"});var Le=new Set(["cart","/cart"]),U="Recommended products",Y="Relevant options",Z=Object.freeze({DATA_WAV_PREFIX:"data:audio/wav;base64,",WEBM_FILENAME:"audio.webm",WEBM_MIME_TYPE:"audio/webm"}),Pe=Object.freeze({POST:"POST"}),h=Object.freeze({ERROR:"error",PROCESSING:"processing",READY:"ready",RECORDING:"recording"}),De=12,Ue=2400,ke=900,Me=4200,Ut=1,W=180,Fe=3e3,tt=Object.freeze({MAYABOT_ACTION:"mayabot:action"}),He=2500,Be=45e3;var io=["audio/webm;codecs=opus","audio/webm","audio/ogg;codecs=opus","audio/ogg","audio/mp4"],ao=250,so=128;function Ye(t,e){let n=null,r=null,o=[],i=!1,a=!1,c=!1;async function p(){if(!(a||i)){a=!0;try{let E=await navigator.mediaDevices.getUserMedia({audio:!0});r=E,c=!1;let V=co();n=new MediaRecorder(E,V?{mimeType:V}:void 0),o=[],n.ondataavailable=w=>{w.data.size>0&&o.push(w.data)},n.onstop=async()=>{let w=new Blob(o,{type:n.mimeType||V||Z.WEBM_MIME_TYPE});if(T(),c){c=!1;return}if(w.size<so){console.warn("Microphone recording was empty or too short",{size:w.size}),e(h.READY);return}await t(w)},n.onerror=w=>{console.error("Microphone recording failed",w.error||w),i=!1,a=!1,T(),e(h.ERROR,"Recording failed")},n.start(ao),i=!0,e(h.RECORDING)}catch(E){console.error("Microphone access denied",E),e(h.ERROR,"Mic unavailable")}finally{a=!1}}}function f({discard:E=!1}={}){if(c=E,n&&n.state!=="inactive"){try{n.requestData()}catch{}n.stop(),i=!1,E||e(h.PROCESSING);return}i=!1,T(),E||e(h.PROCESSING)}function g(){a||(i?f():p())}function I(){f({discard:!0})}function T(){r&&(r.getTracks().forEach(E=>E.stop()),r=null)}return{toggle:g,cancel:I}}function co(){return!("MediaRecorder"in window)||typeof MediaRecorder.isTypeSupported!="function"?"":io.find(t=>MediaRecorder.isTypeSupported(t))||""}var je="shopify",Ve="woocommerce",uo="custom";function lt(t){let e=String(t||"").trim();return/^\d+$/.test(e)?e:""}function dt(t,e=1){let n=Number(t?.[d.QUANTITY]);return Number.isFinite(n)&&n>0?Math.floor(n):e}async function $(t,e){return(await fetch(new URL(t,window.location.origin),{method:"POST",headers:{Accept:"application/json","Content-Type":"application/json"},body:JSON.stringify(e),credentials:"same-origin"})).ok}function lo(){return po()?je:fo()?Ve:uo}async function $e(t){let e=lo();return e===je?mo(t):e===Ve?_o(t):!1}function po(){return!!(window.Shopify||document.querySelector('meta[name="shopify-checkout-api-token"]')||document.querySelector('script[src*="cdn.shopify.com"]'))}function fo(){return!!(document.body?.classList?.contains("woocommerce")||window.wc_add_to_cart_params||document.querySelector('link[href*="woocommerce"], script[src*="woocommerce"]'))}async function mo(t){let e=t.parameters||{};if(t.action===s.ADD_TO_CART){let n=lt(e.variant_id||e.cart_id||e[d.PRODUCT_ID]);return n?$("/cart/add.js",{items:[{id:n,quantity:dt(e)}]}):!1}if(t.action===s.REMOVE_FROM_CART){let n=lt(e.cart_id||e.variant_id||e[d.PRODUCT_ID]);return n?$("/cart/change.js",{id:n,quantity:0}):!1}if(t.action===s.UPDATE_CART_QUANTITY){let n=lt(e.cart_id||e.variant_id||e[d.PRODUCT_ID]);return n?$("/cart/change.js",{id:n,quantity:dt(e,0)}):!1}return t.action===s.CLEAR_CART?$("/cart/clear.js",{}):t.action===s.CHECKOUT?pt("/checkout"):ze(t)?pt("/cart"):!1}async function _o(t){let e=t.parameters||{};if(t.action===s.ADD_TO_CART){let n=lt(e.variant_id||e.cart_id||e[d.PRODUCT_ID]);return n?$("/wp-json/wc/store/cart/add-item",{id:Number(n),quantity:dt(e)}):!1}if(t.action===s.REMOVE_FROM_CART){let n=String(e.cart_key||e.key||"").trim();return n?$("/wp-json/wc/store/cart/remove-item",{key:n}):!1}if(t.action===s.UPDATE_CART_QUANTITY){let n=String(e.cart_key||e.key||"").trim();return n?$("/wp-json/wc/store/cart/update-item",{key:n,quantity:dt(e,0)}):!1}return t.action===s.CHECKOUT?pt("/checkout"):ze(t)?pt("/cart"):!1}function ze(t){return t.action===s.NAVIGATE_TO&&Le.has(t.parameters?.[d.PAGE])}function pt(t){return window.location.href=t,!0}var ho="/v1/widget/action-event";function O(t){return String(t||"").trim()}function yo(t,e){return new URL(t,e).toString()}function go(t){return!t||typeof t!="object"?[]:Object.keys(t).map(e=>O(e)).filter(Boolean).slice(0,20)}function To(t){if(!t||typeof t!="object")return{};let e={};for(let[n,r]of Object.entries(t).slice(0,20)){let o=O(n).slice(0,80);o&&(typeof r=="boolean"||r===null?e[o]=r:typeof r=="number"?e[o]=Number.isFinite(r)?r:0:e[o]=O(r).slice(0,240))}return e}async function ft(t,e,n,r){if(!t||!e||!n?.action)return;let o=JSON.stringify({site_id:e,origin:window.location.origin,url:window.location.href,occurred_at:new Date().toISOString(),request_id:O(n.request_id||n.action_request_id),turn_id:O(n.turn_id),sequence:Number(n.sequence||0),action:O(n.action).toUpperCase(),status:O(r?.status)||"unknown",stage:O(r?.stage),reason:O(r?.reason),duration_ms:Number(r?.duration_ms||0),param_keys:go(n.parameters||n.params),requested_url:O(r?.requested_url),final_url:O(r?.final_url||window.location.href),evidence:To(r?.evidence)}),i=yo(ho,t);if(!Ao(i,o))try{await fetch(i,{method:"POST",headers:{Accept:"application/json","Content-Type":"application/json"},body:o,keepalive:!0})}catch(a){console.warn("[AIHubAdapter] Action execution report failed.",a)}}function Ao(t,e){if(typeof navigator>"u"||typeof navigator.sendBeacon!="function"||typeof Blob!="function")return!1;try{return navigator.sendBeacon(t,new Blob([e],{type:"application/json"}))}catch{return!1}}function et(t){if(!t||typeof t!="string")return[];let e=[];for(let n of Eo()){try{e.push(...Array.from(n.querySelectorAll(t)))}catch{return[]}if(e.length>=600)return e.slice(0,600)}return wo(e)}function Eo(){let t=[],e=new Set,n=[document];for(;n.length&&t.length<60;){let r=n.shift();!r||e.has(r)||(e.add(r),t.push(r),n.push(...bo(r)))}return t}function bo(t){let e=[];for(let n of So(t)){n.shadowRoot&&e.push(n.shadowRoot);let r=Io(n);r&&e.push(r)}return e}function So(t){try{return Array.from(t.querySelectorAll("*"))}catch{return[]}}function Io(t){if(String(t?.tagName||"").toLowerCase()!=="iframe")return null;try{let e=t.contentDocument;return e?.documentElement?e:null}catch{return null}}function wo(t){return Array.from(new Set(t))}var tc=Object.freeze([u("stripe",["stripe","stripe.com","checkout.stripe.com","js.stripe.com"]),u("paypal",["paypal","paypal.com","paypalobjects.com"]),u("razorpay",["razorpay","checkout.razorpay.com"]),u("paytm",["paytm","securegw.paytm.in"]),u("cashfree",["cashfree","cashfree.com"]),u("checkout.com",["checkout.com","cko-session-id"]),u("adyen",["adyen","checkoutshopper"]),u("square",["squareup","squarecdn","square.site"]),u("braintree",["braintree","braintreegateway"]),u("mollie",["mollie","mollie.com"]),u("klarna",["klarna","klarna.com"]),u("afterpay",["afterpay","afterpay.com","clearpay"]),u("payu",["payu","payu.in","payu.com"]),u("paystack",["paystack","paystack.co"]),u("phonepe",["phonepe","phonepe.com"]),u("billdesk",["billdesk","billdesk.com"]),u("authorize.net",["authorize.net","accept.authorize.net"])]),We=Object.freeze([u("calendly",["calendly","calendly.com"]),u("acuity",["acuityscheduling","squarespace scheduling"]),u("booksy",["booksy","booksy.com"]),u("zocdoc",["zocdoc","zocdoc.com"]),u("appointlet",["appointlet","appointlet.com"]),u("setmore",["setmore","setmore.com"]),u("cal.com",["cal.com","calcom"]),u("google_calendar",["calendar.google.com","google calendar"]),u("microsoft_bookings",["microsoft bookings","outlook.office365.com/book"]),u("simplybook",["simplybook","simplybook.me"]),u("tidycal",["tidycal","tidycal.com"]),u("savvycal",["savvycal","savvycal.com"]),u("fresha",["fresha","fresha.com"])]),qe=Object.freeze([u("google_maps",["google.com/maps","maps.googleapis","maps.google"]),u("mapbox",["mapbox","mapbox.com"]),u("openstreetmap",["openstreetmap","osm.org"]),u("leaflet",["leaflet","leafletjs"]),u("here_maps",["here.com","hereapi","wego.here.com"]),u("bing_maps",["bing.com/maps","virtualearth"]),u("mappls",["mappls","mapmyindia"])]),Ge=Object.freeze([u("whatsapp",["wa.me","api.whatsapp.com","web.whatsapp.com"]),u("telegram",["t.me/","telegram.me"]),u("messenger",["m.me/","messenger.com/t"]),u("zendesk",["zendesk.com","zdassets.com/hc"]),u("intercom",["intercom.help","intercom.com"]),u("freshchat",["freshchat.com"])]),ec=Object.freeze([u("recaptcha",["recaptcha","g-recaptcha","google.com/recaptcha"]),u("hcaptcha",["hcaptcha","h-captcha"]),u("turnstile",["turnstile","challenges.cloudflare.com"]),u("cloudflare_challenge",["cf-chl","cloudflare challenge"])]);function u(t,e){return{name:t,tokens:e}}function kt(t,e,n=10){let r=Mt(t);return e.filter(o=>o.tokens.some(i=>r.includes(i))).map(o=>o.name).slice(0,n)}function Mt(t){return String(t||"").replace(/\s+/g," ").trim().toLowerCase()}var Ke="a[href], iframe[src]",Oo="a[href]",Xe=new Set(["http:","https:"]),mt=new Set(["mailto:","tel:"]),Ro=Object.freeze([d.URL,"href","link","target_url","provider_url","booking_url","appointment_url","calendar_url","map_url","location_url","contact_url"]),Je=new Set([s.OPEN_MAP,s.OPEN_LOCATION,s.SET_LOCATION]),Ze=new Set([s.CHECK_APPOINTMENT_AVAILABILITY,s.REQUEST_APPOINTMENT,s.BOOK_APPOINTMENT_REQUEST,s.REQUEST_CONSULTATION,s.REQUEST_SITE_VISIT,s.START_BOOKING]),tn=new Set([s.OPEN_CONTACT,s.CONTACT_AGENT,s.REQUEST_CALLBACK,s.REQUEST_COUNSELOR_CALLBACK,s.HANDOFF_TO_ADVISOR,s.HANDOFF_TO_AGENT,s.HANDOFF_TO_CLINIC,s.HANDOFF_TO_HUMAN,s.HANDOFF_TO_LAWYER,s.HANDOFF_TO_LICENSED_AGENT,s.HANDOFF_TO_RECRUITER]);function en(t){let e=on(t);return Je.has(e)||Ze.has(e)||tn.has(e)}async function nn(t){let e=on(t);return Je.has(e)?Ft(t,qe,Ke,Ht):Ze.has(e)?Ft(t,We,Ke,Ht):tn.has(e)?Ft(t,Ge,Oo,vo):!1}function Ft(t,e,n,r){let o=xo(t?.parameters||t?.params||{},e,r);if(o)return Qe(o);let i=Co(n,e,r);return i?Qe(i):!1}function xo(t,e,n){for(let r of Ro){let o=rn(t?.[r]);if(o&&n(o,e))return o}return null}function Co(t,e,n){for(let r of et(t)){let o=No(r);if(!(!o||!n(o,e))&&Lo(o,r,e))return o}return null}function No(t){return rn(t?.getAttribute?.("href")||t?.getAttribute?.("src"))}function Ht(t,e){return Xe.has(t.protocol)&&kt(t.href,e).length>0}function vo(t,e){return mt.has(t.protocol)?!0:Ht(t,e)}function Lo(t,e,n){if(mt.has(t.protocol))return!0;let r=[t.href,e?.textContent||"",e?.getAttribute?.("aria-label")||"",e?.getAttribute?.("title")||""].join(" ");return kt(Mt(r),n).length>0}function Qe(t){if(mt.has(t.protocol)||t.origin===window.location.origin)return window.location.href=t.href,!0;let e=window.open(t.href,"_blank","noopener,noreferrer");return e?(e.opener=null,!0):(window.location.href=t.href,!0)}function rn(t){let e=String(t||"").trim();if(!e||e.startsWith("#"))return null;try{let n=new URL(e,window.location.href);return Xe.has(n.protocol)||mt.has(n.protocol)?n:null}catch{return null}}function on(t){return String(t?.action||"").trim().toUpperCase()}var Po=Object.freeze(["title","name"]),Do=Object.freeze(["summary","description","body"]),Uo=Object.freeze(["image_url","imageUrl","image","thumbnail"]),ko=Object.freeze(["url","href","permalink","source_url"]),Mo="knowledge_item",Fo=30;function v(t){return t==null||typeof t=="object"?"":String(t||"").trim()}function Ho(t){let e=new Set;return(Array.isArray(t)?t:[]).map(v).filter(Boolean).filter(n=>e.has(n)||e.size>=Fo?!1:(e.add(n),!0))}function _t(t,e){for(let n of e){let r=v(t?.[n]);if(r)return r}return""}function nt(t){return t&&typeof t=="object"&&!Array.isArray(t)?t:{}}function Bo(t){let e=Yo([t?.price,t?.amount,t?.premium,t?.premium_min,t?.monthly_premium,t?.annual_premium,t?.min_price,t?.starting_price]),n=v(t?.currency||"INR");return!Number.isFinite(e)||e<=0?"":`${n} ${e.toLocaleString()}`}function Yo(t){for(let e of t){let n=Number(String(e??"").replace(/,/g,""));if(Number.isFinite(n)&&n>0)return n}return 0}function jo(t){return!t||typeof t!="object"?"":t.in_stock===!0?"Available":t.in_stock===!1?"Unavailable":v(t.status||t.availability||"")}function Vo(t){let e=v(t);if(!e)return"";try{let n=new URL(e,window.location.origin);return/^https?:$/i.test(n.protocol)?n.origin===window.location.origin?`${n.pathname}${n.search}${n.hash}`:n.toString():""}catch{return""}}function $o(t){if(!t)return null;let e=v(t.id);if(!e)return null;let n=nt(t.pricing),r=nt(t.availability);return{id:e,externalId:v(t.external_id),entityType:v(t.entity_type||t.category_name)||Mo,title:_t(t,Po)||e,subtitle:v(t.subtitle||t.category_name||t.entity_type),summary:_t(t,Do),body:v(t.body),url:Vo(_t(t,ko)),imageUrl:_t(t,Uo),attributes:nt(t.attributes),pricing:n,availability:r,location:nt(t.location),contact:nt(t.contact),displayPrice:Bo(n),displayAvailability:jo(r)}}async function Bt(t){let e=Ho(t);if(!e.length)return[];let n=new URL(C.KNOWLEDGE_BY_IDS,l.apiUrl);n.searchParams.set("site_id",l.siteId),n.searchParams.set("ids",e.join(","));let r=await fetch(n.toString(),{headers:{Accept:"application/json"}});if(!r.ok)throw new Error("Failed to fetch entities from AI Hub API");let o=(await r.json()).map($o).filter(Boolean),i=new Map(o.map(a=>[String(a.id),a]));return e.map(a=>i.get(a)).filter(Boolean)}async function an(t){let[e]=await Bt([t]);return e?.url||""}function sn(){if(document.getElementById("mayabot-entity-overlay-styles"))return;let t=document.createElement("style");t.id="mayabot-entity-overlay-styles",t.textContent=`
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
  `,document.head.appendChild(t)}var zo=2,cn=Number.POSITIVE_INFINITY,ht=Number.NEGATIVE_INFINITY,un=12,jt=[],Vt=Y;function k(t){return String(t??"").replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;").replace(/"/g,"&quot;").replace(/'/g,"&#039;")}function fn(t){return String(t||"item").replace(/[_-]+/g," ").trim().split(/\s+/).slice(0,zo).join(" ")}function Wo(){sn();let t=document.getElementById("mayabot-entity-panel");return t||(t=document.createElement("div"),t.id="mayabot-entity-panel",t.setAttribute("aria-live","polite"),t.innerHTML=`
    <div class="mayabot-entity-header">
      <h2 class="mayabot-entity-title">${Y}</h2>
      <button class="mayabot-entity-close" type="button" aria-label="Close recommendations">&times;</button>
    </div>
    <div class="mayabot-entity-grid"></div>
  `,t.querySelector(".mayabot-entity-close").addEventListener("click",()=>{t.classList.remove("active")}),document.body.appendChild(t),t)}function qo(t){return t<=1?"count-1":t===2?"count-2":t===3?"count-3":"count-many"}function Go(t){return t<=1?1:t===2?2:3}function Yt(t,e,n=""){let r=(Array.isArray(e)?e:[]).map(c=>String(c?.id??"").trim()).filter(Boolean),o=r.length,i=t.length,a=o>0?"succeeded":"failed";return{status:a,stage:"entity_overlay",reason:n||(a==="succeeded"?"":"no_matching_entities_rendered"),evidence:{requested_entity_count:i,rendered_entity_count:o,missing_entity_count:Math.max(i-o,0),requested_entity_ids:t.slice(0,un).join(","),rendered_entity_ids:r.slice(0,un).join(",")}}}function Ko(t){return[t.displayPrice,t.displayAvailability,t.location?.city,t.attributes?.category].map(e=>String(e||"").trim()).filter(Boolean).slice(0,3)}function Qo(t){return t.imageUrl?`
      <div class="mayabot-entity-media">
        <img src="${k(t.imageUrl)}" alt="${k(t.title)}">
      </div>
    `:`
    <div class="mayabot-entity-media">
      <div class="mayabot-entity-badge">${k(fn(t.entityType))}</div>
    </div>
  `}function Xo(t){let e=Ko(t);return e.length?`
    <div class="mayabot-entity-facts">
      ${e.map(n=>`<span class="mayabot-entity-fact">${k(n)}</span>`).join("")}
    </div>
  `:""}function Jo(t){return t.url?`
    <div class="mayabot-entity-actions">
      <button type="button" data-view-entity="${k(t.id)}">Open</button>
    </div>
  `:""}function gt(t,e){let n=Wo(),r=n.querySelector(".mayabot-entity-grid"),o=n.querySelector(".mayabot-entity-title"),i=t.length;if(jt=Array.isArray(t)?[...t]:[],Vt=e||Y,n.classList.remove("count-1","count-2","count-3","count-many"),n.classList.add(qo(i)),n.style.setProperty("--mayabot-entity-card-count",String(Go(i))),o.textContent=Vt,!i){r.innerHTML='<p class="mayabot-entity-empty">No matching records are currently available.</p>',n.classList.add("active"),ln();return}r.innerHTML=t.map(a=>`
        <article class="mayabot-entity-card" data-entity-id="${k(a.id)}">
          ${Qo(a)}
          <h3 class="mayabot-entity-name">${k(a.title)}</h3>
          <p class="mayabot-entity-meta">${k(a.subtitle||fn(a.entityType))}</p>
          <p class="mayabot-entity-summary">${k(a.summary||a.body||"Details are available on the website.")}</p>
          ${Xo(a)}
          ${Jo(a)}
        </article>
      `).join(""),r.querySelectorAll("[data-view-entity]").forEach(a=>{a.addEventListener("click",async()=>{await $t(a.getAttribute("data-view-entity"))})}),n.classList.add("active"),ln()}function Zo(t){if(!t)return!1;try{let e=new URL(t,window.location.origin);return e.origin===window.location.origin?(window.location.href=`${e.pathname}${e.search}${e.hash}`,!0):(window.open(e.toString(),"_blank","noopener,noreferrer"),!0)}catch{return!1}}function ln(){window.setTimeout(()=>{let t=document.getElementById("mayabot-chat"),e=document.getElementById("mayabot-msgs");e&&(e.innerHTML=""),t&&t.classList.remove("visible")},W)}async function $t(t){let e=await an(t);return Zo(e)}async function mn(t,e=Y){let n=zt({[d.ENTITY_IDS]:t});if(!n.length)return gt([],e),Yt([],[],"missing_entity_ids");try{let r=await Bt(n);return gt(r,e),Yt(n,r)}catch(r){return console.warn("[AI Hub Widget] Entity overlay failed:",r),gt([],e),Yt(n,[],"entity_overlay_fetch_failed")}}function zt(t){let e=t[d.ENTITY_IDS]||t.ids||t.items||[],n=new Set;return(Array.isArray(e)?e:[]).map(r=>String(r??"").trim()).filter(Boolean).filter(r=>n.has(r)?!1:(n.add(r),!0))}function _n(t={}){if(!jt.length)return!1;let e=String(t.sort_by||t.sortBy||"price_asc").trim().toLowerCase(),n=[...jt].sort((o,i)=>ti(o,i,e)),r=ni(Vt,e);return gt(n,r),!0}function ti(t,e,n){return n==="price_desc"?yt(e,ht)-yt(t,ht):n==="rating"?dn(e,ht)-dn(t,ht):n==="newest"?pn(e)-pn(t):yt(t,cn)-yt(e,cn)}function yt(t,e){return hn([t?.pricing?.price,t?.pricing?.amount,t?.pricing?.premium,t?.pricing?.premium_min,t?.pricing?.monthly_premium,t?.pricing?.annual_premium,t?.pricing?.min_price,t?.pricing?.starting_price,t?.attributes?.price,t?.attributes?.amount,t?.attributes?.premium,t?.attributes?.monthly_premium,t?.attributes?.annual_premium,t?.displayPrice],e)}function dn(t,e){return hn([t?.attributes?.rating,t?.attributes?.review_rating,t?.attributes?.stars,t?.availability?.rating],e)}function pn(t){let e=t?.attributes?.updated_at||t?.attributes?.date||t?.availability?.updated_at||"",n=Date.parse(String(e||""));return Number.isFinite(n)?n:0}function hn(t,e){for(let n of t){let r=ei(n);if(Number.isFinite(r))return r}return e}function ei(t){if(typeof t=="number")return t;let e=String(t??"").replace(/,/g,"").match(/-?\d+(?:\.\d+)?/);return e?Number(e[0]):Number.NaN}function ni(t,e){let n={price_asc:"sorted low to high",price_desc:"sorted high to low",rating:"sorted by rating",newest:"newest first"};return`${String(t||Y).replace(/\s+-\s+sorted.*$/i,"")} - ${n[e]||n.price_asc}`}function yn(t){return t.action===s.SHOW_ENTITIES||t.action===s.COMPARE_ENTITIES||t.action===s.OPEN_ENTITY_DETAIL||t.action===s.SORT_ENTITIES}async function gn(t){return t.action===s.SHOW_ENTITIES||t.action===s.COMPARE_ENTITIES?ri(t.parameters||{}):t.action===s.OPEN_ENTITY_DETAIL?$t(t.parameters?.[d.ENTITY_ID]||t.parameters?.id):t.action===s.SORT_ENTITIES?_n(t.parameters||{}):!1}function ri(t){return mn(zt(t),t[d.SEARCH_QUERY]||t.title||Y)}var rt="mayabot-handoff-panel",Tn="mayabot-handoff-overlay-styles",oi=Object.freeze(["contact","support","help"]),ii=Object.freeze(["checkout","cart"]),Sn=new Set([s.CHECKOUT_HANDOFF,s.HANDOFF_TO_ADVISOR,s.HANDOFF_TO_AGENT,s.HANDOFF_TO_CLINIC,s.HANDOFF_TO_HUMAN,s.HANDOFF_TO_LAWYER,s.HANDOFF_TO_LICENSED_AGENT,s.HANDOFF_TO_RECRUITER]),An=Object.freeze({[s.CHECKOUT_HANDOFF]:{title:"Checkout needs your confirmation",body:"This step may include payment or a secure checkout page. I can take you there, then you complete the final step yourself.",primary:"Open checkout"},[s.HANDOFF_TO_ADVISOR]:{title:"Advisor handoff",body:"This request needs a qualified advisor. I can open the contact path so the site team can continue.",primary:"Contact advisor"},[s.HANDOFF_TO_AGENT]:{title:"Agent handoff",body:"This step needs an agent or account-specific help. I can open the contact path for follow-up.",primary:"Contact agent"},[s.HANDOFF_TO_CLINIC]:{title:"Clinic handoff",body:"This request needs clinic confirmation. I can open the appointment or contact path for the next step.",primary:"Contact clinic"},[s.HANDOFF_TO_HUMAN]:{title:"Human handoff",body:"This step needs human confirmation. I can open the most relevant contact path.",primary:"Open contact"},[s.HANDOFF_TO_LAWYER]:{title:"Legal handoff",body:"This request needs a legal professional. I can open the consultation or contact path.",primary:"Contact lawyer"},[s.HANDOFF_TO_LICENSED_AGENT]:{title:"Licensed agent handoff",body:"This request needs a licensed agent. I can open the quote or contact path for follow-up.",primary:"Contact agent"},[s.HANDOFF_TO_RECRUITER]:{title:"Recruiter handoff",body:"This request needs recruiter review. I can open the application or contact path.",primary:"Contact recruiter"}});function q(t){return String(t??"").replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;").replace(/"/g,"&quot;").replace(/'/g,"&#039;")}function z(t){return String(t||"").trim()}function ai(){if(document.getElementById(Tn))return;let t=document.createElement("style");t.id=Tn,t.textContent=`
    #${rt} {
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
    #${rt}.active {
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
      #${rt} {
        bottom: 82px;
        width: min(calc(100vw - 20px), 420px);
      }
    }
  `,document.head.appendChild(t)}function si(){ai();let t=document.getElementById(rt);return t||(t=document.createElement("div"),t.id=rt,t.setAttribute("aria-live","polite"),document.body.appendChild(t),t)}function ci(){return window.AIHubAdapterRuntime?.config?.adapter?.routes||window.AIHubAdapter?.config?.adapter?.routes||{}}function ui(t,e){let n=En(e[d.URL]||e.path||e.href||e.handoff_flow?.page_url);if(n)return n;let r=ci(),o=t===s.CHECKOUT_HANDOFF?ii:oi;for(let i of o){let a=En(r[i]);if(a)return a}return""}function En(t){let e=z(t);if(!e)return"";try{let n=new URL(e,window.location.origin);return n.origin!==window.location.origin?"":`${n.pathname}${n.search}${n.hash}`||"/"}catch{return""}}function li(t){return An[t]||An[s.HANDOFF_TO_HUMAN]}function di(t){return t&&typeof t=="object"?t:{}}function pi(t,e){return z(t.title)||e}function fi(t,e,n){return z(e[d.MESSAGE])||z(t.handling)||n}function mi(t,e){return z(e[d.REASON]||e.reason||e.blocked_reason||t.key)}function _i(t){let e=[["Provider",t.provider_label||t.provider],["Boundary",t.automation_boundary],["Recovery",t.recovery],["Evidence",t.evidence],["Page",t.page_url]].filter(([,n])=>z(n));return e.length?`
    <p class="mayabot-handoff-meta">
      ${e.map(([n,r])=>`<span><strong>${q(n)}:</strong> ${q(r)}</span>`).join("")}
    </p>
  `:""}function bn(t){t.classList.remove("active")}function hi(){window.setTimeout(()=>{let t=document.getElementById("mayabot-chat"),e=document.getElementById("mayabot-msgs");e&&(e.innerHTML=""),t&&t.classList.remove("visible")},W)}function In(t,e={}){let n=z(t).toUpperCase(),r=li(n),o=di(e.handoff_flow),i=si(),a=ui(n,e),c=pi(o,r.title),p=fi(o,e,r.body),f=mi(o,e);return i.innerHTML=`
    <div class="mayabot-handoff-body">
      <div class="mayabot-handoff-top">
        <h2 class="mayabot-handoff-title">${q(c)}</h2>
        <button class="mayabot-handoff-close" type="button" aria-label="Close handoff">&times;</button>
      </div>
      <p class="mayabot-handoff-text">${q(p)}</p>
      ${_i(o)}
      ${f?`<p class="mayabot-handoff-reason">${q(f)}</p>`:""}
      <div class="mayabot-handoff-actions">
        <button type="button" class="secondary" data-close-handoff>Close</button>
        ${a?`<button type="button" data-open-handoff>${q(r.primary)}</button>`:""}
      </div>
    </div>
  `,i.querySelector(".mayabot-handoff-close")?.addEventListener("click",()=>bn(i)),i.querySelector("[data-close-handoff]")?.addEventListener("click",()=>bn(i)),i.querySelector("[data-open-handoff]")?.addEventListener("click",()=>{window.location.href=a}),i.classList.add("active"),hi(),!0}function wn(t){return Sn.has(t.action)}function On(t){return In(t.action,t.parameters||{})}function xn(t){return t.action===s.NAVIGATE_TO&&!!Nn(t.parameters?.[d.PAGE])}function Cn(t){return window.location.href=Nn(t.parameters?.[d.PAGE]),!0}function Nn(t){let e=String(t||"").trim();if(!e||vn(e)||/^https?:\/\//i.test(e))return"";if(e==="home"||e==="/")return"/";let n=yi(e);if(n)return n;let r=e.replace(/^\/+|\/+$/g,"");return r?`/${r}`:"/"}function yi(t){let e=window.AIHubAdapterRuntime?.config?.adapter?.routes||window.AIHubAdapter?.config?.adapter?.routes||{},n=gi(t);for(let r of n){let o=e[r],i=Rn(o);if(i)return i}for(let[r,o]of Object.entries(e)){if(!n.includes(Wt(r)))continue;let i=Rn(o);if(i)return i}return""}function gi(t){let e=Wt(t),n=String(t||"").trim().replace(/^\/+|\/+$/g,"").toLowerCase(),r=n.split("?")[0].split("#")[0].split("/").filter(Boolean).pop()||"";return Array.from(new Set([e,n,Wt(r)].filter(Boolean)))}function Wt(t){return String(t||"").trim().toLowerCase().replace(/[^a-z0-9/_\s-]+/g," ").replace(/[_-]+/g," ").replace(/\s+/g," ").trim().replace(/\s+/g,"-")}function Rn(t){let e=String(t||"").trim();if(!e||vn(e))return"";if(/^https?:\/\//i.test(e))try{let n=new URL(e);return n.origin!==window.location.origin?"":`${n.pathname||"/"}${n.search||""}${n.hash||""}`}catch{return""}return e.startsWith("/")?e:`/${e.replace(/^\/+/,"")}`}function vn(t){return/^(?:javascript:|data:|\/\/)/i.test(String(t||"").trim())}function Ln(t){let e=t?.params||t?.parameters||{};return{...t||{},action:String(t?.action||"").trim().toUpperCase(),params:e,parameters:e}}var qt="AIHubAdapterRuntime",Gt="AIHubAdapter";function Ti(t){let e=t?.params||t?.parameters||{};return{...t||{},params:e,parameters:e}}function ot(){return!!(window[qt]?.executeAction||window[Gt]?.handleAction)}async function Kt(t){return(await it(t)).succeeded}async function it(t){let e=Ti(t);if(window[qt]?.executeAction){let n=window[qt],r=await n.executeAction(e)===!0,o=n.lastActionResult||{};return{succeeded:r,handled:o.handled===!0||r,status:o.status||(r?"ok":"not_handled"),reason:o.reason||"",blocked:o.status==="blocked",disabled:o.status==="disabled"}}if(window[Gt]?.handleAction){let n=await window[Gt].handleAction(e)===!0;return{succeeded:n,handled:n,status:n?"ok":"not_handled",reason:"",blocked:!1,disabled:!1}}return{succeeded:!1,handled:!1,status:"missing_adapter",reason:"",blocked:!1,disabled:!1}}var Ai=Object.freeze([{path:"/api/products?per_page=96",routePrefix:"/product/"},{path:"/api/products",routePrefix:"/product/"},{path:"/api/products.json",routePrefix:""},{path:"/products.json",routePrefix:"/products/"},{path:"/collections/all/products.json",routePrefix:"/products/"}]),Ei=Object.freeze(["products","data","items","results"]),Dn=Object.freeze(["id","product_id","handle","sku"]),Un=Object.freeze(["name","title"]),bi=Object.freeze(["url","href","permalink","product_url"]),Si=Object.freeze(["image_url","imageUrl","image_src","imageSrc","image","images","media","thumbnail","thumbnail_url","featured_image","featuredImage","featured_image_url"]),Ii=Object.freeze(["brand","vendor"]),wi=Object.freeze(["category","category_name","product_type"]),Oi=Object.freeze(["description","summary","body_html"]),Ri=Object.freeze(["original_price","compare_at_price","regular_price"]),kn=Object.freeze(["currency","currency_code"]),xi=Object.freeze(["display_price","price_text","formatted_price"]),Ci="Unknown Brand",Ni="Products",vi="/",Li=/^[a-z0-9][a-z0-9-]*$/i,Qt=null;function R(t){return t==null||typeof t=="object"?"":String(t||"").trim()}function Zt(t){return R(t).toLowerCase().replace(/[^a-z0-9]+/g," ").trim()}function Mn(t){let e=new Set(["a","am","an","and","ask","asked","did","for","me","not","on","only","please","show","some","the","to","wanna","want","what","with","you","your"]),n=[],r=new Set;for(let o of Pi(Zt(t)).split(" ")){let i=Di(o);i.length<=1||e.has(i)||r.has(i)||(n.push(i),r.add(i))}return n}function Pi(t){return t.replace(/\b(?:i\s+)?did\s+not\s+ask\s+for\s+(?:a\s+|an\s+)?[a-z0-9]+\b/g," ")}function Di(t){return["phone","phones","mobile","mobiles"].includes(t)?"phone":["book","books"].includes(t)?"books":t}function te(t,e){return e.map(n=>R(t?.[n])).filter(Boolean)}function L(t,e){return te(t,e)[0]||""}function Tt(t){let e=R(t).replace(/,/g,"");if(!e)return 0;let n=e.match(/-?\d+(?:\.\d+)?/),r=Number(n?n[0]:e);return Number.isFinite(r)?r:0}function Ui(t,e){let n=L(t,xi);if(n)return n;let r=L(t,kn).toUpperCase();return e>0&&r?`${r} ${e.toLocaleString()}`:e>0?e.toLocaleString():""}function ki(t){for(let e of Si){let n=Xt(t?.[e]);if(n)return n}return""}function Xt(t){if(!t)return"";if(Array.isArray(t)){for(let e of t){let n=Xt(e);if(n)return n}return""}if(typeof t=="object"){for(let e of["src","url","image_url","imageUrl","image_src","imageSrc","thumbnail","thumbnail_url","featured_image","featuredImage","featured_image_url"]){let n=Xt(t[e]);if(n)return n}return""}return Mi(t)}function Mi(t){let e=R(t);if(!e||/^javascript:/i.test(e))return"";if(/^data:image\//i.test(e))return e;try{let n=new URL(e,window.location.origin);return["http:","https:"].includes(n.protocol)?n.toString():""}catch{return""}}function Fi(t){let e=R(t);if(!e)return"";try{let n=new URL(e,window.location.origin);return n.origin!==window.location.origin?"":`${n.pathname}${n.search}${n.hash}`}catch{return""}}function Hi(t,e,n){let r=Fi(L(t,bi));return r||(!Li.test(e)||!/[a-z]/i.test(e)||!n?.routePrefix?"":`${n.routePrefix}${encodeURIComponent(e)}${vi}`)}function ee(t,e={}){if(!t)return null;let n=L(t,Dn),r=R(t.handle||t.slug||t.product_handle),o=L(t,Un),i=Tt(t.price||t.amount||t.cost),a=Tt(L(t,Ri));return!n&&!r?null:{id:n,handle:r,name:o,title:R(t.title||o),brand:L(t,Ii)||Ci,category:L(t,wi)||Ni,description:L(t,Oi),price:Number.isFinite(i)?i:0,originalPrice:Number.isFinite(a)?a:0,displayPrice:Ui(t,i),currency:L(t,kn),rating:Tt(t.rating||t.review_rating),reviewCount:Tt(t.review_count||t.reviews_count||t.reviews),imageUrl:ki(t),url:Hi(t,r||n,e)}}function Bi(t){return te(t,Dn)}function Pn(t){return te(t,Un).map(Zt)}function Fn(t,e){let n=R(e);return!!(n&&Bi(t).includes(n))}function Hn(t,e){let n=Mn(e);if(!n.length)return!1;let r=Zt([t?.name,t?.title,t?.brand,t?.category,t?.category_name,t?.product_type,t?.description,t?.tags].join(" "));return n.every(o=>r.includes(o)||r.includes(o.replace(/s$/,"")))}function Yi(t,e){let n=new Set(Pn(e));return Pn(t).some(r=>n.has(r))}function ji(t,e){return!!(t?.imageUrl&&t.imageUrl===e?.imageUrl)}function Vi(t){if(Array.isArray(t))return t;for(let e of Ei){let n=t?.[e];if(Array.isArray(n))return n}return[]}async function $i(t){try{let e=await fetch(new URL(t.path,window.location.origin),{headers:{Accept:"application/json"}});if(!e.ok)return[];let n=await e.json();return Vi(n).map(r=>ee(r,t)).filter(Boolean)}catch(e){return console.warn(`[AI Hub Widget] Catalog endpoint lookup failed for ${t.path}:`,e),[]}}async function Jt(){return Qt||(Qt=Promise.all(Ai.map($i)).then(t=>t.flat())),Qt}async function zi(t,e=120){if(!Mn(t).length)return[];let r=new URL("/v1/products",l.apiUrl);r.searchParams.set("site_id",l.siteId),r.searchParams.set("limit",String(e));try{let o=await fetch(r.toString(),{headers:{Accept:"application/json"}});return o.ok?(await o.json()).map(i=>ee(i)).filter(Boolean).filter(i=>Hn(i,t)).slice(0,12):[]}catch(o){return console.warn("[AI Hub Widget] Hub product search fallback failed:",o),[]}}async function Bn(t,e=""){let n=(Array.isArray(t)?t:[]).map(R).filter(Boolean),r=[],o="",i="";if(n.length)try{r=await Yn(n),o="hub_by_ids"}catch(a){i="hub_product_lookup_failed",console.warn("[AI Hub Widget] Hub product ID lookup failed:",a)}if(!r.length&&n.length){let a=await Jt();r=n.map(c=>a.find(p=>Fn(p,c))).filter(Boolean),r.length&&(o="host_by_ids")}return!r.length&&e&&(r=await zi(e),r.length&&(o="hub_search")),!r.length&&e&&(r=(await Jt()).filter(c=>Hn(c,e)).slice(0,12),r.length&&(o="host_search")),{products:r,source:o,reason:r.length?"":i||"no_matching_products_rendered"}}async function Yn(t){let e=(Array.isArray(t)?t:[]).map(R).filter(Boolean);if(!e.length)return[];let n=new URL(C.PRODUCTS_BY_IDS,l.apiUrl);n.searchParams.set("site_id",l.siteId),n.searchParams.set("ids",e.join(","));let r=await fetch(n.toString(),{headers:{Accept:"application/json"}});if(!r.ok)throw new Error("Failed to fetch products from AI Hub API");let o=(await r.json()).map(a=>ee(a)).filter(Boolean),i=new Map(o.map(a=>[String(a.id),a]));return e.map(a=>i.get(a)).filter(Boolean)}async function At(t){let e=R(t);if(!e)return"";let[n]=await Yn([e]);if(n?.url)return n.url;let r=await Jt(),o=r.find(a=>Fn(a,e));return o?.url?o.url:n&&r.find(a=>Yi(a,n)||ji(a,n))?.url||""}var Wi=["data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='320' height='240' viewBox='0 0 320 240'%3E","%3Crect width='320' height='240' fill='%23f1f2ee'/%3E","%3Cpath d='M98 156h124l-31-40-25 30-17-22-51 32Z' fill='%23c8c3ba'/%3E","%3Ccircle cx='117' cy='95' r='17' fill='%23d8d3ca'/%3E","%3Ctext x='160' y='198' text-anchor='middle' fill='%23686660' font-family='Arial,sans-serif' font-size='16'%3EImage pending%3C/text%3E","%3C/svg%3E"].join(""),jn=12,re=[],oe=U,$n=new Map;function j(t){return String(t??"").replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;").replace(/"/g,"&quot;").replace(/'/g,"&#039;")}function qi(){if(document.getElementById("mayabot-product-overlay-styles"))return;let t=document.createElement("style");t.id="mayabot-product-overlay-styles",t.textContent=`
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
    /* Facts scroll inside the card so Add/View stay reachable on short screens. */
    .mayabot-product-facts {
      margin: 0;
      display: grid;
      gap: 6px;
      overflow: auto;
      max-height: 190px;
      flex: 1 1 auto;
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
  `,document.head.appendChild(t)}function Gi(){qi();let t=document.getElementById("mayabot-product-panel");return t||(t=document.createElement("div"),t.id="mayabot-product-panel",t.setAttribute("aria-live","polite"),t.innerHTML=`
    <div class="mayabot-product-header">
      <h2 class="mayabot-product-title">${U}</h2>
      <button class="mayabot-product-close" type="button" aria-label="Close recommendations">&times;</button>
    </div>
    <div class="mayabot-product-grid"></div>
  `,t.querySelector(".mayabot-product-close").addEventListener("click",()=>{t.classList.remove("active")}),document.body.appendChild(t),t)}async function Ki(t){let e={action:s.ADD_TO_CART,params:{[d.PRODUCT_ID]:t,[d.QUANTITY]:Ut},parameters:{[d.PRODUCT_ID]:t,[d.QUANTITY]:Ut}};ot()&&await Kt(e)||window.dispatchEvent(new CustomEvent(tt.MAYABOT_ACTION,{detail:e}))}async function Qi(t){try{let n=await At(t);if(n){window.location.href=n;return}}catch(n){console.warn("[AI Hub Widget] Product detail URL lookup failed:",n)}let e={action:s.SHOW_PRODUCT_DETAIL,params:{[d.PRODUCT_ID]:t},parameters:{[d.PRODUCT_ID]:t}};ot()&&await Kt(e)||window.dispatchEvent(new CustomEvent(tt.MAYABOT_ACTION,{detail:e}))}function Xi(t){return t<=1?"count-1":t===2?"count-2":t===3?"count-3":"count-many"}function Ji(t){return t<=1?1:t===2?2:3}function Zi(t){let e=new Set;return(Array.isArray(t)?t:[]).map(n=>String(n??"").trim()).filter(Boolean).filter(n=>e.has(n)?!1:(e.add(n),!0))}function ne(t,e,n="",r={}){let o=(Array.isArray(e)?e:[]).map(p=>String(p?.id??"").trim()).filter(Boolean),i=o.length,a=t.length,c=i>0?"succeeded":"failed";return{status:c,stage:"product_overlay",reason:n||(c==="succeeded"?"":"no_matching_products_rendered"),evidence:{requested_product_count:a,rendered_product_count:i,missing_product_count:Math.max(a-i,0),requested_product_ids:t.slice(0,jn).join(","),rendered_product_ids:o.slice(0,jn).join(","),lookup_source:r.source||"",search_query:r.searchQuery||""}}}function ta(t){let e=String(t?.displayPrice||"").trim();if(e)return e;let n=Number(t?.price||0);return Number.isFinite(n)&&n>0?n.toLocaleString():"Price unavailable"}var ea=6,na=24,ra=120;function oa(t){let e=new Map;return Array.isArray(t)&&t.forEach(n=>{if(!n||typeof n!="object")return;let r=String(n.product_id||"").trim();if(!r||!Array.isArray(n.facts))return;let o=n.facts.filter(i=>i&&typeof i=="object"&&i.label&&i.value).slice(0,ea).map(i=>({label:String(i.label).slice(0,na),value:String(i.value).slice(0,ra)}));o.length&&e.set(r,o)}),e}function ia(t){let e=$n.get(String(t));return!e||!e.length?"":`<dl class="mayabot-product-facts">${e.map(r=>`<div class="mayabot-fact"><dt>${j(r.label)}</dt><dd>${j(r.value)}</dd></div>`).join("")}</dl>`}function Et(t,e){let n=Gi(),r=n.querySelector(".mayabot-product-grid"),o=n.querySelector(".mayabot-product-title"),i=t.length;if(re=Array.isArray(t)?[...t]:[],oe=e||U,n.classList.remove("count-1","count-2","count-3","count-many"),n.classList.add(Xi(i)),n.style.setProperty("--mayabot-card-count",String(Ji(i))),o.textContent=oe,!i){r.innerHTML='<p class="mayabot-product-empty">No matching products are currently available.</p>',n.classList.add("active");return}r.innerHTML=t.map(a=>{let c=j(a.id);return`
        <article class="mayabot-product-card" data-product-id="${c}">
          <img class="mayabot-product-image" src="${j(a.imageUrl||Wi)}" alt="${j(a.name)}">
          <h3 class="mayabot-product-name">${j(a.name||a.title||"Product")}</h3>
          <p class="mayabot-product-meta">${j(a.brand)} - ${j(ta(a))}</p>
          ${ia(a.id)}
          <div class="mayabot-product-actions">
            <button type="button" data-add="${c}">Add</button>
            <button type="button" class="secondary" data-view="${c}">View</button>
          </div>
        </article>
      `}).join(""),r.querySelectorAll("[data-add]").forEach(a=>{a.addEventListener("click",async()=>{await Ki(a.getAttribute("data-add"))})}),r.querySelectorAll("[data-view]").forEach(a=>{a.addEventListener("click",async()=>{await Qi(a.getAttribute("data-view"))})}),n.classList.add("active"),t.length>0&&aa()}function aa(){window.setTimeout(()=>{let t=document.getElementById("mayabot-chat"),e=document.getElementById("mayabot-msgs");e&&(e.innerHTML=""),t&&t.classList.remove("visible")},W)}async function zn(t,e=U,n={}){let r=Zi(t),o=String(n.searchQuery||"").trim();if($n=oa(n.comparisonFacts),!r.length&&!o)return Et([],e),ne([],[],"missing_product_ids");try{let{products:i,source:a,reason:c}=await Bn(r,o);return Et(i,e),ne(r,i,c,{source:a,searchQuery:o})}catch(i){return console.warn("[AI Hub Widget] Product overlay failed:",i),Et([],e),ne(r,[],"product_overlay_fetch_failed",{searchQuery:o})}}function Wn(t={}){if(!re.length)return!1;let e=String(t.sort_by||t.sortBy||"price_asc").trim().toLowerCase(),n=[...re].sort((r,o)=>sa(r,o,e));return Et(n,ca(oe,e)),!0}function sa(t,e,n){return n==="price_desc"?G(e.price,Number.NEGATIVE_INFINITY)-G(t.price,Number.NEGATIVE_INFINITY):n==="rating"?G(e.rating||e.review_rating,Number.NEGATIVE_INFINITY)-G(t.rating||t.review_rating,Number.NEGATIVE_INFINITY):n==="newest"?Vn(e)-Vn(t):G(t.price,Number.POSITIVE_INFINITY)-G(e.price,Number.POSITIVE_INFINITY)}function G(t,e){let n=String(t??"").replace(/,/g,"").match(/-?\d+(?:\.\d+)?/);if(!n)return e;let r=Number(n[0]);return Number.isFinite(r)?r:e}function Vn(t){let e=t?.updated_at||t?.created_at||t?.date||"",n=Date.parse(String(e||""));return Number.isFinite(n)?n:0}function ca(t,e){let n={price_asc:"sorted low to high",price_desc:"sorted high to low",rating:"sorted by rating",newest:"newest first"};return`${String(t||U).replace(/\s+-\s+sorted.*$/i,"")} - ${n[e]||n.price_asc}`}function Gn(t){return t.action===s.SHOW_PRODUCTS||t.action===s.SHOW_COMPARISON||t.action===s.SHOW_PRODUCT_DETAIL||t.action===s.SORT_PRODUCTS}async function Kn(t){return t.action===s.SHOW_COMPARISON?qn(t.parameters||{},"Product comparison",{syncListing:!1,comparisonFacts:(t.parameters||{}).comparison}):t.action===s.SHOW_PRODUCTS?qn(t.parameters||{},U):t.action===s.SHOW_PRODUCT_DETAIL?da(t.parameters||{}):t.action===s.SORT_PRODUCTS?Wn(t.parameters||{}):!1}async function qn(t,e=U,n={}){let r=Array.isArray(t[d.PRODUCT_IDS])?t[d.PRODUCT_IDS]:[],o=la(t),a=n.syncListing!==!1?await ua(o):{succeeded:!1,handled:!1,status:"skipped",stage:"product_display_sync",reason:"comparison_overlay"},c=await zn(r,t.title||o||e,{searchQuery:o,comparisonFacts:n.comparisonFacts}),p={...c.evidence||{},listing_sync_status:a.status||"",listing_sync_stage:a.stage||"",listing_sync_reason:a.reason||""};return c.status!=="succeeded"?{...c,evidence:p}:o&&a.handled&&!a.succeeded?{status:"failed",stage:"product_display_sync",reason:a.reason||a.status||"listing_sync_failed",evidence:p}:{...c,stage:a.succeeded?"product_display_sync":c.stage,evidence:p}}async function ua(t){let e=Qn(t);return e?it({action:s.FILTER_PRODUCTS,params:{[d.SEARCH_QUERY]:e,query:e,q:e}}):{succeeded:!1,handled:!1,status:"skipped",stage:"product_display_sync",reason:"missing_search_query"}}function la(t){return Qn(t[d.SEARCH_QUERY]||t.search||t.query||t.q||"")}function Qn(t){return String(t||"").trim()}async function da(t){let e="";try{e=await At(t[d.PRODUCT_ID])}catch(n){return console.warn("[AI Hub Widget] Product detail URL lookup failed:",n),!1}return e?(window.location.href=e,!0):!1}var ie="stop_action_fallback",pa=new Set([s.SHOW_PRODUCTS,s.SHOW_COMPARISON,s.SHOW_PRODUCT_DETAIL,s.SORT_PRODUCTS]);function Xn(t){return ot()&&!pa.has(t.action)}async function Jn(t){let e=await it(t);return e.succeeded?!0:e.blocked||e.disabled?ie:!1}function Zn(t){return window.dispatchEvent(new CustomEvent(tt.MAYABOT_ACTION,{detail:t})),{status:"requested",stage:"browser_event",reason:"event_dispatched_without_confirmation"}}var fa=12,ma=8,_a=80,tr=Object.freeze([["data-entity-id",""],["data-product-id","product"],["data-listing-id","listing"],["data-offer-id","offer"],["data-plan-id","plan"],["data-item-id",""]]),ha="data-entity-type",ya="entity",er=Object.freeze(["sort","sort_by","sortby","orderby","order_by","order"]),ga=Object.freeze(["page","p","offset","cursor","q","query","search","token","session","email","phone","name","address","utm_source","utm_medium","utm_campaign"]),Ta=Object.freeze([["price","[data-price], [itemprop='price'], .price"],["rating","[data-rating], [itemprop='ratingValue'], .rating"],["availability","[data-availability], [itemprop='availability'], .availability, .stock"]]);function P(t){return String(t||"").replace(/\s+/g," ").trim().slice(0,_a)}function Aa(t){if(!t||typeof t.getBoundingClientRect!="function")return!1;let e=t.getBoundingClientRect();if(e.width<=0||e.height<=0)return!1;let n=t.ownerDocument?.defaultView,r=n?.getComputedStyle?.(t);if(r&&(r.visibility==="hidden"||r.display==="none"))return!1;let o=t.ownerDocument?.documentElement,i=Number(n?.innerWidth||o?.clientWidth||0),a=Number(n?.innerHeight||o?.clientHeight||0);return i>0&&a>0&&e.bottom>0&&e.right>0&&e.top<a&&e.left<i}function Ea(t){for(let[e,n]of tr){let r=P(t.getAttribute(e));if(r)return{id:r,impliedType:n}}return null}function ba(t,e){return P(t.getAttribute(ha)).toLowerCase()||e||ya}function Sa(t){let e=t.querySelector?.("h1, h2, h3, h4, [data-entity-name], [itemprop='name']");return P(e?.textContent||t.getAttribute("aria-label")||t.getAttribute("title"))}function Ia(t){let e=t.matches?.("a[href]")?t:t.querySelector?.("a[href]");return va(e?.href||"")}function wa(t){let e={};for(let[n,r]of Ta){let o=t.querySelector?.(r);if(!o)continue;let i=P(o.getAttribute?.("content")||o.getAttribute?.(`data-${n}`)||o.textContent);i&&(e[n]=i)}return e}function Oa(){return tr.map(([t])=>`[${t}]`).join(",")}function Ra(){let t=new Set,e=[];for(let n of et(Oa())){if(e.length>=fa)break;let r=Ea(n);!r||t.has(r.id)||!Aa(n)||(t.add(r.id),e.push({id:r.id,entity_type:ba(n,r.impliedType),label:Sa(n),route:Ia(n),facts:wa(n)}))}return e}function xa(){let t=nr();if(!t)return{};let e={};for(let[n,r]of t.entries()){let o=n.toLowerCase();if(!(ga.includes(o)||er.includes(o))){if(Object.keys(e).length>=ma)break;e[P(n)]=P(r)}}return e}function Ca(){let t=nr();for(let n of er){let r=P(t?.get?.(n));if(r)return r}let e=et("select[name*='sort' i], select[id*='sort' i]")[0];return P(e?.value)}function Na(){try{return{path:P(window.location.pathname)||"/",search:P(window.location.search)}}catch{return{path:"",search:""}}}function bt(){return{route:Na(),filters:xa(),sort:Ca(),visible_entities:Ra()}}function nr(){try{return new URLSearchParams(window.location.search)}catch{return null}}function va(t){if(!t)return"";try{let e=new URL(t,window.location.origin);return e.origin!==window.location.origin?"":`${e.pathname}${e.search}`||"/"}catch{return""}}var zc=Object.freeze(["CHECKOUT","CLEAR_CART","REMOVE_FROM_CART","UPDATE_CART_QUANTITY","CLEAR_HISTORY","SUBMIT_PAYMENT","PLACE_ORDER"]);var y=Object.freeze({DISPLAY:"display",NAVIGATION:"navigation",DETAIL:"detail",FILTER:"filter",SORT:"sort",CART:"cart",NONE:"none"}),La=1200,Pa=60,Da=Object.freeze({SHOW_PRODUCTS:y.DISPLAY,SHOW_ENTITIES:y.DISPLAY,SHOW_COMPARISON:y.DISPLAY,COMPARE_ENTITIES:y.DISPLAY,NAVIGATE_TO:y.NAVIGATION,SHOW_PRODUCT_DETAIL:y.DETAIL,OPEN_ENTITY_DETAIL:y.DETAIL,FILTER_PRODUCTS:y.FILTER,CLEAR_FILTERS:y.FILTER,SORT_PRODUCTS:y.SORT,SORT_ENTITIES:y.SORT,ADD_TO_CART:y.CART,REMOVE_FROM_CART:y.CART,UPDATE_CART_QUANTITY:y.CART,CLEAR_CART:y.CART}),Ua="[data-cart-count], [data-testid='cart-count'], .cart-count, #cart-count";function or(t){return Da[String(t||"").toUpperCase()]||y.NONE}function ce(){let t=bt();return{path:t.route.path,search:t.route.search,filters:t.filters,sort:String(t.sort||"").toLowerCase(),visibleIds:t.visible_entities.map(e=>String(e.id)),cartCount:ka()}}function ka(){let t=document.querySelector(Ua);if(!t)return null;let e=t.getAttribute("data-cart-count")??t.textContent,n=Number.parseInt(String(e||"").replace(/[^\d-]/g,""),10);return Number.isFinite(n)?n:null}function ir(t){let e=[];for(let n of["product_ids","entity_ids"])Array.isArray(t[n])&&e.push(...t[n].map(String));for(let n of["product_id","entity_id"])t[n]&&e.push(String(t[n]));return e}function at(t){let e=String(t||"").split("?")[0].split("#")[0];return e.length>1?e.replace(/\/+$/,""):e}function ae(t){return String(t||"").trim().toLowerCase().replace(/[^a-z0-9/_\s-]+/g," ").replace(/[_-]+/g," ").replace(/\s+/g," ").trim().replace(/\s+/g,"-")}function rr(t){let e=String(t||"").trim();if(!e||/^(?:javascript:|data:|\/\/)/i.test(e))return"";try{let n=new URL(e,window.location.origin);return n.origin!==window.location.origin?"":at(n.pathname||"/")}catch{return""}}function Ma(t){let e=String(t||"").trim();if(!e)return"";if(e==="/"||ae(e)==="home")return"/";let n=window.AIHubAdapterRuntime?.config?.adapter?.routes||window.AIHubAdapter?.config?.adapter?.routes||{},r=ae(e);for(let[o,i]of Object.entries(n)){if(ae(o)!==r)continue;let a=rr(i);if(a)return a}return e.startsWith("/")||/^https?:\/\//i.test(e)?rr(e):at(`/${r}`)}function Fa(t,e){let n=ir(t);return n.length?n.filter(o=>!e.visibleIds.includes(o)).length?{satisfied:!1,reason:"requested_records_not_visible"}:{satisfied:!0,reason:""}:e.visibleIds.length>0?{satisfied:!0,reason:""}:{satisfied:!1,reason:"nothing_visible"}}function Ha(t,e,n){let r=Ma(t.page),o=at(e.path);return r&&o===r?{satisfied:!0,reason:""}:!r&&o!==at(n.path)?{satisfied:!0,reason:""}:r&&o!==at(n.path)?{satisfied:!1,reason:"wrong_route"}:{satisfied:!1,reason:"route_unchanged"}}function Ba(t,e,n){let r=ir(t)[0];return r?`${e.path}${e.search}`.includes(r)?{satisfied:!0,reason:""}:e.visibleIds.includes(r)&&e.path!==n.path?{satisfied:!0,reason:""}:{satisfied:!1,reason:"record_not_opened"}:{satisfied:!1,reason:"no_record_requested"}}function Ya(t,e,n){if(t==="CLEAR_FILTERS")return Object.keys(n.filters).length===0?{satisfied:!0,reason:""}:{satisfied:!1,reason:"filters_still_active"};let r=new Map(Object.entries(n.filters).map(([p,f])=>[p.toLowerCase(),se(f)])),o=e.filters&&typeof e.filters=="object"?e.filters:e,i=new Set(["product_ids","entity_ids","page","search_query","query","q","request_id"]),a=Object.entries(o||{}).filter(([p,f])=>!i.has(p.toLowerCase())&&se(f));return a.length?a.every(([p,f])=>{let g=r.get(p.toLowerCase());return g!==void 0&&g===se(f)})?{satisfied:!0,reason:""}:{satisfied:!1,reason:"filter_value_mismatch"}:r.size>0?{satisfied:!0,reason:""}:{satisfied:!1,reason:"no_filter_observed"}}function se(t){return(Array.isArray(t)?t:[t]).map(n=>String(n??"").trim().toLowerCase()).filter(Boolean).sort().join(",")}function ja(t,e,n){let r=String(t.sort_by||"").toLowerCase();return r&&e.sort&&e.sort.includes(r.split("_")[0])?{satisfied:!0,reason:""}:e.visibleIds.join(",")!==n.visibleIds.join(",")?{satisfied:!0,reason:""}:{satisfied:!1,reason:"order_unchanged"}}function Va(t,e,n){if(n.cartCount===null||e.cartCount===null)return{satisfied:!1,reason:"cart_state_unobservable"};let r=e.cartCount>n.cartCount,o=e.cartCount<n.cartCount;return t==="ADD_TO_CART"?r?{satisfied:!0,reason:""}:{satisfied:!1,reason:"cart_unchanged"}:t==="REMOVE_FROM_CART"?o?{satisfied:!0,reason:""}:{satisfied:!1,reason:"cart_unchanged"}:t==="CLEAR_CART"?e.cartCount===0?{satisfied:!0,reason:""}:{satisfied:!1,reason:"cart_not_empty"}:e.cartCount!==n.cartCount?{satisfied:!0,reason:""}:{satisfied:!1,reason:"cart_unchanged"}}function $a(t,e,n){let r=String(t?.action||"").toUpperCase(),o=t?.parameters||t?.params||{},i=or(r);return i===y.DISPLAY?Fa(o,e):i===y.NAVIGATION?Ha(o,e,n):i===y.DETAIL?Ba(o,e,n):i===y.FILTER?Ya(r,o,e):i===y.SORT?ja(o,e,n):i===y.CART?Va(r,e,n):{satisfied:!0,reason:"no_postcondition"}}async function ar(t,e){let n=or(t?.action);if(n===y.NONE)return{family:n,verified:!0,reason:"no_postcondition"};let r=Date.now()+La,o={satisfied:!1,reason:"not_observed"};for(;Date.now()<r&&(o=$a(t,ce(),e),!o.satisfied);)await za(Pa);return{family:n,verified:o.satisfied,reason:o.reason}}function za(t){return new Promise(e=>window.setTimeout(e,t))}var Wa=Object.freeze([{name:"runtime_adapter",canExecute:Xn,execute:Jn},{name:"product_overlay",canExecute:Gn,execute:Kn},{name:"entity_overlay",canExecute:yn,execute:gn},{name:"handoff_overlay",canExecute:wn,execute:On},{name:"platform_adapter",canExecute:()=>!0,execute:$e},{name:"provider_adapter",canExecute:en,execute:nn},{name:"navigation",canExecute:xn,execute:Cn},{name:"browser_event",canExecute:()=>!0,execute:Zn}]);async function le(t){let e=[];for(let n of t||[]){let r=Ln(n),o=await qa(r);o&&e.push(o)}return e}async function qa(t){if(!t.action)return;let e=Date.now(),n=window.location.href,r=ce();await ft(l.apiUrl,l.siteId,t,{status:"requested",stage:"widget_dispatch",requested_url:n,final_url:n,evidence:ue(t,n,n)}),await ft(l.apiUrl,l.siteId,t,{status:"executing",stage:"widget_dispatch",requested_url:n,final_url:window.location.href,evidence:ue(t,n,window.location.href)});let o;try{o=await Ga(t)}catch(p){o={status:"failed",stage:"widget_dispatch",reason:p instanceof Error?p.message:"execution_error"}}let i=o.status==="succeeded"?await ar(t,r):{family:"none",verified:!1,reason:o.reason||"execution_failed"},a=window.location.href,c={...ue(t,n,a,o),postcondition_family:i.family,postcondition_verified:i.verified,postcondition_reason:i.reason};return await ft(l.apiUrl,l.siteId,t,{status:o.status,stage:o.stage,reason:o.reason,duration_ms:Date.now()-e,requested_url:n,final_url:a,evidence:c}),{action:t.action,request_id:t.request_id||t.action_request_id||"",turn_id:t.turn_id||"",sequence:Number(t.sequence||0),status:o.status,stage:o.stage,reason:o.reason,verified:i.verified,postcondition:i.family,requested_url:n,final_url:a,evidence:c}}async function Ga(t){if(!t.action)return{status:"failed",stage:"normalization",reason:"missing_action"};for(let e of Wa){if(!e.canExecute(t))continue;let n=await e.execute(t),r=Ka(n,e.name);if(r)return r}return{status:"failed",stage:"all",reason:"no_executor_succeeded"}}function Ka(t,e){if(t===!0)return{status:"succeeded",stage:e,reason:""};if(t===ie)return{status:"blocked",stage:e,reason:"action_blocked"};if(!t||typeof t!="object")return null;let n=String(t.status||"").trim().toLowerCase();return n?{status:n,stage:String(t.stage||e).trim()||e,reason:String(t.reason||"").trim(),evidence:t.evidence&&typeof t.evidence=="object"?t.evidence:{}}:null}function ue(t,e,n,r={}){let o=t.parameters||t.params||{},i={requested_url:e,final_url:n,url_changed:e!==n,path_changed:sr(e)!==sr(n),title:document.title||"",stage:r.stage||"",result_status:r.status||""};return o.page&&(i.target_page=o.page),o.product_id&&(i.product_id=o.product_id),o.entity_id&&(i.entity_id=o.entity_id),Array.isArray(o.product_ids)&&(i.product_count=o.product_ids.length),Array.isArray(o.entity_ids)&&(i.entity_count=o.entity_ids.length),{...i,...r.evidence&&typeof r.evidence=="object"?r.evidence:{}}}function sr(t){try{return new URL(t,window.location.href).pathname}catch{return""}}var Qa=1,Xa=1.08,Ja=300,Za=Object.freeze(["hannah","sonia","libby","ava","susan","hazel","heera","salli","joanna","amy","emma","olivia","natasha","zira","aria","jenny","samantha","victoria","tessa","moira","karen","female","woman","nova","shimmer","google us english","microsoft aria"]),M="",St="",st=null,de=0;function ct(t){if(!("speechSynthesis"in window)||!("SpeechSynthesisUtterance"in window))return!1;It();let e=++de;M=t;let n=()=>{if(e!==de||M!==t)return!1;try{let r=new SpeechSynthesisUtterance(t),o=ts(window.speechSynthesis.getVoices());return o?(o&&(r.voice=o),r.rate=Qa,r.pitch=Xa,r.onstart=cr,r.onend=cr,It(),window.speechSynthesis.cancel(),window.speechSynthesis.resume(),window.speechSynthesis.speak(r),!0):(M="",!1)}catch{return!1}};return window.speechSynthesis.getVoices().length>0?n():(window.speechSynthesis.onvoiceschanged=n,st=window.setTimeout(()=>{st=null,n()},Ja),!0)}function wt(){M&&ct(M)}function ur(){try{return!!M||!!window.speechSynthesis?.speaking||!!window.speechSynthesis?.pending}catch{return!!M}}function lr(){de+=1,It(),M="",St="";try{window.speechSynthesis?.cancel()}catch{}}function ts(t){if(!Array.isArray(t)||t.length===0)return null;let e=es(t)||ns(t);return e&&(St=e.name),e}function es(t){if(St){let n=t.find(r=>r.name===St);if(n)return n}let e=String(l.speechVoiceName||"").toLowerCase();return e&&t.find(n=>n.name.toLowerCase()===e)||null}function ns(t){return l.speechVoicePreference.toLowerCase()!=="female"?t.find(e=>e.default)||t[0]:t.find(e=>Za.some(n=>e.name.toLowerCase().includes(n)))||null}function cr(){It(),M=""}function It(){st&&window.clearTimeout(st),st=null,window.speechSynthesis&&(window.speechSynthesis.onvoiceschanged=null)}var m=Object.freeze({NETWORK:"network",TIMEOUT:"timeout",ACCESS_DENIED:"access_denied",INVALID_REQUEST:"invalid_request",PAYLOAD_TOO_LARGE:"payload_too_large",UNSUPPORTED_MEDIA:"unsupported_media",RATE_LIMITED:"rate_limited",PROVIDER_UNAVAILABLE:"provider_unavailable",SERVER_ERROR:"server_error",MICROPHONE:"microphone",UNKNOWN:"unknown"}),dr=Object.freeze({[m.NETWORK]:"Connection issue",[m.TIMEOUT]:"Timed out",[m.ACCESS_DENIED]:"Access denied",[m.INVALID_REQUEST]:"Try again",[m.PAYLOAD_TOO_LARGE]:"Recording too long",[m.UNSUPPORTED_MEDIA]:"Audio not supported",[m.RATE_LIMITED]:"Service busy",[m.PROVIDER_UNAVAILABLE]:"Service unavailable",[m.SERVER_ERROR]:"Service error",[m.MICROPHONE]:"Mic unavailable",[m.UNKNOWN]:"Try again"}),pr=64,S=class extends Error{constructor(e,{status:n=0,code:r="",requestId:o="",stage:i=""}={}){super(`voice_transport_${e}`),this.name="VoiceTransportError",this.category=e,this.status=Number(n)||0,this.code=String(r||"").slice(0,pr),this.requestId=String(o||"").slice(0,pr),this.stage=i}get customerMessage(){return rs(this.category)}toDiagnostics(){return{category:this.category,status:this.status,code:this.code,request_id:this.requestId,stage:this.stage}}};function rs(t){return dr[t]||dr[m.UNKNOWN]}function os(t){let e=Number(t)||0;return e===401||e===403?m.ACCESS_DENIED:e===408?m.TIMEOUT:e===413?m.PAYLOAD_TOO_LARGE:e===415?m.UNSUPPORTED_MEDIA:e===429?m.RATE_LIMITED:e===502||e===503||e===504?m.PROVIDER_UNAVAILABLE:e>=500?m.SERVER_ERROR:e>=400?m.INVALID_REQUEST:m.UNKNOWN}function ut(t){if(t instanceof S)return t;let e=String(t?.message||t||"").toLowerCase();return t?.name==="AbortError"||e.includes("abort")||e.includes("timeout")||e.includes("timed out")?new S(m.TIMEOUT):e.includes("microphone")||e.includes("permission")||e.includes("notallowed")?new S(m.MICROPHONE):t?.name==="TypeError"||e.includes("failed to fetch")||e.includes("network")||e.includes("load failed")?new S(m.NETWORK):new S(m.UNKNOWN)}function fr(t,e=null){let n=Number(t?.status)||0,r=t?.headers?.get?.("x-request-id")||t?.headers?.get?.("x-correlation-id")||"",o=e&&typeof e=="object"&&(e.code||e.error_code)||"",i=/^[A-Za-z0-9_.:-]{1,64}$/.test(String(o||""))?String(o):"";return new S(os(n),{status:n,code:i,requestId:r,stage:"http_response"})}var is="/v1/widget/runtime-event",as=16;function x(t={}){let e=JSON.stringify({site_id:l.siteId,origin:window.location.origin,occurred_at:new Date().toISOString(),session_id:l.sessionId,request_id:F(t.request_id,80),component:F(t.component||"voice",60),stage:F(t.stage,80),event_type:F(t.event_type||"runtime_event",80),severity:F(t.severity||"info",20),status:F(t.status||"ok",20),message_code:F(t.message_code,80),duration_ms:mr(t.duration_ms),metadata:ss(t.metadata)}),n=new URL(is,l.apiUrl).toString();fetch(n,{method:"POST",headers:{Accept:"application/json","Content-Type":"application/json"},body:e,keepalive:!0}).catch(()=>{})}function ss(t){if(!t||typeof t!="object"||Array.isArray(t))return{};let e={};for(let[n,r]of Object.entries(t).slice(0,as)){let o=F(n,60).toLowerCase();!o||cs(o)||(typeof r=="boolean"||r===null?e[o]=r:typeof r=="number"?e[o]=mr(r):typeof r=="string"&&(e[o]=F(r,120)))}return e}function cs(t){return["audio","transcript","response","error","exception","token","secret"].some(e=>t.includes(e))}function F(t,e){return String(t||"").replace(/\s+/g," ").trim().slice(0,e)}function mr(t){let e=Number(t||0);return Number.isFinite(e)?Math.max(0,e):0}var us=3,ls="AIHubAdapterRuntime",ds="AIHubAdapter";function ps(t,e){let n=new URL(C.SHOP_WS,t);return n.protocol=n.protocol==="https:"?"wss:":"ws:",n.searchParams.set("site_id",e),n.searchParams.set("session_id",l.sessionId),n.toString()}function fs(t){return new Promise((e,n)=>{let r=new FileReader;r.onloadend=()=>{let o=String(r.result||"");e(o.includes(",")?o.split(",").pop():o)},r.onerror=()=>n(r.error||new Error("Failed to read audio blob")),r.readAsDataURL(t)})}var pe=class{constructor(){this.queue=[],this.blocked=[],this.playing=!1,this.current=null,this.lastPlaybackStartMs=0,this.installUnlockListeners()}push(e,n=""){e&&(this.queue.push({audioB64:e,fallbackText:n}),this.playNext())}playNext(){if(this.playing||this.queue.length===0)return;this.playing=!0;let e=this.queue.shift(),n=new Audio(Z.DATA_WAV_PREFIX+e.audioB64);n.preload="auto",this.current=n,n.onplay=()=>{this.lastPlaybackStartMs=typeof performance<"u"?performance.now():0},n.onended=()=>{this.current=null,this.playing=!1,this.playNext()},n.onerror=()=>{this.current=null,e.fallbackText&&K(e.fallbackText),this.playing=!1,this.playNext()},n.play().catch(r=>{if(console.warn("Audio playback failed",r),this.current=null,this.isAutoplayBlocked(r)){e.fallbackText?K(e.fallbackText):this.blocked.unshift(e),this.playing=!1;return}e.fallbackText&&K(e.fallbackText),this.playing=!1,this.playNext()})}installUnlockListeners(){if(typeof window>"u")return;let e=()=>{this.retryBlocked(),wt()};window.addEventListener("pointerdown",e,{capture:!0,passive:!0}),window.addEventListener("keydown",e,{capture:!0}),window.addEventListener("touchstart",e,{capture:!0,passive:!0})}retryBlocked(){this.blocked.length&&(this.queue.unshift(...this.blocked.splice(0)),this.playNext())}speakInsteadOfBlocked(e){!e||!this.blocked.length||(this.blocked=[],K(e))}isAutoplayBlocked(e){let n=`${e?.name||""} ${e?.message||e||""}`.toLowerCase();return n.includes("notallowed")||n.includes("user didn't interact")||n.includes("not allowed")}stop(){if(this.queue=[],this.blocked=[],this.current){try{this.current.pause(),this.current.currentTime=0}catch{}this.current.onended=null,this.current.onerror=null,this.current=null}this.playing=!1,lr()}isSpeaking(){return this.playing||this.queue.length>0||ur()}},Ot=new pe;function Rt(){Ot.stop()}function _e(){return Ot.isSpeaking()}function hr(){gr.reset(),yr.reset()}var fe=class{constructor(){this.inFlight=null}reset(){try{this.inFlight?.abort()}catch{}this.inFlight=null}async sendAudio(e,n,r=[]){let o=H();x({event_type:"voice_turn_started",stage:"http_request",status:"started",metadata:{transport:"http",audio_type:e?.type||"unknown"}});let i=new FormData;i.append("audio",e,hs(e)),i.append("site_id",l.siteId),i.append("session_id",l.sessionId),r&&r.length>0&&i.append("conversation_history",JSON.stringify(r));let a=br();a&&i.append("page_context",JSON.stringify(a));let c,p=typeof AbortController=="function"?new AbortController:null;this.inFlight=p;try{c=await fetch(`${l.apiUrl}${C.SHOP}`,{method:Pe.POST,body:i,signal:p?.signal})}catch(E){throw ut(E)}if(!c.ok)throw fr(c,await gs(c));let f=await c.json();f.transcript&&n.onUserMessage?.(f.transcript);let g=Array.isArray(f.ui_actions)?f.ui_actions:[],I=[];g.length>0&&(I=await le(g),n.onActionResults?.(I));let T=Ar(f.response_text||"",g,I);T&&n.onAssistantMessage?.(T,g),n.onStatusChange?.(h.READY),f.audio_b64&&T===(f.response_text||"")?_s(f.audio_b64,T):T&&K(T),n.onComplete?.(f),x({event_type:"voice_turn_completed",stage:"http_response",status:"ok",request_id:ms(c),duration_ms:H()-o,metadata:{transport:"http",action_count:f.ui_actions?.length||0}})}},me=class{constructor(){this.ws=null,this.connected=!1,this.connecting=null,this.failed=!1,this.retries=0,this.audioQueue=Ot,this.callbacks=null,this.turnText="",this.receivedAudio=!1,this.pendingAudioChunks=[]}async ensureConnected(e=[]){return this.canUseWebSocket()?this.isOpen()?!0:this.connecting?this.connecting:(this.connecting=this.openConnection(e),this.connecting):!1}canUseWebSocket(){return!this.failed&&l.useWebSocket&&"WebSocket"in window}isOpen(){return this.connected&&this.ws?.readyState===WebSocket.OPEN}openConnection(e=[]){return new Promise(n=>{let r=new WebSocket(ps(l.apiUrl,l.siteId)),o=!1;this.ws=r;let i=(c=null)=>{o||(o=!0,this.markConnectionFailed(n,c,r))},a=window.setTimeout(()=>{i()},He);r.onopen=()=>{o||(o=!0,this.handleConnectionOpen(a,e,n))},r.onmessage=c=>{this.handleMessage(c).catch(p=>this.handleTransportError(p))},r.onerror=()=>{if(o){this.failActiveTurn(m.NETWORK);return}i(a)},r.onclose=()=>{if(this.connected=!1,o){this.failActiveTurn(m.NETWORK);return}i(a)}})}markConnectionOpen(){this.connected=!0,this.connecting=null,this.retries=0}handleConnectionOpen(e,n,r){window.clearTimeout(e),this.markConnectionOpen(),this.sendConfig(n),r(!0)}markConnectionFailed(e,n=null,r=null){n&&window.clearTimeout(n),this.connected=!1,this.connecting=null,this.retries+=1,this.retries>=us&&(this.failed=!0),r&&r.readyState!==WebSocket.CLOSED&&r.close(),e(!1)}sendConfig(e=[]){this.sendJson({type:N.CONFIG,history:e||[],session_id:l.sessionId,page_context:br()})}sendJson(e){return!this.ws||this.ws.readyState!==WebSocket.OPEN?!1:(this.ws.send(JSON.stringify(e)),!0)}async sendAudio(e,n,r=[]){if(!await this.ensureConnected(r))return!1;this.callbacks=n,this.turnText="",this.receivedAudio=!1,this.pendingAudioChunks=[],this.sendConfig(r);let i=await fs(e),a=this.beginTurn();return this.turnStartedAt=H(),x({event_type:"voice_turn_started",stage:"websocket_send",status:"started",metadata:{transport:"websocket",audio_type:e?.type||"unknown"}}),this.sendJson({type:N.AUDIO_CHUNK,data:i,mime_type:e?.type||""})&&this.sendJson({type:N.AUDIO_END,mime_type:e?.type||""})?(await a,!0):(this.settleTurn(),this.callbacks=null,!1)}beginTurn(){return this.settleTurn(),new Promise(e=>{let n=window.setTimeout(()=>{this.failActiveTurn(m.TIMEOUT)},Be);this.activeTurn={resolve:e,timer:n}})}settleTurn(){let e=this.activeTurn;return this.activeTurn=null,e?(window.clearTimeout(e.timer),e.resolve(),!0):!1}failActiveTurn(e){if(!this.activeTurn)return;let n=this.callbacks;if(this.callbacks=null,this.pendingAudioChunks=[],n){let r=new S(e,{stage:"websocket"});n.onStatusChange?.(h.ERROR,r.customerMessage),n.onComplete?.({error:r.category}),x({event_type:"voice_turn_failed",stage:"websocket",severity:"error",status:"failed",message_code:r.code||r.category,duration_ms:H()-(this.turnStartedAt||H()),metadata:{transport:"websocket",category:r.category,http_status:r.status}})}this.settleTurn()}async handleMessage(e){let n=this.callbacks;if(!n)return;let r=this.parseMessage(e.data);if(!r){this.completeWithError(n,"Invalid WebSocket message");return}if(!this.handleIncrementalMessage(r,n)){if(r.type===N.DONE){await this.handleDoneMessage(r,n);return}r.type===N.ERROR&&this.completeWithError(n,r.message||"WebSocket error")}}parseMessage(e){try{let n=JSON.parse(e);return n&&typeof n=="object"?n:null}catch{return null}}handleIncrementalMessage(e,n){return e.type===N.TRANSCRIPT?(n.onUserMessage?.(e.text||""),!0):e.type===N.TEXT_CHUNK?(this.turnText+=e.text||"",!0):e.type===N.AUDIO_CHUNK?(this.receivedAudio=!!e.audio_b64||this.receivedAudio,e.audio_b64&&this.pendingAudioChunks.push(e.audio_b64),!0):!1}async handleDoneMessage(e,n){let r=e.response_text||this.turnText;try{let o=Array.isArray(e.ui_actions)?e.ui_actions:[],i=[];o.length>0&&(i=await le(o),n.onActionResults?.(i));let a=Ar(r,o,i);if(n.onAssistantMessage?.(a,o,{streamed:!0}),n.onStatusChange?.(h.READY),this.receivedAudio&&a===r)for(let c of this.pendingAudioChunks)this.audioQueue.push(c);else a&&K(a);n.onComplete?.(e),x({event_type:"voice_turn_completed",stage:"websocket_done",status:"ok",duration_ms:H()-(this.turnStartedAt||H()),metadata:{transport:"websocket",action_count:e.ui_actions?.length||0}})}catch(o){this.handleTransportError(o)}finally{this.pendingAudioChunks=[],this.callbacks=null,this.settleTurn()}}completeWithError(e,n){e.onStatusChange?.(h.ERROR,Er(n)),e.onComplete?.({error:n});let r=ut(n);x({event_type:"voice_turn_failed",stage:"websocket_message",severity:"error",status:"failed",message_code:r.code||r.category,duration_ms:H()-(this.turnStartedAt||H()),metadata:{transport:"websocket",category:r.category,http_status:r.status}}),this.callbacks=null,this.settleTurn()}handleTransportError(e){console.error("AI Hub WebSocket transport failed",e);let n=this.callbacks;n&&this.completeWithError(n,String(e))}reset(){this.callbacks=null,this.turnText="",this.receivedAudio=!1,this.pendingAudioChunks=[],this.settleTurn();try{this.ws?.close()}catch{}this.ws=null,this.connected=!1,this.connecting=null,this.failed=!1,this.retries=0}},yr=new fe,gr=new me;async function Tr(t,e,n,r=[]){try{if(l.useWebSocket&&await gr.sendAudio(t,n,r))return;await yr.sendAudio(t,n,r)}catch(o){console.error(o);let i=o instanceof S?o:ut(o);x({event_type:"voice_turn_failed",stage:i.stage||"transport",severity:"error",status:"failed",request_id:i.requestId,message_code:i.code||i.category,metadata:{transport:l.useWebSocket?"websocket_or_http":"http",category:i.category,http_status:i.status}}),n.onStatusChange?.(h.ERROR,Er(o)),n.onComplete?.({error:String(o)})}}function ms(t){return t?.headers?.get?.("x-request-id")||t?.headers?.get?.("x-correlation-id")||""}function H(){return typeof performance<"u"?performance.now():Date.now()}function _s(t,e=""){Ot.push(t,e)}function hs(t){let e=String(t?.type||"").toLowerCase();return e.includes("mp4")?"audio.mp4":e.includes("ogg")?"audio.ogg":e.includes("wav")?"audio.wav":Z.WEBM_FILENAME}var ys=/\b(opened|opening|taking you|took you|navigat|sorted|sorting|filtered|filtering|showing|shown|displayed|added to (?:your )?cart|here (?:it |they )?(?:is|are))\b/i,_r="I could not complete that on the page. The site may not have responded - please try again, or do it manually.";function Ar(t,e,n){let r=String(t||"");if(!r||!Array.isArray(e)||e.length===0||!ys.test(r))return r;let o=Array.isArray(n)?n:[];return o.length!==e.length?_r:o.every(a=>a?.status==="succeeded"&&a?.verified!==!1)?r:_r}async function gs(t){try{return await t.json()}catch{return null}}function Er(t){if(t instanceof S)return t.customerMessage;let e=String(t?.message||t||"").toLowerCase();return e.includes("quota")?"Quota reached":e.includes("transcription")||e.includes("speech")?"Voice unavailable":ut(t).customerMessage}function K(t){return t?ct(String(t).slice(0,700)):!1}function br(){let t=window[ls],e=window[ds];try{if(typeof t?.getContext=="function")return t.getContext();if(typeof e?.getContext=="function")return e.getContext()}catch(n){console.warn("[AI Hub Widget] Page context collection failed:",n)}return Ts()}function Ts(){try{return{title:document.title||"",url:window.location.href,path:window.location.pathname,...bt()}}catch(t){return console.warn("[AI Hub Widget] Local page state collection failed:",t),null}}var As=4,Es=40,bs=24,Ss=80,Is=120;function Ir(){let t=[];function e(n,r){let o=String(r||"").trim();o&&(t.push({role:n,content:o}),t.length>De&&t.shift())}return{history:t,clear(){t.length=0},rememberUserMessage(n){e("user",n)},rememberAssistantMessage(n,r){e("assistant",ws(n,r))},rememberActionResults(n){let r=Rs(n);r&&e("assistant",r)}}}function ws(t,e){let n=Os(e);return n.length?`${t} [PRODUCT_IDS: ${n.join(",")}]`:t}function Os(t){let e=[];for(let n of t||[]){let r=n.params||{};Sr(e,r[d.PRODUCT_IDS]),Sr(e,[r[d.PRODUCT_ID]])}return e}function Sr(t,e){for(let n of Array.isArray(e)?e:[])n&&!t.includes(n)&&t.push(n)}function Rs(t){let e=(Array.isArray(t)?t:[]).map(xs).filter(Boolean).slice(0,As);return e.length?`[BROWSER_ACTION_RESULTS: ${e.join(" | ")}]`:""}function xs(t){if(!t||typeof t!="object"||!t.action)return"";let e=[xt(t.action,Es),`status=${xt(t.status,bs)||"unknown"}`],n=Ns(t.final_url);return n&&e.push(`final_path=${xt(n,Is)}`),t.reason&&e.push(`reason=${xt(t.reason,Ss)}`),Cs(e,t.evidence),e.join(" ")}function Cs(t,e={}){e.rendered_product_count!==void 0&&t.push(`rendered_products=${Number(e.rendered_product_count||0)}`),e.rendered_entity_count!==void 0&&t.push(`rendered_records=${Number(e.rendered_entity_count||0)}`)}function xt(t,e){return String(t||"").replace(/\s+/g," ").trim().slice(0,e)}function Ns(t){try{let e=new URL(String(t||""),window.location.href);return`${e.pathname}${e.search}${e.hash}`}catch{return""}}var wr="aihub:session-reset",Ct="AIHub",vs=Object.freeze(["mayabot:","aihub:"]);function Ls(t){let e=[];for(let n=0;n<t.length;n+=1){let r=t.key(n);r&&vs.some(o=>r.startsWith(o))&&e.push(r)}return e}function Or(t){if(!t)return[];try{let e=Ls(t);for(let n of e)t.removeItem(n);return e}catch{return[]}}function Ps(){let t=[];try{t.push(...Or(window.sessionStorage))}catch{}try{t.push(...Or(window.localStorage))}catch{}return t}function Rr({cancelRecording:t,stopPlayback:e,resetTransport:n,conversationMemory:r,clearOverlays:o,rotateSessionId:i}={}){return function(){let c={stopped_recording:!1,stopped_audio:!1,cleared_keys:[],session_id:""};return c.stopped_recording=Q(t),c.stopped_audio=Q(e),Q(n),Q(()=>r?.clear?.()),Q(o),c.cleared_keys=Ps(),c.session_id=String(Q(i)||""),c}}function Q(t){if(typeof t!="function")return!1;try{let e=t();return e===void 0?!0:e}catch(e){return console.warn("[AI Hub Widget] Session reset step failed:",e),!1}}function xr(t){let e=window[Ct]||{};e.resetSession=t,window[Ct]=e;let n=()=>t();return window.addEventListener(wr,n),()=>{window.removeEventListener(wr,n),window[Ct]?.resetSession===t&&delete window[Ct].resetSession}}var Cr=null;function he(t){Cr||(Nr(t),Cr=window.setInterval(()=>Nr(t),Fe))}async function Nr({boot:t,shutdownWidget:e}){try{if(await Ds()){t();return}e()}catch{t()}}async function Ds(){let t=new URL(C.WIDGET_STATUS,l.apiUrl);t.searchParams.set("site_id",l.siteId);let e=await fetch(t.toString(),{cache:"no-store",headers:{Accept:"application/json"}});return e.ok?(await e.json()).enabled!==!1:!0}window.__mayabot_identifier="voice-orb";var ye=null,ge=null;function vr(){if(window.__mayabotBooted||document.getElementById("mayabot-widget"))return;window.__mayabotBooted=!0,be();let t=ve(),e=null,n=null,r=!1;function o(_=Ue){e&&window.clearTimeout(e),e=window.setTimeout(()=>{t.msgs.innerHTML="",t.chat.classList.remove("visible"),e=null},_)}function i(_,b=""){r=_===h.RECORDING,Te(w(_)),t.status.className="",_===h.RECORDING?(e&&(window.clearTimeout(e),e=null),t.msgs.innerHTML="",t.btn.classList.add("recording"),t.chat.classList.add("visible"),t.status.innerText="Listening...",t.status.classList.add("listening")):_===h.PROCESSING?(t.btn.classList.remove("recording"),t.chat.classList.add("visible"),t.status.innerText="Analyzing...",t.status.classList.add("processing")):_===h.READY?(t.status.innerText="Ready",t.status.classList.add("ready")):_===h.ERROR&&(t.status.innerText=b||"Try again",t.status.classList.add("error"),t.btn.classList.remove("recording"))}let a=Ir(),c=null,p="",f=!1;async function g(_){if(!f){f=!0,t.btn.disabled=!0,c=null,p="";try{await Tr(_,t,{onUserMessage:b=>{J(t,b,"user"),a.rememberUserMessage(b)},onAssistantChunk:(b,Nt)=>{p=Nt,c||(c=J(t,"","ai")),Dt(t,c,p)},onAssistantMessage:(b,Nt,Ur={})=>{Ur.streamed&&c?Dt(t,c,b):J(t,b,"ai"),a.rememberAssistantMessage(b,Nt),c=null,p=""},onActionResults:a.rememberActionResults,onStatusChange:i,onComplete:()=>o()},a.history)}finally{f=!1,t.btn.disabled=!1,c=null,p=""}}}let I=Ye(g,i);ye=I;function T(){return _e()?(Rt(),x({event_type:"voice_playback_stopped",stage:"orb_gesture",status:"cancelled"}),i(h.READY),!0):!1}function E(){if(f){T();return}if(r){I.toggle();return}T()||I.toggle()}let V={idle:{label:"Maya voice assistant. Click, press Enter, or press Space to talk.",title:"Click to talk"},recording:{label:"Maya is listening. Click once to send, or press Escape to cancel.",title:"Click once to send - Escape to cancel"},processing:{label:"Maya is working on your request. Please wait.",title:"Request in progress"},speaking:{label:"Maya is speaking. Click to stop, or press Escape to stop.",title:"Click to stop Maya"}};function w(_){return _===h.RECORDING?"recording":_===h.PROCESSING?"processing":_e()?"speaking":"idle"}function Te(_){let b=V[_]||V.idle;t.btn.setAttribute("aria-label",b.label),t.btn.setAttribute("title",b.title)}Te("idle"),t.btn.addEventListener("click",_=>{if(f){T();return}T()||_.detail>1||E()});let Ae=_=>{if(_.key==="Escape"){if(r){I.cancel(),x({event_type:"voice_recording_cancelled",stage:"keyboard_escape",status:"cancelled"}),i(h.READY);return}T()}};document.addEventListener("keydown",Ae);let Ee=_=>{t.btn.contains(_.target)||wt()};document.addEventListener("pointerdown",Ee,{capture:!0});let Dr=xr(Rr({cancelRecording:()=>I.cancel(),stopPlayback:Rt,resetTransport:hr,conversationMemory:a,clearOverlays:()=>{t.msgs.innerHTML="",t.chat.classList.remove("visible"),document.getElementById("mayabot-product-panel")?.remove()},rotateSessionId:()=>l.rotateSessionId()}));ge=()=>{document.removeEventListener("keydown",Ae),document.removeEventListener("pointerdown",Ee,{capture:!0}),Dr(),e&&window.clearTimeout(e),e=null,n&&window.clearTimeout(n),n=null,ge=null},Us()&&(ks(),n=window.setTimeout(()=>{if(a.history.length>0)return;let _=`Welcome to ${l.brandName}. How can I help you today?`;J(t,_,"ai"),i(h.READY),o(Me),ct(_)},ke))}function Lr(){ye?.cancel(),ye=null,ge?.(),Rt(),window.__mayabotBooted=!1,document.getElementById("mayabot-widget")?.remove(),document.getElementById("mayabot-product-panel")?.remove()}function Us(){if(!l.autoGreet||!Ms())return!1;try{return window.sessionStorage.getItem(Pr())!=="1"}catch{return!window.__mayabotAutoGreeted}}function ks(){window.__mayabotAutoGreeted=!0;try{window.sessionStorage.setItem(Pr(),"1")}catch{}}function Pr(){return`mayabot:auto-greeted:${l.siteId}`}function Ms(){let t=window.location.pathname.replace(/\/+$/,"")||"/";return t==="/"||t.endsWith("/index.html")}document.readyState==="loading"?document.addEventListener("DOMContentLoaded",()=>he({boot:vr,shutdownWidget:Lr})):he({boot:vr,shutdownWidget:Lr});})();
