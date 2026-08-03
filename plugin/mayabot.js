(()=>{function Zt(){let t="#5d5fef",e=document.querySelector('meta[name="theme-color"]');if(e&&e.content)t=e.content;else{let h=document.querySelector('button[class*="primary"], .btn-primary, [data-primary]');if(h){let g=window.getComputedStyle(h).backgroundColor;g&&g!=="rgba(0, 0, 0, 0)"&&g!=="transparent"&&(t=g)}}let n=window.matchMedia&&window.matchMedia("(prefers-color-scheme: dark)").matches,r=n?"rgba(24, 24, 27, 0.75)":"rgba(255, 255, 255, 0.85)",o=n?"rgba(255, 255, 255, 0.1)":"rgba(0, 0, 0, 0.08)",a=n?"#f3f4f6":"#111827",i=n?"rgba(255, 255, 255, 0.1)":"rgba(0, 0, 0, 0.05)",c=n?"rgba(0, 0, 0, 0.25)":"#ffffff",f=document.createElement("style");f.textContent=`
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
  `,document.head.appendChild(f)}var _t="site_1",qn="__AI_";var Kn="aihub:auto-site-id:",Qn=["data-aihub-scope","data-site-scope"],Xn=["data-site-id","data-aihub-site-id"];function y(t){return String(t||"").trim()}function $(t){return y(t).replace(/\/+$/,"")}function ne(t,e,n,r=_t){return Jn(t,e,n)||Zn()||y(r)||_t}function Jn(t,e,n){for(let a of Xn){let i=y(t?.getAttribute(a));if(i)return i}let r=y(e?.searchParams.get("site"))||y(e?.searchParams.get("site_id"))||y(e?.searchParams.get("shop"));if(r)return r;let o=y(n);return o&&!o.startsWith(qn)?o:""}function Zn(){let t=tr(),e=`${Kn}${t}`,n=cr(e);if(n){let c=ir(n);return c!==n&&ee(e,c),c}let r=y(window.location.host||window.location.hostname||"site"),o=re(),a=ar(`${r}${o?`_${o.replace(/\//g,"_")}`:""}`),i=oe(`auto_${a}_${sr(t)}`);return ee(e,i),i}function tr(){return`${window.location.origin}${re()}`}function re(){return er()}function er(){for(let e of Qn){let n=y(nr()?.getAttribute(e));if(n)return te(n)}let t=document.querySelector("meta[name='aihub-site-scope']")?.getAttribute("content");return te(t)}function nr(){return document.currentScript}function te(t){let e=y(t);if(!e||e==="/")return"";try{let r=new URL(e,window.location.href);if(r.origin===window.location.origin){let[o]=rr(r.pathname);return o?`/${o}`:""}}catch{}let[n]=e.replace(/^\/+/,"").split("/");return n?`/${n}`:""}function rr(t=window.location.pathname){return y(t).split("/").map(e=>or(e).trim()).filter(Boolean)}function or(t){try{return decodeURIComponent(t)}catch{return String(t||"")}}function ar(t){return y(t).toLowerCase().replace(/[^a-z0-9]+/g,"_").replace(/^_+|_+$/g,"")||"site"}function oe(t){return y(t).slice(0,80).replace(/_+$/g,"")||_t}function ir(t){let e=y(t);return e.startsWith("auto_")?oe(e.toLowerCase().replace(/[^a-z0-9]+/g,"_").replace(/^_+|_+$/g,"")):e}function sr(t){let e=2166136261,n=y(t);for(let r=0;r<n.length;r+=1)e^=n.charCodeAt(r),e=Math.imul(e,16777619);return(e>>>0).toString(36)}function cr(t){try{return y(window.localStorage.getItem(t))}catch{return""}}function ee(t,e){try{window.localStorage.setItem(t,e)}catch{}}var x=document.currentScript,ae="__AI_PUBLIC_API_URL__",ur="__AI_DEFAULT_SITE_ID__",lr="mayabot:session:",dr="Maya",pr="AI Salesperson",fr="female";function L(t){return String(t||"").trim()}function mr(){let t=L(x?.getAttribute("src"));if(!t)return null;try{return new URL(t,window.location.href)}catch{return null}}function yr(t){let e=L(x?.getAttribute("data-api-url"));if(e)return $(e);if(!ae.startsWith("__AI_"))return $(ae);if(t?.origin){let n=t.pathname.replace(/\/mayabot(?:-widget)?\.js$/,"");return $(`${t.origin}${n}`)}return $(window.location.origin)}function _r(t){let e=`${lr}${t}`;try{let n=window.sessionStorage.getItem(e);if(n)return n;let r=ie(t);return window.sessionStorage.setItem(e,r),r}catch{return ie(t)}}function ie(t){let e=window.crypto?.randomUUID?.()||`${Date.now()}-${Math.random().toString(16).slice(2)}`;return`${t}-${e}`.slice(0,120)}var ce=mr(),se=ne(x,ce,ur),d={siteId:se,get sessionId(){return _r(se)},apiUrl:yr(ce),useWebSocket:L(x?.getAttribute("data-use-websocket")).toLowerCase()==="true",autoGreet:L(x?.getAttribute("data-auto-greet")).toLowerCase()!=="false",brandName:L(x?.getAttribute("data-brand"))||dr,assistantTitle:L(x?.getAttribute("data-assistant-title"))||pr,speechVoiceName:L(x?.getAttribute("data-speech-voice")),speechVoicePreference:L(x?.getAttribute("data-speech-voice-preference"))||fr};function ue(){let t=document.createElement("div");return t.id="mayabot-widget",t.innerHTML=`
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
  `,document.body.appendChild(t),t.querySelector(".mayabot-kicker").textContent=d.brandName,t.querySelector(".mayabot-title").textContent=d.assistantTitle,{btn:document.getElementById("mayabot-btn"),chat:document.getElementById("mayabot-chat"),msgs:document.getElementById("mayabot-msgs"),status:document.getElementById("mayabot-status")}}function j(t,e,n){t.chat.classList.add("visible");let r=document.createElement("div");return r.className=`mayabot-msg ${n}`,r.innerText=e,t.msgs.appendChild(r),t.msgs.scrollTop=t.msgs.scrollHeight,r}function ht(t,e,n){e&&(e.innerText=n,t.msgs.scrollTop=t.msgs.scrollHeight)}var s=Object.freeze({ADD_TO_CART:"ADD_TO_CART",BOOK_APPOINTMENT_REQUEST:"BOOK_APPOINTMENT_REQUEST",BUILD_ITINERARY:"BUILD_ITINERARY",BUILD_LEARNING_PATH:"BUILD_LEARNING_PATH",CAPTURE_LEAD:"CAPTURE_LEAD",CAPTURE_PATIENT_LEAD:"CAPTURE_PATIENT_LEAD",CHECKOUT:"CHECKOUT",CHECKOUT_HANDOFF:"CHECKOUT_HANDOFF",CHECK_APPOINTMENT_AVAILABILITY:"CHECK_APPOINTMENT_AVAILABILITY",CHECK_AVAILABILITY:"CHECK_AVAILABILITY",CHECK_DELIVERY_AVAILABILITY:"CHECK_DELIVERY_AVAILABILITY",CHECK_ELIGIBILITY_SOFT:"CHECK_ELIGIBILITY_SOFT",CHECK_PREREQUISITES:"CHECK_PREREQUISITES",CLEAR_CART:"CLEAR_CART",CLEAR_FILTERS:"CLEAR_FILTERS",CLEAR_HISTORY:"CLEAR_HISTORY",COMPARE_ENTITIES:"COMPARE_ENTITIES",CONTACT_AGENT:"CONTACT_AGENT",FILTER_ENTITIES:"FILTER_ENTITIES",FILTER_PRODUCTS:"FILTER_PRODUCTS",HANDOFF_TO_ADVISOR:"HANDOFF_TO_ADVISOR",HANDOFF_TO_AGENT:"HANDOFF_TO_AGENT",HANDOFF_TO_CLINIC:"HANDOFF_TO_CLINIC",HANDOFF_TO_HUMAN:"HANDOFF_TO_HUMAN",HANDOFF_TO_LAWYER:"HANDOFF_TO_LAWYER",HANDOFF_TO_LICENSED_AGENT:"HANDOFF_TO_LICENSED_AGENT",HANDOFF_TO_RECRUITER:"HANDOFF_TO_RECRUITER",JOIN_WAITLIST:"JOIN_WAITLIST",MATCH_JOBS:"MATCH_JOBS",NAVIGATE_TO:"NAVIGATE_TO",OPEN_CLAIM_FLOW:"OPEN_CLAIM_FLOW",OPEN_CONTACT:"OPEN_CONTACT",OPEN_DISCLOSURE:"OPEN_DISCLOSURE",OPEN_ENTITY_DETAIL:"OPEN_ENTITY_DETAIL",OPEN_LOCATION:"OPEN_LOCATION",OPEN_MAP:"OPEN_MAP",OPEN_POLICY:"OPEN_POLICY",OPEN_PROJECTS:"OPEN_PROJECTS",OPEN_RENEWAL_FLOW:"OPEN_RENEWAL_FLOW",OPEN_SERVICES:"OPEN_SERVICES",OPEN_SYLLABUS:"OPEN_SYLLABUS",OPEN_TELECONSULT:"OPEN_TELECONSULT",REMOVE_FROM_CART:"REMOVE_FROM_CART",REQUEST_APPOINTMENT:"REQUEST_APPOINTMENT",REQUEST_CALLBACK:"REQUEST_CALLBACK",REQUEST_CONSULTATION:"REQUEST_CONSULTATION",REQUEST_COUNSELOR_CALLBACK:"REQUEST_COUNSELOR_CALLBACK",REQUEST_ESTIMATE:"REQUEST_ESTIMATE",REQUEST_SITE_VISIT:"REQUEST_SITE_VISIT",REQUEST_TEST_DRIVE:"REQUEST_TEST_DRIVE",REQUEST_VIEWING:"REQUEST_VIEWING",RUN_AFFORDABILITY_CALCULATOR:"RUN_AFFORDABILITY_CALCULATOR",RUN_CALCULATOR:"RUN_CALCULATOR",RUN_DOM_SEQUENCE:"RUN_DOM_SEQUENCE",SAVE_SEARCH:"SAVE_SEARCH",SCHEDULE_ORDER:"SCHEDULE_ORDER",SEARCH_AVAILABILITY:"SEARCH_AVAILABILITY",SET_LOCATION:"SET_LOCATION",SHOW_COMPARISON:"SHOW_COMPARISON",SHOW_EMERGENCY_NOTICE:"SHOW_EMERGENCY_NOTICE",SHOW_ENTITIES:"SHOW_ENTITIES",SHOW_PRODUCT_DETAIL:"SHOW_PRODUCT_DETAIL",SHOW_PRODUCTS:"SHOW_PRODUCTS",SORT_ENTITIES:"SORT_ENTITIES",SORT_PRODUCTS:"SORT_PRODUCTS",START_APPLICATION:"START_APPLICATION",START_BOOKING:"START_BOOKING",START_ENROLLMENT:"START_ENROLLMENT",START_INTAKE:"START_INTAKE",START_QUOTE:"START_QUOTE",START_TICKET_PURCHASE:"START_TICKET_PURCHASE",UPDATE_CART_QUANTITY:"UPDATE_CART_QUANTITY",UPDATE_PREFERENCES:"UPDATE_PREFERENCES"}),l=Object.freeze({ENTITY_ID:"entity_id",ENTITY_IDS:"entity_ids",MESSAGE:"message",PAGE:"page",PRODUCT_ID:"product_id",PRODUCT_IDS:"product_ids",QUANTITY:"quantity",REASON:"reason",SEARCH_QUERY:"search_query",URL:"url"}),ii=Object.freeze({BLOCKED:"blocked",EXECUTING:"executing",FAILED:"failed",REQUESTED:"requested",SKIPPED:"skipped",SUCCEEDED:"succeeded",UNKNOWN:"unknown"}),E=Object.freeze({KNOWLEDGE_BY_IDS:"/v1/knowledge/by-ids",PRODUCTS_BY_IDS:"/v1/products/by-ids",SHOP:"/v1/shop",SHOP_WS:"/v1/ws/shop",WIDGET_STATUS:"/v1/widget/status"}),S=Object.freeze({AUDIO_CHUNK:"audio_chunk",AUDIO_END:"audio_end",CONFIG:"config",DONE:"done",ERROR:"error",TEXT_CHUNK:"text_chunk",TRANSCRIPT:"transcript"});var le=new Set(["cart","/cart"]),R="Recommended products",P="Relevant options",z=Object.freeze({DATA_WAV_PREFIX:"data:audio/wav;base64,",WEBM_FILENAME:"audio.webm",WEBM_MIME_TYPE:"audio/webm"}),de=Object.freeze({POST:"POST"}),m=Object.freeze({ERROR:"error",PROCESSING:"processing",READY:"ready",RECORDING:"recording"}),pe=12,fe=2400,me=900,ye=4200,gt=1,k=180,_e=3e3,W=Object.freeze({MAYABOT_ACTION:"mayabot:action"}),he=2500;var hr=["audio/webm;codecs=opus","audio/webm","audio/ogg;codecs=opus","audio/ogg","audio/mp4"],gr=250,br=128;function ge(t,e){let n=null,r=null,o=[],a=!1,i=!1,c=!1;async function f(){if(!(i||a)){i=!0;try{let _=await navigator.mediaDevices.getUserMedia({audio:!0});r=_,c=!1;let D=Tr();n=new MediaRecorder(_,D?{mimeType:D}:void 0),o=[],n.ondataavailable=p=>{p.data.size>0&&o.push(p.data)},n.onstop=async()=>{let p=new Blob(o,{type:n.mimeType||D||z.WEBM_MIME_TYPE});if(v(),c){c=!1;return}if(p.size<br){console.warn("Microphone recording was empty or too short",{size:p.size}),e(m.READY);return}await t(p)},n.onerror=p=>{console.error("Microphone recording failed",p.error||p),a=!1,i=!1,v(),e(m.ERROR,"Recording failed")},n.start(gr),a=!0,e(m.RECORDING)}catch(_){console.error("Microphone access denied",_),e(m.ERROR,"Mic unavailable")}finally{i=!1}}}function h({discard:_=!1}={}){if(c=_,n&&n.state!=="inactive"){try{n.requestData()}catch{}n.stop(),a=!1,_||e(m.PROCESSING);return}a=!1,v(),_||e(m.PROCESSING)}function g(){i||(a?h():f())}function b(){h({discard:!0})}function v(){r&&(r.getTracks().forEach(_=>_.stop()),r=null)}return{toggle:g,cancel:b}}function Tr(){return!("MediaRecorder"in window)||typeof MediaRecorder.isTypeSupported!="function"?"":hr.find(t=>MediaRecorder.isTypeSupported(t))||""}var be="shopify",Te="woocommerce",Ar="custom";function J(t){let e=String(t||"").trim();return/^\d+$/.test(e)?e:""}function Z(t,e=1){let n=Number(t?.[l.QUANTITY]);return Number.isFinite(n)&&n>0?Math.floor(n):e}async function U(t,e){return(await fetch(new URL(t,window.location.origin),{method:"POST",headers:{Accept:"application/json","Content-Type":"application/json"},body:JSON.stringify(e),credentials:"same-origin"})).ok}function Er(){return Sr()?be:Ir()?Te:Ar}async function Ae(t){let e=Er();return e===be?Or(t):e===Te?wr(t):!1}function Sr(){return!!(window.Shopify||document.querySelector('meta[name="shopify-checkout-api-token"]')||document.querySelector('script[src*="cdn.shopify.com"]'))}function Ir(){return!!(document.body?.classList?.contains("woocommerce")||window.wc_add_to_cart_params||document.querySelector('link[href*="woocommerce"], script[src*="woocommerce"]'))}async function Or(t){let e=t.parameters||{};if(t.action===s.ADD_TO_CART){let n=J(e.variant_id||e.cart_id||e[l.PRODUCT_ID]);return n?U("/cart/add.js",{items:[{id:n,quantity:Z(e)}]}):!1}if(t.action===s.REMOVE_FROM_CART){let n=J(e.cart_id||e.variant_id||e[l.PRODUCT_ID]);return n?U("/cart/change.js",{id:n,quantity:0}):!1}if(t.action===s.UPDATE_CART_QUANTITY){let n=J(e.cart_id||e.variant_id||e[l.PRODUCT_ID]);return n?U("/cart/change.js",{id:n,quantity:Z(e,0)}):!1}return t.action===s.CLEAR_CART?U("/cart/clear.js",{}):t.action===s.CHECKOUT?tt("/checkout"):Ee(t)?tt("/cart"):!1}async function wr(t){let e=t.parameters||{};if(t.action===s.ADD_TO_CART){let n=J(e.variant_id||e.cart_id||e[l.PRODUCT_ID]);return n?U("/wp-json/wc/store/cart/add-item",{id:Number(n),quantity:Z(e)}):!1}if(t.action===s.REMOVE_FROM_CART){let n=String(e.cart_key||e.key||"").trim();return n?U("/wp-json/wc/store/cart/remove-item",{key:n}):!1}if(t.action===s.UPDATE_CART_QUANTITY){let n=String(e.cart_key||e.key||"").trim();return n?U("/wp-json/wc/store/cart/update-item",{key:n,quantity:Z(e,0)}):!1}return t.action===s.CHECKOUT?tt("/checkout"):Ee(t)?tt("/cart"):!1}function Ee(t){return t.action===s.NAVIGATE_TO&&le.has(t.parameters?.[l.PAGE])}function tt(t){return window.location.href=t,!0}var xr="/v1/widget/action-event";function T(t){return String(t||"").trim()}function Rr(t,e){return new URL(t,e).toString()}function Cr(t){return!t||typeof t!="object"?[]:Object.keys(t).map(e=>T(e)).filter(Boolean).slice(0,20)}function Nr(t){if(!t||typeof t!="object")return{};let e={};for(let[n,r]of Object.entries(t).slice(0,20)){let o=T(n).slice(0,80);o&&(typeof r=="boolean"||r===null?e[o]=r:typeof r=="number"?e[o]=Number.isFinite(r)?r:0:e[o]=T(r).slice(0,240))}return e}async function et(t,e,n,r){if(!t||!e||!n?.action)return;let o=JSON.stringify({site_id:e,origin:window.location.origin,url:window.location.href,occurred_at:new Date().toISOString(),request_id:T(n.request_id||n.action_request_id),turn_id:T(n.turn_id),sequence:Number(n.sequence||0),action:T(n.action).toUpperCase(),status:T(r?.status)||"unknown",stage:T(r?.stage),reason:T(r?.reason),duration_ms:Number(r?.duration_ms||0),param_keys:Cr(n.parameters||n.params),requested_url:T(r?.requested_url),final_url:T(r?.final_url||window.location.href),evidence:Nr(r?.evidence)}),a=Rr(xr,t);if(!Lr(a,o))try{await fetch(a,{method:"POST",headers:{Accept:"application/json","Content-Type":"application/json"},body:o,keepalive:!0})}catch(i){console.warn("[AIHubAdapter] Action execution report failed.",i)}}function Lr(t,e){if(typeof navigator>"u"||typeof navigator.sendBeacon!="function"||typeof Blob!="function")return!1;try{return navigator.sendBeacon(t,new Blob([e],{type:"application/json"}))}catch{return!1}}function Se(t){if(!t||typeof t!="string")return[];let e=[];for(let n of Pr()){try{e.push(...Array.from(n.querySelectorAll(t)))}catch{return[]}if(e.length>=600)return e.slice(0,600)}return Mr(e)}function Pr(){let t=[],e=new Set,n=[document];for(;n.length&&t.length<60;){let r=n.shift();!r||e.has(r)||(e.add(r),t.push(r),n.push(...vr(r)))}return t}function vr(t){let e=[];for(let n of Dr(t)){n.shadowRoot&&e.push(n.shadowRoot);let r=Ur(n);r&&e.push(r)}return e}function Dr(t){try{return Array.from(t.querySelectorAll("*"))}catch{return[]}}function Ur(t){if(String(t?.tagName||"").toLowerCase()!=="iframe")return null;try{let e=t.contentDocument;return e?.documentElement?e:null}catch{return null}}function Mr(t){return Array.from(new Set(t))}var _i=Object.freeze([u("stripe",["stripe","stripe.com","checkout.stripe.com","js.stripe.com"]),u("paypal",["paypal","paypal.com","paypalobjects.com"]),u("razorpay",["razorpay","checkout.razorpay.com"]),u("paytm",["paytm","securegw.paytm.in"]),u("cashfree",["cashfree","cashfree.com"]),u("checkout.com",["checkout.com","cko-session-id"]),u("adyen",["adyen","checkoutshopper"]),u("square",["squareup","squarecdn","square.site"]),u("braintree",["braintree","braintreegateway"]),u("mollie",["mollie","mollie.com"]),u("klarna",["klarna","klarna.com"]),u("afterpay",["afterpay","afterpay.com","clearpay"]),u("payu",["payu","payu.in","payu.com"]),u("paystack",["paystack","paystack.co"]),u("phonepe",["phonepe","phonepe.com"]),u("billdesk",["billdesk","billdesk.com"]),u("authorize.net",["authorize.net","accept.authorize.net"])]),Ie=Object.freeze([u("calendly",["calendly","calendly.com"]),u("acuity",["acuityscheduling","squarespace scheduling"]),u("booksy",["booksy","booksy.com"]),u("zocdoc",["zocdoc","zocdoc.com"]),u("appointlet",["appointlet","appointlet.com"]),u("setmore",["setmore","setmore.com"]),u("cal.com",["cal.com","calcom"]),u("google_calendar",["calendar.google.com","google calendar"]),u("microsoft_bookings",["microsoft bookings","outlook.office365.com/book"]),u("simplybook",["simplybook","simplybook.me"]),u("tidycal",["tidycal","tidycal.com"]),u("savvycal",["savvycal","savvycal.com"]),u("fresha",["fresha","fresha.com"])]),Oe=Object.freeze([u("google_maps",["google.com/maps","maps.googleapis","maps.google"]),u("mapbox",["mapbox","mapbox.com"]),u("openstreetmap",["openstreetmap","osm.org"]),u("leaflet",["leaflet","leafletjs"]),u("here_maps",["here.com","hereapi","wego.here.com"]),u("bing_maps",["bing.com/maps","virtualearth"]),u("mappls",["mappls","mapmyindia"])]),we=Object.freeze([u("whatsapp",["wa.me","api.whatsapp.com","web.whatsapp.com"]),u("telegram",["t.me/","telegram.me"]),u("messenger",["m.me/","messenger.com/t"]),u("zendesk",["zendesk.com","zdassets.com/hc"]),u("intercom",["intercom.help","intercom.com"]),u("freshchat",["freshchat.com"])]),hi=Object.freeze([u("recaptcha",["recaptcha","g-recaptcha","google.com/recaptcha"]),u("hcaptcha",["hcaptcha","h-captcha"]),u("turnstile",["turnstile","challenges.cloudflare.com"]),u("cloudflare_challenge",["cf-chl","cloudflare challenge"])]);function u(t,e){return{name:t,tokens:e}}function bt(t,e,n=10){let r=Tt(t);return e.filter(o=>o.tokens.some(a=>r.includes(a))).map(o=>o.name).slice(0,n)}function Tt(t){return String(t||"").replace(/\s+/g," ").trim().toLowerCase()}var xe="a[href], iframe[src]",kr="a[href]",Ce=new Set(["http:","https:"]),nt=new Set(["mailto:","tel:"]),Fr=Object.freeze([l.URL,"href","link","target_url","provider_url","booking_url","appointment_url","calendar_url","map_url","location_url","contact_url"]),Ne=new Set([s.OPEN_MAP,s.OPEN_LOCATION,s.SET_LOCATION]),Le=new Set([s.CHECK_APPOINTMENT_AVAILABILITY,s.REQUEST_APPOINTMENT,s.BOOK_APPOINTMENT_REQUEST,s.REQUEST_CONSULTATION,s.REQUEST_SITE_VISIT,s.START_BOOKING]),Pe=new Set([s.OPEN_CONTACT,s.CONTACT_AGENT,s.REQUEST_CALLBACK,s.REQUEST_COUNSELOR_CALLBACK,s.HANDOFF_TO_ADVISOR,s.HANDOFF_TO_AGENT,s.HANDOFF_TO_CLINIC,s.HANDOFF_TO_HUMAN,s.HANDOFF_TO_LAWYER,s.HANDOFF_TO_LICENSED_AGENT,s.HANDOFF_TO_RECRUITER]);function ve(t){let e=Me(t);return Ne.has(e)||Le.has(e)||Pe.has(e)}async function De(t){let e=Me(t);return Ne.has(e)?At(t,Oe,xe,Et):Le.has(e)?At(t,Ie,xe,Et):Pe.has(e)?At(t,we,kr,$r):!1}function At(t,e,n,r){let o=Hr(t?.parameters||t?.params||{},e,r);if(o)return Re(o);let a=Br(n,e,r);return a?Re(a):!1}function Hr(t,e,n){for(let r of Fr){let o=Ue(t?.[r]);if(o&&n(o,e))return o}return null}function Br(t,e,n){for(let r of Se(t)){let o=Yr(r);if(!(!o||!n(o,e))&&jr(o,r,e))return o}return null}function Yr(t){return Ue(t?.getAttribute?.("href")||t?.getAttribute?.("src"))}function Et(t,e){return Ce.has(t.protocol)&&bt(t.href,e).length>0}function $r(t,e){return nt.has(t.protocol)?!0:Et(t,e)}function jr(t,e,n){if(nt.has(t.protocol))return!0;let r=[t.href,e?.textContent||"",e?.getAttribute?.("aria-label")||"",e?.getAttribute?.("title")||""].join(" ");return bt(Tt(r),n).length>0}function Re(t){if(nt.has(t.protocol)||t.origin===window.location.origin)return window.location.href=t.href,!0;let e=window.open(t.href,"_blank","noopener,noreferrer");return e?(e.opener=null,!0):(window.location.href=t.href,!0)}function Ue(t){let e=String(t||"").trim();if(!e||e.startsWith("#"))return null;try{let n=new URL(e,window.location.href);return Ce.has(n.protocol)||nt.has(n.protocol)?n:null}catch{return null}}function Me(t){return String(t?.action||"").trim().toUpperCase()}var zr=Object.freeze(["title","name"]),Wr=Object.freeze(["summary","description","body"]),Vr=Object.freeze(["image_url","imageUrl","image","thumbnail"]),Gr=Object.freeze(["url","href","permalink","source_url"]),qr="knowledge_item",Kr=30;function I(t){return t==null||typeof t=="object"?"":String(t||"").trim()}function Qr(t){let e=new Set;return(Array.isArray(t)?t:[]).map(I).filter(Boolean).filter(n=>e.has(n)||e.size>=Kr?!1:(e.add(n),!0))}function rt(t,e){for(let n of e){let r=I(t?.[n]);if(r)return r}return""}function V(t){return t&&typeof t=="object"&&!Array.isArray(t)?t:{}}function Xr(t){let e=Jr([t?.price,t?.amount,t?.premium,t?.premium_min,t?.monthly_premium,t?.annual_premium,t?.min_price,t?.starting_price]),n=I(t?.currency||"INR");return!Number.isFinite(e)||e<=0?"":`${n} ${e.toLocaleString()}`}function Jr(t){for(let e of t){let n=Number(String(e??"").replace(/,/g,""));if(Number.isFinite(n)&&n>0)return n}return 0}function Zr(t){return!t||typeof t!="object"?"":t.in_stock===!0?"Available":t.in_stock===!1?"Unavailable":I(t.status||t.availability||"")}function to(t){let e=I(t);if(!e)return"";try{let n=new URL(e,window.location.origin);return/^https?:$/i.test(n.protocol)?n.origin===window.location.origin?`${n.pathname}${n.search}${n.hash}`:n.toString():""}catch{return""}}function eo(t){if(!t)return null;let e=I(t.id);if(!e)return null;let n=V(t.pricing),r=V(t.availability);return{id:e,externalId:I(t.external_id),entityType:I(t.entity_type||t.category_name)||qr,title:rt(t,zr)||e,subtitle:I(t.subtitle||t.category_name||t.entity_type),summary:rt(t,Wr),body:I(t.body),url:to(rt(t,Gr)),imageUrl:rt(t,Vr),attributes:V(t.attributes),pricing:n,availability:r,location:V(t.location),contact:V(t.contact),displayPrice:Xr(n),displayAvailability:Zr(r)}}async function St(t){let e=Qr(t);if(!e.length)return[];let n=new URL(E.KNOWLEDGE_BY_IDS,d.apiUrl);n.searchParams.set("site_id",d.siteId),n.searchParams.set("ids",e.join(","));let r=await fetch(n.toString(),{headers:{Accept:"application/json"}});if(!r.ok)throw new Error("Failed to fetch entities from AI Hub API");let o=(await r.json()).map(eo).filter(Boolean),a=new Map(o.map(i=>[String(i.id),i]));return e.map(i=>a.get(i)).filter(Boolean)}async function ke(t){let[e]=await St([t]);return e?.url||""}function Fe(){if(document.getElementById("mayabot-entity-overlay-styles"))return;let t=document.createElement("style");t.id="mayabot-entity-overlay-styles",t.textContent=`
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
  `,document.head.appendChild(t)}var no=2,He=Number.POSITIVE_INFINITY,ot=Number.NEGATIVE_INFINITY,Be=12,Ot=[],wt=P;function C(t){return String(t??"").replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;").replace(/"/g,"&quot;").replace(/'/g,"&#039;")}function ze(t){return String(t||"item").replace(/[_-]+/g," ").trim().split(/\s+/).slice(0,no).join(" ")}function ro(){Fe();let t=document.getElementById("mayabot-entity-panel");return t||(t=document.createElement("div"),t.id="mayabot-entity-panel",t.setAttribute("aria-live","polite"),t.innerHTML=`
    <div class="mayabot-entity-header">
      <h2 class="mayabot-entity-title">${P}</h2>
      <button class="mayabot-entity-close" type="button" aria-label="Close recommendations">&times;</button>
    </div>
    <div class="mayabot-entity-grid"></div>
  `,t.querySelector(".mayabot-entity-close").addEventListener("click",()=>{t.classList.remove("active")}),document.body.appendChild(t),t)}function oo(t){return t<=1?"count-1":t===2?"count-2":t===3?"count-3":"count-many"}function ao(t){return t<=1?1:t===2?2:3}function It(t,e,n=""){let r=(Array.isArray(e)?e:[]).map(c=>String(c?.id??"").trim()).filter(Boolean),o=r.length,a=t.length,i=o>0?"succeeded":"failed";return{status:i,stage:"entity_overlay",reason:n||(i==="succeeded"?"":"no_matching_entities_rendered"),evidence:{requested_entity_count:a,rendered_entity_count:o,missing_entity_count:Math.max(a-o,0),requested_entity_ids:t.slice(0,Be).join(","),rendered_entity_ids:r.slice(0,Be).join(",")}}}function io(t){return[t.displayPrice,t.displayAvailability,t.location?.city,t.attributes?.category].map(e=>String(e||"").trim()).filter(Boolean).slice(0,3)}function so(t){return t.imageUrl?`
      <div class="mayabot-entity-media">
        <img src="${C(t.imageUrl)}" alt="${C(t.title)}">
      </div>
    `:`
    <div class="mayabot-entity-media">
      <div class="mayabot-entity-badge">${C(ze(t.entityType))}</div>
    </div>
  `}function co(t){let e=io(t);return e.length?`
    <div class="mayabot-entity-facts">
      ${e.map(n=>`<span class="mayabot-entity-fact">${C(n)}</span>`).join("")}
    </div>
  `:""}function uo(t){return t.url?`
    <div class="mayabot-entity-actions">
      <button type="button" data-view-entity="${C(t.id)}">Open</button>
    </div>
  `:""}function it(t,e){let n=ro(),r=n.querySelector(".mayabot-entity-grid"),o=n.querySelector(".mayabot-entity-title"),a=t.length;if(Ot=Array.isArray(t)?[...t]:[],wt=e||P,n.classList.remove("count-1","count-2","count-3","count-many"),n.classList.add(oo(a)),n.style.setProperty("--mayabot-entity-card-count",String(ao(a))),o.textContent=wt,!a){r.innerHTML='<p class="mayabot-entity-empty">No matching records are currently available.</p>',n.classList.add("active"),Ye();return}r.innerHTML=t.map(i=>`
        <article class="mayabot-entity-card" data-entity-id="${C(i.id)}">
          ${so(i)}
          <h3 class="mayabot-entity-name">${C(i.title)}</h3>
          <p class="mayabot-entity-meta">${C(i.subtitle||ze(i.entityType))}</p>
          <p class="mayabot-entity-summary">${C(i.summary||i.body||"Details are available on the website.")}</p>
          ${co(i)}
          ${uo(i)}
        </article>
      `).join(""),r.querySelectorAll("[data-view-entity]").forEach(i=>{i.addEventListener("click",async()=>{await xt(i.getAttribute("data-view-entity"))})}),n.classList.add("active"),Ye()}function lo(t){if(!t)return!1;try{let e=new URL(t,window.location.origin);return e.origin===window.location.origin?(window.location.href=`${e.pathname}${e.search}${e.hash}`,!0):(window.open(e.toString(),"_blank","noopener,noreferrer"),!0)}catch{return!1}}function Ye(){window.setTimeout(()=>{let t=document.getElementById("mayabot-chat"),e=document.getElementById("mayabot-msgs");e&&(e.innerHTML=""),t&&t.classList.remove("visible")},k)}async function xt(t){let e=await ke(t);return lo(e)}async function We(t,e=P){let n=Rt({[l.ENTITY_IDS]:t});if(!n.length)return it([],e),It([],[],"missing_entity_ids");try{let r=await St(n);return it(r,e),It(n,r)}catch(r){return console.warn("[AI Hub Widget] Entity overlay failed:",r),it([],e),It(n,[],"entity_overlay_fetch_failed")}}function Rt(t){let e=t[l.ENTITY_IDS]||t.ids||t.items||[],n=new Set;return(Array.isArray(e)?e:[]).map(r=>String(r??"").trim()).filter(Boolean).filter(r=>n.has(r)?!1:(n.add(r),!0))}function Ve(t={}){if(!Ot.length)return!1;let e=String(t.sort_by||t.sortBy||"price_asc").trim().toLowerCase(),n=[...Ot].sort((o,a)=>po(o,a,e)),r=mo(wt,e);return it(n,r),!0}function po(t,e,n){return n==="price_desc"?at(e,ot)-at(t,ot):n==="rating"?$e(e,ot)-$e(t,ot):n==="newest"?je(e)-je(t):at(t,He)-at(e,He)}function at(t,e){return Ge([t?.pricing?.price,t?.pricing?.amount,t?.pricing?.premium,t?.pricing?.premium_min,t?.pricing?.monthly_premium,t?.pricing?.annual_premium,t?.pricing?.min_price,t?.pricing?.starting_price,t?.attributes?.price,t?.attributes?.amount,t?.attributes?.premium,t?.attributes?.monthly_premium,t?.attributes?.annual_premium,t?.displayPrice],e)}function $e(t,e){return Ge([t?.attributes?.rating,t?.attributes?.review_rating,t?.attributes?.stars,t?.availability?.rating],e)}function je(t){let e=t?.attributes?.updated_at||t?.attributes?.date||t?.availability?.updated_at||"",n=Date.parse(String(e||""));return Number.isFinite(n)?n:0}function Ge(t,e){for(let n of t){let r=fo(n);if(Number.isFinite(r))return r}return e}function fo(t){if(typeof t=="number")return t;let e=String(t??"").replace(/,/g,"").match(/-?\d+(?:\.\d+)?/);return e?Number(e[0]):Number.NaN}function mo(t,e){let n={price_asc:"sorted low to high",price_desc:"sorted high to low",rating:"sorted by rating",newest:"newest first"};return`${String(t||P).replace(/\s+-\s+sorted.*$/i,"")} - ${n[e]||n.price_asc}`}function qe(t){return t.action===s.SHOW_ENTITIES||t.action===s.COMPARE_ENTITIES||t.action===s.OPEN_ENTITY_DETAIL||t.action===s.SORT_ENTITIES}async function Ke(t){return t.action===s.SHOW_ENTITIES||t.action===s.COMPARE_ENTITIES?yo(t.parameters||{}):t.action===s.OPEN_ENTITY_DETAIL?xt(t.parameters?.[l.ENTITY_ID]||t.parameters?.id):t.action===s.SORT_ENTITIES?Ve(t.parameters||{}):!1}function yo(t){return We(Rt(t),t[l.SEARCH_QUERY]||t.title||P)}var G="mayabot-handoff-panel",Qe="mayabot-handoff-overlay-styles",_o=Object.freeze(["contact","support","help"]),ho=Object.freeze(["checkout","cart"]),tn=new Set([s.CHECKOUT_HANDOFF,s.HANDOFF_TO_ADVISOR,s.HANDOFF_TO_AGENT,s.HANDOFF_TO_CLINIC,s.HANDOFF_TO_HUMAN,s.HANDOFF_TO_LAWYER,s.HANDOFF_TO_LICENSED_AGENT,s.HANDOFF_TO_RECRUITER]),Xe=Object.freeze({[s.CHECKOUT_HANDOFF]:{title:"Checkout needs your confirmation",body:"This step may include payment or a secure checkout page. I can take you there, then you complete the final step yourself.",primary:"Open checkout"},[s.HANDOFF_TO_ADVISOR]:{title:"Advisor handoff",body:"This request needs a qualified advisor. I can open the contact path so the site team can continue.",primary:"Contact advisor"},[s.HANDOFF_TO_AGENT]:{title:"Agent handoff",body:"This step needs an agent or account-specific help. I can open the contact path for follow-up.",primary:"Contact agent"},[s.HANDOFF_TO_CLINIC]:{title:"Clinic handoff",body:"This request needs clinic confirmation. I can open the appointment or contact path for the next step.",primary:"Contact clinic"},[s.HANDOFF_TO_HUMAN]:{title:"Human handoff",body:"This step needs human confirmation. I can open the most relevant contact path.",primary:"Open contact"},[s.HANDOFF_TO_LAWYER]:{title:"Legal handoff",body:"This request needs a legal professional. I can open the consultation or contact path.",primary:"Contact lawyer"},[s.HANDOFF_TO_LICENSED_AGENT]:{title:"Licensed agent handoff",body:"This request needs a licensed agent. I can open the quote or contact path for follow-up.",primary:"Contact agent"},[s.HANDOFF_TO_RECRUITER]:{title:"Recruiter handoff",body:"This request needs recruiter review. I can open the application or contact path.",primary:"Contact recruiter"}});function F(t){return String(t??"").replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;").replace(/"/g,"&quot;").replace(/'/g,"&#039;")}function M(t){return String(t||"").trim()}function go(){if(document.getElementById(Qe))return;let t=document.createElement("style");t.id=Qe,t.textContent=`
    #${G} {
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
    #${G}.active {
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
      #${G} {
        bottom: 82px;
        width: min(calc(100vw - 20px), 420px);
      }
    }
  `,document.head.appendChild(t)}function bo(){go();let t=document.getElementById(G);return t||(t=document.createElement("div"),t.id=G,t.setAttribute("aria-live","polite"),document.body.appendChild(t),t)}function To(){return window.AIHubAdapterRuntime?.config?.adapter?.routes||window.AIHubAdapter?.config?.adapter?.routes||{}}function Ao(t,e){let n=Je(e[l.URL]||e.path||e.href||e.handoff_flow?.page_url);if(n)return n;let r=To(),o=t===s.CHECKOUT_HANDOFF?ho:_o;for(let a of o){let i=Je(r[a]);if(i)return i}return""}function Je(t){let e=M(t);if(!e)return"";try{let n=new URL(e,window.location.origin);return n.origin!==window.location.origin?"":`${n.pathname}${n.search}${n.hash}`||"/"}catch{return""}}function Eo(t){return Xe[t]||Xe[s.HANDOFF_TO_HUMAN]}function So(t){return t&&typeof t=="object"?t:{}}function Io(t,e){return M(t.title)||e}function Oo(t,e,n){return M(e[l.MESSAGE])||M(t.handling)||n}function wo(t,e){return M(e[l.REASON]||e.reason||e.blocked_reason||t.key)}function xo(t){let e=[["Provider",t.provider_label||t.provider],["Boundary",t.automation_boundary],["Recovery",t.recovery],["Evidence",t.evidence],["Page",t.page_url]].filter(([,n])=>M(n));return e.length?`
    <p class="mayabot-handoff-meta">
      ${e.map(([n,r])=>`<span><strong>${F(n)}:</strong> ${F(r)}</span>`).join("")}
    </p>
  `:""}function Ze(t){t.classList.remove("active")}function Ro(){window.setTimeout(()=>{let t=document.getElementById("mayabot-chat"),e=document.getElementById("mayabot-msgs");e&&(e.innerHTML=""),t&&t.classList.remove("visible")},k)}function en(t,e={}){let n=M(t).toUpperCase(),r=Eo(n),o=So(e.handoff_flow),a=bo(),i=Ao(n,e),c=Io(o,r.title),f=Oo(o,e,r.body),h=wo(o,e);return a.innerHTML=`
    <div class="mayabot-handoff-body">
      <div class="mayabot-handoff-top">
        <h2 class="mayabot-handoff-title">${F(c)}</h2>
        <button class="mayabot-handoff-close" type="button" aria-label="Close handoff">&times;</button>
      </div>
      <p class="mayabot-handoff-text">${F(f)}</p>
      ${xo(o)}
      ${h?`<p class="mayabot-handoff-reason">${F(h)}</p>`:""}
      <div class="mayabot-handoff-actions">
        <button type="button" class="secondary" data-close-handoff>Close</button>
        ${i?`<button type="button" data-open-handoff>${F(r.primary)}</button>`:""}
      </div>
    </div>
  `,a.querySelector(".mayabot-handoff-close")?.addEventListener("click",()=>Ze(a)),a.querySelector("[data-close-handoff]")?.addEventListener("click",()=>Ze(a)),a.querySelector("[data-open-handoff]")?.addEventListener("click",()=>{window.location.href=i}),a.classList.add("active"),Ro(),!0}function nn(t){return tn.has(t.action)}function rn(t){return en(t.action,t.parameters||{})}function an(t){return t.action===s.NAVIGATE_TO&&!!cn(t.parameters?.[l.PAGE])}function sn(t){return window.location.href=cn(t.parameters?.[l.PAGE]),!0}function cn(t){let e=String(t||"").trim();if(!e||un(e)||/^https?:\/\//i.test(e))return"";if(e==="home"||e==="/")return"/";let n=Co(e);if(n)return n;let r=e.replace(/^\/+|\/+$/g,"");return r?`/${r}`:"/"}function Co(t){let e=window.AIHubAdapterRuntime?.config?.adapter?.routes||window.AIHubAdapter?.config?.adapter?.routes||{},n=No(t);for(let r of n){let o=e[r],a=on(o);if(a)return a}for(let[r,o]of Object.entries(e)){if(!n.includes(Ct(r)))continue;let a=on(o);if(a)return a}return""}function No(t){let e=Ct(t),n=String(t||"").trim().replace(/^\/+|\/+$/g,"").toLowerCase(),r=n.split("?")[0].split("#")[0].split("/").filter(Boolean).pop()||"";return Array.from(new Set([e,n,Ct(r)].filter(Boolean)))}function Ct(t){return String(t||"").trim().toLowerCase().replace(/[^a-z0-9/_\s-]+/g," ").replace(/[_-]+/g," ").replace(/\s+/g," ").trim().replace(/\s+/g,"-")}function on(t){let e=String(t||"").trim();if(!e||un(e))return"";if(/^https?:\/\//i.test(e))try{let n=new URL(e);return n.origin!==window.location.origin?"":`${n.pathname||"/"}${n.search||""}${n.hash||""}`}catch{return""}return e.startsWith("/")?e:`/${e.replace(/^\/+/,"")}`}function un(t){return/^(?:javascript:|data:|\/\/)/i.test(String(t||"").trim())}function ln(t){let e=t?.params||t?.parameters||{};return{...t||{},action:String(t?.action||"").trim().toUpperCase(),params:e,parameters:e}}var Nt="AIHubAdapterRuntime",Lt="AIHubAdapter";function Lo(t){let e=t?.params||t?.parameters||{};return{...t||{},params:e,parameters:e}}function q(){return!!(window[Nt]?.executeAction||window[Lt]?.handleAction)}async function Pt(t){return(await K(t)).succeeded}async function K(t){let e=Lo(t);if(window[Nt]?.executeAction){let n=window[Nt],r=await n.executeAction(e)===!0,o=n.lastActionResult||{};return{succeeded:r,handled:o.handled===!0||r,status:o.status||(r?"ok":"not_handled"),reason:o.reason||"",blocked:o.status==="blocked",disabled:o.status==="disabled"}}if(window[Lt]?.handleAction){let n=await window[Lt].handleAction(e)===!0;return{succeeded:n,handled:n,status:n?"ok":"not_handled",reason:"",blocked:!1,disabled:!1}}return{succeeded:!1,handled:!1,status:"missing_adapter",reason:"",blocked:!1,disabled:!1}}var Po=Object.freeze([{path:"/api/products?per_page=96",routePrefix:"/product/"},{path:"/api/products",routePrefix:"/product/"},{path:"/api/products.json",routePrefix:""},{path:"/products.json",routePrefix:"/products/"},{path:"/collections/all/products.json",routePrefix:"/products/"}]),vo=Object.freeze(["products","data","items","results"]),pn=Object.freeze(["id","product_id","handle","sku"]),fn=Object.freeze(["name","title"]),Do=Object.freeze(["url","href","permalink","product_url"]),Uo=Object.freeze(["image_url","imageUrl","image_src","imageSrc","image","images","media","thumbnail","thumbnail_url","featured_image","featuredImage","featured_image_url"]),Mo=Object.freeze(["brand","vendor"]),ko=Object.freeze(["category","category_name","product_type"]),Fo=Object.freeze(["description","summary","body_html"]),Ho=Object.freeze(["original_price","compare_at_price","regular_price"]),mn=Object.freeze(["currency","currency_code"]),Bo=Object.freeze(["display_price","price_text","formatted_price"]),Yo="Unknown Brand",$o="Products",jo="/",zo=/^[a-z0-9][a-z0-9-]*$/i,vt=null;function A(t){return t==null||typeof t=="object"?"":String(t||"").trim()}function Mt(t){return A(t).toLowerCase().replace(/[^a-z0-9]+/g," ").trim()}function yn(t){let e=new Set(["a","am","an","and","ask","asked","did","for","me","not","on","only","please","show","some","the","to","wanna","want","what","with","you","your"]),n=[],r=new Set;for(let o of Wo(Mt(t)).split(" ")){let a=Vo(o);a.length<=1||e.has(a)||r.has(a)||(n.push(a),r.add(a))}return n}function Wo(t){return t.replace(/\b(?:i\s+)?did\s+not\s+ask\s+for\s+(?:a\s+|an\s+)?[a-z0-9]+\b/g," ")}function Vo(t){return["phone","phones","mobile","mobiles"].includes(t)?"phone":["book","books"].includes(t)?"books":t}function kt(t,e){return e.map(n=>A(t?.[n])).filter(Boolean)}function O(t,e){return kt(t,e)[0]||""}function st(t){let e=A(t).replace(/,/g,"");if(!e)return 0;let n=e.match(/-?\d+(?:\.\d+)?/),r=Number(n?n[0]:e);return Number.isFinite(r)?r:0}function Go(t,e){let n=O(t,Bo);if(n)return n;let r=O(t,mn).toUpperCase();return e>0&&r?`${r} ${e.toLocaleString()}`:e>0?e.toLocaleString():""}function qo(t){for(let e of Uo){let n=Dt(t?.[e]);if(n)return n}return""}function Dt(t){if(!t)return"";if(Array.isArray(t)){for(let e of t){let n=Dt(e);if(n)return n}return""}if(typeof t=="object"){for(let e of["src","url","image_url","imageUrl","image_src","imageSrc","thumbnail","thumbnail_url","featured_image","featuredImage","featured_image_url"]){let n=Dt(t[e]);if(n)return n}return""}return Ko(t)}function Ko(t){let e=A(t);if(!e||/^javascript:/i.test(e))return"";if(/^data:image\//i.test(e))return e;try{let n=new URL(e,window.location.origin);return["http:","https:"].includes(n.protocol)?n.toString():""}catch{return""}}function Qo(t){let e=A(t);if(!e)return"";try{let n=new URL(e,window.location.origin);return n.origin!==window.location.origin?"":`${n.pathname}${n.search}${n.hash}`}catch{return""}}function Xo(t,e,n){let r=Qo(O(t,Do));return r||(!zo.test(e)||!/[a-z]/i.test(e)||!n?.routePrefix?"":`${n.routePrefix}${encodeURIComponent(e)}${jo}`)}function Ft(t,e={}){if(!t)return null;let n=O(t,pn),r=A(t.handle||t.slug||t.product_handle),o=O(t,fn),a=st(t.price||t.amount||t.cost),i=st(O(t,Ho));return!n&&!r?null:{id:n,handle:r,name:o,title:A(t.title||o),brand:O(t,Mo)||Yo,category:O(t,ko)||$o,description:O(t,Fo),price:Number.isFinite(a)?a:0,originalPrice:Number.isFinite(i)?i:0,displayPrice:Go(t,a),currency:O(t,mn),rating:st(t.rating||t.review_rating),reviewCount:st(t.review_count||t.reviews_count||t.reviews),imageUrl:qo(t),url:Xo(t,r||n,e)}}function Jo(t){return kt(t,pn)}function dn(t){return kt(t,fn).map(Mt)}function _n(t,e){let n=A(e);return!!(n&&Jo(t).includes(n))}function hn(t,e){let n=yn(e);if(!n.length)return!1;let r=Mt([t?.name,t?.title,t?.brand,t?.category,t?.category_name,t?.product_type,t?.description,t?.tags].join(" "));return n.every(o=>r.includes(o)||r.includes(o.replace(/s$/,"")))}function Zo(t,e){let n=new Set(dn(e));return dn(t).some(r=>n.has(r))}function ta(t,e){return!!(t?.imageUrl&&t.imageUrl===e?.imageUrl)}function ea(t){if(Array.isArray(t))return t;for(let e of vo){let n=t?.[e];if(Array.isArray(n))return n}return[]}async function na(t){try{let e=await fetch(new URL(t.path,window.location.origin),{headers:{Accept:"application/json"}});if(!e.ok)return[];let n=await e.json();return ea(n).map(r=>Ft(r,t)).filter(Boolean)}catch(e){return console.warn(`[AI Hub Widget] Catalog endpoint lookup failed for ${t.path}:`,e),[]}}async function Ut(){return vt||(vt=Promise.all(Po.map(na)).then(t=>t.flat())),vt}async function ra(t,e=120){if(!yn(t).length)return[];let r=new URL("/v1/products",d.apiUrl);r.searchParams.set("site_id",d.siteId),r.searchParams.set("limit",String(e));try{let o=await fetch(r.toString(),{headers:{Accept:"application/json"}});return o.ok?(await o.json()).map(a=>Ft(a)).filter(Boolean).filter(a=>hn(a,t)).slice(0,12):[]}catch(o){return console.warn("[AI Hub Widget] Hub product search fallback failed:",o),[]}}async function gn(t,e=""){let n=(Array.isArray(t)?t:[]).map(A).filter(Boolean),r=[],o="",a="";if(n.length)try{r=await bn(n),o="hub_by_ids"}catch(i){a="hub_product_lookup_failed",console.warn("[AI Hub Widget] Hub product ID lookup failed:",i)}if(!r.length&&n.length){let i=await Ut();r=n.map(c=>i.find(f=>_n(f,c))).filter(Boolean),r.length&&(o="host_by_ids")}return!r.length&&e&&(r=await ra(e),r.length&&(o="hub_search")),!r.length&&e&&(r=(await Ut()).filter(c=>hn(c,e)).slice(0,12),r.length&&(o="host_search")),{products:r,source:o,reason:r.length?"":a||"no_matching_products_rendered"}}async function bn(t){let e=(Array.isArray(t)?t:[]).map(A).filter(Boolean);if(!e.length)return[];let n=new URL(E.PRODUCTS_BY_IDS,d.apiUrl);n.searchParams.set("site_id",d.siteId),n.searchParams.set("ids",e.join(","));let r=await fetch(n.toString(),{headers:{Accept:"application/json"}});if(!r.ok)throw new Error("Failed to fetch products from AI Hub API");let o=(await r.json()).map(i=>Ft(i)).filter(Boolean),a=new Map(o.map(i=>[String(i.id),i]));return e.map(i=>a.get(i)).filter(Boolean)}async function ct(t){let e=A(t);if(!e)return"";let[n]=await bn([e]);if(n?.url)return n.url;let r=await Ut(),o=r.find(i=>_n(i,e));return o?.url?o.url:n&&r.find(i=>Zo(i,n)||ta(i,n))?.url||""}var oa=["data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='320' height='240' viewBox='0 0 320 240'%3E","%3Crect width='320' height='240' fill='%23f1f2ee'/%3E","%3Cpath d='M98 156h124l-31-40-25 30-17-22-51 32Z' fill='%23c8c3ba'/%3E","%3Ccircle cx='117' cy='95' r='17' fill='%23d8d3ca'/%3E","%3Ctext x='160' y='198' text-anchor='middle' fill='%23686660' font-family='Arial,sans-serif' font-size='16'%3EImage pending%3C/text%3E","%3C/svg%3E"].join(""),Tn=12,Bt=[],Yt=R;function H(t){return String(t??"").replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;").replace(/"/g,"&quot;").replace(/'/g,"&#039;")}function aa(){if(document.getElementById("mayabot-product-overlay-styles"))return;let t=document.createElement("style");t.id="mayabot-product-overlay-styles",t.textContent=`
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
  `,document.head.appendChild(t)}function ia(){aa();let t=document.getElementById("mayabot-product-panel");return t||(t=document.createElement("div"),t.id="mayabot-product-panel",t.setAttribute("aria-live","polite"),t.innerHTML=`
    <div class="mayabot-product-header">
      <h2 class="mayabot-product-title">${R}</h2>
      <button class="mayabot-product-close" type="button" aria-label="Close recommendations">&times;</button>
    </div>
    <div class="mayabot-product-grid"></div>
  `,t.querySelector(".mayabot-product-close").addEventListener("click",()=>{t.classList.remove("active")}),document.body.appendChild(t),t)}async function sa(t){let e={action:s.ADD_TO_CART,params:{[l.PRODUCT_ID]:t,[l.QUANTITY]:gt},parameters:{[l.PRODUCT_ID]:t,[l.QUANTITY]:gt}};q()&&await Pt(e)||window.dispatchEvent(new CustomEvent(W.MAYABOT_ACTION,{detail:e}))}async function ca(t){try{let n=await ct(t);if(n){window.location.href=n;return}}catch(n){console.warn("[AI Hub Widget] Product detail URL lookup failed:",n)}let e={action:s.SHOW_PRODUCT_DETAIL,params:{[l.PRODUCT_ID]:t},parameters:{[l.PRODUCT_ID]:t}};q()&&await Pt(e)||window.dispatchEvent(new CustomEvent(W.MAYABOT_ACTION,{detail:e}))}function ua(t){return t<=1?"count-1":t===2?"count-2":t===3?"count-3":"count-many"}function la(t){return t<=1?1:t===2?2:3}function da(t){let e=new Set;return(Array.isArray(t)?t:[]).map(n=>String(n??"").trim()).filter(Boolean).filter(n=>e.has(n)?!1:(e.add(n),!0))}function Ht(t,e,n="",r={}){let o=(Array.isArray(e)?e:[]).map(f=>String(f?.id??"").trim()).filter(Boolean),a=o.length,i=t.length,c=a>0?"succeeded":"failed";return{status:c,stage:"product_overlay",reason:n||(c==="succeeded"?"":"no_matching_products_rendered"),evidence:{requested_product_count:i,rendered_product_count:a,missing_product_count:Math.max(i-a,0),requested_product_ids:t.slice(0,Tn).join(","),rendered_product_ids:o.slice(0,Tn).join(","),lookup_source:r.source||"",search_query:r.searchQuery||""}}}function pa(t){let e=String(t?.displayPrice||"").trim();if(e)return e;let n=Number(t?.price||0);return Number.isFinite(n)&&n>0?n.toLocaleString():"Price unavailable"}function ut(t,e){let n=ia(),r=n.querySelector(".mayabot-product-grid"),o=n.querySelector(".mayabot-product-title"),a=t.length;if(Bt=Array.isArray(t)?[...t]:[],Yt=e||R,n.classList.remove("count-1","count-2","count-3","count-many"),n.classList.add(ua(a)),n.style.setProperty("--mayabot-card-count",String(la(a))),o.textContent=Yt,!a){r.innerHTML='<p class="mayabot-product-empty">No matching products are currently available.</p>',n.classList.add("active"),An();return}r.innerHTML=t.map(i=>{let c=H(i.id);return`
        <article class="mayabot-product-card" data-product-id="${c}">
          <img class="mayabot-product-image" src="${H(i.imageUrl||oa)}" alt="${H(i.name)}">
          <h3 class="mayabot-product-name">${H(i.name||i.title||"Product")}</h3>
          <p class="mayabot-product-meta">${H(i.brand)} - ${H(pa(i))}</p>
          <div class="mayabot-product-actions">
            <button type="button" data-add="${c}">Add</button>
            <button type="button" class="secondary" data-view="${c}">View</button>
          </div>
        </article>
      `}).join(""),r.querySelectorAll("[data-add]").forEach(i=>{i.addEventListener("click",async()=>{await sa(i.getAttribute("data-add"))})}),r.querySelectorAll("[data-view]").forEach(i=>{i.addEventListener("click",async()=>{await ca(i.getAttribute("data-view"))})}),n.classList.add("active"),An()}function An(){window.setTimeout(()=>{let t=document.getElementById("mayabot-chat"),e=document.getElementById("mayabot-msgs");e&&(e.innerHTML=""),t&&t.classList.remove("visible")},k)}async function Sn(t,e=R,n={}){let r=da(t),o=String(n.searchQuery||"").trim();if(!r.length&&!o)return ut([],e),Ht([],[],"missing_product_ids");try{let{products:a,source:i,reason:c}=await gn(r,o);return ut(a,e),Ht(r,a,c,{source:i,searchQuery:o})}catch(a){return console.warn("[AI Hub Widget] Product overlay failed:",a),ut([],e),Ht(r,[],"product_overlay_fetch_failed",{searchQuery:o})}}function In(t={}){if(!Bt.length)return!1;let e=String(t.sort_by||t.sortBy||"price_asc").trim().toLowerCase(),n=[...Bt].sort((r,o)=>fa(r,o,e));return ut(n,ma(Yt,e)),!0}function fa(t,e,n){return n==="price_desc"?B(e.price,Number.NEGATIVE_INFINITY)-B(t.price,Number.NEGATIVE_INFINITY):n==="rating"?B(e.rating||e.review_rating,Number.NEGATIVE_INFINITY)-B(t.rating||t.review_rating,Number.NEGATIVE_INFINITY):n==="newest"?En(e)-En(t):B(t.price,Number.POSITIVE_INFINITY)-B(e.price,Number.POSITIVE_INFINITY)}function B(t,e){let n=String(t??"").replace(/,/g,"").match(/-?\d+(?:\.\d+)?/);if(!n)return e;let r=Number(n[0]);return Number.isFinite(r)?r:e}function En(t){let e=t?.updated_at||t?.created_at||t?.date||"",n=Date.parse(String(e||""));return Number.isFinite(n)?n:0}function ma(t,e){let n={price_asc:"sorted low to high",price_desc:"sorted high to low",rating:"sorted by rating",newest:"newest first"};return`${String(t||R).replace(/\s+-\s+sorted.*$/i,"")} - ${n[e]||n.price_asc}`}function wn(t){return t.action===s.SHOW_PRODUCTS||t.action===s.SHOW_COMPARISON||t.action===s.SHOW_PRODUCT_DETAIL||t.action===s.SORT_PRODUCTS}async function xn(t){return t.action===s.SHOW_COMPARISON?On(t.parameters||{},"Product comparison",{syncListing:!1}):t.action===s.SHOW_PRODUCTS?On(t.parameters||{},R):t.action===s.SHOW_PRODUCT_DETAIL?ha(t.parameters||{}):t.action===s.SORT_PRODUCTS?In(t.parameters||{}):!1}async function On(t,e=R,n={}){let r=Array.isArray(t[l.PRODUCT_IDS])?t[l.PRODUCT_IDS]:[],o=_a(t),i=n.syncListing!==!1?await ya(o):{succeeded:!1,handled:!1,status:"skipped",stage:"product_display_sync",reason:"comparison_overlay"},c=await Sn(r,t.title||o||e,{searchQuery:o}),f={...c.evidence||{},listing_sync_status:i.status||"",listing_sync_stage:i.stage||"",listing_sync_reason:i.reason||""};return c.status!=="succeeded"?{...c,evidence:f}:o&&i.handled&&!i.succeeded?{status:"failed",stage:"product_display_sync",reason:i.reason||i.status||"listing_sync_failed",evidence:f}:{...c,stage:i.succeeded?"product_display_sync":c.stage,evidence:f}}async function ya(t){let e=Rn(t);return e?K({action:s.FILTER_PRODUCTS,params:{[l.SEARCH_QUERY]:e,query:e,q:e}}):{succeeded:!1,handled:!1,status:"skipped",stage:"product_display_sync",reason:"missing_search_query"}}function _a(t){return Rn(t[l.SEARCH_QUERY]||t.search||t.query||t.q||"")}function Rn(t){return String(t||"").trim()}async function ha(t){let e="";try{e=await ct(t[l.PRODUCT_ID])}catch(n){return console.warn("[AI Hub Widget] Product detail URL lookup failed:",n),!1}return e?(window.location.href=e,!0):!1}var $t="stop_action_fallback",ga=new Set([s.SHOW_PRODUCTS,s.SHOW_COMPARISON,s.SHOW_PRODUCT_DETAIL,s.SORT_PRODUCTS]);function Cn(t){return q()&&!ga.has(t.action)}async function Nn(t){let e=await K(t);return e.succeeded?!0:e.blocked||e.disabled?$t:!1}function Ln(t){return window.dispatchEvent(new CustomEvent(W.MAYABOT_ACTION,{detail:t})),!0}var ba=Object.freeze([{name:"runtime_adapter",canExecute:Cn,execute:Nn},{name:"product_overlay",canExecute:wn,execute:xn},{name:"entity_overlay",canExecute:qe,execute:Ke},{name:"handoff_overlay",canExecute:nn,execute:rn},{name:"platform_adapter",canExecute:()=>!0,execute:Ae},{name:"provider_adapter",canExecute:ve,execute:De},{name:"navigation",canExecute:an,execute:sn},{name:"browser_event",canExecute:()=>!0,execute:Ln}]);async function zt(t){let e=[];for(let n of t||[]){let r=ln(n),o=await Ta(r);o&&e.push(o)}return e}async function Ta(t){if(!t.action)return;let e=Date.now(),n=window.location.href;await et(d.apiUrl,d.siteId,t,{status:"requested",stage:"widget_dispatch",requested_url:n,final_url:n,evidence:jt(t,n,n)}),await et(d.apiUrl,d.siteId,t,{status:"executing",stage:"widget_dispatch",requested_url:n,final_url:window.location.href,evidence:jt(t,n,window.location.href)});let r;try{r=await Aa(t)}catch(i){r={status:"failed",stage:"widget_dispatch",reason:i instanceof Error?i.message:"execution_error"}}let o=window.location.href,a=jt(t,n,o,r);return await et(d.apiUrl,d.siteId,t,{status:r.status,stage:r.stage,reason:r.reason,duration_ms:Date.now()-e,requested_url:n,final_url:o,evidence:a}),{action:t.action,request_id:t.request_id||t.action_request_id||"",turn_id:t.turn_id||"",sequence:Number(t.sequence||0),status:r.status,stage:r.stage,reason:r.reason,requested_url:n,final_url:o,evidence:a}}async function Aa(t){if(!t.action)return{status:"failed",stage:"normalization",reason:"missing_action"};for(let e of ba){if(!e.canExecute(t))continue;let n=await e.execute(t),r=Ea(n,e.name);if(r)return r}return{status:"failed",stage:"all",reason:"no_executor_succeeded"}}function Ea(t,e){if(t===!0)return{status:"succeeded",stage:e,reason:""};if(t===$t)return{status:"blocked",stage:e,reason:"action_blocked"};if(!t||typeof t!="object")return null;let n=String(t.status||"").trim().toLowerCase();return n?{status:n,stage:String(t.stage||e).trim()||e,reason:String(t.reason||"").trim(),evidence:t.evidence&&typeof t.evidence=="object"?t.evidence:{}}:null}function jt(t,e,n,r={}){let o=t.parameters||t.params||{},a={requested_url:e,final_url:n,url_changed:e!==n,path_changed:Pn(e)!==Pn(n),title:document.title||"",stage:r.stage||"",result_status:r.status||""};return o.page&&(a.target_page=o.page),o.product_id&&(a.product_id=o.product_id),o.entity_id&&(a.entity_id=o.entity_id),Array.isArray(o.product_ids)&&(a.product_count=o.product_ids.length),Array.isArray(o.entity_ids)&&(a.entity_count=o.entity_ids.length),{...a,...r.evidence&&typeof r.evidence=="object"?r.evidence:{}}}function Pn(t){try{return new URL(t,window.location.href).pathname}catch{return""}}var Sa=1,Ia=1.08,Oa=300,wa=Object.freeze(["hannah","sonia","libby","ava","susan","hazel","heera","salli","joanna","amy","emma","olivia","natasha","zira","aria","jenny","samantha","victoria","tessa","moira","karen","female","woman","nova","shimmer","google us english","microsoft aria"]),N="",lt="",Q=null,Wt=0;function X(t){if(!("speechSynthesis"in window)||!("SpeechSynthesisUtterance"in window))return!1;dt();let e=++Wt;N=t;let n=()=>{if(e!==Wt||N!==t)return!1;try{let r=new SpeechSynthesisUtterance(t),o=xa(window.speechSynthesis.getVoices());return o?(o&&(r.voice=o),r.rate=Sa,r.pitch=Ia,r.onstart=vn,r.onend=vn,dt(),window.speechSynthesis.cancel(),window.speechSynthesis.resume(),window.speechSynthesis.speak(r),!0):(N="",!1)}catch{return!1}};return window.speechSynthesis.getVoices().length>0?n():(window.speechSynthesis.onvoiceschanged=n,Q=window.setTimeout(()=>{Q=null,n()},Oa),!0)}function pt(){N&&X(N)}function Dn(){try{return!!N||!!window.speechSynthesis?.speaking||!!window.speechSynthesis?.pending}catch{return!!N}}function Un(){Wt+=1,dt(),N="",lt="";try{window.speechSynthesis?.cancel()}catch{}}function xa(t){if(!Array.isArray(t)||t.length===0)return null;let e=Ra(t)||Ca(t);return e&&(lt=e.name),e}function Ra(t){if(lt){let n=t.find(r=>r.name===lt);if(n)return n}let e=String(d.speechVoiceName||"").toLowerCase();return e&&t.find(n=>n.name.toLowerCase()===e)||null}function Ca(t){return d.speechVoicePreference.toLowerCase()!=="female"?t.find(e=>e.default)||t[0]:t.find(e=>wa.some(n=>e.name.toLowerCase().includes(n)))||null}function vn(){dt(),N=""}function dt(){Q&&window.clearTimeout(Q),Q=null,window.speechSynthesis&&(window.speechSynthesis.onvoiceschanged=null)}var Na=3,La="AIHubAdapterRuntime",Pa="AIHubAdapter";function va(t,e){let n=new URL(E.SHOP_WS,t);return n.protocol=n.protocol==="https:"?"wss:":"ws:",n.searchParams.set("site_id",e),n.searchParams.set("session_id",d.sessionId),n.toString()}function Da(t){return new Promise((e,n)=>{let r=new FileReader;r.onloadend=()=>{let o=String(r.result||"");e(o.includes(",")?o.split(",").pop():o)},r.onerror=()=>n(r.error||new Error("Failed to read audio blob")),r.readAsDataURL(t)})}var Vt=class{constructor(){this.queue=[],this.blocked=[],this.playing=!1,this.current=null,this.lastPlaybackStartMs=0,this.installUnlockListeners()}push(e,n=""){e&&(this.queue.push({audioB64:e,fallbackText:n}),this.playNext())}playNext(){if(this.playing||this.queue.length===0)return;this.playing=!0;let e=this.queue.shift(),n=new Audio(z.DATA_WAV_PREFIX+e.audioB64);n.preload="auto",this.current=n,n.onplay=()=>{this.lastPlaybackStartMs=typeof performance<"u"?performance.now():0},n.onended=()=>{this.current=null,this.playing=!1,this.playNext()},n.onerror=()=>{this.current=null,e.fallbackText&&Y(e.fallbackText),this.playing=!1,this.playNext()},n.play().catch(r=>{if(console.warn("Audio playback failed",r),this.current=null,this.isAutoplayBlocked(r)){e.fallbackText?Y(e.fallbackText):this.blocked.unshift(e),this.playing=!1;return}e.fallbackText&&Y(e.fallbackText),this.playing=!1,this.playNext()})}installUnlockListeners(){if(typeof window>"u")return;let e=()=>{this.retryBlocked(),pt()};window.addEventListener("pointerdown",e,{capture:!0,passive:!0}),window.addEventListener("keydown",e,{capture:!0}),window.addEventListener("touchstart",e,{capture:!0,passive:!0})}retryBlocked(){this.blocked.length&&(this.queue.unshift(...this.blocked.splice(0)),this.playNext())}speakInsteadOfBlocked(e){!e||!this.blocked.length||(this.blocked=[],Y(e))}isAutoplayBlocked(e){let n=`${e?.name||""} ${e?.message||e||""}`.toLowerCase();return n.includes("notallowed")||n.includes("user didn't interact")||n.includes("not allowed")}stop(){if(this.queue=[],this.blocked=[],this.current){try{this.current.pause(),this.current.currentTime=0}catch{}this.current.onended=null,this.current.onerror=null,this.current=null}this.playing=!1,Un()}isSpeaking(){return this.playing||this.queue.length>0||Dn()}},ft=new Vt;function Kt(){ft.stop()}function Mn(){return ft.isSpeaking()}var Gt=class{async sendAudio(e,n,r=[]){let o=new FormData;o.append("audio",e,Fa(e)),o.append("site_id",d.siteId),o.append("session_id",d.sessionId),r&&r.length>0&&o.append("conversation_history",JSON.stringify(r));let a=Hn();a&&o.append("page_context",JSON.stringify(a));let i=await fetch(`${d.apiUrl}${E.SHOP}`,{method:de.POST,body:o});if(!i.ok)throw new Error("AI Hub API request failed");let c=await i.json();if(c.transcript&&n.onUserMessage?.(c.transcript),c.response_text&&n.onAssistantMessage?.(c.response_text,c.ui_actions||[]),n.onStatusChange?.(m.READY),c.audio_b64?ka(c.audio_b64,c.response_text||""):c.response_text&&Y(c.response_text),c.ui_actions&&c.ui_actions.length>0){let f=await zt(c.ui_actions);n.onActionResults?.(f)}n.onComplete?.(c)}},qt=class{constructor(){this.ws=null,this.connected=!1,this.connecting=null,this.failed=!1,this.retries=0,this.audioQueue=ft,this.callbacks=null,this.turnText="",this.receivedAudio=!1}async ensureConnected(e=[]){return this.canUseWebSocket()?this.isOpen()?!0:this.connecting?this.connecting:(this.connecting=this.openConnection(e),this.connecting):!1}canUseWebSocket(){return!this.failed&&d.useWebSocket&&"WebSocket"in window}isOpen(){return this.connected&&this.ws?.readyState===WebSocket.OPEN}openConnection(e=[]){return new Promise(n=>{let r=new WebSocket(va(d.apiUrl,d.siteId)),o=!1;this.ws=r;let a=(c=null)=>{o||(o=!0,this.markConnectionFailed(n,c,r))},i=window.setTimeout(()=>{a()},he);r.onopen=()=>{o||(o=!0,this.handleConnectionOpen(i,e,n))},r.onmessage=c=>{this.handleMessage(c).catch(f=>this.handleTransportError(f))},r.onerror=()=>a(i),r.onclose=()=>{this.connected=!1,a(i)}})}markConnectionOpen(){this.connected=!0,this.connecting=null,this.retries=0}handleConnectionOpen(e,n,r){window.clearTimeout(e),this.markConnectionOpen(),this.sendConfig(n),r(!0)}markConnectionFailed(e,n=null,r=null){n&&window.clearTimeout(n),this.connected=!1,this.connecting=null,this.retries+=1,this.retries>=Na&&(this.failed=!0),r&&r.readyState!==WebSocket.CLOSED&&r.close(),e(!1)}sendConfig(e=[]){this.sendJson({type:S.CONFIG,history:e||[],session_id:d.sessionId,page_context:Hn()})}sendJson(e){return!this.ws||this.ws.readyState!==WebSocket.OPEN?!1:(this.ws.send(JSON.stringify(e)),!0)}async sendAudio(e,n,r=[]){if(!await this.ensureConnected(r))return!1;this.callbacks=n,this.turnText="",this.receivedAudio=!1,this.sendConfig(r);let a=await Da(e);return this.sendJson({type:S.AUDIO_CHUNK,data:a,mime_type:e?.type||""}),this.sendJson({type:S.AUDIO_END,mime_type:e?.type||""}),!0}async handleMessage(e){let n=this.callbacks;if(!n)return;let r=this.parseMessage(e.data);if(!r){this.completeWithError(n,"Invalid WebSocket message");return}if(!this.handleIncrementalMessage(r,n)){if(r.type===S.DONE){await this.handleDoneMessage(r,n);return}r.type===S.ERROR&&this.completeWithError(n,r.message||"WebSocket error")}}parseMessage(e){try{let n=JSON.parse(e);return n&&typeof n=="object"?n:null}catch{return null}}handleIncrementalMessage(e,n){return e.type===S.TRANSCRIPT?(n.onUserMessage?.(e.text||""),!0):e.type===S.TEXT_CHUNK?(this.turnText+=e.text||"",n.onAssistantChunk?.(e.text||"",this.turnText),!0):e.type===S.AUDIO_CHUNK?(this.receivedAudio=!!e.audio_b64||this.receivedAudio,this.audioQueue.push(e.audio_b64),!0):!1}async handleDoneMessage(e,n){let r=e.response_text||this.turnText;n.onAssistantMessage?.(r,e.ui_actions||[],{streamed:!0}),n.onStatusChange?.(m.READY),!this.receivedAudio&&r?Y(r):this.receivedAudio&&r&&this.audioQueue.speakInsteadOfBlocked(r);try{if(e.ui_actions&&e.ui_actions.length>0){let o=await zt(e.ui_actions);n.onActionResults?.(o)}n.onComplete?.(e)}catch(o){this.handleTransportError(o)}finally{this.callbacks=null}}completeWithError(e,n){e.onStatusChange?.(m.ERROR,Fn(n)),e.onComplete?.({error:n}),this.callbacks=null}handleTransportError(e){console.error("AI Hub WebSocket transport failed",e);let n=this.callbacks;n&&this.completeWithError(n,String(e))}},Ua=new Gt,Ma=new qt;async function kn(t,e,n,r=[]){try{if(d.useWebSocket&&await Ma.sendAudio(t,n,r))return;await Ua.sendAudio(t,n,r)}catch(o){console.error(o),n.onStatusChange?.(m.ERROR,Fn(o)),n.onComplete?.({error:String(o)})}}function ka(t,e=""){ft.push(t,e)}function Fa(t){let e=String(t?.type||"").toLowerCase();return e.includes("mp4")?"audio.mp4":e.includes("ogg")?"audio.ogg":e.includes("wav")?"audio.wav":z.WEBM_FILENAME}function Fn(t){let e=String(t?.message||t||"").toLowerCase();return e.includes("quota")?"Quota reached":e.includes("microphone")||e.includes("permission")?"Mic unavailable":e.includes("voice")||e.includes("transcription")||e.includes("speech")?"Voice unavailable":e.includes("network")||e.includes("fetch")||e.includes("api request")?"Connection issue":"Try again"}function Y(t){return t?X(String(t).slice(0,700)):!1}function Hn(){let t=window[La],e=window[Pa];try{if(typeof t?.getContext=="function")return t.getContext();if(typeof e?.getContext=="function")return e.getContext()}catch(n){console.warn("[AI Hub Widget] Page context collection failed:",n)}return null}var Ha=4,Ba=40,Ya=24,$a=80,ja=120;function Yn(){let t=[];function e(n,r){let o=String(r||"").trim();o&&(t.push({role:n,content:o}),t.length>pe&&t.shift())}return{history:t,rememberUserMessage(n){e("user",n)},rememberAssistantMessage(n,r){e("assistant",za(n,r))},rememberActionResults(n){let r=Va(n);r&&e("assistant",r)}}}function za(t,e){let n=Wa(e);return n.length?`${t} [PRODUCT_IDS: ${n.join(",")}]`:t}function Wa(t){let e=[];for(let n of t||[]){let r=n.params||{};Bn(e,r[l.PRODUCT_IDS]),Bn(e,[r[l.PRODUCT_ID]])}return e}function Bn(t,e){for(let n of Array.isArray(e)?e:[])n&&!t.includes(n)&&t.push(n)}function Va(t){let e=(Array.isArray(t)?t:[]).map(Ga).filter(Boolean).slice(0,Ha);return e.length?`[BROWSER_ACTION_RESULTS: ${e.join(" | ")}]`:""}function Ga(t){if(!t||typeof t!="object"||!t.action)return"";let e=[mt(t.action,Ba),`status=${mt(t.status,Ya)||"unknown"}`],n=Ka(t.final_url);return n&&e.push(`final_path=${mt(n,ja)}`),t.reason&&e.push(`reason=${mt(t.reason,$a)}`),qa(e,t.evidence),e.join(" ")}function qa(t,e={}){e.rendered_product_count!==void 0&&t.push(`rendered_products=${Number(e.rendered_product_count||0)}`),e.rendered_entity_count!==void 0&&t.push(`rendered_records=${Number(e.rendered_entity_count||0)}`)}function mt(t,e){return String(t||"").replace(/\s+/g," ").trim().slice(0,e)}function Ka(t){try{let e=new URL(String(t||""),window.location.href);return`${e.pathname}${e.search}${e.hash}`}catch{return""}}var $n=null;function Qt(t){$n||(jn(t),$n=window.setInterval(()=>jn(t),_e))}async function jn({boot:t,shutdownWidget:e}){try{if(await Qa()){t();return}e()}catch{t()}}async function Qa(){let t=new URL(E.WIDGET_STATUS,d.apiUrl);t.searchParams.set("site_id",d.siteId);let e=await fetch(t.toString(),{cache:"no-store",headers:{Accept:"application/json"}});return e.ok?(await e.json()).enabled!==!1:!0}window.__mayabot_identifier="voice-orb";var Xt=null,Jt=null;function zn(){if(window.__mayabotBooted||document.getElementById("mayabot-widget"))return;window.__mayabotBooted=!0,Zt();let t=ue(),e=null;function n(p=fe){e&&window.clearTimeout(e),e=window.setTimeout(()=>{t.msgs.innerHTML="",t.chat.classList.remove("visible"),e=null},p)}function r(p,w=""){t.status.className="",p===m.RECORDING?(e&&(window.clearTimeout(e),e=null),t.msgs.innerHTML="",t.btn.classList.add("recording"),t.chat.classList.add("visible"),t.status.innerText="Listening...",t.status.classList.add("listening")):p===m.PROCESSING?(t.btn.classList.remove("recording"),t.chat.classList.add("visible"),t.status.innerText="Analyzing...",t.status.classList.add("processing")):p===m.READY?(t.status.innerText="Ready",t.status.classList.add("ready")):p===m.ERROR&&(t.status.innerText=w||"Try again",t.status.classList.add("error"),t.btn.classList.remove("recording"))}let o=Yn(),a=null,i="",c=!1;async function f(p){if(!c){c=!0,t.btn.disabled=!0,a=null,i="";try{await kn(p,t,{onUserMessage:w=>{j(t,w,"user"),o.rememberUserMessage(w)},onAssistantChunk:(w,yt)=>{i=yt,a||(a=j(t,"","ai")),ht(t,a,i)},onAssistantMessage:(w,yt,Gn={})=>{Gn.streamed&&a?ht(t,a,w):j(t,w,"ai"),o.rememberAssistantMessage(w,yt),a=null,i=""},onActionResults:o.rememberActionResults,onStatusChange:r,onComplete:()=>n()},o.history)}finally{c=!1,t.btn.disabled=!1,a=null,i=""}}}let h=ge(f,r);Xt=h;let g=!1,b=null;function v(){return Mn()?(Kt(),r(m.READY),!0):!1}t.btn.setAttribute("aria-label","Maya voice assistant. Tap to talk, or tap to stop when speaking."),t.btn.setAttribute("title","Tap to talk \u2014 tap or press Escape to stop Maya"),t.btn.addEventListener("pointerdown",()=>{v()&&(g=!0,b&&window.clearTimeout(b),b=window.setTimeout(()=>{g=!1,b=null},750))},{capture:!0}),t.btn.addEventListener("click",()=>{if(g){g=!1,b&&window.clearTimeout(b),b=null;return}c||v()||h.toggle()});let _=p=>{p.key==="Escape"&&v()};document.addEventListener("keydown",_);let D=p=>{t.btn.contains(p.target)||pt()};document.addEventListener("pointerdown",D,{capture:!0}),Jt=()=>{document.removeEventListener("keydown",_),document.removeEventListener("pointerdown",D,{capture:!0}),b&&window.clearTimeout(b),Jt=null},Xa()&&(Ja(),window.setTimeout(()=>{if(o.history.length>0)return;let p=`Welcome to ${d.brandName}. How can I help you today?`;j(t,p,"ai"),r(m.READY),n(ye),X(p)},me))}function Wn(){Xt?.cancel(),Xt=null,Jt?.(),Kt(),window.__mayabotBooted=!1,document.getElementById("mayabot-widget")?.remove(),document.getElementById("mayabot-product-panel")?.remove()}function Xa(){if(!d.autoGreet||!Za())return!1;try{return window.sessionStorage.getItem(Vn())!=="1"}catch{return!window.__mayabotAutoGreeted}}function Ja(){window.__mayabotAutoGreeted=!0;try{window.sessionStorage.setItem(Vn(),"1")}catch{}}function Vn(){return`mayabot:auto-greeted:${d.siteId}`}function Za(){let t=window.location.pathname.replace(/\/+$/,"")||"/";return t==="/"||t.endsWith("/index.html")}document.readyState==="loading"?document.addEventListener("DOMContentLoaded",()=>Qt({boot:zn,shutdownWidget:Wn})):Qt({boot:zn,shutdownWidget:Wn});})();
