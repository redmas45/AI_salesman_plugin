(()=>{function gn(){let t="#5d5fef",e=document.querySelector('meta[name="theme-color"]');if(e&&e.content)t=e.content;else{let f=document.querySelector('button[class*="primary"], .btn-primary, [data-primary]');if(f){let A=window.getComputedStyle(f).backgroundColor;A&&A!=="rgba(0, 0, 0, 0)"&&A!=="transparent"&&(t=A)}}let n=window.matchMedia&&window.matchMedia("(prefers-color-scheme: dark)").matches,r=n?"rgba(24, 24, 27, 0.75)":"rgba(255, 255, 255, 0.85)",o=n?"rgba(255, 255, 255, 0.1)":"rgba(0, 0, 0, 0.08)",i=n?"#f3f4f6":"#111827",a=n?"rgba(255, 255, 255, 0.1)":"rgba(0, 0, 0, 0.05)",s=n?"rgba(0, 0, 0, 0.25)":"#ffffff",u=document.createElement("style");u.textContent=`
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
  `,document.head.appendChild(u)}var pe="site_1",Jo="__AI_";var Zo="aihub:auto-site-id:",ti=["data-aihub-scope","data-site-scope"],ei=["data-site-id","data-aihub-site-id"];function w(t){return String(t||"").trim()}function bt(t){return w(t).replace(/\/+$/,"")}function An(t,e,n,r=pe){return ni(t,e,n)||ri()||w(r)||pe}function ni(t,e,n){for(let i of ei){let a=w(t?.getAttribute(i));if(a)return a}let r=w(e?.searchParams.get("site"))||w(e?.searchParams.get("site_id"))||w(e?.searchParams.get("shop"));if(r)return r;let o=w(n);return o&&!o.startsWith(Jo)?o:""}function ri(){let t=oi(),e=`${Zo}${t}`,n=pi(e);if(n){let s=li(n);return s!==n&&Tn(e,s),s}let r=w(window.location.host||window.location.hostname||"site"),o=En(),i=ui(`${r}${o?`_${o.replace(/\//g,"_")}`:""}`),a=Sn(`auto_${i}_${di(t)}`);return Tn(e,a),a}function oi(){return`${window.location.origin}${En()}`}function En(){return ii()}function ii(){for(let e of ti){let n=w(ai()?.getAttribute(e));if(n)return bn(n)}let t=document.querySelector("meta[name='aihub-site-scope']")?.getAttribute("content");return bn(t)}function ai(){return document.currentScript}function bn(t){let e=w(t);if(!e||e==="/")return"";try{let r=new URL(e,window.location.href);if(r.origin===window.location.origin){let[o]=si(r.pathname);return o?`/${o}`:""}}catch{}let[n]=e.replace(/^\/+/,"").split("/");return n?`/${n}`:""}function si(t=window.location.pathname){return w(t).split("/").map(e=>ci(e).trim()).filter(Boolean)}function ci(t){try{return decodeURIComponent(t)}catch{return String(t||"")}}function ui(t){return w(t).toLowerCase().replace(/[^a-z0-9]+/g,"_").replace(/^_+|_+$/g,"")||"site"}function Sn(t){return w(t).slice(0,80).replace(/_+$/g,"")||pe}function li(t){let e=w(t);return e.startsWith("auto_")?Sn(e.toLowerCase().replace(/[^a-z0-9]+/g,"_").replace(/^_+|_+$/g,"")):e}function di(t){let e=2166136261,n=w(t);for(let r=0;r<n.length;r+=1)e^=n.charCodeAt(r),e=Math.imul(e,16777619);return(e>>>0).toString(36)}function pi(t){try{return w(window.localStorage.getItem(t))}catch{return""}}function Tn(t,e){try{window.localStorage.setItem(t,e)}catch{}}var $=document.currentScript,wn="__AI_PUBLIC_API_URL__",fi="__AI_DEFAULT_SITE_ID__",In="mayabot:session:",mi="Maya",hi="AI Salesperson",_i="female";function J(t){return String(t||"").trim()}function yi(){let t=J($?.getAttribute("src"));if(!t)return null;try{return new URL(t,window.location.href)}catch{return null}}function gi(t){let e=J($?.getAttribute("data-api-url"));if(e)return bt(e);if(!wn.startsWith("__AI_"))return bt(wn);if(t?.origin){let n=t.pathname.replace(/\/mayabot(?:-widget)?\.js$/,"");return bt(`${t.origin}${n}`)}return bt(window.location.origin)}function bi(t){let e=`${In}${t}`;try{let n=window.sessionStorage.getItem(e);if(n)return n;let r=me(t);return window.sessionStorage.setItem(e,r),r}catch{return me(t)}}function Ti(t){let e=me(t);try{window.sessionStorage.setItem(`${In}${t}`,e)}catch{}return e}function me(t){let e=window.crypto?.randomUUID?.()||`${Date.now()}-${Math.random().toString(16).slice(2)}`;return`${t}-${e}`.slice(0,120)}var On=yi(),fe=An($,On,fi),d={siteId:fe,get sessionId(){return bi(fe)},rotateSessionId(){return Ti(fe)},apiUrl:gi(On),useWebSocket:J($?.getAttribute("data-use-websocket")).toLowerCase()==="true",autoGreet:J($?.getAttribute("data-auto-greet")).toLowerCase()!=="false",brandName:J($?.getAttribute("data-brand"))||mi,assistantTitle:J($?.getAttribute("data-assistant-title"))||hi,speechVoiceName:J($?.getAttribute("data-speech-voice")),speechVoicePreference:J($?.getAttribute("data-speech-voice-preference"))||_i};function Cn(){let t=document.createElement("div");return t.id="mayabot-widget",t.innerHTML=`
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
  `,document.body.appendChild(t),t.querySelector(".mayabot-kicker").textContent=d.brandName,t.querySelector(".mayabot-title").textContent=d.assistantTitle,{btn:document.getElementById("mayabot-btn"),chat:document.getElementById("mayabot-chat"),msgs:document.getElementById("mayabot-msgs"),status:document.getElementById("mayabot-status")}}function Tt(t,e,n){t.chat.classList.add("visible");let r=document.createElement("div");return r.className=`mayabot-msg ${n}`,r.innerText=e,t.msgs.appendChild(r),t.msgs.scrollTop=t.msgs.scrollHeight,r}function he(t,e,n){e&&(e.innerText=n,t.msgs.scrollTop=t.msgs.scrollHeight)}var c=Object.freeze({ADD_TO_CART:"ADD_TO_CART",BOOK_APPOINTMENT_REQUEST:"BOOK_APPOINTMENT_REQUEST",BUILD_ITINERARY:"BUILD_ITINERARY",BUILD_LEARNING_PATH:"BUILD_LEARNING_PATH",CAPTURE_LEAD:"CAPTURE_LEAD",CAPTURE_PATIENT_LEAD:"CAPTURE_PATIENT_LEAD",CHECKOUT:"CHECKOUT",CHECKOUT_HANDOFF:"CHECKOUT_HANDOFF",CHECK_APPOINTMENT_AVAILABILITY:"CHECK_APPOINTMENT_AVAILABILITY",CHECK_AVAILABILITY:"CHECK_AVAILABILITY",CHECK_DELIVERY_AVAILABILITY:"CHECK_DELIVERY_AVAILABILITY",CHECK_ELIGIBILITY_SOFT:"CHECK_ELIGIBILITY_SOFT",CHECK_PREREQUISITES:"CHECK_PREREQUISITES",CLEAR_CART:"CLEAR_CART",CLEAR_FILTERS:"CLEAR_FILTERS",CLEAR_HISTORY:"CLEAR_HISTORY",COMPARE_ENTITIES:"COMPARE_ENTITIES",CONTACT_AGENT:"CONTACT_AGENT",FILTER_ENTITIES:"FILTER_ENTITIES",FILTER_PRODUCTS:"FILTER_PRODUCTS",HANDOFF_TO_ADVISOR:"HANDOFF_TO_ADVISOR",HANDOFF_TO_AGENT:"HANDOFF_TO_AGENT",HANDOFF_TO_CLINIC:"HANDOFF_TO_CLINIC",HANDOFF_TO_HUMAN:"HANDOFF_TO_HUMAN",HANDOFF_TO_LAWYER:"HANDOFF_TO_LAWYER",HANDOFF_TO_LICENSED_AGENT:"HANDOFF_TO_LICENSED_AGENT",HANDOFF_TO_RECRUITER:"HANDOFF_TO_RECRUITER",JOIN_WAITLIST:"JOIN_WAITLIST",MATCH_JOBS:"MATCH_JOBS",NAVIGATE_TO:"NAVIGATE_TO",OPEN_CLAIM_FLOW:"OPEN_CLAIM_FLOW",OPEN_CONTACT:"OPEN_CONTACT",OPEN_DISCLOSURE:"OPEN_DISCLOSURE",OPEN_ENTITY_DETAIL:"OPEN_ENTITY_DETAIL",OPEN_LOCATION:"OPEN_LOCATION",OPEN_MAP:"OPEN_MAP",OPEN_POLICY:"OPEN_POLICY",OPEN_PROJECTS:"OPEN_PROJECTS",OPEN_RENEWAL_FLOW:"OPEN_RENEWAL_FLOW",OPEN_SERVICES:"OPEN_SERVICES",OPEN_SYLLABUS:"OPEN_SYLLABUS",OPEN_TELECONSULT:"OPEN_TELECONSULT",REMOVE_FROM_CART:"REMOVE_FROM_CART",REQUEST_APPOINTMENT:"REQUEST_APPOINTMENT",REQUEST_CALLBACK:"REQUEST_CALLBACK",REQUEST_CONSULTATION:"REQUEST_CONSULTATION",REQUEST_COUNSELOR_CALLBACK:"REQUEST_COUNSELOR_CALLBACK",REQUEST_ESTIMATE:"REQUEST_ESTIMATE",REQUEST_SITE_VISIT:"REQUEST_SITE_VISIT",REQUEST_TEST_DRIVE:"REQUEST_TEST_DRIVE",REQUEST_VIEWING:"REQUEST_VIEWING",RUN_AFFORDABILITY_CALCULATOR:"RUN_AFFORDABILITY_CALCULATOR",RUN_CALCULATOR:"RUN_CALCULATOR",RUN_DOM_SEQUENCE:"RUN_DOM_SEQUENCE",SAVE_SEARCH:"SAVE_SEARCH",SCHEDULE_ORDER:"SCHEDULE_ORDER",SEARCH_AVAILABILITY:"SEARCH_AVAILABILITY",SET_LOCATION:"SET_LOCATION",SHOW_COMPARISON:"SHOW_COMPARISON",SHOW_EMERGENCY_NOTICE:"SHOW_EMERGENCY_NOTICE",SHOW_ENTITIES:"SHOW_ENTITIES",SHOW_PRODUCT_DETAIL:"SHOW_PRODUCT_DETAIL",SHOW_PRODUCTS:"SHOW_PRODUCTS",SORT_ENTITIES:"SORT_ENTITIES",SORT_PRODUCTS:"SORT_PRODUCTS",START_APPLICATION:"START_APPLICATION",START_BOOKING:"START_BOOKING",START_ENROLLMENT:"START_ENROLLMENT",START_INTAKE:"START_INTAKE",START_QUOTE:"START_QUOTE",START_TICKET_PURCHASE:"START_TICKET_PURCHASE",UPDATE_CART_QUANTITY:"UPDATE_CART_QUANTITY",UPDATE_PREFERENCES:"UPDATE_PREFERENCES"}),p=Object.freeze({ENTITY_ID:"entity_id",ENTITY_IDS:"entity_ids",MESSAGE:"message",PAGE:"page",PRODUCT_ID:"product_id",PRODUCT_IDS:"product_ids",PRODUCT_NAME:"product_name",QUANTITY:"quantity",REASON:"reason",SEARCH_QUERY:"search_query",URL:"url"}),ku=Object.freeze({BLOCKED:"blocked",EXECUTING:"executing",FAILED:"failed",REQUESTED:"requested",SKIPPED:"skipped",SUCCEEDED:"succeeded",UNKNOWN:"unknown"}),U=Object.freeze({KNOWLEDGE_BY_IDS:"/v1/knowledge/by-ids",PRODUCTS_BY_IDS:"/v1/products/by-ids",SHOP:"/v1/shop",SHOP_WS:"/v1/ws/shop",WIDGET_STATUS:"/v1/widget/status"}),k=Object.freeze({AUDIO_CHUNK:"audio_chunk",AUDIO_END:"audio_end",CONFIG:"config",DONE:"done",ERROR:"error",TEXT_CHUNK:"text_chunk",TRANSCRIPT:"transcript"});var Rn=new Set(["cart","/cart"]),j="Recommended products",Z="Relevant options",At=Object.freeze({DATA_WAV_PREFIX:"data:audio/wav;base64,",WEBM_FILENAME:"audio.webm",WEBM_MIME_TYPE:"audio/webm"}),xn=Object.freeze({POST:"POST"}),y=Object.freeze({ERROR:"error",PROCESSING:"processing",READY:"ready",RECORDING:"recording"});var Nn=2400,vn=900,Ln=4200,_e=1,lt=180,Pn=3e3,Et=Object.freeze({MAYABOT_ACTION:"mayabot:action"}),Dn=2500,Un=45e3;var Ai=["audio/webm;codecs=opus","audio/webm","audio/ogg;codecs=opus","audio/ogg","audio/mp4"],Ei=250,Si=128;function kn(t,e){let n=null,r=null,o=[],i=!1,a=!1,s=!1;async function u(){if(!(a||i)){a=!0;try{let b=await navigator.mediaDevices.getUserMedia({audio:!0});r=b,s=!1;let R=wi();n=new MediaRecorder(b,R?{mimeType:R}:void 0),o=[],n.ondataavailable=I=>{I.data.size>0&&o.push(I.data)},n.onstop=async()=>{let I=new Blob(o,{type:n.mimeType||R||At.WEBM_MIME_TYPE});if(C(),s){s=!1;return}if(I.size<Si){console.warn("Microphone recording was empty or too short",{size:I.size}),e(y.READY);return}await t(I)},n.onerror=I=>{console.error("Microphone recording failed",I.error||I),i=!1,a=!1,C(),e(y.ERROR,"Recording failed")},n.start(Ei),i=!0,e(y.RECORDING)}catch(b){console.error("Microphone access denied",b),e(y.ERROR,"Mic unavailable")}finally{a=!1}}}function f({discard:b=!1}={}){if(s=b,n&&n.state!=="inactive"){try{n.requestData()}catch{}n.stop(),i=!1,b||e(y.PROCESSING);return}i=!1,C(),b||e(y.PROCESSING)}function A(){a||(i?f():u())}function v(){f({discard:!0})}function C(){r&&(r.getTracks().forEach(b=>b.stop()),r=null)}return{toggle:A,cancel:v}}function wi(){return!("MediaRecorder"in window)||typeof MediaRecorder.isTypeSupported!="function"?"":Ai.find(t=>MediaRecorder.isTypeSupported(t))||""}var Mn="shopify",Fn="woocommerce",Ii="custom";function Ft(t){let e=String(t||"").trim();return/^\d+$/.test(e)?e:""}function Ht(t,e=1){let n=Number(t?.[p.QUANTITY]);return Number.isFinite(n)&&n>0?Math.floor(n):e}async function rt(t,e){return(await fetch(new URL(t,window.location.origin),{method:"POST",headers:{Accept:"application/json","Content-Type":"application/json"},body:JSON.stringify(e),credentials:"same-origin"})).ok}function Oi(){return Ci()?Mn:Ri()?Fn:Ii}async function Hn(t){let e=Oi();return e===Mn?xi(t):e===Fn?Ni(t):!1}function Ci(){return!!(window.Shopify||document.querySelector('meta[name="shopify-checkout-api-token"]')||document.querySelector('script[src*="cdn.shopify.com"]'))}function Ri(){return!!(document.body?.classList?.contains("woocommerce")||window.wc_add_to_cart_params||document.querySelector('link[href*="woocommerce"], script[src*="woocommerce"]'))}async function xi(t){let e=t.parameters||{};if(t.action===c.ADD_TO_CART){let n=Ft(e.variant_id||e.cart_id||e[p.PRODUCT_ID]);return n?rt("/cart/add.js",{items:[{id:n,quantity:Ht(e)}]}):!1}if(t.action===c.REMOVE_FROM_CART){let n=Ft(e.cart_id||e.variant_id||e[p.PRODUCT_ID]);return n?rt("/cart/change.js",{id:n,quantity:0}):!1}if(t.action===c.UPDATE_CART_QUANTITY){let n=Ft(e.cart_id||e.variant_id||e[p.PRODUCT_ID]);return n?rt("/cart/change.js",{id:n,quantity:Ht(e,0)}):!1}return t.action===c.CLEAR_CART?rt("/cart/clear.js",{}):t.action===c.CHECKOUT?Bt("/checkout"):Bn(t)?Bt("/cart"):!1}async function Ni(t){let e=t.parameters||{};if(t.action===c.ADD_TO_CART){let n=Ft(e.variant_id||e.cart_id||e[p.PRODUCT_ID]);return n?rt("/wp-json/wc/store/cart/add-item",{id:Number(n),quantity:Ht(e)}):!1}if(t.action===c.REMOVE_FROM_CART){let n=String(e.cart_key||e.key||"").trim();return n?rt("/wp-json/wc/store/cart/remove-item",{key:n}):!1}if(t.action===c.UPDATE_CART_QUANTITY){let n=String(e.cart_key||e.key||"").trim();return n?rt("/wp-json/wc/store/cart/update-item",{key:n,quantity:Ht(e,0)}):!1}return t.action===c.CHECKOUT?Bt("/checkout"):Bn(t)?Bt("/cart"):!1}function Bn(t){return t.action===c.NAVIGATE_TO&&Rn.has(t.parameters?.[p.PAGE])}function Bt(t){return window.location.href=t,!0}var vi="/v1/widget/action-event";function P(t){return String(t||"").trim()}function Li(t,e){return new URL(t,e).toString()}function Pi(t){return!t||typeof t!="object"?[]:Object.keys(t).map(e=>P(e)).filter(Boolean).slice(0,20)}function Di(t){if(!t||typeof t!="object")return{};let e={};for(let[n,r]of Object.entries(t).slice(0,20)){let o=P(n).slice(0,80);o&&(typeof r=="boolean"||r===null?e[o]=r:typeof r=="number"?e[o]=Number.isFinite(r)?r:0:e[o]=P(r).slice(0,240))}return e}async function Yt(t,e,n,r){if(!t||!e||!n?.action)return;let o=JSON.stringify({site_id:e,origin:window.location.origin,url:window.location.href,occurred_at:new Date().toISOString(),request_id:P(n.request_id||n.action_request_id),turn_id:P(n.turn_id),sequence:Number(n.sequence||0),action:P(n.action).toUpperCase(),status:P(r?.status)||"unknown",stage:P(r?.stage),reason:P(r?.reason),duration_ms:Number(r?.duration_ms||0),param_keys:Pi(n.parameters||n.params),requested_url:P(r?.requested_url),final_url:P(r?.final_url||window.location.href),evidence:Di(r?.evidence)}),i=Li(vi,t);if(!Ui(i,o))try{await fetch(i,{method:"POST",headers:{Accept:"application/json","Content-Type":"application/json"},body:o,keepalive:!0})}catch(a){console.warn("[AIHubAdapter] Action execution report failed.",a)}}function Ui(t,e){if(typeof navigator>"u"||typeof navigator.sendBeacon!="function"||typeof Blob!="function")return!1;try{return navigator.sendBeacon(t,new Blob([e],{type:"application/json"}))}catch{return!1}}function x(t){if(!t||typeof t!="string")return[];let e=[];for(let n of ki()){try{e.push(...Array.from(n.querySelectorAll(t)))}catch{return[]}if(e.length>=600)return e.slice(0,600)}return Bi(e)}function ki(){let t=[],e=new Set,n=[document];for(;n.length&&t.length<60;){let r=n.shift();!r||e.has(r)||(e.add(r),t.push(r),n.push(...Mi(r)))}return t}function Mi(t){let e=[];for(let n of Fi(t)){n.shadowRoot&&e.push(n.shadowRoot);let r=Hi(n);r&&e.push(r)}return e}function Fi(t){try{return Array.from(t.querySelectorAll("*"))}catch{return[]}}function Hi(t){if(String(t?.tagName||"").toLowerCase()!=="iframe")return null;try{let e=t.contentDocument;return e?.documentElement?e:null}catch{return null}}function Bi(t){return Array.from(new Set(t))}var zu=Object.freeze([l("stripe",["stripe","stripe.com","checkout.stripe.com","js.stripe.com"]),l("paypal",["paypal","paypal.com","paypalobjects.com"]),l("razorpay",["razorpay","checkout.razorpay.com"]),l("paytm",["paytm","securegw.paytm.in"]),l("cashfree",["cashfree","cashfree.com"]),l("checkout.com",["checkout.com","cko-session-id"]),l("adyen",["adyen","checkoutshopper"]),l("square",["squareup","squarecdn","square.site"]),l("braintree",["braintree","braintreegateway"]),l("mollie",["mollie","mollie.com"]),l("klarna",["klarna","klarna.com"]),l("afterpay",["afterpay","afterpay.com","clearpay"]),l("payu",["payu","payu.in","payu.com"]),l("paystack",["paystack","paystack.co"]),l("phonepe",["phonepe","phonepe.com"]),l("billdesk",["billdesk","billdesk.com"]),l("authorize.net",["authorize.net","accept.authorize.net"])]),Yn=Object.freeze([l("calendly",["calendly","calendly.com"]),l("acuity",["acuityscheduling","squarespace scheduling"]),l("booksy",["booksy","booksy.com"]),l("zocdoc",["zocdoc","zocdoc.com"]),l("appointlet",["appointlet","appointlet.com"]),l("setmore",["setmore","setmore.com"]),l("cal.com",["cal.com","calcom"]),l("google_calendar",["calendar.google.com","google calendar"]),l("microsoft_bookings",["microsoft bookings","outlook.office365.com/book"]),l("simplybook",["simplybook","simplybook.me"]),l("tidycal",["tidycal","tidycal.com"]),l("savvycal",["savvycal","savvycal.com"]),l("fresha",["fresha","fresha.com"])]),$n=Object.freeze([l("google_maps",["google.com/maps","maps.googleapis","maps.google"]),l("mapbox",["mapbox","mapbox.com"]),l("openstreetmap",["openstreetmap","osm.org"]),l("leaflet",["leaflet","leafletjs"]),l("here_maps",["here.com","hereapi","wego.here.com"]),l("bing_maps",["bing.com/maps","virtualearth"]),l("mappls",["mappls","mapmyindia"])]),jn=Object.freeze([l("whatsapp",["wa.me","api.whatsapp.com","web.whatsapp.com"]),l("telegram",["t.me/","telegram.me"]),l("messenger",["m.me/","messenger.com/t"]),l("zendesk",["zendesk.com","zdassets.com/hc"]),l("intercom",["intercom.help","intercom.com"]),l("freshchat",["freshchat.com"])]),Gu=Object.freeze([l("recaptcha",["recaptcha","g-recaptcha","google.com/recaptcha"]),l("hcaptcha",["hcaptcha","h-captcha"]),l("turnstile",["turnstile","challenges.cloudflare.com"]),l("cloudflare_challenge",["cf-chl","cloudflare challenge"])]);function l(t,e){return{name:t,tokens:e}}function ye(t,e,n=10){let r=ge(t);return e.filter(o=>o.tokens.some(i=>r.includes(i))).map(o=>o.name).slice(0,n)}function ge(t){return String(t||"").replace(/\s+/g," ").trim().toLowerCase()}var qn="a[href], iframe[src]",Yi="a[href]",zn=new Set(["http:","https:"]),$t=new Set(["mailto:","tel:"]),$i=Object.freeze([p.URL,"href","link","target_url","provider_url","booking_url","appointment_url","calendar_url","map_url","location_url","contact_url"]),Gn=new Set([c.OPEN_MAP,c.OPEN_LOCATION,c.SET_LOCATION]),Wn=new Set([c.CHECK_APPOINTMENT_AVAILABILITY,c.REQUEST_APPOINTMENT,c.BOOK_APPOINTMENT_REQUEST,c.REQUEST_CONSULTATION,c.REQUEST_SITE_VISIT,c.START_BOOKING]),Kn=new Set([c.OPEN_CONTACT,c.CONTACT_AGENT,c.REQUEST_CALLBACK,c.REQUEST_COUNSELOR_CALLBACK,c.HANDOFF_TO_ADVISOR,c.HANDOFF_TO_AGENT,c.HANDOFF_TO_CLINIC,c.HANDOFF_TO_HUMAN,c.HANDOFF_TO_LAWYER,c.HANDOFF_TO_LICENSED_AGENT,c.HANDOFF_TO_RECRUITER]);function Qn(t){let e=Zn(t);return Gn.has(e)||Wn.has(e)||Kn.has(e)}async function Xn(t){let e=Zn(t);return Gn.has(e)?be(t,$n,qn,Te):Wn.has(e)?be(t,Yn,qn,Te):Kn.has(e)?be(t,jn,Yi,zi):!1}function be(t,e,n,r){let o=ji(t?.parameters||t?.params||{},e,r);if(o)return Vn(o);let i=qi(n,e,r);return i?Vn(i):!1}function ji(t,e,n){for(let r of $i){let o=Jn(t?.[r]);if(o&&n(o,e))return o}return null}function qi(t,e,n){for(let r of x(t)){let o=Vi(r);if(!(!o||!n(o,e))&&Gi(o,r,e))return o}return null}function Vi(t){return Jn(t?.getAttribute?.("href")||t?.getAttribute?.("src"))}function Te(t,e){return zn.has(t.protocol)&&ye(t.href,e).length>0}function zi(t,e){return $t.has(t.protocol)?!0:Te(t,e)}function Gi(t,e,n){if($t.has(t.protocol))return!0;let r=[t.href,e?.textContent||"",e?.getAttribute?.("aria-label")||"",e?.getAttribute?.("title")||""].join(" ");return ye(ge(r),n).length>0}function Vn(t){if($t.has(t.protocol)||t.origin===window.location.origin)return window.location.href=t.href,!0;let e=window.open(t.href,"_blank","noopener,noreferrer");return e?(e.opener=null,!0):(window.location.href=t.href,!0)}function Jn(t){let e=String(t||"").trim();if(!e||e.startsWith("#"))return null;try{let n=new URL(e,window.location.href);return zn.has(n.protocol)||$t.has(n.protocol)?n:null}catch{return null}}function Zn(t){return String(t?.action||"").trim().toUpperCase()}var Wi=Object.freeze(["title","name"]),Ki=Object.freeze(["summary","description","body"]),Qi=Object.freeze(["image_url","imageUrl","image","thumbnail"]),Xi=Object.freeze(["url","href","permalink","source_url"]),Ji="knowledge_item",Zi=30;function M(t){return t==null||typeof t=="object"?"":String(t||"").trim()}function ta(t){let e=new Set;return(Array.isArray(t)?t:[]).map(M).filter(Boolean).filter(n=>e.has(n)||e.size>=Zi?!1:(e.add(n),!0))}function jt(t,e){for(let n of e){let r=M(t?.[n]);if(r)return r}return""}function St(t){return t&&typeof t=="object"&&!Array.isArray(t)?t:{}}function ea(t){let e=na([t?.price,t?.amount,t?.premium,t?.premium_min,t?.monthly_premium,t?.annual_premium,t?.min_price,t?.starting_price]),n=M(t?.currency||"INR");return!Number.isFinite(e)||e<=0?"":`${n} ${e.toLocaleString()}`}function na(t){for(let e of t){let n=Number(String(e??"").replace(/,/g,""));if(Number.isFinite(n)&&n>0)return n}return 0}function ra(t){return!t||typeof t!="object"?"":t.in_stock===!0?"Available":t.in_stock===!1?"Unavailable":M(t.status||t.availability||"")}function oa(t){let e=M(t);if(!e)return"";try{let n=new URL(e,window.location.origin);return/^https?:$/i.test(n.protocol)?n.origin===window.location.origin?`${n.pathname}${n.search}${n.hash}`:n.toString():""}catch{return""}}function ia(t){if(!t)return null;let e=M(t.id);if(!e)return null;let n=St(t.pricing),r=St(t.availability);return{id:e,externalId:M(t.external_id),entityType:M(t.entity_type||t.category_name)||Ji,title:jt(t,Wi)||e,subtitle:M(t.subtitle||t.category_name||t.entity_type),summary:jt(t,Ki),body:M(t.body),url:oa(jt(t,Xi)),imageUrl:jt(t,Qi),attributes:St(t.attributes),pricing:n,availability:r,location:St(t.location),contact:St(t.contact),displayPrice:ea(n),displayAvailability:ra(r)}}async function Ae(t){let e=ta(t);if(!e.length)return[];let n=new URL(U.KNOWLEDGE_BY_IDS,d.apiUrl);n.searchParams.set("site_id",d.siteId),n.searchParams.set("ids",e.join(","));let r=await fetch(n.toString(),{headers:{Accept:"application/json"}});if(!r.ok)throw new Error("Failed to fetch entities from AI Hub API");let o=(await r.json()).map(ia).filter(Boolean),i=new Map(o.map(a=>[String(a.id),a]));return e.map(a=>i.get(a)).filter(Boolean)}async function tr(t){let[e]=await Ae([t]);return e?.url||""}function er(){if(document.getElementById("mayabot-entity-overlay-styles"))return;let t=document.createElement("style");t.id="mayabot-entity-overlay-styles",t.textContent=`
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
  `,document.head.appendChild(t)}var aa=2,nr=Number.POSITIVE_INFINITY,qt=Number.NEGATIVE_INFINITY,rr=12,Se=[],we=Z;function q(t){return String(t??"").replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;").replace(/"/g,"&quot;").replace(/'/g,"&#039;")}function sr(t){return String(t||"item").replace(/[_-]+/g," ").trim().split(/\s+/).slice(0,aa).join(" ")}function sa(){er();let t=document.getElementById("mayabot-entity-panel");return t||(t=document.createElement("div"),t.id="mayabot-entity-panel",t.setAttribute("aria-live","polite"),t.innerHTML=`
    <div class="mayabot-entity-header">
      <h2 class="mayabot-entity-title">${Z}</h2>
      <button class="mayabot-entity-close" type="button" aria-label="Close recommendations">&times;</button>
    </div>
    <div class="mayabot-entity-grid"></div>
  `,t.querySelector(".mayabot-entity-close").addEventListener("click",()=>{t.classList.remove("active")}),document.body.appendChild(t),t)}function ca(t){return t<=1?"count-1":t===2?"count-2":t===3?"count-3":"count-many"}function ua(t){return t<=1?1:t===2?2:3}function Ee(t,e,n=""){let r=(Array.isArray(e)?e:[]).map(s=>String(s?.id??"").trim()).filter(Boolean),o=r.length,i=t.length,a=o>0?"succeeded":"failed";return{status:a,stage:"entity_overlay",reason:n||(a==="succeeded"?"":"no_matching_entities_rendered"),evidence:{requested_entity_count:i,rendered_entity_count:o,missing_entity_count:Math.max(i-o,0),requested_entity_ids:t.slice(0,rr).join(","),rendered_entity_ids:r.slice(0,rr).join(",")}}}function la(t){return[t.displayPrice,t.displayAvailability,t.location?.city,t.attributes?.category].map(e=>String(e||"").trim()).filter(Boolean).slice(0,3)}function da(t){return t.imageUrl?`
      <div class="mayabot-entity-media">
        <img src="${q(t.imageUrl)}" alt="${q(t.title)}">
      </div>
    `:`
    <div class="mayabot-entity-media">
      <div class="mayabot-entity-badge">${q(sr(t.entityType))}</div>
    </div>
  `}function pa(t){let e=la(t);return e.length?`
    <div class="mayabot-entity-facts">
      ${e.map(n=>`<span class="mayabot-entity-fact">${q(n)}</span>`).join("")}
    </div>
  `:""}function fa(t){return t.url?`
    <div class="mayabot-entity-actions">
      <button type="button" data-view-entity="${q(t.id)}">Open</button>
    </div>
  `:""}function zt(t,e){let n=sa(),r=n.querySelector(".mayabot-entity-grid"),o=n.querySelector(".mayabot-entity-title"),i=t.length;if(Se=Array.isArray(t)?[...t]:[],we=e||Z,n.classList.remove("count-1","count-2","count-3","count-many"),n.classList.add(ca(i)),n.style.setProperty("--mayabot-entity-card-count",String(ua(i))),o.textContent=we,!i){r.innerHTML='<p class="mayabot-entity-empty">No matching records are currently available.</p>',n.classList.add("active"),or();return}r.innerHTML=t.map(a=>`
        <article class="mayabot-entity-card" data-entity-id="${q(a.id)}">
          ${da(a)}
          <h3 class="mayabot-entity-name">${q(a.title)}</h3>
          <p class="mayabot-entity-meta">${q(a.subtitle||sr(a.entityType))}</p>
          <p class="mayabot-entity-summary">${q(a.summary||a.body||"Details are available on the website.")}</p>
          ${pa(a)}
          ${fa(a)}
        </article>
      `).join(""),r.querySelectorAll("[data-view-entity]").forEach(a=>{a.addEventListener("click",async()=>{await Ie(a.getAttribute("data-view-entity"))})}),n.classList.add("active"),or()}function ma(t){if(!t)return!1;try{let e=new URL(t,window.location.origin);return e.origin===window.location.origin?(window.location.href=`${e.pathname}${e.search}${e.hash}`,!0):(window.open(e.toString(),"_blank","noopener,noreferrer"),!0)}catch{return!1}}function or(){window.setTimeout(()=>{let t=document.getElementById("mayabot-chat"),e=document.getElementById("mayabot-msgs");e&&(e.innerHTML=""),t&&t.classList.remove("visible")},lt)}async function Ie(t){let e=await tr(t);return ma(e)}async function cr(t,e=Z){let n=Oe({[p.ENTITY_IDS]:t});if(!n.length)return zt([],e),Ee([],[],"missing_entity_ids");try{let r=await Ae(n);return zt(r,e),Ee(n,r)}catch(r){return console.warn("[AI Hub Widget] Entity overlay failed:",r),zt([],e),Ee(n,[],"entity_overlay_fetch_failed")}}function Oe(t){let e=t[p.ENTITY_IDS]||t.ids||t.items||[],n=new Set;return(Array.isArray(e)?e:[]).map(r=>String(r??"").trim()).filter(Boolean).filter(r=>n.has(r)?!1:(n.add(r),!0))}function ur(t={}){if(!Se.length)return!1;let e=String(t.sort_by||t.sortBy||"price_asc").trim().toLowerCase(),n=[...Se].sort((o,i)=>ha(o,i,e)),r=ya(we,e);return zt(n,r),!0}function ha(t,e,n){return n==="price_desc"?Vt(e,qt)-Vt(t,qt):n==="rating"?ir(e,qt)-ir(t,qt):n==="newest"?ar(e)-ar(t):Vt(t,nr)-Vt(e,nr)}function Vt(t,e){return lr([t?.pricing?.price,t?.pricing?.amount,t?.pricing?.premium,t?.pricing?.premium_min,t?.pricing?.monthly_premium,t?.pricing?.annual_premium,t?.pricing?.min_price,t?.pricing?.starting_price,t?.attributes?.price,t?.attributes?.amount,t?.attributes?.premium,t?.attributes?.monthly_premium,t?.attributes?.annual_premium,t?.displayPrice],e)}function ir(t,e){return lr([t?.attributes?.rating,t?.attributes?.review_rating,t?.attributes?.stars,t?.availability?.rating],e)}function ar(t){let e=t?.attributes?.updated_at||t?.attributes?.date||t?.availability?.updated_at||"",n=Date.parse(String(e||""));return Number.isFinite(n)?n:0}function lr(t,e){for(let n of t){let r=_a(n);if(Number.isFinite(r))return r}return e}function _a(t){if(typeof t=="number")return t;let e=String(t??"").replace(/,/g,"").match(/-?\d+(?:\.\d+)?/);return e?Number(e[0]):Number.NaN}function ya(t,e){let n={price_asc:"sorted low to high",price_desc:"sorted high to low",rating:"sorted by rating",newest:"newest first"};return`${String(t||Z).replace(/\s+-\s+sorted.*$/i,"")} - ${n[e]||n.price_asc}`}function dr(t){return t.action===c.SHOW_ENTITIES||t.action===c.COMPARE_ENTITIES||t.action===c.OPEN_ENTITY_DETAIL||t.action===c.SORT_ENTITIES}async function pr(t){return t.action===c.SHOW_ENTITIES||t.action===c.COMPARE_ENTITIES?ga(t.parameters||{}):t.action===c.OPEN_ENTITY_DETAIL?Ie(t.parameters?.[p.ENTITY_ID]||t.parameters?.id):t.action===c.SORT_ENTITIES?ur(t.parameters||{}):!1}function ga(t){return cr(Oe(t),t[p.SEARCH_QUERY]||t.title||Z)}var wt="mayabot-handoff-panel",fr="mayabot-handoff-overlay-styles",ba=Object.freeze(["contact","support","help"]),Ta=Object.freeze(["checkout","cart"]),yr=new Set([c.CHECKOUT_HANDOFF,c.HANDOFF_TO_ADVISOR,c.HANDOFF_TO_AGENT,c.HANDOFF_TO_CLINIC,c.HANDOFF_TO_HUMAN,c.HANDOFF_TO_LAWYER,c.HANDOFF_TO_LICENSED_AGENT,c.HANDOFF_TO_RECRUITER]),mr=Object.freeze({[c.CHECKOUT_HANDOFF]:{title:"Checkout needs your confirmation",body:"This step may include payment or a secure checkout page. I can take you there, then you complete the final step yourself.",primary:"Open checkout"},[c.HANDOFF_TO_ADVISOR]:{title:"Advisor handoff",body:"This request needs a qualified advisor. I can open the contact path so the site team can continue.",primary:"Contact advisor"},[c.HANDOFF_TO_AGENT]:{title:"Agent handoff",body:"This step needs an agent or account-specific help. I can open the contact path for follow-up.",primary:"Contact agent"},[c.HANDOFF_TO_CLINIC]:{title:"Clinic handoff",body:"This request needs clinic confirmation. I can open the appointment or contact path for the next step.",primary:"Contact clinic"},[c.HANDOFF_TO_HUMAN]:{title:"Human handoff",body:"This step needs human confirmation. I can open the most relevant contact path.",primary:"Open contact"},[c.HANDOFF_TO_LAWYER]:{title:"Legal handoff",body:"This request needs a legal professional. I can open the consultation or contact path.",primary:"Contact lawyer"},[c.HANDOFF_TO_LICENSED_AGENT]:{title:"Licensed agent handoff",body:"This request needs a licensed agent. I can open the quote or contact path for follow-up.",primary:"Contact agent"},[c.HANDOFF_TO_RECRUITER]:{title:"Recruiter handoff",body:"This request needs recruiter review. I can open the application or contact path.",primary:"Contact recruiter"}});function dt(t){return String(t??"").replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;").replace(/"/g,"&quot;").replace(/'/g,"&#039;")}function ot(t){return String(t||"").trim()}function Aa(){if(document.getElementById(fr))return;let t=document.createElement("style");t.id=fr,t.textContent=`
    #${wt} {
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
    #${wt}.active {
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
      #${wt} {
        bottom: 82px;
        width: min(calc(100vw - 20px), 420px);
      }
    }
  `,document.head.appendChild(t)}function Ea(){Aa();let t=document.getElementById(wt);return t||(t=document.createElement("div"),t.id=wt,t.setAttribute("aria-live","polite"),document.body.appendChild(t),t)}function Sa(){return window.AIHubAdapterRuntime?.config?.adapter?.routes||window.AIHubAdapter?.config?.adapter?.routes||{}}function wa(t,e){let n=hr(e[p.URL]||e.path||e.href||e.handoff_flow?.page_url);if(n)return n;let r=Sa(),o=t===c.CHECKOUT_HANDOFF?Ta:ba;for(let i of o){let a=hr(r[i]);if(a)return a}return""}function hr(t){let e=ot(t);if(!e)return"";try{let n=new URL(e,window.location.origin);return n.origin!==window.location.origin?"":`${n.pathname}${n.search}${n.hash}`||"/"}catch{return""}}function Ia(t){return mr[t]||mr[c.HANDOFF_TO_HUMAN]}function Oa(t){return t&&typeof t=="object"?t:{}}function Ca(t,e){return ot(t.title)||e}function Ra(t,e,n){return ot(e[p.MESSAGE])||ot(t.handling)||n}function xa(t,e){return ot(e[p.REASON]||e.reason||e.blocked_reason||t.key)}function Na(t){let e=[["Provider",t.provider_label||t.provider],["Boundary",t.automation_boundary],["Recovery",t.recovery],["Evidence",t.evidence],["Page",t.page_url]].filter(([,n])=>ot(n));return e.length?`
    <p class="mayabot-handoff-meta">
      ${e.map(([n,r])=>`<span><strong>${dt(n)}:</strong> ${dt(r)}</span>`).join("")}
    </p>
  `:""}function _r(t){t.classList.remove("active")}function va(){window.setTimeout(()=>{let t=document.getElementById("mayabot-chat"),e=document.getElementById("mayabot-msgs");e&&(e.innerHTML=""),t&&t.classList.remove("visible")},lt)}function gr(t,e={}){let n=ot(t).toUpperCase(),r=Ia(n),o=Oa(e.handoff_flow),i=Ea(),a=wa(n,e),s=Ca(o,r.title),u=Ra(o,e,r.body),f=xa(o,e);return i.innerHTML=`
    <div class="mayabot-handoff-body">
      <div class="mayabot-handoff-top">
        <h2 class="mayabot-handoff-title">${dt(s)}</h2>
        <button class="mayabot-handoff-close" type="button" aria-label="Close handoff">&times;</button>
      </div>
      <p class="mayabot-handoff-text">${dt(u)}</p>
      ${Na(o)}
      ${f?`<p class="mayabot-handoff-reason">${dt(f)}</p>`:""}
      <div class="mayabot-handoff-actions">
        <button type="button" class="secondary" data-close-handoff>Close</button>
        ${a?`<button type="button" data-open-handoff>${dt(r.primary)}</button>`:""}
      </div>
    </div>
  `,i.querySelector(".mayabot-handoff-close")?.addEventListener("click",()=>_r(i)),i.querySelector("[data-close-handoff]")?.addEventListener("click",()=>_r(i)),i.querySelector("[data-open-handoff]")?.addEventListener("click",()=>{window.location.href=a}),i.classList.add("active"),va(),!0}function br(t){return yr.has(t.action)}function Tr(t){return gr(t.action,t.parameters||{})}function Er(t){return t.action===c.NAVIGATE_TO&&!!wr(t.parameters?.[p.PAGE])}function Sr(t){return window.location.href=wr(t.parameters?.[p.PAGE]),!0}function wr(t){let e=String(t||"").trim();if(!e||Ir(e)||/^https?:\/\//i.test(e))return"";if(e==="home"||e==="/")return"/";let n=La(e);if(n)return n;let r=e.replace(/^\/+|\/+$/g,"");return r?`/${r}`:"/"}function La(t){let e=window.AIHubAdapterRuntime?.config?.adapter?.routes||window.AIHubAdapter?.config?.adapter?.routes||{},n=Pa(t);for(let r of n){let o=e[r],i=Ar(o);if(i)return i}for(let[r,o]of Object.entries(e)){if(!n.includes(Ce(r)))continue;let i=Ar(o);if(i)return i}return""}function Pa(t){let e=Ce(t),n=String(t||"").trim().replace(/^\/+|\/+$/g,"").toLowerCase(),r=n.split("?")[0].split("#")[0].split("/").filter(Boolean).pop()||"";return Array.from(new Set([e,n,Ce(r)].filter(Boolean)))}function Ce(t){return String(t||"").trim().toLowerCase().replace(/[^a-z0-9/_\s-]+/g," ").replace(/[_-]+/g," ").replace(/\s+/g," ").trim().replace(/\s+/g,"-")}function Ar(t){let e=String(t||"").trim();if(!e||Ir(e))return"";if(/^https?:\/\//i.test(e))try{let n=new URL(e);return n.origin!==window.location.origin?"":`${n.pathname||"/"}${n.search||""}${n.hash||""}`}catch{return""}return e.startsWith("/")?e:`/${e.replace(/^\/+/,"")}`}function Ir(t){return/^(?:javascript:|data:|\/\/)/i.test(String(t||"").trim())}function Or(t){let e=t?.params||t?.parameters||{};return{...t||{},action:String(t?.action||"").trim().toUpperCase(),params:e,parameters:e}}var Re="AIHubAdapterRuntime",xe="AIHubAdapter";function Da(t){let e=t?.params||t?.parameters||{};return{...t||{},params:e,parameters:e}}function It(){return!!(window[Re]?.executeAction||window[xe]?.handleAction)}async function Ne(t){return(await Ot(t)).succeeded}async function Ot(t){let e=Da(t);if(window[Re]?.executeAction){let n=window[Re],r=await n.executeAction(e)===!0,o=n.lastActionResult||{};return{succeeded:r,handled:o.handled===!0||r,status:o.status||(r?"ok":"not_handled"),reason:o.reason||"",blocked:o.status==="blocked",disabled:o.status==="disabled"}}if(window[xe]?.handleAction){let n=await window[xe].handleAction(e)===!0;return{succeeded:n,handled:n,status:n?"ok":"not_handled",reason:"",blocked:!1,disabled:!1}}return{succeeded:!1,handled:!1,status:"missing_adapter",reason:"",blocked:!1,disabled:!1}}var Ua=Object.freeze([{path:"/api/products?per_page=96",routePrefix:"/product/"},{path:"/api/products",routePrefix:"/product/"},{path:"/api/products.json",routePrefix:""},{path:"/products.json",routePrefix:"/products/"},{path:"/collections/all/products.json",routePrefix:"/products/"}]),ka=Object.freeze(["products","data","items","results"]),Rr=Object.freeze(["id","product_id","handle","sku"]),xr=Object.freeze(["name","title"]),Ma=Object.freeze(["url","href","permalink","product_url"]),Fa=Object.freeze(["image_url","imageUrl","image_src","imageSrc","image","images","media","thumbnail","thumbnail_url","featured_image","featuredImage","featured_image_url"]),Ha=Object.freeze(["brand","vendor"]),Ba=Object.freeze(["category","category_name","product_type"]),Ya=Object.freeze(["description","summary","body_html"]),$a=Object.freeze(["original_price","compare_at_price","regular_price"]),Nr=Object.freeze(["currency","currency_code"]),ja=Object.freeze(["display_price","price_text","formatted_price"]),qa="Unknown Brand",Va="Products",za="/",Ga=/^[a-z0-9][a-z0-9-]*$/i,ve=null;function D(t){return t==null||typeof t=="object"?"":String(t||"").trim()}function De(t){return D(t).toLowerCase().replace(/[^a-z0-9]+/g," ").trim()}function vr(t){let e=new Set(["a","am","an","and","ask","asked","did","for","me","not","on","only","please","show","some","the","to","wanna","want","what","with","you","your"]),n=[],r=new Set;for(let o of Wa(De(t)).split(" ")){let i=Ka(o);i.length<=1||e.has(i)||r.has(i)||(n.push(i),r.add(i))}return n}function Wa(t){return t.replace(/\b(?:i\s+)?did\s+not\s+ask\s+for\s+(?:a\s+|an\s+)?[a-z0-9]+\b/g," ")}function Ka(t){return["phone","phones","mobile","mobiles"].includes(t)?"phone":["book","books"].includes(t)?"books":t}function Ue(t,e){return e.map(n=>D(t?.[n])).filter(Boolean)}function F(t,e){return Ue(t,e)[0]||""}function Gt(t){let e=D(t).replace(/,/g,"");if(!e)return 0;let n=e.match(/-?\d+(?:\.\d+)?/),r=Number(n?n[0]:e);return Number.isFinite(r)?r:0}function Qa(t,e){let n=F(t,ja);if(n)return n;let r=F(t,Nr).toUpperCase();return e>0&&r?`${r} ${e.toLocaleString()}`:e>0?e.toLocaleString():""}function Xa(t){for(let e of Fa){let n=Le(t?.[e]);if(n)return n}return""}function Le(t){if(!t)return"";if(Array.isArray(t)){for(let e of t){let n=Le(e);if(n)return n}return""}if(typeof t=="object"){for(let e of["src","url","image_url","imageUrl","image_src","imageSrc","thumbnail","thumbnail_url","featured_image","featuredImage","featured_image_url"]){let n=Le(t[e]);if(n)return n}return""}return Ja(t)}function Ja(t){let e=D(t);if(!e||/^javascript:/i.test(e))return"";if(/^data:image\//i.test(e))return e;try{let n=new URL(e,window.location.origin);return["http:","https:"].includes(n.protocol)?n.toString():""}catch{return""}}function Za(t){let e=D(t);if(!e)return"";try{let n=new URL(e,window.location.origin);return n.origin!==window.location.origin?"":`${n.pathname}${n.search}${n.hash}`}catch{return""}}function ts(t,e,n){let r=Za(F(t,Ma));return r||(!Ga.test(e)||!/[a-z]/i.test(e)||!n?.routePrefix?"":`${n.routePrefix}${encodeURIComponent(e)}${za}`)}function ke(t,e={}){if(!t)return null;let n=F(t,Rr),r=D(t.handle||t.slug||t.product_handle),o=F(t,xr),i=Gt(t.price||t.amount||t.cost),a=Gt(F(t,$a));return!n&&!r?null:{id:n,handle:r,name:o,title:D(t.title||o),brand:F(t,Ha)||qa,category:F(t,Ba)||Va,description:F(t,Ya),price:Number.isFinite(i)?i:0,originalPrice:Number.isFinite(a)?a:0,displayPrice:Qa(t,i),currency:F(t,Nr),rating:Gt(t.rating||t.review_rating),reviewCount:Gt(t.review_count||t.reviews_count||t.reviews),imageUrl:Xa(t),url:ts(t,r||n,e)}}function es(t){return Ue(t,Rr)}function Cr(t){return Ue(t,xr).map(De)}function Lr(t,e){let n=D(e);return!!(n&&es(t).includes(n))}function Pr(t,e){let n=vr(e);if(!n.length)return!1;let r=De([t?.name,t?.title,t?.brand,t?.category,t?.category_name,t?.product_type,t?.description,t?.tags].join(" "));return n.every(o=>r.includes(o)||r.includes(o.replace(/s$/,"")))}function ns(t,e){let n=new Set(Cr(e));return Cr(t).some(r=>n.has(r))}function rs(t,e){return!!(t?.imageUrl&&t.imageUrl===e?.imageUrl)}function os(t){if(Array.isArray(t))return t;for(let e of ka){let n=t?.[e];if(Array.isArray(n))return n}return[]}async function is(t){try{let e=await fetch(new URL(t.path,window.location.origin),{headers:{Accept:"application/json"}});if(!e.ok)return[];let n=await e.json();return os(n).map(r=>ke(r,t)).filter(Boolean)}catch(e){return console.warn(`[AI Hub Widget] Catalog endpoint lookup failed for ${t.path}:`,e),[]}}async function Pe(){return ve||(ve=Promise.all(Ua.map(is)).then(t=>t.flat())),ve}async function as(t,e=120){if(!vr(t).length)return[];let r=new URL("/v1/products",d.apiUrl);r.searchParams.set("site_id",d.siteId),r.searchParams.set("limit",String(e));try{let o=await fetch(r.toString(),{headers:{Accept:"application/json"}});return o.ok?(await o.json()).map(i=>ke(i)).filter(Boolean).filter(i=>Pr(i,t)).slice(0,12):[]}catch(o){return console.warn("[AI Hub Widget] Hub product search fallback failed:",o),[]}}async function Dr(t,e=""){let n=(Array.isArray(t)?t:[]).map(D).filter(Boolean),r=[],o="",i="";if(n.length)try{r=await Ur(n),o="hub_by_ids"}catch(a){i="hub_product_lookup_failed",console.warn("[AI Hub Widget] Hub product ID lookup failed:",a)}if(!r.length&&n.length){let a=await Pe();r=n.map(s=>a.find(u=>Lr(u,s))).filter(Boolean),r.length&&(o="host_by_ids")}return!r.length&&e&&(r=await as(e),r.length&&(o="hub_search")),!r.length&&e&&(r=(await Pe()).filter(s=>Pr(s,e)).slice(0,12),r.length&&(o="host_search")),{products:r,source:o,reason:r.length?"":i||"no_matching_products_rendered"}}async function Ur(t){let e=(Array.isArray(t)?t:[]).map(D).filter(Boolean);if(!e.length)return[];let n=new URL(U.PRODUCTS_BY_IDS,d.apiUrl);n.searchParams.set("site_id",d.siteId),n.searchParams.set("ids",e.join(","));let r=await fetch(n.toString(),{headers:{Accept:"application/json"}});if(!r.ok)throw new Error("Failed to fetch products from AI Hub API");let o=(await r.json()).map(a=>ke(a)).filter(Boolean),i=new Map(o.map(a=>[String(a.id),a]));return e.map(a=>i.get(a)).filter(Boolean)}async function Wt(t){let e=D(t);if(!e)return"";let[n]=await Ur([e]);if(n?.url)return n.url;let r=await Pe(),o=r.find(a=>Lr(a,e));return o?.url?o.url:n&&r.find(a=>ns(a,n)||rs(a,n))?.url||""}var ss=1,cs=1.08,us=300,ls=Object.freeze(["hannah","sonia","libby","ava","susan","hazel","heera","salli","joanna","amy","emma","olivia","natasha","zira","aria","jenny","samantha","victoria","tessa","moira","karen","female","woman","nova","shimmer","google us english","microsoft aria"]),V="",Kt="",Ct=null,Me=0;function it(t){if(!("speechSynthesis"in window)||!("SpeechSynthesisUtterance"in window))return!1;Qt();let e=++Me;V=t;let n=()=>{if(e!==Me||V!==t)return!1;try{let r=new SpeechSynthesisUtterance(t),o=ds(window.speechSynthesis.getVoices());return o?(o&&(r.voice=o),r.rate=ss,r.pitch=cs,r.onstart=kr,r.onend=kr,Qt(),window.speechSynthesis.cancel(),window.speechSynthesis.resume(),window.speechSynthesis.speak(r),!0):(V="",!1)}catch{return!1}};return window.speechSynthesis.getVoices().length>0?n():(window.speechSynthesis.onvoiceschanged=n,Ct=window.setTimeout(()=>{Ct=null,n()},us),!0)}function Xt(){V&&it(V)}function Mr(){try{return!!V||!!window.speechSynthesis?.speaking||!!window.speechSynthesis?.pending}catch{return!!V}}function Jt(){Me+=1,Qt(),V="",Kt="";try{window.speechSynthesis?.cancel()}catch{}}function ds(t){if(!Array.isArray(t)||t.length===0)return null;let e=ps(t)||fs(t);return e&&(Kt=e.name),e}function ps(t){if(Kt){let n=t.find(r=>r.name===Kt);if(n)return n}let e=String(d.speechVoiceName||"").toLowerCase();return e&&t.find(n=>n.name.toLowerCase()===e)||null}function fs(t){return d.speechVoicePreference.toLowerCase()!=="female"?t.find(e=>e.default)||t[0]:t.find(e=>ls.some(n=>e.name.toLowerCase().includes(n)))||null}function kr(){Qt(),V=""}function Qt(){Ct&&window.clearTimeout(Ct),Ct=null,window.speechSynthesis&&(window.speechSynthesis.onvoiceschanged=null)}var ms=["data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='320' height='240' viewBox='0 0 320 240'%3E","%3Crect width='320' height='240' fill='%23f1f2ee'/%3E","%3Cpath d='M98 156h124l-31-40-25 30-17-22-51 32Z' fill='%23c8c3ba'/%3E","%3Ccircle cx='117' cy='95' r='17' fill='%23d8d3ca'/%3E","%3Ctext x='160' y='198' text-anchor='middle' fill='%23686660' font-family='Arial,sans-serif' font-size='16'%3EImage pending%3C/text%3E","%3C/svg%3E"].join(""),Fr=12,hs=4,_s=6,ys=700,te=[],He=j,ee=new Map,Be=!1;function gs(){try{Jt()}catch{}}function tt(t){return String(t??"").replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;").replace(/"/g,"&quot;").replace(/'/g,"&#039;")}function bs(){if(document.getElementById("mayabot-product-overlay-styles"))return;let t=document.createElement("style");t.id="mayabot-product-overlay-styles",t.textContent=`
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
  `,document.head.appendChild(t)}function Ts(){bs();let t=document.getElementById("mayabot-product-panel");return t||(t=document.createElement("div"),t.id="mayabot-product-panel",t.setAttribute("aria-live","polite"),t.setAttribute("role","dialog"),t.setAttribute("tabindex","-1"),t.innerHTML=`
    <div class="mayabot-product-header">
      <h2 class="mayabot-product-title">${j}</h2>
      <button class="mayabot-product-close" type="button" aria-label="Close recommendations">&times;</button>
    </div>
    <div class="mayabot-compare-speak" role="group" aria-label="Speak comparison">
      <p>Would you like me to speak all the comparison points?</p>
      <button type="button" class="mayabot-compare-yes">Yes</button>
      <button type="button" class="mayabot-compare-no secondary">No</button>
    </div>
    <div class="mayabot-product-grid"></div>
  `,t.querySelector(".mayabot-product-close").addEventListener("click",Hr),t.querySelector(".mayabot-compare-yes").addEventListener("click",()=>Br(!0)),t.querySelector(".mayabot-compare-no").addEventListener("click",()=>Br(!1)),t.addEventListener("keydown",e=>{e.key==="Escape"&&Hr()}),document.body.appendChild(t),t)}function Hr(){let t=document.getElementById("mayabot-product-panel");t&&(t.classList.remove("active","ask-speak"),gs())}function Br(t){let e=document.getElementById("mayabot-product-panel");if(e&&e.classList.remove("ask-speak"),Be=!0,t){let n=Es(te);n&&it(n)}}function As(t,e){let n=document.getElementById("mayabot-product-panel");if(!n)return;if(!(e&&Array.isArray(t)&&t.length>=2)||Be){n.classList.remove("ask-speak");return}n.classList.add("ask-speak"),window.setTimeout(()=>n.querySelector(".mayabot-compare-yes")?.focus(),0)}function Es(t){let e=[];for(let n of(t||[]).slice(0,hs)){let o=(ee.get(String(n.id))||[]).slice(0,_s).map(a=>`${a.label}: ${a.value}`).join(", "),i=n.name||n.title||"This product";e.push(o?`${i}. ${o}.`:`${i}.`)}return e.join(" ").slice(0,ys)}async function Ss(t){let e={action:c.ADD_TO_CART,params:{[p.PRODUCT_ID]:t,[p.QUANTITY]:_e},parameters:{[p.PRODUCT_ID]:t,[p.QUANTITY]:_e}};It()&&await Ne(e)||window.dispatchEvent(new CustomEvent(Et.MAYABOT_ACTION,{detail:e}))}async function ws(t){try{let n=await Wt(t);if(n){window.location.href=n;return}}catch(n){console.warn("[AI Hub Widget] Product detail URL lookup failed:",n)}let e={action:c.SHOW_PRODUCT_DETAIL,params:{[p.PRODUCT_ID]:t},parameters:{[p.PRODUCT_ID]:t}};It()&&await Ne(e)||window.dispatchEvent(new CustomEvent(Et.MAYABOT_ACTION,{detail:e}))}function Is(t){return t<=1?"count-1":t===2?"count-2":t===3?"count-3":"count-many"}function Os(t){return t<=1?1:t===2?2:3}function Cs(t){let e=new Set;return(Array.isArray(t)?t:[]).map(n=>String(n??"").trim()).filter(Boolean).filter(n=>e.has(n)?!1:(e.add(n),!0))}function Fe(t,e,n="",r={}){let o=(Array.isArray(e)?e:[]).map(u=>String(u?.id??"").trim()).filter(Boolean),i=o.length,a=t.length,s=i>0?"succeeded":"failed";return{status:s,stage:"product_overlay",reason:n||(s==="succeeded"?"":"no_matching_products_rendered"),evidence:{requested_product_count:a,rendered_product_count:i,missing_product_count:Math.max(a-i,0),requested_product_ids:t.slice(0,Fr).join(","),rendered_product_ids:o.slice(0,Fr).join(","),lookup_source:r.source||"",search_query:r.searchQuery||""}}}function Rs(t){let e=String(t?.displayPrice||"").trim();if(e)return e;let n=Number(t?.price||0);return Number.isFinite(n)&&n>0?n.toLocaleString():"Price unavailable"}var xs=6,Ns=24,vs=120;function Ls(t){let e=new Map;return Array.isArray(t)&&t.forEach(n=>{if(!n||typeof n!="object")return;let r=String(n.product_id||"").trim();if(!r||!Array.isArray(n.facts))return;let o=n.facts.filter(i=>i&&typeof i=="object"&&i.label&&i.value).slice(0,xs).map(i=>({label:String(i.label).slice(0,Ns),value:String(i.value).slice(0,vs)}));o.length&&e.set(r,o)}),e}function Ps(t){let e=ee.get(String(t));return!e||!e.length?"":`<dl class="mayabot-product-facts">${e.map(r=>`<div class="mayabot-fact"><dt>${tt(r.label)}</dt><dd>${tt(r.value)}</dd></div>`).join("")}</dl>`}function Zt(t,e){let n=Ts(),r=n.querySelector(".mayabot-product-grid"),o=n.querySelector(".mayabot-product-title"),i=t.length;if(te=Array.isArray(t)?[...t]:[],He=e||j,n.classList.remove("count-1","count-2","count-3","count-many"),n.classList.add(Is(i)),n.style.setProperty("--mayabot-card-count",String(Os(i))),o.textContent=He,!i){r.innerHTML='<p class="mayabot-product-empty">No matching products are currently available.</p>',n.classList.add("active");return}r.innerHTML=t.map(a=>{let s=tt(a.id);return`
        <article class="mayabot-product-card" data-product-id="${s}">
          <img class="mayabot-product-image" src="${tt(a.imageUrl||ms)}" alt="${tt(a.name)}">
          <h3 class="mayabot-product-name">${tt(a.name||a.title||"Product")}</h3>
          <p class="mayabot-product-meta">${tt(a.brand)} - ${tt(Rs(a))}</p>
          ${Ps(a.id)}
          <div class="mayabot-product-actions">
            <button type="button" data-add="${s}">Add</button>
            <button type="button" class="secondary" data-view="${s}">View</button>
          </div>
        </article>
      `}).join(""),r.querySelectorAll("[data-add]").forEach(a=>{a.addEventListener("click",async()=>{await Ss(a.getAttribute("data-add"))})}),r.querySelectorAll("[data-view]").forEach(a=>{a.addEventListener("click",async()=>{await ws(a.getAttribute("data-view"))})}),n.classList.add("active"),t.length>0&&Ds()}function Ds(){window.setTimeout(()=>{let t=document.getElementById("mayabot-chat"),e=document.getElementById("mayabot-msgs");e&&(e.innerHTML=""),t&&t.classList.remove("visible")},lt)}async function $r(t,e=j,n={}){let r=Cs(t),o=String(n.searchQuery||"").trim();ee=Ls(n.comparisonFacts);let i=ee.size>0;if(Be=!1,!r.length&&!o)return Zt([],e),Fe([],[],"missing_product_ids");try{let{products:a,source:s,reason:u}=await Dr(r,o);return Zt(a,e),As(a,i),Fe(r,a,u,{source:s,searchQuery:o})}catch(a){return console.warn("[AI Hub Widget] Product overlay failed:",a),Zt([],e),Fe(r,[],"product_overlay_fetch_failed",{searchQuery:o})}}function jr(t={}){if(!te.length)return!1;let e=String(t.sort_by||t.sortBy||"price_asc").trim().toLowerCase(),n=[...te].sort((r,o)=>Us(r,o,e));return Zt(n,ks(He,e)),!0}function Us(t,e,n){return n==="price_desc"?pt(e.price,Number.NEGATIVE_INFINITY)-pt(t.price,Number.NEGATIVE_INFINITY):n==="rating"?pt(e.rating||e.review_rating,Number.NEGATIVE_INFINITY)-pt(t.rating||t.review_rating,Number.NEGATIVE_INFINITY):n==="newest"?Yr(e)-Yr(t):pt(t.price,Number.POSITIVE_INFINITY)-pt(e.price,Number.POSITIVE_INFINITY)}function pt(t,e){let n=String(t??"").replace(/,/g,"").match(/-?\d+(?:\.\d+)?/);if(!n)return e;let r=Number(n[0]);return Number.isFinite(r)?r:e}function Yr(t){let e=t?.updated_at||t?.created_at||t?.date||"",n=Date.parse(String(e||""));return Number.isFinite(n)?n:0}function ks(t,e){let n={price_asc:"sorted low to high",price_desc:"sorted high to low",rating:"sorted by rating",newest:"newest first"};return`${String(t||j).replace(/\s+-\s+sorted.*$/i,"")} - ${n[e]||n.price_asc}`}function Vr(t){return t.action===c.SHOW_PRODUCTS||t.action===c.SHOW_COMPARISON||t.action===c.SHOW_PRODUCT_DETAIL||t.action===c.SORT_PRODUCTS}async function zr(t){return t.action===c.SHOW_COMPARISON?qr(t.parameters||{},"Product comparison",{syncListing:!1,comparisonFacts:(t.parameters||{}).comparison}):t.action===c.SHOW_PRODUCTS?qr(t.parameters||{},j):t.action===c.SHOW_PRODUCT_DETAIL?Hs(t.parameters||{}):t.action===c.SORT_PRODUCTS?jr(t.parameters||{}):!1}async function qr(t,e=j,n={}){let r=Array.isArray(t[p.PRODUCT_IDS])?t[p.PRODUCT_IDS]:[],o=Fs(t),a=n.syncListing!==!1?await Ms(o):{succeeded:!1,handled:!1,status:"skipped",stage:"product_display_sync",reason:"comparison_overlay"},s=await $r(r,t.title||o||e,{searchQuery:o,comparisonFacts:n.comparisonFacts}),u={...s.evidence||{},listing_sync_status:a.status||"",listing_sync_stage:a.stage||"",listing_sync_reason:a.reason||""};return s.status!=="succeeded"?{...s,evidence:u}:o&&a.handled&&!a.succeeded?{status:"failed",stage:"product_display_sync",reason:a.reason||a.status||"listing_sync_failed",evidence:u}:{...s,stage:a.succeeded?"product_display_sync":s.stage,evidence:u}}async function Ms(t){let e=Gr(t);return e?Ot({action:c.FILTER_PRODUCTS,params:{[p.SEARCH_QUERY]:e,query:e,q:e}}):{succeeded:!1,handled:!1,status:"skipped",stage:"product_display_sync",reason:"missing_search_query"}}function Fs(t){return Gr(t[p.SEARCH_QUERY]||t.search||t.query||t.q||"")}function Gr(t){return String(t||"").trim()}async function Hs(t){let e="";try{e=await Wt(t[p.PRODUCT_ID])}catch(n){return console.warn("[AI Hub Widget] Product detail URL lookup failed:",n),!1}return e?(window.location.href=e,!0):!1}var Ye="stop_action_fallback",Bs=new Set([c.SHOW_PRODUCTS,c.SHOW_COMPARISON,c.SHOW_PRODUCT_DETAIL,c.SORT_PRODUCTS]);function Wr(t){return It()&&!Bs.has(t.action)}async function Kr(t){let e=await Ot(t);return e.succeeded?!0:e.blocked||e.disabled?Ye:!1}function Qr(t){return window.dispatchEvent(new CustomEvent(Et.MAYABOT_ACTION,{detail:t})),{status:"requested",stage:"browser_event",reason:"event_dispatched_without_confirmation"}}var Ys=12,$s=8,js=80,Xr=Object.freeze([["data-entity-id",""],["data-product-id","product"],["data-listing-id","listing"],["data-offer-id","offer"],["data-plan-id","plan"],["data-item-id",""]]),qs="data-entity-type",Vs="entity",Jr=Object.freeze(["sort","sort_by","sortby","orderby","order_by","order"]),zs=Object.freeze(["page","p","offset","cursor","q","query","search","token","session","email","phone","name","address","utm_source","utm_medium","utm_campaign"]),Gs=Object.freeze([["price","[data-price], [itemprop='price'], .price"],["rating","[data-rating], [itemprop='ratingValue'], .rating"],["availability","[data-availability], [itemprop='availability'], .availability, .stock"]]);function H(t){return String(t||"").replace(/\s+/g," ").trim().slice(0,js)}function Ws(t){if(!t||typeof t.getBoundingClientRect!="function")return!1;let e=t.getBoundingClientRect();if(e.width<=0||e.height<=0)return!1;let n=t.ownerDocument?.defaultView,r=n?.getComputedStyle?.(t);if(r&&(r.visibility==="hidden"||r.display==="none"))return!1;let o=t.ownerDocument?.documentElement,i=Number(n?.innerWidth||o?.clientWidth||0),a=Number(n?.innerHeight||o?.clientHeight||0);return i>0&&a>0&&e.bottom>0&&e.right>0&&e.top<a&&e.left<i}function Ks(t){for(let[e,n]of Xr){let r=H(t.getAttribute(e));if(r)return{id:r,impliedType:n}}return null}function Qs(t,e){return H(t.getAttribute(qs)).toLowerCase()||e||Vs}function Xs(t){let e=t.querySelector?.("h1, h2, h3, h4, [data-entity-name], [itemprop='name']");return H(e?.textContent||t.getAttribute("aria-label")||t.getAttribute("title"))}function Js(t){let e=t.matches?.("a[href]")?t:t.querySelector?.("a[href]");return ic(e?.href||"")}function Zs(t){let e={};for(let[n,r]of Gs){let o=t.querySelector?.(r);if(!o)continue;let i=H(o.getAttribute?.("content")||o.getAttribute?.(`data-${n}`)||o.textContent);i&&(e[n]=i)}return e}function tc(){return Xr.map(([t])=>`[${t}]`).join(",")}function ec(){let t=new Set,e=[];for(let n of x(tc())){if(e.length>=Ys)break;let r=Ks(n);!r||t.has(r.id)||!Ws(n)||(t.add(r.id),e.push({id:r.id,entity_type:Qs(n,r.impliedType),label:Xs(n),route:Js(n),facts:Zs(n)}))}return e}function nc(){let t=Zr();if(!t)return{};let e={};for(let[n,r]of t.entries()){let o=n.toLowerCase();if(!(zs.includes(o)||Jr.includes(o))){if(Object.keys(e).length>=$s)break;e[H(n)]=H(r)}}return e}function rc(){let t=Zr();for(let n of Jr){let r=H(t?.get?.(n));if(r)return r}let e=x("select[name*='sort' i], select[id*='sort' i]")[0];return H(e?.value)}function oc(){try{return{path:H(window.location.pathname)||"/",search:H(window.location.search)}}catch{return{path:"",search:""}}}function ne(){return{route:oc(),filters:nc(),sort:rc(),visible_entities:ec()}}function Zr(){try{return new URLSearchParams(window.location.search)}catch{return null}}function ic(t){if(!t)return"";try{let e=new URL(t,window.location.origin);return e.origin!==window.location.origin?"":`${e.pathname}${e.search}`||"/"}catch{return""}}var Bl=Object.freeze(["CHECKOUT","CLEAR_CART","REMOVE_FROM_CART","UPDATE_CART_QUANTITY","CLEAR_HISTORY","SUBMIT_PAYMENT","PLACE_ORDER"]);var T=Object.freeze({DISPLAY:"display",NAVIGATION:"navigation",DETAIL:"detail",FILTER:"filter",SORT:"sort",CART:"cart",NONE:"none"}),ac=1200,sc=60,cc=Object.freeze({SHOW_PRODUCTS:T.DISPLAY,SHOW_ENTITIES:T.DISPLAY,SHOW_COMPARISON:T.DISPLAY,COMPARE_ENTITIES:T.DISPLAY,NAVIGATE_TO:T.NAVIGATION,SHOW_PRODUCT_DETAIL:T.DETAIL,OPEN_ENTITY_DETAIL:T.DETAIL,FILTER_PRODUCTS:T.FILTER,CLEAR_FILTERS:T.FILTER,SORT_PRODUCTS:T.SORT,SORT_ENTITIES:T.SORT,ADD_TO_CART:T.CART,REMOVE_FROM_CART:T.CART,UPDATE_CART_QUANTITY:T.CART,CLEAR_CART:T.CART}),uc="[data-cart-count], [data-testid='cart-count'], .cart-count, #cart-count";function eo(t){return cc[String(t||"").toUpperCase()]||T.NONE}function qe(){let t=ne();return{path:t.route.path,search:t.route.search,filters:t.filters,sort:String(t.sort||"").toLowerCase(),visibleIds:t.visible_entities.map(e=>String(e.id)),cartCount:lc()}}function lc(){let t=document.querySelector(uc);if(!t)return null;let e=t.getAttribute("data-cart-count")??t.textContent,n=Number.parseInt(String(e||"").replace(/[^\d-]/g,""),10);return Number.isFinite(n)?n:null}function no(t){let e=[];for(let n of["product_ids","entity_ids"])Array.isArray(t[n])&&e.push(...t[n].map(String));for(let n of["product_id","entity_id"])t[n]&&e.push(String(t[n]));return e}function Rt(t){let e=String(t||"").split("?")[0].split("#")[0];return e.length>1?e.replace(/\/+$/,""):e}function $e(t){return String(t||"").trim().toLowerCase().replace(/[^a-z0-9/_\s-]+/g," ").replace(/[_-]+/g," ").replace(/\s+/g," ").trim().replace(/\s+/g,"-")}function to(t){let e=String(t||"").trim();if(!e||/^(?:javascript:|data:|\/\/)/i.test(e))return"";try{let n=new URL(e,window.location.origin);return n.origin!==window.location.origin?"":Rt(n.pathname||"/")}catch{return""}}function dc(t){let e=String(t||"").trim();if(!e)return"";if(e==="/"||$e(e)==="home")return"/";let n=window.AIHubAdapterRuntime?.config?.adapter?.routes||window.AIHubAdapter?.config?.adapter?.routes||{},r=$e(e);for(let[o,i]of Object.entries(n)){if($e(o)!==r)continue;let a=to(i);if(a)return a}return e.startsWith("/")||/^https?:\/\//i.test(e)?to(e):Rt(`/${r}`)}function pc(t,e){let n=no(t);return n.length?n.filter(o=>!e.visibleIds.includes(o)).length?{satisfied:!1,reason:"requested_records_not_visible"}:{satisfied:!0,reason:""}:e.visibleIds.length>0?{satisfied:!0,reason:""}:{satisfied:!1,reason:"nothing_visible"}}function fc(t,e,n){let r=dc(t.page),o=Rt(e.path);return r&&o===r?{satisfied:!0,reason:""}:!r&&o!==Rt(n.path)?{satisfied:!0,reason:""}:r&&o!==Rt(n.path)?{satisfied:!1,reason:"wrong_route"}:{satisfied:!1,reason:"route_unchanged"}}function mc(t,e,n){let r=no(t)[0];return r?`${e.path}${e.search}`.includes(r)?{satisfied:!0,reason:""}:e.visibleIds.includes(r)&&e.path!==n.path?{satisfied:!0,reason:""}:{satisfied:!1,reason:"record_not_opened"}:{satisfied:!1,reason:"no_record_requested"}}function hc(t,e,n){if(t==="CLEAR_FILTERS")return Object.keys(n.filters).length===0?{satisfied:!0,reason:""}:{satisfied:!1,reason:"filters_still_active"};let r=new Map(Object.entries(n.filters).map(([u,f])=>[u.toLowerCase(),je(f)])),o=e.filters&&typeof e.filters=="object"?e.filters:e,i=new Set(["product_ids","entity_ids","page","search_query","query","q","request_id"]),a=Object.entries(o||{}).filter(([u,f])=>!i.has(u.toLowerCase())&&je(f));return a.length?a.every(([u,f])=>{let A=r.get(u.toLowerCase());return A!==void 0&&A===je(f)})?{satisfied:!0,reason:""}:{satisfied:!1,reason:"filter_value_mismatch"}:r.size>0?{satisfied:!0,reason:""}:{satisfied:!1,reason:"no_filter_observed"}}function je(t){return(Array.isArray(t)?t:[t]).map(n=>String(n??"").trim().toLowerCase()).filter(Boolean).sort().join(",")}function _c(t,e,n){let r=String(t.sort_by||"").toLowerCase();return r&&e.sort&&e.sort.includes(r.split("_")[0])?{satisfied:!0,reason:""}:e.visibleIds.join(",")!==n.visibleIds.join(",")?{satisfied:!0,reason:""}:{satisfied:!1,reason:"order_unchanged"}}function yc(t,e,n){if(n.cartCount===null||e.cartCount===null)return{satisfied:!1,reason:"cart_state_unobservable"};let r=e.cartCount>n.cartCount,o=e.cartCount<n.cartCount;return t==="ADD_TO_CART"?r?{satisfied:!0,reason:""}:{satisfied:!1,reason:"cart_unchanged"}:t==="REMOVE_FROM_CART"?o?{satisfied:!0,reason:""}:{satisfied:!1,reason:"cart_unchanged"}:t==="CLEAR_CART"?e.cartCount===0?{satisfied:!0,reason:""}:{satisfied:!1,reason:"cart_not_empty"}:e.cartCount!==n.cartCount?{satisfied:!0,reason:""}:{satisfied:!1,reason:"cart_unchanged"}}function gc(t,e,n){let r=String(t?.action||"").toUpperCase(),o=t?.parameters||t?.params||{},i=eo(r);return i===T.DISPLAY?pc(o,e):i===T.NAVIGATION?fc(o,e,n):i===T.DETAIL?mc(o,e,n):i===T.FILTER?hc(r,o,e):i===T.SORT?_c(o,e,n):i===T.CART?yc(r,e,n):{satisfied:!0,reason:"no_postcondition"}}async function ro(t,e){let n=eo(t?.action);if(n===T.NONE)return{family:n,verified:!0,reason:"no_postcondition"};let r=Date.now()+ac,o={satisfied:!1,reason:"not_observed"};for(;Date.now()<r&&(o=gc(t,qe(),e),!o.satisfied);)await bc(sc);return{family:n,verified:o.satisfied,reason:o.reason}}function bc(t){return new Promise(e=>window.setTimeout(e,t))}var h=Object.freeze({searchForm:"search-form",searchInput:"search-input",searchSubmit:"search-submit",searchResults:"search-results",addToCart:"add-to-cart",clearCart:"clear-cart",cartButton:"cart-button",cartLineItem:"cart-line-item",navLink:"nav-link",productCard:"product-card",productLink:"product-link",productName:"product-name",productDetail:"product-detail",productTitle:"product-title"}),Ve="data-aihub-nav",oo="data-entity-name",z=4e3,io=1500,Tc=80,Ac='[id^="mayabot"], [data-aihub-widget]';function ft(t){return!!t&&!t.closest?.(Ac)}var mt=t=>`[data-aihub-role="${t}"]`,st=t=>x(mt(t)).filter(ft),S=t=>st(t)[0]||null;function Ec(t){let e=g(t);return e&&x(`[data-product-id="${ze(e)}"]`).find(ft)||null}function g(t){return String(t??"").trim()}function ze(t){return window.CSS?.escape?window.CSS.escape(t):g(t).replace(/["\\]/g,"\\$&")}async function B(t,e){let n=Date.now()+e;for(;;){let r=t();if(r)return r;if(Date.now()>=n)return null;await new Promise(o=>window.setTimeout(o,Tc))}}function G(){return!!(S(h.searchForm)||S(h.searchInput)||S(h.searchSubmit))}function xt(){return!!S(h.addToCart)}function Nt(){return!!S(h.clearCart)}function vt(){return st(h.navLink).length>0}function ct(){return We().length>0}function W(t){let e=String(t||"").split("?")[0].split("#")[0];return e.length>1?e.replace(/\/+$/,""):e||"/"}function Ge(t){try{let e=new URL(String(t||""),window.location.origin);return e.origin!==window.location.origin?"":`${e.pathname}${e.search}`||"/"}catch{return""}}function Lt(t){return g(t).toLowerCase().replace(/[^a-z0-9]+/g," ").trim()}function at(t){return g(t).toLowerCase().replace(/[\s\-_/\\,.:;|]+/g," ").replace(/\s+/g," ").trim()}function We(){let t=st(h.productCard);return t.length?t:x("[data-product-id]").filter(ft)}function re(t){let e=g(t?.getAttribute?.(oo));return e||g(t?.querySelector?.(mt(h.productName))?.textContent)}var Ke="product_id",Sc="product_name";function oe(t,e){let n=Ec(t);if(n)return{card:n,matchedBy:Ke};let r=at(e);if(!r)return null;let o=We().filter(i=>at(re(i))===r);return o.length===1?{card:o[0],matchedBy:Sc}:o.length>1?{ambiguous:!0,matchCount:o.length}:null}function K(t,e,n=""){return{handled:!0,status:"succeeded",self_verified:!0,stage:t,reason:n,evidence:e||{}}}function E(t,e,n){return{handled:!0,status:"failed",stage:t,reason:e,evidence:n||{}}}function ao(t,e,n){return{handled:!0,status:"unconfirmed",stage:t,reason:e,evidence:n||{}}}function so(t,e){return{handled:!0,status:"unsupported_host",stage:t,reason:e,evidence:{}}}function Q(t){return t?(fo(t),co(t,"down"),co(t,"up"),typeof t.click=="function"?t.click():mo(t,"click"),Cc(t),!0):!1}function lo(t,e){return t?(fo(t),wc(t,ae(e)),Ic(t),!0):!1}function po(t){if(!t)return!1;let e=ae(t.tagName).toLowerCase()==="form"?t:t.closest?.("form");return e&&typeof e.requestSubmit=="function"?(e.requestSubmit(),!0):Q(t)}function fo(t){try{t.scrollIntoView?.({behavior:"smooth",block:"center",inline:"center"})}catch{}typeof t.focus=="function"&&t.focus({preventScroll:!0})}function wc(t,e){if(Rc(t)){t.textContent=e;return}let n=Object.getPrototypeOf(t),r=Object.getOwnPropertyDescriptor(n,"value");if(r?.set){r.set.call(t,e);return}t.value=e}function Ic(t){uo(t,"beforeinput"),uo(t,"input"),t.dispatchEvent(new Event("change",{bubbles:!0}))}function co(t,e){Oc(t,`pointer${e}`),mo(t,`mouse${e}`)}function Oc(t,e){typeof PointerEvent=="function"&&t.dispatchEvent(new PointerEvent(e,{bubbles:!0,cancelable:!0,pointerType:"mouse",isPrimary:!0}))}function mo(t,e){t.dispatchEvent(new MouseEvent(e,{bubbles:!0,cancelable:!0,view:window}))}function uo(t,e){if(typeof InputEvent=="function"){t.dispatchEvent(new InputEvent(e,{bubbles:!0,cancelable:!0,inputType:"insertText"}));return}t.dispatchEvent(new Event(e,{bubbles:!0,cancelable:!0}))}function Cc(t){let e=ae(t.getAttribute?.("role")).toLowerCase();["button","link","menuitem","option","tab"].includes(e)&&(ie(t,"keydown","Enter"),ie(t,"keyup","Enter"),(e==="button"||e==="tab")&&(ie(t,"keydown"," "),ie(t,"keyup"," ")))}function ie(t,e,n){t.dispatchEvent(new KeyboardEvent(e,{bubbles:!0,cancelable:!0,key:n}))}function Rc(t){let e=ae(t?.getAttribute?.("role")).toLowerCase();return!!(t?.isContentEditable||!("value"in t)&&["searchbox","textbox"].includes(e))}function ae(t){return String(t||"").trim()}function xc(t){try{let e=`${window.location.pathname}${window.location.search}`.toLowerCase();return e.includes(encodeURIComponent(t).toLowerCase())||e.includes(t.toLowerCase())}catch{return!1}}var Nc=1;function vc(t){let e=g(t).split(/\s+/).filter(n=>n.length>2);return e.length<2?"":e.reduce((n,r)=>r.length>n.length?r:n,"")}async function Pt(t,{broadenIfSparse:e=!1}={}){let n=g(t);if(!G())return null;if(!n)return so("host_search","empty_query");let r=await ho(n);if(!e||!r||r.status!=="succeeded")return r;let o=r.evidence?.result_count;if(typeof o!="number"||o>Nc)return r;let i=vc(n);if(!i||i===n)return r;let a=await ho(i);return a?.status==="succeeded"&&(a.evidence?.result_count||0)>o?{...a,evidence:{...a.evidence,broadened_from:n}}:r}async function ho(t){let e=S(h.searchInput);if(!e){let s=S(h.searchSubmit)||S(h.searchForm);s&&Q(s),e=await B(()=>S(h.searchInput),io)}if(!e)return E("host_search","search_input_unavailable");lo(e,t);let n=e.closest?.("form")||S(h.searchForm);po(n||S(h.searchSubmit)||e);let r=await B(()=>{let s=S(h.searchResults);return!s||s.getAttribute("data-results-loading")==="true"?null:s},z);if(!r)return ao("host_search","results_not_settled");let o=Number(r.getAttribute("data-result-count")),i={result_count:Number.isFinite(o)?o:null,query:r.getAttribute("data-query")||"",route:`${window.location.pathname}${window.location.search}`,route_reflects_query:xc(t)};return i.route_reflects_query||i.query.toLowerCase().includes(t.toLowerCase())?r.getAttribute("data-results-empty")==="true"||i.result_count===0?E("host_search","no_results",i):K("host_search",i):E("host_search","query_not_reflected",i)}var Dt="host_add_to_cart",ht="host_clear_cart",Ut="host_product_detail";function _t(){let t=S(h.cartButton)||x("[data-cart-count]").find(ft)||null;if(!t)return null;let e=Number(t.getAttribute("data-cart-count"));return Number.isFinite(e)?e:null}function Qe(){return st(h.cartLineItem).map(t=>g(t.getAttribute("data-product-id"))).filter(Boolean)}function _o(t){return!!t.disabled||t.getAttribute("aria-disabled")==="true"}async function yo(t,e,n){let r=oe(e,n);if(!r&&n&&G()){let o=await Pt(n);o&&o.status==="succeeded"&&(r=oe(e,n))}return r?r.ambiguous?{error:E(t,"ambiguous_product",{product_name:g(n),match_count:r.matchCount})}:r:{error:E(t,"product_not_on_page",{product_id:g(e),product_name:g(n)})}}function Lc(t,e){let n=g(e);if(n){let r=x(`${mt(h.addToCart)}[data-product-id="${ze(n)}"]`).find(ft);if(r)return r}return t?.querySelector?.(mt(h.addToCart))||null}async function Xe(t){if(!xt()&&!ct())return null;let e=g(t?.product_id||t?.entity_id),n=g(t?.product_name),r=await yo(Dt,e,n);if(r.error)return r.error;let o=g(r.card.getAttribute("data-product-id"))||e,i=Lc(r.card,r.matchedBy===Ke?e:o);if(!i)return E(Dt,"add_control_missing",{product_id:o,product_name:n});if(_o(i))return E(Dt,"add_control_disabled",{product_id:o,product_name:n});let a=_t(),s=Qe();Q(i);let u=await B(()=>{let A=_t(),v=Qe(),C=a!=null&&A!=null&&A>a,b=o&&v.includes(o)&&!s.includes(o),R=v.length>s.length;return C||b||R?{afterCount:A,lines:v}:null},z),f={cart_before:a,cart_after:_t(),product_id:o,product_name:n,matched_by:r.matchedBy};return u?K(Dt,{...f,line_item_present:o?Qe().includes(o):!0}):E(Dt,"cart_unchanged",f)}async function Je(){if(!Nt())return null;let t=S(h.clearCart);if(!t)return E(ht,"clear_control_missing");if(_o(t))return E(ht,"clear_control_disabled");let e=_t();if(e==null)return E(ht,"cart_state_unobservable");if(e===0)return K(ht,{cart_before:0,cart_after:0});Q(t);let n=await B(()=>_t()===0?!0:null,z),r={cart_before:e,cart_after:_t()};return n?K(ht,r):E(ht,"cart_not_empty",r)}function Pc(t){return t?.querySelector?.(mt(h.productLink))||t?.querySelector?.("a[href]")||null}function Dc(t,e){let n=S(h.productDetail),r=at(e);if(n){let i=g(n.getAttribute("data-product-id"));if(t&&i&&i===t)return"product_id";let a=at(re(n));if(r&&a&&a===r)return"product_name"}let o=S(h.productTitle);return o&&r&&at(o.textContent)===r?"product_title":""}async function Ze(t){if(!ct()&&!G())return null;let e=g(t?.product_id||t?.entity_id),n=g(t?.product_name),r=await yo(Ut,e,n);if(r.error)return r.error;let o=g(r.card.getAttribute("data-product-id"))||e,i=Pc(r.card);if(!i)return E(Ut,"product_link_missing",{product_id:o,product_name:n});let a=W(window.location.pathname);Q(i);let s=await B(()=>Dc(o,n)||null,z),u={product_id:o,product_name:n,matched_by:r.matchedBy,route:`${window.location.pathname}${window.location.search}`,verified_by:s||""};return s?K(Ut,u):W(window.location.pathname)===a?E(Ut,"route_unchanged",u):E(Ut,"product_page_not_confirmed",u)}var kt="host_navigate",Uc="main, [data-aihub-role='search-results'], [data-product-id]";function kc(t){let e=Lt(t);if(!e)return null;let n=st(h.navLink),r=s=>[Lt(s.getAttribute(Ve)),Lt(s.textContent),Lt(Ge(s.getAttribute("href")||s.href))].filter(Boolean),o=n.find(s=>r(s).includes(e));if(o)return o;let i=null,a=0;for(let s of n)for(let u of r(s))!e.includes(u)&&!u.includes(e)||u.length>a&&(a=u.length,i=s);return i}function Mc(t){try{return new URL(String(t||""),window.location.origin).searchParams}catch{return new URLSearchParams}}function Fc(t){if(W(window.location.pathname)!==W(t))return!1;let e=new URLSearchParams(window.location.search);for(let[n,r]of Mc(t).entries())if(e.get(n)!==r)return!1;return!0}async function tn(t){if(!vt())return null;let e=kc(t);if(!e)return E(kt,"no_matching_nav_target",{target:g(t)});let n=Ge(e.getAttribute("href")||e.href),r=W(window.location.pathname);Q(e);let o=await B(()=>n&&Fc(n)?!0:null,z),i=W(window.location.pathname),a={target:g(t),expected:W(n),route:`${window.location.pathname}${window.location.search}`};return o?await B(()=>document.querySelector(Uc)?!0:null,z)?K(kt,a):E(kt,"page_not_ready",a):i!==r?E(kt,"wrong_route",{...a,actual:i}):E(kt,"route_unchanged",{...a,actual:i})}var bo=new Set([c.FILTER_PRODUCTS,c.SHOW_PRODUCTS]),To=new Set([c.SHOW_PRODUCT_DETAIL]);function se(t){return t.parameters||t.params||{}}function Ao(t){let e=se(t);return String(e[p.SEARCH_QUERY]||e.search||e.query||e.q||"").trim()}function Eo(t){let e=se(t);return String(e[p.PAGE]||e.page||e.target||"").trim()}function go(t){let e=se(t);return!!(e[p.PRODUCT_ID]||e.entity_id||String(e[p.PRODUCT_NAME]||"").trim())}function So(t){let e=t.action;return e===c.ADD_TO_CART?(xt()||ct())&&go(t):e===c.CLEAR_CART?Nt():To.has(e)?(ct()||G())&&go(t):bo.has(e)?G()&&!!Ao(t):e===c.NAVIGATE_TO?vt()&&!!Eo(t):!1}async function wo(t){let e=t.action,n=se(t);if(e===c.ADD_TO_CART)return Xe(n);if(e===c.CLEAR_CART)return Je();if(To.has(e))return Ze(n);if(bo.has(e)){let r=Ao(t);return r?Pt(r,{broadenIfSparse:!0}):null}if(e===c.NAVIGATE_TO){let r=Eo(t);return r?tn(r):null}return null}var Hc=Object.freeze([{name:"host_contract",canExecute:So,execute:wo},{name:"runtime_adapter",canExecute:Wr,execute:Kr},{name:"product_overlay",canExecute:Vr,execute:zr},{name:"entity_overlay",canExecute:dr,execute:pr},{name:"handoff_overlay",canExecute:br,execute:Tr},{name:"platform_adapter",canExecute:()=>!0,execute:Hn},{name:"provider_adapter",canExecute:Qn,execute:Xn},{name:"navigation",canExecute:Er,execute:Sr},{name:"browser_event",canExecute:()=>!0,execute:Qr}]);async function nn(t){let e=[];for(let n of t||[]){let r=Or(n),o=await Bc(r);o&&e.push(o)}return e}async function Bc(t){if(!t.action)return;let e=Date.now(),n=window.location.href,r=qe();await Yt(d.apiUrl,d.siteId,t,{status:"requested",stage:"widget_dispatch",requested_url:n,final_url:n,evidence:en(t,n,n)}),await Yt(d.apiUrl,d.siteId,t,{status:"executing",stage:"widget_dispatch",requested_url:n,final_url:window.location.href,evidence:en(t,n,window.location.href)});let o;try{o=await Yc(t)}catch(u){o={status:"failed",stage:"widget_dispatch",reason:u instanceof Error?u.message:"execution_error"}}let i=o.status==="succeeded"&&o.self_verified?{family:o.stage||"host_contract",verified:!0,reason:o.reason||""}:o.status==="succeeded"?await ro(t,r):{family:"none",verified:!1,reason:o.reason||"execution_failed"},a=window.location.href,s={...en(t,n,a,o),postcondition_family:i.family,postcondition_verified:i.verified,postcondition_reason:i.reason};return await Yt(d.apiUrl,d.siteId,t,{status:o.status,stage:o.stage,reason:o.reason,duration_ms:Date.now()-e,requested_url:n,final_url:a,evidence:s}),{action:t.action,request_id:t.request_id||t.action_request_id||"",turn_id:t.turn_id||"",sequence:Number(t.sequence||0),status:o.status,stage:o.stage,reason:o.reason,verified:i.verified,postcondition:i.family,requested_url:n,final_url:a,evidence:s}}async function Yc(t){if(!t.action)return{status:"failed",stage:"normalization",reason:"missing_action"};for(let e of Hc){if(!e.canExecute(t))continue;let n=await e.execute(t),r=$c(n,e.name);if(r)return r}return{status:"failed",stage:"all",reason:"no_executor_succeeded"}}function $c(t,e){if(t===!0)return{status:"succeeded",stage:e,reason:""};if(t===Ye)return{status:"blocked",stage:e,reason:"action_blocked"};if(!t||typeof t!="object")return null;let n=String(t.status||"").trim().toLowerCase();return n?{status:n,stage:String(t.stage||e).trim()||e,reason:String(t.reason||"").trim(),self_verified:!!t.self_verified,evidence:t.evidence&&typeof t.evidence=="object"?t.evidence:{}}:null}function en(t,e,n,r={}){let o=t.parameters||t.params||{},i={requested_url:e,final_url:n,url_changed:e!==n,path_changed:Io(e)!==Io(n),title:document.title||"",stage:r.stage||"",result_status:r.status||""};return o.page&&(i.target_page=o.page),o.product_id&&(i.product_id=o.product_id),o.entity_id&&(i.entity_id=o.entity_id),Array.isArray(o.product_ids)&&(i.product_count=o.product_ids.length),Array.isArray(o.entity_ids)&&(i.entity_count=o.entity_ids.length),{...i,...r.evidence&&typeof r.evidence=="object"?r.evidence:{}}}function Io(t){try{return new URL(t,window.location.href).pathname}catch{return""}}var m=Object.freeze({CANCELLED:"cancelled",NETWORK:"network",TIMEOUT:"timeout",ACCESS_DENIED:"access_denied",INVALID_REQUEST:"invalid_request",PAYLOAD_TOO_LARGE:"payload_too_large",UNSUPPORTED_MEDIA:"unsupported_media",RATE_LIMITED:"rate_limited",PROVIDER_UNAVAILABLE:"provider_unavailable",SERVER_ERROR:"server_error",MICROPHONE:"microphone",UNKNOWN:"unknown"}),Oo=Object.freeze({[m.CANCELLED]:"Stopped",[m.NETWORK]:"Connection issue",[m.TIMEOUT]:"Timed out",[m.ACCESS_DENIED]:"Access denied",[m.INVALID_REQUEST]:"Try again",[m.PAYLOAD_TOO_LARGE]:"Recording too long",[m.UNSUPPORTED_MEDIA]:"Audio not supported",[m.RATE_LIMITED]:"Service busy",[m.PROVIDER_UNAVAILABLE]:"Service unavailable",[m.SERVER_ERROR]:"Service error",[m.MICROPHONE]:"Mic unavailable",[m.UNKNOWN]:"Try again"}),Co=64,O=class extends Error{constructor(e,{status:n=0,code:r="",requestId:o="",stage:i=""}={}){super(`voice_transport_${e}`),this.name="VoiceTransportError",this.category=e,this.status=Number(n)||0,this.code=String(r||"").slice(0,Co),this.requestId=String(o||"").slice(0,Co),this.stage=i}get customerMessage(){return jc(this.category)}toDiagnostics(){return{category:this.category,status:this.status,code:this.code,request_id:this.requestId,stage:this.stage}}};function jc(t){return Oo[t]||Oo[m.UNKNOWN]}function Ro(t){return t instanceof O&&t.category===m.CANCELLED}function qc(t){let e=Number(t)||0;return e===401||e===403?m.ACCESS_DENIED:e===408?m.TIMEOUT:e===413?m.PAYLOAD_TOO_LARGE:e===415?m.UNSUPPORTED_MEDIA:e===429?m.RATE_LIMITED:e===502||e===503||e===504?m.PROVIDER_UNAVAILABLE:e>=500?m.SERVER_ERROR:e>=400?m.INVALID_REQUEST:m.UNKNOWN}function Mt(t){if(t instanceof O)return t;let e=String(t?.message||t||"").toLowerCase();return t?.name==="AbortError"||e.includes("abort")||e.includes("timeout")||e.includes("timed out")?new O(m.TIMEOUT):e.includes("microphone")||e.includes("permission")||e.includes("notallowed")?new O(m.MICROPHONE):t?.name==="TypeError"||e.includes("failed to fetch")||e.includes("network")||e.includes("load failed")?new O(m.NETWORK):new O(m.UNKNOWN)}function xo(t,e=null){let n=Number(t?.status)||0,r=t?.headers?.get?.("x-request-id")||t?.headers?.get?.("x-correlation-id")||"",o=e&&typeof e=="object"&&(e.code||e.error_code)||"",i=/^[A-Za-z0-9_.:-]{1,64}$/.test(String(o||""))?String(o):"";return new O(qc(n),{status:n,code:i,requestId:r,stage:"http_response"})}var Vc="/v1/widget/runtime-event",zc=16;function N(t={}){let e=JSON.stringify({client_id:d.siteId,site_id:d.siteId,origin:window.location.origin,occurred_at:new Date().toISOString(),session_id:d.sessionId,turn_id:Y(t.turn_id,80),request_id:Y(t.request_id,80),component:Y(t.component||"voice",60),stage:Y(t.stage,80),event_type:Y(t.event_type||"runtime_event",80),severity:Y(t.severity||"info",20),status:Y(t.status||"ok",20),message_code:Y(t.message_code,80),duration_ms:No(t.duration_ms),metadata:Gc(t.metadata)}),n=new URL(Vc,d.apiUrl).toString();fetch(n,{method:"POST",headers:{Accept:"application/json","Content-Type":"application/json"},body:e,keepalive:!0}).catch(()=>{})}function Gc(t){if(!t||typeof t!="object"||Array.isArray(t))return{};let e={};for(let[n,r]of Object.entries(t).slice(0,zc)){let o=Y(n,60).toLowerCase();!o||Wc(o)||(typeof r=="boolean"||r===null?e[o]=r:typeof r=="number"?e[o]=No(r):typeof r=="string"&&(e[o]=Y(r,120)))}return e}function Wc(t){return["audio","transcript","response","error","exception","token","secret"].some(e=>t.includes(e))}function Y(t,e){return String(t||"").replace(/\s+/g," ").trim().slice(0,e)}function No(t){let e=Number(t||0);return Number.isFinite(e)?Math.max(0,e):0}var Kc=3,Qc="AIHubAdapterRuntime",Xc="AIHubAdapter";function Jc(t,e){let n=new URL(U.SHOP_WS,t);return n.protocol=n.protocol==="https:"?"wss:":"ws:",n.searchParams.set("site_id",e),n.searchParams.set("session_id",d.sessionId),n.toString()}function Zc(t){return new Promise((e,n)=>{let r=new FileReader;r.onloadend=()=>{let o=String(r.result||"");e(o.includes(",")?o.split(",").pop():o)},r.onerror=()=>n(r.error||new Error("Failed to read audio blob")),r.readAsDataURL(t)})}var rn=class{constructor(){this.queue=[],this.blocked=[],this.playing=!1,this.current=null,this.lastPlaybackStartMs=0,this.installUnlockListeners()}push(e,n=""){e&&(this.queue.push({audioB64:e,fallbackText:n}),this.playNext())}playNext(){if(this.playing||this.queue.length===0)return;this.playing=!0;let e=this.queue.shift(),n=new Audio(At.DATA_WAV_PREFIX+e.audioB64);n.preload="auto",this.current=n,n.onplay=()=>{this.lastPlaybackStartMs=typeof performance<"u"?performance.now():0},n.onended=()=>{this.current=null,this.playing=!1,this.playNext()},n.onerror=()=>{this.current=null,e.fallbackText&&et(e.fallbackText),this.playing=!1,this.playNext()},n.play().catch(r=>{if(console.warn("Audio playback failed",r),this.current=null,this.isAutoplayBlocked(r)){e.fallbackText?et(e.fallbackText):this.blocked.unshift(e),this.playing=!1;return}e.fallbackText&&et(e.fallbackText),this.playing=!1,this.playNext()})}installUnlockListeners(){if(typeof window>"u")return;let e=()=>{this.retryBlocked(),Xt()};window.addEventListener("pointerdown",e,{capture:!0,passive:!0}),window.addEventListener("keydown",e,{capture:!0}),window.addEventListener("touchstart",e,{capture:!0,passive:!0})}retryBlocked(){this.blocked.length&&(this.queue.unshift(...this.blocked.splice(0)),this.playNext())}speakInsteadOfBlocked(e){!e||!this.blocked.length||(this.blocked=[],et(e))}isAutoplayBlocked(e){let n=`${e?.name||""} ${e?.message||e||""}`.toLowerCase();return n.includes("notallowed")||n.includes("user didn't interact")||n.includes("not allowed")}stop(){if(this.queue=[],this.blocked=[],this.current){try{this.current.pause(),this.current.currentTime=0}catch{}this.current.onended=null,this.current.onerror=null,this.current=null}this.playing=!1,Jt()}isSpeaking(){return this.playing||this.queue.length>0||Mr()}},ce=new rn;function ue(){ce.stop()}function sn(){return ce.isSpeaking()}function cn(t="reset"){Po.reset(t),Lo.reset(t)}var on=class{constructor(){this.inFlight=null,this.cancelled=!1}reset(e="reset"){this.cancelled=e==="user_cancel";try{this.inFlight?.abort()}catch{}this.inFlight=null}async sendAudio(e,n,r=[]){let o=X();N({event_type:"voice_turn_started",stage:"http_request",status:"started",metadata:{transport:"http",audio_type:e?.type||"unknown"}});let i=new FormData;i.append("audio",e,nu(e)),i.append("site_id",d.siteId),i.append("session_id",d.sessionId),r&&r.length>0&&i.append("conversation_history",JSON.stringify(r));let a=Mo();a&&i.append("page_context",JSON.stringify(a));let s,u=typeof AbortController=="function"?new AbortController:null;this.inFlight=u,this.cancelled=!1;try{s=await fetch(`${d.apiUrl}${U.SHOP}`,{method:xn.POST,body:i,signal:u?.signal})}catch(I){throw this.cancelled||I?.name==="AbortError"?new O(m.CANCELLED,{stage:"user_cancel"}):Mt(I)}if(!s.ok)throw xo(s,await iu(s));let f=await s.json();f.transcript&&n.onUserMessage?.(f.transcript);let A=Array.isArray(f.ui_actions)?f.ui_actions:[],v=[];A.length>0&&(v=await nn(A),n.onActionResults?.(v));let C=f.response_text||"",b=Uo(C,A,v,f.success_text||"");b&&n.onAssistantMessage?.(b,A),n.onStatusChange?.(y.READY);let R=b===C;R&&f.audio_b64?eu(f.audio_b64,f.spoken_text||C):R?et(f.spoken_text||C):b&&et(b),n.onComplete?.(f),N({event_type:"voice_turn_completed",stage:"http_response",status:"ok",request_id:tu(s),duration_ms:X()-o,metadata:{transport:"http",action_count:f.ui_actions?.length||0}})}},an=class{constructor(){this.ws=null,this.connected=!1,this.connecting=null,this.failed=!1,this.retries=0,this.audioQueue=ce,this.callbacks=null,this.turnText="",this.receivedAudio=!1,this.pendingAudioChunks=[]}async ensureConnected(e=[]){return this.canUseWebSocket()?this.isOpen()?!0:this.connecting?this.connecting:(this.connecting=this.openConnection(e),this.connecting):!1}canUseWebSocket(){return!this.failed&&d.useWebSocket&&"WebSocket"in window}isOpen(){return this.connected&&this.ws?.readyState===WebSocket.OPEN}openConnection(e=[]){return new Promise(n=>{let r=new WebSocket(Jc(d.apiUrl,d.siteId)),o=!1;this.ws=r;let i=(s=null)=>{o||(o=!0,this.markConnectionFailed(n,s,r))},a=window.setTimeout(()=>{i()},Dn);r.onopen=()=>{o||(o=!0,this.handleConnectionOpen(a,e,n))},r.onmessage=s=>{this.handleMessage(s).catch(u=>this.handleTransportError(u))},r.onerror=()=>{if(o){this.failActiveTurn(m.NETWORK);return}i(a)},r.onclose=()=>{if(this.connected=!1,o){this.failActiveTurn(m.NETWORK);return}i(a)}})}markConnectionOpen(){this.connected=!0,this.connecting=null,this.retries=0}handleConnectionOpen(e,n,r){window.clearTimeout(e),this.markConnectionOpen(),this.sendConfig(n),r(!0)}markConnectionFailed(e,n=null,r=null){n&&window.clearTimeout(n),this.connected=!1,this.connecting=null,this.retries+=1,this.retries>=Kc&&(this.failed=!0),r&&r.readyState!==WebSocket.CLOSED&&r.close(),e(!1)}sendConfig(e=[]){this.sendJson({type:k.CONFIG,history:e||[],session_id:d.sessionId,page_context:Mo()})}sendJson(e){return!this.ws||this.ws.readyState!==WebSocket.OPEN?!1:(this.ws.send(JSON.stringify(e)),!0)}async sendAudio(e,n,r=[]){if(!await this.ensureConnected(r))return!1;this.callbacks=n,this.turnText="",this.receivedAudio=!1,this.pendingAudioChunks=[],this.sendConfig(r);let i=await Zc(e),a=this.beginTurn();return this.turnStartedAt=X(),N({event_type:"voice_turn_started",stage:"websocket_send",status:"started",metadata:{transport:"websocket",audio_type:e?.type||"unknown"}}),this.sendJson({type:k.AUDIO_CHUNK,data:i,mime_type:e?.type||""})&&this.sendJson({type:k.AUDIO_END,mime_type:e?.type||""})?(await a,!0):(this.settleTurn(),this.callbacks=null,!1)}beginTurn(){return this.settleTurn(),new Promise(e=>{let n=window.setTimeout(()=>{this.failActiveTurn(m.TIMEOUT)},Un);this.activeTurn={resolve:e,timer:n}})}settleTurn(){let e=this.activeTurn;return this.activeTurn=null,e?(window.clearTimeout(e.timer),e.resolve(),!0):!1}failActiveTurn(e){if(!this.activeTurn)return;let n=this.callbacks;if(this.callbacks=null,this.pendingAudioChunks=[],n){let r=new O(e,{stage:"websocket"});n.onStatusChange?.(y.ERROR,r.customerMessage),n.onComplete?.({error:r.category}),N({event_type:"voice_turn_failed",stage:"websocket",severity:"error",status:"failed",message_code:r.code||r.category,duration_ms:X()-(this.turnStartedAt||X()),metadata:{transport:"websocket",category:r.category,http_status:r.status}})}this.settleTurn()}async handleMessage(e){let n=this.callbacks;if(!n)return;let r=this.parseMessage(e.data);if(!r){this.completeWithError(n,"Invalid WebSocket message");return}if(!this.handleIncrementalMessage(r,n)){if(r.type===k.DONE){await this.handleDoneMessage(r,n);return}r.type===k.ERROR&&this.completeWithError(n,r.message||"WebSocket error")}}parseMessage(e){try{let n=JSON.parse(e);return n&&typeof n=="object"?n:null}catch{return null}}handleIncrementalMessage(e,n){return e.type===k.TRANSCRIPT?(n.onUserMessage?.(e.text||""),!0):e.type===k.TEXT_CHUNK?(this.turnText+=e.text||"",!0):e.type===k.AUDIO_CHUNK?(this.receivedAudio=!!e.audio_b64||this.receivedAudio,e.audio_b64&&this.pendingAudioChunks.push(e.audio_b64),!0):!1}async handleDoneMessage(e,n){let r=e.response_text||this.turnText;try{let o=Array.isArray(e.ui_actions)?e.ui_actions:[],i=[];o.length>0&&(i=await nn(o),n.onActionResults?.(i));let a=Uo(r,o,i,e.success_text||"");n.onAssistantMessage?.(a,o,{streamed:!0}),n.onStatusChange?.(y.READY);let s=a===r;if(this.receivedAudio&&s)for(let u of this.pendingAudioChunks)this.audioQueue.push(u);else s?et(e.spoken_text||r):a&&et(a);n.onComplete?.(e),N({event_type:"voice_turn_completed",stage:"websocket_done",status:"ok",duration_ms:X()-(this.turnStartedAt||X()),metadata:{transport:"websocket",action_count:e.ui_actions?.length||0}})}catch(o){this.handleTransportError(o)}finally{this.pendingAudioChunks=[],this.callbacks=null,this.settleTurn()}}completeWithError(e,n){e.onStatusChange?.(y.ERROR,ko(n)),e.onComplete?.({error:n});let r=Mt(n);N({event_type:"voice_turn_failed",stage:"websocket_message",severity:"error",status:"failed",message_code:r.code||r.category,duration_ms:X()-(this.turnStartedAt||X()),metadata:{transport:"websocket",category:r.category,http_status:r.status}}),this.callbacks=null,this.settleTurn()}handleTransportError(e){console.error("AI Hub WebSocket transport failed",e);let n=this.callbacks;n&&this.completeWithError(n,String(e))}reset(e="reset"){this.callbacks=null,this.turnText="",this.receivedAudio=!1,this.pendingAudioChunks=[],this.settleTurn();try{this.ws?.close()}catch{}this.ws=null,this.connected=!1,this.connecting=null,this.failed=!1,this.retries=0}},Lo=new on,Po=new an;async function Do(t,e,n,r=[]){try{if(d.useWebSocket&&await Po.sendAudio(t,n,r))return;await Lo.sendAudio(t,n,r)}catch(o){let i=o instanceof O?o:Mt(o);if(Ro(i)){N({event_type:"voice_turn_cancelled",stage:i.stage||"transport",status:"cancelled",metadata:{transport:d.useWebSocket?"websocket_or_http":"http"}}),n.onStatusChange?.(y.READY),n.onComplete?.({cancelled:!0});return}console.error(o),N({event_type:"voice_turn_failed",stage:i.stage||"transport",severity:"error",status:"failed",request_id:i.requestId,message_code:i.code||i.category,metadata:{transport:d.useWebSocket?"websocket_or_http":"http",category:i.category,http_status:i.status}}),n.onStatusChange?.(y.ERROR,ko(o)),n.onComplete?.({error:String(o)})}}function tu(t){return t?.headers?.get?.("x-request-id")||t?.headers?.get?.("x-correlation-id")||""}function X(){return typeof performance<"u"?performance.now():Date.now()}function eu(t,e=""){ce.push(t,e)}function nu(t){let e=String(t?.type||"").toLowerCase();return e.includes("mp4")?"audio.mp4":e.includes("ogg")?"audio.ogg":e.includes("wav")?"audio.wav":At.WEBM_FILENAME}var ru=/\b(opened|opening|taking you|took you|navigat|sorted|sorting|filtered|filtering|showing|shown|displayed|added to (?:your )?cart|here (?:it |they )?(?:is|are))\b/i,ou=/\b(?:i(?:'ll| will)\s+try\s+to|i'?m\s+(?:going\s+to|about\s+to)|let me)\b/i,vo="I could not complete that on the page. The site may not have responded - please try again, or do it manually.";function Uo(t,e,n,r=""){let o=String(t||"");if(!o||!Array.isArray(e)||e.length===0)return o;let i=String(r||"");if(!(!!i||ru.test(o)||ou.test(o)))return o;let s=Array.isArray(n)?n:[];return s.length!==e.length||!s.every(f=>f?.status==="succeeded"&&f?.verified!==!1)?vo:i||o}async function iu(t){try{return await t.json()}catch{return null}}function ko(t){if(t instanceof O)return t.customerMessage;let e=String(t?.message||t||"").toLowerCase();return e.includes("quota")?"Quota reached":e.includes("transcription")||e.includes("speech")?"Voice unavailable":Mt(t).customerMessage}function et(t){return t?it(String(t).slice(0,700)):!1}function Mo(){let t=window[Qc],e=window[Xc];try{if(typeof t?.getContext=="function")return t.getContext();if(typeof e?.getContext=="function")return e.getContext()}catch(n){console.warn("[AI Hub Widget] Page context collection failed:",n)}return au()}function au(){try{return{title:document.title||"",url:window.location.href,path:window.location.pathname,...ne()}}catch(t){return console.warn("[AI Hub Widget] Local page state collection failed:",t),null}}var su=4,cu=40,uu=24,lu=80,du=120,un=6,pu=40,fu=600,mu=6,hu=12,Fo=/\[PRODUCT_IDS:\s*([^\]]+)\]/g;function Ho(){let t=[];function e(n,r){let o=String(r||"").trim();o&&(t.push({role:n,content:o}),t.length>pu&&t.shift())}return{history:t,historyForRequest(){if(t.length<=un)return t.map(i=>({...i}));let n=t.slice(0,t.length-un),r=t.slice(t.length-un).map(i=>({...i})),o=_u(n);return o?[o,...r]:r},clear(){t.length=0},rememberUserMessage(n){e("user",n)},rememberAssistantMessage(n,r){e("assistant",yu(n,r))},rememberActionResults(n){let r=bu(n);r&&e("assistant",r)}}}function _u(t){let e=[],n=[];for(let o of t){o.role==="user"&&e.length<mu&&e.push(o.content.replace(/\s+/g," ").trim().slice(0,80));let i;for(Fo.lastIndex=0;(i=Fo.exec(o.content))!==null;)ln(n,i[1].split(",").map(a=>a.trim()))}let r=[];return e.length&&r.push(`Earlier the customer asked: ${e.join("; ")}.`),n.length&&r.push(`Products discussed: ${n.slice(0,hu).join(", ")}.`),r.length?{role:"system",content:`[CONVERSATION_SUMMARY] ${r.join(" ")}`.slice(0,fu)}:null}function yu(t,e){let n=gu(e);return n.length?`${t} [PRODUCT_IDS: ${n.join(",")}]`:t}function gu(t){let e=[];for(let n of t||[]){let r=n.params||{};ln(e,r[p.PRODUCT_IDS]),ln(e,[r[p.PRODUCT_ID]])}return e}function ln(t,e){for(let n of Array.isArray(e)?e:[])n&&!t.includes(n)&&t.push(n)}function bu(t){let e=(Array.isArray(t)?t:[]).map(Tu).filter(Boolean).slice(0,su);return e.length?`[BROWSER_ACTION_RESULTS: ${e.join(" | ")}]`:""}function Tu(t){if(!t||typeof t!="object"||!t.action)return"";let e=[le(t.action,cu),`status=${le(t.status,uu)||"unknown"}`],n=Eu(t.final_url);return n&&e.push(`final_path=${le(n,du)}`),t.reason&&e.push(`reason=${le(t.reason,lu)}`),Au(e,t.evidence),e.join(" ")}function Au(t,e={}){e.rendered_product_count!==void 0&&t.push(`rendered_products=${Number(e.rendered_product_count||0)}`),e.rendered_entity_count!==void 0&&t.push(`rendered_records=${Number(e.rendered_entity_count||0)}`)}function le(t,e){return String(t||"").replace(/\s+/g," ").trim().slice(0,e)}function Eu(t){try{let e=new URL(String(t||""),window.location.href);return`${e.pathname}${e.search}${e.hash}`}catch{return""}}var Bo="aihub:session-reset",de="AIHub",Su=Object.freeze(["mayabot:","aihub:"]);function wu(t){let e=[];for(let n=0;n<t.length;n+=1){let r=t.key(n);r&&Su.some(o=>r.startsWith(o))&&e.push(r)}return e}function Yo(t){if(!t)return[];try{let e=wu(t);for(let n of e)t.removeItem(n);return e}catch{return[]}}function Iu(){let t=[];try{t.push(...Yo(window.sessionStorage))}catch{}try{t.push(...Yo(window.localStorage))}catch{}return t}function $o({cancelRecording:t,stopPlayback:e,resetTransport:n,conversationMemory:r,clearOverlays:o,rotateSessionId:i}={}){return function(){let s={stopped_recording:!1,stopped_audio:!1,cleared_keys:[],session_id:""};return s.stopped_recording=yt(t),s.stopped_audio=yt(e),yt(n),yt(()=>r?.clear?.()),yt(o),s.cleared_keys=Iu(),s.session_id=String(yt(i)||""),s}}function yt(t){if(typeof t!="function")return!1;try{let e=t();return e===void 0?!0:e}catch(e){return console.warn("[AI Hub Widget] Session reset step failed:",e),!1}}function jo(t){let e=window[de]||{};e.resetSession=t,window[de]=e;let n=()=>t();return window.addEventListener(Bo,n),()=>{window.removeEventListener(Bo,n),window[de]?.resetSession===t&&delete window[de].resetSession}}var qo=null;function dn(t){qo||(Vo(t),qo=window.setInterval(()=>Vo(t),Pn))}async function Vo({boot:t,shutdownWidget:e}){try{if(await Ou()){t();return}e()}catch{t()}}async function Ou(){let t=new URL(U.WIDGET_STATUS,d.apiUrl);t.searchParams.set("site_id",d.siteId);let e=await fetch(t.toString(),{cache:"no-store",headers:{Accept:"application/json"}});return e.ok?(await e.json()).enabled!==!1:!0}window.__mayabot_identifier="voice-orb";var pn=null,fn=null;function zo(){if(window.__mayabotBooted||document.getElementById("mayabot-widget"))return;window.__mayabotBooted=!0,gn();let t=Cn(),e=null,n=null,r=!1;function o(_=Nn){e&&window.clearTimeout(e),e=window.setTimeout(()=>{t.msgs.innerHTML="",t.chat.classList.remove("visible"),e=null},_)}function i(_,ut=""){r=_===y.RECORDING,hn(Ko(_)),t.status.className="",_===y.RECORDING?(e&&(window.clearTimeout(e),e=null),t.msgs.innerHTML="",t.chat.classList.add("visible"),t.status.innerText="Listening...",t.status.classList.add("listening")):_===y.PROCESSING?(t.chat.classList.add("visible"),t.status.innerText="Analyzing...",t.status.classList.add("processing")):_===y.READY?(t.status.innerText="Ready",t.status.classList.add("ready")):_===y.ERROR&&(t.status.innerText=ut||"Try again",t.status.classList.add("error"))}let a=Ho(),s=null,u="",f=!1,A=0;async function v(_){if(f)return;f=!0;let ut=++A,nt=()=>ut===A;t.btn.disabled=!0,s=null,u="";try{await Do(_,t,{onUserMessage:L=>{nt()&&(Tt(t,L,"user"),a.rememberUserMessage(L))},onAssistantChunk:(L,gt)=>{nt()&&(u=gt,s||(s=Tt(t,"","ai")),he(t,s,u))},onAssistantMessage:(L,gt,Xo={})=>{nt()&&(Xo.streamed&&s?he(t,s,L):Tt(t,L,"ai"),a.rememberAssistantMessage(L,gt),s=null,u="")},onActionResults:L=>{nt()&&a.rememberActionResults(L)},onStatusChange:(L,gt)=>{nt()&&i(L,gt)},onComplete:()=>{nt()&&o()}},a.historyForRequest())}finally{nt()&&(f=!1,t.btn.disabled=!1),s=null,u=""}}function C(){A+=1,cn("user_cancel"),ue(),f=!1,t.btn.disabled=!1,s=null,u="",N({event_type:"voice_turn_cancelled",stage:"orb_gesture",status:"cancelled"}),i(y.READY)}let b=kn(v,i);pn=b;function R(){return f||sn()}function I(){if(R()){C();return}b.toggle()}let mn={idle:{label:"Maya voice assistant. Click, press Enter, or press Space to talk.",title:"Click to talk"},recording:{label:"Maya is listening. Click once to send, or press Escape to cancel.",title:"Click once to send - Escape to cancel"},processing:{label:"Maya is working on your request. Please wait.",title:"Request in progress"},speaking:{label:"Maya is speaking. Click to stop, or press Escape to stop.",title:"Click to stop Maya"}};function Ko(_){return _===y.RECORDING?"recording":_===y.PROCESSING?"processing":sn()?"speaking":"idle"}function hn(_){let ut=mn[_]||mn.idle;t.btn.setAttribute("aria-label",ut.label),t.btn.setAttribute("title",ut.title),t.btn.setAttribute("data-orb-state",_),t.btn.classList.toggle("recording",_==="recording"),t.btn.classList.toggle("speaking",_==="speaking")}hn("idle"),t.btn.addEventListener("click",_=>{_.detail>1||I()});let _n=_=>{if(_.key==="Escape"){if(r){b.cancel(),N({event_type:"voice_recording_cancelled",stage:"keyboard_escape",status:"cancelled"}),i(y.READY);return}R()&&C()}};document.addEventListener("keydown",_n);let yn=_=>{t.btn.contains(_.target)||Xt()};document.addEventListener("pointerdown",yn,{capture:!0});let Qo=jo($o({cancelRecording:()=>b.cancel(),stopPlayback:ue,resetTransport:cn,conversationMemory:a,clearOverlays:()=>{t.msgs.innerHTML="",t.chat.classList.remove("visible"),document.getElementById("mayabot-product-panel")?.remove()},rotateSessionId:()=>d.rotateSessionId()}));fn=()=>{document.removeEventListener("keydown",_n),document.removeEventListener("pointerdown",yn,{capture:!0}),Qo(),e&&window.clearTimeout(e),e=null,n&&window.clearTimeout(n),n=null,fn=null},Cu()&&(Ru(),n=window.setTimeout(()=>{if(a.history.length>0)return;let _=`Welcome to ${d.brandName}. How can I help you today?`;Tt(t,_,"ai"),i(y.READY),o(Ln),it(_)},vn))}function Go(){pn?.cancel(),pn=null,fn?.(),ue(),window.__mayabotBooted=!1,document.getElementById("mayabot-widget")?.remove(),document.getElementById("mayabot-product-panel")?.remove()}function Cu(){if(!d.autoGreet||!xu())return!1;try{return window.sessionStorage.getItem(Wo())!=="1"}catch{return!window.__mayabotAutoGreeted}}function Ru(){window.__mayabotAutoGreeted=!0;try{window.sessionStorage.setItem(Wo(),"1")}catch{}}function Wo(){return`mayabot:auto-greeted:${d.siteId}`}function xu(){let t=window.location.pathname.replace(/\/+$/,"")||"/";return t==="/"||t.endsWith("/index.html")}document.readyState==="loading"?document.addEventListener("DOMContentLoaded",()=>dn({boot:zo,shutdownWidget:Go})):dn({boot:zo,shutdownWidget:Go});})();
