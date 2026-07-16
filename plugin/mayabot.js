(()=>{function Wt(){let t="#5d5fef",e=document.querySelector('meta[name="theme-color"]');if(e&&e.content)t=e.content;else{let h=document.querySelector('button[class*="primary"], .btn-primary, [data-primary]');if(h){let f=window.getComputedStyle(h).backgroundColor;f&&f!=="rgba(0, 0, 0, 0)"&&f!=="transparent"&&(t=f)}}let n=window.matchMedia&&window.matchMedia("(prefers-color-scheme: dark)").matches,r=n?"rgba(24, 24, 27, 0.75)":"rgba(255, 255, 255, 0.85)",o=n?"rgba(255, 255, 255, 0.1)":"rgba(0, 0, 0, 0.08)",a=n?"#f3f4f6":"#111827",i=n?"rgba(255, 255, 255, 0.1)":"rgba(0, 0, 0, 0.05)",c=n?"rgba(0, 0, 0, 0.25)":"#ffffff",p=document.createElement("style");p.textContent=`
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
    }

    #mayabot-btn {
      position: relative;
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
      transition: all 0.3s cubic-bezier(0.25, 1, 0.5, 1);
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
      transition: all 0.3s ease;
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
      box-shadow: 0 0 0 0 rgba(239, 68, 68, 0.7);
      animation: mayabotPulseRecord 1.5s infinite cubic-bezier(0.66, 0, 0, 1);
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
      transition: all 0.4s cubic-bezier(0.16, 1, 0.3, 1);
    }

    #mayabot-chat.visible {
      opacity: 1;
      pointer-events: all;
      visibility: visible;
      transform: translateY(0) scale(1);
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
      transition: all 0.3s ease;
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

    @keyframes mayabotPulseRecord {
      to { box-shadow: 0 0 0 24px rgba(239, 68, 68, 0); }
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
  `,document.head.appendChild(p)}var lt="site_1",Hn="__AI_";var Bn="aihub:auto-site-id:",Yn=["data-aihub-scope","data-site-scope"],$n=["data-site-id","data-aihub-site-id"];function _(t){return String(t||"").trim()}function B(t){return _(t).replace(/\/+$/,"")}function qt(t,e,n,r=lt){return zn(t,e,n)||jn()||_(r)||lt}function zn(t,e,n){for(let a of $n){let i=_(t?.getAttribute(a));if(i)return i}let r=_(e?.searchParams.get("site"))||_(e?.searchParams.get("site_id"))||_(e?.searchParams.get("shop"));if(r)return r;let o=_(n);return o&&!o.startsWith(Hn)?o:""}function jn(){let t=Wn(),e=`${Bn}${t}`,n=Zn(e);if(n){let c=Xn(n);return c!==n&&Vt(e,c),c}let r=_(window.location.host||window.location.hostname||"site"),o=Kt(),a=Qn(`${r}${o?`_${o.replace(/\//g,"_")}`:""}`),i=Qt(`auto_${a}_${Jn(t)}`);return Vt(e,i),i}function Wn(){return`${window.location.origin}${Kt()}`}function Kt(){return Gn()}function Gn(){for(let e of Yn){let n=_(Vn()?.getAttribute(e));if(n)return Gt(n)}let t=document.querySelector("meta[name='aihub-site-scope']")?.getAttribute("content");return Gt(t)}function Vn(){return document.currentScript}function Gt(t){let e=_(t);if(!e||e==="/")return"";try{let r=new URL(e,window.location.href);if(r.origin===window.location.origin){let[o]=qn(r.pathname);return o?`/${o}`:""}}catch{}let[n]=e.replace(/^\/+/,"").split("/");return n?`/${n}`:""}function qn(t=window.location.pathname){return _(t).split("/").map(e=>Kn(e).trim()).filter(Boolean)}function Kn(t){try{return decodeURIComponent(t)}catch{return String(t||"")}}function Qn(t){return _(t).toLowerCase().replace(/[^a-z0-9]+/g,"_").replace(/^_+|_+$/g,"")||"site"}function Qt(t){return _(t).slice(0,80).replace(/_+$/g,"")||lt}function Xn(t){let e=_(t);return e.startsWith("auto_")?Qt(e.toLowerCase().replace(/[^a-z0-9]+/g,"_").replace(/^_+|_+$/g,"")):e}function Jn(t){let e=2166136261,n=_(t);for(let r=0;r<n.length;r+=1)e^=n.charCodeAt(r),e=Math.imul(e,16777619);return(e>>>0).toString(36)}function Zn(t){try{return _(window.localStorage.getItem(t))}catch{return""}}function Vt(t,e){try{window.localStorage.setItem(t,e)}catch{}}var w=document.currentScript,Xt="__AI_PUBLIC_API_URL__",tr="__AI_DEFAULT_SITE_ID__",er="mayabot:session:",nr="Maya",rr="AI Salesperson",or="female";function C(t){return String(t||"").trim()}function ar(){let t=C(w?.getAttribute("src"));if(!t)return null;try{return new URL(t,window.location.href)}catch{return null}}function ir(t){let e=C(w?.getAttribute("data-api-url"));if(e)return B(e);if(!Xt.startsWith("__AI_"))return B(Xt);if(t?.origin){let n=t.pathname.replace(/\/mayabot(?:-widget)?\.js$/,"");return B(`${t.origin}${n}`)}return B(window.location.origin)}function sr(t){let e=`${er}${t}`;try{let n=window.sessionStorage.getItem(e);if(n)return n;let r=Jt(t);return window.sessionStorage.setItem(e,r),r}catch{return Jt(t)}}function Jt(t){let e=window.crypto?.randomUUID?.()||`${Date.now()}-${Math.random().toString(16).slice(2)}`;return`${t}-${e}`.slice(0,120)}var te=ar(),Zt=qt(w,te,tr),d={siteId:Zt,get sessionId(){return sr(Zt)},apiUrl:ir(te),useWebSocket:C(w?.getAttribute("data-use-websocket")).toLowerCase()==="true",autoGreet:C(w?.getAttribute("data-auto-greet")).toLowerCase()!=="false",brandName:C(w?.getAttribute("data-brand"))||nr,assistantTitle:C(w?.getAttribute("data-assistant-title"))||rr,speechVoiceName:C(w?.getAttribute("data-speech-voice")),speechVoicePreference:C(w?.getAttribute("data-speech-voice-preference"))||or};function ee(){let t=document.createElement("div");return t.id="mayabot-widget",t.innerHTML=`
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
  `,document.body.appendChild(t),t.querySelector(".mayabot-kicker").textContent=d.brandName,t.querySelector(".mayabot-title").textContent=d.assistantTitle,{btn:document.getElementById("mayabot-btn"),chat:document.getElementById("mayabot-chat"),msgs:document.getElementById("mayabot-msgs"),status:document.getElementById("mayabot-status")}}function Y(t,e,n){t.chat.classList.add("visible");let r=document.createElement("div");return r.className=`mayabot-msg ${n}`,r.innerText=e,t.msgs.appendChild(r),t.msgs.scrollTop=t.msgs.scrollHeight,r}function dt(t,e,n){e&&(e.innerText=n,t.msgs.scrollTop=t.msgs.scrollHeight)}var s=Object.freeze({ADD_TO_CART:"ADD_TO_CART",BOOK_APPOINTMENT_REQUEST:"BOOK_APPOINTMENT_REQUEST",BUILD_ITINERARY:"BUILD_ITINERARY",BUILD_LEARNING_PATH:"BUILD_LEARNING_PATH",CAPTURE_LEAD:"CAPTURE_LEAD",CAPTURE_PATIENT_LEAD:"CAPTURE_PATIENT_LEAD",CHECKOUT:"CHECKOUT",CHECKOUT_HANDOFF:"CHECKOUT_HANDOFF",CHECK_APPOINTMENT_AVAILABILITY:"CHECK_APPOINTMENT_AVAILABILITY",CHECK_AVAILABILITY:"CHECK_AVAILABILITY",CHECK_DELIVERY_AVAILABILITY:"CHECK_DELIVERY_AVAILABILITY",CHECK_ELIGIBILITY_SOFT:"CHECK_ELIGIBILITY_SOFT",CHECK_PREREQUISITES:"CHECK_PREREQUISITES",CLEAR_CART:"CLEAR_CART",CLEAR_FILTERS:"CLEAR_FILTERS",CLEAR_HISTORY:"CLEAR_HISTORY",COMPARE_ENTITIES:"COMPARE_ENTITIES",CONTACT_AGENT:"CONTACT_AGENT",FILTER_ENTITIES:"FILTER_ENTITIES",FILTER_PRODUCTS:"FILTER_PRODUCTS",HANDOFF_TO_ADVISOR:"HANDOFF_TO_ADVISOR",HANDOFF_TO_AGENT:"HANDOFF_TO_AGENT",HANDOFF_TO_CLINIC:"HANDOFF_TO_CLINIC",HANDOFF_TO_HUMAN:"HANDOFF_TO_HUMAN",HANDOFF_TO_LAWYER:"HANDOFF_TO_LAWYER",HANDOFF_TO_LICENSED_AGENT:"HANDOFF_TO_LICENSED_AGENT",HANDOFF_TO_RECRUITER:"HANDOFF_TO_RECRUITER",JOIN_WAITLIST:"JOIN_WAITLIST",MATCH_JOBS:"MATCH_JOBS",NAVIGATE_TO:"NAVIGATE_TO",OPEN_CLAIM_FLOW:"OPEN_CLAIM_FLOW",OPEN_CONTACT:"OPEN_CONTACT",OPEN_DISCLOSURE:"OPEN_DISCLOSURE",OPEN_ENTITY_DETAIL:"OPEN_ENTITY_DETAIL",OPEN_LOCATION:"OPEN_LOCATION",OPEN_MAP:"OPEN_MAP",OPEN_POLICY:"OPEN_POLICY",OPEN_PROJECTS:"OPEN_PROJECTS",OPEN_RENEWAL_FLOW:"OPEN_RENEWAL_FLOW",OPEN_SERVICES:"OPEN_SERVICES",OPEN_SYLLABUS:"OPEN_SYLLABUS",OPEN_TELECONSULT:"OPEN_TELECONSULT",REMOVE_FROM_CART:"REMOVE_FROM_CART",REQUEST_APPOINTMENT:"REQUEST_APPOINTMENT",REQUEST_CALLBACK:"REQUEST_CALLBACK",REQUEST_CONSULTATION:"REQUEST_CONSULTATION",REQUEST_COUNSELOR_CALLBACK:"REQUEST_COUNSELOR_CALLBACK",REQUEST_ESTIMATE:"REQUEST_ESTIMATE",REQUEST_SITE_VISIT:"REQUEST_SITE_VISIT",REQUEST_TEST_DRIVE:"REQUEST_TEST_DRIVE",REQUEST_VIEWING:"REQUEST_VIEWING",RUN_AFFORDABILITY_CALCULATOR:"RUN_AFFORDABILITY_CALCULATOR",RUN_CALCULATOR:"RUN_CALCULATOR",RUN_DOM_SEQUENCE:"RUN_DOM_SEQUENCE",SAVE_SEARCH:"SAVE_SEARCH",SCHEDULE_ORDER:"SCHEDULE_ORDER",SEARCH_AVAILABILITY:"SEARCH_AVAILABILITY",SET_LOCATION:"SET_LOCATION",SHOW_COMPARISON:"SHOW_COMPARISON",SHOW_EMERGENCY_NOTICE:"SHOW_EMERGENCY_NOTICE",SHOW_ENTITIES:"SHOW_ENTITIES",SHOW_PRODUCT_DETAIL:"SHOW_PRODUCT_DETAIL",SHOW_PRODUCTS:"SHOW_PRODUCTS",SORT_ENTITIES:"SORT_ENTITIES",SORT_PRODUCTS:"SORT_PRODUCTS",START_APPLICATION:"START_APPLICATION",START_BOOKING:"START_BOOKING",START_ENROLLMENT:"START_ENROLLMENT",START_INTAKE:"START_INTAKE",START_QUOTE:"START_QUOTE",START_TICKET_PURCHASE:"START_TICKET_PURCHASE",UPDATE_CART_QUANTITY:"UPDATE_CART_QUANTITY",UPDATE_PREFERENCES:"UPDATE_PREFERENCES"}),l=Object.freeze({ENTITY_ID:"entity_id",ENTITY_IDS:"entity_ids",MESSAGE:"message",PAGE:"page",PRODUCT_ID:"product_id",PRODUCT_IDS:"product_ids",QUANTITY:"quantity",REASON:"reason",SEARCH_QUERY:"search_query",URL:"url"}),Za=Object.freeze({BLOCKED:"blocked",EXECUTING:"executing",FAILED:"failed",REQUESTED:"requested",SKIPPED:"skipped",SUCCEEDED:"succeeded",UNKNOWN:"unknown"}),A=Object.freeze({KNOWLEDGE_BY_IDS:"/v1/knowledge/by-ids",PRODUCTS_BY_IDS:"/v1/products/by-ids",SHOP:"/v1/shop",SHOP_WS:"/v1/ws/shop",WIDGET_STATUS:"/v1/widget/status"}),E=Object.freeze({AUDIO_CHUNK:"audio_chunk",AUDIO_END:"audio_end",CONFIG:"config",DONE:"done",ERROR:"error",TEXT_CHUNK:"text_chunk",TRANSCRIPT:"transcript"});var ne=new Set(["cart","/cart"]),x="Recommended products",N="Relevant options",$=Object.freeze({DATA_WAV_PREFIX:"data:audio/wav;base64,",WEBM_FILENAME:"audio.webm",WEBM_MIME_TYPE:"audio/webm"}),re=Object.freeze({POST:"POST"}),m=Object.freeze({ERROR:"error",PROCESSING:"processing",READY:"ready",RECORDING:"recording"}),oe=12,ae=2400,ie=900,se=4200,pt=1,U=180,ce=3e3,z=Object.freeze({MAYABOT_ACTION:"mayabot:action"}),ue=2500;var cr=["audio/webm;codecs=opus","audio/webm","audio/ogg;codecs=opus","audio/ogg","audio/mp4"],ur=250,lr=128;function le(t,e){let n=null,r=null,o=[],a=!1,i=!1,c=!1;async function p(){if(!(i||a)){i=!0;try{let y=await navigator.mediaDevices.getUserMedia({audio:!0});r=y,c=!1;let K=dr();n=new MediaRecorder(y,K?{mimeType:K}:void 0),o=[],n.ondataavailable=O=>{O.data.size>0&&o.push(O.data)},n.onstop=async()=>{let O=new Blob(o,{type:n.mimeType||K||$.WEBM_MIME_TYPE});if(L(),c){c=!1;return}if(O.size<lr){console.warn("Microphone recording was empty or too short",{size:O.size}),e(m.READY);return}await t(O)},n.onerror=O=>{console.error("Microphone recording failed",O.error||O),a=!1,i=!1,L(),e(m.ERROR,"Recording failed")},n.start(ur),a=!0,e(m.RECORDING)}catch(y){console.error("Microphone access denied",y),e(m.ERROR,"Mic unavailable")}finally{i=!1}}}function h({discard:y=!1}={}){if(c=y,n&&n.state!=="inactive"){try{n.requestData()}catch{}n.stop(),a=!1,y||e(m.PROCESSING);return}a=!1,L(),y||e(m.PROCESSING)}function f(){i||(a?h():p())}function g(){h({discard:!0})}function L(){r&&(r.getTracks().forEach(y=>y.stop()),r=null)}return{toggle:f,cancel:g}}function dr(){return!("MediaRecorder"in window)||typeof MediaRecorder.isTypeSupported!="function"?"":cr.find(t=>MediaRecorder.isTypeSupported(t))||""}var de="shopify",pe="woocommerce",pr="custom";function Q(t){let e=String(t||"").trim();return/^\d+$/.test(e)?e:""}function X(t,e=1){let n=Number(t?.[l.QUANTITY]);return Number.isFinite(n)&&n>0?Math.floor(n):e}async function P(t,e){return(await fetch(new URL(t,window.location.origin),{method:"POST",headers:{Accept:"application/json","Content-Type":"application/json"},body:JSON.stringify(e),credentials:"same-origin"})).ok}function fr(){return mr()?de:_r()?pe:pr}async function fe(t){let e=fr();return e===de?yr(t):e===pe?hr(t):!1}function mr(){return!!(window.Shopify||document.querySelector('meta[name="shopify-checkout-api-token"]')||document.querySelector('script[src*="cdn.shopify.com"]'))}function _r(){return!!(document.body?.classList?.contains("woocommerce")||window.wc_add_to_cart_params||document.querySelector('link[href*="woocommerce"], script[src*="woocommerce"]'))}async function yr(t){let e=t.parameters||{};if(t.action===s.ADD_TO_CART){let n=Q(e.variant_id||e.cart_id||e[l.PRODUCT_ID]);return n?P("/cart/add.js",{items:[{id:n,quantity:X(e)}]}):!1}if(t.action===s.REMOVE_FROM_CART){let n=Q(e.cart_id||e.variant_id||e[l.PRODUCT_ID]);return n?P("/cart/change.js",{id:n,quantity:0}):!1}if(t.action===s.UPDATE_CART_QUANTITY){let n=Q(e.cart_id||e.variant_id||e[l.PRODUCT_ID]);return n?P("/cart/change.js",{id:n,quantity:X(e,0)}):!1}return t.action===s.CLEAR_CART?P("/cart/clear.js",{}):t.action===s.CHECKOUT?J("/checkout"):me(t)?J("/cart"):!1}async function hr(t){let e=t.parameters||{};if(t.action===s.ADD_TO_CART){let n=Q(e.variant_id||e.cart_id||e[l.PRODUCT_ID]);return n?P("/wp-json/wc/store/cart/add-item",{id:Number(n),quantity:X(e)}):!1}if(t.action===s.REMOVE_FROM_CART){let n=String(e.cart_key||e.key||"").trim();return n?P("/wp-json/wc/store/cart/remove-item",{key:n}):!1}if(t.action===s.UPDATE_CART_QUANTITY){let n=String(e.cart_key||e.key||"").trim();return n?P("/wp-json/wc/store/cart/update-item",{key:n,quantity:X(e,0)}):!1}return t.action===s.CHECKOUT?J("/checkout"):me(t)?J("/cart"):!1}function me(t){return t.action===s.NAVIGATE_TO&&ne.has(t.parameters?.[l.PAGE])}function J(t){return window.location.href=t,!0}var gr="/v1/widget/action-event";function b(t){return String(t||"").trim()}function br(t,e){return new URL(t,e).toString()}function Tr(t){return!t||typeof t!="object"?[]:Object.keys(t).map(e=>b(e)).filter(Boolean).slice(0,20)}function Ar(t){if(!t||typeof t!="object")return{};let e={};for(let[n,r]of Object.entries(t).slice(0,20)){let o=b(n).slice(0,80);o&&(typeof r=="boolean"||r===null?e[o]=r:typeof r=="number"?e[o]=Number.isFinite(r)?r:0:e[o]=b(r).slice(0,240))}return e}async function Z(t,e,n,r){if(!t||!e||!n?.action)return;let o=JSON.stringify({site_id:e,origin:window.location.origin,url:window.location.href,occurred_at:new Date().toISOString(),request_id:b(n.request_id||n.action_request_id),turn_id:b(n.turn_id),sequence:Number(n.sequence||0),action:b(n.action).toUpperCase(),status:b(r?.status)||"unknown",stage:b(r?.stage),reason:b(r?.reason),duration_ms:Number(r?.duration_ms||0),param_keys:Tr(n.parameters||n.params),requested_url:b(r?.requested_url),final_url:b(r?.final_url||window.location.href),evidence:Ar(r?.evidence)}),a=br(gr,t);if(!Er(a,o))try{await fetch(a,{method:"POST",headers:{Accept:"application/json","Content-Type":"application/json"},body:o,keepalive:!0})}catch(i){console.warn("[AIHubAdapter] Action execution report failed.",i)}}function Er(t,e){if(typeof navigator>"u"||typeof navigator.sendBeacon!="function"||typeof Blob!="function")return!1;try{return navigator.sendBeacon(t,new Blob([e],{type:"application/json"}))}catch{return!1}}function _e(t){if(!t||typeof t!="string")return[];let e=[];for(let n of Sr()){try{e.push(...Array.from(n.querySelectorAll(t)))}catch{return[]}if(e.length>=600)return e.slice(0,600)}return xr(e)}function Sr(){let t=[],e=new Set,n=[document];for(;n.length&&t.length<60;){let r=n.shift();!r||e.has(r)||(e.add(r),t.push(r),n.push(...Ir(r)))}return t}function Ir(t){let e=[];for(let n of Or(t)){n.shadowRoot&&e.push(n.shadowRoot);let r=wr(n);r&&e.push(r)}return e}function Or(t){try{return Array.from(t.querySelectorAll("*"))}catch{return[]}}function wr(t){if(String(t?.tagName||"").toLowerCase()!=="iframe")return null;try{let e=t.contentDocument;return e?.documentElement?e:null}catch{return null}}function xr(t){return Array.from(new Set(t))}var ui=Object.freeze([u("stripe",["stripe","stripe.com","checkout.stripe.com","js.stripe.com"]),u("paypal",["paypal","paypal.com","paypalobjects.com"]),u("razorpay",["razorpay","checkout.razorpay.com"]),u("paytm",["paytm","securegw.paytm.in"]),u("cashfree",["cashfree","cashfree.com"]),u("checkout.com",["checkout.com","cko-session-id"]),u("adyen",["adyen","checkoutshopper"]),u("square",["squareup","squarecdn","square.site"]),u("braintree",["braintree","braintreegateway"]),u("mollie",["mollie","mollie.com"]),u("klarna",["klarna","klarna.com"]),u("afterpay",["afterpay","afterpay.com","clearpay"]),u("payu",["payu","payu.in","payu.com"]),u("paystack",["paystack","paystack.co"]),u("phonepe",["phonepe","phonepe.com"]),u("billdesk",["billdesk","billdesk.com"]),u("authorize.net",["authorize.net","accept.authorize.net"])]),ye=Object.freeze([u("calendly",["calendly","calendly.com"]),u("acuity",["acuityscheduling","squarespace scheduling"]),u("booksy",["booksy","booksy.com"]),u("zocdoc",["zocdoc","zocdoc.com"]),u("appointlet",["appointlet","appointlet.com"]),u("setmore",["setmore","setmore.com"]),u("cal.com",["cal.com","calcom"]),u("google_calendar",["calendar.google.com","google calendar"]),u("microsoft_bookings",["microsoft bookings","outlook.office365.com/book"]),u("simplybook",["simplybook","simplybook.me"]),u("tidycal",["tidycal","tidycal.com"]),u("savvycal",["savvycal","savvycal.com"]),u("fresha",["fresha","fresha.com"])]),he=Object.freeze([u("google_maps",["google.com/maps","maps.googleapis","maps.google"]),u("mapbox",["mapbox","mapbox.com"]),u("openstreetmap",["openstreetmap","osm.org"]),u("leaflet",["leaflet","leafletjs"]),u("here_maps",["here.com","hereapi","wego.here.com"]),u("bing_maps",["bing.com/maps","virtualearth"]),u("mappls",["mappls","mapmyindia"])]),ge=Object.freeze([u("whatsapp",["wa.me","api.whatsapp.com","web.whatsapp.com"]),u("telegram",["t.me/","telegram.me"]),u("messenger",["m.me/","messenger.com/t"]),u("zendesk",["zendesk.com","zdassets.com/hc"]),u("intercom",["intercom.help","intercom.com"]),u("freshchat",["freshchat.com"])]),li=Object.freeze([u("recaptcha",["recaptcha","g-recaptcha","google.com/recaptcha"]),u("hcaptcha",["hcaptcha","h-captcha"]),u("turnstile",["turnstile","challenges.cloudflare.com"]),u("cloudflare_challenge",["cf-chl","cloudflare challenge"])]);function u(t,e){return{name:t,tokens:e}}function ft(t,e,n=10){let r=mt(t);return e.filter(o=>o.tokens.some(a=>r.includes(a))).map(o=>o.name).slice(0,n)}function mt(t){return String(t||"").replace(/\s+/g," ").trim().toLowerCase()}var be="a[href], iframe[src]",Rr="a[href]",Ae=new Set(["http:","https:"]),tt=new Set(["mailto:","tel:"]),Cr=Object.freeze([l.URL,"href","link","target_url","provider_url","booking_url","appointment_url","calendar_url","map_url","location_url","contact_url"]),Ee=new Set([s.OPEN_MAP,s.OPEN_LOCATION,s.SET_LOCATION]),Se=new Set([s.CHECK_APPOINTMENT_AVAILABILITY,s.REQUEST_APPOINTMENT,s.BOOK_APPOINTMENT_REQUEST,s.REQUEST_CONSULTATION,s.REQUEST_SITE_VISIT,s.START_BOOKING]),Ie=new Set([s.OPEN_CONTACT,s.CONTACT_AGENT,s.REQUEST_CALLBACK,s.REQUEST_COUNSELOR_CALLBACK,s.HANDOFF_TO_ADVISOR,s.HANDOFF_TO_AGENT,s.HANDOFF_TO_CLINIC,s.HANDOFF_TO_HUMAN,s.HANDOFF_TO_LAWYER,s.HANDOFF_TO_LICENSED_AGENT,s.HANDOFF_TO_RECRUITER]);function Oe(t){let e=Re(t);return Ee.has(e)||Se.has(e)||Ie.has(e)}async function we(t){let e=Re(t);return Ee.has(e)?_t(t,he,be,yt):Se.has(e)?_t(t,ye,be,yt):Ie.has(e)?_t(t,ge,Rr,vr):!1}function _t(t,e,n,r){let o=Nr(t?.parameters||t?.params||{},e,r);if(o)return Te(o);let a=Lr(n,e,r);return a?Te(a):!1}function Nr(t,e,n){for(let r of Cr){let o=xe(t?.[r]);if(o&&n(o,e))return o}return null}function Lr(t,e,n){for(let r of _e(t)){let o=Pr(r);if(!(!o||!n(o,e))&&Dr(o,r,e))return o}return null}function Pr(t){return xe(t?.getAttribute?.("href")||t?.getAttribute?.("src"))}function yt(t,e){return Ae.has(t.protocol)&&ft(t.href,e).length>0}function vr(t,e){return tt.has(t.protocol)?!0:yt(t,e)}function Dr(t,e,n){if(tt.has(t.protocol))return!0;let r=[t.href,e?.textContent||"",e?.getAttribute?.("aria-label")||"",e?.getAttribute?.("title")||""].join(" ");return ft(mt(r),n).length>0}function Te(t){if(tt.has(t.protocol)||t.origin===window.location.origin)return window.location.href=t.href,!0;let e=window.open(t.href,"_blank","noopener,noreferrer");return e?(e.opener=null,!0):(window.location.href=t.href,!0)}function xe(t){let e=String(t||"").trim();if(!e||e.startsWith("#"))return null;try{let n=new URL(e,window.location.href);return Ae.has(n.protocol)||tt.has(n.protocol)?n:null}catch{return null}}function Re(t){return String(t?.action||"").trim().toUpperCase()}var Ur=Object.freeze(["title","name"]),Mr=Object.freeze(["summary","description","body"]),kr=Object.freeze(["image_url","imageUrl","image","thumbnail"]),Fr=Object.freeze(["url","href","permalink","source_url"]),Hr="knowledge_item",Br=30;function S(t){return t==null||typeof t=="object"?"":String(t||"").trim()}function Yr(t){let e=new Set;return(Array.isArray(t)?t:[]).map(S).filter(Boolean).filter(n=>e.has(n)||e.size>=Br?!1:(e.add(n),!0))}function et(t,e){for(let n of e){let r=S(t?.[n]);if(r)return r}return""}function j(t){return t&&typeof t=="object"&&!Array.isArray(t)?t:{}}function $r(t){let e=zr([t?.price,t?.amount,t?.premium,t?.premium_min,t?.monthly_premium,t?.annual_premium,t?.min_price,t?.starting_price]),n=S(t?.currency||"INR");return!Number.isFinite(e)||e<=0?"":`${n} ${e.toLocaleString()}`}function zr(t){for(let e of t){let n=Number(String(e??"").replace(/,/g,""));if(Number.isFinite(n)&&n>0)return n}return 0}function jr(t){return!t||typeof t!="object"?"":t.in_stock===!0?"Available":t.in_stock===!1?"Unavailable":S(t.status||t.availability||"")}function Wr(t){let e=S(t);if(!e)return"";try{let n=new URL(e,window.location.origin);return/^https?:$/i.test(n.protocol)?n.origin===window.location.origin?`${n.pathname}${n.search}${n.hash}`:n.toString():""}catch{return""}}function Gr(t){if(!t)return null;let e=S(t.id);if(!e)return null;let n=j(t.pricing),r=j(t.availability);return{id:e,externalId:S(t.external_id),entityType:S(t.entity_type||t.category_name)||Hr,title:et(t,Ur)||e,subtitle:S(t.subtitle||t.category_name||t.entity_type),summary:et(t,Mr),body:S(t.body),url:Wr(et(t,Fr)),imageUrl:et(t,kr),attributes:j(t.attributes),pricing:n,availability:r,location:j(t.location),contact:j(t.contact),displayPrice:$r(n),displayAvailability:jr(r)}}async function ht(t){let e=Yr(t);if(!e.length)return[];let n=new URL(A.KNOWLEDGE_BY_IDS,d.apiUrl);n.searchParams.set("site_id",d.siteId),n.searchParams.set("ids",e.join(","));let r=await fetch(n.toString(),{headers:{Accept:"application/json"}});if(!r.ok)throw new Error("Failed to fetch entities from AI Hub API");let o=(await r.json()).map(Gr).filter(Boolean),a=new Map(o.map(i=>[String(i.id),i]));return e.map(i=>a.get(i)).filter(Boolean)}async function Ce(t){let[e]=await ht([t]);return e?.url||""}function Ne(){if(document.getElementById("mayabot-entity-overlay-styles"))return;let t=document.createElement("style");t.id="mayabot-entity-overlay-styles",t.textContent=`
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
  `,document.head.appendChild(t)}var Vr=2,Le=Number.POSITIVE_INFINITY,nt=Number.NEGATIVE_INFINITY,Pe=12,bt=[],Tt=N;function R(t){return String(t??"").replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;").replace(/"/g,"&quot;").replace(/'/g,"&#039;")}function Me(t){return String(t||"item").replace(/[_-]+/g," ").trim().split(/\s+/).slice(0,Vr).join(" ")}function qr(){Ne();let t=document.getElementById("mayabot-entity-panel");return t||(t=document.createElement("div"),t.id="mayabot-entity-panel",t.setAttribute("aria-live","polite"),t.innerHTML=`
    <div class="mayabot-entity-header">
      <h2 class="mayabot-entity-title">${N}</h2>
      <button class="mayabot-entity-close" type="button" aria-label="Close recommendations">&times;</button>
    </div>
    <div class="mayabot-entity-grid"></div>
  `,t.querySelector(".mayabot-entity-close").addEventListener("click",()=>{t.classList.remove("active")}),document.body.appendChild(t),t)}function Kr(t){return t<=1?"count-1":t===2?"count-2":t===3?"count-3":"count-many"}function Qr(t){return t<=1?1:t===2?2:3}function gt(t,e,n=""){let r=(Array.isArray(e)?e:[]).map(c=>String(c?.id??"").trim()).filter(Boolean),o=r.length,a=t.length,i=o>0?"succeeded":"failed";return{status:i,stage:"entity_overlay",reason:n||(i==="succeeded"?"":"no_matching_entities_rendered"),evidence:{requested_entity_count:a,rendered_entity_count:o,missing_entity_count:Math.max(a-o,0),requested_entity_ids:t.slice(0,Pe).join(","),rendered_entity_ids:r.slice(0,Pe).join(",")}}}function Xr(t){return[t.displayPrice,t.displayAvailability,t.location?.city,t.attributes?.category].map(e=>String(e||"").trim()).filter(Boolean).slice(0,3)}function Jr(t){return t.imageUrl?`
      <div class="mayabot-entity-media">
        <img src="${R(t.imageUrl)}" alt="${R(t.title)}">
      </div>
    `:`
    <div class="mayabot-entity-media">
      <div class="mayabot-entity-badge">${R(Me(t.entityType))}</div>
    </div>
  `}function Zr(t){let e=Xr(t);return e.length?`
    <div class="mayabot-entity-facts">
      ${e.map(n=>`<span class="mayabot-entity-fact">${R(n)}</span>`).join("")}
    </div>
  `:""}function to(t){return t.url?`
    <div class="mayabot-entity-actions">
      <button type="button" data-view-entity="${R(t.id)}">Open</button>
    </div>
  `:""}function ot(t,e){let n=qr(),r=n.querySelector(".mayabot-entity-grid"),o=n.querySelector(".mayabot-entity-title"),a=t.length;if(bt=Array.isArray(t)?[...t]:[],Tt=e||N,n.classList.remove("count-1","count-2","count-3","count-many"),n.classList.add(Kr(a)),n.style.setProperty("--mayabot-entity-card-count",String(Qr(a))),o.textContent=Tt,!a){r.innerHTML='<p class="mayabot-entity-empty">No matching records are currently available.</p>',n.classList.add("active"),ve();return}r.innerHTML=t.map(i=>`
        <article class="mayabot-entity-card" data-entity-id="${R(i.id)}">
          ${Jr(i)}
          <h3 class="mayabot-entity-name">${R(i.title)}</h3>
          <p class="mayabot-entity-meta">${R(i.subtitle||Me(i.entityType))}</p>
          <p class="mayabot-entity-summary">${R(i.summary||i.body||"Details are available on the website.")}</p>
          ${Zr(i)}
          ${to(i)}
        </article>
      `).join(""),r.querySelectorAll("[data-view-entity]").forEach(i=>{i.addEventListener("click",async()=>{await At(i.getAttribute("data-view-entity"))})}),n.classList.add("active"),ve()}function eo(t){if(!t)return!1;try{let e=new URL(t,window.location.origin);return e.origin===window.location.origin?(window.location.href=`${e.pathname}${e.search}${e.hash}`,!0):(window.open(e.toString(),"_blank","noopener,noreferrer"),!0)}catch{return!1}}function ve(){window.setTimeout(()=>{let t=document.getElementById("mayabot-chat"),e=document.getElementById("mayabot-msgs");e&&(e.innerHTML=""),t&&t.classList.remove("visible")},U)}async function At(t){let e=await Ce(t);return eo(e)}async function ke(t,e=N){let n=Et({[l.ENTITY_IDS]:t});if(!n.length)return ot([],e),gt([],[],"missing_entity_ids");try{let r=await ht(n);return ot(r,e),gt(n,r)}catch(r){return console.warn("[AI Hub Widget] Entity overlay failed:",r),ot([],e),gt(n,[],"entity_overlay_fetch_failed")}}function Et(t){let e=t[l.ENTITY_IDS]||t.ids||t.items||[],n=new Set;return(Array.isArray(e)?e:[]).map(r=>String(r??"").trim()).filter(Boolean).filter(r=>n.has(r)?!1:(n.add(r),!0))}function Fe(t={}){if(!bt.length)return!1;let e=String(t.sort_by||t.sortBy||"price_asc").trim().toLowerCase(),n=[...bt].sort((o,a)=>no(o,a,e)),r=oo(Tt,e);return ot(n,r),!0}function no(t,e,n){return n==="price_desc"?rt(e,nt)-rt(t,nt):n==="rating"?De(e,nt)-De(t,nt):n==="newest"?Ue(e)-Ue(t):rt(t,Le)-rt(e,Le)}function rt(t,e){return He([t?.pricing?.price,t?.pricing?.amount,t?.pricing?.premium,t?.pricing?.premium_min,t?.pricing?.monthly_premium,t?.pricing?.annual_premium,t?.pricing?.min_price,t?.pricing?.starting_price,t?.attributes?.price,t?.attributes?.amount,t?.attributes?.premium,t?.attributes?.monthly_premium,t?.attributes?.annual_premium,t?.displayPrice],e)}function De(t,e){return He([t?.attributes?.rating,t?.attributes?.review_rating,t?.attributes?.stars,t?.availability?.rating],e)}function Ue(t){let e=t?.attributes?.updated_at||t?.attributes?.date||t?.availability?.updated_at||"",n=Date.parse(String(e||""));return Number.isFinite(n)?n:0}function He(t,e){for(let n of t){let r=ro(n);if(Number.isFinite(r))return r}return e}function ro(t){if(typeof t=="number")return t;let e=String(t??"").replace(/,/g,"").match(/-?\d+(?:\.\d+)?/);return e?Number(e[0]):Number.NaN}function oo(t,e){let n={price_asc:"sorted low to high",price_desc:"sorted high to low",rating:"sorted by rating",newest:"newest first"};return`${String(t||N).replace(/\s+-\s+sorted.*$/i,"")} - ${n[e]||n.price_asc}`}function Be(t){return t.action===s.SHOW_ENTITIES||t.action===s.COMPARE_ENTITIES||t.action===s.OPEN_ENTITY_DETAIL||t.action===s.SORT_ENTITIES}async function Ye(t){return t.action===s.SHOW_ENTITIES||t.action===s.COMPARE_ENTITIES?ao(t.parameters||{}):t.action===s.OPEN_ENTITY_DETAIL?At(t.parameters?.[l.ENTITY_ID]||t.parameters?.id):t.action===s.SORT_ENTITIES?Fe(t.parameters||{}):!1}function ao(t){return ke(Et(t),t[l.SEARCH_QUERY]||t.title||N)}var W="mayabot-handoff-panel",$e="mayabot-handoff-overlay-styles",io=Object.freeze(["contact","support","help"]),so=Object.freeze(["checkout","cart"]),Ge=new Set([s.CHECKOUT_HANDOFF,s.HANDOFF_TO_ADVISOR,s.HANDOFF_TO_AGENT,s.HANDOFF_TO_CLINIC,s.HANDOFF_TO_HUMAN,s.HANDOFF_TO_LAWYER,s.HANDOFF_TO_LICENSED_AGENT,s.HANDOFF_TO_RECRUITER]),ze=Object.freeze({[s.CHECKOUT_HANDOFF]:{title:"Checkout needs your confirmation",body:"This step may include payment or a secure checkout page. I can take you there, then you complete the final step yourself.",primary:"Open checkout"},[s.HANDOFF_TO_ADVISOR]:{title:"Advisor handoff",body:"This request needs a qualified advisor. I can open the contact path so the site team can continue.",primary:"Contact advisor"},[s.HANDOFF_TO_AGENT]:{title:"Agent handoff",body:"This step needs an agent or account-specific help. I can open the contact path for follow-up.",primary:"Contact agent"},[s.HANDOFF_TO_CLINIC]:{title:"Clinic handoff",body:"This request needs clinic confirmation. I can open the appointment or contact path for the next step.",primary:"Contact clinic"},[s.HANDOFF_TO_HUMAN]:{title:"Human handoff",body:"This step needs human confirmation. I can open the most relevant contact path.",primary:"Open contact"},[s.HANDOFF_TO_LAWYER]:{title:"Legal handoff",body:"This request needs a legal professional. I can open the consultation or contact path.",primary:"Contact lawyer"},[s.HANDOFF_TO_LICENSED_AGENT]:{title:"Licensed agent handoff",body:"This request needs a licensed agent. I can open the quote or contact path for follow-up.",primary:"Contact agent"},[s.HANDOFF_TO_RECRUITER]:{title:"Recruiter handoff",body:"This request needs recruiter review. I can open the application or contact path.",primary:"Contact recruiter"}});function M(t){return String(t??"").replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;").replace(/"/g,"&quot;").replace(/'/g,"&#039;")}function v(t){return String(t||"").trim()}function co(){if(document.getElementById($e))return;let t=document.createElement("style");t.id=$e,t.textContent=`
    #${W} {
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
    #${W}.active {
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
      #${W} {
        bottom: 82px;
        width: min(calc(100vw - 20px), 420px);
      }
    }
  `,document.head.appendChild(t)}function uo(){co();let t=document.getElementById(W);return t||(t=document.createElement("div"),t.id=W,t.setAttribute("aria-live","polite"),document.body.appendChild(t),t)}function lo(){return window.AIHubAdapterRuntime?.config?.adapter?.routes||window.AIHubAdapter?.config?.adapter?.routes||{}}function po(t,e){let n=je(e[l.URL]||e.path||e.href||e.handoff_flow?.page_url);if(n)return n;let r=lo(),o=t===s.CHECKOUT_HANDOFF?so:io;for(let a of o){let i=je(r[a]);if(i)return i}return""}function je(t){let e=v(t);if(!e)return"";try{let n=new URL(e,window.location.origin);return n.origin!==window.location.origin?"":`${n.pathname}${n.search}${n.hash}`||"/"}catch{return""}}function fo(t){return ze[t]||ze[s.HANDOFF_TO_HUMAN]}function mo(t){return t&&typeof t=="object"?t:{}}function _o(t,e){return v(t.title)||e}function yo(t,e,n){return v(e[l.MESSAGE])||v(t.handling)||n}function ho(t,e){return v(e[l.REASON]||e.reason||e.blocked_reason||t.key)}function go(t){let e=[["Provider",t.provider_label||t.provider],["Boundary",t.automation_boundary],["Recovery",t.recovery],["Evidence",t.evidence],["Page",t.page_url]].filter(([,n])=>v(n));return e.length?`
    <p class="mayabot-handoff-meta">
      ${e.map(([n,r])=>`<span><strong>${M(n)}:</strong> ${M(r)}</span>`).join("")}
    </p>
  `:""}function We(t){t.classList.remove("active")}function bo(){window.setTimeout(()=>{let t=document.getElementById("mayabot-chat"),e=document.getElementById("mayabot-msgs");e&&(e.innerHTML=""),t&&t.classList.remove("visible")},U)}function Ve(t,e={}){let n=v(t).toUpperCase(),r=fo(n),o=mo(e.handoff_flow),a=uo(),i=po(n,e),c=_o(o,r.title),p=yo(o,e,r.body),h=ho(o,e);return a.innerHTML=`
    <div class="mayabot-handoff-body">
      <div class="mayabot-handoff-top">
        <h2 class="mayabot-handoff-title">${M(c)}</h2>
        <button class="mayabot-handoff-close" type="button" aria-label="Close handoff">&times;</button>
      </div>
      <p class="mayabot-handoff-text">${M(p)}</p>
      ${go(o)}
      ${h?`<p class="mayabot-handoff-reason">${M(h)}</p>`:""}
      <div class="mayabot-handoff-actions">
        <button type="button" class="secondary" data-close-handoff>Close</button>
        ${i?`<button type="button" data-open-handoff>${M(r.primary)}</button>`:""}
      </div>
    </div>
  `,a.querySelector(".mayabot-handoff-close")?.addEventListener("click",()=>We(a)),a.querySelector("[data-close-handoff]")?.addEventListener("click",()=>We(a)),a.querySelector("[data-open-handoff]")?.addEventListener("click",()=>{window.location.href=i}),a.classList.add("active"),bo(),!0}function qe(t){return Ge.has(t.action)}function Ke(t){return Ve(t.action,t.parameters||{})}function Xe(t){return t.action===s.NAVIGATE_TO&&!!Ze(t.parameters?.[l.PAGE])}function Je(t){return window.location.href=Ze(t.parameters?.[l.PAGE]),!0}function Ze(t){let e=String(t||"").trim();if(!e||tn(e)||/^https?:\/\//i.test(e))return"";if(e==="home"||e==="/")return"/";let n=To(e);if(n)return n;let r=e.replace(/^\/+|\/+$/g,"");return r?`/${r}`:"/"}function To(t){let e=window.AIHubAdapterRuntime?.config?.adapter?.routes||window.AIHubAdapter?.config?.adapter?.routes||{},n=Ao(t);for(let r of n){let o=e[r],a=Qe(o);if(a)return a}for(let[r,o]of Object.entries(e)){if(!n.includes(St(r)))continue;let a=Qe(o);if(a)return a}return""}function Ao(t){let e=St(t),n=String(t||"").trim().replace(/^\/+|\/+$/g,"").toLowerCase(),r=n.split("?")[0].split("#")[0].split("/").filter(Boolean).pop()||"";return Array.from(new Set([e,n,St(r)].filter(Boolean)))}function St(t){return String(t||"").trim().toLowerCase().replace(/[^a-z0-9/_\s-]+/g," ").replace(/[_-]+/g," ").replace(/\s+/g," ").trim().replace(/\s+/g,"-")}function Qe(t){let e=String(t||"").trim();if(!e||tn(e))return"";if(/^https?:\/\//i.test(e))try{let n=new URL(e);return n.origin!==window.location.origin?"":`${n.pathname||"/"}${n.search||""}${n.hash||""}`}catch{return""}return e.startsWith("/")?e:`/${e.replace(/^\/+/,"")}`}function tn(t){return/^(?:javascript:|data:|\/\/)/i.test(String(t||"").trim())}function en(t){let e=t?.params||t?.parameters||{};return{...t||{},action:String(t?.action||"").trim().toUpperCase(),params:e,parameters:e}}var It="AIHubAdapterRuntime",Ot="AIHubAdapter";function Eo(t){let e=t?.params||t?.parameters||{};return{...t||{},params:e,parameters:e}}function G(){return!!(window[It]?.executeAction||window[Ot]?.handleAction)}async function wt(t){return(await V(t)).succeeded}async function V(t){let e=Eo(t);if(window[It]?.executeAction){let n=window[It],r=await n.executeAction(e)===!0,o=n.lastActionResult||{};return{succeeded:r,handled:o.handled===!0||r,status:o.status||(r?"ok":"not_handled"),reason:o.reason||"",blocked:o.status==="blocked",disabled:o.status==="disabled"}}if(window[Ot]?.handleAction){let n=await window[Ot].handleAction(e)===!0;return{succeeded:n,handled:n,status:n?"ok":"not_handled",reason:"",blocked:!1,disabled:!1}}return{succeeded:!1,handled:!1,status:"missing_adapter",reason:"",blocked:!1,disabled:!1}}var So=Object.freeze([{path:"/api/products?per_page=96",routePrefix:"/product/"},{path:"/api/products",routePrefix:"/product/"},{path:"/api/products.json",routePrefix:""},{path:"/products.json",routePrefix:"/products/"},{path:"/collections/all/products.json",routePrefix:"/products/"}]),Io=Object.freeze(["products","data","items","results"]),rn=Object.freeze(["id","product_id","handle","sku"]),on=Object.freeze(["name","title"]),Oo=Object.freeze(["url","href","permalink","product_url"]),wo=Object.freeze(["image_url","imageUrl","image_src","imageSrc","image","images","media","thumbnail","thumbnail_url","featured_image","featuredImage","featured_image_url"]),xo=Object.freeze(["brand","vendor"]),Ro=Object.freeze(["category","category_name","product_type"]),Co=Object.freeze(["description","summary","body_html"]),No=Object.freeze(["original_price","compare_at_price","regular_price"]),an=Object.freeze(["currency","currency_code"]),Lo=Object.freeze(["display_price","price_text","formatted_price"]),Po="Unknown Brand",vo="Products",Do="/",Uo=/^[a-z0-9][a-z0-9-]*$/i,xt=null;function T(t){return t==null||typeof t=="object"?"":String(t||"").trim()}function Nt(t){return T(t).toLowerCase().replace(/[^a-z0-9]+/g," ").trim()}function sn(t){let e=new Set(["a","am","an","and","ask","asked","did","for","me","not","on","only","please","show","some","the","to","wanna","want","what","with","you","your"]),n=[],r=new Set;for(let o of Mo(Nt(t)).split(" ")){let a=ko(o);a.length<=1||e.has(a)||r.has(a)||(n.push(a),r.add(a))}return n}function Mo(t){return t.replace(/\b(?:i\s+)?did\s+not\s+ask\s+for\s+(?:a\s+|an\s+)?[a-z0-9]+\b/g," ")}function ko(t){return["phone","phones","mobile","mobiles"].includes(t)?"phone":["book","books"].includes(t)?"books":t}function Lt(t,e){return e.map(n=>T(t?.[n])).filter(Boolean)}function I(t,e){return Lt(t,e)[0]||""}function at(t){let e=T(t).replace(/,/g,"");if(!e)return 0;let n=e.match(/-?\d+(?:\.\d+)?/),r=Number(n?n[0]:e);return Number.isFinite(r)?r:0}function Fo(t,e){let n=I(t,Lo);if(n)return n;let r=I(t,an).toUpperCase();return e>0&&r?`${r} ${e.toLocaleString()}`:e>0?e.toLocaleString():""}function Ho(t){for(let e of wo){let n=Rt(t?.[e]);if(n)return n}return""}function Rt(t){if(!t)return"";if(Array.isArray(t)){for(let e of t){let n=Rt(e);if(n)return n}return""}if(typeof t=="object"){for(let e of["src","url","image_url","imageUrl","image_src","imageSrc","thumbnail","thumbnail_url","featured_image","featuredImage","featured_image_url"]){let n=Rt(t[e]);if(n)return n}return""}return Bo(t)}function Bo(t){let e=T(t);if(!e||/^javascript:/i.test(e))return"";if(/^data:image\//i.test(e))return e;try{let n=new URL(e,window.location.origin);return["http:","https:"].includes(n.protocol)?n.toString():""}catch{return""}}function Yo(t){let e=T(t);if(!e)return"";try{let n=new URL(e,window.location.origin);return n.origin!==window.location.origin?"":`${n.pathname}${n.search}${n.hash}`}catch{return""}}function $o(t,e,n){let r=Yo(I(t,Oo));return r||(!Uo.test(e)||!/[a-z]/i.test(e)||!n?.routePrefix?"":`${n.routePrefix}${encodeURIComponent(e)}${Do}`)}function Pt(t,e={}){if(!t)return null;let n=I(t,rn),r=T(t.handle||t.slug||t.product_handle),o=I(t,on),a=at(t.price||t.amount||t.cost),i=at(I(t,No));return!n&&!r?null:{id:n,handle:r,name:o,title:T(t.title||o),brand:I(t,xo)||Po,category:I(t,Ro)||vo,description:I(t,Co),price:Number.isFinite(a)?a:0,originalPrice:Number.isFinite(i)?i:0,displayPrice:Fo(t,a),currency:I(t,an),rating:at(t.rating||t.review_rating),reviewCount:at(t.review_count||t.reviews_count||t.reviews),imageUrl:Ho(t),url:$o(t,r||n,e)}}function zo(t){return Lt(t,rn)}function nn(t){return Lt(t,on).map(Nt)}function cn(t,e){let n=T(e);return!!(n&&zo(t).includes(n))}function un(t,e){let n=sn(e);if(!n.length)return!1;let r=Nt([t?.name,t?.title,t?.brand,t?.category,t?.category_name,t?.product_type,t?.description,t?.tags].join(" "));return n.every(o=>r.includes(o)||r.includes(o.replace(/s$/,"")))}function jo(t,e){let n=new Set(nn(e));return nn(t).some(r=>n.has(r))}function Wo(t,e){return!!(t?.imageUrl&&t.imageUrl===e?.imageUrl)}function Go(t){if(Array.isArray(t))return t;for(let e of Io){let n=t?.[e];if(Array.isArray(n))return n}return[]}async function Vo(t){try{let e=await fetch(new URL(t.path,window.location.origin),{headers:{Accept:"application/json"}});if(!e.ok)return[];let n=await e.json();return Go(n).map(r=>Pt(r,t)).filter(Boolean)}catch(e){return console.warn(`[AI Hub Widget] Catalog endpoint lookup failed for ${t.path}:`,e),[]}}async function Ct(){return xt||(xt=Promise.all(So.map(Vo)).then(t=>t.flat())),xt}async function qo(t,e=120){if(!sn(t).length)return[];let r=new URL("/v1/products",d.apiUrl);r.searchParams.set("site_id",d.siteId),r.searchParams.set("limit",String(e));try{let o=await fetch(r.toString(),{headers:{Accept:"application/json"}});return o.ok?(await o.json()).map(a=>Pt(a)).filter(Boolean).filter(a=>un(a,t)).slice(0,12):[]}catch(o){return console.warn("[AI Hub Widget] Hub product search fallback failed:",o),[]}}async function ln(t,e=""){let n=(Array.isArray(t)?t:[]).map(T).filter(Boolean),r=[],o="",a="";if(n.length)try{r=await dn(n),o="hub_by_ids"}catch(i){a="hub_product_lookup_failed",console.warn("[AI Hub Widget] Hub product ID lookup failed:",i)}if(!r.length&&n.length){let i=await Ct();r=n.map(c=>i.find(p=>cn(p,c))).filter(Boolean),r.length&&(o="host_by_ids")}return!r.length&&e&&(r=await qo(e),r.length&&(o="hub_search")),!r.length&&e&&(r=(await Ct()).filter(c=>un(c,e)).slice(0,12),r.length&&(o="host_search")),{products:r,source:o,reason:r.length?"":a||"no_matching_products_rendered"}}async function dn(t){let e=(Array.isArray(t)?t:[]).map(T).filter(Boolean);if(!e.length)return[];let n=new URL(A.PRODUCTS_BY_IDS,d.apiUrl);n.searchParams.set("site_id",d.siteId),n.searchParams.set("ids",e.join(","));let r=await fetch(n.toString(),{headers:{Accept:"application/json"}});if(!r.ok)throw new Error("Failed to fetch products from AI Hub API");let o=(await r.json()).map(i=>Pt(i)).filter(Boolean),a=new Map(o.map(i=>[String(i.id),i]));return e.map(i=>a.get(i)).filter(Boolean)}async function it(t){let e=T(t);if(!e)return"";let[n]=await dn([e]);if(n?.url)return n.url;let r=await Ct(),o=r.find(i=>cn(i,e));return o?.url?o.url:n&&r.find(i=>jo(i,n)||Wo(i,n))?.url||""}var Ko=["data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='320' height='240' viewBox='0 0 320 240'%3E","%3Crect width='320' height='240' fill='%23f1f2ee'/%3E","%3Cpath d='M98 156h124l-31-40-25 30-17-22-51 32Z' fill='%23c8c3ba'/%3E","%3Ccircle cx='117' cy='95' r='17' fill='%23d8d3ca'/%3E","%3Ctext x='160' y='198' text-anchor='middle' fill='%23686660' font-family='Arial,sans-serif' font-size='16'%3EImage pending%3C/text%3E","%3C/svg%3E"].join(""),pn=12,Dt=[],Ut=x;function k(t){return String(t??"").replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;").replace(/"/g,"&quot;").replace(/'/g,"&#039;")}function Qo(){if(document.getElementById("mayabot-product-overlay-styles"))return;let t=document.createElement("style");t.id="mayabot-product-overlay-styles",t.textContent=`
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
      display: grid;
      grid-template-rows: auto auto auto 1fr;
      gap: 9px;
      min-width: 0;
      border: 1px solid rgba(22, 22, 21, 0.1);
      border-radius: 8px;
      background: #ffffff;
      padding: 12px;
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
      align-self: end;
      margin-top: 2px;
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
      #mayabot-product-panel.count-1,
      #mayabot-product-panel.count-2,
      #mayabot-product-panel.count-3,
      #mayabot-product-panel.count-many {
        --mayabot-card-count: 1;
      }
    }
  `,document.head.appendChild(t)}function Xo(){Qo();let t=document.getElementById("mayabot-product-panel");return t||(t=document.createElement("div"),t.id="mayabot-product-panel",t.setAttribute("aria-live","polite"),t.innerHTML=`
    <div class="mayabot-product-header">
      <h2 class="mayabot-product-title">${x}</h2>
      <button class="mayabot-product-close" type="button" aria-label="Close recommendations">&times;</button>
    </div>
    <div class="mayabot-product-grid"></div>
  `,t.querySelector(".mayabot-product-close").addEventListener("click",()=>{t.classList.remove("active")}),document.body.appendChild(t),t)}async function Jo(t){let e={action:s.ADD_TO_CART,params:{[l.PRODUCT_ID]:t,[l.QUANTITY]:pt},parameters:{[l.PRODUCT_ID]:t,[l.QUANTITY]:pt}};G()&&await wt(e)||window.dispatchEvent(new CustomEvent(z.MAYABOT_ACTION,{detail:e}))}async function Zo(t){try{let n=await it(t);if(n){window.location.href=n;return}}catch(n){console.warn("[AI Hub Widget] Product detail URL lookup failed:",n)}let e={action:s.SHOW_PRODUCT_DETAIL,params:{[l.PRODUCT_ID]:t},parameters:{[l.PRODUCT_ID]:t}};G()&&await wt(e)||window.dispatchEvent(new CustomEvent(z.MAYABOT_ACTION,{detail:e}))}function ta(t){return t<=1?"count-1":t===2?"count-2":t===3?"count-3":"count-many"}function ea(t){return t<=1?1:t===2?2:3}function na(t){let e=new Set;return(Array.isArray(t)?t:[]).map(n=>String(n??"").trim()).filter(Boolean).filter(n=>e.has(n)?!1:(e.add(n),!0))}function vt(t,e,n="",r={}){let o=(Array.isArray(e)?e:[]).map(p=>String(p?.id??"").trim()).filter(Boolean),a=o.length,i=t.length,c=a>0?"succeeded":"failed";return{status:c,stage:"product_overlay",reason:n||(c==="succeeded"?"":"no_matching_products_rendered"),evidence:{requested_product_count:i,rendered_product_count:a,missing_product_count:Math.max(i-a,0),requested_product_ids:t.slice(0,pn).join(","),rendered_product_ids:o.slice(0,pn).join(","),lookup_source:r.source||"",search_query:r.searchQuery||""}}}function ra(t){let e=String(t?.displayPrice||"").trim();if(e)return e;let n=Number(t?.price||0);return Number.isFinite(n)&&n>0?n.toLocaleString():"Price unavailable"}function st(t,e){let n=Xo(),r=n.querySelector(".mayabot-product-grid"),o=n.querySelector(".mayabot-product-title"),a=t.length;if(Dt=Array.isArray(t)?[...t]:[],Ut=e||x,n.classList.remove("count-1","count-2","count-3","count-many"),n.classList.add(ta(a)),n.style.setProperty("--mayabot-card-count",String(ea(a))),o.textContent=Ut,!a){r.innerHTML='<p class="mayabot-product-empty">No matching products are currently available.</p>',n.classList.add("active"),fn();return}r.innerHTML=t.map(i=>{let c=k(i.id);return`
        <article class="mayabot-product-card" data-product-id="${c}">
          <img class="mayabot-product-image" src="${k(i.imageUrl||Ko)}" alt="${k(i.name)}">
          <h3 class="mayabot-product-name">${k(i.name||i.title||"Product")}</h3>
          <p class="mayabot-product-meta">${k(i.brand)} - ${k(ra(i))}</p>
          <div class="mayabot-product-actions">
            <button type="button" data-add="${c}">Add</button>
            <button type="button" class="secondary" data-view="${c}">View</button>
          </div>
        </article>
      `}).join(""),r.querySelectorAll("[data-add]").forEach(i=>{i.addEventListener("click",async()=>{await Jo(i.getAttribute("data-add"))})}),r.querySelectorAll("[data-view]").forEach(i=>{i.addEventListener("click",async()=>{await Zo(i.getAttribute("data-view"))})}),n.classList.add("active"),fn()}function fn(){window.setTimeout(()=>{let t=document.getElementById("mayabot-chat"),e=document.getElementById("mayabot-msgs");e&&(e.innerHTML=""),t&&t.classList.remove("visible")},U)}async function _n(t,e=x,n={}){let r=na(t),o=String(n.searchQuery||"").trim();if(!r.length&&!o)return st([],e),vt([],[],"missing_product_ids");try{let{products:a,source:i,reason:c}=await ln(r,o);return st(a,e),vt(r,a,c,{source:i,searchQuery:o})}catch(a){return console.warn("[AI Hub Widget] Product overlay failed:",a),st([],e),vt(r,[],"product_overlay_fetch_failed",{searchQuery:o})}}function yn(t={}){if(!Dt.length)return!1;let e=String(t.sort_by||t.sortBy||"price_asc").trim().toLowerCase(),n=[...Dt].sort((r,o)=>oa(r,o,e));return st(n,aa(Ut,e)),!0}function oa(t,e,n){return n==="price_desc"?F(e.price,Number.NEGATIVE_INFINITY)-F(t.price,Number.NEGATIVE_INFINITY):n==="rating"?F(e.rating||e.review_rating,Number.NEGATIVE_INFINITY)-F(t.rating||t.review_rating,Number.NEGATIVE_INFINITY):n==="newest"?mn(e)-mn(t):F(t.price,Number.POSITIVE_INFINITY)-F(e.price,Number.POSITIVE_INFINITY)}function F(t,e){let n=String(t??"").replace(/,/g,"").match(/-?\d+(?:\.\d+)?/);if(!n)return e;let r=Number(n[0]);return Number.isFinite(r)?r:e}function mn(t){let e=t?.updated_at||t?.created_at||t?.date||"",n=Date.parse(String(e||""));return Number.isFinite(n)?n:0}function aa(t,e){let n={price_asc:"sorted low to high",price_desc:"sorted high to low",rating:"sorted by rating",newest:"newest first"};return`${String(t||x).replace(/\s+-\s+sorted.*$/i,"")} - ${n[e]||n.price_asc}`}function gn(t){return t.action===s.SHOW_PRODUCTS||t.action===s.SHOW_COMPARISON||t.action===s.SHOW_PRODUCT_DETAIL||t.action===s.SORT_PRODUCTS}async function bn(t){return t.action===s.SHOW_COMPARISON?hn(t.parameters||{},"Product comparison",{syncListing:!1}):t.action===s.SHOW_PRODUCTS?hn(t.parameters||{},x):t.action===s.SHOW_PRODUCT_DETAIL?ca(t.parameters||{}):t.action===s.SORT_PRODUCTS?yn(t.parameters||{}):!1}async function hn(t,e=x,n={}){let r=Array.isArray(t[l.PRODUCT_IDS])?t[l.PRODUCT_IDS]:[],o=sa(t),i=n.syncListing!==!1?await ia(o):{succeeded:!1,handled:!1,status:"skipped",stage:"product_display_sync",reason:"comparison_overlay"},c=await _n(r,t.title||o||e,{searchQuery:o}),p={...c.evidence||{},listing_sync_status:i.status||"",listing_sync_stage:i.stage||"",listing_sync_reason:i.reason||""};return c.status!=="succeeded"?{...c,evidence:p}:o&&i.handled&&!i.succeeded?{status:"failed",stage:"product_display_sync",reason:i.reason||i.status||"listing_sync_failed",evidence:p}:{...c,stage:i.succeeded?"product_display_sync":c.stage,evidence:p}}async function ia(t){let e=Tn(t);return e?V({action:s.FILTER_PRODUCTS,params:{[l.SEARCH_QUERY]:e,query:e,q:e}}):{succeeded:!1,handled:!1,status:"skipped",stage:"product_display_sync",reason:"missing_search_query"}}function sa(t){return Tn(t[l.SEARCH_QUERY]||t.search||t.query||t.q||"")}function Tn(t){return String(t||"").trim()}async function ca(t){let e="";try{e=await it(t[l.PRODUCT_ID])}catch(n){return console.warn("[AI Hub Widget] Product detail URL lookup failed:",n),!1}return e?(window.location.href=e,!0):!1}var Mt="stop_action_fallback",ua=new Set([s.SHOW_PRODUCTS,s.SHOW_COMPARISON,s.SHOW_PRODUCT_DETAIL,s.SORT_PRODUCTS]);function An(t){return G()&&!ua.has(t.action)}async function En(t){let e=await V(t);return e.succeeded?!0:e.blocked||e.disabled?Mt:!1}function Sn(t){return window.dispatchEvent(new CustomEvent(z.MAYABOT_ACTION,{detail:t})),!0}var la=Object.freeze([{name:"runtime_adapter",canExecute:An,execute:En},{name:"product_overlay",canExecute:gn,execute:bn},{name:"entity_overlay",canExecute:Be,execute:Ye},{name:"handoff_overlay",canExecute:qe,execute:Ke},{name:"platform_adapter",canExecute:()=>!0,execute:fe},{name:"provider_adapter",canExecute:Oe,execute:we},{name:"navigation",canExecute:Xe,execute:Je},{name:"browser_event",canExecute:()=>!0,execute:Sn}]);async function Ft(t){let e=[];for(let n of t||[]){let r=en(n),o=await da(r);o&&e.push(o)}return e}async function da(t){if(!t.action)return;let e=Date.now(),n=window.location.href;await Z(d.apiUrl,d.siteId,t,{status:"requested",stage:"widget_dispatch",requested_url:n,final_url:n,evidence:kt(t,n,n)}),await Z(d.apiUrl,d.siteId,t,{status:"executing",stage:"widget_dispatch",requested_url:n,final_url:window.location.href,evidence:kt(t,n,window.location.href)});let r;try{r=await pa(t)}catch(i){r={status:"failed",stage:"widget_dispatch",reason:i instanceof Error?i.message:"execution_error"}}let o=window.location.href,a=kt(t,n,o,r);return await Z(d.apiUrl,d.siteId,t,{status:r.status,stage:r.stage,reason:r.reason,duration_ms:Date.now()-e,requested_url:n,final_url:o,evidence:a}),{action:t.action,request_id:t.request_id||t.action_request_id||"",turn_id:t.turn_id||"",sequence:Number(t.sequence||0),status:r.status,stage:r.stage,reason:r.reason,requested_url:n,final_url:o,evidence:a}}async function pa(t){if(!t.action)return{status:"failed",stage:"normalization",reason:"missing_action"};for(let e of la){if(!e.canExecute(t))continue;let n=await e.execute(t),r=fa(n,e.name);if(r)return r}return{status:"failed",stage:"all",reason:"no_executor_succeeded"}}function fa(t,e){if(t===!0)return{status:"succeeded",stage:e,reason:""};if(t===Mt)return{status:"blocked",stage:e,reason:"action_blocked"};if(!t||typeof t!="object")return null;let n=String(t.status||"").trim().toLowerCase();return n?{status:n,stage:String(t.stage||e).trim()||e,reason:String(t.reason||"").trim(),evidence:t.evidence&&typeof t.evidence=="object"?t.evidence:{}}:null}function kt(t,e,n,r={}){let o=t.parameters||t.params||{},a={requested_url:e,final_url:n,url_changed:e!==n,path_changed:In(e)!==In(n),title:document.title||"",stage:r.stage||"",result_status:r.status||""};return o.page&&(a.target_page=o.page),o.product_id&&(a.product_id=o.product_id),o.entity_id&&(a.entity_id=o.entity_id),Array.isArray(o.product_ids)&&(a.product_count=o.product_ids.length),Array.isArray(o.entity_ids)&&(a.entity_count=o.entity_ids.length),{...a,...r.evidence&&typeof r.evidence=="object"?r.evidence:{}}}function In(t){try{return new URL(t,window.location.href).pathname}catch{return""}}var ma=3,_a=700,ya="AIHubAdapterRuntime",ha="AIHubAdapter",H="";function ga(t,e){let n=new URL(A.SHOP_WS,t);return n.protocol=n.protocol==="https:"?"wss:":"ws:",n.searchParams.set("site_id",e),n.searchParams.set("session_id",d.sessionId),n.toString()}function ba(t){return new Promise((e,n)=>{let r=new FileReader;r.onloadend=()=>{let o=String(r.result||"");e(o.includes(",")?o.split(",").pop():o)},r.onerror=()=>n(r.error||new Error("Failed to read audio blob")),r.readAsDataURL(t)})}var Ht=class{constructor(){this.queue=[],this.blocked=[],this.playing=!1,this.installUnlockListeners()}push(e,n=""){e&&(this.queue.push({audioB64:e,fallbackText:n}),this.playNext())}playNext(){if(this.playing||this.queue.length===0)return;this.playing=!0;let e=this.queue.shift(),n=new Audio($.DATA_WAV_PREFIX+e.audioB64);n.preload="auto",n.onended=()=>{this.playing=!1,this.playNext()},n.onerror=()=>{e.fallbackText&&D(e.fallbackText),this.playing=!1,this.playNext()},n.play().catch(r=>{if(console.warn("Audio playback failed",r),this.isAutoplayBlocked(r)){e.fallbackText?D(e.fallbackText):this.blocked.unshift(e),this.playing=!1;return}e.fallbackText&&D(e.fallbackText),this.playing=!1,this.playNext()})}installUnlockListeners(){if(typeof window>"u")return;let e=()=>{this.retryBlocked(),Ia()};window.addEventListener("pointerdown",e,{capture:!0,passive:!0}),window.addEventListener("keydown",e,{capture:!0}),window.addEventListener("touchstart",e,{capture:!0,passive:!0})}retryBlocked(){this.blocked.length&&(this.queue.unshift(...this.blocked.splice(0)),this.playNext())}speakInsteadOfBlocked(e){!e||!this.blocked.length||(this.blocked=[],D(e))}isAutoplayBlocked(e){let n=`${e?.name||""} ${e?.message||e||""}`.toLowerCase();return n.includes("notallowed")||n.includes("user didn't interact")||n.includes("not allowed")}},On=new Ht,Bt=class{async sendAudio(e,n,r=[]){let o=new FormData;o.append("audio",e,Sa(e)),o.append("site_id",d.siteId),o.append("session_id",d.sessionId),r&&r.length>0&&o.append("conversation_history",JSON.stringify(r));let a=Rn();a&&o.append("page_context",JSON.stringify(a));let i=await fetch(`${d.apiUrl}${A.SHOP}`,{method:re.POST,body:o});if(!i.ok)throw new Error("AI Hub API request failed");let c=await i.json();if(c.transcript&&n.onUserMessage?.(c.transcript),c.response_text&&n.onAssistantMessage?.(c.response_text,c.ui_actions||[]),n.onStatusChange?.(m.READY),c.audio_b64?Ea(c.audio_b64,c.response_text||""):c.response_text&&D(c.response_text),c.ui_actions&&c.ui_actions.length>0){let p=await Ft(c.ui_actions);n.onActionResults?.(p)}n.onComplete?.(c)}},Yt=class{constructor(){this.ws=null,this.connected=!1,this.connecting=null,this.failed=!1,this.retries=0,this.audioQueue=On,this.callbacks=null,this.turnText="",this.receivedAudio=!1}async ensureConnected(e=[]){return this.canUseWebSocket()?this.isOpen()?!0:this.connecting?this.connecting:(this.connecting=this.openConnection(e),this.connecting):!1}canUseWebSocket(){return!this.failed&&d.useWebSocket&&"WebSocket"in window}isOpen(){return this.connected&&this.ws?.readyState===WebSocket.OPEN}openConnection(e=[]){return new Promise(n=>{let r=new WebSocket(ga(d.apiUrl,d.siteId)),o=!1;this.ws=r;let a=(c=null)=>{o||(o=!0,this.markConnectionFailed(n,c,r))},i=window.setTimeout(()=>{a()},ue);r.onopen=()=>{o||(o=!0,this.handleConnectionOpen(i,e,n))},r.onmessage=c=>{this.handleMessage(c).catch(p=>this.handleTransportError(p))},r.onerror=()=>a(i),r.onclose=()=>{this.connected=!1,a(i)}})}markConnectionOpen(){this.connected=!0,this.connecting=null,this.retries=0}handleConnectionOpen(e,n,r){window.clearTimeout(e),this.markConnectionOpen(),this.sendConfig(n),r(!0)}markConnectionFailed(e,n=null,r=null){n&&window.clearTimeout(n),this.connected=!1,this.connecting=null,this.retries+=1,this.retries>=ma&&(this.failed=!0),r&&r.readyState!==WebSocket.CLOSED&&r.close(),e(!1)}sendConfig(e=[]){this.sendJson({type:E.CONFIG,history:e||[],session_id:d.sessionId,page_context:Rn()})}sendJson(e){return!this.ws||this.ws.readyState!==WebSocket.OPEN?!1:(this.ws.send(JSON.stringify(e)),!0)}async sendAudio(e,n,r=[]){if(!await this.ensureConnected(r))return!1;this.callbacks=n,this.turnText="",this.receivedAudio=!1,this.sendConfig(r);let a=await ba(e);return this.sendJson({type:E.AUDIO_CHUNK,data:a,mime_type:e?.type||""}),this.sendJson({type:E.AUDIO_END,mime_type:e?.type||""}),!0}async handleMessage(e){let n=this.callbacks;if(!n)return;let r=this.parseMessage(e.data);if(!r){this.completeWithError(n,"Invalid WebSocket message");return}if(!this.handleIncrementalMessage(r,n)){if(r.type===E.DONE){await this.handleDoneMessage(r,n);return}r.type===E.ERROR&&this.completeWithError(n,r.message||"WebSocket error")}}parseMessage(e){try{let n=JSON.parse(e);return n&&typeof n=="object"?n:null}catch{return null}}handleIncrementalMessage(e,n){return e.type===E.TRANSCRIPT?(n.onUserMessage?.(e.text||""),!0):e.type===E.TEXT_CHUNK?(this.turnText+=e.text||"",n.onAssistantChunk?.(e.text||"",this.turnText),!0):e.type===E.AUDIO_CHUNK?(this.receivedAudio=!!e.audio_b64||this.receivedAudio,this.audioQueue.push(e.audio_b64),!0):!1}async handleDoneMessage(e,n){let r=e.response_text||this.turnText;n.onAssistantMessage?.(r,e.ui_actions||[],{streamed:!0}),n.onStatusChange?.(m.READY),!this.receivedAudio&&r?D(r):this.receivedAudio&&r&&this.audioQueue.speakInsteadOfBlocked(r);try{if(e.ui_actions&&e.ui_actions.length>0){let o=await Ft(e.ui_actions);n.onActionResults?.(o)}n.onComplete?.(e)}catch(o){this.handleTransportError(o)}finally{this.callbacks=null}}completeWithError(e,n){e.onStatusChange?.(m.ERROR,xn(n)),e.onComplete?.({error:n}),this.callbacks=null}handleTransportError(e){console.error("AI Hub WebSocket transport failed",e);let n=this.callbacks;n&&this.completeWithError(n,String(e))}},Ta=new Bt,Aa=new Yt;async function wn(t,e,n,r=[]){try{if(d.useWebSocket&&await Aa.sendAudio(t,n,r))return;await Ta.sendAudio(t,n,r)}catch(o){console.error(o),n.onStatusChange?.(m.ERROR,xn(o)),n.onComplete?.({error:String(o)})}}function Ea(t,e=""){On.push(t,e)}function Sa(t){let e=String(t?.type||"").toLowerCase();return e.includes("mp4")?"audio.mp4":e.includes("ogg")?"audio.ogg":e.includes("wav")?"audio.wav":$.WEBM_FILENAME}function xn(t){let e=String(t?.message||t||"").toLowerCase();return e.includes("quota")?"Quota reached":e.includes("microphone")||e.includes("permission")?"Mic unavailable":e.includes("network")||e.includes("fetch")||e.includes("api request")?"Connection issue":"Try again"}function D(t){if(!t||!("speechSynthesis"in window)||!("SpeechSynthesisUtterance"in window))return!1;H=String(t).slice(0,_a);let e=new SpeechSynthesisUtterance(H);e.rate=1,e.pitch=1,e.volume=1,e.onstart=()=>{H=""},e.onend=()=>{H=""};try{return window.speechSynthesis.cancel(),window.speechSynthesis.resume(),window.speechSynthesis.speak(e),!0}catch(n){return console.warn("Fallback speech failed",n),!1}}function Ia(){H&&D(H)}function Rn(){let t=window[ya],e=window[ha];try{if(typeof t?.getContext=="function")return t.getContext();if(typeof e?.getContext=="function")return e.getContext()}catch(n){console.warn("[AI Hub Widget] Page context collection failed:",n)}return null}var Oa=4,wa=40,xa=24,Ra=80,Ca=120;function Nn(){let t=[];function e(n,r){let o=String(r||"").trim();o&&(t.push({role:n,content:o}),t.length>oe&&t.shift())}return{history:t,rememberUserMessage(n){e("user",n)},rememberAssistantMessage(n,r){e("assistant",Na(n,r))},rememberActionResults(n){let r=Pa(n);r&&e("assistant",r)}}}function Na(t,e){let n=La(e);return n.length?`${t} [PRODUCT_IDS: ${n.join(",")}]`:t}function La(t){let e=[];for(let n of t||[]){let r=n.params||{};Cn(e,r[l.PRODUCT_IDS]),Cn(e,[r[l.PRODUCT_ID]])}return e}function Cn(t,e){for(let n of Array.isArray(e)?e:[])n&&!t.includes(n)&&t.push(n)}function Pa(t){let e=(Array.isArray(t)?t:[]).map(va).filter(Boolean).slice(0,Oa);return e.length?`[BROWSER_ACTION_RESULTS: ${e.join(" | ")}]`:""}function va(t){if(!t||typeof t!="object"||!t.action)return"";let e=[ct(t.action,wa),`status=${ct(t.status,xa)||"unknown"}`],n=Ua(t.final_url);return n&&e.push(`final_path=${ct(n,Ca)}`),t.reason&&e.push(`reason=${ct(t.reason,Ra)}`),Da(e,t.evidence),e.join(" ")}function Da(t,e={}){e.rendered_product_count!==void 0&&t.push(`rendered_products=${Number(e.rendered_product_count||0)}`),e.rendered_entity_count!==void 0&&t.push(`rendered_records=${Number(e.rendered_entity_count||0)}`)}function ct(t,e){return String(t||"").replace(/\s+/g," ").trim().slice(0,e)}function Ua(t){try{let e=new URL(String(t||""),window.location.href);return`${e.pathname}${e.search}${e.hash}`}catch{return""}}var Ma=1,ka=1.08,Fa=300,Ha=Object.freeze(["hannah","zira","aria","jenny","samantha","victoria","tessa","moira","karen","female","woman","nova","shimmer","google us english","microsoft aria"]),q="",ut="";function $t(t){if(!("speechSynthesis"in window)||!("SpeechSynthesisUtterance"in window))return;q=t;let e=()=>{try{let n=new SpeechSynthesisUtterance(t),r=Ba(window.speechSynthesis.getVoices());r&&(n.voice=r),n.rate=Ma,n.pitch=ka,n.onstart=Ln,n.onend=Ln,window.speechSynthesis.cancel(),window.speechSynthesis.resume(),window.speechSynthesis.speak(n)}catch{}};if(window.speechSynthesis.getVoices().length>0){e();return}window.speechSynthesis.onvoiceschanged=e,window.setTimeout(e,Fa)}function Pn(){q&&$t(q)}function vn(){q="",ut="";try{window.speechSynthesis?.cancel()}catch{}}function Ba(t){if(!Array.isArray(t)||t.length===0)return null;let e=Ya(t)||$a(t);return e&&(ut=e.name),e}function Ya(t){if(ut){let n=t.find(r=>r.name===ut);if(n)return n}let e=String(d.speechVoiceName||"").toLowerCase();return e&&t.find(n=>n.name.toLowerCase()===e)||null}function $a(t){return d.speechVoicePreference.toLowerCase()!=="female"?t.find(e=>e.default)||t[0]:t.find(e=>Ha.some(n=>e.name.toLowerCase().includes(n)))||t.find(e=>e.default)||t[0]}function Ln(){q=""}var Dn=null;function zt(t){Dn||(Un(t),Dn=window.setInterval(()=>Un(t),ce))}async function Un({boot:t,shutdownWidget:e}){try{if(await za()){t();return}e()}catch{t()}}async function za(){let t=new URL(A.WIDGET_STATUS,d.apiUrl);t.searchParams.set("site_id",d.siteId);let e=await fetch(t.toString(),{cache:"no-store",headers:{Accept:"application/json"}});return e.ok?(await e.json()).enabled!==!1:!0}window.__mayabot_identifier="voice-orb";var jt=null;function Mn(){if(window.__mayabotBooted||document.getElementById("mayabot-widget"))return;window.__mayabotBooted=!0,Wt();let t=ee(),e=null;function n(f=ae){e&&window.clearTimeout(e),e=window.setTimeout(()=>{t.msgs.innerHTML="",t.chat.classList.remove("visible"),e=null},f)}function r(f,g=""){t.status.className="",f===m.RECORDING?(e&&(window.clearTimeout(e),e=null),t.msgs.innerHTML="",t.btn.classList.add("recording"),t.chat.classList.add("visible"),t.status.innerText="Listening...",t.status.classList.add("listening")):f===m.PROCESSING?(t.btn.classList.remove("recording"),t.chat.classList.add("visible"),t.status.innerText="Analyzing...",t.status.classList.add("processing")):f===m.READY?(t.status.innerText="Ready",t.status.classList.add("ready")):f===m.ERROR&&(t.status.innerText=g||"Try again",t.status.classList.add("error"),t.btn.classList.remove("recording"))}let o=Nn(),a=null,i="",c=!1;async function p(f){if(!c){c=!0,t.btn.disabled=!0,a=null,i="";try{await wn(f,t,{onUserMessage:g=>{Y(t,g,"user"),o.rememberUserMessage(g)},onAssistantChunk:(g,L)=>{i=L,a||(a=Y(t,"","ai")),dt(t,a,i)},onAssistantMessage:(g,L,y={})=>{y.streamed&&a?dt(t,a,g):Y(t,g,"ai"),o.rememberAssistantMessage(g,L),a=null,i=""},onActionResults:o.rememberActionResults,onStatusChange:r,onComplete:()=>n()},o.history)}finally{c=!1,t.btn.disabled=!1,a=null,i=""}}}let h=le(p,r);jt=h,t.btn.addEventListener("click",()=>{c||h.toggle()}),ja()&&(Wa(),window.setTimeout(()=>{if(o.history.length>0)return;let f=`Welcome to ${d.brandName}. How can I help you today?`;Y(t,f,"ai"),r(m.READY),n(se),$t(f)},ie))}function kn(){jt?.cancel(),jt=null,window.__mayabotBooted=!1,document.getElementById("mayabot-widget")?.remove(),document.getElementById("mayabot-product-panel")?.remove(),vn()}function ja(){if(!d.autoGreet||!Ga())return!1;try{return window.sessionStorage.getItem(Fn())!=="1"}catch{return!window.__mayabotAutoGreeted}}function Wa(){window.__mayabotAutoGreeted=!0;try{window.sessionStorage.setItem(Fn(),"1")}catch{}}function Fn(){return`mayabot:auto-greeted:${d.siteId}`}function Ga(){let t=window.location.pathname.replace(/\/+$/,"")||"/";return t==="/"||t.endsWith("/index.html")}document.readyState==="loading"?document.addEventListener("DOMContentLoaded",()=>zt({boot:Mn,shutdownWidget:kn})):zt({boot:Mn,shutdownWidget:kn});document.addEventListener("pointerdown",Pn,{capture:!0});})();
