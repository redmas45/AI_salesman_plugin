(()=>{function re(){let t="#5d5fef",e=document.querySelector('meta[name="theme-color"]');if(e&&e.content)t=e.content;else{let _=document.querySelector('button[class*="primary"], .btn-primary, [data-primary]');if(_){let L=window.getComputedStyle(_).backgroundColor;L&&L!=="rgba(0, 0, 0, 0)"&&L!=="transparent"&&(t=L)}}let n=window.matchMedia&&window.matchMedia("(prefers-color-scheme: dark)").matches,r=n?"rgba(24, 24, 27, 0.75)":"rgba(255, 255, 255, 0.85)",o=n?"rgba(255, 255, 255, 0.1)":"rgba(0, 0, 0, 0.08)",a=n?"#f3f4f6":"#111827",i=n?"rgba(255, 255, 255, 0.1)":"rgba(0, 0, 0, 0.05)",c=n?"rgba(0, 0, 0, 0.25)":"#ffffff",p=document.createElement("style");p.textContent=`
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
  `,document.head.appendChild(p)}var _t="site_1",tr="__AI_";var er="aihub:auto-site-id:",nr=["data-aihub-scope","data-site-scope"],rr=["data-site-id","data-aihub-site-id"];function h(t){return String(t||"").trim()}function j(t){return h(t).replace(/\/+$/,"")}function ie(t,e,n,r=_t){return or(t,e,n)||ar()||h(r)||_t}function or(t,e,n){for(let a of rr){let i=h(t?.getAttribute(a));if(i)return i}let r=h(e?.searchParams.get("site"))||h(e?.searchParams.get("site_id"))||h(e?.searchParams.get("shop"));if(r)return r;let o=h(n);return o&&!o.startsWith(tr)?o:""}function ar(){let t=ir(),e=`${er}${t}`,n=mr(e);if(n){let c=pr(n);return c!==n&&ae(e,c),c}let r=h(window.location.host||window.location.hostname||"site"),o=se(),a=dr(`${r}${o?`_${o.replace(/\//g,"_")}`:""}`),i=ce(`auto_${a}_${fr(t)}`);return ae(e,i),i}function ir(){return`${window.location.origin}${se()}`}function se(){return sr()}function sr(){for(let e of nr){let n=h(cr()?.getAttribute(e));if(n)return oe(n)}let t=document.querySelector("meta[name='aihub-site-scope']")?.getAttribute("content");return oe(t)}function cr(){return document.currentScript}function oe(t){let e=h(t);if(!e||e==="/")return"";try{let r=new URL(e,window.location.href);if(r.origin===window.location.origin){let[o]=ur(r.pathname);return o?`/${o}`:""}}catch{}let[n]=e.replace(/^\/+/,"").split("/");return n?`/${n}`:""}function ur(t=window.location.pathname){return h(t).split("/").map(e=>lr(e).trim()).filter(Boolean)}function lr(t){try{return decodeURIComponent(t)}catch{return String(t||"")}}function dr(t){return h(t).toLowerCase().replace(/[^a-z0-9]+/g,"_").replace(/^_+|_+$/g,"")||"site"}function ce(t){return h(t).slice(0,80).replace(/_+$/g,"")||_t}function pr(t){let e=h(t);return e.startsWith("auto_")?ce(e.toLowerCase().replace(/[^a-z0-9]+/g,"_").replace(/^_+|_+$/g,"")):e}function fr(t){let e=2166136261,n=h(t);for(let r=0;r<n.length;r+=1)e^=n.charCodeAt(r),e=Math.imul(e,16777619);return(e>>>0).toString(36)}function mr(t){try{return h(window.localStorage.getItem(t))}catch{return""}}function ae(t,e){try{window.localStorage.setItem(t,e)}catch{}}var x=document.currentScript,ue="__AI_PUBLIC_API_URL__",hr="__AI_DEFAULT_SITE_ID__",yr="mayabot:session:",_r="Maya",gr="AI Salesperson",br="female";function v(t){return String(t||"").trim()}function Tr(){let t=v(x?.getAttribute("src"));if(!t)return null;try{return new URL(t,window.location.href)}catch{return null}}function Ar(t){let e=v(x?.getAttribute("data-api-url"));if(e)return j(e);if(!ue.startsWith("__AI_"))return j(ue);if(t?.origin){let n=t.pathname.replace(/\/mayabot(?:-widget)?\.js$/,"");return j(`${t.origin}${n}`)}return j(window.location.origin)}function Er(t){let e=`${yr}${t}`;try{let n=window.sessionStorage.getItem(e);if(n)return n;let r=le(t);return window.sessionStorage.setItem(e,r),r}catch{return le(t)}}function le(t){let e=window.crypto?.randomUUID?.()||`${Date.now()}-${Math.random().toString(16).slice(2)}`;return`${t}-${e}`.slice(0,120)}var pe=Tr(),de=ie(x,pe,hr),d={siteId:de,get sessionId(){return Er(de)},apiUrl:Ar(pe),useWebSocket:v(x?.getAttribute("data-use-websocket")).toLowerCase()==="true",autoGreet:v(x?.getAttribute("data-auto-greet")).toLowerCase()!=="false",brandName:v(x?.getAttribute("data-brand"))||_r,assistantTitle:v(x?.getAttribute("data-assistant-title"))||gr,speechVoiceName:v(x?.getAttribute("data-speech-voice")),speechVoicePreference:v(x?.getAttribute("data-speech-voice-preference"))||br};function fe(){let t=document.createElement("div");return t.id="mayabot-widget",t.innerHTML=`
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
  `,document.body.appendChild(t),t.querySelector(".mayabot-kicker").textContent=d.brandName,t.querySelector(".mayabot-title").textContent=d.assistantTitle,{btn:document.getElementById("mayabot-btn"),chat:document.getElementById("mayabot-chat"),msgs:document.getElementById("mayabot-msgs"),status:document.getElementById("mayabot-status")}}function z(t,e,n){t.chat.classList.add("visible");let r=document.createElement("div");return r.className=`mayabot-msg ${n}`,r.innerText=e,t.msgs.appendChild(r),t.msgs.scrollTop=t.msgs.scrollHeight,r}function gt(t,e,n){e&&(e.innerText=n,t.msgs.scrollTop=t.msgs.scrollHeight)}var s=Object.freeze({ADD_TO_CART:"ADD_TO_CART",BOOK_APPOINTMENT_REQUEST:"BOOK_APPOINTMENT_REQUEST",BUILD_ITINERARY:"BUILD_ITINERARY",BUILD_LEARNING_PATH:"BUILD_LEARNING_PATH",CAPTURE_LEAD:"CAPTURE_LEAD",CAPTURE_PATIENT_LEAD:"CAPTURE_PATIENT_LEAD",CHECKOUT:"CHECKOUT",CHECKOUT_HANDOFF:"CHECKOUT_HANDOFF",CHECK_APPOINTMENT_AVAILABILITY:"CHECK_APPOINTMENT_AVAILABILITY",CHECK_AVAILABILITY:"CHECK_AVAILABILITY",CHECK_DELIVERY_AVAILABILITY:"CHECK_DELIVERY_AVAILABILITY",CHECK_ELIGIBILITY_SOFT:"CHECK_ELIGIBILITY_SOFT",CHECK_PREREQUISITES:"CHECK_PREREQUISITES",CLEAR_CART:"CLEAR_CART",CLEAR_FILTERS:"CLEAR_FILTERS",CLEAR_HISTORY:"CLEAR_HISTORY",COMPARE_ENTITIES:"COMPARE_ENTITIES",CONTACT_AGENT:"CONTACT_AGENT",FILTER_ENTITIES:"FILTER_ENTITIES",FILTER_PRODUCTS:"FILTER_PRODUCTS",HANDOFF_TO_ADVISOR:"HANDOFF_TO_ADVISOR",HANDOFF_TO_AGENT:"HANDOFF_TO_AGENT",HANDOFF_TO_CLINIC:"HANDOFF_TO_CLINIC",HANDOFF_TO_HUMAN:"HANDOFF_TO_HUMAN",HANDOFF_TO_LAWYER:"HANDOFF_TO_LAWYER",HANDOFF_TO_LICENSED_AGENT:"HANDOFF_TO_LICENSED_AGENT",HANDOFF_TO_RECRUITER:"HANDOFF_TO_RECRUITER",JOIN_WAITLIST:"JOIN_WAITLIST",MATCH_JOBS:"MATCH_JOBS",NAVIGATE_TO:"NAVIGATE_TO",OPEN_CLAIM_FLOW:"OPEN_CLAIM_FLOW",OPEN_CONTACT:"OPEN_CONTACT",OPEN_DISCLOSURE:"OPEN_DISCLOSURE",OPEN_ENTITY_DETAIL:"OPEN_ENTITY_DETAIL",OPEN_LOCATION:"OPEN_LOCATION",OPEN_MAP:"OPEN_MAP",OPEN_POLICY:"OPEN_POLICY",OPEN_PROJECTS:"OPEN_PROJECTS",OPEN_RENEWAL_FLOW:"OPEN_RENEWAL_FLOW",OPEN_SERVICES:"OPEN_SERVICES",OPEN_SYLLABUS:"OPEN_SYLLABUS",OPEN_TELECONSULT:"OPEN_TELECONSULT",REMOVE_FROM_CART:"REMOVE_FROM_CART",REQUEST_APPOINTMENT:"REQUEST_APPOINTMENT",REQUEST_CALLBACK:"REQUEST_CALLBACK",REQUEST_CONSULTATION:"REQUEST_CONSULTATION",REQUEST_COUNSELOR_CALLBACK:"REQUEST_COUNSELOR_CALLBACK",REQUEST_ESTIMATE:"REQUEST_ESTIMATE",REQUEST_SITE_VISIT:"REQUEST_SITE_VISIT",REQUEST_TEST_DRIVE:"REQUEST_TEST_DRIVE",REQUEST_VIEWING:"REQUEST_VIEWING",RUN_AFFORDABILITY_CALCULATOR:"RUN_AFFORDABILITY_CALCULATOR",RUN_CALCULATOR:"RUN_CALCULATOR",RUN_DOM_SEQUENCE:"RUN_DOM_SEQUENCE",SAVE_SEARCH:"SAVE_SEARCH",SCHEDULE_ORDER:"SCHEDULE_ORDER",SEARCH_AVAILABILITY:"SEARCH_AVAILABILITY",SET_LOCATION:"SET_LOCATION",SHOW_COMPARISON:"SHOW_COMPARISON",SHOW_EMERGENCY_NOTICE:"SHOW_EMERGENCY_NOTICE",SHOW_ENTITIES:"SHOW_ENTITIES",SHOW_PRODUCT_DETAIL:"SHOW_PRODUCT_DETAIL",SHOW_PRODUCTS:"SHOW_PRODUCTS",SORT_ENTITIES:"SORT_ENTITIES",SORT_PRODUCTS:"SORT_PRODUCTS",START_APPLICATION:"START_APPLICATION",START_BOOKING:"START_BOOKING",START_ENROLLMENT:"START_ENROLLMENT",START_INTAKE:"START_INTAKE",START_QUOTE:"START_QUOTE",START_TICKET_PURCHASE:"START_TICKET_PURCHASE",UPDATE_CART_QUANTITY:"UPDATE_CART_QUANTITY",UPDATE_PREFERENCES:"UPDATE_PREFERENCES"}),l=Object.freeze({ENTITY_ID:"entity_id",ENTITY_IDS:"entity_ids",MESSAGE:"message",PAGE:"page",PRODUCT_ID:"product_id",PRODUCT_IDS:"product_ids",QUANTITY:"quantity",REASON:"reason",SEARCH_QUERY:"search_query",URL:"url"}),gi=Object.freeze({BLOCKED:"blocked",EXECUTING:"executing",FAILED:"failed",REQUESTED:"requested",SKIPPED:"skipped",SUCCEEDED:"succeeded",UNKNOWN:"unknown"}),A=Object.freeze({KNOWLEDGE_BY_IDS:"/v1/knowledge/by-ids",PRODUCTS_BY_IDS:"/v1/products/by-ids",SHOP:"/v1/shop",SHOP_WS:"/v1/ws/shop",WIDGET_STATUS:"/v1/widget/status"}),E=Object.freeze({AUDIO_CHUNK:"audio_chunk",AUDIO_END:"audio_end",CONFIG:"config",DONE:"done",ERROR:"error",TEXT_CHUNK:"text_chunk",TRANSCRIPT:"transcript"});var me=new Set(["cart","/cart"]),R="Recommended products",D="Relevant options",W=Object.freeze({DATA_WAV_PREFIX:"data:audio/wav;base64,",WEBM_FILENAME:"audio.webm",WEBM_MIME_TYPE:"audio/webm"}),he=Object.freeze({POST:"POST"}),f=Object.freeze({ERROR:"error",PROCESSING:"processing",READY:"ready",RECORDING:"recording"}),ye=12,_e=2400,ge=900,be=4200,bt=1,H=180,Te=3e3,V=Object.freeze({MAYABOT_ACTION:"mayabot:action"}),Ae=2500;var Sr=["audio/webm;codecs=opus","audio/webm","audio/ogg;codecs=opus","audio/ogg","audio/mp4"],Ir=250,wr=128;function Ee(t,e){let n=null,r=null,o=[],a=!1,i=!1,c=!1;async function p(){if(!(i||a)){i=!0;try{let g=await navigator.mediaDevices.getUserMedia({audio:!0});r=g,c=!1;let w=Or();n=new MediaRecorder(g,w?{mimeType:w}:void 0),o=[],n.ondataavailable=y=>{y.data.size>0&&o.push(y.data)},n.onstop=async()=>{let y=new Blob(o,{type:n.mimeType||w||W.WEBM_MIME_TYPE});if(P(),c){c=!1;return}if(y.size<wr){console.warn("Microphone recording was empty or too short",{size:y.size}),e(f.READY);return}await t(y)},n.onerror=y=>{console.error("Microphone recording failed",y.error||y),a=!1,i=!1,P(),e(f.ERROR,"Recording failed")},n.start(Ir),a=!0,e(f.RECORDING)}catch(g){console.error("Microphone access denied",g),e(f.ERROR,"Mic unavailable")}finally{i=!1}}}function _({discard:g=!1}={}){if(c=g,n&&n.state!=="inactive"){try{n.requestData()}catch{}n.stop(),a=!1,g||e(f.PROCESSING);return}a=!1,P(),g||e(f.PROCESSING)}function L(){i||(a?_():p())}function F(){_({discard:!0})}function P(){r&&(r.getTracks().forEach(g=>g.stop()),r=null)}return{toggle:L,cancel:F}}function Or(){return!("MediaRecorder"in window)||typeof MediaRecorder.isTypeSupported!="function"?"":Sr.find(t=>MediaRecorder.isTypeSupported(t))||""}var Se="shopify",Ie="woocommerce",xr="custom";function Z(t){let e=String(t||"").trim();return/^\d+$/.test(e)?e:""}function tt(t,e=1){let n=Number(t?.[l.QUANTITY]);return Number.isFinite(n)&&n>0?Math.floor(n):e}async function M(t,e){return(await fetch(new URL(t,window.location.origin),{method:"POST",headers:{Accept:"application/json","Content-Type":"application/json"},body:JSON.stringify(e),credentials:"same-origin"})).ok}function Rr(){return Cr()?Se:Nr()?Ie:xr}async function we(t){let e=Rr();return e===Se?Lr(t):e===Ie?Pr(t):!1}function Cr(){return!!(window.Shopify||document.querySelector('meta[name="shopify-checkout-api-token"]')||document.querySelector('script[src*="cdn.shopify.com"]'))}function Nr(){return!!(document.body?.classList?.contains("woocommerce")||window.wc_add_to_cart_params||document.querySelector('link[href*="woocommerce"], script[src*="woocommerce"]'))}async function Lr(t){let e=t.parameters||{};if(t.action===s.ADD_TO_CART){let n=Z(e.variant_id||e.cart_id||e[l.PRODUCT_ID]);return n?M("/cart/add.js",{items:[{id:n,quantity:tt(e)}]}):!1}if(t.action===s.REMOVE_FROM_CART){let n=Z(e.cart_id||e.variant_id||e[l.PRODUCT_ID]);return n?M("/cart/change.js",{id:n,quantity:0}):!1}if(t.action===s.UPDATE_CART_QUANTITY){let n=Z(e.cart_id||e.variant_id||e[l.PRODUCT_ID]);return n?M("/cart/change.js",{id:n,quantity:tt(e,0)}):!1}return t.action===s.CLEAR_CART?M("/cart/clear.js",{}):t.action===s.CHECKOUT?et("/checkout"):Oe(t)?et("/cart"):!1}async function Pr(t){let e=t.parameters||{};if(t.action===s.ADD_TO_CART){let n=Z(e.variant_id||e.cart_id||e[l.PRODUCT_ID]);return n?M("/wp-json/wc/store/cart/add-item",{id:Number(n),quantity:tt(e)}):!1}if(t.action===s.REMOVE_FROM_CART){let n=String(e.cart_key||e.key||"").trim();return n?M("/wp-json/wc/store/cart/remove-item",{key:n}):!1}if(t.action===s.UPDATE_CART_QUANTITY){let n=String(e.cart_key||e.key||"").trim();return n?M("/wp-json/wc/store/cart/update-item",{key:n,quantity:tt(e,0)}):!1}return t.action===s.CHECKOUT?et("/checkout"):Oe(t)?et("/cart"):!1}function Oe(t){return t.action===s.NAVIGATE_TO&&me.has(t.parameters?.[l.PAGE])}function et(t){return window.location.href=t,!0}var vr="/v1/widget/action-event";function b(t){return String(t||"").trim()}function Dr(t,e){return new URL(t,e).toString()}function Ur(t){return!t||typeof t!="object"?[]:Object.keys(t).map(e=>b(e)).filter(Boolean).slice(0,20)}function Mr(t){if(!t||typeof t!="object")return{};let e={};for(let[n,r]of Object.entries(t).slice(0,20)){let o=b(n).slice(0,80);o&&(typeof r=="boolean"||r===null?e[o]=r:typeof r=="number"?e[o]=Number.isFinite(r)?r:0:e[o]=b(r).slice(0,240))}return e}async function nt(t,e,n,r){if(!t||!e||!n?.action)return;let o=JSON.stringify({site_id:e,origin:window.location.origin,url:window.location.href,occurred_at:new Date().toISOString(),request_id:b(n.request_id||n.action_request_id),turn_id:b(n.turn_id),sequence:Number(n.sequence||0),action:b(n.action).toUpperCase(),status:b(r?.status)||"unknown",stage:b(r?.stage),reason:b(r?.reason),duration_ms:Number(r?.duration_ms||0),param_keys:Ur(n.parameters||n.params),requested_url:b(r?.requested_url),final_url:b(r?.final_url||window.location.href),evidence:Mr(r?.evidence)}),a=Dr(vr,t);if(!kr(a,o))try{await fetch(a,{method:"POST",headers:{Accept:"application/json","Content-Type":"application/json"},body:o,keepalive:!0})}catch(i){console.warn("[AIHubAdapter] Action execution report failed.",i)}}function kr(t,e){if(typeof navigator>"u"||typeof navigator.sendBeacon!="function"||typeof Blob!="function")return!1;try{return navigator.sendBeacon(t,new Blob([e],{type:"application/json"}))}catch{return!1}}function xe(t){if(!t||typeof t!="string")return[];let e=[];for(let n of Fr()){try{e.push(...Array.from(n.querySelectorAll(t)))}catch{return[]}if(e.length>=600)return e.slice(0,600)}return $r(e)}function Fr(){let t=[],e=new Set,n=[document];for(;n.length&&t.length<60;){let r=n.shift();!r||e.has(r)||(e.add(r),t.push(r),n.push(...Hr(r)))}return t}function Hr(t){let e=[];for(let n of Br(t)){n.shadowRoot&&e.push(n.shadowRoot);let r=Yr(n);r&&e.push(r)}return e}function Br(t){try{return Array.from(t.querySelectorAll("*"))}catch{return[]}}function Yr(t){if(String(t?.tagName||"").toLowerCase()!=="iframe")return null;try{let e=t.contentDocument;return e?.documentElement?e:null}catch{return null}}function $r(t){return Array.from(new Set(t))}var Ri=Object.freeze([u("stripe",["stripe","stripe.com","checkout.stripe.com","js.stripe.com"]),u("paypal",["paypal","paypal.com","paypalobjects.com"]),u("razorpay",["razorpay","checkout.razorpay.com"]),u("paytm",["paytm","securegw.paytm.in"]),u("cashfree",["cashfree","cashfree.com"]),u("checkout.com",["checkout.com","cko-session-id"]),u("adyen",["adyen","checkoutshopper"]),u("square",["squareup","squarecdn","square.site"]),u("braintree",["braintree","braintreegateway"]),u("mollie",["mollie","mollie.com"]),u("klarna",["klarna","klarna.com"]),u("afterpay",["afterpay","afterpay.com","clearpay"]),u("payu",["payu","payu.in","payu.com"]),u("paystack",["paystack","paystack.co"]),u("phonepe",["phonepe","phonepe.com"]),u("billdesk",["billdesk","billdesk.com"]),u("authorize.net",["authorize.net","accept.authorize.net"])]),Re=Object.freeze([u("calendly",["calendly","calendly.com"]),u("acuity",["acuityscheduling","squarespace scheduling"]),u("booksy",["booksy","booksy.com"]),u("zocdoc",["zocdoc","zocdoc.com"]),u("appointlet",["appointlet","appointlet.com"]),u("setmore",["setmore","setmore.com"]),u("cal.com",["cal.com","calcom"]),u("google_calendar",["calendar.google.com","google calendar"]),u("microsoft_bookings",["microsoft bookings","outlook.office365.com/book"]),u("simplybook",["simplybook","simplybook.me"]),u("tidycal",["tidycal","tidycal.com"]),u("savvycal",["savvycal","savvycal.com"]),u("fresha",["fresha","fresha.com"])]),Ce=Object.freeze([u("google_maps",["google.com/maps","maps.googleapis","maps.google"]),u("mapbox",["mapbox","mapbox.com"]),u("openstreetmap",["openstreetmap","osm.org"]),u("leaflet",["leaflet","leafletjs"]),u("here_maps",["here.com","hereapi","wego.here.com"]),u("bing_maps",["bing.com/maps","virtualearth"]),u("mappls",["mappls","mapmyindia"])]),Ne=Object.freeze([u("whatsapp",["wa.me","api.whatsapp.com","web.whatsapp.com"]),u("telegram",["t.me/","telegram.me"]),u("messenger",["m.me/","messenger.com/t"]),u("zendesk",["zendesk.com","zdassets.com/hc"]),u("intercom",["intercom.help","intercom.com"]),u("freshchat",["freshchat.com"])]),Ci=Object.freeze([u("recaptcha",["recaptcha","g-recaptcha","google.com/recaptcha"]),u("hcaptcha",["hcaptcha","h-captcha"]),u("turnstile",["turnstile","challenges.cloudflare.com"]),u("cloudflare_challenge",["cf-chl","cloudflare challenge"])]);function u(t,e){return{name:t,tokens:e}}function Tt(t,e,n=10){let r=At(t);return e.filter(o=>o.tokens.some(a=>r.includes(a))).map(o=>o.name).slice(0,n)}function At(t){return String(t||"").replace(/\s+/g," ").trim().toLowerCase()}var Le="a[href], iframe[src]",jr="a[href]",ve=new Set(["http:","https:"]),rt=new Set(["mailto:","tel:"]),zr=Object.freeze([l.URL,"href","link","target_url","provider_url","booking_url","appointment_url","calendar_url","map_url","location_url","contact_url"]),De=new Set([s.OPEN_MAP,s.OPEN_LOCATION,s.SET_LOCATION]),Ue=new Set([s.CHECK_APPOINTMENT_AVAILABILITY,s.REQUEST_APPOINTMENT,s.BOOK_APPOINTMENT_REQUEST,s.REQUEST_CONSULTATION,s.REQUEST_SITE_VISIT,s.START_BOOKING]),Me=new Set([s.OPEN_CONTACT,s.CONTACT_AGENT,s.REQUEST_CALLBACK,s.REQUEST_COUNSELOR_CALLBACK,s.HANDOFF_TO_ADVISOR,s.HANDOFF_TO_AGENT,s.HANDOFF_TO_CLINIC,s.HANDOFF_TO_HUMAN,s.HANDOFF_TO_LAWYER,s.HANDOFF_TO_LICENSED_AGENT,s.HANDOFF_TO_RECRUITER]);function ke(t){let e=Be(t);return De.has(e)||Ue.has(e)||Me.has(e)}async function Fe(t){let e=Be(t);return De.has(e)?Et(t,Ce,Le,St):Ue.has(e)?Et(t,Re,Le,St):Me.has(e)?Et(t,Ne,jr,qr):!1}function Et(t,e,n,r){let o=Wr(t?.parameters||t?.params||{},e,r);if(o)return Pe(o);let a=Vr(n,e,r);return a?Pe(a):!1}function Wr(t,e,n){for(let r of zr){let o=He(t?.[r]);if(o&&n(o,e))return o}return null}function Vr(t,e,n){for(let r of xe(t)){let o=Gr(r);if(!(!o||!n(o,e))&&Kr(o,r,e))return o}return null}function Gr(t){return He(t?.getAttribute?.("href")||t?.getAttribute?.("src"))}function St(t,e){return ve.has(t.protocol)&&Tt(t.href,e).length>0}function qr(t,e){return rt.has(t.protocol)?!0:St(t,e)}function Kr(t,e,n){if(rt.has(t.protocol))return!0;let r=[t.href,e?.textContent||"",e?.getAttribute?.("aria-label")||"",e?.getAttribute?.("title")||""].join(" ");return Tt(At(r),n).length>0}function Pe(t){if(rt.has(t.protocol)||t.origin===window.location.origin)return window.location.href=t.href,!0;let e=window.open(t.href,"_blank","noopener,noreferrer");return e?(e.opener=null,!0):(window.location.href=t.href,!0)}function He(t){let e=String(t||"").trim();if(!e||e.startsWith("#"))return null;try{let n=new URL(e,window.location.href);return ve.has(n.protocol)||rt.has(n.protocol)?n:null}catch{return null}}function Be(t){return String(t?.action||"").trim().toUpperCase()}var Qr=Object.freeze(["title","name"]),Xr=Object.freeze(["summary","description","body"]),Jr=Object.freeze(["image_url","imageUrl","image","thumbnail"]),Zr=Object.freeze(["url","href","permalink","source_url"]),to="knowledge_item",eo=30;function S(t){return t==null||typeof t=="object"?"":String(t||"").trim()}function no(t){let e=new Set;return(Array.isArray(t)?t:[]).map(S).filter(Boolean).filter(n=>e.has(n)||e.size>=eo?!1:(e.add(n),!0))}function ot(t,e){for(let n of e){let r=S(t?.[n]);if(r)return r}return""}function G(t){return t&&typeof t=="object"&&!Array.isArray(t)?t:{}}function ro(t){let e=oo([t?.price,t?.amount,t?.premium,t?.premium_min,t?.monthly_premium,t?.annual_premium,t?.min_price,t?.starting_price]),n=S(t?.currency||"INR");return!Number.isFinite(e)||e<=0?"":`${n} ${e.toLocaleString()}`}function oo(t){for(let e of t){let n=Number(String(e??"").replace(/,/g,""));if(Number.isFinite(n)&&n>0)return n}return 0}function ao(t){return!t||typeof t!="object"?"":t.in_stock===!0?"Available":t.in_stock===!1?"Unavailable":S(t.status||t.availability||"")}function io(t){let e=S(t);if(!e)return"";try{let n=new URL(e,window.location.origin);return/^https?:$/i.test(n.protocol)?n.origin===window.location.origin?`${n.pathname}${n.search}${n.hash}`:n.toString():""}catch{return""}}function so(t){if(!t)return null;let e=S(t.id);if(!e)return null;let n=G(t.pricing),r=G(t.availability);return{id:e,externalId:S(t.external_id),entityType:S(t.entity_type||t.category_name)||to,title:ot(t,Qr)||e,subtitle:S(t.subtitle||t.category_name||t.entity_type),summary:ot(t,Xr),body:S(t.body),url:io(ot(t,Zr)),imageUrl:ot(t,Jr),attributes:G(t.attributes),pricing:n,availability:r,location:G(t.location),contact:G(t.contact),displayPrice:ro(n),displayAvailability:ao(r)}}async function It(t){let e=no(t);if(!e.length)return[];let n=new URL(A.KNOWLEDGE_BY_IDS,d.apiUrl);n.searchParams.set("site_id",d.siteId),n.searchParams.set("ids",e.join(","));let r=await fetch(n.toString(),{headers:{Accept:"application/json"}});if(!r.ok)throw new Error("Failed to fetch entities from AI Hub API");let o=(await r.json()).map(so).filter(Boolean),a=new Map(o.map(i=>[String(i.id),i]));return e.map(i=>a.get(i)).filter(Boolean)}async function Ye(t){let[e]=await It([t]);return e?.url||""}function $e(){if(document.getElementById("mayabot-entity-overlay-styles"))return;let t=document.createElement("style");t.id="mayabot-entity-overlay-styles",t.textContent=`
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
  `,document.head.appendChild(t)}var co=2,je=Number.POSITIVE_INFINITY,at=Number.NEGATIVE_INFINITY,ze=12,Ot=[],xt=D;function C(t){return String(t??"").replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;").replace(/"/g,"&quot;").replace(/'/g,"&#039;")}function qe(t){return String(t||"item").replace(/[_-]+/g," ").trim().split(/\s+/).slice(0,co).join(" ")}function uo(){$e();let t=document.getElementById("mayabot-entity-panel");return t||(t=document.createElement("div"),t.id="mayabot-entity-panel",t.setAttribute("aria-live","polite"),t.innerHTML=`
    <div class="mayabot-entity-header">
      <h2 class="mayabot-entity-title">${D}</h2>
      <button class="mayabot-entity-close" type="button" aria-label="Close recommendations">&times;</button>
    </div>
    <div class="mayabot-entity-grid"></div>
  `,t.querySelector(".mayabot-entity-close").addEventListener("click",()=>{t.classList.remove("active")}),document.body.appendChild(t),t)}function lo(t){return t<=1?"count-1":t===2?"count-2":t===3?"count-3":"count-many"}function po(t){return t<=1?1:t===2?2:3}function wt(t,e,n=""){let r=(Array.isArray(e)?e:[]).map(c=>String(c?.id??"").trim()).filter(Boolean),o=r.length,a=t.length,i=o>0?"succeeded":"failed";return{status:i,stage:"entity_overlay",reason:n||(i==="succeeded"?"":"no_matching_entities_rendered"),evidence:{requested_entity_count:a,rendered_entity_count:o,missing_entity_count:Math.max(a-o,0),requested_entity_ids:t.slice(0,ze).join(","),rendered_entity_ids:r.slice(0,ze).join(",")}}}function fo(t){return[t.displayPrice,t.displayAvailability,t.location?.city,t.attributes?.category].map(e=>String(e||"").trim()).filter(Boolean).slice(0,3)}function mo(t){return t.imageUrl?`
      <div class="mayabot-entity-media">
        <img src="${C(t.imageUrl)}" alt="${C(t.title)}">
      </div>
    `:`
    <div class="mayabot-entity-media">
      <div class="mayabot-entity-badge">${C(qe(t.entityType))}</div>
    </div>
  `}function ho(t){let e=fo(t);return e.length?`
    <div class="mayabot-entity-facts">
      ${e.map(n=>`<span class="mayabot-entity-fact">${C(n)}</span>`).join("")}
    </div>
  `:""}function yo(t){return t.url?`
    <div class="mayabot-entity-actions">
      <button type="button" data-view-entity="${C(t.id)}">Open</button>
    </div>
  `:""}function st(t,e){let n=uo(),r=n.querySelector(".mayabot-entity-grid"),o=n.querySelector(".mayabot-entity-title"),a=t.length;if(Ot=Array.isArray(t)?[...t]:[],xt=e||D,n.classList.remove("count-1","count-2","count-3","count-many"),n.classList.add(lo(a)),n.style.setProperty("--mayabot-entity-card-count",String(po(a))),o.textContent=xt,!a){r.innerHTML='<p class="mayabot-entity-empty">No matching records are currently available.</p>',n.classList.add("active"),We();return}r.innerHTML=t.map(i=>`
        <article class="mayabot-entity-card" data-entity-id="${C(i.id)}">
          ${mo(i)}
          <h3 class="mayabot-entity-name">${C(i.title)}</h3>
          <p class="mayabot-entity-meta">${C(i.subtitle||qe(i.entityType))}</p>
          <p class="mayabot-entity-summary">${C(i.summary||i.body||"Details are available on the website.")}</p>
          ${ho(i)}
          ${yo(i)}
        </article>
      `).join(""),r.querySelectorAll("[data-view-entity]").forEach(i=>{i.addEventListener("click",async()=>{await Rt(i.getAttribute("data-view-entity"))})}),n.classList.add("active"),We()}function _o(t){if(!t)return!1;try{let e=new URL(t,window.location.origin);return e.origin===window.location.origin?(window.location.href=`${e.pathname}${e.search}${e.hash}`,!0):(window.open(e.toString(),"_blank","noopener,noreferrer"),!0)}catch{return!1}}function We(){window.setTimeout(()=>{let t=document.getElementById("mayabot-chat"),e=document.getElementById("mayabot-msgs");e&&(e.innerHTML=""),t&&t.classList.remove("visible")},H)}async function Rt(t){let e=await Ye(t);return _o(e)}async function Ke(t,e=D){let n=Ct({[l.ENTITY_IDS]:t});if(!n.length)return st([],e),wt([],[],"missing_entity_ids");try{let r=await It(n);return st(r,e),wt(n,r)}catch(r){return console.warn("[AI Hub Widget] Entity overlay failed:",r),st([],e),wt(n,[],"entity_overlay_fetch_failed")}}function Ct(t){let e=t[l.ENTITY_IDS]||t.ids||t.items||[],n=new Set;return(Array.isArray(e)?e:[]).map(r=>String(r??"").trim()).filter(Boolean).filter(r=>n.has(r)?!1:(n.add(r),!0))}function Qe(t={}){if(!Ot.length)return!1;let e=String(t.sort_by||t.sortBy||"price_asc").trim().toLowerCase(),n=[...Ot].sort((o,a)=>go(o,a,e)),r=To(xt,e);return st(n,r),!0}function go(t,e,n){return n==="price_desc"?it(e,at)-it(t,at):n==="rating"?Ve(e,at)-Ve(t,at):n==="newest"?Ge(e)-Ge(t):it(t,je)-it(e,je)}function it(t,e){return Xe([t?.pricing?.price,t?.pricing?.amount,t?.pricing?.premium,t?.pricing?.premium_min,t?.pricing?.monthly_premium,t?.pricing?.annual_premium,t?.pricing?.min_price,t?.pricing?.starting_price,t?.attributes?.price,t?.attributes?.amount,t?.attributes?.premium,t?.attributes?.monthly_premium,t?.attributes?.annual_premium,t?.displayPrice],e)}function Ve(t,e){return Xe([t?.attributes?.rating,t?.attributes?.review_rating,t?.attributes?.stars,t?.availability?.rating],e)}function Ge(t){let e=t?.attributes?.updated_at||t?.attributes?.date||t?.availability?.updated_at||"",n=Date.parse(String(e||""));return Number.isFinite(n)?n:0}function Xe(t,e){for(let n of t){let r=bo(n);if(Number.isFinite(r))return r}return e}function bo(t){if(typeof t=="number")return t;let e=String(t??"").replace(/,/g,"").match(/-?\d+(?:\.\d+)?/);return e?Number(e[0]):Number.NaN}function To(t,e){let n={price_asc:"sorted low to high",price_desc:"sorted high to low",rating:"sorted by rating",newest:"newest first"};return`${String(t||D).replace(/\s+-\s+sorted.*$/i,"")} - ${n[e]||n.price_asc}`}function Je(t){return t.action===s.SHOW_ENTITIES||t.action===s.COMPARE_ENTITIES||t.action===s.OPEN_ENTITY_DETAIL||t.action===s.SORT_ENTITIES}async function Ze(t){return t.action===s.SHOW_ENTITIES||t.action===s.COMPARE_ENTITIES?Ao(t.parameters||{}):t.action===s.OPEN_ENTITY_DETAIL?Rt(t.parameters?.[l.ENTITY_ID]||t.parameters?.id):t.action===s.SORT_ENTITIES?Qe(t.parameters||{}):!1}function Ao(t){return Ke(Ct(t),t[l.SEARCH_QUERY]||t.title||D)}var q="mayabot-handoff-panel",tn="mayabot-handoff-overlay-styles",Eo=Object.freeze(["contact","support","help"]),So=Object.freeze(["checkout","cart"]),on=new Set([s.CHECKOUT_HANDOFF,s.HANDOFF_TO_ADVISOR,s.HANDOFF_TO_AGENT,s.HANDOFF_TO_CLINIC,s.HANDOFF_TO_HUMAN,s.HANDOFF_TO_LAWYER,s.HANDOFF_TO_LICENSED_AGENT,s.HANDOFF_TO_RECRUITER]),en=Object.freeze({[s.CHECKOUT_HANDOFF]:{title:"Checkout needs your confirmation",body:"This step may include payment or a secure checkout page. I can take you there, then you complete the final step yourself.",primary:"Open checkout"},[s.HANDOFF_TO_ADVISOR]:{title:"Advisor handoff",body:"This request needs a qualified advisor. I can open the contact path so the site team can continue.",primary:"Contact advisor"},[s.HANDOFF_TO_AGENT]:{title:"Agent handoff",body:"This step needs an agent or account-specific help. I can open the contact path for follow-up.",primary:"Contact agent"},[s.HANDOFF_TO_CLINIC]:{title:"Clinic handoff",body:"This request needs clinic confirmation. I can open the appointment or contact path for the next step.",primary:"Contact clinic"},[s.HANDOFF_TO_HUMAN]:{title:"Human handoff",body:"This step needs human confirmation. I can open the most relevant contact path.",primary:"Open contact"},[s.HANDOFF_TO_LAWYER]:{title:"Legal handoff",body:"This request needs a legal professional. I can open the consultation or contact path.",primary:"Contact lawyer"},[s.HANDOFF_TO_LICENSED_AGENT]:{title:"Licensed agent handoff",body:"This request needs a licensed agent. I can open the quote or contact path for follow-up.",primary:"Contact agent"},[s.HANDOFF_TO_RECRUITER]:{title:"Recruiter handoff",body:"This request needs recruiter review. I can open the application or contact path.",primary:"Contact recruiter"}});function B(t){return String(t??"").replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;").replace(/"/g,"&quot;").replace(/'/g,"&#039;")}function k(t){return String(t||"").trim()}function Io(){if(document.getElementById(tn))return;let t=document.createElement("style");t.id=tn,t.textContent=`
    #${q} {
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
    #${q}.active {
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
      #${q} {
        bottom: 82px;
        width: min(calc(100vw - 20px), 420px);
      }
    }
  `,document.head.appendChild(t)}function wo(){Io();let t=document.getElementById(q);return t||(t=document.createElement("div"),t.id=q,t.setAttribute("aria-live","polite"),document.body.appendChild(t),t)}function Oo(){return window.AIHubAdapterRuntime?.config?.adapter?.routes||window.AIHubAdapter?.config?.adapter?.routes||{}}function xo(t,e){let n=nn(e[l.URL]||e.path||e.href||e.handoff_flow?.page_url);if(n)return n;let r=Oo(),o=t===s.CHECKOUT_HANDOFF?So:Eo;for(let a of o){let i=nn(r[a]);if(i)return i}return""}function nn(t){let e=k(t);if(!e)return"";try{let n=new URL(e,window.location.origin);return n.origin!==window.location.origin?"":`${n.pathname}${n.search}${n.hash}`||"/"}catch{return""}}function Ro(t){return en[t]||en[s.HANDOFF_TO_HUMAN]}function Co(t){return t&&typeof t=="object"?t:{}}function No(t,e){return k(t.title)||e}function Lo(t,e,n){return k(e[l.MESSAGE])||k(t.handling)||n}function Po(t,e){return k(e[l.REASON]||e.reason||e.blocked_reason||t.key)}function vo(t){let e=[["Provider",t.provider_label||t.provider],["Boundary",t.automation_boundary],["Recovery",t.recovery],["Evidence",t.evidence],["Page",t.page_url]].filter(([,n])=>k(n));return e.length?`
    <p class="mayabot-handoff-meta">
      ${e.map(([n,r])=>`<span><strong>${B(n)}:</strong> ${B(r)}</span>`).join("")}
    </p>
  `:""}function rn(t){t.classList.remove("active")}function Do(){window.setTimeout(()=>{let t=document.getElementById("mayabot-chat"),e=document.getElementById("mayabot-msgs");e&&(e.innerHTML=""),t&&t.classList.remove("visible")},H)}function an(t,e={}){let n=k(t).toUpperCase(),r=Ro(n),o=Co(e.handoff_flow),a=wo(),i=xo(n,e),c=No(o,r.title),p=Lo(o,e,r.body),_=Po(o,e);return a.innerHTML=`
    <div class="mayabot-handoff-body">
      <div class="mayabot-handoff-top">
        <h2 class="mayabot-handoff-title">${B(c)}</h2>
        <button class="mayabot-handoff-close" type="button" aria-label="Close handoff">&times;</button>
      </div>
      <p class="mayabot-handoff-text">${B(p)}</p>
      ${vo(o)}
      ${_?`<p class="mayabot-handoff-reason">${B(_)}</p>`:""}
      <div class="mayabot-handoff-actions">
        <button type="button" class="secondary" data-close-handoff>Close</button>
        ${i?`<button type="button" data-open-handoff>${B(r.primary)}</button>`:""}
      </div>
    </div>
  `,a.querySelector(".mayabot-handoff-close")?.addEventListener("click",()=>rn(a)),a.querySelector("[data-close-handoff]")?.addEventListener("click",()=>rn(a)),a.querySelector("[data-open-handoff]")?.addEventListener("click",()=>{window.location.href=i}),a.classList.add("active"),Do(),!0}function sn(t){return on.has(t.action)}function cn(t){return an(t.action,t.parameters||{})}function ln(t){return t.action===s.NAVIGATE_TO&&!!pn(t.parameters?.[l.PAGE])}function dn(t){return window.location.href=pn(t.parameters?.[l.PAGE]),!0}function pn(t){let e=String(t||"").trim();if(!e||fn(e)||/^https?:\/\//i.test(e))return"";if(e==="home"||e==="/")return"/";let n=Uo(e);if(n)return n;let r=e.replace(/^\/+|\/+$/g,"");return r?`/${r}`:"/"}function Uo(t){let e=window.AIHubAdapterRuntime?.config?.adapter?.routes||window.AIHubAdapter?.config?.adapter?.routes||{},n=Mo(t);for(let r of n){let o=e[r],a=un(o);if(a)return a}for(let[r,o]of Object.entries(e)){if(!n.includes(Nt(r)))continue;let a=un(o);if(a)return a}return""}function Mo(t){let e=Nt(t),n=String(t||"").trim().replace(/^\/+|\/+$/g,"").toLowerCase(),r=n.split("?")[0].split("#")[0].split("/").filter(Boolean).pop()||"";return Array.from(new Set([e,n,Nt(r)].filter(Boolean)))}function Nt(t){return String(t||"").trim().toLowerCase().replace(/[^a-z0-9/_\s-]+/g," ").replace(/[_-]+/g," ").replace(/\s+/g," ").trim().replace(/\s+/g,"-")}function un(t){let e=String(t||"").trim();if(!e||fn(e))return"";if(/^https?:\/\//i.test(e))try{let n=new URL(e);return n.origin!==window.location.origin?"":`${n.pathname||"/"}${n.search||""}${n.hash||""}`}catch{return""}return e.startsWith("/")?e:`/${e.replace(/^\/+/,"")}`}function fn(t){return/^(?:javascript:|data:|\/\/)/i.test(String(t||"").trim())}function mn(t){let e=t?.params||t?.parameters||{};return{...t||{},action:String(t?.action||"").trim().toUpperCase(),params:e,parameters:e}}var Lt="AIHubAdapterRuntime",Pt="AIHubAdapter";function ko(t){let e=t?.params||t?.parameters||{};return{...t||{},params:e,parameters:e}}function K(){return!!(window[Lt]?.executeAction||window[Pt]?.handleAction)}async function vt(t){return(await Q(t)).succeeded}async function Q(t){let e=ko(t);if(window[Lt]?.executeAction){let n=window[Lt],r=await n.executeAction(e)===!0,o=n.lastActionResult||{};return{succeeded:r,handled:o.handled===!0||r,status:o.status||(r?"ok":"not_handled"),reason:o.reason||"",blocked:o.status==="blocked",disabled:o.status==="disabled"}}if(window[Pt]?.handleAction){let n=await window[Pt].handleAction(e)===!0;return{succeeded:n,handled:n,status:n?"ok":"not_handled",reason:"",blocked:!1,disabled:!1}}return{succeeded:!1,handled:!1,status:"missing_adapter",reason:"",blocked:!1,disabled:!1}}var Fo=Object.freeze([{path:"/api/products?per_page=96",routePrefix:"/product/"},{path:"/api/products",routePrefix:"/product/"},{path:"/api/products.json",routePrefix:""},{path:"/products.json",routePrefix:"/products/"},{path:"/collections/all/products.json",routePrefix:"/products/"}]),Ho=Object.freeze(["products","data","items","results"]),yn=Object.freeze(["id","product_id","handle","sku"]),_n=Object.freeze(["name","title"]),Bo=Object.freeze(["url","href","permalink","product_url"]),Yo=Object.freeze(["image_url","imageUrl","image_src","imageSrc","image","images","media","thumbnail","thumbnail_url","featured_image","featuredImage","featured_image_url"]),$o=Object.freeze(["brand","vendor"]),jo=Object.freeze(["category","category_name","product_type"]),zo=Object.freeze(["description","summary","body_html"]),Wo=Object.freeze(["original_price","compare_at_price","regular_price"]),gn=Object.freeze(["currency","currency_code"]),Vo=Object.freeze(["display_price","price_text","formatted_price"]),Go="Unknown Brand",qo="Products",Ko="/",Qo=/^[a-z0-9][a-z0-9-]*$/i,Dt=null;function T(t){return t==null||typeof t=="object"?"":String(t||"").trim()}function kt(t){return T(t).toLowerCase().replace(/[^a-z0-9]+/g," ").trim()}function bn(t){let e=new Set(["a","am","an","and","ask","asked","did","for","me","not","on","only","please","show","some","the","to","wanna","want","what","with","you","your"]),n=[],r=new Set;for(let o of Xo(kt(t)).split(" ")){let a=Jo(o);a.length<=1||e.has(a)||r.has(a)||(n.push(a),r.add(a))}return n}function Xo(t){return t.replace(/\b(?:i\s+)?did\s+not\s+ask\s+for\s+(?:a\s+|an\s+)?[a-z0-9]+\b/g," ")}function Jo(t){return["phone","phones","mobile","mobiles"].includes(t)?"phone":["book","books"].includes(t)?"books":t}function Ft(t,e){return e.map(n=>T(t?.[n])).filter(Boolean)}function I(t,e){return Ft(t,e)[0]||""}function ct(t){let e=T(t).replace(/,/g,"");if(!e)return 0;let n=e.match(/-?\d+(?:\.\d+)?/),r=Number(n?n[0]:e);return Number.isFinite(r)?r:0}function Zo(t,e){let n=I(t,Vo);if(n)return n;let r=I(t,gn).toUpperCase();return e>0&&r?`${r} ${e.toLocaleString()}`:e>0?e.toLocaleString():""}function ta(t){for(let e of Yo){let n=Ut(t?.[e]);if(n)return n}return""}function Ut(t){if(!t)return"";if(Array.isArray(t)){for(let e of t){let n=Ut(e);if(n)return n}return""}if(typeof t=="object"){for(let e of["src","url","image_url","imageUrl","image_src","imageSrc","thumbnail","thumbnail_url","featured_image","featuredImage","featured_image_url"]){let n=Ut(t[e]);if(n)return n}return""}return ea(t)}function ea(t){let e=T(t);if(!e||/^javascript:/i.test(e))return"";if(/^data:image\//i.test(e))return e;try{let n=new URL(e,window.location.origin);return["http:","https:"].includes(n.protocol)?n.toString():""}catch{return""}}function na(t){let e=T(t);if(!e)return"";try{let n=new URL(e,window.location.origin);return n.origin!==window.location.origin?"":`${n.pathname}${n.search}${n.hash}`}catch{return""}}function ra(t,e,n){let r=na(I(t,Bo));return r||(!Qo.test(e)||!/[a-z]/i.test(e)||!n?.routePrefix?"":`${n.routePrefix}${encodeURIComponent(e)}${Ko}`)}function Ht(t,e={}){if(!t)return null;let n=I(t,yn),r=T(t.handle||t.slug||t.product_handle),o=I(t,_n),a=ct(t.price||t.amount||t.cost),i=ct(I(t,Wo));return!n&&!r?null:{id:n,handle:r,name:o,title:T(t.title||o),brand:I(t,$o)||Go,category:I(t,jo)||qo,description:I(t,zo),price:Number.isFinite(a)?a:0,originalPrice:Number.isFinite(i)?i:0,displayPrice:Zo(t,a),currency:I(t,gn),rating:ct(t.rating||t.review_rating),reviewCount:ct(t.review_count||t.reviews_count||t.reviews),imageUrl:ta(t),url:ra(t,r||n,e)}}function oa(t){return Ft(t,yn)}function hn(t){return Ft(t,_n).map(kt)}function Tn(t,e){let n=T(e);return!!(n&&oa(t).includes(n))}function An(t,e){let n=bn(e);if(!n.length)return!1;let r=kt([t?.name,t?.title,t?.brand,t?.category,t?.category_name,t?.product_type,t?.description,t?.tags].join(" "));return n.every(o=>r.includes(o)||r.includes(o.replace(/s$/,"")))}function aa(t,e){let n=new Set(hn(e));return hn(t).some(r=>n.has(r))}function ia(t,e){return!!(t?.imageUrl&&t.imageUrl===e?.imageUrl)}function sa(t){if(Array.isArray(t))return t;for(let e of Ho){let n=t?.[e];if(Array.isArray(n))return n}return[]}async function ca(t){try{let e=await fetch(new URL(t.path,window.location.origin),{headers:{Accept:"application/json"}});if(!e.ok)return[];let n=await e.json();return sa(n).map(r=>Ht(r,t)).filter(Boolean)}catch(e){return console.warn(`[AI Hub Widget] Catalog endpoint lookup failed for ${t.path}:`,e),[]}}async function Mt(){return Dt||(Dt=Promise.all(Fo.map(ca)).then(t=>t.flat())),Dt}async function ua(t,e=120){if(!bn(t).length)return[];let r=new URL("/v1/products",d.apiUrl);r.searchParams.set("site_id",d.siteId),r.searchParams.set("limit",String(e));try{let o=await fetch(r.toString(),{headers:{Accept:"application/json"}});return o.ok?(await o.json()).map(a=>Ht(a)).filter(Boolean).filter(a=>An(a,t)).slice(0,12):[]}catch(o){return console.warn("[AI Hub Widget] Hub product search fallback failed:",o),[]}}async function En(t,e=""){let n=(Array.isArray(t)?t:[]).map(T).filter(Boolean),r=[],o="",a="";if(n.length)try{r=await Sn(n),o="hub_by_ids"}catch(i){a="hub_product_lookup_failed",console.warn("[AI Hub Widget] Hub product ID lookup failed:",i)}if(!r.length&&n.length){let i=await Mt();r=n.map(c=>i.find(p=>Tn(p,c))).filter(Boolean),r.length&&(o="host_by_ids")}return!r.length&&e&&(r=await ua(e),r.length&&(o="hub_search")),!r.length&&e&&(r=(await Mt()).filter(c=>An(c,e)).slice(0,12),r.length&&(o="host_search")),{products:r,source:o,reason:r.length?"":a||"no_matching_products_rendered"}}async function Sn(t){let e=(Array.isArray(t)?t:[]).map(T).filter(Boolean);if(!e.length)return[];let n=new URL(A.PRODUCTS_BY_IDS,d.apiUrl);n.searchParams.set("site_id",d.siteId),n.searchParams.set("ids",e.join(","));let r=await fetch(n.toString(),{headers:{Accept:"application/json"}});if(!r.ok)throw new Error("Failed to fetch products from AI Hub API");let o=(await r.json()).map(i=>Ht(i)).filter(Boolean),a=new Map(o.map(i=>[String(i.id),i]));return e.map(i=>a.get(i)).filter(Boolean)}async function ut(t){let e=T(t);if(!e)return"";let[n]=await Sn([e]);if(n?.url)return n.url;let r=await Mt(),o=r.find(i=>Tn(i,e));return o?.url?o.url:n&&r.find(i=>aa(i,n)||ia(i,n))?.url||""}var la=["data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='320' height='240' viewBox='0 0 320 240'%3E","%3Crect width='320' height='240' fill='%23f1f2ee'/%3E","%3Cpath d='M98 156h124l-31-40-25 30-17-22-51 32Z' fill='%23c8c3ba'/%3E","%3Ccircle cx='117' cy='95' r='17' fill='%23d8d3ca'/%3E","%3Ctext x='160' y='198' text-anchor='middle' fill='%23686660' font-family='Arial,sans-serif' font-size='16'%3EImage pending%3C/text%3E","%3C/svg%3E"].join(""),In=12,Yt=[],$t=R,xn=new Map;function U(t){return String(t??"").replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;").replace(/"/g,"&quot;").replace(/'/g,"&#039;")}function da(){if(document.getElementById("mayabot-product-overlay-styles"))return;let t=document.createElement("style");t.id="mayabot-product-overlay-styles",t.textContent=`
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
  `,document.head.appendChild(t)}function pa(){da();let t=document.getElementById("mayabot-product-panel");return t||(t=document.createElement("div"),t.id="mayabot-product-panel",t.setAttribute("aria-live","polite"),t.innerHTML=`
    <div class="mayabot-product-header">
      <h2 class="mayabot-product-title">${R}</h2>
      <button class="mayabot-product-close" type="button" aria-label="Close recommendations">&times;</button>
    </div>
    <div class="mayabot-product-grid"></div>
  `,t.querySelector(".mayabot-product-close").addEventListener("click",()=>{t.classList.remove("active")}),document.body.appendChild(t),t)}async function fa(t){let e={action:s.ADD_TO_CART,params:{[l.PRODUCT_ID]:t,[l.QUANTITY]:bt},parameters:{[l.PRODUCT_ID]:t,[l.QUANTITY]:bt}};K()&&await vt(e)||window.dispatchEvent(new CustomEvent(V.MAYABOT_ACTION,{detail:e}))}async function ma(t){try{let n=await ut(t);if(n){window.location.href=n;return}}catch(n){console.warn("[AI Hub Widget] Product detail URL lookup failed:",n)}let e={action:s.SHOW_PRODUCT_DETAIL,params:{[l.PRODUCT_ID]:t},parameters:{[l.PRODUCT_ID]:t}};K()&&await vt(e)||window.dispatchEvent(new CustomEvent(V.MAYABOT_ACTION,{detail:e}))}function ha(t){return t<=1?"count-1":t===2?"count-2":t===3?"count-3":"count-many"}function ya(t){return t<=1?1:t===2?2:3}function _a(t){let e=new Set;return(Array.isArray(t)?t:[]).map(n=>String(n??"").trim()).filter(Boolean).filter(n=>e.has(n)?!1:(e.add(n),!0))}function Bt(t,e,n="",r={}){let o=(Array.isArray(e)?e:[]).map(p=>String(p?.id??"").trim()).filter(Boolean),a=o.length,i=t.length,c=a>0?"succeeded":"failed";return{status:c,stage:"product_overlay",reason:n||(c==="succeeded"?"":"no_matching_products_rendered"),evidence:{requested_product_count:i,rendered_product_count:a,missing_product_count:Math.max(i-a,0),requested_product_ids:t.slice(0,In).join(","),rendered_product_ids:o.slice(0,In).join(","),lookup_source:r.source||"",search_query:r.searchQuery||""}}}function ga(t){let e=String(t?.displayPrice||"").trim();if(e)return e;let n=Number(t?.price||0);return Number.isFinite(n)&&n>0?n.toLocaleString():"Price unavailable"}var ba=6,Ta=24,Aa=120;function Ea(t){let e=new Map;return Array.isArray(t)&&t.forEach(n=>{if(!n||typeof n!="object")return;let r=String(n.product_id||"").trim();if(!r||!Array.isArray(n.facts))return;let o=n.facts.filter(a=>a&&typeof a=="object"&&a.label&&a.value).slice(0,ba).map(a=>({label:String(a.label).slice(0,Ta),value:String(a.value).slice(0,Aa)}));o.length&&e.set(r,o)}),e}function Sa(t){let e=xn.get(String(t));return!e||!e.length?"":`<dl class="mayabot-product-facts">${e.map(r=>`<div class="mayabot-fact"><dt>${U(r.label)}</dt><dd>${U(r.value)}</dd></div>`).join("")}</dl>`}function lt(t,e){let n=pa(),r=n.querySelector(".mayabot-product-grid"),o=n.querySelector(".mayabot-product-title"),a=t.length;if(Yt=Array.isArray(t)?[...t]:[],$t=e||R,n.classList.remove("count-1","count-2","count-3","count-many"),n.classList.add(ha(a)),n.style.setProperty("--mayabot-card-count",String(ya(a))),o.textContent=$t,!a){r.innerHTML='<p class="mayabot-product-empty">No matching products are currently available.</p>',n.classList.add("active"),wn();return}r.innerHTML=t.map(i=>{let c=U(i.id);return`
        <article class="mayabot-product-card" data-product-id="${c}">
          <img class="mayabot-product-image" src="${U(i.imageUrl||la)}" alt="${U(i.name)}">
          <h3 class="mayabot-product-name">${U(i.name||i.title||"Product")}</h3>
          <p class="mayabot-product-meta">${U(i.brand)} - ${U(ga(i))}</p>
          ${Sa(i.id)}
          <div class="mayabot-product-actions">
            <button type="button" data-add="${c}">Add</button>
            <button type="button" class="secondary" data-view="${c}">View</button>
          </div>
        </article>
      `}).join(""),r.querySelectorAll("[data-add]").forEach(i=>{i.addEventListener("click",async()=>{await fa(i.getAttribute("data-add"))})}),r.querySelectorAll("[data-view]").forEach(i=>{i.addEventListener("click",async()=>{await ma(i.getAttribute("data-view"))})}),n.classList.add("active"),wn()}function wn(){window.setTimeout(()=>{let t=document.getElementById("mayabot-chat"),e=document.getElementById("mayabot-msgs");e&&(e.innerHTML=""),t&&t.classList.remove("visible")},H)}async function Rn(t,e=R,n={}){let r=_a(t),o=String(n.searchQuery||"").trim();if(xn=Ea(n.comparisonFacts),!r.length&&!o)return lt([],e),Bt([],[],"missing_product_ids");try{let{products:a,source:i,reason:c}=await En(r,o);return lt(a,e),Bt(r,a,c,{source:i,searchQuery:o})}catch(a){return console.warn("[AI Hub Widget] Product overlay failed:",a),lt([],e),Bt(r,[],"product_overlay_fetch_failed",{searchQuery:o})}}function Cn(t={}){if(!Yt.length)return!1;let e=String(t.sort_by||t.sortBy||"price_asc").trim().toLowerCase(),n=[...Yt].sort((r,o)=>Ia(r,o,e));return lt(n,wa($t,e)),!0}function Ia(t,e,n){return n==="price_desc"?Y(e.price,Number.NEGATIVE_INFINITY)-Y(t.price,Number.NEGATIVE_INFINITY):n==="rating"?Y(e.rating||e.review_rating,Number.NEGATIVE_INFINITY)-Y(t.rating||t.review_rating,Number.NEGATIVE_INFINITY):n==="newest"?On(e)-On(t):Y(t.price,Number.POSITIVE_INFINITY)-Y(e.price,Number.POSITIVE_INFINITY)}function Y(t,e){let n=String(t??"").replace(/,/g,"").match(/-?\d+(?:\.\d+)?/);if(!n)return e;let r=Number(n[0]);return Number.isFinite(r)?r:e}function On(t){let e=t?.updated_at||t?.created_at||t?.date||"",n=Date.parse(String(e||""));return Number.isFinite(n)?n:0}function wa(t,e){let n={price_asc:"sorted low to high",price_desc:"sorted high to low",rating:"sorted by rating",newest:"newest first"};return`${String(t||R).replace(/\s+-\s+sorted.*$/i,"")} - ${n[e]||n.price_asc}`}function Ln(t){return t.action===s.SHOW_PRODUCTS||t.action===s.SHOW_COMPARISON||t.action===s.SHOW_PRODUCT_DETAIL||t.action===s.SORT_PRODUCTS}async function Pn(t){return t.action===s.SHOW_COMPARISON?Nn(t.parameters||{},"Product comparison",{syncListing:!1,comparisonFacts:(t.parameters||{}).comparison}):t.action===s.SHOW_PRODUCTS?Nn(t.parameters||{},R):t.action===s.SHOW_PRODUCT_DETAIL?Ra(t.parameters||{}):t.action===s.SORT_PRODUCTS?Cn(t.parameters||{}):!1}async function Nn(t,e=R,n={}){let r=Array.isArray(t[l.PRODUCT_IDS])?t[l.PRODUCT_IDS]:[],o=xa(t),i=n.syncListing!==!1?await Oa(o):{succeeded:!1,handled:!1,status:"skipped",stage:"product_display_sync",reason:"comparison_overlay"},c=await Rn(r,t.title||o||e,{searchQuery:o,comparisonFacts:n.comparisonFacts}),p={...c.evidence||{},listing_sync_status:i.status||"",listing_sync_stage:i.stage||"",listing_sync_reason:i.reason||""};return c.status!=="succeeded"?{...c,evidence:p}:o&&i.handled&&!i.succeeded?{status:"failed",stage:"product_display_sync",reason:i.reason||i.status||"listing_sync_failed",evidence:p}:{...c,stage:i.succeeded?"product_display_sync":c.stage,evidence:p}}async function Oa(t){let e=vn(t);return e?Q({action:s.FILTER_PRODUCTS,params:{[l.SEARCH_QUERY]:e,query:e,q:e}}):{succeeded:!1,handled:!1,status:"skipped",stage:"product_display_sync",reason:"missing_search_query"}}function xa(t){return vn(t[l.SEARCH_QUERY]||t.search||t.query||t.q||"")}function vn(t){return String(t||"").trim()}async function Ra(t){let e="";try{e=await ut(t[l.PRODUCT_ID])}catch(n){return console.warn("[AI Hub Widget] Product detail URL lookup failed:",n),!1}return e?(window.location.href=e,!0):!1}var jt="stop_action_fallback",Ca=new Set([s.SHOW_PRODUCTS,s.SHOW_COMPARISON,s.SHOW_PRODUCT_DETAIL,s.SORT_PRODUCTS]);function Dn(t){return K()&&!Ca.has(t.action)}async function Un(t){let e=await Q(t);return e.succeeded?!0:e.blocked||e.disabled?jt:!1}function Mn(t){return window.dispatchEvent(new CustomEvent(V.MAYABOT_ACTION,{detail:t})),!0}var Na=Object.freeze([{name:"runtime_adapter",canExecute:Dn,execute:Un},{name:"product_overlay",canExecute:Ln,execute:Pn},{name:"entity_overlay",canExecute:Je,execute:Ze},{name:"handoff_overlay",canExecute:sn,execute:cn},{name:"platform_adapter",canExecute:()=>!0,execute:we},{name:"provider_adapter",canExecute:ke,execute:Fe},{name:"navigation",canExecute:ln,execute:dn},{name:"browser_event",canExecute:()=>!0,execute:Mn}]);async function Wt(t){let e=[];for(let n of t||[]){let r=mn(n),o=await La(r);o&&e.push(o)}return e}async function La(t){if(!t.action)return;let e=Date.now(),n=window.location.href;await nt(d.apiUrl,d.siteId,t,{status:"requested",stage:"widget_dispatch",requested_url:n,final_url:n,evidence:zt(t,n,n)}),await nt(d.apiUrl,d.siteId,t,{status:"executing",stage:"widget_dispatch",requested_url:n,final_url:window.location.href,evidence:zt(t,n,window.location.href)});let r;try{r=await Pa(t)}catch(i){r={status:"failed",stage:"widget_dispatch",reason:i instanceof Error?i.message:"execution_error"}}let o=window.location.href,a=zt(t,n,o,r);return await nt(d.apiUrl,d.siteId,t,{status:r.status,stage:r.stage,reason:r.reason,duration_ms:Date.now()-e,requested_url:n,final_url:o,evidence:a}),{action:t.action,request_id:t.request_id||t.action_request_id||"",turn_id:t.turn_id||"",sequence:Number(t.sequence||0),status:r.status,stage:r.stage,reason:r.reason,requested_url:n,final_url:o,evidence:a}}async function Pa(t){if(!t.action)return{status:"failed",stage:"normalization",reason:"missing_action"};for(let e of Na){if(!e.canExecute(t))continue;let n=await e.execute(t),r=va(n,e.name);if(r)return r}return{status:"failed",stage:"all",reason:"no_executor_succeeded"}}function va(t,e){if(t===!0)return{status:"succeeded",stage:e,reason:""};if(t===jt)return{status:"blocked",stage:e,reason:"action_blocked"};if(!t||typeof t!="object")return null;let n=String(t.status||"").trim().toLowerCase();return n?{status:n,stage:String(t.stage||e).trim()||e,reason:String(t.reason||"").trim(),evidence:t.evidence&&typeof t.evidence=="object"?t.evidence:{}}:null}function zt(t,e,n,r={}){let o=t.parameters||t.params||{},a={requested_url:e,final_url:n,url_changed:e!==n,path_changed:kn(e)!==kn(n),title:document.title||"",stage:r.stage||"",result_status:r.status||""};return o.page&&(a.target_page=o.page),o.product_id&&(a.product_id=o.product_id),o.entity_id&&(a.entity_id=o.entity_id),Array.isArray(o.product_ids)&&(a.product_count=o.product_ids.length),Array.isArray(o.entity_ids)&&(a.entity_count=o.entity_ids.length),{...a,...r.evidence&&typeof r.evidence=="object"?r.evidence:{}}}function kn(t){try{return new URL(t,window.location.href).pathname}catch{return""}}var Da=1,Ua=1.08,Ma=300,ka=Object.freeze(["hannah","sonia","libby","ava","susan","hazel","heera","salli","joanna","amy","emma","olivia","natasha","zira","aria","jenny","samantha","victoria","tessa","moira","karen","female","woman","nova","shimmer","google us english","microsoft aria"]),N="",dt="",X=null,Vt=0;function J(t){if(!("speechSynthesis"in window)||!("SpeechSynthesisUtterance"in window))return!1;pt();let e=++Vt;N=t;let n=()=>{if(e!==Vt||N!==t)return!1;try{let r=new SpeechSynthesisUtterance(t),o=Fa(window.speechSynthesis.getVoices());return o?(o&&(r.voice=o),r.rate=Da,r.pitch=Ua,r.onstart=Fn,r.onend=Fn,pt(),window.speechSynthesis.cancel(),window.speechSynthesis.resume(),window.speechSynthesis.speak(r),!0):(N="",!1)}catch{return!1}};return window.speechSynthesis.getVoices().length>0?n():(window.speechSynthesis.onvoiceschanged=n,X=window.setTimeout(()=>{X=null,n()},Ma),!0)}function ft(){N&&J(N)}function Hn(){try{return!!N||!!window.speechSynthesis?.speaking||!!window.speechSynthesis?.pending}catch{return!!N}}function Bn(){Vt+=1,pt(),N="",dt="";try{window.speechSynthesis?.cancel()}catch{}}function Fa(t){if(!Array.isArray(t)||t.length===0)return null;let e=Ha(t)||Ba(t);return e&&(dt=e.name),e}function Ha(t){if(dt){let n=t.find(r=>r.name===dt);if(n)return n}let e=String(d.speechVoiceName||"").toLowerCase();return e&&t.find(n=>n.name.toLowerCase()===e)||null}function Ba(t){return d.speechVoicePreference.toLowerCase()!=="female"?t.find(e=>e.default)||t[0]:t.find(e=>ka.some(n=>e.name.toLowerCase().includes(n)))||null}function Fn(){pt(),N=""}function pt(){X&&window.clearTimeout(X),X=null,window.speechSynthesis&&(window.speechSynthesis.onvoiceschanged=null)}var Ya=3,$a="AIHubAdapterRuntime",ja="AIHubAdapter";function za(t,e){let n=new URL(A.SHOP_WS,t);return n.protocol=n.protocol==="https:"?"wss:":"ws:",n.searchParams.set("site_id",e),n.searchParams.set("session_id",d.sessionId),n.toString()}function Wa(t){return new Promise((e,n)=>{let r=new FileReader;r.onloadend=()=>{let o=String(r.result||"");e(o.includes(",")?o.split(",").pop():o)},r.onerror=()=>n(r.error||new Error("Failed to read audio blob")),r.readAsDataURL(t)})}var Gt=class{constructor(){this.queue=[],this.blocked=[],this.playing=!1,this.current=null,this.lastPlaybackStartMs=0,this.installUnlockListeners()}push(e,n=""){e&&(this.queue.push({audioB64:e,fallbackText:n}),this.playNext())}playNext(){if(this.playing||this.queue.length===0)return;this.playing=!0;let e=this.queue.shift(),n=new Audio(W.DATA_WAV_PREFIX+e.audioB64);n.preload="auto",this.current=n,n.onplay=()=>{this.lastPlaybackStartMs=typeof performance<"u"?performance.now():0},n.onended=()=>{this.current=null,this.playing=!1,this.playNext()},n.onerror=()=>{this.current=null,e.fallbackText&&$(e.fallbackText),this.playing=!1,this.playNext()},n.play().catch(r=>{if(console.warn("Audio playback failed",r),this.current=null,this.isAutoplayBlocked(r)){e.fallbackText?$(e.fallbackText):this.blocked.unshift(e),this.playing=!1;return}e.fallbackText&&$(e.fallbackText),this.playing=!1,this.playNext()})}installUnlockListeners(){if(typeof window>"u")return;let e=()=>{this.retryBlocked(),ft()};window.addEventListener("pointerdown",e,{capture:!0,passive:!0}),window.addEventListener("keydown",e,{capture:!0}),window.addEventListener("touchstart",e,{capture:!0,passive:!0})}retryBlocked(){this.blocked.length&&(this.queue.unshift(...this.blocked.splice(0)),this.playNext())}speakInsteadOfBlocked(e){!e||!this.blocked.length||(this.blocked=[],$(e))}isAutoplayBlocked(e){let n=`${e?.name||""} ${e?.message||e||""}`.toLowerCase();return n.includes("notallowed")||n.includes("user didn't interact")||n.includes("not allowed")}stop(){if(this.queue=[],this.blocked=[],this.current){try{this.current.pause(),this.current.currentTime=0}catch{}this.current.onended=null,this.current.onerror=null,this.current=null}this.playing=!1,Bn()}isSpeaking(){return this.playing||this.queue.length>0||Hn()}},mt=new Gt;function Qt(){mt.stop()}function Yn(){return mt.isSpeaking()}var qt=class{async sendAudio(e,n,r=[]){let o=new FormData;o.append("audio",e,Ka(e)),o.append("site_id",d.siteId),o.append("session_id",d.sessionId),r&&r.length>0&&o.append("conversation_history",JSON.stringify(r));let a=zn();a&&o.append("page_context",JSON.stringify(a));let i=await fetch(`${d.apiUrl}${A.SHOP}`,{method:he.POST,body:o});if(!i.ok)throw new Error("AI Hub API request failed");let c=await i.json();if(c.transcript&&n.onUserMessage?.(c.transcript),c.response_text&&n.onAssistantMessage?.(c.response_text,c.ui_actions||[]),n.onStatusChange?.(f.READY),c.audio_b64?qa(c.audio_b64,c.response_text||""):c.response_text&&$(c.response_text),c.ui_actions&&c.ui_actions.length>0){let p=await Wt(c.ui_actions);n.onActionResults?.(p)}n.onComplete?.(c)}},Kt=class{constructor(){this.ws=null,this.connected=!1,this.connecting=null,this.failed=!1,this.retries=0,this.audioQueue=mt,this.callbacks=null,this.turnText="",this.receivedAudio=!1}async ensureConnected(e=[]){return this.canUseWebSocket()?this.isOpen()?!0:this.connecting?this.connecting:(this.connecting=this.openConnection(e),this.connecting):!1}canUseWebSocket(){return!this.failed&&d.useWebSocket&&"WebSocket"in window}isOpen(){return this.connected&&this.ws?.readyState===WebSocket.OPEN}openConnection(e=[]){return new Promise(n=>{let r=new WebSocket(za(d.apiUrl,d.siteId)),o=!1;this.ws=r;let a=(c=null)=>{o||(o=!0,this.markConnectionFailed(n,c,r))},i=window.setTimeout(()=>{a()},Ae);r.onopen=()=>{o||(o=!0,this.handleConnectionOpen(i,e,n))},r.onmessage=c=>{this.handleMessage(c).catch(p=>this.handleTransportError(p))},r.onerror=()=>a(i),r.onclose=()=>{this.connected=!1,a(i)}})}markConnectionOpen(){this.connected=!0,this.connecting=null,this.retries=0}handleConnectionOpen(e,n,r){window.clearTimeout(e),this.markConnectionOpen(),this.sendConfig(n),r(!0)}markConnectionFailed(e,n=null,r=null){n&&window.clearTimeout(n),this.connected=!1,this.connecting=null,this.retries+=1,this.retries>=Ya&&(this.failed=!0),r&&r.readyState!==WebSocket.CLOSED&&r.close(),e(!1)}sendConfig(e=[]){this.sendJson({type:E.CONFIG,history:e||[],session_id:d.sessionId,page_context:zn()})}sendJson(e){return!this.ws||this.ws.readyState!==WebSocket.OPEN?!1:(this.ws.send(JSON.stringify(e)),!0)}async sendAudio(e,n,r=[]){if(!await this.ensureConnected(r))return!1;this.callbacks=n,this.turnText="",this.receivedAudio=!1,this.sendConfig(r);let a=await Wa(e);return this.sendJson({type:E.AUDIO_CHUNK,data:a,mime_type:e?.type||""}),this.sendJson({type:E.AUDIO_END,mime_type:e?.type||""}),!0}async handleMessage(e){let n=this.callbacks;if(!n)return;let r=this.parseMessage(e.data);if(!r){this.completeWithError(n,"Invalid WebSocket message");return}if(!this.handleIncrementalMessage(r,n)){if(r.type===E.DONE){await this.handleDoneMessage(r,n);return}r.type===E.ERROR&&this.completeWithError(n,r.message||"WebSocket error")}}parseMessage(e){try{let n=JSON.parse(e);return n&&typeof n=="object"?n:null}catch{return null}}handleIncrementalMessage(e,n){return e.type===E.TRANSCRIPT?(n.onUserMessage?.(e.text||""),!0):e.type===E.TEXT_CHUNK?(this.turnText+=e.text||"",n.onAssistantChunk?.(e.text||"",this.turnText),!0):e.type===E.AUDIO_CHUNK?(this.receivedAudio=!!e.audio_b64||this.receivedAudio,this.audioQueue.push(e.audio_b64),!0):!1}async handleDoneMessage(e,n){let r=e.response_text||this.turnText;n.onAssistantMessage?.(r,e.ui_actions||[],{streamed:!0}),n.onStatusChange?.(f.READY),!this.receivedAudio&&r?$(r):this.receivedAudio&&r&&this.audioQueue.speakInsteadOfBlocked(r);try{if(e.ui_actions&&e.ui_actions.length>0){let o=await Wt(e.ui_actions);n.onActionResults?.(o)}n.onComplete?.(e)}catch(o){this.handleTransportError(o)}finally{this.callbacks=null}}completeWithError(e,n){e.onStatusChange?.(f.ERROR,jn(n)),e.onComplete?.({error:n}),this.callbacks=null}handleTransportError(e){console.error("AI Hub WebSocket transport failed",e);let n=this.callbacks;n&&this.completeWithError(n,String(e))}},Va=new qt,Ga=new Kt;async function $n(t,e,n,r=[]){try{if(d.useWebSocket&&await Ga.sendAudio(t,n,r))return;await Va.sendAudio(t,n,r)}catch(o){console.error(o),n.onStatusChange?.(f.ERROR,jn(o)),n.onComplete?.({error:String(o)})}}function qa(t,e=""){mt.push(t,e)}function Ka(t){let e=String(t?.type||"").toLowerCase();return e.includes("mp4")?"audio.mp4":e.includes("ogg")?"audio.ogg":e.includes("wav")?"audio.wav":W.WEBM_FILENAME}function jn(t){let e=String(t?.message||t||"").toLowerCase();return e.includes("quota")?"Quota reached":e.includes("microphone")||e.includes("permission")?"Mic unavailable":e.includes("voice")||e.includes("transcription")||e.includes("speech")?"Voice unavailable":e.includes("network")||e.includes("fetch")||e.includes("api request")?"Connection issue":"Try again"}function $(t){return t?J(String(t).slice(0,700)):!1}function zn(){let t=window[$a],e=window[ja];try{if(typeof t?.getContext=="function")return t.getContext();if(typeof e?.getContext=="function")return e.getContext()}catch(n){console.warn("[AI Hub Widget] Page context collection failed:",n)}return null}var Qa=4,Xa=40,Ja=24,Za=80,ti=120;function Vn(){let t=[];function e(n,r){let o=String(r||"").trim();o&&(t.push({role:n,content:o}),t.length>ye&&t.shift())}return{history:t,rememberUserMessage(n){e("user",n)},rememberAssistantMessage(n,r){e("assistant",ei(n,r))},rememberActionResults(n){let r=ri(n);r&&e("assistant",r)}}}function ei(t,e){let n=ni(e);return n.length?`${t} [PRODUCT_IDS: ${n.join(",")}]`:t}function ni(t){let e=[];for(let n of t||[]){let r=n.params||{};Wn(e,r[l.PRODUCT_IDS]),Wn(e,[r[l.PRODUCT_ID]])}return e}function Wn(t,e){for(let n of Array.isArray(e)?e:[])n&&!t.includes(n)&&t.push(n)}function ri(t){let e=(Array.isArray(t)?t:[]).map(oi).filter(Boolean).slice(0,Qa);return e.length?`[BROWSER_ACTION_RESULTS: ${e.join(" | ")}]`:""}function oi(t){if(!t||typeof t!="object"||!t.action)return"";let e=[ht(t.action,Xa),`status=${ht(t.status,Ja)||"unknown"}`],n=ii(t.final_url);return n&&e.push(`final_path=${ht(n,ti)}`),t.reason&&e.push(`reason=${ht(t.reason,Za)}`),ai(e,t.evidence),e.join(" ")}function ai(t,e={}){e.rendered_product_count!==void 0&&t.push(`rendered_products=${Number(e.rendered_product_count||0)}`),e.rendered_entity_count!==void 0&&t.push(`rendered_records=${Number(e.rendered_entity_count||0)}`)}function ht(t,e){return String(t||"").replace(/\s+/g," ").trim().slice(0,e)}function ii(t){try{let e=new URL(String(t||""),window.location.href);return`${e.pathname}${e.search}${e.hash}`}catch{return""}}var Gn=null;function Xt(t){Gn||(qn(t),Gn=window.setInterval(()=>qn(t),Te))}async function qn({boot:t,shutdownWidget:e}){try{if(await si()){t();return}e()}catch{t()}}async function si(){let t=new URL(A.WIDGET_STATUS,d.apiUrl);t.searchParams.set("site_id",d.siteId);let e=await fetch(t.toString(),{cache:"no-store",headers:{Accept:"application/json"}});return e.ok?(await e.json()).enabled!==!1:!0}var ci=280;window.__mayabot_identifier="voice-orb";var Jt=null,Zt=null;function Kn(){if(window.__mayabotBooted||document.getElementById("mayabot-widget"))return;window.__mayabotBooted=!0,re();let t=fe(),e=null,n=null,r=!1;function o(m=_e){e&&window.clearTimeout(e),e=window.setTimeout(()=>{t.msgs.innerHTML="",t.chat.classList.remove("visible"),e=null},m)}function a(m,O=""){r=m===f.RECORDING,t.status.className="",m===f.RECORDING?(e&&(window.clearTimeout(e),e=null),t.msgs.innerHTML="",t.btn.classList.add("recording"),t.chat.classList.add("visible"),t.status.innerText="Listening...",t.status.classList.add("listening")):m===f.PROCESSING?(t.btn.classList.remove("recording"),t.chat.classList.add("visible"),t.status.innerText="Analyzing...",t.status.classList.add("processing")):m===f.READY?(t.status.innerText="Ready",t.status.classList.add("ready")):m===f.ERROR&&(t.status.innerText=O||"Try again",t.status.classList.add("error"),t.btn.classList.remove("recording"))}let i=Vn(),c=null,p="",_=!1;async function L(m){if(!_){_=!0,t.btn.disabled=!0,c=null,p="";try{await $n(m,t,{onUserMessage:O=>{z(t,O,"user"),i.rememberUserMessage(O)},onAssistantChunk:(O,yt)=>{p=yt,c||(c=z(t,"","ai")),gt(t,c,p)},onAssistantMessage:(O,yt,Zn={})=>{Zn.streamed&&c?gt(t,c,O):z(t,O,"ai"),i.rememberAssistantMessage(O,yt),c=null,p=""},onActionResults:i.rememberActionResults,onStatusChange:a,onComplete:()=>o()},i.history)}finally{_=!1,t.btn.disabled=!1,c=null,p=""}}}let F=Ee(L,a);Jt=F;let P=null,g=0;function w(){P&&window.clearTimeout(P),P=null,g=0}function y(){return Yn()?(Qt(),a(f.READY),!0):!1}function te(){r||F.toggle()}function Jn(){if(_){y();return}if(r){F.toggle();return}y()||te()}t.btn.setAttribute("aria-label","Maya voice assistant. Double-click to talk; click to stop. Press Enter or Space to talk."),t.btn.setAttribute("title","Double-click to talk; click to stop"),t.btn.addEventListener("click",m=>{if(m.detail===0){Jn();return}if(_){y();return}if(r){w(),F.toggle();return}if(g+=1,g===1){y(),P=window.setTimeout(w,ci);return}w(),te()});let ee=m=>{m.key==="Escape"&&y()};document.addEventListener("keydown",ee);let ne=m=>{t.btn.contains(m.target)||ft()};document.addEventListener("pointerdown",ne,{capture:!0}),Zt=()=>{document.removeEventListener("keydown",ee),document.removeEventListener("pointerdown",ne,{capture:!0}),w(),e&&window.clearTimeout(e),e=null,n&&window.clearTimeout(n),n=null,Zt=null},ui()&&(li(),n=window.setTimeout(()=>{if(i.history.length>0)return;let m=`Welcome to ${d.brandName}. How can I help you today?`;z(t,m,"ai"),a(f.READY),o(be),J(m)},ge))}function Qn(){Jt?.cancel(),Jt=null,Zt?.(),Qt(),window.__mayabotBooted=!1,document.getElementById("mayabot-widget")?.remove(),document.getElementById("mayabot-product-panel")?.remove()}function ui(){if(!d.autoGreet||!di())return!1;try{return window.sessionStorage.getItem(Xn())!=="1"}catch{return!window.__mayabotAutoGreeted}}function li(){window.__mayabotAutoGreeted=!0;try{window.sessionStorage.setItem(Xn(),"1")}catch{}}function Xn(){return`mayabot:auto-greeted:${d.siteId}`}function di(){let t=window.location.pathname.replace(/\/+$/,"")||"/";return t==="/"||t.endsWith("/index.html")}document.readyState==="loading"?document.addEventListener("DOMContentLoaded",()=>Xt({boot:Kn,shutdownWidget:Qn})):Xt({boot:Kn,shutdownWidget:Qn});})();
