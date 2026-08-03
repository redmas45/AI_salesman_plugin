(()=>{function pe(){let t="#5d5fef",e=document.querySelector('meta[name="theme-color"]');if(e&&e.content)t=e.content;else{let y=document.querySelector('button[class*="primary"], .btn-primary, [data-primary]');if(y){let M=window.getComputedStyle(y).backgroundColor;M&&M!=="rgba(0, 0, 0, 0)"&&M!=="transparent"&&(t=M)}}let n=window.matchMedia&&window.matchMedia("(prefers-color-scheme: dark)").matches,r=n?"rgba(24, 24, 27, 0.75)":"rgba(255, 255, 255, 0.85)",o=n?"rgba(255, 255, 255, 0.1)":"rgba(0, 0, 0, 0.08)",a=n?"#f3f4f6":"#111827",i=n?"rgba(255, 255, 255, 0.1)":"rgba(0, 0, 0, 0.05)",c=n?"rgba(0, 0, 0, 0.25)":"#ffffff",p=document.createElement("style");p.textContent=`
    :root {
      --mayabot-primary: ${t};
      --mayabot-surface: ${r};
      --mayabot-border: ${o};
      --mayabot-text: ${a};
      --mayabot-user-bg: ${i};
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
      /* The orb is double-tapped to talk, so suppress double-tap zoom, the
         synthetic tap delay, text selection, and the grey tap highlight. */
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
  `,document.head.appendChild(p)}var St="site_1",mr="__AI_";var _r="aihub:auto-site-id:",yr=["data-aihub-scope","data-site-scope"],hr=["data-site-id","data-aihub-site-id"];function h(t){return String(t||"").trim()}function q(t){return h(t).replace(/\/+$/,"")}function _e(t,e,n,r=St){return gr(t,e,n)||br()||h(r)||St}function gr(t,e,n){for(let a of hr){let i=h(t?.getAttribute(a));if(i)return i}let r=h(e?.searchParams.get("site"))||h(e?.searchParams.get("site_id"))||h(e?.searchParams.get("shop"));if(r)return r;let o=h(n);return o&&!o.startsWith(mr)?o:""}function br(){let t=Tr(),e=`${_r}${t}`,n=Rr(e);if(n){let c=wr(n);return c!==n&&me(e,c),c}let r=h(window.location.host||window.location.hostname||"site"),o=ye(),a=Or(`${r}${o?`_${o.replace(/\//g,"_")}`:""}`),i=he(`auto_${a}_${xr(t)}`);return me(e,i),i}function Tr(){return`${window.location.origin}${ye()}`}function ye(){return Er()}function Er(){for(let e of yr){let n=h(Ar()?.getAttribute(e));if(n)return fe(n)}let t=document.querySelector("meta[name='aihub-site-scope']")?.getAttribute("content");return fe(t)}function Ar(){return document.currentScript}function fe(t){let e=h(t);if(!e||e==="/")return"";try{let r=new URL(e,window.location.href);if(r.origin===window.location.origin){let[o]=Sr(r.pathname);return o?`/${o}`:""}}catch{}let[n]=e.replace(/^\/+/,"").split("/");return n?`/${n}`:""}function Sr(t=window.location.pathname){return h(t).split("/").map(e=>Ir(e).trim()).filter(Boolean)}function Ir(t){try{return decodeURIComponent(t)}catch{return String(t||"")}}function Or(t){return h(t).toLowerCase().replace(/[^a-z0-9]+/g,"_").replace(/^_+|_+$/g,"")||"site"}function he(t){return h(t).slice(0,80).replace(/_+$/g,"")||St}function wr(t){let e=h(t);return e.startsWith("auto_")?he(e.toLowerCase().replace(/[^a-z0-9]+/g,"_").replace(/^_+|_+$/g,"")):e}function xr(t){let e=2166136261,n=h(t);for(let r=0;r<n.length;r+=1)e^=n.charCodeAt(r),e=Math.imul(e,16777619);return(e>>>0).toString(36)}function Rr(t){try{return h(window.localStorage.getItem(t))}catch{return""}}function me(t,e){try{window.localStorage.setItem(t,e)}catch{}}var N=document.currentScript,ge="__AI_PUBLIC_API_URL__",Cr="__AI_DEFAULT_SITE_ID__",Nr="mayabot:session:",vr="Maya",Lr="AI Salesperson",Pr="female";function F(t){return String(t||"").trim()}function Dr(){let t=F(N?.getAttribute("src"));if(!t)return null;try{return new URL(t,window.location.href)}catch{return null}}function Ur(t){let e=F(N?.getAttribute("data-api-url"));if(e)return q(e);if(!ge.startsWith("__AI_"))return q(ge);if(t?.origin){let n=t.pathname.replace(/\/mayabot(?:-widget)?\.js$/,"");return q(`${t.origin}${n}`)}return q(window.location.origin)}function Mr(t){let e=`${Nr}${t}`;try{let n=window.sessionStorage.getItem(e);if(n)return n;let r=be(t);return window.sessionStorage.setItem(e,r),r}catch{return be(t)}}function be(t){let e=window.crypto?.randomUUID?.()||`${Date.now()}-${Math.random().toString(16).slice(2)}`;return`${t}-${e}`.slice(0,120)}var Ee=Dr(),Te=_e(N,Ee,Cr),l={siteId:Te,get sessionId(){return Mr(Te)},apiUrl:Ur(Ee),useWebSocket:F(N?.getAttribute("data-use-websocket")).toLowerCase()==="true",autoGreet:F(N?.getAttribute("data-auto-greet")).toLowerCase()!=="false",brandName:F(N?.getAttribute("data-brand"))||vr,assistantTitle:F(N?.getAttribute("data-assistant-title"))||Lr,speechVoiceName:F(N?.getAttribute("data-speech-voice")),speechVoicePreference:F(N?.getAttribute("data-speech-voice-preference"))||Pr};function Ae(){let t=document.createElement("div");return t.id="mayabot-widget",t.innerHTML=`
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
  `,document.body.appendChild(t),t.querySelector(".mayabot-kicker").textContent=l.brandName,t.querySelector(".mayabot-title").textContent=l.assistantTitle,{btn:document.getElementById("mayabot-btn"),chat:document.getElementById("mayabot-chat"),msgs:document.getElementById("mayabot-msgs"),status:document.getElementById("mayabot-status")}}function K(t,e,n){t.chat.classList.add("visible");let r=document.createElement("div");return r.className=`mayabot-msg ${n}`,r.innerText=e,t.msgs.appendChild(r),t.msgs.scrollTop=t.msgs.scrollHeight,r}function It(t,e,n){e&&(e.innerText=n,t.msgs.scrollTop=t.msgs.scrollHeight)}var s=Object.freeze({ADD_TO_CART:"ADD_TO_CART",BOOK_APPOINTMENT_REQUEST:"BOOK_APPOINTMENT_REQUEST",BUILD_ITINERARY:"BUILD_ITINERARY",BUILD_LEARNING_PATH:"BUILD_LEARNING_PATH",CAPTURE_LEAD:"CAPTURE_LEAD",CAPTURE_PATIENT_LEAD:"CAPTURE_PATIENT_LEAD",CHECKOUT:"CHECKOUT",CHECKOUT_HANDOFF:"CHECKOUT_HANDOFF",CHECK_APPOINTMENT_AVAILABILITY:"CHECK_APPOINTMENT_AVAILABILITY",CHECK_AVAILABILITY:"CHECK_AVAILABILITY",CHECK_DELIVERY_AVAILABILITY:"CHECK_DELIVERY_AVAILABILITY",CHECK_ELIGIBILITY_SOFT:"CHECK_ELIGIBILITY_SOFT",CHECK_PREREQUISITES:"CHECK_PREREQUISITES",CLEAR_CART:"CLEAR_CART",CLEAR_FILTERS:"CLEAR_FILTERS",CLEAR_HISTORY:"CLEAR_HISTORY",COMPARE_ENTITIES:"COMPARE_ENTITIES",CONTACT_AGENT:"CONTACT_AGENT",FILTER_ENTITIES:"FILTER_ENTITIES",FILTER_PRODUCTS:"FILTER_PRODUCTS",HANDOFF_TO_ADVISOR:"HANDOFF_TO_ADVISOR",HANDOFF_TO_AGENT:"HANDOFF_TO_AGENT",HANDOFF_TO_CLINIC:"HANDOFF_TO_CLINIC",HANDOFF_TO_HUMAN:"HANDOFF_TO_HUMAN",HANDOFF_TO_LAWYER:"HANDOFF_TO_LAWYER",HANDOFF_TO_LICENSED_AGENT:"HANDOFF_TO_LICENSED_AGENT",HANDOFF_TO_RECRUITER:"HANDOFF_TO_RECRUITER",JOIN_WAITLIST:"JOIN_WAITLIST",MATCH_JOBS:"MATCH_JOBS",NAVIGATE_TO:"NAVIGATE_TO",OPEN_CLAIM_FLOW:"OPEN_CLAIM_FLOW",OPEN_CONTACT:"OPEN_CONTACT",OPEN_DISCLOSURE:"OPEN_DISCLOSURE",OPEN_ENTITY_DETAIL:"OPEN_ENTITY_DETAIL",OPEN_LOCATION:"OPEN_LOCATION",OPEN_MAP:"OPEN_MAP",OPEN_POLICY:"OPEN_POLICY",OPEN_PROJECTS:"OPEN_PROJECTS",OPEN_RENEWAL_FLOW:"OPEN_RENEWAL_FLOW",OPEN_SERVICES:"OPEN_SERVICES",OPEN_SYLLABUS:"OPEN_SYLLABUS",OPEN_TELECONSULT:"OPEN_TELECONSULT",REMOVE_FROM_CART:"REMOVE_FROM_CART",REQUEST_APPOINTMENT:"REQUEST_APPOINTMENT",REQUEST_CALLBACK:"REQUEST_CALLBACK",REQUEST_CONSULTATION:"REQUEST_CONSULTATION",REQUEST_COUNSELOR_CALLBACK:"REQUEST_COUNSELOR_CALLBACK",REQUEST_ESTIMATE:"REQUEST_ESTIMATE",REQUEST_SITE_VISIT:"REQUEST_SITE_VISIT",REQUEST_TEST_DRIVE:"REQUEST_TEST_DRIVE",REQUEST_VIEWING:"REQUEST_VIEWING",RUN_AFFORDABILITY_CALCULATOR:"RUN_AFFORDABILITY_CALCULATOR",RUN_CALCULATOR:"RUN_CALCULATOR",RUN_DOM_SEQUENCE:"RUN_DOM_SEQUENCE",SAVE_SEARCH:"SAVE_SEARCH",SCHEDULE_ORDER:"SCHEDULE_ORDER",SEARCH_AVAILABILITY:"SEARCH_AVAILABILITY",SET_LOCATION:"SET_LOCATION",SHOW_COMPARISON:"SHOW_COMPARISON",SHOW_EMERGENCY_NOTICE:"SHOW_EMERGENCY_NOTICE",SHOW_ENTITIES:"SHOW_ENTITIES",SHOW_PRODUCT_DETAIL:"SHOW_PRODUCT_DETAIL",SHOW_PRODUCTS:"SHOW_PRODUCTS",SORT_ENTITIES:"SORT_ENTITIES",SORT_PRODUCTS:"SORT_PRODUCTS",START_APPLICATION:"START_APPLICATION",START_BOOKING:"START_BOOKING",START_ENROLLMENT:"START_ENROLLMENT",START_INTAKE:"START_INTAKE",START_QUOTE:"START_QUOTE",START_TICKET_PURCHASE:"START_TICKET_PURCHASE",UPDATE_CART_QUANTITY:"UPDATE_CART_QUANTITY",UPDATE_PREFERENCES:"UPDATE_PREFERENCES"}),d=Object.freeze({ENTITY_ID:"entity_id",ENTITY_IDS:"entity_ids",MESSAGE:"message",PAGE:"page",PRODUCT_ID:"product_id",PRODUCT_IDS:"product_ids",QUANTITY:"quantity",REASON:"reason",SEARCH_QUERY:"search_query",URL:"url"}),Bi=Object.freeze({BLOCKED:"blocked",EXECUTING:"executing",FAILED:"failed",REQUESTED:"requested",SKIPPED:"skipped",SUCCEEDED:"succeeded",UNKNOWN:"unknown"}),w=Object.freeze({KNOWLEDGE_BY_IDS:"/v1/knowledge/by-ids",PRODUCTS_BY_IDS:"/v1/products/by-ids",SHOP:"/v1/shop",SHOP_WS:"/v1/ws/shop",WIDGET_STATUS:"/v1/widget/status"}),x=Object.freeze({AUDIO_CHUNK:"audio_chunk",AUDIO_END:"audio_end",CONFIG:"config",DONE:"done",ERROR:"error",TEXT_CHUNK:"text_chunk",TRANSCRIPT:"transcript"});var Se=new Set(["cart","/cart"]),v="Recommended products",H="Relevant options",Q=Object.freeze({DATA_WAV_PREFIX:"data:audio/wav;base64,",WEBM_FILENAME:"audio.webm",WEBM_MIME_TYPE:"audio/webm"}),Ie=Object.freeze({POST:"POST"}),_=Object.freeze({ERROR:"error",PROCESSING:"processing",READY:"ready",RECORDING:"recording"}),Oe=12,we=2400,xe=900,Re=4200,Ot=1,V=180,Ce=3e3,X=Object.freeze({MAYABOT_ACTION:"mayabot:action"}),Ne=2500,ve=45e3;var kr=["audio/webm;codecs=opus","audio/webm","audio/ogg;codecs=opus","audio/ogg","audio/mp4"],Fr=250,Hr=128;function Le(t,e){let n=null,r=null,o=[],a=!1,i=!1,c=!1;async function p(){if(!(i||a)){i=!0;try{let b=await navigator.mediaDevices.getUserMedia({audio:!0});r=b,c=!1;let O=Br();n=new MediaRecorder(b,O?{mimeType:O}:void 0),o=[],n.ondataavailable=g=>{g.data.size>0&&o.push(g.data)},n.onstop=async()=>{let g=new Blob(o,{type:n.mimeType||O||Q.WEBM_MIME_TYPE});if(k(),c){c=!1;return}if(g.size<Hr){console.warn("Microphone recording was empty or too short",{size:g.size}),e(_.READY);return}await t(g)},n.onerror=g=>{console.error("Microphone recording failed",g.error||g),a=!1,i=!1,k(),e(_.ERROR,"Recording failed")},n.start(Fr),a=!0,e(_.RECORDING)}catch(b){console.error("Microphone access denied",b),e(_.ERROR,"Mic unavailable")}finally{i=!1}}}function y({discard:b=!1}={}){if(c=b,n&&n.state!=="inactive"){try{n.requestData()}catch{}n.stop(),a=!1,b||e(_.PROCESSING);return}a=!1,k(),b||e(_.PROCESSING)}function M(){i||(a?y():p())}function Y(){y({discard:!0})}function k(){r&&(r.getTracks().forEach(b=>b.stop()),r=null)}return{toggle:M,cancel:Y}}function Br(){return!("MediaRecorder"in window)||typeof MediaRecorder.isTypeSupported!="function"?"":kr.find(t=>MediaRecorder.isTypeSupported(t))||""}var Pe="shopify",De="woocommerce",Yr="custom";function at(t){let e=String(t||"").trim();return/^\d+$/.test(e)?e:""}function it(t,e=1){let n=Number(t?.[d.QUANTITY]);return Number.isFinite(n)&&n>0?Math.floor(n):e}async function j(t,e){return(await fetch(new URL(t,window.location.origin),{method:"POST",headers:{Accept:"application/json","Content-Type":"application/json"},body:JSON.stringify(e),credentials:"same-origin"})).ok}function jr(){return $r()?Pe:Vr()?De:Yr}async function Ue(t){let e=jr();return e===Pe?Wr(t):e===De?zr(t):!1}function $r(){return!!(window.Shopify||document.querySelector('meta[name="shopify-checkout-api-token"]')||document.querySelector('script[src*="cdn.shopify.com"]'))}function Vr(){return!!(document.body?.classList?.contains("woocommerce")||window.wc_add_to_cart_params||document.querySelector('link[href*="woocommerce"], script[src*="woocommerce"]'))}async function Wr(t){let e=t.parameters||{};if(t.action===s.ADD_TO_CART){let n=at(e.variant_id||e.cart_id||e[d.PRODUCT_ID]);return n?j("/cart/add.js",{items:[{id:n,quantity:it(e)}]}):!1}if(t.action===s.REMOVE_FROM_CART){let n=at(e.cart_id||e.variant_id||e[d.PRODUCT_ID]);return n?j("/cart/change.js",{id:n,quantity:0}):!1}if(t.action===s.UPDATE_CART_QUANTITY){let n=at(e.cart_id||e.variant_id||e[d.PRODUCT_ID]);return n?j("/cart/change.js",{id:n,quantity:it(e,0)}):!1}return t.action===s.CLEAR_CART?j("/cart/clear.js",{}):t.action===s.CHECKOUT?st("/checkout"):Me(t)?st("/cart"):!1}async function zr(t){let e=t.parameters||{};if(t.action===s.ADD_TO_CART){let n=at(e.variant_id||e.cart_id||e[d.PRODUCT_ID]);return n?j("/wp-json/wc/store/cart/add-item",{id:Number(n),quantity:it(e)}):!1}if(t.action===s.REMOVE_FROM_CART){let n=String(e.cart_key||e.key||"").trim();return n?j("/wp-json/wc/store/cart/remove-item",{key:n}):!1}if(t.action===s.UPDATE_CART_QUANTITY){let n=String(e.cart_key||e.key||"").trim();return n?j("/wp-json/wc/store/cart/update-item",{key:n,quantity:it(e,0)}):!1}return t.action===s.CHECKOUT?st("/checkout"):Me(t)?st("/cart"):!1}function Me(t){return t.action===s.NAVIGATE_TO&&Se.has(t.parameters?.[d.PAGE])}function st(t){return window.location.href=t,!0}var Gr="/v1/widget/action-event";function A(t){return String(t||"").trim()}function qr(t,e){return new URL(t,e).toString()}function Kr(t){return!t||typeof t!="object"?[]:Object.keys(t).map(e=>A(e)).filter(Boolean).slice(0,20)}function Qr(t){if(!t||typeof t!="object")return{};let e={};for(let[n,r]of Object.entries(t).slice(0,20)){let o=A(n).slice(0,80);o&&(typeof r=="boolean"||r===null?e[o]=r:typeof r=="number"?e[o]=Number.isFinite(r)?r:0:e[o]=A(r).slice(0,240))}return e}async function ct(t,e,n,r){if(!t||!e||!n?.action)return;let o=JSON.stringify({site_id:e,origin:window.location.origin,url:window.location.href,occurred_at:new Date().toISOString(),request_id:A(n.request_id||n.action_request_id),turn_id:A(n.turn_id),sequence:Number(n.sequence||0),action:A(n.action).toUpperCase(),status:A(r?.status)||"unknown",stage:A(r?.stage),reason:A(r?.reason),duration_ms:Number(r?.duration_ms||0),param_keys:Kr(n.parameters||n.params),requested_url:A(r?.requested_url),final_url:A(r?.final_url||window.location.href),evidence:Qr(r?.evidence)}),a=qr(Gr,t);if(!Xr(a,o))try{await fetch(a,{method:"POST",headers:{Accept:"application/json","Content-Type":"application/json"},body:o,keepalive:!0})}catch(i){console.warn("[AIHubAdapter] Action execution report failed.",i)}}function Xr(t,e){if(typeof navigator>"u"||typeof navigator.sendBeacon!="function"||typeof Blob!="function")return!1;try{return navigator.sendBeacon(t,new Blob([e],{type:"application/json"}))}catch{return!1}}function ke(t){if(!t||typeof t!="string")return[];let e=[];for(let n of Jr()){try{e.push(...Array.from(n.querySelectorAll(t)))}catch{return[]}if(e.length>=600)return e.slice(0,600)}return no(e)}function Jr(){let t=[],e=new Set,n=[document];for(;n.length&&t.length<60;){let r=n.shift();!r||e.has(r)||(e.add(r),t.push(r),n.push(...Zr(r)))}return t}function Zr(t){let e=[];for(let n of to(t)){n.shadowRoot&&e.push(n.shadowRoot);let r=eo(n);r&&e.push(r)}return e}function to(t){try{return Array.from(t.querySelectorAll("*"))}catch{return[]}}function eo(t){if(String(t?.tagName||"").toLowerCase()!=="iframe")return null;try{let e=t.contentDocument;return e?.documentElement?e:null}catch{return null}}function no(t){return Array.from(new Set(t))}var Qi=Object.freeze([u("stripe",["stripe","stripe.com","checkout.stripe.com","js.stripe.com"]),u("paypal",["paypal","paypal.com","paypalobjects.com"]),u("razorpay",["razorpay","checkout.razorpay.com"]),u("paytm",["paytm","securegw.paytm.in"]),u("cashfree",["cashfree","cashfree.com"]),u("checkout.com",["checkout.com","cko-session-id"]),u("adyen",["adyen","checkoutshopper"]),u("square",["squareup","squarecdn","square.site"]),u("braintree",["braintree","braintreegateway"]),u("mollie",["mollie","mollie.com"]),u("klarna",["klarna","klarna.com"]),u("afterpay",["afterpay","afterpay.com","clearpay"]),u("payu",["payu","payu.in","payu.com"]),u("paystack",["paystack","paystack.co"]),u("phonepe",["phonepe","phonepe.com"]),u("billdesk",["billdesk","billdesk.com"]),u("authorize.net",["authorize.net","accept.authorize.net"])]),Fe=Object.freeze([u("calendly",["calendly","calendly.com"]),u("acuity",["acuityscheduling","squarespace scheduling"]),u("booksy",["booksy","booksy.com"]),u("zocdoc",["zocdoc","zocdoc.com"]),u("appointlet",["appointlet","appointlet.com"]),u("setmore",["setmore","setmore.com"]),u("cal.com",["cal.com","calcom"]),u("google_calendar",["calendar.google.com","google calendar"]),u("microsoft_bookings",["microsoft bookings","outlook.office365.com/book"]),u("simplybook",["simplybook","simplybook.me"]),u("tidycal",["tidycal","tidycal.com"]),u("savvycal",["savvycal","savvycal.com"]),u("fresha",["fresha","fresha.com"])]),He=Object.freeze([u("google_maps",["google.com/maps","maps.googleapis","maps.google"]),u("mapbox",["mapbox","mapbox.com"]),u("openstreetmap",["openstreetmap","osm.org"]),u("leaflet",["leaflet","leafletjs"]),u("here_maps",["here.com","hereapi","wego.here.com"]),u("bing_maps",["bing.com/maps","virtualearth"]),u("mappls",["mappls","mapmyindia"])]),Be=Object.freeze([u("whatsapp",["wa.me","api.whatsapp.com","web.whatsapp.com"]),u("telegram",["t.me/","telegram.me"]),u("messenger",["m.me/","messenger.com/t"]),u("zendesk",["zendesk.com","zdassets.com/hc"]),u("intercom",["intercom.help","intercom.com"]),u("freshchat",["freshchat.com"])]),Xi=Object.freeze([u("recaptcha",["recaptcha","g-recaptcha","google.com/recaptcha"]),u("hcaptcha",["hcaptcha","h-captcha"]),u("turnstile",["turnstile","challenges.cloudflare.com"]),u("cloudflare_challenge",["cf-chl","cloudflare challenge"])]);function u(t,e){return{name:t,tokens:e}}function wt(t,e,n=10){let r=xt(t);return e.filter(o=>o.tokens.some(a=>r.includes(a))).map(o=>o.name).slice(0,n)}function xt(t){return String(t||"").replace(/\s+/g," ").trim().toLowerCase()}var Ye="a[href], iframe[src]",ro="a[href]",$e=new Set(["http:","https:"]),ut=new Set(["mailto:","tel:"]),oo=Object.freeze([d.URL,"href","link","target_url","provider_url","booking_url","appointment_url","calendar_url","map_url","location_url","contact_url"]),Ve=new Set([s.OPEN_MAP,s.OPEN_LOCATION,s.SET_LOCATION]),We=new Set([s.CHECK_APPOINTMENT_AVAILABILITY,s.REQUEST_APPOINTMENT,s.BOOK_APPOINTMENT_REQUEST,s.REQUEST_CONSULTATION,s.REQUEST_SITE_VISIT,s.START_BOOKING]),ze=new Set([s.OPEN_CONTACT,s.CONTACT_AGENT,s.REQUEST_CALLBACK,s.REQUEST_COUNSELOR_CALLBACK,s.HANDOFF_TO_ADVISOR,s.HANDOFF_TO_AGENT,s.HANDOFF_TO_CLINIC,s.HANDOFF_TO_HUMAN,s.HANDOFF_TO_LAWYER,s.HANDOFF_TO_LICENSED_AGENT,s.HANDOFF_TO_RECRUITER]);function Ge(t){let e=Qe(t);return Ve.has(e)||We.has(e)||ze.has(e)}async function qe(t){let e=Qe(t);return Ve.has(e)?Rt(t,He,Ye,Ct):We.has(e)?Rt(t,Fe,Ye,Ct):ze.has(e)?Rt(t,Be,ro,co):!1}function Rt(t,e,n,r){let o=ao(t?.parameters||t?.params||{},e,r);if(o)return je(o);let a=io(n,e,r);return a?je(a):!1}function ao(t,e,n){for(let r of oo){let o=Ke(t?.[r]);if(o&&n(o,e))return o}return null}function io(t,e,n){for(let r of ke(t)){let o=so(r);if(!(!o||!n(o,e))&&uo(o,r,e))return o}return null}function so(t){return Ke(t?.getAttribute?.("href")||t?.getAttribute?.("src"))}function Ct(t,e){return $e.has(t.protocol)&&wt(t.href,e).length>0}function co(t,e){return ut.has(t.protocol)?!0:Ct(t,e)}function uo(t,e,n){if(ut.has(t.protocol))return!0;let r=[t.href,e?.textContent||"",e?.getAttribute?.("aria-label")||"",e?.getAttribute?.("title")||""].join(" ");return wt(xt(r),n).length>0}function je(t){if(ut.has(t.protocol)||t.origin===window.location.origin)return window.location.href=t.href,!0;let e=window.open(t.href,"_blank","noopener,noreferrer");return e?(e.opener=null,!0):(window.location.href=t.href,!0)}function Ke(t){let e=String(t||"").trim();if(!e||e.startsWith("#"))return null;try{let n=new URL(e,window.location.href);return $e.has(n.protocol)||ut.has(n.protocol)?n:null}catch{return null}}function Qe(t){return String(t?.action||"").trim().toUpperCase()}var lo=Object.freeze(["title","name"]),po=Object.freeze(["summary","description","body"]),fo=Object.freeze(["image_url","imageUrl","image","thumbnail"]),mo=Object.freeze(["url","href","permalink","source_url"]),_o="knowledge_item",yo=30;function R(t){return t==null||typeof t=="object"?"":String(t||"").trim()}function ho(t){let e=new Set;return(Array.isArray(t)?t:[]).map(R).filter(Boolean).filter(n=>e.has(n)||e.size>=yo?!1:(e.add(n),!0))}function lt(t,e){for(let n of e){let r=R(t?.[n]);if(r)return r}return""}function J(t){return t&&typeof t=="object"&&!Array.isArray(t)?t:{}}function go(t){let e=bo([t?.price,t?.amount,t?.premium,t?.premium_min,t?.monthly_premium,t?.annual_premium,t?.min_price,t?.starting_price]),n=R(t?.currency||"INR");return!Number.isFinite(e)||e<=0?"":`${n} ${e.toLocaleString()}`}function bo(t){for(let e of t){let n=Number(String(e??"").replace(/,/g,""));if(Number.isFinite(n)&&n>0)return n}return 0}function To(t){return!t||typeof t!="object"?"":t.in_stock===!0?"Available":t.in_stock===!1?"Unavailable":R(t.status||t.availability||"")}function Eo(t){let e=R(t);if(!e)return"";try{let n=new URL(e,window.location.origin);return/^https?:$/i.test(n.protocol)?n.origin===window.location.origin?`${n.pathname}${n.search}${n.hash}`:n.toString():""}catch{return""}}function Ao(t){if(!t)return null;let e=R(t.id);if(!e)return null;let n=J(t.pricing),r=J(t.availability);return{id:e,externalId:R(t.external_id),entityType:R(t.entity_type||t.category_name)||_o,title:lt(t,lo)||e,subtitle:R(t.subtitle||t.category_name||t.entity_type),summary:lt(t,po),body:R(t.body),url:Eo(lt(t,mo)),imageUrl:lt(t,fo),attributes:J(t.attributes),pricing:n,availability:r,location:J(t.location),contact:J(t.contact),displayPrice:go(n),displayAvailability:To(r)}}async function Nt(t){let e=ho(t);if(!e.length)return[];let n=new URL(w.KNOWLEDGE_BY_IDS,l.apiUrl);n.searchParams.set("site_id",l.siteId),n.searchParams.set("ids",e.join(","));let r=await fetch(n.toString(),{headers:{Accept:"application/json"}});if(!r.ok)throw new Error("Failed to fetch entities from AI Hub API");let o=(await r.json()).map(Ao).filter(Boolean),a=new Map(o.map(i=>[String(i.id),i]));return e.map(i=>a.get(i)).filter(Boolean)}async function Xe(t){let[e]=await Nt([t]);return e?.url||""}function Je(){if(document.getElementById("mayabot-entity-overlay-styles"))return;let t=document.createElement("style");t.id="mayabot-entity-overlay-styles",t.textContent=`
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
  `,document.head.appendChild(t)}var So=2,Ze=Number.POSITIVE_INFINITY,dt=Number.NEGATIVE_INFINITY,tn=12,Lt=[],Pt=H;function L(t){return String(t??"").replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;").replace(/"/g,"&quot;").replace(/'/g,"&#039;")}function on(t){return String(t||"item").replace(/[_-]+/g," ").trim().split(/\s+/).slice(0,So).join(" ")}function Io(){Je();let t=document.getElementById("mayabot-entity-panel");return t||(t=document.createElement("div"),t.id="mayabot-entity-panel",t.setAttribute("aria-live","polite"),t.innerHTML=`
    <div class="mayabot-entity-header">
      <h2 class="mayabot-entity-title">${H}</h2>
      <button class="mayabot-entity-close" type="button" aria-label="Close recommendations">&times;</button>
    </div>
    <div class="mayabot-entity-grid"></div>
  `,t.querySelector(".mayabot-entity-close").addEventListener("click",()=>{t.classList.remove("active")}),document.body.appendChild(t),t)}function Oo(t){return t<=1?"count-1":t===2?"count-2":t===3?"count-3":"count-many"}function wo(t){return t<=1?1:t===2?2:3}function vt(t,e,n=""){let r=(Array.isArray(e)?e:[]).map(c=>String(c?.id??"").trim()).filter(Boolean),o=r.length,a=t.length,i=o>0?"succeeded":"failed";return{status:i,stage:"entity_overlay",reason:n||(i==="succeeded"?"":"no_matching_entities_rendered"),evidence:{requested_entity_count:a,rendered_entity_count:o,missing_entity_count:Math.max(a-o,0),requested_entity_ids:t.slice(0,tn).join(","),rendered_entity_ids:r.slice(0,tn).join(",")}}}function xo(t){return[t.displayPrice,t.displayAvailability,t.location?.city,t.attributes?.category].map(e=>String(e||"").trim()).filter(Boolean).slice(0,3)}function Ro(t){return t.imageUrl?`
      <div class="mayabot-entity-media">
        <img src="${L(t.imageUrl)}" alt="${L(t.title)}">
      </div>
    `:`
    <div class="mayabot-entity-media">
      <div class="mayabot-entity-badge">${L(on(t.entityType))}</div>
    </div>
  `}function Co(t){let e=xo(t);return e.length?`
    <div class="mayabot-entity-facts">
      ${e.map(n=>`<span class="mayabot-entity-fact">${L(n)}</span>`).join("")}
    </div>
  `:""}function No(t){return t.url?`
    <div class="mayabot-entity-actions">
      <button type="button" data-view-entity="${L(t.id)}">Open</button>
    </div>
  `:""}function ft(t,e){let n=Io(),r=n.querySelector(".mayabot-entity-grid"),o=n.querySelector(".mayabot-entity-title"),a=t.length;if(Lt=Array.isArray(t)?[...t]:[],Pt=e||H,n.classList.remove("count-1","count-2","count-3","count-many"),n.classList.add(Oo(a)),n.style.setProperty("--mayabot-entity-card-count",String(wo(a))),o.textContent=Pt,!a){r.innerHTML='<p class="mayabot-entity-empty">No matching records are currently available.</p>',n.classList.add("active"),en();return}r.innerHTML=t.map(i=>`
        <article class="mayabot-entity-card" data-entity-id="${L(i.id)}">
          ${Ro(i)}
          <h3 class="mayabot-entity-name">${L(i.title)}</h3>
          <p class="mayabot-entity-meta">${L(i.subtitle||on(i.entityType))}</p>
          <p class="mayabot-entity-summary">${L(i.summary||i.body||"Details are available on the website.")}</p>
          ${Co(i)}
          ${No(i)}
        </article>
      `).join(""),r.querySelectorAll("[data-view-entity]").forEach(i=>{i.addEventListener("click",async()=>{await Dt(i.getAttribute("data-view-entity"))})}),n.classList.add("active"),en()}function vo(t){if(!t)return!1;try{let e=new URL(t,window.location.origin);return e.origin===window.location.origin?(window.location.href=`${e.pathname}${e.search}${e.hash}`,!0):(window.open(e.toString(),"_blank","noopener,noreferrer"),!0)}catch{return!1}}function en(){window.setTimeout(()=>{let t=document.getElementById("mayabot-chat"),e=document.getElementById("mayabot-msgs");e&&(e.innerHTML=""),t&&t.classList.remove("visible")},V)}async function Dt(t){let e=await Xe(t);return vo(e)}async function an(t,e=H){let n=Ut({[d.ENTITY_IDS]:t});if(!n.length)return ft([],e),vt([],[],"missing_entity_ids");try{let r=await Nt(n);return ft(r,e),vt(n,r)}catch(r){return console.warn("[AI Hub Widget] Entity overlay failed:",r),ft([],e),vt(n,[],"entity_overlay_fetch_failed")}}function Ut(t){let e=t[d.ENTITY_IDS]||t.ids||t.items||[],n=new Set;return(Array.isArray(e)?e:[]).map(r=>String(r??"").trim()).filter(Boolean).filter(r=>n.has(r)?!1:(n.add(r),!0))}function sn(t={}){if(!Lt.length)return!1;let e=String(t.sort_by||t.sortBy||"price_asc").trim().toLowerCase(),n=[...Lt].sort((o,a)=>Lo(o,a,e)),r=Do(Pt,e);return ft(n,r),!0}function Lo(t,e,n){return n==="price_desc"?pt(e,dt)-pt(t,dt):n==="rating"?nn(e,dt)-nn(t,dt):n==="newest"?rn(e)-rn(t):pt(t,Ze)-pt(e,Ze)}function pt(t,e){return cn([t?.pricing?.price,t?.pricing?.amount,t?.pricing?.premium,t?.pricing?.premium_min,t?.pricing?.monthly_premium,t?.pricing?.annual_premium,t?.pricing?.min_price,t?.pricing?.starting_price,t?.attributes?.price,t?.attributes?.amount,t?.attributes?.premium,t?.attributes?.monthly_premium,t?.attributes?.annual_premium,t?.displayPrice],e)}function nn(t,e){return cn([t?.attributes?.rating,t?.attributes?.review_rating,t?.attributes?.stars,t?.availability?.rating],e)}function rn(t){let e=t?.attributes?.updated_at||t?.attributes?.date||t?.availability?.updated_at||"",n=Date.parse(String(e||""));return Number.isFinite(n)?n:0}function cn(t,e){for(let n of t){let r=Po(n);if(Number.isFinite(r))return r}return e}function Po(t){if(typeof t=="number")return t;let e=String(t??"").replace(/,/g,"").match(/-?\d+(?:\.\d+)?/);return e?Number(e[0]):Number.NaN}function Do(t,e){let n={price_asc:"sorted low to high",price_desc:"sorted high to low",rating:"sorted by rating",newest:"newest first"};return`${String(t||H).replace(/\s+-\s+sorted.*$/i,"")} - ${n[e]||n.price_asc}`}function un(t){return t.action===s.SHOW_ENTITIES||t.action===s.COMPARE_ENTITIES||t.action===s.OPEN_ENTITY_DETAIL||t.action===s.SORT_ENTITIES}async function ln(t){return t.action===s.SHOW_ENTITIES||t.action===s.COMPARE_ENTITIES?Uo(t.parameters||{}):t.action===s.OPEN_ENTITY_DETAIL?Dt(t.parameters?.[d.ENTITY_ID]||t.parameters?.id):t.action===s.SORT_ENTITIES?sn(t.parameters||{}):!1}function Uo(t){return an(Ut(t),t[d.SEARCH_QUERY]||t.title||H)}var Z="mayabot-handoff-panel",dn="mayabot-handoff-overlay-styles",Mo=Object.freeze(["contact","support","help"]),ko=Object.freeze(["checkout","cart"]),_n=new Set([s.CHECKOUT_HANDOFF,s.HANDOFF_TO_ADVISOR,s.HANDOFF_TO_AGENT,s.HANDOFF_TO_CLINIC,s.HANDOFF_TO_HUMAN,s.HANDOFF_TO_LAWYER,s.HANDOFF_TO_LICENSED_AGENT,s.HANDOFF_TO_RECRUITER]),pn=Object.freeze({[s.CHECKOUT_HANDOFF]:{title:"Checkout needs your confirmation",body:"This step may include payment or a secure checkout page. I can take you there, then you complete the final step yourself.",primary:"Open checkout"},[s.HANDOFF_TO_ADVISOR]:{title:"Advisor handoff",body:"This request needs a qualified advisor. I can open the contact path so the site team can continue.",primary:"Contact advisor"},[s.HANDOFF_TO_AGENT]:{title:"Agent handoff",body:"This step needs an agent or account-specific help. I can open the contact path for follow-up.",primary:"Contact agent"},[s.HANDOFF_TO_CLINIC]:{title:"Clinic handoff",body:"This request needs clinic confirmation. I can open the appointment or contact path for the next step.",primary:"Contact clinic"},[s.HANDOFF_TO_HUMAN]:{title:"Human handoff",body:"This step needs human confirmation. I can open the most relevant contact path.",primary:"Open contact"},[s.HANDOFF_TO_LAWYER]:{title:"Legal handoff",body:"This request needs a legal professional. I can open the consultation or contact path.",primary:"Contact lawyer"},[s.HANDOFF_TO_LICENSED_AGENT]:{title:"Licensed agent handoff",body:"This request needs a licensed agent. I can open the quote or contact path for follow-up.",primary:"Contact agent"},[s.HANDOFF_TO_RECRUITER]:{title:"Recruiter handoff",body:"This request needs recruiter review. I can open the application or contact path.",primary:"Contact recruiter"}});function W(t){return String(t??"").replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;").replace(/"/g,"&quot;").replace(/'/g,"&#039;")}function $(t){return String(t||"").trim()}function Fo(){if(document.getElementById(dn))return;let t=document.createElement("style");t.id=dn,t.textContent=`
    #${Z} {
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
    #${Z}.active {
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
      #${Z} {
        bottom: 82px;
        width: min(calc(100vw - 20px), 420px);
      }
    }
  `,document.head.appendChild(t)}function Ho(){Fo();let t=document.getElementById(Z);return t||(t=document.createElement("div"),t.id=Z,t.setAttribute("aria-live","polite"),document.body.appendChild(t),t)}function Bo(){return window.AIHubAdapterRuntime?.config?.adapter?.routes||window.AIHubAdapter?.config?.adapter?.routes||{}}function Yo(t,e){let n=fn(e[d.URL]||e.path||e.href||e.handoff_flow?.page_url);if(n)return n;let r=Bo(),o=t===s.CHECKOUT_HANDOFF?ko:Mo;for(let a of o){let i=fn(r[a]);if(i)return i}return""}function fn(t){let e=$(t);if(!e)return"";try{let n=new URL(e,window.location.origin);return n.origin!==window.location.origin?"":`${n.pathname}${n.search}${n.hash}`||"/"}catch{return""}}function jo(t){return pn[t]||pn[s.HANDOFF_TO_HUMAN]}function $o(t){return t&&typeof t=="object"?t:{}}function Vo(t,e){return $(t.title)||e}function Wo(t,e,n){return $(e[d.MESSAGE])||$(t.handling)||n}function zo(t,e){return $(e[d.REASON]||e.reason||e.blocked_reason||t.key)}function Go(t){let e=[["Provider",t.provider_label||t.provider],["Boundary",t.automation_boundary],["Recovery",t.recovery],["Evidence",t.evidence],["Page",t.page_url]].filter(([,n])=>$(n));return e.length?`
    <p class="mayabot-handoff-meta">
      ${e.map(([n,r])=>`<span><strong>${W(n)}:</strong> ${W(r)}</span>`).join("")}
    </p>
  `:""}function mn(t){t.classList.remove("active")}function qo(){window.setTimeout(()=>{let t=document.getElementById("mayabot-chat"),e=document.getElementById("mayabot-msgs");e&&(e.innerHTML=""),t&&t.classList.remove("visible")},V)}function yn(t,e={}){let n=$(t).toUpperCase(),r=jo(n),o=$o(e.handoff_flow),a=Ho(),i=Yo(n,e),c=Vo(o,r.title),p=Wo(o,e,r.body),y=zo(o,e);return a.innerHTML=`
    <div class="mayabot-handoff-body">
      <div class="mayabot-handoff-top">
        <h2 class="mayabot-handoff-title">${W(c)}</h2>
        <button class="mayabot-handoff-close" type="button" aria-label="Close handoff">&times;</button>
      </div>
      <p class="mayabot-handoff-text">${W(p)}</p>
      ${Go(o)}
      ${y?`<p class="mayabot-handoff-reason">${W(y)}</p>`:""}
      <div class="mayabot-handoff-actions">
        <button type="button" class="secondary" data-close-handoff>Close</button>
        ${i?`<button type="button" data-open-handoff>${W(r.primary)}</button>`:""}
      </div>
    </div>
  `,a.querySelector(".mayabot-handoff-close")?.addEventListener("click",()=>mn(a)),a.querySelector("[data-close-handoff]")?.addEventListener("click",()=>mn(a)),a.querySelector("[data-open-handoff]")?.addEventListener("click",()=>{window.location.href=i}),a.classList.add("active"),qo(),!0}function hn(t){return _n.has(t.action)}function gn(t){return yn(t.action,t.parameters||{})}function Tn(t){return t.action===s.NAVIGATE_TO&&!!An(t.parameters?.[d.PAGE])}function En(t){return window.location.href=An(t.parameters?.[d.PAGE]),!0}function An(t){let e=String(t||"").trim();if(!e||Sn(e)||/^https?:\/\//i.test(e))return"";if(e==="home"||e==="/")return"/";let n=Ko(e);if(n)return n;let r=e.replace(/^\/+|\/+$/g,"");return r?`/${r}`:"/"}function Ko(t){let e=window.AIHubAdapterRuntime?.config?.adapter?.routes||window.AIHubAdapter?.config?.adapter?.routes||{},n=Qo(t);for(let r of n){let o=e[r],a=bn(o);if(a)return a}for(let[r,o]of Object.entries(e)){if(!n.includes(Mt(r)))continue;let a=bn(o);if(a)return a}return""}function Qo(t){let e=Mt(t),n=String(t||"").trim().replace(/^\/+|\/+$/g,"").toLowerCase(),r=n.split("?")[0].split("#")[0].split("/").filter(Boolean).pop()||"";return Array.from(new Set([e,n,Mt(r)].filter(Boolean)))}function Mt(t){return String(t||"").trim().toLowerCase().replace(/[^a-z0-9/_\s-]+/g," ").replace(/[_-]+/g," ").replace(/\s+/g," ").trim().replace(/\s+/g,"-")}function bn(t){let e=String(t||"").trim();if(!e||Sn(e))return"";if(/^https?:\/\//i.test(e))try{let n=new URL(e);return n.origin!==window.location.origin?"":`${n.pathname||"/"}${n.search||""}${n.hash||""}`}catch{return""}return e.startsWith("/")?e:`/${e.replace(/^\/+/,"")}`}function Sn(t){return/^(?:javascript:|data:|\/\/)/i.test(String(t||"").trim())}function In(t){let e=t?.params||t?.parameters||{};return{...t||{},action:String(t?.action||"").trim().toUpperCase(),params:e,parameters:e}}var kt="AIHubAdapterRuntime",Ft="AIHubAdapter";function Xo(t){let e=t?.params||t?.parameters||{};return{...t||{},params:e,parameters:e}}function tt(){return!!(window[kt]?.executeAction||window[Ft]?.handleAction)}async function Ht(t){return(await et(t)).succeeded}async function et(t){let e=Xo(t);if(window[kt]?.executeAction){let n=window[kt],r=await n.executeAction(e)===!0,o=n.lastActionResult||{};return{succeeded:r,handled:o.handled===!0||r,status:o.status||(r?"ok":"not_handled"),reason:o.reason||"",blocked:o.status==="blocked",disabled:o.status==="disabled"}}if(window[Ft]?.handleAction){let n=await window[Ft].handleAction(e)===!0;return{succeeded:n,handled:n,status:n?"ok":"not_handled",reason:"",blocked:!1,disabled:!1}}return{succeeded:!1,handled:!1,status:"missing_adapter",reason:"",blocked:!1,disabled:!1}}var Jo=Object.freeze([{path:"/api/products?per_page=96",routePrefix:"/product/"},{path:"/api/products",routePrefix:"/product/"},{path:"/api/products.json",routePrefix:""},{path:"/products.json",routePrefix:"/products/"},{path:"/collections/all/products.json",routePrefix:"/products/"}]),Zo=Object.freeze(["products","data","items","results"]),wn=Object.freeze(["id","product_id","handle","sku"]),xn=Object.freeze(["name","title"]),ta=Object.freeze(["url","href","permalink","product_url"]),ea=Object.freeze(["image_url","imageUrl","image_src","imageSrc","image","images","media","thumbnail","thumbnail_url","featured_image","featuredImage","featured_image_url"]),na=Object.freeze(["brand","vendor"]),ra=Object.freeze(["category","category_name","product_type"]),oa=Object.freeze(["description","summary","body_html"]),aa=Object.freeze(["original_price","compare_at_price","regular_price"]),Rn=Object.freeze(["currency","currency_code"]),ia=Object.freeze(["display_price","price_text","formatted_price"]),sa="Unknown Brand",ca="Products",ua="/",la=/^[a-z0-9][a-z0-9-]*$/i,Bt=null;function S(t){return t==null||typeof t=="object"?"":String(t||"").trim()}function $t(t){return S(t).toLowerCase().replace(/[^a-z0-9]+/g," ").trim()}function Cn(t){let e=new Set(["a","am","an","and","ask","asked","did","for","me","not","on","only","please","show","some","the","to","wanna","want","what","with","you","your"]),n=[],r=new Set;for(let o of da($t(t)).split(" ")){let a=pa(o);a.length<=1||e.has(a)||r.has(a)||(n.push(a),r.add(a))}return n}function da(t){return t.replace(/\b(?:i\s+)?did\s+not\s+ask\s+for\s+(?:a\s+|an\s+)?[a-z0-9]+\b/g," ")}function pa(t){return["phone","phones","mobile","mobiles"].includes(t)?"phone":["book","books"].includes(t)?"books":t}function Vt(t,e){return e.map(n=>S(t?.[n])).filter(Boolean)}function C(t,e){return Vt(t,e)[0]||""}function mt(t){let e=S(t).replace(/,/g,"");if(!e)return 0;let n=e.match(/-?\d+(?:\.\d+)?/),r=Number(n?n[0]:e);return Number.isFinite(r)?r:0}function fa(t,e){let n=C(t,ia);if(n)return n;let r=C(t,Rn).toUpperCase();return e>0&&r?`${r} ${e.toLocaleString()}`:e>0?e.toLocaleString():""}function ma(t){for(let e of ea){let n=Yt(t?.[e]);if(n)return n}return""}function Yt(t){if(!t)return"";if(Array.isArray(t)){for(let e of t){let n=Yt(e);if(n)return n}return""}if(typeof t=="object"){for(let e of["src","url","image_url","imageUrl","image_src","imageSrc","thumbnail","thumbnail_url","featured_image","featuredImage","featured_image_url"]){let n=Yt(t[e]);if(n)return n}return""}return _a(t)}function _a(t){let e=S(t);if(!e||/^javascript:/i.test(e))return"";if(/^data:image\//i.test(e))return e;try{let n=new URL(e,window.location.origin);return["http:","https:"].includes(n.protocol)?n.toString():""}catch{return""}}function ya(t){let e=S(t);if(!e)return"";try{let n=new URL(e,window.location.origin);return n.origin!==window.location.origin?"":`${n.pathname}${n.search}${n.hash}`}catch{return""}}function ha(t,e,n){let r=ya(C(t,ta));return r||(!la.test(e)||!/[a-z]/i.test(e)||!n?.routePrefix?"":`${n.routePrefix}${encodeURIComponent(e)}${ua}`)}function Wt(t,e={}){if(!t)return null;let n=C(t,wn),r=S(t.handle||t.slug||t.product_handle),o=C(t,xn),a=mt(t.price||t.amount||t.cost),i=mt(C(t,aa));return!n&&!r?null:{id:n,handle:r,name:o,title:S(t.title||o),brand:C(t,na)||sa,category:C(t,ra)||ca,description:C(t,oa),price:Number.isFinite(a)?a:0,originalPrice:Number.isFinite(i)?i:0,displayPrice:fa(t,a),currency:C(t,Rn),rating:mt(t.rating||t.review_rating),reviewCount:mt(t.review_count||t.reviews_count||t.reviews),imageUrl:ma(t),url:ha(t,r||n,e)}}function ga(t){return Vt(t,wn)}function On(t){return Vt(t,xn).map($t)}function Nn(t,e){let n=S(e);return!!(n&&ga(t).includes(n))}function vn(t,e){let n=Cn(e);if(!n.length)return!1;let r=$t([t?.name,t?.title,t?.brand,t?.category,t?.category_name,t?.product_type,t?.description,t?.tags].join(" "));return n.every(o=>r.includes(o)||r.includes(o.replace(/s$/,"")))}function ba(t,e){let n=new Set(On(e));return On(t).some(r=>n.has(r))}function Ta(t,e){return!!(t?.imageUrl&&t.imageUrl===e?.imageUrl)}function Ea(t){if(Array.isArray(t))return t;for(let e of Zo){let n=t?.[e];if(Array.isArray(n))return n}return[]}async function Aa(t){try{let e=await fetch(new URL(t.path,window.location.origin),{headers:{Accept:"application/json"}});if(!e.ok)return[];let n=await e.json();return Ea(n).map(r=>Wt(r,t)).filter(Boolean)}catch(e){return console.warn(`[AI Hub Widget] Catalog endpoint lookup failed for ${t.path}:`,e),[]}}async function jt(){return Bt||(Bt=Promise.all(Jo.map(Aa)).then(t=>t.flat())),Bt}async function Sa(t,e=120){if(!Cn(t).length)return[];let r=new URL("/v1/products",l.apiUrl);r.searchParams.set("site_id",l.siteId),r.searchParams.set("limit",String(e));try{let o=await fetch(r.toString(),{headers:{Accept:"application/json"}});return o.ok?(await o.json()).map(a=>Wt(a)).filter(Boolean).filter(a=>vn(a,t)).slice(0,12):[]}catch(o){return console.warn("[AI Hub Widget] Hub product search fallback failed:",o),[]}}async function Ln(t,e=""){let n=(Array.isArray(t)?t:[]).map(S).filter(Boolean),r=[],o="",a="";if(n.length)try{r=await Pn(n),o="hub_by_ids"}catch(i){a="hub_product_lookup_failed",console.warn("[AI Hub Widget] Hub product ID lookup failed:",i)}if(!r.length&&n.length){let i=await jt();r=n.map(c=>i.find(p=>Nn(p,c))).filter(Boolean),r.length&&(o="host_by_ids")}return!r.length&&e&&(r=await Sa(e),r.length&&(o="hub_search")),!r.length&&e&&(r=(await jt()).filter(c=>vn(c,e)).slice(0,12),r.length&&(o="host_search")),{products:r,source:o,reason:r.length?"":a||"no_matching_products_rendered"}}async function Pn(t){let e=(Array.isArray(t)?t:[]).map(S).filter(Boolean);if(!e.length)return[];let n=new URL(w.PRODUCTS_BY_IDS,l.apiUrl);n.searchParams.set("site_id",l.siteId),n.searchParams.set("ids",e.join(","));let r=await fetch(n.toString(),{headers:{Accept:"application/json"}});if(!r.ok)throw new Error("Failed to fetch products from AI Hub API");let o=(await r.json()).map(i=>Wt(i)).filter(Boolean),a=new Map(o.map(i=>[String(i.id),i]));return e.map(i=>a.get(i)).filter(Boolean)}async function _t(t){let e=S(t);if(!e)return"";let[n]=await Pn([e]);if(n?.url)return n.url;let r=await jt(),o=r.find(i=>Nn(i,e));return o?.url?o.url:n&&r.find(i=>ba(i,n)||Ta(i,n))?.url||""}var Ia=["data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='320' height='240' viewBox='0 0 320 240'%3E","%3Crect width='320' height='240' fill='%23f1f2ee'/%3E","%3Cpath d='M98 156h124l-31-40-25 30-17-22-51 32Z' fill='%23c8c3ba'/%3E","%3Ccircle cx='117' cy='95' r='17' fill='%23d8d3ca'/%3E","%3Ctext x='160' y='198' text-anchor='middle' fill='%23686660' font-family='Arial,sans-serif' font-size='16'%3EImage pending%3C/text%3E","%3C/svg%3E"].join(""),Dn=12,Gt=[],qt=v,kn=new Map;function B(t){return String(t??"").replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;").replace(/"/g,"&quot;").replace(/'/g,"&#039;")}function Oa(){if(document.getElementById("mayabot-product-overlay-styles"))return;let t=document.createElement("style");t.id="mayabot-product-overlay-styles",t.textContent=`
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
  `,document.head.appendChild(t)}function wa(){Oa();let t=document.getElementById("mayabot-product-panel");return t||(t=document.createElement("div"),t.id="mayabot-product-panel",t.setAttribute("aria-live","polite"),t.innerHTML=`
    <div class="mayabot-product-header">
      <h2 class="mayabot-product-title">${v}</h2>
      <button class="mayabot-product-close" type="button" aria-label="Close recommendations">&times;</button>
    </div>
    <div class="mayabot-product-grid"></div>
  `,t.querySelector(".mayabot-product-close").addEventListener("click",()=>{t.classList.remove("active")}),document.body.appendChild(t),t)}async function xa(t){let e={action:s.ADD_TO_CART,params:{[d.PRODUCT_ID]:t,[d.QUANTITY]:Ot},parameters:{[d.PRODUCT_ID]:t,[d.QUANTITY]:Ot}};tt()&&await Ht(e)||window.dispatchEvent(new CustomEvent(X.MAYABOT_ACTION,{detail:e}))}async function Ra(t){try{let n=await _t(t);if(n){window.location.href=n;return}}catch(n){console.warn("[AI Hub Widget] Product detail URL lookup failed:",n)}let e={action:s.SHOW_PRODUCT_DETAIL,params:{[d.PRODUCT_ID]:t},parameters:{[d.PRODUCT_ID]:t}};tt()&&await Ht(e)||window.dispatchEvent(new CustomEvent(X.MAYABOT_ACTION,{detail:e}))}function Ca(t){return t<=1?"count-1":t===2?"count-2":t===3?"count-3":"count-many"}function Na(t){return t<=1?1:t===2?2:3}function va(t){let e=new Set;return(Array.isArray(t)?t:[]).map(n=>String(n??"").trim()).filter(Boolean).filter(n=>e.has(n)?!1:(e.add(n),!0))}function zt(t,e,n="",r={}){let o=(Array.isArray(e)?e:[]).map(p=>String(p?.id??"").trim()).filter(Boolean),a=o.length,i=t.length,c=a>0?"succeeded":"failed";return{status:c,stage:"product_overlay",reason:n||(c==="succeeded"?"":"no_matching_products_rendered"),evidence:{requested_product_count:i,rendered_product_count:a,missing_product_count:Math.max(i-a,0),requested_product_ids:t.slice(0,Dn).join(","),rendered_product_ids:o.slice(0,Dn).join(","),lookup_source:r.source||"",search_query:r.searchQuery||""}}}function La(t){let e=String(t?.displayPrice||"").trim();if(e)return e;let n=Number(t?.price||0);return Number.isFinite(n)&&n>0?n.toLocaleString():"Price unavailable"}var Pa=6,Da=24,Ua=120;function Ma(t){let e=new Map;return Array.isArray(t)&&t.forEach(n=>{if(!n||typeof n!="object")return;let r=String(n.product_id||"").trim();if(!r||!Array.isArray(n.facts))return;let o=n.facts.filter(a=>a&&typeof a=="object"&&a.label&&a.value).slice(0,Pa).map(a=>({label:String(a.label).slice(0,Da),value:String(a.value).slice(0,Ua)}));o.length&&e.set(r,o)}),e}function ka(t){let e=kn.get(String(t));return!e||!e.length?"":`<dl class="mayabot-product-facts">${e.map(r=>`<div class="mayabot-fact"><dt>${B(r.label)}</dt><dd>${B(r.value)}</dd></div>`).join("")}</dl>`}function yt(t,e){let n=wa(),r=n.querySelector(".mayabot-product-grid"),o=n.querySelector(".mayabot-product-title"),a=t.length;if(Gt=Array.isArray(t)?[...t]:[],qt=e||v,n.classList.remove("count-1","count-2","count-3","count-many"),n.classList.add(Ca(a)),n.style.setProperty("--mayabot-card-count",String(Na(a))),o.textContent=qt,!a){r.innerHTML='<p class="mayabot-product-empty">No matching products are currently available.</p>',n.classList.add("active"),Un();return}r.innerHTML=t.map(i=>{let c=B(i.id);return`
        <article class="mayabot-product-card" data-product-id="${c}">
          <img class="mayabot-product-image" src="${B(i.imageUrl||Ia)}" alt="${B(i.name)}">
          <h3 class="mayabot-product-name">${B(i.name||i.title||"Product")}</h3>
          <p class="mayabot-product-meta">${B(i.brand)} - ${B(La(i))}</p>
          ${ka(i.id)}
          <div class="mayabot-product-actions">
            <button type="button" data-add="${c}">Add</button>
            <button type="button" class="secondary" data-view="${c}">View</button>
          </div>
        </article>
      `}).join(""),r.querySelectorAll("[data-add]").forEach(i=>{i.addEventListener("click",async()=>{await xa(i.getAttribute("data-add"))})}),r.querySelectorAll("[data-view]").forEach(i=>{i.addEventListener("click",async()=>{await Ra(i.getAttribute("data-view"))})}),n.classList.add("active"),Un()}function Un(){window.setTimeout(()=>{let t=document.getElementById("mayabot-chat"),e=document.getElementById("mayabot-msgs");e&&(e.innerHTML=""),t&&t.classList.remove("visible")},V)}async function Fn(t,e=v,n={}){let r=va(t),o=String(n.searchQuery||"").trim();if(kn=Ma(n.comparisonFacts),!r.length&&!o)return yt([],e),zt([],[],"missing_product_ids");try{let{products:a,source:i,reason:c}=await Ln(r,o);return yt(a,e),zt(r,a,c,{source:i,searchQuery:o})}catch(a){return console.warn("[AI Hub Widget] Product overlay failed:",a),yt([],e),zt(r,[],"product_overlay_fetch_failed",{searchQuery:o})}}function Hn(t={}){if(!Gt.length)return!1;let e=String(t.sort_by||t.sortBy||"price_asc").trim().toLowerCase(),n=[...Gt].sort((r,o)=>Fa(r,o,e));return yt(n,Ha(qt,e)),!0}function Fa(t,e,n){return n==="price_desc"?z(e.price,Number.NEGATIVE_INFINITY)-z(t.price,Number.NEGATIVE_INFINITY):n==="rating"?z(e.rating||e.review_rating,Number.NEGATIVE_INFINITY)-z(t.rating||t.review_rating,Number.NEGATIVE_INFINITY):n==="newest"?Mn(e)-Mn(t):z(t.price,Number.POSITIVE_INFINITY)-z(e.price,Number.POSITIVE_INFINITY)}function z(t,e){let n=String(t??"").replace(/,/g,"").match(/-?\d+(?:\.\d+)?/);if(!n)return e;let r=Number(n[0]);return Number.isFinite(r)?r:e}function Mn(t){let e=t?.updated_at||t?.created_at||t?.date||"",n=Date.parse(String(e||""));return Number.isFinite(n)?n:0}function Ha(t,e){let n={price_asc:"sorted low to high",price_desc:"sorted high to low",rating:"sorted by rating",newest:"newest first"};return`${String(t||v).replace(/\s+-\s+sorted.*$/i,"")} - ${n[e]||n.price_asc}`}function Yn(t){return t.action===s.SHOW_PRODUCTS||t.action===s.SHOW_COMPARISON||t.action===s.SHOW_PRODUCT_DETAIL||t.action===s.SORT_PRODUCTS}async function jn(t){return t.action===s.SHOW_COMPARISON?Bn(t.parameters||{},"Product comparison",{syncListing:!1,comparisonFacts:(t.parameters||{}).comparison}):t.action===s.SHOW_PRODUCTS?Bn(t.parameters||{},v):t.action===s.SHOW_PRODUCT_DETAIL?ja(t.parameters||{}):t.action===s.SORT_PRODUCTS?Hn(t.parameters||{}):!1}async function Bn(t,e=v,n={}){let r=Array.isArray(t[d.PRODUCT_IDS])?t[d.PRODUCT_IDS]:[],o=Ya(t),i=n.syncListing!==!1?await Ba(o):{succeeded:!1,handled:!1,status:"skipped",stage:"product_display_sync",reason:"comparison_overlay"},c=await Fn(r,t.title||o||e,{searchQuery:o,comparisonFacts:n.comparisonFacts}),p={...c.evidence||{},listing_sync_status:i.status||"",listing_sync_stage:i.stage||"",listing_sync_reason:i.reason||""};return c.status!=="succeeded"?{...c,evidence:p}:o&&i.handled&&!i.succeeded?{status:"failed",stage:"product_display_sync",reason:i.reason||i.status||"listing_sync_failed",evidence:p}:{...c,stage:i.succeeded?"product_display_sync":c.stage,evidence:p}}async function Ba(t){let e=$n(t);return e?et({action:s.FILTER_PRODUCTS,params:{[d.SEARCH_QUERY]:e,query:e,q:e}}):{succeeded:!1,handled:!1,status:"skipped",stage:"product_display_sync",reason:"missing_search_query"}}function Ya(t){return $n(t[d.SEARCH_QUERY]||t.search||t.query||t.q||"")}function $n(t){return String(t||"").trim()}async function ja(t){let e="";try{e=await _t(t[d.PRODUCT_ID])}catch(n){return console.warn("[AI Hub Widget] Product detail URL lookup failed:",n),!1}return e?(window.location.href=e,!0):!1}var Kt="stop_action_fallback",$a=new Set([s.SHOW_PRODUCTS,s.SHOW_COMPARISON,s.SHOW_PRODUCT_DETAIL,s.SORT_PRODUCTS]);function Vn(t){return tt()&&!$a.has(t.action)}async function Wn(t){let e=await et(t);return e.succeeded?!0:e.blocked||e.disabled?Kt:!1}function zn(t){return window.dispatchEvent(new CustomEvent(X.MAYABOT_ACTION,{detail:t})),!0}var Va=Object.freeze([{name:"runtime_adapter",canExecute:Vn,execute:Wn},{name:"product_overlay",canExecute:Yn,execute:jn},{name:"entity_overlay",canExecute:un,execute:ln},{name:"handoff_overlay",canExecute:hn,execute:gn},{name:"platform_adapter",canExecute:()=>!0,execute:Ue},{name:"provider_adapter",canExecute:Ge,execute:qe},{name:"navigation",canExecute:Tn,execute:En},{name:"browser_event",canExecute:()=>!0,execute:zn}]);async function Xt(t){let e=[];for(let n of t||[]){let r=In(n),o=await Wa(r);o&&e.push(o)}return e}async function Wa(t){if(!t.action)return;let e=Date.now(),n=window.location.href;await ct(l.apiUrl,l.siteId,t,{status:"requested",stage:"widget_dispatch",requested_url:n,final_url:n,evidence:Qt(t,n,n)}),await ct(l.apiUrl,l.siteId,t,{status:"executing",stage:"widget_dispatch",requested_url:n,final_url:window.location.href,evidence:Qt(t,n,window.location.href)});let r;try{r=await za(t)}catch(i){r={status:"failed",stage:"widget_dispatch",reason:i instanceof Error?i.message:"execution_error"}}let o=window.location.href,a=Qt(t,n,o,r);return await ct(l.apiUrl,l.siteId,t,{status:r.status,stage:r.stage,reason:r.reason,duration_ms:Date.now()-e,requested_url:n,final_url:o,evidence:a}),{action:t.action,request_id:t.request_id||t.action_request_id||"",turn_id:t.turn_id||"",sequence:Number(t.sequence||0),status:r.status,stage:r.stage,reason:r.reason,requested_url:n,final_url:o,evidence:a}}async function za(t){if(!t.action)return{status:"failed",stage:"normalization",reason:"missing_action"};for(let e of Va){if(!e.canExecute(t))continue;let n=await e.execute(t),r=Ga(n,e.name);if(r)return r}return{status:"failed",stage:"all",reason:"no_executor_succeeded"}}function Ga(t,e){if(t===!0)return{status:"succeeded",stage:e,reason:""};if(t===Kt)return{status:"blocked",stage:e,reason:"action_blocked"};if(!t||typeof t!="object")return null;let n=String(t.status||"").trim().toLowerCase();return n?{status:n,stage:String(t.stage||e).trim()||e,reason:String(t.reason||"").trim(),evidence:t.evidence&&typeof t.evidence=="object"?t.evidence:{}}:null}function Qt(t,e,n,r={}){let o=t.parameters||t.params||{},a={requested_url:e,final_url:n,url_changed:e!==n,path_changed:Gn(e)!==Gn(n),title:document.title||"",stage:r.stage||"",result_status:r.status||""};return o.page&&(a.target_page=o.page),o.product_id&&(a.product_id=o.product_id),o.entity_id&&(a.entity_id=o.entity_id),Array.isArray(o.product_ids)&&(a.product_count=o.product_ids.length),Array.isArray(o.entity_ids)&&(a.entity_count=o.entity_ids.length),{...a,...r.evidence&&typeof r.evidence=="object"?r.evidence:{}}}function Gn(t){try{return new URL(t,window.location.href).pathname}catch{return""}}var qa=1,Ka=1.08,Qa=300,Xa=Object.freeze(["hannah","sonia","libby","ava","susan","hazel","heera","salli","joanna","amy","emma","olivia","natasha","zira","aria","jenny","samantha","victoria","tessa","moira","karen","female","woman","nova","shimmer","google us english","microsoft aria"]),P="",ht="",nt=null,Jt=0;function rt(t){if(!("speechSynthesis"in window)||!("SpeechSynthesisUtterance"in window))return!1;gt();let e=++Jt;P=t;let n=()=>{if(e!==Jt||P!==t)return!1;try{let r=new SpeechSynthesisUtterance(t),o=Ja(window.speechSynthesis.getVoices());return o?(o&&(r.voice=o),r.rate=qa,r.pitch=Ka,r.onstart=qn,r.onend=qn,gt(),window.speechSynthesis.cancel(),window.speechSynthesis.resume(),window.speechSynthesis.speak(r),!0):(P="",!1)}catch{return!1}};return window.speechSynthesis.getVoices().length>0?n():(window.speechSynthesis.onvoiceschanged=n,nt=window.setTimeout(()=>{nt=null,n()},Qa),!0)}function bt(){P&&rt(P)}function Kn(){try{return!!P||!!window.speechSynthesis?.speaking||!!window.speechSynthesis?.pending}catch{return!!P}}function Qn(){Jt+=1,gt(),P="",ht="";try{window.speechSynthesis?.cancel()}catch{}}function Ja(t){if(!Array.isArray(t)||t.length===0)return null;let e=Za(t)||ti(t);return e&&(ht=e.name),e}function Za(t){if(ht){let n=t.find(r=>r.name===ht);if(n)return n}let e=String(l.speechVoiceName||"").toLowerCase();return e&&t.find(n=>n.name.toLowerCase()===e)||null}function ti(t){return l.speechVoicePreference.toLowerCase()!=="female"?t.find(e=>e.default)||t[0]:t.find(e=>Xa.some(n=>e.name.toLowerCase().includes(n)))||null}function qn(){gt(),P=""}function gt(){nt&&window.clearTimeout(nt),nt=null,window.speechSynthesis&&(window.speechSynthesis.onvoiceschanged=null)}var f=Object.freeze({NETWORK:"network",TIMEOUT:"timeout",ACCESS_DENIED:"access_denied",INVALID_REQUEST:"invalid_request",PAYLOAD_TOO_LARGE:"payload_too_large",UNSUPPORTED_MEDIA:"unsupported_media",RATE_LIMITED:"rate_limited",PROVIDER_UNAVAILABLE:"provider_unavailable",SERVER_ERROR:"server_error",MICROPHONE:"microphone",UNKNOWN:"unknown"}),Xn=Object.freeze({[f.NETWORK]:"Connection issue",[f.TIMEOUT]:"Timed out",[f.ACCESS_DENIED]:"Access denied",[f.INVALID_REQUEST]:"Try again",[f.PAYLOAD_TOO_LARGE]:"Recording too long",[f.UNSUPPORTED_MEDIA]:"Audio not supported",[f.RATE_LIMITED]:"Service busy",[f.PROVIDER_UNAVAILABLE]:"Service unavailable",[f.SERVER_ERROR]:"Service error",[f.MICROPHONE]:"Mic unavailable",[f.UNKNOWN]:"Try again"}),Jn=64,E=class extends Error{constructor(e,{status:n=0,code:r="",requestId:o="",stage:a=""}={}){super(`voice_transport_${e}`),this.name="VoiceTransportError",this.category=e,this.status=Number(n)||0,this.code=String(r||"").slice(0,Jn),this.requestId=String(o||"").slice(0,Jn),this.stage=a}get customerMessage(){return ei(this.category)}toDiagnostics(){return{category:this.category,status:this.status,code:this.code,request_id:this.requestId,stage:this.stage}}};function ei(t){return Xn[t]||Xn[f.UNKNOWN]}function ni(t){let e=Number(t)||0;return e===401||e===403?f.ACCESS_DENIED:e===408?f.TIMEOUT:e===413?f.PAYLOAD_TOO_LARGE:e===415?f.UNSUPPORTED_MEDIA:e===429?f.RATE_LIMITED:e===502||e===503||e===504?f.PROVIDER_UNAVAILABLE:e>=500?f.SERVER_ERROR:e>=400?f.INVALID_REQUEST:f.UNKNOWN}function ot(t){if(t instanceof E)return t;let e=String(t?.message||t||"").toLowerCase();return t?.name==="AbortError"||e.includes("abort")||e.includes("timeout")||e.includes("timed out")?new E(f.TIMEOUT):e.includes("microphone")||e.includes("permission")||e.includes("notallowed")?new E(f.MICROPHONE):t?.name==="TypeError"||e.includes("failed to fetch")||e.includes("network")||e.includes("load failed")?new E(f.NETWORK):new E(f.UNKNOWN)}function Zn(t,e=null){let n=Number(t?.status)||0,r=t?.headers?.get?.("x-request-id")||t?.headers?.get?.("x-correlation-id")||"",o=e&&typeof e=="object"&&(e.code||e.error_code)||"",a=/^[A-Za-z0-9_.:-]{1,64}$/.test(String(o||""))?String(o):"";return new E(ni(n),{status:n,code:a,requestId:r,stage:"http_response"})}var ri="/v1/widget/runtime-event",oi=16;function I(t={}){let e=JSON.stringify({site_id:l.siteId,origin:window.location.origin,occurred_at:new Date().toISOString(),session_id:l.sessionId,request_id:D(t.request_id,80),component:D(t.component||"voice",60),stage:D(t.stage,80),event_type:D(t.event_type||"runtime_event",80),severity:D(t.severity||"info",20),status:D(t.status||"ok",20),message_code:D(t.message_code,80),duration_ms:tr(t.duration_ms),metadata:ai(t.metadata)}),n=new URL(ri,l.apiUrl).toString();fetch(n,{method:"POST",headers:{Accept:"application/json","Content-Type":"application/json"},body:e,keepalive:!0}).catch(()=>{})}function ai(t){if(!t||typeof t!="object"||Array.isArray(t))return{};let e={};for(let[n,r]of Object.entries(t).slice(0,oi)){let o=D(n,60).toLowerCase();!o||ii(o)||(typeof r=="boolean"||r===null?e[o]=r:typeof r=="number"?e[o]=tr(r):typeof r=="string"&&(e[o]=D(r,120)))}return e}function ii(t){return["audio","transcript","response","error","exception","token","secret"].some(e=>t.includes(e))}function D(t,e){return String(t||"").replace(/\s+/g," ").trim().slice(0,e)}function tr(t){let e=Number(t||0);return Number.isFinite(e)?Math.max(0,e):0}var si=3,ci="AIHubAdapterRuntime",ui="AIHubAdapter";function li(t,e){let n=new URL(w.SHOP_WS,t);return n.protocol=n.protocol==="https:"?"wss:":"ws:",n.searchParams.set("site_id",e),n.searchParams.set("session_id",l.sessionId),n.toString()}function di(t){return new Promise((e,n)=>{let r=new FileReader;r.onloadend=()=>{let o=String(r.result||"");e(o.includes(",")?o.split(",").pop():o)},r.onerror=()=>n(r.error||new Error("Failed to read audio blob")),r.readAsDataURL(t)})}var Zt=class{constructor(){this.queue=[],this.blocked=[],this.playing=!1,this.current=null,this.lastPlaybackStartMs=0,this.installUnlockListeners()}push(e,n=""){e&&(this.queue.push({audioB64:e,fallbackText:n}),this.playNext())}playNext(){if(this.playing||this.queue.length===0)return;this.playing=!0;let e=this.queue.shift(),n=new Audio(Q.DATA_WAV_PREFIX+e.audioB64);n.preload="auto",this.current=n,n.onplay=()=>{this.lastPlaybackStartMs=typeof performance<"u"?performance.now():0},n.onended=()=>{this.current=null,this.playing=!1,this.playNext()},n.onerror=()=>{this.current=null,e.fallbackText&&G(e.fallbackText),this.playing=!1,this.playNext()},n.play().catch(r=>{if(console.warn("Audio playback failed",r),this.current=null,this.isAutoplayBlocked(r)){e.fallbackText?G(e.fallbackText):this.blocked.unshift(e),this.playing=!1;return}e.fallbackText&&G(e.fallbackText),this.playing=!1,this.playNext()})}installUnlockListeners(){if(typeof window>"u")return;let e=()=>{this.retryBlocked(),bt()};window.addEventListener("pointerdown",e,{capture:!0,passive:!0}),window.addEventListener("keydown",e,{capture:!0}),window.addEventListener("touchstart",e,{capture:!0,passive:!0})}retryBlocked(){this.blocked.length&&(this.queue.unshift(...this.blocked.splice(0)),this.playNext())}speakInsteadOfBlocked(e){!e||!this.blocked.length||(this.blocked=[],G(e))}isAutoplayBlocked(e){let n=`${e?.name||""} ${e?.message||e||""}`.toLowerCase();return n.includes("notallowed")||n.includes("user didn't interact")||n.includes("not allowed")}stop(){if(this.queue=[],this.blocked=[],this.current){try{this.current.pause(),this.current.currentTime=0}catch{}this.current.onended=null,this.current.onerror=null,this.current=null}this.playing=!1,Qn()}isSpeaking(){return this.playing||this.queue.length>0||Kn()}},Tt=new Zt;function ne(){Tt.stop()}function re(){return Tt.isSpeaking()}var te=class{async sendAudio(e,n,r=[]){let o=U();I({event_type:"voice_turn_started",stage:"http_request",status:"started",metadata:{transport:"http",audio_type:e?.type||"unknown"}});let a=new FormData;a.append("audio",e,yi(e)),a.append("site_id",l.siteId),a.append("session_id",l.sessionId),r&&r.length>0&&a.append("conversation_history",JSON.stringify(r));let i=rr();i&&a.append("page_context",JSON.stringify(i));let c;try{c=await fetch(`${l.apiUrl}${w.SHOP}`,{method:Ie.POST,body:a})}catch(y){throw ot(y)}if(!c.ok)throw Zn(c,await hi(c));let p=await c.json();if(p.transcript&&n.onUserMessage?.(p.transcript),p.response_text&&n.onAssistantMessage?.(p.response_text,p.ui_actions||[]),n.onStatusChange?.(_.READY),p.audio_b64?_i(p.audio_b64,p.response_text||""):p.response_text&&G(p.response_text),p.ui_actions&&p.ui_actions.length>0){let y=await Xt(p.ui_actions);n.onActionResults?.(y)}n.onComplete?.(p),I({event_type:"voice_turn_completed",stage:"http_response",status:"ok",request_id:mi(c),duration_ms:U()-o,metadata:{transport:"http",action_count:p.ui_actions?.length||0}})}},ee=class{constructor(){this.ws=null,this.connected=!1,this.connecting=null,this.failed=!1,this.retries=0,this.audioQueue=Tt,this.callbacks=null,this.turnText="",this.receivedAudio=!1}async ensureConnected(e=[]){return this.canUseWebSocket()?this.isOpen()?!0:this.connecting?this.connecting:(this.connecting=this.openConnection(e),this.connecting):!1}canUseWebSocket(){return!this.failed&&l.useWebSocket&&"WebSocket"in window}isOpen(){return this.connected&&this.ws?.readyState===WebSocket.OPEN}openConnection(e=[]){return new Promise(n=>{let r=new WebSocket(li(l.apiUrl,l.siteId)),o=!1;this.ws=r;let a=(c=null)=>{o||(o=!0,this.markConnectionFailed(n,c,r))},i=window.setTimeout(()=>{a()},Ne);r.onopen=()=>{o||(o=!0,this.handleConnectionOpen(i,e,n))},r.onmessage=c=>{this.handleMessage(c).catch(p=>this.handleTransportError(p))},r.onerror=()=>{if(o){this.failActiveTurn(f.NETWORK);return}a(i)},r.onclose=()=>{if(this.connected=!1,o){this.failActiveTurn(f.NETWORK);return}a(i)}})}markConnectionOpen(){this.connected=!0,this.connecting=null,this.retries=0}handleConnectionOpen(e,n,r){window.clearTimeout(e),this.markConnectionOpen(),this.sendConfig(n),r(!0)}markConnectionFailed(e,n=null,r=null){n&&window.clearTimeout(n),this.connected=!1,this.connecting=null,this.retries+=1,this.retries>=si&&(this.failed=!0),r&&r.readyState!==WebSocket.CLOSED&&r.close(),e(!1)}sendConfig(e=[]){this.sendJson({type:x.CONFIG,history:e||[],session_id:l.sessionId,page_context:rr()})}sendJson(e){return!this.ws||this.ws.readyState!==WebSocket.OPEN?!1:(this.ws.send(JSON.stringify(e)),!0)}async sendAudio(e,n,r=[]){if(!await this.ensureConnected(r))return!1;this.callbacks=n,this.turnText="",this.receivedAudio=!1,this.sendConfig(r);let a=await di(e),i=this.beginTurn();return this.turnStartedAt=U(),I({event_type:"voice_turn_started",stage:"websocket_send",status:"started",metadata:{transport:"websocket",audio_type:e?.type||"unknown"}}),this.sendJson({type:x.AUDIO_CHUNK,data:a,mime_type:e?.type||""})&&this.sendJson({type:x.AUDIO_END,mime_type:e?.type||""})?(await i,!0):(this.settleTurn(),this.callbacks=null,!1)}beginTurn(){return this.settleTurn(),new Promise(e=>{let n=window.setTimeout(()=>{this.failActiveTurn(f.TIMEOUT)},ve);this.activeTurn={resolve:e,timer:n}})}settleTurn(){let e=this.activeTurn;return this.activeTurn=null,e?(window.clearTimeout(e.timer),e.resolve(),!0):!1}failActiveTurn(e){if(!this.activeTurn)return;let n=this.callbacks;if(this.callbacks=null,n){let r=new E(e,{stage:"websocket"});n.onStatusChange?.(_.ERROR,r.customerMessage),n.onComplete?.({error:r.category}),I({event_type:"voice_turn_failed",stage:"websocket",severity:"error",status:"failed",message_code:r.code||r.category,duration_ms:U()-(this.turnStartedAt||U()),metadata:{transport:"websocket",category:r.category,http_status:r.status}})}this.settleTurn()}async handleMessage(e){let n=this.callbacks;if(!n)return;let r=this.parseMessage(e.data);if(!r){this.completeWithError(n,"Invalid WebSocket message");return}if(!this.handleIncrementalMessage(r,n)){if(r.type===x.DONE){await this.handleDoneMessage(r,n);return}r.type===x.ERROR&&this.completeWithError(n,r.message||"WebSocket error")}}parseMessage(e){try{let n=JSON.parse(e);return n&&typeof n=="object"?n:null}catch{return null}}handleIncrementalMessage(e,n){return e.type===x.TRANSCRIPT?(n.onUserMessage?.(e.text||""),!0):e.type===x.TEXT_CHUNK?(this.turnText+=e.text||"",n.onAssistantChunk?.(e.text||"",this.turnText),!0):e.type===x.AUDIO_CHUNK?(this.receivedAudio=!!e.audio_b64||this.receivedAudio,this.audioQueue.push(e.audio_b64),!0):!1}async handleDoneMessage(e,n){let r=e.response_text||this.turnText;n.onAssistantMessage?.(r,e.ui_actions||[],{streamed:!0}),n.onStatusChange?.(_.READY),!this.receivedAudio&&r?G(r):this.receivedAudio&&r&&this.audioQueue.speakInsteadOfBlocked(r);try{if(e.ui_actions&&e.ui_actions.length>0){let o=await Xt(e.ui_actions);n.onActionResults?.(o)}n.onComplete?.(e),I({event_type:"voice_turn_completed",stage:"websocket_done",status:"ok",duration_ms:U()-(this.turnStartedAt||U()),metadata:{transport:"websocket",action_count:e.ui_actions?.length||0}})}catch(o){this.handleTransportError(o)}finally{this.callbacks=null,this.settleTurn()}}completeWithError(e,n){e.onStatusChange?.(_.ERROR,nr(n)),e.onComplete?.({error:n});let r=ot(n);I({event_type:"voice_turn_failed",stage:"websocket_message",severity:"error",status:"failed",message_code:r.code||r.category,duration_ms:U()-(this.turnStartedAt||U()),metadata:{transport:"websocket",category:r.category,http_status:r.status}}),this.callbacks=null,this.settleTurn()}handleTransportError(e){console.error("AI Hub WebSocket transport failed",e);let n=this.callbacks;n&&this.completeWithError(n,String(e))}},pi=new te,fi=new ee;async function er(t,e,n,r=[]){try{if(l.useWebSocket&&await fi.sendAudio(t,n,r))return;await pi.sendAudio(t,n,r)}catch(o){console.error(o);let a=o instanceof E?o:ot(o);I({event_type:"voice_turn_failed",stage:a.stage||"transport",severity:"error",status:"failed",request_id:a.requestId,message_code:a.code||a.category,metadata:{transport:l.useWebSocket?"websocket_or_http":"http",category:a.category,http_status:a.status}}),n.onStatusChange?.(_.ERROR,nr(o)),n.onComplete?.({error:String(o)})}}function mi(t){return t?.headers?.get?.("x-request-id")||t?.headers?.get?.("x-correlation-id")||""}function U(){return typeof performance<"u"?performance.now():Date.now()}function _i(t,e=""){Tt.push(t,e)}function yi(t){let e=String(t?.type||"").toLowerCase();return e.includes("mp4")?"audio.mp4":e.includes("ogg")?"audio.ogg":e.includes("wav")?"audio.wav":Q.WEBM_FILENAME}async function hi(t){try{return await t.json()}catch{return null}}function nr(t){if(t instanceof E)return t.customerMessage;let e=String(t?.message||t||"").toLowerCase();return e.includes("quota")?"Quota reached":e.includes("transcription")||e.includes("speech")?"Voice unavailable":ot(t).customerMessage}function G(t){return t?rt(String(t).slice(0,700)):!1}function rr(){let t=window[ci],e=window[ui];try{if(typeof t?.getContext=="function")return t.getContext();if(typeof e?.getContext=="function")return e.getContext()}catch(n){console.warn("[AI Hub Widget] Page context collection failed:",n)}return null}var gi=4,bi=40,Ti=24,Ei=80,Ai=120;function ar(){let t=[];function e(n,r){let o=String(r||"").trim();o&&(t.push({role:n,content:o}),t.length>Oe&&t.shift())}return{history:t,rememberUserMessage(n){e("user",n)},rememberAssistantMessage(n,r){e("assistant",Si(n,r))},rememberActionResults(n){let r=Oi(n);r&&e("assistant",r)}}}function Si(t,e){let n=Ii(e);return n.length?`${t} [PRODUCT_IDS: ${n.join(",")}]`:t}function Ii(t){let e=[];for(let n of t||[]){let r=n.params||{};or(e,r[d.PRODUCT_IDS]),or(e,[r[d.PRODUCT_ID]])}return e}function or(t,e){for(let n of Array.isArray(e)?e:[])n&&!t.includes(n)&&t.push(n)}function Oi(t){let e=(Array.isArray(t)?t:[]).map(wi).filter(Boolean).slice(0,gi);return e.length?`[BROWSER_ACTION_RESULTS: ${e.join(" | ")}]`:""}function wi(t){if(!t||typeof t!="object"||!t.action)return"";let e=[Et(t.action,bi),`status=${Et(t.status,Ti)||"unknown"}`],n=Ri(t.final_url);return n&&e.push(`final_path=${Et(n,Ai)}`),t.reason&&e.push(`reason=${Et(t.reason,Ei)}`),xi(e,t.evidence),e.join(" ")}function xi(t,e={}){e.rendered_product_count!==void 0&&t.push(`rendered_products=${Number(e.rendered_product_count||0)}`),e.rendered_entity_count!==void 0&&t.push(`rendered_records=${Number(e.rendered_entity_count||0)}`)}function Et(t,e){return String(t||"").replace(/\s+/g," ").trim().slice(0,e)}function Ri(t){try{let e=new URL(String(t||""),window.location.href);return`${e.pathname}${e.search}${e.hash}`}catch{return""}}var ir=null;function oe(t){ir||(sr(t),ir=window.setInterval(()=>sr(t),Ce))}async function sr({boot:t,shutdownWidget:e}){try{if(await Ci()){t();return}e()}catch{t()}}async function Ci(){let t=new URL(w.WIDGET_STATUS,l.apiUrl);t.searchParams.set("site_id",l.siteId);let e=await fetch(t.toString(),{cache:"no-store",headers:{Accept:"application/json"}});return e.ok?(await e.json()).enabled!==!1:!0}var Ni=280;window.__mayabot_identifier="voice-orb";var ae=null,ie=null;function cr(){if(window.__mayabotBooted||document.getElementById("mayabot-widget"))return;window.__mayabotBooted=!0,pe();let t=Ae(),e=null,n=null,r=!1;function o(m=we){e&&window.clearTimeout(e),e=window.setTimeout(()=>{t.msgs.innerHTML="",t.chat.classList.remove("visible"),e=null},m)}function a(m,T=""){r=m===_.RECORDING,ue(pr(m)),t.status.className="",m===_.RECORDING?(e&&(window.clearTimeout(e),e=null),t.msgs.innerHTML="",t.btn.classList.add("recording"),t.chat.classList.add("visible"),t.status.innerText="Listening...",t.status.classList.add("listening")):m===_.PROCESSING?(t.btn.classList.remove("recording"),t.chat.classList.add("visible"),t.status.innerText="Analyzing...",t.status.classList.add("processing")):m===_.READY?(t.status.innerText="Ready",t.status.classList.add("ready")):m===_.ERROR&&(t.status.innerText=T||"Try again",t.status.classList.add("error"),t.btn.classList.remove("recording"))}let i=ar(),c=null,p="",y=!1;async function M(m){if(!y){y=!0,t.btn.disabled=!0,c=null,p="";try{await er(m,t,{onUserMessage:T=>{K(t,T,"user"),i.rememberUserMessage(T)},onAssistantChunk:(T,At)=>{p=At,c||(c=K(t,"","ai")),It(t,c,p)},onAssistantMessage:(T,At,fr={})=>{fr.streamed&&c?It(t,c,T):K(t,T,"ai"),i.rememberAssistantMessage(T,At),c=null,p=""},onActionResults:i.rememberActionResults,onStatusChange:a,onComplete:()=>o()},i.history)}finally{y=!1,t.btn.disabled=!1,c=null,p=""}}}let Y=Le(M,a);ae=Y;let k=null,b=0;function O(){k&&window.clearTimeout(k),k=null,b=0}function g(){return re()?(ne(),I({event_type:"voice_playback_stopped",stage:"orb_gesture",status:"cancelled"}),a(_.READY),!0):!1}function se(){r||Y.toggle()}function dr(){if(y){g();return}if(r){Y.toggle();return}g()||se()}let ce={idle:{label:"Maya voice assistant. Double-click to talk. Press Enter or Space to talk.",title:"Double-click to talk"},recording:{label:"Maya is listening. Click once to send, or press Escape to cancel.",title:"Click once to send - Escape to cancel"},processing:{label:"Maya is working on your request. Please wait.",title:"Request in progress"},speaking:{label:"Maya is speaking. Click to stop, or press Escape to stop.",title:"Click to stop Maya"}};function pr(m){return m===_.RECORDING?"recording":m===_.PROCESSING?"processing":re()?"speaking":"idle"}function ue(m){let T=ce[m]||ce.idle;t.btn.setAttribute("aria-label",T.label),t.btn.setAttribute("title",T.title)}ue("idle"),t.btn.addEventListener("click",m=>{if(m.detail===0){dr();return}if(y){g();return}if(r){O(),Y.toggle();return}if(b+=1,b===1){g(),k=window.setTimeout(O,Ni);return}O(),se()});let le=m=>{if(m.key==="Escape"){if(r){O(),Y.cancel(),I({event_type:"voice_recording_cancelled",stage:"keyboard_escape",status:"cancelled"}),a(_.READY);return}g()}};document.addEventListener("keydown",le);let de=m=>{t.btn.contains(m.target)||bt()};document.addEventListener("pointerdown",de,{capture:!0}),ie=()=>{document.removeEventListener("keydown",le),document.removeEventListener("pointerdown",de,{capture:!0}),O(),e&&window.clearTimeout(e),e=null,n&&window.clearTimeout(n),n=null,ie=null},vi()&&(Li(),n=window.setTimeout(()=>{if(i.history.length>0)return;let m=`Welcome to ${l.brandName}. How can I help you today?`;K(t,m,"ai"),a(_.READY),o(Re),rt(m)},xe))}function ur(){ae?.cancel(),ae=null,ie?.(),ne(),window.__mayabotBooted=!1,document.getElementById("mayabot-widget")?.remove(),document.getElementById("mayabot-product-panel")?.remove()}function vi(){if(!l.autoGreet||!Pi())return!1;try{return window.sessionStorage.getItem(lr())!=="1"}catch{return!window.__mayabotAutoGreeted}}function Li(){window.__mayabotAutoGreeted=!0;try{window.sessionStorage.setItem(lr(),"1")}catch{}}function lr(){return`mayabot:auto-greeted:${l.siteId}`}function Pi(){let t=window.location.pathname.replace(/\/+$/,"")||"/";return t==="/"||t.endsWith("/index.html")}document.readyState==="loading"?document.addEventListener("DOMContentLoaded",()=>oe({boot:cr,shutdownWidget:ur})):oe({boot:cr,shutdownWidget:ur});})();
